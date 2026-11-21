from copy import deepcopy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lab import r3_l2_completion_receipt, spark_calibration_guard


class CompletionReceiptTests(unittest.TestCase):
    def setUp(self):
        self.bundle = Path(self.enterContext(TemporaryDirectory()))
        self.completion = self.bundle / "completed.report.json"
        self.terminal = self.bundle / "completed/guard-terminal.json"
        self.terminal.parent.mkdir()
        self.record = {
            "evidence": "scripted_cpu_guard_parent_tape",
            "stop": "completed",
            "gpu_jobs": 0,
            "isolated_cpu": True,
            "container_removed": True,
            "child_reaped": True,
            "child_returncode": 0,
            "injected_limit": None,
            "watchdog_stop_sha256": None,
            "container_id": "a" * 64,
            "isolation": {
                "container_id": "a" * 64,
                "image": spark_calibration_guard.IMAGE,
                "network": "none",
                "cpu_limit": 1,
                "memory_bytes": 128 * 1024 * 1024,
                "capabilities_dropped": ["ALL"],
                "mounts": {"/export": "rw", "/fixture/lab": "ro", "/fixture/src": "ro", "/plan.json": "ro"},
            },
            "artifacts": {"manifest_sha256": "b" * 64},
        }

    def verify(self, completion, terminal):
        pins = {}
        for role, record in (("completion", completion), ("terminal", terminal)):
            path = getattr(self, role)
            raw = (json.dumps(record, sort_keys=True) + ("\n" if role == "terminal" else "")).encode()
            path.write_bytes(raw)
            pins[f"{role}_sha256"] = hashlib.sha256(raw).hexdigest()
        return r3_l2_completion_receipt.verify(self.bundle, **pins)

    def test_valid_separately_pinned_receipts_are_offline_only(self):
        receipt = self.verify(self.record, self.record)
        self.assertIs(receipt["authorizes_execution"], False)
        self.assertEqual(receipt["manifest_sha256"], "b" * 64)
        self.assertNotEqual(receipt["completion_sha256"], receipt["terminal_sha256"])
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            r3_l2_completion_receipt.verify(
                self.bundle, completion_sha256=receipt["completion_sha256"], terminal_sha256="0" * 64,
            )

    def test_matching_re_pinned_bad_terminal_state_is_rejected(self):
        for field, value in (("child_reaped", False), ("child_returncode", 137), ("child_returncode", False),
                             ("gpu_jobs", True), ("container_removed", False), ("watchdog_stop_sha256", "c" * 64),
                             ("injected_limit", "memory_floor")):
            with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, "reaped CPU completion"):
                changed = {**self.record, field: value}
                self.verify(changed, changed)

    def test_matching_re_pinned_isolation_mismatch_is_rejected(self):
        for field, value in (("container_id", "c" * 64), ("network", "bridge"), ("mounts", {"/plan.json": "rw"}),
                             ("cpu_limit", True), ("memory_bytes", 0)):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "isolation envelope"):
                changed = deepcopy(self.record)
                changed["isolation"][field] = value
                self.verify(changed, changed)

    def test_re_pinned_but_different_summary_and_terminal_are_rejected(self):
        changed = {**self.record, "artifacts": {"manifest_sha256": "c" * 64}}
        with self.assertRaisesRegex(ValueError, "differs from the host terminal"):
            self.verify(changed, self.record)
