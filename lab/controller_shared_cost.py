"""Reconcile independently pinned offline controller charges across both arms and common work."""

import argparse
import json
from pathlib import Path

from lab import controller_pair_audit as pair
from lab import controller_selection as selection
from lab.replication_inventory import _capture_bytes, _json, _metadata

SCOPES = (*pair.ARMS, "common")
COMMON_ROLES = {"setup", "calibration", "training", "checkpoint", "independent_scoring", "cleanup"}
PRIOR_WITNESS_SCHEMA = "controller_prior_settlement_witness_v1"
PRIOR_SETTLEMENT_SCHEMA = "controller_prior_settlement_v1"


def _receipt(record):
    selection._object(record, ("id", "scope", "role", "prior_settlement_sha256", "usage"), "unit charge")
    identifier = selection._text(record["id"], "unit charge ID")
    scope, role = record["scope"], record["role"]
    selection._require(scope in SCOPES, "invalid charge scope")
    allowed_roles = COMMON_ROLES if scope == "common" else pair.ROLES
    selection._require(type(role) is str and role in allowed_roles, "charge role differs from its scope")
    prior = record["prior_settlement_sha256"]
    usage = record["usage"]
    if prior is not None:
        selection._digest(prior)
        selection._require(usage is not None, "a reused charge requires known settled usage")
    if usage is not None:
        pair._meter(usage)
    return identifier


def _totals(records):
    prior = dict.fromkeys(pair.USAGE, 0)
    incremental = prior.copy()
    unsettled = []
    for record in records:
        usage = record["usage"]
        if usage is None:
            unsettled.append(record["id"])
            continue
        subtotal = prior if record["prior_settlement_sha256"] is not None else incremental
        for field, amount in usage.items():
            subtotal[field] += amount
    return {
        "known_prior_usage": prior,
        "known_incremental_usage": incremental,
        "unsettled_charge_ids": sorted(unsettled),
    }


def _prior_observations(reference, charge_index_sha256, receipts):
    bundle, path, pin = reference
    root = Path(bundle).resolve(strict=True)
    selection._require(root.is_dir(), "prior settlement bundle must be a directory")
    witness = selection._object(_metadata(Path(path), pin), ("schema", "charge_index_sha256", "rows"),
                                "prior settlement witness")
    selection._require(witness["schema"] == PRIOR_WITNESS_SCHEMA
                       and witness["charge_index_sha256"] == charge_index_sha256
                       and type(witness["rows"]) is list, "invalid prior settlement witness or charge index pin")
    prior = {key: row for key, row in receipts.items() if row["prior_settlement_sha256"] is not None}
    seen_charges = set()
    by_parent = {}
    for row in witness["rows"]:
        selection._object(row, ("charge_id", "entry_id"), "prior settlement witness row")
        charge_id = selection._text(row["charge_id"], "prior charge ID")
        entry_id = selection._text(row["entry_id"], "prior entry ID")
        selection._require(charge_id in prior and charge_id not in seen_charges,
                           "unknown or duplicate prior settlement witness charge")
        seen_charges.add(charge_id)
        by_parent.setdefault(prior[charge_id]["prior_settlement_sha256"], []).append((charge_id, entry_id))
    selection._require(seen_charges == prior.keys(), "incomplete prior settlement witness coverage")

    seen_entries = set()
    for digest, links in by_parent.items():
        parent = selection._object(_json(_capture_bytes(root, "prior-settlement", digest)),
                                   ("schema", "ledger_id", "entries"), "prior settlement")
        selection._require(parent["schema"] == PRIOR_SETTLEMENT_SCHEMA and type(parent["entries"]) is list,
                           "invalid prior settlement schema or entries")
        ledger_id = selection._text(parent["ledger_id"], "prior ledger ID")
        entries = {}
        for entry in parent["entries"]:
            selection._object(entry, ("entry_id", "usage"), "prior settlement entry")
            entry_id = selection._text(entry["entry_id"], "prior entry ID")
            selection._require(entry_id not in entries, "duplicate entry in prior settlement")
            pair._meter(entry["usage"])
            entries[entry_id] = entry["usage"]
        for charge_id, entry_id in links:
            identity = ledger_id, entry_id
            selection._require(identity not in seen_entries, "prior settlement entry reused")
            selection._require(entry_id in entries and entries[entry_id] == prior[charge_id]["usage"],
                               "prior settlement entry is absent or its exact usage differs")
            seen_entries.add(identity)
    return {"witness_sha256": pin, "matched_charges": len(seen_charges), "native_authenticity_verified": False}


def verify(placement, charge_index, *, placement_sha256, charge_index_sha256, prior_settlement_witness=None):
    """Check allocation coverage against its supplied index, without admitting a run.

    With a prior settlement witness, each prior charge must match the exact usage
    of a distinct ledger entry in its pinned settlement. This verifies the retained
    evidence and leaves native ledger authenticity unverified.
    """
    plan = selection._pinned_json(placement, placement_sha256)
    index = selection._pinned_json(charge_index, charge_index_sha256)
    selection._object(plan, ("schema", "charge_index_sha256", "charges_by_scope"), "charge placement")
    selection._object(index, ("schema", "receipts"), "charge index")
    selection._require(plan["schema"] == "controller_cost_placement_v1"
                       and index["schema"] == "controller_unit_charges_v1"
                       and plan["charge_index_sha256"] == charge_index_sha256,
                       "placement must bind the independently pinned charge index")
    scope_plan = selection._object(plan["charges_by_scope"], SCOPES, "charge scopes")
    placements = {}
    for scope in SCOPES:
        identifiers = scope_plan[scope]
        selection._require(type(identifiers) is list, "charge scopes require lists of unit charge IDs")
        for identifier in identifiers:
            selection._text(identifier, "placed charge ID")
            selection._require(identifier not in placements, "unit charge placed more than once")
            placements[identifier] = scope
    selection._require(bool(placements), "charge placement must account for at least one unit")
    selection._require(type(index["receipts"]) is list, "charge index requires a receipt list")
    receipts = {}
    for record in index["receipts"]:
        identifier = _receipt(record)
        selection._require(identifier not in receipts, "duplicate unit charge receipt")
        selection._require(placements.get(identifier) == record["scope"], "unplaced or crossed unit charge")
        receipts[identifier] = record

    by_scope = {}
    for scope in SCOPES:
        expected = scope_plan[scope]
        totals = _totals(receipts[key] for key in expected if key in receipts)
        missing = sorted(set(expected) - receipts.keys())
        complete = not missing and not totals["unsettled_charge_ids"]
        by_scope[scope] = {
            **totals, "missing_charge_ids": missing, "coverage_complete": complete,
            "incremental_usage": totals["known_incremental_usage"] if complete else None,
        }
    coverage_complete = all(report["coverage_complete"] for report in by_scope.values())
    program_totals = _totals(receipts.values())
    report = {
        "evidence": "offline_charge_placement",
        "authorizes_execution": False,
        "placement_sha256": placement_sha256,
        "charge_index_sha256": charge_index_sha256,
        "coverage_complete": coverage_complete,
        "by_scope": by_scope,
        "known_prior_usage": program_totals["known_prior_usage"],
        "known_incremental_usage": program_totals["known_incremental_usage"],
        "incremental_usage": program_totals["known_incremental_usage"] if coverage_complete else None,
    }
    if prior_settlement_witness is not None:
        report["prior_settlement_observations"] = _prior_observations(prior_settlement_witness,
                                                                    charge_index_sha256, receipts)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("placement", type=Path)
    parser.add_argument("charge_index", type=Path)
    parser.add_argument("--placement-sha256", required=True)
    parser.add_argument("--charge-index-sha256", required=True)
    parser.add_argument("--prior-settlement-witness", nargs=3, metavar=("BUNDLE", "PATH", "SHA256"))
    args = parser.parse_args()
    try:
        report = verify(**vars(args))
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(report, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
