import json
import unittest

from lab import l2_generation_audit, r3_l2_generation
from lab.tests import test_r3_l2_archive as fixture


class ArchiveIdentityTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture.ArchiveTests()
        self.fixture.setUp()
        self.out = self.fixture.out
        self.index = self.fixture.run_archive()["index"]

    def neutral_arms(self, index):
        return {arm["block_id"]: arm for arm in index["arms"] if arm["condition"] == "neutral"}

    def assert_refuses_swap(self, expected, candidate, candidate_out):
        self.assertEqual(expected["board_head"], candidate["board_head"])
        with self.assertRaisesRegex(ValueError, "generation receipt identity mismatch"):
            l2_generation_audit.audit(
                self.out / expected["board"], candidate_out / candidate["journal"],
                expected_board_head=expected["board_head"], expected_identity=expected["identity"],
                renderer=fixture.render,
            )

    def test_same_condition_in_another_block_cannot_replace_receipt(self):
        expected, candidate = self.neutral_arms(self.index).values()
        self.assertNotEqual(expected["block_id"], candidate["block_id"])
        self.assert_refuses_swap(expected, candidate, self.out)

    def test_same_schedule_in_another_archive_cannot_replace_receipt(self):
        other_out = self.fixture.scratch / "another-archive"
        self.fixture.out = other_out
        other = self.fixture.run_archive()["index"]

        self.assertEqual(self.index["schedule_sha256"], other["schedule_sha256"])
        self.assertNotEqual(self.index["archive_id"], other["archive_id"])
        expected = self.neutral_arms(self.index)["one"]
        candidate = self.neutral_arms(other)["one"]
        self.assertEqual(expected["arm_position"], candidate["arm_position"])
        self.assert_refuses_swap(expected, candidate, other_out)

    def test_legacy_receipt_audits_without_an_identity_but_cannot_supply_one(self):
        board = self.fixture.scratch / "legacy.jsonl"
        journal = board.with_suffix(".generation.jsonl")
        r3_l2_generation.run(
            board, "neutral", generate=fixture.generate, render=fixture.render,
            max_input_tokens=40, max_output_tokens=10, accept_at_limit=False,
            reference_text="Paper ledger marker: green",
        )
        header = json.loads(journal.read_text().splitlines()[0])
        self.assertNotIn("identity", header)
        result = l2_generation_audit.audit(board, journal, renderer=fixture.render)
        self.assertEqual(result["status"], "completed")
        self.assertNotIn("identity", result)

        expected = self.neutral_arms(self.index)["one"]
        self.assertEqual(expected["board_head"], result["board_head"])
        with self.assertRaisesRegex(ValueError, "generation receipt identity mismatch"):
            l2_generation_audit.audit(
                board, journal, expected_identity=expected["identity"], renderer=fixture.render,
            )
