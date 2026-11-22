"""Check exact scheduled scorer inputs independently of grade capture coverage."""

from copy import deepcopy
from hashlib import sha256
import json
import subprocess
import sys
import unittest

from lab import replication_coverage as audit
from lab.tests import test_replication_execution_policy as policy_cases


class ReplicationScoringArtifactTests(unittest.TestCase):
    def setUp(self):
        self.case = case = policy_cases.ReplicationExecutionPolicyTests()
        self.addCleanup(case.doCleanups)
        case.setUp()
        execution, grades = case.grading_fixture()
        grade_pin = case.policy.fixture._pin("grading", json.dumps(grades))
        self.inputs = case.inputs | {"execution_observation": execution, "grade_witness": grade_pin}
        self.artifacts = {field: {} for field in audit.GRADE_CONTEXT}
        rows = json.loads(self.inputs["unchanged"][0].read_bytes())["rows"]
        for row in rows:
            for field in audit.GRADE_CONTEXT:
                raw = f"{row['task_id']}:{row['replicate_id']}:{field}".encode()
                digest = sha256(raw).hexdigest()
                self.assertEqual(digest, row[field])
                self.artifacts[field][digest] = raw
        self.document = {"schema": audit.SCORING_ARTIFACTS_SCHEMA, "line": self.inputs["line"],
                         "schedule_pins": case.document["schedule_pins"], "execution_observation_sha256": execution[1],
                         "grade_witness_sha256": grade_pin[1],
                         "artifacts": {field: sorted(files) for field, files in self.artifacts.items()}}

    def capture_artifacts(self):
        for field, directory in audit.SCORING_ARTIFACT_DIRECTORIES.items():
            folder = self.case.root / directory
            folder.mkdir()
            for digest, raw in self.artifacts[field].items():
                (folder / digest).write_bytes(raw)

    def pin(self, document=None):
        return self.case.policy.fixture._pin("scoring-artifacts", json.dumps(
            self.document if document is None else document))

    def test_existing_grades_do_not_assert_scoring_input_custody(self):
        report = audit.verify(**self.inputs)
        grade = report["execution_observation"]["grading_receipts"]
        self.assertEqual(grade["states"], {"scored": 13, "invalid": 1, "unavailable": 1})
        self.assertEqual(sum(grade["complete_graded_pairs_by_role"].values()), 6)
        self.assertNotIn("scoring_artifact_custody", grade)
        self.assertEqual({entry.name for entry in self.case.root.iterdir()}, {"loader", "output", "score", "terminal"})
        with self.assertRaisesRegex(ValueError, "missing or inaccessible scorer capture file"):
            audit.verify(**self.inputs, scoring_artifacts=self.pin())

    def test_cli_witness_checks_all_scheduled_scoring_input_bytes(self):
        self.capture_artifacts()
        rows = json.loads(self.inputs["unchanged"][0].read_bytes())["rows"]
        limits = {"schema": audit.LIMIT_SCHEMA, "line": self.inputs["line"],
                  "schedule_pins": self.document["schedule_pins"], "per_assignment_limits": {
                      role: {row["block_id"]: {"calls": 0} for row in rows}
                      for role in ("reference", "unchanged", "recalibrated")}}
        limits_pin = self.case.policy.fixture._pin("per-assignment-limits", json.dumps(limits))
        command = [sys.executable, "-B", "-m", "lab.replication_coverage", "--line", self.inputs["line"]]
        for name, value in (self.inputs | {"limits": limits_pin}).items():
            if name == "line":
                continue
            values = value if isinstance(value, tuple) else (value,)
            command.extend(("--" + name.replace("_", "-"), *map(str, values)))
        previous = subprocess.check_output(command, text=True, timeout=10)
        verified = json.loads(subprocess.check_output(
            [*command, "--scoring-artifacts", *map(str, self.pin())], text=True, timeout=10))
        joined = verified["execution_observation"]["grading_receipts"].pop("scoring_artifact_custody")
        self.assertEqual(json.dumps(verified, sort_keys=True) + "\n", previous)
        self.assertEqual(joined["scheduled_assignments"], 3)
        self.assertEqual(joined["verified_artifacts"], {"scorer": 3, "hidden-truth": 3, "scoring-opportunities": 3})
        self.assertIn("within_per_assignment_limits", verified["execution_observation"]["grading_receipts"])
        self.assertFalse(joined["scorer_execution_verified"])
        self.assertFalse(verified["scientific_acceptance"])

    def test_independent_witness_cannot_cross_a_schedule_execution_or_grade(self):
        self.capture_artifacts()
        for key in ("line", "schedule_pins", "execution_observation_sha256", "grade_witness_sha256"):
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "differs from the pinned schedule"):
                audit.verify(**self.inputs, scoring_artifacts=self.pin(self.document | {key: "0" * 64}))

    def test_a_rehashed_score_roster_still_requires_every_scheduled_artifact(self):
        self.capture_artifacts()
        for field, directory in audit.SCORING_ARTIFACT_DIRECTORIES.items():
            for alternative in (self.document["artifacts"][field][:-1], ["0" * 64]):
                document = deepcopy(self.document)
                document["artifacts"][field] = alternative
                with self.subTest(artifact=field, entries=len(alternative)), self.assertRaisesRegex(
                    ValueError, f"{directory} artifact roster differs from the full schedule"
                ):
                    audit.verify(**self.inputs, scoring_artifacts=self.pin(document))

    def test_unattempted_assignments_remain_in_the_artifact_denominator(self):
        self.capture_artifacts()
        fixture = self.case.policy.fixture
        coverage = json.loads(self.inputs["coverage"][0].read_bytes())
        for row in coverage["rows"]:
            for arms in row["roles"].values():
                for receipt in arms.values():
                    receipt.update(state="unavailable", usage=dict.fromkeys(audit.RESOURCES))
        coverage_pin = fixture._pin("unavailable-coverage", json.dumps(coverage))
        execution = self.case.document | {"coverage_sha256": coverage_pin[1], "executions": []}
        execution_pin = fixture._pin("no-execution", json.dumps(execution))
        grades = {"schema": audit.GRADE_SCHEMA, "line": self.inputs["line"],
                  "execution_observation_sha256": execution_pin[1], "grades": []}
        grade_pin = fixture._pin("empty-grades", json.dumps(grades))
        bound = self.document | {"execution_observation_sha256": execution_pin[1], "grade_witness_sha256": grade_pin[1]}
        inputs = self.inputs | {"coverage": coverage_pin, "execution_observation": execution_pin, "grade_witness": grade_pin}
        report = audit.verify(**inputs, scoring_artifacts=self.pin(bound))
        grades = report["execution_observation"]["grading_receipts"]
        self.assertEqual(grades["states"], {"scored": 0, "invalid": 0, "unavailable": 0})
        self.assertEqual(grades["scoring_artifact_custody"]["scheduled_assignments"], 3)
        self.assertEqual(sum(grades["scoring_artifact_custody"]["verified_artifacts"].values()), 9)

    def test_changed_or_linked_capture_cannot_keep_its_expected_digest(self):
        self.capture_artifacts()
        changed = self.case.root / "hidden-truth" / self.document["artifacts"]["hidden_truth_sha256"][0]
        raw = changed.read_bytes()
        changed.write_bytes(b"different synthetic truth")
        with self.assertRaisesRegex(ValueError, "captured hidden-truth digest mismatch"):
            audit.verify(**self.inputs, scoring_artifacts=self.pin())
        changed.write_bytes(raw)
        retained = changed.with_name("retained-fixture")
        changed.rename(retained)
        changed.symlink_to(retained)
        with self.assertRaisesRegex(ValueError, "missing or inaccessible hidden-truth capture file"):
            audit.verify(**self.inputs, scoring_artifacts=self.pin())

    def test_scoring_artifact_custody_needs_the_exact_grading_witness(self):
        self.capture_artifacts()
        with self.assertRaisesRegex(ValueError, "requires an independently pinned grading witness"):
            audit.verify(**(self.inputs | {"grade_witness": None}), scoring_artifacts=self.pin())
