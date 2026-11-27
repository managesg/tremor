"""Exercise selected B4 boundaries using the EP-1 driver and a loopback backend."""

import argparse
import json
from collections import Counter
from pathlib import Path

from tremor import backend_claude, ep1, spend

SEED = 0


def run_fake(path, kind, respond, sheet, scorer=None):
    server, url, requests = ep1._fakeclaude().start(respond)
    try:
        ledger = spend.Ledger(str(path / "ledger" / f"{kind}.jsonl"), sheet, batch=kind)
        client = backend_claude.ClaudeClient("sk-ant-dry-run-not-a-key-0000", ledger, url,
                                            allow_host="127.0.0.1")
        result = ep1.run_batch(kind, client, ledger, SEED, str(path / kind), True, third_scorer=scorer)
        assert result["stamp"] == ep1.FAKE
        return result, len(requests)
    finally:
        server.shutdown()
        server.server_close()


def run_case(root, name, respond, scorer=None):
    case = root / name
    case.mkdir()
    sheet = ep1._dry_sheet(case / "price-sheet.json")
    canary, canary_calls = run_fake(case, "canary", ep1.worst_case_responder, sheet)
    assert canary["reason"] == "complete" and canary_calls == 1
    result, calls = run_fake(case, "ep1", respond, sheet, scorer)
    records = ep1._read_jsonl(str(case / "ep1" / "episodes.jsonl"))
    assert result["episodes"] == len(records)
    assert all(row["stamp"] == ep1.FAKE and row["evidence"] == "fake" for row in records)
    assert result["ledger"]["calls"] == calls + canary_calls
    assert result["ledger"]["stop_reason"] == result["reason"]
    return result, calls, records


def malformed_responder(path, headers, body, n, counts, schedule):
    status, response = ep1.worst_case_responder(path, headers, body, n)
    cell, position = divmod(n - 1, ep1.CALLS_PER_EPISODE)
    if position < counts.get(schedule[cell], 0):
        response["content"][0]["text"] = "no JSON in this test response"
    return status, response


def malformed_case(root, name, counts, expected, threshold, measure):
    schedule = [(block["set"], cond) for block in ep1.plan("ep1", SEED) for cond in block["order"]]

    def respond(path, headers, body, n):
        return malformed_responder(path, headers, body, n, counts, schedule)

    final, calls, records = run_case(root, name, respond)
    assert final["reason"] == "stopped:void_model"
    assert final["detail"] == expected
    assert len(records) < len(schedule)
    assert calls == ep1.CALLS_PER_EPISODE * len(records)
    assert [(row["set"], row["cond"]) for row in records] == schedule[:len(records)]
    assert [row["malformed"] for row in records] == [counts.get(cell, 0) for cell in schedule[:len(records)]]
    assert records[0]["set"] == 0 and records[0]["malformed"] == 0
    assert measure(records[:-1]) == threshold
    assert measure(records) == threshold + 1
    per_arm = Counter()
    for row in records:
        per_arm[row["cond"]] += row["malformed"]
    return {"reason": final["reason"], "detail": final["detail"], "episodes": len(records), "calls": calls,
            "equality": threshold, "stop_count": threshold + 1, "per_arm": dict(per_arm)}


def scorer_case(root, name, fault, expected_detail, expected_calls):
    invocations = 0

    def scorer(taskset, log):
        nonlocal invocations
        invocations += 1
        return fault(taskset, log) if expected_calls == 0 or invocations == 3 else ep1._lean(taskset, log)

    final, calls, records = run_case(root, name, ep1.worst_case_responder, scorer)
    assert final["reason"] == "stopped:scorer_disagreement"
    assert final["detail"] == expected_detail
    assert calls == expected_calls
    if calls:
        assert len(records) == 2 and records[0]["void"] is None
        assert records[-1]["void"].startswith(expected_detail)
        summary = ep1._summary(records, True)
        assert summary["arms"][records[-1]["arm"]]["censored_task_sets"] == 1
    else:
        assert not records
    return {"reason": final["reason"], "detail": final["detail"], "episodes": len(records), "calls": calls}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path, help="new output directory for fake batch artifacts")
    args = parser.parse_args()
    args.out.mkdir()

    plan = ep1.plan("ep1", SEED)
    overall = {(block, cond): 8 for block in (1, 2) for cond in plan[block]["order"]}
    overall[3, plan[3]["order"][0]] = 1
    checks = {
        "malformed-overall": malformed_case(args.out, "malformed-overall", overall, "malformed_overall", 48,
                                            lambda rows: sum(row["malformed"] for row in rows)),
    }
    for arm in ep1.BASE_CONDS:
        by_arm = {(block, arm): 8 for block in (1, 2, 3)}
        by_arm[4, arm] = 1

        def arm_count(rows):
            return sum(row["malformed"] for row in rows if row["cond"] == arm)

        checks[f"malformed-{arm}"] = malformed_case(args.out, f"malformed-{arm}", by_arm, f"malformed_{arm}", 24,
                                                    arm_count)
    checks.update({
        "scorer-startup-invalid": scorer_case(args.out, "scorer-startup-invalid",
                                             lambda *_: {"status": "INVALID"}, "scorer_invalid", 0),
        "scorer-episode-invalid": scorer_case(args.out, "scorer-episode-invalid",
                                             lambda *_: {"status": "INVALID"}, "scorer_invalid", 16),
        "scorer-episode-disagrees": scorer_case(args.out, "scorer-episode-disagrees",
                                               lambda *_: {"status": "OK", "score": {"distinct_passing": 99}},
                                               "scorer_disagreement", 16),
    })
    print(json.dumps(checks, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
