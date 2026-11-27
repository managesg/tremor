"""Read-only audit of a saved L5 development matrix using an external summary pin."""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

from tremor import cell, team
from tremor.board import read_log
from tremor.trapbench import alloc, alloc2


def _require(condition, detail):
    if not condition:
        raise ValueError(detail)


def _pinned_json(path, digest):
    data = path.read_bytes()
    _require(hashlib.sha256(data).hexdigest() == digest, f"{path.name} digest mismatch")
    return json.loads(data)


def _trace(path, head, count):
    trace = read_log(path)
    _require(trace and (trace[-1]["hash"], len(trace)) == (head, count), f"{path.name} terminal mismatch")
    return trace


def _schedule_counts(schedule):
    """Recompute observed position and directed-neighbor counts from ordered blocks."""
    conditions = schedule["conditions"]
    count = len(conditions)
    _require(count == 10 and len(set(conditions)) == count, "unexpected L5 condition inventory")
    by_stratum = defaultdict(list)
    for block in schedule["blocks"]:
        order = block["order"]
        _require(len(order) == count and set(order) == set(conditions), "block is not a complete condition permutation")
        by_stratum[block["stratum"]].append(order)
    _require(set(by_stratum) == set(schedule["strata"]) == {"team-4", "team-8"},
             "schedule strata differ from observed team sizes")
    cycles = {}
    for stratum, orders in by_stratum.items():
        size = schedule["strata"][stratum]["cycle_size"]
        completed, remainder = divmod(len(orders), count)
        positions = Counter((condition, i) for order in orders for i, condition in enumerate(order))
        neighbors = Counter(pair for order in orders for pair in zip(order, order[1:]))
        expected = {"positions": {condition: [positions[condition, i] for i in range(count)]
                                  for condition in conditions},
                    "adjacent": {a: {b: neighbors[a, b] for b in conditions if a != b} for a in conditions},
                    "complete_cycles": completed, "remainder_blocks": remainder, "cycle_size": count}
        _require(size == count and expected == schedule["strata"][stratum],
                 "schedule position or neighbor counts do not match executed order")
        for start in range(0, completed * count, count):
            cycle = orders[start:start + count]
            _require(all(len(set(position)) == count for position in zip(*cycle))
                     and len({pair for order in cycle for pair in zip(order, order[1:])}) == count * (count - 1),
                     "claimed complete cycle is not position and neighbor balanced")
        cycles[stratum] = completed
    return cycles


def _claim_history(trace):
    claims, released, rounds = {}, set(), {0: {}}
    for event in trace:
        if event["type"] == "release":
            released.add(event["data"]["item"])
        if event["type"] != "end_round":
            continue
        expired = {effect["item"] for effect in event["data"]["expired"]}
        for item in released | expired:
            claims.pop(item, None)
        for resolution in event["data"]["resolved"]:
            if resolution["winner"] is not None:
                claims[resolution["item"]] = resolution["winner"]
        rounds[event["round"] + 1] = claims.copy()
        released.clear()
    return rounds


def _delivery(arm, row):
    path = arm / "delivery.jsonl"
    receipt = row["delivery_board"]
    if row["carrier"] not in ("memory", "environment"):
        _require(receipt is None and not path.exists(), "unexpected named delivery board")
        return 0
    trace = _trace(path, receipt["head"], receipt["event_count"])
    posts = {event["data"]["id"]: event for event in trace if event["type"] == "post"}
    reads = [event for event in trace if event["type"] == "read"]
    for reported, read in zip(row["exposure"], reads, strict=True):
        post = posts[reported["item"]]
        worker = reported["worker"]
        scope = "shared" if row["carrier"] == "memory" else worker
        _require(read["seq"] == reported["read_event_seq"] and read["agent"] == worker
                 and read["round"] == reported["delivery_round"]
                 and read["data"] == {"item": reported["item"], "n": 1}
                 and post["round"] < read["round"] and post["data"]["refs"] == [scope]
                 and len(post["data"]["text"].encode()) == reported["named_read_bytes"],
                 "named delivery does not match worker, scope or committed bytes")
    return len(reads)


def _work(arm, row, *, contended):
    trace = _trace(arm / "board.jsonl", row["board_head"], row["board_event_count"])
    claims = _claim_history(trace)
    target = row["perturbed_task"]
    boundary = 2 if contended else 1
    prior_holder = claims[boundary].get(target)
    released = [event for event in trace if event["type"] == "release"]
    disrupted = row["disrupted"]
    _require(prior_holder is not None and len(released) == int(disrupted)
             and all(event["round"] == boundary and event["agent"] == prior_holder
                     and event["data"]["item"] == target and event["data"]["done"] is False for event in released)
             and claims[boundary + 1].get(target) == (None if disrupted else prior_holder)
             and row["perturbation_applied"] is disrupted, "disruption differs from committed claim history")
    contention = row.get("contention")
    _require((contention is not None) is contended, "contention evidence differs from plan")
    if contention is not None:
        commit = trace[contention["commit_seq"]]
        recorded = contention["resolution"]
        contender = contention["contender"]
        expected = "refused" if row["carrier"] == "code" else "violation_executed"
        attempts = [event for event in row["dispatch"] if event["phase"] == "contention"
                    and event["action"] == {"type": "claim", "item": target, "agent": contender}]
        _require(commit["type"] == "end_round" and commit["round"] == contention["round"]
                 and recorded in commit["data"]["resolved"] and recorded["item"] == target
                 and recorded["winner"] == claims[commit["round"]].get(target)
                 and recorded["collision"] is (expected == "violation_executed")
                 and (contender in recorded["claimants"]) is recorded["collision"]
                 and len(attempts) == 1 and attempts[0]["status"] == contention["status"] == expected,
                 "contention attempt differs from committed claim resolution")
    attempts = [event for event in row["dispatch"] if event["action"]["type"] == "work"]
    _require(len(attempts) == row["attempted_work"] == row["taskset"]["n_agents"], "wrong work denominator")
    violations = blocked = 0
    actions = []
    for event, work in zip(attempts, row["work"], strict=True):
        action = event["action"]
        allowed = claims[event["round"]].get(action["task"]) == action["agent"]
        enforced = row["carrier"] == "code"
        expected = "admitted" if allowed else "refused" if enforced else "violation_executed"
        accepted = expected in team.EXECUTED
        saved = {key: value for key, value in action.items() if key != "type"}
        saved.update(action="work", rejected=not accepted)
        _require(event["enforced"] is enforced and event["status"] == expected
                 and work == {"phase": event["phase"], "norm_allows": allowed, "accepted": accepted, "action": saved},
                 "work verdict differs from committed claims and carrier policy")
        violations += accepted and not allowed
        blocked += not accepted and allowed
        actions.append(saved)
    _require((row["executed_norm_violations"], row["blocked_legitimate_work"]) == (violations, blocked),
             "norm counts do not match work verdicts")
    score = alloc2.second_scorer_gate(actions, row["taskset"], alloc.score)
    log = arm / "cell" / "log.jsonl"
    _require(score["valid"] and score == row["score"] and cell.verify_log(log.parent), "invalid score or cell log")
    entries = [json.loads(line)["entry"] for line in log.read_bytes().splitlines()] if log.exists() else []
    outcomes = [event for event in row["dispatch"] if event["status"] != "admitted"]
    for entry, outcome in zip(entries, outcomes, strict=True):
        _require(entry["status"] == outcome["status"] and entry["reason"] == outcome["reason"]
                 and entry["agent"] == outcome["action"]["agent"]
                 and entry["action_type"] == outcome["action"]["type"],
                 "recorded dispatch outcome lacks matching cell evidence")
    return [event["action"] for event in attempts]


def audit(directory, *, summary_sha256):
    directory = Path(directory)
    summary = _pinned_json(directory / "summary.json", summary_sha256)
    _require(summary["evidence"] == "scripted_development" and summary["status"] == "completed",
             "missing completed development matrix")
    plan = _pinned_json(directory / "plan.json", summary["plan_sha256"])
    _require(summary["schedule"] == plan["schedule"], "completion schedule differs from plan")
    cycles = _schedule_counts(plan["schedule"])
    blocks = plan["schedule"]["blocks"]
    tasksets = plan["tasksets"]
    _require(len(blocks) == len(tasksets) and {block["block_id"] for block in blocks} == set(tasksets)
             and all(block["stratum"] == f'team-{tasksets[block["block_id"]]["n_agents"]}' for block in blocks),
             "scheduled blocks do not match the declared tasksets and team sizes")
    positions = [(block["block_id"], condition) for block in blocks for condition in block["order"]]
    _require({path.name for path in directory.glob("arm-*")} == {f"arm-{i:02d}" for i in range(len(positions))},
             "archive contains missing or unexpected arm directories")
    common, named_reads, work_attempts = {}, 0, 0
    for index, ((block_id, condition), reported) in enumerate(zip(positions, summary["rows"], strict=True)):
        arm_id = f"arm-{index:02d}"
        arm = directory / arm_id
        identity = {"block_id": block_id, "condition": condition, "arm_id": arm_id}
        _require(json.loads((arm / "intent.json").read_bytes()) == identity and not (arm / "failure.json").exists(),
                 "completed arm has mismatched intent or failure")
        row = _pinned_json(arm / "result.json", reported["result_sha256"])
        _require(reported == row | {"result_sha256": reported["result_sha256"]}
                 and all(row[key] == value for key, value in identity.items())
                 and row["taskset"] == tasksets[block_id]
                 and condition == f'{row["carrier"]}:{"disrupted" if row["disrupted"] else "clean"}',
                 "arm result differs from its schedule or summary")
        attempts = _work(arm, row, contended=plan.get("contended", False))
        _require(common.setdefault(block_id, attempts) == attempts, "work attempts changed within a matched block")
        named_reads += _delivery(arm, row)
        work_attempts += len(attempts)
    return {"status": "verified", "arms": len(positions), "work_attempts": work_attempts,
            "named_reads": named_reads, "complete_cycles": cycles, "summary_sha256": summary_sha256}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--summary-sha256", required=True)
    args = parser.parse_args()
    try:
        result = audit(args.directory, summary_sha256=args.summary_sha256)
    except (IndexError, KeyError, OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
