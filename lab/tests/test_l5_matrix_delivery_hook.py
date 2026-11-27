from collections import Counter
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lab import l5_matrix
from tremor.board import read_log
from tremor.team import view_of


class L5MatrixDeliveryHookTests(unittest.TestCase):
    def setUp(self):
        self.scratch = Path(self.enterContext(TemporaryDirectory()))

    @staticmethod
    def acknowledge(guide):
        return hashlib.sha256(guide.encode()).hexdigest() if guide is not None else None

    def test_default_matrix_and_acknowledged_hook_preserve_the_same_results(self):
        plain, verified = self.scratch / "plain", self.scratch / "verified"
        legacy = l5_matrix.run(plain, seed=86)
        self.assertEqual(len(legacy["rows"]), 20)
        expected_fields = {"block_id", "condition", "arm_id", "worker", "phase", "item", "delivery_read_seq",
                           "delivery_read_sha256", "board_head", "board_event_count", "guide_sha256"}
        counts = Counter()
        target_boundary = []

        def verify(frame, guide):
            self.assertEqual(set(frame), expected_fields)
            counts[frame["block_id"], frame["condition"], frame["phase"]] += 1
            arm = verified / frame["arm_id"]
            board_path = arm / "board.jsonl"
            board = read_log(board_path)
            self.assertEqual((frame["board_head"], frame["board_event_count"]), (board[-1]["hash"], len(board)))
            identity = json.loads((arm / "intent.json").read_bytes())
            self.assertEqual(identity, {key: frame[key] for key in identity})
            self.assertEqual(frame["guide_sha256"], self.acknowledge(guide))
            if frame["condition"].startswith("environment:"):
                self.assertEqual(guide, l5_matrix.GUIDE)
                raw = (arm / "delivery.jsonl").read_bytes().splitlines(keepends=True)[-1]
                event = json.loads(raw)
                self.assertEqual(frame["delivery_read_seq"], event["seq"])
                self.assertEqual(frame["delivery_read_sha256"], hashlib.sha256(raw).hexdigest())
                self.assertEqual((event["type"], event["agent"], event["data"]),
                                 ("read", frame["worker"], {"item": frame["item"], "n": 1}))
            else:
                self.assertIsNone(guide)
                for key in ("item", "delivery_read_seq", "delivery_read_sha256"):
                    self.assertIsNone(frame[key])
            if (frame["condition"], frame["phase"], frame["worker"]) == ("environment:disrupted", "post", "a1"):
                released = next(event for event in board if event["type"] == "release" and event["agent"] == "a1")
                task = released["data"]["item"]
                self.assertNotIn(task, view_of(board_path)["claims"])
                target_boundary.append((frame["arm_id"], task))
            return self.acknowledge(guide)

        output = l5_matrix.run(verified, seed=86, verify_delivery=verify)
        self.assertEqual(output, legacy)
        self.assertEqual((verified / "summary.json").read_bytes(), (plain / "summary.json").read_bytes())
        self.assertEqual(sum(counts.values()), 96)
        self.assertEqual(counts, Counter({
            (f"team-{size}", f"{carrier}:{condition}", phase): size
            for size in (4, 8) for carrier in ("environment", "neutral")
            for condition in ("clean", "disrupted") for phase in ("pre", "post")
        }))
        self.assertEqual(len(target_boundary), 2)
        by_arm = {row["arm_id"]: row for row in output["rows"]}
        for arm_id, task in target_boundary:
            arm = by_arm[arm_id]
            self.assertEqual(arm["perturbed_task"], task)
            self.assertEqual(arm["executed_norm_violations"], 0)
            self.assertTrue(any(event["phase"] == "recovery" and event["action"]["type"] == "claim"
                                and event["action"]["item"] == task for event in arm["dispatch"]))
        neutral = [row for row in output["rows"] if row["condition"] == "neutral:disrupted"]
        self.assertEqual([row["executed_norm_violations"] for row in neutral], [1, 1])

    def test_wrong_withheld_and_stale_acknowledgment_abort_before_recovery(self):
        prior = self.acknowledge("claim after work")
        for name, reply in (("wrong", "0" * 64), ("withheld", None), ("stale", prior)):
            with self.subTest(name=name):
                root = self.scratch / name
                rejected = []

                def verify(frame, guide):
                    if (frame["condition"], frame["phase"], frame["worker"]) == (
                        "environment:disrupted", "post", "a1"
                    ):
                        self.assertEqual(guide, l5_matrix.GUIDE)
                        rejected.append(frame["arm_id"])
                        return reply
                    return self.acknowledge(guide)

                with self.assertRaisesRegex(ValueError, "delivery verification did not acknowledge the actual guide"):
                    l5_matrix.run(root, seed=86, verify_delivery=verify)
                self.assertEqual(len(rejected), 1)
                arm = root / rejected[0]
                board_path = arm / "board.jsonl"
                board = read_log(board_path)
                release = next(index for index, event in enumerate(board) if event["type"] == "release")
                self.assertEqual(board[release]["agent"], "a1")
                self.assertNotIn(board[release]["data"]["item"], view_of(board_path)["claims"])
                self.assertFalse(any(event["type"] == "claim" and event["agent"] == "a1"
                                     for event in board[release + 1:]))
                self.assertEqual(json.loads((arm / "failure.json").read_bytes()), {"error_type": "ValueError"})
                self.assertFalse((arm / "result.json").exists())
                self.assertFalse((root / "summary.json").exists())
