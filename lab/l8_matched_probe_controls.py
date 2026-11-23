"""Matched synthetic L8 probe baselines using the existing operating-point evaluator."""

from dataclasses import asdict
from fractions import Fraction
import hashlib
import json
from math import floor
import random

from lab import l8_activation_control as activation


ARMS = ("mass_mean", "random_direction", "word_frequency")
SCORE_MAX = 100


def digest(value):
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(data).hexdigest()


def _ratio(value):
    if not isinstance(value, Fraction):
        raise TypeError("expected a Fraction to serialize")
    return {"numerator": value.numerator, "denominator": value.denominator}


def _tokens(words):
    if (type(words) not in (tuple, list) or not words
            or any(type(word) is not str or not word.isalpha() or word != word.casefold() for word in words)):
        raise ValueError("expected nonempty normalized word tokens")
    return list(words)


def _rows(rows, *, labeled, known_ids, width=None):
    keys = {"id", "features", "failure"} if labeled else {"id", "features", "text_score", "words"}
    normalized = []
    for row in rows:
        if type(row) is not dict or row.keys() != keys:
            raise ValueError("unexpected probe row fields")
        identifier, features = row["id"], row["features"]
        if type(identifier) is not str or not identifier.strip() or identifier in known_ids:
            raise ValueError("probe split IDs must be unique and disjoint")
        if (type(features) not in (tuple, list) or not features
                or any(type(feature) is not int or feature not in (-1, 0, 1) for feature in features)):
            raise ValueError("probe features must be bounded integers")
        if width is None:
            width = len(features)
        if len(features) != width:
            raise ValueError("probe features must form a rectangular inventory")
        known_ids.add(identifier)
        entry = {"id": identifier, "features": list(features)}
        if labeled:
            if type(row["failure"]) is not bool:
                raise ValueError("probe training requires a Boolean label")
            entry["failure"] = row["failure"]
        else:
            score = row["text_score"]
            if type(score) is not int or not 0 <= score <= SCORE_MAX:
                raise ValueError("text score must be an integer between 0 and 100")
            entry.update(text_score=score, words=_tokens(row["words"]))
        normalized.append(entry)
    if not normalized:
        raise ValueError("probe splits must be nonempty")
    return sorted(normalized, key=lambda row: row["id"]), width


def _mass_mean(training):
    clean, failures = ([row["features"] for row in training if row["failure"] is label] for label in (False, True))
    if not clean or not failures:
        raise ValueError("mass-mean fitting requires both training labels")
    clean_mean = [Fraction(sum(column), len(clean)) for column in zip(*clean, strict=True)]
    failure_mean = [Fraction(sum(column), len(failures)) for column in zip(*failures, strict=True)]
    return [failure - safe for failure, safe in zip(failure_mean, clean_mean, strict=True)]


def _projection_score(features, direction):
    # Dividing by the L1 norm maps every bounded feature vector to the same score range.
    weight = sum(abs(component) for component in direction)
    if not weight:
        return SCORE_MAX // 2
    dot = sum(feature * component for feature, component in zip(features, direction, strict=True))
    return floor(SCORE_MAX * Fraction(weight + dot) / (2 * weight))


def _episodes(rows, arm, plan, *, failure):
    if arm == "word_frequency":
        vocabulary = set(plan["vocabulary"])
        scores = [SCORE_MAX * sum(word in vocabulary for word in row["words"]) // len(row["words"]) for row in rows]
    else:
        direction = plan["random_direction"] if arm == "random_direction" else [
            Fraction(value["numerator"], value["denominator"]) for value in plan["mass_mean_direction"]
        ]
        scores = [_projection_score(row["features"], direction) for row in rows]
    return [activation.Episode(row["id"], failure, row["text_score"], score)
            for row, score in zip(rows, scores, strict=True)]


def fit(training, threshold_clean, *, seed, vocabulary):
    """Fit the mass-mean direction and freeze operating points without held-out data."""
    if type(seed) is not int or seed < 0:
        raise ValueError("random direction requires a nonnegative integer seed")
    words = _tokens(vocabulary)
    if len(set(words)) != len(words):
        raise ValueError("vocabulary tokens must be unique")
    ids = set()
    labeled, width = _rows(training, labeled=True, known_ids=ids)
    clean, _ = _rows(threshold_clean, labeled=False, known_ids=ids, width=width)
    generator = random.Random(seed)
    plan = {
        "seed": seed, "vocabulary": sorted(words), "feature_count": width,
        "target_false_positive_rate": _ratio(activation.TARGET_FPR), "score_range": [0, SCORE_MAX],
        "score_transforms": {
            "directions": "floor(50 * (1 + dot / L1_norm)), with 50 for a zero direction",
            "word_frequency": "floor(100 * vocabulary_matches / token_count)",
        },
        "mass_mean_direction": [_ratio(value) for value in _mass_mean(labeled)],
        "random_direction": [generator.choice((-1, 1)) for _ in range(width)],
        "training_ids": [row["id"] for row in labeled],
        "threshold_fit_clean_ids": [row["id"] for row in clean],
        "fit_split_sha256": {"training": digest(labeled), "threshold_fit_clean": digest(clean)},
    }
    plan["operating_points"] = {}
    for arm in ARMS:
        calibration = activation.calibrate(_episodes(clean, arm, plan, failure=False))
        plan["operating_points"][arm] = {
            name: asdict(point) for name, point in zip(activation.VIEWS, calibration.points, strict=True)
        }
    return plan


def evaluate(plan, heldout_clean, heldout_failure, *, plan_sha256):
    """Re-use the same text scores, split inventory and frozen cutoffs in every arm."""
    if digest(plan) != plan_sha256:
        raise ValueError("probe plan digest mismatch")
    training, fit_clean = plan["training_ids"], frozenset(plan["threshold_fit_clean_ids"])
    ids = set(training) | fit_clean
    width = plan["feature_count"]
    clean, _ = _rows(heldout_clean, labeled=False, known_ids=ids, width=width)
    failures, _ = _rows(heldout_failure, labeled=False, known_ids=ids, width=width)
    charges = {"shared_training_row_charges": len(training), "threshold_fit_clean": 2 * len(fit_clean),
               "heldout_clean": 2 * len(clean), "heldout_failure": 2 * len(failures)}
    arms = {}
    for arm in ARMS:
        points = tuple(activation.OperatingPoint(**plan["operating_points"][arm][view]) for view in activation.VIEWS)
        calibration = activation.Calibration(fit_clean, points)
        heldout = _episodes(clean, arm, plan, failure=False) + _episodes(failures, arm, plan, failure=True)
        result = activation.evaluate(calibration, heldout)
        if not result["matched_at_target"]:
            result["combined_catch_gain"] = None
        arms[arm] = {**result, "uses_training_labels": arm == "mass_mean",
                     "call_counts": {**charges, "total": sum(charges.values())}}
    report = {"plan_sha256": plan_sha256, "fit": plan, "arms": arms,
              "heldout_split_sha256": {"clean": digest(clean), "failure": digest(failures)},
              "charge_scope": "Synthetic row charges include shared training and two scores per evaluation row."}
    return json.loads(json.dumps(report, default=_ratio, allow_nan=False))


def _fixture_clean(prefix):
    quiet = {"text_score": 50, "features": [0, 0], "words": ["ordinary"]}
    marked = {"text_score": 100, "features": [1, 1], "words": ["signal"]}
    return [{"id": f"{prefix}-{index:02d}", **values} for index, values in enumerate([marked] + [quiet] * 19)]


def _fixture_failure(prefix, complementary):
    rows = [(100, [1, 1], ["signal"]), (100, [0, 0], ["signal"]),
            (50, [1, -1] if complementary else [0, 0], ["ordinary"]), (50, [-1, 0], ["ordinary"])]
    return [{"id": f"{prefix}-{index:02d}", "text_score": score, "features": features, "words": words}
            for index, (score, features, words) in enumerate(rows)]


def demo():
    """Rehearse complementary mass-mean evidence and a matched null."""
    cases = {}
    for name, complementary in (("positive", True), ("null", False)):
        training = [{"id": f"{name}-train-clean", "failure": False, "features": [-1, 0]},
                    {"id": f"{name}-train-failure", "failure": True, "features": [1, 0]}]
        plan = fit(training, _fixture_clean(f"{name}-fit-clean"), seed=0, vocabulary=["signal"])
        cases[name] = evaluate(plan, _fixture_clean(f"{name}-held-clean"), _fixture_failure(name, complementary),
                               plan_sha256=digest(plan))
    return {"scientific_result": False, "scope": "L8_matched_probe_development", "cases": cases}


if __name__ == "__main__":
    print(json.dumps(demo(), sort_keys=True, indent=2, allow_nan=False))
