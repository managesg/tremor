"""R6 fixed four-member Holm step-down over {H1, H3, H5, RT} and the claim rule (prereg/R6-protocol-draft.md
section 6, R6-O7, D8, D9). Pure; no I/O. The R5 pin lab/r5_perf_harness.py (family of 3) is not used or edited.

p per member (the caller computes them): H1 = max(p_EG4, p_EG8), 1 if the signs disagree; H3, H5 one-sided p_up;
RT one-sided exact McNemar. A member not run must be passed as p = 1 (no default is filled in here)."""
import math

FAMILY = ("H1", "H3", "H5", "RT")
# Supported side of the unadjusted 95% interval (R5:33, R6:78-81; protocol, not a parameter). H1: both on the same side.
SUPPORT = {"H1": "same", "H3": "above", "H5": "above", "RT": "below"}


def _num(x, name):
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        raise ValueError(f"{name} must be a finite real number, not bool/NaN/inf")
    return x


def holm_family(p_values, *, alpha):
    """Step-down over exactly H1, H3, H5, RT. Returns {member: {p, step, threshold, tested, rejected}}.
    Sorted by (p, canonical order); tested at threshold alpha/(4 - step + 1); stops at the first non-rejection
    (later members: tested False, rejected False, threshold still reported)."""
    a = _num(alpha, "alpha")
    if not 0 < a < 1:
        raise ValueError("alpha must be in (0, 1)")
    if not isinstance(p_values, dict) or set(p_values) != set(FAMILY):
        raise ValueError(f"p_values must have exactly the keys {FAMILY}")
    for m in FAMILY:
        if not 0 <= _num(p_values[m], f"p[{m}]") <= 1:
            raise ValueError(f"p[{m}] must be in [0, 1]")
    out, stopped = {}, False
    for step, m in enumerate(sorted(FAMILY, key=lambda k: (p_values[k], FAMILY.index(k))), start=1):
        thr = a / (len(FAMILY) - step + 1)
        tested = not stopped
        rej = tested and p_values[m] <= thr
        stopped = stopped or not rej
        out[m] = {"p": p_values[m], "step": step, "threshold": thr, "tested": tested, "rejected": rej}
    return out


def _side(iv, name):
    if (not isinstance(iv, (tuple, list)) or len(iv) != 2
            or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in iv)
            or iv[0] > iv[1]):
        raise ValueError(f"{name} must be a (lo, hi) pair of finite numbers with lo <= hi")
    lo, hi = iv
    return "above" if lo > 0 else "below" if hi < 0 else "straddles"


def _check_holm(holm):
    keys = {"p", "step", "threshold", "tested", "rejected"}
    if not isinstance(holm, dict) or set(holm) != set(FAMILY):
        raise ValueError("holm must be a holm_family result")
    steps = []
    for m in FAMILY:
        e = holm[m]
        if (not isinstance(e, dict) or set(e) != keys or not isinstance(e["tested"], bool)
                or not isinstance(e["rejected"], bool) or (e["rejected"] and not e["tested"])
                or isinstance(e["step"], bool) or not isinstance(e["step"], int) or not 1 <= e["step"] <= 4
                or not 0 <= _num(e["p"], "p") <= 1 or not 0 < _num(e["threshold"], "threshold") < 1):
            raise ValueError(f"holm[{m}] is not a holm_family entry")
        steps.append(e["step"])
    if sorted(steps) != [1, 2, 3, 4]:
        raise ValueError("holm steps must be 1..4")


def claim(member, holm, interval, direction, *, k):
    """'killed' | 'supported' | 'not_supported'. Kill wins: a killed member is never supported, even if Holm rejects.
    holm: the holm_family result. interval: unadjusted 95% (lo, hi); for H1 a pair of such intervals (EG4, EG8).
    direction: the supported side ('same' for H1, 'above' H3/H5, 'below' RT), must equal the protocol's. k: the B1 constant, a number for H5 and None else.
    Kill: H1 intervals on opposite sides; H3 interval below 0; H5 upper bound below k; RT interval above 0.
    Supported: Holm rejection and the interval(s) strictly on the supported side (H1: both strictly on one same side)."""
    if member not in FAMILY:
        raise ValueError(f"member must be one of {FAMILY}")
    if direction != SUPPORT[member]:
        raise ValueError(f"direction for {member} must be {SUPPORT[member]!r}")
    _check_holm(holm)
    if (member == "H5") != (k is not None):
        raise ValueError("k is required for H5 and must be None for the others")
    if k is not None:
        _num(k, "k")
    rej = holm[member]["rejected"]
    if member == "H1":
        if not isinstance(interval, (tuple, list)) or len(interval) != 2:
            raise ValueError("H1 interval must be the pair (EG4 interval, EG8 interval)")
        s = {_side(interval[0], "EG4"), _side(interval[1], "EG8")}
        killed = s == {"above", "below"}
        ok = len(s) == 1 and s != {"straddles"}
    else:
        side = _side(interval, "interval")
        killed = interval[1] < k if member == "H5" else side == ("below" if member == "H3" else "above")
        ok = side == direction
    return "killed" if killed else "supported" if rej and ok else "not_supported"
