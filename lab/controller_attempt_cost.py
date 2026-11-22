"""Reconcile verified controller attempts with independently pinned charges."""

from pathlib import Path

from lab import controller_common_cost as common
from lab import controller_pair_audit as pairs
from lab import controller_selection as selection


WITNESS_SCHEMA = "controller_attempt_charge_witness_v1"
ASSIGNMENT_SCHEMA = "public_controller_attempt_charges_v1"


def reconcile(trace, trace_pin, witness):
    """Join a replayed trace to cost artifacts. The caller first verifies the pair."""
    witness_path, witness_pin = witness
    root = Path(witness_path).resolve(strict=True).parent
    document = selection._pinned_json(witness_path, witness_pin)
    names = ("assignment", "placement", "charge_index", "common_roles")
    selection._object(document, ("schema", "trace_sha256", *names), "attempt charge witness")
    selection._require(document["schema"] == WITNESS_SCHEMA and document["trace_sha256"] == trace_pin,
                       "charge witness refers to a different trace")
    paths = {name: selection._reference(root, document[name]) for name in names}
    pins = {name: document[name]["sha256"] for name in names}
    totals = common.verify(paths["placement"], paths["charge_index"], paths["common_roles"],
                           placement_sha256=pins["placement"], charge_index_sha256=pins["charge_index"],
                           roles_sha256=pins["common_roles"])
    assignment = selection._pinned_json(paths["assignment"], pins["assignment"])
    selection._object(assignment, ("schema", "trace_sha256", "rows"), "attempt charge assignment")
    selection._require(assignment["schema"] == ASSIGNMENT_SCHEMA and assignment["trace_sha256"] == trace_pin
                       and type(assignment["rows"]) is list, "invalid assignment schema or trace")
    tape = selection._pinned_json(trace, trace_pin)
    attempts = {(row["block_id"], row["arm"], attempt["sequence"]): attempt
                for row in tape["arms"] for attempt in row["attempts"]}
    index = selection._pinned_json(paths["charge_index"], pins["charge_index"])
    receipts = {row["id"]: row for row in index["receipts"]}
    placement = selection._pinned_json(paths["placement"], pins["placement"])["charges_by_scope"]
    arm_charges = {identifier for role in pairs.ARMS for identifier in placement[role]}
    seen_attempts, seen_charges, unknown = set(), set(), []
    for link in assignment["rows"]:
        selection._object(link, ("block_id", "arm", "sequence", "charge_id"), "attempt charge row")
        block = selection._text(link["block_id"], "block ID")
        arm = selection._text(link["arm"], "arm")
        sequence = link["sequence"]
        selection._require(type(sequence) is int and sequence >= 0, "invalid attempt sequence")
        key = block, arm, sequence
        charge = selection._text(link["charge_id"], "charge ID")
        selection._require(key in attempts and key not in seen_attempts
                           and charge in receipts and charge not in seen_charges,
                           "absent or duplicate attempt or charge")
        receipt, attempt = receipts[charge], attempts[key]
        selection._require(receipt["scope"] == arm and receipt["role"] == attempt["role"]
                           and receipt["prior_settlement_sha256"] is None and receipt["usage"] == attempt["usage"],
                           "attempt charge scope, role, settlement or exact usage differs")
        seen_attempts.add(key)
        seen_charges.add(charge)
        if receipt["usage"] is None:
            unknown.append(charge)
    selection._require(seen_attempts == attempts.keys() and seen_charges == arm_charges,
                       "incomplete attempt mapping or extra arm charge")
    return {"evidence": "scripted_controller_attempt_charge_join", "trace_sha256": trace_pin,
            "charge_witness_sha256": witness_pin, "matched_attempts": len(seen_attempts),
            "unknown_attempt_charge_ids": sorted(unknown), "common_and_arm_costs": totals,
            "native_metering_verified": False}
