import math
import unittest

from tremor import sgv

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

    def test_nine_reruns_still_pools_ten_keep_their_own(self):
        # The stated threshold is 10 reruns: a unit with 9 pools by task type, a unit with 10 keeps its own.
        r = {"A": [0, 4] * 5, "N": [0, 4, 0, 4, 0, 4, 0, 4, 4]}
        est = sgv.dispersion(r, {"A": 4, "N": 4}, task_type={"A": "t", "N": "t"})
        self.assertAlmostEqual(est["N"], 40 / 9)  # A's estimate, not N's own 9-rerun value
        own = sgv.dispersion(r, {"A": 4, "N": 4}, task_type={"A": "t", "N": "t"}, min_reruns=9)["N"]
        self.assertNotAlmostEqual(own, 40 / 9)
        self.assertEqual(sgv.MIN_RERUNS, 10)

    def test_bool_counts_items_and_floor_raise(self):
        for call in (lambda: sgv.dispersion({"A": [True, 0] * 5}, {"A": 4}),
                     lambda: sgv.dispersion({"A": [0, 4] * 5}, {"A": True}),
                     lambda: sgv.dispersion({"A": [0, 4] * 5}, {"A": 4}, min_reruns=True)):
            with self.assertRaises(ValueError):
                call()

    def test_bool_budget_and_rerun_cost_raise(self):
        r = {"A": [0, 4] * 5}
        for args in ((True, 0), (1, True), (False, 0)):
            with self.assertRaises(ValueError):
                sgv.allocate(r, {"A": 4}, *args)

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

    def test_wrong_rerun_type_in_allocate_is_value_error(self):
        for bad in (5, None, "ab"):
            with self.assertRaises(ValueError):
                sgv.allocate({"a": bad}, {"a": 3}, 10, 1)

    def test_pooled_mean_near_float_max_is_exact_or_value_error(self):
        big = 10 ** 308
        cs = [0] * 9 + [big]
        r, n = {"a": cs, "b": cs, "c": [1]}, {"a": big, "b": big, "c": big}
        tt = {"a": "t", "b": "t", "c": "t"}
        est = sgv.dispersion(r, n, tt)  # fmean overflowed: OverflowError
        self.assertEqual(est["c"], est["a"])
        self.assertTrue(math.isfinite(est["c"]))

    def test_allocate_total_overflow_never_drops_budget(self):
        big = 10 ** 308
        cs = [0] * 9 + [big]
        out = sgv.allocate({"a": cs, "b": cs}, {"a": big, "b": big}, 10, 0)  # total was inf: all shares 0.0
        self.assertEqual(out, {"a": 5.0, "b": 5.0})

    def test_allocate_unequal_shares_with_huge_estimates(self):
        big = 10 ** 308
        a, b = [0] * 9 + [big], [0] * 8 + [big, big]
        out = sgv.allocate({"a": a, "b": b}, {"a": big, "b": big}, 10, 0)
        self.assertTrue(all(math.isfinite(v) for v in out.values()))
        self.assertAlmostEqual(sum(out.values()), 10)

    def test_malformed_inputs_raise(self):
        for call in (lambda: sgv.allocate({"A": [1] * 10}, ITEMS, 5, 1),        # reruns cost 10 > budget 5
                     lambda: sgv.dispersion({"A": [5] * 10}, ITEMS),              # count above items
                     lambda: sgv.dispersion({"A": [-1, 4] * 5}, {"A": 4}),        # negative pass count
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

    def test_negative_rerun_cost_rejected(self):
        with self.assertRaises(ValueError):
            sgv.allocate({"A": [0, 4] * 5}, ITEMS, 100, -1)

    def test_budget_exactly_spent_by_reruns_is_accepted(self):
        # 2 units x 2 reruns x cost 1 = 4 = budget: remaining 0, so every share is 0.
        r = {"A": [1, 3], "B": [0, 4]}
        out = sgv.allocate(r, ITEMS, 4, 1, min_reruns=2)
        self.assertEqual(out, {"A": 0.0, "B": 0.0})

    def test_untyped_units_do_not_pool_with_each_other(self):
        # A has 10 reruns and a defined estimate; B has 2 and no task type, so it has no peers: None.
        r = {"A": [0, 4] * 5, "B": [1, 3]}
        est = sgv.dispersion(r, ITEMS)
        self.assertAlmostEqual(est["A"], 40 / 9)
        self.assertIsNone(est["B"])

    def test_min_reruns_floor_is_two(self):
        with self.assertRaises(ValueError):
            sgv.dispersion({"A": [1, 3]}, ITEMS, min_reruns=1)
        with self.assertRaises(ValueError):
            sgv.allocate({"A": [1, 3]}, ITEMS, 10, 1, min_reruns=1)
        # a unit with 1 rerun has no estimate at all
        self.assertIsNone(sgv.dispersion({"A": [2]}, ITEMS, min_reruns=2)["A"])


if __name__ == "__main__":
    unittest.main()
