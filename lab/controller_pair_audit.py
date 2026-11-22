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
TRACE_V2 = "controller_paired_trace_v2"
ORDER_PLAN = "controller_order_plan_v1"
RELEASE_WITNESS = "controller_release_witness_v1"
RELEASE_PAYLOAD = ("agent", "task", "done")


def _scorer_ids():
    return {module.__name__.rsplit(".", 1)[1]: hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
            for module in (alloc, alloc2)}


def _release_events(witness, *, block_id, arm):
    selection._object(witness, ("block_id", "arm", "releases"), "release witness arm")
    selection._require(witness["block_id"] == block_id and witness["arm"] == arm,
                       "release witness does not match the scheduled arm")
    releases = witness["releases"]
    if releases is None:
        return None
    selection._require(type(releases) is list, "release witness requires an event list or null")
    events = {}
    for event in releases:
        selection._object(event, ("sequence", *RELEASE_PAYLOAD, "executed"), "release event")
        sequence = event["sequence"]
        selection._require(type(sequence) is int and sequence >= 0 and sequence not in events,
                           "invalid or duplicate release sequence")
        selection._require(type(event["done"]) is bool and type(event["executed"]) is bool,
                           "release outcome flags must be boolean")
        events[sequence] = event
    return events


def _completion_safeguard(status, score=None):
    done = score["done_releases"] if score is not None else None
    false = score["false_done"] if score is not None else None
    return {"status": status, "done_releases": done, "false_completions": false,
            "false_completion_rate": str(Fraction(false, done)) if done else None}


def _outcome(block, arm, row, manifest, prior, witness=None):
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
    attempt_fields = ("sequence", "role", "status", "usage", "work")
    releases = None
    marked = set()
    cleanup_started = False
    taskset = block["taskset"]
    if witness is not None:
        attempt_fields += ("release",)
        releases = _release_events(witness, block_id=block["block_id"], arm=arm)
        eligible = {task["id"] for task in taskset["tasks"]}
    for ordinal, attempt in enumerate(row["attempts"]):
        selection._object(attempt, attempt_fields, "attempt")
        selection._require(type(attempt["sequence"]) is int and attempt["sequence"] == ordinal
                           and attempt["role"] in ROLES and attempt["status"] in ("completed", "failed", "refused"),
                           "invalid attempt sequence, role or status")
        is_cleanup = attempt["role"] == "cleanup"
        selection._require(is_cleanup or not cleanup_started, "only cleanup can follow the first cleanup attempt")
        cleanup_started = cleanup_started or is_cleanup
        selection._require(is_cleanup or not _breaches(cumulative, settings["budget"]),
                           "only cleanup can follow a recorded cap breach")
        selection._require(is_cleanup or not (unknown or prior["unknown_usage_attempts"]),
                           "only cleanup can follow unresolved usage")
        usage = attempt["usage"]
        if usage is None:
            unknown.append(ordinal)
        else:
            charged = _meter(usage)
            # A call requires an available slot at dispatch. Other measured costs may overrun on return.
            selection._require(is_cleanup or cumulative["calls"] + charged["calls"] <= settings["budget"]["calls"],
                               "recorded call after the dispatch cap was exhausted")
            _accumulate(totals, charged)
            _accumulate(cumulative, charged)
        action = attempt["work"]
        if action is not None:
            selection._object(action, ("agent", "task", "name", "answer"), "worker proposal")
            selection._require(attempt["role"] == "worker", "non-worker role cannot submit work")
            work.append({**action, "action": "work", "rejected": attempt["status"] != "completed"})
        release = attempt.get("release")
        if release is not None:
            selection._object(release, RELEASE_PAYLOAD, "release attempt")
            selection._require(attempt["role"] == "worker" and action is None, "invalid release attempt")
            selection._text(release["agent"], "release agent")
            selection._text(release["task"], "release task")
            selection._require(type(release["done"]) is bool, "release done flag must be boolean")
            executed = attempt["status"] == "completed"
            selection._require(not executed or release["task"] in eligible,
                               "executed release named a task outside the frozen inventory")
            marked.add(ordinal)
            if releases is not None:
                selection._require(ordinal in releases, "marked release is absent from the witness")
                event = releases[ordinal]
                selection._require(executed == event["executed"],
                                   "witness and attempt disagree on release execution")
                selection._require(all(release[key] == event[key] for key in RELEASE_PAYLOAD),
                                   "witness and attempt disagree on release payload")
                work.append({**release, "action": "release", "rejected": not executed})
    if releases is not None:
        selection._require(marked == releases.keys(), "witness release lacks a marked attempt")
    overruns = _breaches(totals, settings["budget"])
    base = {"arm": arm, "terminal": terminal, "attempts": len(row["attempts"]),
            "known_usage": totals, "unknown_usage_attempts": unknown, "exceeded_caps": overruns}
    if terminal != "completed":
        if witness is not None:
            base["completion_safeguard"] = _completion_safeguard("unavailable_noncompleted_arm")
        return {**base, "distinct_passing": None}
    selection._require(not unknown and not overruns, "completed arm has unaccounted usage or exceeded a cap")
    selection._require(any(attempt["role"] == "worker" and attempt["status"] == "completed"
                           for attempt in row["attempts"]),
                       "completed arm lacks a completed worker observation")
    primary, score = alloc.score(work, taskset), alloc2.score(work, taskset)
    selection._require(score["valid"] and not alloc2.compare(primary, score),
                       "completed arm failed independent work scoring")
    selection._require(primary["unknown_task_events"] == 0,
                       "completed arm submitted work outside the frozen task inventory")
    if witness is not None:
        base["completion_safeguard"] = (_completion_safeguard("observed", score) if releases is not None
                                        else _completion_safeguard("unavailable_missing_witness"))
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



def _order_plan(witness, blocks, manifest_pin, task_pin):
    path, pin = witness
    plan = selection._pinned_json(path, pin)
    selection._object(plan, ("schema", "manifest_sha256", "task_inventory_sha256", "strata"), "order plan")
    selection._require(plan["schema"] == ORDER_PLAN and plan["manifest_sha256"] == manifest_pin
                       and plan["task_inventory_sha256"] == task_pin, "order plan does not bind the frozen schedule")
    expected = {}
    for block in blocks:
        block_id = selection._text(block["block_id"], "block ID")
        order = block["order"]
        selection._require(block_id not in expected and type(order) is list and sorted(order) == sorted(ARMS),
                           "invalid block or arm order in frozen schedule")
        expected[block_id] = (block["condition"], order[0])
    strata = plan["strata"]
    selection._require(type(strata) is list and strata, "expected nonempty order strata")
    matched, reports = set(), {}
    for stratum in strata:
        selection._object(stratum, ("id", "condition", "block_ids", "combined_first_min", "combined_first_max"),
                          "order stratum")
        label = selection._text(stratum["id"], "stratum ID")
        condition = selection._text(stratum["condition"], "stratum condition")
        members = stratum["block_ids"]
        selection._require(label not in reports and type(members) is list and members,
                           "repeated or empty order stratum")
        minimum, maximum = stratum["combined_first_min"], stratum["combined_first_max"]
        selection._require(type(minimum) is int and type(maximum) is int and 0 <= minimum <= maximum <= len(members),
                           "invalid first-arm count bounds")
        counts = dict.fromkeys(ARMS, 0)
        for member in members:
            member = selection._text(member, "stratum block ID")
            selection._require(member in expected and member not in matched,
                               "order strata must partition the frozen schedule")
            actual_condition, first_arm = expected[member]
            selection._require(actual_condition == condition, "order stratum condition differs from frozen block")
            counts[first_arm] += 1
            matched.add(member)
        selection._require(minimum <= counts["combined"] <= maximum, "first-arm count outside frozen bounds")
        reports[label] = {"condition": condition, "block_ids": members, "scheduled_first": counts,
                          "combined_first_bounds": [minimum, maximum]}
    selection._require(matched == expected.keys(), "order strata must partition the frozen schedule")
    return {"order_plan_sha256": pin, "planned_order_bounds_verified": True, "runtime_order_verified": False,
            "strata": reports}


def verify(bundle, manifest, evidence_index, trace, *, manifest_sha256, evidence_index_sha256, trace_sha256,
           release_witness=None, policy_witness=None, order_witness=None):
    """Replay paired outcomes and optionally check an independently pinned schedule order plan."""
    selected = selection.verify(bundle, manifest, evidence_index, manifest_sha256=manifest_sha256,
                                evidence_index_sha256=evidence_index_sha256, policy_witness=policy_witness)
    document = selection._pinned_json(manifest, selected["manifest_sha256"])
    tape = selection._pinned_json(trace, trace_sha256)
    tape_fields = ("evidence", "manifest_sha256", "input_files", "arms")
    versioned = type(tape) is dict and "schema" in tape
    selection._object(tape, (*tape_fields, "schema") if versioned else tape_fields, "paired trace")
    witness_arms = None
    if versioned:
        selection._require(tape["schema"] == TRACE_V2, "unknown paired trace schema")
        selection._require(release_witness is not None, "V2 trace requires an independent release witness pin")
        witness_path, witness_pin = release_witness
        witness = selection._pinned_json(witness_path, witness_pin)
        selection._object(witness, ("schema", "trace_sha256", "arms"), "release witness")
        selection._require(witness["schema"] == RELEASE_WITNESS and witness["trace_sha256"] == trace_sha256
                           and type(witness["arms"]) is list, "release witness must bind the pinned V2 trace")
        witness_arms = witness["arms"]
    else:
        selection._require(release_witness is None, "a release witness requires a V2 trace")
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
    order_report = (_order_plan(order_witness, blocks, manifest_sha256, tasks["sha256"])
                    if order_witness is not None else None)
    selection._require(len(tape["arms"]) == 2 * len(blocks), "each declared arm needs a terminal trace")
    if witness_arms is not None:
        selection._require(len(witness_arms) == len(tape["arms"]), "each V2 arm needs release witness coverage status")
        for arm_witness in witness_arms:
            selection._require(type(arm_witness) is dict, "expected one release witness record per arm")
    resources = {arm: {"known_usage": dict.fromkeys(selection.BUDGET, 0),
                       "unknown_usage_attempts": 0, "exceeded_caps": []} for arm in ARMS}
    seen, assignments, pairs = set(), set(), []
    prompt_coverage = None
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
        tasks = block["taskset"]["tasks"]
        has_prompts = any("check" in task for task in tasks)
        selection._require(not has_prompts or all(type(task.get("check")) is str and task["check"]
                                                  for task in tasks),
                           "mixed or invalid assignment prompt coverage")
        if prompt_coverage is None:
            prompt_coverage = has_prompts
        selection._require(has_prompts is prompt_coverage, "assignment prompt coverage differs across blocks")
        if has_prompts:
            # Reference answers are scored under the inventory pin, not part of the delivered prompts.
            canonical_content = tuple(sorted(task["check"] for task in tasks))
        else:
            canonical_content = tuple(sorted(
                json.dumps((task["id"], task["expect"]), sort_keys=True, separators=(",", ":"), allow_nan=False)
                for task in tasks
            ))
        assignment = (block["condition"], block["seed"], slots, canonical_content)
        selection._require(assignment not in assignments, "duplicate experimental task assignment")
        assignments.add(assignment)
        rows = []
        for ordinal, arm in enumerate(block["order"], start=2 * block_index):
            arm_witness = witness_arms[ordinal] if witness_arms is not None else None
            rows.append(_outcome(block, arm, tape["arms"][ordinal], document, resources[arm], arm_witness))
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
    result = {"evidence": "scripted_cpu_pair_audit", "scientific_acceptance": False,
              "trace_sha256": trace_sha256, "complete_pairs": sum(row["paired_delta"] is not None for row in pairs),
              "arm_resource_receipts": resources, "pairs": pairs}
    if witness_arms is not None:
        result["release_witness_sha256"] = witness_pin
    if policy_witness is not None:
        result["policy_configuration"] = selected["policy_configuration"]
    if order_report is not None:
        result["scheduled_order"] = order_report
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for path in ("bundle", "manifest", "evidence_index", "trace"):
        parser.add_argument(path, type=Path)
    for pin in ("manifest", "evidence-index", "trace"):
        parser.add_argument(f"--{pin}-sha256", required=True)
    parser.add_argument("--release-witness", nargs=2, metavar=("PATH", "SHA256"))
    parser.add_argument("--policy-witness", nargs=2, metavar=("PATH", "SHA256"))
    parser.add_argument("--order-witness", nargs=2, metavar=("PATH", "SHA256"))
    args = parser.parse_args()
    try:
        result = verify(**vars(args))
    except (KeyError, OSError, RecursionError, TypeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
