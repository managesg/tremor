"""Mock process tests of the Spark watchdog, with no Docker or GPU calls."""

import contextlib
import io
import json
import signal
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from lab import spark_calibration_guard as guard


class SparkCalibrationGuardTests(unittest.TestCase):
    def setUp(self):
        lock_directory = self.enterContext(tempfile.TemporaryDirectory())
        self.enterContext(mock.patch.object(guard, "LOCK_PATH", Path(lock_directory) / "spark.lock"))

    def receipt(self, now):
        return {
            "admission_id": "unit-test",
            "batch": guard.BATCH,
            "reserved_gpu_hours": 0.1,
            "available_r2_r3_gpu_hours": 7.5,
            "review_reference": "mock reviewer",
            "authorization_reference": "mock authorization",
            "ledger_reference": "mock ledger",
            "issued_utc": now.isoformat(),
        }

    def drive(self, *, runtime, freemem, status=0):
        clock = [0]
        killed = []

        class Child:
            returncode = status

            def poll(self):
                return self.returncode if clock[0] >= runtime else None

        def kill():
            killed.append(clock[0])

        def pause(seconds):
            clock[0] += seconds

        result = guard.watch(Child(), kill, lambda: freemem(clock[0]), lambda: clock[0], pause)
        return result, killed

    def test_clean_and_error_exits_are_distinguished(self):
        for status, expected in ((0, "completed"), (1, "child_error")):
            (reason, minimum), kills = self.drive(runtime=3, freemem=lambda _: guard.FLOOR_KIB + 3,
                                                   status=status)
            self.assertEqual(reason, expected)
            self.assertEqual(minimum, guard.FLOOR_KIB + 3)
            self.assertEqual(kills, [])

    def test_inclusive_memory_floor_stops_the_job(self):
        (reason, minimum), kills = self.drive(runtime=999, freemem=lambda t: guard.FLOOR_KIB + (t < 4))
        self.assertEqual((reason, minimum), ("memory_floor", guard.FLOOR_KIB))
        self.assertEqual(kills, [4])

    def test_wall_limit_includes_work_since_start(self):
        (reason, _), kills = self.drive(runtime=999, freemem=lambda _: guard.FLOOR_KIB + 1)
        self.assertEqual(reason, "wall_limit")
        self.assertEqual(kills, [guard.WALL_SECONDS])

    def test_no_launch_without_the_approval_switch(self):
        with (
            mock.patch("sys.argv", ["spark_calibration_guard"]),
            mock.patch.object(guard, "available_kib") as available,
            contextlib.redirect_stderr(io.StringIO()),
            self.assertRaises(SystemExit) as caught,
        ):
            guard.main()
        self.assertEqual(caught.exception.code, 2)
        available.assert_not_called()

    def test_success_uses_local_read_only_mounts_and_cleans_only_its_container(self):
        output = io.StringIO()
        with (
            mock.patch("sys.argv", ["spark_calibration_guard", "--approved-launch",
                                    "--receipt", "mock.json"]),
            mock.patch.object(Path, "read_text", return_value=json.dumps(self.receipt(datetime.now(timezone.utc)))),
            mock.patch.object(guard, "ensure_no_running_calibration"),
            mock.patch.object(guard, "claim_receipt") as claim,
            mock.patch.object(guard, "available_kib", return_value=guard.ADMISSION_KIB),
            mock.patch.object(guard.subprocess, "run") as run,
            mock.patch.object(guard.subprocess, "Popen") as popen,
            contextlib.redirect_stdout(output),
        ):
            popen.return_value.poll.return_value = 0
            popen.return_value.returncode = 0
            run.return_value.returncode = 0
            guard.main()
        create = run.call_args_list[0].args[0]
        name = create[create.index("--name") + 1]
        self.assertIn("--pull=never", create)
        self.assertEqual(create[create.index("--network") + 1], "none")
        self.assertIn(guard.IMAGE, create)
        self.assertEqual(sum(value.endswith(",readonly") for value in create), 2)
        self.assertEqual(create[create.index("--entrypoint") + 1], "timeout")
        self.assertIn("--kill-after=5s", create)
        self.assertEqual(create[create.index("--memory-swap") + 1], "60g")
        self.assertEqual(claim.call_args.args[1], "unit-test")
        popen.assert_called_once_with([*guard.DOCKER, "start", "--attach", name])
        self.assertEqual(run.call_args_list[-1].args[0], [*guard.DOCKER, "rm", "--force", name])
        outcome, accounting = map(json.loads, output.getvalue().splitlines())
        self.assertEqual(outcome["stop"], "completed")
        self.assertTrue(accounting["cleanup_confirmed"])

    def test_receipt_is_fresh_complete_and_single_use(self):
        now = datetime.now(timezone.utc)
        receipt = self.receipt(now)
        self.assertEqual(guard.verify_receipt(receipt, now), "unit-test")
        for invalid in (
            dict(receipt, issued_utc=(now - timedelta(hours=2)).isoformat()),
            dict(receipt, review_reference=""),
            dict(receipt, available_r2_r3_gpu_hours=0.05),
        ):
            with self.assertRaises(ValueError):
                guard.verify_receipt(invalid, now)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            guard.claim_receipt(root, "unit-test", receipt, "first")
            with self.assertRaises(FileExistsError):
                guard.claim_receipt(root, "unit-test", receipt, "second")

    def test_create_timeout_and_sigterm_scope_cleanup(self):
        def terminate_guard():
            signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)

        for fail in (subprocess.TimeoutExpired("docker create", 30), terminate_guard):
            with (
                self.subTest(fail=fail),
                mock.patch("sys.argv", ["spark_calibration_guard", "--approved-launch",
                                        "--receipt", "mock.json"]),
                mock.patch.object(Path, "read_text", return_value=json.dumps(self.receipt(datetime.now(timezone.utc)))),
                mock.patch.object(guard, "ensure_no_running_calibration"),
                mock.patch.object(guard, "claim_receipt"),
                mock.patch.object(guard, "available_kib", return_value=guard.ADMISSION_KIB),
                mock.patch.object(guard.subprocess, "run") as run,
                mock.patch.object(guard.subprocess, "Popen") as popen,
                mock.patch.object(guard, "cleanup", return_value=True) as cleanup,
                contextlib.redirect_stdout(io.StringIO()),
                self.assertRaises((subprocess.TimeoutExpired, SystemExit)),
            ):
                def fail_create(*_args, **_kwargs):
                    if callable(fail):
                        fail()
                    raise fail
                run.side_effect = fail_create
                guard.main()
            create = run.call_args.args[0]
            cleanup.assert_called_once_with(create[create.index("--name") + 1])
            popen.assert_not_called()

    def test_headroom_rechecked_after_create(self):
        with (
            mock.patch("sys.argv", ["spark_calibration_guard", "--approved-launch",
                                    "--receipt", "mock.json"]),
            mock.patch.object(Path, "read_text", return_value=json.dumps(self.receipt(datetime.now(timezone.utc)))),
            mock.patch.object(guard, "ensure_no_running_calibration"),
            mock.patch.object(guard, "claim_receipt"),
            mock.patch.object(guard, "available_kib", side_effect=[guard.ADMISSION_KIB, guard.ADMISSION_KIB - 1]),
            mock.patch.object(guard.subprocess, "run"),
            mock.patch.object(guard.subprocess, "Popen") as popen,
            mock.patch.object(guard, "cleanup", return_value=True) as cleanup,
            contextlib.redirect_stdout(io.StringIO()),
            self.assertRaisesRegex(RuntimeError, "70 GiB"),
        ):
            guard.main()
        cleanup.assert_called_once()
        popen.assert_not_called()

    def test_host_lock_refuses_overlap_and_releases_after_exit(self):
        with guard.host_lock():
            with self.assertRaisesRegex(SystemExit, "holds the host lock"), guard.host_lock():
                self.fail("overlapping host lock acquired")
        with guard.host_lock():
            pass

    def test_active_container_refuses_admission_before_receipt_claim(self):
        with (
            mock.patch("sys.argv", ["spark_calibration_guard", "--approved-launch",
                                    "--receipt", "mock.json"]),
            mock.patch.object(Path, "read_text", return_value=json.dumps(self.receipt(datetime.now(timezone.utc)))),
            mock.patch.object(guard, "claim_receipt") as claim,
            mock.patch.object(guard.subprocess, "run") as run,
            mock.patch.object(guard.subprocess, "Popen") as popen,
            self.assertRaisesRegex(SystemExit, "earlier calibration container is still active"),
        ):
            run.return_value.stdout = "leftover-task-container-id\n"
            guard.main()
        self.assertEqual(run.call_args.args[0], [*guard.DOCKER, "ps", "-q", "--filter", "name=^/tremor-r2-"])
        claim.assert_not_called()
        popen.assert_not_called()
