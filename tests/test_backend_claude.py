import glob
import json
import os
import sys
import tempfile
import unittest
from unittest import mock
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import fakeclaude  # noqa: E402
from murmuration import backend_claude as bc, spend  # noqa: E402

M = "claude-sonnet-5-5"
KEY = "sk-ant-FAKEKEY-do-not-leak-0123456789"
P = {"input": 2, "output": 10, "cache_read": 0.1, "cache_write_5m": 2.5, "cache_write_1h": 4}


class ClaudeBackendTests(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        sp = os.path.join(self.d, "ps.json")
        with open(sp, "w") as f:
            json.dump({"fetched": datetime.now(timezone.utc).date().isoformat(), "source_url": "https://x", "models": {M: P}, "aliases": {M: ["claude-sonnet-5-5-20261101"]}}, f)
        self.sheet = spend.PriceSheet.load(sp)
        self.srv = None

    def tearDown(self):
        if self.srv:
            self.srv.shutdown()

    def client(self, responder, **kw):
        self.srv, url, self.seen = fakeclaude.start(responder)
        self.led = spend.Ledger(os.path.join(self.d, "l.jsonl"), self.sheet, **kw)
        return bc.ClaudeClient(KEY, self.led, url, allow_host="127.0.0.1")

    def ep(self, tokens=80_000, secs=60):
        return bc.Episode("e1", tokens, secs)

    def msgs(self):
        return [{"role": "user", "content": "hi"}]

    def test_records_usage_and_headers(self):
        c = self.client(lambda *a: fakeclaude.ok(M))
        rec = c.call(self.ep(), "t:0", M, self.msgs(), 50, 0.0)
        self.assertEqual(rec["usage"]["cache_read_input_tokens"], 50)
        self.assertIsNone(rec["void"])
        h = {k.lower(): v for k, v in self.seen[0]["headers"].items()}
        self.assertEqual(h["anthropic-version"], "2023-06-01")
        self.assertEqual(self.seen[0]["path"], "/v1/messages")
        self.assertEqual((self.seen[0]["body"]["model"], self.seen[0]["body"]["max_tokens"], self.seen[0]["body"]["temperature"]), (M, 50, 0.0))
        charge = [e for e in self.led._lines() if e["kind"] == "charge"][0]
        self.assertEqual(charge["usage"]["cache_creation"]["ephemeral_1h_input_tokens"], 15)
        self.assertEqual(charge["returned_model"], M)

    def test_returned_model_mismatch_voids(self):
        c = self.client(lambda *a: fakeclaude.ok("glm-5.3-flash"))
        e = self.ep()
        rec = c.call(e, "t:0", M, self.msgs(), 50)
        self.assertIn("glm-5.3-flash", rec["void"])
        self.assertTrue(e.void)
        with self.assertRaises(bc.EpisodeVoided):
            c.call(e, "t:1", M, self.msgs(), 50)
        self.assertEqual(len(self.seen), 1)
        self.assertTrue([x for x in self.led._lines() if x["kind"] == "charge"][0]["void"])  # still billed

    def test_documented_alias_allowed(self):
        c = self.client(lambda *a: fakeclaude.ok("claude-sonnet-5-5-20261101"))
        self.assertIsNone(c.call(self.ep(), "t:0", M, self.msgs(), 50)["void"])

    def test_ceiling_stops_before_request(self):
        c = self.client(lambda *a: fakeclaude.ok(M), ceiling=0.0001)
        with self.assertRaises(spend.SpendCeilingExceeded):
            c.call(self.ep(), "t:0", M, self.msgs(), 5000)
        self.assertEqual(self.seen, [])

    def test_max_calls_stop(self):
        c = self.client(lambda *a: fakeclaude.ok(M), max_calls=2)
        e = self.ep()
        for i in range(2):
            c.call(e, f"t:{i}", M, self.msgs(), 50)
        with self.assertRaises(spend.MaxCallsExceeded):
            c.call(e, "t:2", M, self.msgs(), 50)
        self.assertEqual(len(self.seen), 2)

    def test_episode_caps(self):
        c = self.client(lambda *a: fakeclaude.ok(M))
        with self.assertRaises(bc.EpisodeCapExceeded):
            c.call(self.ep(tokens=100), "t:0", M, self.msgs(), 50)
        with self.assertRaises(bc.EpisodeCapExceeded):
            c.call(self.ep(secs=0), "t:0", M, self.msgs(), 50)
        self.assertEqual(self.seen, [])

    def test_retry_once_then_stop(self):
        c = self.client(lambda p, h, b, n: (529, {"error": {"message": "busy"}}) if n == 1 else fakeclaude.ok(M))
        rec = c.call(self.ep(), "t:0", M, self.msgs(), 50)
        self.assertEqual((rec["id"], len(self.seen)), ("t:0#r1", 2))
        c2 = self.client(lambda *a: (500, {}))
        with self.assertRaises(RuntimeError):
            c2.call(self.ep(), "u:0", M, self.msgs(), 50)
        self.assertEqual(len(self.seen), 2)  # first + exactly one retry
        c3 = self.client(lambda *a: (400, {"error": {"message": "bad"}}))
        with self.assertRaises(RuntimeError):
            c3.call(self.ep(), "v:0", M, self.msgs(), 50)
        self.assertEqual(len(self.seen), 1)  # 4xx is not retried

    def test_key_never_leaks(self):
        # server echoes the key in its error body; client must scrub it from exceptions and ledger
        c = self.client(lambda *a: (401, {"error": {"message": f"bad key {KEY}"}}))
        with self.assertRaises(RuntimeError) as cm:
            c.call(self.ep(), "t:0", M, self.msgs(), 50)
        self.assertNotIn(KEY, str(cm.exception))
        self.assertNotIn(KEY, repr(cm.exception))
        c = self.client(lambda *a: fakeclaude.ok(M, text="x"))
        c.call(self.ep(), "t:9", M, self.msgs(), 50)
        for p in glob.glob(os.path.join(self.d, "*")):
            self.assertNotIn(KEY, open(p).read())
        self.assertNotIn(KEY, json.dumps(c.ledger._lines()))
        self.assertNotIn(KEY, repr(vars(c.ledger)))

    def test_proxy_and_base_url_env_ignored(self):
        saved = {k: os.environ.get(k) for k in ("ANTHROPIC_BASE_URL", "HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "ALL_PROXY")}
        try:
            for k in saved:
                os.environ[k] = "http://127.0.0.1:9"  # dead port: any use would fail the call
            c = self.client(lambda *a: fakeclaude.ok(M))
            self.assertEqual(c.call(self.ep(), "t:0", M, self.msgs(), 50)["returned_model"], M)
            self.assertEqual(len(self.seen), 1)
        finally:
            for k, v in saved.items():
                os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        self.assertEqual(bc.DEFAULT_BASE_URL, "https://api.anthropic.com")

    def test_url_and_key_validation(self):
        led = spend.Ledger(os.path.join(self.d, "x.jsonl"), self.sheet)
        with self.assertRaises(ValueError):
            bc.ClaudeClient(KEY, led, "http://example.com")
        with self.assertRaises(ValueError):
            bc.ClaudeClient("", led)

    def test_d5_host_allowlist(self):
        led = spend.Ledger(os.path.join(self.d, "x.jsonl"), self.sheet)
        pilot = self._pilot()
        with mock.patch.object(spend, "PILOT_LEDGER_DIR", pilot):
            pled = spend.Ledger(os.path.join(pilot, "x.jsonl"), self.sheet)
            bc.ClaudeClient(KEY, pled)  # default host is accepted
            bc.ClaudeClient(KEY, pled, "https://api.anthropic.com/")
        for bad in ("https://evil.example", "https://api.anthropic.com.evil.example", "https://api.anthropic.com@evil.example",
                    "https://evil.example@api.anthropic.com", "http://api.anthropic.com", "https://api.anthropic.com:8443",
                    "https://api.anthropic.com/x", "http://127.0.0.1:9", "http://localhost:9"):
            with self.assertRaises(ValueError, msg=bad):
                bc.ClaudeClient(KEY, led, bad)  # loopback too: it needs allow_host
        with self.assertRaises(ValueError):  # allow_host naming another host is not enough
            bc.ClaudeClient(KEY, led, "https://evil.example", allow_host="evil.example")
        with self.assertRaises(ValueError):  # a mismatched allow_host
            bc.ClaudeClient(KEY, led, "http://127.0.0.1:9", allow_host="localhost")
        bc.ClaudeClient(KEY, led, "http://127.0.0.1:9", allow_host="127.0.0.1")

    def test_d5_redirect_not_followed(self):
        # 301/302/303 are the ones urllib follows for a POST (as a GET, copying x-api-key); 307/308 it refuses anyway
        for code in (301, 302, 303, 307, 308):
            other, ourl, oseen = fakeclaude.start(lambda *a: fakeclaude.ok(M))
            try:
                c = self.client(lambda *a: (code, {}, {"Location": ourl + "/v1/messages"}))
                with self.assertRaises(RuntimeError, msg=code):
                    c.call(self.ep(), f"t:{code}", M, self.msgs(), 50)
                self.assertEqual((len(self.seen), oseen), (1, []), msg=code)
            finally:
                other.shutdown()
                self.srv.shutdown()
                self.srv = None

    def test_r2_proxy_env_never_receives_the_key(self):
        proxy, purl, pseen = fakeclaude.start(lambda *a: fakeclaude.ok("claude-opus-5-5"))
        names = ("ANTHROPIC_BASE_URL", "HTTPS_PROXY", "HTTP_PROXY", "ALL_PROXY", "https_proxy", "http_proxy", "all_proxy")
        saved = {k: os.environ.get(k) for k in names + ("NO_PROXY", "no_proxy")}
        try:
            os.environ.pop("NO_PROXY", None), os.environ.pop("no_proxy", None)
            for k in names:
                os.environ[k] = purl
            with mock.patch.object(bc, "_OPENER", bc._build_opener()):  # built AFTER the env is set
                c = self.client(lambda *a: fakeclaude.ok(M))
                self.assertEqual(c.call(self.ep(), "t:0", M, self.msgs(), 50)["returned_model"], M)
            self.assertEqual((len(self.seen), pseen), (1, []))
            self.assertEqual({k.lower(): v for k, v in self.seen[0]["headers"].items()}["x-api-key"], KEY)
        finally:
            proxy.shutdown()
            for k, v in saved.items():
                os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)

    # R1: every ledger for api.anthropic.com lives in the one pinned directory
    def _pilot(self):
        pilot = os.path.join(os.path.realpath(tempfile.mkdtemp()), "spend")
        os.mkdir(pilot, 0o700)
        return pilot

    def _real(self, path, pilot):
        with mock.patch.object(spend, "PILOT_LEDGER_DIR", pilot):
            return bc.ClaudeClient(KEY, spend.Ledger(path, self.sheet))

    def test_r1_real_host_needs_the_pinned_dir_and_lowercase_jsonl(self):
        pilot = self._pilot()
        self._real(os.path.join(pilot, "ok.jsonl"), pilot)
        with self.assertRaises(ValueError):  # a second directory
            self._real(os.path.join(tempfile.mkdtemp(), "ok.jsonl"), pilot)
        with self.assertRaises(ValueError):  # a subdirectory of it
            self._real(os.path.join(pilot, "sub", "ok.jsonl"), pilot)
        for name in ("a.json", "b.log", "C.JSONL", "d.Jsonl", "Abc.jsonl", "e", ".hidden.jsonl"):
            with self.assertRaises(ValueError, msg=name):
                self._real(os.path.join(pilot, name), pilot)

    def test_r1_symlinks_refused(self):
        pilot = self._pilot()
        alias = os.path.join(os.path.realpath(tempfile.mkdtemp()), "alias")
        os.symlink(pilot, alias)  # same directory under another name
        with self.assertRaises(ValueError):
            self._real(os.path.join(alias, "x.jsonl"), pilot)
        with self.assertRaises(ValueError):  # the pinned directory itself is a symlink
            self._real(os.path.join(alias, "x.jsonl"), alias)
        os.symlink(os.path.join(self.d, "elsewhere.jsonl"), os.path.join(pilot, "lnk.jsonl"))
        with self.assertRaises(ValueError):  # the ledger file is a symlink
            self._real(os.path.join(pilot, "lnk.jsonl"), pilot)

    def test_r1_opus_probe_three_dirs_cannot_exceed_the_cap(self):
        opus = {"input": 4, "output": 20, "cache_read": 0.2, "cache_write_5m": 5, "cache_write_1h": 8}
        sp = os.path.join(self.d, "opus.json")
        with open(sp, "w") as f:
            json.dump({"fetched": datetime.now(timezone.utc).date().isoformat(), "source_url": "https://x",
                       "models": {"claude-opus-5-5": opus}}, f)
        sheet = spend.PriceSheet.load(sp)
        pilot, reserved = self._pilot(), 0.0
        dirs = [pilot, tempfile.mkdtemp(), tempfile.mkdtemp()]
        with mock.patch.object(spend, "PILOT_LEDGER_DIR", pilot):
            for i, d in enumerate(dirs * 3):  # old behaviour: three dirs x USD 4.08 > USD 10
                try:
                    c = bc.ClaudeClient(KEY, spend.Ledger(os.path.join(d, f"o{i}.jsonl"), sheet), allow_host=None)
                    reserved += c.ledger.reserve(f"o{i}", "claude-opus-5-5", 700_000, 64_000)
                except (ValueError, spend.SpendError):
                    pass
        self.assertLessEqual(reserved, spend.HARD_CAP_USD)
        self.assertEqual(glob.glob(os.path.join(dirs[1], "*.jsonl")) + glob.glob(os.path.join(dirs[2], "*.jsonl")), [])

    def test_d6_actual_over_reserved_marks_overspent(self):
        big = {"input_tokens": 5_000_000, "output_tokens": 10}
        c = self.client(lambda *a: fakeclaude.ok(M, usage=big))
        with self.assertRaises(spend.Overspent):
            c.call(self.ep(), "t:0", M, self.msgs(), 50)
        self.assertAlmostEqual(c.ledger.totals()["spent_usd"], 10.0001, places=3)  # the true cost is recorded
        self.assertTrue(c.ledger.totals()["overspent"])
        with self.assertRaises(spend.Overspent):
            c.call(self.ep(), "t:1", M, self.msgs(), 50)
        self.assertEqual(len(self.seen), 1)  # no second request

    def test_d6_negative_or_missing_usage_marks_overspent(self):
        for usage in ({"input_tokens": -10_000_000, "output_tokens": 5}, {"output_tokens": 5}, "junk"):
            c = self.client(lambda *a: fakeclaude.ok(M, usage=usage))
            with self.assertRaises(spend.Overspent):
                c.call(self.ep(), "t:0", M, self.msgs(), 50)
            t = c.ledger.totals()
            self.assertGreater(t["spent_usd"], 0)  # worst case kept, never negative
            self.assertTrue(t["overspent"])
            os.remove(c.ledger.path)
        c = self.client(lambda *a: (200, {"model": M, "stop_reason": "end_turn", "content": []}))  # no usage key at all
        with self.assertRaises(spend.Overspent):
            c.call(self.ep(), "t:0", M, self.msgs(), 50)

    def test_d3_nan_usage_fails_closed_without_poisoning_ledger(self):
        nan = float("nan")
        c = self.client(lambda *a: fakeclaude.ok(M, usage={"input_tokens": nan, "output_tokens": 1}))
        with self.assertRaises(spend.SpendError):
            c.call(self.ep(), "t:0", M, self.msgs(), 50)
        self.assertNotIn("NaN", open(c.ledger.path).read())
        t = c.ledger.totals()  # still readable and finite
        self.assertTrue(t["spent_usd"] > 0 and t["overspent"])
        with self.assertRaises(spend.SpendError):
            c.call(self.ep(), "t:1", M, self.msgs(), 50)
        self.assertEqual(len(self.seen), 1)

    def test_d4_max_tokens_validated_before_request(self):
        c = self.client(lambda *a: fakeclaude.ok(M))
        for bad in (-1, 0, 1.5, float("nan"), True, "9", 10**9):
            with self.assertRaises(spend.SpendError, msg=repr(bad)):
                c.call(self.ep(), f"t:{bad}", M, self.msgs(), bad)
        self.assertEqual(self.seen, [])

    def test_d7_returned_model_priced_at_the_dearer(self):
        opus = {"input": 4, "output": 20, "cache_read": 0.2, "cache_write_5m": 5, "cache_write_1h": 8}
        self.sheet.data["models"]["claude-opus-5-5"] = opus
        c = self.client(lambda *a: fakeclaude.ok("claude-opus-5-5"))
        rec = c.call(self.ep(), "t:0", M, self.msgs(), 50)
        self.assertIsNotNone(rec["void"])
        self.assertAlmostEqual(rec["usd"], 755e-6)  # Opus price for the usage, not Sonnet's 377.5e-6
        c = self.client(lambda *a: fakeclaude.ok("glm-5.3-flash"))  # unknown price: worst case, never cheaper
        os.remove(c.ledger.path)
        rec = c.call(self.ep(), "t:1", M, self.msgs(), 50)
        self.assertAlmostEqual(rec["usd"], c.ledger.totals()["reserved"]["t:1"])

    def test_d8_key_echo_never_persisted(self):
        echo = {"model": KEY, "stop_reason": f"x{KEY[:14]}", "content": [{"type": "text", "text": f"SELECT '{KEY}'"}],
                "usage": {"input_tokens": 5, "output_tokens": 5, "note": KEY, "cache_creation": {"x": KEY}}}
        c = self.client(lambda *a: (200, echo))
        rec = c.call(self.ep(), "t:0", M, self.msgs(), 50)
        self.assertIsNotNone(rec["void"])  # the echoed model is a mismatch
        for p in glob.glob(os.path.join(self.d, "*")):
            blob = open(p).read()
            self.assertNotIn(KEY, blob)
            self.assertNotIn(KEY[:14], blob)
        self.assertNotIn(KEY, repr(rec))

    def test_d9_episode_usd_includes_retry_cost(self):
        c = self.client(lambda p, h, b, n: (529, {}) if n == 1 else fakeclaude.ok(M))
        e = self.ep()
        rec = c.call(e, "t:0", M, self.msgs(), 50)
        t = c.ledger.totals()
        self.assertEqual(rec["id"], "t:0#r1")
        self.assertAlmostEqual(e.usd, t["spent_usd"])  # first attempt's worst case + second's charge
        self.assertGreater(e.usd, rec["usd"])

    def test_non_text_blocks_refused(self):
        c = self.client(lambda *a: fakeclaude.ok(M))
        img = [{"role": "user", "content": [{"type": "image", "source": {"type": "url", "url": "https://x/y.png"}}]}]
        with self.assertRaises(ValueError):
            c.call(self.ep(), "t:0", M, img, 50)
        self.assertEqual(self.seen, [])


if __name__ == "__main__":
    unittest.main()
