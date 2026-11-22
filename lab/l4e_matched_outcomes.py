"""Summarize pinned L4-E public matched adapter and context outcomes."""

import argparse
from fractions import Fraction
import json
from pathlib import Path

from lab.l4b_recovery_observation import classify
from lab.replication_inventory import _hex, _metadata, _object, _require
from lab.replication_pairing import _identifier


PLAN_SCHEMA = "tremor.l4e_matched_outcome_plan.v1"
RECOVERY_PLAN_SCHEMA = "tremor.l4e_matched_outcome_plan.v2"
OBSERVATION_SCHEMA = "tremor.l4e_matched_outcome_observations.v1"
RECOVERY_WITNESS_SCHEMA = "tremor.l4e_matched_recovery_witness.v1"
ARMS = ("adapter", "context")
IDENTITY = ("pair_id", "task_sha256", "seed_sha256")
PINS = ("scorer_sha256", "l4e_receipt_sha256", "content_parity_sha256")
USAGE = ("input_tokens", "output_tokens", "gpu_wall_ns")


def _identity(row):
    return _identifier(row["pair_id"]), tuple(_hex(row[field], 64) for field in IDENTITY[1:])


def _norm(value):
    _object(value, ("passed", "reason"), "sibling-norm outcome")
    passed, reason = value["passed"], value["reason"]
    _require((type(passed) is bool and reason is None)
             or (passed is None and type(reason) is str and bool(reason.strip())), "invalid sibling-norm outcome")
    return value


def _recovery(value, horizon):
    _object(value, ("state", "confirmation_night", "observed_through_night", "reason"), "recovery observation")
    state, night, through, reason = (value[field] for field in
                                    ("state", "confirmation_night", "observed_through_night", "reason"))
    _require((type(through) is int and 0 <= through <= horizon)
             or (through is None and state == "unavailable"), "invalid recovery follow-up")
    if state == "recovered":
        _require(type(night) is int and 0 <= night <= through and reason is None, "invalid confirmed recovery")
        return night
    if state == "right_censored":
        _require(night is None and through == horizon and reason is None,
                 "administrative censoring requires full follow-up")
        return horizon
    _require(state == "unavailable" and night is None and type(reason) is str and bool(reason.strip()),
             "unavailable recovery requires an explicit reason")
    return None


def _usage_totals(rows, arm):
    result = {}
    for resource in USAGE:
        values = [row[arm]["usage"][resource] for row in rows]
        known, missing = sum(value for value in values if value is not None), values.count(None)
        result[resource] = {"known_subtotal": known, "unavailable_records": missing,
                            "complete_total": None if missing else known}
    return result


def _contrast(rows, field):
    complete = [row for row in rows if all(row[arm][field] is not None for arm in ARMS)]
    means = dict.fromkeys(ARMS)
    difference = ratio = None
    reason = "incomplete_matched_outcomes"
    if len(complete) == len(rows):
        means = {arm: Fraction(sum(row[arm][field] for row in rows), len(rows)) for arm in ARMS}
        difference = means["adapter"] - means["context"]
        if field == "restricted_nights":
            ratio = means["adapter"] / means["context"] if means["context"] else None
            reason = None if ratio is not None else "zero_context_mean"
        else:
            reason = None
    return {"complete_pairs": len(complete),
            "means": {arm: None if count is None else str(count) for arm, count in means.items()},
            "adapter_minus_context": None if difference is None else str(difference),
            **({"adapter_over_context": None if ratio is None else str(ratio)} if field == "restricted_nights" else {}),
            "unavailable_reason": reason}


def _recovery_witness(reference, *, plan_sha256, observations_sha256, expected, horizon, hold):
    path, pin = reference
    witness = _object(_metadata(Path(path), pin), ("schema", "plan_sha256", "observations_sha256", "hold", "rows"),
                      "L4-E recovery witness")
    _require(witness["schema"] == RECOVERY_WITNESS_SCHEMA and witness["plan_sha256"] == plan_sha256
             and witness["observations_sha256"] == observations_sha256,
             "recovery witness does not bind the matched plan and observations")
    _require(type(witness["hold"]) is int and witness["hold"] == hold,
             "recovery witness hold differs from frozen plan")
    _require(type(witness["rows"]) is list, "invalid recovery witness rows")
    matched = {}
    for row in witness["rows"]:
        _object(row, (*IDENTITY, "arm", "terminal", "samples"), "L4-E recovery history")
        pair, match = _identity(row)
        key = pair, _identifier(row["arm"])
        _require(key in expected and key not in matched and expected[key][0] == match,
                 "unexpected, duplicate or mismatched recovery history")
        observed = classify(row["samples"], horizon=horizon, hold=hold, terminal=row["terminal"])
        status = observed["status"]
        first_unknown = observed["first_unknown_night"]
        continuous_through = horizon if first_unknown is None else first_unknown - 1
        state = status if status in ("recovered", "right_censored") else "unavailable"
        declaration = expected[key][1]
        _require((declaration["state"], declaration["confirmation_night"], declaration["observed_through_night"])
                 == (state, observed["confirmation_night"], None if continuous_through < 0 else continuous_through),
                 "matched recovery differs from observed confirmation or continuous follow-up")
        matched[key] = {"pair_id": pair, "arm": key[1], "classification": status,
                        "continuous_through_night": None if continuous_through < 0 else continuous_through,
                        "terminal": observed["terminal"],
                        "latest_sampled_night": row["samples"][-1]["night"] if row["samples"] else None,
                        "known_nights": observed["known_nights"], "confirmation_night": observed["confirmation_night"],
                        "candidate_confirmation_night": observed["candidate_confirmation_night"]}
    _require(matched.keys() == expected.keys(), "recovery witness must contain every scheduled arm history")
    return {"witness_sha256": pin, "hold_nights": hold, "matched_arm_histories": len(matched),
            "histories": [matched[key] for key in expected], "native_capture_verified": False}


def verify(plan_path, observations_path, *, plan_sha256, observations_sha256, recovery_witness=None):
    """Verify paired public readouts without accepting protocol or settlement claims."""
    plan = _metadata(Path(plan_path), plan_sha256)
    witnessed = plan.get("schema") == RECOVERY_PLAN_SCHEMA
    fields = ("schema", "scope", *PINS, "horizon_nights", "pairs")
    _object(plan, (*fields, "recovery_hold_nights") if witnessed else fields, "L4-E matched outcome plan")
    _require(witnessed == (recovery_witness is not None), "frozen recovery plan and recovery witness are both required")
    hold = plan.get("recovery_hold_nights")
    _require(not witnessed or (type(hold) is int and hold >= 1), "invalid frozen recovery hold")
    records = _object(_metadata(Path(observations_path), observations_sha256), ("schema", *PINS, "plan_sha256", "rows"),
                      "L4-E matched observations")
    horizon = plan["horizon_nights"]
    _require(plan["schema"] in (PLAN_SCHEMA, RECOVERY_PLAN_SCHEMA) and records["schema"] == OBSERVATION_SCHEMA
             and plan["scope"] == "scripted_development" and records["plan_sha256"] == plan_sha256
             and type(horizon) is int and horizon > 0,
             "wrong L4-E plan, observation schema or recovery horizon")
    _require(all(records[field] == _hex(plan[field], 64) for field in PINS), "scorer or L4-E receipt differs")
    _require(type(plan["pairs"]) is list and plan["pairs"] and type(records["rows"]) is list,
             "expected L4-E matched pair and observation inventories")
    expected = {}
    assignments = set()
    for row in plan["pairs"]:
        pair, match = _identity(_object(row, IDENTITY, "L4-E scheduled pair"))
        _require(pair not in expected and match not in assignments, "duplicate scheduled pair or task and seed")
        expected[pair] = match
        assignments.add(match)
    outcomes = {pair: {} for pair in expected}
    recovery_declarations = {}
    for row in records["rows"]:
        _object(row, (*IDENTITY, "arm", "norm", "recovery", "usage"), "L4-E observed arm")
        pair, match = _identity(row)
        arm = _identifier(row["arm"])
        _require(expected.get(pair) == match and arm in ARMS and arm not in outcomes[pair],
                 "unexpected, duplicate or mismatched observed arm")
        usage = _object(row["usage"], USAGE, "L4-E declared usage")
        _require(all(value is None or type(value) is int and value >= 0 for value in usage.values()),
                 "usage must be nonnegative or unavailable")
        norm = _norm(row["norm"])
        recovery_declarations[pair, arm] = (match, row["recovery"])
        outcomes[pair][arm] = {"norm_passed": norm["passed"], "norm_reason": norm["reason"],
                               "recovery": row["recovery"], "restricted_nights": _recovery(row["recovery"], horizon),
                               "usage": usage}
    _require(all(value.keys() == set(ARMS) for value in outcomes.values()), "record both arms for every scheduled pair")
    rows = [{"pair_id": pair, **arms} for pair, arms in outcomes.items()]
    report = {"evidence": "scripted_l4e_matched_outcomes", "plan_sha256": plan_sha256,
            "observations_sha256": observations_sha256, "horizon_nights": horizon, "pairs": rows,
            "evidence_pins": {field: plan[field] for field in PINS},
            "norm": _contrast(rows, "norm_passed"), "recovery": _contrast(rows, "restricted_nights"),
            "declared_usage": {arm: _usage_totals(rows, arm) for arm in ARMS},
            "native_execution_verified": False, "settlement_verified": False, "scientific_acceptance": False}
    if recovery_witness is not None:
        report["recovery_witness"] = _recovery_witness(
            recovery_witness, plan_sha256=plan_sha256, observations_sha256=observations_sha256,
            expected=recovery_declarations, horizon=horizon, hold=hold,
        )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan_path", type=Path)
    parser.add_argument("observations_path", type=Path)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--observations-sha256", required=True)
    parser.add_argument("--recovery-witness", nargs=2, metavar=("PATH", "SHA256"),
                        help="verify exact night histories against the matched outcome declarations")
    try:
        result = verify(**vars(parser.parse_args()))
    except (OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
