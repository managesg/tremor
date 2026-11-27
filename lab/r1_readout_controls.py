"""Scripted nulls and positive controls for L1, L3 and L7 readouts."""

import json

from tremor import readouts


def l1_controls():
    """Cross count dispersion and dose response while holding marginal means fixed."""
    counts = {"binomial_variance": (0, 1, 1, 1, 2), "excess_variance": (0, 0, 1, 2, 2)}
    outcomes = {"flat": (0.5,) * 4, "increasing": (0.125, 0.375, 0.625, 0.875)}
    doses = (0, 1, 2, 3)
    result = []
    for variance, values in counts.items():
        reruns = [[1] * count + [0] * (2 - count) for count in values]
        for response, ys in outcomes.items():
            slope, lower, upper = readouts.dose_slope(doses, ys)
            result.append({
                "variance": variance, "response": response, "reruns": reruns, "doses": doses,
                "outcomes": ys, "overdispersion": readouts.overdispersion(reruns),
                "mean_within_set_variance": readouts.rerun_variance(reruns),
                "linear_dose_slope": slope, "scripted_bootstrap_interval": [lower, upper],
            })
    return result


def l3_controls():
    """Match both monitors' individual miss rates and vary joint misses."""
    first = (1, 1, 0, 0)
    independent = (1, 0, 1, 0)
    inputs = {"independent_views": [first, independent], "copied_views": [first, first]}
    return {label: {"misses": misses, **readouts.pairwise_miss(misses)}
            for label, misses in inputs.items()}


def _balanced_errors(size, sources):
    """Enumerate balanced parity traces with exact pairwise independence by source."""
    return [[(episode & mask).bit_count() % 2 for episode in range(64)]
            for mask in (1 + i % sources for i in range(size))]


def l7_controls():
    """Grow teams with independent evidence or reuse four error traces."""
    controls = {}
    for label in ("independent_growth", "four_sources"):
        cells = {}
        for size in (4, 32):
            sources = size if label == "independent_growth" else 4
            misses = _balanced_errors(size, sources)
            measure = readouts.pairwise_miss(misses)
            cells[str(size)] = {
                "sources": sources, "task_sets": len(misses[0]),
                "mean_pairwise_error_correlation": measure["rho_bar"],
                "correlation_range": [measure["rho_min"], measure["rho_max"]],
                "kish_diagnostic": measure["n_eff"],
            }
        controls[label] = {
            "sizes": cells,
            "rho_32_minus_4": (cells["32"]["mean_pairwise_error_correlation"]
                              - cells["4"]["mean_pairwise_error_correlation"]),
        }
    return controls


def compare():
    return {"instrument_validation": True, "L1": l1_controls(), "L3": l3_controls(), "L7": l7_controls()}


if __name__ == "__main__":
    print(json.dumps(compare(), indent=2, sort_keys=True, allow_nan=False))
