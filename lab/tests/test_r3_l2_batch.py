import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock

from lab import l2_generation_audit, r3_l2_batch, r3_l2_generation


class L2BatchTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.output = self.root / "evidence"
        source = self.write("paper.txt", b"Paper ledger marker: green")
        references = {"references": {"case": {"path": "paper.txt", "sha256": source}}}
        truth = {"markers": {"case": "green"}}
        self.batch = {
            "purpose": "scripted_l2_warning", "conditions": ["warning", "neutral"], "seed": 17,
            "blocks": [{"block_id": f"block-{i}", "case_id": "case", "stratum": "fixture"} for i in range(2)],
            "limits": {"max_input_tokens": 60, "max_output_tokens": 12, "accept_at_limit": False},
            "custody": {"manifest": "references.json", "manifest_sha256": self.write("references.json", references),
                        "truth_inventory": "truth.json", "truth_sha256": self.write("truth.json", truth)},
        }

    def write(self, path, data):
        raw = data if isinstance(data, bytes) else json.dumps(data, sort_keys=True).encode()
        (self.root / path).write_bytes(raw)
        return hashlib.sha256(raw).hexdigest()

    def execute(self, generate=r3_l2_batch._scripted_generate, *, override_pin=None):
        pin = self.write("batch.json", self.batch)
        return r3_l2_batch.run(self.root, self.root / "batch.json", self.output,
                               batch_sha256=pin if override_pin is None else override_pin, generate=generate)

    def test_runs_matched_schedule_with_shared_reference_and_replayable_receipts(self):
        result = self.execute()
        self.assertEqual((result["status"], result["attempted_arms"], result["planned_arms"]), ("completed", 4, 4))
        self.assertEqual([pair["warning_minus_neutral"] for pair in result["scored_pairs"]], [0, 0])
        self.assertEqual(len({arm["reference_sha256"] for arm in result["arms"]}), 1)
        batch_journal = [json.loads(row) for row in (self.output / "batch.jsonl").read_text().splitlines()]
        order = [(block["block_id"], condition) for block in batch_journal[0]["schedule"]["blocks"]
                 for condition in block["order"]]
        self.assertEqual([(arm["block_id"], arm["condition"]) for arm in result["arms"]], order)
        for arm in result["arms"]:
            board = self.output / (arm["arm"] + ".jsonl")
            meter = arm["meter"]
            reviewed = l2_generation_audit.audit(board, board.with_suffix(".generation.jsonl"),
                                                   expected_journal_sha256=meter["journal_sha256"],
                                                   expected_board_head=meter["board_head"], renderer=l2_generation_audit.render_scripted_prompt)
            self.assertEqual(reviewed, meter)
            self.assertEqual((arm["exposures"], arm["adoptions"], meter["reference_reads"]), (2, 1, 1))
        before = (self.output / "batch.jsonl").read_bytes()
        with self.assertRaises(FileExistsError):
            self.execute()
        self.assertEqual((self.output / "batch.jsonl").read_bytes(), before)

    def test_rejects_changed_manifest_or_reference_before_asking_for_decisions(self):
        generate = Mock(side_effect=AssertionError("called too early"))
        with self.assertRaisesRegex(ValueError, "batch manifest digest mismatch"):
            self.execute(generate, override_pin="0" * 64)
        self.write("paper.txt", b"Paper ledger marker: blue")
        with self.assertRaisesRegex(ValueError, "reference source digest mismatch"):
            self.execute(generate)
        self.assertFalse(self.output.exists())
        generate.assert_not_called()

    def test_failure_keeps_prior_arm_and_unknown_usage_without_counting_as_a_pair(self):
        count = 0

        def fail_during_second_arm(prompt, **caps):
            nonlocal count
            count += 1
            if count == 5:
                raise RuntimeError("scripted driver failure")
            return r3_l2_batch._scripted_generate(prompt, **caps)

        result = self.execute(fail_during_second_arm)
        self.assertEqual((result["status"], result["attempted_arms"], result["scored_pairs"]), ("failed", 2, []))
        complete, failed = result["arms"]
        self.assertEqual(complete["meter"]["completed_generations"], 3)
        self.assertEqual((failed["meter"]["completed_generations"], failed["meter"]["unknown_usage_attempts"]), (1, 1))
        self.assertTrue((self.output / "arm-1.generation.jsonl").is_file())
        self.assertFalse((self.output / "arm-2.jsonl").exists())

    def test_rerender_rejects_a_complete_journal_that_leaked_reference_at_initial_turn(self):
        board = self.root / "altered.jsonl"

        def altered_renderer(*observed, verification):
            if verification is None:
                verification = {"id": "invented", "text": "Paper ledger marker: green"}
            return l2_generation_audit.render_scripted_prompt(*observed, verification=verification)

        r3_l2_generation.run(board, "warning", generate=r3_l2_batch._scripted_generate, render=altered_renderer,
                             reference_text="Paper ledger marker: green", **self.batch["limits"])
        journal = board.with_suffix(".generation.jsonl")
        receipt = l2_generation_audit.audit(board, journal)
        self.assertEqual(receipt["status"], "completed")
        result = subprocess.run([sys.executable, "-m", "lab.l2_generation_audit", str(board), str(journal),
                                 "--strict-scripted", "--journal-sha256", receipt["journal_sha256"],
                                 "--board-head", receipt["board_head"]], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("prompt differs from renderer", result.stderr)
