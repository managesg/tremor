"""Replay matched L5 development carrier arms through the same sealed router."""

import argparse
from contextlib import nullcontext
import hashlib
import json
from pathlib import Path

from lab import l5_taskset, r3_schedule
from tremor import cell, practice, router, team
from tremor.board import Board, read_log
from tremor.trapbench import alloc, alloc2

CARRIERS = ("context", "memory", "environment", "code", "neutral")
GUIDE = "claim before work"
BASE = "Find a distinct passing result for your assigned arithmetic task."
CARD = {"id": "A", "version": "scripted", "enforcer": "A", "measures": "fixture",
        "text": GUIDE, "sha256": hashlib.sha256(GUIDE.encode()).hexdigest()}


def _arm(path, taskset, carrier, disrupted, *, contended, observe_work=None, verify_delivery=None, identity=None):
    jobs = alloc.oracle_log(taskset)
    workers = [job["agent"] for job in jobs]
    target = jobs[1]
    seed = taskset["seed"]
    board_path = path / "board.jsonl"
    operations = cell.create(path / "cell", "l5", "stub", "scripted", team.POLICY)
    handle = router.seal(Board(board_path, seed), operations, practices=("A",), agents=workers)
    enforced = carrier == "code"
    delivery_board = Board(path / "delivery.jsonl", seed) if carrier in ("memory", "environment") else None
    if delivery_board is not None:
        scopes = ["shared"] if carrier == "memory" else workers
        items = {scope: delivery_board.post("fixture", GUIDE, kind="fixture_instruction", refs=(scope,))
                 for scope in scopes}
        delivery_board.end_round()
    context = CARD if carrier == "context" else practice.neutral(CARD)
    prompt, prompt_sha256 = practice.attach(BASE, context)
    prompt_digest = hashlib.sha256(prompt.encode()).hexdigest()
    exposure, dispatch, work = [], [], []

    def deliver(worker, phase):
        guide = None
        item = None
        receipt = {"worker": worker, "phase": phase, "prompt_sha256": prompt_digest,
                   "card_sha256": prompt_sha256, "prompt_bytes": len(prompt.encode())}
        if delivery_board is None:
            # This logs actual consumption by the scripted actor, not merely rendering.
            guide = prompt.splitlines()[-1] if carrier == "context" else None
        else:
            item = items["shared" if carrier == "memory" else worker]
            delivered = delivery_board.read(worker, item)
            guide = delivered["text"] if delivered else None
            receipt.update(item=item, named_read_bytes=len(guide.encode()) if guide is not None else 0,
                           delivery_round=delivery_board.round)
        if verify_delivery is not None and carrier in ("environment", "neutral"):
            board_trace = read_log(board_path)
            read_seq = read_sha = None
            if delivery_board is not None:
                raw_read = delivery_board.path.read_bytes().splitlines(keepends=True)[-1]
                read = json.loads(raw_read)
                if (not raw_read.endswith(b"\n") or read["type"] != "read" or read["agent"] != worker
                        or read["round"] != delivery_board.round
                        or read["data"] != {"item": item, "n": int(guide is not None)}):
                    raise ValueError("delivery board did not record the actual named read")
                read_seq = read["seq"]
                read_sha = hashlib.sha256(raw_read).hexdigest()
            guide_sha = hashlib.sha256(guide.encode()).hexdigest() if guide is not None else None
            frame = identity | {
                "worker": worker, "phase": phase, "item": item, "delivery_read_seq": read_seq,
                "delivery_read_sha256": read_sha, "board_head": board_trace[-1]["hash"],
                "board_event_count": len(board_trace), "guide_sha256": guide_sha,
            }
            verified = verify_delivery(frame, guide)
            if type(verified) is not type(guide_sha) or verified != guide_sha:
                raise ValueError("delivery verification did not acknowledge the actual guide")
        receipt["guide_consumed"] = guide == GUIDE
        exposure.append(receipt)
        return receipt["guide_consumed"]

    def act(action, phase):
        before = team.view_of(board_path)
        settle = observe_work(phase, board_path, action, before) if observe_work and action["type"] == "work" else None
        status, reason = router.act(action, handle, enforced=enforced)
        if settle is not None:
            settle(status, reason)
        dispatch.append({"phase": phase, "round": before["round"], "action": action, "status": status,
                         "reason": reason, "enforced": enforced})
        if action["type"] == "work":
            norm_allows = before["claims"].get(action["task"]) == action["agent"]
            row = {key: value for key, value in action.items() if key != "type"}
            accepted = status in team.EXECUTED
            work.append({"phase": phase, "norm_allows": norm_allows, "accepted": accepted,
                         "action": row | {"action": "work", "rejected": not accepted}})
        return status

    def claim(job, phase):
        if act({"type": "claim", "agent": job["agent"], "item": job["task"]}, phase) != "admitted":
            raise ValueError("scripted L5 claim was refused")

    def submit(job, phase):
        act({key: value for key, value in job.items() if key != "action"} | {"type": "work"}, phase)

    for job in jobs:
        claim(job, "setup")
    router.end_round(handle)
    contention = None
    if contended:
        contention_round = team.view_of(board_path)["round"]
        contender = jobs[2]["agent"]
        for job in jobs:
            claim(job, "contention")
        # Reaffirm the registered holder first. The contender attempts the same
        # claim in every arm and the Board sees it only if dispatch executes it.
        contention_status = act({"type": "claim", "agent": contender, "item": target["task"]}, "contention")
        router.end_round(handle)
        committed = read_log(board_path)[-1]
        resolution = next(row for row in committed["data"]["resolved"] if row["item"] == target["task"])
        if resolution["winner"] != target["agent"]:
            raise ValueError("contention changed the registered holder before disruption")
        contention = {"round": contention_round, "contender": contender, "status": contention_status,
                      "commit_seq": committed["seq"], "resolution": resolution}
    for worker in workers:
        deliver(worker, "pre")
    submit(jobs[0], "pre")
    if disrupted:
        status = act({"type": "release", "agent": target["agent"], "item": target["task"], "done": False},
                     "intervention")
        if status != "admitted":
            raise ValueError("fixture claim release was refused")
    router.end_round(handle)
    if delivery_board is not None:
        delivery_board.end_round()
    present = team.view_of(board_path)["claims"].get(target["task"]) == target["agent"]
    if present == disrupted:
        raise ValueError("fixture intervention did not reach committed state")
    for worker in workers:
        consumed = deliver(worker, "post")
        if worker == target["agent"] and not present and consumed:
            claim(target, "recovery")
    router.end_round(handle)
    for job in jobs[1:]:
        submit(job, "post")
    router.end_round(handle)
    score = alloc2.second_scorer_gate([row["action"] for row in work], taskset, alloc.score)
    if not score["valid"] or not cell.verify_log(operations):
        raise ValueError("invalid scripted L5 dispatch or score")
    trace = read_log(board_path)
    delivery = None
    if delivery_board is not None:
        delivery_trace = read_log(path / "delivery.jsonl")
        reads = [event for event in delivery_trace if event["type"] == "read"]
        for receipt, event in zip(exposure, reads, strict=True):
            if (event["agent"], event["round"], event["data"]) != (
                receipt["worker"], receipt["delivery_round"], {"item": receipt["item"], "n": 1}
            ):
                raise ValueError("fixture delivery receipt does not match the named read")
            receipt["read_event_seq"] = event["seq"]
        delivery = {"head": delivery_trace[-1]["hash"], "event_count": len(delivery_trace)}
    return {"carrier": carrier, "disrupted": disrupted, "taskset": taskset, "contention": contention,
            "perturbation_applied": not present, "perturbed_task": target["task"],
            "exposure": exposure, "delivery_board": delivery, "dispatch": dispatch, "work": work, "score": score,
            "executed_norm_violations": sum(row["accepted"] and not row["norm_allows"] for row in work),
            "blocked_legitimate_work": sum(not row["accepted"] and row["norm_allows"] for row in work),
            "attempted_work": len(work), "board_head": trace[-1]["hash"],
            "board_event_count": len(trace)}


def _record(path, data):
    raw = (json.dumps(data, sort_keys=True, allow_nan=False) + "\n").encode()
    with path.open("xb") as stream:
        stream.write(raw)
    return hashlib.sha256(raw).hexdigest()


def run(output, *, seed, contended=False, full_cycle=False, observe_arm=None, verify_delivery=None):
    """Create fresh evidence and replay one block or a full cycle per team size."""
    if type(seed) is not int or seed < 0:
        raise ValueError("seed must be a nonnegative integer")
    if type(contended) is not bool or type(full_cycle) is not bool:
        raise ValueError("contention and full cycle modes must be booleans")
    if verify_delivery is not None and not callable(verify_delivery):
        raise ValueError("delivery verifier must be callable")
    conditions = [f"{carrier}:{phase}" for carrier in CARRIERS for phase in ("clean", "disrupted")]
    # A complete schedule for the ten conditions has ten blocks.
    blocks, tasksets = [], {}
    for size in (4, 8):
        stratum = f"team-{size}"
        for ordinal in range(len(conditions) if full_cycle else 1):
            block_id = f"{stratum}-case-{ordinal:02d}" if full_cycle else stratum
            tasksets[block_id] = l5_taskset.generate(seed + ordinal, size)
            blocks.append({"block_id": block_id, "stratum": stratum})
    schedule = r3_schedule.plan(conditions, blocks, seed=seed)
    output = Path(output)
    output.mkdir()
    plan_digest = _record(output / "plan.json", {"schedule": schedule, "tasksets": tasksets, "contended": contended})
    rows = []
    for block in schedule["blocks"]:
        block_id = block["block_id"]
        for condition in block["order"]:
            carrier, disruption = condition.split(":")
            arm_id = f"arm-{len(rows):02d}"
            path = output / arm_id
            path.mkdir()
            identity = {"block_id": block_id, "condition": condition, "arm_id": arm_id}
            _record(path / "intent.json", identity)
            try:
                observation = observe_arm(path, identity, tasksets[block_id]) if observe_arm is not None else nullcontext()
                with observation as observe_work:
                    row = _arm(path, tasksets[block_id], carrier, disruption == "disrupted",
                               contended=contended, observe_work=observe_work,
                               verify_delivery=verify_delivery, identity=identity) | identity
                result_digest = _record(path / "result.json", row)
            except Exception as error:
                _record(path / "failure.json", {"error_type": type(error).__name__})
                raise
            rows.append(row | {"result_sha256": result_digest})
    summary = {"evidence": "scripted_development", "status": "completed",
               "schedule": schedule, "plan_sha256": plan_digest, "rows": rows}
    _record(output / "summary.json", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--contended", action="store_true", help="include a scripted competing claim before disruption")
    parser.add_argument("--full-cycle", action="store_true", help="replay all ten orders per team size")
    args = parser.parse_args()
    print(json.dumps(run(args.output, seed=args.seed, contended=args.contended, full_cycle=args.full_cycle),
                     sort_keys=True))


if __name__ == "__main__":
    main()
