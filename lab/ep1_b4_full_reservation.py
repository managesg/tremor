"""Exercise B4 reservations through the EP-1 driver at the loopback wire boundary."""

import argparse
import json
from pathlib import Path
from unittest.mock import patch

from lab.ep1_b4_probe import run_case
from tremor import ep1, team_claude as tc

INPUT_BYTES = 2_000
OUTPUT_TOKENS = 300
CANARY_TOKENS = 90_300
TRANSPORT_FAILURES = frozenset((7, 8, 23, 24))
# The first 12 calls use one transport retry. Complete two cells, then spend
# eight reservations in a third cell before its episode-level retry is denied.
NO_ROOM_FAILURES = frozenset((*range(1, 24, 2), 35, 36))
ORIGINAL_PROMPT = tc._ModelEpisode.prompt


def pad_prompt(episode, agent, round_index, view):
    """Add inert ASCII spaces to the synthetic system field, before sizing/reserve."""
    system, user = ORIGINAL_PROMPT(episode, agent, round_index, view)
    caps = episode.caps
    payload = {"system": system, "messages": [{"role": "user", "content": user}],
               "model": caps["model"], "temperature": caps["temperature"],
               "max_tokens": caps["output_tokens"], "thinking": caps["thinking"]}
    missing = INPUT_BYTES - len(json.dumps(payload, sort_keys=True).encode())
    if missing < 0:
        raise ValueError("fixture's original prompt exceeded the input boundary")
    return system + " " * missing, user


def run_probe(root, name, failed_requests, expected_calls, expected_aborts):
    wire_bytes = []

    def respond(path, headers, body, request_number):
        wire_bytes.append((int(headers["Content-Length"]), len(json.dumps(body, sort_keys=True).encode())))
        if request_number in failed_requests:
            return 503, {"error": {"message": "scripted transient outage"}}
        return ep1.worst_case_responder(path, headers, body, request_number)

    with patch.object(tc._ModelEpisode, "prompt", pad_prompt):
        final, calls, records = run_case(root, name, respond)
    assert calls == expected_calls
    assert wire_bytes == [(INPUT_BYTES, INPUT_BYTES)] * calls
    case = root / name
    entries = ep1._read_jsonl(str(case / "ledger" / "ep1.jsonl"))
    reserves = [row for row in entries if row["kind"] == "reserve"]
    charges = [row for row in entries if row["kind"] == "charge"]
    unmetered = [row for row in entries if row["kind"] == "unbilled_unknown"]
    assert len(reserves) == calls
    assert all((row["input_tokens_ub"], row["max_tokens"]) == (INPUT_BYTES, OUTPUT_TOKENS)
               for row in reserves)
    assert len(charges) == calls - len(failed_requests)
    assert all((row["usage"]["input_tokens"], row["usage"]["output_tokens"]) == (INPUT_BYTES, OUTPUT_TOKENS)
               for row in charges)
    assert {row["id"] for row in unmetered} == {reserves[index - 1]["id"] for index in failed_requests}
    assert final["ledger"]["tokens"] == CANARY_TOKENS + calls * (INPUT_BYTES + OUTPUT_TOKENS)

    aborted = [row for row in records if row["ended"] == "infrastructure_abort"]
    reruns = [row for row in records if row["attempt"] == 1]
    assert len(aborted) == expected_aborts == final["aborts"]
    if name == "full-schedule":
        assert final["reason"] == "inconclusive", final
        assert len(records) == 62 and len(reruns) == 2
        for before, after in zip(aborted, reruns, strict=True):
            assert (before["set"], before["cond"]) == (after["set"], after["cond"])
            assert after["id_tag"] == before["id_tag"] + "r1"
            assert after["episode_id"] != before["episode_id"]
    else:
        assert final["detail"] == "no_rerun_calls_left", final
        assert not reruns
        assert final["reason"] == "stopped:cap"
    return {"reason": final["reason"], "detail": final["detail"], "ep1_requests": calls,
            "nested_requests": final["ledger"]["calls"], "ep1_request_bytes": INPUT_BYTES,
            "ep1_reservations": len(reserves), "ep1_charged_responses": len(charges),
            "ep1_unmetered_reservations": len(unmetered), "nested_tokens": final["ledger"]["tokens"],
            "nested_usd": final["ledger"]["usd"], "remaining": final["ledger"]["remaining"],
            "episode_records": len(records), "episode_aborts": len(aborted), "episode_reruns": len(reruns)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path, help="new directory for the two offline cases")
    args = parser.parse_args()
    args.out.mkdir()
    summary = {
        "full_schedule": run_probe(args.out, "full-schedule", TRANSPORT_FAILURES, 496, 2),
        "no_room_for_rerun": run_probe(args.out, "no-room-for-rerun", NO_ROOM_FAILURES, 36, 1),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
