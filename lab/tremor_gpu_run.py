"""TREMOR GPU launcher: R6 P0 then the B0 cost number, one command, DRY-RUN BY DEFAULT.

Stdlib only. No scheduler, timer, loop, daemon or detached process. Steps, each with a receipt JSON
(sha256 of its inputs, UTC time, outcome) under --out, a directory that must be new and inside --out-root:
  01-readiness        lab.r5_gpu_readiness.check (read-only)
  02-admission-check  lab.tremor_admission_gate.check (dry, claims nothing)
  03-manifest         the twelve P0 requests (lab.r6_p0_probe SIZES x CAPS x REPEATS) with the caps the
                      modules define; B0'/B1' (28 and 280 calls, protocol draft section 10) are listed only,
                      they need sealed task sets and their own admission and are not run here
  04-run              live only: gate.admit (one-use claim), then lab.r6_p0_probe.run_p0
  05-b0-estimate      live only, when --b0-calls and --load-seconds are given
Without --live nothing is sent (a dry run still runs the read-only `nvidia-smi` queries of step 1 and hashes the
model folder; it connects to nothing and claims nothing). A live run is refused (exit 2, `REFUSED[name]: ...`, before any network call
and before any claim) unless ALL hold: freeze record, admission accepted by the gate, --pc-notice file that
is structured (see below), loopback endpoint or one listed with --allow-endpoint HOST:PORT,
--i-have-owner-confirm, readiness ok, live identity equal to the freeze record's model_snapshot.
PC notice format, one line each (UTC ISO instants, end after start, and now must lie in [start, end); values may not be
negations such as "no" or "none"):
  placement: <non-empty value>
  quiet_window: 2026-12-01T10:00:00Z/2026-12-01T11:00:00Z
--allow-endpoint takes IP-literal HOST:PORT only (no DNS name is ever resolved); endpoint hosts must be IP literals.
Before the one-use claim the launcher checks the prompt pins, the seed range (below 2**32) and that
--max-total-tokens covers the first call; a refusal there spends nothing.
Dry-run exit: 0 all steps ok, 1 a step reported a problem. Receipts keep the deterministic fields apart
from "utc" and "measured".
shortcut: only the P0 batch ("r6-p0") is wired; B0'/B1' need their own launcher once the task sets exist.
"""
import argparse
import hashlib
import ipaddress
import json
import os
import re
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

from lab import r5_gpu_readiness as ready
from lab import r6_inkling_client as rc
from lab import r6_p0_probe as p0
from lab import tremor_admission_gate as gate

BATCH = p0.BATCH
B0_B1_CALLS = {"B0'": 28, "B1'": 280}  # prereg/R6-protocol-draft.md section 10 table; listed, never run here


class Refused(Exception):
    def __init__(self, name, detail=""):
        super().__init__(f"{name}: {detail}")
        self.name, self.detail = name, detail


def _sha_file(path):
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except (OSError, TypeError):
        return "absent"


def _sha_json(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _utc():
    return datetime.now(timezone.utc)


def _hostport(endpoint):
    u = urllib.parse.urlsplit(endpoint or "")
    try:
        port = u.port
    except ValueError:
        port = None
    if u.scheme != "http" or not u.hostname or port is None:
        raise Refused("endpoint-invalid", "endpoint must be http://IP:PORT")
    return u.hostname, port


def _allow_set(entries):
    got = set()
    for e in entries:
        host, _, port = e.rpartition(":")
        try:
            got.add((ipaddress.ip_address(host.strip("[]")), int(port)))
        except ValueError:
            raise Refused("allow-endpoint-invalid", f"{e!r} must be IP-literal HOST:PORT (no DNS names)") from None
    return got


def _endpoint_ok(a):
    host, port = _hostport(a.endpoint)
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False  # a DNS name is never resolved
    return ip.is_loopback or (ip, port) in _allow_set(a.allow_endpoint)


class _Receipts:
    def __init__(self, out):
        self.out = out

    def write(self, step, inputs, outcome, detail="", result=None, measured=None):
        body = {"step": step, "utc": _utc().isoformat(), "outcome": outcome, "detail": detail,
                "inputs": inputs, "result": result or {}, "measured": measured or {}}
        fd = os.open(os.path.join(self.out, step + ".json"),
                     os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(body, f, sort_keys=True, indent=1)
        return body


def _prepare_out(a):
    """--out must not exist and must sit directly under a real directory inside --out-root."""
    out = os.path.abspath(a.out)
    if os.path.lexists(out):
        raise Refused("out-not-new", out)
    root = os.path.realpath(a.out_root)
    parent = os.path.realpath(os.path.dirname(out))
    if os.path.commonpath([root, parent]) != root:
        raise Refused("out-outside-root", f"{out} is not under {root}")
    os.mkdir(os.path.join(parent, os.path.basename(out)), 0o700)
    return os.path.join(parent, os.path.basename(out))


def _prompts(a):
    got = {}
    for item in a.prompt:
        size, _, path = item.partition("=")
        try:
            got[int(size)] = Path(path).read_text(encoding="utf-8")
        except (ValueError, OSError, UnicodeError):
            return None, f"prompt {item!r} unreadable"
    if set(got) != set(p0.SIZES):
        return None, f"prompts must be given for exactly {list(p0.SIZES)}"
    return got, ""


def _manifest(a):
    prompts, why = _prompts(a)
    if prompts is None or a.seed is None:
        return None, why or "no --seed given"
    calls, i = [], 0
    for rep in range(p0.REPEATS):
        for size in p0.SIZES:
            for cap in p0.CAPS:
                i += 1
                body = {"messages": p0._messages(prompts[size]), "max_tokens": cap, "stream": False, "seed": a.seed}
                calls.append({"n": i, "repeat": rep, "input_tokens_target": size, "max_tokens": cap, "seed": a.seed,
                              "prompt_sha256": p0.prompt_sha256(prompts[size]),
                              "body_bytes": len(json.dumps(body).encode())})
    return {"batch": BATCH, "calls": calls,
            "caps": {"stops": dict(rc.P0_STOPS), "output_caps": list(p0.CAPS), "repeats": p0.REPEATS,
                     "max_total_tokens": a.max_total_tokens, "max_response_bytes": a.max_response_bytes},
            "listed_not_run": dict(B0_B1_CALLS)}, ""


_NEG = re.compile(r"^(no|none|not|n/a|na|nil|tbd|unknown|without|pending|later|todo)\b|^-|\bno (placement|quiet)", re.I)


def _instant(x):
    t = datetime.fromisoformat(x.strip().replace("Z", "+00:00"))
    if t.tzinfo is None or t.utcoffset().total_seconds() != 0:
        raise ValueError("not UTC")
    return t


def _notice_problem(text, now=None):
    fields = {}
    for line in text.splitlines():
        k, sep, v = line.partition(":")
        k = k.strip().lower()
        if sep and k in ("placement", "quiet_window"):
            if k in fields:
                return f"{k} given twice"
            fields[k] = v.strip()
    for k in ("placement", "quiet_window"):
        if not fields.get(k) or _NEG.search(fields[k]):
            return f"{k} missing, empty or negated"
    try:
        start, _, end = fields["quiet_window"].partition("/")
        start, end = _instant(start), _instant(end)
    except ValueError:
        return "quiet_window is not <UTC ISO start>/<UTC ISO end>"
    if end <= start:
        return "quiet_window end is not after the start"
    if not start <= (now or _utc()) < end:
        return "quiet_window has not started or has ended"
    return ""


def _static_refusals(a):
    if not a.freeze or not os.path.isfile(a.freeze):
        raise Refused("no-freeze-record", "give --freeze FILE")
    text = ""
    try:
        text = Path(a.pc_notice).read_text(encoding="utf-8") if a.pc_notice else ""
    except OSError:
        pass
    if not text.strip():
        raise Refused("no-pc-notice", "give --pc-notice FILE (non-empty)")
    problem = _notice_problem(text)
    if problem:
        raise Refused("pc-notice-incomplete", "notice needs the lines `placement: <value>` and `quiet_window: "
                      f"<start>/<end>` (UTC ISO instants, end after start, now inside [start, end)): {problem}")
    if not a.i_have_owner_confirm:
        raise Refused("no-owner-confirm", "pass --i-have-owner-confirm only with the owner's word")
    if not _endpoint_ok(a):
        raise Refused("endpoint-not-allowed", "not loopback and not in --allow-endpoint")
    missing = [n for n in ("seed", "gguf_path", "max_total_tokens", "max_response_bytes", "admission")
               if getattr(a, n) is None]
    if missing or _prompts(a)[0] is None:
        raise Refused("missing-live-input", f"missing {missing or 'prompts'}")


def _caps(a):
    return dict(hosted_cap=a.hosted_cap, gpu_cap=a.gpu_cap, max_window_hours=a.max_window_hours,
                owner_words=a.owner_words)


def _build_client(a, sink):
    host, _ = _hostport(a.endpoint)
    remote = not rc._is_loopback(host)
    s = rc.P0_STOPS
    try:
        return rc.InklingClient(
            a.endpoint, admission_path=a.admission if remote else None, repo_root=a.repo_root if remote else None,
            allow_remote=remote, timeout_s=s["timeout_s"], max_tokens=max(p0.CAPS), stub=not remote,
            max_calls=s["max_calls"], max_wall_s=s["max_wall_s"], max_total_tokens=a.max_total_tokens,
            max_errors=s["max_errors"], max_skips=s["max_skips"], skip_wait_s=s["skip_wait_s"],
            max_response_bytes=a.max_response_bytes, sink=sink, trace_path=None,
            freeze_path=a.freeze if remote else None, gate_caps=_caps(a) if remote else None), remote
    except rc.ClientRefused as e:
        raise Refused("client-refused", str(e)) from None


def _preclaim(a, prompts, man):
    """Everything run_p0 would refuse on its own, checked before a claim can be spent."""
    if isinstance(a.seed, bool) or not isinstance(a.seed, int) or not 0 <= a.seed < 2 ** 32:
        raise Refused("seed-out-of-range", "seed must be an int in [0, 2**32)")
    try:
        pinned = p0._manifest(p0._record(a.freeze, "freeze", BATCH))
    except rc.ClientRefused as e:
        raise Refused("freeze-unreadable", str(e)) from None
    if any(p0.prompt_sha256(t) not in pinned for t in prompts.values()):
        raise Refused("prompt-not-pinned", "a prompt is not pinned in the freeze record's protected_inputs")
    first = man["calls"][0]
    if first["body_bytes"] + first["max_tokens"] > a.max_total_tokens:
        raise Refused("token-budget-too-small",
                      f"--max-total-tokens {a.max_total_tokens} cannot cover the first call "
                      f"({first['body_bytes']} request bytes + {first['max_tokens']} output tokens)")


def _live(a, rec, in_sha):
    prompts, _ = _prompts(a)
    man, _ = _manifest(a)
    _preclaim(a, prompts, man)
    try:  # identity first: a mismatch must never spend the admission
        frozen = p0._snapshot(p0._record(a.freeze, "freeze", BATCH))
        same = p0.identity_matches(frozen, p0.identity_snapshot(a.proc_root, a.gguf_path))
    except (rc.ClientRefused, OSError) as e:
        raise Refused("identity-mismatch", f"unreadable: {e}") from None
    if not same:
        raise Refused("identity-mismatch", "live server differs from the freeze record's model_snapshot")
    sink = []
    client, remote = _build_client(a, sink)
    if not remote:  # a loopback client never claims; the launcher does, once, before any call
        try:
            gate.admit(a.freeze, a.admission, _utc(), a.repo_root, **_caps(a))
        except gate.AdmissionRefused as e:
            raise Refused("claim-refused", str(e)) from None
    try:
        res = p0.run_p0(client, prompts, sink=sink, seed=a.seed, stops=dict(rc.P0_STOPS), freeze_path=a.freeze,
                        admission_path=a.admission, proc_root=a.proc_root, gguf_path=a.gguf_path)
    except rc.ClientRefused as e:  # a refused claim or stop before any call; the claim may be spent
        rec.write("04-run", in_sha, "error", str(e))
        raise Refused("claim-refused" if remote else "run-refused", str(e)) from None
    finally:
        client.close()
    try:
        summary = p0.summarise(res["traces"], res["repeat_matches"], res["stopped"], res["default_temperature"])
    except rc.ClientRefused:  # no call was measured
        summary = None
    outcome = "error" if summary is None else "ok" if res["stopped"] is None else "stopped"
    rec.write("04-run", in_sha, outcome, res["stopped"] or "",
              result={"n_calls": len(res["traces"]), "stopped": res["stopped"],
                      "repeat_matches": res["repeat_matches"]},
              measured={"traces_sha256": _sha_json(res["traces"]), "summary": summary,
                        "wall_total_s": res["wall_total_s"]})
    if summary is None:
        rec.write("05-b0-estimate", {}, "skipped", "no call was measured")
        return 1
    if a.b0_calls is None or a.load_seconds is None:
        rec.write("05-b0-estimate", {}, "skipped", "give --b0-calls and --load-seconds")
    else:
        try:
            est = p0.b0_cost_estimate(summary, a.b0_calls, a.load_seconds)
            rec.write("05-b0-estimate", {"summary_sha256": _sha_json(summary)}, "ok", measured=est)
        except rc.ClientRefused as e:
            rec.write("05-b0-estimate", {"summary_sha256": _sha_json(summary)}, "refused", str(e))
    return 0 if res["stopped"] is None else 1


def _parser():
    ap = argparse.ArgumentParser(prog="tremor_gpu_run", allow_abbrev=False, description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--out-root", required=True, help="the directory --out must sit under")
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--model-dir", required=True)
    ap.add_argument("--min-mem-kib", required=True, type=int)
    ap.add_argument("--other-gpu-processes-allowed", action="store_true")
    ap.add_argument("--freeze")
    ap.add_argument("--admission")
    for n, t in (("hosted-cap", float), ("gpu-cap", float), ("max-window-hours", float)):
        ap.add_argument("--" + n, required=True, type=t)
    ap.add_argument("--owner-words", required=True)
    ap.add_argument("--prompt", action="append", default=[], metavar="SIZE=FILE")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--max-total-tokens", type=int)
    ap.add_argument("--max-response-bytes", type=int)
    ap.add_argument("--endpoint", required=True)
    ap.add_argument("--allow-endpoint", action="append", default=[], metavar="HOST:PORT")
    ap.add_argument("--proc-root", default="/proc")
    ap.add_argument("--gguf-path")
    ap.add_argument("--pc-notice")
    ap.add_argument("--b0-calls", type=int)
    ap.add_argument("--load-seconds", type=float)
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--i-have-owner-confirm", action="store_true")
    return ap


def main(argv=None, *, readiness_kw=None):
    a = _parser().parse_args(argv)
    rec = None
    try:
        _hostport(a.endpoint)
        _allow_set(a.allow_endpoint)
        if a.live:
            _static_refusals(a)
        out = _prepare_out(a)
        rec = _Receipts(out)
        in_sha = {"freeze": _sha_file(a.freeze), "admission": _sha_file(a.admission),
                  "pc_notice": _sha_file(a.pc_notice), **{f"prompt_{v.partition('=')[0]}": _sha_file(v.partition("=")[2])
                                                          for v in a.prompt}}
        # step 1
        r = ready.check(a.repo_root, a.model_dir, a.min_mem_kib, a.other_gpu_processes_allowed,
                        **(readiness_kw or {}))
        rec.write("01-readiness", {"model_manifest": _sha_file(os.path.join(a.model_dir, "MANIFEST.sha256.json")),
                                   "plan": _sha_file(os.path.join(a.repo_root, ready.PLAN))},
                  "ok" if r["ok"] else "fail", "", result={"ok": r["ok"]}, measured=r)
        # step 2: dry check, claims nothing
        gate_err = None
        if a.freeze and a.admission:
            try:
                gate.check(a.freeze, a.admission, _utc(), a.repo_root, **_caps(a))
            except gate.AdmissionRefused as e:
                gate_err = str(e)
        else:
            gate_err = "no --freeze or --admission given"
        rec.write("02-admission-check", {"freeze": in_sha["freeze"], "admission": in_sha["admission"]},
                  "ok" if gate_err is None else "refused", gate_err or "", result={"ok": gate_err is None})
        # step 3
        man, why = _manifest(a)
        rec.write("03-manifest", {k: v for k, v in in_sha.items() if k.startswith("prompt_")},
                  "ok" if man else "skipped", why, result={"manifest": man} if man else {})
        if a.live:
            if not r["ok"]:
                raise Refused("readiness-failed", "; ".join(r["failures"]))
            if gate_err is not None:
                raise Refused("admission-not-accepted", gate_err)
            return _live(a, rec, in_sha)
        print(f"DRY RUN (nothing sent). endpoint {a.endpoint}: "
              f"{'allowed' if _endpoint_ok(a) else 'would be REFUSED (not loopback, not allow-listed)'}")
        print(f"readiness: {'ok' if r['ok'] else 'FAIL ' + '; '.join(r['failures'])}")
        print(f"admission check: {'ok' if gate_err is None else 'REFUSED ' + gate_err}")
        print("manifest: " + (json.dumps(man, sort_keys=True) if man else f"not built ({why})"))
        rec.write("04-run", {}, "not-run", "dry-run: nothing sent")
        return 0 if r["ok"] and gate_err is None and man else 1
    except Refused as e:
        print(f"REFUSED[{e.name}]: {e.detail}")
        if rec:
            rec.write("04-refusal", {}, "refused", f"{e.name}: {e.detail}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
