from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from lab import spark_calibration_guard as guard


NAME = "tremor-r2-" + "b" * 32
ID = "12" * 32


class SparkAdmissionDiagnosticTests(unittest.TestCase):
    def setUp(self):
        scratch = Path(self.enterContext(TemporaryDirectory()))
        self.journal = scratch / "journal.jsonl"
        self.enterContext(mock.patch.object(guard, "ADMISSION_JOURNAL", self.journal))
        self.enterContext(mock.patch.object(guard, "LOCK_PATH", scratch / "lock"))

    def pending(self):
        guard._append_attempt(self.journal, "pending", "fixture", NAME)
        return self.journal.read_bytes()

    def test_cli_reports_clean_journal_without_calling_docker(self):
        output = io.StringIO()
        with (
            mock.patch("sys.argv", [guard.__name__, "--diagnose-admission"]),
            mock.patch.object(guard.subprocess, "run") as docker,
            redirect_stdout(output),
        ):
            guard.main()
        docker.assert_not_called()
        self.assertEqual(json.loads(output.getvalue()), {"journal": "no_pending_attempt"})
        self.assertFalse(self.journal.exists())

    def test_empty_label_query_does_not_resolve_pending_attempt(self):
        before = self.pending()
        with mock.patch.object(guard.subprocess, "run", return_value=mock.Mock(stdout="")) as docker:
            report = guard.diagnose_admission(self.journal)
        self.assertEqual(report["observation"], "no_match_at_query_time")
        self.assertTrue(report["admission_blocked"])
        self.assertIn("-aq", docker.call_args.args[0])
        self.assertIn("--no-trunc", docker.call_args.args[0])
        self.assertIn(f"label={guard.ATTEMPT_LABEL}={NAME}", docker.call_args.args[0])
        with self.assertRaisesRegex(SystemExit, "unresolved create or cleanup"):
            guard.ensure_no_unresolved_attempt(self.journal)
        self.assertEqual(before, self.journal.read_bytes())

    def test_stopped_object_is_bound_by_label_and_full_id(self):
        before = self.pending()
        inspection = {"id": ID, "name": "/renamed", "attempt": NAME, "state": "exited"}
        replies = [mock.Mock(stdout=ID + "\n"), mock.Mock(stdout=json.dumps(inspection))]
        with mock.patch.object(guard.subprocess, "run", side_effect=replies) as docker:
            report = guard.diagnose_admission(self.journal)
        self.assertEqual((report["observation"], report["container_id"], report["container_state"]),
                         ("matching_object", ID, "exited"))
        self.assertFalse(report["name_matches"])
        self.assertTrue(report["admission_blocked"])
        self.assertEqual(docker.call_args.args[0][-1], ID)
        self.assertEqual(before, self.journal.read_bytes())

    def test_invalid_listing_inspection_and_daemon_failure_stay_unresolved(self):
        before = self.pending()
        for lines in (ID[:12] + "\n", f"{ID}\n{ID}\n"):
            with (
                mock.patch.object(guard.subprocess, "run", return_value=mock.Mock(stdout=lines)),
                self.assertRaisesRegex(ValueError, "ambiguous or noncanonical"),
            ):
                guard.diagnose_admission(self.journal)
        for inspection in ({"id": ID, "name": f"/{NAME}", "attempt": "other", "state": "exited"},
                           {"id": "ce" * 32, "name": f"/{NAME}", "attempt": NAME, "state": "exited"}):
            with (
                mock.patch.object(guard.subprocess, "run", side_effect=[
                    mock.Mock(stdout=ID + "\n"), mock.Mock(stdout=json.dumps(inspection)),
                ]),
                self.assertRaisesRegex(ValueError, "does not corroborate"),
            ):
                guard.diagnose_admission(self.journal)
        with (
            mock.patch.object(guard.subprocess, "run", side_effect=[
                mock.Mock(stdout=ID + "\n"), subprocess.CalledProcessError(1, "inspect"),
            ]),
            self.assertRaises(subprocess.CalledProcessError),
        ):
            guard.diagnose_admission(self.journal)
        self.assertEqual(before, self.journal.read_bytes())
