"""Independently replay serialized Grover development traces and optional input digest."""
import argparse
from collections import Counter
from fractions import Fraction
import hashlib
from itertools import product
import json
from pathlib import Path

from .transfer_fixtures import WORKERS, development_fixture

MODES = ("independent", "fixed_lead", "rotating_lead", "peers")
ACCESS = ("own", "shared")
PAID = frozenset(("read", "plan", "blocked", "assign", "claim", "claim_conflict",
                  "handoff", "work", "verify", "merge"))
PLAN_FIELDS = {"actor", "assignments", "cost", "event", "kind", "round"}


def _check(ok, message):
    if not ok:
        raise ValueError(message)


def _unique_object(pairs):
    result = dict(pairs)
    _check(len(result) == len(pairs), "duplicate JSON key")
    return result


def _integer_ids(ids):
    return isinstance(ids, list) and all(type(i) is int for i in ids)


def _counts_match(record, expected):
    return all(type(record[key]) is int and record[key] == value for key, value in expected.items())


def _expected(stage, target):
    """Use rational per-state amplitudes, independent of the production verifier."""
    marked = {index for _, indices in stage.marks for index in indices}
    size = 1 << stage.qubits
    amplitudes = [Fraction(1)] * size
    for step in range(stage.cap + 1):
        probability = sum((amplitudes[i] ** 2 for i in marked), Fraction(0)) / size
        if probability >= target:
            return [step, str(probability)]
        reflected = [-value if i in marked else value for i, value in enumerate(amplitudes)]
        doubled_mean = 2 * sum(reflected) / size
        amplitudes = [doubled_mean - value for value in reflected]
    return None


def _expected_assignments(eligible, dependencies, receipts, round_id, access):
    visible = {worker: {task for task, owner, issued, _ in receipts.values()
                        if issued < round_id and (access == "shared" or owner == worker)}
               for worker in WORKERS}
    assignments = {}
    for task, solvers in eligible.items():
        for worker in WORKERS:
            ready = visible[worker]
            if (worker in solvers and worker not in assignments and task not in ready
                    and all(dependency in ready for dependency in dependencies[task])):
                assignments[worker] = task
                break
    return assignments


def _arm(arm, stages, shards):
    mode, access, budget = (arm[key] for key in ("mode", "evidence_access", "budget"))
    _check(type(budget) is int and budget >= 1, "invalid budget")
    trace = arm["trace"]
    _check(bool(trace) and trace[-1]["kind"] == "merge", "missing final merge")
    costs = Counter()
    receipts = {}
    work = {}
    view_reads = {}
    plans, authorized, claims = {}, set(), {}
    eligible, dependencies = {}, {}
    for name, stage in stages.items():
        stage_shards = [shard for shard in shards if shard.startswith(f"shard/{name}/")]
        for shard in stage_shards:
            eligible[shard] = (shards[shard][0],)
            dependencies[shard] = []
        eligible[name] = stage.solvers
        dependencies[name] = stage_shards
        if stage.prerequisite:
            dependencies[name].append(stage.prerequisite)
    read_order = [[], [], []]
    prior_round = 0
    attempted = None

    for index, row in enumerate(trace):
        kind, actor, round_id = (row[key] for key in ("kind", "actor", "round"))
        _check(type(row["event"]) is int and row["event"] == index and type(round_id) is int
               and prior_round <= round_id <= min(3, prior_round + 1), "invalid event chronology")
        final = index == len(trace) - 1
        _check((final and round_id == prior_round + 1 and actor == "verifier")
               or (not final and round_id < 3 and kind != "merge"), "invalid round or merge")
        starts_round = index == 0 or round_id != prior_round
        prior_round = round_id
        if mode == "rotating_lead" and starts_round and not final and round_id > 0:
            _check(kind == "handoff" or (kind == "budget_stop" and row["attempted"] == "handoff"),
                   "missing rotating handoff")
        if kind == "budget_stop":
            attempted = row["attempted"]
            _check(index == len(trace) - 2 and attempted in PAID - {"merge", "verify"}
                   and sum(costs.values()) + 2 + (attempted == "work") > budget,
                   "invalid budget stop")
            if attempted == "handoff":
                _check(mode == "rotating_lead" and starts_round and round_id > 0 and actor == WORKERS[round_id - 1],
                       "invalid handoff stop actor")
            elif attempted in ("plan", "assign"):
                lead = WORKERS[0] if mode == "fixed_lead" else WORKERS[round_id]
                _check(mode in ("fixed_lead", "rotating_lead") and actor == lead, "invalid lead stop actor")
            elif attempted == "read":
                _check(len(read_order[round_id]) < len(WORKERS)
                       and actor == WORKERS[len(read_order[round_id])], "invalid read stop actor")
            else:
                _check(bool(read_order[round_id]) and actor == read_order[round_id][-1]
                       and (attempted not in ("claim", "claim_conflict") or mode == "peers"),
                       "invalid worker stop actor")
        else:
            _check(kind in PAID, "unknown trace event")
        cost = int(kind != "budget_stop")
        _check(type(row["cost"]) is int and row["cost"] == cost, "incorrect event cost")
        costs[kind] += cost

        if kind == "plan":
            lead = WORKERS[0] if mode == "fixed_lead" else WORKERS[round_id]
            _check(mode in ("fixed_lead", "rotating_lead") and actor == lead and round_id not in plans,
                   "incorrect plan authority")
            _check(row.keys() == PLAN_FIELDS, "unexpected plan event fields")
            expected = _expected_assignments(eligible, dependencies, receipts, round_id, access)
            _check(row["assignments"] == expected, "plan assignments differ from fixture readiness")
            plans[round_id] = expected
        elif kind == "assign":
            lead = WORKERS[0] if mode == "fixed_lead" else WORKERS[round_id]
            worker, task = row["worker"], row["task"]
            _check(actor == lead and worker in WORKERS and plans.get(round_id, {}).get(worker) == task,
                   "assignment lacks lead plan")
            authorized.add((round_id, worker, task))
        elif kind == "claim":
            task = row["task"]
            _check(mode == "peers" and row["worker"] == actor and actor in eligible.get(task, ())
                   and (round_id, task) not in claims, "incorrect claim authority")
            claims[round_id, task] = actor
            authorized.add((round_id, actor, task))
        elif kind == "handoff":
            _check(mode == "rotating_lead" and starts_round and round_id > 0 and actor == WORKERS[round_id - 1]
                   and row["recipient"] == WORKERS[round_id], "incorrect handoff")
        if kind in ("blocked", "claim_conflict"):
            task = row["task"]
            _check(actor in eligible.get(task, ()) and (round_id, actor) in view_reads
                   and actor == read_order[round_id][-1], "invalid dependency or conflict actor")
            visible = view_reads[round_id, actor]
            if kind == "blocked":
                missing = [dep for dep in dependencies[task] if dep not in visible]
                _check(bool(missing) and row["missing"] == missing, "incorrect blocked dependencies")
            else:
                holder = claims.get((round_id, task))
                _check(mode == "peers" and holder is not None and row["holder"] == holder and actor != holder
                       and task not in visible, "incorrect claim conflict")
        if kind in ("read", "work"):
            visible = {}
            for receipt, (task, worker, issued, answer) in receipts.items():
                if issued < round_id and (access == "shared" or worker == actor):
                    visible.setdefault(task, receipt)
            _check(actor in WORKERS, "unknown actor")
        if kind == "read":
            ids = row["visible"]
            _check(_integer_ids(ids) and len(ids) == len(visible) and set(ids) == set(visible.values()),
                   "read contains unauthorized or premature receipt")
            read_order[round_id].append(actor)
            view_reads[round_id, actor] = visible
        elif kind == "work":
            _check(view_reads.get((round_id, actor)) == visible, "work lacks a matching participant read")
            name, given = row["task"], row["answer"]
            _check(mode == "independent" or (round_id, actor, name) in authorized, "missing work authority")
            if name in shards:
                owner, marks = shards[name]
                _check(actor == owner, "wrong shard publisher")
                expected = marks
                valid_shape = _integer_ids(given)
            else:
                stage = stages[name]
                _check(actor in stage.solvers, "ineligible stage solver")
                target = stage.target
                if stage.prerequisite:
                    _check(stage.prerequisite in visible, "missing prerequisite receipt")
                    predecessor = receipts[visible[stage.prerequisite]][3]
                    target = target if predecessor is None else Fraction(predecessor[1])
                expected = _expected(stage, target)
                valid_shape = given is None or (type(given) is list and len(given) == 2
                                                 and type(given[0]) is int and type(given[1]) is str)
            ids = row["inputs"]
            required = dependencies[name]
            _check(_integer_ids(ids) and all(dep in visible for dep in required)
                   and ids == [visible[dep] for dep in required], "bad work receipt inputs")
            work[index] = (name, actor, round_id, given)
            verifier = trace[index + 1]
            _check(verifier["kind"] == "verify" and type(verifier["submission"]) is int
                   and verifier["submission"] == index and verifier["round"] == round_id
                   and verifier["accepted"] is (valid_shape and given == expected), "incorrect work verdict")
        elif kind == "verify":
            _check(actor == "verifier" and row["submission"] == index - 1 and index - 1 in work,
                   "unpaired verification")
            if row["accepted"]:
                receipts[index] = work[index - 1]

    full_rounds = prior_round - int(attempted is not None)
    _check(all(order == list(WORKERS[:len(order)]) for order in read_order)
           and all(order == list(WORKERS) for order in read_order[:full_rounds]), "wrong worker order")

    union = sorted({r[0] for r in receipts.values()})
    stage_union = sorted(set(union) & stages.keys())
    spent = sum(costs.values())
    _check(trace[-1]["verified_union"] == arm["verified_union"] == union
           and arm["verified_stage_union"] == stage_union
           and _counts_match(arm, {"stage_utility": len(stage_union), "utility": len(union)}),
           "incorrect verified union or utility")
    counts = {
        "spent": spent, "unused": budget - spent, "handoffs": costs["handoff"],
        "blocked_dependencies": costs["blocked"], "claim_conflicts": costs["claim_conflict"],
        "duplicate_work": len(work) - len({row[0] for row in work.values()}),
        "valid_integrations": sum(bool(dependencies[name]) for name in union),
    }
    _check(spent <= budget and _counts_match(arm, counts)
           and arm["budget_stopped"] is (attempted is not None)
           and arm["costs"].keys() == costs.keys() and _counts_match(arm["costs"], costs),
           "incorrect accounting")
    return {"mode": mode, "access": access, "stage_union": stage_union, "spent": spent,
            "verified_work": len(receipts), "events": len(trace)}


def audit(raw, *, expected_sha256=None):
    """Verify a serialized scripted trace. Actor names are fixture labels."""
    digest = hashlib.sha256(raw).hexdigest()
    _check(expected_sha256 is None or expected_sha256 == digest, "input digest mismatch")
    report = json.loads(raw, object_pairs_hook=_unique_object)
    _check(report["instrument_validation"] is True and report["worker_order"] == list(WORKERS),
           "unexpected trace scope or worker order")
    seen = set()
    cases = []
    for case in report["cases"]:
        regime, seed = case["regime"], case["development_seed"]
        _check((regime, seed) not in seen, "duplicate development case")
        seen.add((regime, seed))
        fixture = development_fixture(regime, seed)
        stages = {stage.name: stage for stage in fixture.stages}
        shards = {f"shard/{stage.name}/{source}": (source, sorted(marks))
                  for stage in fixture.stages for source, marks in stage.marks
                  if any(solver not in dict(stage.marks) for solver in stage.solvers)}
        arms = {(arm["mode"], arm["evidence_access"]): arm for arm in case["arms"]}
        _check(len(case["arms"]) == len(arms) and arms.keys() == set(product(MODES, ACCESS))
               and len({arm["budget"] for arm in arms.values()}) == 1, "incomplete or unmatched comparison grid")
        cells = {key: _arm(arm, stages, shards) for key, arm in arms.items()}
        for (mode, access), cell in cells.items():
            utility = len(cell["stage_union"])
            arm = arms[mode, access]
            gains = {
                "gain_over_independent_union": utility - len(cells["independent", "own"]["stage_union"]),
                "gain_over_independent_at_same_access": utility - len(cells["independent", access]["stage_union"]),
            }
            _check(_counts_match(arm, gains), "incorrect comparison baseline")
        cases.append({"regime": regime, "seed": seed, "cells": list(cells.values())})
    _check(bool(cases), "missing development case")
    return {"sha256": digest, "external_digest_checked": expected_sha256 is not None,
            "actors_authenticated": False, "cases": cases}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path)
    parser.add_argument("--expected-sha256")
    args = parser.parse_args()
    try:
        result = audit(args.trace.read_bytes(), expected_sha256=args.expected_sha256)
    except (ValueError, KeyError, IndexError, TypeError, OSError) as error:
        parser.exit(2, f"Grover trace audit failed: {error}\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
