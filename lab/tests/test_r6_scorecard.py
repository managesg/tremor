from copy import deepcopy
import json
from pathlib import Path
import re
import unittest

from lab import r6_scorecard as sc

PLAN = Path(__file__).resolve().parents[2] / "prereg" / "R6-pvsnp-research-line-plan.md"
KW = ("lean-checked 2^{n/",)
PAT = (r"proof of p\s*(vs|!=|≠|=)\s*np", r"probability[^.]*resolv")


def template():
    text = PLAN.read_text(encoding="utf-8")
    block = re.search(r"```json\n(.*?)\n```", text, re.S).group(1)
    return json.loads(block)


W = {"barrier_compliance": 0.25, "formal_precision": 0.20, "falsifiability": 0.25,
     "verifiability": 0.15, "incremental_value": 0.15}
# Every `a|b|c` option list in the template needs an explicit choice here; an unlisted one is an error.
CHOICES = {
    "proposer|red_team|control_solver|definition_auditor|solver": "proposer",
    "circuit|algebraic|meta_complexity|proof_complexity|fine_grained|descriptive": "circuit",
    "lower_bound|upper_bound|reduction|finite_lemma|formal_statement": "lower_bound",
    "multitape_tm|ram|uniform_circuit|nonuniform_circuit|arithmetic_circuit|proof_system": "multitape_tm",
    "bit_length_N|variables_n|clauses_m|truth_table_2^n|matrix_dim_n": "variables_n",
    "refuted|not_refuted|not_testable_at_small_n|na": "na",
    "checked_by_oracle|proved_in_artifact|cited_classical|citation_to_be_verified|recalled_unverified"
    "|from_briefing_unverified|conjecture": "checked_by_oracle",
    "evades|hits|not_applicable|open": "open",
    "pass|fail|na": "na",
    "pass|fail": "pass",
    "F1|F2|F3|F4|F5|F6": "F1",
    "advance|revise|prune": "revise",
    "true|false": False,
}


def fill(x):
    """Replace every `a|b|c` option list by an explicit choice."""
    if isinstance(x, dict):
        return {k: fill(v) for k, v in x.items()}
    if isinstance(x, list):
        return [fill(v) for v in x]
    if isinstance(x, str) and "|" in x:
        if x == "refuted|not_refuted|na":
            return "na"
        return CHOICES[x]
    return x


def V(c):
    return sc.validate(c, weights=W)


def good():
    """A valid lower-bound card that passes every gate."""
    c = fill(template())
    c["reviewer"]["overclaim_flag"] = False
    c["candidate_id"] = "cand-1"
    c["statement"] = "a finite statement"
    c["claim_type"] = "lower_bound"
    for k in ("relativization", "natural_proofs", "algebrization"):
        c["barrier_audit"][k].update(status="evades", argument="written mechanism")
    c["claims"] = [{"id": "c1", "text": "x", "status": "checked_by_oracle", "evidence": "e"}]
    c["oracle_checks"].update(claims_checkable=1, claims_checked=1, claims_passed=1)
    c["separations"] = {"asymptotic_vs_practical": "text", "worst_vs_average_case": "text"}
    for k, s in zip(sc.CRITERIA, (5, 4, 3, 2, 1)):
        c["criteria"][k]["score"] = s
    c["hard_gates"] = {"G1_barrier": "pass", "G2_unverified_as_fact": "pass", "G3_overclaim": "pass",
                       "G4_model_parameter": "pass", "G5_separation": "pass", "G6_definition_audit": "na"}
    c["weighted_total"] = 100 * (0.25 * 5 + 0.20 * 4 + 0.25 * 3 + 0.15 * 2 + 0.15 * 1) / 5
    c["verdict"] = "revise"
    return c


def run(c, kw=KW, pat=PAT, w=W):
    return sc.score(c, weights=w, briefing_keywords=kw, overclaim_patterns=pat)


def gate_of(c, name, **kw):
    r = run(c, **kw)
    assert r["valid"], r["reasons"]
    return r["gates"][name]


class Schema(unittest.TestCase):
    def test_template_round_trips(self):
        c = fill(template())
        self.assertEqual(V(c), [])
        self.assertEqual(V(json.loads(json.dumps(c))), [])
        self.assertEqual(json.loads(json.dumps(c)), c)

    def test_good_is_valid_and_clean(self):
        c = good()
        self.assertEqual(V(c), [])
        r = run(c)
        self.assertTrue(r["valid"])
        self.assertFalse(r["disqualified"])
        self.assertEqual(r["reasons"], [])
        self.assertEqual(r["declared_mismatch"], [])
        self.assertEqual(r["gates"]["G6_definition_audit"], "na")

    def bad(self, mutate, needle=None):
        c = good()
        mutate(c)
        errs = V(c)
        self.assertTrue(errs, "expected a refusal")
        if needle:
            self.assertTrue(any(needle in e for e in errs), errs)
        return c

    def test_refuses_non_object_and_unknown_and_missing(self):
        for v in (None, [], "x", 3):
            self.assertTrue(V(v))
        self.bad(lambda c: c.update(extra=1), "unknown key")
        self.bad(lambda c: c["agent"].update(extra=1), "agent.extra")
        self.bad(lambda c: c["criteria"]["falsifiability"].update(extra=1), "unknown key")
        self.bad(lambda c: c.pop("separations"), "separations: missing")
        self.bad(lambda c: c["lean"].pop("sorry_count"), "lean.sorry_count: missing")

    def test_refuses_bool_nan_inf_and_strings_as_numbers(self):
        for bad in (True, False, float("nan"), float("inf"), float("-inf"), "3", None):
            self.bad(lambda c, b=bad: c["criteria"]["falsifiability"].update(score=b))
            self.bad(lambda c, b=bad: c["criteria"]["falsifiability"].update(weight=b))
        for bad in (True, float("nan"), float("inf"), 1.5, "1", None):
            self.bad(lambda c, b=bad: c["agent"].update(team_size=b))
            self.bad(lambda c, b=bad: c.update(iteration=b))
        self.bad(lambda c: c["resources"].update(wall_seconds=float("nan")))
        self.bad(lambda c: c["resources"].update(hosted_usd=True))
        self.bad(lambda c: c.update(weighted_total=float("nan")))

    def test_score_range_0_to_5(self):
        for s in (-0.1, 5.1, -1, 6, 2.5, 3.0):
            self.bad(lambda c, s=s: c["criteria"]["barrier_compliance"].update(score=s))
        for s in (0, 5, 3):
            c = good()
            c["criteria"]["barrier_compliance"]["score"] = s
            self.assertEqual(V(c), [])

    def test_card_weights_must_equal_frozen_weights(self):
        self.bad(lambda c: c["criteria"]["falsifiability"].update(weight=0.26), "frozen")
        self.bad(lambda c: c["criteria"]["falsifiability"].update(weight=0.0), "frozen")
        # a card that sums to 1.0 but swaps two weights is still refused
        self.bad(lambda c: (c["criteria"]["barrier_compliance"].update(weight=0.15),
                            c["criteria"]["incremental_value"].update(weight=0.25)), "frozen")
        c = good()
        c["criteria"]["falsifiability"]["weight"] = 0.25 + 1e-12
        self.assertEqual(V(c), [])
        self.bad(lambda c: c["criteria"]["falsifiability"].update(weight=-0.25), "weight")
        # another frozen set is honoured: weights are an input, not a constant
        w2 = {k: 0.2 for k in sc.CRITERIA}
        self.assertTrue(sc.validate(good(), weights=w2))
        c = good()
        for k in sc.CRITERIA:
            c["criteria"][k]["weight"] = 0.2
        self.assertEqual(sc.validate(c, weights=w2), [])
        self.assertTrue(V(c))

    def test_frozen_weights_themselves_refused_when_bad(self):
        for w in (None, {}, {**W, "falsifiability": 0.3}, {**W, "falsifiability": float("nan")},
                  {**W, "falsifiability": True}, {**W, "extra": 0.0}, {**W, "falsifiability": -0.25, "formal_precision": 0.7}):
            with self.assertRaises(ValueError):
                sc.validate(good(), weights=w)
        with self.assertRaises(TypeError):
            sc.validate(good())

    def test_criteria_set_is_exact(self):
        self.bad(lambda c: c["criteria"].pop("verifiability"), "missing")
        self.bad(lambda c: c["criteria"].update(bonus={"score": 0, "weight": 0.0, "evidence": ""}), "unknown key")

    def test_enums(self):
        self.bad(lambda c: c.update(lens="graph"))
        self.bad(lambda c: c.update(claim_type="a|b"))
        self.bad(lambda c: c.update(verdict="maybe"))
        self.bad(lambda c: c["agent"].update(role="x"))
        self.bad(lambda c: c["barrier_audit"]["algebrization"].update(status="unknown"))
        self.bad(lambda c: c["hard_gates"].update(G2_unverified_as_fact="na"))
        self.bad(lambda c: c["hard_gates"].update(G1_barrier="PASS"))
        self.bad(lambda c: c["performance_row"].update(family="F7"))
        self.bad(lambda c: c["claims"][0].update(status="proved"))
        self.bad(lambda c: c.update(schema_version="r6-scorecard-1"))
        self.bad(lambda c: c.update(line="R5"))

    def test_g5_g6_g1_accept_na_status(self):
        c = good()
        c["hard_gates"].update(G1_barrier="na", G5_separation="na", G6_definition_audit="na")
        self.assertEqual(V(c), [])

    def test_performance_row_pass_and_conf(self):
        for v in (True, 2, -1, 1.0, "1", None):
            self.bad(lambda c, v=v: c["performance_row"].update(**{"pass": v}))
        for v in (-0.1, 1.1, True, float("nan")):
            self.bad(lambda c, v=v: c["performance_row"].update(conf=v))

    def test_cross_field_rules(self):
        self.bad(lambda c: c["claims"].append(dict(c["claims"][0])), "duplicate id")
        self.bad(lambda c: c["small_n_claim"].update(result="refuted"), "refuted")
        self.bad(lambda c: c["small_n_claim"].update(result="refuted", explicit_constants=True,
                                                     threshold_n0=21), "refuted")
        c = good()
        c["small_n_claim"].update(result="refuted", explicit_constants=True, threshold_n0=20)
        self.assertEqual(V(c), [])
        self.bad(lambda c: c["oracle_checks"].update(claims_passed=2), "oracle_checks")
        self.bad(lambda c: c["oracle_checks"].update(claims_checkable=0), "oracle_checks")
        self.bad(lambda c: c["red_team"].update(label_overridden=True), "red_team")
        c = good()
        c["red_team"].update(label_overridden=True, counterexample_verified=True)
        self.assertEqual(V(c), [])

    def test_sha_and_spans(self):
        self.bad(lambda c: c["predicate"].update(sha256="abc"))
        self.bad(lambda c: c["predicate"].update(sha256="A" * 64))
        self.bad(lambda c: c["definition_audit"].update(defect_spans=[[1]]))
        c = good()
        c["predicate"]["sha256"] = "a" * 64
        c["definition_audit"]["defect_spans"] = ["q", [3, 7]]
        self.assertEqual(V(c), [])

    def test_invalid_score_result_shape(self):
        c = good()
        c["criteria"]["falsifiability"]["score"] = float("nan")
        r = run(c)
        self.assertFalse(r["valid"])
        self.assertTrue(r["disqualified"])
        self.assertIsNone(r["gates"])
        self.assertIsNone(r["weighted_total"])
        self.assertTrue(r["reasons"])


class G1(unittest.TestCase):
    def card(self, claim_type, **audit):
        c = good()
        c["claim_type"] = claim_type
        for k, (st, arg) in audit.items():
            c["barrier_audit"][k].update(status=st, argument=arg)
        return c

    def test_lower_bound_each_entry_each_status(self):
        for k in ("relativization", "natural_proofs", "algebrization"):
            for st, arg, want in (("evades", "m", "pass"), ("not_applicable", "r", "pass"),
                                  ("evades", "", "fail"), ("evades", "  \n", "fail"),
                                  ("not_applicable", "", "fail"), ("hits", "m", "fail"),
                                  ("open", "m", "fail")):
                self.assertEqual(gate_of(self.card("lower_bound", **{k: (st, arg)}), "G1_barrier"), want,
                                 (k, st, arg))

    def test_upper_bound_checks_only_relativization(self):
        self.assertEqual(gate_of(self.card("upper_bound", natural_proofs=("hits", ""),
                                           algebrization=("open", "")), "G1_barrier"), "pass")
        for st, arg in (("hits", "m"), ("open", "m"), ("evades", ""), ("not_applicable", " ")):
            self.assertEqual(gate_of(self.card("upper_bound", relativization=(st, arg)), "G1_barrier"), "fail")

    def test_other_claim_types_na(self):
        for ct in ("reduction", "finite_lemma", "formal_statement"):
            c = self.card(ct, relativization=("open", ""), natural_proofs=("hits", ""))
            if ct == "formal_statement":
                c["definition_audit"].update(done=True, faithful=True)
            self.assertEqual(gate_of(c, "G1_barrier"), "na")
            self.assertFalse(run(c)["disqualified"])

    def test_reasons_name_failing_entries(self):
        r = run(self.card("lower_bound", algebrization=("open", "")))
        self.assertTrue(r["disqualified"])
        self.assertTrue(any(x.startswith("G1") and "algebrization" in x and "relativization" not in x
                            for x in r["reasons"]), r["reasons"])


class G2to6(unittest.TestCase):
    def test_g2_missing_status(self):
        c = good()
        c["claims"][0]["status"] = None
        self.assertEqual(gate_of(c, "G2_unverified_as_fact"), "fail")

    def test_g2_oracle_rerun(self):
        c = good()
        c["oracle_checks"].update(claims_checked=1, claims_passed=0)
        self.assertEqual(gate_of(c, "G2_unverified_as_fact"), "fail")
        c = good()
        c["oracle_checks"].update(claims_checkable=1, claims_checked=0, claims_passed=0)
        self.assertEqual(gate_of(c, "G2_unverified_as_fact"), "fail")
        c = good()
        c["claims"][0]["status"] = "conjecture"
        c["oracle_checks"].update(claims_checked=0, claims_passed=0)
        self.assertEqual(gate_of(c, "G2_unverified_as_fact"), "pass")

    def test_g2_briefing_keyword(self):
        c = good()
        c["claims"][0].update(text="Uses Lean-Checked 2^{n/sqrt(log n)} counting", status="checked_by_oracle")
        self.assertEqual(gate_of(c, "G2_unverified_as_fact"), "fail")
        c["claims"][0]["status"] = "from_briefing_unverified"
        c["oracle_checks"].update(claims_checked=0, claims_passed=0)
        self.assertEqual(gate_of(c, "G2_unverified_as_fact"), "pass")
        c["claims"][0]["text"] = "nothing special"
        c["claims"][0]["status"] = "conjecture"
        self.assertEqual(gate_of(c, "G2_unverified_as_fact"), "pass")

    def test_g3(self):
        for field in ("statement",):
            c = good()
            c[field] = "We give a Proof of P != NP here"
            self.assertEqual(gate_of(c, "G3_overclaim"), "fail")
        c = good()
        c["claims"][0]["text"] = "the probability that we resolve it is high"
        c["claims"][0]["status"] = "conjecture"
        self.assertEqual(gate_of(c, "G3_overclaim"), "fail")
        c = good()
        c["criteria"]["falsifiability"]["evidence"] = "proof of P = NP"
        self.assertEqual(gate_of(c, "G3_overclaim"), "fail")
        self.assertEqual(gate_of(good(), "G3_overclaim"), "pass")
        c = good()
        c["reviewer"]["overclaim_flag"] = True
        r = run(c)
        self.assertEqual(r["gates"]["G3_overclaim"], "fail")
        self.assertTrue(r["disqualified"])
        self.assertEqual(r["weighted_total"], 0.0)

    def test_g3_scans_claim_evidence(self):
        c = good()
        c["claims"][0]["evidence"] = "a proof of P vs NP"
        self.assertEqual(gate_of(c, "G3_overclaim"), "fail")

    def test_unicode_cannot_hide_keywords_or_patterns(self):
        c = good()
        c["claims"][0]["text"] = "LEAN\u2011CHECKED 2^{n/ counting"  # non-breaking hyphen, caps
        self.assertEqual(gate_of(c, "G2_unverified_as_fact"), "fail")
        c["claims"][0]["text"] = "\uff4c\uff45\uff41\uff4e-checked 2^{n/ counting"  # full-width letters
        self.assertEqual(gate_of(c, "G2_unverified_as_fact"), "fail")
        c = good()
        c["statement"] = "\uff4c\uff45\uff41\uff4e\u2011checked 2^{n/ x"
        self.assertEqual(gate_of(c, "G2_unverified_as_fact"), "fail")
        c = good()
        c["statement"] = "a \uff50\uff52\uff4f\uff4f\uff46 of P vs NP"
        self.assertEqual(gate_of(c, "G3_overclaim"), "fail")
        c["statement"] = "a proof\u00a0of P vs NP"  # no-break space
        self.assertEqual(gate_of(c, "G3_overclaim"), "fail")
        c["statement"] = "fine"
        self.assertEqual(gate_of(c, "G3_overclaim", kw=("LEAN\u2011checked",)), "pass")
        c["statement"] = "a proof-of-concept of P vs NP"
        for bad in ("[x\u2013z]", "\uff3bxz]", "proof\u2011of", "\uff50roof"):
            with self.assertRaises(ValueError):
                run(c, pat=(bad,))
        self.assertEqual(gate_of(c, "G3_overclaim", pat=(r"proof\-of\-concept",)), "fail")  # escaped ASCII dash
        self.assertEqual(gate_of(c, "G3_overclaim", pat=(r"[a-z]+\-of",)), "fail")
        c["statement"] = "a proof\u2011of\u2011concept"  # text side is still normalised
        self.assertEqual(gate_of(c, "G3_overclaim", pat=(r"proof\-of\-concept",)), "fail")
        c["statement"] = "x"
        c["claims"][0]["text"] = "lean-checked 2^{n/"
        self.assertEqual(gate_of(c, "G2_unverified_as_fact", kw=("Lean\u2011Checked",)), "fail")

    def test_g4(self):
        for field, val in (("model_of_computation", ""), ("model_of_computation", "quantum_tm"),
                           ("input_parameter", ""), ("input_parameter", "n")):
            c = good()
            c[field] = val
            self.assertEqual(gate_of(c, "G4_model_parameter"), "fail", (field, val))
        for m in sc.MODELS:
            c = good()
            c["model_of_computation"] = m
            self.assertEqual(gate_of(c, "G4_model_parameter"), "pass")
        for p in sc.PARAMS:
            c = good()
            c["input_parameter"] = p
            self.assertEqual(gate_of(c, "G4_model_parameter"), "pass")

    def test_g5(self):
        for k in ("asymptotic_vs_practical", "worst_vs_average_case"):
            for v in ("", "  "):
                c = good()
                c["separations"][k] = v
                self.assertEqual(gate_of(c, "G5_separation"), "fail")
                c["claim_type"] = "finite_lemma"
                self.assertEqual(gate_of(c, "G5_separation"), "na")
        self.assertEqual(gate_of(good(), "G5_separation"), "pass")

    def test_g6(self):
        for done, faithful, want in ((True, True, "pass"), (True, False, "fail"), (False, True, "fail"),
                                     (True, None, "fail"), (False, None, "fail")):
            c = good()
            c["claim_type"] = "formal_statement"
            c["definition_audit"].update(done=done, faithful=faithful)
            self.assertEqual(gate_of(c, "G6_definition_audit"), want, (done, faithful))
        c = good()
        c["definition_audit"].update(done=False, faithful=False)
        self.assertEqual(gate_of(c, "G6_definition_audit"), "na")


class Total(unittest.TestCase):
    def test_weighted_total(self):
        self.assertAlmostEqual(run(good())["weighted_total"], 100 * (1.25 + 0.8 + 0.75 + 0.3 + 0.15) / 5)

    def test_custom_weights_and_extremes(self):
        c = good()
        w2 = dict(zip(sc.CRITERIA, (0.5, 0.5, 0, 0, 0)))
        for k, w, s in zip(sc.CRITERIA, (0.5, 0.5, 0, 0, 0), (5, 5, 0, 0, 0)):
            c["criteria"][k].update(weight=w, score=s)
        self.assertAlmostEqual(run(c, w=w2)["weighted_total"], 100.0)
        self.assertFalse(run(c)["valid"])  # not the frozen weights
        for k in sc.CRITERIA:
            c["criteria"][k].update(score=0)
        self.assertEqual(run(c, w=w2)["weighted_total"], 0.0)

    def test_total_uses_frozen_weights(self):
        c = good()
        c["criteria"]["falsifiability"]["weight"] = 0.25 + 5e-10  # within tolerance of the frozen weight
        exact = 100 * (0.25 * 5 + 0.20 * 4 + 0.25 * 3 + 0.15 * 2 + 0.15 * 1) / 5
        self.assertEqual(run(c)["weighted_total"], run(good())["weighted_total"])
        self.assertAlmostEqual(run(c)["weighted_total"], exact, places=12)

    def test_each_weight_matters(self):
        base = run(good())["weighted_total"]
        for k in sc.CRITERIA:
            c = good()
            c["criteria"][k]["score"] = 0
            self.assertLess(run(c)["weighted_total"], base, k)

    def test_gate_failure_zeroes_total_and_sets_disqualified(self):
        c = good()
        c["model_of_computation"] = ""
        r = run(c)
        self.assertTrue(r["disqualified"])
        self.assertEqual(r["weighted_total"], 0.0)
        self.assertTrue(any(x.startswith("G4") for x in r["reasons"]))

    def test_gate_failure_never_changes_pass(self):
        c = good()
        c["performance_row"]["pass"] = 1
        c["claim_type"] = "formal_statement"  # G6 fails: no audit
        before = deepcopy(c)
        r = run(c)
        self.assertTrue(r["disqualified"])
        self.assertEqual(c, before)
        self.assertEqual(c["performance_row"]["pass"], 1)
        self.assertNotIn("pass", r)
        self.assertNotIn("performance_row", r)
        c["performance_row"]["pass"] = 0
        c["model_of_computation"] = "bad"
        self.assertEqual(run(c)["gates"], {**run(c)["gates"]})
        self.assertEqual(c["performance_row"]["pass"], 0)

    def test_declared_mismatch_reported_not_trusted(self):
        c = good()
        c["hard_gates"]["G1_barrier"] = "fail"
        c["weighted_total"] = 99.0
        c["disqualified"] = True
        r = run(c)
        self.assertEqual(r["declared_mismatch"], ["G1_barrier", "weighted_total", "disqualified"])
        self.assertFalse(r["disqualified"])

    def test_advance_on_disqualified_card_is_invalid(self):
        c = good()
        c["model_of_computation"] = ""
        c["verdict"] = "advance"
        r = run(c)
        self.assertFalse(r["valid"])
        self.assertTrue(r["disqualified"])
        self.assertEqual(r["weighted_total"], 0.0)
        self.assertTrue(any("verdict" in x for x in r["errors"]))
        self.assertEqual(r["gates"]["G4_model_parameter"], "fail")
        c["verdict"] = "revise"
        self.assertTrue(run(c)["valid"])
        c = good()
        c["verdict"] = "advance"
        self.assertTrue(run(c)["valid"])

    def test_deterministic_and_pure(self):
        c = good()
        before = deepcopy(c)
        self.assertEqual(run(c), run(c))
        self.assertEqual(c, before)


class Inputs(unittest.TestCase):
    def test_open_parameters_are_required(self):
        with self.assertRaises(TypeError):
            sc.score(good())
        with self.assertRaises(TypeError):
            sc.score(good(), briefing_keywords=("a",), overclaim_patterns=("a",))
        with self.assertRaises(TypeError):
            sc.score(good(), weights=W, briefing_keywords=("a",))
        with self.assertRaises(TypeError):
            run_with_old_kwarg = dict(weights=W, briefing_keywords=("a",), overclaim_patterns=("a",),
                                      reviewer_overclaim=False)
            sc.score(good(), **run_with_old_kwarg)

    def test_bad_and_empty_lists_refused(self):
        for kw in ("abc", [""], [1], None, [], ()):
            with self.assertRaises(ValueError):
                run(good(), kw=kw)
            with self.assertRaises(ValueError):
                run(good(), pat=kw)

    def test_reviewer_flag_is_a_required_bool_on_the_card(self):
        for v in (1, None, "true"):
            c = good()
            c["reviewer"]["overclaim_flag"] = v
            self.assertTrue(V(c))
        c = good()
        del c["reviewer"]["overclaim_flag"]
        self.assertTrue(V(c))


class Rulings(unittest.TestCase):
    def test_g2_scans_claim_evidence(self):
        c = good()
        c["claims"][0]["evidence"] = "per Lean-Checked 2^{n/sqrt(log n)}"
        self.assertEqual(gate_of(c, "G2_unverified_as_fact"), "fail")
        c["claims"][0]["status"] = "from_briefing_unverified"
        c["oracle_checks"].update(claims_checked=0, claims_passed=0)
        self.assertEqual(gate_of(c, "G2_unverified_as_fact"), "pass")

    def test_g2_statement_needs_a_covering_briefing_claim(self):
        c = good()
        c["statement"] = "builds on lean-checked 2^{n/ counting"
        self.assertEqual(gate_of(c, "G2_unverified_as_fact"), "fail")
        c["claims"].append({"id": "c2", "text": "other", "status": "from_briefing_unverified", "evidence": ""})
        self.assertEqual(gate_of(c, "G2_unverified_as_fact"), "fail")  # does not carry the same keyword
        c["claims"][1]["evidence"] = "the Lean-Checked 2^{n/ item"
        self.assertEqual(gate_of(c, "G2_unverified_as_fact"), "pass")
        c["claims"][1]["status"] = "conjecture"  # same keyword but not marked
        self.assertEqual(gate_of(c, "G2_unverified_as_fact"), "fail")

    def test_empty_status_is_g2_failure_not_schema_error(self):
        c = good()
        c["claims"][0]["status"] = ""
        self.assertEqual(V(c), [])
        self.assertEqual(gate_of(c, "G2_unverified_as_fact"), "fail")
        c["claims"][0]["status"] = None
        self.assertEqual(gate_of(c, "G2_unverified_as_fact"), "fail")

    def test_span_start_after_end_refused(self):
        c = good()
        c["definition_audit"]["defect_spans"] = [[7, 3]]
        self.assertTrue(V(c))
        c["definition_audit"]["defect_spans"] = [[3, 3]]
        self.assertEqual(V(c), [])

    def test_fill_rejects_unlisted_option_lists(self):
        with self.assertRaises(KeyError):
            fill({"x": "a|b"})


if __name__ == "__main__":
    unittest.main()
