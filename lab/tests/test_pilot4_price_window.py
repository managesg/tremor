from datetime import date
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from lab import pilot4_price_window as window
from tremor import spend


RETAINED_PRICE_SHEET = Path(__file__).resolve().parents[2] / "docs" / "reports" / "price-sheet.json"
RETAINED_PRICE_SHEET_SHA256 = "16b204c23aa5ce3b169e44a3b2608ee39e3aa8da14b6b1838d8cb15a3356984f"


class Pilot4PriceWindowTests(unittest.TestCase):
    def setUp(self):
        folder = Path(self.enterContext(TemporaryDirectory()))
        self.sheet = folder / "price-sheet.json"
        raw = json.dumps({
            "fetched": "2026-01-10",
            "source_url": "https://example.invalid/offline-test",
            "models": {"claude-haiku-5-5": dict.fromkeys(spend.KEYS, 0.1)},
        }).encode()
        self.sheet.write_bytes(raw)
        self.pin = sha256(raw).hexdigest()

    def _verify(self, start, end, *, pin=None):
        return window.verify(self.sheet, price_sheet_sha256=self.pin if pin is None else pin,
                             starts_at=start, ends_at=end)

    def test_exact_retained_sheet_verifies_offline(self):
        with (patch("socket.socket", side_effect=AssertionError("unexpected socket")),
              patch.object(spend, "Ledger", side_effect=AssertionError("unexpected ledger"))):
            receipt = window.verify(
                RETAINED_PRICE_SHEET, price_sheet_sha256=RETAINED_PRICE_SHEET_SHA256,
                starts_at="2026-11-23T21:00:00Z", ends_at="2026-11-23T23:59:59.999999Z",
            )
        self.assertEqual(receipt["valid_through_utc_date"], "2026-11-23")
        self.assertEqual(receipt["price_sheet_sha256"], RETAINED_PRICE_SHEET_SHA256)
        self.assertFalse(receipt["authorizes_execution"])

    def test_refuses_first_stale_utc_instant_even_if_start_was_valid(self):
        self._verify("2026-01-13T23:00:00Z", "2026-01-13T23:59:59.999999+00:00")
        with self.assertRaisesRegex(ValueError, "end price-sheet check failed: .*4 days old"):
            self._verify("2026-01-13T23:00:00Z", "2026-01-14T00:00:00Z")

    def test_refuses_start_before_fetch(self):
        with self.assertRaisesRegex(ValueError, "start price-sheet check failed"):
            self._verify("2026-01-09T23:59:59Z", "2026-01-10T00:00:00Z")

    def test_refuses_undefined_non_utc_or_non_increasing_window(self):
        start = "2026-01-13T01:00:00Z"
        invalid = (None, "2026-01-13", "2026-01-13T02:00:00", "2026-01-13T02:00:00-01:00",
                   "2026-01-32T02:00:00Z", "2026-01-13T00:59:59Z", start)
        for end in invalid:
            with self.subTest(end=end), self.assertRaises(ValueError):
                self._verify(start, end)

    def test_refuses_replacement_digest_at_either_endpoint(self):
        start = "2026-01-12T23:00:00Z"
        end = "2026-01-13T01:00:00Z"
        with self.assertRaisesRegex(ValueError, "start price-sheet digest"):
            self._verify(start, end, pin="0" * 64)
        original = spend.PriceSheet.load(self.sheet, today=date(2026, 1, 12))
        replacement = spend.PriceSheet(original.data, "0" * 64)
        with patch.object(spend.PriceSheet, "load", side_effect=(original, replacement)) as loader:
            with self.assertRaisesRegex(ValueError, "end price-sheet digest"):
                self._verify(start, end)
        self.assertEqual([call.kwargs["today"] for call in loader.call_args_list],
                         [date(2026, 1, 12), date(2026, 1, 13)])
