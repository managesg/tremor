"""Offline verifier for Grover threshold tasks planned after EP-1."""

import json
import math
from dataclasses import dataclass
from fractions import Fraction

from . import gatesim

MAX_QUBITS = 10
MAX_ITERATIONS = 128
PROBABILITY_TOLERANCE = 1e-12


@dataclass(frozen=True)
class ThresholdTask:
    qubits: int
    marked: tuple[int, ...]
    max_iterations: int
    target: Fraction

    def __post_init__(self):
        if type(self.qubits) is not int or not 1 <= self.qubits <= MAX_QUBITS:
            raise ValueError("invalid qubit count")
        if type(self.max_iterations) is not int or not 0 <= self.max_iterations <= MAX_ITERATIONS:
            raise ValueError("invalid iteration bound")
        if type(self.marked) is not tuple:
            raise ValueError("marked indices must be an immutable tuple")
        if any(type(index) is not int or not 0 <= index < 1 << self.qubits for index in self.marked):
            raise ValueError("marked index outside the circuit")
        if len(set(self.marked)) != len(self.marked):
            raise ValueError("duplicate marked index")
        if not isinstance(self.target, Fraction) or not 0 <= self.target <= 1:
            raise ValueError("target must be a rational probability in [0, 1]")


def exact_trace(task):
    """Advance the marked and unmarked coefficients without replaying gates."""
    size = 1 << task.qubits
    marked_count = len(task.marked)
    plain_count = size - marked_count
    marked, plain = Fraction(1), Fraction(1)
    trace = []
    for _ in range(task.max_iterations + 1):
        trace.append(marked_count * marked ** 2 / size)
        mean = (plain_count * plain - marked_count * marked) / size
        marked, plain = 2 * mean + marked, 2 * mean - plain
    return trace


def reference(task):
    """Cross-check exact arithmetic against gate replay and find the first hit."""
    trace = exact_trace(task)
    errors = []
    states = gatesim.grover_states(task.qubits, task.marked, task.max_iterations)
    for probability, state in zip(trace, states, strict=True):
        observed = gatesim.marked_probability(state, task.marked)
        error = abs(observed - float(probability))
        if error > PROBABILITY_TOLERANCE or not math.isfinite(error):
            raise ValueError("gate replay and exact reference disagree")
        errors.append(error)
    first = next(((iteration, probability) for iteration, probability in enumerate(trace)
                  if probability >= task.target), None)
    return {"first": first, "trace": trace, "max_difference": max(errors)}


def verify(task, answer):
    """Score the exact pair (earliest iteration, probability), or None for no hit."""
    expected = reference(task)["first"]
    if answer is None:
        return expected is None
    return (isinstance(answer, tuple) and len(answer) == 2
            and type(answer[0]) is int and isinstance(answer[1], Fraction)
            and answer == expected)


# Public fixtures for the verifier. Future held-out task seeds stay separate.
CONTROLS = {
    "overshoot": ThresholdTask(3, (5,), 4, Fraction(9, 10)),
    "boundary": ThresholdTask(3, (5,), 4, Fraction(25, 32)),
    "no_hit": ThresholdTask(3, (5,), 4, Fraction(1)),
    "multiple_marked": ThresholdTask(3, (1, 6), 4, Fraction(1)),
}


if __name__ == "__main__":
    print(json.dumps({"instrument_validation": True,
                      "controls": {name: reference(task) for name, task in CONTROLS.items()}},
                     sort_keys=True, indent=2, default=str))
