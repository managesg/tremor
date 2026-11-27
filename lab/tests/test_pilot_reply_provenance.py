import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from lab import pilot_reply_provenance
from tremor import ep1


class PilotReplyProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path(self.enterContext(TemporaryDirectory()))
        self.ledger_path = self.directory / "pilot3.jsonl"
        self.usage = {"input_tokens": 10, "output_tokens": 151, "cache_creation_input_tokens": 0,
                      "cache_read_input_tokens": 0}
        self.turn = {
            "call_id": "episode:r1:a0", "round": 1, "reply": 'Explanation. [{"type":"pass"}]',
            "usage": self.usage, "stop_reason": "end_turn", "returned_model": ep1.MODEL,
            "block_types": ["text"], "usd": 0.01,
        }
        self.response_sha = hashlib.sha256(self.turn["reply"].encode()).hexdigest()
        self.enterContext(patch("lab.pilot_clearance._validate_episodes", side_effect=self.validated_turns))

    @staticmethod
    def validated_turns(schedule, rows):
        # The historical archive audit separately covers complete episode validation.
        return [turn for episode in rows for turn in episode["turns"]]

    def audit(self, *, response_sha=None):
        ledger = [
            {"kind": "batch_open"},
            {"kind": "reserve", "id": self.turn["call_id"]},
            {"kind": "charge", "id": self.turn["call_id"], "usage": self.usage, "usd": self.turn["usd"],
             "stop_reason": self.turn["stop_reason"], "returned_model": ep1.MODEL, "void": None,
             "usage_invalid": None, "response_sha256": response_sha or self.response_sha},
            {"kind": "batch_stop", "reason": "complete"},
        ]
        final = {
            "kind": "pilot3", "reason": "complete", "aborts": 0, "episodes": 1,
            "voids": dict.fromkeys(ep1.BASE_CONDS + tuple(ep1.PILOT_CARDS), 0),
            "ledger": {"batch": "pilot3", "stop_reason": "complete", "calls": 1, "tokens": 161,
                       "tokens_by_class": {"input": 10, "output": 151, "cache_creation": 0,
                                           "cache_read": 0, "unmetered_worst": 0}, "usd": 0.01},
        }
        (self.directory / "schedule.json").write_text("{}")
        (self.directory / "episodes.jsonl").write_text(json.dumps({"cond": "none", "turns": [self.turn]}) + "\n")
        (self.directory / "final.json").write_text(json.dumps(final))
        self.ledger_path.write_text("".join(json.dumps({**row, "batch": "pilot3"}) + "\n" for row in ledger))
        return pilot_reply_provenance.audit(self.directory, self.ledger_path)

    def test_only_reconciled_reply_reaches_diagnostics(self):
        report = self.audit()
        self.assertEqual(report["response_sha256_matches"], 1)
        self.assertEqual(report["source_sha256"]["ledger"], hashlib.sha256(self.ledger_path.read_bytes()).hexdigest())
        core = report["diagnostics"]["core"]
        self.assertEqual(core["above_ceiling_call_ids"], [self.turn["call_id"]])
        self.assertEqual(core["second_round_non_array_call_ids"], [self.turn["call_id"]])
        self.assertEqual(core["max_tokens_stop_call_ids"], [])

    def test_mismatched_charge_hash_cannot_reach_diagnostic(self):
        with self.assertRaisesRegex(ValueError, "ledger disagrees"):
            self.audit(response_sha="0" * 64)

    def test_non_text_block_cannot_be_described_as_a_complete_reply(self):
        self.turn["block_types"].append("thinking")
        with self.assertRaisesRegex(ValueError, "non-text provider blocks"):
            self.audit()
