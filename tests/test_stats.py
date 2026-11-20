import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from murmuration import stats  # noqa: E402


def mean(rs):
    return sum(r["d"] for r in rs) / len(rs)


class T(unittest.TestCase):
    def test_holm(self):
        self.assertEqual(stats.holm([0.01, 0.04, 0.03]), [True, False, False])
        self.assertEqual(stats.holm([0.001, 0.01, 0.02]), [True, True, True])

    def test_all_seeds(self):
        rows = [{"task": "a", "pass": 1}, {"task": "a", "pass": 1}, {"task": "b", "pass": 1}, {"task": "b", "pass": 0}]
        self.assertEqual(stats.all_seeds_rate(rows), 0.5)
        self.assertIsNone(stats.all_seeds_rate([]))

    def test_bootstrap_cluster_and_seed(self):
        # cluster c0 has 2 rows of +1, cluster c1 one row of -1: resampling clusters moves the mean
        rows = [{"c": "c0", "d": 1}, {"c": "c0", "d": 1}, {"c": "c1", "d": -1}]
        a = stats.paired_bootstrap(rows, "c", mean, n=200, seed=3)
        self.assertEqual(a, stats.paired_bootstrap(rows, "c", mean, n=200, seed=3))
        self.assertAlmostEqual(a[0], 1 / 3)
        self.assertEqual((a[1], a[2]), (-1.0, 1.0))  # only whole-cluster draws: means in {-1, 1/3, 1}
        # a by-row resample could give 2/3 or -1/3; whole-cluster draws cannot
        vals = {round(stats.paired_bootstrap(rows, "c", mean, n=1, seed=s)[1], 6) for s in range(50)}
        self.assertTrue(vals <= {-1.0, round(1 / 3, 6), 1.0})

    def test_holm_boundary_is_inclusive_reject(self):
        # p == alpha/(m-rank) is not "greater than", so it still rejects
        self.assertEqual(stats.holm([0.025, 0.9]), [True, False])
        self.assertEqual(stats.holm([0.05]), [True])

    def test_bootstrap_seed_is_honoured(self):
        rows = [{"c": i, "d": float(i * i)} for i in range(12)]
        a = stats.paired_bootstrap(rows, "c", mean, n=300, seed=1)
        self.assertEqual(a, stats.paired_bootstrap(rows, "c", mean, n=300, seed=1))
        self.assertNotEqual(a, stats.paired_bootstrap(rows, "c", mean, n=300, seed=2))

    def test_prereg(self):
        from murmuration.manifest import tree_hash
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "a.py"), "w").write("x=1")
            h = tree_hash([d])
            stats.check_prereg(h, [d])
            open(os.path.join(d, "a.py"), "w").write("x=2")
            with self.assertRaises(ValueError):
                stats.check_prereg(h, [d])


if __name__ == "__main__":
    unittest.main()
