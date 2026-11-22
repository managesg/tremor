"""Join scripted controller pair outcomes to independently pinned holdout clusters."""

import argparse
import json
from pathlib import Path

from lab import controller_holdout as holdout
from lab import controller_pair_audit as pairs
from lab import controller_selection as selection


def verify(bundle, manifest, evidence_index, trace, task_inventory, exposure_witness, *,
           manifest_sha256, evidence_index_sha256, trace_sha256, witness_sha256, release_witness,
           prior_inventory=None, policy_witness=None):
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
    return {
        "evidence": "scripted_cpu_controller_cluster_audit",
        "scientific_acceptance": False,
        "exposure": exposure,
        "paired_audit": outcomes,
        "fully_observed_pair_clusters": sum(cluster["complete_pairs"] == len(cluster["blocks"])
                                       for cluster in summaries),
        "clusters": summaries,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("bundle", "manifest", "evidence_index", "trace", "task_inventory", "exposure_witness"):
        parser.add_argument(name, type=Path)
    for name in ("manifest", "evidence-index", "trace", "witness"):
        parser.add_argument(f"--{name}-sha256", required=True)
    parser.add_argument("--release-witness", nargs=2, metavar=("PATH", "SHA256"), required=True)
    parser.add_argument("--prior-inventory", nargs=2, metavar=("PATH", "SHA256"))
    parser.add_argument("--policy-witness", nargs=2, metavar=("PATH", "SHA256"))
    try:
        report = verify(**vars(parser.parse_args()))
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(report, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
