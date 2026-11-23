"""Scheduled board-read lags for R1 row 157, from generator inputs only.

Frozen source: docs/reports/workplan-ep/R1-row157-staggered-reads-definition.md (definitions 2-4).
A plan has the shape of lab/r1_contention_schedule.py: {"rounds": R, "roster": [agents per round], "tasks": [...]}.
Reading: lag l_a(r) is how many commits back agent a reads in round r: it sees the board as committed at
         the end of round r - l, round 0 being the setup commit. l >= 1 (definition 2) and l <= r (the board
         has no commit before the setup commit), so round 1 can only have lag 1; round 1 is exempt (definition 3).
Reading: from round 2 on, the agent at roster index i in round r has lag 1 + ((i + r) % 2): lags alternate between
         the latest commit and the one before, so every round with two or more agents has two distinct lags and
         the alternation shifts by round. The rule uses the roster only; the seed enters the pin through meta.
Reading: staggered() applies definition 3 literally, so a design with no round r >= 2 that has two agents is
         vacuously staggered; the round-count floor belongs to the contention check, not to this one.
"""

import hashlib
import json

from lab.r1_contention_schedule import _validate


def lags(plan):
    """Per round, {agent: lag} for the agents the roster names active in that round."""
    rounds, roster, _ = _validate(plan)
    return [{agent: 1 if r == 1 else 1 + (i + r) % 2 for i, agent in enumerate(roster[r - 1])}
            for r in range(1, rounds + 1)]


def _checked(rows, roster):
    if not isinstance(rows, list) or not isinstance(roster, list) or len(rows) != len(roster):
        raise ValueError("rows and roster need one entry per round")
    for r, (row, agents) in enumerate(zip(rows, roster), start=1):
        if (not isinstance(row, dict) or not isinstance(agents, list)
                or sorted(row, key=str) != sorted(agents, key=str) or len(set(agents)) != len(agents)):
            raise ValueError("each round's lags must cover exactly that round's active agents")
        for agent, lag in row.items():
            if type(agent) is not str or not agent or type(lag) is not int or not 1 <= lag <= r:
                raise ValueError("a lag must be an integer from 1 to the round number")
    return rows


def staggered(rows, roster):
    """Definition 3: every round r >= 2 with at least two active agents has at least two distinct lags."""
    rows = _checked(rows, roster)
    return all(len(set(row.values())) >= 2 for r, row in enumerate(rows, start=1) if r >= 2 and len(row) >= 2)


def pin(rows, meta):
    """Canonical JSON bytes of the lag table plus meta, and their sha256."""
    if (not isinstance(meta, dict) or set(meta) != {"generator_path", "generator_sha256", "seed", "rule"}
            or any(type(meta[key]) is not str or not meta[key] for key in ("generator_path", "generator_sha256", "rule"))
            or type(meta["seed"]) is not int):
        raise ValueError("meta needs generator_path, generator_sha256, seed and rule")
    _checked(rows, [list(row) for row in rows])
    table = [{"round": r, "lags": dict(row)} for r, row in enumerate(rows, start=1)]
    raw = json.dumps({"meta": meta, "rows": table}, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return raw, hashlib.sha256(raw).hexdigest()
