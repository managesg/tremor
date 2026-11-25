from copy import deepcopy
import unittest

from lab import l4a_segmented_control as control
from lab.l4_measured_compression import pin


class L4ASegmentedControlTests(unittest.TestCase):
    @staticmethod
    def ratio(numerator, denominator=1):
        return {"numerator": numerator, "denominator": denominator}

    @staticmethod
    def fit(training):
        return control.fit_training(training, expected_training_pin=pin(training), knots=control.KNOTS)

    @staticmethod
    def score(holdout, fitted):
        return control.score_holdout(holdout, fitted, expected_holdout_pin=pin(holdout), expected_fit_pin=pin(fitted))

    def test_exact_kink_and_inverted_control_have_same_gain_with_opposite_slopes(self):
        demo = control.demo()
        for shape, left, right in (("kink", -5, 5), ("inverted", 5, -5)):
            with self.subTest(shape=shape):
                fitted = demo[shape]["fit"]
                self.assertEqual(fitted["line"]["rss"], self.ratio(13, 448))
                self.assertEqual(fitted["hinge"]["rss"], self.ratio(0))
                self.assertEqual(fitted["hinge"]["knot"], self.ratio(2, 5))
                self.assertEqual(fitted["candidate_rss"], [
                    {"knot": self.ratio(3, 10), "rss": self.ratio(3, 448)},
                    {"knot": self.ratio(2, 5), "rss": self.ratio(0)},
                    {"knot": self.ratio(1, 2), "rss": self.ratio(3, 448)},
                ])
                self.assertEqual(fitted["slopes"], {"left": self.ratio(left, 8), "right": self.ratio(right, 8)})
                report = demo[shape]["holdout"]
                self.assertIs(report["scientific_result"], False)
                for result in [report, *report["chains"]]:
                    self.assertEqual(result["straight_mse"], self.ratio(257, 50176))
                    self.assertEqual(result["hinge_mse"], self.ratio(1, 1024))
                    self.assertEqual(result["gain"], self.ratio(13, 3136))
        self.assertEqual(demo["kink"]["fit"]["hinge"]["coefficients"],
                         [self.ratio(3, 8), self.ratio(-5, 8), self.ratio(5, 4)])

    def test_linear_control_has_zero_gain_and_explicit_tied_candidates(self):
        training, holdout = control.fixture("linear")
        fitted = self.fit(training)
        self.assertEqual(fitted["tied_knots"], [self.ratio(3, 10), self.ratio(2, 5), self.ratio(1, 2)])
        self.assertEqual(fitted["hinge"]["knot"], self.ratio(3, 10))
        self.assertEqual(fitted["hinge"]["coefficients"], [self.ratio(3, 32), self.ratio(5, 16), self.ratio(0)])
        report = self.score(holdout, fitted)
        self.assertEqual(report["straight_mse"], self.ratio(1, 1024))
        self.assertEqual(report["hinge_mse"], self.ratio(1, 1024))
        self.assertEqual(report["gain"], self.ratio(0))

    def test_frozen_kink_fit_loses_to_the_line_on_inverted_holdout(self):
        training, _ = control.fixture("kink")
        _, inverted_holdout = control.fixture("inverted")
        fitted = self.fit(training)
        report = self.score(inverted_holdout, fitted)
        self.assertEqual(report["fit_sha256"], pin(fitted))
        self.assertEqual(report["gain"], self.ratio(-39, 3136))

    def test_heldout_outcome_changes_cannot_change_training_fit_or_weight_other_chain(self):
        training, holdout = control.fixture("kink")
        fitted = self.fit(training)
        original = self.score(holdout, fitted)
        holdout[0]["levels"][0]["false_notes"] += 1
        changed = self.score(holdout, fitted)
        self.assertEqual(fitted, self.fit(training))
        self.assertEqual(changed["fit_sha256"], original["fit_sha256"])
        self.assertNotEqual(changed["holdout_sha256"], original["holdout_sha256"])
        self.assertEqual(changed["chains"][1], original["chains"][1])
        self.assertEqual(changed["chains"][0]["hinge_mse"], self.ratio(5, 3584))
        self.assertEqual(changed["hinge_mse"], self.ratio(17, 14336))

    def test_changed_training_fit_and_holdout_require_their_original_pins(self):
        training, holdout = control.fixture("kink")
        fitted = self.fit(training)
        original_training_pin = pin(training)
        training[0]["levels"][0]["false_notes"] += 1
        with self.assertRaisesRegex(ValueError, "chain inventory differs from its expected pin"):
            control.fit_training(training, expected_training_pin=original_training_pin, knots=control.KNOTS)

        changed_fit = deepcopy(fitted)
        changed_fit["hinge"]["coefficients"][0] = self.ratio(1)
        with self.assertRaisesRegex(ValueError, "fitted model differs from the expected pin"):
            control.score_holdout(holdout, changed_fit, expected_holdout_pin=pin(holdout), expected_fit_pin=pin(fitted))

        original_holdout_pin = pin(holdout)
        holdout[0]["levels"][0]["false_notes"] += 1
        with self.assertRaisesRegex(ValueError, "chain inventory differs from its expected pin"):
            control.score_holdout(holdout, fitted, expected_holdout_pin=original_holdout_pin, expected_fit_pin=pin(fitted))

    def test_crossed_chain_family_or_snapshot_rejected_after_repinning_holdout(self):
        training, holdout = control.fixture("kink")
        fitted = self.fit(training)
        for key in ("id", "family", "snapshot"):
            with self.subTest(key=key):
                crossed = deepcopy(holdout)
                if key == "snapshot":
                    original_level = training[0]["levels"][0]
                    crossed[0]["levels"][0].update(snapshot=original_level["snapshot"],
                                                   snapshot_pin=original_level["snapshot_pin"])
                else:
                    crossed[0][key] = training[0][key]
                with self.assertRaisesRegex(ValueError, "held-out scope crosses training"):
                    self.score(crossed, fitted)

    def test_decomposed_family_id_and_cross_split_raw_source_alias_are_refused(self):
        training, holdout = control.fixture("kink")
        aliased = deepcopy(training)
        aliased[0]["family"] = "cafe\u0301"
        with self.assertRaisesRegex(ValueError, "invalid or repeated chain/family"):
            self.fit(aliased)

        for chain, episode_id in ((training[0], "train-raw"), (holdout[0], "holdout-raw")):
            level = chain["levels"][0]
            episode = {"id": episode_id, "source": "shared", "version": 1, "day": 0, "text": "same source"}
            level["snapshot"]["raw_before"] = [episode]
            level["snapshot_pin"] = pin(level["snapshot"])
        with self.assertRaisesRegex(ValueError, "held-out scope crosses training"):
            self.score(holdout, self.fit(training))

    def test_measured_level_duplicates_and_incomplete_endpoints_are_refused(self):
        training, _ = control.fixture("kink")
        repeated = deepcopy(training)
        first = repeated[0]["levels"][0]
        for note in first["snapshot"]["loaded_after"]:
            note["text"] = "aa"
        first["snapshot_pin"] = pin(first["snapshot"])
        with self.assertRaisesRegex(ValueError, "seven distinct measured levels"):
            self.fit(repeated)

        missing_level = deepcopy(training)
        missing_level[0]["levels"].pop()
        with self.assertRaisesRegex(ValueError, "seven distinct measured levels"):
            self.fit(missing_level)

        for key, value in (("cutoff", 5), ("loaded_after", [])):
            with self.subTest(key=key):
                incomplete = deepcopy(training)
                first = incomplete[0]["levels"][0]
                first["snapshot"][key] = value
                first["snapshot_pin"] = pin(first["snapshot"])
                with self.assertRaisesRegex(ValueError, "complete six-night payload and false-share inventories"):
                    self.fit(incomplete)
