"""Bench defect D1 (runs/x42-r1-bench-verdict.uPqmQ9): pairwise_miss must not report undefined Kish values."""
import unittest

from tremor import readouts as R


class KishGuard(unittest.TestCase):
    def test_no_defined_pair_is_missing_not_independent(self):
        r = R.pairwise_miss([[1, 1, 1], [1, 1, 1], [0, 0, 0]])
        self.assertEqual((r["rho_bar"], r["rho_min"], r["rho_max"], r["n_eff"]), (None, None, None, None))

    def test_near_zero_denominator_has_no_kish_size(self):
        r = R.pairwise_miss([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
        self.assertAlmostEqual(r["rho_bar"], -0.5)
        self.assertIsNone(r["n_eff"])

    def test_anticorrelated_pair_has_no_kish_size(self):
        r = R.pairwise_miss([[1, 0], [0, 1]])
        self.assertEqual(r["rho_bar"], -1.0)
        self.assertIsNone(r["n_eff"])

    def test_defined_cases_unchanged(self):
        self.assertEqual(R.pairwise_miss([[1, 0], [1, 0]])["n_eff"], 1.0)
        r = R.pairwise_miss([[1, 0, 1, 0], [1, 1, 0, 0]])
        self.assertEqual((r["rho_bar"], r["n_eff"]), (0.0, 2.0))


if __name__ == "__main__":
    unittest.main()
