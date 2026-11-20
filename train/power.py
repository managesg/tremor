"""nvidia-smi power parsing and GPU energy integration. Stdlib only, no process calls here.

Sample with ONE long-lived call outside this module (the plan's format, no header, no units):
  nvidia-smi --query-gpu=timestamp,power.draw,utilization.gpu --format=csv,noheader,nounits -lms 1000
Headered output (e.g. timestamp,power.draw.instant,utilization.gpu with units like '4.80 W', '4 %') also parses.
Samples are (t_seconds, watts, util_percent_or_None); (t, watts) pairs are accepted (util unknown).
"""
import datetime as dt
import re

NOTE = "GPU-only: nvidia-smi board power; excludes CPU, memory host, disk and wall power."
FIELDS = ("power.draw.instant", "power.draw.average", "power.draw")
UNITS = {"joules_gpu": "J", "joules_gpu_net": "J", "seconds": "s", "baseline_w": "W",
         "idle_fraction": "fraction of GPU-seconds with utilization.gpu == 0"}


def parse_watts(s):
    m = re.match(r"\s*([0-9]*\.?[0-9]+)\s*(?:W)?\s*$", s or "")
    return float(m.group(1)) if m else None  # '[N/A]', '' -> None


def parse_util(s):
    m = re.match(r"\s*([0-9]+)\s*(?:%)?\s*$", s or "")
    return int(m.group(1)) if m else None


def _ts(s):
    s = s.strip()
    try:
        return dt.datetime.strptime(s, "%Y/%m/%d %H:%M:%S.%f").timestamp()
    except ValueError:
        return dt.datetime.fromisoformat(s).timestamp()


def _ts(s):
    s = s.strip()
    try:
        return dt.datetime.strptime(s, "%Y/%m/%d %H:%M:%S.%f").timestamp()
    except ValueError:
        return dt.datetime.fromisoformat(s).timestamp()


def parse_csv(text, field=None):
    """nvidia-smi CSV -> [(t_seconds, watts, util_or_None)]; unreadable rows skipped.
    No header line (the plan's noheader format): columns are timestamp, power, utilization in that order.
    A header line must name a timestamp and a power column, else ValueError."""
    lines = [l for l in text.splitlines() if l.strip()]
    if not lines:
        raise ValueError("empty input")
    if "timestamp" in lines[0].lower():
        head = [h.strip().lower() for h in lines[0].split(",")]
        ti = head.index(next(h for h in head if h.startswith("timestamp")))
        names = [field] if field else FIELDS
        pi = next((i for n in names for i, h in enumerate(head) if h.startswith(n)), None)
        if pi is None:
            raise ValueError("no power column in header: %r" % head)
        ui = next((i for i, h in enumerate(head) if h.startswith("utilization.gpu")), None)
        lines = lines[1:]
    else:
        ti, pi, ui = 0, 1, 2
    out = []
    for l in lines:
        c = l.split(",")
        try:
            w = parse_watts(c[pi])
            if w is not None:
                out.append((_ts(c[ti]), w, parse_util(c[ui]) if ui is not None and ui < len(c) else None))
        except (ValueError, IndexError):
            continue
    if not out and len(lines) > 0:
        raise ValueError("no readable rows")
    return out


def baseline_watts(samples):
    """Mean watts of a separate pre-job idle record (the plan's 60 s baseline); never the job's own minimum."""
    r = sample(samples)
    if not r["seconds"]:
        raise ValueError("baseline record spans zero seconds")
    return r["joules_gpu"] / r["seconds"]


def sample(samples, baseline_w=None):
    """Trapezoid energy over samples. joules_gpu is gross (raw). With baseline_w (from baseline_watts of a
    separate pre-job record) joules_gpu_net = gross - baseline_w * seconds, else None.
    idle_fraction = GPU-seconds whose interval-start utilization.gpu == 0 over reserved GPU-seconds (one GPU);
    None when utilization is missing or the window has zero seconds."""
    if len(samples) < 2:
        raise ValueError("need at least 2 samples")
    s = sorted(samples, key=lambda x: x[0])
    joules = idle = 0.0
    util_known = True
    for a, b in zip(s, s[1:]):
        dtt = b[0] - a[0]
        joules += (a[1] + b[1]) / 2 * dtt
        u = a[2] if len(a) > 2 else None
        if u is None:
            util_known = False
        elif u == 0:
            idle += dtt
    secs = s[-1][0] - s[0][0]
    return {"joules_gpu": joules,
            "joules_gpu_net": None if baseline_w is None else joules - baseline_w * secs,
            "seconds": secs,
            "idle_fraction": idle / secs if secs and util_known else None,
            "baseline_w": baseline_w, "units": UNITS, "note": NOTE}
