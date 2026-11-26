import itertools
import unittest

from lab import r6_t2_identity as T

GL = 400


def kw(**k):
    return dict(gate_limit=GL, **k)


def exp(m, *cells):
    e = [0] * (m * m)
    for i, j in cells:
        e[i * m + j] += 1
    return tuple(e)


class Hand(unittest.TestCase):
    def test_perm2(self):
        self.assertEqual(T.perm_target(2, 3), {exp(2, (0, 0), (1, 1)): 1, exp(2, (0, 1), (1, 0)): 1})

    def test_hc2(self):
        self.assertEqual(T.hc_target(2, 2), {exp(2, (0, 1), (1, 0)): 1})

    def test_term_counts(self):
        for p in (2, 3):
            self.assertEqual([len(T.perm_target(m, p)) for m in (2, 3, 4)], [2, 6, 24])
            self.assertEqual([len(T.hc_target(m, p)) for m in (2, 3, 4)], [1, 2, 6])

    def test_hc3_terms(self):
        want = {exp(3, (0, 1), (1, 2), (2, 0)), exp(3, (0, 2), (2, 1), (1, 0))}
        self.assertEqual(set(T.hc_target(3, 3)), want)

    def test_x2_minus_x(self):
        x = ("var", 0, 0)
        for p in (2, 3):
            c = (("mul", x, x), ("sub", 0, x))
            poly = T.circuit_poly(c, 2, p, gate_limit=GL)
            self.assertEqual(poly, {exp(2, (0, 0), (0, 0)): 1, exp(2, (0, 0)): p - 1})
        # over F_2 it is x^2 + x, nonzero, yet zero on 0/1 points
        c = (("mul", x, x), ("sub", 0, x))
        zero = (("const", 0, None),)
        self.assertFalse(T.identical_as_polynomials(c, {}, 2, 2, gate_limit=GL))
        self.assertTrue(T.agrees_on_01(c, {}, 2, 2, **kw()))
        self.assertTrue(T.agrees_on_01(zero, {}, 2, 2, **kw()))

    def test_hand_circuit_perm2(self):
        c = (("mul", ("var", 0, 0), ("var", 1, 1)), ("mul", ("var", 0, 1), ("var", 1, 0)), ("add", 0, 1))
        for p in (2, 3):
            t = T.perm_target(2, p)
            self.assertTrue(T.identical_as_polynomials(c, t, 2, p, **kw()))
            self.assertTrue(T.agrees_on_01(c, t, 2, p, **kw()))
            self.assertFalse(T.identical_as_polynomials(c, T.hc_target(2, p), 2, p, **kw()))
            self.assertFalse(T.agrees_on_01(c, T.hc_target(2, p), 2, p, **kw()))

    def test_sub_cancel_and_mod(self):
        x = ("var", 1, 1)
        c = (("const", 2, None), ("mul", 0, x), ("add", 1, x))  # 2x + x = 0 mod 3
        self.assertEqual(T.circuit_poly(c, 2, 3, gate_limit=GL), {})
        c2 = (("mul", ("var", 1, 1), ("var", 1, 1)), ("add", 0, 0), ("add", 1, ("var", 1, 1)))  # 2x^2 + x
        self.assertEqual(T.circuit_poly(c2, 2, 2, gate_limit=GL), {exp(2, (1, 1)): 1})

    def test_exponents_not_reduced(self):
        x = ("var", 0, 1)
        c = (("mul", x, x), ("mul", 0, x))
        self.assertEqual(T.circuit_poly(c, 2, 3, gate_limit=GL), {exp(2, (0, 1), (0, 1), (0, 1)): 1})

    def test_variable_bit_not_transposed(self):
        for p in (2, 3):
            x01 = (("const", 0, None), ("add", ("var", 0, 1), 0))
            t01, t10 = {exp(2, (0, 1)): 1}, {exp(2, (1, 0)): 1}
            self.assertTrue(T.agrees_on_01(x01, t01, 2, p, **kw()))
            self.assertFalse(T.agrees_on_01(x01, t10, 2, p, **kw()))
            self.assertTrue(T.identical_as_polynomials(x01, t01, 2, p, **kw()))
            self.assertFalse(T.identical_as_polynomials(x01, t10, 2, p, **kw()))
        m3 = (("const", 0, None), ("add", ("var", 0, 2), 0))
        self.assertTrue(T.agrees_on_01(m3, {exp(3, (0, 2)): 1}, 3, 3, **kw()))
        self.assertFalse(T.agrees_on_01(m3, {exp(3, (2, 0)): 1}, 3, 3, **kw()))

    def test_canonical(self):
        c = (("const", 1, None), ("mul", ("var", 0, 1), 0), ("add", 1, ("var", 1, 0)))
        self.assertEqual(T.circuit_to_canonical(c), [
            ("const", ("c", 1), None),
            ("mul", ("x", 0, 1), ("g", 0)),
            ("add", ("g", 1), ("x", 1, 0))])


class Planted(unittest.TestCase):
    def check(self, m, p, kind, seed):
        d = T.planted(m, p, kind, seed)
        t = T.target_by_name(d["target"], m, p)
        c = d["circuit"]
        ag = T.agrees_on_01(c, t, m, p, **kw())
        ident = T.identical_as_polynomials(c, t, m, p, **kw())
        return ag, ident

    def test_kinds(self):
        want = {"correct": (True, True), "agrees_not_identical": (True, False),
                "wrong_coefficient": (False, False), "wrong_on_01": (False, False)}
        for m in (2, 3):
            for p in (2, 3):
                for kind, w in want.items():
                    for seed in range(6):
                        self.assertEqual(self.check(m, p, kind, seed), w, (m, p, kind, seed))

    def test_both_targets_appear(self):
        names = {T.planted(2, 3, "correct", s)["target"] for s in range(20)}
        self.assertEqual(names, {"perm", "hc"})

    def test_m4_correct(self):
        d = T.planted(4, 3, "agrees_not_identical", 1)
        t = T.target_by_name(d["target"], 4, 3)
        self.assertTrue(T.agrees_on_01(d["circuit"], t, 4, 3, **kw()))
        self.assertFalse(T.identical_as_polynomials(d["circuit"], t, 4, 3, **kw()))

    def test_deterministic_and_seeded(self):
        a = T.planted(3, 3, "agrees_not_identical", 7)
        self.assertEqual(a, T.planted(3, 3, "agrees_not_identical", 7))
        self.assertGreater(len({T.planted(3, 3, "agrees_not_identical", s)["circuit"] for s in range(8)}), 1)
        self.assertNotEqual(T.planted(3, 3, "correct", 1)["circuit"], T.planted(3, 3, "wrong_on_01", 1)["circuit"])

    def test_agrees_diff_is_x2_minus_x(self):
        d = T.planted(2, 3, "agrees_not_identical", 3)
        t = T.target_by_name(d["target"], 2, 3)
        diff = T.circuit_poly(d["circuit"], 2, 3, gate_limit=GL)
        self.assertEqual(len(diff), len(t) + 2)

    def test_wrong_on_01_drops_a_term(self):
        d = T.planted(3, 2, "wrong_on_01", 2)
        t = T.target_by_name(d["target"], 3, 2)
        self.assertEqual(len(T.circuit_poly(d["circuit"], 3, 2, gate_limit=GL)), len(t) - 1)

    def test_wrong_coefficient_one_term(self):
        d = T.planted(3, 3, "wrong_coefficient", 2)
        t = T.target_by_name(d["target"], 3, 3)
        got = T.circuit_poly(d["circuit"], 3, 3, gate_limit=GL)
        diff = [e for e in set(got) | set(t) if got.get(e, 0) != t.get(e, 0)]
        self.assertEqual(len(diff), 1)

    def test_empty_sum_hc2(self):
        for s in range(30):
            d = T.planted(2, 2, "wrong_on_01", s)
            if d["target"] == "hc":
                self.assertEqual(d["circuit"], (("const", 0, None),))
                return
        self.fail("no hc seed")


class Refusals(unittest.TestCase):
    def bad(self, c, m=2, p=3, gl=GL):
        with self.assertRaises(T.T2Refusal):
            T.circuit_poly(c, m, p, gate_limit=gl)

    def test_gates(self):
        v = ("var", 0, 0)
        self.bad((("add", 0, v),))  # self reference
        self.bad((("add", 1, v), ("add", v, v)))  # forward
        self.bad((("add", -1, v),))
        self.bad((("add", v),))  # arity
        self.bad((("add", v, v, v),))
        self.bad((("add", v, None),))
        self.bad((("neg", v, v),))
        self.bad((("add", ("var", 2, 0), v),))  # row index out of range for m=2
        self.bad((("add", ("var", 0, -1), v),))
        self.bad((("add", True, v),))
        self.bad(())
        self.bad([])
        self.bad(None)

    def test_constants(self):
        for c in (True, False, float("nan"), 1.0, 3, -1, "1", None):
            self.bad((("const", c, None),))
        self.bad((("const", 1, 0),))
        self.bad((("const", 2, None),), p=2)
        T.circuit_poly((("const", 2, None),), 2, 3, gate_limit=GL)

    def test_limit_required_and_enforced(self):
        c = (("const", 1, None),) * 3
        with self.assertRaises(TypeError):
            T.circuit_poly(c, 2, 3)
        for gl in (0, -1, True, 2.0, None):
            self.bad(c, gl=gl)
        self.bad(c, gl=2)
        T.circuit_poly(c, 2, 3, gate_limit=3)
        t = T.perm_target(2, 3)
        with self.assertRaises(T.T2Refusal):
            T.agrees_on_01(c, t, 2, 3, gate_limit=2)
        with self.assertRaises(T.T2Refusal):
            T.identical_as_polynomials(c, t, 2, 3, gate_limit=2)

    def test_m_p(self):
        c = (("const", 1, None),)
        for m, p in ((1, 3), (5, 3), (True, 3), (2, 5), (2, True), (2.0, 3)):
            with self.assertRaises(T.T2Refusal):
                T.circuit_poly(c, m, p, gate_limit=GL)
        with self.assertRaises(T.T2Refusal):
            T.perm_target(5, 3)
        with self.assertRaises(T.T2Refusal):
            T.hc_target(2, 7)

    def test_planted_args(self):
        for args in ((2, 3, "nope", 1), (2, 3, "correct", True), (2, 3, "correct", 1.5), (2, 3, "correct", "1"),
                     (2, 3, "correct", None), (9, 3, "correct", 1)):
            with self.assertRaises(T.T2Refusal):
                T.planted(*args)
        with self.assertRaises(T.T2Refusal):
            T.target_by_name("x", 2, 3)

    def test_bad_target(self):
        c = (("const", 1, None),)
        for t in ({(1, 0, 0): 1}, {(1, 0, 0, 0): 0}, {(1, 0, 0, 0): 3}, {(1, 0, 0, 0): True}, {(-1, 0, 0, 0): 1}, [], None):
            with self.assertRaises(T.T2Refusal):
                T.agrees_on_01(c, t, 2, 3, gate_limit=GL)
            with self.assertRaises(T.T2Refusal):
                T.identical_as_polynomials(c, t, 2, 3, gate_limit=GL)

    def test_term_limit_precheck_before_build(self):
        # (x+y)(x-y) = x^2 - y^2 has 2 result terms but 4 raw products: refused up front at limit 3
        x, y = ("var", 0, 0), ("var", 0, 1)
        c = (("add", x, y), ("sub", x, y), ("mul", 0, 1))
        old = T.TERM_LIMIT
        try:
            T.TERM_LIMIT = 4
            self.assertEqual(len(T.circuit_poly(c, 2, 3, gate_limit=GL)), 2)
            T.TERM_LIMIT = 3
            self.bad(c)
        finally:
            T.TERM_LIMIT = old

    def test_term_limit_on_add(self):
        c = (("add", ("var", 0, 0), ("var", 0, 1)), ("add", 0, ("var", 1, 0)))
        old = T.TERM_LIMIT
        try:
            T.TERM_LIMIT = 3
            self.assertEqual(len(T.circuit_poly(c, 2, 3, gate_limit=GL)), 3)
            T.TERM_LIMIT = 2
            self.bad(c)
        finally:
            T.TERM_LIMIT = old

    def test_term_limit(self):
        # (1+x)^k style blowup is bounded by TERM_LIMIT; check the refusal path with a lowered bound
        old = T.TERM_LIMIT
        T.TERM_LIMIT = 3
        try:
            c = (("add", ("var", 0, 0), ("var", 0, 1)), ("add", ("var", 1, 0), ("var", 1, 1)), ("mul", 0, 1))
            self.bad(c)
        finally:
            T.TERM_LIMIT = old


class Whole(unittest.TestCase):
    def test_agreement_counts_all_points(self):
        # differs from PERM_2 only at the all-ones point: x11 x12 x21 x22
        m, p = 2, 3
        base = list(T.planted(m, p, "correct", 0)["circuit"])
        d = T.planted(m, p, "correct", 0)
        t = T.target_by_name(d["target"], m, p)
        v = [("var", 0, 0), ("var", 0, 1), ("var", 1, 0), ("var", 1, 1)]
        g = list(d["circuit"])
        n = len(g)
        g += [("mul", v[0], v[1]), ("mul", v[2], v[3]), ("mul", n, n + 1), ("add", n - 1, n + 2)]
        self.assertFalse(T.agrees_on_01(tuple(g), t, m, p, **kw()))
        self.assertTrue(T.agrees_on_01(tuple(base), t, m, p, **kw()))

    def test_fields_differ(self):
        # 2 = 0 over F_2 but not over F_3
        c = (("const", 1, None), ("add", 0, 0))
        self.assertEqual(T.circuit_poly(c, 2, 2, gate_limit=GL), {})
        self.assertEqual(T.circuit_poly(c, 2, 3, gate_limit=GL), {(0,) * 4: 2})


if __name__ == "__main__":
    unittest.main()
