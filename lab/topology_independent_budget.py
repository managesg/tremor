"""Scripted independent contributors with fixed shares and a reviewed union."""

import json

from lab import l7_parallel_selection as assessment, topology


def run(fixture, *, worker_caps, budget, scoring_truth, worker_order=None):
    """Run each worker alone and score its sealed results before deduplicating.

    Each worker cap includes the local trace's terminal seal. The common
    allowance also covers separate review of each seal and the final union.
    The union includes verified work retained when a worker reaches its cap.
    """
    roster = tuple(sorted(fixture.observations))
    order = roster if worker_order is None else tuple(worker_order)
    if not roster or len(order) != len(roster) or set(order) != set(roster):
        raise ValueError("worker order must contain every contributor exactly once")
    if set(worker_caps) != set(roster) or any(
        type(cap) is not int or cap < topology.UNIT_COST["merge"] for cap in worker_caps.values()
    ):
        raise ValueError("each contributor needs a fixed cap that covers sealing")
    if set(scoring_truth) != set(fixture.tasks):
        raise ValueError("scoring truth must cover the full task inventory")
    review_cost = len(roster) * assessment.REVIEW_COST
    union_cost = topology.UNIT_COST["merge"]
    if type(budget) is not int or sum(worker_caps.values()) + review_cost + union_cost != budget:
        raise ValueError("allowance must equal the fixed shares, reviews and union charge")

    receipts = {}
    for worker in order:
        local = topology.Fixture(fixture.name, fixture.tasks, {worker: fixture.observations[worker]})
        receipts[worker] = topology.run(local, "independent", budget=worker_caps[worker],
                                        evidence_access="own", workers=(worker,))

    dependencies = {task: definition.requires for task, definition in fixture.tasks.items()}
    reviewed = {worker: assessment._review(assessment._seal(receipts[worker]["trace"]),
                                           dependencies, scoring_truth) for worker in roster}
    union = sorted({task for tasks in reviewed.values() for task in tasks})
    worker_spent = sum(receipt["spent"] for receipt in receipts.values())
    spent = worker_spent + review_cost + union_cost
    return {
        "evidence": "scripted_development", "fixture": fixture.name, "roster": roster,
        "budget": budget, "worker_caps": {worker: worker_caps[worker] for worker in roster},
        "assessment_sha256": assessment._digest(scoring_truth),
        "workers": {worker: receipts[worker] for worker in roster}, "reviewed_tasks": reviewed,
        "verified_union": union, "verified_utility": len(union),
        "workers_stopped": [worker for worker in roster if receipts[worker]["budget_stopped"]],
        "accounting": {"worker_spent_including_seals": worker_spent, "review_spent": review_cost,
                       "union_spent": union_cost, "spent": spent, "unused": budget - spent},
    }


def demo():
    return [run(fixture, worker_caps={worker: 9 for worker in fixture.observations}, budget=31,
                scoring_truth={name: task.expected for name, task in fixture.tasks.items()})
            for fixture in topology.FIXTURES]


if __name__ == "__main__":
    print(json.dumps(demo(), sort_keys=True, indent=2))
