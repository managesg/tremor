import unittest

from murmuration import monsel as M

# Four calibration failure episodes; 1 = the view missed it.
MISSES = {
    "actions": [0, 0, 1, 1],    # catches e0, e1 (catch 0.5)
    "reasoning": [0, 0, 1, 1],  # same catches as actions: fully correlated
    "board": [1, 1, 0, 1],      # catches e2 only (catch 0.25)
    "counts": [1, 1, 1, 0],     # catches e3 only (catch 0.25)
}


class MonitorSelection(unittest.TestCase):
    def test_greedy_prefers_complementary_views(self):
        # Step 1: actions and reasoning tie at 0.5; name order picks "actions".
        # Step 2: reasoning adds nothing (0.5); board or counts add one episode (0.75); "board" by name.
        # Step 3: counts covers the last episode (1.0).
        self.assertEqual(M.select(MISSES, 3), ["actions", "board", "counts"])
        self.assertEqual(M.ensemble_catch(MISSES, ["actions", "board", "counts"]), 1.0)
        # Top-2 by individual catch (actions, reasoning) catches only 0.5.
        self.assertEqual(M.ensemble_catch(MISSES, ["actions", "reasoning"]), 0.5)

    def test_hidden_view_is_seeded_and_from_selection(self):
        sel = ["actions", "board", "counts"]
        self.assertEqual(M.hidden_view(sel, seed=7), M.hidden_view(sel, seed=7))
        self.assertIn(M.hidden_view(sel, seed=1), sel)
        self.assertEqual(M.ensemble_catch(MISSES, []), 0.0)

    def test_malformed_inputs_raise(self):
        with self.assertRaises(ValueError):
            M.select(MISSES, 0)
        with self.assertRaises(ValueError):
            M.select({"a": [0, 1], "b": [0]}, 1)
        with self.assertRaises(ValueError):
            M.select({"a": [0, 2]}, 1)
        with self.assertRaises(ValueError):
            M.hidden_view([], seed=0)


if __name__ == "__main__":
    unittest.main()
