"""Regression checks for the offline Pilot 4 review boundary."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from lab import pilot4_preflight_manifest as manifest


class Pilot4ManifestTests(unittest.TestCase):
    def test_pending_manifest_replays_without_sockets_and_keeps_a_distinct_batch(self):
        with patch("socket.socket", side_effect=AssertionError("unexpected socket")):
            result = manifest.build_manifest()

        identifiers = {
            identifier
            for episode in result["schedule"]
            for identifier in (episode["episode_id"], *episode["call_ids"])
        }
        self.assertEqual(result["status"], "awaiting_review")
        self.assertIsNone(result["selected_candidate"])
        self.assertIs(result["execution_authorized_by_manifest"], False)
        self.assertEqual((result["episode_count"], len(identifiers)), (30, 270))
        self.assertTrue(all(identifier.startswith("ep1p4") for identifier in identifiers))
        reservation = result["reservation"]
        self.assertEqual(
            (reservation["planned_calls"], reservation["max_attempts"], reservation["max_reserved_tokens"]),
            (240, 260, 598_000),
        )
        self.assertEqual(reservation["pricing_review_status"], "pending")
        self.assertEqual(set(result["wording_candidate_replays"]), {"packet", "array_only"})

    def test_modified_price_sheet_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            price_sheet = Path(directory) / "price-sheet.json"
            price_sheet.write_bytes(manifest.PRICE_SHEET.read_bytes() + b"\n")
            with self.assertRaisesRegex(ValueError, "historical input digest mismatch"):
                manifest.build_manifest(price_sheet=price_sheet)

    def test_modified_candidate_request_digest_fails_closed(self):
        with patch.dict(manifest.CANDIDATE_REQUEST_SHA256, {"packet": "0" * 64}):
            with self.assertRaisesRegex(ValueError, "wording candidate request digest changed"):
                manifest.build_manifest()
