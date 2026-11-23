"""Scheduled design contention for R1 row 157, from generator inputs only.

Frozen sources: docs/reports/workplan-ep/R1-row157-contention-definition.md (definitions 4-6) and
R1-row157-contention-addendum.md (rules 1-3). Counts come from the plan, never from a run.

A plan is {"rounds": R, "roster": [agents active in round 1, ..., round R],
"tasks": [{"id": str, "release": round or None, "complete": round or None}, ...]}.
A task is scheduled open in round r when release <= r <= complete (complete None: never completes).
A task with release None is never released. An agent is scheduled eligible when the roster names it in r.
"""

import hashlib
import json
from fractions import Fraction


MIN_ROUNDS = 4  # "four or more rounds", policy row 157


def _round(value, low, high, what):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{what} must be an integer in {low}..{high}")
    return value


def _validate(plan):
    if not isinstance(plan, dict) or set(plan) != {"rounds", "roster", "tasks"}:
        raise ValueError("plan must have exactly rounds, roster and tasks")
    rounds = _round(plan["rounds"], 1, 10**6, "rounds")
    roster = plan["roster"]
    if not isinstance(roster, list) or len(roster) != rounds:
        raise ValueError("roster needs one agent list per round")
    for agents in roster:
        if (not isinstance(agents, list) or not all(type(a) is str and a for a in agents)
                or len(set(agents)) != len(agents)):
            raise ValueError("each roster entry must be a list of unique non-empty agent ids")
    tasks = plan["tasks"]
    if not isinstance(tasks, list):
        raise ValueError("tasks must be a list")
    ids = set()
    for task in tasks:
        if not isinstance(task, dict) or set(task) != {"id", "release", "complete"}:
            raise ValueError("each task needs exactly id, release and complete")
        if type(task["id"]) is not str or not task["id"] or task["id"] in ids:
            raise ValueError("task ids must be unique non-empty strings")
        ids.add(task["id"])
        release, complete = task["release"], task["complete"]
        if release is None:
            if complete is not None:
                raise ValueError("a task that is never released cannot complete")
            continue
        _round(release, 1, rounds, "release")
        if complete is not None:
            _round(complete, release, rounds, "complete")
    return rounds, roster, tasks


def schedule(plan):
    """Per-round scheduled counts; kappa is Fraction(A_hat, T_hat), or None when T_hat is 0."""
    rounds, roster, tasks = _validate(plan)
    rows = []
    for r in range(1, rounds + 1):
        open_tasks = sum(
            t["release"] is not None and t["release"] <= r and (t["complete"] is None or r <= t["complete"])
            for t in tasks)
        agents = len(roster[r - 1])
        rows.append({"round": r, "scheduled_agents": agents, "scheduled_open_tasks": open_tasks,
                     "kappa": Fraction(agents, open_tasks) if open_tasks else None})
    return rows


def _checked(rows):
    if not isinstance(rows, list):
        raise ValueError("rows must be a list")
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict) or set(row) != {"round", "scheduled_agents", "scheduled_open_tasks", "kappa"}:
            raise ValueError("malformed schedule row")
        a, t = row["scheduled_agents"], row["scheduled_open_tasks"]
        if type(row["round"]) is not int or row["round"] != index or type(a) is not int or type(t) is not int or a < 0 or t < 0:
            raise ValueError("schedule rows must be consecutive rounds with non-negative integer counts")
        if row["kappa"] != (Fraction(a, t) if t else None):
            raise ValueError("kappa differs from scheduled agents over scheduled open tasks")
    return rows


def satisfies(rows):
    """Contention above 1: A_hat > T_hat in every round with T_hat >= 1; no such round: not eligible.
    The episode needs R >= 4 rounds (definition 1), so a shorter schedule never satisfies."""
    eligible = [row for row in _checked(rows) if row["scheduled_open_tasks"] >= 1]
    return len(rows) >= MIN_ROUNDS and bool(eligible) and all(row["scheduled_agents"] > row["scheduled_open_tasks"] for row in eligible)


def pin(rows, meta):
    """Canonical JSON bytes of the table plus meta, and their sha256."""
    if (not isinstance(meta, dict) or set(meta) != {"generator_path", "generator_sha256", "seed", "rule"}
            or any(type(meta[key]) is not str or not meta[key] for key in ("generator_path", "generator_sha256", "rule"))
            or type(meta["seed"]) is not int):
        raise ValueError("meta needs generator_path, generator_sha256, seed and rule")
    table = [row | {"kappa": None if row["kappa"] is None else str(row["kappa"])} for row in _checked(rows)]
    raw = json.dumps({"meta": meta, "rows": table}, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return raw, hashlib.sha256(raw).hexdigest()
