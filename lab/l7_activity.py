"""Audit worker activity on fixed-roster, synthetic L7 topology traces."""

from collections import Counter
import json

from lab import topology

SIZES = (4, 8, 16, 32)
DEVELOPMENT_BUDGET = 140


def _require(condition, detail):
    if not condition:
        raise ValueError(detail)


def measure(roster, receipt):
    """Keep attempted, verified, and unobserved work separate under the reserved roster."""
    workers = tuple(roster)
    _require(bool(workers) and all(type(worker) is str and worker and worker != "verifier" for worker in workers)
             and len(set(workers)) == len(workers), "invalid activity roster")
    trace = receipt["trace"]
    _require(bool(trace) and trace[-1]["kind"] == "merge", "activity trace needs its terminal merge")
    budget = receipt["budget"]
    _require(type(budget) is int and budget >= topology.UNIT_COST["merge"], "invalid activity budget")
    totals, attempts, verified = Counter(), {}, {}
    visited = set()
    stopped = False
    first_stop = None
    previous_round = -1
    read_pairs = set()
    for index, event in enumerate(trace):
        kind, actor, round_id = event["kind"], event["actor"], event["round"]
        _require(type(event["event"]) is int and event["event"] == index
                 and type(round_id) is int and previous_round <= round_id <= topology.ROUNDS,
                 "activity trace event order differs")
        _require(not stopped or kind == "merge", "activity trace continued after its budget stop")
        previous_round = round_id
        expected_cost = 0 if kind == "budget_stop" else topology.UNIT_COST.get(kind)
        _require(type(event["cost"]) is int and event["cost"] == expected_cost, "activity event cost differs")
        totals[kind] += event["cost"]
        if kind in ("merge", "verify"):
            _require(actor == "verifier", "unexpected verifier identity")
        else:
            _require(actor in workers, "activity event actor is outside the roster")
        if kind == "merge":
            _require(index == len(trace) - 1 and round_id >= 1
                     and round_id == (trace[index - 1]["round"] + 1 if index else 1),
                     "unexpected activity terminal")
        elif kind == "budget_stop":
            attempted = event["attempted"]
            _require(attempted in topology.UNIT_COST and attempted not in ("verify", "merge"),
                     "unexpected activity budget stop kind")
            reserve = topology.UNIT_COST["verify"] if attempted == "work" else 0
            _require(sum(totals.values()) + topology.UNIT_COST[attempted] + reserve + topology.UNIT_COST["merge"] > budget,
                     "budget stop does not exhaust the available cap")
            stopped = True
            first_stop = {"worker": actor, "round": round_id, "attempted": attempted}
        elif kind == "read":
            _require((actor, round_id) not in read_pairs, "repeated read opportunity in an activity round")
            visited.add(actor)
            read_pairs.add((actor, round_id))
        elif kind == "work":
            _require((actor, round_id) in read_pairs, "work without an observed roster opportunity")
            attempts[index] = event
        elif kind == "verify":
            submitted = event["submission"]
            _require(type(submitted) is int and submitted in attempts and submitted not in verified
                     and attempts[submitted]["round"] == round_id and type(event["accepted"]) is bool,
                     "unmatched or repeated work verification")
            verified[submitted] = event["accepted"]
        elif kind in ("assign", "claim", "handoff"):
            recipient = event["recipient"] if kind == "handoff" else event["worker"]
            _require(recipient in workers, "coordination recipient is outside the roster")

    _require(set(attempts) == set(verified), "work attempt is missing verification")
    full_opportunities = {(worker, round_id) for worker in workers for round_id in range(topology.ROUNDS)}
    _require(read_pairs <= full_opportunities and (stopped or read_pairs == full_opportunities),
             "completed activity trace is missing a planned worker opportunity")
    spent = sum(totals.values())
    _require(0 <= spent <= budget and receipt["spent"] == spent
             and receipt["unused"] == budget - spent and receipt["budget_stopped"] is stopped
             and totals == receipt["costs"], "activity budget does not reconcile")
    tried = {event["actor"] for event in attempts.values()}
    passed = {attempts[index]["actor"] for index, accepted in verified.items() if accepted}
    retained = sorted({attempts[index]["task"] for index, accepted in verified.items() if accepted})
    _require(trace[-1]["verified_union"] == receipt["verified_union"] == retained
             and type(receipt["utility"]) is int and receipt["utility"] == len(retained),
             "activity receipt utility differs from verified work")
    observed_share = len(tried) / len(workers)
    return {"roster_count": len(workers), "workers_with_observed_opportunity": len(visited),
            "attempted_work_workers": len(tried), "verified_work_workers": len(passed),
            "observed_attempt_share": observed_share, "full_window_attempt_share": None if stopped else observed_share,
            "observed_opportunities": len(read_pairs), "planned_opportunities": len(full_opportunities),
            "budget_stopped": stopped, "first_budget_stop": first_stop,
            "distinct_verified_tasks": len(retained), "spent": spent, "budget": budget}


def _sample(size):
    roster = tuple(f"w{index:02d}" for index in range(size))
    template = topology.FIXTURES[0]
    active = {0: {"left": 2}, 1: {"right": 3}, 2: {"join": 7}}
    observations = {worker: active.get(index, {}) for index, worker in enumerate(roster)}
    return roster, topology.Fixture(template.name, template.tasks, observations)


def demo():
    rows = []
    for size in SIZES:
        roster, fixture = _sample(size)
        arms = {}
        for mode in topology.MODES:
            receipt = topology.run(fixture, mode, budget=DEVELOPMENT_BUDGET, workers=roster, evidence_access="shared")
            arms[mode] = {"receipt": receipt, "activity": measure(roster, receipt)}
        rows.append({"size": size, "roster": roster, "arms": arms})
    roster, fixture = _sample(8)
    stopped = topology.run(fixture, "peers", budget=12, workers=roster)
    return {"scientific_result": False, "activity_definition": "at_least_one_work_attempt",
            "reporting_unit": "synthetic_units", "common_budget": DEVELOPMENT_BUDGET, "evidence_access": "shared",
            "rotating_lead_also_rotates_order": True, "rows": rows,
            "short_budget_control": {"roster": roster, "receipt": stopped, "activity": measure(roster, stopped)}}


if __name__ == "__main__":
    print(json.dumps(demo(), sort_keys=True, indent=2))
