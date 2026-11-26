"""Tests for lab.r6_p0_probe. A FakeClient follows the revised client contract (one client, per-call
max_tokens, reasoning_tokens, remaining_wall_s); nothing opens a socket, so no address is contacted."""
import hashlib
import json
import os
import statistics
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from lab import r6_inkling_client as rc
from lab import r6_p0_probe as p0

STOPS = dict(rc.P0_STOPS)
MSGS = {s: [{"role": "user", "content": f"synthetic {s}"}] for s in p0.SIZES}


class FakeClient:
    """script: one dict per call: wall, error, skip, tps, ct, rt, content, refuse. Advances a fake clock."""
    def __init__(self, sink, now, script, *, max_tokens=300, timeout=300.0, skip_wait=60.0, wall_left=900.0,
                 remote=False, gate_args=None):
        self._sink, self._now, self.script = sink, now, script
        self._max_tokens, self._timeout, self._skip_wait = max_tokens, timeout, skip_wait
        self._wall_left, self._remote, self._gate_args = wall_left, remote, gate_args
        self._claimed, self.calls, self.claims = False, [], 0

    def claim(self):
        self.claims += 1
        self._claimed = True

    def remaining_wall_s(self):
        return self._wall_left - self._now[0]

    def call(self, messages, *, max_tokens=None, seed=None):
        i = len(self.calls)
        self.calls.append({"max_tokens": max_tokens, "seed": seed, "messages": messages})
        sp = (self.script[i] if i < len(self.script) else self.script[-1])
        if sp.get("refuse"):
            raise rc.ClientRefused("refused")
        w = sp.get("wall", 1.0)
        self._now[0] += w
        err = sp.get("error")
        r = {"wall_s": w, "prompt_tokens": 10, "completion_tokens": sp.get("ct", 20),
             "reasoning_tokens": sp.get("rt"), "queue_wait_s": sp.get("wait", 0.0),
             "tokens_per_s": sp.get("tps", 10.0), "finish_reason": "stop", "error": err,
             "skip": sp.get("skip", False), "status": None}
        self._sink.append(r)
        if err:
            raise rc.CallFailed(err)
        return {"content": sp.get("content", "same"), "finish_reason": "stop", "trace": dict(r)}


def rec(wall, tps=10.0, ct=20, error=None, skip=False, wait=0.0, rt=None):
    return {"wall_s": wall, "tokens_per_s": tps, "completion_tokens": ct, "error": error,
            "skip": skip, "queue_wait_s": wait, "reasoning_tokens": rt}


class Proc:
    """Fake /proc tree in a TemporaryDirectory plus a GGUF file."""
    def __init__(self, tmp, pid=4242, ticks=777, exe=b"binary-A", maps_path=None, extra_pid=None):
        self.root = os.path.join(tmp, "proc")
        self.gguf = os.path.join(tmp, "m.gguf")
        with open(self.gguf, "wb") as f:
            f.write(b"gguf-bytes")
        self.exe_file = os.path.join(tmp, "exe-file")
        with open(self.exe_file, "wb") as f:
            f.write(exe)
        st = os.stat(self.gguf)
        self.dev = f"{os.major(st.st_dev):02x}:{os.minor(st.st_dev):02x}"
        os.makedirs(self.root)
        for p in [pid] + ([extra_pid] if extra_pid else []):
            d = os.path.join(self.root, str(p))
            os.makedirs(d)
            with open(os.path.join(d, "maps"), "w") as f:
                f.write(f"7f00-7f10 r--s 00000000 {self.dev} {st.st_ino} {maps_path or self.gguf}\n")
            with open(os.path.join(d, "stat"), "w") as f:
                f.write(f"{p} (llama server) S " + " ".join(["0"] * 18) + f" {ticks} 0 0\n")
            with open(os.path.join(d, "cmdline"), "wb") as f:
                f.write(b"llama-server\x00-c\x00262144\x00--parallel\x001\x00")
            os.symlink(self.exe_file, os.path.join(d, "exe"))
        os.makedirs(os.path.join(self.root, "self"))  # non-numeric entry is ignored


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.proc = Proc(self.tmp.name)
        self.frozen = p0.identity_snapshot(self.proc.root, self.proc.gguf)
        self.freeze_path = os.path.join(self.tmp.name, "freeze.json")
        self.adm_path = os.path.join(self.tmp.name, "adm.json")
        self.write_freeze()
        self.write_adm()

    def tearDown(self):
        self.tmp.cleanup()

    def write_freeze(self, **over):
        d = {"batch": "r6-p0", "model_snapshot": self.frozen,
             "protected_inputs": [{"path": f"p{s}", "sha256": p0.prompt_sha256(m), "custodian": "c"}
                                  for s, m in MSGS.items()]}
        d.update(over)
        with open(self.freeze_path, "w") as f:
            json.dump(d, f)

    def write_adm(self, batch="r6-p0"):
        with open(self.adm_path, "w") as f:
            json.dump({"batch": batch}, f)

    def run_p0(self, script=None, client_kw=None, prompts=None, **kw):
        self.sink, self.now = [], [0.0]
        self.client = FakeClient(self.sink, self.now, script or [{}], **(client_kw or {}))
        a = dict(sink=self.sink, seed=7, stops=STOPS, freeze_path=self.freeze_path,
                 admission_path=self.adm_path, proc_root=self.proc.root, gguf_path=self.proc.gguf,
                 clock=lambda: self.now[0])
        a.update(kw)
        return p0.run_p0(self.client, prompts or MSGS, **a)


class Identity(Base):
    def test_snapshot_fields(self):
        s = self.frozen
        self.assertEqual((s["pid"], s["start_ticks"]), (4242, 777))
        self.assertEqual(s["exe_sha256"], hashlib.sha256(b"binary-A").hexdigest())
        self.assertEqual(s["cmdline"], ["llama-server", "-c", "262144", "--parallel", "1"])
        st = os.stat(self.proc.gguf)
        self.assertEqual((s["gguf_inode"], s["gguf_size"], s["gguf_mtime_ns"], s["gguf_dev"]),
                         (st.st_ino, st.st_size, st.st_mtime_ns, self.proc.dev))

    def test_matches_same_and_each_field_differs(self):
        self.assertTrue(p0.identity_matches(self.frozen, dict(self.frozen)))
        for k in self.frozen:
            b = dict(self.frozen)
            b[k] = ["x"] if isinstance(b[k], list) else "x" if isinstance(b[k], str) else b[k] + 1
            self.assertFalse(p0.identity_matches(self.frozen, b), k)
        b = dict(self.frozen)
        del b["pid"]
        self.assertFalse(p0.identity_matches(self.frozen, b))
        self.assertFalse(p0.identity_matches(self.frozen, None))

    def test_same_path_other_inode_or_device_not_matched(self):
        for dev, ino in ((self.proc.dev, 1), ("ff:ff", os.stat(self.proc.gguf).st_ino)):
            with open(os.path.join(self.proc.root, "4242", "maps"), "w") as f:
                f.write(f"7f00-7f10 r--s 0 {dev} {ino} {self.proc.gguf}\n")
            with self.assertRaises(rc.ClientRefused):
                p0.identity_snapshot(self.proc.root, self.proc.gguf)

    def test_no_process_or_two_processes_refuse(self):
        with tempfile.TemporaryDirectory() as t:
            pr = Proc(t, maps_path="/other/file.gguf")
            with self.assertRaises(rc.ClientRefused):
                p0.identity_snapshot(pr.root, pr.gguf)
        with tempfile.TemporaryDirectory() as t:
            pr = Proc(t, extra_pid=99)
            with self.assertRaises(rc.ClientRefused):
                p0.identity_snapshot(pr.root, pr.gguf)

    def test_mismatch_stops_before_claim_and_call(self):
        d = os.path.join(self.proc.root, "4242")
        good = {self.proc.exe_file: b"binary-A", os.path.join(d, "cmdline"): open(os.path.join(d, "cmdline"), "rb").read(),
                os.path.join(d, "stat"): open(os.path.join(d, "stat"), "rb").read()}
        bad = {"exe": (self.proc.exe_file, b"binary-B"), "cmdline": (os.path.join(d, "cmdline"), b"llama-server\x00-c\x00999\x00"),
               "stat": (os.path.join(d, "stat"), b"4242 (x) S " + b" ".join([b"0"] * 18) + b" 778 0\n")}
        for name, (path, data) in bad.items():
            for pth, g in good.items():
                with open(pth, "wb") as f:
                    f.write(g)
            with open(path, "wb") as f:
                f.write(data)
            with self.assertRaises(rc.StopRule, msg=name):
                self.run_p0(client_kw=dict(remote=True, gate_args=(self.freeze_path, self.adm_path)))
            self.assertEqual((self.client.calls, self.client.claims), ([], 0))

    def test_unreadable_identity_stops(self):
        with self.assertRaises(rc.StopRule):
            self.run_p0(proc_root=os.path.join(self.tmp.name, "nope"))
        self.assertEqual(self.client.calls, [])


class Preconditions(Base):
    def refused(self, **kw):
        with self.assertRaises(rc.ClientRefused, msg=str(kw)):
            self.run_p0(**kw)
        self.assertEqual((self.client.calls, self.client.claims), ([], 0))

    def test_batch_id_must_be_r6_p0_in_freeze_and_admission(self):
        self.write_freeze(batch="r6-b0")
        self.refused()
        self.write_freeze()
        self.write_adm("r6-b0")
        self.refused()

    def test_freeze_snapshot_not_a_caller_dict(self):
        self.write_freeze(model_snapshot={"pid": 1})
        self.refused()
        self.write_freeze(model_snapshot=None)
        self.refused()
        with open(self.freeze_path, "w") as f:
            f.write("{not json")
        self.refused()

    def test_prompt_not_in_manifest_refused(self):
        other = dict(MSGS)
        other[1000] = [{"role": "user", "content": "unsealed"}]
        self.refused(prompts=other)
        self.write_freeze(protected_inputs=[])
        self.refused()

    def test_remote_client_on_other_records_or_already_claimed_refused(self):
        self.refused(client_kw=dict(remote=True, gate_args=("other.json", self.adm_path)))
        with self.assertRaises(rc.ClientRefused):
            self.sink, self.now = [], [0.0]
            c = FakeClient(self.sink, self.now, [{}], remote=True, gate_args=(self.freeze_path, self.adm_path))
            c._claimed = True
            p0.run_p0(c, MSGS, sink=self.sink, seed=1, stops=STOPS, freeze_path=self.freeze_path,
                      admission_path=self.adm_path, proc_root=self.proc.root, gguf_path=self.proc.gguf)
        self.assertEqual(c.calls, [])

    def test_remote_claim_happens_once_after_checks(self):
        r = self.run_p0(client_kw=dict(remote=True, gate_args=(self.freeze_path, self.adm_path)))
        self.assertEqual(self.client.claims, 1)
        self.assertIsNone(r["stopped"])

    def test_loopback_client_never_claims(self):
        self.run_p0()
        self.assertEqual(self.client.claims, 0)

    def test_stop_values_above_plan_refused(self):
        for k, v in (("max_wall_s", 901.0), ("max_errors", 3), ("max_calls", 13), ("max_skips", 3),
                     ("skip_wait_s", 61.0), ("timeout_s", 301.0)):
            self.refused(stops=dict(STOPS, **{k: v}))
        self.refused(stops={"max_calls": 12})
        self.refused(stops=dict(STOPS, max_errors=0))

    def test_client_timeout_and_skip_wait_checked(self):
        self.refused(client_kw=dict(timeout=301.0))
        self.refused(client_kw=dict(skip_wait=61.0))
        self.refused(client_kw=dict(timeout=100.0), stops=dict(STOPS, timeout_s=50.0))
        self.refused(client_kw=dict(max_tokens=64))

    def test_inputs_refused(self):
        self.refused(seed=-1)
        self.refused(seed=True)
        self.refused(prompts={200: MSGS[200]})
        self.refused(sink=[])  # not the client's sink


class Sequence(Base):
    def test_full_run_order_caps_seed_and_summary(self):
        script = [{"wall": 5.0, "rt": 4, "ct": 20}] * 11 + [{"wall": 20.0, "tps": 1.5, "rt": None}]
        r = self.run_p0(script)
        self.assertIsNone(r["stopped"])
        self.assertEqual(len(r["traces"]), 12)
        got = [(c["messages"], c["max_tokens"], c["seed"]) for c in self.client.calls]
        want = [(MSGS[s], cap, 7) for _ in range(2) for s in p0.SIZES for cap in p0.CAPS]
        self.assertEqual(got, want)  # repeats outermost: six cells, then the same six again
        self.assertEqual(r["repeat_matches"], [True] * 6)
        s = p0.summarise(r["traces"], r["repeat_matches"], r["stopped"])
        self.assertEqual((s["n_calls"], s["n_ok"], s["n_errors"], s["skip_rate"]), (12, 12, 0, 0.0))
        self.assertEqual((s["wall_max_s"], s["wall_p50_s"], s["wall_total_s"]), (20.0, 5.0, 75.0))
        self.assertEqual(s["tokens_per_s_min"], 1.5)
        self.assertEqual((s["reasoning_known"], s["reasoning_unknown"]), (11, 1))
        self.assertEqual(s["reasoning_per_call"], [0.2] * 11 + [None])
        self.assertAlmostEqual(s["reasoning_share"], 0.2)

    def test_seed_bound_32_bit(self):
        self.run_p0(seed=2 ** 32 - 1)
        with self.assertRaises(rc.ClientRefused):
            self.run_p0(seed=2 ** 32)
        self.assertEqual(self.client.calls, [])

    def test_result_carries_cmdline_temperature(self):
        self.assertIsNone(self.run_p0()["default_temperature"])  # fake cmdline has no --temp
        with open(os.path.join(self.proc.root, "4242", "cmdline"), "wb") as f:
            f.write(b"llama-server\x00--temp\x000.6\x00")
        self.frozen = p0.identity_snapshot(self.proc.root, self.proc.gguf)
        self.write_freeze()
        self.assertEqual(self.run_p0()["default_temperature"], 0.6)

    def test_repeat_mismatch_recorded(self):
        r = self.run_p0([{"content": "a"}] + [{"content": "b"}] * 5 + [{"content": "x"}] + [{"content": "b"}] * 5)
        self.assertEqual(r["repeat_matches"][0], False)
        self.assertEqual(r["repeat_matches"][1:], [True] * 5)

    def test_two_errors_stop_total_not_consecutive(self):
        r = self.run_p0([{}, {"error": "http 500"}, {}, {"error": "http 500"}, {}])
        self.assertEqual(r["stopped"], "errors")
        self.assertEqual(len(r["traces"]), 4)

    def test_one_error_does_not_stop(self):
        r = self.run_p0([{"error": "http 500"}, {}])
        self.assertIsNone(r["stopped"])
        self.assertEqual(len(r["traces"]), 12)

    def test_skip_spike_stops_after_two(self):
        r = self.run_p0([{"skip": True, "wall": 70.0}])
        self.assertEqual(r["stopped"], "skip spike")
        self.assertEqual(len(r["traces"]), 2)

    def test_wall_budget_never_exceeded(self):
        # 3 calls of 290 s leave 30 s < the 300 s per-call timeout: the fourth call must not start
        r = self.run_p0([{"wall": 290.0}])
        self.assertEqual(r["stopped"], "wall budget below the per-call timeout")
        self.assertEqual(len(r["traces"]), 3)  # 320 s left after two calls, 30 s after three
        self.assertLessEqual(r["wall_total_s"], 900.0)

    def test_driver_checks_its_own_wall_budget(self):
        r = self.run_p0([{"wall": 100.0}], stops=dict(STOPS, max_wall_s=400.0))
        self.assertEqual((r["stopped"], len(r["traces"])), ("wall budget below the per-call timeout", 2))

    def test_client_own_remaining_wall_checked(self):
        r = self.run_p0([{"wall": 60.0}], client_kw=dict(wall_left=350.0))
        self.assertEqual(r["stopped"], "wall budget below the per-call timeout")
        self.assertEqual(len(r["traces"]), 1)

    def test_max_calls_stop(self):
        r = self.run_p0(stops=dict(STOPS, max_calls=5))
        self.assertEqual(r["stopped"], "max_calls reached")
        self.assertEqual(len(r["traces"]), 5)

    def test_client_refusal_midrun_still_returns_dict(self):
        r = self.run_p0([{}, {}, {"refuse": True}])
        self.assertEqual(r["stopped"], "refused")
        self.assertEqual(len(r["traces"]), 2)


class Numbers(unittest.TestCase):
    def good(self):
        return [rec(10.0 + i) for i in range(12)]  # walls 10..21

    def test_summary_known_values(self):
        t = self.good()
        t[3] = rec(30.0, tps=2.5, wait=61.0, skip=True, rt=10, ct=20)
        s = p0.summarise(t)
        self.assertEqual(s["wall_max_s"], 30.0)
        self.assertEqual(s["wall_p50_s"], statistics.median([r["wall_s"] for r in t]))
        self.assertEqual(s["tokens_per_s_min"], 2.5)
        self.assertEqual(s["queue_wait_max_s"], 61.0)
        self.assertAlmostEqual(s["skip_rate"], 1 / 12)
        self.assertAlmostEqual(s["wall_total_s"], sum(r["wall_s"] for r in t))
        self.assertAlmostEqual(s["tokens_per_s_wall_min"], 20 / 30.0)
        self.assertEqual((s["reasoning_known"], s["reasoning_unknown"], s["reasoning_share"]), (1, 11, 0.5))

    def test_reasoning_all_unknown_is_none_not_zero(self):
        s = p0.summarise(self.good())
        self.assertIsNone(s["reasoning_share"])
        self.assertEqual(s["reasoning_per_call"], [None] * 12)

    def test_error_counts_in_T_but_not_rate(self):
        t = self.good() + [rec(300.0, tps=None, error="per-call timeout", wait=None)]
        t[-1]["completion_tokens"] = None
        s = p0.summarise(t)
        self.assertEqual((s["n_errors"], s["wall_max_s"], s["wall_max_ok_s"]), (1, 300.0, 21.0))
        self.assertIsNone(p0.summarise([rec(1.0, tps=None, wait=None)])["queue_wait_max_s"])

    def test_summarise_refuses(self):
        for bad in ([], None, [rec(float("nan"))], [rec(True)], [rec(-1.0)], [rec(float("inf"))]):
            with self.assertRaises(rc.ClientRefused):
                p0.summarise(bad)

    def test_b0_formula_and_exact_T(self):
        s = p0.summarise(self.good())  # T = 21
        r = p0.b0_cost_estimate(s, 28, 600)
        self.assertEqual(r, {"gpu_hours": (28 * 21.0 + 600) / 3600, "t_s": 21.0, "t_is_bound": False})
        self.assertEqual(p0.b0_cost_estimate(s, 1, 0)["gpu_hours"], 21.0 / 3600)

    def test_b0_fast_error_bounds_T_by_timeout(self):
        tr = self.good()[:11] + [rec(0.01, error="http 500", tps=None, wait=None)]
        r = p0.b0_cost_estimate(p0.summarise(tr), 28, 0)
        self.assertEqual((r["t_s"], r["t_is_bound"]), (300.0, True))
        self.assertEqual(r["gpu_hours"], 28 * 300.0 / 3600)

    def test_reasoning_above_completion_is_invalid(self):
        tr = self.good()
        tr[0] = rec(10.0, ct=20, rt=21)
        tr[1] = rec(11.0, ct=20, rt=20)
        s = p0.summarise(tr)
        self.assertEqual((s["reasoning_invalid"], s["reasoning_known"], s["reasoning_share"]), (1, 1, 1.0))
        self.assertIsNone(s["reasoning_per_call"][0])
        self.assertEqual(s["reasoning_per_call"][1], 1.0)

    def test_summary_carries_reasoning_note_and_temperature(self):
        s = p0.summarise(self.good(), default_temperature=0.8)
        self.assertIn("unverified for this build", s["reasoning_note"])
        self.assertEqual(s["default_temperature"], 0.8)
        self.assertIsNone(p0.summarise(self.good())["default_temperature"])

    def test_cmdline_temperature(self):
        f = p0.cmdline_temperature
        self.assertEqual(f(["x", "--temp", "0.7"]), 0.7)
        self.assertEqual(f(["x", "--temperature=0.3"]), 0.3)
        for bad in (["x"], ["x", "--temp"], ["x", "--temp", "hot"], ["x", "--temp", "nan"], ["--temp", "-1"], []):
            self.assertIsNone(f(bad), bad)

    def test_b0_one_tolerated_error_reports_bound(self):
        t = self.good()[:11] + [rec(300.0, error="http 500", tps=None, wait=None)]
        r = p0.b0_cost_estimate(p0.summarise(t), 28, 0)
        self.assertTrue(r["t_is_bound"])
        self.assertEqual(r["t_s"], 300.0)

    def test_b0_refuses(self):
        s = p0.summarise(self.good())
        short = p0.summarise(self.good()[:11])
        two = p0.summarise(self.good()[:10] + [rec(5.0, error="e"), rec(5.0, error="e")])
        stopped = p0.summarise(self.good(), stopped="skip spike")
        for sm in (short, two, stopped, {}, None, dict(s, wall_max_s=0)):
            with self.assertRaises(rc.ClientRefused):
                p0.b0_cost_estimate(sm, 28, 0)
        for calls, load in ((0, 0), (True, 0), (2.5, 0), (28, -1), (28, True), (28, float("nan")),
                            (28, float("inf")), (28, None), (None, 0)):
            with self.assertRaises(rc.ClientRefused, msg=f"{calls} {load}"):
                p0.b0_cost_estimate(s, calls, load)


class SH(BaseHTTPRequestHandler):
    """127.0.0.1 stub; script[i] = {status, delay, content, ct, rt, pm, gm} for request i."""
    def log_message(self, *a):
        pass

    def do_POST(self):
        srv = self.server
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        with srv.lock:
            i = len(srv.bodies)
            srv.bodies.append(body)
        sp = srv.script[min(i, len(srv.script) - 1)]
        time.sleep(sp.get("delay", 0))
        if sp.get("status", 200) != 200:
            self.send_response(sp["status"])
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        usage = {"prompt_tokens": 10, "completion_tokens": sp.get("ct", 20)}
        if "rt" in sp:
            usage["completion_tokens_details"] = {"reasoning_tokens": sp["rt"]}
        out = json.dumps({"choices": [{"message": {"content": sp.get("content", "same")}, "finish_reason": "stop"}],
                          "usage": usage, "timings": {"prompt_ms": 10, "predicted_ms": 100}}).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)


TEXTS = {s: f"sealed synthetic prompt {s}" for s in p0.SIZES}


class Integration(Base):
    """The REAL InklingClient (stub=True) against a loopback stub."""
    def setUp(self):
        super().setUp()
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), SH)
        self.srv.daemon_threads = True
        self.srv.bodies, self.srv.script, self.srv.lock = [], [{}], threading.Lock()
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}"
        self.write_freeze(protected_inputs=[{"path": f"p{s}", "sha256": p0.prompt_sha256(x), "custodian": "c"}
                                            for s, x in TEXTS.items()])

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        super().tearDown()

    def real(self, **kw):
        self.sink = []
        a = dict(admission_path=None, repo_root=None, allow_remote=False, timeout_s=5, max_tokens=300,
                 stub=True, max_calls=12, max_wall_s=900, max_total_tokens=10**6, max_errors=2,
                 max_skips=2, skip_wait_s=60, max_response_bytes=10**5, sink=self.sink, trace_path=None,
                 freeze_path=None, gate_caps=None)
        a.update(kw)
        self.client = rc.InklingClient(self.url, **a)
        return self.client

    def go(self, client=None, **kw):
        c = client or self.real()
        a = dict(sink=self.sink, seed=7, stops=STOPS, freeze_path=self.freeze_path,
                 admission_path=self.adm_path, proc_root=self.proc.root, gguf_path=self.proc.gguf)
        a.update(kw)
        self.client.claims = 0
        self.client.claim = lambda: self.fail("claim called on loopback")
        return p0.run_p0(c, TEXTS, **a)

    def test_full_sequence(self):
        self.srv.script = [{"rt": 5, "ct": 20}] * 11 + [{"ct": 20}]  # last call reports no reasoning tokens
        r = self.go()
        self.assertIsNone(r["stopped"])
        self.assertEqual(len(r["traces"]), len(self.srv.bodies))
        self.assertEqual(len(r["traces"]), 12)
        want = [(TEXTS[s], cap) for _ in range(2) for s in p0.SIZES for cap in p0.CAPS]
        got = [(b["messages"], b["max_tokens"]) for b in self.srv.bodies]
        self.assertEqual(got, [([{"role": "user", "content": x}], cap) for x, cap in want])
        self.assertEqual({b["seed"] for b in self.srv.bodies}, {7})
        self.assertIs(self.client._sink, self.sink)
        s = p0.summarise(r["traces"], r["repeat_matches"], r["stopped"])
        self.assertEqual((s["reasoning_known"], s["reasoning_unknown"]), (11, 1))
        self.assertAlmostEqual(s["reasoning_share"], 0.25)
        self.assertEqual(s["reasoning_per_call"], [0.25] * 11 + [None])
        self.assertEqual(r["repeat_matches"], [True] * 6)
        self.assertEqual(p0.b0_cost_estimate(s, 28, 0)["t_is_bound"], False)

    def test_identity_mismatch_zero_requests(self):
        open(self.proc.exe_file, "wb").write(b"swapped")
        with self.assertRaises(rc.StopRule):
            self.go()
        self.assertEqual(self.srv.bodies, [])

    def test_two_errors_real_stop(self):
        self.srv.script = [{}, {"status": 500}, {}, {"status": 500}, {}]
        r = self.go()
        self.assertEqual(r["stopped"], "errors")
        self.assertEqual((len(r["traces"]), len(self.srv.bodies)), (4, 4))
        self.assertEqual(self.client.stats()["errors"], 2)

    def test_client_own_stop_is_reported_not_raised(self):
        # a client built tighter than the driver stops first; its StopRule comes back as a stop reason
        r = self.go(self.real(max_calls=3))
        self.assertEqual(r["stopped"], "max_calls reached")
        self.assertEqual((len(r["traces"]), len(self.srv.bodies)), (3, 3))

    def test_skip_spike_real_stop(self):
        self.srv.script = [{"delay": 0.3}]
        r = self.go(self.real(skip_wait_s=0.05))
        self.assertEqual(r["stopped"], "skip spike")
        self.assertEqual((len(r["traces"]), len(self.srv.bodies)), (2, 2))

    def test_wall_budget_refusal_before_any_request(self):
        # client budget (200 s) below its own per-call timeout (300 s): no call may start
        r = self.go(self.real(timeout_s=300, max_wall_s=200))
        self.assertEqual(self.srv.bodies, [])
        self.assertTrue(r["stopped"])

    def test_first_call_works_when_remaining_wall_is_none(self):
        c = self.real()
        self.assertIsNone(c.remaining_wall_s())
        self.assertIsNone(self.go(c)["stopped"])

    def test_bare_string_is_wrapped_and_unsealed_text_refused(self):
        with self.assertRaises(rc.ClientRefused):
            p0.run_p0(
                self.real(), {**TEXTS, 1000: "unsealed"}, sink=self.sink, seed=1, stops=STOPS,
                freeze_path=self.freeze_path, admission_path=self.adm_path, proc_root=self.proc.root,
                gguf_path=self.proc.gguf)
        self.assertEqual(self.srv.bodies, [])


if __name__ == "__main__":
    unittest.main()
