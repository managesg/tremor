import itertools
import unittest
from unittest import mock

from lab import r6_t2_identity as A
from lab import r6_t2_identity_b as B
from lab import r6_t2_tasks as T

EXPECT = {
    "correct": (True, True),
    "agrees_not_identical": (True, False),
    "wrong_coefficient": (False, False),
    "wrong_on_01": (False, False),
}
X = lambda i, j: ("var", i - 1, j - 1)  # 1-based, as the prompt shows
PERM2 = (("mul", X(1, 1), X(2, 2)), ("mul", X(1, 2), X(2, 1)), ("add", 0, 1))


def hand(circuit, m=2, p=2, target="perm", kind="correct"):
    return T.Task(m, p, kind, 0, target, tuple(circuit))


class HandCases(unittest.TestCase):
    def test_perm2_correct(self):
        for p in (2, 3):
            self.assertEqual(T.label(hand(PERM2, p=p)), (True, True))

    def test_perm2_vs_hc2_is_wrong(self):
        # HC_2 is only x12*x21; PERM_2 has an extra term, wrong at the identity point
        self.assertEqual(T.label(hand(PERM2, target="hc")), (False, False))

    def test_hc2_single_term(self):
        c = (("mul", X(1, 2), X(2, 1)),)
        self.assertEqual(T.label(hand(c, target="hc")), (True, True))

    def test_agrees_not_identical(self):
        # + c*(x11*x11 - x11): zero on 0/1 points, a surviving monomial formally
        for p, c in ((2, 1), (3, 2)):
            circ = PERM2 + (
                ("mul", X(1, 1), X(1, 1)), ("sub", 3, X(1, 1)), ("const", c, None),
                ("mul", 5, 4), ("add", 2, 6))
            self.assertEqual(T.label(hand(circ, p=p)), (True, False))

    def test_wrong_coefficient(self):
        # p=3: 2*x11*x22 added -> coefficient 3 = 0 mod 3 would vanish, so add 1*: coefficient 2
        circ = PERM2 + (("const", 1, None), ("mul", 3, 0), ("add", 2, 4))
        self.assertEqual(T.label(hand(circ, p=3)), (False, False))
        # p=2: coefficient 1+1 = 0, the monomial vanishes
        self.assertEqual(T.label(hand(circ, p=2)), (False, False))

    def test_wrong_on_01_missing_term(self):
        self.assertEqual(T.label(hand(PERM2[:1])), (False, False))

    def test_constant_zero_gate_is_not_gate_zero(self):
        # gate 1 = const 0 (not gate 0); out = g0 + g1 = x11*x22 only
        c = (("mul", X(1, 1), X(2, 2)), ("const", 0, None), ("add", 0, 1))
        self.assertEqual(T.label(hand(c)), (False, False))

    def test_one_term_target_hc2_mod_formal(self):
        # x12*x21 + x12*x21 over F_2 is the zero polynomial: wrong
        c = (("mul", X(1, 2), X(2, 1)), ("add", 0, 0))
        self.assertEqual(T.label(hand(c, target="hc")), (False, False))


class Generation(unittest.TestCase):
    def test_deterministic(self):
        for m, p, kind in itertools.product((2, 3), (2, 3), T.KINDS):
            self.assertEqual(T.generate(m, p, kind, 5), T.generate(m, p, kind, 5))

    def test_seed_matters_and_targets_vary(self):
        ts = [T.generate(3, 3, "correct", s) for s in range(12)]
        self.assertGreater(len({t.circuit for t in ts}), 1)
        self.assertEqual({t.target for t in ts}, {"perm", "hc"})

    def test_labels_follow_kind_expectation(self):
        for m, p, kind in itertools.product((2, 3), (2, 3), T.KINDS):
            for seed in (0, 1, 2):
                t = T.generate(m, p, kind, seed)
                self.assertEqual(tuple(T.label(t)), EXPECT[kind], (m, p, kind, seed))

    def test_m4_one_each(self):
        for kind in T.KINDS:
            self.assertEqual(tuple(T.label(T.generate(4, 2, kind, 0))), EXPECT[kind], kind)

    def test_task_fields(self):
        t = T.generate(2, 3, "correct", 9)
        self.assertEqual((t.m, t.p, t.kind, t.seed), (2, 3, "correct", 9))
        self.assertIn(t.target, T.TARGETS)

    def test_refusals(self):
        nan = float("nan")
        bad = [(True, 2, "correct", 0), (nan, 2, "correct", 0), (5, 2, "correct", 0), (1, 2, "correct", 0),
               (2.0, 2, "correct", 0), (2, True, "correct", 0), (2, 5, "correct", 0), (2, nan, "correct", 0),
               (2, 2, "bogus", 0), (2, 2, None, 0), (2, 2, ["correct"], 0), (2, 2, "correct", True),
               (2, 2, "correct", nan), (2, 2, "correct", 1.5), (2, 2, "correct", 2**63),
               (2, 2, "correct", -2**63 - 1), (2, 2, "correct", "0")]
        for args in bad:
            with self.assertRaises(T.T2TaskError, msg=repr(args)):
                T.generate(*args)

    def test_task_refusals(self):
        good = T.generate(2, 2, "correct", 0)
        for bad in (None, tuple(good), good._replace(m=True), good._replace(p=7), good._replace(target="x"),
                    good._replace(circuit=()), good._replace(circuit=list(good.circuit))):
            for f in (T.label, T.render_prompt, T.registry, lambda t: T.check_claim(t, "agrees=yes;identical=yes")):
                with self.assertRaises(T.T2TaskError):
                    f(bad)


class Labelling(unittest.TestCase):
    def test_b_disagreement_raises(self):
        t = T.generate(2, 2, "correct", 0)
        for name in ("agrees_on_01", "identical_as_polynomials"):
            with mock.patch.object(B, name, lambda *a, **k: False):
                with self.assertRaises(T.LabelDisagreement):
                    T.label(t)
                with self.assertRaises(T.LabelDisagreement):
                    T.check_claim(t, "agrees=yes;identical=yes")

    def test_a_disagreement_raises(self):
        t = T.generate(2, 2, "wrong_on_01", 0)
        with mock.patch.object(A, "identical_as_polynomials", lambda *a, **k: True):
            with self.assertRaises(T.LabelDisagreement):
                T.label(t)

    def test_label_never_reads_kind_or_seed(self):
        for kind in T.KINDS:
            t = T.generate(3, 2, kind, 1)
            base = T.label(t)
            for fake in ("zzz", None, 7):
                self.assertEqual(T.label(t._replace(kind=fake, seed=fake)), base)
        # a hand circuit mislabelled with another kind keeps its true label
        self.assertEqual(T.label(hand(PERM2, kind="wrong_on_01")), (True, True))

    def test_prompt_and_claim_ignore_kind_and_seed(self):
        t = T.generate(2, 3, "wrong_coefficient", 4)
        u = t._replace(kind="correct", seed=99)
        self.assertEqual(T.render_prompt(t), T.render_prompt(u))
        self.assertEqual(T.check_claim(t, "agrees=no;identical=no"), T.check_claim(u, "agrees=no;identical=no"))

    def test_a_and_b_both_called(self):
        t = T.generate(2, 2, "correct", 0)
        with mock.patch.object(B, "agrees_on_01", wraps=B.agrees_on_01) as b1, \
                mock.patch.object(A, "agrees_on_01", wraps=A.agrees_on_01) as a1:
            T.label(t)
        self.assertEqual((a1.call_count, b1.call_count), (1, 1))


class Prompt(unittest.TestCase):
    def test_exact_hand_prompt(self):
        c = (("mul", X(1, 2), X(2, 1)), ("const", 1, None), ("sub", 0, 1), ("add", 2, X(1, 1)))
        s = T.render_prompt(hand(c, p=3, target="hc"))
        self.assertIn("g0 = x[1,2] * x[2,1]\ng1 = const 1\ng2 = g0 - g1\ng3 = g2 + x[1,1]\n", s)
        self.assertIn("F_3", s)
        self.assertIn("HC_2", s)
        self.assertIn("agrees=yes;identical=no", s)
        self.assertIn("one cycle of length 2", s)

    def test_perm_named(self):
        s = T.render_prompt(hand(PERM2))
        self.assertIn("PERM_2", s)
        self.assertNotIn("cycle", s)

    def test_deterministic_ascii_and_no_leak(self):
        for kind in T.KINDS:
            t = T.generate(3, 2, kind, 3)
            s = T.render_prompt(t)
            self.assertEqual(s, T.render_prompt(t))
            s.encode("ascii")
            for word in (kind, "planted", "seed", "label", "agrees_not", "wrong_coefficient", "wrong_on_01"):
                self.assertNotIn(word, s)
        self.assertNotEqual(T.prompt_sha256(T.generate(3, 2, "correct", 0)),
                            T.prompt_sha256(T.generate(3, 2, "wrong_on_01", 0)))


class Claims(unittest.TestCase):
    def setUp(self):
        self.t = T.generate(2, 2, "agrees_not_identical", 0)  # truth (True, False)

    def test_every_verdict_pair(self):
        for a, i in itertools.product(("yes", "no"), repeat=2):
            want = "correct" if (a, i) == ("yes", "no") else "wrong"
            self.assertEqual(T.check_claim(self.t, f"agrees={a};identical={i}"), want)

    def test_malformed_is_wrong(self):
        ok = "agrees=yes;identical=no"
        for bad in ("", ok + "\n", " " + ok, ok.upper(), "agrees=yes; identical=no", "agrees=yes", "yes,no",
                    "agrees=yes;identical=no;", "agrees=true;identical=false", ok + ok, None, 1, True, b"x",
                    (True, False), [True, False], {"agrees": True}, float("nan"), "agrees=yes;identical=nо"):
            self.assertEqual(T.check_claim(self.t, bad), "wrong", repr(bad))
            self.assertIsNone(T.parse_claim(bad))

    def test_str_subclass_is_malformed(self):
        class S(str):
            pass

        self.assertEqual(T.check_claim(self.t, S("agrees=yes;identical=no")), "wrong")

    def test_parse(self):
        self.assertEqual(T.parse_claim("agrees=no;identical=yes"), (False, True))


class Registry(unittest.TestCase):
    def test_exposes_only_evaluation(self):
        t = T.generate(2, 3, "wrong_on_01", 2)
        r = T.registry(t)
        self.assertEqual(set(r), {"eval_circuit", "eval_target"})
        for f in r.values():
            for cell in f.__closure__ or ():
                self.assertNotIsInstance(cell.cell_contents, T.Task)
                self.assertNotIn(cell.cell_contents, (t.kind, t.seed)) if isinstance(
                    cell.cell_contents, str) else None

    def test_hand_values(self):
        r = T.registry(hand(PERM2, p=3))
        self.assertEqual(r["eval_circuit"]((1, 0, 0, 1)), 1)
        self.assertEqual(r["eval_circuit"]((1, 1, 1, 1)), 2)
        self.assertEqual(r["eval_circuit"]((2, 2, 2, 2)), 8 % 3)
        self.assertEqual(r["eval_target"]((1, 1, 1, 1)), 2)
        h = T.registry(hand(PERM2, target="hc"))
        self.assertEqual(h["eval_target"]((1, 1, 1, 1)), 1)
        self.assertEqual(h["eval_target"]((1, 0, 0, 1)), 0)

    def test_values_match_label_on_01_points(self):
        for kind in T.KINDS:
            t = T.generate(2, 3, kind, 1)
            r = T.registry(t)
            same = all(r["eval_circuit"](pt) == r["eval_target"](pt)
                       for pt in itertools.product((0, 1), repeat=4))
            self.assertEqual(same, T.label(t).agrees_on_01, kind)

    def test_bad_points(self):
        r = T.registry(hand(PERM2))
        for pt in ((0, 1, 0), [0, 1, 0, 1], (0, 1, 0, 2), (0, 1, 0, True), (0, 1, 0, -1), (0, 1, 0, 1.0), None):
            for f in r.values():
                with self.assertRaises(T.T2TaskError):
                    f(pt)


class CircuitValidation(unittest.TestCase):
    def test_each_refusal_on_every_consumer(self):
        x = X(1, 1)
        bad = {
            "unknown op": (("div", x, x),),
            "forward ref": (("add", 1, x), ("mul", x, x)),
            "self ref": (("add", 0, x),),
            "negative gate ref": (("mul", x, x), ("add", -1, 0)),
            "var row out of range": (("mul", ("var", 2, 0), x),),
            "var col out of range": (("mul", ("var", 0, 2), x),),
            "negative var": (("mul", ("var", -1, 0), x),),
            "bool operand": (("mul", x, x), ("add", True, 0)),
            "bool var index": (("mul", ("var", True, 0), x),),
            "bool const": (("const", True, None),),
            "negative const": (("const", -1, None),),
            "float const": (("const", 1.0, None),),
            "const with operand": (("const", 1, 0),),
            "gate is a list": (["mul", x, x],),
            "gate arity": (("mul", x),),
            "bad operand": (("mul", x, "x"),),
            "too many gates": (("const", 0, None),) * (T.GATE_LIMIT + 1),
            "not a gate": (5,),
        }
        for name, c in bad.items():
            t = hand(c)
            for f in (T.label, T.render_prompt, T.registry, lambda t: T.check_claim(t, "agrees=yes;identical=yes")):
                with self.assertRaises(T.T2TaskError, msg=name):
                    f(t)

    def test_const_at_or_above_p_refused_by_label_not_a_bare_error(self):
        with self.assertRaises(T.T2TaskError):
            T.label(hand((("const", 2, None),)))


class RegistryExactness(unittest.TestCase):
    def test_sub_is_not_symmetric(self):
        r = T.registry(hand((("sub", X(1, 1), X(1, 2)),), p=3))
        self.assertEqual(r["eval_circuit"]((1, 0, 0, 0)), 1)
        self.assertEqual(r["eval_circuit"]((0, 1, 0, 0)), 2)  # 0 - 1 mod 3
        g = T.registry(hand((("const", 0, None), ("const", 1, None), ("sub", 1, 0)), p=3))
        self.assertEqual(g["eval_circuit"]((0, 0, 0, 0)), 1)
        h = T.registry(hand((("const", 0, None), ("const", 1, None), ("sub", 0, 1)), p=3))
        self.assertEqual(h["eval_circuit"]((0, 0, 0, 0)), 2)

    def test_variable_index_not_transposed(self):
        r = T.registry(hand((("add", X(1, 2), X(1, 2)),), p=3))   # 2*x[1,2], row-major slot 1
        self.assertEqual(r["eval_circuit"]((0, 1, 0, 0)), 2)
        self.assertEqual(r["eval_circuit"]((0, 0, 1, 0)), 0)
        s = T.registry(hand((("add", X(2, 1), X(2, 1)),), p=3))   # slot 2
        self.assertEqual(s["eval_circuit"]((0, 1, 0, 0)), 0)
        self.assertEqual(s["eval_circuit"]((0, 0, 1, 0)), 2)

    def test_const_reduced_mod_p(self):
        r = T.registry(hand((("const", 5, None),), p=3))
        self.assertEqual(r["eval_circuit"]((0, 0, 0, 0)), 2)
        r2 = T.registry(hand((("const", 3, None), ("add", 0, X(1, 1))), p=3))
        self.assertEqual(r2["eval_circuit"]((1, 0, 0, 0)), 1)

    def test_hc_target_m3_hand(self):
        # HC_3 = x12 x23 x31 + x13 x21 x32; other permutations excluded
        h = T.registry(hand((("const", 0, None),), m=3, p=3, target="hc"))
        self.assertEqual(h["eval_target"]((0, 1, 0, 0, 0, 1, 1, 0, 0)), 1)
        self.assertEqual(h["eval_target"]((1, 0, 0, 0, 1, 0, 0, 0, 1)), 0)
        self.assertEqual(h["eval_target"]((1,) * 9), 2)


class PromptFormula(unittest.TestCase):
    PERM = "Target PERM_{m} = sum over all permutations s of {{1..{m}}} of x[1,s(1)]*x[2,s(2)]*...*x[{m},s({m})].\n"
    HC = ("Target HC_{m} = sum over all permutations s that are one cycle of length {m} of {{1..{m}}} of "
          "x[1,s(1)]*x[2,s(2)]*...*x[{m},s({m})].\n")

    def test_exact_formula_lines(self):
        c2 = (("mul", X(1, 2), X(2, 1)),)
        c3 = (("mul", X(1, 1), X(2, 2)),)
        for m, c in ((2, c2), (3, c3)):
            for target, tmpl in (("perm", self.PERM), ("hc", self.HC)):
                self.assertIn("\n" + tmpl.format(m=m), T.render_prompt(hand(c, m=m, target=target)), (m, target))


if __name__ == "__main__":
    unittest.main()
