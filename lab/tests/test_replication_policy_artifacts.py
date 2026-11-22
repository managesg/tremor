"""Ensure that a declaration cannot substitute for available exact-byte evidence."""

from copy import deepcopy
from hashlib import sha256
import json
import subprocess
import sys
import unittest

from lab import replication_pairing as pairing
from lab.tests import test_replication_policy as fixtures
from lab.tests import test_replication_coverage as captures


class ReplicationPolicyArtifactTests(unittest.TestCase):
    def setUp(self):
        self.case = fixtures.ReplicationPolicyTests()
        self.addCleanup(self.case.doCleanups)
        self.case.setUp()
        self.fixture = self.case.fixture
        self.bundle = self.fixture.root / "policy-bundle"
        for role in ("policy", "input"):
            (self.bundle / role).mkdir(parents=True)
        for row in self.fixture.rows:
            key = f"{row['task_id']}:{row['replicate_id']}"
            row["task_input_sha256"] = self.store("input", key)
        self.inputs = self.fixture._inputs()
        self.profile = self.case.profile
        self.profile["schedule_pins"] = {name: pin[1] for name, pin in self.inputs.items() if name != "line"}
        for text in (
            "ref-chat_template", "ref-token_accounting", "ref-normalization", "transfer-template",
            "comparator", "technique", "technique-threshold", "technique-budget", "comparator-threshold",
            "comparator-budget", "second-threshold", "calibration-procedure", "common-calibration-budget",
        ):
            self.store("policy", text)
        self.policy = self.case.pin()
        self.inventory = {
            "schema": "replication_policy_artifacts_v1",
            "policy_witness_sha256": self.policy[1],
            "prior_inputs": {case: self.store("input", case) for case in ("dev", "fit-ref", "fit-second")},
        }

    def store(self, category, text):
        raw = text.encode()
        pin = sha256(raw).hexdigest()
        (self.bundle / category / pin).write_bytes(raw)
        return pin

    def witness(self):
        return self.bundle, *self.fixture._pin("policy-artifacts", json.dumps(self.inventory))

    def test_exact_artifact_intake_via_pairing_cli(self):
        command = [sys.executable, "-B", "-m", "lab.replication_pairing", "--line", "L2",
                   *(part for name in ("splits", "unchanged", "recalibrated", "reference")
                     for part in (f"--{name}", *map(str, self.inputs[name]))),
                   "--policy-witness", *map(str, self.policy), "--policy-artifacts", *map(str, self.witness())]
        result = subprocess.run(command, text=True, capture_output=True, timeout=10, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        evidence = json.loads(result.stdout)["policy_portability"]["artifact_custody"]
        self.assertEqual(evidence["verified_policy_artifacts"], 13)
        self.assertEqual(evidence["verified_prior_tasks"], 3)
        self.assertEqual(evidence["verified_holdout_assignments"], 3)
        self.assertTrue(evidence["exact_checked_input_bytes_disjoint_across_splits"])

    def verify(self):
        return pairing.verify(**self.inputs, policy_witness=self.policy, policy_artifacts=self.witness())

    def test_changed_policy_blob_cannot_be_hidden_by_matching_declarations(self):
        digest = self.profile["roles"]["reference"]["arms"]["technique"]["method_sha256"]
        (self.bundle / "policy" / digest).write_bytes(b"different method content")
        with self.assertRaisesRegex(ValueError, "captured policy digest mismatch"):
            self.verify()

    def test_missing_holdout_bytes_and_linked_artifacts_are_refused(self):
        digest = self.fixture.rows[0]["task_input_sha256"]
        path = self.bundle / "input" / digest
        retained = path.with_name("retained")
        path.rename(retained)
        with self.assertRaisesRegex(ValueError, "missing or inaccessible input"):
            self.verify()
        path.symlink_to(retained)
        with self.assertRaisesRegex(ValueError, "missing or inaccessible input"):
            self.verify()

    def test_fresh_repin_cannot_hide_input_reuse_across_partitions(self):
        original = self.inventory["prior_inputs"].copy()
        for digest in (self.fixture.rows[0]["task_input_sha256"], original["fit-ref"]):
            self.inventory["prior_inputs"] = original | {"fit-second": digest}
            with self.subTest(digest=digest), self.assertRaisesRegex(ValueError, "cross split boundaries"):
                self.verify()

    def test_roster_and_policy_witness_must_match(self):
        original = deepcopy(self.inventory)
        self.inventory["prior_inputs"].pop("fit-second")
        with self.assertRaisesRegex(ValueError, "invalid prior task input roster"):
            self.verify()
        self.inventory = original | {"policy_witness_sha256": "0" * 64}
        with self.assertRaisesRegex(ValueError, "does not bind"):
            self.verify()

    def test_coverage_cli_with_snapshot_and_captured_outputs(self):
        capture = captures.ReplicationCoverageTests()
        self.addCleanup(capture.doCleanups)
        capture.setUp()
        capture.fixture.rows = deepcopy(self.fixture.rows)
        inputs, document, root, _ = capture.capture_fixture()
        self.profile["schedule_pins"] = document["schedule_pins"]
        self.policy = self.case.pin()
        self.inventory["policy_witness_sha256"] = self.policy[1]
        observation = capture.fixture._pin("execution", json.dumps(document))
        command = [sys.executable, "-B", "-m", "lab.replication_coverage", "--line", inputs["line"]]
        for name, pinned in inputs.items():
            if name != "line":
                command.extend((f"--{name}", *map(str, pinned)))
        command.extend(("--execution-observation", *map(str, observation), "--capture-root", str(root),
                        "--policy-witness", *map(str, self.policy), "--policy-artifacts", *map(str, self.witness())))
        result = subprocess.run(command, text=True, capture_output=True, timeout=10, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["pairing"]["policy_portability"]["artifact_custody"]["verified_policy_artifacts"], 13)
        self.assertEqual(report["execution_observation"]["checked_capture_bytes"]["outputs"], 15)
        self.assertFalse(report["pairing"]["policy_portability"]["runtime_policy_verified"])

    def test_unscheduled_holdout_members_are_explicitly_excluded(self):
        self.fixture.splits["members"].append({
            "task_id": "other-holdout", "group_id": "other-held-group", "split": "holdout",
        })
        self.inputs = self.fixture._inputs()
        self.profile["schedule_pins"] = {name: pin[1] for name, pin in self.inputs.items() if name != "line"}
        self.policy = self.case.pin()
        self.inventory["policy_witness_sha256"] = self.policy[1]
        proof = self.verify()["policy_portability"]["artifact_custody"]
        self.assertEqual(proof["unscheduled_holdout_tasks"], 1)
        self.assertEqual(proof["verified_holdout_assignments"], 3)

    def test_empty_policy_and_input_artifacts_are_refused(self):
        original = deepcopy(self.inventory)
        self.inventory["prior_inputs"]["fit-second"] = self.store("input", "")
        with self.assertRaisesRegex(ValueError, "empty task input"):
            self.verify()
        self.inventory = original
        digest = self.store("policy", "")
        self.profile["calibration"]["procedure_sha256"] = digest
        self.policy = self.case.pin()
        self.inventory["policy_witness_sha256"] = self.policy[1]
        with self.assertRaisesRegex(ValueError, "empty policy"):
            self.verify()
