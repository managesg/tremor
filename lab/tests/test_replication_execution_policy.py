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

    def grading_fixture(self, *, recalibrated_gap=("case-a", "r1")):
        execution = self.pin()
        observations = json.loads(execution[0].read_bytes())["executions"]
        rows = {(row["task_id"], row["replicate_id"]): row
                for row in json.loads(self.inputs["unchanged"][0].read_bytes())["rows"]}
        folder = self.root / "score"
        folder.mkdir()
        grades = []
        for event, terminal in zip(observations, self.terminals, strict=True):
            if terminal["state"] != "observed":
                continue
            assignment = terminal["assignment"]
            row = rows[assignment["task_id"], assignment["replicate_id"]]
            binding = {"assignment": assignment, "terminal_sha256": event["observer_capture_sha256"],
                       "output_sha256": terminal["output_sha256"],
                       **{field: row[field] for field in audit.GRADE_CONTEXT}}
            score = json.dumps({"schema": audit.SCORE_SCHEMA, **binding,
                                "measurements": {"scripted_fixture_readout": 1}}).encode()
            score_pin = sha256(score).hexdigest()
            (folder / score_pin).write_bytes(score)
            grades.append({**binding, "state": "scored", "reason": None, "score_sha256": score_pin})
        grades[0].update(state="invalid", reason="scripted invalid disposition", score_sha256=None)
        gap = next(row for row in grades if (
            row["assignment"]["role"], row["assignment"]["arm"], row["assignment"]["task_id"],
            row["assignment"]["replicate_id"],
        ) == ("recalibrated", "technique", *recalibrated_gap))
        gap.update(state="unavailable", reason="scripted unavailable disposition", score_sha256=None)
        return execution, {"schema": audit.GRADE_SCHEMA, "line": self.inputs["line"],
                           "execution_observation_sha256": execution[1], "grades": grades}

    def test_cli_joins_independent_grading_to_exact_captures(self):
        execution, declaration = self.grading_fixture()
        witness = self.policy.fixture._pin("grading", json.dumps(declaration))
        command = [sys.executable, "-B", "-m", "lab.replication_coverage", "--line", self.inputs["line"]]
        for name, value in (self.inputs | {"execution_observation": execution, "grade_witness": witness}).items():
            if name != "line":
                values = value if isinstance(value, tuple) else (value,)
                command.extend((f"--{name.replace('_', '-')}", *map(str, values)))
        run = subprocess.run(command, capture_output=True, text=True, timeout=10, check=True)
        result = json.loads(run.stdout)
        grade = result["execution_observation"]["grading_receipts"]
        self.assertEqual(grade["states"], {"scored": 13, "invalid": 1, "unavailable": 1})
        self.assertEqual(sum(grade["complete_graded_pairs_by_role"].values()), 6)
        self.assertFalse(grade["scorer_execution_verified"])
        self.assertFalse(result["scientific_acceptance"])
        self.assertEqual(result["execution_observation"]["checked_capture_bytes"]["outputs"], 15)

    def test_fresh_grade_pins_cannot_cross_outputs_inputs_or_attempts(self):
        execution, declaration = self.grading_fixture()
        fixture = self.policy.fixture

        def verify(document):
            witness = fixture._pin("grading", json.dumps(document))
            return audit.verify(**self.inputs, execution_observation=execution, grade_witness=witness)

        with self.assertRaisesRegex(ValueError, "pinned execution observation"):
            verify(declaration | {"execution_observation_sha256": "0" * 64})
        for field in (*audit.GRADE_CONTEXT, "terminal_sha256", "output_sha256"):
            wrong = deepcopy(declaration)
            wrong["grades"][0][field] = "0" * 64
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "frozen scoring inputs"):
                verify(wrong)
        for bad in (declaration["grades"][:-1], declaration["grades"] + declaration["grades"][:1]):
            with self.assertRaisesRegex(ValueError, "each observed attempt once"):
                verify(declaration | {"grades": bad})
        stopped = next(row for row in self.terminals if row["state"] == "stopped")
        altered = deepcopy(declaration)
        altered["grades"].append(altered["grades"][-1] | {"assignment": stopped["assignment"]})
        with self.assertRaisesRegex(ValueError, "each observed attempt once"):
            verify(altered)
        bad_score = deepcopy(declaration)
        bad_score["grades"][-1]["score_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "score capture file"):
            verify(bad_score)
        crossed_score = deepcopy(declaration)
        self.assertEqual(crossed_score["grades"][-1]["output_sha256"], crossed_score["grades"][-2]["output_sha256"])
        crossed_score["grades"][-1]["score_sha256"] = crossed_score["grades"][-2]["score_sha256"]
        with self.assertRaisesRegex(ValueError, "score capture differs from the grading receipt"):
            verify(crossed_score)

    def test_contrast_coverage_uses_same_assignments_despite_equal_role_counts(self):
        execution, declaration = self.grading_fixture(recalibrated_gap=("case-b", "r1"))
        witness = self.policy.fixture._pin("grading", json.dumps(declaration))
        report = audit.verify(**self.inputs, execution_observation=execution, grade_witness=witness)
        grades = report["execution_observation"]["grading_receipts"]
        self.assertEqual(grades["complete_graded_pairs_by_role"],
                         {"reference": 2, "unchanged": 2, "recalibrated": 2})
        expected = {"scheduled_assignments": 3, "matched_graded_assignments": 1, "reason": None}
        self.assertEqual(grades["graded_contrast_coverage"], {
            "reference_vs_unchanged": expected | {"matched_graded_assignments": 2},
            "reference_vs_recalibrated": expected,
            "unchanged_vs_recalibrated": expected,
        })
        self.assertFalse(report["scientific_acceptance"])

    def test_missing_reference_contrast_is_unavailable_instead_of_zero(self):
        schedule = {("a", "r1"), ("b", "r1")}
        coverage = audit._graded_contrasts({"unchanged": {("a", "r1")}, "recalibrated": set()}, schedule)
        unavailable = {"scheduled_assignments": None, "matched_graded_assignments": None,
                       "reason": "missing_reference_schedule"}
        self.assertEqual(coverage["reference_vs_unchanged"], unavailable)
        self.assertEqual(coverage["reference_vs_recalibrated"], unavailable)
        self.assertEqual(coverage["unchanged_vs_recalibrated"],
                         {"scheduled_assignments": 2, "matched_graded_assignments": 0, "reason": None})

    def test_contrast_requires_grades_and_limits_on_the_same_assignment(self):
        coverage = json.loads(self.inputs["coverage"][0].read_bytes())
        rows = {(row["task_id"], row["replicate_id"]): row["roles"] for row in coverage["rows"]}
        rows["case-a", "r2"]["recalibrated"]["technique"]["usage"]["calls"] = 1
        rows["case-b", "r1"]["reference"]["comparator"]["usage"]["gpu_wall_ns"] = None
        self.inputs["coverage"] = self.policy.fixture._pin("budgeted-coverage", json.dumps(coverage))
        self.document["coverage_sha256"] = self.inputs["coverage"][1]
        for terminal in self.terminals:
            assignment = terminal["assignment"]
            key = assignment["task_id"], assignment["replicate_id"]
            terminal["usage"] = rows[key][assignment["role"]][assignment["arm"]]["usage"]
            terminal["coverage_sha256"] = self.inputs["coverage"][1]

        execution, grades = self.grading_fixture(recalibrated_gap=("case-b", "r1"))
        graded = self.policy.fixture._pin("budgeted-grades", json.dumps(grades))
        schedule = json.loads(self.inputs["unchanged"][0].read_bytes())["rows"]
        limits = {
            "schema": audit.LIMIT_SCHEMA, "line": self.inputs["line"], "schedule_pins": self.document["schedule_pins"],
            "per_assignment_limits": {
                role: {row["block_id"]: {"calls": 0, "gpu_wall_ns": 0} for row in schedule}
                for role in ("reference", "unchanged", "recalibrated")
            },
        }
        limit_pin = self.policy.fixture._pin("per-assignment-limits", json.dumps(limits))
        inputs = self.inputs | {"execution_observation": execution, "grade_witness": graded}
        report = audit.verify(**inputs, limits=limit_pin)
        result = report["execution_observation"]["grading_receipts"]
        cluster, = report["linked_clusters"]
        self.assertEqual(cluster["observed_pairs_within_limits"], {"reference": 1, "unchanged": 2, "recalibrated": 2})
        self.assertEqual(result["complete_graded_pairs_by_role"], {"reference": 2, "unchanged": 2, "recalibrated": 2})
        within = result["within_per_assignment_limits"]
        self.assertEqual(within["complete_graded_pairs_by_role"], {"reference": 1, "unchanged": 2, "recalibrated": 1})
        self.assertEqual({name: row["matched_graded_assignments"]
                          for name, row in within["graded_contrast_coverage"].items()},
                         {"reference_vs_unchanged": 1, "reference_vs_recalibrated": 0,
                          "unchanged_vs_recalibrated": 0})
        self.assertTrue(all(row["scheduled_assignments"] == 3 and row["reason"] is None
                            for row in within["graded_contrast_coverage"].values()))
        before = audit.verify(**inputs)["execution_observation"]["grading_receipts"]
        self.assertNotIn("within_per_assignment_limits", before)
        self.assertEqual({key: value for key, value in result.items() if key != "within_per_assignment_limits"}, before)
