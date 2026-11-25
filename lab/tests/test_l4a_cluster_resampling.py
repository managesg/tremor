from copy import deepcopy
from fractions import Fraction
import unittest

from lab import l4a_cluster_resampling as resampling, l4a_segmented_control as control
from lab.l4_measured_compression import pin
from lab.l4a_cluster_distribution import distribution


class L4AClusterResamplingTests(unittest.TestCase):
    @staticmethod
    def fraction(ratio):
        return Fraction(**ratio)

    @classmethod
    def histogram(cls, report):
        return [(cls.fraction(row["gain"]), row["draws"]) for row in report["histogram"]]

    @staticmethod
    def paired_case():
        training, holdout = control.fixture("kink")
        fitted = control.fit_training(training, expected_training_pin=pin(training), knots=control.KNOTS)
        scored = control.score_holdout(holdout, fitted, expected_holdout_pin=pin(holdout), expected_fit_pin=pin(fitted))
        return training, holdout, fitted, scored

    def test_conditional_and_joint_bootstrap_have_different_exact_distributions(self):
        demo = resampling.demo()
        conditional, joint = demo["conditional"], demo["refit"]
        self.assertEqual(conditional["method"], "fixed_fit_heldout_chains")
        self.assertEqual(self.histogram(conditional), [
            (Fraction(-39, 3136), 1), (Fraction(-13, 3136), 2), (Fraction(13, 3136), 1),
        ])
        self.assertEqual((conditional["planned_draws"], conditional["defined_draws"], conditional["undefined_draws"]),
                         (4, 4, 0))
        self.assertEqual(self.fraction(conditional["defined_draw_mean"]), Fraction(-13, 3136))
        self.assertEqual(joint["method"], "independent_training_refit_and_heldout_chains")
        self.assertEqual(self.histogram(joint), [
            (Fraction(-39, 3136), 2), (Fraction(-13, 3136), 4), (Fraction(), 8), (Fraction(13, 3136), 2),
        ])
        self.assertEqual((joint["planned_draws"], joint["defined_draws"], joint["undefined_draws"]), (16, 16, 0))
        self.assertEqual(self.fraction(joint["observed_gain"]), Fraction())
        self.assertEqual(self.fraction(joint["defined_draw_mean"]), Fraction(-13, 6272))
        for report in demo.values():
            self.assertIsNone(report["scientific_interval"])
            self.assertIsNone(report["scientific_decision"])
            self.assertIs(report["scientific_result"], False)

    def test_missing_knot_support_keeps_undefined_draws_in_planned_denominator(self):
        report = resampling.demo()["refit_with_undefined"]
        self.assertEqual((report["planned_draws"], report["defined_draws"], report["undefined_draws"]), (16, 8, 8))
        self.assertEqual(report["undefined_reasons"], {"candidate knot needs two distinct measured values strictly on each side": 8})
        self.assertEqual([count for _, count in self.histogram(report)], [2, 4, 2])
        self.assertEqual(report["defined_draw_mean"], report["observed_gain"])

    def test_equal_gain_clusters_keep_ordered_multiplicity(self):
        self.assertEqual(distribution([Fraction(), Fraction(), Fraction(3)], max_draws=27), {
            Fraction(): 8, Fraction(1): 12, Fraction(2): 6, Fraction(3): 1,
        })
        self.assertEqual(distribution([Fraction(2, 3)] * 2, max_draws=4), {Fraction(2, 3): 4})

    def test_draw_caps_refuse_both_paths_instead_of_reporting_a_partial_distribution(self):
        training, holdout, fitted, scored = self.paired_case()
        with self.assertRaisesRegex(ValueError, "draw count exceeds max_draws"):
            resampling.conditional(scored, expected_fit_pin=pin(fitted), expected_score_pin=pin(scored), max_draws=3)
        with self.assertRaisesRegex(ValueError, "joint chain draws exceed the cap"):
            resampling.refitted(training, holdout, fitted, expected_training_pin=pin(training),
                                expected_holdout_pin=pin(holdout), expected_fit_pin=pin(fitted),
                                expected_score_pin=pin(scored), knots=control.KNOTS, max_draws=3)

    def test_score_pin_and_even_repinned_chain_or_aggregate_mutation_are_refused(self):
        _, _, fitted, scored = self.paired_case()
        for changed_key, message in (("aggregate", "paired aggregate"), ("chain", "paired loss difference")):
            with self.subTest(changed_key=changed_key):
                changed = deepcopy(scored)
                target = changed if changed_key == "aggregate" else changed["chains"][0]
                target["gain"] = {"numerator": 0, "denominator": 1}
                with self.assertRaisesRegex(ValueError, "paired score differs from the expected fit or score pin"):
                    resampling.conditional(changed, expected_fit_pin=pin(fitted), expected_score_pin=pin(scored), max_draws=4)
                with self.assertRaisesRegex(ValueError, message):
                    resampling.conditional(changed, expected_fit_pin=pin(fitted), expected_score_pin=pin(changed), max_draws=4)

    def test_malformed_digest_refuses_even_with_matching_fit_argument(self):
        _, _, _, scored = self.paired_case()
        for field in ("fit_sha256", "holdout_sha256"):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "expected fit or score pin"):
                changed = scored | {field: "not-a-digest"}
                resampling.conditional(changed, expected_fit_pin=changed["fit_sha256"],
                                       expected_score_pin=pin(changed), max_draws=4)

    def test_joint_path_reproduces_original_fit_and_score(self):
        training, holdout, fitted, scored = self.paired_case()
        changed_fit = deepcopy(fitted)
        changed_fit["hinge"]["coefficients"][0] = {"numerator": 0, "denominator": 1}
        with self.assertRaisesRegex(ValueError, "do not reproduce the expected original fit"):
            resampling.refitted(training, holdout, changed_fit, expected_training_pin=pin(training),
                                expected_holdout_pin=pin(holdout), expected_fit_pin=pin(changed_fit),
                                expected_score_pin=pin(scored), knots=control.KNOTS, max_draws=4)
        with self.assertRaisesRegex(ValueError, "do not reproduce the expected original score"):
            resampling.refitted(training, holdout, fitted, expected_training_pin=pin(training),
                                expected_holdout_pin=pin(holdout), expected_fit_pin=pin(fitted),
                                expected_score_pin="0" * 64, knots=control.KNOTS, max_draws=4)
