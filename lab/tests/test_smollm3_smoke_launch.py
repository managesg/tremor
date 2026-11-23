from contextlib import nullcontext
import hashlib
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from lab import r3_resource_audit
from lab import smollm3_smoke_launch as smoke


IDENTITY = "a" * 64
ADMISSION_PIN = "b" * 64
PLAN_PIN = "c" * 64
RECEIPT = {"admission_id": "smollm3-test", "outer_wall_seconds": 300}
INPUTS = {**RECEIPT, "worker_plan_sha256": PLAN_PIN}
OPENING = ("synthetic-ledger", "synthetic-guard", "synthetic-placement", "d" * 64)


class SmokeLaunchTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory())).resolve()
        self.paths = [self.root / name for name in ("receipt", "reserve", "snapshot", "worker", "pins", "capture")]
        self.paths[2].mkdir()
        self.paths[3].mkdir()
        self.events = []
        self.observe(smoke.spark, "host_lock", lambda: nullcontext())
        self.observe(smoke.spark, "ensure_no_unresolved_attempt")
        self.observe(smoke.spark, "ensure_no_running_calibration")
        self.preflight = self.observe(smoke.preflight, "verify", lambda *args, **kwargs: INPUTS)
        self.recheck = self.observe(smoke.admission, "verify", lambda *args, **kwargs: RECEIPT)
        self.observe(smoke, "_headroom")
        self.observe(smoke, "_claim")
        self.inspect = self.observe(smoke.container, "verify_created")
        self.observe(smoke.spark, "_append_attempt",
                     lambda path, event, *args: self.events.append(event))
        self.handle = SimpleNamespace(pid=9, returncode=0, wait=lambda **kwargs: 0)
        self.create_response = IDENTITY + "\n"
        self.remove_response = IDENTITY + "\n"
        self.run = self.observe(smoke.subprocess, "run", self.docker)
        self.attach = self.observe(smoke.subprocess, "Popen", self.attachment)
        self.watch = self.observe(smoke.spark, "watch", lambda *args, **kwargs: ("completed", 75_000_000))

    def observe(self, module, name, result=lambda *args, **kwargs: None):
        def record(*args, **kwargs):
            self.events.append(name)
            return result(*args, **kwargs)
        return self.enterContext(patch.object(module, name, side_effect=record))

    def docker(self, argv, **kwargs):
        command = argv[len(smoke.spark.DOCKER)]
        self.events.append(command)
        if command == "create":
            return SimpleNamespace(stdout=self.create_response, returncode=0)
        if argv[-1] != IDENTITY:
            raise AssertionError("Docker mutation or inspection must use the exact ID")
        if command == "inspect":
            return SimpleNamespace(stdout="{}", returncode=0)
        if command == "rm":
            return SimpleNamespace(stdout=self.remove_response, returncode=0)
        if command == "kill":
            return SimpleNamespace(stdout="", returncode=0)
        raise AssertionError(command)

    def attachment(self, argv, *, stdout, **kwargs):
        self.assertEqual(argv[-3:], ["start", "--attach", IDENTITY])
        stdout.write(b"test worker receipt\n")
        return self.handle

    def launch(self):
        smoke.launch(*self.paths, admission_sha256=ADMISSION_PIN, opening_balance=OPENING)

    def test_missing_opening_rejects_before_docker_or_claim(self):
        with self.assertRaisesRegex(ValueError, "independent opening balance"):
            smoke.launch(*self.paths, admission_sha256=ADMISSION_PIN, opening_balance=None)
        self.run.assert_not_called()
        self.assertNotIn("_claim", self.events)
        self.assertFalse(self.paths[-1].exists())

    def test_same_opening_is_required_before_create_and_attachment(self):
        self.launch()
        self.assertEqual([call.kwargs["opening_balance"] for call in self.preflight.call_args_list],
                         [OPENING, OPENING])
        observed = [index for index, event in enumerate(self.events) if event == "verify"]
        self.assertLess(observed[0], self.events.index("create"))
        self.assertGreater(observed[2], self.events.index("inspect"))
        self.assertLess(observed[2], self.events.index("Popen"))

    def terminal(self):
        rows = (self.paths[-1] / "guard.jsonl").read_text().splitlines()
        return json.loads(rows[-1])["record"]

    def test_clean_launch_holds_pending_until_exact_cleanup_and_capture(self):
        self.launch()
        for first, second in (("ensure_no_unresolved_attempt", "_claim"), ("pending", "create"),
                              ("verify_created", "Popen"), ("rm", "removed")):
            self.assertLess(self.events.index(first), self.events.index(second))
        self.assertEqual(self.recheck.call_count, 2)
        self.assertEqual(self.preflight.call_count, 2)
        inspect = self.paths[-1] / "prestart-inspect.json"
        self.assertEqual(inspect.stat().st_mode & 0o777, 0o600)
        self.assertEqual(json.loads(inspect.read_text()), {})
        record = self.terminal()
        self.assertTrue(record["cleanup_confirmed"])
        self.assertEqual(record["worker_output"]["sha256"], hashlib.sha256(b"test worker receipt\n").hexdigest())
        capture = self.paths[-1] / "guard.jsonl"
        created = json.loads(capture.read_text().splitlines()[1])["record"]
        self.assertEqual(created["prestart_inspect_sha256"], hashlib.sha256(inspect.read_bytes()).hexdigest())
        outcome, terminal, decision, _, verified_created = r3_resource_audit._read_host_capture(
            capture, hashlib.sha256(capture.read_bytes()).hexdigest(),
            exact_container=True, admission_id=RECEIPT["admission_id"], include_created=True,
        )
        self.assertEqual(created, verified_created)
        self.assertEqual(outcome["container_id"], IDENTITY)
        self.assertTrue(terminal["container_cleanup_confirmed"])
        self.assertIsNone(decision)
        with self.assertRaisesRegex(ValueError, "malformed host capture"):
            r3_resource_audit._read_host_capture(
                capture, hashlib.sha256(capture.read_bytes()).hexdigest(),
                exact_container=True, admission_id=RECEIPT["admission_id"],
            )

    def test_incomplete_create_never_starts_or_removes_an_unbound_container(self):
        self.create_response = "a" * 12
        with self.assertRaisesRegex(RuntimeError, "full container ID"):
            self.launch()
        for event in ("inspect", "Popen", "rm", "removed"):
            self.assertNotIn(event, self.events)
        self.assertIn("pending", self.events)
        self.assertFalse(self.terminal()["cleanup_confirmed"])

    def test_inspect_mismatch_never_mutates_unproven_container(self):
        self.inspect.side_effect = ValueError("mismatch")
        with self.assertRaisesRegex(ValueError, "mismatch"):
            self.launch()
        self.assertNotIn("Popen", self.events)
        self.assertNotIn("rm", self.events)
        self.assertNotIn("removed", self.events)

    def test_expired_post_create_window_stops_before_attachment(self):
        self.recheck.side_effect = [RECEIPT, ValueError("expired")]
        with self.assertRaisesRegex(ValueError, "expired"):
            self.launch()
        self.assertNotIn("Popen", self.events)
        self.assertIn("removed", self.events)
        self.assertEqual(self.terminal()["attachment_status"], "not_started")

    def test_post_create_input_drift_stops_before_attachment(self):
        worker_file = self.paths[3] / "worker.py"
        worker_file.write_text("pinned")

        def verify_inputs(*args, **kwargs):
            if worker_file.read_text() != "pinned":
                raise ValueError("worker file differs from its exact pin")
            return INPUTS

        def docker(argv, **kwargs):
            result = self.docker(argv, **kwargs)
            if argv[len(smoke.spark.DOCKER)] == "create":
                worker_file.write_text("changed")
            return result

        self.preflight.side_effect = verify_inputs
        self.run.side_effect = docker
        with self.assertRaisesRegex(ValueError, "worker file differs"):
            self.launch()
        self.attach.assert_not_called()
        self.assertIn("removed", self.events)
        self.assertTrue(self.terminal()["cleanup_confirmed"])

    def test_wrong_remove_receipt_keeps_pending(self):
        self.remove_response = "e" * 64 + "\n"
        with self.assertRaisesRegex(RuntimeError, "cleanup"):
            self.launch()
        self.assertNotIn("removed", self.events)
        self.assertFalse(self.terminal()["cleanup_confirmed"])

    def test_watchdog_captures_stop_and_kills_exact_id(self):
        def watchdog(child, kill, *args, on_stop, **kwargs):
            on_stop("memory_floor", 10)
            kill()
            return "memory_floor", 10
        self.watch.side_effect = watchdog
        with self.assertRaisesRegex(RuntimeError, "memory_floor"):
            self.launch()
        self.assertIn("kill", self.events)
        self.assertIn("removed", self.events)
        text = (self.paths[-1] / "guard.jsonl").read_text()
        self.assertIn('"watchdog_decision": "memory_floor"', text)

    def test_unresolved_attach_registration_cannot_clear_pending(self):
        self.attach.side_effect = OSError("ambiguous attach")
        with self.assertRaisesRegex(OSError, "ambiguous attach"):
            self.launch()
        self.assertIn("rm", self.events)
        self.assertNotIn("removed", self.events)
        self.assertEqual(self.terminal()["attachment_status"], "unconfirmed")


class SmokeClaimTests(unittest.TestCase):
    def test_private_fixed_owner_one_use_claim(self):
        root = Path(self.enterContext(TemporaryDirectory())).resolve()
        attempt = "tremor-r2-" + "b" * 32
        with patch.object(smoke.pwd, "getpwuid", return_value=SimpleNamespace(pw_dir=str(root))):
            smoke._claim(RECEIPT["admission_id"], ADMISSION_PIN, attempt)
            with self.assertRaises(FileExistsError):
                smoke._claim(RECEIPT["admission_id"], ADMISSION_PIN, attempt)
        marker = root / ".tremor-smollm3-claims" / f"{RECEIPT['admission_id']}.json"
        self.assertEqual(marker.stat().st_mode & 0o777, 0o600)
        self.assertEqual(json.loads(marker.read_text()), {"admission_sha256": ADMISSION_PIN, "attempt": attempt})
