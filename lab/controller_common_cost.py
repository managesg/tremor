"""Audit common controller charges against separately pinned role declarations."""

import argparse
import json
from pathlib import Path

from lab import controller_selection as selection
from lab import controller_shared_cost as shared


SCHEMA = "controller_common_charge_roles_v1"


def verify(placement, charge_index, roles, *, placement_sha256, charge_index_sha256, roles_sha256):
    """Keep common cost categories visible without allocating them to paired arms."""
    audited = shared.verify(placement, charge_index, placement_sha256=placement_sha256,
                            charge_index_sha256=charge_index_sha256)
    plan = selection._pinned_json(placement, placement_sha256)
    index = selection._pinned_json(charge_index, charge_index_sha256)
    catalog = selection._pinned_json(roles, roles_sha256)
    selection._object(catalog, ("schema", "roles"), "common charge role inventory")
    selection._require(catalog["schema"] == SCHEMA, "invalid common charge role schema")
    expected = selection._object(catalog["roles"], plan["charges_by_scope"]["common"], "common charge IDs")
    receipts = {row["id"]: row for row in index["receipts"] if row["scope"] == "common"}
    by_role = {}
    for identifier, role in expected.items():
        selection._require(type(role) is str and role in shared.COMMON_ROLES, "unknown common charge role")
        receipt = receipts.get(identifier)
        selection._require(receipt is None or receipt["role"] == role,
                           "common charge role differs from the independent declaration")
        by_role.setdefault(role, []).append(identifier)

    report = {}
    for role, ids in by_role.items():
        totals = shared._totals(receipts[key] for key in ids if key in receipts)
        missing = sorted(set(ids) - receipts.keys())
        complete = not missing and not totals["unsettled_charge_ids"]
        report[role] = {
            **totals,
            "declared_charge_ids": sorted(ids),
            "missing_charge_ids": missing,
            "coverage_complete": complete,
            "incremental_usage": totals["known_incremental_usage"] if complete else None,
        }
    return {
        "evidence": "offline_common_charge_role_audit",
        "roles_sha256": roles_sha256,
        "by_role": report,
        "placement": audited,
        "scientific_acceptance": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("placement", "charge_index", "roles"):
        parser.add_argument(name, type=Path)
        parser.add_argument(f"--{name.replace('_', '-')}-sha256", required=True)
    try:
        report = verify(**vars(parser.parse_args()))
    except (OSError, ValueError, TypeError, KeyError) as error:
        parser.error(str(error))
    print(json.dumps(report, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
