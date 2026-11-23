from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lab import smollm3_smoke_admission as admission


class SmolLM3SmokeAdmissionTests(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(TemporaryDirectory())
        self.path = Path(directory) / "receipt.json"
        self.now = datetime(2026, 11, 21, 15, 45, tzinfo=timezone.utc)
        self.receipt = {
            "schema": admission.SCHEMA,
            "batch": admission.BATCH,
            "admission_id": "smollm3-smoke-001",
            "valid_from_utc": "2026-11-21T15:45:00Z",
            "valid_until_utc": "2026-11-21T15:50:00+00:00",
            "worker_plan_sha256": admission.WORKER_PLAN_SHA256,
            "model_manifest_sha256": admission.MODEL_MANIFEST_SHA256,
            "allocation": admission.ALLOCATION,
            "reservation_sha256": "1" * 64,
            "review_reference": "independent-smoke-review",
            "authorization_reference": "replication-budget-approval",
            "reserved_gpu_hours": 0.1,
            "outer_wall_seconds": 300,
        }

    def check(self, *, raw=None, now=None, digest=None):
        if raw is None:
            raw = json.dumps(self.receipt).encode()
        self.path.write_bytes(raw)
        return admission.verify(
            self.path, admission_sha256=sha256(raw).hexdigest() if digest is None else digest,
            now=self.now if now is None else now,
        )

    def test_pinned_valid_receipt_can_be_rechecked_without_side_effects(self):
        self.assertEqual(self.check(), self.receipt)
        original = self.path.read_bytes()
        self.assertEqual(
            admission.verify(self.path, admission_sha256=sha256(original).hexdigest(), now=self.now),
            self.receipt,
        )
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_external_pin_duplicate_and_oversized_inputs_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            self.check(digest="0" * 64)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.check(raw=b'{"schema":"a","schema":"b"}')
        with self.assertRaisesRegex(ValueError, "oversized"):
            self.check(raw=b" " * 16385)

    def test_crossed_batch_family_worker_manifest_and_reservation_are_rejected(self):
        for field, value in (
            ("schema", "tremor.smollm3_smoke_admission.v2"),
            ("admission_id", "../previous"),
            ("batch", "spark-r2-qwen35-4b-throughput"),
            ("allocation", "r2-r3"),
            ("worker_plan_sha256", "0" * 64),
            ("model_manifest_sha256", "0" * 64),
            ("reservation_sha256", "missing"),
            ("review_reference", " "),
            ("authorization_reference", None),
            ("reserved_gpu_hours", 0.2),
            ("outer_wall_seconds", 300.0),
        ):
            with self.subTest(field=field, value=value):
                with self.assertRaises(ValueError):
                    self.check(raw=json.dumps({**self.receipt, field: value}).encode())

    def test_resource_envelope_uses_exact_decimal(self):
        raw = json.dumps(self.receipt).replace(": 0.1", ": 0.10000000000000000001").encode()
        with self.assertRaisesRegex(ValueError, "resource envelope"):
            self.check(raw=raw)

    def test_utc_window_must_cover_the_whole_outer_deadline(self):
        for now in (
            self.now - timedelta(seconds=1),
            self.now + timedelta(microseconds=1),
            self.now.replace(tzinfo=None),
            self.now.astimezone(timezone(-timedelta(hours=5))),
        ):
            with self.subTest(now=now), self.assertRaisesRegex(ValueError, "UTC"):
                self.check(now=now)
        invalid = {**self.receipt, "valid_until_utc": "2026-11-21T16:00:00"}
        with self.assertRaisesRegex(ValueError, "ISO 8601 UTC"):
            self.check(raw=json.dumps(invalid).encode())

    def test_symbolic_link_is_refused(self):
        self.check()
        alias = self.path.parent / "alias.json"
        alias.symlink_to(self.path)
        with self.assertRaises(OSError):
            admission.verify(alias, admission_sha256=sha256(self.path.read_bytes()).hexdigest(), now=self.now)
