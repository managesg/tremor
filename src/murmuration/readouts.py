"""Readouts from logs only (PROPOSAL-RESIDENCY-V3 section 3, item 3). Pure functions, stdlib only.

Formulas (standard statistics, not results of this project):
- overdispersion: Pearson dispersion for k task sets with n reruns each, pooled p: var_ddof1(counts) /
  (n p (1-p)); 1 under independent Bernoulli(p) reruns (binomial), >1 when task sets differ (McCullagh &
  Nelder, Generalized Linear Models, ch. 4).
- dose slope: OLS slope, percentile bootstrap over (dose, y) pairs (Efron & Tibshirani 1993).
- R: pooled mean offspring over a transmission forest = (adopters - roots) / adopters, equal in expectation
  to R for a subcritical Galton-Watson process (Harris 1963).
- n_eff: Kish design effect n / (1 + (n-1) rho_bar) (Kish, Survey Sampling, 1965), exchangeable members.
"""
import random
import statistics as st


def rerun_variance(groups):
    """groups: list (task sets) of lists (reruns) of outcomes in [0,1]. Mean within-set variance."""
    return st.fmean(st.variance(g) for g in groups if len(g) > 1)


def overdispersion(groups):
    """Observed variance of per-set sums over binomial expectation n p (1-p). Equal n required."""
    n = len(groups[0])
    if any(len(g) != n for g in groups):
        raise ValueError("equal reruns per task set required")
    counts = [sum(g) for g in groups]
    p = sum(counts) / (n * len(groups))
    if p in (0, 1):
        return 1.0  # shortcut: degenerate p has zero variance both ways; treat as null value
    return st.variance(counts) / (n * p * (1 - p))


def _slope(xs, ys):
    mx, my = st.fmean(xs), st.fmean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        raise ValueError("no spread in dose")
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx


def dose_slope(doses, ys, B=2000, seed=0, level=0.95):
    """Returns (slope, lo, hi). Pair bootstrap; resamples with constant dose are skipped."""
    rng, n, bs = random.Random(seed), len(doses), []
    for _ in range(B):
        idx = [rng.randrange(n) for _ in range(n)]
        xs = [doses[i] for i in idx]
        if len(set(xs)) > 1:
            bs.append(_slope(xs, [ys[i] for i in idx]))
    bs.sort()
    a = (1 - level) / 2
    return _slope(doses, ys), bs[int(a * len(bs))], bs[int((1 - a) * len(bs)) - 1]


def reproduction_number(notes, planted):
    """notes: dicts with "id","parents". Adopters = planted ids plus all their descendants.
    Returns (R_hat, adopters). R_hat = (adopters - roots)/adopters; 0.0 if nothing adopted."""
    kids = {}
    for n in notes:
        for p in n["parents"]:
            kids.setdefault(p, []).append(n["id"])
    roots = set(planted)
    if not roots:
        return 0.0, 0
    seen, todo = roots.copy(), list(roots)
    while todo:
        for c in kids.get(todo.pop(), []):
            if c not in seen:
                seen.add(c)
                todo.append(c)
    return (len(seen) - len(roots)) / len(seen), len(seen)


def first_generation_offspring(notes, planted):
    """Return (mean, counts by planted note) for direct, observed offspring in L2.

    Every planted id must be present in notes. Planted notes contribute zero when
    no child names them and are never counted as offspring. A child that names a
    planted id alongside another distinct parent has ambiguous attribution.
    """
    counts = dict.fromkeys(planted, 0)
    if not counts:
        raise ValueError("at least one planted note is required")

    parents_by_id = {}
    for note in notes:
        note_id = note["id"]
        if note_id in parents_by_id:
            raise ValueError(f"duplicate note id: {note_id}")
        parents_by_id[note_id] = set(note["parents"])

    missing = counts.keys() - parents_by_id.keys()
    if missing:
        raise ValueError(f"missing planted notes: {sorted(missing)}")

    for note_id, parents in parents_by_id.items():
        if note_id in counts or counts.keys().isdisjoint(parents):
            continue
        if len(parents) > 1:
            raise ValueError(f"ambiguous parentage for note {note_id}")
        counts[next(iter(parents))] += 1
    return st.fmean(counts.values()), counts


def pairwise_miss(misses):
    """misses[m][e] in {0,1}: monitor m missed failure episode e. Returns dict with the joint-miss matrix,
    mean pairwise phi correlation (pairs with a constant monitor are skipped), its spread, and Kish n_eff."""
    m, E = len(misses), len(misses[0])
    joint = [[sum(a and b for a, b in zip(misses[i], misses[j])) / E for j in range(m)] for i in range(m)]
    rhos = []
    for i in range(m):
        for j in range(i + 1, m):
            pi, pj = joint[i][i], joint[j][j]
            d = (pi * (1 - pi) * pj * (1 - pj)) ** 0.5
            if d > 0:
                rhos.append((joint[i][j] - pi * pj) / d)
    rho = st.fmean(rhos) if rhos else 0.0
    den = 1 + (m - 1) * rho
    return {"joint": joint, "rho_bar": rho, "rho_min": min(rhos, default=0.0),
            "rho_max": max(rhos, default=0.0), "n_eff": m / den if den > 0 else float("inf")}


def recovery_time(series, shock, baseline=None, tol=0.0, hold=1):
    """Steps after index `shock` until the series is within tol of baseline for `hold` consecutive points
    (baseline default: mean of series[:shock]). None if it never recovers."""
    b = st.fmean(series[:shock]) if baseline is None else baseline
    for t in range(shock, len(series) - hold + 1):
        if all(abs(v - b) <= tol for v in series[t:t + hold]):
            return t - shock
    return None
