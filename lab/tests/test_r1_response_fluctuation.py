from fractions import Fraction
import unittest

from lab.r1_response_fluctuation import demo, measure


class ResponseFluctuationTests(unittest.TestCase):
    dose_groups = ((0, (0, 0, 1, 1, 1)), (1, (0, 1, 1, 1, 2)), (2, (1, 1, 1, 2, 2)))

    def test_same_mean_and_count_slope_with_different_reference_variance(self):
        ordinary = measure(self.dose_groups, team_size=2, reference_dose=1)
        higher = measure(
            (self.dose_groups[0], (1, (0, 0, 1, 2, 2)), self.dose_groups[2]),
            team_size=2, reference_dose=1,
        )
        for result, variance, dispersion, ratio in (
            (ordinary, Fraction(1, 2), 1, Fraction(4, 5)),
            (higher, Fraction(1), 2, Fraction(2, 5)),
        ):
            self.assertEqual(result["reference_adoption_count_mean"], 1)
            self.assertEqual(result["count_scale_slope"], Fraction(2, 5))
            self.assertEqual(result["reference_sample_count_variance"], variance)
            self.assertEqual(result["reference_binomial_count_variance"], Fraction(1, 2))
            self.assertEqual(result["reference_overdispersion"], dispersion)
            self.assertEqual(result["candidate_slope_per_sample_count_variance"], ratio)

    def test_flat_response_at_positive_variance_gives_zero_ratio(self):
        counts = self.dose_groups[1][1]
        result = measure(enumerate((counts,) * 3), team_size=2, reference_dose=1)
        self.assertEqual(result["count_scale_slope"], 0)
        self.assertEqual(result["reference_sample_count_variance"], Fraction(1, 2))
        self.assertEqual(result["candidate_slope_per_sample_count_variance"], 0)

    def test_zero_variance_with_nonboundary_mean_leaves_candidate_ratio_undefined(self):
        groups = (self.dose_groups[0], (1, (1,) * 5), self.dose_groups[2])
        result = measure(groups, team_size=2, reference_dose=1)
        self.assertEqual(result["count_scale_slope"], Fraction(2, 5))
        self.assertEqual(result["reference_sample_count_variance"], 0)
        self.assertEqual(result["reference_overdispersion"], 0)
        self.assertIsNone(result["candidate_slope_per_sample_count_variance"])

    def test_both_binomial_boundaries_and_insufficient_reference_reruns(self):
        for count in (0, 2):
            with self.subTest(count=count):
                result = measure(enumerate(((count,) * 5,) * 3), team_size=2, reference_dose=1)
                self.assertEqual(result["reference_binomial_count_variance"], 0)
                self.assertIsNone(result["reference_overdispersion"])
                self.assertIsNone(result["candidate_slope_per_sample_count_variance"])
        groups = (self.dose_groups[0], (1, (1,)), self.dose_groups[2])
        result = measure(groups, team_size=2, reference_dose=1)
        self.assertEqual(result["count_scale_slope"], Fraction(2, 5))
        self.assertIsNone(result["reference_sample_count_variance"])
        self.assertIsNone(result["reference_overdispersion"])
        self.assertIsNone(result["candidate_slope_per_sample_count_variance"])

    def test_fractional_dose_keeps_count_scale_and_uses_named_reference(self):
        dose_groups = tuple((Fraction(dose, 2), counts) for dose, counts in reversed(self.dose_groups))
        result = measure(dose_groups, team_size=2, reference_dose=Fraction(1, 2))
        self.assertEqual(result["reference_dose"], Fraction(1, 2))
        self.assertEqual(result["count_scale_slope"], Fraction(4, 5))
        self.assertEqual(result["candidate_slope_per_sample_count_variance"], Fraction(8, 5))

    def test_invalid_roster_dose_or_counts_are_rejected(self):
        for groups, team, reference in (
            (self.dose_groups, True, 1),
            (self.dose_groups, 2, 3),
            (self.dose_groups[:2], 2, 1),
            (self.dose_groups + ((1, (1,)),), 2, 1),
            (self.dose_groups + ((3, (3,)),), 2, 1),
            (self.dose_groups + ((3, (True,)),), 2, 1),
            (self.dose_groups + ((3, ()),), 2, 1),
            (self.dose_groups + ((3.0, (1,)),), 2, 1),
        ):
            with self.subTest(groups=groups, team=team, reference=reference), self.assertRaises(ValueError):
                measure(groups, team_size=team, reference_dose=reference)

    def test_demo_is_explicitly_development_only(self):
        report = demo()
        self.assertEqual(report["scope"], "scripted_development")
        self.assertIs(report["scientific_result"], False)
        self.assertEqual(report["cases"]["positive"]["count_scale_slope"], {"numerator": 2, "denominator": 5})
        self.assertIsNone(report["cases"]["zero_observed_variance"]["candidate_slope_per_sample_count_variance"])
