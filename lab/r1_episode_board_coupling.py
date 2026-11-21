"""Scripted four-round R1 fixture with scoring coupled to one committed Board."""

import hashlib
import json
from pathlib import Path

from lab.r1_episode_v2 import CLAIM_TTL, ERROR_ROUND, MEASURED_ROUNDS, _score, _write
from murmuration import cell, router, team
from murmuration.board import Board, read_log
from murmuration.trapbench import alloc


def _act(handle, action, *, contender=False):
    status, reason = router.act(action, handle, enforced=not contender)
    if status not in (team.EXECUTED if contender else ("admitted",)):
        raise ValueError(f"scripted action did not execute: {reason}")


def _post(handle, actor, kind, payload, *, refs=()):
    _act(handle, {
        "type": "post", "agent": actor, "kind": kind,
        "text": json.dumps(payload, sort_keys=True), "refs": list(refs),
    })


def _commit(handle, path):
    router.end_round(handle)
    return read_log(path)[-1]


def _work(handle, board, task, actor, planned_round, note_id):
    _act(handle, {"type": "read", "agent": actor})
    read = read_log(board)[-1]
    view = team.view_of(board)
    if read["type"] != "read" or view["round"] != planned_round or view["claims"].get(task["id"]) != actor:
        raise ValueError("scripted work requires a committed read and claim")
    note = next((item for item in view["items"] if item["id"] == note_id), None)
    if note is None or note["round"] >= planned_round:
        raise ValueError("scripted worker could not read the committed input")
    left = json.loads(note["text"])[task["id"]]
    right = int(task["check"].split()[-1])
    action = {"type": "work", "agent": actor, "task": task["id"],
              "name": alloc.NAME_RULE.format(agent=actor, task=task["id"]), "answer": left + right}
    _act(handle, action)
    receipt = {key: value for key, value in action.items() if key != "type"} | {
        "action": "work", "rejected": False, "read_head": read["hash"],
    }
    _post(handle, actor, "fixture_work_receipt", receipt, refs=(note_id,))
    return read


def _committed_receipts(board):
    log = read_log(board)
    view = team.view_of(board)
    receipts = [json.loads(item["text"]) for item in view["items"] if item["kind"] == "fixture_work_receipt"]
    if len(receipts) != view["round"] - 1:
        raise ValueError("one work receipt is required per measured round")
    return receipts, log[-1]


def run(output, *, case, seed=17, stop_after_round=MEASURED_ROUNDS):
    """Exercise scripted inputs, claims and score boundaries without model calls."""
    if type(case) is not str or case not in ERROR_ROUND or type(seed) is not int or seed < 0:
        raise ValueError("expected a known scripted case and a nonnegative seed")
    if type(stop_after_round) is not int or not 0 <= stop_after_round <= MEASURED_ROUNDS:
        raise ValueError("stop must be a measured round boundary")
    output = Path(output)
    output.mkdir()
    taskset = alloc.gen(seed)
    tasks = taskset["tasks"]
    workers = ["a0", "a1", "a2", "a3"]
    contenders = ("a0", "a1")
    assignments = dict(zip(workers, (tasks[2], tasks[3], tasks[4], tasks[1]), strict=True))
    contested = tasks[0]["id"]
    inputs = {task["id"]: int(task["check"].split()[1]) for task in tasks}
    changed_task = tasks[1 if ERROR_ROUND[case] == 1 else 4]["id"]
    inputs[changed_task] += 1
    plan_pin = _write(output / "plan.json", {
        "case": case, "seed": seed, "taskset": taskset, "inputs": inputs,
        "contested": contested, "claimants": contenders, "controlled_stop_after_round": stop_after_round,
    })
    operations = cell.create(output / "cell", "r1-board-coupling", "stub", "scripted", team.POLICY)
    board = output / "board.jsonl"
    handle = router.seal(Board(board, seed, claim_ttl=CLAIM_TTL), operations, practices=("A",), agents=workers)
    _post(handle, "a3", "fixture_inputs", inputs)
    note_id = read_log(board)[-1]["data"]["id"]
    for worker, task in assignments.items():
        _act(handle, {"type": "claim", "agent": worker, "item": task["id"]})
    _commit(handle, board)

    contention = first_score = None
    reads = []
    schedule = [("a3", tasks[1])]
    for index in range(1, stop_after_round + 1):
        actor, task = schedule[index - 1]
        if index == 1:
            for worker in contenders:
                _act(handle, {"type": "claim", "agent": worker, "item": contested}, contender=True)
        read = _work(handle, board, task, actor, index, note_id)
        reads.append({"round": index, "reader": actor, "item": note_id, "read_head": read["hash"]})
        commit = _commit(handle, board)
        if index == 1:
            resolution = next(row for row in commit["data"]["resolved"] if row["item"] == contested)
            winner = resolution["winner"]
            if not resolution["collision"] or resolution["claimants"] != list(contenders) or winner not in contenders:
                raise ValueError("expected two committed claimants and a winner")
            loser = next(worker for worker in contenders if worker != winner)
            schedule.extend(((winner, tasks[0]), (loser, assignments[loser]), ("a2", assignments["a2"])))
            contention = {"commit_head": commit["hash"], **resolution}
            work, head = _committed_receipts(board)
            first_score = {"board_head": head["hash"], "distinct_passing": _score(work, taskset)["distinct_passing"]}

    if not cell.verify_log(operations):
        raise ValueError("invalid scripted Router cell log")
    work, _ = _committed_receipts(board)
    completed = stop_after_round == MEASURED_ROUNDS
    result = {
        "scope": "scripted_r1_board_coupling", "scientific_result": False, "case": case,
        "committed_measured_rounds": stop_after_round, "unstarted_work": MEASURED_ROUNDS - len(work),
        "status": "completed" if completed else "incomplete_committed_prefix",
        "first_round_score": first_score, "final_score": _score(work, taskset) if completed else None,
        "contention": contention, "committed_input_reads": reads,
        "plan_sha256": plan_pin, "board_sha256": hashlib.sha256(board.read_bytes()).hexdigest(),
    }
    _write(output / "summary.json", result)
    return result
