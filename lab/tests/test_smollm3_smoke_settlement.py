import hashlib
import json
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lab import smollm3_smoke_settlement as settlement
from lab.spark_calibration_guard import WORKER_LOG_LIMIT


class SmokeSettlementTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.identity = {"admission_id": "synthetic", "batch": settlement.BATCH,
                         "allocation": settlement.ALLOCATION}
        self.reserve = {
            **self.identity, "event": "reserve", "program_ceiling_gpu_hours": 70,
            "historical_t7_hold_gpu_hours": 4, "reserved_gpu_hours": 0.1,
            "available_program_before_gpu_hours": 65, "available_replication_before_gpu_hours": 1,
            "available_program_after_gpu_hours": 64.9, "available_replication_after_gpu_hours": 0.9,
        }

    def write(self, name, contents):
        path = self.root / name
        path.write_bytes(contents)
        path.chmod(0o600)
        return path, hashlib.sha256(contents).hexdigest()

    def run_verifier(self, **kwargs):
        path, pin = self.write("reserve.json", json.dumps(self.reserve).encode())
        return settlement.verify(path, reservation_sha256=pin, **kwargs)

    def capture(self, *, cleanup=True, wall=83.24227687099483):
        _, worker_pin = self.write("worker.log", b"public smoke receipt\n")
        start = {"admission_id": "synthetic", "container": "isolated-smoke"}
        created = {**start, "container_id": "a" * 64}
        attached = {**created, "attachment_pid": 42}
        terminal = {
            **attached, "attachment_returncode": 0, "attachment_status": "reaped",
            "cleanup_confirmed": cleanup, "container_cleanup_confirmed": cleanup,
            "observed_wall_seconds": wall,
            "worker_output": {"bytes": 21, "sha256": worker_pin, "limit_reached": False},
        }
        events = (
            ("start", {**start, "worker_log_limit": WORKER_LOG_LIMIT}),
            ("created", created),
            ("outcome", {**attached, "stop": "completed", "min_memavailable_kib": 30_000_000}),
            ("terminal", terminal),
        )
        return self.write_capture(events, worker_pin)

    def write_capture(self, events, worker_pin):
        raw = "".join(json.dumps({"version": 2, "sequence": i, "event": event, "record": record}) + "\n"
                      for i, (event, record) in enumerate(events)).encode()
        path, pin = self.write("host.jsonl", raw)
        return {"host_capture": path, "host_capture_sha256": pin, "worker_log_sha256": worker_pin}

    def cancelled_capture(self, *, cleanup=True, elapsed=0, inspection=True, attached=False, log=b"",
                          inspection_export=True, state="created"):
        _, worker_pin = self.write("worker.log", log)
        start = {"admission_id": "synthetic", "container": "isolated-smoke"}
        created = {**start, "container_id": "a" * 64}
        sidecar = json.dumps({"id": created["container_id"], "name": "/" + created["container"],
                              "attempt": created["container"], "state": state}).encode()
        if inspection_export:
            self.write("prestart-inspect.json", sidecar)
        inspect_pin = hashlib.sha256(sidecar).hexdigest() if inspection else None
        return self.write_capture((
            ("start", {**start, "worker_log_limit": WORKER_LOG_LIMIT}),
            ("created", {**created, "prestart_inspect_sha256": inspect_pin}),
            ("terminal", {
                **created, "attachment_pid": 42 if attached else None,
                "attachment_returncode": 1 if attached else None,
                "attachment_status": "reaped" if attached else "not_started",
                "cleanup_confirmed": cleanup, "container_cleanup_confirmed": cleanup,
                "observed_wall_seconds": elapsed,
                "worker_output": {"bytes": len(log), "sha256": worker_pin, "limit_reached": False},
            }),
        ), worker_pin)

    def cancellation(self, capture, **changes):
        data = {
            **self.identity, "event": "cancel", "host_capture_sha256": capture["host_capture_sha256"],
            "reservation_sha256": hashlib.sha256(json.dumps(self.reserve).encode()).hexdigest(),
            "actual_charged_gpu_hours": 0, "returned_reservation_gpu_hours": 0.1,
            "available_program_gpu_hours": 65, "available_replication_gpu_hours": 1,
        } | changes
        path, pin = self.write("cancel.json", json.dumps(data).encode())
        return {"settlement": path, "settlement_sha256": pin}

    def test_exact_nonattachment_can_return_unused_reserve_with_pinned_cancellation(self):
        capture = self.cancelled_capture()
        pending = self.run_verifier(**capture)
        self.assertEqual((pending["status"], pending["reason"]), ("held", "missing_cancellation"))
        self.assertEqual(pending["held_gpu_hours"], Decimal("0.1"))
        receipt = self.run_verifier(**capture, **self.cancellation(capture))
        self.assertEqual(receipt["status"], "verified_unused_reservation_return")
        self.assertEqual(receipt["actual_charged_gpu_hours"], Decimal(0))
        self.assertEqual(receipt["held_gpu_hours"], Decimal(0))
        self.assertEqual(receipt["available_replication_gpu_hours"], Decimal(1))

    def test_ambiguous_nonattachment_does_not_release_hold(self):
        options = (
            {"cleanup": False}, {"elapsed": 1}, {"inspection": False},
            {"attached": True}, {"log": b"unknown activity\n"},
        )
        for option in options:
            with self.subTest(option=option):
                capture = self.cancelled_capture(**option)
                self.assertEqual(self.run_verifier(**capture)["held_gpu_hours"], Decimal("0.1"))
                with self.assertRaisesRegex(ValueError, "uncertain reservation"):
                    self.run_verifier(**capture, **self.cancellation(capture))
        capture = self.cancelled_capture()
        receipt = self.cancellation(capture)
        capture["worker_log_sha256"] = None
        with self.assertRaisesRegex(ValueError, "uncertain reservation"):
            self.run_verifier(**capture, **receipt)

    def test_settlement_cannot_substitute_for_cancellation_or_change_amounts(self):
        capture = self.cancelled_capture()
        with self.assertRaisesRegex(ValueError, "invalid replication cancel record"):
            self.run_verifier(**capture, **self.cancellation(capture, event="settle"))
        with self.assertRaisesRegex(ValueError, "settlement mismatch"):
            self.run_verifier(**capture, **self.cancellation(capture, actual_charged_gpu_hours=0.01))

    def test_cancellation_requires_actual_pinned_created_inspection(self):
        capture = self.cancelled_capture(inspection_export=False)
        self.assertEqual(self.run_verifier(**capture)["reason"], "missing_prestart_inspection")
        with self.assertRaisesRegex(ValueError, "uncertain reservation"):
            self.run_verifier(**capture, **self.cancellation(capture))
        capture = self.cancelled_capture(state="running")
        with self.assertRaisesRegex(ValueError, "exact created container"):
            self.run_verifier(**capture, **self.cancellation(capture))
        capture = self.cancelled_capture()
        self.write("prestart-inspect.json", b"{}")
        with self.assertRaisesRegex(ValueError, "external digest mismatch: prestart-inspect"):
            self.run_verifier(**capture, **self.cancellation(capture))

    def test_exact_clean_receipts_debit_only_program_and_replication(self):
        capture = self.capture()
        data = {
            **self.identity, "event": "settle", "host_capture_sha256": capture["host_capture_sha256"],
            "reservation_sha256": hashlib.sha256(json.dumps(self.reserve).encode()).hexdigest(),
            "actual_charged_gpu_hours": 0.023123, "returned_reservation_gpu_hours": 0.076877,
            "available_program_gpu_hours": 64.976877, "available_replication_gpu_hours": 0.976877,
        }
        path, pin = self.write("settle.json", json.dumps(data).encode())
        report = self.run_verifier(**capture, settlement=path, settlement_sha256=pin)
        self.assertEqual(report["status"], "verified_settlement")
        self.assertEqual(report["held_gpu_hours"], 0)
        self.assertEqual(report["actual_charged_gpu_hours"], Decimal("0.023123"))
        self.assertEqual(report["available_replication_gpu_hours"], Decimal("0.976877"))
        self.assertNotIn("available_r2_r3_gpu_hours", report)
        self.reserve["historical_t7_hold_gpu_hours"] = 3
        with self.assertRaisesRegex(ValueError, "does not bind"):
            self.run_verifier(**capture, settlement=path, settlement_sha256=pin)

    def test_missing_or_uncertain_receipts_preserve_entire_hold(self):
        scenarios = [
            ({}, "missing_host_capture"),
            (self.capture(cleanup=False), "cleanup_unconfirmed"),
        ]
        for inputs, expected in scenarios:
            with self.subTest(expected=expected):
                report = self.run_verifier(**inputs)
                self.assertEqual((report["status"], report["reason"]), ("held", expected))
                self.assertEqual(report["held_gpu_hours"], Decimal("0.1"))
        capture = self.capture(wall=361)
        self.assertEqual(self.run_verifier(**capture)["reason"], "reservation_overrun")
        capture = self.capture()
        self.assertEqual(self.run_verifier(**{**capture, "worker_log_sha256": None})["reason"],
                         "missing_independent_worker_evidence")
        with self.assertRaisesRegex(ValueError, "worker log digest mismatch"):
            self.run_verifier(**{**capture, "worker_log_sha256": "0" * 64})

    def test_repinned_cross_allocation_and_incorrect_balance_refused(self):
        self.reserve["allocation"] = "spark-r2-r3"
        with self.assertRaisesRegex(ValueError, "invalid replication reserve"):
            self.run_verifier()
        self.reserve["allocation"] = settlement.ALLOCATION
        self.reserve["available_replication_after_gpu_hours"] = 1
        with self.assertRaisesRegex(ValueError, "balance mismatch"):
            self.run_verifier()
