"""Describe output length and exact-array adherence in supplied pilot turn records."""

import json
import sys

from lab.pilot_clearance import CORE, OUTPUT_CEILING
from tremor import ep1

CONDITIONS = CORE + tuple(ep1.PILOT_CARDS)


def _reject_nonfinite(value):
    raise ValueError(f"nonfinite JSON constant: {value}")


def _unique_object(pairs):
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError("repeated JSON object key")
    return result


def _array_only(reply):
    # Compare the whole supplied reply after discarding JSON whitespace only.
    reply = reply.strip(" \t\r\n")
    try:
        decoded = json.loads(reply, parse_constant=_reject_nonfinite, object_pairs_hook=_unique_object)
    except (ValueError, RecursionError):
        return False
    return isinstance(decoded, list)


def _describe(turns):
    second_round = [turn for turn in turns if turn["round"] == 1]
    return {
        "recorded_turns": len(turns),
        "max_output_tokens": max((turn["usage"]["output_tokens"] for turn in turns), default=None),
        "above_ceiling_call_ids": sorted(turn["call_id"] for turn in turns
                                         if turn["usage"]["output_tokens"] > OUTPUT_CEILING),
        "max_tokens_stop_call_ids": sorted(turn["call_id"] for turn in turns
                                           if turn["stop_reason"] == "max_tokens"),
        "second_round_turns": len(second_round),
        "second_round_non_array_call_ids": sorted(turn["call_id"] for turn in second_round
                                                   if not _array_only(turn["reply"])),
    }


def describe(records):
    """Describe supplied records in both scopes without judging pilot clearance.

    Each record contains cond, call_id, zero-based round, usage.output_tokens,
    stop_reason and the complete reply text. Provenance and schedule coverage
    are established outside this diagnostic. Array shape is independent of the
    action parser and does not validate decoded actions. Historical driver
    excerpts capped at 1,200 characters are insufficient as complete replies.
    """
    turns = list(records)
    seen = set()
    for turn in turns:
        if not isinstance(turn, dict):
            raise ValueError("each turn must be an object")
        call_id = turn.get("call_id")
        if not isinstance(call_id, str) or not call_id.strip() or call_id in seen:
            raise ValueError("turn requires a unique nonblank call_id")
        seen.add(call_id)
        if turn.get("cond") not in CONDITIONS or type(turn.get("round")) is not int or turn["round"] not in (0, 1):
            raise ValueError(f"unknown condition or round: {call_id}")
        usage = turn.get("usage")
        output = usage.get("output_tokens") if isinstance(usage, dict) else None
        if type(output) is not int or output < 0:
            raise ValueError(f"missing or invalid output_tokens: {call_id}")
        stop = turn.get("stop_reason")
        if not isinstance(turn.get("reply"), str) or not isinstance(stop, str) or not stop.strip():
            raise ValueError(f"missing reply or stop reason: {call_id}")

    by_condition = {condition: [turn for turn in turns if turn["cond"] == condition]
                    for condition in CONDITIONS}
    return {
        "output_token_ceiling": OUTPUT_CEILING,
        "all_conditions": _describe(turns),
        "core": _describe([turn for condition in CORE for turn in by_condition[condition]]),
        "per_condition": {condition: _describe(cell) for condition, cell in by_condition.items()},
    }


if __name__ == "__main__":
    records = json.load(sys.stdin, object_pairs_hook=_unique_object, parse_constant=_reject_nonfinite)
    if not isinstance(records, list):
        raise ValueError("expected a JSON array of turn records")
    print(json.dumps(describe(records), indent=2, sort_keys=True, allow_nan=False))
