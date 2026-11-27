"""Tests for lab/tremor_gpu_run.py. Every behaviour is a probe(E) taking an Env bound to a module, so the
same probes run on the real launcher (must pass) and on named mutant copies under /tmp/claude-1000 (the
named killer probe must fail). The live rehearsal only ever talks to a stub server this file starts on a
free 127.0.0.1 port and stops afterwards; the shared Inkling service is never contacted."""
import ast
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import socket
import subprocess
import tempfile
import threading
import types
import unittest
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

from lab import r6_inkling_client as rc
from lab import r6_p0_probe as p0
from lab import tremor_admission_gate as gate
from lab import tremor_gpu_run as real

SRC = Path(real.__file__)
BASE = "/tmp/claude-1000"
WORDS = "I admit batch r6-p0 once"
TEXTS = {s: f"sealed synthetic prompt {s}" for s in p0.SIZES}
REV = "a" * 40
REMOTE = "192.0.2.7:8011"  # TEST-NET-1: never reachable, never contacted (connect is patched)


def sha(b):
    return hashlib.sha256(b).hexdigest()


class Stub(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        self.server.bodies.append(body)
        out = json.dumps({"choices": [{"message": {"content": "same"}, "finish_reason": "stop"}],
                          "usage": {"prompt_tokens": 10, "completion_tokens": 20},
                          "timings": {"prompt_ms": 10, "predicted_ms": 100}}).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)


class Env:
    """A throwaway git repo, model dir, fake /proc, records and stub server, all under BASE."""

    def __init__(self, M):
        self.M = M
        os.makedirs(BASE, exist_ok=True)
        self._td = tempfile.TemporaryDirectory(dir=BASE, prefix="tgr-")
        self.tmp = Path(self._td.name)
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        self._git("init", "-q")
        self._git("config", "user.email", "t@t")
        self._git("config", "user.name", "t")
        (self.repo / "proto.md").write_bytes(b"protocol")
        (self.repo / "prereg").mkdir()
        (self.repo / "prereg/R5-agent-performance-line-plan.md").write_text(
            f"`data/hf/Qwen3.5-4B` pinned, revision `{REV}`\n")
        self._git("add", "."); self._git("commit", "-qm", "floor")
        floor = self._git("rev-parse", "HEAD")
        for s, t in TEXTS.items():
            (self.repo / f"p{s}.txt").write_bytes(t.encode())
        self._git("add", "."); self._git("commit", "-qm", "pin")
        pin = self._git("rev-parse", "HEAD")
        self._floor = (gate, gate.FLOOR_COMMIT)
        gate.FLOOR_COMMIT = floor
        self.model = self.tmp / "model"
        self.model.mkdir()
        (self.model / "w.bin").write_bytes(b"weights")
        (self.model / "MANIFEST.sha256.json").write_text(json.dumps(
            {"revision": REV, "files": [{"path": "w.bin", "sha256": sha(b"weights"), "bytes": 7}]}))
        self.proc = self._proc()
        snap = p0.identity_snapshot(self.proc["root"], self.proc["gguf"])
        freeze = {"batch": "r6-p0", "protocol_path": "proto.md", "protocol_sha256": sha(b"protocol"),
                  "commit": pin, "tree": self._git("rev-parse", pin + "^{tree}"),
                  "protected_inputs": [{"path": f"p{s}.txt", "sha256": p0.prompt_sha256(t), "custodian": "c"}
                                       for s, t in TEXTS.items()],
                  "reserved_gpu_hours": 10, "hosted_usd_plan": 9, "hosted_usd_stop": 15,
                  **{k: f"v-{k}" for k in ("config_hash", "task_family_revision", "scorer_ids", "contrasts",
                                           "stopping_rules", "expected_and_max_resources",
                                           "approval_review_evidence", "d1_basis", "inherited_pins")},
                  "model_snapshot": snap}
        self.freeze = self.tmp / "freeze.json"
        self.freeze.write_text(json.dumps(freeze))
        now = datetime.now(timezone.utc)
        self.adm = self.tmp / "adm.json"
        self.adm_body = {"batch": "r6-p0", "one_use": True, "used": False,
                         "valid_from_utc": (now - timedelta(hours=1)).isoformat(),
                         "valid_until_utc": (now + timedelta(hours=1)).isoformat(),
                         "reserved_gpu_hours": 10, "hosted_usd_plan": 9, "hosted_usd_stop": 15,
                         "owner_words": WORDS, "freeze_record_sha256": sha(self.freeze.read_bytes())}
        self.adm.write_text(json.dumps(self.adm_body))
        self.notice = self.tmp / "notice.txt"
        self.notice.write_text(self.notice_text())
        (self.tmp / "mem").write_text("MemAvailable:   20971520 kB\n")
        (self.tmp / "load").write_text("0.10 0.10 0.10 1/1 1\n")
        self.outroot = self.tmp / "outroot"
        self.outroot.mkdir()
        self.n = 0
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), Stub)
        self.srv.daemon_threads = True
        self.srv.bodies = []
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.port = self.srv.server_address[1]
        self.connects = []

    @staticmethod
    def notice_text(placement="Spark GPU, PC coordinator informed", start=-1, end=2):
        n = datetime.now(timezone.utc).replace(microsecond=0)
        w = f"{(n + timedelta(hours=start)).isoformat()}/{(n + timedelta(hours=end)).isoformat()}"
        return f"placement: {placement}\nquiet_window: {w}\n"

    def close(self):
        self.srv.shutdown()
        self.srv.server_close()
        self._floor[0].FLOOR_COMMIT = self._floor[1]
        self._td.cleanup()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()

    def _git(self, *a):
        return subprocess.run(["git", "-C", str(self.repo), *a], check=True, capture_output=True,
                              text=True).stdout.strip()

    def _proc(self):
        root, gguf, exe = self.tmp / "proc", self.tmp / "m.gguf", self.tmp / "exe-file"
        gguf.write_bytes(b"gguf-bytes")
        exe.write_bytes(b"binary-A")
        st = os.stat(gguf)
        dev = f"{os.major(st.st_dev):02x}:{os.minor(st.st_dev):02x}"
        d = root / "4242"
        d.mkdir(parents=True)
        (d / "maps").write_text(f"7f00-7f10 r--s 00000000 {dev} {st.st_ino} {gguf}\n")
        (d / "stat").write_text("4242 (llama server) S " + " ".join(["0"] * 18) + " 777 0 0\n")
        (d / "cmdline").write_bytes(b"llama-server\x00-c\x00262144\x00")
        os.symlink(exe, d / "exe")
        return {"root": str(root), "gguf": str(gguf), "exe": exe}

    # ---- running the launcher -------------------------------------------------------
    def ready_kw(self, fail=False):
        def runner(argv):
            if fail:
                return types.SimpleNamespace(returncode=1, stdout="", stderr="boom")
            out = "GPU0, 24000 MiB, 100 MiB, 0 %" if "--query-gpu=name,memory.total,memory.used,utilization.gpu" \
                in argv else ""
            return types.SimpleNamespace(returncode=0, stdout=out, stderr="")
        return dict(runner=runner, meminfo_path=str(self.tmp / "mem"), loadavg_path=str(self.tmp / "load"))

    def argv(self, live=False, drop=(), prompts=None, **over):
        a = {"--out": str(self.outroot / f"run{self.n}"), "--out-root": str(self.outroot),
             "--repo-root": str(self.repo), "--model-dir": str(self.model), "--min-mem-kib": "1000",
             "--freeze": str(self.freeze), "--admission": str(self.adm), "--hosted-cap": "15",
             "--gpu-cap": "10", "--max-window-hours": "48", "--owner-words": WORDS, "--seed": "7",
             "--max-total-tokens": "1000000", "--max-response-bytes": "100000",
             "--endpoint": f"http://127.0.0.1:{self.port}", "--gguf-path": self.proc["gguf"],
             "--proc-root": self.proc["root"], "--pc-notice": str(self.notice)}
        a.update(over)
        out = []
        for k, v in a.items():
            if k not in drop:
                out += [k, v]
        for s in p0.SIZES:
            out += ["--prompt", f"{s}={(prompts or {}).get(s, f'{self.repo}/p{s}.txt')}"]
        if live:
            out += ["--live", "--i-have-owner-confirm"]
        self.n += 1
        return out

    def run(self, argv, block=True, ready=None):
        """Returns (exit code, stdout). Every socket connect is counted; blocked ones raise OSError."""
        orig = socket.socket.connect

        def counting(sock, addr):
            self.connects.append(addr)
            if block:
                raise OSError("blocked by test")
            return orig(sock, addr)
        buf = io.StringIO()
        with mock.patch.object(socket.socket, "connect", counting), \
                mock.patch.object(socket.socket, "connect_ex", lambda s, a: self.connects.append(a) or 1), \
                contextlib.redirect_stdout(buf):
            code = self.M.main(argv, readiness_kw=ready or self.ready_kw())
        return code, buf.getvalue()

    def receipts(self, argv):
        d = Path(argv[argv.index("--out") + 1])
        return {p.name: json.loads(p.read_text()) for p in sorted(d.glob("*.json"))} if d.is_dir() else {}

    def claim_file(self):
        return self.repo / ".git" / "tremor-admission-claims" / "r6-p0"

    def refused(self, name, argv, **kw):
        code, out = self.run(argv, **kw)
        assert code == 2, (code, out)
        assert f"REFUSED[{name}]" in out, out
        assert self.connects == [], self.connects
        assert self.srv.bodies == []
        return out


def stable(d):
    return {k: v for k, v in d.items() if k not in ("utc", "measured")}


# ---- probes -------------------------------------------------------------------------
def p_dry_default_no_network(E):
    argv = E.argv()
    code, out = E.run(argv)
    assert code == 0 and "DRY RUN" in out, (code, out)
    assert E.connects == [] and E.srv.bodies == []
    assert not E.claim_file().exists()


def p_dry_even_with_confirm_flag(E):
    argv = E.argv() + ["--i-have-owner-confirm"]
    code, out = E.run(argv)
    assert code == 0 and "DRY RUN" in out and E.connects == [] and E.srv.bodies == []


def p_dry_receipts(E):
    argv = E.argv()
    E.run(argv)
    r = E.receipts(argv)
    assert sorted(r) == ["01-readiness.json", "02-admission-check.json", "03-manifest.json", "04-run.json"], sorted(r)
    assert r["02-admission-check.json"]["outcome"] == "ok" and r["01-readiness.json"]["outcome"] == "ok"
    assert r["04-run.json"]["outcome"] == "not-run"
    assert all(v["utc"].endswith("+00:00") for v in r.values())


def p_receipt_hashes(E):
    argv = E.argv()
    E.run(argv)
    r = E.receipts(argv)
    assert r["02-admission-check.json"]["inputs"] == {"freeze": sha(E.freeze.read_bytes()),
                                                       "admission": sha(E.adm.read_bytes())}
    assert r["01-readiness.json"]["inputs"]["model_manifest"] == sha((E.model / "MANIFEST.sha256.json").read_bytes())
    assert sorted(r["03-manifest.json"]["inputs"]) == ["prompt_1000", "prompt_200", "prompt_2000"]
    assert r["03-manifest.json"]["inputs"]["prompt_200"] == sha((E.repo / "p200.txt").read_bytes())
    assert sorted(r["03-manifest.json"]["inputs"].values()) == sorted(
        sha((E.repo / f"p{s}.txt").read_bytes()) for s in p0.SIZES)


def p_dry_prints_caps(E):
    code, out = E.run(E.argv())
    man = json.loads(out.split("manifest: ", 1)[1])
    assert man["caps"]["stops"] == rc.P0_STOPS and man["caps"]["output_caps"] == list(p0.CAPS)
    assert len(man["calls"]) == rc.P0_STOPS["max_calls"]
    assert [c["max_tokens"] for c in man["calls"]] == [64, 300] * 6
    assert man["listed_not_run"] == {"B0'": 28, "B1'": 280}
    assert man["calls"][0]["prompt_sha256"] == p0.prompt_sha256(TEXTS[200])


def p_dry_no_claim_no_write_outside_out(E):
    before = E.adm.read_bytes()
    E.run(E.argv())
    assert E.adm.read_bytes() == before and not E.claim_file().exists()


def p_dry_reports_endpoint_refusal(E):
    code, out = E.run(E.argv(**{"--endpoint": "http://192.0.2.7:8011"}))
    assert code == 0 and "would be REFUSED" in out and E.connects == []


def p_dry_gate_problem_exit1(E):
    E.adm.write_text(json.dumps(dict(E.adm_body, used=True)))
    argv = E.argv()
    code, out = E.run(argv)
    assert code == 1 and "REFUSED" in out and E.receipts(argv)["02-admission-check.json"]["outcome"] == "refused"


def p_refuse_no_freeze(E):
    E.refused("no-freeze-record", E.argv(live=True, drop=("--freeze",)))


def p_refuse_no_notice(E):
    E.notice.write_text("   \n")
    E.refused("no-pc-notice", E.argv(live=True))


def p_refuse_notice_incomplete(E):
    E.notice.write_text("quiet window 10:00 only")
    E.refused("pc-notice-incomplete", E.argv(live=True))


def p_refuse_notice_negated(E):
    E.notice.write_text("no placement; no quiet window\n")
    E.refused("pc-notice-incomplete", E.argv(live=True))
    E.notice.write_text(E.notice_text(placement="none"))
    E.refused("pc-notice-incomplete", E.argv(live=True))


def p_refuse_notice_window(E):
    good = E.notice_text()
    first, q = good.splitlines()
    for bad in (E.notice_text(start=-3, end=-1),  # in the past
                E.notice_text(start=2, end=1),  # end before start
                first + "\nquiet_window: tomorrow\n",
                first + "\n" + q.replace("+00:00", "") + "\n",  # not UTC
                first + "\n" + q.split("/")[0] + "\n",  # no end
                first + "\n"):  # no quiet_window line
        E.notice.write_text(bad)
        E.refused("pc-notice-incomplete", E.argv(live=True))


def p_refuse_notice_future_window(E):
    E.notice.write_text(E.notice_text(start=5, end=7))
    argv = E.argv(live=True)
    E.refused("pc-notice-incomplete", argv)
    assert "has not started or has ended" in E.run(argv)[1] and not E.claim_file().exists()


def p_refuse_notice_end_not_after_start(E):
    for start, end in ((-1, -1), (-2, -3), (1, 0)):  # equal, and end before start, window around now or not
        E.notice.write_text(E.notice_text(start=start, end=end))
        argv = E.argv(live=True)
        code, out = E.run(argv)
        assert code == 2 and "REFUSED[pc-notice-incomplete]" in out and "end is not after the start" in out, out
        assert "has not started or has ended" not in out
        assert E.connects == [] and E.srv.bodies == [] and not E.claim_file().exists()


def p_refuse_notice_pending(E):
    for v in ("pending", "TBD", "unknown", "later", "todo"):
        E.notice.write_text(E.notice_text(placement=v))
        E.refused("pc-notice-incomplete", E.argv(live=True))


def p_refuse_notice_repeated(E):
    E.notice.write_text(E.notice_text() + "placement: other\n")
    E.refused("pc-notice-incomplete", E.argv(live=True))
    E.notice.write_text(E.notice_text() + E.notice_text().splitlines()[1] + "\n")
    E.refused("pc-notice-incomplete", E.argv(live=True))


def p_notice_window_boundaries(E):
    t = datetime(2026, 12, 1, 10, 0, tzinfo=timezone.utc)
    text = f"placement: Spark\nquiet_window: {t.isoformat()}/{(t + timedelta(hours=1)).isoformat()}\n"
    f = E.M._notice_problem
    assert f(text, now=t) == ""
    assert f(text, now=t - timedelta(seconds=1)) != ""
    assert f(text, now=t + timedelta(hours=1) - timedelta(seconds=1)) == ""
    assert f(text, now=t + timedelta(hours=1)) != ""


def p_notice_example_accepted(E):
    code, out = E.run(E.argv(live=True), block=False)
    assert code == 0, out


def p_refuse_seed_range(E):
    E.refused("seed-out-of-range", E.argv(live=True, **{"--seed": "4294967296"}))
    assert not E.claim_file().exists() and json.loads(E.adm.read_text())["used"] is False


def p_refuse_unpinned_prompt(E):
    other = E.tmp / "other.txt"
    other.write_text("an unpinned prompt")
    E.refused("prompt-not-pinned", E.argv(live=True, prompts={200: str(other)}))
    assert not E.claim_file().exists() and json.loads(E.adm.read_text())["used"] is False


def p_refuse_unpinned_prompt_remote(E):
    other = E.tmp / "other.txt"
    other.write_text("an unpinned prompt")
    E.refused("prompt-not-pinned", E.argv(live=True, prompts={200: str(other)},
                                          **{"--endpoint": f"http://{REMOTE}", "--allow-endpoint": REMOTE}))
    assert not E.claim_file().exists()


def p_refuse_token_budget(E):
    E.refused("token-budget-too-small", E.argv(live=True, **{"--max-total-tokens": "100"}))
    assert not E.claim_file().exists() and json.loads(E.adm.read_text())["used"] is False


def p_token_budget_boundary(E):
    first = E.M._manifest(E.M._parser().parse_args(E.argv(live=True)))[0]["calls"][0]
    need = first["body_bytes"] + first["max_tokens"]
    E.refused("token-budget-too-small", E.argv(live=True, **{"--max-total-tokens": str(need - 1)}))


def p_empty_result_no_crash(E):
    res = {"traces": [], "stopped": "max_calls reached", "repeat_matches": [], "wall_total_s": 0.0,
           "default_temperature": None}
    argv = E.argv(live=True)
    with mock.patch.object(E.M.p0, "run_p0", lambda *a, **k: res):
        code, out = E.run(argv)
    assert code == 1, out
    assert E.receipts(argv)["04-run.json"]["outcome"] == "error" and E.claim_file().exists()


def p_run_error_after_claim_writes_receipt(E):
    def boom(*a, **k):
        raise rc.ClientRefused("stop before any call")
    argv = E.argv(live=True)
    with mock.patch.object(E.M.p0, "run_p0", boom):
        code, out = E.run(argv)
    assert code == 2 and E.receipts(argv)["04-run.json"]["outcome"] == "error" and E.claim_file().exists()


def p_refuse_dns_allow(E):
    lookups = []
    argv = E.argv(live=True, **{"--endpoint": "http://evil.example:8011", "--allow-endpoint": "evil.example:8011"})
    with mock.patch.object(socket, "getaddrinfo", lambda *a, **k: lookups.append(a) or []):
        E.refused("allow-endpoint-invalid", argv)
        E.refused("endpoint-not-allowed", E.argv(live=True, **{"--endpoint": "http://evil.example:8011"}))
    assert lookups == []
    ns = types.SimpleNamespace(endpoint="http://evil.example:8011", allow_endpoint=["evil.example:8011"])
    assert E.M._endpoint_ok(ns) is False


def p_loopback_ipv6_allowed(E):
    code, out = E.run(E.argv(**{"--endpoint": "http://[::1]:8011"}))
    assert code == 0 and "allowed" in out and "REFUSED" not in out, out


def p_refuse_lookalike_loopback(E):
    E.refused("endpoint-not-allowed", E.argv(live=True, **{"--endpoint": f"http://127.0.0.1.evil.example:{E.port}"}))


def p_refuse_allow_substring(E):
    E.refused("endpoint-not-allowed", E.argv(live=True, **{"--endpoint": "http://192.0.2.7:801",
                                                          "--allow-endpoint": REMOTE}))


def p_refuse_abbrev(E):
    argv = E.argv() + ["--liv", "--i-have"]
    with contextlib.redirect_stderr(io.StringIO()), mock.patch.object(socket.socket, "connect", lambda *a: 1 / 0):
        try:
            E.M.main(argv, readiness_kw=E.ready_kw())
        except SystemExit as e:
            assert e.code == 2
        else:
            raise AssertionError("abbreviated flags were accepted")
    assert E.srv.bodies == []


def p_refuse_scheme(E):
    for ep in (f"https://127.0.0.1:{E.port}", f"ftp://127.0.0.1:{E.port}", "http://127.0.0.1"):
        E.refused("endpoint-invalid", E.argv(**{"--endpoint": ep}))


def p_client_caps_are_the_modules(E):
    seen = {}

    def fake(client, *a, **k):
        seen.update(calls=client._max_calls, wall=client._max_wall, errors=client._max_errors,
                    skips=client._max_skips, skip_wait=client._skip_wait, timeout=client._timeout,
                    tokens=client._max_tokens, stops=k["stops"])
        raise rc.ClientRefused("stopped by test")
    with mock.patch.object(E.M.p0, "run_p0", fake):
        E.run(E.argv(live=True))
    s = rc.P0_STOPS
    assert seen == dict(calls=s["max_calls"], wall=s["max_wall_s"], errors=s["max_errors"], skips=s["max_skips"],
                        skip_wait=s["skip_wait_s"], timeout=s["timeout_s"], tokens=max(p0.CAPS), stops=s)


def p_receipts_exclusive(E):
    d = E.tmp / "rcpt"
    d.mkdir()
    r = E.M._Receipts(str(d))
    r.write("x", {}, "ok")
    try:
        r.write("x", {}, "ok")
    except FileExistsError:
        return
    raise AssertionError("a receipt was overwritten")


def p_doc_states_dry_run_reads(E):
    d = " ".join(E.M.__doc__.split())
    assert "nvidia-smi" in d and "hashes the model folder" in d


def p_refuse_no_owner_confirm(E):
    argv = E.argv(live=True)
    argv.remove("--i-have-owner-confirm")
    E.refused("no-owner-confirm", argv)


def p_refuse_endpoint(E):
    E.refused("endpoint-not-allowed", E.argv(live=True, **{"--endpoint": "http://192.0.2.7:8011"}))


def p_refuse_localhost_name(E):
    E.refused("endpoint-not-allowed", E.argv(live=True, **{"--endpoint": f"http://localhost:{E.port}"}))


def p_refuse_missing_input(E):
    E.refused("missing-live-input", E.argv(live=True, drop=("--seed",)))


def p_refuse_admission_not_accepted(E):
    E.adm.write_text(json.dumps(dict(E.adm_body, owner_words="something else")))
    argv = E.argv(live=True)
    E.refused("admission-not-accepted", argv)
    assert "04-refusal.json" in E.receipts(argv) and not E.claim_file().exists()


def p_refuse_no_admission_record(E):
    E.refused("missing-live-input", E.argv(live=True, drop=("--admission",)))


def p_refuse_readiness(E):
    E.refused("readiness-failed", E.argv(live=True), ready=E.ready_kw(fail=True))
    assert not E.claim_file().exists()


def p_refuse_identity(E):
    E.proc["exe"].write_bytes(b"swapped")
    E.refused("identity-mismatch", E.argv(live=True))
    assert not E.claim_file().exists()  # a mismatch never spends the admission


def p_out_not_new(E):
    argv = E.argv()
    out = Path(argv[argv.index("--out") + 1])
    out.mkdir()
    E.refused("out-not-new", argv)
    assert list(out.iterdir()) == []


def p_out_outside_root(E):
    other = E.tmp / "elsewhere"
    other.mkdir()
    E.refused("out-outside-root", E.argv(**{"--out": str(other / "x")}))
    E.refused("out-outside-root", E.argv(**{"--out": str(E.outroot / ".." / "x")}))
    assert not (E.tmp / "x").exists()


def p_out_symlinked_parent_outside_root(E):
    elsewhere = E.tmp / "elsewhere-link"
    elsewhere.mkdir()
    os.symlink(elsewhere, E.outroot / "lnk")
    E.refused("out-outside-root", E.argv(**{"--out": str(E.outroot / "lnk" / "x")}))
    assert list(elsewhere.iterdir()) == []


def p_refuse_notice_non_utc_offset(E):
    n = datetime.now(timezone.utc).replace(microsecond=0)
    tz = timezone(timedelta(hours=2))
    w = f"{(n - timedelta(hours=1)).astimezone(tz).isoformat()}/{(n + timedelta(hours=2)).astimezone(tz).isoformat()}"
    assert "+02:00" in w
    assert E.M._notice_problem(f"placement: Spark\nquiet_window: {w}\n") != ""
    E.notice.write_text(f"placement: Spark GPU\nquiet_window: {w}\n")
    out = E.refused("pc-notice-incomplete", E.argv(live=True))
    assert "UTC ISO" in out, out
    assert not E.claim_file().exists()


def p_granted_run(E):
    argv = E.argv(live=True, **{"--b0-calls": "28", "--load-seconds": "0"})
    code, out = E.run(argv, block=False)
    assert code == 0, out
    assert len(E.srv.bodies) == 12
    assert set(E.connects) == {("127.0.0.1", E.port)}
    r = E.receipts(argv)
    assert sorted(r) == ["01-readiness.json", "02-admission-check.json", "03-manifest.json", "04-run.json",
                         "05-b0-estimate.json"], sorted(r)
    assert r["04-run.json"]["outcome"] == "ok" and r["04-run.json"]["result"]["n_calls"] == 12
    assert r["04-run.json"]["result"]["repeat_matches"] == [True] * 6
    assert r["05-b0-estimate.json"]["outcome"] == "ok"
    assert r["04-run.json"]["inputs"]["pc_notice"] == sha(E.notice.read_bytes())
    assert E.claim_file().exists() and json.loads(E.adm.read_text())["used"] is True


def p_second_claim_refused(E):
    code, _ = E.run(E.argv(live=True), block=False)
    assert code == 0 and len(E.srv.bodies) == 12
    E.connects.clear()
    code, out = E.run(E.argv(live=True))  # record now says used
    assert code == 2 and "REFUSED[admission-not-accepted]" in out and E.connects == []
    E.adm.write_text(json.dumps(E.adm_body))  # owner-visible record restored: the claim file still holds
    code, out = E.run(E.argv(live=True))
    assert code == 2 and "REFUSED[claim-refused]" in out and E.connects == []
    assert len(E.srv.bodies) == 12


def p_allow_listed_remote(E):
    seen = {}

    def fake(client, *a, **k):
        seen["remote"] = client._remote
        raise rc.ClientRefused("stopped by test")
    argv = E.argv(live=True, **{"--endpoint": f"http://{REMOTE}", "--allow-endpoint": REMOTE})
    with mock.patch.object(E.M.p0, "run_p0", fake):
        code, out = E.run(argv)
    assert code == 2 and "REFUSED[claim-refused]: stopped by test" in out, out
    assert seen == {"remote": True} and E.connects == []
    assert not E.claim_file().exists()  # the launcher itself never claims for a remote client


def p_deterministic(E):
    a1, a2 = E.argv(), E.argv()
    E.run(a1)
    E.run(a2)
    r1, r2 = E.receipts(a1), E.receipts(a2)
    assert {k: stable(v) for k, v in r1.items()} == {k: stable(v) for k, v in r2.items()}


PROBES = {n[2:]: f for n, f in list(globals().items()) if n.startswith("p_") and callable(f)}


def check(module, name):
    with Env(module) as E:
        PROBES[name](E)


class Launcher(unittest.TestCase):
    pass


def _add(name):
    def t(self):
        check(real, name)
    setattr(Launcher, "test_" + name, t)


for _n in PROBES:
    _add(_n)


class Static(unittest.TestCase):
    def test_no_scheduler_loop_or_process_control(self):
        tree = ast.parse(SRC.read_text())
        banned = {"sched", "threading", "subprocess", "signal", "multiprocessing", "time", "asyncio"}
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                assert not banned & {a.name.split(".")[0] for a in n.names}
            if isinstance(n, ast.ImportFrom):
                assert (n.module or "").split(".")[0] not in banned
            assert not isinstance(n, (ast.While, ast.AsyncFunctionDef))
        text = SRC.read_text()
        for word in ("os.system", "Popen", "fork(", "sleep(", "crontab", "systemctl", "nohup", "setsid"):
            assert word not in text, word

    def test_dry_run_is_the_parser_default(self):
        ns = real._parser().parse_args(["--out", "o", "--out-root", "r", "--model-dir", "m", "--min-mem-kib", "1",
                                        "--hosted-cap", "1", "--gpu-cap", "1", "--max-window-hours", "1",
                                        "--owner-words", "w", "--endpoint", "http://127.0.0.1:1"])
        self.assertFalse(ns.live)
        self.assertFalse(ns.i_have_owner_confirm)


# ---- mutants ------------------------------------------------------------------------
# (name, exact text in tremor_gpu_run.py, replacement, probes that must fail)
MUTANTS = [
    ("no_freeze_check", "if not a.freeze or not os.path.isfile(a.freeze):", "if False:", ["refuse_no_freeze"]),
    ("no_notice_check", "if not text.strip():", "if False:", ["refuse_no_notice"]),
    ("no_notice_content_check", "    problem = _notice_problem(text)\n    if problem:",
     "    problem = ''\n    if problem:", ["refuse_notice_incomplete", "refuse_notice_negated"]),
    ("no_confirm_check", "if not a.i_have_owner_confirm:", "if False:", ["refuse_no_owner_confirm"]),
    ("no_endpoint_check", "if not _endpoint_ok(a):", "if False:", ["refuse_endpoint", "refuse_localhost_name"]),
    ("no_notice_negation_check", "if not fields.get(k) or _NEG.search(fields[k]):", "if not fields.get(k):",
     ["refuse_notice_negated"]),
    ("no_end_le_start_check", "if end <= start:", "if False:", ["refuse_notice_end_not_after_start"]),
    ("no_start_check", "if not start <= (now or _utc()) < end:", "if not (now or _utc()) < end:",
     ["refuse_notice_future_window", "notice_window_boundaries"]),
    ("end_inclusive", "if not start <= (now or _utc()) < end:", "if not start <= (now or _utc()) <= end:",
     ["notice_window_boundaries"]),
    ("start_exclusive", "if not start <= (now or _utc()) < end:", "if not start < (now or _utc()) < end:",
     ["notice_window_boundaries"]),
    ("word_filter_weakened", "|pending|later|todo)", ")", ["refuse_notice_pending"]),
    ("word_filter_off", "_NEG.search(fields[k])", "False", ["refuse_notice_negated"]),
    ("repeat_allowed", "return f\"{k} given twice\"", "pass", ["refuse_notice_repeated"]),
    ("no_quiet_window_line", "for k in (\"placement\", \"quiet_window\"):\n        if not fields.get(k)",
     "for k in (\"placement\",):\n        if not fields.get(k)", ["refuse_notice_window"]),
    ("loopback_startswith_127", "return ip.is_loopback or (ip, port) in _allow_set(a.allow_endpoint)",
     "return host.startswith(\"127\") or (ip, port) in _allow_set(a.allow_endpoint)", ["loopback_ipv6_allowed"]),
    ("allow_substring", "return ip.is_loopback or (ip, port) in _allow_set(a.allow_endpoint)",
     "return ip.is_loopback or f\"{host}:{port}\" in \" \".join(a.allow_endpoint)", ["refuse_allow_substring"]),
    ("dns_allowed", "        return False  # a DNS name is never resolved",
     "        return f\"{host}:{port}\" in a.allow_endpoint", ["refuse_dns_allow"]),
    ("allow_entry_unchecked", "except ValueError:\n            raise Refused(\"allow-endpoint-invalid\"",
     "except ValueError:\n            continue\n            raise Refused(\"allow-endpoint-invalid\"", ["refuse_dns_allow"]),
    ("abbrev_allowed", "allow_abbrev=False, ", "", ["refuse_abbrev"]),
    ("no_preclaim", "    _preclaim(a, prompts, man)\n", "",
     ["refuse_unpinned_prompt", "refuse_seed_range", "refuse_token_budget"]),
    ("no_seed_check", "if isinstance(a.seed, bool) or not isinstance(a.seed, int) or not 0 <= a.seed < 2 ** 32:",
     "if False:", ["refuse_seed_range"]),
    ("no_pin_check", "if any(p0.prompt_sha256(t) not in pinned for t in prompts.values()):", "if False:",
     ["refuse_unpinned_prompt", "refuse_unpinned_prompt_remote"]),
    ("no_token_check", "if first[\"body_bytes\"] + first[\"max_tokens\"] > a.max_total_tokens:", "if False:",
     ["refuse_token_budget"]),
    ("token_check_off_by_one", "if first[\"body_bytes\"] + first[\"max_tokens\"] > a.max_total_tokens:",
     "if first[\"body_bytes\"] + first[\"max_tokens\"] > a.max_total_tokens + 1:", ["token_budget_boundary"]),
    ("summarise_unguarded", "    except rc.ClientRefused:  # no call was measured\n        summary = None",
     "    except ZeroDivisionError:\n        summary = None", ["empty_result_no_crash"]),
    ("no_error_receipt", "        rec.write(\"04-run\", in_sha, \"error\", str(e))\n", "",
     ["run_error_after_claim_writes_receipt"]),
    ("receipt_not_exclusive", "os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)\n        with os.fdopen",
     "os.O_CREAT | os.O_WRONLY | os.O_NOFOLLOW, 0o600)\n        with os.fdopen", ["receipts_exclusive"]),
    ("max_calls_1000", "max_calls=s[\"max_calls\"]", "max_calls=1000", ["client_caps_are_the_modules"]),
    ("scheme_unchecked", "if u.scheme != \"http\" or not u.hostname or port is None:",
     "if not u.hostname or port is None:", ["refuse_scheme"]),
    ("prompt_receipt_by_argv_order", "f\"prompt_{v.partition('=')[0]}\": _sha_file(v.partition(\"=\")[2])\n"
     "                                                          for v in a.prompt}",
     "f\"prompt_{k}\": _sha_file(v.partition(\"=\")[2])\n"
     "                                                          for k, v in enumerate(a.prompt)}", ["receipt_hashes"]),
    ("no_missing_input_check", "if missing or _prompts(a)[0] is None:", "if False:", ["refuse_missing_input"]),
    ("no_admission_check", "if gate_err is not None:", "if False:", ["refuse_admission_not_accepted"]),
    ("no_readiness_check", 'if not r["ok"]:', "if False:", ["refuse_readiness"]),
    ("no_identity_check", "if not same:", "if False:", ["refuse_identity"]),
    ("no_claim", "gate.admit(a.freeze, a.admission, _utc(), a.repo_root, **_caps(a))", "None",
     ["second_claim_refused", "granted_run"]),
    ("dry_default_flipped", 'ap.add_argument("--live", action="store_true")',
     'ap.add_argument("--live", action="store_true", default=True)', ["dry_default_no_network"]),
    ("network_before_check", "        if a.live:\n            _static_refusals(a)",
     '        if a.live:\n            __import__("socket").create_connection(_hostport(a.endpoint), 1).close()\n'
     "            _static_refusals(a)", ["refuse_no_freeze", "refuse_no_owner_confirm"]),
    ("receipt_hash_wrong", "return hashlib.sha256(f.read()).hexdigest()", "return hashlib.sha256(path.encode()).hexdigest()",
     ["receipt_hashes"]),
    ("out_may_exist", "if os.path.lexists(out):", "if False:", ["out_not_new"]),
    ("out_root_unchecked", "if os.path.commonpath([root, parent]) != root:", "if False:", ["out_outside_root"]),
    ("allow_list_ignored", "return ip.is_loopback or (ip, port) in _allow_set(a.allow_endpoint)",
     "return ip.is_loopback", ["allow_listed_remote"]),
    ("instant_accepts_offset", "t.tzinfo is None or t.utcoffset().total_seconds() != 0", "t.tzinfo is None",
     ["refuse_notice_non_utc_offset"]),
    ("out_parent_not_resolved", "parent = os.path.realpath(os.path.dirname(out))", "parent = os.path.dirname(out)",
     ["out_symlinked_parent_outside_root"]),
    ("dry_claims", "        rec.write(\"04-run\", {}, \"not-run\", \"dry-run: nothing sent\")",
     "        gate.admit(a.freeze, a.admission, _utc(), a.repo_root, **_caps(a))\n"
     "        rec.write(\"04-run\", {}, \"not-run\", \"dry-run: nothing sent\")", ["dry_no_claim_no_write_outside_out"]),
]


def load_mutant(tmp, name, old, new):
    src = SRC.read_text()
    assert src.count(old) == 1, (name, src.count(old))
    path = Path(tmp) / f"{name}.py"
    path.write_text(src.replace(old, new))
    spec = importlib.util.spec_from_file_location(f"mut_{name}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Mutants(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.makedirs(BASE, exist_ok=True)
        cls._td = tempfile.TemporaryDirectory(dir=BASE, prefix="tgr-mut-")

    @classmethod
    def tearDownClass(cls):
        cls._td.cleanup()

    def test_at_least_ten_mutants(self):
        self.assertGreaterEqual(len(MUTANTS), 10)
        self.assertEqual(len({m[0] for m in MUTANTS}), len(MUTANTS))

    def test_unmutated_copy_passes_every_killer_probe(self):
        mod = load_mutant(self._td.name, "identity", "if not same:", "if not same:")
        for name in {p for m in MUTANTS for p in m[3]}:
            check(mod, name)


def _add_mutant(name, old, new, killers):
    def t(self):
        mod = load_mutant(self._td.name, name, old, new)
        killed = []
        for k in killers:
            try:
                check(mod, k)
            except BaseException as e:  # a crash is a kill too
                if isinstance(e, KeyboardInterrupt):
                    raise
                killed.append(k)
        self.assertEqual(killed, killers, f"mutant {name} survived probes {set(killers) - set(killed)}")
    setattr(Mutants, "test_mutant_" + name, t)


for _m in MUTANTS:
    _add_mutant(*_m)


if __name__ == "__main__":
    unittest.main()
