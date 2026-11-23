"""Exact developmental L1 response and count fluctuation diagnostics."""

from fractions import Fraction
import json

from lab.l1_nested_model_control import count_scale_slope


def _dose(value):
    if type(value) not in (int, Fraction) or value < 0:
        raise ValueError("dose must be an exact nonnegative number")
    return Fraction(value)


def measure(dose_counts, *, team_size, reference_dose):
    """Use mean adoption counts for the slope and sample variance at one dose."""
    if type(team_size) is not int or team_size < 1:
        raise ValueError("team size must be a positive integer")
    reference = _dose(reference_dose)
    counts_by_dose = {}
    for dose, counts in dose_counts:
        dose = _dose(dose)
        if dose in counts_by_dose:
            raise ValueError("each dose needs exactly one rerun group")
        counts = tuple(counts)
        if not counts or any(type(count) is not int or not 0 <= count <= team_size for count in counts):
            raise ValueError("each dose needs integer adoption counts within the team size")
        counts_by_dose[dose] = counts
    if reference not in counts_by_dose:
        raise ValueError("reference dose is absent")

    means = {dose: Fraction(sum(counts), len(counts)) for dose, counts in counts_by_dose.items()}
    slope = count_scale_slope(means.items())
    baseline_counts = counts_by_dose[reference]
    baseline_mean = means[reference]
    variance = None
    if len(baseline_counts) > 1:
        variance = sum((count - baseline_mean) ** 2 for count in baseline_counts) / (len(baseline_counts) - 1)

    adoption_fraction = baseline_mean / team_size
    binomial_variance = team_size * adoption_fraction * (1 - adoption_fraction)
    return {
        "reference_dose": reference,
        "reference_adoption_count_mean": baseline_mean,
        "reference_reruns": len(baseline_counts),
        "count_scale_slope": slope,
        "reference_sample_count_variance": variance,
        "reference_binomial_count_variance": binomial_variance,
        "reference_overdispersion": variance / binomial_variance if variance is not None and binomial_variance else None,
        "candidate_slope_per_sample_count_variance": slope / variance if variance else None,
    }


def _ratio(value):
    return {"numerator": value.numerator, "denominator": value.denominator} if isinstance(value, Fraction) else value


def demo():
    """Report a positive, flat, zero-variance and boundary fixture."""
    ordinary_reference = (0, 1, 1, 1, 2)
    low = (0, 0, 1, 1, 1)
    high = (1, 1, 1, 2, 2)
    comparisons = {
        "positive": (low, ordinary_reference, high),
        "higher_fluctuation": (low, (0, 0, 1, 2, 2), high),
        "flat": (ordinary_reference,) * 3,
        "zero_observed_variance": (low, (1,) * 5, high),
        "zero_binomial_variance": ((0,) * 5,) * 3,
    }
    return {
        "scope": "scripted_development",
        "scientific_result": False,
        "units": {
            "dose": "verification passes per unit",
            "count_scale_slope": "adoption count per unit dose",
            "count_variance": "squared adoption count",
            "reference_overdispersion": "dimensionless",
            "candidate_slope_per_sample_count_variance": "inverse adoption count per unit dose",
        },
        "cases": {
            name: {field: _ratio(value) for field, value in measure(
                enumerate(groups), team_size=2, reference_dose=1,
            ).items()}
            for name, groups in comparisons.items()
        },
    }


if __name__ == "__main__":
    print(json.dumps(demo(), sort_keys=True, indent=2, allow_nan=False))
