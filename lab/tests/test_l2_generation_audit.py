import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lab.l2_generation_audit import audit
from lab.r3_l2_generation import run
from lab.spark_decision import Generation


def render(worker, instruction, source_id, source_text, *, verification):
    return json.dumps({"worker": worker, "source_id": source_id, "verification": verification})


class GenerationAuditTests(unittest.TestCase):
    def setUp(self):
        root = Path(self.enterContext(TemporaryDirectory()))
        self.board = root / "board.jsonl"
        self.journal = self.board.with_suffix(".generation.jsonl")

    def execute(self, *, fail=False, condition="warning"):
        def generate(prompt, **caps):
            fields = json.loads(prompt)
            if fields["worker"] == "b" and fail:
                raise RuntimeError("test fault")
            if fields["worker"] == "a" and fields["verification"] is None:
                proposal = {"action": "verify"}
            else:
                proposal = {"value": "green", "source_id": fields["source_id"]}
            return Generation(json.dumps(proposal), 18, 8, 100, False)

        return run(self.board, condition, generate=generate, render=render, max_input_tokens=40,
                   max_output_tokens=10, accept_at_limit=False, reference_text="Paper ledger marker: green")

    def rows(self):
        return [json.loads(row) for row in self.journal.read_text().splitlines()]

    def write_rows(self, rows):
        self.journal.write_text("\n".join(map(json.dumps, rows)) + "\n")

    def test_matches_real_fixture_and_external_digest(self):
        run_report = self.execute()
        digest = hashlib.sha256(self.journal.read_bytes()).hexdigest()
        result = audit(self.board, self.journal, expected_journal_sha256=digest)
        self.assertEqual((result["status"], result["completed_generations"], result["reference_reads"]), ("completed", 3, 1))
        self.assertEqual((result["input_tokens_known"], result["output_tokens_known"]),
                         (run_report["input_tokens"], run_report["output_tokens"]))
        with self.assertRaisesRegex(ValueError, "journal digest mismatch"):
            audit(self.board, self.journal, expected_journal_sha256="0" * 64)
        with self.assertRaisesRegex(ValueError, "external board head mismatch"):
            audit(self.board, self.journal, expected_board_head="0" * 64)

    def test_unknown_usage_survives_interruption(self):
        with self.assertRaisesRegex(RuntimeError, "test fault"):
            self.execute(fail=True)
        for rows in (self.rows(), self.rows()[:-1]):
            self.write_rows(rows)
            result = audit(self.board, self.journal)
            self.assertEqual((result["status"], result["completed_generations"], result["unknown_usage_attempts"]),
                             ("incomplete", 2, 1))
            self.assertEqual(result["output_tokens_known"], 16)

    def test_rejects_wrong_board_head_reference_digest_or_missing_worker(self):
        self.execute()
        original = self.rows()
        mutations = ((len(original) - 1, "board_head", "0" * 64, "final board"),
                     (3, "reference_sha256", "0" * 64, "reference receipt mismatch"))
        for index, field, value, message in mutations:
            with self.subTest(field=field):
                rows = [row.copy() for row in original]
                rows[index][field] = value
                self.write_rows(rows)
                with self.assertRaisesRegex(ValueError, message):
                    audit(self.board, self.journal)
        self.write_rows([row for row in original if row.get("worker") != "b"])
        with self.assertRaisesRegex(ValueError, "missing an initial generation"):
            audit(self.board, self.journal)

    def test_a_pinned_partial_journal_rejects_a_board_with_other_instruction_bytes(self):
        with self.assertRaises(RuntimeError):
            self.execute(fail=True)
        warning_journal = self.journal
        pin = hashlib.sha256(warning_journal.read_bytes()).hexdigest()
        self.board = self.board.with_name("neutral.jsonl")
        self.execute(condition="neutral")
        with self.assertRaisesRegex(ValueError, "generation instruction"):
            audit(self.board, warning_journal, expected_journal_sha256=pin)
