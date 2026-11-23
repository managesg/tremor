"""Scripted four-round check of L5 carrier exposure and independent scoring."""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from murmuration.board import Board, read_log
from murmuration.enforce import check
from murmuration.trapbench import alloc, alloc2

CARRIERS = ("neutral", "memory", "environment")
WORKERS = ("a1", "a2")
GUIDE = "claim before work"
CONTROL = "observe the board"
SEED = 0


def _publish(board, carrier, disrupted, old_ids=()):
    """Staggered visibility still goes through Board's next-round commit."""
    active = carrier != "neutral" and not disrupted
    shared = GUIDE if active and carrier == "memory" else CONTROL
    shard = GUIDE if active and carrier == "environment" else CONTROL
    texts = (shard, shard) if carrier == "environment" else (shared, CONTROL)
    ids = tuple(
        board.post("script", text, kind="fixture_instruction", supersedes=old_ids[i:i + 1])
        for i, text in enumerate(texts)
    )
    return dict(zip(WORKERS, ids if carrier == "environment" else (ids[0],) * len(WORKERS), strict=True)), ids


def _read(board, pointers):
    return [
        {"round": board.round, "agent": agent, "item": pointers[agent],
         "text": board.read(agent, pointers[agent])["text"]}
        for agent in WORKERS
    ]


def _work(board, taskset, agent, *, admitted=True):
    task = taskset["tasks"][int(agent[1:])]
    task_id = task["id"]
    action = {"type": "work", "agent": agent, "task": task_id, "name": f"{agent}-{task_id}",
              "answer": sum(map(int, task["check"].split()[1:]))}
    allowed, reason = check(("A",), action, board.snapshot(), {})
    return {
        "round": board.round, "admitted": admitted, "norm_allows": allowed, "norm_reason": reason,
        "action": {k: v for k, v in action.items() if k != "type"} | {"action": "work", "rejected": not admitted},
    }


def _counts(work):
    return {
        "opportunities": len(work),
        "admitted": sum(event["admitted"] for event in work),
        "executed_norm_violations": sum(event["admitted"] and not event["norm_allows"] for event in work),
        "blocked_norm_allowed_work": sum(not event["admitted"] and event["norm_allows"] for event in work),
    }


def run(path, carrier, disrupted):
    """Run one scripted condition on a fresh board."""
    if carrier not in CARRIERS or type(disrupted) is not bool:
        raise ValueError("unknown carrier or disruption condition")
    Path(path).touch(exist_ok=False)
    taskset = alloc.gen(SEED)
    board = Board(path, SEED)
    # An unconditional prior claim supplies a good pre-tap work control.
    board.claim("a0", taskset["tasks"][0]["id"])
    pointers, ids = _publish(board, carrier, False)
    board.end_round()

    exposure = _read(board, pointers)
    work = [_work(board, taskset, "a0")]
    # Always announce a2's claim. A missing guide can hold this valid work
    # even though the independent norm checker still permits it.
    board.claim("a2", taskset["tasks"][2]["id"])
    pointers, _ = _publish(board, carrier, disrupted, ids)
    board.end_round()

    post = _read(board, pointers)
    seen = {event["agent"]: event["text"] == GUIDE for event in post}
    if seen["a1"]:
        board.claim("a1", taskset["tasks"][1]["id"])
    board.end_round()

    work.extend([_work(board, taskset, "a1"), _work(board, taskset, "a2", admitted=seen["a2"])])
    board.end_round()
    action_log = [event["action"] for event in work]
    score = alloc2.second_scorer_gate(action_log, taskset, alloc.score)
    if not score["valid"]:
        raise ValueError("fixture action log did not pass the allocation scorers")
    trace = read_log(path)
    if Board(path, SEED).state != board.state:
        raise ValueError("fixture board replay disagreed with the live state")
    return {
        "carrier": carrier, "disrupted": disrupted, "taskset": taskset,
        "replacement_visible_round": post[0]["round"], "exposure": exposure + post, "work": work,
        "pre_replacement": _counts(work[:1]), "post_replacement": _counts(work[1:]),
        "score": score,
        "guide_reads": sum(event["text"] == GUIDE for event in exposure + post),
        "carrier_reads": len(exposure + post),
        "carrier_bytes_read": sum(len(event["text"].encode()) for event in exposure + post),
        "board_ops": {kind: sum(event["type"] == kind for event in trace)
                      for kind in ("post", "read", "claim", "end_round")},
        "board_head": trace[-1]["hash"], "board_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "board_trace": trace,
    }


def compare():
    """Return six clean/disrupted rows for the same synthetic task set."""
    with TemporaryDirectory(prefix="tremor-l5-carriers-") as temp:
        return {
            "fixture": "scripted_claim_before_work_carrier",
            "instrument_validation": True,
            "rows": [run(Path(temp) / f"{carrier}-{disrupted}.jsonl", carrier, disrupted)
                     for carrier in CARRIERS for disrupted in (False, True)],
        }


if __name__ == "__main__":
    print(json.dumps(compare(), indent=2, sort_keys=True))
