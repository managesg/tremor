"""Verify matched development recovery records and their restricted-window arithmetic."""

import argparse
import json
from pathlib import Path

from lab import adapter_lineage, l4b_recovery, l4b_restricted_math


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _ratio(value):
    return None if value is None else {"numerator": value.numerator, "denominator": value.denominator}


def _matches(match, lower, near):
    _require(type(match["pairs"]) is list and bool(match["pairs"]), "restricted comparison requires scheduled pairs")
    lower_rows, near_rows = ({row["chain_id"]: row for row in arm["chains"]} for arm in (lower, near))
    _require(lower_rows.keys().isdisjoint(near_rows), "matched arm chain identities must be distinct")
    seen_pairs, seen_families, seen_lower, seen_near = set(), set(), set(), set()
    result = []
    for item in match["pairs"]:
        l4b_recovery._fields(item, "pair_id family_id lower_chain_id near_chain_id")
        pair, family, lower_id, near_id = (l4b_recovery._identifier(item[key]) for key in (
            "pair_id", "family_id", "lower_chain_id", "near_chain_id",
        ))
        _require(pair not in seen_pairs and family not in seen_families and lower_id not in seen_lower
                 and near_id not in seen_near and lower_id in lower_rows and near_id in near_rows,
                 "pair has duplicate identity, crossed arm or missing scheduled mate")
        seen_pairs.add(pair)
        seen_families.add(family)
        seen_lower.add(lower_id)
        seen_near.add(near_id)
        result.append({"pair_id": pair, "family_id": family, "lower": lower_rows[lower_id], "near": near_rows[near_id]})
    _require(seen_lower == lower_rows.keys() and seen_near == near_rows.keys(),
             "restricted match does not cover exactly the two scheduled arm inventories")
    return result


def verify(match, lower_design, lower_obs, near_design, near_obs, *, match_sha256):
    """Bind both arm roles and every scheduled pair before calculating a development ratio."""
    document = adapter_lineage._json(Path(match), match_sha256)
    l4b_recovery._fields(document, "schema scope tau lower_design_sha256 lower_observations_sha256 "
                                  "near_design_sha256 near_observations_sha256 pairs")
    _require(document["schema"] == "l4b_restricted_match_v1" and document["scope"] == "scripted_development",
             "unexpected restricted recovery scope")
    tau = document["tau"]
    _require(type(tau) is int and tau > 0, "restricted comparison needs a positive common horizon")
    lower = l4b_recovery.verify(lower_design, lower_obs, design_sha256=document["lower_design_sha256"],
                                observations_sha256=document["lower_observations_sha256"])
    near = l4b_recovery.verify(near_design, near_obs, design_sha256=document["near_design_sha256"],
                               observations_sha256=document["near_observations_sha256"])
    _require(lower["scorer_sha256"] == near["scorer_sha256"], "restricted arms use different scorer pins")
    rules = {(row["horizon"], row["hold"], row["endpoint"]) for arm in (lower, near) for row in arm["chains"]}
    _require(len(rules) == 1, "restricted arms use different observation rules")
    horizon, hold, endpoint = next(iter(rules))
    _require(tau <= horizon, "restriction horizon exceeds the common observation horizon")
    pairs = _matches(document, lower, near)
    result = l4b_restricted_math.calculate(pairs, tau=tau)
    for field in ("lower_mean", "near_mean", "near_over_lower", "near_minus_lower"):
        result[field] = _ratio(result[field])
    return {
        **result,
        "match_sha256": match_sha256, "scorer_sha256": lower["scorer_sha256"],
        "observation_horizon": horizon, "hold": hold, "endpoint": endpoint,
        "lower_design_sha256": lower["design_sha256"], "lower_observations_sha256": lower["observations_sha256"],
        "near_design_sha256": near["design_sha256"], "near_observations_sha256": near["observations_sha256"],
        "scientific_ratio": None, "scientific_interval": None, "authorizes_execution": False,
        "independent_custody_verified": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("match", "lower_design", "lower_obs", "near_design", "near_obs"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--match-sha256", required=True)
    args = parser.parse_args()
    try:
        result = verify(args.match, args.lower_design, args.lower_obs, args.near_design, args.near_obs,
                        match_sha256=args.match_sha256)
    except (KeyError, OSError, TypeError, ValueError, ZeroDivisionError) as error:
        parser.exit(2, f"{error}\n")
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
