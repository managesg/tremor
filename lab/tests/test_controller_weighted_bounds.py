"""Frozen weight profiles keep all scheduled clusters in missing-outcome bounds."""

import json
import subprocess
import sys
import unittest

from lab import controller_cluster_audit as audit
from lab import controller_holdout as holdout
from lab.tests import test_controller_cluster_audit as clustered
from tremor.trapbench import alloc


class ControllerWeightedBoundsTests(unittest.TestCase):
    def setUp(self):
        self.cluster = clustered.ControllerClusterAuditTests()
        self.addCleanup(self.cluster.doCleanups)
        self.cluster.setUp()
        self.inputs = self.cluster.freeze()
        self.fixture = self.cluster.pair.fixture
        self.path = self.fixture.root / "cohort-weights.json"
        self.weights = {
            "schema": "controller_cohort_weights_v1",
            "manifest_sha256": self.inputs["manifest_sha256"],
            "exposure_witness_sha256": self.inputs["witness_sha256"],
            "task_inventory_sha256": self.fixture.manifest["inputs"]["task_manifest_sha256"],
            "cluster_weights": {"public-shared-cluster": [1, 1]},
        }

    def witness(self, **updates):
        return self.path, self.fixture.write(self.path, self.weights | updates)

    def test_weighted_cli_keeps_stopped_pair_and_original_denominator(self):
        command = [
            sys.executable, "-B", "-m", "lab.controller_cluster_audit",
            *[str(self.inputs[key]) for key in (
                "bundle", "manifest", "evidence_index", "trace", "task_inventory", "exposure_witness")],
            *[piece for field in ("manifest", "evidence_index", "trace", "witness")
              for piece in (f"--{field.replace('_', '-')}-sha256", self.inputs[f"{field}_sha256"])],
            "--release-witness", *map(str, self.inputs["release_witness"]),
            "--cohort-weight-witness", *map(str, self.witness()),
        ]
        proc = subprocess.run(command, capture_output=True, text=True, timeout=10, check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        outcome = json.loads(proc.stdout)["weighted_outcome_bounds"]["declared_cluster_weights"]
        self.assertEqual(outcome["mean_paired_delta_bounds"], ["-1/12", "1/4"])
        self.assertEqual(outcome["observed_weight_mass"], "1/2")
        self.assertIsNone(outcome["mean_paired_delta"])

    def test_mismatched_profile_identity_or_weights_are_refused(self):
        for edit, error in (
            ({"exposure_witness_sha256": "0" * 64}, "must bind"),
            ({"task_inventory_sha256": "0" * 64}, "must bind"),
            ({"cluster_weights": {}}, "cluster roster"),
            ({"cluster_weights": {"public-shared-cluster": [1, 2]}}, "sum exactly to one"),
            ({"cluster_weights": {"public-shared-cluster": [True, 1]}}, "positive integer fraction"),
            ({"cluster_weights": {"public-shared-cluster": [0, 1]}}, "positive integer fraction"),
        ):
            with self.subTest(edit=edit), self.assertRaisesRegex(ValueError, error):
                audit.verify(**self.inputs, cohort_weight_witness=self.witness(**edit))

    def test_complete_coverage_collapses_to_the_observed_point(self):
        self.cluster.pair.rows[3]["terminal"] = "completed"
        self.cluster.pair.rows[3]["attempts"] = self.cluster.pair.rows[1]["attempts"]
        result = audit.verify(**self.cluster.freeze(), cohort_weight_witness=self.witness())
        exact = result["weighted_outcome_bounds"]["declared_cluster_weights"]
        self.assertEqual(exact["mean_paired_delta_bounds"], ["1/6", "1/6"])
        self.assertEqual(exact["mean_paired_delta"], "1/6")
        self.assertEqual(exact["observed_weight_mass"], "1")

    def separate_cluster(self):
        pair = self.cluster.pair
        taskset = alloc.gen(26, split="heldout")
        pair.block = {"block_id": "separate", "condition": "clean", "seed": 26,
                      "order": ["plain", "combined"], "taskset": taskset}
        work = [{key: value for key, value in row.items() if key != "action"}
                for row in alloc.oracle_log(taskset)]
        pair.rows[:0] = [pair.arm("plain", work[:2]), pair.arm("combined", work[:1])]
        reference = self.fixture.artifact("tasks.json", {"blocks": [pair.block] + self.cluster.blocks})
        pair.inputs["task_manifest_sha256"] = reference
        self.fixture.manifest["inputs"]["task_manifest_sha256"] = reference["sha256"]
        for row in pair.rows:
            row["inputs"] = self.fixture.manifest["inputs"].copy()
        inputs = pair.freeze([[] for _ in pair.rows])
        exposure_path = self.inputs["exposure_witness"]
        exposure = json.loads(exposure_path.read_bytes())
        exposure["holdout"].insert(0, {
            "block_id": "separate", "family": "toy-tasks", "lineage": "other-public-lineage",
            "seed_group": "other-public-seed", "cluster_id": "other-public-cluster",
            "taskset_sha256": holdout._canonical(taskset), "prompt_sha256": holdout._task_prompts(taskset),
        })
        exposure.update(manifest_sha256=inputs["manifest_sha256"], task_inventory_sha256=reference["sha256"])
        exposure_pin = self.fixture.write(exposure_path, exposure)
        self.weights.update(manifest_sha256=inputs["manifest_sha256"], exposure_witness_sha256=exposure_pin,
                            task_inventory_sha256=reference["sha256"])
        return inputs | {"task_inventory": self.inputs["task_inventory"],
                         "exposure_witness": exposure_path, "witness_sha256": exposure_pin}

    def test_matching_three_block_archive_distinguishes_weighting_choices(self):
        inputs = self.separate_cluster()
        witness = self.witness(cluster_weights={"public-shared-cluster": [1, 4], "other-public-cluster": [3, 4]})
        report = audit.verify(**inputs, cohort_weight_witness=witness, missing_outcome_bounds=True)
        weight_report = report["weighted_outcome_bounds"]
        self.assertEqual(report["exposure"]["heldout_clusters"], 2)
        self.assertEqual(weight_report["equal_cluster_sensitivity"]["mean_paired_delta_bounds"], ["-1/8", "1/24"])
        self.assertEqual(weight_report["equal_scheduled_block_sensitivity"]["mean_paired_delta_bounds"], ["-1/9", "1/9"])
        exact = weight_report["declared_cluster_weights"]
        self.assertEqual(exact["mean_paired_delta_bounds"], ["-7/48", "-1/16"])
        self.assertEqual(exact["observed_weight_mass"], "7/8")
        self.assertEqual(exact["missing_weight_mass"], "1/8")
        self.assertEqual(exact["observed_weighted_contribution"], "-5/48")
        self.assertIsNone(exact["mean_paired_delta"])
        self.assertFalse(report["scientific_acceptance"])

    def test_all_missing_weight_is_retained_under_declared_profile(self):
        for row in self.cluster.pair.rows:
            row["terminal"] = "void"
        result = audit.verify(**self.cluster.freeze(), cohort_weight_witness=self.witness())
        weights = result["weighted_outcome_bounds"]["declared_cluster_weights"]
        self.assertEqual(weights["observed_weight_mass"], "0")
        self.assertEqual(weights["missing_weight_mass"], "1")
        self.assertIsNone(weights["observed_weighted_contribution"])
        self.assertEqual(weights["mean_paired_delta_bounds"], ["-2/3", "2/3"])
        self.assertIsNone(weights["mean_paired_delta"])
