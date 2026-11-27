import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from tremor import analysis as an


def rec(arm, ts, y, i=0, **kw):
    r = {"evidence": "model", "instrument_validation": False, "label": "model episode", "episode_id": f"ep1-{arm}-{ts}-{i}",
         "model": "claude-haiku-5-5", "arm": arm, "Y": y, "ended": "complete", "void": None, "abort_reason": None,
         "taskset_id": ts, "malformed_by_reason": {}, "refused": 0, "stopped_agents": [], "turns": []}
    r.update(kw)
    return r


def batch(none, play, code, k=12):  # 12: the prereg minimum of task sets to show a contrast
    return [rec(a, f"s{i}", v) for i in range(k) for a, v in (("none", none), ("play", play), ("code", code))]


class T(unittest.TestCase):
    def refused(self, r):
        with self.assertRaises(an.AnalysisRefused):
            an.summarise([r])

    def test_refusals(self):
        self.refused(rec("none", "s", 0.5, instrument_validation=True))
        self.refused(rec("none", "s", 0.5, label=an.FAKE))
        self.refused(rec("none", "s", 0.5, evidence="fake"))
        self.refused(rec("none", "s", 0.5, evidence=None))
        self.refused(rec("none", "s", 0.5, model=None))
        self.refused(rec("none", "s", 0.5, episode_id=""))

    def test_scripted_never_reaches_model_table_even_relabelled(self):
        self.refused(rec("none", "s", 0.5, episode_id="scripted:floor-1"))  # evidence 'model', clean label
        with self.assertRaises(an.AnalysisRefused):
            an.summarise(batch(0.2, 0.5, 0.8) + [rec("none", "s", 0.5, episode_id="Scripted:x")])

    def test_scripted_table_rules(self):
        s = {"instrument_validation": True, "evidence": "fake", "label": an.FAKE, "model": None}
        out = an.summarise([rec("none", "s", .5, episode_id="scripted:a", **s)], kind="scripted")
        self.assertIn("FAKE", an.render(out))
        with self.assertRaises(an.AnalysisRefused):  # no scripted: prefix
            an.summarise([rec("none", "s", .5, **s)], kind="scripted")
        with self.assertRaises(an.AnalysisRefused):  # model record in a scripted table
            an.summarise([rec("none", "s", .5)], kind="scripted")

    def test_margin_rule(self):
        ok = an.summarise(batch(0.2, 0.5, 0.8))["hdi"]
        self.assertEqual((ok["status"], round(ok["recovered"], 6)), ("interpretable", 0.5))
        self.assertEqual(an.summarise(batch(0.2, 0.5, 0.25))["hdi"]["reason"], "code_gain_unresolved")
        self.assertEqual(an.summarise(batch(0.5, 0.5, 0.2))["hdi"]["reason"], "code_worse_than_none")

    def test_defaults_and_paired_t(self):
        import inspect
        self.assertEqual(inspect.signature(an.summarise).parameters["n_boot"].default, 10000)
        s = an.summarise(batch(0.2, 0.5, 0.8), n_boot=50)
        self.assertEqual(s["exploratory"]["paired_t"]["play_none"]["df"], 11)
        self.assertAlmostEqual(s["exploratory"]["paired_t"]["play_none"]["mean_diff"], 0.3)
        self.assertIn("paired t", an.render(s))

    def test_resolved_needs_both_intervals(self):
        self.assertEqual(an.resolve((.1, .5), (.2, .4)), "positive")
        self.assertEqual(an.resolve((-.5, -.1), (-.4, -.2)), "negative")
        self.assertEqual(an.resolve((.1, .5), (-.1, .7)), "unresolved")  # t straddles
        self.assertEqual(an.resolve((.1, .5), (-.4, -.2)), "unresolved")  # opposite sides
        self.assertEqual(an.resolve((-.1, .5), (.2, .4)), "unresolved")  # bootstrap straddles
        c = an.summarise(batch(0.2, 0.5, 0.8), n_boot=50)["contrasts"]["play_none"]
        self.assertEqual((c["resolved"], c["name"]), ("positive", "Y_play - Y_none"))
        self.assertEqual(sorted(c), ["ci_boot", "ci_t", "exploratory", "hi_below_soi_both", "label", "name", "point",
                                     "resolved", "smaller_than_effect_of_interest"])

    def test_render_is_built_from_structured_fields_only(self):
        s = an.summarise(batch(0.2, 0.5, 0.8), n_boot=50)
        s["contrasts"]["play_none"]["resolved"] = "unresolved"
        s["hdi_block"] = {"interpretable": False, "reason": "code_gain_unresolved"}
        s["hdi"] = None  # render must not touch the raw block
        s["contrasts"]["play_none"]["label"] = "not resolved: inconclusive"
        t = an.render(s)
        self.assertIn("not resolved", [l for l in t.splitlines() if l.startswith("Y_play - Y_none")][0])
        self.assertIn("HDI not interpretable (code_gain_unresolved)", t)

    def test_hdi_block_flag_and_reason(self):
        ok = an.summarise(batch(0.2, 0.5, 0.8))["hdi_block"]
        self.assertEqual((ok["interpretable"], ok["reason"], round(ok["recovered"], 6)), (True, None, 0.5))
        bad = an.summarise(batch(0.5, 0.5, 0.2))["hdi_block"]
        self.assertEqual((bad["interpretable"], bad["reason"]), (False, "code_worse_than_none"))

    def test_structured_and_rendered_verdicts_agree_over_seeds(self):
        import random
        seen = set()
        for seed in range(60):
            rnd = random.Random(seed)
            gaps = [rnd.choice([0, .05, .2, .5]) * rnd.choice([-1, 1]) for _ in range(2)]
            noise = rnd.choice([.01, .2, .4])
            rs = [rec(a, f"s{i}", min(1, max(0, .5 + g + rnd.uniform(-noise, noise))))
                  for i in range(rnd.choice([1, 2, 11, 12, 16])) for a, g in (("none", 0), ("play", gaps[0]), ("code", gaps[1]))]
            s = an.summarise(rs, seed=seed, n_boot=200)
            lines = {l.split("  ")[0].strip(): l for l in an.render(s).splitlines()}
            for k, name in an.CONTRASTS:
                c = s["contrasts"][k]
                seen.add(c["resolved"])
                self.assertIn("  " + c["label"], lines[name], (seed, k))
                self.assertEqual(" resolved " in lines[name] + " ", c["resolved"] != "unresolved", (seed, k))
                self.assertEqual(c["label"] == an.NOT_SHOWN, len({r["taskset_id"] for r in rs}) < 12)
                self.assertEqual("n/a" in lines[name].split(name)[1][:12], c["point"] is None)
            self.assertEqual(("Note: " + an.INCONCLUSIVE in an.render(s)),
                             any(c["resolved"] == "unresolved" for c in s["contrasts"].values()))
        self.assertEqual(seen, {"positive", "negative", "unresolved"})

    def test_near_zero_denominator(self):
        h = an.summarise(batch(0.5, 0.4, 0.5 + 1e-12))["hdi"]
        self.assertEqual(h["status"], "not_interpretable")
        self.assertEqual(h["degenerate_resamples"], 10000)

    def test_counts_task_sets_not_turns(self):
        turns = [{"agent": f"a{i}", "retries": 1} for i in range(4)]
        rs = [rec("none", "s1", .5, i=i, turns=turns, malformed_by_reason={"truncated": 2}, refused=3,
                  stopped_agents=["a0"]) for i in range(3)]
        rs.append(rec("none", "s2", .5, ended="void", void="x"))
        a = an.summarise(rs)["arms"]["none"]
        self.assertEqual((a["task_sets"], a["episodes"], a["censored_task_sets"]), (2, 4, 1))
        self.assertEqual((a["truncations"], a["retries"], a["denials"], a["refusal_stopped_agents"]), (6, 12, 9, 3))
        self.assertEqual(a["completion"], 0.75)

    def test_error_correlation_known_matrix(self):
        c = an.error_correlation({"a": [1, 1, 0, 0], "b": [1, 1, 0, 0], "c": [1, 0, 1, 0], "d": [0, 0, 0, 0]})
        self.assertAlmostEqual(c[("a", "b")], 1.0)
        self.assertAlmostEqual(c[("a", "c")], 0.0)
        self.assertIsNone(c[("a", "d")])
        anti = an.error_correlation({"a": [1, 0, 1, 0], "b": [0, 1, 0, 1]})
        self.assertAlmostEqual(anti[("a", "b")], -1.0)

    def test_agreement_and_identical_wrong(self):
        ans = lambda g: [{"agent": a, "task": t, "answer": x, "pass": ok} for a, t, x, ok in g]
        r = rec("none", "s", .5, agent_answers=ans([("a", 1, "x", False), ("b", 1, "x", False), ("a", 2, "y", True),
                                                    ("b", 2, "y", True), ("a", 3, "p", False), ("b", 3, "q", False)]))
        p = an.summarise([r])["exploratory"]["per_arm"]["none"]["agent_pairs"][("a", "b")]
        self.assertEqual((p["items"], p["agree"], p["identical_wrong"]), (3, 2, 1))

    def test_slot_phi_withheld_and_shared_answers_exclude_unscored_records(self):
        wrong = [{"agent": agent, "task": 1, "answer": 0, "pass": False} for agent in ("a0", "a1")]
        right = [{"agent": agent, "task": 1, "answer": 1, "pass": True} for agent in ("a0", "a1")]
        good = [
            rec("none", "stopped", 0, ended="episode_stopped", agent_answers=wrong),
            rec("none", "complete", .25, agent_answers=right),
        ]
        exclusions = [
            {"void": "action_boundary"},
            {"ended": "infrastructure_abort"},
            {"valid": False},
            {"scores": {"valid": False}},
            {"status": "void:invalid_log"},
            {"abort_reason": "infrastructure_abort"},
            {"Y": None},
        ]
        bad = [
            rec("none", f"excluded{i}", .25, agent_answers=[right[0], wrong[1]], **fields)
            for i, fields in enumerate(exclusions)
        ]
        summary = an.summarise(good + bad)
        none = summary["exploratory"]["per_arm"]["none"]
        self.assertEqual(none["agent_pairs"][("a0", "a1")]["items"], 2)
        self.assertAlmostEqual(none["agent_pairs"][("a0", "a1")]["phi"], 1)
        self.assertIsNone(none["slot_miss_phi"]["mean"])
        rendered = an.render(summary)
        self.assertIn("slot-miss phi withheld", rendered)
        self.assertNotIn("mean pairwise error phi", rendered)

    def test_determinism_by_seed(self):
        rs = [rec(a, f"s{i}", min(1, max(0, v + 0.05 * ((i * 7) % 5 - 2))))
              for i in range(12) for a, v in (("none", .2), ("play", .5), ("code", .8))]
        a = an.summarise(rs, seed=3, n_boot=300)
        self.assertEqual(a, an.summarise(rs, seed=3, n_boot=300))
        self.assertNotEqual(a["hdi"]["contrasts"], an.summarise(rs, seed=4, n_boot=300)["hdi"]["contrasts"])

    def test_unresolved_contrast_note_with_interpretable_hdi(self):
        t = an.render(an.summarise(batch(0.2, 0.2, 0.8)))  # play_none is 0 (unresolved); HDI = 1 interpretable
        self.assertIn("HDI 1.000", t)
        self.assertIn("Note: inconclusive is neither equivalence nor a null finding", t)

    def test_fewer_than_twelve_task_sets_show_no_contrast(self):
        """prereg section 10: with fewer than 12 complete sets every contrast reads 'incomplete: not shown'."""
        small, ok = an.summarise(batch(0.2, 0.5, 0.8, k=11), n_boot=50), an.summarise(batch(0.2, 0.5, 0.8), n_boot=50)
        self.assertEqual((small["shown"], ok["shown"], small["min_task_sets"]), (False, True, 12))
        for k, _ in an.CONTRASTS:
            c = small["contrasts"][k]
            self.assertEqual((c["label"], c["point"], c["ci_boot"], c["resolved"]), (an.NOT_SHOWN, None, None, "unresolved"))
            self.assertIsNone(c["ci_t"])
            self.assertEqual(small["hdi"]["contrasts"][k], {"d": None, "lo": None, "hi": None})
            self.assertIsNone(small["exploratory"]["paired_t"][k])
            self.assertNotEqual(ok["contrasts"][k]["label"], an.NOT_SHOWN)
        self.assertEqual((small["hdi_block"]["interpretable"], small["hdi_block"]["reason"]), (False, an.NOT_SHOWN))
        self.assertEqual(small["hdi"]["reason"], an.NOT_SHOWN)
        for key in ("point", "lo", "hi", "denom_ci", "recovered", "degenerate_resamples"):
            self.assertIsNone(small["hdi"][key])
        text = an.render(small)
        self.assertEqual(text.count(an.NOT_SHOWN), 4)  # three contrasts and the HDI line
        self.assertNotIn("+0.300", text)
        self.assertNotIn("+0.600", text)
        self.assertFalse(any(line.startswith("paired t") for line in text.splitlines()))
        self.assertIn("paired t Y_play - Y_none: mean +0.300", an.render(ok))

    def test_smaller_than_the_effect_of_interest_label_and_kill(self):
        """prereg sections 11 and 12: hi < 0.20 in both intervals labels the contrast; on the primary it is the kill."""
        tiny = an.summarise(batch(0.5, 0.52, 0.9), n_boot=200)  # play_none d = 0.02, both intervals far below 0.20
        c = tiny["contrasts"]["play_none"]
        self.assertTrue(c["smaller_than_effect_of_interest"])
        self.assertEqual(tiny["kill"], {"fires": True, "code_rule_stays": True})
        t = an.render(tiny)
        self.assertIn(an.SMALLER, [l for l in t.splitlines() if l.startswith("Y_play - Y_none")][0])
        self.assertIn("Kill read-off", t)
        self.assertIn("the rule stays in code", t)
        big = an.summarise(batch(0.5, 0.75, 0.9), n_boot=200)  # d = 0.25: hi above 0.20
        self.assertFalse(big["contrasts"]["play_none"]["smaller_than_effect_of_interest"])
        self.assertFalse(big["kill"]["fires"])
        self.assertNotIn("Kill read-off", an.render(big))
        rs = [rec(a, f"s{i}", v + (0.05 if i % 2 else -0.05) * (a == "play"))
              for i in range(12) for a, v in (("none", .5), ("play", .68), ("code", .9))]
        es = an.summarise(rs, n_boot=200)
        edge = es["contrasts"]["play_none"]  # d = 0.18, t interval hi just above 0.20
        self.assertGreater(edge["ci_t"][1], an.SOI)
        self.assertFalse(edge["hi_below_soi_both"])
        self.assertFalse(es["kill"]["fires"])  # kill needs both intervals (section 12)
        # ruling 3: the label follows the cluster-bootstrap upper bound alone
        self.assertEqual(edge["smaller_than_effect_of_interest"], edge["ci_boot"][1] < an.SOI)

    def test_label_uses_bootstrap_alone_kill_uses_both(self):
        """Ruling 3 vs section 12, on a contrast record where the two intervals straddle 0.20."""
        c = an._contrast("play_none", {"d": 0.1, "lo": 0.0, "hi": 0.19}, {"ci95_lo": -0.01, "ci95_hi": 0.21},
                         False, True)
        self.assertEqual((c["smaller_than_effect_of_interest"], c["hi_below_soi_both"]), (True, False))
        c = an._contrast("play_none", {"d": 0.1, "lo": 0.0, "hi": 0.21}, {"ci95_lo": -0.01, "ci95_hi": 0.19},
                         False, True)
        self.assertEqual((c["smaller_than_effect_of_interest"], c["hi_below_soi_both"]), (False, False))

    def test_every_secondary_read_off_is_labelled_exploratory(self):
        r = lambda a, i, y: rec(a, f"s{i}", y, scores={"name_collisions": 1},  # noqa: E731
                                scorers={"alloc2": {"done_releases": 2, "false_done": 1 if a == "play" else 0}},
                                orders={"claim_collision_rate": 0.5})
        s = an.summarise([r(a, i, v) for i in range(12) for a, v in (("none", .2), ("play", .5), ("code", .8))], n_boot=50)
        self.assertEqual(s["exploratory"]["label"], an.EXPLORATORY)
        self.assertEqual(s["hdi_block"]["label"], an.EXPLORATORY)
        self.assertEqual([s["contrasts"][k]["exploratory"] for k, _ in an.CONTRASTS], [False, True, True])
        p = s["exploratory"]["per_arm"]["play"]
        self.assertEqual((p["false_done"], p["done_releases"], p["false_done_rate"], p["name_collisions"],
                          p["claim_collision_rate"]), (12, 24, 0.5, 12, 0.5))
        self.assertIsNone(an.summarise([rec("none", "s", .5)])["exploratory"]["per_arm"]["none"]["false_done_rate"])
        lines = an.render(s).splitlines()
        sec = lines[next(i for i, l in enumerate(lines) if l.startswith("Secondary")):]
        for l in [l for l in lines if l.startswith(("Y_code", "HDI", "paired t"))] + sec[1:-1]:
            self.assertTrue(l.endswith("[exploratory]"), l)
        self.assertFalse(lines[[l.startswith("Y_play - Y_none") for l in lines].index(True)].endswith("[exploratory]"))
        self.assertTrue(any(l.startswith("paired t Y_play - Y_none") for l in sec))
        self.assertEqual(sec[-1], an.RELEASE_NOTE)

    def test_all_agents_stopped_episodes_stay_in_with_their_y(self):
        """Intention to treat (G1b-R R-5 ruling): an episode ended because every agent was stopped is scored from its
        log and counted per arm; no task set leaves the analysis for it, so every arm keeps the same 20 sets."""
        rs = [rec(a, f"s{i}", 0.0 if a == "code" and i < 15 else v, ended="episode_stopped" if a == "code" and i < 15
                  else "complete", stopped_agents=["a0", "a1", "a2", "a3"] if a == "code" and i < 15 else [])
              for i in range(20) for a, v in (("none", .5), ("play", .5), ("code", 1.0))]
        s = an.summarise(rs, n_boot=200)
        self.assertEqual(s["n_task_sets_all_arms"], 20)
        self.assertEqual({a: (p["task_sets"], p["censored_task_sets"]) for a, p in s["arms"].items()},
                         {a: (20, 0) for a in ("none", "play", "code")})
        self.assertEqual([s["arms"][a]["all_agents_stopped"] for a in ("none", "play", "code")], [0, 0, 15])
        self.assertAlmostEqual(s["contrasts"]["code_none"]["point"], (5 * 1.0 + 15 * 0.0) / 20 - 0.5)
        self.assertIn("all_stopped", an.render(s))

    def test_render(self):
        t = an.render(an.summarise(batch(0.5, 0.5, 0.5)))
        self.assertTrue(t.startswith(an.PRIOR_ART))
        self.assertIn("inconclusive is neither equivalence nor a null finding", t)
        self.assertIn("not resolved: inconclusive", t)
        self.assertNotIn("inconclusive is neither", an.render(an.summarise(batch(0.2, 0.5, 0.8))).split("HDI")[0])


class RefusalRowsTests(unittest.TestCase):
    """Pre-freeze change 15: refusals per arm in two rows, `A:*` and `board_error:*`, never one summed column."""

    def test_two_rows_per_arm_and_no_summed_column(self):
        rs = [rec("code", "s1", .5, refusals=[["a1", "A:duplicate_claim:t0"], ("a2", "A:x"), ("a1", "board_error:KeyError")]),
              rec("none", "s1", .5, refusals=[["a3", "board_error:ValueError"]]),
              rec("play", "s1", .5, refusals=[["a0", "something_else"]])]
        s = an.summarise(rs)
        self.assertEqual(s["arms"]["code"]["refusal_rows"], {"A": 2, "board_error": 1, "other": 0})
        self.assertEqual(s["arms"]["none"]["refusal_rows"], {"A": 0, "board_error": 1, "other": 0})
        self.assertEqual(s["arms"]["play"]["refusal_rows"]["other"], 1)  # an unknown label is shown, never dropped
        text = an.render(s)
        self.assertNotIn("denials", text)
        self.assertRegex(text, r"(?m)^code A:\*\s+2$")
        self.assertRegex(text, r"(?m)^code board_error:\*\s+1$")
        self.assertIn("never summed", text)


if __name__ == "__main__":
    unittest.main()
