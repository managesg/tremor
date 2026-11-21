"""Public arithmetic grading controls for the R1 development bench."""

import json

from murmuration.trapbench import alloc, alloc2


CHECKS = ("distinct_passing", "surviving_passing", "duplicates", "name_collisions",
          "extra_work_events", "Y", "valid")
CLEAN = (4, 4, 0, 0, 0, 1.0, True)
ONE_MISS = (3, 3, 0, 0, 0, 0.75, True)


def _taskset():
    # A sum of 1 makes True numerically equal while remaining a non-integer JSON type.
    return {"n_agents": 4, "name_rule": "{agent}-{task}", "tasks": [
        {"id": "sum-a", "check": "sum 0 1", "expect": 1},
        {"id": "sum-b", "check": "sum 2 3", "expect": 5},
        {"id": "sum-c", "check": "sum 3 4", "expect": 7},
        {"id": "sum-d", "check": "sum 4 5", "expect": 9},
    ]}


def _cases(clean):
    def replace(index, **fields):
        return [clean[index] | fields if i == index else row for i, row in enumerate(clean)]

    return {
        "reordered_distinct_work": (list(reversed(clean)), CLEAN),
        "incorrect_integer_sum": (replace(0, answer=2), ONE_MISS),
        "float_equal_to_sum": (replace(0, answer=1.0), ONE_MISS),
        "string_equal_to_sum": (replace(0, answer="1"), ONE_MISS),
        "true_equal_to_sum": (replace(0, answer=True), ONE_MISS),
        "missing_answer": ([{k: v for k, v in clean[0].items() if k != "answer"}, *clean[1:]], ONE_MISS),
        "refused_correct_work": (replace(0, rejected=True), ONE_MISS),
        "unrecognized_task": (replace(0, task="outside"), ONE_MISS),
        "duplicate_correct_task": (replace(1, task="sum-a", answer=1), (3, 3, 1, 0, 0, 0.75, True)),
        "colliding_output_name": (replace(1, name=clean[0]["name"]), (4, 3, 0, 1, 0, 1.0, True)),
        "incorrect_last_writer": (replace(1, name=clean[0]["name"], answer=6), (3, 2, 0, 1, 0, 0.75, True)),
        "repeat_worker": (replace(1, agent=clean[0]["agent"]), (4, 4, 0, 0, 1, None, False)),
        "non_boolean_refusal": (replace(0, rejected="true"), (3, 3, 0, 0, 0, None, False)),
        "action_missing": ([{k: v for k, v in clean[0].items() if k != "action"}, *clean[1:]],
                           (3, 3, 0, 0, 0, None, False)),
    }


def _checked_score(log, taskset, expected):
    result = {}
    for name, score in (("alloc", alloc.score), ("alloc2", alloc2.score)):
        actual = {field: score_value for field, score_value in score(log, taskset).items() if field in CHECKS}
        if actual != expected:
            raise ValueError(f"{name} disagrees with the public arithmetic fixture expectation")
        result[name] = actual
    return result


def evaluate():
    """Compare both existing result scorers with hand-tabulated expectations."""
    taskset = _taskset()
    clean = alloc.oracle_log(taskset)
    before = _checked_score(clean, taskset, dict(zip(CHECKS, CLEAN, strict=True)))
    cases = {}
    for name, (rows, metrics) in _cases(clean).items():
        expected = dict(zip(CHECKS, metrics, strict=True))
        after = _checked_score(rows, taskset, expected)
        cases[name] = {"expected": expected, "after": after, "changed": after != before}
    return {
        "evidence": "public_arithmetic_development_corpus",
        "protected_n2": False,
        "before": before,
        "cases": cases,
    }


if __name__ == "__main__":
    print(json.dumps(evaluate(), sort_keys=True, allow_nan=False))
