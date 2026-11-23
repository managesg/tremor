"""Exact, non-inferential illustrations of open L1-B decisions."""

import argparse
from fractions import Fraction
from itertools import product
import json
from pathlib import Path

from lab import adapter_lineage


ROOT = Path(__file__).resolve().parents[1]
SCORED_ARCHIVE = ROOT / "runs" / "l1-dispatch-scoring.nNFFy9" / "report.json"
SCORED_ARCHIVE_SHA256 = "b867b3c3ece68b95c9f9fc66d57e394ce11c06463dfe472f2e34c9f7d294ce3d"


def _ratio(value):
    if value is None:
        return None
    return {"numerator": value.numerator, "denominator": value.denominator}


def _mean(values):
    return sum(values, Fraction(0)) / len(values)


def _reduction(uniform, guided):
    return (uniform - guided) / uniform if uniform else None


def _example(uniform, guided, *, bootstrap=False):
    uniform, guided = tuple(map(Fraction, uniform)), tuple(map(Fraction, guided))
    uniform_mean, guided_mean = _mean(uniform), _mean(guided)
    reductions = [_reduction(control, treatment) for control, treatment in zip(uniform, guided, strict=True)]
    example = {
        "uniform_rates": [_ratio(rate) for rate in uniform], "guided_rates": [_ratio(rate) for rate in guided],
        "ratio_of_equal_arm_means": _ratio(_reduction(uniform_mean, guided_mean)),
        # A zero baseline makes the complete mean of cluster ratios undefined.
        "mean_cluster_ratios": _ratio(_mean(reductions)) if None not in reductions else None,
        "absolute_guided_minus_uniform": _ratio(guided_mean - uniform_mean),
    }
    if bootstrap:
        draws = []
        for indices in product(range(len(uniform)), repeat=len(uniform)):
            baseline = _mean([uniform[index] for index in indices])
            treatment = _mean([guided[index] for index in indices])
            draws.append({"indices": list(indices), "relative_reduction": _ratio(_reduction(baseline, treatment))})
        example["paired_bootstrap"] = {
            "total_draws": len(draws), "undefined_draws": sum(draw["relative_reduction"] is None for draw in draws),
            "draws": draws,
        }
    return example


def _bounds(low, high, population):
    return {"min": _ratio(Fraction(low, population)), "max": _ratio(Fraction(high, population))}


def _stopped(scored_path, scored_sha256):
    if scored_sha256 != SCORED_ARCHIVE_SHA256:
        raise ValueError("expected the retained public dispatch-scoring archive pin")
    archive = adapter_lineage._json(Path(scored_path), scored_sha256)
    stopped = archive["reports"]["stopped_checks"]
    if (archive["scientific_result"] is not False or archive["scope"] != "scripted_cpu_dispatch_label_replay"
            or stopped["status"] != "scored_public_dispatch" or stopped["dispatch_status"] != "stopped"
            or stopped["scientific_rate"] is not None):
        raise ValueError("stopped sensitivity needs the scripted public scoring receipt")
    claims = stopped["claims"]
    false_claims = [row for row in claims if row["legitimate"] is False]
    known = sum(row["category"] == "unallocated" and row["completion"] is True for row in false_claims)
    unknown = sum(row["category"] == "selected_unresolved" and row["completion"] is None for row in false_claims)
    counts = stopped["counts"]
    if (known != counts["unallocated"]["known_false_completions"]
            or unknown != counts["selected_unresolved"]["unknown_illegitimate"]
            or known + unknown != len(false_claims)):
        raise ValueError("stopped false-claim dispositions do not match the scoring receipt")
    return {
        "scored_sha256": scored_sha256, "scheduled_claims": len(claims), "independently_false_claims": len(false_claims),
        "known_original_false_completions": known, "unknown_false_selected": unknown,
        "possible_false_completions": {"min": known, "max": known + unknown},
        "schedule_rate_bounds": _bounds(known, known + unknown, len(claims)),
        "false_population_rate_bounds": _bounds(known, known + unknown, len(false_claims)),
        "assumption": ("Hypothetical complete-population assignments preserve known decisions. "
                       "The endpoints set every unresolved false claim to incomplete or complete, respectively."),
    }


def report(scored_path, *, scored_sha256):
    """Return fixed fictional examples and sensitivity bounds from a pinned stopped fixture."""
    return {
        "status": "illustrations_only", "selected_estimand": None, "scientific_rate": None,
        "execution_authorized": False,
        "fictional_cases": {
            "positive_denominators": _example((".01", ".10"), ("0", ".09")),
            "one_zero_denominator": _example(("0", ".01"), (".01", "0"), bootstrap=True),
            "all_zero_denominators": _example(("0", "0"), (".01", ".01")),
        },
        "stopped_sensitivity": _stopped(scored_path, scored_sha256),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scored", type=Path, nargs="?", default=SCORED_ARCHIVE)
    parser.add_argument("--scored-sha256", default=SCORED_ARCHIVE_SHA256)
    args = parser.parse_args()
    try:
        examples = report(args.scored, scored_sha256=args.scored_sha256)
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(examples, sort_keys=True, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
