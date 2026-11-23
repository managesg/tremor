import hashlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest import mock
from contextlib import redirect_stdout

from lab import r3_resource_audit, spark_calibration_guard as guard
from lab.tests import test_r3_resource_audit as fixtures


class HostCaptureTests(unittest.TestCase):
    def capture(self, destination, code):
        popen = subprocess.Popen

        def isolated_cpu_writer(command, **kwargs):
            self.assertEqual(command[:3], ["/usr/bin/prlimit", f"--fsize={guard.WORKER_LOG_LIMIT}:{guard.WORKER_LOG_LIMIT}", "--"])
            self.assertEqual(kwargs["stderr"], subprocess.STDOUT)
            self.assertIs(kwargs["close_fds"], True)
            return popen([*command[:3], sys.executable, "-B", "-c", code], **kwargs)

        with (
            mock.patch.object(guard, "available_kib", return_value=guard.ADMISSION_KIB),
            mock.patch.object(guard, "claim_receipt"),
            mock.patch.object(guard, "cleanup", return_value=True),
            mock.patch.object(guard.subprocess, "run") as run,
            mock.patch.object(guard.subprocess, "Popen", side_effect=isolated_cpu_writer),
        ):
            guard._capture_calibration("synthetic", {}, destination)
        self.assertIn("--log-driver=none", run.call_args_list[0].args[0])

    def verify(self, directory):
        log = directory / "guard.jsonl"
        pin = hashlib.sha256(log.read_bytes()).hexdigest()
        outcome, terminal, decision, actual_pin = r3_resource_audit._read_host_capture(log, pin)
        self.assertEqual(actual_pin, pin)
        return r3_resource_audit.audit([fixtures.reserve()], outcome=outcome, terminal=terminal, decision=decision,
                                       require_attachment_proof=True)

    def test_real_cpu_writer_cannot_mix_progress_into_host_receipt(self):
        with TemporaryDirectory() as scratch:
            root = Path(scratch) / "capture"
            self.capture(root, '''
from pathlib import Path
assert all(fd.resolve().name != "guard.jsonl" for fd in Path("/proc/self/fd").iterdir())
print('{"stop":"fake","cleanup_confirmed":true}')
''')
            host = root / "guard.jsonl"
            worker = root / "worker.log"
            self.assertEqual(stat.S_IMODE(root.stat().st_mode), 0o700)
            self.assertEqual([stat.S_IMODE(path.stat().st_mode) for path in (host, worker)], [0o600, 0o600])
            self.assertEqual(json.loads(worker.read_bytes())["stop"], "fake")
            rows = [json.loads(line) for line in host.read_bytes().splitlines()]
            self.assertEqual([line["event"] for line in rows], ["start", "outcome", "terminal"])
            self.assertEqual(rows[1]["record"]["stop"], "completed")
            result = self.verify(root)
            self.assertEqual((result["status"], result["reason"]), ("held", "missing_settlement"))
            with self.assertRaisesRegex(ValueError, "external host capture digest mismatch"):
                r3_resource_audit._read_host_capture(host, "0" * 64)

    def test_same_size_worker_replacement_and_mixed_host_diagnostic_are_refused(self):
        with TemporaryDirectory() as scratch:
            root = Path(scratch) / "capture"
            self.capture(root, "print('worker-output')")
            worker, host = root / "worker.log", root / "guard.jsonl"
            original = worker.read_bytes()
            worker.write_bytes(b"X" + original[1:])
            with self.assertRaisesRegex(ValueError, "worker evidence digest differs"):
                self.verify(root)
            worker.write_bytes(original)
            with host.open("ab") as stream:
                stream.write(b'{"stop":"progress"}\n')
            with self.assertRaisesRegex(ValueError, "invalid host capture envelope"):
                self.verify(root)

    def test_file_limit_is_enforced_on_a_real_cpu_writer_and_keeps_the_hold(self):
        with TemporaryDirectory() as scratch:
            root = Path(scratch) / "capture"
            with (
                mock.patch.object(guard, "WORKER_LOG_LIMIT", 4096),
                mock.patch.object(r3_resource_audit, "WORKER_LOG_LIMIT", 4096),
                self.assertRaises(SystemExit) as stopped,
            ):
                self.capture(root, "import os; os.write(1, b'x' * 131072); os.write(1, b'x' * 131072)")
            self.assertEqual(stopped.exception.code, 1)
            self.assertEqual((root / "worker.log").stat().st_size, 4096)
            with mock.patch.object(r3_resource_audit, "WORKER_LOG_LIMIT", 4096):
                result = self.verify(root)
            self.assertEqual((result["status"], result["reason"]), ("held", "worker_output_limit"))

    def test_cli_requires_pin_and_reconciles_a_matching_receipt(self):
        with TemporaryDirectory() as scratch:
            parent = Path(scratch)
            root = parent / "capture"
            self.capture(root, "print('fixture')")
            log = root / "guard.jsonl"
            pin = hashlib.sha256(log.read_bytes()).hexdigest()
            outcome, terminal, _, _ = r3_resource_audit._read_host_capture(log, pin)
            measured = r3_resource_audit.charge_for_wall_time(terminal["observed_wall_seconds"])
            reserve = fixtures.reserve()
            returned = reserve["reserved_gpu_hours"] - measured
            settlement = fixtures.settle(
                outcome=outcome, terminal=terminal, actual_charged_gpu_hours=measured,
                returned_reservation_gpu_hours=returned,
                available_program_gpu_hours=reserve["available_program_after_gpu_hours"] + returned,
                available_r2_r3_gpu_hours=reserve["available_r2_r3_after_gpu_hours"] + returned,
                run_log_sha256=pin,
            )
            ledger = parent / "ledger.jsonl"
            ledger.write_text("".join(json.dumps(row, default=float) + "\n" for row in (reserve, settlement)))
            output = io.StringIO()
            with redirect_stdout(output):
                r3_resource_audit.main([str(ledger), "--guard-log", str(log), "--host-capture-sha256", pin])
            self.assertEqual(json.loads(output.getvalue())["status"], "verified_settlement")

    def test_capture_reader_rejects_symlink_and_hardlink_aliases(self):
        with TemporaryDirectory() as scratch:
            root = Path(scratch)
            original = root / "original"
            original.write_bytes(b"record")
            original.chmod(0o600)
            symlink = root / "symlink"
            symlink.symlink_to(original)
            with self.assertRaises(OSError):
                r3_resource_audit._private_capture_bytes(symlink, 100)
            os.link(original, root / "alias")
            with self.assertRaisesRegex(ValueError, "single-link regular file"):
                r3_resource_audit._private_capture_bytes(original, 100)
