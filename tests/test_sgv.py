import unittest

from murmuration import sgv


class SusceptibilityGuidedVerification(unittest.TestCase):
    def test_worked_allocation(self):
        # Unit "a": five 1s and five 0s, mean 0.5, variance 2.5 / 9, overdispersion (2.5 / 9) / 0.25 = 10 / 9.
        # Unit "b": all 1 -> mean 1, undefined (None), no share. Unit "c": 3 reruns, type "t" -> pooled 10 / 9.
        reruns = {"a": [1, 0] * 5, "b": [1] * 10, "c": [1, 0, 1]}
        # Budget 100, rerun cost 1 per rerun, 23 reruns -> 77 left, split evenly between a and c.
        out = sgv.allocate(reruns, 100, 1, task_type={"a": "t", "c": "t", "b": "u"})
        self.assertAlmostEqual(out["a"], 38.5)
        self.assertAlmostEqual(out["c"], 38.5)
        self.assertEqual(out["b"], 0.0)

    def test_overdispersion_not_raw_variance_sets_the_ranking(self):
        # A = [0.1, 0.9] * 5: mean 0.5, variance 1.6 / 9, overdispersion (1.6 / 9) / 0.25 = 0.711...
        # B = [1] + [0] * 9: mean 0.1, variance 0.9 / 9 = 0.1, overdispersion 0.1 / 0.09 = 1.111...
        # Raw variance would rank A above B; overdispersion ranks B above A.
        est = sgv.dispersion({"A": [0.1, 0.9] * 5, "B": [1] + [0] * 9})
        self.assertAlmostEqual(est["A"], 1.6 / 9 / 0.25)
        self.assertAlmostEqual(est["B"], 0.1 / 0.09)
        self.assertGreater(est["B"], est["A"])

    def test_undersampled_without_peers_is_missing(self):
        est = sgv.dispersion({"x": [1, 0, 1]})
        self.assertEqual(est, {"x": None})
        self.assertIsNone(sgv.allocate({"x": [1, 0, 1]}, 10, 0))

    def test_no_signal_returns_none(self):
        self.assertIsNone(sgv.allocate({"a": [1] * 10, "b": [0] * 10}, 50, 1))

    def test_malformed_inputs_raise(self):
        with self.assertRaises(ValueError):
            sgv.allocate({"a": [1] * 10}, 5, 1)       # reruns cost 10 > budget 5
        with self.assertRaises(ValueError):
            sgv.allocate({"a": [2] * 10}, 50, 1)      # outcome outside [0, 1]
        with self.assertRaises(ValueError):
            sgv.allocate({"a": []}, 50, 1)
        with self.assertRaises(ValueError):
            sgv.dispersion({"a": [1, 0]}, min_reruns=2.5)


if __name__ == "__main__":
    unittest.main()
