import unittest

from lab.r1_kish_spread import diagnose


class KishSpreadTests(unittest.TestCase):
    def test_constant_monitors_have_no_observed_correlations(self):
        result = diagnose([[0, 0], [1, 1]])
        self.assertEqual((result["observed_pairs"], result["possible_pairs"]), (0, 1))
        self.assertIsNone(result["observed_phi_range"])
        self.assertIsNone(result["kish_effective_size"])

    def test_partial_correlation_coverage_reports_spread_without_extrapolating(self):
        result = diagnose([[1, 0], [1, 0], [0, 0]])
        self.assertEqual((result["observed_pairs"], result["possible_pairs"]), (1, 3))
        self.assertEqual(result["observed_phi_range"], [1, 1])
        self.assertIsNone(result["kish_denominator"])
        self.assertIsNone(result["kish_effective_size"])

    def test_complete_cohort_keeps_the_observed_nonuniform_spread(self):
        result = diagnose([[1, 1, 0, 0], [1, 1, 0, 0], [1, 0, 1, 0]])
        self.assertEqual((result["observed_pairs"], result["possible_pairs"]), (3, 3))
        self.assertEqual(result["observed_phi_range"], [0, 1])
        self.assertAlmostEqual(result["observed_mean_phi"], 1 / 3)
        self.assertAlmostEqual(result["kish_effective_size"], 1.8)

    def test_complementary_monitors_have_no_finite_kish_estimate(self):
        result = diagnose([[1, 0, 0], [0, 1, 1]])
        self.assertEqual(result["observed_phi_range"], [-1, -1])
        self.assertEqual(result["kish_denominator"], 0)
        self.assertIsNone(result["kish_effective_size"])

    def test_cancelling_correlations_do_not_produce_a_huge_finite_estimate(self):
        for size in (4, 6):
            with self.subTest(size=size):
                result = diagnose([[int(i == j) for j in range(size)] for i in range(size)])
                self.assertAlmostEqual(result["observed_mean_phi"], -1 / (size - 1))
                self.assertAlmostEqual(result["kish_denominator"], 0)
                self.assertIsNone(result["kish_effective_size"])

    def test_invalid_observations_are_rejected(self):
        for rows in ([], [[]], [[1], [1, 0]], [[1, None]], [[0.0, 1]]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                diagnose(rows)
