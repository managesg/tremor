from copy import deepcopy
import unittest

from lab import l3_equal_budget_monitors as monitors


class L3EqualBudgetMonitorTests(unittest.TestCase):
    @staticmethod
    def failure_rows(prefix):
        return [
            {"id": f"{prefix}-{index}", "failure": True, "views": {"A": a, "B": a, "C": c}}
            for index, (a, c) in enumerate(((0, 0), (0, 1), (1, 0), (1, 1)))
        ]

    @staticmethod
    def clean_rows(prefix):
        return [
            {"id": f"{prefix}-{index}", "failure": False, "views": dict.fromkeys(("A", "B", "C"), int(index == 0))}
            for index in range(20)
        ]

    def fitted_plan(self):
        return monitors.fit(self.failure_rows("calibration"), self.clean_rows("threshold"))

    def test_positive_and_null_match_exact_catches_and_discordant_counts(self):
        demo = monitors.demo()
        self.assertIs(demo["scientific_result"], False)
        self.assertEqual(demo["scope"], "L3_B_fallback_development")
        expected = {
            "positive": (("A", "C"), 3, {"both": 2, "selected_only": 1, "top_only": 0, "neither": 1}, 1, 4),
            "null": (("A", "B"), 2, {"both": 2, "selected_only": 0, "top_only": 0, "neither": 2}, 0, 1),
        }
        self.assertEqual(set(demo["cases"]), set(expected))
        for case, (pair, catches, discordance, numerator, denominator) in expected.items():
            with self.subTest(case=case):
                report = demo["cases"][case]
                top, selected = report["arms"]["top"], report["arms"]["selected"]
                self.assertEqual(tuple(top["pair"]), ("A", "B"))
                self.assertEqual(tuple(selected["pair"]), pair)
                self.assertEqual(top["heldout_catches"], 2)
                self.assertEqual(selected["heldout_catches"], catches)
                self.assertEqual(report["paired_failure_flags"], discordance)
                self.assertIs(report["heldout_target_matched"], True)
                self.assertEqual(report["heldout_catch_gain"], {"numerator": numerator, "denominator": denominator})

    def test_assessment_split_cannot_overlap_either_fit_split(self):
        calibration = self.failure_rows("calibration")
        threshold = self.clean_rows("threshold")
        threshold[0]["id"] = calibration[0]["id"]
        with self.assertRaises(ValueError):
            monitors.fit(calibration, threshold)
        plan = self.fitted_plan()
        pin = monitors.digest(plan)
        cases = (
            (self.clean_rows("threshold"), self.failure_rows("heldout-failure")),
            (self.clean_rows("heldout-clean"), self.failure_rows("calibration")),
        )
        for clean, failure in cases:
            with self.subTest(overlap=(clean[0]["id"], failure[0]["id"])), self.assertRaises(ValueError):
                monitors.evaluate(plan, clean, failure, plan_sha256=pin)

    def test_equal_call_counts_include_both_calibration_and_holdout_costs(self):
        demo = monitors.demo()
        expected_calls = {"calibration_failure": 12, "threshold_fit_clean": 40,
                          "heldout_clean": 40, "heldout_failure": 8, "total": 100}
        fp_rate = {"numerator": 1, "denominator": 20}
        for case, result in demo["cases"].items():
            for name, arm in result["arms"].items():
                with self.subTest(case=case, arm=name):
                    self.assertEqual(arm["call_counts"], expected_calls)
                    self.assertEqual(arm["threshold_fit_false_positives"], 1)
                    self.assertEqual(arm["heldout_false_positives"], 1)
                    self.assertEqual(arm["threshold_fit_false_positive_rate"], fp_rate)
                    self.assertEqual(arm["heldout_false_positive_rate"], fp_rate)

    def test_holdout_truth_cannot_change_the_fitted_pairs_or_cutoffs(self):
        plan = self.fitted_plan()
        pin = monitors.digest(plan)
        clean = self.clean_rows("heldout-clean")
        failure = self.failure_rows("heldout-failure")
        original = monitors.evaluate(plan, clean, failure, plan_sha256=pin)
        changed_clean, changed_failure = deepcopy(clean), deepcopy(failure)
        changed_clean[1] = {**failure[1], "failure": False}
        changed_failure[1] = {**clean[1], "failure": True}
        changed = monitors.evaluate(plan, changed_clean, changed_failure, plan_sha256=pin)
        self.assertEqual(monitors.digest(plan), pin)
        for name in original["arms"]:
            with self.subTest(arm=name):
                for field in ("pair", "cutoff", "calibration_joint_misses", "threshold_fit_false_positives"):
                    self.assertEqual(original["arms"][name][field], changed["arms"][name][field])
        self.assertEqual(changed["arms"]["selected"]["heldout_false_positives"], 2)
        self.assertEqual(changed["arms"]["top"]["heldout_false_positives"], 1)
        self.assertIs(changed["heldout_target_matched"], False)
        self.assertIsNone(changed["heldout_catch_gain"])

    def test_changed_fit_plan_is_refused_at_original_pin(self):
        plan = self.fitted_plan()
        pin = monitors.digest(plan)
        changed = {**plan, "forged": True}
        with self.assertRaises(ValueError):
            monitors.evaluate(changed, self.clean_rows("heldout-clean"), self.failure_rows("heldout-failure"),
                              plan_sha256=pin)

    def test_malformed_view_matrix_cannot_silently_drop_columns_or_impute_results(self):
        for kind in ("missing", "nonbinary"):
            with self.subTest(kind=kind):
                rows = self.failure_rows("calibration")
                if kind == "missing":
                    del rows[1]["views"]["B"]
                else:
                    rows[1]["views"]["B"] = 2
                with self.assertRaises(ValueError):
                    monitors.fit(rows, self.clean_rows("threshold"))
