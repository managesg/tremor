"""Dream arms A-E (EMERGENCE-PROGRAM section 4). Memory is an append-only list of record dicts
{"id","text","source", optional "claim","supersedes","withdrawn"}; nothing is ever edited or removed.

A none. B raw log. C equal-token retrieval (own-task text). D placebo (other-task text, shuffled).
E scripted re-verify (replay claims, withdraw failures by appended supersede). Dream bytes are charged
inside `cap`; over the cap raises.
shortcut: bytes stand in for tokens and are exact for ASCII text; upgrade if a tokenizer budget is needed.
"""
import json
import random


def active(memory):
    """Records neither superseded nor withdrawn."""
    sup = {r["supersedes"] for r in memory if r.get("supersedes")}
    return [r for r in memory if r["id"] not in sup and not r.get("withdrawn")]


def _cut(text, n):
    return text.encode()[:max(n, 0)].decode(errors="ignore")


def dream(arm, memory, transcripts, task, budget=0, cap=None, seed=0, replay=None, world=None):
    """transcripts: [{"task","text"}]. Returns {"memory": new list, "dream_bytes": int}."""
    mem = list(memory)
    rec = lambda text: {"id": f"dream-{arm}-{len(mem)}", "text": text, "source": f"dream:{arm}"}
    cost = 0
    if arm == "A":
        pass
    elif arm == "B":
        text = "\n".join(t["text"] for t in transcripts if t["task"] == task)
        mem.append(rec(text))
        cost = len(text.encode())
    elif arm in ("C", "D"):
        if arm == "C":
            lines = [x for t in transcripts if t["task"] == task for x in t["text"].splitlines()]
        else:
            lines = [x for t in transcripts if t["task"] != task for x in t["text"].splitlines()]
            random.Random(seed).shuffle(lines)
        text = _cut("\n".join(lines), budget)  # shortcut: short source yields fewer bytes than budget
        mem.append(rec(text))
        cost = len(text.encode())
    elif arm == "E":
        for r in active(memory):
            if "claim" in r:
                cost += len(json.dumps(r["claim"], sort_keys=True).encode())
                if not replay(r["claim"], world):
                    s = {"id": f"sup-{r['id']}", "supersedes": r["id"], "withdrawn": True, "text": "",
                         "source": "dream:E"}
                    mem.append(s)
                    cost += len(json.dumps(s, sort_keys=True).encode())
    else:
        raise ValueError(f"unknown arm {arm!r}")
    if cap is not None and cost > cap:
        raise ValueError(f"dream bytes {cost} exceed cap {cap}")
    return {"memory": mem, "dream_bytes": cost}
