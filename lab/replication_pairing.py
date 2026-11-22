"""Verify one prospective L1–L3 holdout pairing from independently pinned manifests."""

import argparse
import json
from pathlib import Path
import re

from lab.replication_inventory import ROLES, _hex, _metadata, _object, _require


LINES = ("L1", "L2", "L3")
SPLITS = ("development", "reference_calibration", "second_family_calibration", "holdout")
IDENTITY_FIELDS = ("task_id", "replicate_id", "block_id")
SCHEDULE_V1 = "replication_holdout_schedule_v1"
SCHEDULE_V2 = "replication_holdout_schedule_v2"
MATCH_FIELDS = (
    "task_input_sha256", "task_seed_sha256", "initial_state_sha256",
    "eligible_actions_sha256", "perturbation_sha256", "observability_sha256",
    "scoring_opportunities_sha256", "scorer_sha256", "hidden_truth_sha256",
)


def _identifier(value):
    _require(type(value) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]*", value),
             "expected a canonical ASCII identity")
    return value


def _splits(document):
    _object(document, ("schema", "members"), "split inventory")
    _require(document["schema"] == "replication_split_inventory_v1", "unknown split inventory schema")
    members = document["members"]
    _require(type(members) is list and members, "expected split inventory members")
    task_splits, group_splits = {}, {}
    for member in members:
        _object(member, ("task_id", "group_id", "split"), "split member")
        task, group = (_identifier(member[key]) for key in ("task_id", "group_id"))
        split = member["split"]
        _require(split in SPLITS, "unknown split assignment")
        _require(task not in task_splits, "duplicate task in split inventory")
        _require(group_splits.setdefault(group, split) == split, "canonical group crosses split boundaries")
        task_splits[task] = split
    return task_splits


def _inventory_bindings(inventory):
    path, pin = inventory
    document = _metadata(Path(path), pin)
    _require(document.get("evidence") == "structural_snapshot_inventory_only"
             and document.get("inventory_verified") is True
             and document.get("loader_verified") is False
             and document.get("scientific_acceptance") is False, "expected a structural inventory receipt")
    snapshots = _object(document.get("snapshots"), ROLES, "inventory snapshots")
    bindings = {}
    for role, row in snapshots.items():
        _require(type(row) is dict, "invalid inventory snapshot")
        named = _object(row.get("named_tensor_payloads"), ("count", "sha256"), "named tensor inventory")
        _require(type(named["count"]) is int and named["count"] > 0, "invalid named tensor count")
        bindings[role] = {
            "inventory_sha256": pin,
            "model_manifest_sha256": _hex(row.get("manifest_sha256"), 64),
            "named_tensor_sha256": _hex(named["sha256"], 64),
        }
    for key in ("model_manifest_sha256", "named_tensor_sha256"):
        _require(bindings["reference"][key] != bindings["transfer"][key],
                 "reference and transfer inventory identities must differ")
    return bindings


def _schedule(document, *, role, line, task_splits, snapshot=None):
    fields = ("schema", "role", "line", "rows")
    if snapshot is None:
        _require(document.get("schema") == SCHEDULE_V1, "snapshot-bound schedule requires pinned inventory")
        _object(document, fields, "holdout schedule")
    else:
        _require(document.get("schema") == SCHEDULE_V2, "pinned inventory requires snapshot-bound schedules")
        _object(document, (*fields, "snapshot"), "holdout schedule")
        _require(document["snapshot"] == snapshot, f"{role} schedule snapshot does not match pinned inventory")
    _require(document["role"] == role and document["line"] == line, "holdout schedule role or line mismatch")
    rows = document["rows"]
    _require(type(rows) is list and rows, "expected scheduled holdout rows")
    result, assignments = {}, set()
    for row in rows:
        _object(row, (*IDENTITY_FIELDS, *MATCH_FIELDS), "holdout row")
        task, replicate, block = (_identifier(row[key]) for key in IDENTITY_FIELDS)
        _require(task_splits.get(task) == "holdout", "scheduled task is absent from the pinned holdout")
        key = task, replicate
        _require(key not in result, "duplicate task and replicate in holdout schedule")
        context = tuple(_hex(row[field], 64) for field in MATCH_FIELDS)
        assignment = task, context
        _require(assignment not in assignments, "duplicate holdout assignment under distinct replicate IDs")
        result[key] = (block, *context)
        assignments.add(assignment)
    return result


def verify(*, line, splits, unchanged, recalibrated, reference=None, inventory=None):
    """Compare pinned metadata. Each input is a (path, SHA-256) pair.

    Split group IDs represent the custodian's reviewed canonical groupings.
    All IDs are opaque ASCII names. Each replicate of a task has a distinct
    pinned assignment, such as a different task seed map.
    The caller supplies each pin independently from its reviewed freeze record.
    A standalone reference result does not substitute for a reference holdout schedule.
    An optional structural inventory binds all present v2 schedules to exact
    snapshot receipts. It supplies declared identity and no runtime attestation.
    """
    _require(line in LINES, "expected one of L1, L2 or L3")
    schedules = {"unchanged": unchanged, "recalibrated": recalibrated}
    if reference is not None:
        schedules["reference"] = reference
    bindings = _inventory_bindings(inventory) if inventory is not None else None
    split_path, split_pin = splits
    task_splits = _splits(_metadata(Path(split_path), split_pin))
    observed, pins, snapshots = {}, {"splits": split_pin}, {}
    for role, (path, pin) in schedules.items():
        if bindings is not None:
            snapshots[role] = bindings["reference" if role == "reference" else "transfer"]
        observed[role] = _schedule(_metadata(Path(path), pin), role=role, line=line, task_splits=task_splits,
                                   snapshot=snapshots.get(role))
        pins[role] = pin

    baseline = observed["unchanged"]
    for role, schedule in observed.items():
        if role == "unchanged":
            continue
        _require(schedule.keys() == baseline.keys(), f"{role} holdout task or replicate set differs")
        _require(schedule == baseline, f"{role} holdout block or match context differs")

    result = {
        "evidence": "prospective_holdout_pairing_only",
        "line": line,
        "manifest_sha256": pins,
        "paired_task_replicates": len(baseline),
        "cross_family_pairing": "verified" if reference is not None else "withheld_missing_reference_holdout",
        "scientific_acceptance": False,
    }
    if bindings is not None:
        result["scheduled_snapshot_binding"] = snapshots
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--line", choices=LINES, required=True)
    for name in ("splits", "unchanged", "recalibrated", "reference"):
        parser.add_argument(f"--{name}", nargs=2, metavar=("PATH", "SHA256"), required=name != "reference")
    parser.add_argument("--inventory", nargs=2, metavar=("PATH", "SHA256"),
                        help="independently pinned structural inventory for snapshot-bound schedules")
    try:
        result = verify(**vars(parser.parse_args()))
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
