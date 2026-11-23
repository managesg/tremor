from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lab import ep1_b4_wire_audit as audit


class WireReceiptAuditTests(unittest.TestCase):
    def setUp(self):
        self.first = "episode:r0:a0"
        self.hash = "a" * 64
        usage = {"input_tokens": 2000, "output_tokens": 300, "cache_read_input_tokens": 0,
                 "cache_creation_input_tokens": 0}
        self.first_request = {"sequence": 0, "batch": "ep1", "bytes": 2000, "sha256": self.hash, "status": 503,
                              "usage": None}
        self.retry_request = self.first_request | {"sequence": 1, "status": 200, "usage": usage.copy()}
        reserve = {"kind": "reserve", "id": self.first, "batch": "ep1", "input_tokens_ub": 2000,
                   "model": "fixture", "max_tokens": 300, "worst_usd": 0.0004}
        self.ledger = [
            reserve,
            {"kind": "unbilled_unknown", "id": self.first, "error": "HTTP 503 FAKE"},
            reserve | {"id": self.first + "#r1"},
            {"kind": "charge", "id": self.first + "#r1", "request_sha256": self.hash, "request_bytes": 2000,
             "requested_model": "fixture", "usage": usage,
             "usd": 0.0002},
            {"kind": "batch_stop", "batch": "ep1", "reason": "inconclusive"},
        ]

    def test_replays_distinct_wire_attempts_and_unknown_reservation(self):
        result = audit._wire_batch(self.ledger, [self.first_request, self.retry_request], "ep1", 2000)
        self.assertEqual(result["calls"], [self.first, self.first + "#r1"])
        self.assertEqual(result["unmetered"], [self.first])
        self.assertEqual(result["charged"], [self.first + "#r1"])
        self.assertEqual(str(result["usd"]), "0.0006")

    def test_retry_must_carry_exact_original_bytes_even_if_it_matches_its_own_charge(self):
        other = "b" * 64
        self.ledger[3]["request_sha256"] = other
        with self.assertRaisesRegex(ValueError, "retry changed parent"):
            audit._wire_batch(self.ledger, [self.first_request, self.retry_request | {"sha256": other}], "ep1", 2000)

    def test_request_receipt_cannot_hide_a_wrong_meter_or_reservation_identity(self):
        self.ledger[3]["request_bytes"] -= 1
        with self.assertRaisesRegex(ValueError, "charged usage or request"):
            audit._wire_batch(self.ledger, [self.first_request, self.retry_request], "ep1", 2000)
        self.ledger[3]["id"] = self.first
        with self.assertRaisesRegex(ValueError, "unique reservation"):
            audit._wire_batch(self.ledger, [self.first_request, self.retry_request], "ep1", 2000)

    def test_refuses_a_changed_external_seal_before_reading_artifacts(self):
        with TemporaryDirectory() as scratch:
            path = Path(scratch)
            (path / "seal.json").write_text("{}")
            with self.assertRaisesRegex(ValueError, "external FAKE archive seal mismatch"):
                audit.audit(path, seal_sha256="0" * 64)

    def test_refuses_a_charge_that_differs_from_observed_response_usage(self):
        self.retry_request["usage"]["cache_read_input_tokens"] = 1
        with self.assertRaisesRegex(ValueError, "charged usage or request"):
            audit._wire_batch(self.ledger, [self.first_request, self.retry_request], "ep1", 2000)

    def test_ledger_identity_must_equal_the_actual_turn_even_if_counts_match(self):
        row = {"turns": [{"call_id": self.first}], "calls": 1, "tokens": {"input": 2000, "output": 300},
               "ended": "infrastructure_abort"}
        audit._episode_meter(row, [self.first, self.first + "#r1"], {self.first + "#r1"})
        wrong = "episode:r0:unobserved"
        with self.assertRaisesRegex(ValueError, "ledger call identities differ"):
            audit._episode_meter(row, [wrong, wrong + "#r1"], {wrong + "#r1"})

    def test_invalid_or_void_scored_episode_cannot_count_as_complete(self):
        calls = [f"e:r0:a{i}" for i in range(8)]
        row = {"turns": [{"call_id": call} for call in calls], "calls": 8, "tokens": {"input": 16000, "output": 2400},
               "ended": "complete", "valid": True, "void": None, "Y": 0.25,
               "scorers": {"alloc": {"Y": 0.25}, "alloc2": {"Y": 0.25}, "disagreement": None,
                           "third": {"status": "OK"}}}
        audit._episode_meter(row, calls, set(calls))
        with self.assertRaisesRegex(ValueError, "invalid completed FAKE"):
            audit._episode_meter(row | {"valid": False, "void": "fixture fault"}, calls, set(calls))
