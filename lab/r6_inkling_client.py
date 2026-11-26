"""Minimal stdlib client for llama-server's OpenAI-compatible chat endpoint (R6 probe P0).

Fail closed: any problem raises ClientRefused / StopRule or records a failed trace;
nothing partial is returned as a success. No environment keys are read, no auth header
is sent, and request or response text never enters a trace.
Stop numbers are the plan's (prereg/R6-pvsnp-research-line-plan.md 6.2), exported as
P0_STOPS for the caller to pass in; the client itself has no defaults.
"""
import ipaddress
import json
import os
import re
import http.client
import socket
import threading
import time
import urllib.parse
from datetime import datetime, timezone

from lab import tremor_admission_gate as gate

# Plan 6.2: 12 calls, 15 minutes, 2 errors, skip spike = 2 calls busy or waiting over 60 s;
# 300 s per-call timeout. The 60 s and 300 s are the planner's choices.
P0_STOPS = {"max_calls": 12, "max_wall_s": 900.0, "max_errors": 2,
            "max_skips": 2, "skip_wait_s": 60.0, "timeout_s": 300.0}
_GATE_CAPS = {"hosted_cap", "gpu_cap", "max_window_hours", "owner_words"}
_PATH = "/v1/chat/completions"


class ClientRefused(Exception):
    pass


class StopRule(ClientRefused):
    pass


class CallFailed(Exception):
    pass


def _posint(v, name, zero=False):
    if isinstance(v, bool) or not isinstance(v, int) or v < (0 if zero else 1):
        raise ClientRefused(f"{name} must be a {'non-negative' if zero else 'positive'} int")
    return v


def _posnum(v, name):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not 0 < v < float("inf"):
        raise ClientRefused(f"{name} must be a finite positive number")
    return float(v)


def _is_loopback(host):
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _count(u, key):
    v = u.get(key) if isinstance(u, dict) else None
    if isinstance(v, bool) or not isinstance(v, int) or v < 0:
        raise CallFailed(f"usage.{key} missing or invalid")
    return v


class InklingClient:
    def __init__(self, base_url, *, admission_path, repo_root, allow_remote, timeout_s, max_tokens,
                 stub, max_calls, max_wall_s, max_total_tokens, max_errors,
                 max_skips, skip_wait_s, max_response_bytes, sink, trace_path,
                 freeze_path, gate_caps):
        u = urllib.parse.urlsplit(base_url if isinstance(base_url, str) else "")
        if u.scheme != "http" or not u.hostname:
            raise ClientRefused("base_url must be http with a host")
        if u.username or u.password or u.query or u.fragment:
            raise ClientRefused("base_url must not carry credentials, query or fragment")
        try:
            u.port
        except ValueError:
            raise ClientRefused("base_url port invalid")
        self._timeout = _posnum(timeout_s, "timeout_s")
        self._max_tokens = _posint(max_tokens, "max_tokens")
        self._max_calls = _posint(max_calls, "max_calls")
        self._max_wall = _posnum(max_wall_s, "max_wall_s")
        self._max_total = _posint(max_total_tokens, "max_total_tokens")
        self._max_errors = _posint(max_errors, "max_errors")
        self._max_skips = _posint(max_skips, "max_skips")
        self._skip_wait = _posnum(skip_wait_s, "skip_wait_s")
        self._max_resp = _posint(max_response_bytes, "max_response_bytes")
        if (sink is None) == (trace_path is None):
            raise ClientRefused("give exactly one of sink or trace_path")
        if sink is not None and not callable(getattr(sink, "append", None)):
            raise ClientRefused("sink needs append()")
        if u.hostname == "localhost":
            raise ClientRefused("use an IP literal (127.0.0.1 or ::1), not localhost")
        self._remote = not _is_loopback(u.hostname)
        self._gate_args = None
        if not self._remote and stub is not True:
            raise ClientRefused("a loopback host needs stub=True (a tunnel or local server is not safe)")
        if self._remote and stub is not False:
            raise ClientRefused("a non-loopback host needs stub=False")
        if self._remote:
            self._gate_args = self._admission(admission_path, repo_root, freeze_path, gate_caps)
            if allow_remote is not True:
                raise ClientRefused("non-loopback host needs allow_remote=True")
            f, a, r, caps = self._gate_args
            try:
                gate.check(f, a, self._now(), r, **caps)
            except Exception as e:
                raise ClientRefused(f"admission refused: {type(e).__name__}")
        self._host, self._port = u.hostname, u.port or 80
        if re.fullmatch(r"[A-Za-z0-9/._~%-]*", u.path) is None:
            raise ClientRefused("base_url path has characters outside [A-Za-z0-9/._~%-]")
        self._path = u.path.rstrip("/") + _PATH
        self._claimed = False
        self._lock = threading.Lock()
        self._t0 = None
        self._calls = self._errors = self._skips = self._tokens = 0
        self._stopped = None
        self._sink, self._fd = sink, None
        if trace_path is not None:
            parent = os.path.abspath(os.path.dirname(os.path.abspath(trace_path)))
            if os.path.realpath(parent) != parent:
                raise ClientRefused("trace_path parent is or sits under a symlink")
            self._fd = os.open(trace_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()

    @staticmethod
    def _admission(admission_path, repo_root, freeze_path, gate_caps):
        if not (isinstance(admission_path, str) and isinstance(freeze_path, str)
                and isinstance(repo_root, str) and isinstance(gate_caps, dict)
                and set(gate_caps) == _GATE_CAPS):
            raise ClientRefused("admission needs admission_path, freeze_path, repo_root and all gate caps")
        return freeze_path, admission_path, repo_root, dict(gate_caps)

    @staticmethod
    def _now():
        return datetime.now(timezone.utc)

    def claim(self):
        """Explicit one-use claim of the admission batch (gate.admit). Never done in the constructor."""
        with self._lock:
            if not self._remote:
                raise ClientRefused("a loopback stub client never claims an admission")
            f, a, r, caps = self._gate_args
            try:
                gate.admit(f, a, self._now(), r, **caps)
            except Exception as e:
                raise ClientRefused(f"claim refused: {type(e).__name__}")
            self._claimed = True

    def close(self):
        fd, self._fd = self._fd, None
        if fd is not None:
            os.close(fd)

    # --- stop rules and budgets -------------------------------------------------
    def _stop(self, why):
        self._stopped = why
        raise StopRule(why)

    def _remaining(self):
        return self._max_wall - (time.monotonic() - self._t0)

    def _gate_call(self, est_prompt):
        if self._stopped:
            raise StopRule(self._stopped)
        if self._remote and not self._claimed:
            raise ClientRefused("remote calls need claim() first")
        if self._t0 is None:
            self._t0 = time.monotonic()
        if self._calls >= self._max_calls:
            self._stop("max_calls reached")
        if self._remaining() <= 0:
            self._stop("wall-time budget spent")
        if self._tokens + est_prompt + self._max_tokens > self._max_total:
            self._stop("token budget cannot cover another call")
        if self._skips >= self._max_skips:
            self._stop("skip spike")
        if self._errors >= self._max_errors:
            self._stop("errors")

    # --- calls -------------------------------------------------------------------
    def call(self, messages, *, seed=None):
        """One chat completion; returns {content, finish_reason, trace}. Raises CallFailed on a failed call (no retries)."""
        if not isinstance(messages, list) or not messages:
            raise ClientRefused("messages must be a non-empty list")
        body = {"messages": messages, "max_tokens": self._max_tokens, "stream": False}
        if seed is not None:
            body["seed"] = _posint(seed, "seed", zero=True)
        data = json.dumps(body).encode()
        # shortcut: one token per request byte is an upper bound, so a huge prompt cannot overshoot the budget
        with self._lock:
            self._gate_call(len(data))
            return self._once(data)

    def _once(self, data):
        self._calls += 1
        start, t = time.monotonic(), self._now()
        rec = {"utc": t.isoformat(), "wall_s": None, "prompt_tokens": None, "completion_tokens": None,
               "finish_reason": None, "queue_wait_s": None, "tokens_per_s": None, "status": None,
               "skip": False, "error": None}
        out = None
        try:
            out = self._request(data, start, rec)
        except BaseException as e:
            rec["error"] = (str(e)[:160] if isinstance(e, CallFailed) else type(e).__name__)
            self._errors += 1
            rec["wall_s"] = time.monotonic() - start
            rec["skip"] = rec["status"] in (429, 503) or rec["wall_s"] > self._skip_wait
            self._skips += rec["skip"]
            self._emit(rec)
            if isinstance(e, (KeyboardInterrupt, SystemExit)):
                raise
            raise CallFailed(rec["error"]) from None
        rec["wall_s"] = time.monotonic() - start
        wait = rec["queue_wait_s"]
        rec["skip"] = rec["wall_s"] > self._skip_wait if wait is None else wait > self._skip_wait
        self._skips += rec["skip"]
        self._tokens += rec["prompt_tokens"] + rec["completion_tokens"]
        self._emit(rec)
        return {"content": out[0], "finish_reason": rec["finish_reason"], "trace": dict(rec)}

    def _request(self, data, start, rec):
        left = min(self._timeout, self._remaining())
        if left <= 0:
            raise CallFailed("wall-time budget spent")
        deadline = start + left
        conn = http.client.HTTPConnection(self._host, self._port, timeout=left)
        # watchdog: a server that trickles bytes cannot stretch the hard per-call deadline
        socks = []

        def cut():
            try:
                (socks[0] if socks else conn.sock).shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
        timer = threading.Timer(left, cut)
        timer.daemon = True
        timer.start()
        try:
            conn.request("POST", self._path, body=data, headers={"Content-Type": "application/json"})
            sock = conn.sock  # getresponse() drops conn.sock when the server closes
            socks.append(sock)
            r = conn.getresponse()
            rec["status"] = r.status
            if 300 <= r.status < 400:
                raise CallFailed("redirect refused")
            if r.status != 200:
                raise CallFailed(f"http {r.status}")
            buf = bytearray()
            while not r.isclosed():
                rem = deadline - time.monotonic()
                if rem <= 0:
                    raise CallFailed("per-call timeout")
                sock.settimeout(rem)
                chunk = r.read1(min(65536, self._max_resp + 1 - len(buf)))
                if not chunk:
                    break
                buf += chunk
                if len(buf) > self._max_resp:
                    raise CallFailed("response too large")
        except CallFailed:
            raise
        except Exception as e:
            raise CallFailed("per-call timeout" if time.monotonic() >= deadline else type(e).__name__) from None
        finally:
            timer.cancel()
            conn.close()
        if time.monotonic() > deadline:
            raise CallFailed("per-call timeout")
        if r.length:  # Content-Length promised more bytes than arrived
            raise CallFailed("truncated")
        try:
            d = json.loads(bytes(buf).decode("utf-8"), object_pairs_hook=gate._unique,
                           parse_constant=gate._bad_const)
            ch = d["choices"][0]
            content, fin = ch["message"]["content"], ch["finish_reason"]
            usage = d["usage"]
            pt, ct = _count(usage, "prompt_tokens"), _count(usage, "completion_tokens")
        except CallFailed:
            raise
        except Exception:
            raise CallFailed("malformed response") from None
        if not isinstance(content, str) or not isinstance(fin, str):
            raise CallFailed("malformed response")
        wall = time.monotonic() - start
        rec.update(prompt_tokens=pt, completion_tokens=ct, finish_reason=fin)
        tm = d.get("timings")
        if isinstance(tm, dict):
            pm, gm = tm.get("prompt_ms"), tm.get("predicted_ms")
            if all(isinstance(x, (int, float)) and not isinstance(x, bool) and x >= 0 for x in (pm, gm)):
                server = (pm + gm) / 1000.0
                rec["queue_wait_s"] = wall if server > wall else wall - server  # implausible timings: use wall
                if gm > 0:
                    rec["tokens_per_s"] = ct / (gm / 1000.0)
        if rec["tokens_per_s"] is None and wall > 0:
            rec["tokens_per_s"] = ct / wall
        return (content,)

    def _emit(self, rec):
        if self._fd is not None:
            b = memoryview((json.dumps(rec, sort_keys=True) + "\n").encode())
            while b:
                b = b[os.write(self._fd, b):]
            os.fsync(self._fd)
        else:
            self._sink.append(dict(rec))

    def stats(self):
        """B0 probe fields: calls, errors, skip_rate, total tokens."""
        with self._lock:
            n = self._calls
            return {"calls": n, "errors": self._errors, "skips": self._skips,
                    "skip_rate": (self._skips / n) if n else 0.0, "total_tokens": self._tokens,
                    "stopped": self._stopped}
