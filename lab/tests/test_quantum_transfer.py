import unittest
from fractions import Fraction
from unittest.mock import patch

from lab.quantum import transfer


class QuantumTransferTests(unittest.TestCase):
    def test_first_hit_and_overshoot(self):
        task = transfer.CONTROLS["overshoot"]
        result = transfer.reference(task)
        self.assertEqual(result["first"], (2, Fraction(121, 128)))
        self.assertEqual(result["trace"], [Fraction(v) for v in ("1/8", "25/32", "121/128", "169/512", "25/2048")])
        self.assertTrue(transfer.verify(task, (2, Fraction(121, 128))))
        self.assertFalse(transfer.verify(task, (3, Fraction(169, 512))))
        self.assertFalse(transfer.verify(task, None))

    def test_equality_full_mark_probability_and_no_hit(self):
        self.assertEqual(transfer.reference(transfer.CONTROLS["boundary"])["first"],
                         (1, Fraction(25, 32)))
        self.assertTrue(transfer.verify(transfer.CONTROLS["multiple_marked"], (1, Fraction(1))))
        self.assertTrue(transfer.verify(transfer.CONTROLS["no_hit"], None))
        task = transfer.ThresholdTask(1, (0, 1), 0, Fraction(1))
        self.assertTrue(transfer.verify(task, (0, Fraction(1))))
        self.assertFalse(transfer.verify(task, (False, Fraction(1))))

    def test_initial_three_quarters_equality_is_the_earliest_hit(self):
        target = Fraction(3, 4)
        for qubits in range(2, transfer.MAX_QUBITS + 1):
            with self.subTest(qubits=qubits):
                marked = tuple(range(3 * (1 << qubits) // 4))
                task = transfer.ThresholdTask(qubits, marked, 2, target)
                result = transfer.reference(task)
                self.assertEqual(result["trace"], [target, Fraction(0), target])
                self.assertTrue(transfer.verify(task, (0, target)))
                self.assertFalse(transfer.verify(task, (2, target)))
                self.assertFalse(transfer.verify(task, None))

    def test_independent_gate_disagreement_refuses(self):
        with patch.object(transfer.gatesim, "marked_probability", return_value=0):
            with self.assertRaisesRegex(ValueError, "disagree"):
                transfer.reference(transfer.CONTROLS["boundary"])

    def test_invalid_marking_is_refused_before_scoring(self):
        for indices in ([0], (0, 0), (2,), (False,)):
            with self.subTest(indices=indices), self.assertRaises(ValueError):
                transfer.ThresholdTask(1, indices, 1, Fraction(1))
