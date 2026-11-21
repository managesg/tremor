"""Run public Grover development fixtures through TREMOR's CPU coordinator."""

import argparse
from fractions import Fraction
import json

from lab import topology
from .transfer import ThresholdTask, exact_trace
from .transfer_fixtures import REGIMES, WORKERS, development_fixture

DEVELOPMENT_CASES = (("complementary", 0), ("complementary", 9), ("redundant", 0), ("sequential", 0))


def _shard(stage, source):
    return f"shard/{stage}/{source}"


def _answer(value):
    if value is None:
        return None
    if (type(value) is not list or len(value) != 2 or type(value[0]) is not int
            or type(value[1]) is not str):
        raise ValueError("invalid threshold answer")
    probability = Fraction(value[1])
    if str(probability) != value[1]:
        raise ValueError("expected canonical rational probability")
    return value[0], probability


def _propose(name, question, evidence):
    """Reconstruct the answer using worker-local questions and exact prior receipts."""
    if name.startswith("shard/"):
        return sorted(question["marked_indices"])
    marks = set(question.get("marked_indices", ()))
    for source in question.get("mark_sources", ()):
        marks.update(evidence[_shard(name, source)])
    if "target_from_verified_task" in question:
        previous = _answer(evidence[question["target_from_verified_task"]])
        target = Fraction(question["target_if_predecessor_has_no_hit"]) if previous is None else previous[1]
    else:
        target = Fraction(question["target"])
    task = ThresholdTask(question["qubits"], tuple(sorted(marks)), question["iteration_cap"], target)
    return next(([i, str(probability)] for i, probability in enumerate(exact_trace(task)) if probability >= target), None)


def adapt(fixture):
    """Bind the private verifier and the separate worker observation projection."""
    tasks, shards = {}, {}
    for stage in fixture.stages:
        sources = dict(stage.marks)
        dependencies = []
        if any(solver not in sources for solver in stage.solvers):
            for source, marks in stage.marks:
                shard = _shard(stage.name, source)
                tasks[shard] = topology.Task(None)
                shards[shard] = (source, sorted(marks))
                dependencies.append(shard)
        if stage.prerequisite:
            dependencies.append(stage.prerequisite)
        tasks[stage.name] = topology.Task(None, tuple(dependencies))

    observations = {}
    for worker in WORKERS:
        observations[worker] = {}
        for question in fixture.question_for(worker)["questions"]:
            stage = question["task"]
            name = stage if "iteration_cap" in question else _shard(stage, worker)
            observations[worker][name] = question

    def verify(work, evidence):
        name, answer = work["task"], work["answer"]
        if name not in tasks or evidence.keys() != set(tasks[name].requires):
            return False
        if name in shards:
            source, marks = shards[name]
            return (work["actor"] == source and type(answer) is list
                    and all(type(index) is int for index in answer) and answer == marks)
        try:
            previous = {key: _answer(value) for key, value in evidence.items() if key not in shards}
            decoded = _answer(answer)
        except (ValueError, ZeroDivisionError):
            return False
        if any(evidence[key] != shards[key][1] for key in evidence if key in shards):
            return False
        return fixture.score(name, work["actor"], decoded, previous)

    return topology.Fixture(fixture.regime, tasks, observations), topology.WorkProtocol(_propose, verify)


def compare(cases=DEVELOPMENT_CASES, *, budget=topology.BUDGET):
    reports = []
    for regime, seed in cases:
        domain = development_fixture(regime, seed)
        fixture, protocol = adapt(domain)
        stage_ids = {stage.name for stage in domain.stages}
        arms = {}
        for access in topology.EVIDENCE_ACCESS:
            for mode in topology.MODES:
                result = topology.run(fixture, mode, budget=budget, evidence_access=access,
                                      work_protocol=protocol, rotate_worker_order=False)
                union = sorted(stage_ids.intersection(result["verified_union"]))
                arms[mode, access] = {**result, "evidence_access": access, "verified_stage_union": union,
                                     "stage_utility": len(union)}
        baseline = arms["independent", "own"]["stage_utility"]
        for (mode, access), arm in arms.items():
            arm["gain_over_independent_union"] = arm["stage_utility"] - baseline
            arm["gain_over_independent_at_same_access"] = arm["stage_utility"] - arms["independent", access]["stage_utility"]
        reports.append({"regime": regime, "development_seed": seed, "arms": list(arms.values())})
    return {"instrument_validation": True, "worker_order": list(WORKERS), "cases": reports}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--budget", type=int, default=topology.BUDGET)
    args = parser.parse_args()
    try:
        result = compare(budget=args.budget)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
