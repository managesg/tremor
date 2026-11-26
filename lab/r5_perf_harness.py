"""Offline R5 harness, Phase 0 / Stage A (prereg/R5-agent-performance-line-plan.md sections 2 to 4).

Pure standard library plus murmuration (readouts, stats) and lab.l3c_harness.task_seed. No model call, no
network. No parameter the plan leaves open (sizes, K, alpha, level, B, perms, edge, seeds, tags) has a default:
a missing one raises TypeError; a bool, NaN, infinite, negative or out-of-range one raises ValueError.
Numbers the plan states are constants: MIN_RERUNS = 10 (P:286-288), FAMILY = H1, H3, H5 (section 2).

Layouts (rows are dicts; every episode is scripted or supplied by a runner, never drawn here except in the
`planted_*` generators):
- per-agent row (H2): {"n", "task", "rerun", "agent", "pass"}; "pass" is the int 0 or 1, one row per agent, so a
  pass count is the number of AGENTS passing, never EP-1's work slots (episode_counts refuses a repeated agent).
- H3 row: {"arm", "task", "conf" (float in [0, 1] or None = unparseable), "pass" (number in [0, 1])}.
- H1 row: {"arm" ("team" or "nominal"), "n", "task", "episode", "pass" (0 or 1)}.
- H5 episode: {"task", "episode", "cands": [{"flags": int >= 0 view flags, "fails": 0 or 1 (oracle)}]}.

Readings the plan leaves open (each is the narrowest one; flagged so the protocol can replace them):
- H2 comparator = the same model with c = 0 and q fitted by pooled binomial MLE; (q, c) are fitted by maximum
  likelihood over the fit sizes pooled. Held-out unit = task set (cluster); per-task mean log score difference.
  The fit sizes [2, 4], target 8, the H1 sizes (4, 8), the H5 grid [2, 4, 8, 16] and the minima 400 / 200 are the
  plan's values, passed explicitly and refused if different. Held-out task sets AND seeds (row["seed"]) must be
  disjoint from the fit's. Fit degenerate (floor or ceiling) is a reason for "uninformative"; a fit with c exactly 0
  is reported as result["c_at_zero"] (the forecast then equals the comparator and the difference is exactly 0).
- H2 interval calibration. The interval is a joint percentile bootstrap: each replicate resamples the fit task sets
  AND the held-out task sets and refits. A held-out-only bootstrap conditions on one fit and is not calibrated
  (9 hits in 100 independent-agent runs at a nominal 5% one-sided tail, 57 of them with c fitted at 0); the joint one
  carries the fit's uncertainty. Measured under independent agents (test_null_calibration_independent_agents, 150
  runs, 12 task sets, 90% interval, nominal 0.05 per tail): 0 intervals had a lower end above 0 (88 of the 150 fits
  had c at 0 and are reported, not counted as hits) and 0 verdicts were "supported". The bound the test enforces is
  the exact binomial tail at 1e-3, so it shows the rate is not above nominal, not that it equals nominal: the
  interval is a percentile bootstrap with no boundary correction (c >= 0) and is conservative here. For "supported"
  that means false positives are bounded by the interval and by the overdispersion and coverage gates; it does not
  mean power is known.
- H2 coverage: the central `level` predictive interval of a task set's rerun SUM has exact coverage above `level`
  (discrete sum; 0.951 to 0.963 at m = 40 and 10 reruns). The inside count is tested two-sided and exactly against
  its own Poisson-binomial distribution built from those exact coverages, not against 0.95. "Rejected" means p <= alpha.
  n = 1 (closed form 1 - q) is not implemented: sizes must be >= 2.
- H2 overdispersion per n measures shared failure WITHIN an episode: the dispersion of each episode's pass count
  around its own task set's rate (ratio of sums, bootstrap over task sets). Independent agents give 1 however the
  pass rate differs between task sets; a shared cause (c > 0) gives more than 1. "Interval contains 1 at every n"
  then reads: no shared failure seen at any size, so the common-cause model cannot be told from independence.
- H1: both intervals must exclude 0 on the same side for "supported", on opposite sides for "killed"; the Holm
  p is max(p4, p8) when the signs agree, else 1. Within-task label permutation, two-sided.
- H3: Holm p is the one-sided upper permutation p. H5: no null is stated, so the Holm p is a permutation of the
  candidates' not-clean bits across episodes within a task (breaks the hidden-state dependence, keeps u_t).
- Decisions come from the intervals (supported: lower end above 0; killed: as the plan states per hypothesis). A
  "supported" is a claim only if it also survives holm_family (family of 3: H1, H3, H5; a hypothesis not run counts
  as p = 1). H2 is the primary and is not in the family; its "supported" needs the interval above 0 AND coverage not
  rejected AND no reason for "uninformative".
- H5 "killed wins" (sentence for the R5 protocol, to be pasted into the plan): "If the 95% interval for S lies
  wholly above 0 but its upper bound is below K, the result is reported as KILLED (the effect is real but smaller
  than the registered size K, so best-of-N is not claimed to buy fewer than N independent draws in any useful
  amount), and the conflict is stated alongside." The plan states supported (lower end above 0) and killed (upper
  bound below K) separately; this sentence settles their overlap.
- H5 "clean episode" for the 400 / 200 minima (P:189-190): a calibration-split candidate that passes the oracle
  (clean) or fails it (failure), counted over all tasks; see h5_primary for why. This counts per calibration
  CANDIDATE and so reinterprets P:189-190 (episodes); the R5 protocol must ratify it.
- run_arms stamps every row with the master `seed`, so held-out seeds differ from the fit's only when the fit and
  the held-out rows come from separate calls with different seeds (h2_primary refuses equal ones).
- The bootstrap refits in the H2 interval search q only within +-0.1 of the point estimate (fit_common_cause near=).
- The tests need the practices/ folder at the repo root (team.run_episode loads the practice cards from it).
- run_arms is the arm-by-size loop over a caller-supplied run_episode (team.run_episode in the tests, with a scripted
  adopter; a model backend goes in through episode_kw). agent_passes, nominal_rows (stats.nominal_group) and
  team_rows turn its records into the layouts the estimators read. gap, gap0, D and the failure rate given a clean
  candidate are h5_description (description only); the draw-position rate check is draw_position_check.
"""
import math
import random
from fractions import Fraction

from murmuration import readouts, stats

from lab.l3c_harness import task_seed

MIN_RERUNS = 10
FAMILY = ("H1", "H3", "H5")
PLAN_FIT_SIZES, PLAN_TARGET, PLAN_H1_SIZES = (2, 4), 8, (4, 8)  # plan section 2: H2 fit sizes and target; H1 sizes
PLAN_GRID = (2, 4, 8, 16)                                       # H5 grid (P:460)
MIN_CLEAN, MIN_FAIL = 400, 200                                  # P:189-190
_EPS = 1e-12  # float tie guard for permutation comparisons; arithmetic, not a scientific parameter


def _int(x, name, low, high=10**12):
    if isinstance(x, bool) or not isinstance(x, int) or not low <= x <= high:
        raise ValueError(f"{name} must be an integer between {low} and {high}")
    return x


def _num(x, name, low, high, open_low=False, open_high=False):
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        raise ValueError(f"{name} must be a finite number")
    if x < low or x > high or (open_low and x == low) or (open_high and x == high):
        raise ValueError(f"{name} must be in {'(' if open_low else '['}{low}, {high}{')' if open_high else ']'}")
    return x


def _prob(x, name):
    return _num(x, name, 0, 1)


def _level(x, name):
    return _num(x, name, 0, 1, True, True)


def _seed(x):
    return _int(x, "seed", -2**63, 2**63)


def _plan(x, want, name):
    """The registered value, passed explicitly: refuse anything else (a list is compared as a set of sizes)."""
    if isinstance(want, tuple):
        ok = isinstance(x, (list, tuple)) and sorted(x) == sorted(want) and len(x) == len(want)
    else:
        ok = not isinstance(x, bool) and x == want
    if not ok:
        raise ValueError(f"{name} must be the registered {want!r}")
    return x


def _tag(x):
    if not isinstance(x, str) or not x:
        raise ValueError("tag must be a nonempty string")
    return x


def _sizes(x, name):
    if isinstance(x, (str, bytes)) or not isinstance(x, (list, tuple)) or not x:
        raise ValueError(f"{name} must be a nonempty list of sizes")
    for n in x:
        _int(n, name, 2, 10**4)
    if len(set(x)) != len(x):
        raise ValueError(f"{name} must be distinct")
    return list(x)


def _rows(rows, keys, name):
    if isinstance(rows, (str, bytes)) or not isinstance(rows, (list, tuple)) or not rows:
        raise ValueError(f"{name} must be a nonempty list of dict rows")
    for r in rows:
        if not isinstance(r, dict) or not set(keys) <= set(r):
            raise ValueError(f"each {name} row needs the keys {sorted(keys)}")
    return rows


def _boot(items, stat, B, seed, level, tag):
    """Percentile interval of stat(items resampled with replacement), same index rule as l3c_harness."""
    _int(B, "B", 1, 10**9), _seed(seed), _level(level, "level")
    if len(items) < 2:
        raise ValueError("a cluster bootstrap needs at least two clusters")
    rng = random.Random(task_seed(tag, seed, 0))
    vals = sorted(stat([items[rng.randrange(len(items))] for _ in items]) for _ in range(B))
    a = (1 - level) / 2
    return vals[int(a * len(vals))], vals[min(len(vals) - 1, math.ceil((1 - a) * len(vals)) - 1)]


def _mean(xs):
    return math.fsum(xs) / len(xs)


def _side(interval):
    lo, hi = interval
    return 1 if lo > 0 else -1 if hi < 0 else 0


# ---------------------------------------------------------------------------------------------- H2 ----

def episode_counts(rows):
    """{(n, task, rerun): X}: X = number of agents whose own work passes (one 0/1 row per agent)."""
    seen = {}
    for r in _rows(rows, ("n", "task", "rerun", "agent", "pass"), "per-agent"):
        n, agent = _int(r["n"], "n", 1, 10**4), _int(r["agent"], "agent", 0, 10**4)
        if type(r["pass"]) is not int or r["pass"] not in (0, 1):
            raise ValueError("pass must be the int 0 or 1")
        d = seen.setdefault((n, r["task"], r["rerun"]), {})
        if agent in d:
            raise ValueError("repeated agent in an episode: one 0/1 row per agent, not per work slot")
        d[agent] = r["pass"]
    for key, d in seen.items():
        if sorted(d) != list(range(key[0])):
            raise ValueError("an episode needs exactly one row for each of its n agents")
    return {key: sum(d.values()) for key, d in seen.items()}


def pmf(n, q, c):
    """Pass-count pmf over 0..n: probability c all fail together, else each fails independently with q.
    pmf[0] = c + (1 - c) q^n is nulls.correlated_monitors(n, q, c)["all_miss"]."""
    _int(n, "n", 2, 10**4), _prob(q, "q"), _prob(c, "c")
    out = [(1 - c) * math.comb(n, k) * (1 - q) ** k * q ** (n - k) for k in range(n + 1)]
    out[0] += c
    return out


def _xlogy(cnt, v):
    return 0.0 if cnt == 0 else -math.inf if v <= 0 else cnt * math.log(v)


def _loglik(q, c, counts):
    ll = 0.0
    for n, cnt in counts.items():
        ll += _xlogy(cnt[0], c + (1 - c) * q ** n) + _xlogy(sum(cnt[1:]), 1 - c)
        for k in range(1, n + 1):
            ll += _xlogy(k * cnt[k], 1 - q) + _xlogy((n - k) * cnt[k], q) + cnt[k] * math.log(math.comb(n, k))
    return ll


def _best_c(q, counts):
    """Maximiser over c in [0, 1] of the (concave) log likelihood at fixed q, by bisection on its derivative."""
    npos = sum(sum(cnt[1:]) for cnt in counts.values())
    if npos == 0:
        return 1.0

    def slope(c):
        s = -npos / (1 - c)
        for n, cnt in counts.items():
            if cnt[0]:
                d = c + (1 - c) * q ** n
                if d <= 0:
                    return math.inf
                s += cnt[0] * (1 - q ** n) / d
        return s

    if slope(0.0) <= 0:
        return 0.0
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if slope(mid) > 0 else (lo, mid)
    return (lo + hi) / 2


def _check_counts(counts):
    if not isinstance(counts, dict) or not counts:
        raise ValueError("counts must map each size n to a list of n + 1 episode counts")
    for n, cnt in counts.items():
        _int(n, "n", 2, 10**4)
        if not isinstance(cnt, (list, tuple)) or len(cnt) != n + 1:
            raise ValueError("counts[n] needs n + 1 entries (pass counts 0..n)")
        for x in cnt:
            _int(x, "count", 0)
    if sum(sum(c) for c in counts.values()) == 0:
        raise ValueError("no episodes")


def fit_common_cause(counts, near=None):
    """Maximum likelihood (q, c) pooled over sizes. counts = {n: [episodes with X = 0, ..., X = n]}.
    Profile over q (grid of 201, then golden section), exact in c. degenerate = floor or ceiling in the data.
    near: a q to search around (+/- 0.1, for bootstrap refits); None searches [0, 1]."""
    _check_counts(counts)

    def prof(q):
        c = _best_c(q, counts)
        return _loglik(q, c, counts), c

    if near is None:
        grid = [i / 200 for i in range(201)]
    else:
        lo0, hi0 = max(0.0, near - 0.1), min(1.0, near + 0.1)
        grid = [lo0 + (hi0 - lo0) * i / 20 for i in range(21)]
    vals = [prof(q)[0] for q in grid]
    i = vals.index(max(vals))
    best_q, best = grid[i], vals[i]
    lo, hi = grid[max(0, i - 1)], grid[min(len(grid) - 1, i + 1)]
    g = (math.sqrt(5) - 1) / 2
    x1, x2 = hi - g * (hi - lo), lo + g * (hi - lo)
    f1, f2 = prof(x1)[0], prof(x2)[0]
    for _ in range(80 if near is None else 30):
        if f1 < f2:
            lo, x1, f1 = x1, x2, f2
            x2 = lo + g * (hi - lo)
            f2 = prof(x2)[0]
        else:
            hi, x2, f2 = x2, x1, f1
            x1 = hi - g * (hi - lo)
            f1 = prof(x1)[0]
    for x, f in ((x1, f1), (x2, f2)):
        if f > best:
            best_q, best = x, f
    ll, c = prof(best_q)
    npos = sum(sum(cnt[1:]) for cnt in counts.values())
    return {"q": best_q, "c": c, "loglik": ll, "degenerate": npos == 0 or best_q in (0.0, 1.0)}


def fit_independent(counts):
    """Comparator: c = 0, q = 1 - pooled pass rate (binomial maximum likelihood)."""
    _check_counts(counts)
    agents = sum(n * sum(cnt) for n, cnt in counts.items())
    passes = sum(k * cnt[k] for cnt in counts.values() for k in range(len(cnt)))
    return {"q": 1 - passes / agents, "c": 0.0}


def binom_two_sided(k, m, p):
    """Exact two-sided binomial test: sum of the probabilities of outcomes no more likely than k (Fraction)."""
    _int(m, "m", 1, 10**5), _int(k, "k", 0, m)
    if not isinstance(p, Fraction):
        _num(p, "p", 0, 1, True, True)
        p = Fraction(str(p))
    if not 0 < p < 1:
        raise ValueError("p must be in (0, 1)")
    pm = [math.comb(m, i) * p ** i * (1 - p) ** (m - i) for i in range(m + 1)]
    return sum(x for x in pm if x <= pm[k])


def _sum_dist(pm, reps):
    dist = [1.0]
    for _ in range(reps):
        nxt = [0.0] * (len(dist) + len(pm) - 1)
        for i, x in enumerate(dist):
            for j, y in enumerate(pm):
                nxt[i + j] += x * y
        dist = nxt
    return dist


def _interval_of(dist, level):
    tail, acc, a, b = (1 - level) / 2, 0.0, None, None
    for s, x in enumerate(dist):
        acc += x
        if a is None and acc >= tail - _EPS:
            a = s
        if b is None and acc >= 1 - tail - _EPS:
            b = s
    return a, b


def predictive_sum_interval(pm, reps, level):
    """Central `level` interval (a, b) of the sum of `reps` iid draws from pmf `pm`:
    a = least s with cdf(s) >= (1 - level)/2, b = least s with cdf(s) >= 1 - (1 - level)/2."""
    _int(reps, "reps", 1, 10**4), _level(level, "level")
    return _interval_of(_sum_dist(pm, reps), level)


def coverage_detail(held, pm, level):
    """held = {task: [pass count per rerun]}. Returns {"inside": number of task sets whose rerun sum lies inside the
    central `level` predictive interval, "probs": each task set's EXACT coverage of that interval (it exceeds
    `level` because the sum is discrete)}."""
    inside, probs = 0, []
    for xs in held.values():
        dist = _sum_dist(pm, len(xs))
        a, b = _interval_of(dist, level)
        inside += a <= sum(xs) <= b
        probs.append(sum(dist[a:b + 1]))
    return {"inside": inside, "probs": probs}


def coverage_count(held, pm, level):
    return coverage_detail(held, pm, level)["inside"]


def poisson_binomial_pmf(probs):
    pm = [1.0]
    for p in probs:
        _prob(p, "coverage probability")
        nxt = [0.0] * (len(pm) + 1)
        for k, x in enumerate(pm):
            nxt[k] += x * (1 - p)
            nxt[k + 1] += x * p
        pm = nxt
    return pm


def coverage_p(inside, probs):
    """Two-sided exact test of the inside count against its exact distribution when every task set is covered with
    its own exact probability (Poisson binomial; equal probabilities give the binomial). p = sum of the
    probabilities of outcomes no more likely than the observed one (float tie guard 1e-9, relative)."""
    pm = poisson_binomial_pmf(probs)
    _int(inside, "inside", 0, len(probs))
    return sum(x for x in pm if x <= pm[inside] * (1 + 1e-9))


def floor_ceiling_reading(rows, sizes, edge):
    """B0 probe: per size, pooled per-agent pass rate; floor if <= edge, ceiling if >= 1 - edge, else ok."""
    sizes = _sizes(sizes, "sizes")
    _num(edge, "edge", 0, 0.5, open_high=True)
    out = {}
    for n in sizes:
        ys = [r["pass"] for r in _rows(rows, ("n", "pass"), "per-agent") if r["n"] == n]
        if not ys:
            raise ValueError(f"no rows at n = {n}")
        rate = _mean(ys)
        out[n] = {"rate": rate, "reading": "floor" if rate <= edge else "ceiling" if rate >= 1 - edge else "ok"}
    return out


def _within_items(rows, n):
    """Per task set at size n: (SS, den). SS = sum over episodes of (X - Xbar)^2 (X = the episode's pass count);
    den = (R - 1) n p(1 - p) nR / (nR - 1), the expectation of SS for independent agents with the task's own rate p
    (p estimated from the same episodes; E[p_hat (1 - p_hat)] = p (1 - p)(1 - 1/(nR)))."""
    by = {}
    for (m, task, _), x in episode_counts(rows).items():
        if m == n:
            by.setdefault(task, []).append(x)
    if not by or any(len(xs) < 2 for xs in by.values()):
        raise ValueError(f"every task set needs at least 2 episodes at n = {n}")
    items = []
    for xs in by.values():
        R, mean = len(xs), _mean(xs)
        p = mean / n
        items.append((math.fsum((x - mean) ** 2 for x in xs),
                      (R - 1) * n * p * (1 - p) * n * R / (n * R - 1)))
    return items


def _within_dispersion(items):
    den = math.fsum(d for _, d in items)
    return math.fsum(s for s, _ in items) / den if den > 0 else 1.0


def overdispersion_interval(rows, n, B, seed, level):
    """Shared failure WITHIN an episode: dispersion of each episode's pass count around that task set's own rate,
    ratio of sums over task sets (1 for independent agents however the rate differs between task sets; above 1 when
    agents fail together). Returns (point, (lo, hi)); percentile bootstrap over task sets."""
    items = _within_items(rows, n)
    return _within_dispersion(items), _boot(items, _within_dispersion, B, seed, level, f"od-{n}")


def h2_decision(interval, coverage_p, alpha, uninformative):
    _level(alpha, "alpha")
    if uninformative:
        return "uninformative"
    lo, hi = interval
    if lo > 0 and not coverage_p <= alpha:
        return "supported"
    return "killed" if hi < 0 else "inconclusive"


def _ld(a, b):
    """log(a / b) with zero masses mapped to +-1e9 (0 / 0 = 0), so a bootstrap mean stays finite and sortable."""
    if a <= 0 and b <= 0:
        return 0.0
    return -1e9 if a <= 0 else 1e9 if b <= 0 else math.log(a / b)


def _joint_boot(fit_tasks, held_tasks, sizes, target, point_q, B, seed, level):
    """Interval for the held-out log score difference that carries the FIT's uncertainty too: each replicate resamples
    the fit task sets and the held-out task sets, refits (q, c) and the c = 0 comparator, and rescores."""
    rng = random.Random(task_seed("h2-joint", seed, 0))
    fts, hts, vals = list(fit_tasks.values()), list(held_tasks.values()), []
    for _ in range(B):
        counts = {n: [0] * (n + 1) for n in sizes}
        for t in (fts[rng.randrange(len(fts))] for _ in fts):
            for n in sizes:
                for k, x in enumerate(t[n]):
                    counts[n][k] += x
        f, ind = fit_common_cause(counts, near=point_q), fit_independent(counts)
        pm, pm0 = pmf(target, f["q"], f["c"]), pmf(target, ind["q"], 0.0)
        ds = []
        for hist, reps in (hts[rng.randrange(len(hts))] for _ in hts):
            ds.append(math.fsum(c * _ld(pm[x], pm0[x]) for x, c in enumerate(hist)) / reps)
        vals.append(_mean(ds))
    vals.sort()
    a = (1 - level) / 2
    return vals[int(a * len(vals))], vals[min(len(vals) - 1, math.ceil((1 - a) * len(vals)) - 1)]


def h2_primary(fit_rows, held_rows, *, fit_sizes, target_n, level, alpha, B, seed, edge):
    """H2: forecast the pass-count distribution at target_n from the fit sizes; held-out task sets AND seeds.
    fit_sizes and target_n are the registered values ([2, 4] and 8), passed explicitly."""
    sizes = _plan(_sizes(fit_sizes, "fit_sizes"), PLAN_FIT_SIZES, "fit_sizes")
    _plan(target_n, PLAN_TARGET, "target_n")
    _level(level, "level"), _level(alpha, "alpha")
    keys = ("n", "task", "rerun", "agent", "pass", "seed")
    _rows(fit_rows, keys, "per-agent"), _rows(held_rows, keys, "per-agent")
    if {r["seed"] for r in fit_rows} & {r["seed"] for r in held_rows}:
        raise ValueError("held-out seeds must not appear in the fit rows")
    fit_ep, held_ep = episode_counts(fit_rows), episode_counts(held_rows)
    if {k[0] for k in fit_ep} != set(sizes) or {k[0] for k in held_ep} != {target_n}:
        raise ValueError("fit rows must cover exactly fit_sizes and held rows exactly target_n")
    if {k[1] for k in fit_ep} & {k[1] for k in held_ep}:
        raise ValueError("held-out task sets must not appear in the fit rows")
    fit_tasks, held, held_tasks = {}, {}, {}
    for (n, t, _), x in fit_ep.items():
        fit_tasks.setdefault(t, {m: [0] * (m + 1) for m in sizes})[n][x] += 1
    for (_, t, _), x in sorted(held_ep.items(), key=lambda kv: (str(kv[0][1]), str(kv[0][2]))):
        held.setdefault(t, []).append(x)
    for t, xs in held.items():
        hist = [0] * (target_n + 1)
        for x in xs:
            hist[x] += 1
        held_tasks[t] = (hist, len(xs))
    counts = {n: [sum(t[n][k] for t in fit_tasks.values()) for k in range(n + 1)] for n in sizes}
    fit, ind = fit_common_cause(counts), fit_independent(counts)
    pm, pm0 = pmf(target_n, fit["q"], fit["c"]), pmf(target_n, ind["q"], 0.0)
    reasons = []
    if fit["degenerate"]:
        reasons.append("fit degenerate (floor or ceiling in the fit data)")
    readings = floor_ceiling_reading(list(fit_rows) + list(held_rows), sizes + [target_n], edge)
    reasons += [f"{v['reading']} at n = {n}" for n, v in readings.items() if v["reading"] != "ok"]
    reruns = {}
    for (n, task, _) in list(fit_ep) + list(held_ep):
        reruns[(n, task)] = reruns.get((n, task), 0) + 1
    if min(reruns.values()) < MIN_RERUNS:
        reasons.append(f"under {MIN_RERUNS} reruns")
    ods = {n: overdispersion_interval(list(fit_rows) + list(held_rows), n, B, seed, level)[1]
           for n in sizes + [target_n]}
    if all(lo <= 1 <= hi for lo, hi in ods.values()):
        reasons.append("overdispersion interval contains 1 at every n")
    diff = interval = None
    if any(pm[x] <= 0 or pm0[x] <= 0 for xs in held.values() for x in xs):
        reasons.append("zero forecast mass at an observed count")
    else:
        per_task = [_mean([math.log(pm[x]) - math.log(pm0[x]) for x in xs]) for xs in held.values()]
        diff = _mean(per_task)
        interval = _joint_boot(fit_tasks, held_tasks, sizes, target_n, fit["q"], B, seed, level)
    cov = coverage_detail(held, pm, level)
    cov_p = coverage_p(cov["inside"], cov["probs"])
    decision = h2_decision(interval or (0.0, 0.0), cov_p, alpha, reasons)
    return {"fit": fit, "c_at_zero": fit["c"] == 0.0, "comparator": ind, "diff": diff, "interval": interval,
            "overdispersion": ods,
            "coverage": {"inside": cov["inside"], "m": len(held), "p": cov_p,
                         "exact": (min(cov["probs"]), max(cov["probs"]))},
            "floor_ceiling": readings, "uninformative": reasons, "decision": decision}


# ---------------------------------------------------------------------------------------------- H3 ----

def brier(conf, outcome):
    """Mean squared gap between stated confidence and a 0/1 outcome."""
    if len(conf) != len(outcome) or not conf:
        raise ValueError("conf and outcome must be equal-length and nonempty")
    for c, y in zip(conf, outcome):
        _prob(c, "conf")
        if type(y) is not int or y not in (0, 1):
            raise ValueError("outcome must be the int 0 or 1")
    return _mean([(c - y) ** 2 for c, y in zip(conf, outcome)])


def _h3_tasks(rows, team_arm, solo_arm):
    by = {}
    for r in rows:
        if r["arm"] in (team_arm, solo_arm):
            _prob(r["pass"], "pass")
            if r["conf"] is not None:
                _prob(r["conf"], "conf")
                by.setdefault(r["task"], {team_arm: [], solo_arm: []})[r["arm"]].append((r["conf"], r["pass"]))
    for t, d in by.items():
        if not d[team_arm] or not d[solo_arm]:
            raise ValueError(f"task {t!r} needs both arms")
    return [by[t] for t in sorted(by, key=str)]


def _delta_g(tasks, team_arm, solo_arm):
    g = lambda pairs: _mean([c - p for c, p in pairs])
    return _mean([g(t[team_arm]) - g(t[solo_arm]) for t in tasks])


def h3_primary(rows, *, team_arm, solo_arm, B, perms, seed, level, edge, max_unparseable):
    """H3: dG = G_team - G_solo, G = mean stated confidence - pass rate; pair permutation across the two arms
    within each task set. Returns the statistic, bootstrap interval, one- and two-sided p and the decision."""
    _tag(team_arm), _tag(solo_arm), _int(perms, "perms", 1, 10**6), _prob(max_unparseable, "max_unparseable")
    _num(edge, "edge", 0, 0.5, open_high=True)
    rows = _rows(rows, ("arm", "task", "conf", "pass"), "H3")
    used = [r for r in rows if r["arm"] in (team_arm, solo_arm)]
    tasks = _h3_tasks(rows, team_arm, solo_arm)
    obs = _delta_g(tasks, team_arm, solo_arm)
    interval = _boot([_delta_g([t], team_arm, solo_arm) for t in tasks], _mean, B, seed, level, "h3-boot")
    null = []
    for b in range(perms):
        rng = random.Random(task_seed("h3-perm", seed, b))
        shuffled = []
        for t in tasks:
            items = t[team_arm] + t[solo_arm]
            rng.shuffle(items)
            k = len(t[team_arm])
            shuffled.append({team_arm: items[:k], solo_arm: items[k:]})
        null.append(_delta_g(shuffled, team_arm, solo_arm))
    p_up = (1 + sum(x >= obs - _EPS for x in null)) / (1 + perms)
    p_low = (1 + sum(x <= obs + _EPS for x in null)) / (1 + perms)
    reasons = []
    if sum(r["conf"] is None for r in used) / len(used) > max_unparseable:
        reasons.append("unparseable confidence share above the cap")
    if len({c for t in tasks for arm in t.values() for c, _ in arm}) < 2:
        reasons.append("constant confidences")
    for arm in (team_arm, solo_arm):
        rate = _mean([r["pass"] for r in used if r["arm"] == arm])
        if rate <= edge or rate >= 1 - edge:
            reasons.append(f"floor or ceiling in arm {arm}")
    side = _side(interval)
    decision = "uninformative" if reasons else "supported" if side > 0 else "killed" if side < 0 else "inconclusive"
    ys = [p for t in tasks for arm in t.values() for _, p in arm]
    return {"delta_g": obs, "interval": interval, "p_up": p_up, "p_low": p_low, "p_two": min(1.0, 2 * min(p_up, p_low)),
            "null": null, "uninformative": reasons, "decision": decision,
            "brier": brier([c for t in tasks for arm in t.values() for c, _ in arm], [int(y) for y in ys])
            if all(y in (0, 1) for y in ys) else None}


def behaviour_check(rows, *, with_arm, without_arm, B, seed, level):
    """Pass rate with against without the confidence field: per-task difference, bootstrap interval; if the
    interval excludes 0, H3 holds only for teams asked for confidence."""
    by = {}
    for r in _rows(rows, ("arm", "task", "pass"), "behaviour"):
        if r["arm"] in (with_arm, without_arm):
            by.setdefault(r["task"], {with_arm: [], without_arm: []})[r["arm"]].append(_prob(r["pass"], "pass"))
    if not by or any(not d[with_arm] or not d[without_arm] for d in by.values()):
        raise ValueError("every task needs both arms")
    diffs = [_mean(d[with_arm]) - _mean(d[without_arm]) for d in by.values()]
    interval = _boot(diffs, _mean, B, seed, level, "behaviour")
    return {"diff": _mean(diffs), "interval": interval, "excludes_zero": _side(interval) != 0}


# ---------------------------------------------------------------------------------------------- H1 ----

def h1_primary(rows, *, sizes, B, perms, seed, level, edge, tokens_matched):
    """H1: does the sign of EG(sizes[0]) forecast that of EG(sizes[1])? EG(n) = Y_team(n) - Y_nominal(n) over
    task sets (stats.emergence_gain); null: team and nominal labels permuted within task set."""
    sizes = _plan(_sizes(sizes, "sizes"), PLAN_H1_SIZES, "sizes")
    if sizes[0] >= sizes[1]:
        raise ValueError("sizes must be increasing: (4, 8)")
    _int(perms, "perms", 1, 10**6), _num(edge, "edge", 0, 0.5, open_high=True)
    if not isinstance(tokens_matched, bool):
        raise ValueError("tokens_matched must be True or False")
    rows = _rows(rows, ("arm", "n", "task", "episode", "pass"), "H1")
    out, reasons = {}, [] if tokens_matched else ["token match failed"]
    for n in sizes:
        by = {}
        for r in rows:
            if r["n"] == n:
                if r["arm"] not in ("team", "nominal") or type(r["pass"]) is not int or r["pass"] not in (0, 1):
                    raise ValueError("arm must be team or nominal and pass the int 0 or 1")
                by.setdefault(r["task"], {"team": [], "nominal": []})[r["arm"]].append(r["pass"])
        if not by or any(not d["team"] or not d["nominal"] for d in by.values()):
            raise ValueError(f"every task needs both arms at n = {n}")
        tasks = [by[t] for t in sorted(by, key=str)]
        gain = lambda ts: stats.emergence_gain([_mean(t["team"]) for t in ts], [_mean(t["nominal"]) for t in ts])
        eg = gain(tasks)
        interval = _boot([gain([t]) for t in tasks], _mean, B, seed, level, f"h1-boot-{n}")
        null = []
        for b in range(perms):
            rng = random.Random(task_seed(f"h1-perm-{n}", seed, b))
            shuffled = []
            for t in tasks:
                items = t["team"] + t["nominal"]
                rng.shuffle(items)
                shuffled.append({"team": items[:len(t["team"])], "nominal": items[len(t["team"]):]})
            null.append(gain(shuffled))
        p = (1 + sum(abs(x) >= abs(eg) - _EPS for x in null)) / (1 + perms)
        out[n] = {"eg": eg, "interval": interval, "p": p, "null": null}
        for arm in ("team", "nominal"):
            rate = _mean([y for t in tasks for y in t[arm]])
            if rate <= edge or rate >= 1 - edge:
                reasons.append(f"floor or ceiling in {arm} at n = {n}")
    s0, s1 = (_side(out[n]["interval"]) for n in sizes)
    decision = ("uninformative" if reasons else "supported" if s0 == s1 != 0 else "killed" if s0 * s1 == -1
                else "inconclusive")
    same = (out[sizes[0]]["eg"] > 0) == (out[sizes[1]]["eg"] > 0) and 0 not in (out[sizes[0]]["eg"], out[sizes[1]]["eg"])
    return {"sizes": out, "uninformative": reasons, "decision": decision,
            "p_holm": max(out[n]["p"] for n in sizes) if same else 1.0}


# ---------------------------------------------------------------------------------------------- H5 ----

def select_clean(cands, n):
    """Selection rule: fewest view flags among the first n, first wins ties; when no candidate is clean,
    candidate 0 is returned and reported flagged. Returns (index, clean)."""
    _int(n, "n", 1, 10**6)
    if not isinstance(cands, (list, tuple)) or len(cands) < n:
        raise ValueError("need at least n candidates")
    flags = [_int(c["flags"], "flags", 0, 10**6) for c in cands[:n]]
    i = flags.index(min(flags))
    return (i, True) if flags[i] == 0 else (0, False)


def _first_clean(cands, limit):
    """Index of the first clean candidate among the first `limit`; limit if none (no clean among them)."""
    for i, c in enumerate(cands[:limit]):
        if _int(c["flags"], "flags", 0, 10**6) == 0:
            return i
    return limit


def _check_h5(calibration, scored, grid):
    ids = lambda eps: {(e["task"], e["episode"]) for e in eps}
    cal = _rows(calibration, ("task", "episode", "cands"), "calibration")
    sc = _rows(scored, ("task", "episode", "cands"), "scored")
    if ids(cal) & ids(sc):
        raise ValueError("calibration episodes must be kept apart from the scored ones")
    top = max(grid)
    by_cal, by_sc = {}, {}
    for e in cal:
        by_cal.setdefault(e["task"], []).append(e)
    for e in cal + sc:
        for c in e["cands"]:
            _int(c["flags"], "flags", 0, 10**6), _int(c["fails"], "fails", 0, 1)
    for e in sc:
        if len(e["cands"]) < top:
            raise ValueError("every scored episode needs at least max(grid) candidates")
        by_sc.setdefault(e["task"], []).append(e)
    if set(by_sc) - set(by_cal):
        raise ValueError("every scored task needs calibration episodes")
    return by_cal, by_sc


def _h5_task(cal_eps, bits_first, grid):
    """(u_hat, per-N observed, per-N term) for one task; bits_first = first-clean positions of scored episodes."""
    flat = [c["flags"] > 0 for e in cal_eps for c in e["cands"]]
    if not flat:
        raise ValueError("calibration episodes hold no candidates")
    u = sum(flat) / len(flat)
    obs = [_mean([int(p >= n) for p in bits_first]) for n in grid]
    return u, obs, [o - u ** n for o, n in zip(obs, grid)]


def _h5(calibration, scored, *, grid, B, perms, seed, level, K, negligible, reasons0=()):
    """H5: S = mean over tasks and N in grid of [observed P(no clean among N) - u_t^N]; u_t from the calibration
    split. Interval: cluster bootstrap over tasks. p: permutation of the candidates' not-clean bits across
    episodes within a task (independent-draws null). Supported lo > 0; killed hi < K."""
    if isinstance(grid, (str, bytes)) or not isinstance(grid, (list, tuple)) or not grid or len(set(grid)) != len(grid):
        raise ValueError("grid must be a nonempty list of distinct N")
    grid = [_int(n, "grid", 1, 10**6) for n in grid]
    _int(perms, "perms", 1, 10**6), _num(K, "K", 0, 1, open_low=True), _num(negligible, "negligible", 0, 1, True, True)
    by_cal, by_sc = _check_h5(calibration, scored, grid)
    top, tasks = max(grid), sorted(by_sc, key=str)
    firsts = {t: [_first_clean(e["cands"], top) for e in by_sc[t]] for t in tasks}
    per = {t: _h5_task(by_cal[t], firsts[t], grid) for t in tasks}
    terms = [_mean(per[t][2]) for t in tasks]
    s = _mean(terms)
    interval = _boot(terms, _mean, B, seed, level, "h5-boot")
    null = []
    for b in range(perms):
        rng = random.Random(task_seed("h5-perm", seed, b))
        total = 0.0
        for t in tasks:
            bits = [int(c["flags"] > 0) for e in by_sc[t] for c in e["cands"][:top]]
            rng.shuffle(bits)
            pos = []
            for j in range(len(by_sc[t])):
                chunk = bits[j * top:(j + 1) * top]
                pos.append(chunk.index(0) if 0 in chunk else top)
            total += _mean(_h5_task(by_cal[t], pos, grid)[2])
        null.append(total / len(tasks))
    p_up = (1 + sum(x >= s - _EPS for x in null)) / (1 + perms)
    reasons = list(reasons0)
    us = [per[t][0] for t in tasks]
    if all(u in (0, 1) for u in us):
        reasons.append("every u_t is 0 or 1")
    if all(max(u ** n for u in us) < negligible for n in grid):
        reasons.append("u_t^N negligible at every grid N")
    lo, hi = interval
    conflict = lo > 0 and hi < K
    decision = "uninformative" if reasons else "killed" if hi < K else "supported" if lo > 0 else "inconclusive"
    return {"S": s, "interval": interval, "p_up": p_up, "u_hat": dict(zip(tasks, us)), "null": null,
            "per_N": {n: _mean([per[t][1][i] - per[t][0] ** n for t in tasks]) for i, n in enumerate(grid)},
            "uninformative": reasons, "decision": decision, "conflict": conflict}


def h5_primary(calibration, scored, *, grid, B, perms, seed, level, K, negligible, min_clean, min_fail):
    """H5 at the registered settings: grid [2, 4, 8, 16] and the minima 400 / 200 (P:189-190), passed explicitly.

    A "clean episode" is a calibration-split candidate that passes the oracle and a "failure episode" one that fails
    it, counted over all tasks. Why: P:189-190 reads one rate at a 5% false-positive rate from at least 400 clean
    episodes (the threshold, here the share of passing outputs that look clean) and at least 200 failure episodes (the
    catch rate, here 1 - a_t, read on failing outputs); u_t = f_t (1 - a_t) is read on exactly that split, so the
    counts are taken there and not on the scored episodes."""
    if isinstance(grid, (str, bytes)) or not isinstance(grid, (list, tuple)):
        raise ValueError("grid must be a list")
    _plan(list(grid), PLAN_GRID, "grid"), _plan(min_clean, MIN_CLEAN, "min_clean"), _plan(min_fail, MIN_FAIL, "min_fail")
    cands = [c for e in _rows(calibration, ("task", "episode", "cands"), "calibration") for c in e["cands"]]
    clean, fail = sum(1 for c in cands if c["fails"] == 0), sum(1 for c in cands if c["fails"] == 1)
    reasons = [] if clean >= min_clean and fail >= min_fail else [
        f"{min_clean} clean and {min_fail} failure calibration episodes not reached ({clean}, {fail})"]
    res = _h5(calibration, scored, grid=grid, B=B, perms=perms, seed=seed, level=level, K=K, negligible=negligible,
              reasons0=reasons)
    res["counts"] = {"clean": clean, "failure": fail}
    res["description_only"] = h5_description(calibration, scored, grid)
    return res


def h5_description(calibration, scored, grid):
    """Description only, no claim. Per N, mean over tasks of: gap = P(selected is reported clean and fails the oracle),
    gap0 = [1 - u^N] f a / ((1 - f) + f a) (f, a, u from the calibration split; 0 when the denominator is 0),
    D = gap - gap0; and over episodes with a clean candidate among the first N, the failure rate of the selected one."""
    grid = [_int(n, "grid", 1, 10**6) for n in grid]
    by_cal, by_sc = _check_h5(calibration, scored, grid)
    gaps = {n: [] for n in grid}
    gap0s = {n: [] for n in grid}
    sel = {n: [] for n in grid}
    for t in sorted(by_sc, key=str):
        cal = [c for e in by_cal[t] for c in e["cands"]]
        f = sum(c["fails"] for c in cal) / len(cal)
        failing = [c for c in cal if c["fails"] == 1]
        a = sum(c["flags"] == 0 for c in failing) / len(failing) if failing else 0.0
        u = sum(c["flags"] > 0 for c in cal) / len(cal)
        den = (1 - f) + f * a
        for n in grid:
            hits, picks = [], []
            for e in by_sc[t]:
                i, clean = select_clean(e["cands"], n)
                hits.append(int(clean and e["cands"][i]["fails"] == 1))
                if clean:
                    picks.append(e["cands"][i]["fails"])
            gaps[n].append(_mean(hits))
            gap0s[n].append((1 - u ** n) * f * a / den if den > 0 else 0.0)
            sel[n] += picks
    return {n: {"gap": _mean(gaps[n]), "gap0": _mean(gap0s[n]), "D": _mean(gaps[n]) - _mean(gap0s[n]),
                "fail_given_clean": _mean(sel[n]) if sel[n] else None} for n in grid}


def draw_position_check(scored, *, top, perms, seed):
    """Order effects (plan section 2, H5): rate of not-clean candidates by draw position over the first `top`
    candidates of every scored episode. Statistic = largest absolute gap between a position's rate and the pooled
    rate; null: candidate order permuted within each episode (exchangeable draws). p = (1 + #{perm >= obs}) / (1 + perms)."""
    _int(top, "top", 2, 10**4), _int(perms, "perms", 1, 10**6), _seed(seed)
    eps = _rows(scored, ("task", "episode", "cands"), "scored")
    rows = []
    for e in eps:
        if len(e["cands"]) < top:
            raise ValueError("every scored episode needs at least `top` candidates")
        rows.append([int(_int(c["flags"], "flags", 0, 10**6) > 0) for c in e["cands"][:top]])

    def stat(rs):
        rates = [_mean([r[j] for r in rs]) for j in range(top)]
        pooled = _mean(rates)
        return rates, max(abs(x - pooled) for x in rates)

    rates, obs = stat(rows)
    count = 0
    for b in range(perms):
        rng = random.Random(task_seed("h5-pos", seed, b))
        shuffled = []
        for r in rows:
            r = list(r)
            rng.shuffle(r)
            shuffled.append(r)
        count += stat(shuffled)[1] >= obs - _EPS
    return {"rates": rates, "stat": obs, "p": (1 + count) / (1 + perms)}


# ---------------------------------------------------------------------------------------------- Holm ----

def holm_family(p_by_h, alpha):
    """Holm step-down over the registered family of 3 (H1, H3, H5). A hypothesis not run counts as p = 1, so
    the family size stays 3. Returns {hypothesis: reject} for the ones given."""
    _level(alpha, "alpha")
    if not isinstance(p_by_h, dict) or not p_by_h or not set(p_by_h) <= set(FAMILY):
        raise ValueError("p_by_h must be a nonempty dict keyed by H1, H3, H5")
    flags = stats.holm([p_by_h.get(h, 1.0) for h in FAMILY], alpha)
    return {h: flags[i] for i, h in enumerate(FAMILY) if h in p_by_h}


# ------------------------------------------------------------------------------- arm-by-size loop ----

def agent_passes(record, taskset):
    """One 0/1 per agent a0..a{n-1} from a team.run_episode record: the agent has an accepted work event on a task of
    the set whose answer is the JSON integer the oracle expects (EP-1 rule 2: a bool is not an integer). This is a
    per-AGENT pass, not Y (EP-1's work slots)."""
    if not isinstance(record, dict) or record.get("valid") is not True or record.get("status") != "ok":
        raise ValueError("void or invalid episode record")
    n = _int(taskset.get("n_agents"), "n_agents", 1, 10**4)
    if record.get("n_agents") != n:
        raise ValueError("record and taskset disagree on n_agents")
    expect = {t["id"]: t["expect"] for t in taskset["tasks"]}
    passed = {e.get("agent") for e in record["log"] if isinstance(e, dict) and e.get("action") == "work"
              and not e.get("rejected") and e.get("task") in expect and type(e.get("answer")) is int
              and e["answer"] == expect[e["task"]]}
    return [int(f"a{i}" in passed) for i in range(n)]


def run_arms(run_episode, taskset_for, *, arms, sizes, task_ids, reruns, practice, seed, tag, episode_kw):
    """Arm-by-size loop over a caller-supplied episode runner (team.run_episode, called as
    run_episode(taskset, arm, practice, n_agents=n, seed=episode_seed, **episode_kw(arm, n, task, rerun, episode_seed))).
    The runner is never replaced here: tests pass the real run_episode with a scripted adopter; a model backend goes in
    through episode_kw (run_episode itself refuses one, team.py:226-227). taskset_for(n, task) builds the task set.
    Returns {arm: per-agent rows in the H2 layout (plus "arm")}; each rerun r of a task has its own seed, derived by
    sha256 of tag:arm:n:seed:task*10**6+r."""
    if not callable(run_episode) or not callable(taskset_for) or not callable(episode_kw):
        raise ValueError("run_episode, taskset_for and episode_kw must be callables")
    if isinstance(arms, (str, bytes)) or not isinstance(arms, (list, tuple)) or not arms:
        raise ValueError("arms must be a nonempty list")
    sizes = _sizes(sizes, "sizes")
    _int(reruns, "reruns", 1, 10**5), _seed(seed), _tag(tag), _tag(practice)
    out = {arm: [] for arm in arms}
    for arm in arms:
        for n in sizes:
            for t in task_ids:
                for r in range(reruns):
                    ep_seed = task_seed(f"{tag}:{arm}:{n}", seed, _int(t, "task", 0, 10**6) * 10**6 + r)
                    ts = taskset_for(n, t)
                    rec = run_episode(ts, arm, practice, n_agents=n, seed=ep_seed, **episode_kw(arm, n, t, r, ep_seed))
                    out[arm] += [{"n": n, "task": t, "rerun": r, "agent": a, "pass": p, "seed": seed, "arm": arm}
                                 for a, p in enumerate(agent_passes(rec, ts))]
    return out


def nominal_rows(agent_rows):
    """H1 nominal-group rows from per-agent rows: stats.nominal_group per episode (agents pooled, identical answers
    de-duplicated, the group passes if any distinct answer passes); a row without "answer" counts as its own answer."""
    rows = [{"task": (r["n"], r["task"], r["rerun"]), "answer": r.get("answer", r["agent"]), "pass": r["pass"]}
            for r in _rows(agent_rows, ("n", "task", "rerun", "agent", "pass"), "per-agent")]
    return [{"arm": "nominal", "n": g["task"][0], "task": g["task"][1], "episode": g["task"][2], "pass": int(g["pass"])}
            for g in stats.nominal_group(rows)]


def team_rows(agent_rows):
    """H1 team rows from the team arm's per-agent rows: the episode passes when any agent's work passes (the same
    any-pass reading as the nominal group, so EG isolates what the interaction adds)."""
    ep = {}
    for r in _rows(agent_rows, ("n", "task", "rerun", "agent", "pass"), "per-agent"):
        ep[(r["n"], r["task"], r["rerun"])] = ep.get((r["n"], r["task"], r["rerun"]), 0) | r["pass"]
    return [{"arm": "team", "n": n, "task": t, "episode": k, "pass": y} for (n, t, k), y in sorted(ep.items(), key=str)]


# ----------------------------------------------------------------------------- scripted agents ----

def _rng(tag, n, seed, task, k):
    _tag(tag), _seed(seed), _int(task, "task", 0, 10**6), _int(k, "index", 0, 10**6 - 1)
    return random.Random(task_seed(f"{tag}:{n}", seed, task * 10**6 + k))


def planted_pass_rows(task_ids, n, reruns, q_by_task, c, seed, tag):
    """Scripted H2 agents: per episode, with probability c every agent fails, else each fails with the task's q."""
    _int(n, "n", 2, 10**4), _int(reruns, "reruns", 1, 10**5), _prob(c, "c")
    if len(task_ids) != len(q_by_task):
        raise ValueError("one q per task")
    rows = []
    for t, q in zip(task_ids, q_by_task):
        _prob(q, "q")
        for r in range(reruns):
            rng = _rng(tag, n, seed, t, r)
            common = rng.random() < c
            rows += [{"n": n, "task": t, "rerun": r, "agent": a, "seed": seed,
                      "pass": 0 if common or rng.random() < q else 1}
                     for a in range(n)]
    return rows


def planted_h3_rows(task_ids, per_arm, p_by_task, arms, seed, tag):
    """Scripted H3 episodes. arms = {name: (mu, dp)}: confidence uniform on [mu - 0.1, mu + 0.1] clipped to
    [0, 1] (mean mu when unclipped); pass is 0/1 with probability p_t + dp. Planted G = mu - (mean p_t + dp)."""
    _int(per_arm, "per_arm", 1, 10**5)
    rows = []
    for name, (mu, dp) in sorted(arms.items()):
        _prob(mu, "mu")
        for t, p in zip(task_ids, p_by_task):
            _prob(p + dp, "pass probability")
            for k in range(per_arm):
                rng = _rng(tag + ":" + name, 0, seed, t, k)
                rows.append({"arm": name, "task": t, "conf": min(1.0, max(0.0, mu + (rng.random() - 0.5) * 0.2)),
                             "pass": int(rng.random() < p + dp)})
    return rows


def planted_h1_rows(task_ids, n, episodes, q_by_task, c, gain, seed, tag):
    """Scripted H1 episodes. Nominal group passes when any of n independent-given-cause agents passes
    (P = (1 - c)(1 - q^n)); the team passes with that probability plus the planted gain. Planted EG = gain."""
    _int(n, "n", 2, 10**4), _int(episodes, "episodes", 1, 10**5), _prob(c, "c"), _num(gain, "gain", -1, 1)
    rows = []
    for t, q in zip(task_ids, q_by_task):
        _prob(q, "q")
        p_nom = (1 - c) * (1 - q ** n)
        _prob(p_nom + gain, "team pass probability")
        for k in range(episodes):
            rng = _rng(tag + ":nominal", n, seed, t, k)
            common = rng.random() < c
            nominal = int(not common and any(rng.random() >= q for _ in range(n)))
            rows.append({"arm": "nominal", "n": n, "task": t, "episode": k, "pass": nominal})
            rows.append({"arm": "team", "n": n, "task": t, "episode": k,
                         "pass": int(_rng(tag + ":team", n, seed, t, k).random() < p_nom + gain)})
    return rows


def planted_h5_episodes(task_ids, f_by_task, a_by_task, spread, episodes, cands, first_episode, seed, tag,
                        order_drift):
    """Scripted H5 candidates. Hidden state per episode: failure rate f_t (1 + spread) or f_t (1 - spread), each
    with probability 1/2 (mean f_t; spread = 0 is independent draws); order_drift adds order_drift * j / (cands - 1) to
    the failure rate of the j-th candidate (0 keeps the draws exchangeable). A failing candidate is flagged (flags = 1)
    with probability 1 - a_t; a passing one never. Planted u_t = f_t (1 - a_t)."""
    _num(order_drift, "order_drift", -1, 1)
    _prob(spread, "spread"), _int(episodes, "episodes", 1, 10**5), _int(cands, "cands", 1, 10**4)
    _int(first_episode, "first_episode", 0, 10**5)
    if not len(task_ids) == len(f_by_task) == len(a_by_task):
        raise ValueError("one f and one a per task")
    out = []
    for t, f, a in zip(task_ids, f_by_task, a_by_task):
        _prob(f, "f"), _prob(a, "a")
        if f * (1 + spread) > 1:
            raise ValueError("f (1 + spread) must not exceed 1")
        for e in range(first_episode, first_episode + episodes):
            rng = _rng(tag, 0, seed, t, e)
            ft = f * (1 + spread) if rng.random() < 0.5 else f * (1 - spread)
            cs = []
            for j in range(cands):
                fails = int(rng.random() < min(1.0, max(0.0, ft + order_drift * j / max(1, cands - 1))))
                cs.append({"fails": fails, "flags": int(fails and rng.random() >= a)})
            out.append({"task": t, "episode": e, "cands": cs})
    return out
