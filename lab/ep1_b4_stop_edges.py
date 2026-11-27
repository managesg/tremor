"""Retain FAKE evidence at the first-block, wire-size and canary stops."""

import argparse
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from lab import ep1_b4_full_reservation as reservation
from lab.ep1_b4_probe import run_case, run_fake
from tremor import ep1, spend, team_claude


def _require(condition, detail):
    if not condition:
        raise ValueError(detail)


def _pins(directory, names):
    return {name: hashlib.sha256((directory / name).read_bytes()).hexdigest() for name in names}


def first_block(root, malformed):
    """Send the first request of block two only when the first block passes."""
    _require(malformed in (6, 7), "first-block fixture requires exactly six or seven malformed replies")
    name = f"first-block-{malformed}"

    def respond(path, headers, body, number):
        if number == 25:
            return 400, {"error": {"message": "FAKE sentinel for block-two entry"}}
        status, response = ep1.worst_case_responder(path, headers, body, number)
        if number <= malformed:
            response["content"][0]["text"] = "FAKE non-JSON response"
        return status, response

    final, calls, rows = run_case(root, name, respond)
    first = ep1.plan("ep1", 0)[0]
    expected = [(first["set"], cond) for cond in first["order"]]
    _require([(row["set"], row["cond"]) for row in rows[:3]] == expected
             and all(row["ended"] == "complete" and row["valid"] is True and row["void"] is None for row in rows[:3])
             and sum(row["malformed"] for row in rows[:3]) == malformed,
             "first block did not retain all three valid cells at the requested count")
    if malformed == 6:
        _require(calls == 25 and len(rows) == 4 and rows[-1]["set"] != first["set"]
                 and final["detail"] == "http_400", "threshold equality failed to reach the next block")
    else:
        _require(malformed == 7 and calls == 24 and len(rows) == 3
                 and final["detail"] == "malformed_first_block", "driver did not stop above the first-block boundary")
    return {"malformed_first_block": malformed, "entered_block_two": calls == 25, "ep1_requests": calls,
            "reason": final["reason"], "detail": final["detail"],
            "files": _pins(root / name, ("ep1/schedule.json", "ep1/episodes.jsonl", "ep1/final.json", "ledger/ep1.jsonl"))}


def prompt_boundary(root):
    """Inject exactly one byte above the real driver limit on the second prompt."""
    prompts = 0
    wire_lengths = []

    def pad(episode, agent, round_index, view):
        nonlocal prompts
        system, user = reservation.pad_prompt(episode, agent, round_index, view)
        prompts += 1
        return system + (" " if prompts == 2 else ""), user

    def respond(path, headers, body, number):
        wire_lengths.append(int(headers["Content-Length"]))
        return ep1.worst_case_responder(path, headers, body, number)

    with patch.object(team_claude._ModelEpisode, "prompt", pad):
        final, calls, rows = run_case(root, "prompt-boundary", respond)
    row, = rows
    case = root / "prompt-boundary"
    ledger = ep1._read_jsonl(str(case / "ledger" / "ep1.jsonl"))
    reserves = [entry for entry in ledger if entry["kind"] == "reserve"]
    charges = [entry for entry in ledger if entry["kind"] == "charge"]
    accepted, rejected = row["turns"]
    analysis = ep1._summary(rows, True)["arms"][row["arm"]]
    _require((calls, wire_lengths, prompts) == (1, [2000], 2)
             and (accepted["request_bytes"], rejected["request_bytes"], rejected["status"]) == (2000, 2001, "prompt_too_large")
             and row["ended"] == "prompt_too_large" and row["rerunnable"] is False and row["attempt"] == 0
             and [entry["id"] for entry in reserves] == [entry["id"] for entry in charges] == [accepted["call_id"]]
             and final["detail"] == "prompt_too_large"
             and analysis["censored_task_sets"] == 1 and analysis["completion"] == 0.0,
             "request-size refusal, charge or analysis censoring did not match the fixture")
    return {"sent_bytes": wire_lengths, "refused_bytes": rejected["request_bytes"], "ep1_requests": calls,
            "ep1_reservations": len(reserves), "reason": final["reason"], "detail": final["detail"],
            "censored_task_sets": analysis["censored_task_sets"],
            "files": _pins(case, ("ep1/episodes.jsonl", "ep1/final.json", "ledger/ep1.jsonl"))}


def canary_boundary(root, fault):
    _require(fault in ("wrong-model", "missing-usage", "invalid-reply"), "unknown FAKE canary case")
    case = root / f"canary-{fault}"
    case.mkdir()
    sheet = ep1._dry_sheet(case / "price-sheet.json")

    def bad_canary(path, headers, body, number):
        status, response = ep1.worst_case_responder(path, headers, body, number)
        if fault == "wrong-model":
            response["model"] = "claude-sonnet-5-5"
            response["usage"].update(input_tokens=1, output_tokens=1)
        elif fault == "missing-usage":
            response["usage"].pop("output_tokens")
        else:
            response["stop_reason"] = "max_tokens"
        return status, response

    result, calls = run_fake(case, "canary", bad_canary, sheet)
    _require(result["ok"] is False and calls == 1 and result["reason"].startswith("stopped:"),
             "bad canary did not stop after one request")
    if fault != "missing-usage":
        expected = "wrong_model" if fault == "wrong-model" else "malformed:truncated"
        _require(result["detail"] == expected and result["ledger"]["charge_lines"] == 1,
                 "FAKE canary fault or retained charge did not match")
    else:
        _require(result["detail"] in ("call_failed:BatchStopped", "call_failed:Overspent"),
                 "missing usage did not fail at the ledger boundary")
        entries = ep1._read_jsonl(str(case / "ledger" / "canary.jsonl"))
        reserve, = [row for row in entries if row["kind"] == "reserve"]
        charge, = [row for row in entries if row["kind"] == "charge"]
        _require(charge["usage"] is None and charge["usage_invalid"] and charge["usd"] == reserve["worst_usd"]
                 and any(row["kind"] == "overspent" for row in entries),
                 "invalid usage did not keep its unresolved worst-case charge")

    downstream_calls = 0

    def downstream(path, headers, body, number):
        nonlocal downstream_calls
        downstream_calls += 1
        return ep1.worst_case_responder(path, headers, body, number)

    try:
        run_fake(case, "ep1", downstream, sheet)
    except spend.BatchStopped as error:
        _require("canary" in str(error), "unexpected EP-1 preflight refusal")
    else:
        raise ValueError("EP-1 was admitted after a failed canary")
    _require(downstream_calls == 0 and not (case / "ep1" / "schedule.json").exists(),
             "failed canary permitted a downstream schedule or request")
    try:
        run_fake(case, "canary", downstream, sheet)
    except spend.BatchStopped as error:
        _require("already stopped or settled" in str(error), "unexpected retry of stopped canary")
    else:
        raise ValueError("failed canary reopened")
    _require(downstream_calls == 0, "failed canary was sent again")
    return {"canary_requests": calls, "downstream_ep1_requests": downstream_calls, "reason": result["reason"],
            "detail": result["detail"], "charge_lines": result["ledger"]["charge_lines"],
            "canary_reopened": False,
            "files": _pins(case, ("canary/canary.json", "ledger/canary.jsonl"))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir()
    report = {"evidence": "FAKE_b4_stop_edges", "first_block_equal": first_block(args.output, 6),
              "first_block_above": first_block(args.output, 7), "prompt": prompt_boundary(args.output),
              "canary": {fault: canary_boundary(args.output, fault)
                         for fault in ("wrong-model", "missing-usage", "invalid-reply")}}
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
