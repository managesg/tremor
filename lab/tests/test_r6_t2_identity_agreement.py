"""Agreement of the two independent T2 checkers (A: r6_t2_identity, B: r6_t2_identity_b).

Legitimate differences, tested through the converter below: A writes variables
('var', i, j) 0-based, B writes ('x', i, j) 1-based; A returns targets as dicts, B as
Poly objects; the planted circuits differ because the seeds are mapped differently.
Both use exponent index i*m+j (row-major, 0-based) so targets compare directly.
Each checker is run on BOTH implementations' planted circuits; truths must be equal.
"""

import itertools
import unittest
from unittest import mock

from lab import r6_t2_identity as A
from lab import r6_t2_identity_b as B

LIMIT = 4096
EXPECT = {
    "correct": (True, True),
    "agrees_not_identical": (True, False),
    "wrong_coefficient": (False, False),
    "wrong_on_01": (False, False),
}


# ---- converter, through A's canonical form -------------------------------------------
def _b_to_canon(circuit):
    def op(x):
        if isinstance(x, tuple):
            assert x[0] == "x"
            return ("x", x[1] - 1, x[2] - 1)
        return ("g", x)

    return [
        ("const", ("c", l), None) if o == "const" else (o, op(l), op(r))
        for o, l, r in circuit
    ]


def _canon_to(circuit_canon, var_tag, shift, gate_plain=True):
    def op(x):
        if x[0] == "g":
            return x[1]
        return (var_tag, x[1] + shift, x[2] + shift)

    return tuple(
        ("const", l[1], None) if o == "const" else (o, op(l), op(r))
        for o, l, r in circuit_canon
    )


def a_to_b(circuit):
    return _canon_to(A.circuit_to_canonical(circuit), "x", 1)


def b_to_a(circuit):
    return _canon_to(_b_to_canon(circuit), "var", 0)


# ---- truth pairs: (agrees on 0/1 points, identical as polynomials) --------------------
def truths_a(circuit_a, name, m, p):
    t = A.target_by_name(name, m, p)
    return (
        A.agrees_on_01(circuit_a, t, m, p, gate_limit=LIMIT),
        A.identical_as_polynomials(circuit_a, t, m, p, gate_limit=LIMIT),
    )


def truths_b(circuit_b, name, m, p):
    t = B.perm_target(m, p) if name == "perm" else B.hc_target(m, p)
    return (
        B.agrees_on_01(circuit_b, t, m, p, LIMIT),
        B.identical_as_polynomials(circuit_b, t, m, p, LIMIT),
    )


def both(circuit_a, circuit_b, name, m, p):
    """Truth pairs of A's and B's checkers on the same circuit given in both formats."""
    return truths_a(circuit_a, name, m, p), truths_b(circuit_b, name, m, p)


def hand_perm_circuit(m, extra=()):
    """Permutation sum written by hand in A format, independent of any builder."""
    gates = []
    acc = None
    for perm in itertools.permutations(range(m)):
        t = ("var", 0, perm[0])
        for i in range(1, m):
            gates.append(("mul", t, ("var", i, perm[i])))
            t = len(gates) - 1
        if acc is None:
            acc = t
        else:
            gates.append(("add", acc, t))
            acc = len(gates) - 1
    for g in extra:
        gates.append(g)
    return tuple(gates)


class ConverterTests(unittest.TestCase):
    def test_hand_case(self):
        ca = (("mul", ("var", 0, 1), ("var", 2, 0)), ("const", 1, None), ("sub", 0, 1))
        cb = (("mul", ("x", 1, 2), ("x", 3, 1)), ("const", 1, None), ("sub", 0, 1))
        self.assertEqual(a_to_b(ca), cb)
        self.assertEqual(b_to_a(cb), ca)

    def test_round_trips_and_canonical(self):
        for m, p, kind in itertools.product((2, 3), (2, 3), A.KINDS):
            ca = A.planted(m, p, kind, 1)["circuit"]
            self.assertEqual(b_to_a(a_to_b(ca)), ca)
            cb = B.planted(m, p, kind, 1)["circuit"]
            self.assertEqual(a_to_b(b_to_a(cb)), cb)
            self.assertEqual(A.circuit_to_canonical(b_to_a(cb)), _b_to_canon(cb))

    def test_index_zero_gate_vs_constant_zero(self):
        # m=2, p=3. Operand 0 is gate 0 (x00*x11), never the constant 0.
        x, y = ("var", 0, 0), ("var", 1, 1)
        cases = (
            ((("mul", x, y), ("add", 0, 0)), {(1, 0, 0, 1): 2}),          # gate 0 twice
            ((("const", 0, None), ("add", 0, 0)), {}),                      # constant 0
            ((("const", 0, None), ("add", 0, x)), {(1, 0, 0, 0): 1}),       # 0 + x00
            ((("const", 2, None), ("mul", 0, x)), {(1, 0, 0, 0): 2}),       # 2 * x00
        )
        for ca, want in cases:
            self.assertEqual(A.circuit_poly(ca, 2, 3, gate_limit=LIMIT), want)
            self.assertEqual(dict(B.circuit_poly(a_to_b(ca), 2, 3, LIMIT).terms()), want)

    def test_asymmetric_polynomials_agree(self):
        # x01*x01 + x20 over m=3: exponents at 0-based indices 1 and 6.
        ca = (("mul", ("var", 0, 1), ("var", 0, 1)), ("add", 0, ("var", 2, 0)))
        pa = A.circuit_poly(ca, 3, 3, gate_limit=LIMIT)
        e1 = [0] * 9
        e1[1] = 2
        e2 = [0] * 9
        e2[6] = 1
        self.assertEqual(pa, {tuple(e1): 1, tuple(e2): 1})
        pb = B.circuit_poly(a_to_b(ca), 3, 3, LIMIT)
        self.assertEqual(dict(pb.terms()), pa)


class TargetTests(unittest.TestCase):
    def test_hand_computed(self):
        # PERM_2 = x11 x22 + x12 x21 -> indices (0,3) and (1,2) of a 4-vector
        want = {(1, 0, 0, 1): 1, (0, 1, 1, 0): 1}
        self.assertEqual(A.perm_target(2, 3), want)
        self.assertEqual(dict(B.perm_target(2, 3).terms()), want)
        # HC_2 = x12 x21
        self.assertEqual(A.hc_target(2, 3), {(0, 1, 1, 0): 1})
        self.assertEqual(dict(B.hc_target(2, 3).terms()), {(0, 1, 1, 0): 1})
        # HC_3 = x12 x23 x31 + x13 x21 x32 (indices 1,5,6 and 2,3,7)
        h = {(0, 1, 0, 0, 0, 1, 1, 0, 0): 1, (0, 0, 1, 1, 0, 0, 0, 1, 0): 1}
        self.assertEqual(A.hc_target(3, 2), h)
        self.assertEqual(dict(B.hc_target(3, 2).terms()), h)

    def test_all_m_p_agree(self):
        for m, p in itertools.product((2, 3, 4), (2, 3)):
            self.assertEqual(dict(B.perm_target(m, p).terms()), A.perm_target(m, p))
            self.assertEqual(dict(B.hc_target(m, p).terms()), A.hc_target(m, p))
            self.assertEqual(len(A.hc_target(m, p)), {2: 1, 3: 2, 4: 6}[m])


class HandCircuitTests(unittest.TestCase):
    def test_hand_correct_m3(self):
        for p in (2, 3):
            ca = hand_perm_circuit(3)
            self.assertEqual(both(ca, a_to_b(ca), "perm", 3, p), ((True, True), (True, True)))
            # same circuit against HC_3 is wrong on 0/1 points and as a polynomial
            self.assertEqual(both(ca, a_to_b(ca), "hc", 3, p), ((False, False), (False, False)))

    def test_hand_agrees_not_identical_m3(self):
        for p, c in ((2, 1), (3, 2)):
            base = hand_perm_circuit(3)
            n = len(base)
            x = ("var", 0, 0)
            extra = (
                ("mul", x, x),                # n
                ("sub", n, x),                # n+1: x^2 - x
                ("const", c, None),           # n+2
                ("mul", n + 2, n + 1),        # n+3
                ("add", n - 1, n + 3),        # n+4
            )
            ca = hand_perm_circuit(3, extra)
            self.assertEqual(both(ca, a_to_b(ca), "perm", 3, p), ((True, False), (True, False)))
            poly = A.circuit_poly(ca, 3, p, gate_limit=LIMIT)
            e = [0] * 9
            e[0] = 2
            self.assertEqual(poly[tuple(e)], c)  # the x11^2 term survives formally


class PlantedAgreementTests(unittest.TestCase):
    def check(self, m, p, kind, seed):
        tag = (m, p, kind, seed)
        ia = A.planted(m, p, kind, seed)
        ca, name_a = ia["circuit"], ia["target"]
        ta_a, ta_b = both(ca, a_to_b(ca), name_a, m, p)
        self.assertEqual(ta_a, ta_b, ("A circuit", tag))
        self.assertEqual(ta_a, EXPECT[kind], ("A circuit kind", tag))
        pa = A.circuit_poly(ca, m, p, gate_limit=LIMIT)
        pb = B.circuit_poly(a_to_b(ca), m, p, LIMIT)
        self.assertEqual(pa, dict(pb.terms()), ("A circuit poly", tag))

        ib = B.planted(m, p, kind, seed)
        cb, name_b = ib["circuit"], ib["target_name"]
        tb_a, tb_b = both(b_to_a(cb), cb, name_b, m, p)
        self.assertEqual(tb_a, tb_b, ("B circuit", tag))
        self.assertEqual(tb_a, EXPECT[kind], ("B circuit kind", tag))
        self.assertEqual(tb_b, (ib["agrees_on_01"], ib["identical_as_polynomials"]), tag)
        pa = A.circuit_poly(b_to_a(cb), m, p, gate_limit=LIMIT)
        pb = B.circuit_poly(cb, m, p, LIMIT)
        self.assertEqual(pa, dict(pb.terms()), ("B circuit poly", tag))

    def test_negative_control_wrong_b_answer_is_caught(self):
        # A deliberately wrong B checker must make the agreement check fail.
        for name in ("agrees_on_01", "identical_as_polynomials"):
            real = getattr(B, name)
            with mock.patch.object(B, name, lambda *a, _r=real: not _r(*a)):
                ca = A.planted(2, 3, "correct", 0)
                ra, rb = both(ca["circuit"], a_to_b(ca["circuit"]), ca["target"], 2, 3)
                self.assertNotEqual(ra, rb, name)  # both() must really consult B
                with self.assertRaises(AssertionError, msg=name):
                    self.check(2, 3, "correct", 0)

    def test_m2_m3(self):
        for m, p, kind, seed in itertools.product((2, 3), (2, 3), A.KINDS, range(10)):
            self.check(m, p, kind, seed)

    def test_m4_few(self):
        for p, kind in itertools.product((2, 3), A.KINDS):
            self.check(4, p, kind, 0)


if __name__ == "__main__":
    unittest.main()
