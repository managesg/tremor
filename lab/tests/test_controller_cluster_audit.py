from copy import deepcopy
import json
import subprocess
import sys
import unittest

from lab import controller_cluster_audit as audit
from lab import controller_holdout as holdout
from lab.tests import test_controller_pair_audit as pair_fixtures
from murmuration.trapbench import alloc


class ControllerClusterAuditTests(unittest.TestCase):
    def setUp(self):
        self.pair = pair = pair_fixtures.ControllerPairAuditTests()
        self.addCleanup(pair.doCleanups)
        pair.setUp()
        pair.block["taskset"] = alloc.gen(25, split="heldout")
        proposals = [
            {key: value for key, value in job.items() if key != "action"}
            for job in alloc.oracle_log(pair.block["taskset"])
        ]
        pair.rows = [
            pair.arm("plain", [*proposals[:2], proposals[2] | {"task": proposals[0]["task"]}]),
            pair.arm("combined", proposals[:3]),
        ]
        self.blocks = [pair.block, deepcopy(pair.block)]
        self.blocks[1].update(block_id="paired-disrupted", condition="disrupted")
        pair.rows.extend(deepcopy(pair.rows))
        for row in pair.rows[2:]:
            row.update(block_id="paired-disrupted", condition="disrupted")
        pair.rows[3]["terminal"] = "stopped"
        pair.rows[3]["attempts"] = [pair.attempt(0, "verification") | {"usage": None}]
        self.prior = {
            role: {"source_sha256": "8" * 64, "members": [{
                "family": "prior-family", "lineage": "prior-lineage", "seed_group": "prior-group",
                "prompt_sha256": holdout._task_prompts(alloc.gen(11)),
            }]} for role in holdout.PRIOR_ROLES
        }

    def freeze(self):
        pair = self.pair
        fixture = pair.fixture
        reference = fixture.artifact("tasks.json", {"blocks": self.blocks})
        pair.inputs["task_manifest_sha256"] = reference
        fixture.manifest["inputs"]["task_manifest_sha256"] = reference["sha256"]
        for row in pair.rows:
            row["inputs"] = fixture.manifest["inputs"].copy()
        inputs = pair.freeze([[], [], [], []])
        witness = fixture.root / "exposure.json"
        witness_digest = fixture.write(witness, {
            "schema": holdout.SCHEMA,
            "manifest_sha256": inputs["manifest_sha256"],
            "task_inventory_sha256": reference["sha256"],
            "prior": self.prior,
            "holdout": [{
                "block_id": block["block_id"],
                "family": "toy-tasks",
                "lineage": "public-heldout",
                "seed_group": "public-shared-seed",
                "cluster_id": "public-shared-cluster",
                "taskset_sha256": holdout._canonical(block["taskset"]),
                "prompt_sha256": holdout._task_prompts(block["taskset"]),
            } for block in self.blocks],
        })
        return inputs | {"task_inventory": fixture.bundle / "tasks.json", "exposure_witness": witness,
                         "witness_sha256": witness_digest}

    def test_cli_keeps_stopped_pair_in_same_cluster_and_exposes_unknown_cost(self):
        inputs = self.freeze()
        command = [
            sys.executable, "-m", "lab.controller_cluster_audit",
            *(str(inputs[key]) for key in (
                "bundle", "manifest", "evidence_index", "trace", "task_inventory", "exposure_witness"
            )),
            *(piece for field in ("manifest", "evidence_index", "trace", "witness")
              for piece in (f"--{field.replace('_', '-')}-sha256", inputs[f"{field}_sha256"])),
            "--release-witness", *(str(value) for value in inputs["release_witness"]),
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["exposure"]["heldout_blocks"], 2)
        self.assertEqual(report["exposure"]["heldout_clusters"], 1)
        self.assertEqual(report["fully_observed_pair_clusters"], 0)
        self.assertEqual(report["clusters"], [{
            "cluster_id": "public-shared-cluster",
            "blocks": [
                {"block_id": "paired-clean", "paired_delta": "1/6"},
                {"block_id": "paired-disrupted", "paired_delta": None},
            ],
            "complete_pairs": 1,
        }])
        audit_report = report["paired_audit"]
        self.assertEqual(audit_report["arm_resource_receipts"]["combined"]["unknown_usage_attempts"], 1)
        self.assertFalse(report["scientific_acceptance"])

    def test_both_completed_pairs_count_as_one_fully_observed_cluster(self):
        stopped = self.pair.rows[3]
        stopped["terminal"] = "completed"
        stopped["attempts"] = deepcopy(self.pair.rows[1]["attempts"])
        report = audit.verify(**self.freeze())
        self.assertEqual(report["fully_observed_pair_clusters"], 1)
        self.assertEqual(report["clusters"][0]["complete_pairs"], 2)

    def test_policy_witness_preserves_an_all_disabled_cluster_as_diagnostic(self):
        common, references = self.pair.policy_files(combined={}, plain={})
        inputs = self.freeze()
        witness = self.pair.policy_pin(inputs["manifest_sha256"], common, references)
        result = audit.verify(**inputs, policy_witness=witness)
        self.assertEqual([block["paired_delta"] for block in result["clusters"][0]["blocks"]], ["1/6", None])
        configuration = result["paired_audit"]["policy_configuration"]
        self.assertEqual(configuration["declared_design"], "all_disabled_diagnostic")
        self.assertFalse(configuration["runtime_policy_application_verified"])

    def test_requires_release_witness_even_through_library_entry(self):
        with self.assertRaisesRegex(ValueError, "requires a V2 release witness"):
            audit.verify(**(self.freeze() | {"release_witness": None}))

    def test_rejects_exposure_from_another_pinned_freeze(self):
        inputs = self.freeze()
        witness = inputs["exposure_witness"]
        content = json.loads(witness.read_bytes()) | {"manifest_sha256": "a" * 64}
        inputs["witness_sha256"] = self.pair.fixture.write(witness, content)
        with self.assertRaisesRegex(ValueError, "different freeze"):
            audit.verify(**inputs)
