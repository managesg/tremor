"""Replay the public Grover cap sweep and audit exact verified stage unions."""

import argparse
import json

from lab import topology
from . import topology_audit, topology_transfer


REFERENCE_SHA256 = "6ce893d3c05d06df563dde15086bc3764e1e1b0efdcceebb650b303210115bdc"


def _replay(cap, expected_sha256=None):
    trace = topology_transfer.compare(budget=cap)
    # Match topology_transfer's CLI serialization and historical reference.
    raw = (json.dumps(trace, indent=2, sort_keys=True) + "\n").encode()
    verified = topology_audit.audit(raw, expected_sha256=expected_sha256)
    cells = {
        (case["regime"], case["seed"], cell["mode"], cell["access"]): cell
        for case in verified["cases"]
        for cell in case["cells"]
    }
    return verified["sha256"], cells


def summarize(reference_sha256=REFERENCE_SHA256):
    """Verify each cap against the pinned full-cap development trace."""
    full_cap = topology.BUDGET
    reference_digest, reference = _replay(full_cap, reference_sha256)
    rows = []
    for cap in range(1, full_cap + 1):
        digest, cells = (reference_digest, reference) if cap == full_cap else _replay(cap)
        if cells.keys() != reference.keys():
            raise ValueError(f"cap {cap} does not reproduce the complete reference grid")
        different = []
        for key in sorted(cells):
            observed_union = cells[key]["stage_union"]
            reference_union = reference[key]["stage_union"]
            if observed_union != reference_union:
                regime, seed, mode, access = key
                different.append({"regime": regime, "seed": seed, "mode": mode, "access": access,
                                  "stage_union": observed_union, "reference_stage_union": reference_union})
        rows.append({
            "cap": cap, "trace_sha256": digest, "different_cells": different,
            "verified_stage_credits": sum(len(cell["stage_union"]) for cell in cells.values()),
            "total_spent": sum(cell["spent"] for cell in cells.values()),
        })

    return {
        "evidence": "scripted_public_cpu_development", "units": "abstract_scripted_cost_units",
        "authorizes_execution": False, "actors_authenticated": False,
        "reference_cap": full_cap, "reference_sha256": reference_digest,
        "cells_per_cap": len(reference),
        "audited_cells": len(reference) * len(rows),
        "first_cap_with_exact_reference_unions": next(row["cap"] for row in rows if not row["different_cells"]),
        "caps": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-sha256", default=REFERENCE_SHA256)
    args = parser.parse_args()
    try:
        report = summarize(args.reference_sha256)
    except (ValueError, KeyError, IndexError, TypeError) as error:
        parser.exit(2, f"Grover cap frontier failed: {error}\n")
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
