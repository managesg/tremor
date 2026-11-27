"""Susceptibility readouts in one thin module (WORKPLAN-RESIDENCY-V3 policy row 159). Stdlib only.

Re-exports from readouts: rerun_variance, dose_slope, reproduction_number (R per note), recovery_time,
pairwise_miss (pairwise error correlation). Ported from lab (src never imports lab): response_fluctuation_ratio
(lab/r1_response_fluctuation.measure) and kish_spread_check (lab/r1_kish_spread.diagnose). New: adoption,
cascade_depth. Statistical sources are those cited in readouts.py.
"""
import math
from fractions import Fraction
from itertools import combinations

from tremor.readouts import (  # noqa: F401  re-exports
    dose_slope, pairwise_miss, recovery_time, reproduction_number, rerun_variance,
)

__all__ = [
    "rerun_variance", "dose_slope", "response_fluctuation_ratio", "adoption", "cascade_depth",
    "reproduction_number", "recovery_time", "pairwise_miss", "kish_spread_check",
]


def _children(notes):
    kids = {}
    for n in notes:
        for p in n["parents"]:
            kids.setdefault(p, []).append(n["id"])
    return kids


def adoption(notes, planted):
    """Number of adopters = planted ids plus all descendants via "parents" (0 if nothing planted)."""
    return reproduction_number(notes, planted)[1]


def cascade_depth(notes, planted):
    """Max shortest-path generations from any planted root to an adopter (0 = roots only); None if nothing planted."""
    roots = set(planted)
    if not roots:
        return None  # missing is not zero
    kids = _children(notes)
    seen, level, depth = roots.copy(), list(roots), 0
    while True:
        nxt = []
        for node in level:
            for c in kids.get(node, []):
                if c not in seen:
                    seen.add(c)
                    nxt.append(c)
        if not nxt:
            return depth
        level, depth = nxt, depth + 1


# --- ported from lab/l1_nested_model_control.py (exact least squares) ---
def _number(value):
    if type(value) not in (int, Fraction):
        raise ValueError("expected an exact integer or Fraction")
    return Fraction(value)


def _dot(left, right):
    return sum((a * b for a, b in zip(left, right, strict=True)), Fraction(0))


def _count_scale_slope(dose_counts):
    try:
        iterator = iter(dose_counts)
    except TypeError as error:
        raise ValueError("expected an iterable of exact (dose, count) pairs") from error
    points = []
    for pair in iterator:
        if type(pair) not in (tuple, list) or len(pair) != 2:
            raise ValueError("expected an ordered (dose, count) pair")
        dose, count = pair
        points.append((_number(dose), _number(count)))
    if len({dose for dose, _ in points}) < 3:
        raise ValueError("susceptibility needs at least three distinct doses")
    doses, counts = zip(*points, strict=True)
    mean_dose, mean_count = sum(doses) / len(doses), sum(counts) / len(counts)
    centered_doses = [dose - mean_dose for dose in doses]
    centered_counts = [count - mean_count for count in counts]
    return _dot(centered_doses, centered_counts) / _dot(centered_doses, centered_doses)


def _dose(value):
    if type(value) not in (int, Fraction) or value < 0:
        raise ValueError("dose must be an exact nonnegative number")
    return Fraction(value)


def response_fluctuation_ratio(dose_counts, *, team_size, reference_dose):
    """Exact: reference_overdispersion = sample count variance / binomial n p (1-p) at the reference dose;
    count_scale_slope = OLS slope of mean adoption count on dose; slope per sample variance (None if undefined)."""
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
    slope = _count_scale_slope(means.items())
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


def kish_spread_check(misses):
    """Kish n_eff = m / (1 + 2 sum_pairs phi / m) only when all m(m-1)/2 phi pairs are defined (Kish 1965,
    exchangeable members); also reports the observed phi mean and range. None where undefined."""
    if not isinstance(misses, (list, tuple)) or not misses:
        raise ValueError("at least one monitor and one episode are required")
    if any(not isinstance(row, (list, tuple)) or not row for row in misses):
        raise ValueError("monitor rows must be nonempty arrays")
    episodes = len(misses[0])
    if any(len(row) != episodes or any(type(bit) not in (bool, int) or bit not in (0, 1) for bit in row)
           for row in misses):
        raise ValueError("monitor rows must have equal length and binary results")

    monitors = len(misses)
    possible = math.comb(monitors, 2)
    variable = [(row, sum(row)) for row in misses]
    variable = [(row, count) for row, count in variable if 0 < count < episodes]
    correlations = []
    for (first, a), (second, b) in combinations(variable, 2):
        joint = sum(x and y for x, y in zip(first, second))
        scale = math.sqrt(a * (episodes - a) * b * (episodes - b))
        correlations.append((episodes * joint - a * b) / scale)

    observed = len(correlations)
    mean = math.fsum(correlations) / observed if observed else None
    denominator = (
        math.fsum([monitors, *(2 * rho for rho in correlations)]) / monitors
        if observed and observed == possible else None
    )
    # Correlation rounding accumulates across pairs near cancellation.
    rounding_bound = 2 * (monitors - 1) * math.ulp(1.0)
    effective = monitors / denominator if denominator is not None and denominator > rounding_bound else None
    return {
        "monitors": monitors,
        "episodes": episodes,
        "observed_pairs": observed,
        "possible_pairs": possible,
        "observed_mean_phi": mean,
        "observed_phi_range": [min(correlations), max(correlations)] if observed else None,
        "kish_denominator": denominator,
        "kish_effective_size": effective,
    }
