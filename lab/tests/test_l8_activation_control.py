import unittest
from fractions import Fraction

from lab.l8_activation_control import Episode, calibrate, compare, evaluate


class ActivationControlTests(unittest.TestCase):
    def test_same_standalone_catch_rates_but_only_complementary_view_improves_ensemble(self):
        controls = compare()["controls"]
        complementary, copied = controls["complementary"], controls["copied"]
        for result in (complementary, copied):
            self.assertEqual(result["calibration_clean_task_sets"], 400)
            self.assertEqual(result["heldout_clean_task_sets"], 400)
            self.assertEqual(result["heldout_failure_task_sets"], 200)
            self.assertTrue(result["matched_at_target"])
            self.assertEqual(result["false_positive_counts"], dict(text=20, activation=20, combined=20))
            self.assertEqual(result["catch_counts"]["text"], 120)
            self.assertEqual(result["catch_counts"]["activation"], 120)
        self.assertEqual(complementary["catch_counts"]["combined"], 168)
        self.assertEqual(complementary["combined_catch_gain"], Fraction(6, 25))
        self.assertEqual(complementary["paired_failure_flags"],
                         dict(both=120, text_only=0, combined_only=48, neither=32))
        self.assertEqual(complementary["paired_clean_flags"],
                         dict(both=10, text_only=10, combined_only=10, neither=370))
        self.assertEqual(complementary["text_activation_joint_misses"], 32)
        self.assertAlmostEqual(complementary["text_activation_miss_phi"], 0)
        self.assertEqual(copied["catch_counts"]["combined"], 120)
        self.assertEqual(copied["combined_catch_gain"], 0)
        self.assertEqual(copied["text_activation_joint_misses"], 80)
        self.assertAlmostEqual(copied["text_activation_miss_phi"], 1)

    def test_cutoff_tie_is_never_split_by_heldout_labels_or_ids(self):
        result = compare()["controls"]["cutoff_tie"]
        self.assertFalse(result["matched_at_target"])
        self.assertEqual(result["operating_points"]["combined"],
                         dict(cutoff=80, calibration_flagged=16, calibration_tied_at_cutoff=10))
        self.assertEqual(result["false_positive_rates"]["combined"], Fraction(1, 25))

    def test_calibration_only_thresholds_stay_frozen_under_heldout_shift(self):
        clean = [Episode(f"cal-{i}", False, int(i < 20), int(i < 20)) for i in range(400)]
        frozen = calibrate(clean)
        heldout = [Episode(f"eval-{i}", False, int(i < 20), int(i < 25)) for i in range(400)]
        heldout.append(Episode("failure", True, 0, 1))
        result = evaluate(frozen, heldout)
        self.assertEqual(result["false_positive_counts"], dict(text=20, activation=25, combined=25))
        self.assertFalse(result["matched_at_target"])
        self.assertEqual(frozen, calibrate(list(reversed(clean))))
        self.assertEqual(result, evaluate(frozen, list(reversed(heldout))))
        self.assertIsNone(result["text_activation_miss_phi"])

    def test_rejects_calibration_failures_and_shared_task_sets(self):
        clean = Episode("task-a", False, 0, 1)
        failure = Episode("task-b", True, 0, 1)
        with self.assertRaisesRegex(ValueError, "requires clean"):
            calibrate([clean, failure])
        with self.assertRaisesRegex(ValueError, "overlap"):
            evaluate(calibrate([clean]), [Episode("task-a", True, 1, 0), failure])
        with self.assertRaisesRegex(ValueError, "unique"):
            evaluate(calibrate([clean]), [failure, failure])
