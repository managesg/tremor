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


def _cohort_weights(witness, clusters, *, manifest_sha256, exposure_sha256, inventory_sha256):
    path, pin = witness
    profile = selection._pinned_json(path, pin)
    selection._object(profile, ("schema", "manifest_sha256", "exposure_witness_sha256",
                                "task_inventory_sha256", "cluster_weights"), "cohort weight profile")
    selection._require(profile["schema"] == "controller_cohort_weights_v1"
                       and profile["manifest_sha256"] == manifest_sha256
                       and profile["exposure_witness_sha256"] == exposure_sha256
                       and profile["task_inventory_sha256"] == inventory_sha256,
                       "cohort weight profile must bind the pinned manifest, exposure and inventory")
    rows = profile["cluster_weights"]
    selection._require(type(rows) is dict and rows.keys() == {row["cluster_id"] for row in clusters},
                       "cohort weight profile differs from the scheduled cluster roster")
    weights = {}
    for identifier, fraction in rows.items():
        selection._require(type(fraction) is list and len(fraction) == 2
                           and all(type(term) is int and term > 0 for term in fraction),
                           "each cluster weight must be a positive integer fraction")
        weights[identifier] = Fraction(*fraction)
    selection._require(sum(weights.values()) == 1, "cluster weights must sum exactly to one")
    return weights


def _weighted_bounds(clusters, bounds, weights):
    """Pool finite-cohort bounds without redistributing missing outcome mass."""
    low = high = observed_mass = observed = Fraction(0)
    for cluster, interval in zip(clusters, bounds, strict=True):
        weight = weights[cluster["cluster_id"]]
        lo, hi = (Fraction(value) for value in interval["mean_paired_delta_bounds"])
        low += weight * lo
        high += weight * hi
        block_weight = weight / len(cluster["blocks"])
        for block in cluster["blocks"]:
            if block["paired_delta"] is not None:
                observed += block_weight * Fraction(block["paired_delta"])
                observed_mass += block_weight
    return {"cluster_weights": {name: str(value) for name, value in weights.items()},
            "mean_paired_delta_bounds": [str(low), str(high)],
            "mean_paired_delta": str(observed) if observed_mass == 1 else None,
            "observed_weight_mass": str(observed_mass),
            "missing_weight_mass": str(1 - observed_mass),
            "observed_weighted_contribution": str(observed) if observed_mass else None}


def _weight_diagnostics(clusters, bounds, weights, witness_pin):
    blocks = sum(len(row["blocks"]) for row in clusters)
    equal_cluster = {row["cluster_id"]: Fraction(1, len(clusters)) for row in clusters}
    equal_block = {row["cluster_id"]: Fraction(len(row["blocks"]), blocks) for row in clusters}
    return {"scope": "descriptive_finite_cohort_bounds_with_equal_blocks_within_clusters",
            "weight_witness_sha256": witness_pin,
            "declared_cluster_weights": _weighted_bounds(clusters, bounds, weights),
            "equal_cluster_sensitivity": _weighted_bounds(clusters, bounds, equal_cluster),
            "equal_scheduled_block_sensitivity": _weighted_bounds(clusters, bounds, equal_block)}


def verify(bundle, manifest, evidence_index, trace, task_inventory, exposure_witness, *,
           manifest_sha256, evidence_index_sha256, trace_sha256, witness_sha256, release_witness,
           prior_inventory=None, policy_witness=None, missing_outcome_bounds=False, charge_witness=None,
           cohort_weight_witness=None, order_witness=None):
    """Retain each scheduled pair in its verified cluster, including stopped pairs."""
    selection._require(release_witness is not None, "cluster audit requires a V2 release witness")
    freeze = {"manifest_sha256": manifest_sha256, "evidence_index_sha256": evidence_index_sha256}
    exposure = holdout.verify(
        bundle, manifest, evidence_index, task_inventory, exposure_witness, **freeze,
        witness_sha256=witness_sha256, prior_inventory=prior_inventory,
    )
    outcomes = pairs.verify(
        bundle, manifest, evidence_index, trace, **freeze, trace_sha256=trace_sha256,
        release_witness=release_witness, policy_witness=policy_witness, order_witness=order_witness,
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
    if missing_outcome_bounds or cohort_weight_witness is not None:
        inventory = selection._pinned_json(task_inventory, exposure["task_inventory_sha256"])
        bounds = _missing_bounds(
            summaries, {pair["block_id"]: pair for pair in outcomes["pairs"]},
            {block["block_id"]: block["taskset"]["n_agents"] for block in inventory["blocks"]},
        )
        if missing_outcome_bounds:
            report["missing_outcome_bounds"] = bounds
        if cohort_weight_witness is not None:
            weights = _cohort_weights(cohort_weight_witness, summaries, manifest_sha256=manifest_sha256,
                                      exposure_sha256=witness_sha256,
                                      inventory_sha256=exposure["task_inventory_sha256"])
            report["weighted_outcome_bounds"] = _weight_diagnostics(
                summaries, bounds["by_cluster"], weights, cohort_weight_witness[1],
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
    parser.add_argument("--order-witness", nargs=2, metavar=("PATH", "SHA256"))
    parser.add_argument("--missing-outcome-bounds", action="store_true",
                        help="report descriptive paired score bounds within each declared cluster")
    parser.add_argument("--cohort-weight-witness", nargs=2, metavar=("PATH", "SHA256"),
                        help="bound the full cohort under an independently pinned cluster weight profile")
    parser.add_argument("--charge-witness", nargs=2, metavar=("PATH", "SHA256"),
                        help="join exact arm attempts to independently pinned cost and common-role artifacts")
    try:
        report = verify(**vars(parser.parse_args()))
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(report, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
