"""Realized readouts for R1 row 157, computed from one run's own recorded files.

Frozen sources: docs/reports/workplan-ep/R1-row157-contention-definition.md (definition 7) and
R1-row157-contention-addendum.md (rule 4). Both are readouts only; neither is used for eligibility.

Reading: rounds are the measured rounds 1..R, R = committed end_round events on the board minus the setup commit
         (board round 0). A run stopped early reports its committed rounds only; none is invented for the rest.
Reading: the sealed roster is the distinct work agents of plan.json rounds, in order (the agents the run sealed
         into the router); it is checked against board.jsonl and dispatch.json agents.
Reading: "active" = roster agents not stopped; neither files record an agent stop (the only stop is the whole-run
         controlled stop, handled above), so A_r = roster size in every reported round.
Reading: the board has no release concept for tasks, so "released by round r" comes from the plan's scheduled
         release (r1_episode_v3.schedule_plan applied to plan.json's taskset and roster, and checked against the
         scheduled counts recorded in plan.json); a task with no release round is never open.
Reading: "start of round r" = the board after the commit of board round r-1 (board round r is the open round).
Reading: a task is completed when a committed release with done=true by its live holder is on the board; the
         scripted work actions record none, so completion there never reduces T_r (claims expire by TTL instead).
Reading: a task is held when it has a live claim (committed winner, not released, not expired) in that board state.
Reading: T_r = released, not completed, not held. rho_r = A_r / T_r as a Fraction, None when T_r = 0.
Reading: claim actions in round r = every claim event logged in board round r, collisions included, and only the
         scripted claims logged in that round (the setup claim is board round 0, so it is not a measured round).
Reading: distinct claimed tasks = distinct items among those claim events; c_r = claims / distinct as a Fraction,
         None when no task was claimed. No threshold is applied anywhere.
"""

import hashlib
import json
from fractions import Fraction
from pathlib import Path

from lab import r1_contention_schedule as contention_schedule
from lab import r1_episode_v3
from tremor.board import read_log


def _load(path):
    try:
        data = json.loads(Path(path).read_bytes())
    except (OSError, UnicodeDecodeError) as error:
        raise ValueError(f"cannot read {path}: {error}") from error
    if not isinstance(data, dict):
        raise ValueError(f"{path} must hold a JSON object")
    return data


def _plan(run_dir):
    plan = _load(run_dir / "plan.json")
    rounds, taskset = plan.get("rounds"), plan.get("taskset")
    if (plan.get("scope") != "scripted_r1_episode_v3" or not isinstance(rounds, list) or not rounds
            or not isinstance(taskset, dict) or not isinstance(taskset.get("tasks"), list)):
        raise ValueError("plan.json is not a v3 episode plan")
    try:
        roster = list(dict.fromkeys(r["work"]["agent"] for r in rounds))
    except (TypeError, KeyError) as error:
        raise ValueError("plan rounds must name a work agent") from error
    if not roster or not all(type(a) is str and a for a in roster):
        raise ValueError("plan roster must be non-empty agent ids")
    tasks = r1_episode_v3.schedule_plan(taskset, roster)["tasks"]
    recorded = (plan.get("scheduled_contention") or {}).get("table")
    rebuilt = contention_schedule.schedule(r1_episode_v3.schedule_plan(taskset, roster))
    if recorded != [row | {"kappa": None if row["kappa"] is None else str(row["kappa"])} for row in rebuilt]:
        raise ValueError("plan scheduled counts differ from the plan's own release schedule")
    return roster, tasks, plan


def _states(events, roster, task_ids):
    """Board state after each end_round commit: states[k] = (held items, completed items) after board round k."""
    claims, done, pending, states = {}, set(), [], []
    for event in events:
        kind, agent, data = event["type"], event["agent"], event["data"]
        if kind in ("claim", "release") and agent not in roster:
            raise ValueError(f"board names an agent outside the sealed roster: {agent}")
        if kind in ("claim", "release") and data["item"] not in task_ids:
            raise ValueError(f"board names an unknown task: {data['item']}")
        if kind in ("claim", "release"):
            pending.append(event)
        elif kind == "end_round":
            if event["round"] != len(states):
                raise ValueError("board end_round commits are not consecutive")
            for p in pending:
                if p["type"] == "release" and claims.get(p["data"]["item"]) == p["agent"]:  # holder's name
                    del claims[p["data"]["item"]]
                    if p["data"]["done"] is True:
                        done.add(p["data"]["item"])
            for e in data["expired"]:
                claims.pop(e["item"], None)
            for r in data["resolved"]:
                if r["winner"] is not None:
                    claims[r["item"]] = r["winner"]
            pending = []
            states.append((frozenset(claims), frozenset(done)))
    return states


def readouts(run_dir):
    """One row per committed measured round; see the module Reading lines for every definition."""
    run_dir = Path(run_dir)
    if not run_dir.is_dir():
        raise ValueError("run_dir must be an existing directory")
    roster, tasks, plan = _plan(run_dir)
    task_ids = {t["id"] for t in tasks}
    events = read_log(run_dir / "board.jsonl")
    if not events or events[0]["type"] != "init":
        raise ValueError("board.jsonl is missing or empty")
    states = _states(events, roster, task_ids)
    record = _load(run_dir / "dispatch.json")
    if record.get("plan_sha256") != hashlib.sha256((run_dir / "plan.json").read_bytes()).hexdigest():
        raise ValueError("plan.json differs from the plan the run recorded in dispatch.json")
    dispatch = record.get("settled")
    if not isinstance(dispatch, list) or any(
            not isinstance(d, dict) or not isinstance(d.get("action"), dict)
            or d["action"].get("agent") not in roster for d in dispatch):
        raise ValueError("dispatch.json must list settled actions by roster agents")
    if len(states) - 1 != plan.get("controlled_stop_after_round"):  # a cut board must not pass as a stop
        raise ValueError("board commits differ from the run's recorded stop round")
    out = []
    for r in range(1, len(states)):
        held, done = states[r - 1]
        open_tasks = sum(1 for t in tasks if t["release"] is not None and t["release"] <= r
                         and t["id"] not in held and t["id"] not in done)
        claims = [e["data"]["item"] for e in events if e["type"] == "claim" and e["round"] == r]
        distinct = len(set(claims))
        out.append({"round": r, "realized_active_agents": len(roster), "realized_open_tasks": open_tasks,
                    "rho": Fraction(len(roster), open_tasks) if open_tasks else None,
                    "claim_actions": len(claims), "distinct_claimed_tasks": distinct,
                    "c": Fraction(len(claims), distinct) if distinct else None})
    return out
