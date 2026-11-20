"""Differential test: our stdlib gatesim vs QGrid's numpy statevector.py (read-only import by file path).

Phase convention: per QGrid's docstring both use D @ O, so amplitudes must agree INCLUDING global phase.
If they differ only by a global phase that is a convention difference: it is counted separately and the
test then requires the probabilities to agree. Every disagreement is written to quantum/differential-report.md.
"""
import importlib.util
import math
import os
import random
import unittest
from collections import Counter

from quantum import gatesim as g

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
QG = os.path.join(ROOT, "data", "qgrid", "quantum", "statevector.py")
REPORT = os.path.join(ROOT, "lab", "quantum", "differential-report.md")
AMP_TOL, PROB_TOL = 1e-9, 1e-12

sv = None
SKIP = None
if not os.path.isfile(QG):
    SKIP = "data/qgrid/quantum/statevector.py not found"
else:
    try:
        import numpy  # noqa: F401
        spec = importlib.util.spec_from_file_location("qgrid_statevector", QG)
        sv = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sv)
    except ImportError as e:
        SKIP = "numpy unavailable (%s)" % e


def instances(seed=20261120):
    rng = random.Random(seed)
    for n in range(1, 11):
        N = 1 << n
        sizes = {0, 1, N, max(0, N - 1), N // 2, rng.randint(1, N)}
        for M in sorted(sizes):
            yield n, sorted(rng.sample(range(N), M))
        yield n, sorted(rng.sample(range(N), min(N, 3)))  # a small set per n


def global_phase(a, b):
    """Return the phase c (|c|=1) with a == c*b elementwise within tol, else None."""
    i = max(range(len(b)), key=lambda j: abs(b[j]))
    if abs(b[i]) < 1e-12:
        return None
    c = a[i] / b[i]
    if abs(abs(c) - 1) > 1e-9:
        return None
    return c if all(abs(x - c * y) <= AMP_TOL for x, y in zip(a, b)) else None


@unittest.skipIf(SKIP, SKIP or "")
class Differential(unittest.TestCase):
    def test_against_qgrid(self):
        cats, repro, n_cases, n_states = Counter(), {}, 0, 0
        theory = Counter()  # which implementation the closed form supports

        def note(cat, inst):
            cats[cat] += 1
            if cat not in repro or (len(inst[1]), inst[0]) < (len(repro[cat][1]), repro[cat][0]):
                repro[cat] = inst

        for n, marked in instances():
            N, M = 1 << n, len(marked)
            n_cases += 1
            if sv.optimal_iterations(N, M) != g.optimal_iterations(N, M):
                note("optimal_iterations", (n, marked, 0))
            kopt = g.optimal_iterations(N, M)
            mine = g.grover_states(n, marked, kopt + 2)
            theirs = sv.grover_states(n, marked, kopt + 2)
            if len(mine) != len(theirs):
                note("state_count", (n, marked, kopt + 2))
                continue
            for k, (a, b) in enumerate(zip(mine, theirs)):
                n_states += 1
                inst = (n, marked, k)
                b = [complex(x) for x in b]
                pm, pq = g.marked_probability(a, marked), float(sum(abs(b[m]) ** 2 for m in set(marked)))
                cf = g.closed_form(N, M, k)
                theory["gatesim"] += abs(pm - cf) <= 1e-9
                theory["qgrid"] += abs(pq - cf) <= 1e-9
                if abs(pm - pq) > PROB_TOL:
                    note("marked_probability", inst)
                if max(abs(x - y) for x, y in zip(a, b)) <= AMP_TOL:
                    continue
                c = global_phase(a, b)
                note("global_phase_only" if c is not None else "amplitude", inst)
                if c is None:
                    continue
                self.assertLessEqual(abs(pm - pq), PROB_TOL, inst)  # phase-only: probabilities must agree

        lines = ["# Differential report: gatesim vs QGrid statevector.py", "",
                 "Instances: %d; statevectors compared: %d; amplitude tol %g, probability tol %g."
                 % (n_cases, n_states, AMP_TOL, PROB_TOL),
                 "Convention: D @ O, amplitudes compared INCLUDING global phase.", "",
                 "Total disagreements: %d" % sum(cats.values()), ""]
        lines += ["- %s: %d (minimal repro n=%d marked=%s k=%d)" % ((c, v) + (repro[c][0], repro[c][1], repro[c][2]))
                  for c, v in sorted(cats.items())] or ["- none"]
        lines += ["", "Closed-form sin^2((2k+1)theta) agreement over %d states: gatesim %d, qgrid %d."
                  % (n_states, theory["gatesim"], theory["qgrid"])]
        text = "\n".join(lines) + "\n"
        try:
            with open(REPORT, "w") as f:
                f.write(text)
        except OSError:
            print("\n[report not written: read-only mount]\n" + text)
        bad = {c: v for c, v in cats.items() if c != "global_phase_only"}
        self.assertEqual(bad, {}, text)


if __name__ == "__main__":
    unittest.main()
