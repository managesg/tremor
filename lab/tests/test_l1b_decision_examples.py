import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lab import l1_dispatch_replay, l1_scoring_replay, l1_verification_allocation, l1b_decision_examples


class L1BDecisionExamplesTests(unittest.TestCase):
    dispatch_sha256 = "397985a50f8ac6576b52877e911c731f1f171d713e21b56708015180b3c85e42"
    labels_sha256 = "51d6b11f000ee1f1b6641138ea51a3d9ef26cd0194c0ec2f5c306a9492bbc720"
    scored_sha256 = "b867b3c3ece68b95c9f9fc66d57e394ce11c06463dfe472f2e34c9f7d294ce3d"

    @classmethod
    def setUpClass(cls):
        cls.root = Path(cls.enterClassContext(TemporaryDirectory()))
        # Rebuild the documented public archive so ignored Spark run paths are unnecessary in a fresh checkout.
        reference = cls.root / "reference.json"
        cls.write(reference, l1_verification_allocation.demo(), indent=2)
        labels = cls.root / "labels.json"
        cls.write(labels, l1_scoring_replay.reference_labels(reference), indent=2)
        bundle = cls.root / "dispatch"
        l1_dispatch_replay.run(bundle)
        archived = l1_scoring_replay.replay(bundle, reference, labels, pins_sha256=cls.dispatch_sha256,
                                            labels_sha256=cls.labels_sha256)
        cls.scored_archive = cls.root / "scored.json"
        cls.write(cls.scored_archive, archived)
        cls.result = l1b_decision_examples.report(cls.scored_archive, scored_sha256=cls.scored_sha256)

    @staticmethod
    def write(path, document, *, indent=None):
        raw = (json.dumps(document, sort_keys=True, allow_nan=False, indent=indent) + "\n").encode()
        path.write_bytes(raw)

    @staticmethod
    def ratio(numerator, denominator):
        return {"numerator": numerator, "denominator": denominator}

    def test_different_baseline_rates_change_cluster_aggregation(self):
        case = self.result["fictional_cases"]["positive_denominators"]
        self.assertEqual(case["ratio_of_equal_arm_means"], self.ratio(2, 11))
        self.assertEqual(case["mean_cluster_ratios"], self.ratio(11, 20))
        self.assertEqual(case["absolute_guided_minus_uniform"], self.ratio(-1, 100))

    def test_zero_baseline_draw_stays_in_the_paired_resampling_inventory(self):
        case = self.result["fictional_cases"]["one_zero_denominator"]
        self.assertIsNone(case["mean_cluster_ratios"])
        bootstrap = case["paired_bootstrap"]
        self.assertEqual((bootstrap["total_draws"], bootstrap["undefined_draws"]), (4, 1))
        self.assertEqual([row["indices"] for row in bootstrap["draws"]], [[0, 0], [0, 1], [1, 0], [1, 1]])
        self.assertEqual([row["relative_reduction"] for row in bootstrap["draws"]],
                         [None, self.ratio(0, 1), self.ratio(0, 1), self.ratio(1, 1)])

    def test_all_zero_baselines_leave_relative_effects_undefined_and_absolute_risk_positive(self):
        case = self.result["fictional_cases"]["all_zero_denominators"]
        self.assertEqual(case["uniform_rates"], [self.ratio(0, 1), self.ratio(0, 1)])
        self.assertIsNone(case["ratio_of_equal_arm_means"])
        self.assertIsNone(case["mean_cluster_ratios"])
        self.assertEqual(case["absolute_guided_minus_uniform"], self.ratio(1, 100))

    def test_stopped_public_archive_bounds_are_exact_and_no_inference_is_selected(self):
        self.assertEqual(hashlib.sha256(self.scored_archive.read_bytes()).hexdigest(), self.scored_sha256)
        stopped = self.result["stopped_sensitivity"]
        self.assertEqual(stopped["scored_sha256"], self.scored_sha256)
        self.assertEqual(stopped["scheduled_claims"], 32)
        self.assertEqual(stopped["independently_false_claims"], 4)
        self.assertEqual(stopped["known_original_false_completions"], 2)
        self.assertEqual(stopped["unknown_false_selected"], 2)
        self.assertEqual(stopped["possible_false_completions"], {"min": 2, "max": 4})
        self.assertEqual(stopped["schedule_rate_bounds"], {"min": self.ratio(1, 16), "max": self.ratio(1, 8)})
        self.assertEqual(stopped["false_population_rate_bounds"], {"min": self.ratio(1, 2), "max": self.ratio(1, 1)})
        self.assertEqual(self.result["status"], "illustrations_only")
        self.assertIsNone(self.result["selected_estimand"])
        self.assertIsNone(self.result["scientific_rate"])
        self.assertIs(self.result["execution_authorized"], False)

    def test_changed_archive_is_refused_under_either_original_or_replacement_pin(self):
        changed = self.root / "changed.json"
        raw = self.scored_archive.read_bytes() + b"\n"
        changed.write_bytes(raw)
        replacement = hashlib.sha256(raw).hexdigest()
        self.assertNotEqual(replacement, self.scored_sha256)
        for pin in (self.scored_sha256, replacement):
            with self.subTest(pin=pin), self.assertRaises(ValueError):
                l1b_decision_examples.report(changed, scored_sha256=pin)
