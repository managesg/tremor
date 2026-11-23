"""Exact first-choice occupancy in a public scripted L5 task-order null."""

from collections import Counter
from fractions import Fraction
from itertools import permutations, product
import json


WORKERS = ("a0", "a1", "a2", "a3")
TASKS = ("t0", "t1", "t2", "t3")
METRICS = ("distinct_first_choices", "duplicate_first_choices", "colliding_tasks")


def _choice_counts(choices):
    occupancy = Counter(choices)
    distinct = len(occupancy)
    return distinct, len(choices) - distinct, sum(count >= 2 for count in occupancy.values())


def _ratio(numerator, denominator):
    value = Fraction(numerator, denominator)
    return {"numerator": value.numerator, "denominator": value.denominator}


def _summarize(profiles):
    frequencies = Counter(_choice_counts(profile) for profile in profiles)
    outcomes = sum(frequencies.values())
    totals = [sum(counts[index] * frequency for counts, frequency in frequencies.items())
              for index in range(len(METRICS))]
    return {
        "first_choice_profiles": outcomes,
        "expected": {metric: _ratio(total, outcomes) for metric, total in zip(METRICS, totals, strict=True)},
        "probability_of_any_collision": _ratio(sum(frequency for counts, frequency in frequencies.items()
                                                   if counts[2]), outcomes),
        "histogram": [{**dict(zip(METRICS, counts, strict=True)), "profiles": frequency}
                      for counts, frequency in sorted(frequencies.items())],
    }


def compare():
    """Enumerate equally likely first choices from independent uniform full rankings."""
    rankings_by_first_task = Counter(ranking[0] for ranking in permutations(TASKS))
    return {
        "scientific_result": False,
        "scope": "scripted_first_simultaneous_choice",
        "workers": list(WORKERS),
        "tasks": list(TASKS),
        "rankings_by_first_task_per_worker": dict(rankings_by_first_task),
        "arms": {
            "independent_random_order": _summarize(product(TASKS, repeat=len(WORKERS))),
            "static_rank_partition": _summarize((TASKS,)),
            "shared_identical_order": _summarize(((TASKS[0],) * len(WORKERS),)),
        },
    }


if __name__ == "__main__":
    print(json.dumps(compare(), sort_keys=True, indent=2, allow_nan=False))
