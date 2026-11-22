"""Check exact paired discordance arithmetic on the scripted L3-B report."""

import argparse
from fractions import Fraction
from hashlib import sha256
from itertools import combinations
import json
from math import comb
from pathlib import Path

from lab.replication_inventory import _metadata, _object, _require


CELLS = ("both", "selected_only", "top_only", "neither")
ARMS = ("top", "selected")
TARGET = Fraction(1, 20)
MAX_SCRIPTED_PAIRS = 4096


def _rational(value):
    _object(value, ("numerator", "denominator"), "rate")
    _require(all(type(part) is int for part in value.values()) and value["denominator"] > 0, "invalid rate")
    return Fraction(value["numerator"], value["denominator"])


def _table(case, split, marginal, rate):
    table = _object(case[f"paired_{split}_flags"], CELLS, f"paired {split} table")
    denominator = case[f"heldout_{split}_count"]
    _require(type(denominator) is int and denominator > 0
             and all(type(count) is int and count >= 0 for count in table.values())
             and sum(table.values()) == denominator, f"invalid paired {split} count")
    for arm in ARMS:
        count = case["arms"][arm][marginal]
        _require(type(count) is int and count == table["both"] + table[f"{arm}_only"]
                 and _rational(case["arms"][arm][rate]) == Fraction(count, denominator),
                 f"paired {split} table differs from the reported margin")
    return table


def _inventory(values, label, minimum=1):
    _require(type(values) is list and len(values) >= minimum
             and all(type(value) is str and value.strip() for value in values)
             and len(set(values)) == len(values), f"invalid {label} inventory")
    return values


def _calibration_selection(fit, views, count):
    catches = _object(fit["calibration_individual_catches"], views, "calibration catch inventory")
    _require(all(type(value) is int and 0 <= value <= count for value in catches.values()),
             "invalid calibration catch counts")
    expected = set(combinations(sorted(views), 2))
    joint = {}
    rows = fit["calibration_joint_misses"]
    _require(type(rows) is list, "invalid calibration pair inventory")
    for row in rows:
        _object(row, ("pair", "misses"), "calibration pair")
        pair = tuple(_inventory(row["pair"], "calibration pair", minimum=2))
        _require(pair in expected and pair not in joint, "invalid or duplicate calibration pair")
        misses = row["misses"]
        first, second = (catches[view] for view in pair)
        _require(type(misses) is int and max(0, count - first - second) <= misses <= count - max(first, second),
                 "calibration joint misses contradict the individual catches")
        joint[pair] = misses
    _require(joint.keys() == expected, "calibration pair inventory is incomplete")
    ranked = sorted(views, key=lambda view: (-catches[view], view))
    first, second = ranked[:2]
    alternate = min((view for view in views if view != first),
                    key=lambda view: (joint[tuple(sorted((first, view)))], view))
    return {"top": [first, second], "selected": [first, alternate]}, joint


def _threshold_fit_rates(case):
    fit = case["fit"]
    raw = json.dumps(fit, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    _require(sha256(raw).hexdigest() == case["plan_sha256"], "inner plan digest differs from threshold fit")
    _require(_rational(fit["target_false_positive_rate"]) == TARGET, "threshold-fit target differs")
    identifiers = _inventory(fit["threshold_fit_clean_ids"], "threshold-fit clean")
    calibration = _inventory(fit["calibration_failure_ids"], "calibration failure")
    _require(set(identifiers).isdisjoint(calibration), "calibration and clean fit inventories overlap")
    views = _inventory(fit["view_ids"], "monitor view", minimum=2)
    expected_pairs, joint_misses = _calibration_selection(fit, views, len(calibration))
    fit_arms = _object(fit["arms"], ARMS, "threshold-fit arms")
    expected_calls = {
        "calibration_failure": len(views) * len(calibration),
        "threshold_fit_clean": 2 * len(identifiers),
        "heldout_clean": 2 * case["heldout_clean_count"],
        "heldout_failure": 2 * case["heldout_failure_count"],
    }
    expected_calls["total"] = sum(expected_calls.values())
    rates = []
    for arm in ARMS:
        point = _object(fit_arms[arm], ("pair", "cutoff", "calibration_joint_misses",
                                      "threshold_fit_false_positives"), "threshold-fit operating point")
        reported = case["arms"][arm]
        pair, cutoff, misses = (point[field] for field in ("pair", "cutoff", "calibration_joint_misses"))
        _require(pair == expected_pairs[arm] and type(cutoff) is int and 0 <= cutoff <= 2
                 and type(misses) is int and misses == joint_misses[tuple(sorted(pair))],
                 "threshold-fit point differs from the calibration selection or binary score range")
        _require(all(type(reported[field]) is type(point[field]) and reported[field] == point[field]
                     for field in ("pair", "cutoff", "calibration_joint_misses")),
                 "reported operating point differs from the pinned fit")
        calls = _object(reported["call_counts"], expected_calls, "scripted call charge")
        _require(all(type(calls[field]) is int and calls[field] == expected for field, expected in expected_calls.items()),
                 "scripted call charge differs from the planned view and sample counts")
        count, copy = point["threshold_fit_false_positives"], reported["threshold_fit_false_positives"]
        _require(type(count) is int and 0 <= count <= len(identifiers)
                 and type(copy) is int and copy == count, "threshold-fit count differs from the pinned fit")
        _require(cutoff < 2 or count == reported["heldout_false_positives"] == reported["heldout_catches"] == 0,
                 "maximum binary cutoff cannot produce flags")
        rate = Fraction(count, len(identifiers))
        _require(_rational(reported["threshold_fit_false_positive_rate"]) == rate,
                 "threshold-fit rate differs from the verified count and denominator")
        rates.append(rate)
    return rates


def conditional_two_sided(top_only, selected_only):
    """Exact two-sided sign tail under independent exchangeable discordant pairs."""
    _require(all(type(count) is int and count >= 0 for count in (top_only, selected_only)),
             "discordance counts must be nonnegative integers")
    discordant = top_only + selected_only
    _require(discordant <= MAX_SCRIPTED_PAIRS, "too many scripted pairs for exact calculation")
    smaller = min(top_only, selected_only)
    tail = sum(comb(discordant, count) for count in range(smaller + 1))
    return min(Fraction(1), Fraction(2 * tail, 2**discordant))


def verify(report, *, report_sha256):
    source = _object(_metadata(Path(report), report_sha256), ("scope", "scientific_result", "cases"),
                     "scripted L3 report")
    _require(source["scope"] == "L3_B_fallback_development" and source["scientific_result"] is False,
             "expected scripted L3-B fallback evidence")
    _require(type(source["cases"]) is dict and source["cases"], "expected scripted L3 cases")
    cases = {}
    for label, case in source["cases"].items():
        _object(case["arms"], ARMS, "L3 monitor arms")
        clean = _table(case, "clean", "heldout_false_positives", "heldout_false_positive_rate")
        failure = _table(case, "failure", "heldout_catches", "heldout_catch_rate")
        fit_rates = _threshold_fit_rates(case)
        matched = all(rate == TARGET for rate in fit_rates) and all(
            Fraction(clean["both"] + clean[f"{arm}_only"], case["heldout_clean_count"]) == TARGET for arm in ARMS
        )
        _require(case["heldout_target_matched"] is matched, "reported matched operating point differs")
        gain = Fraction(failure["selected_only"] - failure["top_only"], case["heldout_failure_count"])
        if matched:
            _require(_rational(case["heldout_catch_gain"]) == gain, "reported catch gain differs")
        else:
            _require(case["heldout_catch_gain"] is None, "unmatched operating point must withhold gain")
        cases[label] = {
            "clean_discordant_pairs": clean["selected_only"] + clean["top_only"],
            "failure_discordant_pairs": failure["selected_only"] + failure["top_only"],
            "catch_gain_at_matched_target": str(gain) if matched else None,
            "illustrative_two_sided_tail": (
                str(conditional_two_sided(failure["top_only"], failure["selected_only"])) if matched else None
            ),
            "illustrative_minimum_tail_at_fixture_size": (
                str(conditional_two_sided(0, case["heldout_failure_count"])) if matched else None
            ),
        }
    return {"report_sha256": report_sha256, "cases": cases, "scientific_acceptance": False,
            "assumption": "independent_exchangeable_discordant_pairs_for_illustration_only"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--report-sha256", required=True)
    args = parser.parse_args()
    try:
        result = verify(**vars(args))
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
