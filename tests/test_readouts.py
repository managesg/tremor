import random
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from murmuration import readouts as R


class Readouts(unittest.TestCase):
    def test_overdispersion_null_and_planted(self):
        rng = random.Random(1)
        null = [[float(rng.random() < 0.5) for _ in range(5)] for _ in range(2000)]
        self.assertAlmostEqual(R.overdispersion(null), 1.0, delta=0.1)
        # planted: half the task sets always succeed, half never: counts in {0,5}; var = 25*(~1) vs 5*.25
        het = [[1.0] * 5 if i % 2 else [0.0] * 5 for i in range(200)]
        self.assertAlmostEqual(R.overdispersion(het), 5.0, delta=0.1)  # = n for a full split
        self.assertEqual(R.overdispersion([[1.0] * 3] * 4), 1.0)

    def test_rerun_variance(self):
        self.assertEqual(R.rerun_variance([[1, 1, 1], [0, 0, 0]]), 0.0)
        self.assertAlmostEqual(R.rerun_variance([[0, 1], [0, 1]]), 0.5)

    def test_dose_slope_null_and_planted(self):
        rng = random.Random(12)
        doses = [d for d in range(6) for _ in range(20)]
        s, lo, hi = R.dose_slope(doses, [rng.gauss(0, 1) for _ in doses], seed=3)
        self.assertTrue(lo < 0 < hi)
        s, lo, hi = R.dose_slope(doses, [0.3 * d + rng.gauss(0, 1) for d in doses], seed=3)
        self.assertAlmostEqual(s, 0.3, delta=0.08)
        self.assertTrue(lo < 0.3 < hi and lo > 0)
        with self.assertRaises(ValueError):
            R.dose_slope([1, 1, 1], [0, 1, 2])

    def test_reproduction_number(self):
        notes = [{"id": f"x{i}", "parents": []} for i in range(5)]
        self.assertEqual(R.reproduction_number(notes, ["x0"]), (0.0, 1))  # null: nobody adopts
        rng, notes, roots, k = random.Random(4), [], [], 0

        def poisson(lam):  # Knuth
            L, p, n = 2.718281828 ** -lam, 1.0, 0
            while True:
                p *= rng.random()
                if p <= L:
                    return n
                n += 1
        for r in range(3000):
            root = f"r{r}"; roots.append(root); notes.append({"id": root, "parents": []})
            todo = [root]
            while todo:
                par = todo.pop()
                for _ in range(poisson(0.7)):
                    k += 1; cid = f"c{k}"; notes.append({"id": cid, "parents": [par]}); todo.append(cid)
        Rhat, n = R.reproduction_number(notes, roots)
        self.assertAlmostEqual(Rhat, 0.7, delta=0.03)
        self.assertGreater(n, 3000)

    def test_first_generation_offspring_can_exceed_one(self):
        notes = [
            {"id": "seed", "parents": []},
            {"id": "child-1", "parents": ["seed"]},
            {"id": "child-2", "parents": ["seed"]},
            {"id": "grandchild", "parents": ["child-1"]},
        ]
        self.assertEqual(R.first_generation_offspring(notes, ["seed"]), (2.0, {"seed": 2}))

    def test_first_generation_offspring_includes_zero_child_seeds(self):
        notes = [
            {"id": "seed", "parents": []},
            {"id": "quiet", "parents": []},
            {"id": "child", "parents": ["seed", "seed"]},
            {"id": "unrelated", "parents": []},
        ]
        self.assertEqual(
            R.first_generation_offspring(notes, ["seed", "quiet"]),
            (0.5, {"seed": 1, "quiet": 0}),
        )
        self.assertEqual(R.first_generation_offspring(notes, ["quiet"]), (0.0, {"quiet": 0}))

    def test_first_generation_offspring_refuses_ambiguous_parentage(self):
        notes = [
            {"id": "seed-a", "parents": []},
            {"id": "seed-b", "parents": []},
            {"id": "child", "parents": ["seed-a", "seed-b"]},
        ]
        for seeds in (["seed-a", "seed-b"], ["seed-a"]):
            with self.subTest(seeds=seeds), self.assertRaisesRegex(ValueError, "ambiguous parentage.*child"):
                R.first_generation_offspring(notes, seeds)

    def test_first_generation_offspring_refuses_incomplete_root_evidence(self):
        notes = [{"id": "child", "parents": ["seed"]}]
        with self.assertRaisesRegex(ValueError, "at least one planted note"):
            R.first_generation_offspring(notes, [])
        with self.assertRaisesRegex(ValueError, "missing planted notes.*seed"):
            R.first_generation_offspring(notes, ["seed"])
        with self.assertRaisesRegex(ValueError, "duplicate note id.*child"):
            R.first_generation_offspring(notes + notes, ["child"])

    def test_pairwise_miss_independent_and_identical(self):
        rng = random.Random(5)
        ind = [[int(rng.random() < 0.4) for _ in range(4000)] for _ in range(4)]
        r = R.pairwise_miss(ind)
        self.assertAlmostEqual(r["rho_bar"], 0.0, delta=0.05)
        self.assertAlmostEqual(r["n_eff"], 4.0, delta=0.3)
        base = [int(rng.random() < 0.4) for _ in range(500)]
        r = R.pairwise_miss([base, base, base])  # perfectly correlated: n_eff = 1
        self.assertAlmostEqual(r["rho_bar"], 1.0)
        self.assertAlmostEqual(r["n_eff"], 1.0)
        self.assertAlmostEqual(r["joint"][0][1], sum(base) / 500)

    def test_pairwise_miss_planted_rho(self):
        # shared-cause model: miss = common (p=.5) with prob .6 else independent coin; rho known by hand
        rng, E, m = random.Random(6), 20000, 3
        common = [rng.random() < 0.5 for _ in range(E)]
        mons = [[int(c if rng.random() < 0.6 else rng.random() < 0.5) for c in common] for _ in range(m)]
        # corr(a,b) = 0.6^2 = 0.36 for symmetric p=.5 mixing
        r = R.pairwise_miss(mons)
        self.assertAlmostEqual(r["rho_bar"], 0.36, delta=0.03)
        self.assertAlmostEqual(r["n_eff"], 3 / (1 + 2 * 0.36), delta=0.1)

    def test_recovery_time(self):
        self.assertEqual(R.recovery_time([1, 1, 1, 1], 2), 0)  # null: no shock effect
        s = [1, 1, 1, 0, 0.4, 0.7, 0.95, 1, 1]
        self.assertEqual(R.recovery_time(s, 3, tol=0.1), 3)
        self.assertEqual(R.recovery_time(s, 3, tol=0.1, hold=2), 3)
        self.assertIsNone(R.recovery_time([1, 1, 0, 0, 0], 2, tol=0.1))
        self.assertEqual(R.recovery_time([1, 1, 0, 1, 0, 1, 1], 2, tol=0.1, hold=2), 3)


if __name__ == "__main__":
    unittest.main()
