import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from murmuration import runner  # noqa: E402


class RunnerTests(unittest.TestCase):
    def test_arms_and_record(self):
        s = {a: runner.run("shop", a, 1, "scripted") for a in runner.ARMS}
        self.assertEqual(s["oracle"]["score"], 1.0)
        self.assertEqual(s["raw-notes"]["score"], 1.0)
        self.assertLess(s["stateless"]["score"], 0.5)
        self.assertGreater(s["raw-notes"]["tokens"]["input"], s["oracle"]["tokens"]["input"])
        r = s["oracle"]
        self.assertEqual(set(r["tokens"]), {"input", "output", "cache_read", "cache_write"})
        self.assertIsNone(r["tokens"]["cache_read"])
        self.assertEqual(r["manifest"]["seed"], 1)
        self.assertEqual(r["tokens_method"], "len//4 estimate")
        self.assertGreaterEqual(r["wall_seconds"], 0)

    def test_deterministic(self):
        a, b = (runner.run("farm", "oracle", 3, "scripted") for _ in range(2))
        self.assertEqual((a["score"], a["tokens"]), (b["score"], b["tokens"]))

    def test_jsonl_out(self):
        d = os.path.join(tempfile.mkdtemp(), "out")
        for arm in runner.ARMS:
            runner.run("clinic", arm, 2, "scripted", out_dir=d)
        files = sorted(os.listdir(d))
        self.assertEqual(len(files), 3)
        for f in files:
            lines = open(os.path.join(d, f)).read().splitlines()
            self.assertEqual(len(lines), 1)
            json.loads(lines[0])

    def test_local_hf_fails_cleanly(self):
        try:
            import torch  # noqa: F401
        except ImportError:
            with self.assertRaisesRegex(RuntimeError, "torch"):
                runner.run("shop", "oracle", 1, "local_hf")
        else:
            self.skipTest("torch present")

    def test_stub_and_bad_args(self):
        with self.assertRaises(NotImplementedError):
            runner.run("shop", "oracle", 1, "claude")
        for args in (("nope", "oracle", 1, "scripted"), ("shop", "x", 1, "scripted"), ("shop", "oracle", 1, "x")):
            with self.assertRaises(ValueError):
                runner.run(*args)


if __name__ == "__main__":
    unittest.main()
