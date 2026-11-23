import unittest
from fractions import Fraction

from lab import r1_readout_controls as controls


class ReadoutControlTests(unittest.TestCase):
    def test_l1_changes_dispersion_and_slope_independently_at_matching_means(self):
        cases = controls.l1_controls()
        self.assertEqual(len(cases), 4)
        for case in cases:
            with self.subTest(variance=case["variance"], response=case["response"]):
                concentrated = case["variance"] == "binomial_variance"
                expected_slope = 0.25 if case["response"] == "increasing" else 0
                self.assertEqual(sum(map(sum, case["reruns"])), 5)
                self.assertEqual(sum(case["outcomes"]), 2)
                self.assertEqual(case["overdispersion"], 1 if concentrated else 2)
                self.assertEqual(case["mean_within_set_variance"], 0.3 if concentrated else 0.1)
                self.assertEqual(case["linear_dose_slope"], expected_slope)
                self.assertEqual(case["scripted_bootstrap_interval"], [expected_slope] * 2)

    def test_l3_detects_copied_errors_at_the_same_individual_miss_rates(self):
        cases = controls.l3_controls()
        independent, copied = cases["independent_views"], cases["copied_views"]
        self.assertEqual(independent["joint"], [[0.5, 0.25], [0.25, 0.5]])
        self.assertEqual(copied["joint"], [[0.5, 0.5], [0.5, 0.5]])
        self.assertEqual((independent["rho_bar"], copied["rho_bar"]), (0, 1))
        self.assertEqual((independent["n_eff"], copied["n_eff"]), (2, 1))

    def test_l7_detects_fewer_distinct_error_sources_in_a_bigger_team(self):
        cases = controls.l7_controls()
        null, repeated = cases["independent_growth"], cases["four_sources"]
        self.assertEqual(null["rho_32_minus_4"], 0)
        self.assertAlmostEqual(repeated["rho_32_minus_4"], float(Fraction(7, 31)))
        self.assertEqual(repeated["sizes"]["32"]["correlation_range"], [0, 1])
        for key, expected in (("independent_growth", 32), ("four_sources", 4)):
            self.assertEqual(cases[key]["sizes"]["4"]["kish_diagnostic"], 4)
            self.assertAlmostEqual(cases[key]["sizes"]["32"]["kish_diagnostic"], expected)
