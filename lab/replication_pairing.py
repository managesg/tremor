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
PORTABILITY = "replication_policy_portability_v1"
PORTABILITY_ARMS = ("technique", "comparator")
MECHANICS = ("chat_template", "token_accounting", "normalization")
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


def _identities(values, label):
    _require(type(values) is list, f"expected a list of {label}")
    unique = {_identifier(value) for value in values}
    _require(len(unique) == len(values), f"duplicate {label}")
    return unique


def _policy(config):
    _object(config, ("mechanical", "arms"), "replication policy")
    mechanical = _object(config["mechanical"], MECHANICS, "mechanical policy")
    for pin in mechanical.values():
        _hex(pin, 64)
    arms = _object(config["arms"], PORTABILITY_ARMS, "policy arms")
    for arm in arms.values():
        _object(arm, ("method_sha256", "parameters"), "policy arm")
        _hex(arm["method_sha256"], 64)
        _require(type(arm["parameters"]) is dict, "expected named frozen parameters")
        for key, pin in arm["parameters"].items():
            _identifier(key)
            _hex(pin, 64)
    return mechanical, arms


def _portability(witness, *, line, pins, task_splits):
    path, pin = witness
    document = _metadata(Path(path), pin)
    _object(document, ("schema", "line", "schedule_pins", "roles",
                       "allowed_mechanical_changes", "calibration"), "policy portability witness")
    _require(document["schema"] == PORTABILITY and document["line"] == line
             and document["schedule_pins"] == pins, "portability witness does not bind the paired schedules")
    roles = _object(document["roles"], ("reference", "unchanged", "recalibrated"), "policy roles")
    ref_mechanics, ref_arms = _policy(roles["reference"])
    transfer_mechanics, transfer_arms = _policy(roles["unchanged"])
    recalibrated_mechanics, recalibrated_arms = _policy(roles["recalibrated"])
    _require(ref_arms == transfer_arms, "unchanged transfer changed a frozen arm")
    _require(transfer_mechanics == recalibrated_mechanics, "transfer runtime mechanics differ")
    allowed_mechanics = _identities(document["allowed_mechanical_changes"], "mechanical change names")
    _require(allowed_mechanics <= set(MECHANICS), "unknown mechanical change")
    changes = {key for key in MECHANICS if ref_mechanics[key] != transfer_mechanics[key]}
    _require(changes <= allowed_mechanics, "undeclared mechanical change")

    fit = _object(document["calibration"], ("task_ids", "allowed_parameters", "procedure_sha256",
                                           "allowance_sha256"), "calibration plan")
    tasks = _identities(fit["task_ids"], "calibration task IDs")
    _require(tasks and all(task_splits.get(task) == "second_family_calibration" for task in tasks),
             "calibration tasks must belong to the second-family calibration split")
    _hex(fit["procedure_sha256"], 64)
    _hex(fit["allowance_sha256"], 64)
    allowed = _object(fit["allowed_parameters"], PORTABILITY_ARMS, "recalibration parameters")
    changed = {}
    for arm in PORTABILITY_ARMS:
        old, new = transfer_arms[arm], recalibrated_arms[arm]
        _require(old["method_sha256"] == new["method_sha256"], "calibration changed a frozen method")
        parameters = old["parameters"]
        _require(parameters.keys() == new["parameters"].keys(), "calibration changed the frozen parameter roster")
        eligible = _identities(allowed[arm], "allowed parameter names")
        _require(eligible <= parameters.keys(), "calibration allowance names an unknown parameter")
        differences = {key for key in parameters if parameters[key] != new["parameters"][key]}
        _require(differences <= eligible, "calibration changed an unauthorized parameter")
        changed[arm] = sorted(differences)
    return {"evidence": "pinned_policy_declarations_only", "witness_sha256": pin,
            "mechanical_changes": sorted(changes), "recalibrated_parameter_changes": changed,
            "declared_second_family_calibration_tasks": len(tasks),
            "runtime_policy_verified": False, "calibration_execution_verified": False}


def verify(*, line, splits, unchanged, recalibrated, reference=None, inventory=None, policy_witness=None):
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
    if policy_witness is not None:
        result["policy_portability"] = _portability(policy_witness, line=line, pins=pins, task_splits=task_splits)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--line", choices=LINES, required=True)
    for name in ("splits", "unchanged", "recalibrated", "reference"):
        parser.add_argument(f"--{name}", nargs=2, metavar=("PATH", "SHA256"), required=name != "reference")
    parser.add_argument("--inventory", nargs=2, metavar=("PATH", "SHA256"),
                        help="independently pinned structural inventory for snapshot-bound schedules")
    parser.add_argument("--policy-witness", nargs=2, metavar=("PATH", "SHA256"),
                        help="independently pinned frozen policy and calibration scope")
    try:
        result = verify(**vars(parser.parse_args()))
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
