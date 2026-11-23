"""Each null's enumeration against a hand-derived closed form (R1 "Scripted nulls, one per line")."""
import time
import unittest
from fractions import Fraction as F

from murmuration import nulls as N


class L1ScriptedAdopters(unittest.TestCase):
    def test_binomial_moments_at_each_dose(self):
        # Closed form: mean n p, variance n p (1 - p).
        p = {0: F(1, 4), 1: F(1, 2), 2: F(3, 4)}
        out = N.scripted_adopters(3, p)
        for dose, q in p.items():
            self.assertEqual(out[dose], (3 * q, 3 * q * (1 - q)))

    def test_flat_dose_has_no_response(self):
        out = N.scripted_adopters(4, {0: F(1, 3), 1: F(1, 3)})
        self.assertEqual(out[0], out[1])


class L2ReedFrost(unittest.TestCase):
    def test_one_susceptible(self):
        # Population 7, 5 immune, one seed -> one susceptible, infected with probability q.
        self.assertEqual(N.reed_frost(7, 5, 1, F(1, 3)), {1: F(2, 3), 2: F(1, 3)})

    def test_two_susceptibles_over_generations(self):
        # Seed infects each of 2 independently with q. Final size 3 can also arise in generation 2:
        # P(final 1) = (1-q)^2; P(final 2) = 2 q (1-q) * (1-q)  [the one infected fails to infect the other];
        # P(final 3) = q^2 + 2 q (1-q) * q.
        q = F(1, 2)
        out = N.reed_frost(3, 0, 1, q)
        self.assertEqual(out, {1: (1 - q) ** 2, 2: 2 * q * (1 - q) ** 2, 3: q ** 2 + 2 * q ** 2 * (1 - q)})
        self.assertEqual(sum(out.values()), 1)

    def test_immunity_reduces_reach(self):
        # Same population of 3 and one seed, q = 1/2. No immune: sizes 1, 2, 3 with 1/4, 1/4, 1/2 (previous
        # test), mean 9/4. One immune leaves one susceptible: sizes 1, 2 with 1/2 each, mean 3/2.
        q = F(1, 2)
        mean = lambda d: sum(k * w for k, w in d.items())
        self.assertEqual(mean(N.reed_frost(3, 0, 1, q)), F(9, 4))
        self.assertEqual(mean(N.reed_frost(3, 1, 1, q)), F(3, 2))   # 1*1/2 + 2*1/2
        self.assertEqual(N.reed_frost(3, 2, 1, q), {1: 1})
        self.assertEqual(N.reed_frost(4, 0, 1, F(0)), {1: 1})  # no zero-probability outcomes listed


class L3CorrelatedMonitors(unittest.TestCase):
    def test_common_cause_closed_form(self):
        # m = 3, p = 1/2, c = 1/4: all miss c + (1-c) p^3 = 11/32; a pair c + (1-c) p^2 = 7/16;
        # one view q = c + (1-c) p = 5/8; phi = (7/16 - 25/64) / (5/8 * 3/8) = 1/5.
        out = N.correlated_monitors(3, F(1, 2), F(1, 4))
        self.assertEqual((out["all_miss"], out["pair_miss"], out["phi"]), (F(11, 32), F(7, 16), F(1, 5)))

    def test_independent_and_degenerate(self):
        self.assertEqual(N.correlated_monitors(4, F(1, 3), 0)["phi"], 0)   # no common cause
        self.assertIsNone(N.correlated_monitors(2, F(1, 3), 1)["phi"])     # every view always misses


class L4IteratedMap(unittest.TestCase):
    def test_matches_closed_form(self):
        # x_t = keep^t x0 + add (1 - keep^t) / (1 - keep).
        keep, add, x0 = F(1, 2), F(1, 10), F(1)
        xs = N.iterated_map(x0, keep, add, 5)
        for t, x in enumerate(xs):
            self.assertEqual(x, keep ** t * x0 + add * (1 - keep ** t) / (1 - keep))

    def test_recovery_nights(self):
        # 1 * (1/2)^t <= 1/8 first at t = 3.
        self.assertEqual(N.recovery_nights(1, F(1, 2), F(1, 8)), 3)
        self.assertIsNone(N.recovery_nights(F(1, 2), 1, 0))
        self.assertEqual(N.recovery_nights(F(1, 2), 0, 0), 1)
        self.assertIsNone(N.recovery_nights(F(1, 2), F(1, 2), 0))  # never exactly 0: must not hang

    def test_recovery_nights_fast_and_exact_near_keep_one(self):
        # row-169 verifier: keep = 9999/10000 took 47 s one night at a time. Check the defining
        # inequalities exactly on both sides of the answer.
        x0, keep, tol = F(1), F(999, 1000), F(1, 10 ** 6)
        start = time.monotonic()
        t = N.recovery_nights(x0, keep, tol)
        self.assertLess(time.monotonic() - start, 10)
        self.assertLessEqual(x0 * keep ** t, tol)
        self.assertGreater(x0 * keep ** (t - 1), tol)


class L6FixedKD(unittest.TestCase):
    def test_hand_worked_two_rounds(self):
        # K=1, D=1, two rounds, u=1/2: sequences RR, R0, 0R, 00 each 1/4.
        # asks: 1, 1, 1, 0 -> 3/4. idle granted rounds: 0, 1, 0, 0 -> 1/4.
        self.assertEqual(N.fixed_kd(1, 1, 2, F(1, 2)), (F(3, 4), F(1, 4)))

    def test_never_promoted(self):
        # K larger than the horizon: every request is asked, never any exposure.
        self.assertEqual(N.fixed_kd(5, 1, 3, F(1, 3)), (F(1), F(0)))


class L7RandomBlocks(unittest.TestCase):
    def test_same_block_probability(self):
        # Closed form: a given pair shares a block with probability (s - 1) / (n - 1).
        for n, s in ((4, 2), (6, 2), (6, 3)):
            self.assertEqual(N.random_blocks(n, s, [(0, 1)]), F(s - 1, n - 1))
        self.assertEqual(N.random_blocks(6, 3, [(0, 1), (2, 3), (4, 5)]), 3 * F(2, 5))


class Malformed(unittest.TestCase):
    def test_raises(self):
        for call in (lambda: N.scripted_adopters(0, {}),
                     lambda: N.scripted_adopters(2, {0: 0.5}),
                     lambda: N.reed_frost(1, 0, 0, F(1, 2)),
                     lambda: N.reed_frost(2, 2, 1, F(1, 2)),
                     lambda: N.iterated_map(1, F(3, 4), F(1, 2), 1),
                     lambda: N.fixed_kd(0, 1, 1, F(1, 2)),
                     lambda: N.random_blocks(5, 2, []),
                     lambda: N.random_blocks(4, 2, [(0, 0)]),
                     lambda: N.random_blocks(4, 2, [(False, True)]),
                     lambda: N.random_blocks(4, 2, [(0.5, 1)]),
                     lambda: N.random_blocks(4, 2, [("a", 1)]),
                     lambda: N.scripted_adopters(2, [F(1, 2)]),
                     lambda: N.correlated_monitors(1, F(1, 2), 0),
                     lambda: N.correlated_monitors(3, 0.5, 0)):
            with self.assertRaises(ValueError):
                call()


if __name__ == "__main__":
    unittest.main()
