"""Four measured rounds with scheduled contention above 1, on the v2 Board, router and scorers.

Change from v2 (lab/r1_episode_v2.py): the schedule is explicit and pinned (lab/r1_contention_schedule.py),
and tasks are released over rounds instead of all claimed in setup, so scheduled open tasks stay below
the scheduled agents in every round, round 1 included. Round 1 is scored apart, as in v2.

Reading: R = 4 rounds (policy: four or more).
Reading: kappa > 1 in every round with an open task (policy: contention above 1).
Reading: roster is the four agents of alloc.gen, active in every round (structural count, no crash scheduled).
Reading: t0 and t1 are released in round 1, t2 in round 2, t3 in round 3 (one claim per agent per round,
         claimed in the round of release, worked the round after; t0 is claimed in setup).
Reading: a work task completes in its worker's round: t0 in 1, t1 in 2, t2 in 3, t3 in 4.
Reading: t4 is released in round 1 and never scheduled to complete (the contested task); t5 is never released.
Reading: a2 and a3 claim t4 in round 1, so the Board commits a collision there.
Reading: one named reader per round, a0 to a3, as in v2.
"""

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from lab import r1_contention_schedule as contention_schedule
from lab.r1_episode_v2 import CLAIM_TTL, ERROR_ROUND, MARKER, MEASURED_ROUNDS, _score, _write
from murmuration import cell, router, team
from murmuration.board import Board, read_log
from murmuration.trapbench import alloc

RULE = "fixed-roster-staggered-release-v3"
GENERATOR_PATH = "lab/r1_episode_v3.py"


def schedule_plan(taskset, workers):
    """Generator inputs for the scheduled counts; no run is needed to compute them."""
    release = [1, 1, 2, 3, 1, None]
    complete = [1, 2, 3, 4, None, None]
    if len(workers) != 4 or len(taskset["tasks"]) != 6:
        raise ValueError("the v3 rule is written for four agents and six tasks")
    return {"rounds": MEASURED_ROUNDS, "roster": [list(workers) for _ in range(MEASURED_ROUNDS)],
            "tasks": [{"id": t["id"], "release": release[i], "complete": complete[i]}
                      for i, t in enumerate(taskset["tasks"])]}


def pinned_schedule(seed, taskset, workers):
    """Scheduled table and its pin; raises when the design does not satisfy contention above 1."""
    rows = contention_schedule.schedule(schedule_plan(taskset, workers))
    if len(rows) < 4 or not contention_schedule.satisfies(rows):
        raise ValueError("scheduled design does not satisfy contention above 1")
    meta = {"generator_path": GENERATOR_PATH, "seed": seed, "rule": RULE,
            "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    _, digest = contention_schedule.pin(rows, meta)
    table = [row | {"kappa": str(row["kappa"])} for row in rows]
    return {"table": table, "pin_sha256": digest, "pin_meta": meta}


def run(output, *, case, seed=17, stop_after_round=MEASURED_ROUNDS):
    """Run a neutral fixture with an optional controlled stop after both Boards commit."""
    if type(case) is not str or case not in ERROR_ROUND or type(seed) is not int or seed < 0:
        raise ValueError("unknown scripted episode or invalid seed")
    if type(stop_after_round) is not int or not 0 <= stop_after_round <= MEASURED_ROUNDS:
        raise ValueError("controlled stop must name one planned commit boundary")
    taskset = alloc.gen(seed)
    jobs = alloc.oracle_log(taskset)
    if len(jobs) != MEASURED_ROUNDS:
        raise ValueError("scripted episode requires one worker per measured round")
    workers = [job["agent"] for job in jobs]
    contested = taskset["tasks"][len(workers)]["id"]
    contenders = workers[2:4]
    scheduled = pinned_schedule(seed, taskset, workers)
    plan_tasks = schedule_plan(taskset, workers)["tasks"]
    owner = {job["task"]: job["agent"] for job in jobs}
    if [job["task"] for job in jobs] != [t["id"] for t in plan_tasks[:len(jobs)]]:
        raise ValueError("oracle jobs must follow the scheduled task order")
    rounds = []
    for index, job in enumerate(jobs, start=1):
        action = {key: value for key, value in job.items() if key != "action"} | {"type": "work"}
        action["answer"] += int(index == ERROR_ROUND[case])
        rounds.append({"round": index, "named_reader": job["agent"], "work": action})

    output = Path(output)
    output.mkdir()
    plan = {"scope": "scripted_r1_episode_v3", "case": case, "seed": seed, "taskset": taskset,
            "claim_ttl": CLAIM_TTL, "rounds": rounds, "planned_rounds": MEASURED_ROUNDS,
            "contention": {"round": 1, "task": contested, "workers": contenders},
            "scheduled_contention": scheduled,
            "controlled_stop_after_round": stop_after_round}
    plan_pin = _write(output / "plan.json", plan)
    board_path = output / "board.jsonl"
    operations = cell.create(output / "cell", "r1-episode-v3", "stub", "scripted", team.POLICY)
    handle = router.seal(Board(board_path, seed, claim_ttl=CLAIM_TTL), operations, practices=("A",), agents=workers)
    delivery = Board(output / "delivery.jsonl", seed)
    marker = delivery.post("fixture", MARKER, kind="fixture")
    first = {"type": "claim", "agent": jobs[0]["agent"], "item": jobs[0]["task"]}
    if router.act(first, handle, enforced=False) != ("admitted", "ok"):
        raise ValueError("scripted setup claim was not admitted")
    router.end_round(handle)
    delivery.end_round()

    work, dispatch, reads = [], [], []
    first_score = contention = None
    for planned in rounds[:stop_after_round]:
        index, reader = planned["round"], planned["named_reader"]
        delivered = delivery.read(reader, marker)
        if delivery.round != index or delivered is None or delivered["text"] != MARKER:
            raise ValueError("scripted named read did not see the committed marker")
        # Claims come from the scheduled plan: a task is claimed in its scheduled release round (the
        # contested task by both contenders). The first task is the one exception: claimed in setup.
        claims = []
        for task in plan_tasks:
            if task["release"] != index or task["id"] == jobs[0]["task"]:
                continue
            claimants = contenders if task["id"] == contested else [owner[task["id"]]]
            claims += [{"type": "claim", "agent": agent, "item": task["id"]} for agent in claimants]
        worked = next(t for t in plan_tasks if t["id"] == planned["work"]["task"])
        if worked["complete"] != index:
            raise ValueError("scripted work must complete in its scheduled round")
        for action in claims:
            status, reason = router.act(action, handle, enforced=False)
            if status not in team.EXECUTED:
                raise ValueError("scripted claim did not reach the Board")
            dispatch.append({"round": index, "action": action, "status": status, "reason": reason})

        before = read_log(board_path)
        current = planned["work"]
        if team.view_of(board_path)["round"] != index:
            raise ValueError("scripted work must use its planned committed round")
        status, reason = router.act(current, handle, enforced=False)
        if status not in (*team.EXECUTED, "refused"):
            raise ValueError("scripted work did not settle")
        dispatch.append({"round": index, "action": current, "status": status, "reason": reason,
                         "pre_action_board_head": before[-1]["hash"], "pre_action_board_event_count": len(before)})
        work.append({key: value for key, value in current.items() if key != "type"} |
                    {"action": "work", "rejected": status not in team.EXECUTED})
        router.end_round(handle)
        delivery.end_round()
        if index == 1:
            commit = read_log(board_path)[-1]
            resolution = next(item for item in commit["data"]["resolved"] if item["item"] == contested)
            if (not resolution["collision"] or resolution["claimants"] != sorted(contenders)
                    or resolution["winner"] not in contenders):
                raise ValueError("scripted first round did not commit the planned contention")
            contention = {"round": index, "commit_seq": commit["seq"], "resolution": resolution}
            prefix = _score(work.copy(), taskset)
            first_score = {"round": 1, "scheduled_work": 1, "settled_work": len(work),
                           "distinct_passing": prefix["distinct_passing"], "dual_scorer_agreement": True,
                           "board_head": commit["hash"], "board_event_count": commit["seq"] + 1}

    main_trace, delivery_trace = read_log(board_path), read_log(delivery.path)
    for trace in (main_trace, delivery_trace):
        if [event["round"] for event in trace if event["type"] == "end_round"] != list(range(stop_after_round + 1)):
            raise ValueError("scripted commits differ from the planned boundary")
    for planned, read in zip(rounds[:stop_after_round],
                             (event for event in delivery_trace if event["type"] == "read"), strict=True):
        if (read["agent"], read["round"], read["data"]) != (
            planned["named_reader"], planned["round"], {"item": marker, "n": 1}
        ):
            raise ValueError("scripted named read differs from the schedule")
        reads.append({"reader": read["agent"], "round": read["round"], "item": marker, "seq": read["seq"]})
    if not cell.verify_log(operations):
        raise ValueError("scripted router cell log is invalid")
    dispatch_pin = _write(output / "dispatch.json", {"plan_sha256": plan_pin, "settled": dispatch})

    completed = stop_after_round == MEASURED_ROUNDS
    summary = {
        "status": "completed" if completed else "incomplete_committed_prefix",
        "scope": plan["scope"], "case": case, "scientific_result": False,
        "planned_rounds": MEASURED_ROUNDS, "committed_measured_rounds": stop_after_round,
        "unstarted_work": MEASURED_ROUNDS - len(work), "named_reads": reads, "contention": contention,
        "scheduled_contention_pin_sha256": scheduled["pin_sha256"],
        "first_round_score": first_score, "final_score": _score(work, taskset) if completed else None,
        "plan_sha256": plan_pin, "dispatch_sha256": dispatch_pin,
        "board_sha256": hashlib.sha256(board_path.read_bytes()).hexdigest(),
        "delivery_sha256": hashlib.sha256(delivery.path.read_bytes()).hexdigest(),
    }
    _write(output / "summary.json", summary)
    return summary


def demo():
    with TemporaryDirectory(prefix="tremor-r1-episode-v3-") as temporary:
        root = Path(temporary)
        return {case: run(root / case, case=case) for case in ERROR_ROUND} | {
            "stopped_after_first": run(root / "stopped", case="late_error", stop_after_round=1)}


if __name__ == "__main__":
    print(json.dumps(demo(), sort_keys=True, indent=2, allow_nan=False))
