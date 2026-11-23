"""Four measured rounds on the scripted R1 board and allocation scorers."""

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from murmuration import cell, router, team
from murmuration.board import Board, read_log
from murmuration.trapbench import alloc, alloc2


MEASURED_ROUNDS = 4
CLAIM_TTL = 4
ERROR_ROUND = {"early_error": 1, "late_error": MEASURED_ROUNDS}
MARKER = "Development read marker"


def _write(path, value):
    raw = (json.dumps(value, sort_keys=True, allow_nan=False) + "\n").encode()
    with path.open("xb") as output:
        output.write(raw)
    return hashlib.sha256(raw).hexdigest()


def _score(rows, taskset):
    result = alloc2.second_scorer_gate(rows, taskset, alloc.score)
    if not result["valid"]:
        raise ValueError("invalid scripted episode work")
    return result


def run(output, *, case, seed=17, stop_after_round=MEASURED_ROUNDS):
    """Run a neutral fixture with an optional controlled stop after both Boards commit.

    An abrupt interruption before the controlled boundary produces no completion summary.
    """
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
    contenders = workers[1:3]
    rounds = []
    for index, job in enumerate(jobs, start=1):
        action = {key: value for key, value in job.items() if key != "action"} | {"type": "work"}
        action["answer"] += int(index == ERROR_ROUND[case])
        rounds.append({"round": index, "named_reader": job["agent"], "work": action})

    output = Path(output)
    output.mkdir()
    plan = {"scope": "scripted_r1_episode_v2", "case": case, "seed": seed, "taskset": taskset,
            "claim_ttl": CLAIM_TTL, "rounds": rounds, "planned_rounds": MEASURED_ROUNDS,
            "contention": {"round": 1, "task": contested, "workers": contenders},
            "controlled_stop_after_round": stop_after_round}
    plan_pin = _write(output / "plan.json", plan)
    board_path = output / "board.jsonl"
    operations = cell.create(output / "cell", "r1-episode-v2", "stub", "scripted", team.POLICY)
    handle = router.seal(Board(board_path, seed, claim_ttl=CLAIM_TTL), operations, practices=("A",), agents=workers)
    delivery = Board(output / "delivery.jsonl", seed)
    marker = delivery.post("fixture", MARKER, kind="fixture")
    for job in jobs:
        action = {"type": "claim", "agent": job["agent"], "item": job["task"]}
        if router.act(action, handle, enforced=False) != ("admitted", "ok"):
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
        if index == 1:
            for worker in contenders:
                action = {"type": "claim", "agent": worker, "item": contested}
                status, reason = router.act(action, handle, enforced=False)
                if status not in team.EXECUTED:
                    raise ValueError("scripted contender did not reach the Board")
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
        "first_round_score": first_score, "final_score": _score(work, taskset) if completed else None,
        "plan_sha256": plan_pin, "dispatch_sha256": dispatch_pin,
        "board_sha256": hashlib.sha256(board_path.read_bytes()).hexdigest(),
        "delivery_sha256": hashlib.sha256(delivery.path.read_bytes()).hexdigest(),
    }
    _write(output / "summary.json", summary)
    return summary


def demo():
    with TemporaryDirectory(prefix="tremor-r1-episode-v2-") as temporary:
        root = Path(temporary)
        return {case: run(root / case, case=case) for case in ERROR_ROUND} | {
            "stopped_after_first": run(root / "stopped", case="late_error", stop_after_round=1)}


if __name__ == "__main__":
    print(json.dumps(demo(), sort_keys=True, indent=2, allow_nan=False))
