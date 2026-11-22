"""Check exact paired discordance arithmetic on the scripted L3-B report."""

import argparse
from fractions import Fraction
from hashlib import sha256
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


def _threshold_fit_rates(case):
    fit = case["fit"]
    raw = json.dumps(fit, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    _require(sha256(raw).hexdigest() == case["plan_sha256"], "inner plan digest differs from threshold fit")
    _require(_rational(fit["target_false_positive_rate"]) == TARGET, "threshold-fit target differs")
    identifiers = fit["threshold_fit_clean_ids"]
    _require(type(identifiers) is list and identifiers
             and all(type(identifier) is str and identifier.strip() for identifier in identifiers)
             and len(set(identifiers)) == len(identifiers), "invalid threshold-fit clean inventory")
    fit_arms = _object(fit["arms"], ARMS, "threshold-fit arms")
    rates = []
    for arm in ARMS:
        count = fit_arms[arm]["threshold_fit_false_positives"]
        reported = case["arms"][arm]
        copy = reported["threshold_fit_false_positives"]
        _require(type(count) is int and 0 <= count <= len(identifiers)
                 and type(copy) is int and copy == count, "threshold-fit count differs from the pinned fit")
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
