import json
from datetime import datetime, timezone
from pathlib import Path
import select
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from lab import spark_calibration_guard as guard
from lab.tests.test_r3_exact_container import ID
from lab.tests import test_spark_calibration_guard as fixtures


NAME = "tremor-r2-" + "a" * 32


class SparkAdmissionJournalTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.journal = self.root / "journal.jsonl"
        self.lock = self.root / "lock"
        self.enterContext(mock.patch.object(guard, "ADMISSION_JOURNAL", self.journal))
        self.enterContext(mock.patch.object(guard, "LOCK_PATH", self.lock))
        self.receipt = self.root / "receipt.json"
        receipt = fixtures.SparkCalibrationGuardTests().receipt(datetime.now(timezone.utc))
        self.receipt.write_text(json.dumps(dict(receipt, admission_id="next")))
        self.argv = [guard.__name__, "--approved-launch", "--receipt", str(self.receipt)]

    def test_sigkill_after_durable_intent_blocks_both_launch_paths_before_docker(self):
        child = subprocess.Popen(
            [sys.executable, "-B", "-c", """
from pathlib import Path
import signal
import sys
from lab import spark_calibration_guard as guard
with guard.host_lock(Path(sys.argv[1])):
    guard._append_attempt(Path(sys.argv[2]), 'pending', 'previous', sys.argv[3])
    print('intent durable', flush=True)
    signal.pause()
""", str(self.lock), str(self.journal), NAME],
            stdout=subprocess.PIPE, text=True,
        )
        with child:
            try:
                self.assertTrue(select.select([child.stdout], [], [], 5)[0])
                self.assertEqual(child.stdout.readline().rstrip(), "intent durable")
                with self.assertRaisesRegex(SystemExit, "holds the host lock"), guard.host_lock():
                    self.fail("overlapping admission")
            finally:
                child.kill()
                child.wait(timeout=5)
        self.assertEqual(child.returncode, -9)
        for flags in ([], ["--require-container-identity", "--capture-directory", str(self.root / "logs")]):
            with (
                mock.patch("sys.argv", self.argv + flags),
                mock.patch.object(guard.subprocess, "run", return_value=mock.Mock(stdout="")) as docker,
                mock.patch.object(guard, "claim_receipt") as claim,
                self.assertRaisesRegex(SystemExit, "unresolved create or cleanup for previous"),
            ):
                guard.main()
            docker.assert_not_called()
            claim.assert_not_called()

    def test_bad_or_partial_journal_fails_closed(self):
        guard._append_attempt(self.journal, "pending", "previous", NAME)
        guard._append_attempt(self.journal, "removed", "wrong-admission", NAME, ID)
        with self.assertRaisesRegex(ValueError, "invalid Spark admission journal transition"):
            guard.ensure_no_unresolved_attempt(self.journal)
        self.journal.write_bytes(b'["pending"')
        with self.assertRaisesRegex(ValueError, "incomplete Spark admission journal"):
            guard.ensure_no_unresolved_attempt(self.journal)

    def test_exact_lifecycle_records_intent_before_create_and_closes_only_with_cleanup(self):
        start_child = subprocess.Popen
        for name, removal in (("bound", ID), ("unknown", "e4" * 32)):
            journal = self.root / (name + ".jsonl")

            def docker(command, **kwargs):
                if command[len(guard.DOCKER)] == "create":
                    with self.assertRaisesRegex(SystemExit, f"unresolved create or cleanup for {name}"):
                        guard.ensure_no_unresolved_attempt(journal)
                    nonce = json.loads(journal.read_text())[2]
                    self.assertIn(f"ai.seabridge.tremor.attempt={nonce}", command)
                    return subprocess.CompletedProcess(command, 0, stdout=ID + "\n")
                return subprocess.CompletedProcess(command, 0, stdout=removal + "\n")

            def attach(_command, **kwargs):
                return start_child([sys.executable, "-B", "-c", "print('cpu fixture')"], **kwargs)

            with (
                mock.patch.object(guard, "claim_receipt"),
                mock.patch.object(guard, "available_kib", return_value=guard.ADMISSION_KIB),
                mock.patch.object(guard.subprocess, "run", side_effect=docker),
                mock.patch.object(guard.subprocess, "Popen", side_effect=attach),
            ):
                guard._capture_calibration(name, {}, self.root / name, exact_container=True, admission_journal=journal)
            if name == "bound":
                guard.ensure_no_unresolved_attempt(journal)
                self.assertEqual(json.loads(journal.read_text().splitlines()[-1])[-1], ID)
            else:
                with self.assertRaisesRegex(SystemExit, "unresolved create or cleanup for unknown"):
                    guard.ensure_no_unresolved_attempt(journal)

    def test_native_preflight_queries_stopped_containers(self):
        with (
            mock.patch("sys.argv", self.argv + ["--require-container-identity",
                                                "--capture-directory", str(self.root / "logs")]),
            mock.patch.object(guard.subprocess, "run", return_value=mock.Mock(stdout=ID + "\n")) as docker,
            mock.patch.object(guard, "claim_receipt") as claim,
            self.assertRaisesRegex(SystemExit, "earlier calibration container still exists"),
        ):
            guard.main()
        self.assertIn("-aq", docker.call_args.args[0])
        claim.assert_not_called()
