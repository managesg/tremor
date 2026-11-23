"""Public L1 comparator controls with a separate, charged pilot fit."""

from dataclasses import asdict, dataclass
from fractions import Fraction
import json
import random

from lab import l1_verification_allocation as core

PILOT_UNIT_COST = 1 + core.CHECK_COST


@dataclass(frozen=True)
class PilotObservation:
    identifier: str
    output_bytes: int
    team_size: int
    check_prevented_false: bool


def fit(pilot, claims):
    """Fit an exact two-feature least-squares toy predictor without assessment labels."""
    assessment_ids = {claim.identifier for claim in claims}
    ids = set()
    for item in pilot:
        if (not isinstance(item, PilotObservation) or not isinstance(item.identifier, str)
                or not item.identifier.startswith("pilot-") or item.identifier in ids or item.identifier in assessment_ids
                or type(item.output_bytes) is not int or item.output_bytes < 0
                or type(item.team_size) is not int or item.team_size < 1
                or type(item.check_prevented_false) is not bool):
            raise ValueError("pilot fit requires a disjoint, uniquely identified labelled inventory")
        ids.add(item.identifier)
    count = len(pilot)
    if count < 3:
        raise ValueError("insufficient pilot observations")
    points = [(item.output_bytes, item.team_size, int(item.check_prevented_false)) for item in pilot]
    xbar, zbar, ybar = [Fraction(sum(column), count) for column in zip(*points, strict=True)]
    centered = [(x - xbar, z - zbar, y - ybar) for x, z, y in points]
    xx = sum(x * x for x, _, _ in centered)
    xz = sum(x * z for x, z, _ in centered)
    zz = sum(z * z for _, z, _ in centered)
    xy = sum(x * y for x, _, y in centered)
    zy = sum(z * y for _, z, y in centered)
    determinant = xx * zz - xz * xz
    if determinant == 0:
        raise ValueError("pilot feature matrix has no unique fit")
    x_coef, z_coef = (xy * zz - zy * xz) / determinant, (zy * xx - xy * xz) / determinant
    return ybar - x_coef * xbar - z_coef * zbar, x_coef, z_coef


def proportional_order(claims, scores):
    """Allocate one check at a time by score per next check, capped by open work."""
    queues = {stratum: [] for stratum in scores}
    for claim in claims:
        queues[claim.stratum].append(claim)
    if not any(scores.values()):
        return list(claims)
    assigned = dict.fromkeys(queues, 0)
    result = []
    while len(result) < len(claims):
        open_strata = (stratum for stratum, queue in queues.items() if assigned[stratum] < len(queue))
        stratum = max(open_strata, key=lambda name: scores[name] / (assigned[name] + 1))
        result.append(queues[stratum][assigned[stratum]])
        assigned[stratum] += 1
    return result


def make_plan(claims, calibration, features, pilot, *, mode, budget, seed=17):
    claims = tuple(claims)
    inventory = core._claim_inventory(claims)
    if mode not in core.ADDITIONAL_CHECK_MODES or type(budget) is not int or budget < 0 or type(seed) is not int:
        raise ValueError("invalid development comparator or budget")
    if (set(features) != {claim.identifier for claim in claims}
            or any(len(pair) != 2 or any(type(value) is not int for value in pair) or pair[0] < 0 or pair[1] < 1
                   for pair in features.values())):
        raise ValueError("features must match the scheduled claims and contain measured length and roster size")
    order, measured, scores, calibration_pin = list(claims), 0, {}, None
    provenance = {"features_sha256": core.digest(features)}
    if mode == "random":
        random.Random(seed).shuffle(order)
        provenance["order_seed"] = seed
    elif mode in ("length", "team_size"):
        index = 0 if mode == "length" else 1
        order.sort(key=lambda claim: -features[claim.identifier][index])
    elif mode == "pilot_predictor":
        measured = len(pilot) * PILOT_UNIT_COST
        if measured > budget:
            raise ValueError("budget cannot fund the separate pilot")
        intercept, x_coef, z_coef = fit(pilot, claims)
        predictions = {item: intercept + x_coef * pair[0] + z_coef * pair[1] for item, pair in features.items()}
        order.sort(key=lambda claim: -predictions[claim.identifier])
        scores = {item: float(value) for item, value in predictions.items()}
        calibration_pin = core.digest([asdict(item) for item in pilot])
        provenance["fitted_coefficients"] = [str(value) for value in (intercept, x_coef, z_coef)]
    else:
        measured, scores = core._measure(calibration, claims, "overdispersion")
        order = proportional_order(claims, scores)
        calibration_pin = core.digest(calibration)
    if measured > budget:
        raise ValueError("budget cannot fund the separate measurement")
    slots = (budget - measured) // core.CHECK_COST
    choices = [{"claim_id": claim.identifier, "stratum": claim.stratum, "action": "check", "cost": core.CHECK_COST}
               for claim in order[:slots]]
    spent = measured + len(choices) * core.CHECK_COST
    return {"mode": mode, "budget": budget, "measurement_spent": measured, "allocated": spent,
            "unused": budget - spent, "scores": scores, "choices": choices, "calibration_sha256": calibration_pin,
            "claim_inventory_sha256": core.digest(inventory), "provenance": provenance}


def demo():
    claims, calibration = core.development_inputs()
    features = {claim.identifier: (60 + (13 * index) % 99, 2 + (5 * index) % 7)
                for index, claim in enumerate(claims)}
    pilot = tuple(PilotObservation(f"pilot-{index}", length, team_size, prevented)
                  for index, (length, team_size, prevented) in enumerate(
                      ((100, 2, False), (100, 4, False), (100, 8, True), (160, 2, False),
                       (160, 4, True), (260, 2, True), (260, 8, True), (160, 8, False))
                  ))
    scenarios = {}
    for scenario, false_claims in (("positive", {1, 3, 5, 7}), ("null", set())):
        arms = {}
        for mode in core.ADDITIONAL_CHECK_MODES:
            plan = make_plan(claims, calibration, features, pilot, mode=mode, budget=56)
            pin = core.digest(plan)
            oracle = {claim.identifier: core.Outcome(index not in false_claims, None if index == 7 else index not in false_claims,
                                                      (None, None))
                      for index, claim in enumerate(claims)}
            arms[mode] = {"plan": plan, "plan_sha256": pin,
                          "metrics": core.grade(plan, claims, oracle, expected_plan_sha256=pin)}
        scenarios[scenario] = {"scientific_result": False, "arms": arms}
    return scenarios


if __name__ == "__main__":
    print(json.dumps(demo(), sort_keys=True, indent=2, allow_nan=False))
