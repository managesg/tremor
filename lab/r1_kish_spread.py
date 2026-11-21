"""Report pairwise correlation coverage before interpreting Kish effective size."""

import json
import math
import sys
from itertools import combinations


def diagnose(misses):
    """Compute observed phi spread and Kish when all pairs are defined.

    Kish needs at least one observed pair. It describes variance under
    exchangeability, which correlation spread alone cannot establish.
    """
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


if __name__ == "__main__":
    print(json.dumps(diagnose(json.load(sys.stdin)), sort_keys=True, allow_nan=False))
