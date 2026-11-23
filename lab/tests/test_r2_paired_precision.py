from decimal import Decimal
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lab import r2_paired_precision as precision


class R2PairedPrecisionTests(unittest.TestCase):
    scorer_sha256 = "a1" * 32

    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.schedule = {"schema": "r2_paired_schedule_v1", "contrast": "control_minus_treatment",
                         "unit": "fractional_outcome", "control_arm": "control", "treatment_arm": "treatment",
                         "scorer_sha256": self.scorer_sha256,
                         "clusters": [self.cluster("minus"), self.cluster("plus")]}

    @staticmethod
    def cluster(name, reruns=3):
        return {"cluster_id": name, "family_id": f"family-{name}", "case_id": f"case-{name}",
                "reruns": [{"rerun_id": f"{name}-{index}", "seed": 11 + index,
                            "opportunity_id": f"{name}-opportunity-{index}"} for index in range(reruns)]}

    @staticmethod
    def rows(schedule, *, identical=False):
        rows = []
        for cluster in schedule["clusters"]:
            identity = {key: cluster[key] for key in ("cluster_id", "family_id", "case_id")}
            treatment = "0.60" if identical or cluster["cluster_id"] == "minus" else "0.40"
            for rerun in cluster["reruns"]:
                rows.extend(({**identity, **rerun, "arm": "control", "status": "scored", "value": "0.50"},
                             {**identity, **rerun, "arm": "treatment", "status": "scored", "value": treatment}))
        return rows

    def write(self, name, document):
        raw = (json.dumps(document, sort_keys=True, allow_nan=False) + "\n").encode()
        path = self.root / name
        path.write_bytes(raw)
        return path, hashlib.sha256(raw).hexdigest()

    def verify(self, *, schedule=None, rows=None, design_overrides=None, observation_overrides=None,
               capacity_overrides=None, with_capacity=True, pin_overrides=None):
        schedule = self.schedule if schedule is None else schedule
        schedule_path, schedule_sha256 = self.write("schedule.json", schedule)
        design = {"schema": "r2_paired_precision_design_v1", "line": "L1-B", "cohort": "public-test-cohort",
                  "schedule_sha256": schedule_sha256, "reruns_per_cluster": 3,
                  "expected_effect": "0.56", "kill_boundary": "0.28"}
        design.update({key: schedule[key] for key in ("contrast", "unit", "control_arm", "treatment_arm", "scorer_sha256")})
        design.update(design_overrides or {})
        design_path, design_sha256 = self.write("design.json", design)
        observations = {"schema": "r2_paired_observations_v1", "schedule_sha256": schedule_sha256,
                        "scorer_sha256": schedule["scorer_sha256"], "rows": self.rows(schedule) if rows is None else rows}
        observations.update(observation_overrides or {})
        observations_path, observations_sha256 = self.write("observations.json", observations)
        pins = {"design_sha256": design_sha256, "schedule_sha256": schedule_sha256, "observations_sha256": observations_sha256}
        if with_capacity:
            capacity = {"schema": "r2_precision_capacity_v1", "design_sha256": design_sha256,
                        "max_clusters": 2, "reruns_per_cluster": 3}
            capacity.update(capacity_overrides or {})
            capacity_path, capacity_sha256 = self.write("capacity.json", capacity)
            pins.update(capacity=capacity_path, capacity_sha256=capacity_sha256)
        pins.update(pin_overrides or {})
        return precision.verify(design_path, schedule_path, observations_path, **pins)

    def test_exact_variance_and_target_reach_the_capacity_boundary_at_equality(self):
        report = self.verify()
        self.assertEqual(report["status"], "precision_projection")
        self.assertEqual(report["variance_disposition"], "verified_cluster_variance")
        self.assertIs(report["authorizes_execution"], False)
        self.assertIsNone(report["scientific_decision_reachability"])
        self.assertEqual(report["paired"]["sample_variance"], {"numerator": 1, "denominator": 50})
        self.assertEqual(report["paired"]["mean_difference"], {"numerator": 0, "denominator": 1})
        planning = report["planning"]
        self.assertEqual(planning["target_se"], {"numerator": 1, "denominator": 10})
        self.assertEqual(planning["variance_per_cluster"], {"numerator": 1, "denominator": 50})
        self.assertEqual(planning["required_clusters"], 2)
        self.assertEqual(Decimal(planning["projected_se"]), Decimal("0.10"))
        self.assertIs(planning["reachable"], True)
        below = self.verify(capacity_overrides={"max_clusters": 1})["planning"]
        self.assertIs(below["reachable"], False)
        self.assertGreater(Decimal(below["projected_se"]), Decimal("0.10"))
        no_capacity = self.verify(with_capacity=False)["planning"]
        self.assertEqual(no_capacity["required_clusters"], 2)
        self.assertIsNone(no_capacity["projected_se"])
        self.assertIsNone(no_capacity["reachable"])

    def test_an_incomplete_scheduled_cluster_holds_projection_even_with_two_eligible_clusters(self):
        schedule = {**self.schedule, "clusters": [*self.schedule["clusters"], self.cluster("partial")]}
        for missing in ("missing", "censored", "unrecorded"):
            with self.subTest(missing=missing):
                rows = self.rows(schedule)
                if missing == "unrecorded":
                    rows.pop()
                else:
                    rows[-1].update(status=missing, value=None)
                report = self.verify(schedule=schedule, rows=rows)
                self.assertEqual(report["paired"]["counts"]["eligible_clusters"], 2)
                self.assertEqual(report["status"], "awaiting_pilot")
                self.assertEqual(report["variance_disposition"],
                                 "incomplete_grid" if missing == "unrecorded" else "ineligible_clusters")
                self.assertIsNone(report["planning"]["projected_se"])
                self.assertIsNone(report["planning"]["reachable"])

    def test_one_cluster_and_two_identical_cluster_means_do_not_produce_a_projection(self):
        smaller = {**self.schedule, "clusters": self.schedule["clusters"][:1]}
        cases = {
            "undersized_pilot": {"schedule": smaller},
            "degenerate_pilot": {"rows": self.rows(self.schedule, identical=True)},
        }
        for disposition, parameters in cases.items():
            with self.subTest(disposition=disposition):
                report = self.verify(**parameters)
                self.assertEqual(report["status"], "awaiting_pilot")
                self.assertEqual(report["variance_disposition"], disposition)
                self.assertIsNone(report["planning"]["projected_se"])
                self.assertIsNone(report["planning"]["required_clusters"])

    def test_historical_null_effects_keep_receipt_without_selecting_a_precision_target(self):
        historical = {**self.schedule, "clusters": [self.cluster("minus", 2)]}
        report = self.verify(schedule=historical, design_overrides={"expected_effect": None, "kill_boundary": None},
                             with_capacity=False)
        self.assertEqual(report["status"], "awaiting_design")
        self.assertEqual(report["variance_disposition"], "undersized_pilot")
        self.assertIsNone(report["planning"])
        self.assertEqual(report["paired"]["counts"]["paired_reruns"], 2)
        self.assertIs(report["authorizes_execution"], False)

    def test_crossed_design_and_schedule_scopes_are_refused_even_when_repinned(self):
        conflicts = (
            {"contrast": "treatment_minus_control"}, {"unit": "different_unit"},
            {"control_arm": "treatment", "treatment_arm": "control"}, {"scorer_sha256": "0" * 64},
            {"schedule_sha256": "0" * 64}, {"reruns_per_cluster": 4},
        )
        for change in conflicts:
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.verify(design_overrides=change)
        with self.assertRaises(ValueError):
            self.verify(observation_overrides={"schedule_sha256": "0" * 64})
        for change in ({"design_sha256": "0" * 64}, {"reruns_per_cluster": 4}):
            with self.subTest(capacity=change), self.assertRaises(ValueError):
                self.verify(capacity_overrides=change)

    def test_invalid_effect_sign_or_paired_null_definition_is_rejected(self):
        for change in ({"expected_effect": "-0.56"}, {"kill_boundary": "0"}, {"expected_effect": "0.28"},
                       {"expected_effect": None}, {"kill_boundary": None}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.verify(design_overrides=change)

    def test_all_four_supplied_artifact_pins_are_independent(self):
        for field in ("design_sha256", "schedule_sha256", "observations_sha256", "capacity_sha256"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.verify(pin_overrides={field: "0" * 64})
