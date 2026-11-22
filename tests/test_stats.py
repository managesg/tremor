import os
import sys
import tempfile
import unittest
from decimal import Decimal, localcontext
from fractions import Fraction

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

    def test_holm_refuses_any_invalid_p_value_before_step_down(self):
        invalid = (float("nan"), float("inf"), float("-inf"), Decimal("NaN"),
                   Decimal("sNaN"), Decimal("Infinity"), Fraction(-1, 10),
                   Decimal("1.0000000000000000000001"), True, "0.05", None)
        for value in invalid:
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "pvals\\[1\\]"):
                stats.holm([0.5, value])

    def test_holm_validates_alpha_even_for_an_empty_family(self):
        invalid = (float("nan"), float("inf"), Decimal("sNaN"), Fraction(-1, 7),
                   Decimal("1.0000000000000000000001"), True, "0.05")
        for value in invalid:
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "alpha"):
                stats.holm([], alpha=value)
        self.assertEqual(stats.holm([]), [])
        self.assertEqual(stats.holm([1, 0], alpha=0), [False, True])
        self.assertEqual(stats.holm([1], alpha=1), [True])

    def test_holm_preserves_exact_nonfloat_thresholds_and_input_order(self):
        exact = Fraction(1, 60)
        self.assertEqual(stats.holm([Fraction(1, 2), exact, Fraction(1, 40)], alpha=Fraction(1, 20)),
                         [False, True, True])
        with localcontext() as context:
            context.prec = 2
            self.assertEqual(stats.holm([Decimal("0.24"), 0.8, Fraction(1, 4)], alpha=Decimal("0.75")),
                             [True, False, True])
            self.assertEqual(stats.holm([Decimal("0.017"), 0.5, Fraction(1, 4)], alpha=Decimal("0.05")),
                             [False, False, False])

    def test_holm_integer_alpha_keeps_an_exact_fraction_cutoff(self):
        values = [Fraction(1, 2), Fraction(1, 3), Fraction(2, 3)]
        self.assertEqual(stats.holm(values, alpha=1), [True, True, True])
        self.assertEqual(stats.holm(values, alpha=1.0), [False, False, False])

    def test_bootstrap_seed_is_honoured(self):
        rows = [{"c": i, "d": float(i * i)} for i in range(12)]
        a = stats.paired_bootstrap(rows, "c", mean, n=300, seed=1)
        self.assertEqual(a, stats.paired_bootstrap(rows, "c", mean, n=300, seed=1))
        self.assertNotEqual(a, stats.paired_bootstrap(rows, "c", mean, n=300, seed=2))

    def _hrows(self, k=12):
        return [{"c": i, "none": 0.2, "play": 0.5, "code": 0.8} for i in range(k)]

    def test_hdi_known_answer_and_range(self):
        # all clusters identical: (0.8-0.5)/(0.8-0.2) = 0.5, interval collapses
        h = stats.hdi(self._hrows(), "c", n=200, seed=1)
        self.assertFalse(h["undefined"])
        self.assertAlmostEqual(h["point"], 0.5)
        self.assertAlmostEqual(h["lo"], 0.5)
        self.assertAlmostEqual(h["hi"], 0.5)
        # play beats code -> below 0; play hurts -> above 1; both kept
        lo_ = [{**r, "play": 0.9} for r in self._hrows()]
        hi_ = [{**r, "play": 0.1} for r in self._hrows()]
        self.assertAlmostEqual(stats.hdi(lo_, "c", n=50)["point"], -1 / 6)
        self.assertAlmostEqual(stats.hdi(hi_, "c", n=50)["point"], 7 / 6)

    def test_hdi_denominator_containing_zero_is_undefined(self):
        rows = [{"c": i, "none": 0.5, "play": 0.4, "code": 0.5 + (0.3 if i % 2 else -0.3)} for i in range(10)]
        h = stats.hdi(rows, "c", n=300, seed=2)
        self.assertTrue(h["undefined"])
        self.assertIsNone(h["point"])
        self.assertIsNone(h["lo"])
        self.assertEqual(h["reason"], "code_gain_unresolved")  # was "contains 0" before the margin rule
        self.assertLessEqual(h["denom_ci"][0], 0)
        self.assertGreaterEqual(h["denom_ci"][1], 0)
        z = [{"c": i, "none": 0.5, "play": 0.4, "code": 0.5} for i in range(5)]  # denominator exactly 0
        zz = stats.hdi(z, "c", n=20)
        self.assertTrue(zz["undefined"])
        self.assertEqual(zz["degenerate_resamples"], 20)
        nz = [{"c": i, "none": 0.5, "play": 0.4, "code": 0.5 + 1e-12} for i in range(5)]  # near-zero counts too
        self.assertEqual(stats.hdi(nz, "c", n=20)["degenerate_resamples"], 20)
        self.assertTrue(stats.hdi([], "c")["undefined"])

    def test_hdi_margin_rule(self):
        r = stats.hdi(self._hrows(), "c", n=100, seed=1)  # code gain 0.6 resolved
        self.assertEqual((r["status"], r["recovered"]), ("interpretable", 0.5))
        self.assertAlmostEqual(r["contrasts"]["play_none"]["d"], 0.3)
        self.assertAlmostEqual(r["contrasts"]["code_play"]["d"], 0.3)
        small = [{**q, "code": 0.25} for q in self._hrows()]  # resolved above 0 but under 10 points
        s = stats.hdi(small, "c", n=100)
        self.assertEqual((s["status"], s["reason"], s["point"], s["recovered"]),
                         ("not_interpretable", "code_gain_unresolved", None, None))
        self.assertAlmostEqual(s["contrasts"]["code_none"]["d"], 0.05)  # raw contrast still shown
        self.assertEqual(stats.hdi(small, "c", n=100, margin=0.04)["status"], "interpretable")
        neg = [{**q, "code": 0.0} for q in self._hrows()]
        g = stats.hdi(neg, "c", n=100)
        self.assertEqual((g["status"], g["reason"]), ("not_interpretable", "code_worse_than_none"))
        for k in ("play_none", "code_none", "code_play"):
            self.assertEqual(set(g["contrasts"][k]), {"d", "lo", "hi"})
        straddle = [{"c": i, "none": 0.5, "play": 0.4, "code": 0.5 + (0.3 if i % 2 else -0.3)} for i in range(10)]
        self.assertEqual(stats.hdi(straddle, "c", n=200, seed=2)["reason"], "code_gain_unresolved")
        # point 0.2 clears the margin but the interval reaches 0: still unresolved
        wide = [{"c": i, "none": 0.0, "play": 0.1, "code": 0.2 + (0.6 if i % 2 else -0.6)} for i in range(10)]
        w = stats.hdi(wide, "c", n=300, seed=1)
        self.assertGreaterEqual(w["contrasts"]["code_none"]["d"], 0.1)
        self.assertEqual(w["reason"], "code_gain_unresolved")

    def test_hdi_cluster_permutation_and_seed(self):
        import random
        rows = [{"c": i // 3, "none": 0.1 * (i % 3), "play": 0.5 + 0.05 * (i % 5), "code": 0.9 - 0.02 * (i % 4)}
                for i in range(30)]
        a = stats.hdi(rows, "c", n=200, seed=7)
        self.assertEqual(a, stats.hdi(rows, "c", n=200, seed=7))
        self.assertNotEqual(a["lo"], stats.hdi(rows, "c", n=200, seed=8)["lo"])
        shuf = rows[:]
        random.Random(0).shuffle(shuf)  # permuting rows, hence within clusters, changes nothing
        self.assertEqual(a, stats.hdi(shuf, "c", n=200, seed=7))
        # clusters resampled whole: two clusters with HDI 0 and 1 only ever give 0, 0.5-ish pools or 1
        two = [{"c": "a", "none": 0, "play": 1, "code": 1}, {"c": "b", "none": 0, "play": 0, "code": 1}]
        self.assertAlmostEqual(stats.hdi(two, "c", n=50, seed=1)["point"], 0.5)

    def test_emergence_gain_and_nominal_group(self):
        self.assertAlmostEqual(stats.emergence_gain([1, 1, 0], [1, 0, 0]), 1 / 3)
        self.assertEqual(stats.emergence_gain(0.7, 0.5), 0.7 - 0.5)
        rows = [{"task": "t1", "agent": 1, "answer": "x", "pass": 1},
                {"task": "t1", "agent": 2, "answer": "x", "pass": 1},
                {"task": "t1", "agent": 3, "answer": "y", "pass": 0},
                {"task": "t2", "agent": 1, "answer": "z", "pass": 0}]
        g = stats.nominal_group(rows)
        self.assertEqual([(r["task"], r["pass"], r["unique"], r["duplicates"]) for r in g],
                         [("t1", True, 2, 1), ("t2", False, 1, 0)])

    def test_incoherence(self):
        self.assertIsNone(stats.incoherence([1, 2]))
        self.assertEqual(stats.incoherence([2, 2, 2]), 0.0)
        self.assertEqual(stats.incoherence([0, 0, 0]), 0.0)
        self.assertAlmostEqual(stats.incoherence([1, 2, 3]), 1 / 7)  # var 2/3, bias^2 4
        self.assertAlmostEqual(stats.incoherence([1, -1, 1, -1]), 1.0)

    def test_prereg(self):
        from murmuration.manifest import tree_hash
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "a.py"), "w").write("x=1")
            h = tree_hash([d])
            stats.check_prereg(h, [d])
            open(os.path.join(d, "a.py"), "w").write("x=2")
            with self.assertRaises(ValueError):
                stats.check_prereg(h, [d])


class PairedT(unittest.TestCase):
    def test_known_answer(self):
        # diffs 1,2,3,4,5: mean 3, sd sqrt(2.5), se sqrt(.5)=0.70711, t=4.2426, df 4, crit 2.776
        r = stats.paired_t([(x + 10, 10) for x in (1, 2, 3, 4, 5)])
        self.assertAlmostEqual(r["mean_diff"], 3)
        self.assertAlmostEqual(r["se"], 0.5 ** 0.5)
        self.assertAlmostEqual(r["t"], 3 / 0.5 ** 0.5)
        self.assertEqual(r["df"], 4)
        self.assertAlmostEqual(r["ci95_lo"], 3 - 2.776 * 0.5 ** 0.5)
        self.assertAlmostEqual(r["ci95_hi"], 3 + 2.776 * 0.5 ** 0.5)

    def test_df19_and_large_df(self):
        r = stats.paired_t([(i % 2, 0) for i in range(20)])  # df 19 -> 2.093
        self.assertAlmostEqual(r["ci95_hi"] - r["mean_diff"], 2.093 * r["se"])
        big = stats.paired_t([(i % 2, 0) for i in range(80)])  # df 79 -> normal 1.96
        self.assertAlmostEqual(big["ci95_hi"] - big["mean_diff"], 1.96 * big["se"])

    def test_constant_and_too_few(self):
        r = stats.paired_t([(2, 1), (3, 2)])
        self.assertEqual((r["se"], r["t"], r["ci95_lo"], r["ci95_hi"]), (0.0, None, 1.0, 1.0))
        with self.assertRaises(ValueError):
            stats.paired_t([(1, 0)])

    def test_default_resamples(self):
        import inspect
        for f in (stats.paired_bootstrap, stats.hdi):
            self.assertEqual(inspect.signature(f).parameters["n"].default, 10000)


if __name__ == "__main__":
    unittest.main()
