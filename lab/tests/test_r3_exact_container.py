import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from lab import r3_resource_audit as audit, spark_calibration_guard as guard
from lab.tests.test_r3_resource_audit import reserve


ID = "d3" * 32


class ExactContainerTests(unittest.TestCase):
    def capture(self, folder, *, create=ID, removed=ID, watchdog=False):
        real_popen = subprocess.Popen

        def docker(command, **kwargs):
            verb = command[len(guard.DOCKER)]
            if verb == "create":
                if isinstance(create, Exception):
                    raise create
                return subprocess.CompletedProcess(command, 0, stdout=create + "\n")
            self.assertIn(verb, {"kill", "rm"})
            self.assertEqual(command[-1], ID)
            return subprocess.CompletedProcess(command, 0, stdout=removed + "\n")

        def cpu_attacher(command, **kwargs):
            self.assertEqual(command[-3:], ["start", "--attach", ID])
            return real_popen([sys.executable, "-B", "-c", "print('cpu fixture')"], **kwargs)

        with (
            mock.patch.object(guard, "available_kib",
                              side_effect=[guard.ADMISSION_KIB, guard.ADMISSION_KIB, guard.FLOOR_KIB]
                              if watchdog else None, return_value=guard.ADMISSION_KIB),
            mock.patch.object(guard, "claim_receipt"),
            mock.patch.object(guard.subprocess, "run", side_effect=docker) as calls,
            mock.patch.object(guard.subprocess, "Popen", side_effect=cpu_attacher) as child,
        ):
            if isinstance(create, Exception):
                with self.assertRaises(type(create)):
                    guard._capture_calibration("synthetic", {}, folder, exact_container=True)
            elif create != ID:
                with self.assertRaisesRegex(RuntimeError, "exactly one full container ID"):
                    guard._capture_calibration("synthetic", {}, folder, exact_container=True)
            elif watchdog:
                with self.assertRaises(SystemExit):
                    guard._capture_calibration("synthetic", {}, folder, exact_container=True)
            else:
                guard._capture_calibration("synthetic", {}, folder, exact_container=True)
        return [call.args[0][len(guard.DOCKER)] for call in calls.call_args_list], child.call_count

    def read(self, folder, *, admission="synthetic"):
        path = folder / "guard.jsonl"
        return audit._read_host_capture(path, hashlib.sha256(path.read_bytes()).hexdigest(),
                                        exact_container=True, admission_id=admission)

    def report(self, folder):
        outcome, terminal, decision, _ = self.read(folder)
        return audit.audit([reserve()], outcome=outcome, terminal=terminal, decision=decision,
                           require_attachment_proof=True)

    def test_success_uses_and_records_exact_id(self):
        with TemporaryDirectory() as scratch:
            folder = Path(scratch) / "capture"
            self.assertEqual(self.capture(folder), (["create", "rm"], 1))
            outcome, terminal, _, _ = self.read(folder)
            self.assertEqual(outcome["container_id"], ID)
            self.assertEqual(terminal["container_id"], ID)
            self.assertTrue(terminal["container_cleanup_confirmed"])
            self.assertEqual(self.report(folder)["reason"], "missing_settlement")

    def test_watchdog_kills_only_exact_id(self):
        with TemporaryDirectory() as scratch:
            folder = Path(scratch) / "capture"
            self.assertEqual(self.capture(folder, watchdog=True), (["create", "kill", "rm"], 1))
            self.assertEqual(self.read(folder)[2]["container_id"], ID)
            self.assertEqual(self.report(folder)["reason"], "memory_floor")

    def test_lost_or_malformed_create_does_not_act_by_name(self):
        for response in (subprocess.TimeoutExpired("docker create", 30), ID[:12], ID.upper(), ID + "\n" + ID):
            with self.subTest(response=response), TemporaryDirectory() as scratch:
                folder = Path(scratch) / "capture"
                self.assertEqual(self.capture(folder, create=response), (["create"], 0))
                self.assertIsNone(self.read(folder)[1]["container_id"])
                self.assertEqual(self.report(folder)["reason"], "cleanup_unconfirmed")

    def test_wrong_removal_echo_does_not_confirm_cleanup(self):
        with TemporaryDirectory() as scratch:
            folder = Path(scratch) / "capture"
            self.capture(folder, removed="e4" * 32)
            self.assertFalse(self.read(folder)[1]["container_cleanup_confirmed"])
            self.assertEqual(self.report(folder)["reason"], "cleanup_unconfirmed")

    def test_audit_refuses_replacement_downgrade_and_wrong_admission(self):
        with TemporaryDirectory() as scratch:
            folder = Path(scratch) / "capture"
            self.capture(folder)
            log = folder / "guard.jsonl"
            rows = [json.loads(line) for line in log.read_bytes().splitlines()]
            rows[-1]["record"]["container_id"] = "e4" * 32
            log.write_text("".join(json.dumps(row) + "\n" for row in rows))
            with self.assertRaisesRegex(ValueError, "container ID differs from create"):
                self.read(folder)
            log.write_text(json.dumps(rows[0]) + "\n")
            with self.assertRaisesRegex(ValueError, "admission differs from reserve"):
                self.read(folder, admission="different")
            rows[0]["version"] = 1
            log.write_text(json.dumps(rows[0]) + "\n")
            with self.assertRaisesRegex(ValueError, "requires a version 2 capture"):
                self.read(folder)
