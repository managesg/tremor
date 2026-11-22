"""Join scripted controller pair outcomes to independently pinned holdout clusters."""

import argparse
from fractions import Fraction
import json
from pathlib import Path

from lab import controller_attempt_cost as costs
from lab import controller_holdout as holdout
from lab import controller_pair_audit as pairs
from lab import controller_selection as selection


def _block_bounds(pair, slots):
    eligible = pair["eligible_count"]
    counts = {row["arm"]: row["distinct_passing"] for row in pair["arms"]}
    for count in counts.values():
        selection._require(count is None or 0 <= count <= slots, "passing count outside frozen work slots")
    combined, plain = counts["combined"], counts["plain"]
    combined_low, combined_high = (0, slots) if combined is None else (combined, combined)
    plain_low, plain_high = (0, slots) if plain is None else (plain, plain)
    return Fraction(combined_low - plain_high, eligible), Fraction(combined_high - plain_low, eligible)


def _missing_bounds(clusters, pairs_by_id, slots_by_id):
    """Bound each cluster's equal-block diagnostic without filling in missing scores."""
    by_cluster = []
    for cluster in clusters:
        ids = [block["block_id"] for block in cluster["blocks"]]
        bounds = [_block_bounds(pairs_by_id[identifier], slots_by_id[identifier]) for identifier in ids]
        low = sum(row[0] for row in bounds) / len(bounds)
        high = sum(row[1] for row in bounds) / len(bounds)
        by_cluster.append({
            "cluster_id": cluster["cluster_id"],
            "missing_pairs": len(bounds) - cluster["complete_pairs"],
            "mean_paired_delta_bounds": [str(low), str(high)],
            "blocks": [
                {"block_id": identifier, "delta_bounds": [str(lo), str(hi)]}
                for identifier, (lo, hi) in zip(ids, bounds, strict=True)
            ],
        })
    return {"scope": "descriptive_equal_block_bounds_within_each_declared_cluster",
            "missing_arm_count_range": "zero_to_frozen_work_slots", "by_cluster": by_cluster}


def verify(bundle, manifest, evidence_index, trace, task_inventory, exposure_witness, *,
           manifest_sha256, evidence_index_sha256, trace_sha256, witness_sha256, release_witness,
           prior_inventory=None, policy_witness=None, missing_outcome_bounds=False, charge_witness=None):
    """Retain each scheduled pair in its verified cluster, including stopped pairs."""
    selection._require(release_witness is not None, "cluster audit requires a V2 release witness")
    freeze = {"manifest_sha256": manifest_sha256, "evidence_index_sha256": evidence_index_sha256}
    exposure = holdout.verify(
        bundle, manifest, evidence_index, task_inventory, exposure_witness, **freeze,
        witness_sha256=witness_sha256, prior_inventory=prior_inventory,
    )
    outcomes = pairs.verify(
        bundle, manifest, evidence_index, trace, **freeze, trace_sha256=trace_sha256,
        release_witness=release_witness, policy_witness=policy_witness,
    )
    custody = selection._pinned_json(exposure_witness, witness_sha256)
    clusters = {}
    for row, result in zip(custody["holdout"], outcomes["pairs"], strict=True):
        selection._require(row["block_id"] == result["block_id"], "pair and exposure block identity differs")
        cluster = clusters.setdefault(row["cluster_id"], [])
        cluster.append({"block_id": result["block_id"], "paired_delta": result["paired_delta"]})
    summaries = [
        {"cluster_id": identifier, "blocks": blocks,
         "complete_pairs": sum(block["paired_delta"] is not None for block in blocks)}
        for identifier, blocks in clusters.items()
    ]
    report = {
        "evidence": "scripted_cpu_controller_cluster_audit",
        "scientific_acceptance": False,
        "exposure": exposure,
        "paired_audit": outcomes,
        "fully_observed_pair_clusters": sum(cluster["complete_pairs"] == len(cluster["blocks"])
                                       for cluster in summaries),
        "clusters": summaries,
    }
    if missing_outcome_bounds:
        inventory = selection._pinned_json(task_inventory, exposure["task_inventory_sha256"])
        report["missing_outcome_bounds"] = _missing_bounds(
            summaries, {pair["block_id"]: pair for pair in outcomes["pairs"]},
            {block["block_id"]: block["taskset"]["n_agents"] for block in inventory["blocks"]},
        )
    if charge_witness is not None:
        report["observed_charge_join"] = costs.reconcile(trace, trace_sha256, charge_witness)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("bundle", "manifest", "evidence_index", "trace", "task_inventory", "exposure_witness"):
        parser.add_argument(name, type=Path)
    for name in ("manifest", "evidence-index", "trace", "witness"):
        parser.add_argument(f"--{name}-sha256", required=True)
    parser.add_argument("--release-witness", nargs=2, metavar=("PATH", "SHA256"), required=True)
    parser.add_argument("--prior-inventory", nargs=2, metavar=("PATH", "SHA256"))
    parser.add_argument("--policy-witness", nargs=2, metavar=("PATH", "SHA256"))
    parser.add_argument("--missing-outcome-bounds", action="store_true",
                        help="report descriptive paired score bounds within each declared cluster")
    parser.add_argument("--charge-witness", nargs=2, metavar=("PATH", "SHA256"),
                        help="join exact arm attempts to independently pinned cost and common-role artifacts")
    try:
        report = verify(**vars(parser.parse_args()))
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(report, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
