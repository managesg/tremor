"""Bind exact additive pilot variance to prospective R2 precision planning."""

import argparse
from fractions import Fraction
import json
from pathlib import Path

from lab import adapter_lineage, r2_paired_receipt, r2_precision_math, r2_precision_preflight


DESIGN_FIELDS = ("schema line cohort contrast unit control_arm treatment_arm scorer_sha256 schedule_sha256 "
                 "reruns_per_cluster expected_effect kill_boundary")


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _capacity(capacity, capacity_sha256, design_sha256, reruns):
    _require((capacity is None) == (capacity_sha256 is None), "capacity needs a path and independent pin")
    if capacity is None:
        return None
    path = Path(capacity).absolute()
    result = r2_precision_preflight._capacity(path.parent.resolve(), {"path": path.name, "sha256": capacity_sha256},
                                             design_sha256)
    _require(result["reruns_per_cluster"] == reruns, "capacity rerun count differs from the paired design")
    return result


def _cluster_variance(paired, reruns):
    eligible = [cluster for cluster in paired["cluster_contributions"] if cluster["status"] == "eligible"]
    _require(all(cluster["paired_reruns"] == reruns for cluster in eligible),
             "eligible paired clusters use a different rerun count from the precision design")
    if not paired["grid_complete"]:
        return None, "incomplete_grid"
    if len(eligible) < 2:
        return None, "undersized_pilot"
    if paired["counts"]["excluded_clusters"]:
        return None, "ineligible_clusters"
    evidence = paired["sample_variance"]
    variance = Fraction(evidence["numerator"], evidence["denominator"])
    return variance, "verified_cluster_variance" if variance else "degenerate_pilot"


def verify(design, schedule, observations, *, design_sha256, schedule_sha256, observations_sha256,
           capacity=None, capacity_sha256=None):
    """Join external design and pair pins without turning the receipt into an admission."""
    declared = adapter_lineage._json(Path(design), design_sha256)
    r2_precision_preflight._fields(declared, DESIGN_FIELDS)
    _require(declared["schema"] == "r2_paired_precision_design_v1"
             and declared["contrast"] == "control_minus_treatment"
             and declared["schedule_sha256"] == schedule_sha256, "unsupported additive precision design or crossed schedule")
    line, cohort = (r2_precision_preflight._id(declared[key]) for key in ("line", "cohort"))
    reruns = r2_precision_preflight._int(declared["reruns_per_cluster"], 3)
    effect, boundary = (declared[key] for key in ("expected_effect", "kill_boundary"))
    _require((effect is None) == (boundary is None), "precision effects need both expected effect and boundary")
    paired = r2_paired_receipt.verify(schedule, observations, schedule_sha256=schedule_sha256,
                                     observations_sha256=observations_sha256)
    _require(all(declared[key] == value for key, value in paired["design"].items())
             and declared["scorer_sha256"] == paired["scorer_sha256"], "paired receipt differs in arm, units or scorer")
    available = _capacity(capacity, capacity_sha256, design_sha256, reruns)
    variance, disposition = _cluster_variance(paired, reruns)
    planning = None
    status = "awaiting_design"
    if effect is not None:
        planning = r2_precision_math.calculate_from_cluster_variance(
            expected_effect=effect, kill_boundary=boundary, variance=variance,
            reruns_per_cluster=reruns, capacity=available,
        )
        status = "precision_projection" if variance else "awaiting_pilot"
    return {
        "status": status, "variance_disposition": disposition, "line": line, "cohort": cohort,
        "design_sha256": design_sha256, "capacity_sha256": capacity_sha256, "paired": paired, "planning": planning,
        "observed_standard_error": None, "scientific_decision_reachability": None,
        "authorizes_execution": False, "scientific_result": False, "independent_custody_verified": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("design", type=Path)
    parser.add_argument("schedule", type=Path)
    parser.add_argument("observations", type=Path)
    parser.add_argument("--design-sha256", required=True)
    parser.add_argument("--schedule-sha256", required=True)
    parser.add_argument("--observations-sha256", required=True)
    parser.add_argument("--capacity", type=Path)
    parser.add_argument("--capacity-sha256")
    args = parser.parse_args()
    try:
        report = verify(args.design, args.schedule, args.observations, design_sha256=args.design_sha256,
                        schedule_sha256=args.schedule_sha256, observations_sha256=args.observations_sha256,
                        capacity=args.capacity, capacity_sha256=args.capacity_sha256)
    except (KeyError, OSError, TypeError, ValueError, ZeroDivisionError) as error:
        parser.exit(2, f"{error}\n")
    print(json.dumps(report, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
