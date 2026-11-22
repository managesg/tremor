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

    def test_missing_outcome_bounds_preserve_known_other_arm_and_stopped_status(self):
        result = audit.verify(**self.freeze(), missing_outcome_bounds=True)
        cluster, = result["missing_outcome_bounds"]["by_cluster"]
        self.assertEqual(cluster["mean_paired_delta_bounds"], ["-1/12", "1/4"])
        self.assertEqual(cluster["missing_pairs"], 1)
        self.assertEqual(cluster["blocks"], [
            {"block_id": "paired-clean", "delta_bounds": ["1/6", "1/6"]},
            {"block_id": "paired-disrupted", "delta_bounds": ["-1/3", "1/3"]},
        ])
        self.assertIsNone(result["clusters"][0]["blocks"][1]["paired_delta"])
        self.assertEqual(result["paired_audit"]["arm_resource_receipts"]["combined"]["unknown_usage_attempts"], 1)
        self.assertFalse(result["scientific_acceptance"])

    def test_bounds_expand_for_two_missing_arms_and_collapse_for_completed_pair(self):
        stopped = self.pair.rows[3]
        plain = self.pair.rows[2]
        plain["terminal"] = "void"
        result = audit.verify(**self.freeze(), missing_outcome_bounds=True)
        cluster, = result["missing_outcome_bounds"]["by_cluster"]
        self.assertEqual(cluster["blocks"][1]["delta_bounds"], ["-2/3", "2/3"])
        self.assertEqual(cluster["mean_paired_delta_bounds"], ["-1/4", "5/12"])

        plain["terminal"] = "completed"
        stopped["terminal"] = "completed"
        stopped["attempts"] = deepcopy(self.pair.rows[1]["attempts"])
        result = audit.verify(**self.freeze(), missing_outcome_bounds=True)
        cluster, = result["missing_outcome_bounds"]["by_cluster"]
        self.assertEqual(cluster["mean_paired_delta_bounds"], ["1/6", "1/6"])
        self.assertEqual(cluster["missing_pairs"], 0)

    def cost_witness(self, inputs, *, modify=None):
        fixture = self.pair.fixture
        scopes = {"plain": [], "combined": [], "common": ["setup", "scoring"]}
        rows, charges = [], []
        for arm_row in self.pair.rows:
            arm = arm_row["arm"]
            for attempt in arm_row["attempts"]:
                charge = f"attempt-charge-{len(charges)}"
                scopes[arm].append(charge)
                rows.append({"block_id": arm_row["block_id"], "arm": arm,
                             "sequence": attempt["sequence"], "charge_id": charge})
                charges.append({"id": charge, "scope": arm, "role": attempt["role"],
                                "usage": deepcopy(attempt["usage"]), "prior_settlement_sha256": None})
        charges += [
            {"id": "setup", "scope": "common", "role": "setup",
             "usage": self.pair.attempt(0, "cleanup", cpu=9)["usage"], "prior_settlement_sha256": "a" * 64},
            {"id": "scoring", "scope": "common", "role": "independent_scoring",
             "usage": None, "prior_settlement_sha256": None},
        ]
        roles = {"setup": "setup", "scoring": "independent_scoring"}
        if modify is not None:
            modify(rows, charges, roles)
        charge_index = fixture.artifact("cost-index.json", {
            "schema": "controller_unit_charges_v1", "receipts": charges,
        })
        placement = fixture.artifact("cost-placement.json", {
            "schema": "controller_cost_placement_v1", "charge_index_sha256": charge_index["sha256"],
            "charges_by_scope": scopes,
        })
        assignment = fixture.artifact("cost-assignment.json", {
            "schema": "public_controller_attempt_charges_v1", "trace_sha256": inputs["trace_sha256"],
            "rows": rows,
        })
        common_roles = fixture.artifact("cost-common-roles.json", {
            "schema": "controller_common_charge_roles_v1", "roles": roles,
        })
        witness = fixture.bundle / "charge-witness.json"
        pin = fixture.write(witness, {"schema": "controller_attempt_charge_witness_v1",
                                      "trace_sha256": inputs["trace_sha256"], "assignment": assignment,
                                      "placement": placement, "charge_index": charge_index,
                                      "common_roles": common_roles})
        return str(witness), pin

    def test_cost_join_retains_unknown_arm_and_common_cost_and_prior_settlement(self):
        inputs = self.freeze()
        result = audit.verify(**inputs, charge_witness=self.cost_witness(inputs))
        joined = result["observed_charge_join"]
        self.assertEqual(joined["matched_attempts"], 10)
        self.assertEqual(joined["unknown_attempt_charge_ids"], ["attempt-charge-9"])
        self.assertFalse(joined["native_metering_verified"])
        totals = joined["common_and_arm_costs"]
        self.assertIsNone(totals["placement"]["incremental_usage"])
        self.assertEqual(totals["placement"]["known_incremental_usage"]["cpu_wall_ns"], 18)
        self.assertEqual(totals["by_role"]["setup"]["known_prior_usage"]["cpu_wall_ns"], 9)
        self.assertIsNone(totals["by_role"]["independent_scoring"]["incremental_usage"])

    def test_fresh_charge_witness_rejects_equal_total_reallocation_and_common_role_swap(self):
        inputs = self.freeze()

        def transfer_cost(rows, charges, roles):
            charges[0]["usage"]["cpu_wall_ns"] += 1
            charges[1]["usage"]["cpu_wall_ns"] -= 1

        for modify, expected in (
            (transfer_cost, "exact usage differs"),
            (lambda rows, charges, roles: rows.pop(), "incomplete attempt mapping"),
            (lambda rows, charges, roles: roles.update(scoring="calibration"), "common charge role differs"),
        ):
            with self.subTest(expected=expected), self.assertRaisesRegex(ValueError, expected):
                audit.verify(**inputs, charge_witness=self.cost_witness(inputs, modify=modify))

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
