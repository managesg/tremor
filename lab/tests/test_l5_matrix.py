import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from lab.l5_matrix import CARRIERS, run
from tremor.board import read_log


class L5MatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = Path(cls.enterClassContext(TemporaryDirectory())) / "evidence"
        cls.report = run(cls.output, seed=86)

    def test_matches_all_arms_within_each_size(self):
        ordered = [(block["block_id"], condition) for block in self.report["schedule"]["blocks"]
                   for condition in block["order"]]
        self.assertEqual(ordered, [(row["block_id"], row["condition"]) for row in self.report["rows"]])
        for size in (4, 8):
            rows = [row for row in self.report["rows"] if row["block_id"] == f"team-{size}"]
            self.assertEqual({(row["carrier"], row["disrupted"]) for row in rows},
                             {(carrier, disrupted) for carrier in CARRIERS for disrupted in (False, True)})
            neutral = next(row for row in rows if row["condition"] == "neutral:clean")
            common = [event["action"] for event in neutral["dispatch"] if event["action"]["type"] == "work"]
            for row in rows:
                self.assertEqual(row["taskset"], neutral["taskset"])
                self.assertEqual(row["score"]["slots"], size)
                attempted = [event["action"] for event in row["dispatch"] if event["action"]["type"] == "work"]
                self.assertEqual(attempted, common)
                self.assertEqual(len({action["agent"] for action in attempted}), size)

    def test_intervention_and_recovery_use_committed_state(self):
        for row in self.report["rows"]:
            trace = read_log(self.output / row["arm_id"] / "board.jsonl")
            self.assertEqual((trace[-1]["hash"], len(trace)), (row["board_head"], row["board_event_count"]))
            self.assertEqual(sum(entry["type"] == "release" for entry in trace), int(row["disrupted"]))
            self.assertEqual(row["perturbation_applied"], row["disrupted"])
            self.assertEqual(row["executed_norm_violations"], int(row["condition"] == "neutral:disrupted"))
            refusal = int(row["condition"] == "code:disrupted")
            self.assertEqual(row["score"]["distinct_passing"], row["attempted_work"] - refusal)
            self.assertEqual(row["blocked_legitimate_work"], 0)

    def test_named_reads_match_committed_worker_delivery(self):
        for row in self.report["rows"]:
            self.assertEqual(len(row["exposure"]), 2 * row["attempted_work"])
            path = self.output / row["arm_id"] / "delivery.jsonl"
            named = row["carrier"] in ("memory", "environment")
            self.assertEqual(path.exists(), named)
            seen = row["carrier"] in ("context", "memory", "environment")
            self.assertTrue(all(receipt["guide_consumed"] == seen for receipt in row["exposure"]))
            if not named:
                continue
            trace = read_log(path)
            self.assertEqual(row["delivery_board"], {"head": trace[-1]["hash"], "event_count": len(trace)})
            posts = {event["data"]["id"]: event for event in trace if event["type"] == "post"}
            reads = [event for event in trace if event["type"] == "read"]
            for receipt, event in zip(row["exposure"], reads, strict=True):
                post = posts[receipt["item"]]
                self.assertEqual((receipt["worker"], receipt["delivery_round"]), (event["agent"], event["round"]))
                self.assertEqual(event["data"], {"item": receipt["item"], "n": 1})
                self.assertEqual(event["seq"], receipt["read_event_seq"])
                self.assertLess(post["round"], event["round"])
                scope = "shared" if row["carrier"] == "memory" else event["agent"]
                self.assertEqual(post["data"]["refs"], [scope])

    def test_refuses_overwriting_evidence(self):
        before = (self.output / "arm-00" / "result.json").read_bytes()
        with self.assertRaises(FileExistsError):
            run(self.output, seed=87)
        self.assertEqual((self.output / "arm-00" / "result.json").read_bytes(), before)

    def test_persisted_plan_and_each_result_match_completion_index(self):
        self.assertEqual(json.loads((self.output / "summary.json").read_bytes()), self.report)
        self.assertEqual(hashlib.sha256((self.output / "plan.json").read_bytes()).hexdigest(),
                         self.report["plan_sha256"])
        for row in self.report["rows"]:
            raw = (self.output / row["arm_id"] / "result.json").read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), row["result_sha256"])

    def test_failure_retains_the_plan_and_started_arm(self):
        with TemporaryDirectory() as scratch:
            path = Path(scratch) / "failure"
            with patch("lab.l5_matrix._arm", side_effect=RuntimeError("scripted interruption")):
                with self.assertRaisesRegex(RuntimeError, "scripted interruption"):
                    run(path, seed=86)
            self.assertTrue((path / "plan.json").is_file())
            self.assertTrue((path / "arm-00" / "intent.json").is_file())
            self.assertEqual(json.loads((path / "arm-00" / "failure.json").read_bytes()),
                             {"error_type": "RuntimeError"})
            self.assertFalse((path / "summary.json").exists())
