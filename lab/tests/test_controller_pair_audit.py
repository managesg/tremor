import copy
import json
import subprocess
import sys
import unittest

from lab import controller_pair_audit as audit
from lab.tests import test_controller_selection as fixtures
from murmuration.trapbench import alloc


class ControllerPairAuditTests(unittest.TestCase):
    def setUp(self):
        self.fixture = f = fixtures.ControllerSelectionTests()
        self.addCleanup(f.doCleanups)
        f.setUp()
        for arm in f.manifest["arms"].values():
            arm["budget"]["cpu_wall_ns"] = 100
        self.block = {"block_id": "paired-clean", "condition": "clean", "seed": 25, "order": ["plain", "combined"],
                      "taskset": alloc.gen(25)}
        self.inputs = {
            "task_manifest_sha256": f.artifact("tasks.json", {"blocks": [self.block]}),
            "scorer_sha256": f.artifact("scorers.json", {"scorers": audit._scorer_ids()}),
            "protocol_sha256": f.artifact("protocol.txt", b"Scripted paired accounting development fixture"),
        }
        f.manifest["inputs"] = {key: reference["sha256"] for key, reference in self.inputs.items()}
        proposals = [dict((key, value) for key, value in job.items() if key != "action")
                     for job in alloc.oracle_log(self.block["taskset"])]
        self.rows = [
            self.arm("plain", [proposals[0], proposals[1], proposals[2] | {"task": proposals[0]["task"]}]),
            self.arm("combined", proposals[:3]),
        ]

    @staticmethod
    def attempt(sequence, role, work=None, *, status="completed", cpu=2, calls=0, tokens=0):
        usage = dict.fromkeys(audit.USAGE, 0) | {"cpu_wall_ns": cpu, "calls": calls, "input_tokens": tokens}
        return {"sequence": sequence, "role": role, "status": status, "usage": usage, "work": work}

    def arm(self, arm, proposals):
        f = self.fixture
        return {"block_id": self.block["block_id"], "arm": arm,
                "condition": self.block["condition"], "seed": self.block["seed"],
                "scope": f.manifest["scope"], "inputs": f.manifest["inputs"].copy(),
                "policy_sha256": f.manifest["arms"][arm]["policy_sha256"], "terminal": "completed",
                "attempts": [self.attempt(i, "worker", work) for i, work in enumerate(proposals)]}

    def freeze(self, releases=None):
        f = self.fixture
        manifest, index, manifest_pin, index_pin = f.freeze()
        trace = f.root / "trace.json"
        document = {"evidence": "scripted_cpu", "manifest_sha256": manifest_pin,
                    "input_files": self.inputs, "arms": self.rows}
        if releases is not None:
            document["schema"] = audit.TRACE_V2
            for row in self.rows:
                for attempt in row["attempts"]:
                    attempt.setdefault("release", None)
        trace_pin = f.write(trace, document)
        inputs = {"bundle": f.bundle, "manifest": manifest, "evidence_index": index, "trace": trace,
                  "manifest_sha256": manifest_pin, "evidence_index_sha256": index_pin, "trace_sha256": trace_pin}
        if releases is not None:
            witness = f.root / "release_witness.json"
            witness_pin = f.write(witness, {
                "schema": audit.RELEASE_WITNESS, "trace_sha256": trace_pin,
                "arms": [
                    {"block_id": row["block_id"], "arm": row["arm"], "releases": observations}
                    for row, observations in zip(self.rows, releases, strict=True)
                ],
            })
            inputs["release_witness"] = (witness, witness_pin)
        return inputs

    def add_release(self, row_index, work, *, status="completed", done=True):
        row = self.rows[row_index]
        sequence = len(row["attempts"])
        payload = {"agent": work["agent"], "task": work["task"], "done": done}
        row["attempts"].append(self.attempt(sequence, "worker", status=status) | {"release": payload})
        return {"sequence": sequence, **payload, "executed": status == "completed"}

    def test_committed_fixture_recounts_penalized_duplicate_and_charges_failed_advice(self):
        combined = self.rows[1]["attempts"]
        combined.append(self.attempt(len(combined), "advice", status="failed", cpu=5))
        result = audit.verify(**self.freeze())
        self.assertFalse(result["scientific_acceptance"])
        pair, = result["pairs"]
        self.assertEqual((pair["eligible_count"], pair["paired_delta"]), (6, "1/6"))
        self.assertEqual([row["distinct_passing"] for row in pair["arms"]], [2, 3])
        self.assertEqual(pair["arms"][0]["duplicate_work"], 1)
        self.assertEqual(result["arm_resource_receipts"]["combined"]["known_usage"]["cpu_wall_ns"], 11)
        self.assertNotIn("release_witness_sha256", result)
        self.assertNotIn("completion_safeguard", pair["arms"][0])

    def test_failed_workers_do_not_turn_a_missing_observation_into_zero_work(self):
        self.rows[1]["attempts"] = [
            self.attempt(0, "worker", status="failed", cpu=3),
            self.attempt(1, "worker", status="failed", cpu=4),
            self.attempt(2, "observation"),
        ]
        with self.assertRaisesRegex(ValueError, "completed arm lacks a completed worker observation"):
            audit.verify(**self.freeze())

        self.rows[1]["terminal"] = "stopped"
        stopped = audit.verify(**self.freeze())
        self.assertEqual(stopped["complete_pairs"], 0)
        self.assertIsNone(stopped["pairs"][0]["paired_delta"])
        self.assertEqual(stopped["arm_resource_receipts"]["combined"]["known_usage"]["cpu_wall_ns"], 9)

        self.rows[1]["terminal"] = "completed"
        self.rows[1]["attempts"][1]["status"] = "completed"
        completed = audit.verify(**self.freeze())
        self.assertEqual(completed["complete_pairs"], 1)
        self.assertEqual(completed["pairs"][0]["arms"][1]["distinct_passing"], 0)
        self.assertEqual(completed["pairs"][0]["paired_delta"], "-1/3")

    def test_v2_independent_scorer_counts_false_done_and_preserves_primary(self):
        combined = self.rows[1]["attempts"]
        correct = combined[0]["work"]
        wrong = {**combined[1]["work"], "answer": combined[1]["work"]["answer"] + 1}
        combined[1]["work"] = wrong
        releases = [
            self.add_release(1, wrong),
            self.add_release(1, correct),
            self.add_release(1, wrong, status="refused"),
            self.add_release(1, wrong, done=False),
        ]
        inputs = self.freeze([[], releases])
        result = audit.verify(**inputs)
        self.assertFalse(result["scientific_acceptance"])
        self.assertEqual(result["release_witness_sha256"], inputs["release_witness"][1])
        pair, = result["pairs"]
        self.assertEqual(pair["paired_delta"], "0")
        self.assertEqual(pair["arms"][0]["completion_safeguard"], {
            "status": "observed", "done_releases": 0, "false_completions": 0, "false_completion_rate": None,
        })
        self.assertEqual(pair["arms"][1]["completion_safeguard"], {
            "status": "observed", "done_releases": 2, "false_completions": 1, "false_completion_rate": "1/2",
        })

    def test_v2_release_before_correct_work_still_counts_as_false(self):
        arm = self.rows[1]
        work = arm["attempts"][0]["work"]
        release = self.add_release(1, work) | {"sequence": 0}
        arm["attempts"].insert(0, arm["attempts"].pop())
        for ordinal, attempt in enumerate(arm["attempts"]):
            attempt["sequence"] = ordinal
        result = audit.verify(**self.freeze([[], [release]]))
        safeguard = result["pairs"][0]["arms"][1]["completion_safeguard"]
        self.assertEqual((safeguard["done_releases"], safeguard["false_completions"]), (1, 1))

    def test_v2_explicit_missing_witness_and_noncompleted_arm_stay_unavailable(self):
        self.add_release(0, self.rows[0]["attempts"][0]["work"])
        combined = self.rows[1]
        combined["terminal"] = "stopped"
        event = self.add_release(1, combined["attempts"][0]["work"])
        combined["attempts"][-1]["usage"] = None
        pair, = audit.verify(**self.freeze([None, [event]]))["pairs"]
        self.assertIsNone(pair["paired_delta"])
        for arm, status in zip(pair["arms"], ("unavailable_missing_witness", "unavailable_noncompleted_arm"), strict=True):
            self.assertEqual(arm["completion_safeguard"], {
                "status": status, "done_releases": None, "false_completions": None, "false_completion_rate": None,
            })

    def test_v2_rejects_erased_fabricated_and_contradictory_releases(self):
        event = self.add_release(1, self.rows[1]["attempts"][0]["work"])
        for releases, error in (
            ([], "marked release is absent"),
            ([event, event], "duplicate release sequence"),
            ([event, {**event, "sequence": 1}], "release lacks a marked attempt"),
            ([{**event, "executed": False}], "disagree on release execution"),
            ([{**event, "done": False}], "disagree on release payload"),
            ([{**event, "agent": "other-worker"}], "disagree on release payload"),
        ):
            with self.subTest(error=error), self.assertRaisesRegex(ValueError, error):
                audit.verify(**self.freeze([[], releases]))
        self.rows[1]["attempts"][-1]["release"]["task"] = "unknown-task"
        with self.assertRaisesRegex(ValueError, "outside the frozen inventory"):
            audit.verify(**self.freeze([[], [{**event, "task": "unknown-task"}]]))

    def test_v2_rejects_witness_from_other_trace_even_with_a_valid_pin(self):
        inputs = self.freeze([[], []])
        with self.assertRaisesRegex(ValueError, "requires an independent release witness pin"):
            audit.verify(**{field: value for field, value in inputs.items() if field != "release_witness"})
        path, _ = inputs["release_witness"]
        document = json.loads(path.read_bytes())
        document["trace_sha256"] = "0" * 64
        inputs["release_witness"] = path, self.fixture.write(path, document)
        with self.assertRaisesRegex(ValueError, "must bind the pinned V2 trace"):
            audit.verify(**inputs)

    def test_v2_cli_replays_an_independently_pinned_witness(self):
        inputs = self.freeze([[], []])
        command = [sys.executable, "-B", "-m", "lab.controller_pair_audit",
                   *[str(inputs[key]) for key in ("bundle", "manifest", "evidence_index", "trace")],
                   "--manifest-sha256", inputs["manifest_sha256"], "--evidence-index-sha256",
                   inputs["evidence_index_sha256"], "--trace-sha256", inputs["trace_sha256"],
                   "--release-witness", *map(str, inputs["release_witness"])]
        result = subprocess.run(command, capture_output=True, text=True, timeout=10, check=True)
        self.assertEqual(json.loads(result.stdout), audit.verify(**inputs))
        command[-1] = "0" * 64
        refused = subprocess.run(command, capture_output=True, text=True, timeout=10, check=False)
        self.assertEqual(refused.returncode, 2)
        self.assertIn("digest mismatch: release_witness.json", refused.stderr)

    def test_stopped_arm_keeps_unknown_usage_without_a_paired_effect(self):
        row = self.rows[1]
        row["terminal"] = "stopped"
        row["attempts"].append(self.attempt(3, "verification", status="failed") | {"usage": None})
        result = audit.verify(**self.freeze())
        self.assertEqual(result["complete_pairs"], 0)
        self.assertIsNone(result["pairs"][0]["paired_delta"])
        self.assertEqual(result["arm_resource_receipts"]["combined"]["unknown_usage_attempts"], 1)
        row["terminal"] = "completed"
        with self.assertRaisesRegex(ValueError, "unaccounted usage"):
            audit.verify(**self.freeze())

    def test_cleanup_is_retained_but_follow_on_work_is_refused_after_a_breach(self):
        row = self.rows[1]
        row["terminal"] = "stopped"
        for arm in self.fixture.manifest["arms"].values():
            arm["budget"]["cpu_wall_ns"] = 10
        row["attempts"].append(self.attempt(3, "observation", cpu=5))
        row["attempts"].append(self.attempt(4, "verification", cpu=1))
        with self.assertRaisesRegex(ValueError, "only cleanup can follow a recorded cap breach"):
            audit.verify(**self.freeze())
        row["attempts"][-1]["role"] = "cleanup"
        result = audit.verify(**self.freeze())
        self.assertEqual(result["arm_resource_receipts"]["combined"]["known_usage"]["cpu_wall_ns"], 12)

    def test_unresolved_attempt_blocks_later_noncleanup_across_blocks(self):
        f = self.fixture
        second = self.block | {"block_id": "paired-second", "condition": "disrupted"}
        self.inputs["task_manifest_sha256"] = f.artifact("tasks.json", {"blocks": [self.block, second]})
        f.manifest["inputs"]["task_manifest_sha256"] = self.inputs["task_manifest_sha256"]["sha256"]
        for row in self.rows:
            row["inputs"] = f.manifest["inputs"].copy()
        self.rows.extend(copy.deepcopy(row) | {"block_id": second["block_id"], "condition": second["condition"]}
                         for row in self.rows[:2])
        self.rows[1]["terminal"] = "stopped"
        self.rows[1]["attempts"].append(self.attempt(3, "verification", status="failed") | {"usage": None})
        with self.assertRaisesRegex(ValueError, "only cleanup can follow unresolved usage"):
            audit.verify(**self.freeze())
        self.rows[-1]["attempts"] = [self.attempt(0, "cleanup", cpu=1)]
        self.rows[-1]["terminal"] = "stopped"
        result = audit.verify(**self.freeze())
        self.assertEqual(result["complete_pairs"], 0)
        self.assertEqual(result["arm_resource_receipts"]["combined"]["unknown_usage_attempts"], 1)

    def test_mismatched_observed_input_and_stale_source_are_refused(self):
        common_hashes = self.rows[0]["inputs"]
        common_hashes["protocol_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "observed arm inputs differ"):
            audit.verify(**self.freeze())
        common_hashes["protocol_sha256"] = self.fixture.manifest["inputs"]["protocol_sha256"]
        (self.fixture.bundle / "protocol.txt").write_bytes(b"replacement")
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            audit.verify(**self.freeze())

    def test_per_call_cap_refuses_even_when_aggregate_fits(self):
        arm = self.rows[0]
        arm["attempts"].append(self.attempt(3, "verification", calls=1, tokens=4))
        for declaration in self.fixture.manifest["arms"].values():
            declaration["budget"]["per_call_input_tokens"] = 3
        with self.assertRaisesRegex(ValueError, "exceeded a cap"):
            audit.verify(**self.freeze())

    def test_cached_input_counts_toward_the_per_call_cap(self):
        attempt = self.attempt(3, "verification", calls=1, tokens=1)
        attempt["usage"]["cache_read_tokens"] = 3
        self.rows[0]["attempts"].append(attempt)
        for declaration in self.fixture.manifest["arms"].values():
            declaration["budget"]["per_call_input_tokens"] = 3
        with self.assertRaisesRegex(ValueError, "exceeded a cap"):
            audit.verify(**self.freeze())

    def test_completed_block_cannot_hide_an_aggregate_cap_breach(self):
        f = self.fixture
        second = self.block | {"block_id": "paired-second", "condition": "disrupted",
                               "order": ["combined", "plain"]}
        self.inputs["task_manifest_sha256"] = f.artifact("tasks.json", {"blocks": [self.block, second]})
        f.manifest["inputs"]["task_manifest_sha256"] = self.inputs["task_manifest_sha256"]["sha256"]
        for arm in f.manifest["arms"].values():
            arm["budget"]["cpu_wall_ns"] = 10
        for row in self.rows:
            row["inputs"] = f.manifest["inputs"].copy()
        self.rows.extend(copy.deepcopy(row) | {"block_id": second["block_id"], "condition": second["condition"]}
                         for row in reversed(self.rows[:2]))
        with self.assertRaisesRegex(ValueError, "cap across matched blocks"):
            audit.verify(**self.freeze())
        for row in self.rows[2:]:
            row["terminal"] = "stopped"
        result = audit.verify(**self.freeze())
        self.assertEqual(result["complete_pairs"], 1)
        self.assertEqual(result["arm_resource_receipts"]["combined"]["exceeded_caps"], ["cpu_wall_ns"])

    def test_renamed_assignment_is_refused_at_its_fresh_pins_even_when_reordered(self):
        original_arms = copy.deepcopy(self.rows)
        f = self.fixture
        for reorder in (False, True):
            with self.subTest(reorder=reorder):
                alias = copy.deepcopy(self.block)
                alias["block_id"] = "renamed"
                alias_arms = copy.deepcopy(original_arms)
                if reorder:
                    alias["order"].reverse()
                    alias["taskset"]["tasks"].reverse()
                    alias_arms.reverse()
                for row in alias_arms:
                    row["block_id"] = alias["block_id"]
                self.inputs["task_manifest_sha256"] = f.artifact("tasks.json", {"blocks": [self.block, alias]})
                f.manifest["inputs"]["task_manifest_sha256"] = self.inputs["task_manifest_sha256"]["sha256"]
                self.rows = original_arms + alias_arms
                for row in self.rows:
                    row["inputs"] = f.manifest["inputs"].copy()
                with self.assertRaisesRegex(ValueError, "duplicate experimental task assignment"):
                    audit.verify(**self.freeze())

    def test_cli_checks_archival_pin_before_replay(self):
        fixture = self.freeze()
        command = [sys.executable, "-B", "-m", "lab.controller_pair_audit",
                   *[str(fixture[key]) for key in ("bundle", "manifest", "evidence_index", "trace")],
                   "--manifest-sha256", fixture["manifest_sha256"],
                   "--evidence-index-sha256", fixture["evidence_index_sha256"],
                   "--trace-sha256", fixture["trace_sha256"]]
        valid = subprocess.run(command, capture_output=True, text=True, timeout=10, check=True)
        self.assertEqual(json.loads(valid.stdout)["complete_pairs"], 1)
        command[-1] = "0" * 64
        refused = subprocess.run(command, capture_output=True, text=True, timeout=10, check=False)
        self.assertEqual(refused.returncode, 2)
        self.assertIn("digest mismatch: trace.json", refused.stderr)
