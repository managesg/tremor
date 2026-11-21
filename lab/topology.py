"""CPU-only coordination fixtures and trace scoring for instrument validation."""

import argparse
import json
from collections import Counter
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass

from . import frontier_advisor

MODES = ("independent", "fixed_lead", "rotating_lead", "peers")
EVIDENCE_ACCESS = ("own", "shared")
WORKERS = ("a", "b", "c")
ROUNDS = 3
BUDGET = 32
UNIT_COST = dict(read=1, plan=1, blocked=1, assign=1, claim=1, claim_conflict=1,
                 handoff=1, work=1, verify=1, merge=1)


@dataclass(frozen=True)
class Task:
    expected: int | None
    requires: tuple[str, ...] = ()


@dataclass(frozen=True)
class Fixture:
    name: str
    tasks: dict[str, Task]
    observations: dict[str, dict[str, object]]


@dataclass(frozen=True)
class WorkProtocol:
    propose: Callable
    verify: Callable


FIXTURES = (
    Fixture("complementary", {
        "left": Task(2), "right": Task(3), "join": Task(12, ("left", "right")),
    }, {"a": {"left": 2}, "b": {"right": 3}, "c": {"join": 7}}),
    Fixture("redundant", {
        "common": Task(5), "backup": Task(11), "separate": Task(13),
    }, {"a": {"common": 5}, "b": {"common": 5, "backup": 11}, "c": {"separate": 13}}),
    Fixture("sequential", {
        "root": Task(2), "middle": Task(5, ("root",)), "final": Task(10, ("middle",)),
    }, {"a": {"root": 2}, "b": {"middle": 3}, "c": {"final": 5}}),
)


def _visible(verified, agent, round_index, shared):
    return {
        item["task"]: item
        for item in reversed(verified)
        if item["round"] < round_index and (shared or item["worker"] == agent)
    }


def _valid_work(fixture, verified, mode, work, *, evidence_access=None, work_protocol=None):
    """Accept the fixture's answer with evidence visible before this round."""
    name, agent = work["task"], work["actor"]
    task = fixture.tasks[name]
    shared = mode != "independent" if evidence_access is None else evidence_access == "shared"
    visible = _visible(verified, agent, work["round"], shared)
    if name not in fixture.observations[agent]:
        return False
    if any(dependency not in visible for dependency in task.requires):
        return False
    if work["inputs"] != [visible[dependency]["event"] for dependency in task.requires]:
        return False
    if work_protocol is None:
        return work["answer"] == task.expected
    evidence = {dependency: visible[dependency]["answer"] for dependency in task.requires}
    return work_protocol.verify(deepcopy(work), deepcopy(evidence))


def _plan(fixture, worker_views, worker_order):
    """Assign from workers' readiness by task ID without sharing their answers."""
    assignments = {}
    for name, task in fixture.tasks.items():
        for worker in worker_order:
            visible = worker_views[worker]
            if (worker not in assignments and name in fixture.observations[worker]
                    and name not in visible and all(dependency in visible for dependency in task.requires)):
                assignments[worker] = name
                break
    return assignments


def run(fixture, mode, budget=BUDGET, *, evidence_access=None, advisor=None, work_protocol=None,
        rotate_worker_order=True):
    """Run a policy against a common synchronous work and verification protocol."""
    if mode not in MODES:
        raise ValueError("unknown coordination mode")
    if type(budget) is not int or budget < UNIT_COST["merge"]:
        raise ValueError("budget must be an integer that covers the final merge")
    if evidence_access is not None and evidence_access not in EVIDENCE_ACCESS:
        raise ValueError("evidence access must be own or shared")
    shared = mode != "independent" if evidence_access is None else evidence_access == "shared"
    trace, verified = [], []
    consulted, deferred = set(), set()
    spent, stopped = 0, False
    unit_costs = UNIT_COST | {
        "advice_request": frontier_advisor.REQUEST_COST,
        "advice_result": frontier_advisor.RESULT_COST,
    }

    def record(kind, actor, *, reserve=0, **data):
        nonlocal spent, stopped
        if spent + unit_costs[kind] + reserve + UNIT_COST["merge"] > budget:
            trace.append(dict(event=len(trace), round=round_index, kind="budget_stop",
                              actor=actor, attempted=kind, cost=0))
            stopped = True
            return None
        entry = dict(event=len(trace), round=round_index, kind=kind, actor=actor,
                     cost=unit_costs[kind], **data)
        trace.append(entry)
        spent += entry["cost"]
        return entry

    for round_index in range(ROUNDS):
        claimed = {}
        lead = None
        order = WORKERS
        if mode == "fixed_lead":
            lead = WORKERS[0]
        if mode == "rotating_lead":
            lead = WORKERS[round_index]
            if rotate_worker_order:
                order = WORKERS[round_index:] + WORKERS[:round_index]
            if round_index and record("handoff", WORKERS[round_index - 1], recipient=lead) is None:
                break
        worker_views = {agent: _visible(verified, agent, round_index, shared) for agent in order}
        assignments = {}
        if lead is not None:
            assignments = _plan(fixture, worker_views, order)
            if record("plan", lead, assignments=assignments) is None:
                break
        for agent in order:
            visible = worker_views[agent]
            if record("read", agent, visible=[item["event"] for item in visible.values()]) is None:
                break
            for name, observation in fixture.observations[agent].items():
                if name in visible:
                    continue
                if name in claimed:
                    if mode == "peers" and record("claim_conflict", agent, task=name, holder=claimed[name]) is None:
                        break
                    continue
                dependencies = fixture.tasks[name].requires
                missing = [dependency for dependency in dependencies if dependency not in visible]
                if missing:
                    key = (agent, name)
                    if key in deferred:
                        continue
                    if record("blocked", agent, task=name, missing=missing) is None:
                        break
                    if advisor is not None and key not in consulted:
                        request = record("advice_request", agent, task=name, missing=missing,
                                         reserve=frontier_advisor.RESULT_COST)
                        if request is None:
                            break
                        consulted.add(key)
                        proposal = advisor(frontier_advisor.Request(agent, name, tuple(missing)))
                        status = "unavailable" if proposal is None else "rejected"
                        if proposal == frontier_advisor.DEFER:
                            status = frontier_advisor.DEFER
                            deferred.add(key)
                        record("advice_result", "scripted_advisor", request=request["event"], status=status)
                    continue
                if lead is not None and assignments.get(agent) != name:
                    continue
                if mode != "independent":
                    kind = "assign" if lead is not None else "claim"
                    if record(kind, lead or agent, task=name, worker=agent) is None:
                        break
                    claimed[name] = agent
                inputs = [visible[dependency] for dependency in dependencies]
                work = record("work", agent, task=name, inputs=[item["event"] for item in inputs],
                              reserve=UNIT_COST["verify"])
                if work is None:
                    break
                if work_protocol is None:
                    work["answer"] = observation + sum(item["answer"] for item in inputs)
                else:
                    evidence = {item["task"]: item["answer"] for item in inputs}
                    work["answer"] = work_protocol.propose(name, deepcopy(observation), deepcopy(evidence))
                accepted = _valid_work(fixture, verified, mode, work, evidence_access=evidence_access,
                                       work_protocol=work_protocol)
                verdict = record("verify", "verifier", submission=work["event"], accepted=accepted)
                if accepted:
                    verified.append(dict(event=verdict["event"], worker=agent, task=name,
                                         round=round_index, answer=work["answer"]))
                break
            if stopped:
                break
        if stopped:
            break

    # The same merger deduplicates verified task IDs in every arm.
    unique = sorted({item["task"] for item in verified})
    trace.append(dict(event=len(trace), round=round_index + 1, kind="merge", actor="verifier",
                      cost=UNIT_COST["merge"], verified_union=unique))
    costs = Counter()
    for event in trace:
        costs[event["kind"]] += event["cost"]
    return {
        "mode": mode,
        "verified_union": unique,
        "utility": len(unique),
        "duplicate_work": sum(event["kind"] == "work" for event in trace)
        - len({event["task"] for event in trace if event["kind"] == "work"}),
        "valid_integrations": sum(bool(fixture.tasks[name].requires) for name in unique),
        "blocked_dependencies": sum(event["kind"] == "blocked" for event in trace),
        "claim_conflicts": sum(event["kind"] == "claim_conflict" for event in trace),
        "handoffs": sum(event["kind"] == "handoff" for event in trace),
        "budget": budget,
        "spent": sum(costs.values()),
        "unused": budget - sum(costs.values()),
        "costs": dict(costs),
        "budget_stopped": stopped,
        "trace": trace,
    }


def compare(*, cross_evidence=False):
    """Report all modes on identical task fixtures and resource ceilings."""
    comparisons = []
    for fixture in FIXTURES:
        if cross_evidence:
            cells = {(mode, access): run(fixture, mode, evidence_access=access)
                     for access in EVIDENCE_ACCESS for mode in MODES}
            baseline = cells["independent", "own"]["utility"]
            for (mode, access), arm in cells.items():
                arm["evidence_access"] = access
                arm["gain_over_independent"] = arm["utility"] - baseline
                arm["gain_over_self_assignment_at_same_access"] = arm["utility"] - cells["independent", access]["utility"]
                arm["gain_over_own_evidence_at_same_mode"] = arm["utility"] - cells[mode, "own"]["utility"]
            arms = list(cells.values())
        else:
            arms = [run(fixture, mode) for mode in MODES]
            baseline = arms[0]["utility"]
            for arm in arms:
                arm["gain_over_independent"] = arm["utility"] - baseline
        comparisons.append({"fixture": fixture.name, "arms": arms})
    return {
        "instrument_validation": True,
        "workers": WORKERS,
        "rounds": ROUNDS,
        "unit_cost": UNIT_COST,
        "comparisons": comparisons,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cross-evidence", action="store_true", help="cross assignment policy with evidence sharing")
    print(json.dumps(compare(cross_evidence=parser.parse_args().cross_evidence), indent=2, sort_keys=True))
