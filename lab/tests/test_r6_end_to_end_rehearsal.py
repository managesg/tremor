"""Offline end-to-end rehearsal of the R6 pipeline with fixed seeds (instrument check, no model, no network).

generators (F1, T1 toy fixture, T2, T3) -> scripted answers (right by the task's own oracle, wrong, malformed,
empty) -> scoring (family checkers, lab/r6_stage_a.make_card + lab/r6_scorecard) -> Holm (lab/r6_holm) on a
paired lemma comparison (RT shape: x = accepted only in control, y = accepted only in treatment).

Glue used and what is not joined: F1 has no scorecard family (LENS lacks F1), so F1 is scored by its own checkers and
performance_row only; T2 is carded as an F5-shaped task. No hard gate is planted in the cards (gate_plant is not
used). In the paired comparison H1, H3 and H5 get p = 1; their claims are exercised only with the p-values and
intervals the tests give by hand, not from agent runs.
"""
import hashlib
import json
import os
import socket
import subprocess
import unittest
from unittest import mock

from lab import r5_perf_harness as h
from lab import r6_f1_tasks as F1
from lab import r6_holm as H
from lab import r6_scorecard as sc
from lab import r6_stage_a as SA
from lab import r6_t1_audit_pairs as T1
from lab import r6_t2_tasks as T2
from lab import r6_t3_lemmas as T3

SL, TOT = 5000, 10**9
AGENTS = ("right", "wrong", "malformed", "empty")
CARD = dict(weights={k: 0.2 for k in sc.CRITERIA}, rubric={k: 3 for k in sc.CRITERIA},
            briefing_keywords=["zzbriefing"], overclaim_patterns=["proof of P vs NP"])

TOY = "def f := ∀ x, x < 3 ∧ ℝ\ndef g := ∑ y, y < 3 ∧ ok\n"
TOY_SPECS = [
    {"id": "t_f", "before": "def f := ∀ x, x ", "old": "<", "after": " 3 ∧ ℝ", "new": "≤",
     "informal": "def f", "why": "w", "may_elaborate": "likely", "evidence": T1.EVIDENCE},
    {"id": "t_g", "before": "def g := ∑ y, y ", "old": "<", "after": " 3 ∧ ok", "new": "≤",
     "informal": "def g", "why": "w", "may_elaborate": "likely", "evidence": T1.EVIDENCE},
]


# ------------------------------------------------------------------------------------------ generators ----

def f1_tasks(seed):
    return [(F1.generate(n, m, seed + i), kind) for i, (n, m) in enumerate(((4, 3), (4, 60), (5, 10), (5, 80)))
            for kind in F1.KINDS]


def t1_tasks():
    return [T1.defective_task(s["id"], TOY, TOY_SPECS) for s in TOY_SPECS] + T1.faithful_pairs(TOY, TOY_SPECS)


def t2_tasks(seed):
    return [T2.generate(2, 2, kind, seed) for kind in T2.KINDS]


def t3_tasks(seed):
    return [T3.generate(kind, k, seed, v) for kind in T3.KINDS for k in (3, 4, 5, 6) for v in T3.VARIANTS]


# ---------------------------------------------------------------------------------------- scripted answers ----

def _f1_right(item):
    f, kind = item
    if kind == "count":
        return [F1.model_count(f)]
    s = F1.solve(f)
    if s == 0:
        return ["NONE"]
    i = (s & -s).bit_length() - 1
    return [tuple((i >> v) & 1 for v in range(f.n))]


def f1_answers(agent, item):
    f, kind = item
    if agent == "right":
        return _f1_right(item)
    if agent == "wrong":
        if kind == "count":
            c = F1.model_count(f)
            return [c + 1] + ([c - 1] if c else [])
        return [(0,) * f.n] if F1.solve(f) == 0 else ["NONE"]
    if agent == "malformed":
        if kind == "count":
            return [-1, True, "5", 2 ** f.n + 1, 1.5]
        return ["garbage", "WITNESS: NONE", (2,) * f.n, (True,) * f.n, [0] * (f.n + 1), 7]
    return [None, "", [], {}]


def t1_answers(agent, task):
    sp = task["span"]
    if agent == "right":
        return [{"faithful": False, "span": list(sp)}] if task["defective"] else [{"faithful": True, "span": None}]
    if agent == "wrong":
        if task["defective"]:
            return [{"faithful": True, "span": None}, {"faithful": False, "span": [sp[0], sp[1] + 1]},
                    {"faithful": False, "span": [sp[0] + 1, sp[1] + 1]}]
        return [{"faithful": False, "span": [0, 1]}]
    if agent == "malformed":
        return [{"faithful": "no", "span": None}, {"faithful": 0, "span": None}, {"faithful": False, "span": "ab"},
                {"faithful": False, "span": [1]}, {"faithful": False, "span": [1.0, 2.0]}, {"span": None}]
    return [None, {}, ""]


def t2_answers(agent, task):
    a, i = T2.label(task)
    yn = lambda b: "yes" if b else "no"  # noqa: E731
    if agent == "right":
        return [f"agrees={yn(a)};identical={yn(i)}"]
    if agent == "wrong":
        return [f"agrees={yn(not a)};identical={yn(not i)}", f"agrees={yn(not a)};identical={yn(i)}",
                f"agrees={yn(a)};identical={yn(not i)}"]
    if agent == "malformed":
        return ["agrees=maybe;identical=no", "agrees=yes; identical=no", "AGREES=YES;IDENTICAL=NO",
                f"agrees={yn(a)};identical={yn(i)}\n", 5, [f"agrees={yn(a)};identical={yn(i)}"]]
    return ["", None]


def t3_answers(agent, task):
    lab = T3.label(task, SL, TOT)
    if agent == "right":
        return ["true"] if lab.holds else [lab.counterexample]
    if agent == "wrong":
        return [0, (1 << task.k) - 1] if lab.holds else ["true"]
    if agent == "malformed":
        return [-1, 1 << task.k, True, 1.5, "maybe", "True"]
    return [None, "", []]


# ------------------------------------------------------------------------------------------------ graders ----

def g_f1(item, a):
    f, kind = item
    try:
        return int(F1.check_count(f, a) if kind == "count" else F1.check_sat_claim(f, a))
    except ValueError:  # the module's contract: a raise is pass 0, never a skipped row
        return 0


def g_t1(task, a):
    return int(T1.oracle(task, a))


def g_t2(task, a):
    return int(T2.check_claim(task, a) == "correct")


def g_t3(task, a):
    return int(T3.check_claim(task, a, SL, TOT) == "correct")


def card_task(fam, task):
    if fam == "t1":
        return task
    return {"family": "F5", "source": task.source if fam == "t3" else "", "step_limit": SL}


def prompt(fam, task):
    return {"f1": lambda t: F1.render_prompt(*t), "t1": T1.render_prompt, "t2": T2.render_prompt,
            "t3": T3.render_prompt}[fam](task)


def build(seed):
    return {"f1": (f1_tasks(seed), f1_answers, g_f1), "t1": (t1_tasks(), t1_answers, g_t1),
            "t2": (t2_tasks(seed), t2_answers, g_t2), "t3": (t3_tasks(seed), t3_answers, g_t3)}


def pipeline(seed):
    """Everything the rehearsal produces for one seed, JSON-serialisable."""
    out = {}
    for fam, (tasks, answers, grade) in build(seed).items():
        rec = {"prompts": [hashlib.sha256(prompt(fam, t).encode("utf-8")).hexdigest() for t in tasks], "agents": {}}
        for ag in AGENTS:
            rows, cards = [], []
            for tid, t in enumerate(tasks):
                for k, a in enumerate(answers(ag, t)):
                    p = grade(t, a)
                    row = {"task": tid, "n": 1, "rerun": k, "agent": 0, "pass": p}
                    rows.append(row)
                    if fam == "f1":
                        cards.append(F1.performance_row(str(tid), 1, k, 0, bool(p), None))
                    else:
                        c, res = SA.make_card(card_task(fam, t), tid, row, {"conf": None}, CARD)
                        cards.append({"id": c["candidate_id"], "pass": c["performance_row"]["pass"],
                                      "valid": res["valid"], "total": res["weighted_total"],
                                      "dq": res["disqualified"], "mismatch": res["declared_mismatch"]})
            rec["agents"][ag] = {"rows": rows, "cards": cards, "score": sum(r["pass"] for r in rows) / len(rows)}
        out[fam] = rec
    return out


def dump(x):
    return json.dumps(x, sort_keys=True, default=str).encode()


def holm_decision(seed, treat, ctrl, n_use=8):
    """Paired planted-false lemmas; accepted = the agent's first answer did not refute the lemma. Treatment accepted
    minus control accepted; x = accepted only in control (supports the treatment), y = only in treatment."""
    tasks = [t for t in t3_tasks(seed) if t.variant == "planted_false"][:n_use]

    def acc(agent, t):
        return 1 - g_t3(t, t3_answers(agent, t)[0])

    diffs = [acc(treat, t) - acc(ctrl, t) for t in tasks]
    x, y = sum(d == -1 for d in diffs), sum(d == 1 for d in diffs)
    p = SA.rt_exact_p(x, y)
    iv = h._boot(diffs, h._mean, 60, seed, 0.95, "rt-boot")
    holm = H.holm_family({"H1": 1, "H3": 1, "H5": 1, "RT": p}, alpha=0.05)
    return {"x": x, "y": y, "p": p, "interval": iv, "rejected": holm["RT"]["rejected"],
            "claim": H.claim("RT", holm, iv, "below", k=None)}


# ------------------------------------------------------------------------------------------------- tests ----

class Rehearsal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        boom = AssertionError("network or subprocess used")
        for tgt in ("socket.socket", "socket.create_connection", "socket.getaddrinfo", "subprocess.Popen",
                    "os.system"):
            p = mock.patch(tgt, side_effect=boom)
            p.start()
            cls.addClassCleanup(p.stop)  # armed before the first pipeline run
        cls.run1 = pipeline(7)

    def test_guards_are_live(self):
        with self.assertRaises(AssertionError):
            socket.socket()
        with self.assertRaises(AssertionError):
            subprocess.run(["true"])
        with self.assertRaises(AssertionError):
            os.system("true")

    def test_pipeline_runs_without_network_or_subprocess(self):
        self.assertEqual(dump(pipeline(7)), dump(self.run1))  # the guards stay armed for the whole rerun

    def test_f1_set_has_sat_and_unsat_formulas(self):
        zs = {F1.solve(f) == 0 for f, k in f1_tasks(7) if k == "sat"}
        self.assertEqual(zs, {True, False})

    def test_right_agents_score_at_the_ceiling(self):
        for fam, rec in self.run1.items():
            a = rec["agents"]["right"]
            self.assertEqual(a["score"], 1.0, fam)
            self.assertTrue(all(c["pass"] == 1 for c in a["cards"]), fam)

    def test_wrong_agents_score_at_the_floor(self):
        for fam, rec in self.run1.items():
            a = rec["agents"]["wrong"]
            self.assertEqual(a["score"], 0.0, fam)
            self.assertTrue(all(c["pass"] == 0 for c in a["cards"]), fam)

    def test_malformed_and_empty_count_as_wrong_not_missing(self):
        for fam, (tasks, answers, _) in build(7).items():
            for ag in ("malformed", "empty"):
                rows = self.run1[fam]["agents"][ag]["rows"]
                self.assertEqual(len(rows), sum(len(answers(ag, t)) for t in tasks), (fam, ag))
                self.assertEqual({r["task"] for r in rows}, set(range(len(tasks))), (fam, ag))  # no task dropped
                self.assertTrue(all(r["pass"] == 0 for r in rows), (fam, ag))
                self.assertEqual(self.run1[fam]["agents"][ag]["score"], 0.0)

    def test_malformed_answers_raise_or_are_labelled_not_skipped(self):
        f, _ = f1_tasks(7)[0]
        with self.assertRaises(ValueError):
            F1.check_sat_claim(f, "garbage")
        self.assertEqual(T3.check_claim(t3_tasks(7)[0], -1, SL, TOT), "malformed")
        self.assertEqual(T2.check_claim(t2_tasks(7)[0], "agrees=maybe;identical=no"), "wrong")

    def test_cards_are_accepted_by_the_scorecard_and_pass_is_the_oracle_pass(self):
        for fam in ("t1", "t2", "t3"):
            for ag in AGENTS:
                rec = self.run1[fam]["agents"][ag]
                for r, c in zip(rec["rows"], rec["cards"]):
                    self.assertTrue(c["valid"])
                    self.assertEqual(c["pass"], r["pass"])
                    self.assertAlmostEqual(c["total"], 60.0)  # 100 * 3/5
                    self.assertEqual((c["dq"], c["mismatch"]), (False, []))

    def _card(self):
        t = card_task("t3", t3_tasks(7)[0])
        row = {"task": 0, "n": 1, "rerun": 0, "agent": 0, "pass": 1}
        return SA.make_card(t, 0, row, {"conf": None}, CARD)

    def _score(self, c):
        return sc.score(c, weights=CARD["weights"], briefing_keywords=CARD["briefing_keywords"],
                        overclaim_patterns=CARD["overclaim_patterns"])

    def test_declared_mismatch_is_flagged_and_refused(self):
        c, res = self._card()
        self.assertEqual(res["declared_mismatch"], [])
        g0 = sorted(c["hard_gates"])[0]
        bad_gate = dict(c, hard_gates=dict(c["hard_gates"], **{g0: "fail" if c["hard_gates"][g0] != "fail" else "pass"}))
        self.assertEqual(self._score(dict(c, weighted_total=1.0))["declared_mismatch"], ["weighted_total"])
        self.assertEqual(self._score(dict(c, disqualified=True))["declared_mismatch"], ["disqualified"])
        self.assertIn(g0, self._score(bad_gate)["declared_mismatch"])
        with mock.patch.object(sc, "score", return_value=dict(res, declared_mismatch=["weighted_total"])):
            with self.assertRaises(ValueError):
                self._card()

    def test_t2_label_disagreement_raises_and_is_never_scored(self):
        real = T2.B.agrees_on_01
        flip = lambda *a, **k: not real(*a, **k)  # noqa: E731
        with mock.patch.object(T2.B, "agrees_on_01", side_effect=flip):
            with self.assertRaises(T2.LabelDisagreement):
                T2.check_claim(t2_tasks(7)[0], "agrees=yes;identical=yes")
            with self.assertRaises(T2.LabelDisagreement):
                pipeline(7)

    def test_f1_performance_rows_carry_the_checker_verdict(self):
        rec = self.run1["f1"]["agents"]["right"]
        self.assertTrue(all(c["pass"] == 1 and c["family"] == "F1" for c in rec["cards"]))

    def test_same_seed_gives_byte_identical_output_twice(self):
        self.assertEqual(dump(pipeline(7)), dump(pipeline(7)))
        self.assertEqual(dump(holm_decision(7, "right", "wrong")), dump(holm_decision(7, "right", "wrong")))

    def test_seed_is_not_ignored(self):
        self.assertNotEqual(F1.generate(5, 10, 1), F1.generate(5, 10, 2))
        self.assertNotEqual(T2.render_prompt(T2.generate(3, 3, "correct", 1)),
                            T2.render_prompt(T2.generate(3, 3, "correct", 2)))
        self.assertNotEqual(dump(pipeline(7)), dump(pipeline(8)))

    def test_holm_all_right_vs_all_wrong_is_supported(self):
        d = holm_decision(7, "right", "wrong")
        self.assertEqual((d["x"], d["y"]), (8, 0))
        self.assertEqual(d["p"], 0.5 ** 8)
        self.assertTrue(d["rejected"])
        self.assertEqual(d["interval"], (-1.0, -1.0))
        self.assertEqual(d["claim"], "supported")

    def test_holm_reversed_comparison_is_the_other_direction(self):
        d = holm_decision(7, "wrong", "right")
        self.assertEqual((d["x"], d["y"], d["p"]), (0, 8, 1.0))
        self.assertFalse(d["rejected"])
        self.assertEqual(d["claim"], "killed")

    def test_holm_identical_vs_identical_is_not_significant(self):
        for ag in ("right", "wrong", "malformed", "empty"):
            d = holm_decision(7, ag, ag)
            self.assertEqual((d["x"], d["y"], d["p"]), (0, 0, 1.0), ag)
            self.assertFalse(d["rejected"], ag)
            self.assertEqual(d["claim"], "not_supported", ag)

    def test_malformed_and_empty_agents_behave_like_wrong_in_the_comparison(self):
        for ag in ("malformed", "empty"):
            self.assertEqual(holm_decision(7, "right", ag), holm_decision(7, "right", "wrong"))

    def test_holm_family_wise_threshold_is_applied(self):
        # 6 discordant lemmas: p = 1/64 = 0.0156 > 0.05/4, so Holm does not reject; 8 do: 1/256 <= 0.0125
        d6 = holm_decision(7, "right", "wrong", n_use=6)
        self.assertEqual(d6["p"], 0.5 ** 6)
        self.assertFalse(d6["rejected"])
        self.assertEqual(d6["claim"], "not_supported")

    def test_holm_four_members_thresholds_and_stop(self):
        r = H.holm_family({"H1": .01, "H3": .03, "H5": .001, "RT": .04}, alpha=.05)
        self.assertEqual([r[m]["step"] for m in H.FAMILY], [2, 3, 1, 4])
        for m, thr in zip(("H5", "H1", "H3", "RT"), (.05 / 4, .05 / 3, .05 / 2, .05)):
            self.assertAlmostEqual(r[m]["threshold"], thr)
        self.assertEqual([r[m]["rejected"] for m in ("H5", "H1", "H3", "RT")], [True, True, False, False])
        self.assertEqual([r[m]["tested"] for m in ("H5", "H1", "H3", "RT")], [True, True, True, False])
        self.assertFalse(r["RT"]["rejected"])  # .04 <= .05 would pass alone: the step-down stops at H3

    def test_holm_equality_at_every_threshold_rejects(self):
        a = .5
        r = H.holm_family({"H1": a / 4, "H3": a / 3, "H5": a / 2, "RT": a}, alpha=a)
        self.assertEqual([r[m]["rejected"] for m in H.FAMILY], [True] * 4)
        r = H.holm_family({"H1": a / 4 * 1.01, "H3": a / 3, "H5": a / 2, "RT": a}, alpha=a)
        self.assertEqual([r[m]["rejected"] for m in H.FAMILY], [False] * 4)

    def test_holm_ties_follow_the_canonical_order(self):
        r = H.holm_family({m: .02 for m in H.FAMILY}, alpha=.05)
        self.assertEqual([r[m]["step"] for m in H.FAMILY], [1, 2, 3, 4])
        self.assertEqual([r[m]["rejected"] for m in H.FAMILY], [False] * 4)  # .02 > .0125 at step 1
        r = H.holm_family({"H1": .001, "H3": .002, "H5": .02, "RT": .02}, alpha=.05)
        self.assertEqual([r[m]["step"] for m in H.FAMILY], [1, 2, 3, 4])
        self.assertEqual([r[m]["rejected"] for m in H.FAMILY], [True] * 4)

    def test_holm_claims_for_h1_h3_h5_with_given_p_values(self):
        r = H.holm_family({"H1": .001, "H3": .002, "H5": .003, "RT": .9}, alpha=.05)
        self.assertEqual(H.claim("H3", r, (.1, .5), "above", k=None), "supported")
        self.assertEqual(H.claim("H3", r, (-.5, -.1), "above", k=None), "killed")
        self.assertEqual(H.claim("H3", r, (-.1, .5), "above", k=None), "not_supported")
        self.assertEqual(H.claim("H5", r, (.3, .6), "above", k=.2), "supported")
        self.assertEqual(H.claim("H5", r, (-.3, .1), "above", k=.2), "killed")
        self.assertEqual(H.claim("H1", r, ((.1, .2), (.3, .4)), "same", k=None), "supported")
        self.assertEqual(H.claim("H1", r, ((.1, .2), (-.4, -.3)), "same", k=None), "killed")
        self.assertEqual(H.claim("RT", r, (-.5, -.1), "below", k=None), "not_supported")  # .9 not rejected
        r2 = H.holm_family({"H1": .5, "H3": .5, "H5": .5, "RT": .5}, alpha=.05)
        self.assertEqual(H.claim("H3", r2, (.1, .5), "above", k=None), "not_supported")  # interval ok, Holm not


if __name__ == "__main__":
    unittest.main()
