"""Development-only Grover fixtures and per-worker question projection."""

import argparse
import hashlib
import json
from dataclasses import dataclass
from fractions import Fraction

from .transfer import ThresholdTask, reference, verify

REGIMES = ("complementary", "redundant", "sequential")
WORKERS = ("a", "b", "c")
FOUR_FIFTHS = Fraction(4, 5)
BOUNDARY = Fraction(25, 32)


@dataclass(frozen=True)
class Stage:
    name: str
    qubits: int
    cap: int
    target: Fraction
    marks: tuple[tuple[str, tuple[int, ...]], ...]
    solvers: tuple[str, ...]
    prerequisite: str | None = None

    def needs_shards(self):
        """Use relay tasks when any solver lacks the complete marked set."""
        source_marks = {worker: set(indices) for worker, indices in self.marks}
        marked = set().union(*source_marks.values())
        return any(worker not in source_marks or source_marks[worker] != marked for worker in self.solvers)

    def task(self, verified):
        """Build the private verifier task from an already-scored predecessor."""
        previous = verified[self.prerequisite] if self.prerequisite else None
        target = self.target if previous is None else previous[1]
        marked = tuple(sorted({index for _, indices in self.marks for index in indices}))
        return ThresholdTask(self.qubits, marked, self.cap, target)


@dataclass(frozen=True)
class Fixture:
    regime: str
    stages: tuple[Stage, ...]

    def __post_init__(self):
        earlier = set()
        for stage in self.stages:
            if stage.name in earlier or (stage.prerequisite is not None and stage.prerequisite not in earlier):
                raise ValueError("stage identities must be unique and prerequisites must precede their use")
            sources = [worker for worker, _ in stage.marks]
            if (len(set(sources)) != len(sources) or set(sources) - set(WORKERS)
                    or len(set(stage.solvers)) != len(stage.solvers) or set(stage.solvers) - set(WORKERS)
                    or not stage.solvers):
                raise ValueError("stage source and solver roles must have unique known workers")
            earlier.add(stage.name)

    def question_for(self, worker):
        """Expose a worker's local input, including how released evidence is used."""
        if worker not in WORKERS:
            raise ValueError("unknown worker")
        questions = []
        for stage in self.stages:
            local_marks = dict(stage.marks).get(worker)
            solve = worker in stage.solvers
            relay = stage.needs_shards()
            base = {"task": stage.name, "qubits": stage.qubits}
            if relay and local_marks is not None:
                questions.append({**base, "marked_indices": list(local_marks)})
            if not solve:
                continue
            question = {**base, "iteration_cap": stage.cap}
            if relay:
                question["mark_sources"] = [source for source, _ in stage.marks]
            else:
                question["marked_indices"] = list(local_marks)
            if stage.prerequisite is None:
                question["target"] = str(stage.target)
            else:
                question["target_from_verified_task"] = stage.prerequisite
                question["target_if_predecessor_has_no_hit"] = str(stage.target)
            questions.append(question)
        return {
            "regime": self.regime,
            "worker": worker,
            "instruction": (
                "Use ideal Grover search from the uniform state. Relay local marked indices "
                "when only a shard is provided. For a question with mark_sources, gather all "
                "listed shards. For a dependent question, wait for the verified predecessor "
                "and use its hit probability as the threshold, or use the stated fallback "
                "if it reported no hit. For each task to solve, return the first iteration from "
                "zero through the inclusive cap with probability at least the threshold and its "
                "exact rational probability, or report no hit."
            ),
            "questions": questions,
        }

    def score(self, name, worker, answer, verified):
        """Score a submission against the same task for each eligible solver."""
        stage = next((stage for stage in self.stages if stage.name == name), None)
        if stage is None or worker not in stage.solvers:
            return False
        if stage.prerequisite is not None and stage.prerequisite not in verified:
            return False
        return verify(stage.task(verified), answer)

    def reference_results(self):
        """Compute private answers in prerequisite order for development checks."""
        verified = {}
        results = {}
        for stage in self.stages:
            result = reference(stage.task(verified))
            verified[stage.name] = result["first"]
            results[stage.name] = result
        return results


def development_fixture(regime, seed):
    """Use a reproducible development seed to select marks and a threshold branch."""
    if regime not in REGIMES:
        raise ValueError("unknown regime")
    if type(seed) is not int or not 0 <= seed < 2**64:
        raise ValueError("seed must be an unsigned 64-bit integer")

    def digest(label):
        return hashlib.sha256(f"grover-development-v1:{regime}:{seed}:{label}".encode()).digest()

    threshold = (BOUNDARY, FOUR_FIFTHS)[digest("threshold")[0] % 2]
    qubits = 4 if regime == "complementary" else 3
    indices = sorted(range(2**qubits), key=lambda index: digest(f"mark:{index}"))
    if regime == "complementary":
        a_size = 1 + digest("shard:a")[0] % 2
        b_size = 1 + digest("shard:b")[0] % 2
        a = tuple(indices[:a_size])
        b = tuple(indices[a_size : a_size + b_size])
        stages = (Stage("join", qubits, 4, Fraction(1), (("a", a), ("b", b)), ("c",)),)
    elif regime == "redundant":
        common = (indices[0],)
        stages = (
            Stage("common", qubits, 4, threshold, (("a", common), ("b", common)), ("a", "b")),
            Stage("separate", qubits, 4, Fraction(1), (("c", (indices[1],)),), ("c",)),
        )
    else:
        stages = (
            Stage("scout", qubits, 4, threshold, (("a", (indices[0],)),), ("a",)),
            Stage("confirm", qubits, 1, FOUR_FIFTHS, (("b", (indices[1],)),), ("b",), "scout"),
            Stage("final", qubits, 4, FOUR_FIFTHS, (("c", (indices[2],)),), ("c",), "confirm"),
        )
    return Fixture(regime, stages)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("regime", choices=REGIMES)
    parser.add_argument("seed", type=int)
    parser.add_argument("worker", choices=WORKERS)
    args = parser.parse_args()
    print(json.dumps(development_fixture(args.regime, args.seed).question_for(args.worker),
                     indent=2, sort_keys=True))
