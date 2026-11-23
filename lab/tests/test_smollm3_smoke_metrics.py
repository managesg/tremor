from contextlib import redirect_stdout
import hashlib
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lab import smollm3_smoke_container as container
from lab import smollm3_smoke_metrics as metrics
from lab.spark_calibration_guard import IMAGE, WORKER_LOG_LIMIT


IDENTITY = "a" * 64
ATTEMPT = "tremor-r2-" + "b" * 32


class SmokeMetricsTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory())).resolve()
        self.snapshot = self.root / "snapshot"
        self.worker_mount = self.root / "runner"
        self.snapshot.mkdir()
        self.worker_mount.mkdir()
        self.inspect = {
            "id": IDENTITY, "image": IMAGE, "name": "/" + ATTEMPT, "attempt": ATTEMPT,
            "entrypoint": ["timeout"], "args": container._worker_args(metrics.admission.WORKER_PLAN_SHA256),
            "user": "1000:1000", "network": "none", "runtime": "runc", "readonly": True,
            "privileged": False, "memory": 60 * 2**30, "swap": 60 * 2**30, "pids": 64,
            "requests": [{"Driver": "", "Count": 0, "DeviceIDs": ["0"], "Capabilities": [["gpu"]], "Options": {}}],
            "devices": [], "log_driver": "none", "state": "created", "tmpfs": {"/tmp": container.TMPFS_OPTIONS},
            "env_matches": [f"{key}={value}" for key, value in container.WORKER_ENV.items()] + [None],
            "mounts": [
                {"Type": "bind", "Source": str(path), "Destination": destination, "RW": False}
                for path, destination in ((self.snapshot, "/snapshot"), (self.worker_mount, "/runner"))
            ],
        }
        self.sample = {
            **metrics.EXPECTED, "cuda_allocator_fraction": 0.2, "output_tokens": 2, "cap_reached": True,
            "load_ns": 2_000_000_000, "generation_ns": 500_000_000,
            "peak_cuda_allocated_bytes": 6_000_000_000, "peak_cuda_reserved_bytes": 7_000_000_000,
        }

    def _write(self, name, raw):
        path = self.root / name
        path.write_bytes(raw)
        path.chmod(0o600)
        return path, hashlib.sha256(raw).hexdigest()

    def _capture(self, raw, *, cleanup=True, inspect=None, include_inspect_pin=True):
        _, worker_pin = self._write("worker.log", raw)
        _, inspect_pin = self._write("prestart-inspect.json", self._line(self.inspect if inspect is None else inspect))
        base = {"admission_id": "synthetic-smoke", "container": ATTEMPT}
        created = {**base, "container_id": IDENTITY}
        attached = {**created, "attachment_pid": 42}
        if include_inspect_pin:
            created["prestart_inspect_sha256"] = inspect_pin
        events = [
            ("start", {**base, "worker_log_limit": WORKER_LOG_LIMIT}),
            ("created", created),
            ("outcome", {**attached, "stop": "completed", "min_memavailable_kib": 30_000_000}),
            ("terminal", {
                **attached, "attachment_returncode": 0, "attachment_status": "reaped",
                "cleanup_confirmed": cleanup, "container_cleanup_confirmed": cleanup,
                "observed_wall_seconds": 4.0,
                "worker_output": {"bytes": len(raw), "sha256": worker_pin, "limit_reached": False},
            }),
        ]
        host_raw = "".join(
            json.dumps({"version": 2, "sequence": i, "event": event, "record": record}) + "\n"
            for i, (event, record) in enumerate(events)
        ).encode()
        path, pin = self._write("host.jsonl", host_raw)
        return path, {"host_capture_sha256": pin, "worker_log_sha256": worker_pin,
                      "admission_id": base["admission_id"], "snapshot": self.snapshot,
                      "worker_mount": self.worker_mount}

    @staticmethod
    def _line(sample):
        return (json.dumps(sample) + "\n").encode()

    def test_accepts_one_cuda_record_among_diagnostics(self):
        raw = b"Loading weights...\rReady\n" + self._line(self.sample) + b"Optional warning\n"
        path, pins = self._capture(raw)
        receipt = metrics.verify(path, **pins)
        self.assertEqual(receipt["evidence"], "verified_smollm3_cuda_smoke_metrics")
        self.assertEqual(receipt["worker_log_sha256"], pins["worker_log_sha256"])
        self.assertEqual(receipt["prestart_inspect_sha256"],
                         hashlib.sha256((self.root / "prestart-inspect.json").read_bytes()).hexdigest())
        self.assertEqual(receipt["peak_cuda_reserved_bytes"], 7_000_000_000)
        self.assertFalse(receipt["authorizes_execution"])

    def test_refuses_cpu_record_and_repinned_invalid_metrics(self):
        changes = [
            {"device": "cpu", "cuda_allocator_fraction": None, "peak_cuda_allocated_bytes": None,
             "peak_cuda_reserved_bytes": None},
            {"input_ids_sha256": "0" * 64}, {"output_tokens": True}, {"output_tokens": 3},
            {"cap_reached": False}, {"peak_cuda_allocated_bytes": 0},
            {"peak_cuda_reserved_bytes": 1}, {"generation_ns": 0}, {"generation_ns": 6_000_000_000},
        ]
        for correction in changes:
            with self.subTest(correction=correction), self.assertRaises(ValueError):
                path, pins = self._capture(self._line({**self.sample, **correction}))
                metrics.verify(path, **pins)

    def test_refuses_ambiguous_truncated_and_duplicate_json(self):
        line = self._line(self.sample)
        for raw in (line + line, line.rstrip(), line.replace(b"{", b'{"device":"cuda:0",', 1)):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                path, pins = self._capture(raw)
                metrics.verify(path, **pins)

    def test_refuses_missing_cleanup_or_crossed_external_worker_pin(self):
        path, pins = self._capture(self._line(self.sample), cleanup=False)
        with self.assertRaisesRegex(ValueError, "cleanup_unconfirmed"):
            metrics.verify(path, **pins)
        path, pins = self._capture(self._line(self.sample))
        with self.assertRaisesRegex(ValueError, "terminal and independent pins"):
            metrics.verify(path, **{**pins, "worker_log_sha256": "0" * 64})

    def test_refuses_missing_sidecar_or_pin_and_sidecar_digest_mismatch(self):
        path, pins = self._capture(self._line(self.sample), include_inspect_pin=False)
        with self.assertRaisesRegex(ValueError, "lacks a valid pre-start"):
            metrics.verify(path, **pins)
        path, pins = self._capture(self._line(self.sample))
        self._write("prestart-inspect.json", self._line({**self.inspect, "network": "host"}))
        with self.assertRaisesRegex(ValueError, "inspection digest"):
            metrics.verify(path, **pins)
        (self.root / "prestart-inspect.json").unlink()
        with self.assertRaisesRegex(ValueError, "missing pre-start"):
            metrics.verify(path, **pins)

    def test_refuses_re_pinned_sidecar_with_different_identity_or_config(self):
        for field, changed in (
            ("id", "c" * 64), ("name", "/other"), ("args", ["unreviewed-worker"]), ("network", "host"),
        ):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "pinned smoke settings"):
                path, pins = self._capture(self._line(self.sample), inspect={**self.inspect, field: changed})
                metrics.verify(path, **pins)

    def test_refuses_inspect_mount_that_differs_from_explicit_reviewed_path(self):
        path, pins = self._capture(self._line(self.sample))
        other = self.root / "other"
        other.mkdir()
        with self.assertRaisesRegex(ValueError, "reviewed read-only inputs"):
            metrics.verify(path, **{**pins, "worker_mount": other})

    def test_cli_checks_explicit_mounts(self):
        path, pins = self._capture(self._line(self.sample))
        stdout = StringIO()
        with redirect_stdout(stdout):
            metrics.main([
                str(path), str(self.snapshot), str(self.worker_mount),
                "--host-capture-sha256", pins["host_capture_sha256"],
                "--worker-log-sha256", pins["worker_log_sha256"], "--admission-id", pins["admission_id"],
            ])
        self.assertEqual(json.loads(stdout.getvalue())["evidence"], "verified_smollm3_cuda_smoke_metrics")
