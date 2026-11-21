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

    def test_independent_gate_disagreement_refuses(self):
        with patch.object(transfer.gatesim, "marked_probability", return_value=0):
            with self.assertRaisesRegex(ValueError, "disagree"):
                transfer.reference(transfer.CONTROLS["boundary"])

    def test_invalid_marking_is_refused_before_scoring(self):
        for indices in ([0], (0, 0), (2,), (False,)):
            with self.subTest(indices=indices), self.assertRaises(ValueError):
                transfer.ThresholdTask(1, indices, 1, Fraction(1))
