from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from lab import smollm3_smoke_worker as worker
from lab.spark_decision import Generation


def pin(raw):
    return sha256(raw).hexdigest()


def write_json(path, value):
    raw = json.dumps(value).encode()
    path.write_bytes(raw)
    return pin(raw)


class SmolLM3SmokeWorkerTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.plan = self.root / "plan.json"
        self.snapshot = self.root / "snapshot"
        self.snapshot.mkdir()
        self.prompt = "fake public chat rendering"
        self.ids = list(range(73))
        self.spec = {
            "schema": worker.SCHEMA,
            "device": "cpu",
            "cuda_allocator_fraction": None,
            "prompt_sha256": pin(self.prompt.encode()),
            "input_ids_sha256": pin(json.dumps(self.ids, separators=(",", ":")).encode()),
            "input_tokens": 73,
            "max_output_tokens": 2,
        }
        records = []
        for name in sorted(worker.RUNTIME_METADATA):
            raw = name.encode()
            (self.snapshot / name).write_bytes(raw)
            records.append({"path": name, "bytes": len(raw), "sha256": pin(raw)})
        self.spec["manifest_sha256"] = write_json(self.snapshot / "MANIFEST.sha256.json", {
            "model": worker.MODEL, "revision": worker.REVISION, "files": records,
        })
        self.render = self.enterContext(patch.object(worker, "_render", return_value=(self.prompt, self.ids)))
        self.enterContext(patch.object(worker, "PROMPT_SHA256", self.spec["prompt_sha256"]))
        self.enterContext(patch.object(worker, "INPUT_IDS_SHA256", self.spec["input_ids_sha256"]))
        self.generate = Mock(return_value=Generation("fake", 73, 2, 25, True))
        self.load = self.enterContext(patch.object(worker, "load_smollm3", return_value=self.generate))
        self.configure = self.enterContext(patch.object(worker, "_configure_device"))
        self.peaks = self.enterContext(patch.object(worker, "_device_peaks", return_value=(128, 256)))

    def run_plan(self, **overrides):
        plan_sha = write_json(self.plan, {**self.spec, **overrides})
        return worker.run(self.snapshot, self.plan, plan_sha256=plan_sha)

    def test_cpu_runs_one_bounded_generation(self):
        report = self.run_plan()
        self.configure.assert_not_called()
        self.peaks.assert_not_called()
        self.load.assert_called_once_with(self.snapshot, device="cpu")
        self.generate.assert_called_once_with(self.prompt, max_input_tokens=73, max_output_tokens=2)
        self.assertEqual((report["input_tokens"], report["output_tokens"], report["generation_ns"]), (73, 2, 25))
        self.assertFalse(report["authorizes_execution"])
        self.assertIsNone(report["peak_cuda_allocated_bytes"])
        self.assertIsNone(report["peak_cuda_reserved_bytes"])

    def test_cuda_allocator_set_before_model_load(self):
        calls = Mock()
        calls.attach_mock(self.configure, "configure")
        calls.attach_mock(self.load, "load")
        calls.attach_mock(self.generate, "generate")
        calls.attach_mock(self.peaks, "peaks")
        report = self.run_plan(device="cuda:0", cuda_allocator_fraction=0.2)
        self.assertEqual([entry[0] for entry in calls.mock_calls], ["configure", "load", "generate", "peaks"])
        self.configure.assert_called_once_with(0.2)
        self.load.assert_called_once_with(self.snapshot, device="cuda:0")
        self.assertEqual(report["cuda_allocator_fraction"], 0.2)
        self.assertEqual((report["peak_cuda_allocated_bytes"], report["peak_cuda_reserved_bytes"]), (128, 256))

    def test_unpinned_or_changed_files_stop_before_rendering(self):
        write_json(self.plan, self.spec)
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            worker.run(self.snapshot, self.plan, plan_sha256="0" * 64)
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            self.run_plan(manifest_sha256="0" * 64)
        path = self.snapshot / "config.json"
        path.write_bytes(b"X" * len(path.read_bytes()))
        with self.assertRaisesRegex(ValueError, "metadata digest mismatch"):
            self.run_plan()
        self.render.assert_not_called()
        self.load.assert_not_called()

    def test_unsafe_device_fraction_and_token_caps_refuse_before_loading(self):
        for overrides in (
            {"device": "cuda:1", "cuda_allocator_fraction": 0.2},
            {"device": "cuda:0", "cuda_allocator_fraction": 0.21},
            {"device": "cuda:0", "cuda_allocator_fraction": None},
            {"device": "cpu", "cuda_allocator_fraction": 0.01},
            {"max_output_tokens": 3},
            {"input_ids_sha256": "0" * 64},
        ):
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                self.run_plan(**overrides)
        self.load.assert_not_called()
        self.configure.assert_not_called()

    def test_same_length_different_input_ids_refuse_before_loading(self):
        self.render.return_value = (self.prompt, self.ids[::-1])
        with self.assertRaisesRegex(ValueError, "differ from the pinned sequence"):
            self.run_plan()
        self.load.assert_not_called()

    def test_receipt_cannot_exceed_output_cap(self):
        self.generate.return_value = Generation("fake", 73, 3, 25, True)
        with self.assertRaisesRegex(ValueError, "generation receipt"):
            self.run_plan()
