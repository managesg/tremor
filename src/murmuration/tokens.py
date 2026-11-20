"""E8.1 token-class ledger. Reads Claude Code transcript JSONL; emits counts only.

Never copies message text, prompts or tool inputs/outputs: only usage numbers, tool names,
and a salted session id leave this module. Stdlib only.
"""
import glob
import hashlib
import json
import os
import re
from collections import Counter

NAME_OK = re.compile(r"^[A-Za-z0-9_]{1,40}$")  # key names only; anything else is dropped
READS, WRITES = {"Read", "Grep", "Glob"}, {"Edit", "Write"}
CLASSES = {"input": "input_tokens", "output": "output_tokens",
           "cache_read": "cache_read_input_tokens", "cache_write": "cache_creation_input_tokens"}


def _files(paths):
    out = []
    for p in paths:
        out += glob.glob(os.path.join(p, "**", "*.jsonl"), recursive=True) if os.path.isdir(p) else [p]
    return sorted(out)


def _records(path):
    """Yield (record, message) for assistant lines; unreadable lines are skipped."""
    with open(path, errors="ignore") as fh:
        for line in fh:
            try:
                o = json.loads(line)
            except ValueError:
                continue
            m = o.get("message") if isinstance(o, dict) else None
            if isinstance(m, dict) and o.get("type") == "assistant":
                yield o, m


def _num(v):
    return v if isinstance(v, int) and not isinstance(v, bool) else None  # absent is None, never 0


def probe(paths):
    """Which usage key names exist, with counts. No values, no text."""
    keys, nested = Counter(), Counter()
    n_assist = n_usage = n_files = 0
    for f in _files(paths):
        n_files += 1
        for _, m in _records(f):
            n_assist += 1
            u = m.get("usage")
            if not isinstance(u, dict):
                continue
            n_usage += 1
            for k, v in u.items():
                if NAME_OK.match(k):
                    keys[k] += 1
                    if isinstance(v, dict):
                        nested.update(f"{k}.{s}" for s in v if NAME_OK.match(s))
    return {"files": n_files, "assistant_messages": n_assist, "with_usage": n_usage,
            "usage_keys": dict(sorted(keys.items())), "nested_keys": dict(sorted(nested.items()))}


def _session(path, salt):
    """One file = one session. Returns the salted-id summary dict, or None without usage."""
    seen, tools, tool_ids, sid, side = {}, Counter(), set(), "", False
    for o, m in _records(path):
        sid = sid or str(o.get("sessionId", "")) + "/" + str(o.get("agentId", ""))
        side = side or bool(o.get("isSidechain"))
        u = m.get("usage")
        if isinstance(u, dict):
            # streamed messages repeat; the last record per message id holds the final counts
            seen[m.get("id") or len(seen)] = (u, bool(o.get("isSidechain")))
        for i, c in enumerate(m.get("content") if isinstance(m.get("content"), list) else []):
            if isinstance(c, dict) and c.get("type") == "tool_use" and isinstance(c.get("name"), str):
                key = c.get("id") or (m.get("id"), i)  # streamed records repeat the same tool_use
                if key not in tool_ids:
                    tool_ids.add(key)
                    tools[c["name"]] += 1
    if not seen:
        return None
    vals = {k: [_num(u.get(f)) for u, _ in seen.values()] for k, f in CLASSES.items()}
    missing = {k: v.count(None) for k, v in vals.items()}
    tot = {k: (sum(x for x in v if x is not None) if len(v) > missing[k] else None) for k, v in vals.items()}
    parts = [tot[k] for k in ("input", "cache_read", "cache_write")]
    inp = None if None in parts else sum(parts)  # unknown if any denominator class is missing
    first = next(iter(seen.values()))[0]
    r, w = sum(tools[t] for t in READS), sum(tools[t] for t in WRITES)
    return {"session": hashlib.sha256((salt + (sid or path)).encode()).hexdigest()[:12],
            "subagent": side, "messages": len(seen), **tot, "missing": missing,
            "cache_hit": tot["cache_read"] / inp if inp else None,
            "cold_start_cache_write": _num(first.get(CLASSES["cache_write"])) if side else None,
            "reads": r, "writes": w, "reads_per_write": r / w if w else None}


def ledger(paths, salt):
    """Per-session token classes, cache-hit ratio, subagent cold start, reads per write."""
    if not salt:
        raise ValueError("salt required: session ids must not leave unsalted")
    return [s for s in (_session(f, salt) for f in _files(paths)) if s]


if __name__ == "__main__":
    import sys
    print(json.dumps(probe(sys.argv[1:] or [os.path.expanduser("~/.claude/projects")]), indent=1))
