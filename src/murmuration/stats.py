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
