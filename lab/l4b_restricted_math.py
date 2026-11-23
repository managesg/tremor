"""Exact development arithmetic for administratively observed recovery pairs."""

from fractions import Fraction
from unicodedata import normalize


CLASSIFIER_FIELDS = set(
    "status endpoint horizon hold terminal onset_night confirmation_night candidate_onset_night "
    "candidate_confirmation_night censor_night unconfirmed_onset_night unconfirmed_streak_nights "
    "known_nights explicit_unknown_nights omitted_nights first_unknown_night scientific_result".split()
)


def _require(condition):
    if not condition:
        raise ValueError("invalid restricted recovery classifier state")


def _canonical_id(value):
    return type(value) is str and bool(value) and value == value.strip() and value == normalize("NFC", value)


def _known(value, minimum=0):
    return type(value) is int and value >= minimum


def _night(value, horizon):
    return value is None or (_known(value) and value <= horizon)


def _hold_time(row, onset_key, confirmation_key):
    onset, confirmation = row[onset_key], row[confirmation_key]
    if onset is None:
        _require(confirmation is None)
    else:
        _require(confirmation == onset + row["hold"] - 1)
    return onset, confirmation


def _check_state(row):
    _require(type(row) is dict and row.keys() in (CLASSIFIER_FIELDS, CLASSIFIER_FIELDS | {"chain_id"}))
    _require("chain_id" not in row or _canonical_id(row["chain_id"]))
    horizon, hold = row["horizon"], row["hold"]
    terminal, status = row["terminal"], row["status"]
    _require(_known(horizon) and _known(hold, 1) and type(terminal) is str
             and terminal in ("window_complete", "operational_stop")
             and row["endpoint"] == "confirmation_night" and row["scientific_result"] is False)
    night_keys = ("onset_night", "confirmation_night", "candidate_onset_night", "candidate_confirmation_night",
                  "censor_night", "unconfirmed_onset_night", "first_unknown_night")
    _require(all(_night(row[key], horizon) for key in night_keys))
    known, explicit, omitted = (row[key] for key in ("known_nights", "explicit_unknown_nights", "omitted_nights"))
    _require(all(_known(value) for value in (known, explicit, omitted)) and known + explicit + omitted == horizon + 1)
    gap = row["first_unknown_night"]
    _require((gap is None) == (explicit + omitted == 0) and (gap is None or gap <= known))

    onset, confirmation = _hold_time(row, "onset_night", "confirmation_night")
    candidate, candidate_confirmation = _hold_time(row, "candidate_onset_night", "candidate_confirmation_night")
    if confirmation is not None:
        _require(status == "recovered" and (gap is None or confirmation < gap) and known >= hold
                 and candidate_confirmation is None)
    else:
        expected = ("operational_truncation" if terminal == "operational_stop"
                    else "right_censored" if gap is None else "incomplete_followup")
        _require(status == expected)
    if candidate is not None:
        _require(gap is not None and gap < candidate and known >= gap + hold)
    _require(row["censor_night"] == (horizon if status == "right_censored" else None))

    short_start, short_length = row["unconfirmed_onset_night"], row["unconfirmed_streak_nights"]
    _require(_known(short_length) and short_length < hold and (short_start is None) == (short_length == 0))
    if short_start is not None:
        _require(terminal == "window_complete" and confirmation is None and candidate_confirmation is None
                 and short_start + short_length == horizon + 1
                 and (gap is None or (gap < short_start and known >= gap + short_length)))


def _restrict(row, tau):
    try:
        _check_state(row)
    except ValueError:
        return {"restricted_nights": None, "reason": "invalid_state"}
    if row["terminal"] == "operational_stop":
        return {"restricted_nights": None, "reason": "operational_stop"}
    if row["horizon"] < tau:
        return {"restricted_nights": None, "reason": "insufficient_horizon"}
    gap = row["first_unknown_night"]
    if gap is not None and gap <= tau:
        return {"restricted_nights": None, "reason": "unknown_at_or_before_tau"}
    confirmation = row["confirmation_night"]
    return {"restricted_nights": tau if confirmation is None else min(confirmation, tau), "reason": None}


def calculate(pairs, *, tau):
    """Compute exact restricted-window means only for a fully observed matched inventory."""
    if not _known(tau):
        raise ValueError("restriction horizon must be a nonnegative integer")
    if type(pairs) is not list or not pairs:
        raise ValueError("restricted recovery needs a nonempty pair inventory")
    results, seen = [], set()
    for pair in pairs:
        if type(pair) is not dict or pair.keys() != {"pair_id", "family_id", "lower", "near"}:
            raise ValueError("unexpected restricted recovery pair fields")
        pair_id, family = pair["pair_id"], pair["family_id"]
        if not _canonical_id(pair_id) or not _canonical_id(family) or pair_id in seen:
            raise ValueError("restricted recovery pair IDs must be canonical and unique")
        seen.add(pair_id)
        results.append({"pair_id": pair_id, "family_id": family,
                        "lower": _restrict(pair["lower"], tau), "near": _restrict(pair["near"], tau)})

    eligible = sum(row["lower"]["reason"] is None and row["near"]["reason"] is None for row in results)
    lower = near = ratio = difference = None
    if eligible == len(results):
        lower, near = (Fraction(sum(row[arm]["restricted_nights"] for row in results), eligible)
                       for arm in ("lower", "near"))
        ratio = near / lower if lower else None
        difference = near - lower
    return {
        "status": "complete" if eligible == len(results) else "withheld_incomplete_pairs",
        "tau": tau, "pair_count": len(results), "eligible_pair_count": eligible, "pairs": results,
        "lower_mean": lower, "near_mean": near, "near_over_lower": ratio, "near_minus_lower": difference,
        "scientific_result": False,
    }
