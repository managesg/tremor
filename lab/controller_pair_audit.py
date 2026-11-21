"""Replay a pinned scripted combined/plain comparison with explicit resource receipts."""

import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path

from lab import controller_selection as selection
from murmuration.trapbench import alloc, alloc2

ARMS = ("combined", "plain")
USAGE = tuple(field for field in selection.BUDGET if not field.startswith("per_call_"))
ROLES = {"worker", "routing", "observation", "communication", "coordination", "verification", "advice", "cleanup"}
TOKEN_FIELDS = ("input_tokens", "output_tokens", "cache_read_tokens", "cache_creation_tokens")


def _scorer_ids():
    return {module.__name__.rsplit(".", 1)[1]: hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
            for module in (alloc, alloc2)}


def _outcome(block, arm, row, manifest, prior):
    selection._object(row, ("block_id", "arm", "condition", "seed", "scope", "inputs",
                            "policy_sha256", "terminal", "attempts"), "arm trace")
    settings = manifest["arms"][arm]
    expected = {"block_id": block["block_id"], "arm": arm, "condition": block["condition"],
                "seed": block["seed"], "scope": manifest["scope"], "inputs": manifest["inputs"],
                "policy_sha256": settings["policy_sha256"]}
    selection._require(all(row[key] == value for key, value in expected.items()),
                       "observed arm inputs differ from the scheduled block and selection")
    terminal = row["terminal"]
    selection._require(terminal in ("completed", "stopped", "void") and type(row["attempts"]) is list,
                       "unknown arm termination or attempts")
    totals = dict.fromkeys(selection.BUDGET, 0)
    cumulative = prior["known_usage"].copy()
    unknown = []
    work = []
    for ordinal, attempt in enumerate(row["attempts"]):
        selection._object(attempt, ("sequence", "role", "status", "usage", "work"), "attempt")
        selection._require(type(attempt["sequence"]) is int and attempt["sequence"] == ordinal
                           and attempt["role"] in ROLES and attempt["status"] in ("completed", "failed", "refused"),
                           "invalid attempt sequence, role or status")
        selection._require(attempt["role"] == "cleanup" or not _breaches(cumulative, settings["budget"]),
                           "only cleanup can follow a recorded cap breach")
        selection._require(attempt["role"] == "cleanup" or not (unknown or prior["unknown_usage_attempts"]),
                           "only cleanup can follow unresolved usage")
        usage = attempt["usage"]
        if usage is None:
            unknown.append(ordinal)
        else:
            charged = _meter(usage)
            _accumulate(totals, charged)
            _accumulate(cumulative, charged)
        action = attempt["work"]
        if action is not None:
            selection._object(action, ("agent", "task", "name", "answer"), "worker proposal")
            selection._require(attempt["role"] == "worker", "non-worker role cannot submit work")
            work.append({**action, "action": "work", "rejected": attempt["status"] != "completed"})
    overruns = _breaches(totals, settings["budget"])
    base = {"arm": arm, "terminal": terminal, "attempts": len(row["attempts"]),
            "known_usage": totals, "unknown_usage_attempts": unknown, "exceeded_caps": overruns}
    if terminal != "completed":
        return {**base, "distinct_passing": None}
    selection._require(not unknown and not overruns, "completed arm has unaccounted usage or exceeded a cap")
    selection._require(any(attempt["role"] == "worker" for attempt in row["attempts"]),
                       "completed arm lacks any worker observation")
    taskset = block["taskset"]
    primary, score = alloc.score(work, taskset), alloc2.score(work, taskset)
    selection._require(score["valid"] and not alloc2.compare(primary, score),
                       "completed arm failed independent work scoring")
    selection._require(primary["unknown_task_events"] == 0,
                       "completed arm submitted work outside the frozen task inventory")
    return {**base, "distinct_passing": score["distinct_passing"], "duplicate_work": score["duplicates"]}


def _meter(usage):
    selection._object(usage, USAGE, "attempt resource receipt")
    selection._require(all(type(value) is int and value >= 0 for value in usage.values())
                       and usage["calls"] <= 1, "attempt resources must be nonnegative integers with at most one call")
    if usage["calls"] == 0:
        selection._require(not any(usage[key] for key in TOKEN_FIELDS), "token usage has no recorded call")
    total_input = usage["input_tokens"] + usage["cache_read_tokens"] + usage["cache_creation_tokens"]
    return usage | {"per_call_input_tokens": total_input, "per_call_output_tokens": usage["output_tokens"]}


def _accumulate(totals, vector):
    for field, amount in vector.items():
        totals[field] = max(totals[field], amount) if field.startswith("per_call_") else totals[field] + amount


def _breaches(totals, limits):
    return [field for field, amount in totals.items() if amount > limits[field]]


def verify(bundle, manifest, evidence_index, trace, *, manifest_sha256, evidence_index_sha256, trace_sha256):
    selected = selection.verify(bundle, manifest, evidence_index, manifest_sha256=manifest_sha256,
                                evidence_index_sha256=evidence_index_sha256)
    document = selection._pinned_json(manifest, selected["manifest_sha256"])
    tape = selection._pinned_json(trace, trace_sha256)
    selection._object(tape, ("evidence", "manifest_sha256", "input_files", "arms"), "paired trace")
    selection._require(tape["evidence"] == "scripted_cpu" and tape["manifest_sha256"] == manifest_sha256,
                       "trace must bind the pinned scripted controller selection")
    root = Path(bundle).resolve(strict=True)
    references = selection._object(tape["input_files"], document["inputs"], "input artifacts")
    for key, reference in references.items():
        selection._match_artifact(root, reference)
        selection._require(reference["sha256"] == document["inputs"][key], "observed common input changed")
    validators = references["scorer_sha256"]
    descriptor = selection._pinned_json(selection._reference(root, validators), validators["sha256"])
    selection._require(descriptor == {"scorers": _scorer_ids()}, "loaded scorer bytes differ from the frozen pair")
    tasks = references["task_manifest_sha256"]
    inventory = selection._pinned_json(selection._reference(root, tasks), tasks["sha256"])
    selection._object(inventory, ("blocks",), "task inventory")
    blocks = inventory["blocks"]
    selection._require(type(blocks) is list and blocks and type(tape["arms"]) is list, "empty or invalid block inventory")
    selection._require(len(tape["arms"]) == 2 * len(blocks), "each declared arm needs a terminal trace")
    resources = {arm: {"known_usage": dict.fromkeys(selection.BUDGET, 0),
                       "unknown_usage_attempts": 0, "exceeded_caps": []} for arm in ARMS}
    seen, pairs = set(), []
    for block_index, block in enumerate(blocks):
        selection._object(block, ("block_id", "condition", "seed", "order", "taskset"), "matched block")
        identifier = selection._text(block["block_id"], "block ID")
        selection._text(block["condition"], "condition")
        selection._require(identifier not in seen and type(block["seed"]) is int
                           and type(block["order"]) is list and sorted(block["order"]) == sorted(ARMS),
                           "duplicate block or invalid expected order and seed")
        seen.add(identifier)
        eligible = [selection._text(task["id"], "eligible task ID") for task in block["taskset"]["tasks"]]
        slots = block["taskset"]["n_agents"]
        selection._require(eligible and len(eligible) == len(set(eligible)) and type(slots) is int
                           and 0 < slots <= len(eligible) and block["taskset"]["seed"] == block["seed"],
                           "invalid eligible work inventory or seed")
        rows = [_outcome(block, arm, tape["arms"][2 * block_index + ordinal], document, resources[arm])
                for ordinal, arm in enumerate(block["order"])]
        for row in rows:
            aggregate = resources[row["arm"]]
            _accumulate(aggregate["known_usage"], row["known_usage"])
            aggregate["unknown_usage_attempts"] += len(row["unknown_usage_attempts"])
            limits = document["arms"][row["arm"]]["budget"]
            aggregate["exceeded_caps"] = _breaches(aggregate["known_usage"], limits)
            selection._require(not aggregate["exceeded_caps"] or row["terminal"] != "completed",
                               "completed arm exceeded a cap across matched blocks")
        counts = {row["arm"]: row["distinct_passing"] for row in rows}
        delta = None if None in counts.values() else str(Fraction(counts["combined"] - counts["plain"], len(eligible)))
        pairs.append({"block_id": identifier, "eligible_count": len(eligible), "paired_delta": delta, "arms": rows})
    return {"evidence": "scripted_cpu_pair_audit", "scientific_acceptance": False,
            "trace_sha256": trace_sha256, "complete_pairs": sum(row["paired_delta"] is not None for row in pairs),
            "arm_resource_receipts": resources, "pairs": pairs}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for path in ("bundle", "manifest", "evidence_index", "trace"):
        parser.add_argument(path, type=Path)
    for pin in ("manifest", "evidence-index", "trace"):
        parser.add_argument(f"--{pin}-sha256", required=True)
    args = parser.parse_args()
    try:
        result = verify(**vars(args))
    except (KeyError, OSError, RecursionError, TypeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
