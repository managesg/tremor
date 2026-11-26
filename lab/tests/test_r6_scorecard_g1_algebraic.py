"""G1 regression fixture: an algebraic lower-bound card with open relativization and algebrization.

Plan: docs/reports/tremor/VPVNP_TREMOR_INTEGRATION_PLAN.md section 2 (G1 fixture) and R6-O29.
The scorecard is not touched; a gate failure zeroes the rubric total and never changes `pass`.
"""
from copy import deepcopy
import unittest

from lab.tests.test_r6_scorecard import V, good, run


def card(rel=("open", "not yet analysed"), alg=("open", "not yet analysed"),
         nat=("evades", "written natural-proofs argument"), claim_type="lower_bound"):
    c = good()
    c["lens"] = "algebraic"
    c["claim_type"] = claim_type
    c["lean"]["kernel_checked"] = False
    c["performance_row"]["pass"] = 1
    for k, (st, arg) in (("relativization", rel), ("natural_proofs", nat), ("algebrization", alg)):
        c["barrier_audit"][k].update(status=st, argument=arg)
    # declare what the scorecard recomputes, so declared_mismatch stays empty
    g = run(c)["gates"]
    c["hard_gates"] = dict(g)
    c["disqualified"] = "fail" in g.values()
    c["weighted_total"] = 0.0 if c["disqualified"] else c["weighted_total"]
    return c


def g1(c):
    r = run(c)
    assert r["valid"], r["errors"]
    return r["gates"]["G1_barrier"]


class G1Algebraic(unittest.TestCase):
    def test_fixture_is_well_formed(self):
        c = card()
        self.assertEqual(c["lens"], "algebraic")
        self.assertEqual(c["claim_type"], "lower_bound")
        self.assertFalse(c["lean"]["kernel_checked"])
        self.assertEqual(V(c), [])

    def test_open_barriers_fail_g1_and_disqualify(self):
        r = run(card())
        self.assertTrue(r["valid"], r["errors"])
        self.assertEqual(r["gates"]["G1_barrier"], "fail")
        self.assertTrue(r["disqualified"])
        self.assertEqual(r["weighted_total"], 0.0)
        self.assertTrue(any(s.startswith("G1:") and "relativization" in s and "algebrization" in s
                            for s in r["reasons"]), r["reasons"])
        self.assertEqual(r["declared_mismatch"], [])

    def test_gate_failure_does_not_change_pass(self):
        c = card()
        before = deepcopy(c)
        r = run(c)
        self.assertEqual(r["gates"]["G1_barrier"], "fail")
        self.assertEqual(c, before)
        self.assertEqual(c["performance_row"]["pass"], 1)
        self.assertNotIn("pass", r)
        # the rubric total is zeroed, the pass flag is not
        self.assertEqual(r["weighted_total"], 0.0)

    def test_evades_passes(self):
        self.assertEqual(g1(card(("evades", "m"), ("evades", "m"))), "pass")

    def test_not_applicable_with_reason_passes(self):
        c = card(("not_applicable", "arithmetic circuits have no Boolean oracle"),
                 ("not_applicable", "no algebraic extension to define"))
        self.assertEqual(g1(c), "pass")
        self.assertFalse(run(c)["disqualified"])

    def test_not_applicable_without_reason_fails(self):
        for empty in ("", "   "):
            self.assertEqual(g1(card(("not_applicable", empty), ("evades", "m"))), "fail")
            self.assertEqual(g1(card(("evades", "m"), ("not_applicable", empty))), "fail")

    def test_evades_without_reason_fails(self):
        self.assertEqual(g1(card(("evades", ""), ("evades", "m"))), "fail")

    def test_hits_fails(self):
        self.assertEqual(g1(card(("hits", "m"), ("evades", "m"))), "fail")

    def test_open_on_only_one_barrier_fails(self):
        self.assertEqual(g1(card(("open", "x"), ("evades", "m"))), "fail")
        self.assertEqual(g1(card(("evades", "m"), ("open", "x"))), "fail")
        self.assertEqual(g1(card(nat=("open", "x"), rel=("evades", "m"), alg=("evades", "m"))), "fail")

    def test_open_barriers_do_not_trigger_other_claim_types(self):
        # reading the code: upper_bound checks relativization only; the others are "na"
        self.assertEqual(g1(card(claim_type="upper_bound")), "fail")
        self.assertEqual(g1(card(("evades", "m"), claim_type="upper_bound")), "pass")
        for ct in ("reduction", "finite_lemma"):
            self.assertEqual(g1(card(claim_type=ct)), "na", ct)

    def test_unknown_status_refused_by_validate(self):
        for k in ("relativization", "natural_proofs", "algebrization"):
            for bad in ("OPEN", "maybe", "", None):
                c = card()
                c["barrier_audit"][k]["status"] = bad
                self.assertTrue(V(c), (k, bad))
                r = run(c)
                self.assertFalse(r["valid"])
                self.assertIsNone(r["gates"])


if __name__ == "__main__":
    unittest.main()
