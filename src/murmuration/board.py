"""Shared board: an append-only, hash-chained JSONL log is the source of truth.

State (items, claims) is an in-memory replay of the log. Every mutation is
`_log(event)` then `_apply(event)`, and loading runs the same `_apply` over the
verified log, so a replayed Board equals the live one by construction.

Writes in a round (post, claim, release) are buffered and become visible only
at `end_round`. Reads and `snapshot` see the committed state of earlier rounds.

LOG LINE SCHEMA (one JSON object per line, keys sorted, no spaces):
    {"seq": int,          # 0-based, contiguous
     "round": int,        # round open when the event was logged (0-based)
     "type": str,         # init | post | read | claim | release | end_round
     "agent": str|null,   # acting agent; null for init and end_round
     "data": {...},       # per type, below
     "prev": str,         # hash of previous line; 64 zeros for seq 0
     "hash": str}         # sha256(prev + canonical JSON of the line without "hash")
  init       data {"seed": any}
  post       data {"id": "p<seq>", "kind": str, "text": str,
                   "refs": [item id], "facts": [fact id],
                   "supersedes": [item id], "position": str|null}
             kind "plant" marks a planted fact; "position" is the agent's
             stance for convergence; "supersedes" retires items (consolidation).
  read       data {"item": id|null, "n": int returned}
  claim      data {"item": str}
  release    data {"item": str, "done": bool, "task_type": str|null}
  end_round  data {"expired": [{"item","agent"}],
                   "resolved": [{"item","claimants":[sorted agents],
                                 "winner": agent|null, "collision": bool}]}
             collision = two or more distinct agents claimed one item in the round.
Orders (orders.py) reads exactly this schema; hand-written logs may omit
seq/prev/hash when passed to `orders.compute` as a list of dicts.
"""
import hashlib
import json
import os
import random

GENESIS = "0" * 64


def _digest(line):
    body = {k: v for k, v in line.items() if k != "hash"}
    return hashlib.sha256((line["prev"] + json.dumps(body, sort_keys=True, separators=(",", ":"))).encode()).hexdigest()


def read_log(path):
    """Load and verify a log; raises ValueError on any edit, gap or reorder."""
    lines = []
    prev = GENESIS
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for n, raw in enumerate(f):
                line = json.loads(raw)
                if line.get("seq") != n or line.get("prev") != prev or line.get("hash") != _digest(line):
                    raise ValueError(f"log tampered at line {n}")
                prev = line["hash"]
                lines.append(line)
    # shortcut: truncating the tail is undetectable without an external head hash; anchor it when runs are archived
    return lines


class Board:
    def __init__(self, log_path, seed, claim_ttl=3):
        self.path, self.seed, self.ttl = log_path, seed, claim_ttl
        self.round, self.items, self.claims = 0, {}, {}
        self._pending = []
        self._lines = read_log(log_path)
        self._prev = self._lines[-1]["hash"] if self._lines else GENESIS
        if self._lines:
            if self._lines[0]["data"]["seed"] != seed:
                raise ValueError("seed differs from the log's init")
            for line in self._lines:
                self._apply(line)
        else:
            self._emit("init", None, {"seed": seed})

    # --- core: every mutation goes through _emit ---
    def _emit(self, type_, agent, data):
        line = {"seq": len(self._lines), "round": self.round, "type": type_, "agent": agent, "data": data, "prev": self._prev}
        line["hash"] = _digest(line)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(line, sort_keys=True, separators=(",", ":")) + "\n")
        self._lines.append(line)
        self._prev = line["hash"]
        self._apply(line)
        return line

    def _apply(self, line):
        t, d = line["type"], line["data"]
        if t in ("post", "claim", "release"):
            self._pending.append(line)
        elif t == "end_round":
            for p in self._pending:
                if p["type"] == "post":
                    for s in p["data"]["supersedes"]:
                        self.items.pop(s, None)
                    self.items[p["data"]["id"]] = dict(p["data"], agent=p["agent"], round=p["round"])
                elif p["type"] == "release" and self.claims.get(p["data"]["item"], {}).get("agent") == p["agent"]:
                    del self.claims[p["data"]["item"]]
            for e in d["expired"]:
                self.claims.pop(e["item"], None)
            for r in d["resolved"]:
                if r["winner"] is not None:
                    self.claims[r["item"]] = {"agent": r["winner"], "round": line["round"]}
            self._pending = []
            self.round += 1

    # --- API ---
    def snapshot(self):
        """Committed state only; a copy."""
        return json.loads(json.dumps({"round": self.round, "items": self.items, "claims": self.claims}))

    @property
    def state(self):
        return dict(self.snapshot(), pending=[p["seq"] for p in self._pending])

    def read(self, agent, item=None):
        """Committed items (list), or one item (dict|None) when `item` is given. Logged."""
        out = self.snapshot()["items"]
        res = out.get(item) if item is not None else list(out.values())
        self._emit("read", agent, {"item": item, "n": (0 if res is None else 1) if item is not None else len(res)})
        return res

    def post(self, agent, text, kind="note", refs=(), facts=(), supersedes=(), position=None):
        """Buffered until end_round. Returns the item id."""
        pid = f"p{len(self._lines)}"
        self._emit("post", agent, {"id": pid, "kind": kind, "text": text, "refs": list(refs), "facts": list(facts),
                                   "supersedes": list(supersedes), "position": position})
        return pid

    def claim(self, agent, item):
        """Buffered; resolved at end_round. Every claim is logged, collisions included."""
        self._emit("claim", agent, {"item": item})

    def release(self, agent, item, done=True, task_type=None):
        if self.claims.get(item, {}).get("agent") != agent:
            raise ValueError(f"{agent} does not hold {item}")
        self._emit("release", agent, {"item": item, "done": done, "task_type": task_type})

    def end_round(self):
        """Commit the round: releases, expiry, then seeded claim resolution."""
        released = {p["data"]["item"] for p in self._pending if p["type"] == "release"}
        expired = sorted(({"item": i, "agent": c["agent"]} for i, c in self.claims.items()
                          if i not in released and self.round - c["round"] >= self.ttl), key=lambda e: e["item"])
        gone = released | {e["item"] for e in expired}
        by_item = {}
        for p in self._pending:
            if p["type"] == "claim":
                by_item.setdefault(p["data"]["item"], set()).add(p["agent"])
        resolved = []
        for item in sorted(by_item):
            cl = sorted(by_item[item])
            holder = self.claims[item]["agent"] if item in self.claims and item not in gone else None
            if holder is not None:
                winner = holder if holder in cl else None
            else:
                winner = random.Random(f"{self.seed}:{self.round}:{item}").choice(cl)
            resolved.append({"item": item, "claimants": cl, "winner": winner, "collision": len(cl) >= 2})
        self._emit("end_round", None, {"expired": expired, "resolved": resolved})
