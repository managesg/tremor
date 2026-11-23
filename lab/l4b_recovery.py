"""Audit declared L4-B recovery observations without estimating a scientific effect."""

import argparse
from collections import Counter
import json
from pathlib import Path
from unicodedata import normalize

from lab import adapter_lineage, l4b_recovery_observation, l4e_public_parity


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _fields(value, fields):
    _require(type(value) is dict and value.keys() == set(fields.split()), "unexpected L4-B observation fields")


def _identifier(value):
    _require(type(value) is str and bool(value) and value == value.strip() and value == normalize("NFC", value),
             "L4-B chain IDs must be nonblank and canonical")
    return value


def verify(design, observations, *, design_sha256, observations_sha256):
    design = adapter_lineage._json(Path(design), design_sha256)
    _fields(design, "schema scope clock endpoint horizon hold scorer_sha256 chains")
    _require(design["schema"] == "l4b_recovery_design_v1" and design["scope"] == "scripted_development"
             and design["clock"] == "elapsed_nights_from_frozen_shock" and design["endpoint"] == "confirmed_hold",
             "unsupported development recovery scope, clock or endpoint")
    scorer = adapter_lineage._digest(design["scorer_sha256"], 64)
    _require(type(design["chains"]) is list and bool(design["chains"]), "recovery design needs scheduled chains")
    scheduled = [_identifier(identifier) for identifier in design["chains"]]
    _require(len(set(scheduled)) == len(scheduled), "duplicate planned recovery chain")

    document = adapter_lineage._json(Path(observations), observations_sha256)
    _fields(document, "schema design_sha256 scorer_sha256 chains")
    _require(document["schema"] == "l4b_recovery_observations_v1" and document["design_sha256"] == design_sha256
             and document["scorer_sha256"] == scorer, "recovery observations cross the exact design or scorer pin")
    _require(type(document["chains"]) is list, "recovery observations require explicit scheduled-chain records")
    records = {}
    for chain in document["chains"]:
        _fields(chain, "chain_id terminal samples")
        identifier = _identifier(chain["chain_id"])
        _require(identifier not in records, "duplicate recovery observation chain")
        records[identifier] = chain
    _require(records.keys() == set(scheduled), "recovery observations differ from the scheduled inventory")
    rows = []
    for identifier in scheduled:
        chain = records[identifier]
        result = l4b_recovery_observation.classify(
            chain["samples"], horizon=design["horizon"], hold=design["hold"], terminal=chain["terminal"],
        )
        rows.append({"chain_id": identifier, **result})
    counts = Counter(row["status"] for row in rows)
    return {
        "status": "verified_scripted_observations", "design_sha256": design_sha256,
        "observations_sha256": observations_sha256, "scorer_sha256": scorer, "chains": rows,
        "disposition_counts": dict(counts), "restricted_mean_recovery": None, "scientific_ratio": None,
        "native_endpoint_frozen": False, "authorizes_execution": False,
    }


def historical_preview(archive, *, archive_sha256):
    _, chains, _ = l4e_public_parity._projection(archive, archive_sha256)
    return {
        "status": "no_qualified_recovery_observations", "archive_sha256": archive_sha256,
        "archived_chains": len(chains), "archived_nights": sum(row["nights"] for row in chains),
        "archived_withdrawals": sum(row["withdrawn_unsupported_notes"] for row in chains),
        "archived_corrections": sum(row["correction_events"] for row in chains),
        "qualified_event_time_records": 0, "restricted_mean_recovery": None, "scientific_ratio": None,
        "native_endpoint_frozen": False, "authorizes_execution": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="mode", required=True)
    observed = commands.add_parser("verify")
    observed.add_argument("design", type=Path)
    observed.add_argument("observations", type=Path)
    observed.add_argument("--design-sha256", required=True)
    observed.add_argument("--observations-sha256", required=True)
    archived = commands.add_parser("historical")
    archived.add_argument("archive", type=Path)
    archived.add_argument("--archive-sha256", required=True)
    args = parser.parse_args()
    try:
        if args.mode == "verify":
            result = verify(args.design, args.observations, design_sha256=args.design_sha256,
                            observations_sha256=args.observations_sha256)
        else:
            result = historical_preview(args.archive, archive_sha256=args.archive_sha256)
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.exit(2, f"{error}\n")
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
