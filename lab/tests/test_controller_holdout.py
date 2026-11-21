import copy
import json
import unittest

from lab import controller_holdout as holdout
from lab.tests import test_controller_selection as fixtures
from murmuration.trapbench import alloc


class ControllerHoldoutTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ControllerSelectionTests()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.setUp()
        self.blocks = [
            {"block_id": condition, "condition": condition, "seed": 25, "order": ["plain", "combined"],
             "taskset": alloc.gen(25, split="heldout")}
            for condition in ("clean", "disrupted")
        ]
        self.rows = [{
            "block_id": block["block_id"], "family": "toy-tasks", "lineage": "heldout-lineage",
            "cluster_id": "heldout-cluster", "seed_group": "heldout-seeds",
            "taskset_sha256": holdout._canonical(block["taskset"]),
            "prompt_sha256": holdout._task_prompts(block["taskset"]),
        } for block in self.blocks]
        self.prior = {
            role: {"source_sha256": "8" * 64, "members": [{
                "family": "public-dev", "lineage": "public-lineage", "seed_group": "public-seeds",
                "prompt_sha256": holdout._task_prompts(alloc.gen(25)),
            }]} for role in holdout.PRIOR_ROLES
        }

    def verify(self, *, witness_adjustment=None):
        f = self.fixture
        tasks = f.bundle / "tasks.json"
        task_pin = f.write(tasks, {"blocks": self.blocks})
        f.manifest["inputs"]["task_manifest_sha256"] = task_pin
        manifest, index, manifest_pin, index_pin = f.freeze()
        witness = f.root / "exposure.json"
        record = {"schema": holdout.SCHEMA, "manifest_sha256": manifest_pin,
                  "task_inventory_sha256": task_pin, "prior": self.prior, "holdout": self.rows}
        record.update(witness_adjustment or {})
        witness_pin = f.write(witness, record)
        return holdout.verify(f.bundle, manifest, index, tasks, witness, manifest_sha256=manifest_pin,
                              evidence_index_sha256=index_pin, witness_sha256=witness_pin)

    def test_clean_and_disrupted_repeats_preserve_one_cluster(self):
        report = self.verify()
        self.assertEqual((report["heldout_blocks"], report["heldout_clusters"]), (2, 1))
        self.assertFalse(report["scientific_acceptance"])

    def test_all_prior_exposure_dimensions_are_disjoint(self):
        row = self.prior["development"]["members"][0]
        original = row.copy()
        for field in holdout.GROUP_FIELDS:
            with self.subTest(field=field):
                row.update(original)
                row[field] = self.rows[0][field]
                with self.assertRaisesRegex(ValueError, f"holdout {field} overlaps prior exposure"):
                    self.verify()

    def test_fresh_witness_cannot_cross_cluster_or_omit_a_block(self):
        self.rows[1]["cluster_id"] = "aliased-cluster"
        with self.assertRaisesRegex(ValueError, "repeated lineage is split"):
            self.verify()
        self.rows.pop()
        with self.assertRaisesRegex(ValueError, "cover every scheduled block"):
            self.verify()

    def test_cluster_join_detects_same_content_after_renaming_tasks(self):
        self.rows[1].update(lineage="renamed-lineage", seed_group="renamed-seed", cluster_id="another-cluster")
        common = copy.deepcopy(self.blocks[0]["taskset"]["tasks"][0])
        common["id"] = "renamed-task"
        other_taskset = alloc.gen(22, split="heldout")
        other_taskset["tasks"][0] = common
        self.blocks[1].update(seed=22, taskset=other_taskset)
        self.rows[1]["taskset_sha256"] = holdout._canonical(other_taskset)
        self.rows[1]["prompt_sha256"] = holdout._task_prompts(other_taskset)
        with self.assertRaisesRegex(ValueError, "repeated task prompt is split"):
            self.verify()

    def test_same_scheduled_seed_cannot_be_split_under_fresh_labels(self):
        taskset = alloc.gen(22, split="heldout")
        taskset["seed"] = self.blocks[0]["seed"]
        self.blocks[1]["taskset"] = taskset
        self.rows[1].update(lineage="new-lineage", seed_group="new-seed-group", cluster_id="new-cluster",
                            taskset_sha256=holdout._canonical(taskset), prompt_sha256=holdout._task_prompts(taskset))
        with self.assertRaisesRegex(ValueError, "repeated scheduled seed is split"):
            self.verify()

    def test_one_reused_prompt_invalidates_a_different_prior_taskset(self):
        prompt = self.rows[0]["prompt_sha256"][0]
        row = self.prior["calibration"]["members"][0]
        row["prompt_sha256"] = sorted([*row["prompt_sha256"], prompt])
        with self.assertRaisesRegex(ValueError, "holdout prompt overlaps prior exposure"):
            self.verify()

    def test_fresh_witness_cannot_substitute_content_or_scope(self):
        baseline = copy.deepcopy(self.rows)
        self.rows[0]["prompt_sha256"] = ["a" * 64]
        with self.assertRaisesRegex(ValueError, "does not bind taskset bytes"):
            self.verify()
        self.rows = baseline
        self.rows[0]["family"] = "another-family"
        with self.assertRaisesRegex(ValueError, "family differs"):
            self.verify()
        with self.assertRaisesRegex(ValueError, "different freeze"):
            self.verify(witness_adjustment={"manifest_sha256": "a" * 64})

    def test_development_taskset_cannot_become_holdout_via_witness_label(self):
        self.blocks[0]["taskset"] = alloc.gen(25)
        with self.assertRaisesRegex(ValueError, "not declared held out"):
            self.verify()

    def test_enabled_line_exposure_must_bind_its_selected_data(self):
        self.fixture.fake_receipt()
        with self.assertRaisesRegex(ValueError, "prior exposure sources"):
            self.verify()
        self.prior["L1"] = copy.deepcopy(self.prior["development"])
        with self.assertRaisesRegex(ValueError, "differs from the selected research data"):
            self.verify()
        receipt = json.loads((self.fixture.bundle / "L1-test-receipt.json").read_bytes())
        self.prior["L1"]["source_sha256"] = receipt["artifacts"]["data"]["sha256"]
        self.assertEqual(self.verify()["heldout_blocks"], 2)
