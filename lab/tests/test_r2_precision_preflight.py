from copy import deepcopy
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lab import r2_precision_preflight as preflight


class R2PrecisionPreflightTests(unittest.TestCase):
    def setUp(self):
        self.bundle = Path(self.enterContext(TemporaryDirectory())).resolve()
        self.manifest = self.bundle / "manifest.json"
        self.design = {"schema": "r2_precision_design_v1", "line": "L1-B", "unit": "relative_reduction_fraction",
                       "expected_effect": "0.25", "kill_boundary": "0.10"}
        design = self.json_artifact("design.json", self.design)
        self.pilot = {"schema": "r2_precision_variance_v1", "design_sha256": design["sha256"],
                      "method": "cluster_mean", "sd": "0.10", "icc": None, "reruns_per_cluster": 3,
                      "clusters": [{"id": "public-a", "status": "eligible", "reruns": 3},
                                   {"id": "public-b", "status": "eligible", "reruns": 3},
                                   {"id": "public-c", "status": "censored", "reruns": 2}]}
        self.capacity = {"schema": "r2_precision_capacity_v1", "design_sha256": design["sha256"],
                         "reruns_per_cluster": 3, "max_clusters": 7}
        self.inventory = {"schema": "r2_precision_preflight_v1", "design": design,
                          "proposal": self.artifact("proposal.md", b"Public precision fixture evidence\n"),
                          "pilot": self.json_artifact("pilot.json", self.pilot),
                          "capacity": self.json_artifact("capacity.json", self.capacity)}
        self.manifest_sha256 = self.pin_manifest(self.inventory)

    @staticmethod
    def sha(raw):
        return hashlib.sha256(raw).hexdigest()

    def artifact(self, name, raw):
        (self.bundle / name).write_bytes(raw)
        return {"path": name, "sha256": self.sha(raw)}

    def json_artifact(self, name, document):
        return self.artifact(name, (json.dumps(document, sort_keys=True, allow_nan=False) + "\n").encode())

    def pin_manifest(self, inventory):
        return self.json_artifact(self.manifest.name, inventory)["sha256"]

    def verify(self, *, manifest_sha256=None):
        return preflight.verify(self.bundle, self.manifest,
                                manifest_sha256=self.manifest_sha256 if manifest_sha256 is None else manifest_sha256)

    def verify_variant(self, **changes):
        inventory = dict(self.inventory)
        for key, document in changes.items():
            inventory[key] = self.json_artifact(f"alternate-{key}.json", document) if document is not None else None
        return self.verify(manifest_sha256=self.pin_manifest(inventory))

    def test_exact_target_for_25_percent_effect_and_10_percent_kill_boundary(self):
        report = self.verify()
        self.assertEqual(report["design_sha256"], self.inventory["design"]["sha256"])
        self.assertIs(report["authorizes_execution"], False)
        self.assertIs(report["scientific_result"], False)
        self.assertIsNone(report["observed_standard_error"])
        self.assertEqual(report["pilot_coverage"], {"eligible_clusters": 2, "censored_clusters": 1})
        planning = report["planning"]
        self.assertEqual(planning["status"], "calculated")
        self.assertEqual(planning["target_se"], {"numerator": 1, "denominator": 28})
        self.assertEqual(planning["variance_per_cluster"], {"numerator": 1, "denominator": 100})
        self.assertEqual(planning["required_clusters"], 8)
        self.assertIs(planning["reachable"], False)
        self.assertGreater(Decimal(planning["projected_se"]) * 28, 1)

        expanded = self.verify_variant(capacity={**self.capacity, "max_clusters": 8})["planning"]
        self.assertIs(expanded["reachable"], True)
        self.assertLess(Decimal(expanded["projected_se"]) * 28, 1)

    def test_balanced_icc_uses_design_effect_and_does_not_count_censored_clusters(self):
        pilot = {**deepcopy(self.pilot), "method": "balanced_icc", "sd": "0.20", "icc": "0.25",
                 "reruns_per_cluster": 4}
        for cluster in pilot["clusters"]:
            if cluster["status"] == "eligible":
                cluster["reruns"] = 4
        capacity = {**self.capacity, "reruns_per_cluster": 4, "max_clusters": 14}
        report = self.verify_variant(pilot=pilot, capacity=capacity)
        self.assertEqual(report["pilot_coverage"], {"eligible_clusters": 2, "censored_clusters": 1})
        planning = report["planning"]
        self.assertEqual(planning["variance_per_cluster"], {"numerator": 7, "denominator": 400})
        self.assertEqual(planning["required_clusters"], 14)
        self.assertIs(planning["reachable"], True)

    def test_missing_pilot_or_capacity_cannot_claim_reachability(self):
        for missing, expected in (("pilot", "missing_pilot"), ("capacity", "missing_capacity")):
            with self.subTest(missing=missing):
                report = self.verify_variant(**{missing: None})
                self.assertEqual(report["planning"]["status"], expected)
                self.assertIsNone(report["planning"]["reachable"])
                self.assertIsNone(report["planning"]["projected_se"])
                self.assertIs(report["authorizes_execution"], False)
                self.assertEqual(report["planning"]["required_clusters"], None if missing == "pilot" else 8)

    def test_degenerate_pilot_and_explicit_zero_capacity_are_distinct(self):
        degenerate = self.verify_variant(pilot={**self.pilot, "sd": "0"})["planning"]
        self.assertEqual(degenerate["status"], "degenerate_pilot")
        for field in ("variance_per_cluster", "required_clusters", "projected_se", "reachable"):
            self.assertIsNone(degenerate[field])

        zero_capacity = self.verify_variant(capacity={**self.capacity, "max_clusters": 0})["planning"]
        self.assertEqual(zero_capacity["status"], "calculated")
        self.assertEqual(zero_capacity["required_clusters"], 8)
        self.assertIsNone(zero_capacity["projected_se"])
        self.assertIs(zero_capacity["reachable"], False)

    def test_fresh_outer_pin_cannot_cross_design_scope_or_rerun_envelope(self):
        variants = (
            {"pilot": {**self.pilot, "design_sha256": "0" * 64}},
            {"capacity": {**self.capacity, "design_sha256": "0" * 64}},
            {"design": {**self.design, "line": "L8-B"}},
            {"capacity": {**self.capacity, "reruns_per_cluster": 4}},
        )
        for index, variant in enumerate(variants):
            with self.subTest(variant=index), self.assertRaises(ValueError):
                self.verify_variant(**variant)

    def test_eligible_rerun_floor_minimum_clusters_and_unique_ids_are_required(self):
        for case in ("duplicate", "short reruns", "too few eligible"):
            with self.subTest(case=case):
                pilot = deepcopy(self.pilot)
                clusters = pilot["clusters"]
                if case == "duplicate":
                    clusters[1]["id"] = clusters[0]["id"]
                elif case == "short reruns":
                    clusters[1]["reruns"] = 2
                else:
                    clusters[1]["status"] = "censored"
                with self.assertRaises(ValueError):
                    self.verify_variant(pilot=pilot)

    def test_wrong_external_pin_or_changed_artifact_is_refused(self):
        with self.assertRaises(ValueError):
            self.verify(manifest_sha256="0" * 64)
        path = self.bundle / self.inventory["proposal"]["path"]
        path.write_bytes(b"Changed public fixture evidence\n")
        with self.assertRaises(ValueError):
            self.verify()
