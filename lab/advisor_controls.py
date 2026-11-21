"""Run local-only, available, and unavailable scripted advice controls offline."""

import json

from . import frontier_advisor, topology

ARMS = {
    "local_only": None,
    "scripted_available": frontier_advisor.available,
    "scripted_unavailable": frontier_advisor.unavailable,
}


def _measure(run):
    trace = run["trace"]
    requests = [event for event in trace if event["kind"] == "advice_request"]
    results = {event["request"]: event for event in trace if event["kind"] == "advice_result"}
    work = [trace[event["submission"]] for event in trace if event["kind"] == "verify" and event["accepted"]]
    accepted_round = {}
    for event in work:
        accepted_round.setdefault((event["actor"], event["task"]), event["round"])
    recoveries = []
    for request in requests:
        verified = accepted_round.get((request["actor"], request["task"]))
        recoveries.append({
            "request": request["event"], "status": results[request["event"]]["status"],
            "rounds_until_verified": None if verified is None else verified - request["round"],
        })
    return {
        "attempts": len(requests),
        "advice_cost": sum(event["cost"] for event in requests) + sum(event["cost"] for event in results.values()),
        "recovery": recoveries,
    }


def compare():
    """Cross the availability control with assignment policy and evidence access."""
    cells = []
    for fixture in topology.FIXTURES:
        for mode in topology.MODES:
            for access in topology.EVIDENCE_ACCESS:
                for name, advisor in ARMS.items():
                    result = topology.run(fixture, mode, evidence_access=access, advisor=advisor)
                    cells.append({"fixture": fixture.name, "evidence_access": access, "advisor": name,
                                  **_measure(result), **result})
    return {"instrument_validation": True, "cells": cells}


if __name__ == "__main__":
    print(json.dumps(compare(), indent=2, sort_keys=True))
