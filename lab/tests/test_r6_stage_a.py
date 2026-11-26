"""Tests for lab/r6_stage_a.py (R6 Stage A): oracles, scripted agents, planted-value recovery, nulls, scorecards, refusals.

Tolerances are derived, never tuned:
- H2 (q, c): the likelihood-ratio region, 2 (ll_hat - ll_planted) <= -2 ln(alpha) (chi-squared, 2 df, closed form).
- H3, H5: the harness's own bootstrap interval; the count of runs that recover is compared with the nominal level
  by the exact binomial lower tail at FALSE_ALARM, never by a hand-picked count.
- Nulls: the count of runs whose interval lies wholly above 0 against the one-sided tail of the nominal level, by the
  exact binomial upper tail at FALSE_ALARM.
"""
import math
import random
import unittest
from unittest import mock

from lab import r5_perf_harness as h
from lab import r6_predicates as pr
from lab import r6_scorecard as sc
from lab import r6_stage_a as a

FALSE_ALARM = 1e-3


def _pmf(i, m, p):
    return math.comb(m, i) * p ** i * (1 - p) ** (m - i)


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


def design(**kw):
    d = dict(n_vars=3, tasks=6, reruns=10, h5_tasks=6, cal_reruns=14, h5_reruns=20, difficulty={"F2": 3, "F3": 3, "F5": 3},
             families=("F2", "F3", "F5"), h35_family="F5", yes_rate=0.5, false_rate=0.5, step_limit=2000,
             total_steps=10**6)
    d.update(kw)
    return d


def plant(**kw):
    p = dict(pass_p={3: 0.7}, c=0.3, conf_bias={"team": 0.1, "solo": -0.1}, ask_effect=0.1, false_clean=0.3, f=0.5,
             spread=0.8)
    p.update(kw)
    return p


def est(**kw):
    e = dict(level=0.95, alpha=0.05, alpha_recover=0.001, grid_steps=50, B=60, perms=49, edge=0.02, K=0.01,
             negligible=0.001, max_unparseable=0.1)
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
        rows, ag = a.play(tasks, [2, 4], 3, 5, "ag", lambda s: 0.4)
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
                a.play(tasks, [2], 1, 5, "ag", lambda s: 0.4)

    def test_planted_failure_probability_is_used_not_a_constant(self):
        tasks = a.make_tasks("F2", design(), 1, "t", 0)
        for fail_p in (0.0, 1.0):
            rows, _ = a.play(tasks, [4], 2, 5, "ag", lambda s: fail_p)
            self.assertEqual({r["pass"] for r in rows}, {int(fail_p == 0.0)})

    def test_flags_only_on_failing_candidates_with_the_planted_miss_rate(self):
        tasks = a.make_tasks("F2", design(), 1, "t", 0)
        rows, ag = a.play(tasks, [16], 12, 5, "fl", lambda s: 0.5, flag_miss=0.25)
        recs = [x.rec[k] for x in ag.values() for k in x.rec]
        self.assertTrue(all(r["flag"] == 0 for r in recs if r["pass"]))
        failing = [r for r in recs if not r["pass"]]
        flagged = sum(r["flag"] for r in failing)
        self.assertGreaterEqual(tail_ge(flagged, len(failing), 0.75), FALSE_ALARM)
        self.assertGreaterEqual(tail_le(flagged, len(failing), 0.75), FALSE_ALARM)

    def test_solo_arm_runs_through_run_episode_with_the_run_arms_seed_rule(self):
        tasks = a.make_tasks("F2", design(), 1, "t", 0)
        rows = a.play_solo(tasks, 3, 5, "so", lambda s: 0.0, (0.7, 0.0))
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

class Recovery(Exact):
    def test_h2_recovers_planted_q_and_c_on_each_family(self):
        seeds = range(1, 6)
        for fam in ("F2", "F3", "F5"):
            rec, sup = 0, 0
            for s in seeds:
                r = a.run_h2(fam, s, design(), plant(), est())
                rec += r["recovered"]
                sup += r["decision"] == "supported"
                self.assertEqual(r["planted"], {"q": 1 - 0.7, "c": 0.3})
                self.assertEqual(r["recovered"], r["delta"] <= r["threshold"])
                if r["recovered"]:
                    self.assertTrue(a.in_interval(0.3, r["interval"]["c"]) and a.in_interval(0.3, r["interval"]["q"]))
                # the pooled pass rate is the planted (1 - c)(1 - q), within 4 standard errors of the episode means
                fit_rows = r["runs"][0][1]
                eps = [x / n for (n, _, _), x in h.episode_counts(fit_rows).items()]
                mean = sum(eps) / len(eps)
                se = math.sqrt(sum((e - mean) ** 2 for e in eps) / (len(eps) - 1) / len(eps))
                self.assertLessEqual(abs(mean - 0.7 * 0.7), 4 * se, (fam, s))
            self.at_least(rec, len(seeds), 1 - 0.001)
            self.assertGreaterEqual(sup, 1, fam)  # a shared cause this large is found: the primary can say supported

    def test_h2_does_not_recover_a_wrong_planted_value(self):
        r = a.run_h2("F2", 1, design(), plant(), est())
        fit = r["harness"]["fit"]
        counts = {n: [0] * (n + 1) for n in (2, 4)}
        for (n, _t, _r), x in h.episode_counts(r["runs"][0][1]).items():
            counts[n][x] += 1
        self.assertFalse(a.lr_region(counts, 0.3, 0.0, 0.001, fit, 50)[0])  # independence is not the planted model
        self.assertFalse(a.lr_region(counts, 0.6, 0.3, 0.001, fit, 50)[0])

    def test_h3_recovers_planted_delta_g_and_behaviour_difference(self):
        seeds, rec, brec, sup = range(1, 6), 0, 0, 0
        for s in seeds:
            r = a.run_h3("F2", s, design(), plant(), est())
            rec += r["recovered"]
            brec += r["behaviour"]["recovered"]
            self.assertAlmostEqual(r["planted"], 0.2, places=12)
            self.assertFalse(a.in_interval(0.2 + 0.25, r["interval"]))      # the interval is narrow enough to tell
            self.assertFalse(a.in_interval(0.0, r["interval"]))
            sup += r["decision"] == "supported"
            self.assertEqual(r["behaviour"]["planted"], 0.1)
        self.assertGreaterEqual(sup, 1)
        self.at_least(rec, len(seeds), 0.95)
        self.at_least(brec, len(seeds), 0.95)

    def test_h3_behaviour_difference_zero_when_the_field_changes_nothing(self):
        brec = 0
        for s in range(1, 4):
            r = a.run_h3("F5", s, design(), plant(ask_effect=0.0), est())
            brec += r["behaviour"]["recovered"] and r["behaviour"]["planted"] == 0.0
        self.at_least(brec, 3, 0.95)

    def test_h5_recovers_planted_S_and_the_false_clean_rate(self):
        seeds, rec, frec = range(1, 4), 0, 0
        d = design(h5_tasks=6, h5_reruns=40)
        for s in seeds:
            r = a.run_h5("F5", s, d, plant(), est())
            rec += r["recovered"]
            frec += r["false_clean"]["recovered"]
            self.assertAlmostEqual(r["planted"], a.h5_planted_S(0.5, 0.3, 0.8), places=15)
            self.assertGreater(r["planted"], 0.03)
            self.assertEqual(r["harness"]["uninformative"], [])
            self.assertGreaterEqual(r["harness"]["counts"]["clean"], 400)
            self.assertGreaterEqual(r["harness"]["counts"]["failure"], 200)
        self.at_least(rec, len(seeds), 0.95)
        self.at_least(frec, len(seeds), 0.95)


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


# ----------------------------------------------------------------------------------------- scorecards ----

class Cards(Exact):
    def go(self, rate, gate):
        d = design(tasks=4)
        r = a.run_h2("F2", 3, d, plant(), est(B=10), )
        return {"H2": {"F2": r}, "cards": {"F2": [a.card_report("F2", t, rows, ag, 3, card(gate_plant=dict(rate=rate, gate=gate)))
                                                   for t, rows, ag in r["runs"]]}}

    def card_for(self, gate, want_pass=None):
        t = a.make_tasks("F5", design(), 1, "c", 0)
        rows, ag = a.play(t, [2], 3, 5, "cd", lambda s: 0.5)
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
        self.assertEqual(set(out), {"H2", "H3", "H5", "cards", "not_instantiated"})
        self.assertEqual(set(out["H2"]), {"F2", "F5"})
        for r in (*out["H2"].values(), out["H3"], out["H5"]):
            for k in ("estimate", "interval", "planted", "recovered", "decision"):
                self.assertIn(k, r)
            self.assertIsInstance(r["recovered"], bool)
        self.assertIn("H1", out["not_instantiated"])
        self.assertEqual(out["H3"]["planted"], 0.2)
        self.assertEqual(out["H5"]["false_clean"]["planted"], 0.3)

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
                     dict(plant=plant(c=1.5)), dict(plant=plant(pass_p={3: 1.0})), dict(plant=plant(pass_p={3: True})),
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
