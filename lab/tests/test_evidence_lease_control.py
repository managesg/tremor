import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from lab.evidence_lease_control import SCOPE, compare, eligible_support
from tremor.board import Board


class EvidenceLeaseTests(unittest.TestCase):
    def test_distinct_receipts_unblock_and_record_each_close_reason(self):
        run = compare()["distinct"]
        events = run["policy_events"]
        self.assertEqual([event["round"] for event in events if event["event"] == "lease_opened"],
                         [2, 5, 6])
        self.assertEqual([(event["round"], event["reason"]) for event in events
                          if event["event"] == "lease_closed"],
                         [(4, "idle_expired"), (5, "observed_violation"), (7, "provenance_withdrawn")])
        self.assertEqual([event["granted"] for event in events if event["event"] == "action"],
                         [False, True, False, True, False, True, False, False])
        self.assertEqual(run["accounting"], {
            "requested": 8, "allowed": 3, "blocked": 5, "blocked_legitimate": 4,
            "executed_standin_violations": 1, "unused_grant_rounds": 1,
        })

    def test_duplicate_source_receipts_never_open(self):
        run = compare()["duplicate-source"]
        self.assertFalse(any(event["event"] == "lease_opened" for event in run["policy_events"]))
        self.assertEqual(run["accounting"], {
            "requested": 8, "allowed": 0, "blocked": 8, "blocked_legitimate": 6,
            "executed_standin_violations": 0, "unused_grant_rounds": 0,
        })

    def test_evidence_must_be_committed_prior_trusted_and_same_scope(self):
        with TemporaryDirectory() as scratch:
            board = Board(Path(scratch) / "board.jsonl", seed=6)
            source = board.post("observer", "A", kind="observation", facts=[SCOPE])
            wrong_scope = board.post("observer", "B", kind="observation", facts=["other"])
            board.post("auditor", "in same round", kind="verification", refs=[source], facts=[SCOPE])
            board.end_round()
            board.post("worker", "wrong author", kind="verification", refs=[source], facts=[SCOPE])
            board.post("auditor", "wrong scope", kind="verification", refs=[wrong_scope], facts=[SCOPE])
            receipt = board.post("auditor", "valid", kind="verification", refs=[source], facts=[SCOPE])
            self.assertEqual(eligible_support(board, SCOPE, 0), {})
            board.end_round()
            self.assertEqual(eligible_support(board, SCOPE, 0), {source: receipt})
            self.assertEqual(eligible_support(board, SCOPE, 2), {})
