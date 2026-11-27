"""Run a small Grover circuit and write a probability trace as JSON."""

import argparse
import json
import math

from .gatesim import closed_form, grover_states, marked_probability


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qubits", type=int, required=True, help="number of qubits, 1 to 10")
    parser.add_argument("--marked", type=int, nargs="*", required=True, help="marked basis indices")
    parser.add_argument("--iterations", type=int, required=True, help="number of iterations, 0 to 128")
    args = parser.parse_args()

    if not 1 <= args.qubits <= 10:
        parser.error("--qubits must be between 1 and 10")
    if not 0 <= args.iterations <= 128:
        parser.error("--iterations must be between 0 and 128")

    marked = sorted(set(args.marked))
    try:
        states = grover_states(args.qubits, marked, args.iterations)
    except ValueError as error:
        parser.error(str(error))

    trace = []
    for iteration, state in enumerate(states):
        probability = marked_probability(state, marked)
        expected = closed_form(1 << args.qubits, len(marked), iteration)
        trace.append({
            "iteration": iteration,
            "marked_probability": probability,
            "closed_form_probability": expected,
            "absolute_error": abs(probability - expected),
            "normalization_error": abs(math.fsum(abs(a) ** 2 for a in state) - 1),
        })
    print(json.dumps({
        "qubits": args.qubits,
        "marked": marked,
        "iterations": args.iterations,
        "trace": trace,
    }, indent=2))


if __name__ == "__main__":
    main()
