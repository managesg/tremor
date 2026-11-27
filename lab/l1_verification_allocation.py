"""Scripted equal-budget L1 verification placement and independent outcome scoring."""

from dataclasses import dataclass
import hashlib
import json

from tremor.readouts import overdispersion

MODES = ("overdispersion", "uniform", "disagreement", "majority_retry")
ADDITIONAL_CHECK_MODES = ("random", "length", "team_size", "pilot_predictor", "proportional")
MEASURED_MODES = ("overdispersion", "disagreement", "pilot_predictor", "proportional")
CHECK_COST = 4
MEASUREMENT_COST = RETRY_COST = 1
RETRIES = 2


@dataclass(frozen=True)
class Claim:
    identifier: str
    stratum: str
    claimed_complete: bool


@dataclass(frozen=True)
class Outcome:
    legitimate: bool
    checker: bool | None
    retries: tuple[bool | None, bool | None]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _claim_inventory(claims):
    if (not claims or any(not isinstance(claim, Claim) or not isinstance(claim.identifier, str) or not claim.identifier
                          or not isinstance(claim.stratum, str) or not claim.stratum
                          or type(claim.claimed_complete) is not bool for claim in claims)
            or len({claim.identifier for claim in claims}) != len(claims)):
        raise ValueError("invalid or duplicate scheduled completion claim")
    return [[claim.identifier, claim.stratum, claim.claimed_complete] for claim in claims]


def _measure(calibration, claims, mode):
    strata = {claim.stratum for claim in claims}
    if set(calibration) != strata:
        raise ValueError("calibration does not cover each scheduled stratum")
    measured, scores, ids = 0, {}, set()
    for stratum, groups in calibration.items():
        outcomes = []
        for identifier, reruns in groups:
            if (not isinstance(identifier, str) or identifier in ids or not identifier.startswith("cal-")
                    or len(reruns) < 10 or any(type(value) is not int or value not in (0, 1) for value in reruns)):
                raise ValueError("invalid independent calibration group")
            ids.add(identifier)
            measured += len(reruns)
            outcomes.append(reruns)
        if len(outcomes) < 2 or len({len(group) for group in outcomes}) != 1:
            raise ValueError("need matched reruns across at least two calibration groups")
        if mode == "overdispersion":
            scores[stratum] = overdispersion(outcomes)
        else:
            rates = [sum(group) / len(group) for group in outcomes]
            scores[stratum] = sum(rate * (1 - rate) for rate in rates) / len(rates)
    if ids & {claim.identifier for claim in claims}:
        raise ValueError("calibration and assessment identifiers overlap")
    return measured * MEASUREMENT_COST, scores


def make_plan(claims, calibration, *, mode, budget):
    """Commit policy choices using claims and observed calibration, without outcome labels."""
    claims = tuple(claims)
    inventory = _claim_inventory(claims)
    if mode not in MODES or type(budget) is not int or budget < 0:
        raise ValueError("unknown allocation mode or invalid synthetic cap")
    measured, scores = 0, {}
    order = claims
    if mode in ("overdispersion", "disagreement"):
        measured, scores = _measure(calibration, claims, mode)
        if measured > budget:
            raise ValueError("cap cannot cover the proposed calibration")
        order = sorted(claims, key=lambda claim: -scores[claim.stratum])
    if mode == "majority_retry":
        action, price = "retry_pair", RETRIES * RETRY_COST
    else:
        action, price = "check", CHECK_COST
    choices = [{"claim_id": claim.identifier, "stratum": claim.stratum, "action": action, "cost": price}
               for claim in order[:(budget - measured) // price]]
    spent = measured + sum(choice["cost"] for choice in choices)
    return {"mode": mode, "budget": budget, "measurement_spent": measured, "allocated": spent,
            "unused": budget - spent, "scores": scores, "choices": choices,
            "calibration_sha256": digest(calibration) if measured else None,
            "claim_inventory_sha256": digest(inventory)}


def grade(plan, claims, oracle, *, expected_plan_sha256):
    claims = tuple(claims)
    inventory = _claim_inventory(claims)
    if digest(plan) != expected_plan_sha256 or plan["claim_inventory_sha256"] != digest(inventory):
        raise ValueError("completion allocation or claim inventory pin differs")
    if set(oracle) != {claim.identifier for claim in claims}:
        raise ValueError("grader needs one independently recorded outcome specification per claim")
    selected = {choice["claim_id"]: choice for choice in plan["choices"]}
    if len(selected) != len(plan["choices"]) or not selected.keys() <= oracle.keys():
        raise ValueError("allocation contains duplicated or unknown claims")
    action = "retry_pair" if plan["mode"] == "majority_retry" else "check"
    cost = RETRIES * RETRY_COST if action == "retry_pair" else CHECK_COST
    measurement = plan["measurement_spent"]
    if (plan["mode"] not in MODES + ADDITIONAL_CHECK_MODES or type(measurement) is not int or measurement < 0
            or (bool(measurement) != (plan["mode"] in MEASURED_MODES))):
        raise ValueError("allocation measurement cost does not reconcile")
    expected_spend = measurement + len(selected) * cost
    if (plan["allocated"] != expected_spend
            or plan["unused"] != plan["budget"] - expected_spend or plan["unused"] < 0):
        raise ValueError("allocation cost does not reconcile")

    rows = []
    unknown_checks = 0
    retry_returns = 0
    for claim in claims:
        outcome = oracle[claim.identifier]
        if (not isinstance(outcome, Outcome) or type(outcome.legitimate) is not bool
                or (outcome.checker is not None and type(outcome.checker) is not bool)
                or len(outcome.retries) != RETRIES
                or any(result is not None and type(result) is not bool for result in outcome.retries)):
            raise ValueError("invalid grader outcome specification")
        choice = selected.get(claim.identifier)
        complete, received = claim.claimed_complete, None
        if choice is not None:
            if (choice["stratum"], choice["action"], choice["cost"]) != (claim.stratum, action, cost):
                raise ValueError("allocated action does not match the recorded opportunity")
            if action == "check":
                received = outcome.checker
                if received is None:
                    unknown_checks += 1
                else:
                    complete = received
            else:
                received = outcome.retries
                retry_returns += sum(value is not None for value in received)
                votes = [claim.claimed_complete, *(vote for vote in received if vote is not None)]
                yes, no = sum(votes), len(votes) - sum(votes)
                complete = True if yes > no and yes >= 2 else False if no > yes and no >= 2 else None
        rows.append({"claim_id": claim.identifier, "action": choice["action"] if choice else None,
                     "returned": received, "final_completion": complete, "legitimate": outcome.legitimate})
    return {
        "scheduled": len(rows), "checks": len(selected) if action == "check" else 0,
        "retried": len(selected) * RETRIES if action == "retry_pair" else 0, "retry_returns": retry_returns,
        "unknown_checks": unknown_checks,
        "undetected_false_completions": sum(row["final_completion"] is True and not row["legitimate"] for row in rows),
        "missed_legitimate": sum(row["final_completion"] is False and row["legitimate"] for row in rows),
        "unresolved_completions": sum(row["final_completion"] is None for row in rows), "outcomes": rows,
    }


def relative_reduction(candidate, baseline):
    return None if baseline == 0 else (baseline - candidate) / baseline


def development_inputs():
    calibration = {"stable": (("cal-s0", (0, 1) * 5), ("cal-s1", (1, 0) * 5)),
                   "variable": (("cal-v0", (0,) * 10), ("cal-v1", (1,) * 10))}
    claims = tuple(Claim(f"test-{index:02d}", "stable" if index % 2 == 0 else "variable", True) for index in range(32))
    return claims, calibration


def demo():
    claims, calibration = development_inputs()
    scenarios = {}
    for case, false_claims in (("positive", {1, 3, 5, 7}), ("null", set())):
        arms = {}
        for mode in MODES:
            plan = make_plan(claims, calibration, mode=mode, budget=56)
            pin = digest(plan)
            oracle = {claim.identifier: Outcome(index not in false_claims, None if index == 7 else index not in false_claims,
                                                (False, None) if index == 7 else (index not in false_claims,) * 2)
                      for index, claim in enumerate(claims)}
            arms[mode] = {"plan": plan, "plan_sha256": pin,
                          "metrics": grade(plan, claims, oracle, expected_plan_sha256=pin)}
        uniform = arms["uniform"]["metrics"]["undetected_false_completions"]
        scenarios[case] = {"scientific_result": False, "arms": arms, "overdispersion_vs_uniform": relative_reduction(
            arms["overdispersion"]["metrics"]["undetected_false_completions"], uniform)}
    return scenarios


if __name__ == "__main__":
    print(json.dumps(demo(), sort_keys=True, indent=2, allow_nan=False))
