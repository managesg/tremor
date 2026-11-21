"""Check public Grover releases and consumed receipts against a pinned observer tape."""

import argparse
from hashlib import sha256
from hmac import compare_digest
import json
from pathlib import Path

from . import custody, topology_audit


SCOPE = "grover_public_release_scope_v1"
WITNESS = "grover_public_release_observation_v1"
TRACE_LIMIT = 4 * 1024 * 1024
SCOPE_FIELDS = ("schema", "run_id", "block_id", "trace_sha256", "regime", "seed", "mode", "access")


def _pinned(path, expected, size):
    raw = custody._read(path, size)
    custody._require(compare_digest(sha256(raw).hexdigest(), custody._pin(expected)), "release input digest mismatch")
    return raw


def _select_arm(trace, scope):
    custody._object(scope, SCOPE_FIELDS, "release scope")
    custody._require(scope["schema"] == SCOPE, "invalid release scope schema")
    custody._identifier(scope["run_id"])
    custody._identifier(scope["block_id"])
    custody._require(type(scope["seed"]) is int and scope["mode"] in topology_audit.MODES
                     and scope["access"] in topology_audit.ACCESS, "invalid public release case")
    case = next((row for row in trace["cases"] if (row["regime"], row["development_seed"])
                 == (scope["regime"], scope["seed"])), None)
    custody._require(case is not None, "release scope does not select a public case")
    return next(row for row in case["arms"] if (row["mode"], row["evidence_access"])
                == (scope["mode"], scope["access"]))


def project_events(arm, scope_sha256):
    """Reconstruct the scripted next-round release contract from an audited public arm."""
    trace = arm["trace"]
    receipts, events = {}, []
    fallback_uses = stage_hit_uses = reads = work = 0
    for row in trace:
        kind, round_id, index = (row[key] for key in ("kind", "round", "event"))
        common = {"scope_sha256": scope_sha256, "event": index, "round": round_id}
        if kind == "verify" and row["accepted"]:
            proposal = trace[row["submission"]]
            task = proposal["task"]
            status = "shard" if task.startswith("shard/") else "no_hit" if proposal["answer"] is None else "hit"
            receipt = {
                **common, "kind": "release", "task": task, "owner": proposal["actor"], "status": status,
                "available_round": round_id + 1, "submission": row["submission"], "answer": proposal["answer"],
                "input_receipt_ids": [receipts[pointer]["receipt_id"] for pointer in proposal["inputs"]],
            }
            receipt["receipt_id"] = sha256(custody.canonical(receipt)).hexdigest()
            receipts[index] = receipt
            events.append(receipt)
        elif kind in ("read", "work"):
            selected = [receipts[pointer] for pointer in row["visible" if kind == "read" else "inputs"]]
            custody._require(all(item["available_round"] <= round_id and (
                arm["evidence_access"] == "shared" or item["owner"] == row["actor"]
            ) for item in selected), "public trace contains a premature or invisible release")
            observation = {
                **common, "kind": kind, "worker": row["actor"],
                "receipt_ids": [item["receipt_id"] for item in selected],
            }
            if kind == "work":
                work += 1
                observation["task"] = row["task"]
                fallback_uses += sum(item["status"] == "no_hit" for item in selected)
                stage_hit_uses += sum(item["status"] == "hit" for item in selected)
            else:
                reads += 1
            events.append(observation)
    return events, {
        "observed_read_slots": reads,
        "observed_work_slots": work,
        "released_shards": sum(row["status"] == "shard" for row in receipts.values()),
        "released_hits": sum(row["status"] == "hit" for row in receipts.values()),
        "released_no_hits": sum(row["status"] == "no_hit" for row in receipts.values()),
        "fallback_uses": fallback_uses,
        "predecessor_hit_uses": stage_hit_uses,
    }


def verify(trace, scope, witness, *, scope_sha256, witness_sha256):
    """Check the eager public schedule and separate observer bytes without asserting custody."""
    scope_row = custody._canonical_document(_pinned(scope, scope_sha256, 16 * 1024))
    snapshot = _pinned(trace, scope_row["trace_sha256"], TRACE_LIMIT)
    topology_audit.audit(snapshot, expected_sha256=scope_row["trace_sha256"])
    arm = _select_arm(json.loads(snapshot), scope_row)
    supplied = custody._canonical_document(_pinned(witness, witness_sha256, custody.LIMIT))
    custody._object(supplied, ("schema", "scope_sha256", "events"), "release witness")
    custody._require(supplied["schema"] == WITNESS and supplied["scope_sha256"] == scope_sha256,
                     "observer tape is from a different scheduled scope")
    expected, counts = project_events(arm, scope_sha256)
    events = supplied["events"]
    custody._require(type(events) is list and len(events) == len(expected), "observer tape misses scheduled events")
    for wanted, found in zip(expected, events, strict=True):
        custody._require(custody.canonical(wanted) == custody.canonical(found),
                         f"observed {wanted['kind']} does not match scheduled event {wanted['event']}")
    stopped = arm["budget_stopped"]
    return {
        "evidence": "public_grover_release_rehearsal",
        "coverage": "budget_stopped_prefix" if stopped else "complete_schedule",
        "budget_stopped": stopped,
        "complete_schedule_fallback_uses": None if stopped else counts["fallback_uses"],
        "scope_sha256": scope_sha256,
        "witness_sha256": witness_sha256,
        **counts,
        "verified_stage_count": arm["stage_utility"],
        "observer_authenticated": False,
        "native_delivery_verified": False,
        "scientific_result": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("trace", "scope", "witness"):
        parser.add_argument(field, type=Path)
    for pin in ("scope-sha256", "witness-sha256"):
        parser.add_argument(f"--{pin}", required=True)
    try:
        report = verify(**vars(parser.parse_args()))
    except (IndexError, KeyError, OSError, RecursionError, TypeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
