"""Four measured rounds with scheduled contention above 1 and scheduled staggered board reads.

Why v4: v3 (lab/r1_episode_v3.py, pinned, unchanged) meets contention above 1 but its only per-round read is
one named reader of a fixed setup marker, which definition 1 of R1-row157-staggered-reads-definition.md rules out.
v4 keeps v3's contention schedule by import and replaces the marker read with scheduled board reads.

Reading: contention is v3's schedule_plan, rule and table (kappa 4/3, 4/3, 4/3, 2), imported and not copied.
Reading: every active agent reads the board once per round, at the start of the round, before the round's claims.
Reading: a read in round r by an agent with lag l returns the board as committed at the end of round r - l
         (round 0 = the setup commit), taken from the per-round committed snapshot kept by the run.
Reading: a read is the committed claims and items of that snapshot, plus the hash of the end_round event that
         committed it, so a reviewer can check it against board.jsonl; the realized read is recorded next to its lag.
Reading: lags come from lab/r1_read_schedule.py (alternating lag, round 1 exempt); read pin meta uses this file.
Reading: reads are recorded in summary.json and reads.json (plan.json holds the scheduled lags), not logged into the main Board, so board.jsonl keeps
         v3's event stream; the v3 delivery Board and its fixed marker are dropped.
"""

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from lab import r1_contention_schedule as contention_schedule
from lab import r1_read_schedule as read_schedule
from lab.r1_episode_v2 import CLAIM_TTL, ERROR_ROUND, MEASURED_ROUNDS, _score, _write
from lab.r1_episode_v3 import RULE as CONTENTION_RULE, schedule_plan
from murmuration import cell, router, team
from murmuration.board import Board, read_log
from murmuration.trapbench import alloc

READ_RULE = "alternating-read-lag-v4"
GENERATOR_PATH = "lab/r1_episode_v4.py"


def _meta(seed, rule):
    return {"generator_path": GENERATOR_PATH, "seed": seed, "rule": rule,
            "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}


def pinned_schedules(seed, taskset, workers):
    """Contention and read schedules with their pins; raises unless both definitions hold."""
    plan = schedule_plan(taskset, workers)
    rows = contention_schedule.schedule(plan)
    if not contention_schedule.satisfies(rows):
        raise ValueError("scheduled design does not satisfy contention above 1")
    lag_rows = read_schedule.lags(plan)
    if not read_schedule.staggered(lag_rows, plan["roster"]):
        raise ValueError("scheduled reads are not staggered")
    _, contention_pin = contention_schedule.pin(rows, _meta(seed, CONTENTION_RULE))
    _, read_pin = read_schedule.pin(lag_rows, _meta(seed, READ_RULE))
    return {"contention": {"table": [row | {"kappa": str(row["kappa"])} for row in rows],
                           "pin_sha256": contention_pin, "pin_meta": _meta(seed, CONTENTION_RULE)},
            "reads": {"lags": [{"round": r, "lags": row} for r, row in enumerate(lag_rows, start=1)],
                      "pin_sha256": read_pin, "pin_meta": _meta(seed, READ_RULE)}}


def run(output, *, case, seed=17, stop_after_round=MEASURED_ROUNDS):
    """Run a neutral fixture with an optional controlled stop after the Board commits."""
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
    scheduled = pinned_schedules(seed, taskset, workers)
    lag_table = {row["round"]: row["lags"] for row in scheduled["reads"]["lags"]}
    plan_tasks = schedule_plan(taskset, workers)["tasks"]
    owner = {job["task"]: job["agent"] for job in jobs}
    if [job["task"] for job in jobs] != [t["id"] for t in plan_tasks[:len(jobs)]]:
        raise ValueError("oracle jobs must follow the scheduled task order")
    rounds = []
    for index, job in enumerate(jobs, start=1):
        action = {key: value for key, value in job.items() if key != "action"} | {"type": "work"}
        action["answer"] += int(index == ERROR_ROUND[case])
        rounds.append({"round": index, "work": action})

    output = Path(output)
    output.mkdir()
    plan = {"scope": "scripted_r1_episode_v4", "case": case, "seed": seed, "taskset": taskset,
            "claim_ttl": CLAIM_TTL, "rounds": rounds, "planned_rounds": MEASURED_ROUNDS,
            "contention": {"round": 1, "task": contested, "workers": contenders},
            "scheduled_contention": scheduled["contention"], "scheduled_reads": scheduled["reads"],
            "controlled_stop_after_round": stop_after_round}
    plan_pin = _write(output / "plan.json", plan)
    board_path = output / "board.jsonl"
    operations = cell.create(output / "cell", "r1-episode-v4", "stub", "scripted", team.POLICY)
    handle = router.seal(Board(board_path, seed, claim_ttl=CLAIM_TTL), operations, practices=("A",), agents=workers)
    first = {"type": "claim", "agent": jobs[0]["agent"], "item": jobs[0]["task"]}
    if router.act(first, handle, enforced=False) != ("admitted", "ok"):
        raise ValueError("scripted setup claim was not admitted")
    router.end_round(handle)
    # snapshots[k] is the board as committed at the end of round k (0 = setup), with that commit's hash.
    snapshots = {0: _commit_view(board_path)}

    work, dispatch, reads = [], [], []
    first_score = contention = None
    for planned in rounds[:stop_after_round]:
        index = planned["round"]
        for agent in workers:
            lag = lag_table[index][agent]
            seen = index - lag
            view = snapshots[seen]
            reads.append({"reader": agent, "round": index, "scheduled_lag": lag, "seen_round": seen,
                          "seen_commit_hash": view["commit_hash"], "claims": view["claims"],
                          "items": sorted(item["id"] for item in view["items"])})
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
        snapshots[index] = _commit_view(board_path)
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

    main_trace = read_log(board_path)
    if [event["round"] for event in main_trace if event["type"] == "end_round"] != list(range(stop_after_round + 1)):
        raise ValueError("scripted commits differ from the planned boundary")
    if not cell.verify_log(operations):
        raise ValueError("scripted router cell log is invalid")
    dispatch_pin = _write(output / "dispatch.json", {"plan_sha256": plan_pin, "settled": dispatch})
    reads_pin = _write(output / "reads.json", {"plan_sha256": plan_pin, "reads": reads})

    completed = stop_after_round == MEASURED_ROUNDS
    summary = {
        "status": "completed" if completed else "incomplete_committed_prefix",
        "scope": plan["scope"], "case": case, "scientific_result": False,
        "planned_rounds": MEASURED_ROUNDS, "committed_measured_rounds": stop_after_round,
        "unstarted_work": MEASURED_ROUNDS - len(work), "board_reads": reads, "contention": contention,
        "scheduled_contention_pin_sha256": scheduled["contention"]["pin_sha256"],
        "scheduled_reads_pin_sha256": scheduled["reads"]["pin_sha256"],
        "first_round_score": first_score, "final_score": _score(work, taskset) if completed else None,
        "plan_sha256": plan_pin, "dispatch_sha256": dispatch_pin, "reads_sha256": reads_pin,
        "board_sha256": hashlib.sha256(board_path.read_bytes()).hexdigest(),
    }
    _write(output / "summary.json", summary)
    return summary


def _commit_view(board_path):
    """Committed board after the latest end_round, with the hash of that end_round event."""
    last = read_log(board_path)[-1]
    if last["type"] != "end_round":
        raise ValueError("a snapshot must be taken right after a commit")
    view = team.view_of(board_path)
    return {"commit_hash": last["hash"], "claims": view["claims"], "items": view["items"]}


def demo():
    with TemporaryDirectory(prefix="tremor-r1-episode-v4-") as temporary:
        root = Path(temporary)
        return {case: run(root / case, case=case) for case in ERROR_ROUND} | {
            "stopped_after_first": run(root / "stopped", case="late_error", stop_after_round=1)}


if __name__ == "__main__":
    print(json.dumps(demo(), sort_keys=True, indent=2, allow_nan=False))
