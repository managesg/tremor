import unittest

from murmuration import sgv


class SusceptibilityGuidedVerification(unittest.TestCase):
    def test_worked_allocation(self):
        # Unit "a": five 1s and five 0s, mean 0.5, squared deviations 10 * 0.25 = 2.5, variance 2.5 / 9.
        # Unit "b": all 1 -> variance 0. Unit "c": 3 reruns, type "t" like "a" -> pooled 0.2777...
        reruns = {"a": [1, 0] * 5, "b": [1] * 10, "c": [1, 0, 1]}
        # Budget 100, rerun cost 1 per rerun, 23 reruns -> 77 left, split evenly between a and c.
        out = sgv.allocate(reruns, 100, 1, task_type={"a": "t", "c": "t", "b": "u"})
        self.assertAlmostEqual(out["a"], 38.5)
        self.assertAlmostEqual(out["c"], 38.5)
        self.assertEqual(out["b"], 0.0)

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


if __name__ == "__main__":
    unittest.main()
