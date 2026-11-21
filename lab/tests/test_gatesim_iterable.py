import unittest
from enum import IntEnum
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

    def test_marked_indices_are_checked_even_without_iterations(self):
        state = gatesim.initial_state(2)
        for invalid in (-1, 4, None, 1.0):
            with self.subTest(index=invalid):
                with self.assertRaises(ValueError):
                    gatesim.grover_states(2, [invalid], 0)
                with self.assertRaises(ValueError):
                    gatesim.marked_probability(state, [invalid])

    def test_duplicate_marked_indices_count_once(self):
        index = IntEnum("Basis", {"LAST": 3}).LAST
        self.assertEqual(gatesim.grover_states(2, [3, index], 2), gatesim.grover_states(2, [3], 2))
        state = gatesim.initial_state(2)
        self.assertEqual(gatesim.marked_probability(state, [3, 3]), gatesim.marked_probability(state, [3]))
