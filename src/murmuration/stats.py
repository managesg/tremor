"""Statistics per SCIENCE.md section 5. Stdlib only."""
import random
from collections import defaultdict

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


def holm(pvals, alpha=0.05):
    """Holm step-down; returns reject flags in input order."""
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


def check_prereg(frozen_hash, paths):
    """Raise ValueError if the code tree no longer matches the frozen code_tree_hash."""
    now = tree_hash(paths)
    if now != frozen_hash:
        raise ValueError(f"code_tree_hash mismatch: frozen {frozen_hash}, now {now}")


def _col_mean(rows, f):
    return sum(f(r) for r in rows) / len(rows)


def hdi(rows, cluster, n=10000, seed=0):
    """HDI = (Y_code - Y_play) / (Y_code - Y_none) with a paired cluster bootstrap (EMERGENCE-PROGRAM 2.2).

    rows: dicts with row[cluster] plus numeric "none", "play", "code". Values outside [0, 1] are real
    results (below 0: playbook beats code; above 1: playbook hurts), never clipped. If the 95% interval
    of Y_code - Y_none contains 0, returns undefined with a reason and no number.
    shortcut: percentile intervals, resamples with a zero denominator are dropped and counted.
    """
    out = {"point": None, "lo": None, "hi": None, "denom_ci": None, "undefined": False,
           "reason": None, "degenerate_resamples": 0}
    if not rows:
        return {**out, "undefined": True, "reason": "no rows"}
    groups = defaultdict(list)
    for r in rows:
        groups[r[cluster]].append(r)
    keys = sorted(groups)
    rng = random.Random(seed)
    num, den, ratios = lambda r: r["code"] - r["play"], lambda r: r["code"] - r["none"], []
    dens = []
    for _ in range(n):
        s = [r for k in (rng.choice(keys) for _ in keys) for r in groups[k]]
        d = _col_mean(s, den)
        dens.append(d)
        if d == 0:
            out["degenerate_resamples"] += 1
        else:
            ratios.append(_col_mean(s, num) / d)
    dens.sort()
    dlo, dhi = dens[int(0.025 * (n - 1))], dens[int(0.975 * (n - 1))]
    out["denom_ci"] = (dlo, dhi)
    d0 = _col_mean(rows, den)
    if dlo <= 0 <= dhi or d0 == 0 or not ratios:
        return {**out, "undefined": True, "reason": "interval of Y_code - Y_none contains 0"}
    ratios.sort()
    m = len(ratios)
    return {**out, "point": _col_mean(rows, num) / d0, "lo": ratios[int(0.025 * (m - 1))],
            "hi": ratios[int(0.975 * (m - 1))]}


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
