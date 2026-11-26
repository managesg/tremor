"""R5 GPU readiness checks with fakes: no GPU, no model load."""

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from lab import r5_gpu_readiness as r5

REV = "a" * 40
GATE = 73_400_320
PLAN = f"Fits: Qwen3.5-4B at `data/hf/Qwen3.5-4B` with `MANIFEST.sha256.json`, revision `{REV}` (SR:119)."


def smi(gpu="NVIDIA GB10, [N/A], [N/A], 0 %\n", apps="", code=0):
    def run(argv):
        return SimpleNamespace(returncode=code, stdout=gpu if "gpu=" in argv[1] else apps, stderr="")
    return run


class Case(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root = Path(td.name)
        (self.root / "prereg").mkdir()
        (self.root / "prereg/R5-agent-performance-line-plan.md").write_text(PLAN)
        self.model = self.root / "model"
        self.model.mkdir()
        self.data = {"a.bin": b"x" * 2500, "b.json": b"{}"}
        files = []
        for n, b in self.data.items():
            (self.model / n).write_bytes(b)
            files.append({"path": n, "sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b)})
        self.write_manifest(files)
        self.mem = self.root / "meminfo"
        self.set_mem(GATE + 1000)
        self.load = self.root / "loadavg"
        self.load.write_text("0.5 0.4 0.3 1/200 99\n")

    def write_manifest(self, files, revision=REV):
        (self.model / "MANIFEST.sha256.json").write_text(json.dumps({"revision": revision, "files": files}))

    def set_mem(self, kib):
        self.mem.write_text(f"MemTotal: 999 kB\nMemAvailable: {kib} kB\n")

    def run_check(self, runner=None, allowed=False, gate=GATE):
        return r5.check(self.root, self.model, gate, allowed, runner=runner or smi(),
                        meminfo_path=self.mem, loadavg_path=self.load, chunk=7)

    def has(self, res, text):
        self.assertFalse(res["ok"])
        self.assertTrue(any(text in f for f in res["failures"]), res["failures"])


class Tests(Case):
    def test_pass(self):
        res = self.run_check()
        self.assertTrue(res["ok"], res["failures"])
        self.assertEqual(res["weights"]["files_checked"], 2)
        self.assertEqual(res["gpu"]["gpus"][0]["name"], "NVIDIA GB10")
        self.assertEqual(res["loadavg"], ["0.5", "0.4", "0.3"])
        self.assertFalse(res["quiet_host_claimed"])
        self.assertFalse(res["writes"]["model_dir_changed"])

    def test_missing_file(self):
        (self.model / "a.bin").unlink()
        res = self.run_check()
        self.has(res, "missing")
        self.assertEqual(res["weights"]["missing"], ["a.bin"])
        self.assertEqual(res["weights"]["files_checked"], 1)

    def test_hash_mismatch(self):
        (self.model / "b.json").write_bytes(b"{ }")
        res = self.run_check()
        self.has(res, "mismatch")
        self.assertEqual(res["weights"]["mismatches"], ["b.json"])

    def test_same_size_content_change(self):
        (self.model / "b.json").write_bytes(b"[]")
        self.assertEqual(self.run_check()["weights"]["mismatches"], ["b.json"])

    def test_apps_query_fails(self):
        def run(argv):
            return SimpleNamespace(returncode=3 if "apps" in argv[1] else 0, stdout="NVIDIA GB10, 1, 1, 0 %", stderr="bad")
        self.has(self.run_check(run), "exit 0/3")

    def test_model_dir_change_detected(self):
        def writer(argv):
            (self.model / "new.txt").write_text("x")
            return smi()(argv)
        res = self.run_check(writer)
        self.has(res, "writes")
        self.assertTrue(res["writes"]["model_dir_changed"])

    def test_same_hash_wrong_size_listed(self):
        files = json.loads((self.model / "MANIFEST.sha256.json").read_text())["files"]
        files[0]["bytes"] += 1
        self.write_manifest(files)
        self.assertEqual(self.run_check()["weights"]["mismatches"], ["a.bin"])

    def test_memory_below_gate(self):
        self.set_mem(GATE - 1)
        self.has(self.run_check(), "below gate")

    def test_memory_at_gate_passes(self):
        self.set_mem(GATE)
        self.assertTrue(self.run_check()["ok"])

    def test_memory_below_host_stop_even_with_low_gate(self):
        self.set_mem(1000)
        self.has(self.run_check(gate=500), "host stop")

    def test_other_gpu_process(self):
        res = self.run_check(smi(apps="123, llama-server, 28000 MiB\n"))
        self.has(res, "other process")
        self.assertEqual(res["gpu"]["other_processes"][0]["process_name"], "llama-server")

    def test_other_gpu_process_allowed_still_reported(self):
        res = self.run_check(smi(apps="123, llama-server, 28000 MiB\n"), allowed=True)
        self.assertTrue(res["ok"])
        self.assertEqual(len(res["gpu"]["other_processes"]), 1)

    def test_nvidia_smi_absent(self):
        def absent(argv):
            raise FileNotFoundError("nvidia-smi")
        self.has(self.run_check(absent), "unavailable")

    def test_nvidia_smi_timeout(self):
        def slow(argv):
            raise subprocess.TimeoutExpired(argv, 20)
        self.has(self.run_check(slow), "unavailable")

    def test_nvidia_smi_nonzero(self):
        self.has(self.run_check(smi(code=9)), "exit 9")

    def test_no_gpu_reported(self):
        self.has(self.run_check(smi(gpu="")), "no GPU")

    def test_revision_mismatch(self):
        self.write_manifest([], revision="b" * 40)
        self.has(self.run_check(), "revision")

    def test_plan_without_revision(self):
        (self.root / "prereg/R5-agent-performance-line-plan.md").write_text("nothing")
        res = self.run_check()
        self.has(res, "revision")
        self.assertIsNone(res["weights"]["revision_expected"])

    def test_manifest_absent(self):
        (self.model / "MANIFEST.sha256.json").unlink()
        self.has(self.run_check(), "manifest unreadable")

    def test_streaming_chunks_and_no_writes(self):
        before = sorted(p.name for p in self.model.iterdir())
        res = self.run_check()
        self.assertEqual(before, sorted(p.name for p in self.model.iterdir()))
        self.assertEqual(res["writes"]["paths_written_by_check"], [])

    def test_gpu_commands_are_read_only_queries(self):
        seen = []
        def spy(argv):
            seen.append(argv)
            return smi()(argv)
        self.run_check(spy)
        self.assertEqual(seen, [r5.GPU_QUERY, r5.APP_QUERY])
        self.assertEqual(r5.HOST_STOP_KIB, 10_485_760)


if __name__ == "__main__":
    unittest.main()
