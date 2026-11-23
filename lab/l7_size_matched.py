"""Compare one flat scripted L7 team with disjoint same-roster subteams."""

from collections import Counter
import json

from lab import l7_activity, l7_parallel_selection as selection, topology

CASES = ("cross_subteam", "within_subteam")


def _fixture(size, case):
    workers = tuple(f"w{index:02d}" for index in range(size))
    observations = {worker: {} for worker in workers}
    observations[workers[0]] = {"left": 2, "join": 7}
    observations[workers[1]] = {"right": 3}
    return workers, topology.Fixture(case, topology.FIXTURES[0].tasks, observations)


def _subteam_activity(workers, team):
    trace = team["trace"]
    stopped = any(row["kind"] == "budget_stop" for row in trace)
    tasks = trace[-1]["verified_union"]
    costs = Counter()
    for row in trace:
        costs[row["kind"]] += row["cost"]
    receipt = {"trace": trace, "budget": team["cap"], "spent": team["spent"], "unused": team["unused"],
               "budget_stopped": stopped, "verified_union": tasks, "utility": len(tasks), "costs": costs}
    return l7_activity.measure(workers, receipt)


def run(size, case, *, budget=None):
    """Match slots, tasks, common budget, and work horizon for both layouts."""
    if type(size) is not int or size not in l7_activity.SIZES or case not in CASES:
        raise ValueError("unknown roster size or task-placement fixture")
    budget = size * 12 + 1 if budget is None else budget
    roster, fixture = _fixture(size, case)
    grouped_order = (roster[0], roster[2], roster[1], *roster[3:]) if case == "cross_subteam" else roster
    groups = {f"slot-{offset // 2:02d}": grouped_order[offset:offset + 2] for offset in range(0, size, 2)}
    reserve = len(groups) * selection.REVIEW_COST + selection.SELECTION_COST
    if type(budget) is not int or budget - reserve < len(groups) * topology.UNIT_COST["merge"]:
        raise ValueError("common budget cannot fund all terminal and review costs")
    base, remainder = divmod(budget - reserve, len(groups))
    team_caps = {label: base + int(index < remainder) for index, label in enumerate(groups)}
    subteams = {label: {worker: fixture.observations[worker] for worker in members}
                for label, members in groups.items()}
    truth = {name: task.expected for name, task in fixture.tasks.items()}
    dependencies = {name: task.requires for name, task in fixture.tasks.items()}

    flat_receipt = topology.run(fixture, "peers", budget=budget - selection.REVIEW_COST,
                                evidence_access="shared", workers=roster)
    flat_activity = l7_activity.measure(roster, flat_receipt)
    flat_artifact = selection._seal(flat_receipt["trace"])
    flat_tasks = selection._review(flat_artifact, dependencies, truth)
    flat_spent = flat_receipt["spent"] + selection.REVIEW_COST
    flat = {"utility": len(flat_tasks), "verified_tasks": flat_tasks, "spent": flat_spent,
            "unused": budget - flat_spent, "activity": flat_activity, "receipt": flat_receipt}

    report = selection.run(fixture, subteams, team_caps=team_caps, budget=budget,
                           assessment_truth=truth, candidate_rosters=groups)
    activity = [_subteam_activity(groups[label], report["teams"][label]) for label in groups]
    attempted = sum(row["attempted_work_workers"] for row in activity)
    stopped = any(row["budget_stopped"] for row in activity)
    parallel_activity = {
        "roster_count": size, "attempted_work_workers": attempted,
        "verified_work_workers": sum(row["verified_work_workers"] for row in activity),
        "workers_with_observed_opportunity": sum(row["workers_with_observed_opportunity"] for row in activity),
        "observed_opportunities": sum(row["observed_opportunities"] for row in activity),
        "planned_opportunities": sum(row["planned_opportunities"] for row in activity),
        "observed_attempt_share": attempted / size, "full_window_attempt_share": None if stopped else attempted / size,
        "budget_stopped": stopped,
    }
    parallel = {"utility": report["utility"], "spent": report["accounting"]["spent"],
                "unused": report["accounting"]["unused"], "activity": parallel_activity, "report": report}
    return {"scientific_result": False, "case": case, "roster": list(roster), "budget": budget,
            "rounds": topology.ROUNDS, "reference_sha256": selection._digest(truth),
            "observations_sha256": selection._digest(fixture.observations), "flat": flat, "parallel": parallel}


def demo():
    return {"cells": [run(size, case) for size in l7_activity.SIZES for case in CASES],
            "budget_stop_control": run(8, "cross_subteam", budget=17)}


if __name__ == "__main__":
    print(json.dumps(demo(), sort_keys=True, indent=2))
