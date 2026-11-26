"""Tests for lab/r6_stage_a.py (R6 Stage A): oracles, scripted agents, planted-value recovery, nulls, scorecards, refusals.

Tolerances are derived, never tuned:
- H2 (q, c): the likelihood-ratio region, 2 (ll_hat - ll_planted) <= -2 ln(alpha) (chi-squared, 2 df, closed form).
- H3, H5: the harness's own bootstrap interval; the count of runs that recover is compared with the nominal level
  by the exact binomial lower tail at FALSE_ALARM, never by a hand-picked count.
- Nulls: the count of runs whose interval lies wholly above 0 against the one-sided tail of the nominal level, by the
  exact binomial upper tail at FALSE_ALARM.
"""
import itertools
import math
import random
import statistics as st
import unittest
from statistics import NormalDist
from unittest import mock

from lab import r5_perf_harness as h
from lab import r6_predicates as pr
from lab import r6_scorecard as sc
from lab import r6_stage_a as a

FALSE_ALARM = 1e-3
# two-sided normal quantile at FALSE_ALARM: the z of every 'mean within z standard errors' check
Z = NormalDist().inv_cdf(1 - FALSE_ALARM / 2)


def _pmf(i, m, p):  # log space, so a large m cannot overflow
    if p in (0, 1):
        return float(i == (m if p else 0))
    return math.exp(math.lgamma(m + 1) - math.lgamma(i + 1) - math.lgamma(m - i + 1) + i * math.log(p) + (m - i) * math.log1p(-p))


def tail_ge(k, m, p):
    return math.fsum(_pmf(i, m, p) for i in range(k, m + 1))


def tail_le(k, m, p):
    return math.fsum(_pmf(i, m, p) for i in range(0, k + 1))


class Exact(unittest.TestCase):
    def at_most(self, hits, runs, pi):
        """hits is not significantly above pi."""
        self.assertGreaterEqual(tail_ge(hits, runs, pi), FALSE_ALARM, f"{hits}/{runs} vs {pi}")

    def at_least(self, hits, runs, pi):
        """hits is not significantly below pi."""
        self.assertGreaterEqual(tail_le(hits, runs, pi), FALSE_ALARM, f"{hits}/{runs} vs {pi}")

    def mean_within(self, xs, planted, label=""):
        """The mean of the per-seed estimates is the planted value within Z standard errors (SE = SD / sqrt(seeds))."""
        mu, se = st.fmean(xs), st.stdev(xs) / math.sqrt(len(xs))
        self.assertLessEqual(abs(mu - planted), Z * se, f"{label}: mean {mu} vs planted {planted}, SE {se}")

    def width_ok(self, intervals, estimates, level):
        """A calibrated interval has half-width about z_level times the SD of the estimator across seeds. The mean width
        may exceed 2 z_level SD only by the relative sampling error of an SD from m seeds, Z / sqrt(2 (m - 1))."""
        m, zl = len(estimates), NormalDist().inv_cdf(1 - (1 - level) / 2)
        wide = st.fmean(hi - lo for lo, hi in intervals)
        self.assertLessEqual(wide, 2 * zl * st.stdev(estimates) * (1 + Z / math.sqrt(2 * (m - 1))), f"mean width {wide}")

    def excludes(self, intervals, estimates, planted, side):
        """The number of intervals wholly on one side of 0 is not below the power the planted value implies when the
        estimate is normal with the observed SD and the interval has its observed mean half-width."""
        sd, half = st.stdev(estimates), st.fmean((hi - lo) / 2 for lo, hi in intervals)
        p0 = NormalDist().cdf((abs(planted) - half) / sd)
        k = sum(lo > 0 if side > 0 else hi < 0 for lo, hi in intervals)
        self.at_least(k, len(intervals), p0)

    def cp(self, k, m, level):
        """Clopper-Pearson by bisection on this file's own exact tails (independent of the module under test)."""
        al = (1 - level) / 2

        def root(f):
            lo, hi = 0.0, 1.0
            for _ in range(80):
                mid = (lo + hi) / 2
                lo, hi = (lo, mid) if f(mid) >= al else (mid, hi)
            return (lo + hi) / 2
        return (0.0 if k == 0 else root(lambda p: tail_ge(k, m, p)),
                1.0 if k == m else 1 - root(lambda r: tail_ge(m - k, m, r)))


def design(**kw):
    d = dict(n_vars=3, tasks=6, reruns=10, h5_tasks=6, cal_reruns=14, h5_reruns=20, difficulty={"F2": 3, "F3": 3, "F5": 3},
             families=("F2", "F3", "F5"), h35_family="F5", yes_rate=0.5, false_rate=0.5, step_limit=2000,
             total_steps=10**6, rt_lemmas=120, audit_pairs=60, faithful_rate=0.4)
    d.update(kw)
    return d


def plant(**kw):
    p = dict(pass_p={3: 0.7}, c=0.3, conf_bias={"team": 0.1, "solo": -0.1}, ask_effect=0.1, false_clean=0.1, f=0.5,
             spread=0.9,
             rt=dict(accept_false=0.6, reject_true=0.1, find={"treatment": 0.8, "control": 0.2},
                     bogus={"treatment": 0.3, "control": 0.05}),
             audit=dict(detect=0.8, false_alarm=0.1, locate=0.7))
    p.update(kw)
    return p


def est(**kw):
    e = dict(level=0.95, alpha=0.05, alpha_recover=0.001, grid_steps=50, B=60, perms=49, edge=0.02, K=0.01,
             negligible=0.001, max_unparseable=0.1, rt_min_accepted=5)
    e.update(kw)
    return e


WEIGHTS = {k: 0.2 for k in sc.CRITERIA}


def card(**kw):
    c = dict(weights=dict(WEIGHTS), rubric={k: 3 for k in sc.CRITERIA}, briefing_keywords=["zzbriefing"],
             overclaim_patterns=["proof of P vs NP"], gate_plant=dict(rate=0.1, gate="G4"))
    c.update(kw)
    return c


# ------------------------------------------------------------------------------ circuits, M1, oracles ----

class Circuits(Exact):
    def test_synthesizer_is_minimum_and_correct_for_all_256_functions_at_n3(self):
        sizes = a._m1_sizes(3)
        self.assertEqual(len(sizes), 256)
        for f in range(256):
            c = a.synth(3, f)
            self.assertEqual(a.circuit_table(3, c), f)
            self.assertEqual(len(c["gates"]), sizes[f])

    def test_synthesizer_for_smaller_n_and_refusal_above_3(self):
        for n in (1, 2):
            for f in range(1 << (1 << n)):
                self.assertEqual(a.circuit_table(n, a.synth(n, f)), f)
        with self.assertRaises(ValueError):
            a.synth(4, 1)

    def test_circuit_table_at_n4_by_hand(self):
        and4 = {"gates": [[8, 0, 1], [8, 2, 3], [8, 4, 5]], "out": 6, "neg": False}  # (x0 x1)(x2 x3)
        self.assertEqual(a.circuit_table(4, and4), 1 << 15)
        self.assertEqual(a.circuit_table(4, dict(and4, neg=True)), (1 << 16) - 1 - (1 << 15))

    def test_circuit_table_refuses_malformed(self):
        ok = {"gates": [[8, 0, 1]], "out": 2, "neg": False}
        a.circuit_table(2, ok)
        for bad in (None, {}, dict(ok, out=3), dict(ok, out=-1), dict(ok, neg=1), dict(ok, gates=[[16, 0, 1]]),
                    dict(ok, gates=[[8, 0, 2]]), dict(ok, gates=[[8, 0]]), dict(ok, gates=[[8.0, 0, 1]]),
                    dict(ok, gates=[[True, 0, 1]]), dict(ok, gates="x"), dict(ok, extra=1)):
            with self.assertRaises(ValueError, msg=repr(bad)):
                a.circuit_table(2, bad)


class Oracles(Exact):
    def tasks(self):
        yield from a.gen_circuit_tasks("F2", 3, 3, 6, 5, "o")
        yield from a.gen_circuit_tasks("F3", 3, 3, 8, 5, "o", yes_rate=0.5)
        yield from a.gen_circuit_tasks("F3", 3, 1, 4, 5, "o", yes_rate=0.5)
        yield from a.gen_lemma_tasks(3, 12, 0.5, 5, "o", 2000, 10**6)

    def test_right_claims_pass_and_wrong_claims_fail_for_every_mode(self):
        for t in self.tasks():
            self.assertEqual(a.ORACLES[t["family"]](t, a.right_claim(t)), 1, t)
            for k in range(8):  # both modes of wrong_claim
                self.assertEqual(a.ORACLES[t["family"]](t, a.wrong_claim(t, random.Random(k))), 0, (t, k))

    def test_f2_oracle(self):
        t = a.gen_circuit_tasks("F2", 3, 3, 1, 1, "x")[0]
        c = a.right_claim(t)
        self.assertEqual(a.oracle_f2(t, c), 1)
        longer = {"gates": c["circuit"]["gates"] + [[6, 0, 0]], "out": c["circuit"]["out"], "neg": c["circuit"]["neg"]}
        self.assertEqual(a.oracle_f2(t, {"circuit": longer, "size": 4}), 0)  # correct circuit, not the minimum
        self.assertEqual(a.oracle_f2(t, dict(c, size=c["size"] + 1)), 0)
        self.assertEqual(a.oracle_f2(t, dict(c, size=float(c["size"]))), 0)
        self.assertEqual(a.oracle_f2(t, {"circuit": c["circuit"]}), 0)
        self.assertEqual(a.oracle_f2(t, None), 0)

    def test_f3_oracle(self):
        yes = {"family": "F3", "n": 3, "f": a.gen_circuit_tasks("F2", 3, 2, 1, 1, "x")[0]["f"], "s": 2}
        no = dict(yes, s=1)
        c = a.right_claim(yes)
        self.assertEqual(a.oracle_f3(yes, c), 1)
        self.assertEqual(a.oracle_f3(yes, {"answer": "yes"}), 0)  # a yes needs its circuit
        self.assertEqual(a.oracle_f3(yes, {"answer": "no"}), 0)
        self.assertEqual(a.oracle_f3(no, {"answer": "no"}), 1)
        self.assertEqual(a.oracle_f3(no, c), 0)  # the circuit has 2 gates, s is 1: truth is no
        self.assertEqual(a.oracle_f3(yes, {"answer": "maybe"}), 0)
        self.assertEqual(a.oracle_f3(yes, {"answer": True}), 0)

    def test_f3_yes_needs_at_most_s_gates_and_correct_function(self):
        t = {"family": "F3", "n": 3, "f": a.gen_circuit_tasks("F2", 3, 2, 1, 1, "x")[0]["f"], "s": 3}
        c = a.right_claim(t)  # truth is yes (2 <= 3)
        self.assertEqual(a.oracle_f3(t, c), 1)
        self.assertEqual(a.oracle_f3(t, {"answer": "yes", "circuit": dict(c["circuit"], neg=not c["circuit"]["neg"])}), 0)
        pad = lambda circ: dict(circ, gates=circ["gates"] + [[6, 0, 0]])  # noqa: E731  one unused extra gate
        self.assertEqual(a.oracle_f3(t, {"answer": "yes", "circuit": pad(c["circuit"])}), 1)  # 3 gates, s = 3: within budget
        tight = dict(t, s=2)
        self.assertEqual(a.oracle_f3(tight, {"answer": "yes", "circuit": c["circuit"]}), 1)
        self.assertEqual(a.oracle_f3(tight, {"answer": "yes", "circuit": pad(c["circuit"])}), 0)  # 3 gates over s = 2

    def test_f5_oracle(self):
        false_t = next(t for t in a.gen_lemma_tasks(2, 30, 1.0, 1, "x", 2000, 10**6))
        true_t = next(t for t in a.gen_lemma_tasks(2, 30, 0.0, 1, "x", 2000, 10**6))
        self.assertFalse(false_t["truth"])
        self.assertTrue(true_t["truth"])
        self.assertEqual(a.oracle_f5(false_t, a.right_claim(false_t)), 1)
        self.assertEqual(a.oracle_f5(true_t, a.right_claim(true_t)), 1)
        cx = false_t["counterexample"]
        self.assertEqual(a.oracle_f5(false_t, {"label": False, "counterexample": dict(cx, x=cx["x"] + 4)}), 0)  # out of domain
        self.assertEqual(a.oracle_f5(false_t, {"label": False, "counterexample": {"x": cx["x"]}}), 0)
        self.assertEqual(a.oracle_f5(false_t, {"label": False, "counterexample": None}), 0)
        self.assertEqual(a.oracle_f5(false_t, {"label": 0, "counterexample": cx}), 0)  # an int is not the label False
        self.assertEqual(a.oracle_f5(true_t, {"label": False, "counterexample": {"x": 0, "y": 0}}), 0)
        self.assertEqual(a.oracle_f5(true_t, {"label": True}), 1)
        self.assertEqual(a.oracle_f5(false_t, {"label": True, "counterexample": None}), 0)

    def test_f5_counterexample_must_really_falsify(self):
        t = {"family": "F5", "width": 2, "source": "popcount(x ^ y) <= 1", "step_limit": 100, "total_steps": 10**5}
        t["truth"], t["counterexample"] = a.lemma_truth(t["source"], 2, 100, 10**5)
        self.assertFalse(t["truth"])
        self.assertEqual(t["counterexample"], {"x": 0, "y": 3})
        self.assertEqual(a.oracle_f5(t, {"label": False, "counterexample": {"x": 0, "y": 3}}), 1)
        self.assertEqual(a.oracle_f5(t, {"label": False, "counterexample": {"x": 1, "y": 2}}), 1)  # any falsifying env
        self.assertEqual(a.oracle_f5(t, {"label": False, "counterexample": {"x": 0, "y": 0}}), 0)  # the lemma holds there

    def test_f5_step_limit_refusal_is_a_fail_not_a_pass(self):
        t = a.gen_lemma_tasks(2, 1, 0.0, 1, "x", 2000, 10**6)[0]
        starved = dict(t, step_limit=1)
        self.assertEqual(a.oracle_f5(starved, {"label": True}), 1)  # a true label never runs the predicate
        f = a.gen_lemma_tasks(2, 1, 1.0, 1, "x", 2000, 10**6)[0]
        self.assertEqual(a.oracle_f5(dict(f, step_limit=1), a.right_claim(f)), 0)  # the counterexample cannot be verified

    def test_gen_lemma_tasks_planted_rate_and_truth_from_the_checker(self):
        for rate, want in ((0.0, True), (1.0, False)):
            for t in a.gen_lemma_tasks(3, 15, rate, 2, "g", 2000, 10**6):
                self.assertEqual(t["truth"], want)
                dom = [{"x": x, "y": y} for x in range(8) for y in range(8)]
                self.assertEqual(pr.check_lemma(pr.parse(t["source"]), iter(dom), 2000, 10**6), t["counterexample"])
        ts = a.gen_lemma_tasks(3, 200, 0.3, 2, "g", 2000, 10**6)
        k = sum(not t["truth"] for t in ts)
        self.assertGreaterEqual(tail_ge(k, 200, 0.3), FALSE_ALARM)
        self.assertGreaterEqual(tail_le(k, 200, 0.3), FALSE_ALARM)

    def test_gen_circuit_tasks_truth_is_the_m1_table(self):
        for t in a.gen_circuit_tasks("F3", 3, 3, 30, 1, "m", yes_rate=0.5):
            self.assertEqual(a._m1_sizes(3)[t["f"]], 3)
            self.assertIn(t["s"], (2, 3))
        yes = a.gen_circuit_tasks("F3", 3, 3, 20, 1, "m", yes_rate=1.0)
        no = a.gen_circuit_tasks("F3", 3, 3, 20, 1, "m", yes_rate=0.0)
        self.assertTrue(all(t["s"] == 3 for t in yes) and all(t["s"] == 2 for t in no))

    def test_generator_refusals(self):
        for call in (lambda: a.gen_circuit_tasks("F5", 3, 3, 1, 1, "x"),
                     lambda: a.gen_circuit_tasks("F3", 3, 3, 1, 1, "x"),          # yes_rate missing
                     lambda: a.gen_circuit_tasks("F2", 3, 3, 1, 1, "x", yes_rate=0.5),
                     lambda: a.gen_circuit_tasks("F2", 3, 6, 1, 1, "x"),          # no function of 3 inputs needs 6 gates
                     lambda: a.gen_circuit_tasks("F3", 3, 0, 1, 1, "x", yes_rate=0.5),
                     lambda: a.gen_circuit_tasks("F2", 5, 3, 1, 1, "x"),
                     lambda: a.gen_circuit_tasks("F2", True, 3, 1, 1, "x"),
                     lambda: a.gen_lemma_tasks(0, 1, 0.5, 1, "x", 100, 100),
                     lambda: a.gen_lemma_tasks(2, 1, 1.5, 1, "x", 100, 100),
                     lambda: a.gen_lemma_tasks(2, 0, 0.5, 1, "x", 100, 100),
                     lambda: a.gen_lemma_tasks(2, 1, 0.5, 1, "x", 0, 100)):    # step limit 0: every run is refused
            with self.assertRaises((ValueError, pr.PredicateRefused)):
                call()


# ----------------------------------------------------------------------------------- scripted agents ----

class Agents(Exact):
    def test_rows_come_from_the_log_and_equal_the_oracle(self):
        tasks = a.make_tasks("F3", design(), 1, "t", 0)
        rows, ag = a.play(tasks, [2, 4], 3, 5, "ag", lambda s, t: 0.4)
        self.assertEqual(len(rows), 6 * 3 * 6)
        self.assertEqual(h.episode_counts(rows).keys(), {(n, t, r) for n in (2, 4) for t in tasks for r in range(3)})
        for r in rows:
            rec = ag[(r["n"], r["task"], r["rerun"])].rec[f"a{r['agent']}"]
            self.assertEqual(r["pass"], a.ORACLES["F3"](tasks[r["task"]], rec["claim"]))
            self.assertEqual(r["pass"], 1 - rec["planted_fail"])  # a wrong claim always fails its oracle

    def test_a_row_that_disagrees_with_the_oracle_is_refused(self):
        tasks = a.make_tasks("F2", design(), 1, "t", 0)
        real = h.agent_passes
        with mock.patch.object(h, "agent_passes", lambda rec, ts: [1 - p for p in real(rec, ts)]):
            with self.assertRaises(ValueError):
                a.play(tasks, [2], 1, 5, "ag", lambda s, t: 0.4)

    def test_planted_failure_probability_is_used_not_a_constant(self):
        tasks = a.make_tasks("F2", design(), 1, "t", 0)
        for fail_p in (0.0, 1.0):
            rows, _ = a.play(tasks, [4], 2, 5, "ag", lambda s, t: fail_p)
            self.assertEqual({r["pass"] for r in rows}, {int(fail_p == 0.0)})

    def test_flags_only_on_failing_candidates_with_the_planted_miss_rate(self):
        tasks = a.make_tasks("F2", design(), 1, "t", 0)
        rows, ag = a.play(tasks, [16], 12, 5, "fl", lambda s, t: 0.5, flag_miss=0.25)
        recs = [x.rec[k] for x in ag.values() for k in x.rec]
        self.assertTrue(all(r["flag"] == 0 for r in recs if r["pass"]))
        failing = [r for r in recs if not r["pass"]]
        flagged = sum(r["flag"] for r in failing)
        self.assertGreaterEqual(tail_ge(flagged, len(failing), 0.75), FALSE_ALARM)
        self.assertGreaterEqual(tail_le(flagged, len(failing), 0.75), FALSE_ALARM)

    def test_every_row_fails_when_the_oracle_says_zero_whatever_the_planted_draws(self):
        tasks = a.make_tasks("F2", design(), 1, "t", 0)
        with mock.patch.dict(a.ORACLES, {"F2": lambda task, claim: 0}):
            rows, ag = a.play(tasks, [2, 4], 2, 5, "ag", lambda s, t: 0.0)  # nobody is planted to fail
            self.assertEqual({r["pass"] for r in rows}, {0})
            self.assertEqual({v["pass"] for x in ag.values() for v in x.rec.values()}, {0})
            self.assertEqual({r["pass"] for r in a.play_solo(tasks, 2, 5, "so", lambda s, t: 0.0, (0.7, 0.0))}, {0})
        with mock.patch.dict(a.ORACLES, {"F2": lambda task, claim: 1}):
            rows, _ = a.play(tasks, [2], 1, 5, "ag", lambda s, t: 1.0)  # everybody is planted to fail
            self.assertEqual({r["pass"] for r in rows}, {1})

    def test_episode_seeds_follow_the_run_arms_formula(self):
        tasks = a.make_tasks("F2", design(tasks=2), 1, "t", 0)
        _, ag = a.play(tasks, [2], 2, 7, "tg", lambda s, t: 0.5)
        for (n, t, r), agent in ag.items():
            self.assertEqual(agent.seed, a.task_seed(f"tg:none:{n}", 7, t * 10**6 + r))
        with mock.patch.object(a.team, "run_episode", wraps=a.team.run_episode) as m:
            a.play_solo(tasks, 2, 7, "tg", lambda s, t: 0.5, (0.5, 0.0))
        seeds = [c.kwargs["seed"] for c in m.call_args_list]
        self.assertEqual(seeds, [a.task_seed("tg:none:1", 7, t * 10**6 + r) for t in tasks for r in range(2)])

    def test_solo_arm_runs_through_run_episode_with_the_run_arms_seed_rule(self):
        tasks = a.make_tasks("F2", design(), 1, "t", 0)
        rows = a.play_solo(tasks, 3, 5, "so", lambda s, t: 0.0, (0.7, 0.0))
        self.assertEqual({(r["n"], r["pass"]) for r in rows}, {(1, 1)})
        self.assertTrue(all(0.6 <= r["conf"] <= 0.8 for r in rows))
        self.assertEqual(len(rows), 6 * 3)


# -------------------------------------------------------------------------------------- derived tolerances ----

class Tolerances(Exact):
    def exact_counts(self, q, c, episodes=4000):
        return {n: [round(episodes * x) for x in h.pmf(n, q, c)] for n in (2, 4)}

    def test_lr_region_contains_the_truth_and_excludes_far_values(self):
        counts = self.exact_counts(0.3, 0.3)
        fit = h.fit_common_cause(counts)
        self.assertAlmostEqual(fit["q"], 0.3, delta=0.01)
        self.assertAlmostEqual(fit["c"], 0.3, delta=0.01)
        ok, delta, thr, qi, ci = a.lr_region(counts, 0.3, 0.3, 0.001, fit, 50)
        self.assertTrue(ok)
        self.assertAlmostEqual(thr, -math.log(0.001), places=12)
        self.assertTrue(qi[0] <= 0.3 <= qi[1] and ci[0] <= 0.3 <= ci[1])
        for q, c in ((0.3, 0.0), (0.3, 0.6), (0.6, 0.3), (0.1, 0.3)):
            self.assertFalse(a.lr_region(counts, q, c, 0.001, fit, 50)[0], (q, c))

    def test_threshold_is_minus_ln_alpha(self):
        counts = self.exact_counts(0.3, 0.3)
        fit = h.fit_common_cause(counts)
        for alpha in (0.05, 0.001):
            self.assertAlmostEqual(a.lr_region(counts, 0.3, 0.3, alpha, fit, 50)[2], -math.log(alpha), places=12)

    def test_lr_region_rejects_a_point_just_outside_and_keeps_one_just_inside(self):
        counts = self.exact_counts(0.3, 0.3, episodes=400)
        fit = h.fit_common_cause(counts)
        _, _, thr, _, _ = a.lr_region(counts, 0.3, 0.3, 0.05, fit, 50)
        edge = None
        for i in range(1, 400):
            c = 0.3 + i / 1000
            ok, delta = a.lr_region(counts, 0.3, c, 0.05, fit, 50)[:2]
            if not ok:
                edge = (c, delta)
                break
        self.assertIsNotNone(edge)
        self.assertGreater(edge[1], thr)
        self.assertLess(a.lr_region(counts, 0.3, edge[0] - 0.001, 0.05, fit, 50)[1], thr + 0.05)

    def test_clopper_pearson_known_values_and_coverage_definition(self):
        lo, hi = a.clopper_pearson(5, 20, 0.95)
        self.assertAlmostEqual(lo, 0.0865714, places=5)
        self.assertAlmostEqual(hi, 0.4910459, places=5)
        self.assertEqual(a.clopper_pearson(0, 20, 0.95)[0], 0.0)
        self.assertEqual(a.clopper_pearson(20, 20, 0.95)[1], 1.0)
        self.assertAlmostEqual(tail_ge(5, 20, lo), 0.025, places=6)
        self.assertAlmostEqual(tail_le(5, 20, hi), 0.025, places=6)

    def test_h5_planted_S_closed_form(self):
        self.assertEqual(a.h5_planted_S(0.4, 0.5, 0.0), 0.0)
        u = 0.4 * 0.5
        want = sum(0.5 * (u * 1.5) ** n + 0.5 * (u * 0.5) ** n - u ** n for n in (2, 4, 8, 16)) / 4
        self.assertAlmostEqual(a.h5_planted_S(0.4, 0.5, 0.5), want, places=15)
        self.assertGreater(a.h5_planted_S(0.4, 0.5, 0.5), a.h5_planted_S(0.4, 0.5, 0.25))  # more shared state, larger S
        self.assertEqual(a.h5_planted_S(0.4, 1.0, 0.5), 0.0)  # nothing is ever flagged: u = 0


# --------------------------------------------------------------------------------------- recovery ----

_CACHE = {}


def cached(key, fn):
    if key not in _CACHE:
        _CACHE[key] = fn()
    return _CACHE[key]


PERMS = 499  # permutations in the recovery runs, so their nulls can be compared with the closed forms


class Recovery(Exact):
    def test_h2_recovers_planted_q_and_c_on_each_family(self):
        seeds = range(1, 6)
        for fam in ("F2", "F3", "F5"):
            runs = [cached(("h2", fam, s), lambda s=s, fam=fam: a.run_h2(fam, s, design(), plant(), est())) for s in seeds]
            rec = sum(r["recovered"] for r in runs)
            for r in runs:
                self.assertEqual(r["planted"], {"q": 1 - 0.7, "c": 0.3})
                self.assertEqual(r["recovered"], r["delta"] <= r["threshold"])
                if r["recovered"]:
                    self.assertTrue(a.in_interval(0.3, r["interval"]["c"]) and a.in_interval(0.3, r["interval"]["q"]))
                # the pooled pass rate is the planted (1 - c)(1 - q), within z standard errors of the episode means
                eps = [x / n for (n, _, _), x in h.episode_counts(r["runs"][0][1]).items()]
                mean = sum(eps) / len(eps)
                se = math.sqrt(sum((e - mean) ** 2 for e in eps) / (len(eps) - 1) / len(eps))
                self.assertLessEqual(abs(mean - 0.7 * 0.7), Z * se, (fam, r))
            self.at_least(rec, len(seeds), 1 - 0.001)
            # the decision under the planted model: the exact coverage test (size <= alpha) does not reject, and the
            # forecast is never wholly worse than the independent comparator (one tail of the 95% interval: 0.025)
            self.at_least(sum(r["harness"]["coverage"]["p"] > 0.05 for r in runs), len(runs), 1 - 0.05)
            self.at_most(sum(r["decision"] == "killed" for r in runs), len(runs), 0.025)
            # across seeds the mean estimate is the planted value (z and the standard error are derived, see Exact)
            self.mean_within([r["estimate"]["q"] for r in runs], 0.3, f"{fam} q")
            self.mean_within([r["estimate"]["c"] for r in runs], 0.3, f"{fam} c")
            # the reported q and c intervals are the likelihood-ratio region: no wider than the region of the exact
            # (expected) counts for the same number of episodes, up to the grid step and the sampling spread of widths
            counts = {n: [design()["tasks"] * design()["reruns"] * x for x in h.pmf(n, 0.3, 0.3)] for n in (2, 4)}
            for key, idx in (("q", 3), ("c", 4)):
                pop = a.lr_region(counts, 0.3, 0.3, 0.001, {"q": 0.3, "c": 0.3}, 50)[idx]
                widths = [r["interval"][key][1] - r["interval"][key][0] for r in runs]
                self.assertLessEqual(sum(widths) / len(widths), pop[1] - pop[0] + Z * st.stdev(widths) / math.sqrt(len(widths))
                                     + 2 / 50, (fam, key))
                self.assertGreater(min(widths), 0.0)
                self.assertTrue(all(w < 1 for w in widths))

    def test_h2_does_not_recover_a_wrong_planted_value(self):
        r = cached(("h2", "F2", 1), lambda: a.run_h2("F2", 1, design(), plant(), est()))
        fit = r["harness"]["fit"]
        counts = {n: [0] * (n + 1) for n in (2, 4)}
        for (n, _t, _r), x in h.episode_counts(r["runs"][0][1]).items():
            counts[n][x] += 1
        self.assertFalse(a.lr_region(counts, 0.3, 0.0, 0.001, fit, 50)[0])  # independence is not the planted model
        self.assertFalse(a.lr_region(counts, 0.6, 0.3, 0.001, fit, 50)[0])

    def test_h3_recovers_planted_delta_g_and_behaviour_difference(self):
        seeds = range(1, 9)
        runs = [cached(("h3", s), lambda s=s: a.run_h3("F2", s, design(tasks=8), plant(), est(perms=PERMS))) for s in seeds]
        rec = sum(r["recovered"] for r in runs)
        brec = sum(r["behaviour"]["recovered"] for r in runs)
        for r in runs:
            self.assertAlmostEqual(r["planted"], 0.2, places=12)
            self.assertFalse(a.in_interval(0.2 + 0.25, r["interval"]))
            self.assertEqual(r["behaviour"]["planted"], 0.1)
        self.at_least(rec, len(seeds), 0.95)
        self.at_least(brec, len(seeds), 0.95)
        ests = [r["estimate"] for r in runs]
        self.mean_within(ests, 0.2, "H3 dG")  # kills a bias of 0.05 on either arm: SE of the mean is derived
        self.mean_within([r["behaviour"]["estimate"] for r in runs], 0.1, "behaviour")
        self.width_ok([r["interval"] for r in runs], ests, 0.95)
        self.excludes([r["interval"] for r in runs], ests, 0.2, +1)

    def test_h3_killed_side_when_the_team_is_less_overconfident(self):
        pl = plant(conf_bias={"team": -0.1, "solo": 0.1})
        runs = [a.run_h3("F2", s, design(tasks=8), pl, est(perms=49)) for s in range(1, 6)]
        for r in runs:
            self.assertAlmostEqual(r["planted"], -0.2, places=12)
        self.at_least(sum(r["recovered"] for r in runs), 5, 0.95)
        ests = [r["estimate"] for r in runs]
        self.mean_within(ests, -0.2, "H3 killed side")
        self.excludes([r["interval"] for r in runs], ests, -0.2, -1)
        killed = sum(r["decision"] == "killed" for r in runs)
        self.assertEqual(killed, sum(r["interval"][1] < 0 for r in runs))  # killed = the interval wholly below 0
        self.assertEqual(sum(r["decision"] == "supported" for r in runs), 0)

    def test_h5_recovers_planted_S_and_the_false_clean_rate(self):
        seeds = range(1, 5)
        d = design(h5_tasks=6, h5_reruns=24, cal_reruns=14)
        runs = [cached(("h5", s), lambda s=s: a.run_h5("F5", s, d, plant(), est(perms=PERMS))) for s in seeds]
        planted = a.h5_planted_S(0.5, 0.1, 0.9)
        self.assertGreater(planted, 0.1)
        for r in runs:
            self.assertAlmostEqual(r["planted"], planted, places=15)
            self.assertEqual(r["harness"]["uninformative"], [])
            self.assertGreaterEqual(r["harness"]["counts"]["clean"], 400)
            self.assertGreaterEqual(r["harness"]["counts"]["failure"], 200)
            fc = r["false_clean"]
            k, m = round(fc["estimate"] * fc["failing_candidates"]), fc["failing_candidates"]
            lo, hi = self.cp(k, m, 0.95)  # the test's own exact interval: kills a changed level or a wrong tail
            self.assertAlmostEqual(fc["interval"][0], lo, places=9)
            self.assertAlmostEqual(fc["interval"][1], hi, places=9)
        self.at_least(sum(r["recovered"] for r in runs), len(seeds), 0.95)
        self.at_least(sum(r["false_clean"]["recovered"] for r in runs), len(seeds), 0.95)
        ests = [r["estimate"] for r in runs]
        self.mean_within(ests, planted, "H5 S")
        self.mean_within([r["false_clean"]["estimate"] for r in runs], 0.1, "false-clean rate")
        self.width_ok([r["interval"] for r in runs], ests, 0.95)
        self.excludes([r["interval"] for r in runs], ests, planted, +1)

    def test_every_planted_value_is_recovered_in_a_full_stage_a_run(self):
        out = a.stage_a(2, design=design(families=("F2", "F3", "F5"), tasks=6, h5_reruns=24, cal_reruns=14), plant=plant(),
                        est=est(B=100, perms=49), card=card())
        flags = [r["recovered"] for r in out["H2"].values()]
        flags += [out["H3"]["recovered"], out["H3"]["behaviour"]["recovered"], out["H5"]["recovered"],
                  out["H5"]["false_clean"]["recovered"], out["RT"]["recovered"]]
        for arm in out["RT"]["arms"].values():
            flags += [arm["recall"]["recovered"], arm["unverified"]["recovered"]]
        flags += [out["F6"][k]["recovered"] for k in ("recall", "true_negative", "precision", "span")]
        self.assertEqual(len(flags), 3 + 5 + 4 + 4)
        # the H2 checks sit at level 1 - 0.001, the rest at 0.95: the whole set is not significantly below the lowest
        self.at_least(sum(flags), len(flags), 0.95)
        self.assertTrue(all(f is True or f is False for f in flags))


# ----------------------------------------------------------------- closed forms for every null ----

class ClosedFormNulls(Exact):
    def test_h3_permutation_null_has_the_closed_form_mean_and_variance(self):
        r = cached(("h3", 1), lambda: a.run_h3("F2", 1, design(tasks=8), plant(), est(perms=PERMS)))
        null = r["harness"]["null"]
        by = {}
        for row in r["rows"]:
            by.setdefault(row["task"], {"team": [], "solo": []})[row["arm"]].append(row["conf"] - row["pass"])
        var = 0.0
        for t in by.values():
            xs = t["team"] + t["solo"]
            n_, a_, b_ = len(xs), len(t["team"]), len(t["solo"])
            mu = sum(xs) / n_
            sigma2 = sum((x - mu) ** 2 for x in xs) / n_
            var += sigma2 * n_ ** 2 / (a_ * b_ * (n_ - 1))
        var /= len(by) ** 2
        self.assertEqual(len(null), PERMS)
        mean = sum(null) / len(null)
        self.assertLessEqual(abs(mean), Z * math.sqrt(var / len(null)))
        sample_var = sum((x - mean) ** 2 for x in null) / (len(null) - 1)
        self.assertLessEqual(abs(sample_var / var - 1), Z * math.sqrt(2 / (len(null) - 1)))  # normal null: Var(S2) = 2 s4 / (B - 1)

    def test_h5_permutation_null_has_the_closed_form_mean(self):
        r = cached(("h5", 1), lambda: a.run_h5("F5", 1, design(h5_tasks=6, h5_reruns=24, cal_reruns=14), plant(), est(perms=PERMS)))
        cal, scored = r["episodes"]
        total = 0.0
        tasks = sorted({e["task"] for e in scored})
        for t in tasks:
            flat = [c["flags"] > 0 for e in cal if e["task"] == t for c in e["cands"]]
            u = sum(flat) / len(flat)
            bits = [int(c["flags"] > 0) for e in scored if e["task"] == t for c in e["cands"][:16]]
            big_m, k = len(bits), sum(bits)
            terms = []
            for n in (2, 4, 8, 16):  # P(the first n of a random order are all not-clean) = falling factorials
                p = 1.0
                for i in range(n):
                    p *= max(k - i, 0) / (big_m - i)
                terms.append(p - u ** n)
            total += sum(terms) / 4
        want = total / len(tasks)
        null = r["harness"]["null"]
        mean = sum(null) / len(null)
        sd = st.stdev(null)
        self.assertLessEqual(abs(mean - want), Z * sd / math.sqrt(len(null)))

    def test_rt_exact_p_is_the_exact_mcnemar_and_the_permutation_null_matches(self):
        self.assertEqual(a.rt_exact_p(0, 0), 1.0)
        self.assertEqual(a.rt_exact_p(5, 0), 1 / 32)
        self.assertEqual(a.rt_exact_p(0, 5), 1.0)
        self.assertEqual(a.rt_exact_p(3, 2), (10 + 5 + 1) / 32)
        # exhaustive: all 2^k label swaps within lemma; the share of swaps with a sum as low as the observed one
        diffs = [-1, -1, -1, 1, 1, 0, 0]
        x, y = 3, 2
        obs = sum(diffs)
        lows = 0
        for signs in itertools.product((1, -1), repeat=len(diffs)):
            lows += sum(s * d for s, d in zip(signs, diffs)) <= obs
        self.assertEqual(lows / 2 ** len(diffs), a.rt_exact_p(x, y))
        # sampled: a swap negates d, so the null has mean 0 and variance x + y (zeros never move)
        k, big_b = 30, 4000
        null = a.rt_permutation_null([-1] * 20 + [1] * 10 + [0] * 5, big_b, 3)
        mean = sum(null) / big_b
        self.assertLessEqual(abs(mean), Z * math.sqrt(k / big_b))
        v = sum(x_ * x_ for x_ in null) / big_b
        self.assertLessEqual(abs(v / k - 1), Z * math.sqrt((2 * k * k - 2 * k) / big_b) / k)  # Var(S^2) = 2k^2 - 2k

    def test_f6_random_span_null_is_one_over_the_number_of_spans(self):
        for length in (1, 2, 5, 9):
            spans = [(s, e) for s in range(length) for e in range(s + 1, length + 1)]
            self.assertEqual(len(spans), a.n_spans(length))
            got = {tuple(a.random_span(random.Random(i), length)) for i in range(60 * a.n_spans(length))}
            self.assertEqual(got, set(spans))  # support is exactly the spans
        task = {"family": "F6", "formal": "abcde", "defective": True, "span": [1, 3], "defect": "x"}
        aud = {"detect": 1.0, "false_alarm": 0.0, "locate": 0.0}  # locates by chance only
        hits, n = 0, 6000
        for i in range(n):
            hits += a.F6Agent(i, task, aud).claim_for("a0")[0]["span"] == [1, 3]
        p = 1 / a.n_spans(5)
        self.assertGreaterEqual(tail_ge(hits, n, p), FALSE_ALARM / 2)
        self.assertGreaterEqual(tail_le(hits, n, p), FALSE_ALARM / 2)


# ------------------------------------------------------------------------------------------- nulls ----

class Nulls(Exact):
    def test_h2_null_independent_agents_gives_no_supported_and_few_interval_hits(self):
        runs, hits, supported, tail = 10, 0, 0, 0.05
        for s in range(1, runs + 1):
            r = a.run_h2("F2", s, design(), plant(c=0.0), est(level=0.9))
            iv = r["harness"]["interval"]
            hits += iv is not None and iv[0] > 0
            supported += r["decision"] == "supported"
            self.assertEqual(r["planted"]["c"], 0.0)
        self.assertEqual(supported, 0)
        self.at_most(hits, runs, tail)  # one tail of the 90% interval

    def test_h2_task_spread_in_q_is_not_read_as_a_shared_cause(self):
        # half the tasks pass 90% of the time, half 40%, with c = 0: pooled pass counts are overdispersed, but agents
        # fail independently within an episode, so the primary must not say supported
        pl = plant(pass_p={2: 0.9, 3: 0.7, 4: 0.4}, c=0.0)
        runs, hits, supported = 8, 0, 0
        for s in range(1, runs + 1):
            r = a.run_h2("F2", s, design(), pl, est(level=0.9), difficulties=[2, 4])
            iv = r["harness"]["interval"]
            hits += iv is not None and iv[0] > 0
            supported += r["decision"] == "supported"
            self.assertIsNone(r["recovered"])
            if s == 1:  # the plant really mixes: each difficulty passes at its own planted rate (c = 0)
                tasks, rows, _ = r["runs"][0]
                for diff, want in ((2, 0.9), (4, 0.4)):
                    xs = [x["pass"] for x in rows if tasks[x["task"]]["difficulty"] == diff]
                    se = math.sqrt(want * (1 - want) / len(xs))
                    self.assertLessEqual(abs(sum(xs) / len(xs) - want), Z * se, diff)
        self.assertEqual(supported, 0)
        self.at_most(hits, runs, 0.05)

    def test_h3_null_equal_bias_gives_no_false_support(self):
        runs, hits = 10, 0
        for s in range(1, runs + 1):
            r = a.run_h3("F3", s, design(), plant(conf_bias={"team": 0.05, "solo": 0.05}), est())
            hits += r["interval"][0] > 0
            self.assertEqual(r["planted"], 0.0)
        self.at_most(hits, runs, 0.025)

    def test_h5_null_independent_draws_give_S_zero_and_no_false_support(self):
        runs, hits = 6, 0
        for s in range(1, runs + 1):
            r = a.run_h5("F5", s, design(), plant(spread=0.0), est())
            hits += r["interval"][0] > 0
            self.assertEqual(r["planted"], 0.0)
        self.at_most(hits, runs, 0.025)

    def test_rt_null_equal_arms_gives_no_false_support(self):
        runs, hits, ph = 14, 0, 0
        equal = plant(rt=dict(plant()["rt"], find={"treatment": 0.5, "control": 0.5}))
        for s in range(1, runs + 1):
            r = a.run_rt(s, design(), equal, est(B=200))
            self.assertEqual(r["planted"], 0.0)
            hits += r["decision"] == "supported"
            ph += r["p_one_sided"] <= 0.05
        self.at_most(hits, runs, 0.025)
        self.at_most(ph, runs, 0.05)  # an exact test: size at most the nominal level


# ------------------------------------------------------------------------------------------------ RT ----

class RedTeam(Exact):
    def runs(self):
        return [cached(("rt", s), lambda s=s: a.run_rt(s, design(), plant(), est(B=200))) for s in range(1, 9)]

    def test_rt_recovers_the_planted_difference_and_arm_rates(self):
        rs = self.runs()
        self.assertAlmostEqual(rs[0]["planted"], 0.6 * (0.2 - 0.8), places=12)
        self.at_least(sum(r["recovered"] for r in rs), len(rs), 0.95)
        ests = [r["estimate"] for r in rs]
        self.mean_within(ests, -0.36, "RT difference")
        self.width_ok([r["interval"] for r in rs], ests, 0.95)
        self.excludes([r["interval"] for r in rs], ests, -0.36, -1)
        for arm, find, bogus in (("treatment", 0.8, 0.3), ("control", 0.2, 0.05)):
            for key in ("recall", "unverified"):
                es = [r["arms"][arm][key] for r in rs]
                self.at_least(sum(e["recovered"] for e in es), len(es), 0.95)
                self.mean_within([e["estimate"] for e in es], find if key == "recall" else bogus, f"{arm} {key}")

    def test_the_proposer_is_the_same_in_both_arms_and_pass_is_the_oracle(self):
        r = self.runs()[0]
        t, c = r["rows"]["treatment"], r["rows"]["control"]
        self.assertEqual(len(t), len(c))
        self.assertEqual([x["pass"] for x in t if x["agent"] == 0], [x["pass"] for x in c if x["agent"] == 0])
        self.assertTrue(all(x["pass"] in (0, 1) for x in t + c))

    def test_the_unverified_counterexample_rate_is_never_an_override(self):
        task = a.gen_lemma_tasks(2, 1, 0.0, 1, "x", 2000, 10**6)[0]
        prop = {"label": True, "counterexample": None}
        bogus = {"label": False, "counterexample": {"x": 0, "y": 0}}
        self.assertEqual(a.rt_outcome(task, prop, bogus), (1, 0, 1))  # the label stands, and it is counted
        fl = a.gen_lemma_tasks(2, 1, 1.0, 1, "x", 2000, 10**6)[0]
        good = {"label": False, "counterexample": fl["counterexample"]}
        self.assertEqual(a.rt_outcome(fl, prop, good), (0, 1, 0))
        self.assertEqual(a.rt_outcome(fl, prop, {"label": True, "counterexample": None}), (1, 0, 0))
        self.assertEqual(a.rt_outcome(fl, {"label": False, "counterexample": fl["counterexample"]}, prop), (0, 0, 0))

    def test_rt_killed_side_and_uninformative(self):
        worse = plant(rt=dict(plant()["rt"], find={"treatment": 0.2, "control": 0.8}))
        rs = [a.run_rt(s, design(), worse, est(B=200)) for s in range(1, 5)]
        ests = [r["estimate"] for r in rs]
        self.mean_within(ests, 0.36, "RT killed side")
        self.excludes([r["interval"] for r in rs], ests, 0.36, +1)
        self.assertEqual({r["decision"] for r in rs} - {"killed"}, set())
        self.assertTrue(all(r["p_one_sided"] > 0.9 for r in rs))
        r = a.run_rt(1, design(), plant(), est(B=50, rt_min_accepted=10**4))
        self.assertEqual(r["decision"], "uninformative")
        self.assertTrue(r["uninformative"])

    def test_rt_with_no_false_lemma_is_refused(self):
        with self.assertRaises(ValueError):
            a.run_rt(1, design(false_rate=0.0, rt_lemmas=4), plant(), est())


# ------------------------------------------------------------------------------------------------ F6 ----

class Audit(Exact):
    def test_generator_plants_label_and_exact_span(self):
        kinds = set()
        for t in a.gen_audit_tasks(300, 0.0, 1, "g"):
            self.assertTrue(t["defective"])
            kinds.add(t["defect"])
            s, e = t["span"]
            self.assertLess(s, e)
            self.assertLessEqual(e, len(t["formal"]))
        self.assertEqual(kinds, {d[0] for d in a.DEFECTS})  # all five defect types
        self.assertTrue(all(not t["defective"] and t["span"] is None for t in a.gen_audit_tasks(50, 1.0, 1, "g")))
        mix = a.gen_audit_tasks(400, 0.25, 2, "g")
        k = sum(not t["defective"] for t in mix)
        self.assertGreaterEqual(tail_ge(k, 400, 0.25), FALSE_ALARM)
        self.assertGreaterEqual(tail_le(k, 400, 0.25), FALSE_ALARM)
        with self.assertRaises(ValueError):
            a.gen_audit_tasks(0, 0.5, 1, "g")
        with self.assertRaises(ValueError):
            a.gen_audit_tasks(5, 1.5, 1, "g")

    def test_the_defective_text_differs_from_the_faithful_one_only_at_the_span(self):
        for t in a.gen_audit_tasks(40, 0.0, 3, "g"):
            kind, inf, formal, old, new = next(d for d in a.DEFECTS if d[0] == t["defect"])
            k = next(c for c in "123456789" if inf.replace("<k>", c) == t["informal"])
            old, new, formal = (x.replace("<k>", k) for x in (old, new, formal))
            s, e = t["span"]
            self.assertEqual(t["formal"][s:e], new)
            self.assertEqual(t["formal"][:s] + old + t["formal"][e:], formal)

    def test_oracle_scores_exact_spans_and_true_negatives(self):
        d = next(t for t in a.gen_audit_tasks(20, 0.0, 1, "g"))
        f = next(t for t in a.gen_audit_tasks(20, 1.0, 1, "g"))
        s, e = d["span"]
        self.assertEqual(a.oracle_f6(d, {"faithful": False, "span": [s, e]}), 1)
        self.assertEqual(a.oracle_f6(d, {"faithful": False, "span": (s, e)}), 1)
        for bad in ([s, e + 1], [s + 1, e], [s - 1, e], [e, s], None, [s, e, 0], ["a", "b"], [float(s), float(e)]):
            self.assertEqual(a.oracle_f6(d, {"faithful": False, "span": bad}), 0, bad)
        self.assertEqual(a.oracle_f6(d, {"faithful": True, "span": None}), 0)
        self.assertEqual(a.oracle_f6(d, {"faithful": 0, "span": [s, e]}), 0)
        self.assertEqual(a.oracle_f6(f, {"faithful": True, "span": None}), 1)
        self.assertEqual(a.oracle_f6(f, {"faithful": False, "span": [0, 1]}), 0)
        self.assertEqual(a.oracle_f6(f, {}), 0)

    def test_audit_recovers_planted_detection_false_alarm_precision_and_span(self):
        seeds = range(1, 11)
        d = design(audit_pairs=100)
        rs = [cached(("f6", s), lambda s=s: a.run_f6(s, d, plant(), est())) for s in seeds]
        for key in ("recall", "true_negative", "precision", "span"):
            self.at_least(sum(r[key]["recovered"] for r in rs), len(rs), 0.95)
        self.mean_within([r["recall"]["estimate"] for r in rs], 0.8, "recall")
        self.mean_within([r["true_negative"]["estimate"] for r in rs], 0.9, "true-negative rate")
        # span accuracy: exact-span matches among flagged defective pairs, planted locate + (1 - locate) / spans
        self.mean_within([r["span"]["estimate"] for r in rs], 0.7, "span accuracy")  # chance term is below 1e-2 here

    def test_planted_precision_and_rates_are_the_closed_forms_of_the_realised_counts(self):
        aud = {"detect": 0.5, "false_alarm": 0.25, "locate": 0.4}
        r = a.run_f6(3, design(audit_pairs=80), plant(audit=aud), est())
        nd = sum(r["tasks"][x["task"]]["defective"] for x in r["rows"])
        nf = len(r["rows"]) - nd
        self.assertAlmostEqual(r["precision"]["planted"], 0.5 * nd / (0.5 * nd + 0.25 * nf), places=12)
        self.assertEqual((r["recall"]["planted"], r["true_negative"]["planted"]), (0.5, 0.75))
        chance = sum(1 / a.n_spans(len(r["tasks"][x["task"]]["formal"])) for x in r["rows"]
                     if r["tasks"][x["task"]]["defective"]) / nd
        self.assertAlmostEqual(r["span"]["planted"], 0.4 + 0.6 * chance, places=12)
        self.assertEqual(r["recall"]["n"], nd)
        self.assertEqual(r["true_negative"]["n"], nf)

    def test_pass_rate_is_the_oracle_and_chance_spans_score_zero_mostly(self):
        d = design(audit_pairs=80)
        blind = plant(audit={"detect": 1.0, "false_alarm": 0.0, "locate": 0.0})
        r = a.run_f6(1, d, blind, est())
        self.assertEqual(r["recall"]["estimate"], 1.0)
        self.assertEqual(r["true_negative"]["estimate"], 1.0)
        self.assertEqual(r["recall"]["planted"], 1.0)
        self.assertEqual(r["precision"]["estimate"], 1.0)
        passed = sum(x["pass"] for x in r["rows"])
        faithful_rows = sum(not r["tasks"][x["task"]]["defective"] for x in r["rows"])
        self.assertGreaterEqual(tail_ge(passed - faithful_rows, 2 * 80, 0.02), FALSE_ALARM)  # only chance spans pass
        self.assertTrue(r["span"]["recovered"])
        silent = a.run_f6(1, d, plant(audit={"detect": 0.0, "false_alarm": 1.0, "locate": 1.0}), est())
        self.assertEqual(silent["recall"]["estimate"], 0.0)
        self.assertEqual(silent["true_negative"]["estimate"], 0.0)
        self.assertIsNone(silent["span"]["estimate"])


# ----------------------------------------------------------------------------------------- scorecards ----

class Cards(Exact):
    def go(self, rate, gate):
        d = design(tasks=4)
        r = a.run_h2("F2", 3, d, plant(), est(B=10), )
        return {"H2": {"F2": r}, "cards": {"F2": [a.card_report("F2", t, rows, ag, 3, card(gate_plant=dict(rate=rate, gate=gate)))
                                                   for t, rows, ag in r["runs"]]}}

    def card_for(self, gate, want_pass=None):
        t = a.make_tasks("F5", design(), 1, "c", 0)
        rows, ag = a.play(t, [2], 3, 5, "cd", lambda s, t: 0.5)
        row = next(x for x in rows if want_pass is None or x["pass"] == want_pass)
        r = dict(row, planted_gate=gate)
        return a.make_card(t[r["task"]], r["task"], r, ag[(2, r["task"], r["rerun"])].rec[f"a{r['agent']}"], card()), r

    def test_each_planted_gate_fails_alone_and_pass_is_untouched(self):
        for gate, name in (("G2", "G2_unverified_as_fact"), ("G3", "G3_overclaim"), ("G4", "G4_model_parameter")):
            (c, res), row = self.card_for(gate)
            self.assertEqual([g for g, v in res["gates"].items() if v == "fail"], [name], gate)
            self.assertTrue(res["disqualified"] and res["weighted_total"] == 0.0 and c["verdict"] == "prune")
            self.assertEqual(c["performance_row"]["pass"], row["pass"])
            self.assertTrue(any(res["reasons"]), gate)
            self.assertEqual(sc.validate(c, weights=WEIGHTS), [])
            self.assertEqual(res["declared_mismatch"], [])

    def test_unplanted_card_is_accepted_with_no_gate_failure_and_a_positive_total(self):
        for want in (0, 1):
            (c, res), row = self.card_for(None, want)
            self.assertEqual(row["pass"], want)
            self.assertEqual(res["gates"]["G1_barrier"], "na")
            self.assertNotIn("fail", res["gates"].values())  # a failed oracle check is not a gate failure
            self.assertAlmostEqual(res["weighted_total"], 60.0)
            self.assertEqual(c["verdict"], "revise")
            self.assertEqual(c["claims"][0]["status"], "checked_by_oracle" if want else "conjecture")
            self.assertEqual(c["oracle_checks"]["claims_passed"], want)
            self.assertEqual(c["performance_row"]["pass"], want)

    def test_gate_report_counts_the_planted_failures_exactly(self):
        for rate in (0.0, 1.0, 0.3):
            out = self.go(rate, "G4")
            for fit_or_held in out["cards"]["F2"]:
                for n, e in fit_or_held["per_team_size"].items():
                    self.assertEqual(e["fail"]["G4_model_parameter"], e["planted"], (rate, n))
                    self.assertEqual(sum(v for g, v in e["fail"].items() if g != "G4_model_parameter"), 0)
                    self.assertTrue(e["pass_unchanged"] and e["zero_total_when_disqualified"])
                    if rate == 0.0:
                        self.assertEqual(e["planted"], 0)
                    if rate == 1.0:
                        self.assertEqual(e["planted"], e["rows"])
        self.assertIsNotNone(self.go(1.0, "G3")["cards"]["F2"][0]["example_planted_card"])
        self.assertIsNone(self.go(0.0, "G3")["cards"]["F2"][0]["example_planted_card"])

    def test_planted_failures_do_not_change_h2_pass_rows(self):
        a0, a1 = self.go(0.0, "G4"), self.go(1.0, "G4")
        self.assertEqual(a0["H2"]["F2"]["estimate"], a1["H2"]["F2"]["estimate"])
        self.assertEqual(a0["H2"]["F2"]["harness"]["diff"], a1["H2"]["F2"]["harness"]["diff"])


# ------------------------------------------------------------------------------------------- stage_a ----

class StageA(Exact):
    def test_stage_a_reports_estimate_interval_planted_recovered_per_hypothesis(self):
        out = a.stage_a(2, design=design(families=("F2", "F5"), tasks=4, h5_reruns=10), plant=plant(), est=est(B=30, perms=19), card=card())
        self.assertEqual(set(out), {"H2", "H3", "H5", "RT", "F6", "cards", "not_instantiated"})
        self.assertEqual(set(out["H2"]), {"F2", "F5"})
        for r in (*out["H2"].values(), out["H3"], out["H5"], out["RT"]):
            for k in ("estimate", "interval", "planted", "recovered", "decision"):
                self.assertIn(k, r)
            self.assertIsInstance(r["recovered"], bool)
        self.assertIn("H1", out["not_instantiated"])
        for key in ("recall", "true_negative", "precision", "span"):
            for k in ("estimate", "interval", "planted", "recovered"):
                self.assertIn(k, out["F6"][key])
        self.assertEqual(out["H3"]["planted"], 0.2)
        self.assertEqual(out["H5"]["false_clean"]["planted"], 0.1)

    def test_stage_a_is_deterministic_in_its_seed(self):
        x, y, z = (a.run_h3("F2", s, design(tasks=4), plant(), est(B=10, perms=9)) for s in (2, 2, 3))
        self.assertEqual(x["estimate"], y["estimate"])
        self.assertNotEqual(x["estimate"], z["estimate"])

    def test_fit_and_held_out_task_sets_and_seeds_are_disjoint(self):
        r = a.run_h2("F2", 4, design(tasks=4), plant(), est(B=10))
        (ft, fr, _), (ht, hr, _) = r["runs"]
        self.assertFalse(set(ft) & set(ht))
        self.assertFalse({x["seed"] for x in fr} & {x["seed"] for x in hr})
        self.assertEqual({x["n"] for x in fr}, {2, 4})
        self.assertEqual({x["n"] for x in hr}, {8})

    def test_refusals(self):
        base = dict(design=design(families=("F2",), tasks=2, h5_tasks=2), plant=plant(), est=est(B=10, perms=9), card=card())

        def call(**over):
            kw = dict(base, **over)
            with mock.patch.object(a, "run_h2", side_effect=AssertionError("reached an estimator")), \
                    mock.patch.object(a, "run_h3", side_effect=AssertionError("reached an estimator")), \
                    mock.patch.object(a, "run_h5", side_effect=AssertionError("reached an estimator")):
                return a.stage_a(1, **kw)

        for part in ("design", "plant", "est", "card"):
            missing = dict(base[part])
            missing.pop(next(iter(missing)))
            with self.assertRaises(ValueError, msg=part):
                call(**{part: missing})
            with self.assertRaises(ValueError, msg=part):
                call(**{part: dict(base[part], extra=1)})
        with self.assertRaises(TypeError):
            a.stage_a(1, design=base["design"], plant=base["plant"], est=base["est"])
        for bad in (True, -1, 1.5, None):
            with self.assertRaises(ValueError):
                a.stage_a(bad, **base)
        for over in (dict(design=design(n_vars=4)), dict(design=design(families=("F4",))), dict(design=design(families=())),
                     dict(design=design(h35_family="F1")),
                     dict(design=design(difficulty={"F2": 2, "F3": 3, "F5": 3}, families=("F2",))),
                     dict(plant=plant(c=1.5)), dict(plant=plant(rt=dict(plant()["rt"], accept_false=1.5))),
                     dict(plant=plant(rt=dict(plant()["rt"], find={"treatment": 0.5}))),
                     dict(plant=plant(audit=dict(plant()["audit"], detect=2.0))), dict(est=est(rt_min_accepted=0)),
                     dict(design=design(audit_pairs=1)), dict(design=design(faithful_rate=-0.1)), dict(plant=plant(pass_p={3: 1.0})), dict(plant=plant(pass_p={3: True})),
                     dict(plant=plant(conf_bias={"team": 0.1})), dict(est=est(alpha_recover=0.0)),
                     dict(est=est(level=1.0)), dict(card=card(gate_plant=dict(rate=0.1, gate="G1"))),
                     dict(card=card(gate_plant=dict(rate=2.0, gate="G4"))),
                     dict(card=card(weights={k: 0.3 for k in sc.CRITERIA})),
                     dict(card=card(rubric={k: 3 for k in list(sc.CRITERIA)[:4]}))):
            with self.assertRaises(ValueError, msg=repr(over)):
                call(**over)

    def test_h3_refuses_confidence_that_would_clip(self):
        with mock.patch.object(a, "play", side_effect=AssertionError("ran before the check")):
            for bias in ({"team": 0.11, "solo": 0.0}, {"team": 0.0, "solo": -0.71}):  # margins of 0.1 on either side
                with self.assertRaises(ValueError):
                    a.run_h3("F2", 1, design(), plant(conf_bias=bias), est())
        with self.assertRaises(ValueError):
            a.run_h3("F2", 1, design(), plant(conf_bias={"team": 0.25, "solo": 0.0}), est())
        with self.assertRaises(ValueError):
            a.run_h3("F2", 1, design(), plant(conf_bias={"team": 0.0, "solo": -0.75}), est())

    def test_h5_below_the_registered_calibration_minima_is_uninformative(self):
        r = a.run_h5("F5", 1, design(cal_reruns=3, h5_reruns=5), plant(), est(B=10, perms=9))
        self.assertEqual(r["decision"], "uninformative")
        self.assertTrue(any("not reached" in x for x in r["harness"]["uninformative"]))

    def test_h5_refuses_a_failure_rate_above_one(self):
        with self.assertRaises(ValueError):
            a.run_h5("F5", 1, design(), plant(f=0.6, spread=0.8), est())

    def test_the_harness_is_the_pinned_one(self):
        import os
        import subprocess
        here = os.path.dirname(os.path.abspath(h.__file__))
        ref = subprocess.run(["git", "show", "d0c67d7:lab/r5_perf_harness.py"], cwd=here, capture_output=True)
        if ref.returncode != 0:
            self.skipTest("commit d0c67d7 is not reachable from here: pin unverified, not passed")
        with open(h.__file__, "rb") as fh:
            self.assertEqual(fh.read(), ref.stdout, "lab/r5_perf_harness.py differs from the d0c67d7 pin")


if __name__ == "__main__":
    unittest.main()
