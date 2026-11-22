"""Classify scripted recovery observations on an elapsed-night grid."""


def classify(samples, *, horizon, hold, terminal):
    """Record the first confirmed recovery or the reason it remains unobserved."""
    if type(horizon) is not int or horizon < 0 or type(hold) is not int or hold < 1:
        raise ValueError("recovery horizon and hold need nonnegative and positive integers, respectively")
    if type(terminal) is not str or terminal not in ("window_complete", "operational_stop"):
        raise ValueError("unknown recovery window terminal")
    if type(samples) is not list:
        raise ValueError("recovery samples must be an ordered list")

    last_night = -1
    first_unknown = streak_start = first_hold = None
    explicit_unknown = 0
    for sample in samples:
        if type(sample) is not dict or sample.keys() != {"night", "predicate"}:
            raise ValueError("unexpected recovery sample fields")
        night, predicate = sample["night"], sample["predicate"]
        if type(night) is not int or not last_night < night <= horizon:
            raise ValueError("recovery nights must increase within the observed horizon")
        if predicate is not None and type(predicate) is not bool:
            raise ValueError("recovery predicate must be Boolean or null")
        if night != last_night + 1:
            if first_unknown is None:
                first_unknown = last_night + 1
            streak_start = None
        if predicate is None:
            explicit_unknown += 1
            if first_unknown is None:
                first_unknown = night
        if predicate is True:
            if streak_start is None:
                streak_start = night
            if first_hold is None and night - streak_start + 1 == hold:
                first_hold = (streak_start, night)
        else:
            streak_start = None
        last_night = night
    if last_night < horizon and first_unknown is None:
        first_unknown = last_night + 1

    result = {
        "status": None, "endpoint": "confirmation_night", "horizon": horizon, "hold": hold, "terminal": terminal,
        "onset_night": None, "confirmation_night": None, "candidate_onset_night": None,
        "candidate_confirmation_night": None, "censor_night": None,
        "unconfirmed_onset_night": None, "unconfirmed_streak_nights": 0,
        "known_nights": len(samples) - explicit_unknown, "explicit_unknown_nights": explicit_unknown,
        "omitted_nights": horizon + 1 - len(samples), "first_unknown_night": first_unknown,
        "scientific_result": False,
    }
    if first_hold is not None:
        onset, confirmation = first_hold
        if first_unknown is None or confirmation < first_unknown:
            return result | {"status": "recovered", "onset_night": onset, "confirmation_night": confirmation}
        result.update(candidate_onset_night=onset, candidate_confirmation_night=confirmation)
    if terminal == "operational_stop":
        return result | {"status": "operational_truncation"}
    if first_hold is None and last_night == horizon and streak_start is not None:
        result.update(unconfirmed_onset_night=streak_start, unconfirmed_streak_nights=horizon - streak_start + 1)
    if first_unknown is not None:
        return result | {"status": "incomplete_followup"}
    return result | {"status": "right_censored", "censor_night": horizon}
