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
