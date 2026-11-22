"""Ensure that matched schedules cannot stand in for exact policy portability."""

from copy import deepcopy
import json
import subprocess
import sys
import unittest

from lab import replication_pairing as pairing
from lab import replication_coverage as coverage
from lab.tests import test_replication_coverage as captures
from lab.tests import test_replication_pairing as fixtures


class ReplicationPolicyTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ReplicationPairingTests()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.setUp()
        self.inputs = self.fixture._inputs()
        digest = fixtures._digest
        reference = {
            "mechanical": {key: digest(f"ref-{key}") for key in
                           ("chat_template", "token_accounting", "normalization")},
            "arms": {arm: {"method_sha256": digest(arm), "parameters": {
                "threshold": digest(f"{arm}-threshold"), "budget": digest(f"{arm}-budget"),
            }} for arm in ("technique", "comparator")},
        }
        unchanged = deepcopy(reference)
        unchanged["mechanical"]["chat_template"] = digest("transfer-template")
        recalibrated = deepcopy(unchanged)
        recalibrated["arms"]["technique"]["parameters"]["threshold"] = digest("second-threshold")
        self.profile = {
            "schema": "replication_policy_portability_v1",
            "line": "L2",
            "schedule_pins": {key: value[1] for key, value in self.inputs.items() if key != "line"},
            "roles": {"reference": reference, "unchanged": unchanged, "recalibrated": recalibrated},
            "allowed_mechanical_changes": ["chat_template"],
            "calibration": {
                "task_ids": ["fit-second"],
                "allowed_parameters": {"technique": ["threshold"], "comparator": []},
                "procedure_sha256": digest("calibration-procedure"),
                "allowance_sha256": digest("common-calibration-budget"),
            },
        }

    def pin(self, profile=None):
        return self.fixture._pin("portability", json.dumps(self.profile if profile is None else profile))

    def test_matching_policy_and_calibration_profile_through_cli(self):
        command = [sys.executable, "-B", "-m", "lab.replication_pairing", "--line", "L2",
                   *(part for name in ("splits", "unchanged", "recalibrated", "reference")
                     for part in (f"--{name}", *map(str, self.inputs[name]))),
                   "--policy-witness", *map(str, self.pin())]
        result = subprocess.run(command, text=True, capture_output=True, timeout=10, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)["policy_portability"]
        self.assertEqual(report["mechanical_changes"], ["chat_template"])
        self.assertEqual(report["recalibrated_parameter_changes"], {"technique": ["threshold"], "comparator": []})
        self.assertFalse(report["runtime_policy_verified"])

    def test_mutant_profiles_are_refused_even_at_their_new_pins(self):
        for mutate, message in (
            (lambda d: d["roles"]["unchanged"]["arms"]["comparator"]["parameters"].update(budget="1" * 64),
             "unchanged transfer changed a frozen arm"),
            (lambda d: d["roles"]["recalibrated"]["arms"]["technique"].update(method_sha256="1" * 64),
             "calibration changed a frozen method"),
            (lambda d: d["roles"]["recalibrated"]["arms"]["comparator"]["parameters"].update(threshold="1" * 64),
             "calibration changed an unauthorized parameter"),
            (lambda d: d["calibration"].update(task_ids=["case-a"]), "second-family calibration split"),
            (lambda d: d["calibration"].update(task_ids=["fit-ref"]), "second-family calibration split"),
            (lambda d: d["schedule_pins"].update(reference="1" * 64), "does not bind the paired schedules"),
            (lambda d: d["roles"]["recalibrated"]["mechanical"].update(chat_template="1" * 64),
             "transfer runtime mechanics differ"),
            (lambda d: d.update(allowed_mechanical_changes=[]), "undeclared mechanical change"),
        ):
            profile = deepcopy(self.profile)
            mutate(profile)
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                pairing.verify(**self.inputs, policy_witness=self.pin(profile))

    def test_missing_reference_schedule_keeps_cross_family_effect_unavailable(self):
        del self.inputs["reference"]
        del self.profile["schedule_pins"]["reference"]
        report = pairing.verify(**self.inputs, policy_witness=self.pin())
        self.assertEqual(report["cross_family_pairing"], "withheld_missing_reference_holdout")
        self.assertEqual(report["policy_portability"]["declared_second_family_calibration_tasks"], 1)

    def test_policy_and_snapshot_coverage_join_through_cli(self):
        capture = captures.ReplicationCoverageTests()
        self.addCleanup(capture.doCleanups)
        capture.setUp()
        inputs, document, root, _ = capture.capture_fixture()
        self.profile["schedule_pins"] = document["schedule_pins"]
        policy = self.pin()
        observations = capture.fixture._pin("execution", json.dumps(document))
        command = [sys.executable, "-B", "-m", "lab.replication_coverage", "--line", inputs["line"]]
        for name, pinned in inputs.items():
            if name != "line":
                command.extend((f"--{name}", *map(str, pinned)))
        command.extend(("--execution-observation", *map(str, observations), "--capture-root", str(root),
                        "--policy-witness", *map(str, policy)))
        result = subprocess.run(command, text=True, capture_output=True, timeout=10, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["pairing"]["policy_portability"]["witness_sha256"], policy[1])
        self.assertEqual(report["execution_observation"]["checked_capture_bytes"]["outputs"], 15)
        self.assertFalse(report["execution_observation"]["native_execution_verified"])

    def test_same_value_after_authorized_fit_is_valid(self):
        original = self.profile["roles"]["unchanged"]["arms"]["technique"]["parameters"]
        self.profile["roles"]["recalibrated"]["arms"]["technique"]["parameters"] = original
        report = pairing.verify(**self.inputs, policy_witness=self.pin())
        self.assertEqual(report["policy_portability"]["recalibrated_parameter_changes"]["technique"], [])
