"""Verify paired additive observations and reduce them to independent cluster means."""

import argparse
from collections import Counter
from fractions import Fraction
import json
from pathlib import Path

from lab import adapter_lineage, r2_paired_grid


def _ratio(value):
    return None if value is None else {"numerator": value.numerator, "denominator": value.denominator}


def verify(schedule_path, observations_path, *, schedule_sha256, observations_sha256):
    """Keep all scheduled mates visible and aggregate only fully scored clusters."""
    schedule = adapter_lineage._json(Path(schedule_path), schedule_sha256)
    observations = adapter_lineage._json(Path(observations_path), observations_sha256)
    grid = r2_paired_grid.join(schedule, observations, schedule_sha256=schedule_sha256)
    states, contributions, means = Counter(), [], []
    scheduled_reruns = paired_reruns = 0
    for cluster in grid:
        reruns = cluster["reruns"]
        scheduled_reruns += len(reruns)
        differences = []
        for rerun in reruns:
            states[rerun["control_status"]] += 1
            states[rerun["treatment_status"]] += 1
            if rerun["difference"] is not None:
                differences.append(rerun["difference"])
        paired_reruns += len(differences)
        if len(differences) != len(reruns):
            status, mean = "incomplete", None
        elif len(reruns) < 3:
            status, mean = "insufficient_reruns", None
        elif any(row["seed"] is None for row in reruns):
            status, mean = "unverified_rerun_seed", None
        elif schedule["scorer_sha256"] is None:
            status, mean = "unverified_scorer", None
        else:
            status = "eligible"
            mean = sum(differences, Fraction()) / len(differences)
            means.append(mean)
        contributions.append({
            "cluster_id": cluster["cluster_id"], "family_id": cluster["family_id"], "case_id": cluster["case_id"],
            "status": status, "scheduled_reruns": len(reruns), "paired_reruns": len(differences),
            "mean_difference": _ratio(mean),
            "reruns": [{**row, "difference": _ratio(row["difference"])} for row in reruns],
        })
    mean = sum(means, Fraction()) / len(means) if means else None
    variance = (
        sum(((value - mean) ** 2 for value in means), Fraction()) / (len(means) - 1)
        if len(means) >= 2 else None
    )
    return {
        "status": "verified_paired_grid", "grid_complete": states["unrecorded"] == 0,
        "design": {"contrast": schedule["contrast"], "unit": schedule["unit"],
                   "control_arm": schedule["control_arm"], "treatment_arm": schedule["treatment_arm"]},
        "schedule_sha256": schedule_sha256, "observations_sha256": observations_sha256,
        "scorer_sha256": schedule["scorer_sha256"],
        "counts": {
            "scheduled_arms": 2 * scheduled_reruns,
            **{f"{state}_arms": states[state] for state in ("scored", "censored", "missing", "unrecorded")},
            "scheduled_reruns": scheduled_reruns, "paired_reruns": paired_reruns,
            "eligible_clusters": len(means), "excluded_clusters": len(grid) - len(means),
        },
        "cluster_contributions": contributions, "mean_difference": _ratio(mean), "sample_variance": _ratio(variance),
        "observed_native_variance": None, "scientific_interval": None, "scientific_result": False,
        "independent_custody_verified": False, "authorizes_execution": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("schedule", type=Path)
    parser.add_argument("observations", type=Path)
    parser.add_argument("--schedule-sha256", required=True)
    parser.add_argument("--observations-sha256", required=True)
    args = parser.parse_args()
    try:
        report = verify(args.schedule, args.observations, schedule_sha256=args.schedule_sha256,
                        observations_sha256=args.observations_sha256)
    except (KeyError, OSError, TypeError, ValueError, ZeroDivisionError) as error:
        parser.exit(2, f"{error}\n")
    print(json.dumps(report, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
