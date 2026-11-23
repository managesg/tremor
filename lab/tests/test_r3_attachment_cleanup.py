from contextlib import redirect_stdout
from decimal import Decimal
import hashlib
import io
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from lab import r3_resource_audit, spark_calibration_guard as guard
from lab.tests import test_r3_resource_audit as fixtures


class AttachmentCleanupTests(unittest.TestCase):
    def failure(self, *, container_error=False, attach_error=False):
        events = []
        output = io.StringIO()
        child = mock.Mock(pid=23412, returncode=None)

        def teardown(_name):
            events.append("container cleanup")
            if container_error:
                raise RuntimeError("container cleanup unconfirmed")
            return True

        def wait(*, timeout):
            self.assertEqual(timeout, 2)
            events.append("attach wait")
            if events.count("attach wait") == 1:
                raise subprocess.TimeoutExpired("fixture attach", timeout)
            child.returncode = -9
            return child.returncode

        def kill():
            events.append("attach kill")
            if attach_error:
                raise RuntimeError("attach kill unconfirmed")

        child.wait.side_effect = wait
        child.kill.side_effect = kill
        message = ("attach kill unconfirmed" if attach_error else
                   "container cleanup unconfirmed" if container_error else "fixture watcher failed")
        with (
            mock.patch.object(guard, "available_kib", return_value=guard.ADMISSION_KIB),
            mock.patch.object(guard, "claim_receipt"),
            mock.patch.object(guard, "watch", side_effect=RuntimeError("fixture watcher failed")),
            mock.patch.object(guard, "cleanup", side_effect=teardown),
            mock.patch.object(guard.subprocess, "run"),
            mock.patch.object(guard.subprocess, "Popen", return_value=child),
            redirect_stdout(output),
            self.assertRaisesRegex(RuntimeError, message),
        ):
            guard._run_calibration("synthetic", {})
        terminal = json.loads(output.getvalue())
        return events, terminal

    def test_watch_failure_still_terminates_and_reaps_own_attachment(self):
        events, terminal = self.failure()
        self.assertEqual(events, ["container cleanup", "attach wait", "attach kill", "attach wait"])
        self.assertIs(terminal["cleanup_confirmed"], True)
        self.assertEqual((terminal["attachment_status"], terminal["attachment_pid"], terminal["attachment_returncode"]),
                         ("reaped", 23412, -9))

    def test_failed_container_cleanup_does_not_skip_attach_reaping(self):
        events, terminal = self.failure(container_error=True)
        self.assertEqual(events[-1], "attach wait")
        self.assertEqual(terminal["attachment_status"], "reaped")
        self.assertIs(terminal["container_cleanup_confirmed"], False)
        self.assertIs(terminal["cleanup_confirmed"], False)

    def test_failed_attachment_termination_keeps_cleanup_unconfirmed(self):
        _, terminal = self.failure(attach_error=True)
        self.assertIs(terminal["container_cleanup_confirmed"], True)
        self.assertIs(terminal["cleanup_confirmed"], False)
        self.assertEqual(terminal["attachment_status"], "unconfirmed")
        self.assertIsNone(terminal["attachment_returncode"])


class AttachmentSettlementTests(unittest.TestCase):
    def setUp(self):
        self.identity = {"admission_id": "synthetic", "container": "synthetic-container", "attachment_pid": 23412}
        self.outcome = fixtures.outcome() | self.identity
        self.terminal = fixtures.terminal(seconds="90") | self.identity | {
            "attachment_status": "reaped", "attachment_returncode": 0, "container_cleanup_confirmed": True,
        }
        self.decision = self.identity | {"watchdog_decision": "wall_limit", "sample_kib": 64_000_000}

    def test_new_scope_requires_new_cleanup_proof_and_completed_zero_exit(self):
        report = r3_resource_audit.audit([fixtures.reserve()], outcome=fixtures.outcome(),
                                        terminal=fixtures.terminal(), require_attachment_proof=True)
        self.assertEqual((report["status"], report["reason"]), ("held", "missing_attachment_proof"))
        with self.assertRaisesRegex(ValueError, "no eligible attachment exit"):
            r3_resource_audit.audit([fixtures.reserve()], outcome=self.outcome,
                                    terminal=self.terminal | {"attachment_returncode": -9},
                                    require_attachment_proof=True)

    def test_conflicting_decision_and_mismatched_attachment_identity_refused(self):
        with self.assertRaisesRegex(ValueError, "decision conflicts with outcome"):
            r3_resource_audit.audit([fixtures.reserve()], outcome=self.outcome, terminal=self.terminal,
                                    decision=self.decision, require_attachment_proof=True)
        with self.assertRaisesRegex(ValueError, "attachment PID differs"):
            r3_resource_audit.audit([fixtures.reserve()], outcome=self.outcome | {"attachment_pid": 23413},
                                    terminal=self.terminal, require_attachment_proof=True)

    def test_uncertain_attachment_holds_reservation_even_after_container_cleanup(self):
        terminal = self.terminal | {"attachment_status": "unconfirmed", "attachment_returncode": None,
                                    "cleanup_confirmed": False}
        record = r3_resource_audit.audit([fixtures.reserve()], terminal=terminal, decision=self.decision,
                                        require_attachment_proof=True)
        self.assertEqual((record["status"], record["reason"]), ("held", "cleanup_unconfirmed"))
        self.assertEqual((record["held_gpu_hours"], record["watchdog_decision"]), (Decimal("0.1"), "wall_limit"))

    def test_memory_floor_cannot_be_reported_as_completion_and_child_error_requires_nonzero(self):
        with self.assertRaisesRegex(ValueError, "conflicts with memory floor"):
            r3_resource_audit.audit([fixtures.reserve()],
                                    outcome=self.outcome | {"min_memavailable_kib": guard.FLOOR_KIB},
                                    terminal=self.terminal, require_attachment_proof=True)
        with self.assertRaisesRegex(ValueError, "child error cannot have a zero exit"):
            r3_resource_audit.audit([fixtures.reserve()], outcome=self.outcome | {"stop": "child_error"},
                                    terminal=self.terminal, require_attachment_proof=True)

    def test_strict_cli_binds_external_receipt_order_and_digest(self):
        with TemporaryDirectory() as directory:
            ledger = Path(directory) / "ledger.jsonl"
            log = Path(directory) / "guard.log"
            terminal = self.terminal | {"observed_wall_seconds": 90}

            def write(records):
                raw = "".join(json.dumps(record, sort_keys=True) + "\n" for record in records).encode()
                log.write_bytes(raw)
                settlement = fixtures.settle(outcome=self.outcome, terminal=terminal, actual_charged_gpu_hours=0.025,
                                             returned_reservation_gpu_hours=0.075, available_program_gpu_hours=65.975,
                                             available_r2_r3_gpu_hours=7.475,
                                             run_log_sha256=hashlib.sha256(raw).hexdigest())
                ledger.write_text("".join(json.dumps(row, default=float) + "\n"
                                          for row in (fixtures.reserve(), settlement)))

            arguments = [str(ledger), "--guard-log", str(log), "--require-attachment-proof"]
            write([self.outcome, terminal])
            output = io.StringIO()
            with redirect_stdout(output):
                r3_resource_audit.main(arguments)
            self.assertEqual(json.loads(output.getvalue())["status"], "verified_settlement")
            write([terminal, self.outcome])
            with mock.patch("sys.stderr", new_callable=io.StringIO) as err, self.assertRaises(SystemExit) as failure:
                r3_resource_audit.main(arguments)
            self.assertEqual(failure.exception.code, 2)
            self.assertIn("guard receipts are out of order", err.getvalue())
