"""Scope an observed replication policy to the exact attempt and held-out input."""

from copy import deepcopy
from hashlib import sha256
import json
import subprocess
import sys
import unittest

from lab import replication_coverage as audit
from lab.tests import test_replication_coverage as captures
from lab.tests import test_replication_policy_artifacts as fixtures


class ReplicationExecutionPolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = fixtures.ReplicationPolicyArtifactTests()
        self.addCleanup(self.policy.doCleanups)
        self.policy.setUp()
        capture = captures.ReplicationCoverageTests()
        self.addCleanup(capture.doCleanups)
        capture.setUp()
        capture.fixture.rows = deepcopy(self.policy.fixture.rows)
        self.inputs, self.document, self.root, _ = capture.capture_fixture()
        self.policy.profile["schedule_pins"] = self.document["schedule_pins"]
        declared = self.policy.policy = self.policy.case.pin()
        self.policy.inventory["policy_witness_sha256"] = declared[1]
        artifacts = self.policy.witness()
        self.inputs.update(policy_witness=declared, policy_artifacts=artifacts, capture_root=self.root)
        self.document.update(schema="replication_execution_observation_v2",
                             policy_witness_sha256=declared[1], artifact_witness_sha256=artifacts[2])
        self.terminals = []
        task_pins = {(row["task_id"], row["replicate_id"]): row["task_input_sha256"]
                     for row in capture.fixture.rows}
        for event in self.document["executions"]:
            terminal = json.loads((self.root / "terminal" / event["observer_capture_sha256"]).read_bytes())
            role, arm = event["role"], event["arm"]
            config = self.policy.profile["roles"][role]
            effective = {"role": role, "arm": arm, "mechanical": config["mechanical"],
                         "arm_policy": config["arms"][arm]}
            digest = sha256(json.dumps(effective, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            terminal.update(schema="replication_terminal_capture_v2", applied_input_policy=None)
            if event["state"] == "observed":
                terminal["applied_input_policy"] = {
                    "policy_witness_sha256": declared[1],
                    "configuration_sha256": digest,
                    "task_input_sha256": task_pins[event["task_id"], event["replicate_id"]],
                }
            self.terminals.append(terminal)

    def pin(self, terminals=None, document=None):
        document = deepcopy(self.document if document is None else document)
        for event, terminal in zip(document["executions"], self.terminals if terminals is None else terminals,
                                   strict=True):
            raw = json.dumps(terminal).encode()
            digest = sha256(raw).hexdigest()
            (self.root / "terminal" / digest).write_bytes(raw)
            event["observer_capture_sha256"] = digest
        return self.policy.fixture._pin("execution-v2", json.dumps(document))

    def test_policy_observation_joins_every_completed_attempt(self):
        result = audit.verify(**self.inputs, execution_observation=self.pin())["execution_observation"]
        self.assertEqual(result["input_policy_capture_rows"], {"observed": 15, "stopped_or_void": 0})
        self.assertFalse(result["native_execution_verified"])
        self.assertFalse(result["native_policy_application_verified"])

    def test_repinned_role_arm_and_task_input_swaps_are_refused(self):
        observed = [terminal for terminal in self.terminals if terminal["state"] == "observed"]
        target = observed[0]
        for field, foreign in (
            ("configuration_sha256", next(row for row in observed if row["assignment"]["role"] !=
                                          target["assignment"]["role"])),
            ("configuration_sha256", next(row for row in observed if row["assignment"]["role"] ==
                                          target["assignment"]["role"] and row["assignment"]["arm"] !=
                                          target["assignment"]["arm"])),
            ("task_input_sha256", next(row for row in observed if row["assignment"]["replicate_id"] !=
                                       target["assignment"]["replicate_id"])),
        ):
            with self.subTest(field=field, foreign=foreign["assignment"]):
                terminals = deepcopy(self.terminals)
                replacement = terminals[self.terminals.index(target)]["applied_input_policy"]
                replacement[field] = foreign["applied_input_policy"][field]
                with self.assertRaisesRegex(ValueError, "captured input or applied policy differs"):
                    audit.verify(**self.inputs, execution_observation=self.pin(terminals))

    def test_legacy_and_missing_policy_terminal_are_refused_for_observed(self):
        for downgrade, message in ((False, "captured input or applied policy differs"),
                                   (True, "invalid terminal capture fields")):
            terminals = deepcopy(self.terminals)
            completed = next(row for row in terminals if row["state"] == "observed")
            completed["applied_input_policy"] = None
            if downgrade:
                completed["schema"] = "replication_terminal_capture_v1"
                del completed["applied_input_policy"]
            with self.subTest(downgrade=downgrade), self.assertRaisesRegex(ValueError, message):
                audit.verify(**self.inputs, execution_observation=self.pin(terminals))

    def test_policy_bound_observation_requires_both_witnesses_and_raw_bytes(self):
        pinned = self.pin()
        for key in ("policy_artifacts", "capture_root"):
            inputs = {name: value for name, value in self.inputs.items() if name != key}
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "requires exact artifact custody"):
                audit.verify(**inputs, execution_observation=pinned)
        for key in ("policy_witness_sha256", "artifact_witness_sha256"):
            document = self.document | {key: "0" * 64}
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "different policy evidence"):
                audit.verify(**self.inputs, execution_observation=self.pin(document=document))

    def test_stopped_attempt_can_supply_exact_policy_without_claiming_output(self):
        terminals = deepcopy(self.terminals)
        stopped = next(row for row in terminals if row["state"] == "stopped")
        role, arm = (stopped["assignment"][key] for key in ("role", "arm"))
        other = next(row for row in terminals if row["state"] == "observed"
                     and (row["assignment"]["role"], row["assignment"]["arm"]) == (role, arm))
        config = other["applied_input_policy"]["configuration_sha256"]
        schedule = json.loads(self.inputs[role][0].read_bytes())["rows"]
        expected = next(row["task_input_sha256"] for row in schedule
                        if all(row[key] == stopped["assignment"][key] for key in ("task_id", "replicate_id")))
        stopped["applied_input_policy"] = {
            "policy_witness_sha256": self.inputs["policy_witness"][1], "configuration_sha256": config,
            "task_input_sha256": expected,
        }
        result = audit.verify(**self.inputs, execution_observation=self.pin(terminals))["execution_observation"]
        self.assertEqual(result["input_policy_capture_rows"], {"observed": 15, "stopped_or_void": 1})
        self.assertEqual(result["checked_capture_bytes"]["outputs"], 15)

    def test_exact_policy_can_be_checked_through_coverage_cli(self):
        args = [sys.executable, "-B", "-m", "lab.replication_coverage", "--line", self.inputs["line"]]
        for name, value in self.inputs.items():
            if name == "line":
                continue
            values = value if isinstance(value, tuple) else (value,)
            args.extend((f"--{name.replace('_', '-')}", *map(str, values)))
        args.extend(("--execution-observation", *map(str, self.pin())))
        result = subprocess.run(args, capture_output=True, text=True, timeout=10, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)["execution_observation"]
        self.assertEqual(output["input_policy_capture_rows"]["observed"], 15)
        self.assertFalse(output["native_policy_application_verified"])
