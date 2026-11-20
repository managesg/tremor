import math
import random
import unittest

from quantum import gatesim as g


def close(a, b, tol=1e-12):
    return abs(a - b) <= tol


class KnownAnswers(unittest.TestCase):
    def test_one_qubit(self):
        # N=2, M=1: O(r,r)=(r,-r); D=[[0,-1],[-1,0]] gives (r,-r); p=sin^2(3pi/4)=0.5
        s = g.grover_states(1, [1], 1)
        r = 1 / math.sqrt(2)
        self.assertTrue(all(close(x, r) for x in s[0]))
        self.assertTrue(close(s[1][0], r) and close(s[1][1], -r))
        self.assertTrue(close(g.marked_probability(s[1], [1]), 0.5))

    def test_two_qubits_one_marked_exact(self):
        # N=4, M=1: one iteration finds the item with certainty; D@O gives -|m>
        s = g.grover_states(2, [2], 1)
        self.assertTrue(close(s[1][2], -1) and all(close(s[1][i], 0) for i in (0, 1, 3)))

    def test_three_qubits(self):
        # N=8, M=1: sin(theta)=1/sqrt8; k=1 -> 25/32, k=2 -> 0.9453125
        s = g.grover_states(3, [5], 2)
        self.assertTrue(close(g.marked_probability(s[2], [5]), 0.9453125))
        self.assertTrue(close(g.marked_probability(s[1], [5]), 25 / 32))

    def test_optimal_iterations(self):
        self.assertEqual([g.optimal_iterations(N, 1) for N in (2, 4, 8, 16, 1024)], [1, 1, 2, 3, 25])
        self.assertEqual(g.optimal_iterations(8, 0), 0)
        self.assertEqual(g.optimal_iterations(8, 8), 0)

    def test_edge_sets(self):
        self.assertTrue(close(g.marked_probability(g.grover_states(3, [], 3)[3], []), 0))
        full = g.grover_states(3, range(8), 2)[2]
        self.assertTrue(close(g.marked_probability(full, range(8)), 1))

    def test_bad_marked(self):
        with self.assertRaises(ValueError):
            g.grover_states(2, [4], 1)


class Properties(unittest.TestCase):
    def test_norm_preserved(self):
        for n in range(1, 7):
            for st in g.grover_states(n, [0, (1 << n) - 1], g.optimal_iterations(1 << n, 2) + 2):
                self.assertTrue(close(sum(abs(a) ** 2 for a in st), 1.0, 1e-12))

    def test_closed_form_vs_simulation(self):
        rng = random.Random(7)
        for n in range(1, 9):
            N = 1 << n
            for M in sorted({1, max(1, N // 4), N // 2, N - 1, N}):
                marked = rng.sample(range(N), M)
                k = g.optimal_iterations(N, M) + 2
                for i, st in enumerate(g.grover_states(n, marked, k)):
                    self.assertTrue(close(g.marked_probability(st, marked), g.closed_form(N, M, i), 1e-11), (n, M, i))

    def test_unitarity_inner_products(self):
        rng = random.Random(3)
        n = 4
        N = 1 << n

        def rand():
            return [complex(rng.gauss(0, 1), rng.gauss(0, 1)) for _ in range(N)]

        def inner(a, b):
            return sum(x.conjugate() * y for x, y in zip(a, b))

        a, b = rand(), rand()
        marked = [1, 6, 11]
        ta, tb = g.grover_iteration(a, n, marked), g.grover_iteration(b, n, marked)
        self.assertTrue(abs(inner(a, b) - inner(ta, tb)) < 1e-10)

    def test_diffuser_is_i_minus_2ss(self):
        st = [complex(i + 1, -i) for i in range(8)]
        mean = sum(st) / 8
        got = g.diffuser(st, 3)
        self.assertTrue(all(abs(x - (y - 2 * mean)) < 1e-12 for x, y in zip(got, st)))

    def test_deterministic(self):
        self.assertEqual(g.grover_states(5, [3, 9], 4), g.grover_states(5, [3, 9], 4))


if __name__ == "__main__":
    unittest.main()
