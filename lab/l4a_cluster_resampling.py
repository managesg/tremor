"""Exact development resampling for paired L4-A chain losses."""

from collections import Counter
from fractions import Fraction
from itertools import product
import json
import re

from lab.l4_measured_compression import pin
from lab.l4a_cluster_distribution import distribution
from lab.l4a_exact_fit import fit as fit_models, predict
from lab.l4a_segmented_control import KNOTS, _chain, _id, _observations, fit_training, score_holdout


SCORE_FIELDS = {"scope", "scientific_result", "fit_sha256", "holdout_sha256",
                "straight_mse", "hinge_mse", "gain", "chains"}


def _ratio(value):
    return {"numerator": value.numerator, "denominator": value.denominator}


def _fraction(value):
    if (type(value) is not dict or value.keys() != {"numerator", "denominator"}
            or any(type(x) is not int for x in value.values()) or value["denominator"] <= 0):
        raise ValueError("paired scores need exact rational values")
    return Fraction(**value)


def _digest(value):
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _paired_gains(scored):
    chains = scored.get("chains")
    if type(chains) is not list or not chains:
        raise ValueError("at least one held-out chain is required")
    values, ids = [], set()
    for row in chains:
        if type(row) is not dict or row.keys() != {"id", "straight_mse", "hinge_mse", "gain"}:
            raise ValueError("invalid paired chain score")
        chain = row["id"]
        if not _id(chain) or chain in ids:
            raise ValueError("invalid or repeated held-out chain")
        straight, hinge, gain = (_fraction(row[name]) for name in ("straight_mse", "hinge_mse", "gain"))
        if min(straight, hinge) < 0 or gain != straight - hinge:
            raise ValueError("paired loss difference does not reconcile")
        ids.add(chain)
        values.append((straight, hinge, gain))
    for index, name in enumerate(("straight_mse", "hinge_mse", "gain")):
        if sum(row[index] for row in values) / len(values) != _fraction(scored[name]):
            raise ValueError("paired aggregate does not reconcile")
    return [row[2] for row in values]


def _report(method, frequencies, *, planned, fit_pin, score_pin, point, undefined_reasons):
    defined = sum(frequencies.values())
    undefined = sum(undefined_reasons.values())
    if planned != defined + undefined:
        raise ValueError("resampling draw counts do not reconcile")
    return {"scope": "scripted_l4a_cluster_resampling", "scientific_result": False, "method": method,
            "fit_sha256": fit_pin, "score_sha256": score_pin, "observed_gain": _ratio(point),
            "planned_draws": planned, "defined_draws": defined, "undefined_draws": undefined,
            "undefined_reasons": dict(undefined_reasons),
            "histogram": [{"gain": _ratio(value), "draws": count} for value, count in sorted(frequencies.items())],
            "defined_draw_mean": _ratio(sum(value * count for value, count in frequencies.items()) / defined)
            if defined else None, "scientific_interval": None, "scientific_decision": None}


def conditional(scored, *, expected_fit_pin, expected_score_pin, max_draws):
    """Resample paired held-out losses with the supplied fit unchanged."""
    if (type(scored) is not dict or scored.keys() != SCORE_FIELDS or pin(scored) != expected_score_pin
            or scored["scope"] != "scripted_l4a_holdout" or scored["scientific_result"] is not False
            or scored["fit_sha256"] != expected_fit_pin
            or not all(_digest(scored[key]) for key in ("fit_sha256", "holdout_sha256"))):
        raise ValueError("paired score differs from the expected fit or score pin")
    gains = _paired_gains(scored)
    frequencies = distribution(gains, max_draws=max_draws)
    return _report("fixed_fit_heldout_chains", frequencies, planned=len(gains) ** len(gains),
                   fit_pin=expected_fit_pin, score_pin=expected_score_pin, point=_fraction(scored["gain"]),
                   undefined_reasons={})


def _gain(models, chain):
    return sum((y - predict(models["line"], x)) ** 2 - (y - predict(models["hinge"], x)) ** 2
               for x, y in chain) / len(chain)


def refitted(training, holdout, fitted, *, expected_training_pin, expected_holdout_pin, expected_fit_pin,
             expected_score_pin, knots, max_draws):
    """Jointly enumerate training refits and paired held-out chain draws."""
    if type(max_draws) is not int or max_draws < 1:
        raise ValueError("draw cap must be a positive integer")
    knots = tuple(knots)
    original = fit_training(training, expected_training_pin=expected_training_pin, knots=knots)
    if original != fitted or pin(fitted) != expected_fit_pin:
        raise ValueError("refit inputs do not reproduce the expected original fit")
    scored = score_holdout(holdout, fitted, expected_holdout_pin=expected_holdout_pin,
                           expected_fit_pin=expected_fit_pin)
    if pin(scored) != expected_score_pin:
        raise ValueError("refit inputs do not reproduce the expected original score")
    train_points, _ = _observations(training, expected_training_pin)
    test_points, _ = _observations(holdout, expected_holdout_pin)
    train_count, test_count = len(train_points), len(test_points)
    heldout_draws = test_count ** test_count
    planned = (train_count ** train_count) * heldout_draws
    if planned > max_draws:
        raise ValueError("joint chain draws exceed the cap")

    frequencies, undefined = Counter(), Counter()
    for chosen in product(train_points.values(), repeat=train_count):
        try:
            models = fit_models([point for chain in chosen for point in chain], knots=knots)
        except ValueError as error:
            # A sampled training grid may lose the support required by a planned knot.
            undefined[str(error)] += heldout_draws
            continue
        gains = [_gain(models, points) for points in test_points.values()]
        frequencies.update(distribution(gains, max_draws=heldout_draws))
    return _report("independent_training_refit_and_heldout_chains", frequencies, planned=planned,
                   fit_pin=expected_fit_pin, score_pin=expected_score_pin, point=_fraction(scored["gain"]),
                   undefined_reasons=undefined)


def _limited_grid(name, widths):
    chain = _chain(name, "kink", 0)
    for level, width in zip(chain["levels"], widths, strict=True):
        snapshot = level["snapshot"]
        for note in snapshot["loaded_before"]:
            note["text"] = "a" * 100
        for note in snapshot["loaded_after"]:
            note["text"] = "a" * width
        level["snapshot_pin"] = pin(snapshot)
    return chain


def demo():
    holdout = [_chain("test-kink", "kink", 0), _chain("test-inverted", "inverted", 0)]
    holdout_pin = pin(holdout)
    fixed = [_chain("train-kink", "kink", 0)]
    fitted = fit_training(fixed, expected_training_pin=pin(fixed), knots=KNOTS)
    scored = score_holdout(holdout, fitted, expected_holdout_pin=holdout_pin, expected_fit_pin=pin(fitted))
    results = {"conditional": conditional(scored, expected_fit_pin=pin(fitted),
                                          expected_score_pin=pin(scored), max_draws=4)}
    training_cases = {
        "refit": [*fixed, _chain("train-inverted", "inverted", 0)],
        "refit_with_undefined": [_limited_grid("train-low", (10, 20, 30, 35, 40, 42, 45)),
                                 _limited_grid("train-high", (35, 40, 45, 50, 55, 60, 70))],
    }
    for case, training in training_cases.items():
        train_pin = pin(training)
        fitted = fit_training(training, expected_training_pin=train_pin, knots=KNOTS)
        fit_pin = pin(fitted)
        scored = score_holdout(holdout, fitted, expected_holdout_pin=holdout_pin, expected_fit_pin=fit_pin)
        results[case] = refitted(training, holdout, fitted, expected_training_pin=train_pin,
                                 expected_holdout_pin=holdout_pin, expected_fit_pin=fit_pin,
                                 expected_score_pin=pin(scored), knots=KNOTS, max_draws=16)
    return results


if __name__ == "__main__":
    print(json.dumps(demo(), indent=2, sort_keys=True, allow_nan=False))
