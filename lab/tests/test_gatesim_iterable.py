import unittest
from fractions import Fraction

from lab.quantum import gatesim
from lab.quantum.transfer import ThresholdTask, exact_trace


class FixedOracleTests(unittest.TestCase):
    def test_one_shot_marked_iterable_matches_exact_multi_step_trace(self):
        marked = (1, 6, 7)
        task = ThresholdTask(4, marked, 5, Fraction(1))
        states = gatesim.grover_states(task.qubits, iter(marked), task.max_iterations)
        self.assertEqual(states, gatesim.grover_states(task.qubits, marked, task.max_iterations))
        for state, probability in zip(states, exact_trace(task), strict=True):
            self.assertAlmostEqual(gatesim.marked_probability(state, marked), float(probability), places=12)
