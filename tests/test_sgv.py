import unittest

from murmuration import sgv

ITEMS = {"A": 4, "B": 4, "C": 4, "D": 4}


class SusceptibilityGuidedVerification(unittest.TestCase):
    def test_worked_overdispersion(self):
        # n = 4 items per rerun, 10 reruns each, binomial variance n p (1 - p) = 4 * 0.5 * 0.5 = 1.
        # A: counts 0, 4 alternating -> mean 2, squared deviations 10 * 4 = 40, variance 40 / 9 -> 40 / 9.
        # B: counts always 2 -> variance 0 -> 0 (reruns agree more than independent items would).
        # C: counts 1, 3 alternating -> squared deviations 10 * 1 = 10, variance 10 / 9 -> 10 / 9.
        r = {"A": [0, 4] * 5, "B": [2] * 10, "C": [1, 3] * 5}
        est = sgv.dispersion(r, ITEMS)
        self.assertAlmostEqual(est["A"], 40 / 9)
        self.assertEqual(est["B"], 0)
        self.assertAlmostEqual(est["C"], 10 / 9)
        # Budget 100, rerun cost 1, 30 reruns -> 70 left, split 40 : 0 : 10.
        out = sgv.allocate(r, ITEMS, 100, 1)
        self.assertAlmostEqual(out["A"], 56)
        self.assertEqual(out["B"], 0.0)
        self.assertAlmostEqual(out["C"], 14)

    def test_undersampled_unit_pools_by_task_type(self):
        # D has 3 reruns (< 10): it takes the mean of A and C, (40 / 9 + 10 / 9) / 2 = 25 / 9.
        r = {"A": [0, 4] * 5, "C": [1, 3] * 5, "D": [0, 4, 0]}
        est = sgv.dispersion(r, ITEMS, task_type={"A": "t", "C": "t", "D": "t"})
        self.assertAlmostEqual(est["D"], 25 / 9)
        self.assertIsNone(sgv.dispersion({"D": [0, 4, 0]}, ITEMS)["D"])

    def test_single_item_pass_fail_has_no_signal(self):
        # One pass/fail item: variance is fixed by the mean, so overdispersion is undefined, not a constant.
        r = {"half": [1, 0] * 5, "one_in_ten": [1] + [0] * 9}
        self.assertEqual(sgv.dispersion(r, {"half": 1, "one_in_ten": 1}), {"half": None, "one_in_ten": None})
        self.assertIsNone(sgv.allocate(r, {"half": 1, "one_in_ten": 1}, 100, 1))

    def test_huge_finite_budget_stays_finite(self):
        # re-verifier at 08659a3: remaining * v overflowed to inf before dividing by the total.
        out = sgv.allocate({"A": [0, 4] * 5, "B": [2, 2] * 5}, {"A": 4, "B": 4}, 1e308, 0)
        self.assertEqual(out, {"A": 1e308, "B": 0.0})

    def test_no_signal_returns_none(self):
        self.assertIsNone(sgv.allocate({"A": [4] * 10, "B": [0] * 10}, ITEMS, 50, 1))

    def test_pooling_uses_matching_task_type_and_skips_none_peer(self):
        # A, B differ in type; C (type t) has estimate None (p == 1) and must not drag the pool down.
        r = {"A": [0, 4] * 5, "B": [1, 3] * 5, "C": [4] * 10, "D": [0, 4, 0], "E": [1, 3, 1]}
        tt = {"A": "t", "B": "u", "C": "t", "D": "t", "E": "u"}
        est = sgv.dispersion(r, {k: 4 for k in r}, task_type=tt)
        self.assertIsNone(est["C"])
        self.assertAlmostEqual(est["D"], 40 / 9)
        self.assertAlmostEqual(est["E"], 10 / 9)

    def test_probability_decided_on_integer_sum(self):
        # 2**53 items: the float share rounds to 1.0, but 9 of 10 reruns differ by one item.
        big = 2 ** 53
        est = sgv.dispersion({"A": [big] * 9 + [big - 1]}, {"A": big}, min_reruns=2)
        self.assertAlmostEqual(est["A"], 1.0)
        self.assertEqual(sgv.dispersion({"A": [big] * 10, "B": [0] * 10}, {"A": big, "B": big}),
                         {"A": None, "B": None})

    def test_huge_counts_overflow_is_value_error_or_exact(self):
        with self.assertRaises(ValueError):
            sgv.dispersion({"A": [0, 10 ** 400] * 5}, {"A": 10 ** 400})
        n = 10 ** 307
        est = sgv.dispersion({"A": [0, n] * 5}, {"A": n})["A"]
        self.assertAlmostEqual(est / n, 10 / 9)

    def test_dispersion_type_checks(self):
        for call in (lambda: sgv.dispersion([[0, 4] * 5], ITEMS),
                     lambda: sgv.dispersion({"A": [0, 4] * 5}, [4]),
                     lambda: sgv.dispersion({"A": 5}, ITEMS),
                     lambda: sgv.dispersion({1: [0, 4], "b": [0, 4]}, {}),   # mixed-type unit keys
                     lambda: sgv.dispersion({"A": [0, 4] * 5}, ITEMS, task_type=["t"])):
            with self.assertRaises(ValueError):
                call()

    def test_malformed_inputs_raise(self):
        for call in (lambda: sgv.allocate({"A": [1] * 10}, ITEMS, 5, 1),        # reruns cost 10 > budget 5
                     lambda: sgv.dispersion({"A": [5] * 10}, ITEMS),              # count above items
                     lambda: sgv.dispersion({"A": []}, ITEMS),
                     lambda: sgv.dispersion({"Z": [1, 2]}, ITEMS),                # no item count
                     lambda: sgv.dispersion({"A": [1, 2]}, {"A": 0}),
                     lambda: sgv.dispersion({"A": [1, 2]}, ITEMS, min_reruns=2.5),
                     # row-169 verifier: NaN and infinite budgets produced NaN and infinite shares
                     lambda: sgv.allocate({"A": [0, 4] * 5}, ITEMS, float("nan"), 1),
                     lambda: sgv.allocate({"A": [0, 4] * 5}, ITEMS, 100, float("nan")),
                     lambda: sgv.allocate({"A": [0, 4] * 5}, ITEMS, float("inf"), 1),
                     lambda: sgv.allocate({"A": [0, 4] * 5}, ITEMS, 10 ** 400, 1),
                     # third pass: an int cost times reruns overflowed the float budget; list reruns
                     lambda: sgv.allocate({"A": [0, 4] * 10}, {"A": 4}, 1e308, 10 ** 308),
                     lambda: sgv.allocate([[0, 4] * 5], ITEMS, 100, 1)):
            with self.assertRaises(ValueError):
                call()


if __name__ == "__main__":
    unittest.main()
