import unittest
from collections import Counter
from itertools import product

import r6_m1_enum as m

X0, X1 = 0b1010, 0b1100  # n=2 inputs, bit i = output on input i


def _lits(n):
    W = 1 << n
    M = (1 << W) - 1
    v = [sum(1 << j for j in range(W) if (j >> i) & 1) for i in range(n)]
    return v + [x ^ M for x in v], M


def brute_formulas(n, binary, top):
    """every explicit formula tree up to `top` leaves, no deduplication: tt -> min leaves."""
    lits, M = _lits(n)
    levels = {1: lits}
    best = {x: 1 for x in lits}
    for s in range(2, top + 1):
        cur = []
        for a in range(1, s):
            for x in levels[a]:
                for y in levels[s - a]:
                    cur.append(x & y)
                    cur.append(x | y)
                    if binary:
                        cur.append(x ^ y)
        levels[s] = cur
        for f in cur:
            best.setdefault(f, s)
            best.setdefault(f ^ M, s)
    return best


def brute_circuits(n, top):
    """every explicit gate sequence (16 ops, two distinct earlier nodes), no dedup."""
    lits, M = _lits(n)
    nodes = lits[:n]
    best = {x: 0 for x in lits}

    def op(t, u, v):
        r = 0
        for k in range(4):
            if (t >> k) & 1:
                r |= (u if k & 1 else u ^ M) & (v if k & 2 else v ^ M)
        return r

    def rec(nodes, depth):
        if depth == top:
            return
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                for t in range(16):
                    f = op(t, nodes[i], nodes[j])
                    if best.get(f, 99) > depth + 1:
                        best[f] = depth + 1
                    rec(nodes + [f], depth + 1)

    rec(nodes, 0)
    return best


class N2ByHand(unittest.TestCase):
    def test_demorgan(self):
        d = m.min_formula_size(2)
        want = {X0: 1, X1: 1, 5: 1, 3: 1, 0: 2, 15: 2, 6: 4, 9: 4}
        want.update({f: 2 for f in (8, 4, 2, 1, 14, 13, 11, 7)})
        self.assertEqual(d, want)

    def test_binary(self):
        d = m.min_formula_size(2, "binary")
        want = {X0: 1, X1: 1, 5: 1, 3: 1}
        want.update({f: 2 for f in range(16) if f not in want})
        self.assertEqual(d, want)

    def test_circuit(self):
        want = {X0: 0, X1: 0, 5: 0, 3: 0, 0: 1, 15: 1}
        want.update({f: 1 for f in (8, 4, 2, 1, 14, 13, 11, 7, 6, 9)})
        self.assertEqual(m.min_circuit_size(2), want)
        strict = dict(want)
        strict[0] = strict[15] = 2
        self.assertEqual(m.min_circuit_size(2, const_gate=False), strict)

    def test_classes(self):
        self.assertEqual(m.class_counts(), {2: 4, 3: 14, 4: 222})


class Refusals(unittest.TestCase):
    def test_bad_n(self):
        for bad in (1, 5, 0, -2):
            for f in (m.min_formula_size, m.min_circuit_size, m.class_count):
                with self.assertRaises(ValueError):
                    f(bad)
        for bad in (True, 2.0, "2", None):
            with self.assertRaises(TypeError):
                m.min_formula_size(bad)
            with self.assertRaises(TypeError):
                m.min_circuit_size(bad)

    def test_bad_basis(self):
        with self.assertRaises(ValueError):
            m.min_formula_size(2, "nand")


class Determinism(unittest.TestCase):
    def test_same_and_independent_copies(self):
        a = m.min_formula_size(3)
        a[0xE8] = -1
        b = m.min_formula_size(3)
        self.assertNotEqual(b[0xE8], -1)
        self.assertEqual(b, m.min_formula_size(3))
        self.assertEqual(list(b), sorted(b))
        c = m.min_circuit_size(3)
        c[0xE8] = -1
        self.assertEqual(m.min_circuit_size(3)[0xE8], 4)
        self.assertEqual(len(b), 256)


class ExplicitCrossCheck(unittest.TestCase):
    def check_prefix(self, table, brute, top):
        for f, s in table.items():
            if s <= top:
                self.assertEqual(brute[f], s, hex(f))
            else:
                self.assertNotIn(f, brute, hex(f))

    def test_n3_formulas_vs_trees(self):
        self.check_prefix(m.min_formula_size(3), brute_formulas(3, False, 5), 5)
        self.check_prefix(m.min_formula_size(3, "binary"), brute_formulas(3, True, 4), 4)

    def test_n4_formulas_vs_trees(self):
        self.check_prefix(m.min_formula_size(4), brute_formulas(4, False, 4), 4)

    def test_n3_circuits_vs_sequences(self):
        self.check_prefix(m.min_circuit_size(3), brute_circuits(3, 3), 3)

    def test_n4_circuits_vs_sequences(self):
        self.check_prefix(m.min_circuit_size(4), brute_circuits(4, 3), 3)


class KnownValues(unittest.TestCase):
    def test_n3(self):
        d = m.min_formula_size(3)
        self.assertEqual(d[0x96], 10)     # 3-input parity: Khrapchenko's 9 is only a lower bound
        self.assertEqual(d[0xE8], 5)      # majority
        self.assertEqual(m.min_formula_size(3, "binary")[0x96], 3)
        c = m.min_circuit_size(3)
        self.assertEqual((c[0x96], c[0xE8], m.max_size(c)), (2, 4, 4))

    def test_n4(self):
        d = m.min_formula_size(4)
        self.assertEqual(d[0x6996], 16)
        self.assertEqual(m.min_formula_size(4, "binary")[0x6996], 4)
        c = m.min_circuit_size(4)
        self.assertEqual(c[0x6996], 3)
        self.assertEqual(sorted(Counter(c.values()).items()),
                         [(0, 8), (1, 62), (2, 456), (3, 2474), (4, 10624), (5, 24184), (6, 25008), (7, 2720)])
        self.assertEqual(sorted(Counter(d.values()).items())[:5],
                         [(1, 8), (2, 50), (3, 256), (4, 940), (5, 2048)])
        self.assertEqual((m.max_size(c), m.max_size(d)), (7, 16))

    def test_symmetry_invariance(self):
        for n in (3, 4):
            M = (1 << (1 << n)) - 1
            for tab in (m.min_formula_size(n), m.min_circuit_size(n)):
                self.assertTrue(all(tab[f ^ M] == s for f, s in tab.items()))
                self.assertEqual(len(tab), 1 << (1 << n))
        # input-swap invariance on n=4
        tab = m.min_circuit_size(4)
        sw = lambda f: sum(((f >> j) & 1) << (j & ~3 | (j & 1) << 1 | (j >> 1) & 1) for j in range(16))
        self.assertTrue(all(tab[sw(f)] == s for f, s in tab.items()))

    def test_bounds_agree_when_exact(self):
        lo, up = m.circuit_size_bounds(4)
        self.assertEqual(lo, up)


if __name__ == "__main__":
    unittest.main()
