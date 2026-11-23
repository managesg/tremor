from copy import deepcopy
import hashlib
import json
import unittest

from lab import l8_matched_probe_controls as probes


class L8MatchedProbeControlTests(unittest.TestCase):
    vocabulary = ("hint",)

    @staticmethod
    def training():
        return [
            {"id": "train-safe", "failure": False, "features": [-1, 0]},
            {"id": "train-failure", "failure": True, "features": [1, 0]},
        ]

    @staticmethod
    def score_row(identifier, *, text=0, activation=-1, token="normal"):
        return {"id": identifier, "text_score": text, "features": [activation, 0], "words": [token]}

    def clean(self, prefix):
        return [self.score_row(f"{prefix}-flag", text=100, activation=1, token="hint"),
                *(self.score_row(f"{prefix}-{index}") for index in range(19))]

    def failures(self):
        return [self.score_row("failure-both", text=100, activation=1, token="hint"),
                self.score_row("failure-text", text=100),
                self.score_row("failure-activation", activation=1),
                self.score_row("failure-neither")]

    def fit(self, *, seed=17):
        return probes.fit(self.training(), self.clean("threshold"), seed=seed, vocabulary=self.vocabulary)

    def evaluate(self, plan, clean=None, failures=None):
        return probes.evaluate(plan, self.clean("heldout") if clean is None else clean,
                               self.failures() if failures is None else failures,
                               plan_sha256=probes.digest(plan))

    def test_training_and_threshold_identifiers_cannot_leak_into_assessment(self):
        plan = self.fit()
        self.evaluate(plan)
        with self.assertRaises(ValueError):
            self.evaluate(plan, clean=self.clean("threshold"))
        failures = self.failures()
        failures[0]["id"] = self.training()[0]["id"]
        with self.assertRaises(ValueError):
            self.evaluate(plan, failures=failures)
        threshold = self.clean("threshold")
        threshold[0]["id"] = self.training()[0]["id"]
        with self.assertRaises(ValueError):
            probes.fit(self.training(), threshold, seed=17, vocabulary=self.vocabulary)

    def test_scoring_rows_reject_training_labels_and_wrong_dimensions(self):
        plan = self.fit()
        failures = self.failures()
        failures[0]["failure"] = True
        with self.assertRaises(ValueError):
            self.evaluate(plan, failures=failures)
        bad = self.failures()
        bad[0]["features"].append(0)
        with self.assertRaises(ValueError):
            self.evaluate(plan, failures=bad)

    def test_evaluation_refuses_an_edited_plan_at_the_original_pin(self):
        plan = self.fit()
        edited = {**deepcopy(plan), "forged": True}
        with self.assertRaises(ValueError):
            probes.evaluate(edited, self.clean("heldout"), self.failures(), plan_sha256=probes.digest(plan))

    def test_mass_mean_ranking_adds_only_the_complementary_synthetic_detection(self):
        demo = probes.demo()
        self.assertIs(demo["scientific_result"], False)
        self.assertEqual(demo["scope"], "L8_matched_probe_development")
        self.assertEqual(set(demo["cases"]), {"positive", "null"})
        for case, report in demo["cases"].items():
            self.assertEqual(set(report["arms"]), {"mass_mean", "random_direction", "word_frequency"})
            for name, arm in report["arms"].items():
                with self.subTest(case=case, arm=name):
                    additional = int(case == "positive" and name == "mass_mean")
                    self.assertIs(arm["matched_at_target"], True)
                    self.assertEqual(arm["false_positive_counts"], {"text": 1, "activation": 1, "combined": 1})
                    self.assertEqual(arm["false_positive_rates"], {
                        view: {"numerator": 1, "denominator": 20} for view in ("text", "activation", "combined")
                    })
                    self.assertEqual(arm["catch_counts"]["text"], 2)
                    self.assertEqual(arm["catch_counts"]["combined"], 2 + additional)
                    self.assertEqual(arm["paired_failure_flags"], {"both": 2, "text_only": 0,
                                                                   "combined_only": additional, "neither": 2 - additional})
                    gain = {"numerator": additional, "denominator": 4 if additional else 1}
                    self.assertEqual(arm["combined_catch_gain"], gain)

    def test_random_direction_replays_under_the_seed_and_mass_mean_uses_training_labels(self):
        plan = self.fit(seed=0)
        alternate_seed = self.fit(seed=1)
        self.assertEqual(probes.digest(plan), probes.digest(self.fit(seed=0)))
        self.assertEqual(plan["seed"], 0)
        self.assertEqual(tuple(plan["random_direction"]), (1, 1))
        self.assertNotEqual(plan["random_direction"], alternate_seed["random_direction"])
        self.assertEqual(plan["mass_mean_direction"], alternate_seed["mass_mean_direction"])
        self.assertEqual(plan["mass_mean_direction"], [
            {"numerator": 2, "denominator": 1}, {"numerator": 0, "denominator": 1}
        ])

        switched = [{**row, "failure": not row["failure"]} for row in self.training()]
        refitted = probes.fit(switched, self.clean("threshold"), seed=0, vocabulary=self.vocabulary)
        self.assertEqual(refitted["random_direction"], plan["random_direction"])
        self.assertEqual(refitted["vocabulary"], plan["vocabulary"])
        self.assertNotEqual(refitted["fit_split_sha256"]["training"], plan["fit_split_sha256"]["training"])
        self.assertEqual(refitted["fit_split_sha256"]["threshold_fit_clean"],
                         plan["fit_split_sha256"]["threshold_fit_clean"])
        self.assertEqual(refitted["mass_mean_direction"], [
            {**value, "numerator": -value["numerator"]} for value in plan["mass_mean_direction"]
        ])

    def test_heldout_shift_withholds_gain_without_refitting_operating_points(self):
        plan = self.fit(seed=0)
        pin = probes.digest(plan)
        matching = self.evaluate(plan)["arms"]["mass_mean"]
        clean = self.clean("heldout")
        clean[1]["features"][0] = 1
        shifted = self.evaluate(plan, clean=clean)["arms"]["mass_mean"]
        self.assertEqual(probes.digest(plan), pin)
        self.assertIs(matching["matched_at_target"], True)
        self.assertIs(shifted["matched_at_target"], False)
        self.assertEqual(shifted["operating_points"], matching["operating_points"])
        self.assertEqual(shifted["false_positive_counts"]["combined"], 2)
        self.assertIsNone(shifted["combined_catch_gain"])

    def test_common_assessment_inventory_and_nominal_charges_are_explicit(self):
        plan = self.fit(seed=0)
        clean, failure = self.clean("heldout"), self.failures()
        report = self.evaluate(plan, clean, failure)

        def inventory_digest(rows):
            encoded = json.dumps(sorted(rows, key=lambda row: row["id"]), sort_keys=True,
                                 separators=(",", ":"), allow_nan=False).encode()
            return hashlib.sha256(encoded).hexdigest()

        self.assertEqual(report["heldout_split_sha256"], {
            "clean": inventory_digest(clean), "failure": inventory_digest(failure)
        })
        self.assertEqual(report, self.evaluate(plan, list(reversed(clean)), list(reversed(failure))))
        charges = {"shared_training_row_charges": 2, "threshold_fit_clean": 40,
                   "heldout_clean": 40, "heldout_failure": 8, "total": 90}
        for name, result in report["arms"].items():
            with self.subTest(arm=name):
                self.assertEqual(result["call_counts"], charges)
                self.assertEqual((result["heldout_clean_task_sets"], result["heldout_failure_task_sets"]), (20, 4))
                self.assertIs(result["uses_training_labels"], name == "mass_mean")
