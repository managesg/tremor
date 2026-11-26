"""Stub-only tests for lab.r6_inkling_client. The real Inkling address is never contacted."""
import json
import os
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

from lab import r6_inkling_client as rc

SECRET = "sk-test-SECRET-9f3"


def reply(content="hi", pt=10, ct=5, fin="stop", timings=None):
    d = {"choices": [{"message": {"content": content}, "finish_reason": fin}],
         "usage": {"prompt_tokens": pt, "completion_tokens": ct}}
    if timings is not None:
        d["timings"] = timings
    return json.dumps(d).encode()


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        srv = self.server
        n = int(self.headers.get("Content-Length", 0))
        srv.seen.append({"path": self.path, "headers": dict(self.headers), "body": self.rfile.read(n)})
        mode = srv.mode
        if mode == "redirect":
            self.send_response(302)
            self.send_header("Location", "/elsewhere")
            self.end_headers()
            return
        if mode == "trickle_headers":
            try:
                self.wfile.write(b"HTTP/1.1 200 OK\r\nX-A: ")
                for _ in range(20):
                    self.wfile.write(b"a")
                    self.wfile.flush()
                    time.sleep(0.3)
            except OSError:
                pass
            return
        if mode == "trickle":
            self.send_response(200)
            self.send_header("Content-Length", "1000")
            self.end_headers()
            try:
                for _ in range(20):
                    self.wfile.write(b" ")
                    self.wfile.flush()
                    time.sleep(0.3)
            except OSError:
                pass
            return
        if mode == "sleep":
            time.sleep(0.6)
        code, body = srv.status, srv.body
        self.send_response(code)
        self.send_header("Content-Length", str(len(body) + (1 if mode == "short" else 0)))
        self.end_headers()
        if mode == "short":
            self.close_connection = True
        try:
            self.wfile.write(body)
        except OSError:
            pass


class Base(unittest.TestCase):
    def setUp(self):
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.srv.daemon_threads = True
        self.srv.seen, self.srv.mode, self.srv.status, self.srv.body = [], "ok", 200, reply()
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}"
        self.sink = []

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()

    def mk(self, **kw):
        a = dict(admission_path=None, repo_root=None, allow_remote=False, timeout_s=5, max_tokens=64,
                 stub=True, max_calls=12, max_wall_s=900, max_total_tokens=10000,
                 max_errors=2, max_skips=2, skip_wait_s=60, max_response_bytes=100000,
                 sink=self.sink, trace_path=None, freeze_path=None, gate_caps=None)
        a.update(kw)
        return rc.InklingClient(self.url, **a)

    MSG = [{"role": "user", "content": "x"}]


class CallTests(Base):
    def test_normal_call_and_trace(self):
        self.srv.body = reply("answer", 10, 5, "length", {"prompt_ms": 100, "predicted_ms": 500})
        c = self.mk()
        out = c.call(self.MSG, seed=3)
        self.assertEqual((out["content"], out["finish_reason"]), ("answer", "length"))
        t = self.sink[0]
        self.assertEqual((t["prompt_tokens"], t["completion_tokens"], t["status"]), (10, 5, 200))
        self.assertAlmostEqual(t["tokens_per_s"], 10.0)
        self.assertGreaterEqual(t["queue_wait_s"], 0)
        self.assertIsNone(t["error"])
        self.assertTrue(t["utc"].endswith("+00:00"))
        self.assertGreater(t["wall_s"], 0)
        seen = self.srv.seen[0]
        self.assertEqual(seen["path"], "/v1/chat/completions")
        b = json.loads(seen["body"])
        self.assertEqual((b["max_tokens"], b["seed"], b["stream"]), (64, 3, False))
        self.assertEqual(c.stats()["total_tokens"], 15)

    def test_per_call_max_tokens_on_one_client(self):
        c = self.mk(max_tokens=300)
        c.call(self.MSG, max_tokens=64)
        c.call(self.MSG, max_tokens=300)
        c.call(self.MSG)
        self.assertEqual([json.loads(r["body"])["max_tokens"] for r in self.srv.seen], [64, 300, 300])
        self.assertEqual(len(self.sink), 3)

    def test_per_call_max_tokens_above_cap_or_invalid_refused(self):
        c = self.mk(max_tokens=300)
        for v in (301, 0, -1, True, 1.5, "64"):
            with self.assertRaises(rc.ClientRefused, msg=v):
                c.call(self.MSG, max_tokens=v)
        self.assertEqual(self.srv.seen, [])
        self.assertEqual(c.stats()["calls"], 0)

    def test_token_precheck_uses_per_call_value(self):
        c = self.mk(max_tokens=300, max_total_tokens=250)
        with self.assertRaises(rc.StopRule):
            c.call(self.MSG)  # 300 + prompt > 250
        c = self.mk(max_tokens=300, max_total_tokens=250)
        c.call(self.MSG, max_tokens=64)  # 64 + prompt fits

    def test_reasoning_tokens(self):
        def body(det):
            d = json.loads(reply())
            if det is not None:
                d["usage"]["completion_tokens_details"] = det
            return json.dumps(d).encode()
        cases = [({"reasoning_tokens": 7}, 7), ({"reasoning_tokens": 0}, 0), (None, None), ({}, None),
                 ({"reasoning_tokens": -1}, None), ({"reasoning_tokens": "3"}, None),
                 ({"reasoning_tokens": 2.5}, None), ({"reasoning_tokens": True}, None),
                 ({"reasoning_tokens": None}, None), ("x", None)]
        for det, want in cases:
            self.srv.body = body(det)
            sink = []
            out = self.mk(sink=sink).call(self.MSG)
            self.assertEqual(out["reasoning_tokens"], want, det)
            self.assertEqual(sink[0]["reasoning_tokens"], want, det)

    def test_queue_wait_is_wall_minus_server_times(self):
        self.srv.mode = "sleep"  # server holds the reply 0.6 s
        self.srv.body = reply(timings={"prompt_ms": 100, "predicted_ms": 100})
        self.mk().call(self.MSG)
        self.assertTrue(0.33 < self.sink[0]["queue_wait_s"] < 0.47, self.sink[0]["queue_wait_s"])

    def test_env_proxy_ignored(self):
        with mock.patch.dict(os.environ, {"http_proxy": "http://127.0.0.1:9", "HTTP_PROXY": "http://127.0.0.1:9"}):
            self.assertEqual(self.mk().call(self.MSG)["content"], "hi")

    def test_tokens_per_s_without_timings_uses_wall(self):
        self.mk().call(self.MSG)
        self.assertIsNone(self.sink[0]["queue_wait_s"])
        self.assertGreater(self.sink[0]["tokens_per_s"], 0)

    def test_timeout(self):
        self.srv.mode = "sleep"
        c = self.mk(timeout_s=0.2)
        with self.assertRaises(rc.CallFailed):
            c.call(self.MSG)
        self.assertIsNotNone(self.sink[0]["error"])
        self.assertIsNone(self.sink[0]["prompt_tokens"])
        self.assertEqual(c.stats()["total_tokens"], 0)

    def test_http_500_and_no_success_stored(self):
        self.srv.status, self.srv.body = 500, b"boom"
        with self.assertRaises(rc.CallFailed):
            self.mk().call(self.MSG)
        self.assertEqual(self.sink[0]["status"], 500)
        self.assertIn("500", self.sink[0]["error"])
        self.assertNotIn("boom", json.dumps(self.sink))

    def test_malformed_json_and_shapes(self):
        for body in (b"{not json", b"[]", b'{"choices":[],"usage":{}}',
                     json.dumps({"choices": [{"message": {"content": "x"}, "finish_reason": "stop"}],
                                 "usage": {"prompt_tokens": "1", "completion_tokens": 1}}).encode(),
                     json.dumps({"choices": [{"message": {"content": None}, "finish_reason": "stop"}],
                                 "usage": {"prompt_tokens": 1, "completion_tokens": 1}}).encode()):
            self.srv.body = body
            c = self.mk(sink=[])
            with self.assertRaises(rc.CallFailed):
                c.call(self.MSG)
            self.assertEqual(c.stats()["total_tokens"], 0)

    def test_oversized_response(self):
        self.srv.body = reply("x" * 5000)
        with self.assertRaises(rc.CallFailed) as cm:
            self.mk(max_response_bytes=1000).call(self.MSG)
        self.assertIn("too large", str(cm.exception))

    def test_redirect_refused(self):
        self.srv.mode = "redirect"
        with self.assertRaises(rc.CallFailed) as cm:
            self.mk().call(self.MSG)
        self.assertIn("redirect", str(cm.exception))
        self.assertEqual(len(self.srv.seen), 1)

    def test_retries_option_removed(self):
        with self.assertRaises(TypeError):
            self.mk(retries=1)

    def test_trickling_server_cannot_extend_timeout(self):
        self.srv.mode = "trickle"
        c = self.mk(timeout_s=1.0)
        t = time.monotonic()
        with self.assertRaises(rc.CallFailed):
            c.call(self.MSG)
        self.assertLess(time.monotonic() - t, 1.8)

    def test_truncated_body_is_not_a_success(self):
        self.srv.mode = "short"  # valid JSON, but one byte fewer than Content-Length
        c = self.mk()
        with self.assertRaisesRegex(rc.CallFailed, "truncated"):
            c.call(self.MSG)
        self.assertEqual(c.stats()["total_tokens"], 0)

    def test_trickled_headers_cannot_extend_timeout(self):
        self.srv.mode = "trickle_headers"
        c = self.mk(timeout_s=1.0)
        t = time.monotonic()
        with self.assertRaises(rc.CallFailed):
            c.call(self.MSG)
        self.assertLess(time.monotonic() - t, 1.8)

    def test_duplicate_keys_and_nonfinite_rejected(self):
        dup = b'{"choices":[{"message":{"content":"x"},"finish_reason":"stop"}],' \
              b'"usage":{"prompt_tokens":1,"completion_tokens":1,"completion_tokens":2}}'
        nan = b'{"choices":[{"message":{"content":"x"},"finish_reason":"stop"}],' \
              b'"usage":{"prompt_tokens":1,"completion_tokens":1},"timings":{"prompt_ms":NaN,"predicted_ms":1}}'
        for body in (dup, nan, nan.replace(b"NaN", b"Infinity")):
            self.srv.body = body
            with self.assertRaises(rc.CallFailed):
                self.mk(sink=[]).call(self.MSG)

    def test_implausible_timings_fall_back_to_wall(self):
        self.srv.body = reply(timings={"prompt_ms": 90000, "predicted_ms": 90000})
        self.mk().call(self.MSG)
        t = self.sink[0]
        self.assertGreater(t["queue_wait_s"], 0)
        self.assertAlmostEqual(t["queue_wait_s"], t["wall_s"], delta=0.05)


class StopTests(Base):
    def test_errors_stop_at_total(self):
        self.srv.status, self.srv.body = 500, b""
        c = self.mk()
        for _ in range(2):
            with self.assertRaises(rc.CallFailed):
                c.call(self.MSG)
        with self.assertRaises(rc.StopRule):
            c.call(self.MSG)
        self.assertEqual(len(self.srv.seen), 2)

    def test_alternating_fail_ok_stops_at_total_errors(self):
        c = self.mk()
        for i in range(2):
            self.srv.status, self.srv.body = 500, b""
            with self.assertRaises(rc.CallFailed):
                c.call(self.MSG)
            self.srv.status, self.srv.body = 200, reply()
            if i == 0:
                c.call(self.MSG)
        with self.assertRaises(rc.StopRule):
            c.call(self.MSG)
        self.assertEqual(len(self.srv.seen), 3)

    def test_skip_spike_on_slow_queue(self):
        self.srv.body = reply(timings={"prompt_ms": 1, "predicted_ms": 1})
        c = self.mk(skip_wait_s=0.05)
        self.srv.mode = "sleep"
        for _ in range(2):
            c.call(self.MSG)
        self.assertTrue(all(t["skip"] for t in self.sink))
        self.assertEqual(c.stats()["skip_rate"], 1.0)
        with self.assertRaises(rc.StopRule):
            c.call(self.MSG)

    def test_busy_503_counts_as_skip(self):
        self.srv.status, self.srv.body = 503, b""
        c = self.mk(max_errors=9)
        for _ in range(2):
            with self.assertRaises(rc.CallFailed):
                c.call(self.MSG)
        self.assertTrue(all(t["skip"] for t in self.sink))
        with self.assertRaises(rc.StopRule):
            c.call(self.MSG)

    def test_fast_calls_are_not_skips(self):
        c = self.mk()
        c.call(self.MSG)
        self.assertFalse(self.sink[0]["skip"])
        self.assertEqual(c.stats()["skip_rate"], 0.0)

    def test_max_calls(self):
        c = self.mk(max_calls=2)
        c.call(self.MSG)
        c.call(self.MSG)
        with self.assertRaises(rc.StopRule):
            c.call(self.MSG)
        self.assertEqual(len(self.srv.seen), 2)

    def test_wall_budget(self):
        c = self.mk(max_wall_s=0.5, timeout_s=0.3)
        c.call(self.MSG)
        time.sleep(0.35)
        with self.assertRaises(rc.StopRule):
            c.call(self.MSG)

    def test_wall_below_timeout_refused_before_first_call(self):
        c = self.mk(max_wall_s=0.2, timeout_s=30)
        with self.assertRaises(rc.StopRule):
            c.call(self.MSG)
        self.assertEqual(self.srv.seen, [])
        self.assertEqual(self.sink, [])

    def test_remaining_wall_s(self):
        c = self.mk(max_wall_s=100, timeout_s=5)
        self.assertIsNone(c.remaining_wall_s())
        c.call(self.MSG)
        r1 = c.remaining_wall_s()
        self.assertTrue(98 < r1 < 100, r1)
        time.sleep(0.1)
        self.assertLess(c.remaining_wall_s(), r1)

    def test_one_clock_across_per_call_caps(self):
        c = self.mk(max_wall_s=0.6, timeout_s=0.3, max_tokens=300)
        c.call(self.MSG, max_tokens=64)
        time.sleep(0.4)
        with self.assertRaises(rc.StopRule):
            c.call(self.MSG, max_tokens=300)

    def test_token_budget(self):
        self.srv.body = reply(pt=40, ct=20)
        c = self.mk(max_total_tokens=300, max_tokens=64)
        for _ in range(3):
            c.call(self.MSG)
        self.assertEqual(c.stats()["total_tokens"], 180)
        with self.assertRaises(rc.StopRule):
            c.call(self.MSG)
        self.assertEqual(len(self.srv.seen), 3)

    def test_prompt_size_counted_before_send(self):
        c = self.mk(max_total_tokens=1000, max_tokens=64)
        with self.assertRaises(rc.StopRule):
            c.call([{"role": "user", "content": "w " * 50000}])
        self.assertEqual(self.srv.seen, [])

    def test_stop_is_sticky(self):
        c = self.mk(max_calls=1)
        c.call(self.MSG)
        for _ in range(2):
            with self.assertRaises(rc.StopRule):
                c.call(self.MSG)

    def test_plan_numbers(self):
        self.assertEqual(rc.P0_STOPS, {"max_calls": 12, "max_wall_s": 900.0, "max_errors": 2,
                                       "max_skips": 2, "skip_wait_s": 60.0, "timeout_s": 300.0})


class RefusalTests(Base):
    def test_no_defaults_for_open_parameters(self):
        with self.assertRaises(TypeError):
            rc.InklingClient(self.url)
        with self.assertRaises(TypeError):
            rc.InklingClient(self.url, admission_path=None, repo_root=None, allow_remote=False)

    def test_bad_scheme_and_url_parts(self):
        for u in ("https://127.0.0.1:1", "ftp://127.0.0.1", "127.0.0.1:8011", "http://u:p@127.0.0.1:1",
                  "http://127.0.0.1:1/?k=v", "http://127.0.0.1:99999", "", None):
            with self.assertRaises(rc.ClientRefused, msg=u):
                kw = dict(admission_path=None, repo_root=None, allow_remote=False, timeout_s=5,
                          max_tokens=64, stub=True, max_calls=1, max_wall_s=9, max_total_tokens=99,
                          max_errors=1, max_skips=1, skip_wait_s=1, max_response_bytes=9,
                          sink=[], trace_path=None, freeze_path=None, gate_caps=None)
                rc.InklingClient(u, **kw)

    def _remote(self, **kw):
        a = dict(admission_path=None, repo_root=None, allow_remote=True, timeout_s=5, max_tokens=64,
                 stub=False, max_calls=1, max_wall_s=9, max_total_tokens=99, max_errors=1,
                 max_skips=1, skip_wait_s=1, max_response_bytes=9, sink=[], trace_path=None,
                 freeze_path=None, gate_caps=None)
        a.update(kw)
        return rc.InklingClient("http://192.0.2.1:8011", **a)

    CAPS = dict(hosted_cap=0, gpu_cap=1, max_window_hours=1, owner_words="w")

    def test_nonloopback_without_admission_refused(self):
        with self.assertRaises(rc.ClientRefused):
            self._remote()
        with self.assertRaises(rc.ClientRefused):
            self._remote(allow_remote=False)

    def test_nonloopback_real_gate_refuses_missing_records(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(rc.ClientRefused):
                self._remote(admission_path="a.json", freeze_path="f.json", repo_root=d,
                             gate_caps=self.CAPS)

    def test_allow_remote_must_be_literal_true(self):
        with mock.patch.object(rc.gate, "check", return_value=True):
            for v in (1, "yes", None):
                with self.assertRaises(rc.ClientRefused):
                    self._remote(allow_remote=v, admission_path="a", freeze_path="f", repo_root="r",
                                 gate_caps=self.CAPS)

    def test_allow_remote_false_refuses_even_with_passing_gate(self):
        with mock.patch.object(rc.gate, "check", return_value=True) as ck:
            with self.assertRaises(rc.ClientRefused):
                self._remote(allow_remote=False, admission_path="a", freeze_path="f", repo_root="r",
                             gate_caps=self.CAPS)
            ck.assert_not_called()

    def test_remote_checks_never_claims_until_claim(self):
        with mock.patch.object(rc.gate, "check", return_value=True) as ck, \
                mock.patch.object(rc.gate, "admit", return_value=True) as ad:
            c = self._remote(admission_path="a", freeze_path="f", repo_root="r", gate_caps=self.CAPS,
                             max_total_tokens=100000)
            ck.assert_called_once()
            self.assertEqual(ck.call_args.args[0:2], ("f", "a"))
            self.assertEqual(ck.call_args.args[3], "r")
            self.assertEqual(ck.call_args.kwargs, self.CAPS)
            ad.assert_not_called()
            with mock.patch("socket.create_connection", side_effect=AssertionError("network")):
                with self.assertRaises(rc.ClientRefused):  # refused before any send
                    c.call([{"role": "user", "content": "x"}])
            c.claim()
            ad.assert_called_once()
            self.assertTrue(c._claimed)

    def test_failed_claim_stays_unclaimed(self):
        with mock.patch.object(rc.gate, "check", return_value=True), \
                mock.patch.object(rc.gate, "admit", side_effect=rc.gate.AdmissionRefused("used")):
            c = self._remote(admission_path="a", freeze_path="f", repo_root="r", gate_caps=self.CAPS)
            with self.assertRaises(rc.ClientRefused):
                c.claim()
            self.assertFalse(c._claimed)

    def test_loopback_claim_never_spends_admission(self):
        with mock.patch.object(rc.gate, "admit", return_value=True) as ad:
            with self.assertRaises(rc.ClientRefused):
                self.mk(admission_path="a", freeze_path="f", repo_root="r", gate_caps=self.CAPS).claim()
            with self.assertRaises(rc.ClientRefused):
                self.mk().claim()
            ad.assert_not_called()

    def _kw(self):
        return dict(admission_path=None, repo_root=None, allow_remote=False, timeout_s=5, max_tokens=64,
                    stub=True, max_calls=1, max_wall_s=9, max_total_tokens=99, max_errors=1,
                    max_skips=1, skip_wait_s=1, max_response_bytes=9, sink=[], trace_path=None,
                    freeze_path=None, gate_caps=None)

    def test_loopback_needs_explicit_stub_and_ip_literal(self):
        for v in (False, None, 1, "yes"):
            with self.assertRaises(rc.ClientRefused):
                self.mk(stub=v)
        for u in ("http://localhost:1", "http://localhost"):
            with self.assertRaisesRegex(rc.ClientRefused, "IP literal"):
                rc.InklingClient(u, **self._kw())
        rc.InklingClient("http://[::1]:1", **self._kw())

    def test_stub_true_on_remote_refused(self):
        with mock.patch.object(rc.gate, "check", return_value=True):
            with self.assertRaises(rc.ClientRefused):
                self._remote(stub=True, admission_path="a", freeze_path="f", repo_root="r",
                             gate_caps=self.CAPS)

    def test_loopback_forms(self):
        for h in ("127.0.0.1", "127.9.9.9", "[::1]"):
            self.assertTrue(rc._is_loopback(h.strip("[]")), h)
        for h in ("100.91.57.48", "10.0.0.1", "example.com", "0.0.0.0"):
            self.assertFalse(rc._is_loopback(h), h)

    def test_bad_url_path_refused_at_construction(self):
        for path in ("/a b", "/a\r\nX: y", "/a\x00", "/\u00e9"):
            with self.assertRaises(rc.ClientRefused, msg=repr(path)):
                rc.InklingClient("http://127.0.0.1:1" + path, **self._kw())
        rc.InklingClient("http://127.0.0.1:1/a/b_c-d.e~f%20", **self._kw())

    def test_bad_numbers(self):
        for k, v in (("timeout_s", 0), ("timeout_s", float("inf")), ("timeout_s", True),
                     ("max_tokens", 0), ("max_errors", 0), ("max_calls", 0),
                     ("max_total_tokens", 0), ("max_wall_s", float("nan"))):
            with self.assertRaises(rc.ClientRefused, msg=(k, v)):
                self.mk(**{k: v})

    def test_sink_or_trace_exactly_one(self):
        with self.assertRaises(rc.ClientRefused):
            self.mk(sink=None, trace_path=None)
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(rc.ClientRefused):
                self.mk(sink=[], trace_path=os.path.join(d, "t"))
        with self.assertRaises(rc.ClientRefused):
            self.mk(sink=object())

    def test_bad_messages_and_seed(self):
        c = self.mk()
        for m in (None, [], "x"):
            with self.assertRaises(rc.ClientRefused):
                c.call(m)
        with self.assertRaises(rc.ClientRefused):
            c.call(self.MSG, seed=-1)
        self.assertEqual(self.srv.seen, [])


class TraceFileTests(Base):
    def test_file_trace_excl_and_content(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "trace.jsonl")
            c = self.mk(sink=None, trace_path=p)
            c.call(self.MSG)
            self.srv.status, self.srv.body = 500, b""
            with self.assertRaises(rc.CallFailed):
                c.call(self.MSG)
            c.close()
            rows = [json.loads(l) for l in open(p)]
            self.assertEqual(len(rows), 2)
            self.assertIsNone(rows[0]["error"])
            self.assertIn("500", rows[1]["error"])
            self.assertEqual(os.stat(p).st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                self.mk(sink=None, trace_path=p)
            os.symlink(os.path.join(d, "nowhere"), os.path.join(d, "ln"))
            with self.assertRaises(OSError):
                self.mk(sink=None, trace_path=os.path.join(d, "ln"))

    def test_trace_parent_symlink_refused(self):
        with tempfile.TemporaryDirectory() as d:
            os.mkdir(os.path.join(d, "real"))
            os.symlink(os.path.join(d, "real"), os.path.join(d, "lnk"))
            with self.assertRaises(rc.ClientRefused):
                self.mk(sink=None, trace_path=os.path.join(d, "lnk", "t.jsonl"))
            self.assertEqual(os.listdir(os.path.join(d, "real")), [])

    def test_trace_write_loops_on_short_writes(self):
        real = os.write
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "t.jsonl")
            c = self.mk(sink=None, trace_path=p)
            with mock.patch.object(rc.os, "write", lambda fd, b: real(fd, bytes(b[:7]))):
                c.call(self.MSG)
            c.close()
            c.close()
            self.assertEqual(json.loads(open(p).read())["status"], 200)

    def test_context_manager_closes_fd(self):
        with tempfile.TemporaryDirectory() as d:
            with self.mk(sink=None, trace_path=os.path.join(d, "t")) as c:
                fd = c._fd
            self.assertIsNone(c._fd)
            with self.assertRaises(OSError):
                os.fstat(fd)

    def test_stats_and_claim_wait_for_lock(self):
        rem = RefusalTests("test_loopback_forms")
        with mock.patch.object(rc.gate, "check", return_value=True):
            c = rem._remote(admission_path="a", freeze_path="f", repo_root="r", gate_caps=RefusalTests.CAPS)
        s = self.mk()
        for obj, fn in ((s, s.stats), (c, c.claim)):
            done = []
            with mock.patch.object(rc.gate, "admit", return_value=True):
                with obj._lock:
                    th = threading.Thread(target=lambda: (fn(), done.append(1)))
                    th.start()
                    time.sleep(0.2)
                    self.assertEqual(done, [])
                th.join(2)
            self.assertEqual(done, [1])

    def test_sink_failure_propagates(self):
        class Bad:
            def append(self, x):
                raise RuntimeError("disk")
        with self.assertRaises(RuntimeError):
            self.mk(sink=Bad()).call(self.MSG)


class SecretTests(Base):
    def test_no_auth_header_no_env_read_no_leak(self):
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": SECRET, "KIMI_API_KEY": SECRET}):
            self.srv.status, self.srv.body = 500, SECRET.encode()
            c = self.mk()
            with self.assertRaises(rc.CallFailed) as cm:
                c.call([{"role": "user", "content": "plain"}])
            self.assertNotIn(SECRET, str(cm.exception))
            self.srv.status, self.srv.body = 200, reply()
            c.call(self.MSG)
        h = {k.lower() for r in self.srv.seen for k in r["headers"]}
        self.assertNotIn("authorization", h)
        self.assertNotIn("cookie", h)
        for r in self.srv.seen:
            self.assertNotIn(SECRET.encode(), r["body"])
        self.assertNotIn(SECRET, json.dumps(self.sink))
        self.assertNotIn("os.environ", open(rc.__file__).read())
        self.assertNotIn("getenv", open(rc.__file__).read())

    def test_trace_has_no_prompt_or_reply_text(self):
        self.srv.body = reply("REPLYTEXT")
        self.mk().call([{"role": "user", "content": "PROMPTTEXT"}])
        s = json.dumps(self.sink)
        self.assertNotIn("REPLYTEXT", s)
        self.assertNotIn("PROMPTTEXT", s)


if __name__ == "__main__":
    unittest.main()
