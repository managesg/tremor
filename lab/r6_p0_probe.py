"""R6 probe P0 driver and B0 cost numbers (prereg/R6-protocol-draft.md section 10, plan 6.2).

Stdlib only. Drives lab.r6_inkling_client through the twelve-call P0 sequence under the plan's
stop rules; no defaults for open parameters (seed, stops, prompts, calls, load seconds).
Request and response text never enters a trace; repeat equality is kept as a boolean.
"""
import hashlib
import json
import math
import os
import statistics
import time

from lab import r6_inkling_client as rc
from lab import tremor_admission_gate as gate

SIZES = (200, 1000, 2000)   # input tokens, plan 6.2 step 2
CAPS = (64, 300)            # output caps, plan 6.2 step 2
REPEATS = 2                 # same-seed repeats
N_REQUIRED = rc.P0_STOPS["max_calls"]
BATCH = "r6-p0"
_ID_KEYS = {"pid", "start_ticks", "exe_sha256", "cmdline", "gguf_path", "gguf_dev", "gguf_inode",
            "gguf_size", "gguf_mtime_ns"}


def identity_snapshot(proc_root, gguf_path):
    """Read-only. The pid is the one process whose maps map the GGUF (same inode, device and path);
    fail closed unless exactly one. /proc/<pid>/maps and /proc/<pid>/exe are readable only by the
    server's own user or root; any other user gets OSError here (the driver turns that into a stop).
    cmdline carries the server arguments (model, mmproj, context size, slots, reasoning flags)."""
    st = os.stat(gguf_path)
    dev = f"{os.major(st.st_dev):02x}:{os.minor(st.st_dev):02x}"
    pids = []
    for name in sorted(os.listdir(proc_root)):
        if not name.isdigit():
            continue
        try:
            with open(os.path.join(proc_root, name, "maps")) as f:
                for line in f:
                    p = line.split(None, 5)
                    if len(p) == 6 and p[3] == dev and p[4] == str(st.st_ino) and p[5].strip() == gguf_path:
                        pids.append(name)
                        break
        except OSError:
            continue
    if len(pids) != 1:
        raise rc.ClientRefused(f"expected exactly one process mapping the GGUF, found {len(pids)}")
    base = os.path.join(proc_root, pids[0])
    with open(os.path.join(base, "stat")) as f:
        text = f.read()
    start_ticks = int(text[text.rindex(")") + 2:].split()[19])  # field 22 of proc(5) stat
    h = hashlib.sha256()
    with open(os.path.join(base, "exe"), "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    with open(os.path.join(base, "cmdline"), "rb") as f:
        cmdline = [x.decode("utf-8", "replace") for x in f.read().split(b"\0") if x]
    return {"pid": int(pids[0]), "start_ticks": start_ticks, "exe_sha256": h.hexdigest(),
            "cmdline": cmdline, "gguf_path": gguf_path, "gguf_dev": dev, "gguf_inode": st.st_ino,
            "gguf_size": st.st_size, "gguf_mtime_ns": st.st_mtime_ns}


def identity_matches(a, b):
    return (isinstance(a, dict) and isinstance(b, dict)
            and set(a) == _ID_KEYS and set(b) == _ID_KEYS and a == b)


def cmdline_temperature(cmdline):
    """Server default temperature from --temp/--temperature (also =VALUE form); None if absent, never guessed."""
    for i, a in enumerate(cmdline):
        for flag in ("--temp", "--temperature"):
            v = a[len(flag) + 1:] if a.startswith(flag + "=") else (
                cmdline[i + 1] if a == flag and i + 1 < len(cmdline) else None)
            if v is not None:
                try:
                    t = float(v)
                except ValueError:
                    return None
                return t if 0 <= t < math.inf else None
    return None


def prompt_sha256(prompt):
    """A sealed prompt is its text (sha256 of the UTF-8 bytes) or a messages list (sha256 of its canonical JSON)."""
    raw = prompt.encode() if isinstance(prompt, str) else json.dumps(prompt, sort_keys=True,
                                                                  separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def _messages(prompt):
    return [{"role": "user", "content": prompt}] if isinstance(prompt, str) else prompt


def _stops(stops, client):
    """Every stop value must be present and no looser than the plan's rc.P0_STOPS; the client's own
    timeout and skip wait must be no looser than the stops."""
    if not isinstance(stops, dict) or set(rc.P0_STOPS) - set(stops):
        raise rc.ClientRefused("stops must carry " + ", ".join(rc.P0_STOPS))
    for k, cap in rc.P0_STOPS.items():
        v = stops[k]
        (rc._posint if isinstance(cap, int) else rc._posnum)(v, k)
        if v > cap:
            raise rc.ClientRefused(f"{k} {v} is above the plan's {cap}")
    for attr, k in (("_timeout", "timeout_s"), ("_skip_wait", "skip_wait_s")):
        v = getattr(client, attr, None)
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not 0 < v <= stops[k]:
            raise rc.ClientRefused(f"client {k} must be positive and at most {stops[k]}")
    return stops


def _record(path, what, batch):
    try:
        with open(path) as f:
            d = json.load(f, object_pairs_hook=gate._unique, parse_constant=gate._bad_const)
    except Exception:
        raise rc.ClientRefused(f"{what} record unreadable") from None
    if not isinstance(d, dict) or d.get("batch") != batch:
        raise rc.ClientRefused(f"{what} record batch is not {batch!r}")
    return d


def _snapshot(freeze):
    snap = freeze.get("model_snapshot")
    if not isinstance(snap, dict) or set(snap) != _ID_KEYS:
        raise rc.ClientRefused("freeze model_snapshot must hold exactly the identity keys")
    return snap


def _manifest(freeze):
    pins = freeze.get("protected_inputs")
    if not isinstance(pins, list) or not pins or not all(isinstance(x, dict) and isinstance(x.get("sha256"), str)
                                                          for x in pins):
        raise rc.ClientRefused("freeze protected_inputs must list sha256 pins")
    return {x["sha256"] for x in pins}


def run_p0(client, prompts, *, sink, seed, stops, freeze_path, admission_path, proc_root, gguf_path,
           clock=None):
    """One client built with max_tokens == max(CAPS) and the given sink; per call max_tokens is 64 or 300.
    prompts: {200: text, 1000: text, 2000: text} (a messages list is also taken); each sha256 (prompt_sha256) must be pinned
    in the freeze record's protected_inputs. Order: batch id, prompt manifest, identity, claim, calls.
    Returns {"traces", "stopped", "wall_total_s", "repeat_matches"}; a stop returns what was measured.
    Call order (repeats outermost, then size, then cap) is a ruling of the coordinator."""
    clock = clock or time.monotonic
    cap_max = max(CAPS)
    if getattr(client, "_max_tokens", None) != cap_max or getattr(client, "_sink", None) is not sink:
        raise rc.ClientRefused("client needs max_tokens == %d and the shared sink" % cap_max)
    if not isinstance(prompts, dict) or set(prompts) != set(SIZES) or not all(
            (isinstance(m, str) and m) or (isinstance(m, list) and m) for m in prompts.values()):
        raise rc.ClientRefused(f"prompts must be keyed by exactly {SIZES}, each sealed text or a non-empty messages list")
    rc._posint(seed, "seed", zero=True)
    if seed >= 2 ** 32:  # llama.cpp seeds are 32-bit
        raise rc.ClientRefused("seed must be below 2**32 (llama.cpp seeds are 32-bit)")
    stops = _stops(stops, client)
    if sink:
        raise rc.ClientRefused("sink must start empty")
    if getattr(client, "_claimed", False):
        raise rc.ClientRefused("client already claimed before the checks")
    freeze = _record(freeze_path, "freeze", BATCH)
    _record(admission_path, "admission", BATCH)
    remote = getattr(client, "_remote", False)
    if remote and tuple(getattr(client, "_gate_args", (None, None))[:2]) != (freeze_path, admission_path):
        raise rc.ClientRefused("client was built on other freeze or admission records")
    pinned = _manifest(freeze)
    if any(prompt_sha256(m) not in pinned for m in prompts.values()):
        raise rc.ClientRefused("a prompt is not pinned in the freeze record")
    frozen = _snapshot(freeze)
    # identity before the claim: a mismatch must never spend the admission
    try:
        live = identity_snapshot(proc_root, gguf_path)
    except Exception as e:
        raise rc.StopRule(f"identity unreadable: {type(e).__name__}") from None
    if not identity_matches(frozen, live):
        raise rc.StopRule("identity mismatch")
    if remote:
        client.claim()
    t0 = clock()
    stopped, hashes, matches = None, {}, []
    try:
        for rep in range(REPEATS):
            for size in SIZES:
                for cap in CAPS:
                    n, errs = len(sink), sum(1 for r in sink if r["error"])
                    skips = sum(1 for r in sink if r["skip"])
                    own = client.remaining_wall_s()  # None until the client's first call
                    left = min(stops["max_wall_s"] - (clock() - t0), math.inf if own is None else own)
                    if n >= stops["max_calls"]:
                        stopped = "max_calls reached"
                    elif errs >= stops["max_errors"]:
                        stopped = "errors"
                    elif skips >= stops["max_skips"]:
                        stopped = "skip spike"
                    elif left < client._timeout:  # a call could outrun the wall budget
                        stopped = "wall budget below the per-call timeout"
                    if stopped:
                        break
                    try:
                        res = client.call(_messages(prompts[size]), max_tokens=cap, seed=seed)
                        h = hashlib.sha256(res["content"].encode()).hexdigest()
                    except rc.CallFailed:
                        h = None
                    if rep == 0:
                        hashes[(size, cap)] = h
                    else:
                        first = hashes[(size, cap)]
                        matches.append(None if h is None or first is None else h == first)
                if stopped:
                    break
            if stopped:
                break
    except rc.ClientRefused as e:  # StopRule included: report what was measured
        stopped = str(e) or type(e).__name__
    return {"traces": [dict(r) for r in sink], "stopped": stopped,
            "wall_total_s": clock() - t0, "repeat_matches": matches,
            "default_temperature": cmdline_temperature(live["cmdline"])}


def _share(r):
    rt, ct = r.get("reasoning_tokens"), r.get("completion_tokens")
    ok = all(isinstance(x, int) and not isinstance(x, bool) and x >= 0 for x in (rt, ct))
    return (rt / ct if ct else None) if ok and rt <= ct else None


def _invalid_reasoning(r):
    rt, ct = r.get("reasoning_tokens"), r.get("completion_tokens")
    return all(isinstance(x, int) and not isinstance(x, bool) and x >= 0 for x in (rt, ct)) and rt > ct


def summarise(trace, repeat_matches=None, stopped=None, default_temperature=None):
    """trace: list of client trace records. Numbers B0 needs; None where nothing was measured.
    stopped: the run's stop reason (None for a run that ended by itself).
    default_temperature: run_p0's value from the server cmdline, reported next to seed-repeat equality."""
    if not isinstance(trace, list) or not trace:
        raise rc.ClientRefused("trace must be a non-empty list")
    walls = [r["wall_s"] for r in trace]
    if any(isinstance(w, bool) or not isinstance(w, (int, float)) or not 0 <= w < math.inf for w in walls):
        raise rc.ClientRefused("every trace record needs a finite wall_s")
    ok = [r for r in trace if not r["error"]]
    okw = [r["wall_s"] for r in ok]
    waits = [r["queue_wait_s"] for r in ok if r["queue_wait_s"] is not None]
    tps = [r["tokens_per_s"] for r in ok if r["tokens_per_s"] is not None]
    tps_wall = [r["completion_tokens"] / r["wall_s"] for r in ok if r["wall_s"] > 0]
    seeded = [m for m in (repeat_matches or []) if m is not None]
    known = [r for r in ok if _share(r) is not None]  # reasoning_tokens None is counted apart, never guessed
    rt_sum, ct_sum = sum(r["reasoning_tokens"] for r in known), sum(r["completion_tokens"] for r in known)
    return {
        "n_calls": len(trace), "n_ok": len(ok), "n_errors": len(trace) - len(ok), "stopped": stopped,
        "skip_rate": sum(1 for r in trace if r["skip"]) / len(trace),
        "wall_max_s": max(walls),  # T: worst wall per call, errors and queue included
        "wall_p50_s": statistics.median(walls),
        "wall_max_ok_s": max(okw) if okw else None,
        "wall_total_s": sum(walls),
        "tokens_per_s_min": min(tps) if tps else None,   # slowest generation rate (server timings, else wall)
        "tokens_per_s_p50": statistics.median(tps) if tps else None,
        "tokens_per_s_wall_min": min(tps_wall) if tps_wall else None,  # completion tokens over whole wall
        "queue_wait_reported": len(waits),
        "queue_wait_max_s": max(waits) if waits else None,
        "seed_pairs": len(seeded), "seed_pairs_equal": sum(1 for m in seeded if m),
        "reasoning_per_call": [_share(r) for r in trace],
        "default_temperature": default_temperature,
        "reasoning_invalid": sum(1 for r in ok if _invalid_reasoning(r)),  # reasoning_tokens > completion_tokens
        "reasoning_note": "reasoning_tokens may be None on every call if the server does not fill "
                          "completion_tokens_details (unverified for this build); the share is then unknown",
        "reasoning_known": len(known), "reasoning_unknown": len(trace) - len(known),
        "reasoning_share": (rt_sum / ct_sum) if ct_sum else None,
    }


def b0_cost_estimate(summary, calls, load_seconds):
    """R5 plan B0: (calls x measured per-call seconds + load seconds) / 3600 GPU-hours.
    Returns {"gpu_hours", "t_s", "t_is_bound"}. Refuses a stopped run and any run short of N_REQUIRED
    calls or at the error stop. One tolerated error: T is the worst wall including that call, a bound."""
    if not isinstance(summary, dict) or not all(k in summary for k in ("n_calls", "n_errors", "wall_max_s", "stopped")):
        raise rc.ClientRefused("summary must come from summarise()")
    if summary["stopped"]:
        raise rc.ClientRefused(f"P0 was stopped: {summary['stopped']}")
    if summary["n_calls"] < N_REQUIRED or summary["n_errors"] >= rc.P0_STOPS["max_errors"]:
        raise rc.ClientRefused(f"sample below the protocol: need {N_REQUIRED} calls with fewer than "
                               f"{rc.P0_STOPS['max_errors']} errors, have {summary['n_calls']} with {summary['n_errors']}")
    t = rc._posnum(summary["wall_max_s"], "wall_max_s")
    if summary["n_errors"] > 0:  # a fast error says nothing about the worst case: bound by the per-call timeout
        t = max(t, rc.P0_STOPS["timeout_s"])
    rc._posint(calls, "calls")
    if isinstance(load_seconds, bool) or not isinstance(load_seconds, (int, float)) \
            or not 0 <= load_seconds < math.inf:
        raise rc.ClientRefused("load_seconds must be a finite non-negative number")
    return {"gpu_hours": (calls * t + load_seconds) / 3600.0, "t_s": t, "t_is_bound": summary["n_errors"] > 0}
