from copy import deepcopy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lab import r2_paired_receipt as paired


class R2PairedReceiptTests(unittest.TestCase):
    scorer_sha256 = "a1" * 32

    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.schedule_path = self.root / "schedule.json"
        self.observations_path = self.root / "observations.json"
        self.schedule = {"schema": "r2_paired_schedule_v1", "contrast": "control_minus_treatment",
                         "unit": "fractional_outcome", "control_arm": "control", "treatment_arm": "treatment",
                         "scorer_sha256": self.scorer_sha256,
                         "clusters": [self.cluster("zero", 3), self.cluster("one", 6), self.cluster("partial", 6)]}
        self.rows = self.rows_for(self.schedule)

    @staticmethod
    def cluster(name, reruns):
        return {"cluster_id": name, "family_id": f"family-{name}", "case_id": f"case-{name}",
                "reruns": [{"rerun_id": f"{name}-{index}", "seed": 100 + index,
                            "opportunity_id": f"opportunity-{name}-{index}"} for index in range(reruns)]}

    @staticmethod
    def write(path, document):
        raw = (json.dumps(document, sort_keys=True, allow_nan=False) + "\n").encode()
        path.write_bytes(raw)
        return hashlib.sha256(raw).hexdigest()

    @staticmethod
    def observation(cluster, rerun, arm, status, value):
        identity = {key: cluster[key] for key in ("cluster_id", "family_id", "case_id")}
        return {**identity, **rerun, "arm": arm, "status": status, "value": value}

    def rows_for(self, schedule):
        rows = []
        for cluster in schedule["clusters"]:
            for ordinal, rerun in enumerate(cluster["reruns"]):
                name = cluster["cluster_id"]
                control, treatment = ("0.5", "0.5") if name == "zero" else ("1", "0")
                rows.append(self.observation(cluster, rerun, "control", "scored", control))
                if name == "partial" and ordinal >= 3:
                    if ordinal < 5:
                        status = "censored" if ordinal == 3 else "missing"
                        rows.append(self.observation(cluster, rerun, "treatment", status, None))
                else:
                    rows.append(self.observation(cluster, rerun, "treatment", "scored", treatment))
        return rows

    def verify(self, *, schedule=None, rows=None, observations_fields=None,
               supplied_schedule_sha256=None, supplied_observations_sha256=None):
        schedule = self.schedule if schedule is None else schedule
        schedule_sha256 = self.write(self.schedule_path, schedule)
        observations = {"schema": "r2_paired_observations_v1", "schedule_sha256": schedule_sha256,
                        "scorer_sha256": self.scorer_sha256, "rows": self.rows if rows is None else rows}
        if observations_fields is not None:
            observations.update(observations_fields)
        observations_sha256 = self.write(self.observations_path, observations)
        return paired.verify(self.schedule_path, self.observations_path,
                             schedule_sha256=schedule_sha256 if supplied_schedule_sha256 is None else supplied_schedule_sha256,
                             observations_sha256=(observations_sha256 if supplied_observations_sha256 is None
                                                  else supplied_observations_sha256))

    def test_cluster_means_have_equal_weight_and_incomplete_cluster_does_not_contribute(self):
        report = self.verify()
        self.assertEqual(report["status"], "verified_paired_grid")
        self.assertIs(report["grid_complete"], False)
        self.assertIs(report["scientific_result"], False)
        self.assertIsNone(report["observed_native_variance"])
        one_half = {"numerator": 1, "denominator": 2}
        self.assertEqual(report["mean_difference"], one_half)
        self.assertEqual(report["sample_variance"], one_half)
        counts = {"scheduled_arms": 30, "scored_arms": 27, "censored_arms": 1, "missing_arms": 1,
                  "unrecorded_arms": 1, "scheduled_reruns": 15, "paired_reruns": 12,
                  "eligible_clusters": 2, "excluded_clusters": 1}
        self.assertEqual({key: report["counts"][key] for key in counts}, counts)
        contributions = report["cluster_contributions"]
        self.assertEqual([(row["cluster_id"], row["status"], row["paired_reruns"], row["mean_difference"])
                          for row in contributions], [
            ("zero", "eligible", 3, {"numerator": 0, "denominator": 1}),
            ("one", "eligible", 6, {"numerator": 1, "denominator": 1}),
            ("partial", "incomplete", 3, None),
        ])
        reverse = self.verify(rows=list(reversed(self.rows)))
        self.assertEqual(reverse["cluster_contributions"], contributions)

    def test_explicit_censored_missing_and_unrecorded_mates_remain_distinct(self):
        partial = self.verify()["cluster_contributions"][-1]
        self.assertEqual([(rerun["control_status"], rerun["treatment_status"], rerun["difference"])
                          for rerun in partial["reruns"][-3:]],
                         [("scored", "censored", None), ("scored", "missing", None), ("scored", "unrecorded", None)])
        cluster = self.schedule["clusters"][-1]
        absent = self.observation(cluster, cluster["reruns"][-1], "treatment", "missing", None)
        complete_inventory = self.verify(rows=[*self.rows, absent])
        self.assertIs(complete_inventory["grid_complete"], True)
        self.assertEqual(complete_inventory["cluster_contributions"][-1]["status"], "incomplete")

    def test_one_eligible_cluster_has_no_sample_variance_and_two_reruns_are_insufficient(self):
        schedule = {**self.schedule, "clusters": [self.cluster("zero", 3), self.cluster("short", 2)]}
        report = self.verify(schedule=schedule, rows=self.rows_for(schedule))
        self.assertEqual(report["mean_difference"], {"numerator": 0, "denominator": 1})
        self.assertIsNone(report["sample_variance"])
        self.assertEqual([row["status"] for row in report["cluster_contributions"]], ["eligible", "insufficient_reruns"])

    def test_null_historical_seed_or_scorer_preserves_scores_but_withholds_eligibility(self):
        for status in ("unverified_rerun_seed", "unverified_scorer"):
            with self.subTest(status=status):
                schedule = {**self.schedule, "clusters": [self.cluster("one", 3)]}
                observations_fields = {}
                if status == "unverified_rerun_seed":
                    schedule["clusters"][0]["reruns"][0]["seed"] = None
                else:
                    schedule["scorer_sha256"] = None
                    observations_fields["scorer_sha256"] = None
                report = self.verify(schedule=schedule, rows=self.rows_for(schedule),
                                     observations_fields=observations_fields)
                self.assertIs(report["grid_complete"], True)
                self.assertEqual(report["counts"]["scored_arms"], 6)
                self.assertEqual(report["counts"]["eligible_clusters"], 0)
                self.assertEqual(report["cluster_contributions"][0]["status"], status)
                self.assertIsNone(report["mean_difference"])
                self.assertIsNone(report["sample_variance"])

    def test_repinning_does_not_allow_crossed_pair_identity(self):
        for field, value in (("family_id", "family-one"), ("case_id", "case-one"), ("seed", 999),
                             ("opportunity_id", "another-opportunity"), ("arm", "another-arm")):
            with self.subTest(field=field):
                rows = deepcopy(self.rows)
                rows[1][field] = value
                with self.assertRaises(ValueError):
                    self.verify(rows=rows)

    def test_repinning_does_not_allow_duplicate_observations_or_mismatched_scorer(self):
        with self.assertRaisesRegex(ValueError, "duplicate paired arm observation"):
            self.verify(rows=[*self.rows, self.rows[0]])
        for key in ("scorer_sha256", "schedule_sha256"):
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "does not bind schedule and scorer"):
                self.verify(observations_fields={key: "0" * 64})

    def test_repinning_does_not_recover_a_malformed_score_or_unscored_value(self):
        for status, value in (("scored", 0.5), ("scored", None), ("missing", "0"), ("censored", "0")):
            with self.subTest(status=status, value=value):
                rows = deepcopy(self.rows)
                rows[0].update(status=status, value=value)
                with self.assertRaises(ValueError):
                    self.verify(rows=rows)

    def test_external_schedule_and_observation_pins_are_required_independently(self):
        for key in ("supplied_schedule_sha256", "supplied_observations_sha256"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.verify(**{key: "0" * 64})
