import unittest

from lab import r6_m1_enum as w2
from lab import r6_pvsnp_tasks as w1


class Agreement(unittest.TestCase):
    """Slow: W1 (DP) and W2 (enumeration) must agree on every table."""

    def test_formula_and_circuit_tables(self):
        for n in (2, 3, 4):
            for basis in w1.BASES:
                with self.subTest(n=n, basis=basis):
                    self.assertEqual(w1.min_formula_size(n, basis), w2.min_formula_size(n, basis))
            with self.subTest(n=n, what="circuit"):
                self.assertEqual(w1.min_circuit_size(n), w2.min_circuit_size(n))

    def test_class_counts(self):
        for n in (2, 3, 4):
            self.assertEqual(w1.npn_class_count(n), w2.class_count(n))
