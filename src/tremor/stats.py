"""Statistics per SCIENCE.md section 5. Stdlib only."""
import random
from collections import defaultdict
from decimal import Decimal
from fractions import Fraction
from numbers import Rational, Real

from .manifest import tree_hash


def paired_bootstrap(rows, cluster, metric, n=10000, seed=0):
    """Percentile 95% CI of metric(rows) resampling whole clusters (row[cluster]) with replacement.

    metric: callable(list of rows) -> float, e.g. mean paired difference. Returns (point, lo, hi).
    shortcut: plain percentile interval, no bias correction; upgrade if clusters < ~20.
    """
    groups = defaultdict(list)
    for r in rows:
        groups[r[cluster]].append(r)
    keys = sorted(groups)
    rng = random.Random(seed)
    vals = sorted(metric([r for k in (rng.choice(keys) for _ in keys) for r in groups[k]]) for _ in range(n))
    return metric(rows), vals[int(0.025 * (n - 1))], vals[int(0.975 * (n - 1))]


def _validate_probability(value, label):
    if (isinstance(value, bool) or not isinstance(value, (Real, Decimal))
            or (isinstance(value, Decimal) and not value.is_finite()) or not 0 <= value <= 1):
        raise ValueError(f"{label} must be a finite probability in [0, 1]")


def holm(pvals, alpha=0.05):
    """Holm step-down with finite inputs in [0, 1]. Reject flags retain input order."""
    _validate_probability(alpha, "alpha")
    for i, pval in enumerate(pvals):
        _validate_probability(pval, f"pvals[{i}]")
    if isinstance(alpha, (Decimal, Rational)):
        alpha = Fraction(alpha)  # Keep exact alpha values exact through division.
    m = len(pvals)
    reject = [False] * m
    for rank, i in enumerate(sorted(range(m), key=lambda j: pvals[j])):
        if pvals[i] > alpha / (m - rank):
            break
        reject[i] = True
    return reject


def all_seeds_rate(rows, task="task", ok="pass"):
    """Share of tasks where every row (seed) passed; None if no rows."""
    by = defaultdict(list)
    for r in rows:
        by[r[task]].append(bool(r[ok]))
    return sum(all(v) for v in by.values()) / len(by) if by else None


def check_prereg(frozen_hash, paths, *, root=None):
    """Raise ValueError if the code tree no longer matches the frozen code_tree_hash."""
    now = tree_hash(paths, root=root)
    if now != frozen_hash:
        raise ValueError(f"code_tree_hash mismatch: frozen {frozen_hash}, now {now}")


def _col_mean(rows, f):
    return sum(f(r) for r in rows) / len(rows)


def _pct(sorted_vals, q):
    return sorted_vals[int(q * (len(sorted_vals) - 1))]


def hdi(rows, cluster, n=10000, seed=0, margin=0.10, tol=1e-9):
    """HDI = (Y_code - Y_play) / (Y_code - Y_none), paired cluster bootstrap by `cluster` (the task set).

    rows: dicts with row[cluster] plus numeric "none", "play", "code". MARGIN RULE (EP1 section on HDI):
    the ratio is reported only if the interval of Y_code - Y_none is wholly above 0 AND its point is
    >= margin (default 0.10). Wholly below 0 -> not_interpretable / code_worse_than_none; straddling 0
    or point under margin -> not_interpretable / code_gain_unresolved; no rows -> "no rows". A
    denominator with |d| < tol counts as undefined (dropped, counted), not only exact 0. The three raw
    contrasts always come back, each with point and 95% bootstrap interval; `recovered` = 1 - HDI only
    when interpretable. HDI values outside [0, 1] stay visible, never clipped.
    shortcut: percentile intervals; resamples with an undefined denominator are dropped and counted.
    """
    cons = {"play_none": ("play", "none"), "code_none": ("code", "none"), "code_play": ("code", "play")}
    out = {"point": None, "lo": None, "hi": None, "denom_ci": None, "undefined": True, "reason": None,
           "status": "not_interpretable", "recovered": None, "margin": margin, "degenerate_resamples": 0,
           "contrasts": {k: {"d": None, "lo": None, "hi": None} for k in cons}}
    if not rows:
        return {**out, "reason": "no rows"}
    groups = defaultdict(list)
    for r in rows:
        groups[r[cluster]].append(r)
    keys = sorted(groups)
    rng = random.Random(seed)
    boots = {k: [] for k in cons}
    num, den, ratios = lambda r: r["code"] - r["play"], lambda r: r["code"] - r["none"], []
    for _ in range(n):
        s = [r for k in (rng.choice(keys) for _ in keys) for r in groups[k]]
        m = {k: _col_mean(s, lambda r, a=a, b=b: r[a] - r[b]) for k, (a, b) in cons.items()}
        for k in cons:
            boots[k].append(m[k])
        d = _col_mean(s, den)
        if abs(d) < tol:
            out["degenerate_resamples"] += 1
        else:
            ratios.append(_col_mean(s, num) / d)
    for k, (a, b) in cons.items():
        v = sorted(boots[k])
        out["contrasts"][k] = {"d": _col_mean(rows, lambda r, a=a, b=b: r[a] - r[b]),
                               "lo": _pct(v, 0.025), "hi": _pct(v, 0.975)}
    c = out["contrasts"]["code_none"]
    out["denom_ci"] = (c["lo"], c["hi"])
    if c["hi"] < 0:
        return {**out, "reason": "code_worse_than_none"}
    if c["lo"] <= 0 or c["d"] < margin - 1e-12 or abs(c["d"]) < tol or not ratios:
        return {**out, "reason": "code_gain_unresolved"}
    ratios.sort()
    point = _col_mean(rows, num) / _col_mean(rows, den)
    return {**out, "undefined": False, "status": "interpretable", "point": point, "recovered": 1 - point,
            "lo": _pct(ratios, 0.025), "hi": _pct(ratios, 0.975)}


def emergence_gain(team, nominal):
    """EG = Y_team - Y_nominal; each argument is a number or a sequence of per-task outcomes (mean taken)."""
    m = lambda x: sum(x) / len(x) if hasattr(x, "__len__") else x
    return m(team) - m(nominal)


def nominal_group(rows, task="task", answer="answer", ok="pass"):
    """Pool the agents' rows per task and de-duplicate identical answers; the group passes if any
    distinct answer passes. Returns one dict per task, sorted by task."""
    by = defaultdict(list)
    for r in rows:
        by[r[task]].append(r)
    res = []
    for t in sorted(by):
        uniq = {}
        for r in by[t]:
            uniq.setdefault(r[answer], bool(r[ok]))
        res.append({"task": t, "pass": any(uniq.values()), "agents": len(by[t]), "unique": len(uniq),
                    "duplicates": len(by[t]) - len(uniq)})
    return res


def incoherence(errors):
    """Hot Mess incoherence over repeats of one task: variance / (bias^2 + variance), errors = signed
    per-repeat errors. None (undefined) under 3 repeats; 0.0 when errors are identical or all zero."""
    if len(errors) < 3:
        return None
    m = sum(errors) / len(errors)
    var = sum((e - m) ** 2 for e in errors) / len(errors)
    tot = m * m + var
    return var / tot if tot else 0.0


# Two-sided 95% critical t for df 1..60 (standard table); above 60 the normal 1.96 is used, which is
# slightly narrow (true t is 1.999 at df 61, 1.980 at df 120).
_T95 = [12.706, 4.303, 3.182, 2.776, 2.571, 2.447, 2.365, 2.306, 2.262, 2.228, 2.201, 2.179, 2.160, 2.145,
        2.131, 2.120, 2.110, 2.101, 2.093, 2.086, 2.080, 2.074, 2.069, 2.064, 2.060, 2.056, 2.052, 2.048,
        2.045, 2.042, 2.040, 2.037, 2.035, 2.032, 2.030, 2.028, 2.026, 2.024, 2.023, 2.021, 2.020, 2.018,
        2.017, 2.015, 2.014, 2.013, 2.012, 2.011, 2.010, 2.009, 2.008, 2.007, 2.006, 2.005, 2.004, 2.003,
        2.002, 2.002, 2.001, 2.000]


def paired_t(pairs):
    """Paired t interval over task-set-level pairs (a, b): diff = a - b, df = n - 1, 95% two-sided.

    Returns {mean_diff, se, t, df, ci95_lo, ci95_hi}; t is None when se is 0. Needs n >= 2 pairs.
    shortcut: tabulated critical values (df 1..60), normal 1.96 above; no scipy.
    """
    d = [a - b for a, b in pairs]
    n = len(d)
    if n < 2:
        raise ValueError("paired_t needs at least 2 pairs")
    m = sum(d) / n
    se = (sum((x - m) ** 2 for x in d) / (n - 1) / n) ** 0.5
    crit = _T95[n - 2] if n - 1 <= 60 else 1.96
    return {"mean_diff": m, "se": se, "t": m / se if se else None, "df": n - 1,
            "ci95_lo": m - crit * se, "ci95_hi": m + crit * se}
