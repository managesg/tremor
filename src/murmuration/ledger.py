"""Permission replay ledger.

Reads Claude Code transcript JSONL, extracts tool-call permission events, and
replays candidate policies over the SAME event stream (counterfactual: it cannot
know what the agent would have done under a different decision).
Stdlib only. Never reads prompt text or tool output beyond the denial marker.
"""
import glob
import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime

# Verified on a real transcript: a denied call is a tool_result with is_error and this text.
# The second pattern (user-declined prompt) is UNVERIFIED; override with --deny-regex.
DENY_RE = re.compile(r"Permission to use .* has been denied|The user doesn't want to proceed", re.S)
DAY = 86400.0


@dataclass(frozen=True)
class Event:
    session: str
    t: float  # seconds since epoch
    tool: str
    key: str  # capability key: tool name, or Bash:<first token>
    denied: bool
    mode: str = ""


def salted(key, salt=None):
    return "h:" + hashlib.sha256((salt + key).encode()).hexdigest()[:10] if salt else key


def cap_key(name, inp, salt=None):
    key = name
    if name == "Bash":
        parts = ((inp or {}).get("command") or "").split()
        key = "Bash:" + (parts[0] if parts else "")
    return salted(key, salt)


def _ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def parse_file(path, deny_re=DENY_RE, salt=None):
    uses, events, mode = {}, [], ""
    with open(path, errors="ignore") as fh:
        for line in fh:
            try:
                o = json.loads(line)
            except ValueError:
                continue
            mode = o.get("permissionMode", mode)
            msg = o.get("message")
            if not isinstance(msg, dict) or not isinstance(msg.get("content"), list):
                continue
            for c in msg["content"]:
                if c.get("type") == "tool_use" and o.get("timestamp"):
                    uses[c["id"]] = (o.get("sessionId", ""), _ts(o["timestamp"]), c.get("name", ""),
                                     cap_key(c.get("name", ""), c.get("input"), salt), mode)
                elif c.get("type") == "tool_result" and c.get("tool_use_id") in uses:
                    s, t, tool, key, m = uses.pop(c["tool_use_id"])
                    text = c.get("content")
                    text = text if isinstance(text, str) else json.dumps(text)
                    events.append(Event(s, t, tool, key, bool(c.get("is_error")) and bool(deny_re.search(text)), m))
    return events


def parse(paths, deny_re=DENY_RE, salt=None):
    files = []
    for p in paths:
        files += glob.glob(os.path.join(p, "**", "*.jsonl"), recursive=True) if os.path.isdir(p) else [p]
    ev = [e for f in sorted(files) for e in parse_file(f, deny_re, salt)]
    return sorted(ev, key=lambda e: (e.t, e.session, e.key))


def classify_denials(events, window=3):
    """What the agent did right after a denial. 'workaround' is a PROXY: same tool, different key."""
    out = {"retried": 0, "workaround": 0, "moved_on": 0}
    for i, e in enumerate(events):
        if not e.denied:
            continue
        nxt = [x for x in events[i + 1:] if x.session == e.session][:window]
        if any(x.key == e.key for x in nxt):
            out["retried"] += 1
        elif any(x.tool == e.tool for x in nxt):
            out["workaround"] += 1
        else:
            out["moved_on"] += 1
    return out


def replay(events, policy, tau_days=14.0, promote_after=3, deny_keys=(), allow0=()):
    """policy: always_ask | static | promote_repeated | grow_decay.
    Invariants: a key is never promoted from a denied event; deny_keys (the ceiling) never enter the allowlist."""
    r = dict(policy=policy, events=len(events), prompts=0, denied_prompts=0, promotions=0, decays=0,
             reprompts_after_decay=0, exposure_idle_days=0.0, dead_rules_at_end=0, final_rules=0)
    if not events:
        return r
    t0, t_end = events[0].t, events[-1].t
    allow = {k: t0 for k in allow0 if k not in deny_keys}
    approvals, decayed = {}, set()
    for e in events:
        if policy == "grow_decay":
            for k in [k for k, last in allow.items() if e.t - last > tau_days * DAY]:
                r["exposure_idle_days"] += tau_days  # held idle for exactly tau, then removed
                del allow[k]
                decayed.add(k)
                r["decays"] += 1
        if policy != "always_ask" and e.key in allow and e.key not in deny_keys and not e.denied:
            r["exposure_idle_days"] += (e.t - allow[e.key]) / DAY  # idle gap before this use, same for all policies
            allow[e.key] = e.t
            continue
        r["prompts"] += 1
        if e.key in decayed and not e.denied:
            r["reprompts_after_decay"] += 1
            decayed.discard(e.key)
        if e.denied or e.key in deny_keys:
            r["denied_prompts"] += 1
            continue
        approvals[e.key] = approvals.get(e.key, 0) + 1
        if policy in ("promote_repeated", "grow_decay") and approvals[e.key] >= promote_after:
            allow[e.key] = e.t
            r["promotions"] += 1
    for last in allow.values():
        idle = (t_end - last) / DAY
        r["exposure_idle_days"] += idle
        r["dead_rules_at_end"] += idle > tau_days
    r["final_rules"] = len(allow)
    r["exposure_idle_days"] = round(r["exposure_idle_days"], 3)
    return r


def report(events, tau_days=14.0, promote_after=3, deny_keys=(), allow0=()):
    pols = ["always_ask", "static", "promote_repeated", "grow_decay"]
    return {
        "n_events": len(events),
        "n_sessions": len({e.session for e in events}),
        "n_denied": sum(e.denied for e in events),
        "after_denial": classify_denials(events),
        "policies": [replay(events, p, tau_days, promote_after, deny_keys, allow0) for p in pols],
    }


def counts(events):
    return {"events": len(events), "sessions": len({e.session for e in events}),
            "denials": sum(e.denied for e in events)}


def split_sessions(events, train_frac=0.7):
    """(train, test) by whole sessions in time order of each session's first event; no session in both."""
    first = {}
    for e in sorted(events, key=lambda e: e.t):
        first.setdefault(e.session, e.t)
    order = sorted(first, key=first.get)
    # shortcut: with <2 sessions the test half is empty, and ties in first-event time break by sorted() stability, i.e. first-seen order
    train = set(order[:int(round(len(order) * train_frac))])
    return [e for e in events if e.session in train], [e for e in events if e.session not in train]


def _tau_row(events, tau, promote_after, deny_keys):
    pr = replay(events, "promote_repeated", tau, promote_after, deny_keys)
    gd = replay(events, "grow_decay", tau, promote_after, deny_keys)
    # a zero denominator means the ratio is undefined: None, never 0.0, and it cannot meet the bar
    saving = 1 - gd["exposure_idle_days"] / pr["exposure_idle_days"] if pr["exposure_idle_days"] else None
    extra = (gd["prompts"] - pr["prompts"]) / pr["prompts"] if pr["prompts"] else None
    ok = saving is not None and extra is not None and saving >= 0.3 and extra <= 0.1
    return {"tau": tau, "exposure_saving": None if saving is None else round(saving, 4),
            "extra_prompts": None if extra is None else round(extra, 4),
            "idle_days": {"promote_repeated": pr["exposure_idle_days"], "grow_decay": gd["exposure_idle_days"]},
            "prompts": {"promote_repeated": pr["prompts"], "grow_decay": gd["prompts"]},
            "meets_bar": ok}  # H1 bar: -30% idle exposure for <=+10% prompts


def tau_sweep(events, taus=(1, 3, 7, 14, 30), train_frac=0.7, promote_after=3, deny_keys=()):
    """H1: pick tau on the TRAIN sessions only (best saving among those meeting the bar), report both halves."""
    train, test = split_sessions(events, train_frac)
    rows = {"train": [_tau_row(train, t, promote_after, deny_keys) for t in taus],
            "test": [_tau_row(test, t, promote_after, deny_keys) for t in taus]}
    ok = [r for r in rows["train"] if r["meets_bar"]]
    chosen = max(ok, key=lambda r: (r["exposure_saving"], -r["tau"]))["tau"] if ok else None
    held = next((r for r in rows["test"] if r["tau"] == chosen), None)
    return {"train": counts(train), "test": counts(test), "rows": rows, "chosen_tau": chosen,
            "held_out_meets_bar": bool(held and held["meets_bar"])}


def mine_allowlist(events, train_frac=0.7, promote_after=3, deny_keys=()):
    """Grow-side baseline ('promote repeated requests'): keys approved >= promote_after times in the train
    sessions, minus the ceiling. Scored on test sessions: false_deny = denied test events on a mined key,
    excess_grant = mined keys never used in test."""
    train, test = split_sessions(events, train_frac)
    n = {}
    for e in train:
        if not e.denied:
            n[e.key] = n.get(e.key, 0) + 1
    allow = {k for k, c in n.items() if c >= promote_after and k not in deny_keys}
    used = {e.key for e in test if not e.denied}
    return {"allowlist": sorted(allow), "false_deny": sum(e.denied and e.key in allow for e in test),
            "excess_grant": len(allow - used), "covered": sum(not e.denied and e.key in allow for e in test),
            "test_events": len(test)}


def cli_report(events, **kw):
    """Hold-out section for the CLI report; wiring into __main__ is the caller's job."""
    return {"counts": counts(events), "tau_sweep": tau_sweep(events, **kw), "allowlist": mine_allowlist(events)}
