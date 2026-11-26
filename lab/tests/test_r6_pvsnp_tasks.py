import unittest
from collections import Counter

from lab import r6_pvsnp_tasks as m

X0, X1 = 0b1010, 0b1100  # n=2 tables: bit i is f(i&1, (i>>1)&1)


def parity(n):
    return sum(1 << i for i in range(1 << n) if bin(i).count("1") % 2)


class HandTableN2(unittest.TestCase):
    # f: (De Morgan formula, binary formula, circuit), enumerated by hand for all 16 functions
    HAND = {
        0b0000: (2, 2, 1),  # constant 0: x AND NOT x
        0b1111: (2, 2, 1),
        0b1010: (1, 1, 0), 0b0101: (1, 1, 0), 0b1100: (1, 1, 0), 0b0011: (1, 1, 0),  # literals
        0b0001: (2, 2, 1), 0b0010: (2, 2, 1), 0b0100: (2, 2, 1), 0b1000: (2, 2, 1),  # the four minterms
        0b0111: (2, 2, 1), 0b1011: (2, 2, 1), 0b1101: (2, 2, 1), 0b1110: (2, 2, 1),  # their negations
        0b0110: (4, 2, 1), 0b1001: (4, 2, 1),  # xor, xnor
    }

    def test_every_entry(self):
        for f, (dm, bi, ci) in self.HAND.items():
            with self.subTest(f=f):
                self.assertEqual(m.min_formula_size(2)[f], dm)
                self.assertEqual(m.min_formula_size(2, "binary")[f], bi)
                self.assertEqual(m.min_circuit_size(2)[f], ci)

    def test_keys_are_all_16_tables(self):
        for d in (m.min_formula_size(2), m.min_formula_size(2, "binary"), m.min_circuit_size(2)):
            self.assertEqual(sorted(d), list(range(16)))

    def test_classes(self):
        self.assertEqual(m.npn_class_count(2), 4)
        self.assertEqual(m.npn_orbit_sizes(2), {0: 2, 3: 4, 1: 8, 6: 2})

    def test_variable_tables(self):
        self.assertEqual((m.var_table(2, 0), m.var_table(2, 1)), (X0, X1))

    def test_n1(self):
        self.assertEqual(m.min_formula_size(1), {0: 2, 1: 1, 2: 1, 3: 2})
        self.assertEqual(m.min_circuit_size(1), {0: 1, 1: 0, 2: 0, 3: 1})


class Refusals(unittest.TestCase):
    def test_bad_n(self):
        for bad in (0, 5, -1, True, 2.0, "3", None):
            for fn in (m.min_formula_size, m.min_circuit_size, m.npn_class_count, m.circuit_open):
                with self.subTest(n=bad, fn=fn.__name__):
                    with self.assertRaises(ValueError):
                        fn(bad)

    def test_bad_basis(self):
        for bad in ("", "DeMorgan", "xor", None):
            with self.assertRaises(ValueError):
                m.min_formula_size(2, bad)

    def test_bad_variable(self):
        for bad in (-1, 2, True, 0.0):
            with self.assertRaises(ValueError):
                m.var_table(2, bad)


class Determinism(unittest.TestCase):
    def test_repeat_and_copy(self):
        a = m.min_formula_size(3)
        a[0] = 99  # mutating a result must not leak into the cache
        self.assertEqual(m.min_formula_size(3)[0], 2)
        self.assertEqual(m.min_circuit_size(3), m.min_circuit_size(3))
        self.assertEqual(m.min_formula_size(3, "binary"), m.min_formula_size(3, "binary"))
        self.assertEqual(m.npn_orbit_sizes(3), m.npn_orbit_sizes(3))


def naive_formula(n, binary):
    """All 2^2^n functions, no symmetry reduction: closure by leaf count."""
    full = (1 << (1 << n)) - 1
    size, lev = {}, {1: set()}
    for j in range(n):
        v = m.var_table(n, j)
        lev[1] |= {v, full ^ v}
    for f in lev[1]:
        size[f] = 1
    k = 1
    while len(size) < 1 << (1 << n):
        k += 1
        new = set()
        for a in range(1, k):
            for g in lev[a]:
                for h in lev[k - a]:
                    new |= {g & h, g | h} | ({g ^ h} if binary else set())
        new |= {full ^ f for f in new}
        new -= set(size)
        for f in new:
            size[f] = k
        lev[k] = new
    return size


def reach_with_gates(n, k):
    """Functions (and negations) computable with at most k gates, all 16 ops, no normalisation."""
    full = (1 << (1 << n)) - 1
    ins = tuple(m.var_table(n, j) for j in range(n))

    def gates(a, b):
        for op in range(16):
            r = 0
            for x in (0, 1):
                for y in (0, 1):
                    if (op >> (2 * x + y)) & 1:
                        r |= (a if x else full ^ a) & (b if y else full ^ b)
            yield r

    states, seen = {frozenset()}, set(ins) | {full ^ v for v in ins}
    for _ in range(k):
        nxt = set()
        for st in states:
            sig = list(ins) + list(st)
            for i in range(len(sig)):
                for j in range(i + 1, len(sig)):
                    for g in gates(sig[i], sig[j]):
                        nxt.add(st | {g})
                        seen |= {g, full ^ g}
        states = nxt
    return seen


class SmallCases(unittest.TestCase):
    def test_n3_known(self):
        self.assertEqual(m.min_formula_size(3)[parity(3)], 10)  # (A and not z) or (not A and z), A = x xor y of 4 leaves: 4+4+2
        self.assertEqual(m.min_formula_size(3, "binary")[parity(3)], 3)
        self.assertEqual(m.min_circuit_size(3)[parity(3)], 2)
        self.assertEqual(m.min_formula_size(3)[0xE8], 5)  # majority
        self.assertEqual(m.min_circuit_size(3)[0xE8], 4)

    def test_n3_formula_against_naive(self):
        self.assertEqual(m.min_formula_size(3), naive_formula(3, False))
        self.assertEqual(m.min_formula_size(3, "binary"), naive_formula(3, True))

    def test_n2_formula_against_naive(self):
        self.assertEqual(m.min_formula_size(2), naive_formula(2, False))

    def test_n3_circuit_against_naive_reachability(self):
        got = m.min_circuit_size(3)
        self.assertEqual(sorted(got), list(range(256)))
        r3 = reach_with_gates(3, 3)
        for f, c in got.items():
            self.assertEqual(c <= 3, f in r3, f)
        self.assertEqual(max(got.values()), 4)

    def test_class_counts(self):
        self.assertEqual([m.npn_class_count(n) for n in (1, 2, 3, 4)], [2, 4, 14, 222])
        for n in (3, 4):
            self.assertEqual(sum(m.npn_orbit_sizes(n).values()), 1 << (1 << n))


class FourInputs(unittest.TestCase):
    def test_parity(self):
        p = parity(4)
        self.assertEqual(p, 0x6996)
        self.assertEqual(m.min_formula_size(4)[p], 16)
        self.assertEqual(m.min_formula_size(4, "binary")[p], 4)
        self.assertEqual(m.min_circuit_size(4)[p], 3)

    def test_totals_and_symmetry(self):
        fs, bs, cs = m.min_formula_size(4), m.min_formula_size(4, "binary"), m.min_circuit_size(4)
        self.assertEqual(m.circuit_open(4), {})
        for d in (fs, bs, cs):
            self.assertEqual(len(d), 65536)
        for f in range(65536):  # output negation and a cheaper basis can only help
            self.assertEqual(fs[f], fs[f ^ 0xFFFF])
            self.assertLessEqual(bs[f], fs[f])
            self.assertLessEqual(cs[f], bs[f] - 1 if bs[f] > 1 else 1)
        self.assertEqual(max(fs.values()), 16)
        self.assertEqual(max(bs.values()), 8)
        self.assertEqual(max(cs.values()), 7)

    def test_circuit_class_histogram(self):  # regression pin of the computed values, not an external truth
        cs = m.min_circuit_size(4)
        h = Counter(cs[r] for r in m.npn_orbit_sizes(4))
        self.assertEqual(sorted(h.items()), [(0, 1), (1, 3), (2, 5), (3, 20), (4, 34), (5, 75), (6, 72), (7, 12)])

    def test_formula_histogram(self):  # regression pins of this solver's own output, not external truth
        pins = {
            (3, "demorgan"): [(1, 6), (2, 26), (3, 64), (4, 30), (5, 80), (6, 32), (8, 16), (10, 2)],
            (3, "binary"): [(1, 6), (2, 32), (3, 114), (4, 80), (5, 24)],
            (4, "demorgan"): [(1, 8), (2, 50), (3, 256), (4, 940), (5, 2048), (6, 5248), (7, 8672),
                              (8, 11768), (9, 10592), (10, 11536), (11, 5472), (12, 6304), (13, 960),
                              (14, 1472), (15, 96), (16, 114)],
            (4, "binary"): [(1, 8), (2, 62), (3, 456), (4, 2474), (5, 10624), (6, 24184), (7, 24640), (8, 3088)],
        }
        for (n, basis), want in pins.items():
            with self.subTest(n=n, basis=basis):
                self.assertEqual(sorted(Counter(m.min_formula_size(n, basis).values()).items()), want)

    def test_crosscheck_report(self):
        r = m.crosscheck_report()
        self.assertEqual(r["classes"], r["classes_recalled"])
        self.assertEqual(r["parity4_demorgan_formula"], r["parity4_demorgan_formula_recalled"])
        self.assertEqual(r["max_circuit_size_n4"], r["max_circuit_size_n4_recalled"])
        self.assertEqual(r["circuit_open_n4"], 0)


if __name__ == "__main__":
    unittest.main()
