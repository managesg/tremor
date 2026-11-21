"""Reconcile independently pinned offline controller charges across both arms and common work."""

import argparse
import json
from pathlib import Path

from lab import controller_pair_audit as pair
from lab import controller_selection as selection

SCOPES = (*pair.ARMS, "common")
COMMON_ROLES = {"setup", "calibration", "training", "checkpoint", "independent_scoring", "cleanup"}


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


def verify(placement, charge_index, *, placement_sha256, charge_index_sha256):
    """Check allocation coverage against its supplied index, without admitting a run.

    Each index row is one independently attributable charge. A prior settlement
    pin is a claim from that index. This checker does not authenticate its origin
    or independently audit the prior resource ledger.
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
    return {
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("placement", type=Path)
    parser.add_argument("charge_index", type=Path)
    parser.add_argument("--placement-sha256", required=True)
    parser.add_argument("--charge-index-sha256", required=True)
    args = parser.parse_args()
    try:
        report = verify(**vars(args))
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(report, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
