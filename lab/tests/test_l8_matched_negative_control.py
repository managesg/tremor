from fractions import Fraction
from math import sqrt
import unittest

from lab import l8_matched_negative_control


class L8MatchedNegativeControlTests(unittest.TestCase):
    def test_uncorrelated_misses_can_coexist_with_a_matched_rate_loss(self):
        result = l8_matched_negative_control.compare()
        self.assertIs(result["scientific_result"], False)
        assessment = result["assessment"]
        self.assertTrue(assessment["matched_at_target"])
        self.assertEqual(assessment["false_positive_counts"], dict(text=20, activation=20, combined=20))
        self.assertEqual(assessment["catch_counts"], dict(text=130, activation=90, combined=90))
        self.assertEqual(assessment["paired_failure_flags"],
                         dict(both=60, text_only=70, combined_only=30, neither=40))
        self.assertEqual(assessment["combined_catch_gain"], -Fraction(1, 5))
        self.assertEqual(assessment["text_activation_joint_misses"], 40)
        expected_phi = (60 * 40 - 70 * 30) / sqrt(130 * 70 * 90 * 110)
        self.assertAlmostEqual(assessment["text_activation_miss_phi"], expected_phi)
