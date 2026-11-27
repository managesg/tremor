"""Stage A tests for lab/r5_perf_harness.py: planted-value recovery, closed-form nulls, null calibration, refusals.

Tolerances are derived, never tuned: a rate over R seeded runs is compared with its exact size pi using
4 * sqrt(pi (1 - pi) / R); a replicate mean is compared with 4 * (replicate SD / sqrt(R)) plus a stated bias term.
"""
import hashlib
import math
import random
import statistics as st
import unittest
from fractions import Fraction

from tremor import nulls, team
from tremor.adopters import ScriptedAdopter
from lab import r5_perf_harness as h
from lab.l3c_harness import task_seed

NAN, INF = float("nan"), float("inf")


def _pmf(i, runs, pi):  # log-space, so a large `runs` cannot overflow
    if pi in (0, 1):
        return float(i == (runs if pi else 0))
    return math.exp(math.lgamma(runs + 1) - math.lgamma(i + 1) - math.lgamma(runs - i + 1)
                    + i * math.log(pi) + (runs - i) * math.log1p(-pi))


def tail_ge(k, runs, pi):
    """P(Binomial(runs, pi) >= k) by summing the exact pmf."""
    return sum(_pmf(i, runs, pi) for i in range(k, runs + 1))


def tail_le(k, runs, pi):
    return sum(_pmf(i, runs, pi) for i in range(0, k + 1))


FALSE_ALARM = 1e-3  # a valid procedure fails the test below with probability at most this (exact binomial tail)


class Exact(unittest.TestCase):
    def at_most(self, hits, runs, pi):
        """hits is not significantly above pi: P(Bin(runs, pi) >= hits) >= FALSE_ALARM."""
        self.assertGreaterEqual(tail_ge(hits, runs, pi), FALSE_ALARM, f"{hits}/{runs} vs {pi}")

    def equals(self, hits, runs, pi):
        """hits is not significantly different from pi in either tail (each tail at FALSE_ALARM / 2)."""
        self.assertGreaterEqual(tail_ge(hits, runs, pi), FALSE_ALARM / 2, f"{hits}/{runs} vs {pi}")
        self.assertGreaterEqual(tail_le(hits, runs, pi), FALSE_ALARM / 2, f"{hits}/{runs} vs {pi}")


def h2_args(**kw):
    a = dict(fit_sizes=[2, 4], target_n=8, level=0.95, alpha=0.05, B=200, seed=7, edge=0.02)
    a.update(kw)
    return a


def h2_rows(c_fit, c_held, q=0.3, tasks=40, reruns=10, seed=1, q_held=None):
    fit = [r for n in (2, 4) for r in h.planted_pass_rows(list(range(tasks)), n, reruns, [q] * tasks, c_fit, seed, "fit")]
    held = h.planted_pass_rows(list(range(100, 100 + tasks)), 8, reruns, [q if q_held is None else q_held] * tasks,
                               c_held, seed + 10**6, "held")  # held-out seeds differ from the fit seeds
    return fit, held


def h3_rows(team, solo, tasks=20, per_arm=8, seed=1, tag="h3"):
    p = [0.3 + 0.4 * i / (tasks - 1) for i in range(tasks)]
    return h.planted_h3_rows(list(range(tasks)), per_arm, p, {"team": team, "solo": solo}, seed, tag)


def h3_args(**kw):
    a = dict(team_arm="team", solo_arm="solo", B=200, perms=199, seed=3, level=0.95, edge=0.02, max_unparseable=0.1)
    a.update(kw)
    return a


def h1_rows(gain4, gain8, tasks=24, eps=20, seed=1, c=0.1, q=0.8):
    ids = list(range(tasks))
    return (h.planted_h1_rows(ids, 4, eps, [q] * tasks, c, gain4, seed, "h1")
            + h.planted_h1_rows(ids, 8, eps, [q] * tasks, c, gain8, seed, "h1"))


def h1_args(**kw):
    a = dict(sizes=(4, 8), B=200, perms=99, seed=5, level=0.95, edge=0.02, tokens_matched=True)
    a.update(kw)
    return a


def h5_data(spread, seed, tasks=10, cal=200, cal_cands=3, scored=100, cands=16, f0=0.25, drift=0.0):
    ids = list(range(tasks))
    f = [f0 + 0.25 * i / (tasks - 1) for i in ids]
    a = [0.1 + 0.2 * i / (tasks - 1) for i in ids]
    calib = h.planted_h5_episodes(ids, f, a, spread, cal, cal_cands, 0, seed, "cal", 0.0)
    sc = h.planted_h5_episodes(ids, f, a, spread, scored, cands, 10**4, seed, "sc", drift)
    return calib, sc, f, a


def h5_args(**kw):
    a = dict(grid=(2, 4, 8, 16), B=200, perms=99, seed=9, level=0.95, K=0.01, negligible=0.001, min_clean=400,
             min_fail=200)
    a.update(kw)
    return a


class Refusals(unittest.TestCase):
    def test_missing_parameters_raise_type_error(self):
        fit, held = h2_rows(0.3, 0.3, tasks=3, reruns=2)
        with self.assertRaises(TypeError):
            h.h2_primary(fit, held, fit_sizes=[2, 4], target_n=8, level=0.95, alpha=0.05, B=10, seed=1)  # no edge
        with self.assertRaises(TypeError):
            h.h3_primary(h3_rows((0.8, 0), (0.7, 0)), team_arm="team", solo_arm="solo", B=5, perms=5, seed=1,
                         level=0.9, edge=0.02)
        with self.assertRaises(TypeError):
            h.h1_primary(h1_rows(0, 0, tasks=2, eps=2), sizes=(4, 8), B=5, perms=5, seed=1, level=0.9, edge=0.02)
        calib, sc, _, _ = h5_data(0.0, 1, tasks=2, cal=5, scored=5)
        with self.assertRaises(TypeError):
            h.h5_primary(calib, sc, grid=(2, 4), B=5, perms=5, seed=1, level=0.9, K=0.1)
        with self.assertRaises(TypeError):
            h.holm_family({"H1": 0.01})
        with self.assertRaises(TypeError):
            h.planted_pass_rows([0], 2, 1, [0.5], 0.1, 1)

    def test_bad_numbers_raise_value_error(self):
        fit, held = h2_rows(0.3, 0.3, tasks=3, reruns=2)
        for bad in (True, NAN, INF, -0.1, 1.5):
            for key in ("level", "alpha"):
                with self.subTest(key=key, bad=bad), self.assertRaises(ValueError):
                    h.h2_primary(fit, held, **h2_args(**{key: bad}))
        for key, bad in (("B", True), ("B", 0), ("B", -3), ("seed", True), ("seed", NAN), ("edge", -0.01),
                         ("edge", NAN), ("edge", 0.5), ("target_n", True), ("target_n", 4), ("fit_sizes", [2, True])):
            with self.subTest(key=key, bad=bad), self.assertRaises(ValueError):
                h.h2_primary(fit, held, **h2_args(**{key: bad}))
        calib, sc, _, _ = h5_data(0.0, 1, tasks=2, cal=5, scored=5)
        for key, bad in (("K", True), ("K", 0), ("K", NAN), ("K", -0.1), ("negligible", NAN), ("negligible", 0),
                         ("perms", 0), ("perms", True), ("level", 1), ("level", NAN), ("seed", True),
                         ("grid", ()), ("grid", (2, 2)), ("grid", (2, True)), ("grid", (0, 4)), ("B", True),
                         ("grid", (2, 4, 8)), ("grid", (2, 4, 8, 17)), ("min_clean", 399), ("min_fail", 199),
                         ("min_clean", True), ("min_clean", NAN)):
            with self.subTest(key=key, bad=bad), self.assertRaises(ValueError):
                h.h5_primary(calib, sc, **h5_args(**{key: bad}))
        rows = h3_rows((0.8, 0), (0.7, 0), tasks=3, per_arm=2)
        for key, bad in (("perms", 0), ("edge", NAN), ("max_unparseable", 1.2), ("max_unparseable", True),
                         ("level", 0), ("B", -1)):
            with self.subTest(key=key, bad=bad), self.assertRaises(ValueError):
                h.h3_primary(rows, **h3_args(**{key: bad}))
        r1 = h1_rows(0, 0, tasks=3, eps=2)
        for key, bad in (("tokens_matched", 1), ("sizes", (8, 4)), ("sizes", (4,)), ("perms", True), ("edge", -1)):
            with self.subTest(key=key, bad=bad), self.assertRaises(ValueError):
                h.h1_primary(r1, **h1_args(**{key: bad}))
        for alpha in (True, NAN, 0, 1, -0.1):
            with self.assertRaises(ValueError):
                h.holm_family({"H1": 0.01}, alpha)

    def test_pass_counts_are_per_agent_not_work_slots(self):
        base = {"n": 2, "task": 0, "rerun": 0, "pass": 1}
        ok = [dict(base, agent=0), dict(base, agent=1)]
        self.assertEqual(h.episode_counts(ok), {(2, 0, 0): 2})
        for bad in ([dict(base, agent=0), dict(base, agent=0), dict(base, agent=1)],   # two work slots, one agent
                    [dict(base, agent=0)],                                             # an agent missing
                    [dict(base, agent=0), dict(base, agent=2)],                        # agent id out of range
                    [dict(base, agent=0), dict(base, agent=1, **{"pass": True})],      # bool-as-int
                    [dict(base, agent=0), dict(base, agent=1, **{"pass": 2})],
                    [dict(base, agent=0), dict(base, agent=1, **{"pass": 1.0})],
                    [dict(base, agent=0), {"n": 2, "task": 0, "rerun": 0, "pass": 1}], []):
            with self.assertRaises(ValueError):
                h.episode_counts(bad)

    def test_h2_structure_refusals(self):
        fit, held = h2_rows(0.3, 0.3, tasks=3, reruns=2)
        with self.assertRaises(ValueError):  # one held task set is also a fit task set
            h.h2_primary(fit, [dict(r, task=0) if r["task"] == 100 else r for r in held], **h2_args())
        with self.assertRaises(ValueError):  # target must exceed every fit size
            h.h2_primary(fit, held, **h2_args(target_n=4))
        with self.assertRaises(ValueError):  # fit rows must cover exactly fit_sizes
            h.h2_primary([r for r in fit if r["n"] == 2], held, **h2_args())
        with self.assertRaises(ValueError):  # held rows must be at the target size only
            h.h2_primary(fit, fit[:2] + held, **h2_args())
        with self.assertRaises(ValueError):  # a held-out seed is also a fit seed
            h.h2_primary(fit, [dict(r, seed=fit[0]["seed"]) for r in held], **h2_args())
        with self.assertRaises(ValueError):  # rows without a seed
            h.h2_primary(fit, [{k: v for k, v in r.items() if k != "seed"} for r in held], **h2_args())
        for key, bad in (("fit_sizes", [2, 4, 6]), ("fit_sizes", [2]), ("target_n", 16), ("fit_sizes", [3, 4])):
            with self.subTest(key=key), self.assertRaises(ValueError):
                h.h2_primary(fit, held, **h2_args(**{key: bad}))
        # rows that agree with an unregistered design are refused by the registered values alone
        fit6 = [r for n in (2, 4, 6) for r in h.planted_pass_rows(list(range(3)), n, 2, [0.3] * 3, 0.1, 1, "f")]
        with self.assertRaises(ValueError):
            h.h2_primary(fit6, held, **h2_args(fit_sizes=[2, 4, 6]))
        held16 = h.planted_pass_rows([100, 101, 102], 16, 2, [0.3] * 3, 0.1, 2, "h")
        with self.assertRaises(ValueError):
            h.h2_primary(fit, held16, **h2_args(target_n=16))
        with self.assertRaises(ValueError):  # H1 sizes are the registered (4, 8)
            h.h1_primary(h1_rows(0, 0, tasks=3, eps=2), **h1_args(sizes=(2, 8)))

    def test_h5_structure_refusals(self):
        calib, sc, _, _ = h5_data(0.0, 1, tasks=3, cal=20, scored=20)
        with self.assertRaises(ValueError):  # a scored episode also sits in the calibration split
            h.h5_primary(calib + sc[:1], sc, **h5_args())
        with self.assertRaises(ValueError):  # scored episodes shorter than max(grid)
            h.h5_primary(calib, [dict(e, cands=e["cands"][:8]) for e in sc], **h5_args())
        with self.assertRaises(ValueError):  # a scored task with no calibration
            h.h5_primary([e for e in calib if e["task"] != 2], sc, **h5_args())
        with self.assertRaises(ValueError):
            h.planted_h5_episodes([0], [0.7], [0.1], 0.5, 3, 3, 0, 1, "x", 0.0)  # f (1 + spread) > 1
        with self.assertRaises(ValueError):
            h.select_clean([{"flags": 0}], 2)

    def test_h3_h1_structure_refusals(self):
        rows = [r for r in h3_rows((0.8, 0), (0.7, 0), tasks=3, per_arm=2) if not (r["task"] == 1 and r["arm"] == "solo")]
        with self.assertRaises(ValueError):
            h.h3_primary(rows, **h3_args())
        r1 = [r for r in h1_rows(0, 0, tasks=3, eps=2) if not (r["task"] == 1 and r["arm"] == "team" and r["n"] == 8)]
        with self.assertRaises(ValueError):
            h.h1_primary(r1, **h1_args())
        with self.assertRaises(ValueError):
            h.h1_primary([dict(r, arm="solo") for r in h1_rows(0, 0, tasks=3, eps=2)], **h1_args())
        with self.assertRaises(ValueError):
            h.holm_family({"H2": 0.01}, 0.05)
        with self.assertRaises(ValueError):
            h.holm_family({}, 0.05)
        with self.assertRaises(ValueError):
            h.holm_family({"H1": NAN}, 0.05)


class Seeding(unittest.TestCase):
    def test_task_seed_is_sha256_of_tag_seed_index(self):
        want = int.from_bytes(hashlib.sha256(b"tag:5:3").digest()[:8], "big") >> 1
        self.assertEqual(task_seed("tag", 5, 3), want)

    def test_generator_uses_that_seed_per_episode(self):
        rows = h.planted_pass_rows([4], 3, 2, [0.4], 0.25, 11, "tg")
        rng = random.Random(task_seed("tg:3", 11, 4 * 10**6 + 1))
        common = rng.random() < 0.25
        want = [0 if common or rng.random() < 0.4 else 1 for _ in range(3)]
        self.assertEqual([r["pass"] for r in rows if r["rerun"] == 1], want)

    def test_same_seed_same_rows_adjacent_seed_differs(self):
        a = h.planted_pass_rows(list(range(5)), 4, 5, [0.5] * 5, 0.2, 1, "t")
        self.assertEqual(a, h.planted_pass_rows(list(range(5)), 4, 5, [0.5] * 5, 0.2, 1, "t"))
        self.assertNotEqual(a, h.planted_pass_rows(list(range(5)), 4, 5, [0.5] * 5, 0.2, 2, "t"))
        self.assertNotEqual(a, h.planted_pass_rows(list(range(5)), 4, 5, [0.5] * 5, 0.2, 1, "u"))

    def test_bootstrap_is_deterministic_and_seed_sensitive(self):
        items = list(range(30))
        a = h._boot(items, st.fmean, 300, 1, 0.9, "x")
        self.assertEqual(a, h._boot(items, st.fmean, 300, 1, 0.9, "x"))
        self.assertNotEqual(a, h._boot(items, st.fmean, 300, 2, 0.9, "x"))

    def test_bootstrap_interval_matches_normal_theory(self):
        # mean of 0..99 resampled: sd = sqrt(var_pop / 100); 90% interval = mean -/+ 1.645 sd. MC quantile error
        # with B = 2000: sqrt(.05 * .95 / B) / density(1.645) = 0.136; 4 of them = 0.55 (+ margin for the normal approx).
        items = list(range(100))
        sd = math.sqrt(st.pvariance(items) / 100)
        lo, hi = h._boot(items, st.fmean, 2000, 4, 0.9, "n")
        self.assertAlmostEqual(lo, 49.5 - 1.645 * sd, delta=0.6)
        self.assertAlmostEqual(hi, 49.5 + 1.645 * sd, delta=0.6)
        with self.assertRaises(ValueError):
            h._boot([1], st.fmean, 10, 1, 0.9, "n")


class H2(Exact):
    def test_pmf_closed_form_and_nulls_all_miss(self):
        self.assertEqual([Fraction(x).limit_denominator(64) for x in h.pmf(2, 0.5, 0.25)],
                         [Fraction(7, 16), Fraction(3, 8), Fraction(3, 16)])
        for n in (2, 4, 8):
            for q, c in ((Fraction(1, 2), Fraction(1, 4)), (Fraction(1, 5), Fraction(1, 3))):
                pm = h.pmf(n, float(q), float(c))
                self.assertAlmostEqual(sum(pm), 1.0, places=12)
                self.assertAlmostEqual(pm[0], float(nulls.correlated_monitors(n, q, c)["all_miss"]), places=12)
        self.assertEqual(h.pmf(3, 0.0, 0.0), [0.0, 0.0, 0.0, 1.0])  # ceiling
        with self.assertRaises(ValueError):
            h.pmf(1, 0.5, 0.1)

    def test_exact_expected_counts_recover_planted_q_and_c(self):
        for q, c, scale in ((Fraction(1, 2), Fraction(1, 4), 256), (Fraction(1, 4), Fraction(1, 2), 512)):
            counts = {n: [int(x * scale) for x in (Fraction(v) for v in h.pmf(n, float(q), float(c)))] for n in (2, 4)}
            self.assertTrue(all(sum(v) == scale for v in counts.values()))
            fit = h.fit_common_cause(counts)
            self.assertAlmostEqual(fit["q"], float(q), places=5)
            self.assertAlmostEqual(fit["c"], float(c), places=5)
            self.assertFalse(fit["degenerate"])

    def test_independent_expected_counts_recover_c_zero(self):
        counts = {n: [int(x * 4096) for x in h.pmf(n, 0.25, 0.0)] for n in (2, 4)}
        fit = h.fit_common_cause(counts)
        self.assertAlmostEqual(fit["c"], 0.0, places=6)
        self.assertAlmostEqual(fit["q"], 0.25, places=6)
        self.assertAlmostEqual(h.fit_independent(counts)["q"], 0.25, places=12)

    def test_fit_is_the_maximum(self):
        counts = {2: [30, 40, 30], 4: [20, 10, 20, 25, 25]}
        fit = h.fit_common_cause(counts)
        for q, c in ((0.5, 0.2), (0.4, 0.1), (0.6, 0.3), (0.5, 0.0), (0.3, 0.4)):
            self.assertGreaterEqual(fit["loglik"], h._loglik(q, c, counts) - 1e-9)

    def test_degenerate_floor_and_ceiling(self):
        floor = h.fit_common_cause({2: [10, 0, 0], 4: [10, 0, 0, 0, 0]})
        self.assertTrue(floor["degenerate"])
        self.assertEqual(floor["c"], 1.0)
        ceil = h.fit_common_cause({2: [0, 0, 10], 4: [0, 0, 0, 0, 10]})
        self.assertTrue(ceil["degenerate"])
        self.assertEqual((ceil["q"], ceil["c"]), (0.0, 0.0))
        with self.assertRaises(ValueError):
            h.fit_common_cause({2: [0, 0, 0]})
        with self.assertRaises(ValueError):
            h.fit_common_cause({2: [1, 1]})

    def test_sampled_recovery_replicate_mean_within_4_se(self):
        q, c, reps = 0.3, 0.3, 40
        qs, cs = [], []
        for s in range(reps):
            ep = h.episode_counts([r for n in (2, 4) for r in h.planted_pass_rows(list(range(40)), n, 10, [q] * 40, c, s, "rec")])
            counts = {2: [0] * 3, 4: [0] * 5}
            for (n, _, _), x in ep.items():
                counts[n][x] += 1
            f = h.fit_common_cause(counts)
            qs.append(f["q"]), cs.append(f["c"])
        for got, want in ((qs, q), (cs, c)):
            self.assertLessEqual(abs(st.fmean(got) - want), 4 * st.stdev(got) / math.sqrt(reps))

    def test_binomial_test_closed_form(self):
        self.assertEqual([h.binom_two_sided(k, 2, 0.95) for k in range(3)],
                         [Fraction(1, 400), Fraction(39, 400), Fraction(1)])
        self.assertEqual([h.binom_two_sided(k, 2, 0.5) for k in range(3)], [Fraction(1, 2), Fraction(1), Fraction(1, 2)])
        self.assertEqual(h.binom_two_sided(0, 2, Fraction(19, 20)), Fraction(1, 400))
        with self.assertRaises(ValueError):
            h.binom_two_sided(3, 2, 0.5)
        with self.assertRaises(ValueError):
            h.binom_two_sided(1, 2, 1.0)

    def test_coverage_p_closed_forms(self):
        self.assertEqual([h.coverage_p(k, [0.5, 0.5]) for k in range(3)], [0.5, 1.0, 0.5])
        self.assertAlmostEqual(h.coverage_p(0, [0.9, 0.5]), 0.05)    # outcomes: 0.05, 0.5, 0.45
        self.assertAlmostEqual(h.coverage_p(1, [0.9, 0.5]), 1.0)
        self.assertAlmostEqual(h.coverage_p(2, [0.9, 0.5]), 0.5)
        for k in range(3):  # equal probabilities are the binomial
            self.assertAlmostEqual(h.coverage_p(k, [0.95] * 2), float(h.binom_two_sided(k, 2, 0.95)))
        with self.assertRaises(ValueError):
            h.coverage_p(3, [0.5, 0.5])
        with self.assertRaises(ValueError):
            h.coverage_p(0, [1.5])

    def test_coverage_detail_exact_probabilities(self):
        d = h.coverage_detail({"a": [1], "b": [2]}, [0.25, 0.5, 0.25], 0.5)  # interval (0, 1), coverage 0.75
        self.assertEqual((d["inside"], d["probs"]), (1, [0.75, 0.75]))
        d = h.coverage_detail({"a": [1, 1]}, [0.25, 0.5, 0.25], 0.875)  # Binomial(4, 1/2) on (0, 3): 15/16
        self.assertEqual((d["inside"], d["probs"]), (1, [15 / 16]))

    def test_coverage_test_size_matches_exact_enumeration(self):
        # 40 task sets, each covered with its exact probability (two sets share a smaller one): the test's exact size
        # comes from enumerating the Poisson binomial; the sampled rejection rate must agree (exact binomial tails).
        probs, alpha, runs = [0.957] * 38 + [0.9, 0.8], 0.05, 1500
        pm = h.poisson_binomial_pmf(probs)
        size = sum(x for k, x in enumerate(pm) if h.coverage_p(k, probs) <= alpha)
        self.assertLessEqual(size, alpha + 1e-12)
        rng, rej = random.Random(task_seed("cov", 1, 0)), 0
        for _ in range(runs):
            k = sum(rng.random() < p for p in probs)
            rej += h.coverage_p(k, probs) <= alpha
        self.equals(rej, runs, size)

    def test_predictive_interval_closed_form(self):
        self.assertEqual(h.predictive_sum_interval([0.25, 0.5, 0.25], 1, 0.5), (0, 1))
        self.assertEqual(h.predictive_sum_interval([0.25, 0.5, 0.25], 2, 0.875), (0, 3))  # Binomial(4, 1/2)
        self.assertEqual(h.predictive_sum_interval([0.0, 1.0], 3, 0.9), (3, 3))
        a, b = h.predictive_sum_interval(h.pmf(8, 0.3, 0.2), 10, 0.95)
        self.assertLess(a, b)

    def test_floor_ceiling_detector_for_b0(self):
        def rows(n, passes):
            return [{"n": n, "task": 0, "rerun": 0, "agent": a, "pass": p} for a, p in enumerate(passes)]
        allr = rows(2, [0, 0]) + rows(4, [1, 1, 1, 1]) + rows(8, [1, 0, 1, 0, 1, 0, 1, 0])
        out = h.floor_ceiling_reading(allr, [2, 4, 8], 0.1)
        self.assertEqual([out[n]["reading"] for n in (2, 4, 8)], ["floor", "ceiling", "ok"])
        self.assertEqual(out[8]["rate"], 0.5)
        edge = rows(8, [1, 0, 0, 0, 0, 0, 0, 0] )  # rate 1/8
        self.assertEqual(h.floor_ceiling_reading(edge, [8], 0.125)[8]["reading"], "floor")  # edge inclusive
        self.assertEqual(h.floor_ceiling_reading(edge, [8], 0.12)[8]["reading"], "ok")
        self.assertEqual(h.floor_ceiling_reading(rows(8, [1] * 7 + [0]), [8], 0.125)[8]["reading"], "ceiling")
        self.assertEqual(h.floor_ceiling_reading(allr, [8], 0.0)[8]["reading"], "ok")
        with self.assertRaises(ValueError):
            h.floor_ceiling_reading(allr, [16], 0.1)
        # B0 shape: one task set, one rerun, from the scripted generator
        b0 = [r for n in (2, 4, 8) for r in h.planted_pass_rows([0], n, 1, [1.0], 0.0, 1, "b0")]
        self.assertEqual({v["reading"] for v in h.floor_ceiling_reading(b0, [2, 4, 8], 0.05).values()}, {"floor"})
        b0 = [r for n in (2, 4, 8) for r in h.planted_pass_rows([0], n, 1, [0.0], 0.0, 1, "b0")]
        self.assertEqual({v["reading"] for v in h.floor_ceiling_reading(b0, [2, 4, 8], 0.05).values()}, {"ceiling"})

    def test_coverage_count_boundaries_are_inclusive(self):
        pm = [0.25, 0.5, 0.25]  # one rerun, level 0.5: interval (0, 1)
        self.assertEqual(h.coverage_count({"a": [0], "b": [1], "c": [2]}, pm, 0.5), 2)
        self.assertEqual(h.coverage_count({"a": [0, 0], "b": [2, 2]}, pm, 0.875), 1)  # sum interval (0, 3): 4 is out
        self.assertEqual(h.coverage_count({"a": [1, 2], "b": [0, 0]}, pm, 0.875), 2)  # 3 and 0 sit on the bounds

    def test_decision_rules(self):
        d = h.h2_decision
        self.assertEqual(d((0.1, 0.3), 0.5, 0.05, []), "supported")
        self.assertEqual(d((0.1, 0.3), 0.05, 0.05, []), "inconclusive")  # coverage rejected (p <= alpha)
        self.assertEqual(d((0.1, 0.3), 0.051, 0.05, []), "supported")
        self.assertEqual(d((-0.3, -0.1), 0.5, 0.05, []), "killed")
        self.assertEqual(d((-0.3, -0.1), 0.001, 0.05, []), "killed")
        self.assertEqual(d((-0.1, 0.3), 0.5, 0.05, []), "inconclusive")
        self.assertEqual(d((0.0, 0.3), 0.5, 0.05, []), "inconclusive")
        self.assertEqual(d((0.1, 0.3), 0.5, 0.05, ["floor"]), "uninformative")
        self.assertEqual(d((-0.3, -0.1), 0.5, 0.05, ["floor"]), "uninformative")

    def test_log_score_difference_is_the_closed_form(self):
        fit, held = h2_rows(0.4, 0.4, tasks=6, reruns=10, seed=3)
        res = h.h2_primary(fit, held, **h2_args())
        ep = h.episode_counts(fit)
        counts = {2: [0] * 3, 4: [0] * 5}
        for (n, _, _), x in ep.items():
            counts[n][x] += 1
        f, ind = h.fit_common_cause(counts), h.fit_independent(counts)
        pm, pm0 = h.pmf(8, f["q"], f["c"]), h.pmf(8, ind["q"], 0.0)
        by = {}
        for (_, t, _), x in h.episode_counts(held).items():
            by.setdefault(t, []).append(x)
        want = st.fmean(st.fmean(math.log(pm[x]) - math.log(pm0[x]) for x in xs) for xs in by.values())
        self.assertAlmostEqual(res["diff"], want, places=12)
        self.assertAlmostEqual(res["fit"]["q"], f["q"], places=12)
        self.assertEqual(res["comparator"]["c"], 0.0)

    def test_power_planted_common_cause_is_supported(self):
        fit, held = h2_rows(0.4, 0.4)
        res = h.h2_primary(fit, held, **h2_args())
        self.assertGreater(res["diff"], 0)
        self.assertGreater(res["interval"][0], 0)
        self.assertEqual(res["coverage"]["m"], 40)
        self.assertEqual(res["uninformative"], [])
        self.assertEqual(res["decision"], "supported")
        self.assertAlmostEqual(res["fit"]["c"], 0.4, delta=0.1)
        self.assertFalse(res["c_at_zero"])
        lo, hi = res["coverage"]["exact"]  # exact coverage of the nominal 95% interval is above 0.95
        self.assertTrue(0.95 < lo <= hi < 0.97)
        self.assertGreater(res["coverage"]["p"], 0.05)
        by = {}
        for (_, t, _), x in h.episode_counts(held).items():
            by.setdefault(t, []).append(x)
        d = h.coverage_detail(by, h.pmf(8, res["fit"]["q"], res["fit"]["c"]), 0.95)
        self.assertEqual(res["coverage"]["inside"], d["inside"])
        self.assertEqual(res["coverage"]["p"], h.coverage_p(d["inside"], d["probs"]))
        self.assertNotEqual(res["coverage"]["p"], float(h.binom_two_sided(d["inside"], 40, 0.95)))  # not tested against 0.95

    def test_killed_when_small_team_common_cause_does_not_carry_to_n8(self):
        # pairs and fours share a cause; the eight do not, and their marginal pass rate (0.42) is what c = 0 fits
        fit, held = h2_rows(0.4, 0.0, q_held=0.58)
        res = h.h2_primary(fit, held, **h2_args())
        self.assertLess(res["interval"][1], 0)
        self.assertEqual(res["decision"], "killed")

    def test_uninformative_cases(self):
        fit, held = h2_rows(0.0, 0.0)  # independent at every n: overdispersion intervals all contain 1
        res = h.h2_primary(fit, held, **h2_args())
        self.assertIn("overdispersion interval contains 1 at every n", res["uninformative"])
        self.assertEqual(res["decision"], "uninformative")
        fit, held = h2_rows(0.4, 0.4, reruns=9)
        res = h.h2_primary(fit, held, **h2_args())
        self.assertIn("under 10 reruns", res["uninformative"])
        fit, held = h2_rows(0.4, 0.4, reruns=10)
        self.assertNotIn("under 10 reruns", h.h2_primary(fit, held, **h2_args())["uninformative"])
        fit, held = h2_rows(0.0, 0.0, q=1.0)  # every agent fails at every n: the fit is degenerate
        res = h.h2_primary(fit, held, **h2_args())
        self.assertTrue(any(s.startswith("fit degenerate") for s in res["uninformative"]))
        self.assertEqual(res["decision"], "uninformative")
        fit, held = h2_rows(0.4, 0.4, q_held=1.0)  # every agent fails at n = 8
        res = h.h2_primary(fit, held, **h2_args())
        self.assertTrue(any(s.startswith("floor at n = 8") for s in res["uninformative"]))
        self.assertEqual(res["decision"], "uninformative")

    def test_within_episode_dispersion_closed_form(self):
        def rows(n, task, xs):
            return [{"n": n, "task": task, "rerun": r, "agent": a, "pass": int(a < x), "seed": 1}
                    for r, x in enumerate(xs) for a in range(n)]
        # task A: X = 0, 2, 2, 0 (mean 1, SS 4, R 4) -> den = 3 * 2 * .25 * 8/7; task B: X = 1, 1 -> SS 0, den = 2/3
        data = rows(2, "A", [0, 2, 2, 0]) + rows(2, "B", [1, 1])
        items = h._within_items(data, 2)
        self.assertEqual([round(x, 12) for x in items[0]], [4.0, round(12 / 7, 12)])
        self.assertEqual([round(x, 12) for x in items[1]], [0.0, round(2 / 3, 12)])
        point, _ = h.overdispersion_interval(data + rows(2, "C", [0, 1, 2]), 2, 20, 1, 0.9)
        self.assertGreater(point, 1)
        with self.assertRaises(ValueError):  # one episode cannot show within-task spread
            h.overdispersion_interval(rows(2, "A", [1]) + rows(2, "B", [1]), 2, 20, 1, 0.9)

    def test_independent_agents_with_different_task_rates_are_not_flagged(self):
        # pass rates 0.8 / 0.2 by task: large task-to-task spread, no shared failure inside any episode
        qs = [0.2 if t % 2 else 0.8 for t in range(40)]
        for n in (2, 4, 8):
            rows = h.planted_pass_rows(list(range(40)), n, 10, qs, 0.0, 3, "od")
            point, (lo, hi) = h.overdispersion_interval(rows, n, 300, 1, 0.95)
            self.assertLessEqual(lo, 1.0 <= hi, (n, lo, hi))
            self.assertAlmostEqual(point, 1.0, delta=0.3)

    def test_planted_shared_cause_is_flagged_at_every_size(self):
        for qs in ([0.3] * 40, [0.2 if t % 2 else 0.5 for t in range(40)]):
            for n in (2, 4, 8):
                rows = h.planted_pass_rows(list(range(40)), n, 10, qs, 0.4, 3, "od")
                point, (lo, hi) = h.overdispersion_interval(rows, n, 300, 1, 0.95)
                self.assertGreater(lo, 1.0, (n, lo, hi))
        # heterogeneous task rates and no shared cause: the whole H2 verdict is uninformative, not "supported"
        fit = [r for n in (2, 4) for r in h.planted_pass_rows(list(range(40)), n, 10, [0.2 if t % 2 else 0.8 for t in range(40)], 0.0, 1, "f")]
        held = h.planted_pass_rows(list(range(100, 140)), 8, 10, [0.2 if t % 2 else 0.8 for t in range(40)], 0.0, 2, "h")
        res = h.h2_primary(fit, held, **h2_args())
        self.assertIn("overdispersion interval contains 1 at every n", res["uninformative"])
        self.assertEqual(res["decision"], "uninformative")

    def test_interval_carries_the_fits_uncertainty(self):
        # few fit task sets, many held-out ones: the joint interval is wider than the held-out-only bootstrap
        fit, held = h2_rows(0.3, 0.3, tasks=40, seed=5)
        fit = [r for r in fit if r["task"] < 4]
        res = h.h2_primary(fit, held, **h2_args(B=300))
        pm, pm0 = h.pmf(8, res["fit"]["q"], res["fit"]["c"]), h.pmf(8, res["comparator"]["q"], 0.0)
        by = {}
        for (_, t, _), x in h.episode_counts(held).items():
            by.setdefault(t, []).append(math.log(pm[x]) - math.log(pm0[x]))
        lo, hi = h._boot([st.fmean(v) for v in by.values()], st.fmean, 300, 7, 0.95, "x")
        self.assertGreater(res["interval"][1] - res["interval"][0], 1.5 * (hi - lo))

    def test_null_calibration_independent_agents(self):
        # Independent agents (the plan's null). Nominal tail of a 90% interval: 0.05 per side. The bound is the exact
        # binomial tail; fits with c at 0 (forecast identical to the comparator, difference 0) are reported, not counted
        # as hits, and the rate among the others is bounded separately.
        runs, hits, zero, hits_pos, supported = 150, 0, 0, 0, 0
        for s in range(runs):
            fit, held = h2_rows(0.0, 0.0, tasks=12, seed=100 + s)
            res = h.h2_primary(fit, held, **h2_args(level=0.9, B=60, seed=s))
            hits += res["interval"][0] > 0
            zero += res["c_at_zero"]
            hits_pos += res["interval"][0] > 0 and not res["c_at_zero"]
            supported += res["decision"] == "supported"
        self.assertGreater(zero, 0)                      # the degenerate fits exist and are reported
        self.at_most(hits, runs, 0.05)
        self.at_most(hits_pos, runs - zero, 0.05)        # among fits with c > 0
        self.at_most(supported, runs, 0.05)              # the gated verdict


class H3(Exact):
    def test_brier_closed_form(self):
        self.assertAlmostEqual(h.brier([0.9, 0.5], [1, 0]), (0.01 + 0.25) / 2)
        for bad in (([0.9], [True]), ([0.9], [2]), ([1.2], [1]), ([], []), ([0.9], [1, 0])):
            with self.assertRaises(ValueError):
                h.brier(*bad)

    def test_planted_delta_g_is_recovered(self):
        # solo: conf 0.7, pass mean 0.5 -> G = 0.2; team: conf 0.8, pass mean 0.4 -> G = 0.4; planted dG = 0.2
        reps, got = 40, []
        for s in range(reps):
            res = h.h3_primary(h3_rows((0.8, -0.1), (0.7, 0.0), tasks=10, per_arm=10, seed=s), **h3_args(B=2, perms=1))
            got.append(res["delta_g"])
        self.assertLessEqual(abs(st.fmean(got) - 0.2), 4 * st.stdev(got) / math.sqrt(reps))

    def test_overconfident_team_is_supported_underconfident_is_killed(self):
        res = h.h3_primary(h3_rows((0.9, -0.1), (0.7, 0.0)), **h3_args())  # planted dG = 0.3
        self.assertGreater(res["interval"][0], 0)
        self.assertLessEqual(res["p_up"], 0.05)
        self.assertEqual(res["decision"], "supported")
        self.assertIsNotNone(res["brier"])
        res = h.h3_primary(h3_rows((0.5, 0.1), (0.7, 0.0)), **h3_args())  # planted dG = -0.3
        self.assertLess(res["interval"][1], 0)
        self.assertGreater(res["p_up"], 0.9)
        self.assertLessEqual(res["p_low"], 0.05)
        self.assertEqual(res["decision"], "killed")

    def test_permuted_pair_stays_together(self):
        # confidence equals the outcome in every pair: every pair gives G = 0, so every relabelling does too.
        rows = [{"arm": a, "task": t, "conf": float(y), "pass": float(y)}
                for a in ("team", "solo") for t in (0, 1, 2) for y in (0, 1, 1, 0)]
        res = h.h3_primary(rows, **h3_args(perms=20, edge=0.4))
        self.assertTrue(all(abs(x) < 1e-12 for x in res["null"]))
        self.assertEqual(res["p_up"], 1.0)
        self.assertEqual(res["p_low"], 1.0)

    def test_permutation_null_matches_closed_form_mean_and_variance(self):
        pairs = {0: ([(0.9, 1), (0.8, 0), (0.6, 1)], [(0.4, 0), (0.5, 1), (0.7, 0), (0.2, 0), (0.95, 1)]),
                 1: ([(0.3, 0), (0.6, 1), (0.8, 1)], [(0.1, 1), (0.9, 0), (0.5, 0), (0.55, 1), (0.65, 0)])}
        rows = [{"arm": arm, "task": t, "conf": c, "pass": y}
                for t, (team, solo) in pairs.items() for arm, ps in (("team", team), ("solo", solo)) for c, y in ps]
        perms = 4000
        res = h.h3_primary(rows, **h3_args(perms=perms, B=10))
        var = 0.0
        for team, solo in pairs.values():
            g = [c - y for c, y in team + solo]
            n_, a, b = len(g), len(team), len(solo)
            var += st.pvariance(g) * n_ / (n_ - 1) * (1 / a + 1 / b)
        var /= len(pairs) ** 2
        null = res["null"]
        self.assertLessEqual(abs(st.fmean(null)), 4 * math.sqrt(var / perms))  # E[dG] = 0
        self.assertLessEqual(abs(st.variance(null) / var - 1), 5 * math.sqrt(2 / (perms - 1)))

    def test_null_calibration_permutation_p_has_exact_size(self):
        # Exchangeable arms, continuous statistic: P(p_up <= alpha) = floor(alpha (B + 1)) / (B + 1) exactly.
        runs, perms, alpha = 400, 39, 0.1
        pi = math.floor(alpha * (perms + 1) + 1e-9) / (perms + 1)
        hits = 0
        for s in range(runs):
            rows = h3_rows((0.7, 0.0), (0.7, 0.0), tasks=6, per_arm=6, seed=s, tag="nullcal")
            hits += h.h3_primary(rows, **h3_args(B=5, perms=perms, seed=s))["p_up"] <= alpha + 1e-12
        self.equals(hits, runs, pi)

    def test_uninformative_cases(self):
        rows = [dict(r, conf=0.5) for r in h3_rows((0.9, -0.1), (0.7, 0.0))]
        self.assertIn("constant confidences", h.h3_primary(rows, **h3_args())["uninformative"])
        rows = h3_rows((0.9, -0.1), (0.7, 0.0))
        cut = [dict(r, conf=None) if i % 3 == 0 else r for i, r in enumerate(rows)]
        res = h.h3_primary(cut, **h3_args())
        self.assertIn("unparseable confidence share above the cap", res["uninformative"])
        self.assertEqual(res["decision"], "uninformative")
        self.assertEqual(h.h3_primary(cut, **h3_args(max_unparseable=0.5))["uninformative"], [])
        zero = [dict(r, **{"pass": 0}) for r in rows]
        self.assertTrue(any("floor or ceiling" in s for s in h.h3_primary(zero, **h3_args())["uninformative"]))

    def test_behaviour_check(self):
        with_f = h.planted_h3_rows(list(range(30)), 6, [0.5] * 30, {"with": (0.7, 0.2), "without": (0.7, 0.0)}, 1, "b")
        res = h.behaviour_check(with_f, with_arm="with", without_arm="without", B=200, seed=1, level=0.95)
        self.assertTrue(res["excludes_zero"])
        self.assertAlmostEqual(res["diff"], 0.2, delta=0.1)
        same = [dict(r, arm=a) for r in with_f if r["arm"] == "without" for a in ("with", "without")]
        res = h.behaviour_check(same, with_arm="with", without_arm="without", B=50, seed=1, level=0.95)
        self.assertFalse(res["excludes_zero"])
        self.assertEqual(res["diff"], 0.0)


class H1(Exact):
    def test_planted_gain_is_recovered(self):
        for n, gain in ((4, 0.15), (8, -0.1)):
            got = []
            for s in range(40):
                rows = h.planted_h1_rows(list(range(10)), n, 20, [0.8] * 10, 0.1, gain, s, "rec")
                got.append(h.stats.emergence_gain([r["pass"] for r in rows if r["arm"] == "team"],
                                                  [r["pass"] for r in rows if r["arm"] == "nominal"]))
            self.assertLessEqual(abs(st.fmean(got) - gain), 4 * st.stdev(got) / math.sqrt(40))

    def test_same_side_is_supported_opposite_sides_killed_none_inconclusive(self):
        res = h.h1_primary(h1_rows(0.2, 0.05, seed=2), **h1_args())  # unequal p: 0.01 and 0.02
        self.assertEqual(res["decision"], "supported")
        self.assertNotEqual(res["sizes"][4]["p"], res["sizes"][8]["p"])
        self.assertEqual(res["p_holm"], max(res["sizes"][4]["p"], res["sizes"][8]["p"]))
        res = h.h1_primary(h1_rows(0.2, 0.2), **h1_args())
        self.assertEqual(res["decision"], "supported")
        self.assertLessEqual(res["p_holm"], 0.05)
        res = h.h1_primary(h1_rows(-0.2, -0.2), **h1_args())  # both below 0: still the same side
        self.assertEqual(res["decision"], "supported")
        self.assertLessEqual(res["p_holm"], 0.05)  # two-sided p
        res = h.h1_primary(h1_rows(0.2, -0.2), **h1_args())
        self.assertEqual(res["decision"], "killed")
        self.assertEqual(res["p_holm"], 1.0)
        res = h.h1_primary(h1_rows(-0.2, 0.2), **h1_args())
        self.assertEqual(res["decision"], "killed")
        res = h.h1_primary(h1_rows(0.2, 0.0, seed=2), **h1_args())
        self.assertEqual(res["decision"], "inconclusive")
        res = h.h1_primary(h1_rows(0.0, 0.0, seed=2), **h1_args())
        self.assertEqual(res["decision"], "inconclusive")

    def test_uninformative_cases(self):
        res = h.h1_primary(h1_rows(0.2, 0.2), **h1_args(tokens_matched=False))
        self.assertEqual((res["decision"], res["uninformative"]), ("uninformative", ["token match failed"]))
        res = h.h1_primary(h1_rows(0.0, 0.0, q=0.999, c=0.0), **h1_args())
        self.assertTrue(any("floor or ceiling" in s for s in res["uninformative"]))

    def test_permutation_null_matches_hypergeometric_closed_form(self):
        # One task of m + m episodes with k passes: EG = (2X - k) / m, X ~ Hypergeometric(2m, k, m).
        tasks = {0: ([1, 1, 0, 1], [0, 0, 1, 0]), 1: ([1, 0, 0, 1], [1, 1, 1, 0])}
        rows = [{"arm": arm, "n": n, "task": t, "episode": i, "pass": y}
                for n in (4, 8) for t, (team, nom) in tasks.items()
                for arm, ys in (("team", team), ("nominal", nom)) for i, y in enumerate(ys)]
        perms = 4000
        res = h.h1_primary(rows, **h1_args(perms=perms, B=10, edge=0.01))
        var = 0.0
        for team, nom in tasks.values():
            m, k = len(team), sum(team) + sum(nom)
            var += 4 * m * (k / (2 * m)) * (1 - k / (2 * m)) * m / (2 * m - 1) / m ** 2
        var /= 4
        null = res["sizes"][4]["null"]
        self.assertLessEqual(abs(st.fmean(null)), 4 * math.sqrt(var / perms))
        self.assertLessEqual(abs(st.variance(null) / var - 1), 5 * math.sqrt(2 / (perms - 1)))

    def test_null_calibration_permutation_p_is_valid(self):
        # Equal team and nominal distributions; the statistic is discrete, so the test is conservative:
        # P(p <= alpha) <= floor(alpha (B + 1)) / (B + 1).
        runs, perms, alpha = 400, 39, 0.1
        pi = math.floor(alpha * (perms + 1) + 1e-9) / (perms + 1)
        hits = 0
        for s in range(runs):
            res = h.h1_primary(h1_rows(0.0, 0.0, tasks=6, eps=6, seed=1000 + s), **h1_args(B=5, perms=perms, seed=s))
            hits += res["sizes"][4]["p"] <= alpha + 1e-12
        self.at_most(hits, runs, pi)


class H5(Exact):
    def test_selection_rule(self):
        c = lambda *flags: [{"flags": f} for f in flags]
        self.assertEqual(h.select_clean(c(2, 1, 0, 0), 4), (2, True))
        self.assertEqual(h.select_clean(c(2, 1, 0, 0), 2), (0, False))   # none clean: candidate 0, flagged
        self.assertEqual(h.select_clean(c(3, 1, 1), 3), (0, False))      # fewest flags is not clean
        self.assertEqual(h.select_clean(c(0, 0), 2), (0, True))          # first wins ties
        self.assertEqual(h.select_clean(c(1, 0, 0), 3), (1, True))
        self.assertEqual(h.select_clean(c(1, 0, 0), 1), (0, False))      # only the first n are looked at

    def test_hand_computed_statistic(self):
        def ep(task, i, *flags):
            return {"task": task, "episode": i, "cands": [{"flags": f, "fails": int(f > 0)} for f in flags]}
        scored = [ep("A", 10, 1, 1), ep("A", 11, 1, 0), ep("A", 12, 0, 0), ep("A", 13, 1, 1),
                  ep("B", 10, 0, 0), ep("B", 11, 1, 1)]
        calib = [ep("A", 0, 1, 0, 1), ep("A", 1, 0, 0, 1), ep("B", 0, 0, 0, 0, 1), ep("B", 1, 0, 0, 0, 1)]
        res = h._h5(calib, scored, grid=(1, 2), B=20, perms=9, seed=9, level=0.95, K=0.01, negligible=0.001)
        # A: u = 3/6, P(no clean among 1, 2) = 3/4, 2/4 -> mean(.75 - .5, .5 - .25) = .25
        # B: u = 2/8, P = 1/2, 1/2 -> mean(.5 - .25, .5 - .0625) = .34375
        self.assertEqual(res["u_hat"], {"A": 0.5, "B": 0.25})
        self.assertAlmostEqual(res["S"], (0.25 + 0.34375) / 2, places=12)
        self.assertAlmostEqual(res["per_N"][1], ((0.75 - 0.5) + (0.5 - 0.25)) / 2, places=12)

    def planted(self, spread, runs, **kw):
        out = []
        for s in range(runs):
            calib, sc, f, a = h5_data(spread, s, **kw)
            out.append(h.h5_primary(calib, sc, **h5_args(B=20, perms=1, seed=s))["S"])
        return out, f, a

    def closed_form(self, f, a, spread, grid, cal, cal_cands):
        s_true = bias = 0.0
        for ft, at in zip(f, a):
            u = ft * (1 - at)
            var_u = ((u - u * u * (1 + spread ** 2)) / cal_cands + (spread * u) ** 2) / cal
            for n in grid:
                s_true += ((u * (1 + spread)) ** n + (u * (1 - spread)) ** n) / 2 - u ** n
                bias += math.comb(n, 2) * u ** (n - 2) * var_u  # E[u_hat^N] - u^N, second order
        k = len(f) * len(grid)
        return s_true / k, bias / k

    def test_jensen_hidden_state_mixture_gives_positive_s(self):
        runs, grid = 30, (2, 4, 8, 16)
        for spread in (0.9, 0.0):
            got, f, a = self.planted(spread, runs)
            s_true, bias = self.closed_form(f, a, spread, grid, 200, 3)
            self.assertLessEqual(abs(st.fmean(got) - (s_true - bias)), 4 * st.stdev(got) / math.sqrt(runs))
            if spread:
                self.assertGreater(s_true, 0.02)
                self.assertGreater(st.fmean(got), 0.02)
            else:
                self.assertEqual(s_true, 0.0)  # independent draws: S = 0 up to the plug-in bias (downward)
                self.assertLessEqual(st.fmean(got), 4 * st.stdev(got) / math.sqrt(runs))

    def test_mixture_is_supported_independent_is_killed(self):
        calib, sc, _, _ = h5_data(0.9, 1)
        res = h.h5_primary(calib, sc, **h5_args())
        self.assertGreater(res["interval"][0], 0)
        self.assertLessEqual(res["p_up"], 0.05)
        self.assertEqual((res["decision"], res["conflict"]), ("supported", False))
        self.assertEqual(sorted(res["per_N"]), [2, 4, 8, 16])
        res = h.h5_primary(calib, sc, **h5_args(K=0.99))  # lo > 0 and hi < K: the registered kill bound wins
        self.assertEqual((res["decision"], res["conflict"]), ("killed", True))
        calib, sc, _, _ = h5_data(0.0, 1)
        res = h.h5_primary(calib, sc, **h5_args(K=0.02))
        self.assertLessEqual(res["interval"][0], 0)
        self.assertLess(res["interval"][1], 0.02)
        self.assertEqual(res["decision"], "killed")

    def test_uninformative_cases(self):
        ids = list(range(4))
        calib = h.planted_h5_episodes(ids, [0.0] * 4, [0.2] * 4, 0.0, 30, 3, 0, 1, "c", 0.0)
        sc = h.planted_h5_episodes(ids, [0.0] * 4, [0.2] * 4, 0.0, 30, 16, 10**4, 1, "s", 0.0)
        res = h.h5_primary(calib, sc, **h5_args())  # nothing ever fails: every u_t = 0
        self.assertIn("every u_t is 0 or 1", res["uninformative"])
        self.assertEqual(res["decision"], "uninformative")
        calib = h.planted_h5_episodes(ids, [0.05] * 4, [0.1] * 4, 0.0, 200, 3, 0, 1, "c", 0.0)
        sc = h.planted_h5_episodes(ids, [0.05] * 4, [0.1] * 4, 0.0, 30, 16, 10**4, 1, "s", 0.0)
        self.assertIn("u_t^N negligible at every grid N",
                      h.h5_primary(calib, sc, **h5_args(negligible=0.01))["uninformative"])
        self.assertNotIn("u_t^N negligible at every grid N",
                         h.h5_primary(calib, sc, **h5_args(negligible=0.0001))["uninformative"])

    def test_minima_are_counted_on_the_calibration_split(self):
        def ep(task, i, flags, fails):
            return {"task": task, "episode": i, "cands": [{"flags": flags, "fails": fails}]}
        _, sc, _, _ = h5_data(0.0, 1, tasks=2, scored=20)
        # exactly 400 passing and 200 failing candidates; 100 of the failing ones look clean (flags 0), so counting
        # by flags instead of by the oracle would give 500 "clean"
        calib = ([ep(0, i, 0, 0) for i in range(399)] + [ep(0, 1000 + i, 1, 1) for i in range(100)]
                 + [ep(0, 2000 + i, 0, 1) for i in range(100)] + [ep(1, 0, 0, 0)])
        res = h.h5_primary(calib, sc, **h5_args())
        self.assertEqual(res["counts"], {"clean": 400, "failure": 200})
        self.assertFalse(any("not reached" in r for r in res["uninformative"]))
        res = h.h5_primary(calib[:-1] + [ep(1, 0, 1, 1)], sc, **h5_args())  # 399 passing, 201 failing
        self.assertTrue(any("not reached" in r for r in res["uninformative"]))
        self.assertEqual(res["decision"], "uninformative")
        res = h.h5_primary(calib[1:], sc, **h5_args())  # 399 clean again, 200 failure
        self.assertTrue(any("not reached" in r for r in res["uninformative"]))
        res = h.h5_primary(calib[:399] + calib[400:], sc, **h5_args())  # 400 passing, 199 failing
        self.assertTrue(any("not reached" in r for r in res["uninformative"]))

    def test_description_gap_gap0_and_D_hand_computed(self):
        def ep(task, i, *cands):
            return {"task": task, "episode": i, "cands": [{"flags": fl, "fails": fa} for fl, fa in cands]}
        scored = [ep("A", 10, (1, 1), (0, 1)), ep("A", 11, (0, 1), (0, 0)), ep("A", 12, (0, 0), (0, 0)),
                  ep("A", 13, (1, 1), (1, 1))]
        calib = [ep("A", 0, (1, 1), (0, 1), (0, 1)), ep("A", 1, (0, 0), (0, 0), (1, 1))]
        # calibration: f = 4/6, a = 2/4, u = 2/6 = f (1 - a). gap0(N) = (1 - u^N) * (1/3) / (1/3 + 1/3)
        d = h.h5_description(calib, scored, (1, 2))
        self.assertAlmostEqual(d[1]["gap"], 1 / 4)
        self.assertAlmostEqual(d[2]["gap"], 2 / 4)
        self.assertAlmostEqual(d[1]["gap0"], (1 - 1 / 3) * 0.5)
        self.assertAlmostEqual(d[2]["gap0"], (1 - 1 / 9) * 0.5)
        self.assertAlmostEqual(d[1]["D"], 1 / 4 - 1 / 3)
        self.assertAlmostEqual(d[2]["D"], 1 / 2 - 4 / 9)
        self.assertAlmostEqual(d[1]["fail_given_clean"], 1 / 2)   # e2 selected fails, e3 does not
        self.assertAlmostEqual(d[2]["fail_given_clean"], 2 / 3)   # e1 and e2 fail, e3 does not; e4 has no clean one
        # f = 1 and a = 0: no clean candidate ever, denominator 0 -> gap0 = 0
        none = [ep("A", 0, (1, 1), (1, 1))]
        self.assertEqual(h.h5_description(none, [ep("A", 5, (1, 1), (1, 1))], (2,))[2]["gap0"], 0.0)

    def test_independent_draws_have_zero_D_and_the_gap_matches_its_closed_form(self):
        # independent draws: P(selected is reported clean and fails) = (1 - u^N) f a / ((1 - f) + f a), so D = 0
        runs, got = 30, []
        for s in range(runs):
            calib, sc, f, a = h5_data(0.0, 300 + s, cal=300, scored=150)
            d = h.h5_description(calib, sc, (2, 4, 8, 16))
            got.append(st.fmean(d[n]["D"] for n in d))
        self.assertLessEqual(abs(st.fmean(got)), 4 * st.stdev(got) / math.sqrt(runs))
        # hidden-state mixture moves it: gap and gap0 are different objects there (description, no claim)
        calib, sc, f, a = h5_data(0.9, 1)
        d = h.h5_description(calib, sc, (2, 4, 8, 16))
        self.assertTrue(all(0 <= d[n]["gap"] <= 1 for n in d))

    def test_draw_position_check(self):
        calib, sc, _, _ = h5_data(0.0, 1, tasks=4, scored=60, cands=8)
        ok = h.draw_position_check(sc, top=8, perms=99, seed=1)
        self.assertEqual(len(ok["rates"]), 8)
        self.assertGreater(ok["p"], 0.05)
        _, drifted, _, _ = h5_data(0.0, 1, tasks=4, scored=60, cands=8, drift=0.5)
        bad = h.draw_position_check(drifted, top=8, perms=99, seed=1)
        self.assertLessEqual(bad["p"], 0.01)
        self.assertGreater(bad["rates"][-1], bad["rates"][0] + 0.2)
        with self.assertRaises(ValueError):
            h.draw_position_check(sc, top=9, perms=9, seed=1)
        # hand check: one episode of 2 candidates [flagged, clean] -> rates [1, 0], statistic 0.5
        one = [{"task": 0, "episode": 0, "cands": [{"flags": 1, "fails": 1}, {"flags": 0, "fails": 0}]}]
        res = h.draw_position_check(one, top=2, perms=9, seed=1)
        self.assertEqual((res["rates"], res["stat"]), ([1.0, 0.0], 0.5))
        self.assertEqual(res["p"], 1.0)  # every order gives 0.5
        # three positions: rates [1, 0, 0], pooled 1/3, gaps 2/3, 1/3, 1/3 -> the statistic is the LARGEST gap, 2/3
        three = [{"task": 0, "episode": 0, "cands": [{"flags": f, "fails": f} for f in (1, 0, 0)]}]
        res = h.draw_position_check(three, top=3, perms=9, seed=1)
        self.assertEqual(res["rates"], [1.0, 0.0, 0.0])
        self.assertAlmostEqual(res["stat"], 2 / 3, places=12)
        self.assertEqual(res["p"], 1.0)  # every order of one flagged candidate in three gives 2/3
        # one position deviates (rate 1) while the other two sit at 1/2: significant by the largest gap (1/3)
        eps = [{"task": 0, "episode": i, "cands": [{"flags": f, "fails": f} for f in (1, i % 2, 1 - i % 2)]}
               for i in range(60)]
        res = h.draw_position_check(eps, top=3, perms=99, seed=1)
        self.assertAlmostEqual(res["stat"], 1 / 3, places=12)
        self.assertLessEqual(res["p"], 0.01)

    def test_position_check_null_calibration(self):
        runs, perms, alpha, hits = 150, 39, 0.1, 0
        pi = math.floor(alpha * (perms + 1) + 1e-9) / (perms + 1)
        for s in range(runs):
            _, sc, _, _ = h5_data(0.0, 700 + s, tasks=2, scored=20, cands=8)
            hits += h.draw_position_check(sc, top=8, perms=perms, seed=s)["p"] <= alpha + 1e-12
        self.at_most(hits, runs, pi)  # exchangeable draws: valid (discrete statistic, so conservative)

    def test_null_calibration_independent_draws(self):
        runs, perms, alpha = 150, 39, 0.1
        pi = math.floor(alpha * (perms + 1) + 1e-9) / (perms + 1)
        interval_hits = p_hits = 0
        for s in range(runs):
            calib, sc, _, _ = h5_data(0.0, 500 + s, tasks=8, cal=40, scored=25, cands=16, f0=0.4)
            res = h.h5_primary(calib, sc, **h5_args(B=100, perms=perms, seed=s, level=0.9, K=0.5))
            self.assertEqual(res["uninformative"], [])
            interval_hits += res["interval"][0] > 0   # one-sided tail of the 90% interval: 0.05
            p_hits += res["p_up"] <= alpha + 1e-12    # discrete statistic: conservative, at most pi
        self.at_most(interval_hits, runs, 0.05)
        self.at_most(p_hits, runs, pi)


class Arms(Exact):
    """run_arms with the real team.run_episode and a scripted model whose failures are planted."""

    class Planted(ScriptedAdopter):
        """Every work event fails (answer + 1) when the episode's common cause fires (probability c) or the agent's
        own draw is below f; draws are keyed by the episode seed, so the planted outcome is known in advance."""

        def __init__(self, f, c, seed):
            super().__init__(1.0, seed)
            self.f, self.c = f, c

        def turn(self, ctx):
            out = []
            for e in super().turn(ctx):
                if e["type"] == "work" and (random.Random(f"common:{self.seed}").random() < self.c
                                            or random.Random(f"fail:{self.seed}:{ctx.agent}").random() < self.f):
                    e = dict(e, answer=e["answer"] + 1)
                out.append(e)
            return out

    @staticmethod
    def taskset(n, t):
        return {"split": "r5", "seed": t, "n_agents": n, "name_rule": "{agent}-{task}",
                "tasks": [{"id": f"t{t}x{i}", "check": f"sum {i} {i}", "expect": 2 * i} for i in range(n)]}

    def play(self, arms, sizes, tasks, reruns, f, c, seed=1, tag="arms"):
        seen = []

        def kw(arm, n, t, r, ep_seed):
            seen.append((arm, n, t, r, ep_seed))
            return {"adopter": self.Planted(f, c, ep_seed)}
        return h.run_arms(team.run_episode, self.taskset, arms=arms, sizes=sizes, task_ids=tasks, reruns=reruns,
                          practice="A", seed=seed, tag=tag, episode_kw=kw), seen

    def test_rows_are_per_agent_and_match_the_planted_draws(self):
        out, seen = self.play(["none", "code"], [2, 4, 8], [0, 1], 3, 0.3, 0.2)
        self.assertEqual(set(out), {"none", "code"})
        for arm, rows in out.items():
            self.assertEqual(len(rows), 2 * 3 * (2 + 4 + 8))
            self.assertEqual(h.episode_counts(rows).keys(), {(n, t, r) for n in (2, 4, 8) for t in (0, 1) for r in range(3)})
        for arm, n, t, r, ep_seed in seen:
            self.assertEqual(ep_seed, task_seed(f"arms:{arm}:{n}", 1, t * 10**6 + r))
            common = random.Random(f"common:{ep_seed}").random() < 0.2
            want = [int(not common and not random.Random(f"fail:{ep_seed}:a{a}").random() < 0.3) for a in range(n)]
            got = [r_["pass"] for r_ in out[arm] if (r_["n"], r_["task"], r_["rerun"]) == (n, t, r)]
            if arm == "none":
                self.assertEqual(got, want)
            else:  # the code arm refuses duplicate claims: an agent without accepted work cannot pass
                self.assertTrue(all(g <= w for g, w in zip(got, want)))
        self.assertTrue(all(r["seed"] == 1 and r["arm"] in out for rows in out.values() for r in rows))

    def test_pooled_pass_rate_is_the_planted_rate(self):
        out, _ = self.play(["none"], [4], list(range(20)), 10, 0.3, 0.25)
        eps = [x / 4 for x in h.episode_counts(out["none"]).values()]
        want = (1 - 0.25) * (1 - 0.3)
        self.assertLessEqual(abs(st.fmean(eps) - want), 4 * st.stdev(eps) / math.sqrt(len(eps)))

    def test_pipeline_into_h2_and_h1(self):
        fit, _ = self.play(["none"], [2, 4], list(range(12)), 10, 0.3, 0.3, seed=1)
        held, _ = self.play(["none"], [8], list(range(100, 112)), 10, 0.3, 0.3, seed=2)
        res = h.h2_primary(fit["none"], held["none"], **h2_args(B=40))
        self.assertEqual(res["coverage"]["m"], 12)
        self.assertIn(res["decision"], ("supported", "killed", "inconclusive", "uninformative"))
        both, _ = self.play(["none", "code"], [4, 8], list(range(6)), 4, 0.3, 0.0)
        rows = team_and_nominal = h.team_rows(both["code"]) + h.nominal_rows(both["none"])
        self.assertEqual(len(rows), 2 * 2 * 6 * 4)
        out = h.h1_primary(rows, **h1_args(B=20, perms=9, edge=0.0))
        self.assertEqual(sorted(out["sizes"]), [4, 8])

    def test_agent_passes_counts_only_integer_correct_accepted_work(self):
        ts = self.taskset(3, 0)
        ev = lambda agent, task, answer, **kw: {"agent": agent, "action": "work", "task": task, "answer": answer, **kw}
        rec = {"valid": True, "status": "ok", "n_agents": 3, "log": [
            ev("a0", "t0x0", 0), ev("a1", "t0x1", 2.0), ev("a2", "t0x2", 4, rejected=True)]}
        self.assertEqual(h.agent_passes(rec, ts), [1, 0, 0])
        rec["log"] = [ev("a0", "t0x0", False), ev("a1", "nope", 2), ev("a2", "t0x2", 4)]  # False == 0 is not an integer
        self.assertEqual(h.agent_passes(rec, ts), [0, 0, 1])
        for bad in (dict(rec, valid=False), dict(rec, status="void:invalid_log"), dict(rec, n_agents=4), None):
            with self.assertRaises(ValueError):
                h.agent_passes(bad, ts)

    def test_nominal_and_team_rows_from_agent_rows(self):
        row = lambda task, agent, y, **kw: dict({"n": 2, "task": task, "rerun": 0, "agent": agent, "pass": y}, **kw)
        data = [row(0, 0, 0), row(0, 1, 1), row(1, 0, 0), row(1, 1, 0),
                row(2, 0, 1, answer="x"), row(2, 1, 0, answer="y"), row(3, 0, 0, answer="x"), row(3, 1, 0, answer="x")]
        self.assertEqual([r["pass"] for r in h.nominal_rows(data)], [1, 0, 1, 0])
        self.assertEqual([r["pass"] for r in h.team_rows(data)], [1, 0, 1, 0])
        self.assertEqual(h.nominal_rows(data)[0], {"arm": "nominal", "n": 2, "task": 0, "episode": 0, "pass": 1})
        # the nominal group de-duplicates identical answers: the first row's verdict stands for "x"
        dup = [row(0, 0, 0, answer="x"), row(0, 1, 1, answer="x")]
        self.assertEqual(h.nominal_rows(dup)[0]["pass"], 0)
        self.assertEqual(h.team_rows(dup)[0]["pass"], 1)

    def test_run_arms_refusals(self):
        ok = dict(run_episode=team.run_episode, taskset_for=self.taskset, arms=["none"], sizes=[2], task_ids=[0],
                  reruns=1, practice="A", seed=1, tag="x", episode_kw=lambda *a: {})
        h.run_arms(**ok)
        for key, bad in (("arms", []), ("arms", "none"), ("reruns", 0), ("reruns", True), ("seed", True), ("tag", ""),
                         ("sizes", [1]), ("episode_kw", None), ("run_episode", None), ("taskset_for", 3)):
            with self.subTest(key=key), self.assertRaises(ValueError):
                h.run_arms(**dict(ok, **{key: bad}))
        with self.assertRaises(TypeError):
            h.run_arms(**{k: v for k, v in ok.items() if k != "episode_kw"})
        with self.assertRaises(NotImplementedError):  # run_episode itself refuses a model backend
            h.run_arms(**dict(ok, episode_kw=lambda *a: {"backend": object()}))


class Holm(unittest.TestCase):
    def test_family_size_stays_three(self):
        self.assertEqual(h.holm_family({"H1": 0.02, "H3": 0.02}, 0.05), {"H1": False, "H3": False})  # 0.02 > 0.05/3
        self.assertEqual(h.holm_family({"H1": 0.001, "H3": 0.02, "H5": 0.03}, 0.05),
                         {"H1": True, "H3": True, "H5": True})
        self.assertEqual(h.holm_family({"H5": 0.01}, 0.05), {"H5": True})
        self.assertEqual(h.holm_family({"H5": 0.02}, 0.05), {"H5": False})
        self.assertEqual(h.holm_family({"H1": 0.0167, "H3": 0.5, "H5": 0.0166}, 0.05),
                         {"H1": True, "H3": False, "H5": True})
        self.assertEqual(h.holm_family({"H1": 0.03, "H3": 0.01, "H5": 0.2}, 0.05),
                         {"H1": False, "H3": True, "H5": False})  # step-down stops at the first miss


if __name__ == "__main__":
    unittest.main()
