import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import fakeclaude  # noqa: E402
from murmuration import runner, spend  # noqa: E402


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

    def test_claude_refused_without_opt_in(self):
        with self.assertRaisesRegex(RuntimeError, "allow_backend"):
            runner.run("shop", "oracle", 1, "claude")
        with self.assertRaisesRegex(RuntimeError, "spend_ledger"):
            runner.run("shop", "oracle", 1, "claude", allow_backend=True)

    def _sheet(self, d):
        p = os.path.join(d, "ps.json")
        with open(p, "w") as f:
            json.dump({"fetched": datetime.now(timezone.utc).date().isoformat(), "source_url": "https://x",
                       "models": {"claude-sonnet-5-5": {"input": 2, "output": 10, "cache_read": 0.1,
                                                        "cache_write_5m": 2.5, "cache_write_1h": 4}}}, f)
        return p

    def test_claude_backend_against_fake_server(self):
        d = tempfile.mkdtemp()
        sql = {"v": "SELECT COUNT(*) FROM orders"}
        srv, url, seen = fakeclaude.start(lambda *a: fakeclaude.ok("claude-sonnet-5-5", sql["v"]))
        try:
            kw = dict(allow_backend=True, spend_ledger=os.path.join(d, "l.jsonl"), price_sheet=self._sheet(d),
                      api_key="sk-fake", base_url=url, allow_host="127.0.0.1", max_calls=40)
            r = runner.run("shop", "oracle", 1, "claude", **kw)
            self.assertEqual(len(seen), 40)
            self.assertEqual((r["tokens"]["input"], r["tokens"]["cache_read"], r["tokens_method"]), (4000, 2000, "api usage"))
            self.assertIsNone(r["void"])
            self.assertEqual(r["models_returned"], ["claude-sonnet-5-5"])
            self.assertGreater(r["manifest"]["price_sheet_source"]["sha256"], "")
            kw["spend_ledger"] = os.path.join(d, "l2.jsonl")
            kw["max_calls"] = 3
            with self.assertRaises(spend.MaxCallsExceeded):
                runner.run("shop", "oracle", 1, "claude", **kw)
        finally:
            srv.shutdown()

    def test_claude_mismatch_voids_record(self):
        d = tempfile.mkdtemp()
        srv, url, seen = fakeclaude.start(lambda *a: fakeclaude.ok("some-other-model"))
        try:
            r = runner.run("shop", "oracle", 1, "claude", allow_backend=True, spend_ledger=os.path.join(d, "l.jsonl"),
                           price_sheet=self._sheet(d), api_key="sk-fake", base_url=url, allow_host="127.0.0.1")
            self.assertIsNotNone(r["void"])
            self.assertIsNone(r["score"])
            self.assertEqual(len(seen), 1)
        finally:
            srv.shutdown()

    def test_d9_run_usd_includes_retry_cost(self):
        d = tempfile.mkdtemp()
        led = os.path.join(d, "l.jsonl")
        r, seen = fakeclaude.dry_run("shop", "oracle", 1, led, self._sheet(d),
                                     responder=lambda p, h, b, n: (529, {}) if n == 1 else fakeclaude.ok("claude-sonnet-5-5"),
                                     max_calls=60)
        spent = spend.Ledger(led, spend.PriceSheet.load(self._sheet(d))).totals()["spent_usd"]
        self.assertAlmostEqual(r["usd"], spent)  # ledger total, retried attempt included
        self.assertEqual(len(seen), 41)

    def test_dry_run_is_fake_server_only(self):
        d = tempfile.mkdtemp()
        r, seen = fakeclaude.dry_run("shop", "oracle", 1, os.path.join(d, "l.jsonl"), self._sheet(d), api_key="sk-ant-REAL-LOOKING")
        self.assertEqual(len(seen), 40)
        self.assertEqual({{k.lower(): v for k, v in s["headers"].items()}["x-api-key"] for s in seen}, {"dry-run-no-key"})  # a supplied key is discarded
        with self.assertRaisesRegex(RuntimeError, "loopback"):
            runner.run("shop", "oracle", 1, "claude", allow_backend=True, dry_run=True, base_url="https://api.anthropic.com",
                       spend_ledger=os.path.join(d, "m.jsonl"), price_sheet=self._sheet(d), api_key="sk-x")

    def test_runner_cannot_raise_hard_cap(self):
        d = tempfile.mkdtemp()
        with self.assertRaises(spend.SpendError):
            fakeclaude.dry_run("shop", "oracle", 1, os.path.join(d, "l.jsonl"), self._sheet(d), ceiling=1000)

    def test_bad_args(self):
        for args in (("nope", "oracle", 1, "scripted"), ("shop", "x", 1, "scripted"), ("shop", "oracle", 1, "x")):
            with self.assertRaises(ValueError):
                runner.run(*args)


if __name__ == "__main__":
    unittest.main()
