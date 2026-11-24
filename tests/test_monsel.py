import unittest

from murmuration import monsel as M

# Four calibration failure episodes; 1 = the view missed it.
MISSES = {
    "actions": [0, 0, 1, 1],    # catches e0, e1 (catch 0.5)
    "reasoning": [0, 0, 1, 1],  # same catches as actions: fully correlated
    "board": [1, 1, 0, 1],      # catches e2 only (catch 0.25)
    "counts": [1, 1, 1, 0],     # catches e3 only (catch 0.25)
}

EXPECTED_HIDDEN = ["board", "actions", "actions", "actions", "board", "counts"]  # seeds 0, 1, 2, 3, 7, 42


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
        with self.assertRaises(ValueError):
            M.ensemble_catch({"a": [1, 0]}, ["z"])  # was KeyError
        # row-169 verifier: unreplayable seed, string and duplicate selections, non-dict table
        for call in (lambda: M.hidden_view(["a", "b"], None),
                     lambda: M.hidden_view(["a", "a", "b"], 0),
                     lambda: M.hidden_view("abc", 0),
                     lambda: M.ensemble_catch({"a": [1, 0], "b": [0, 1]}, "ab"),
                     lambda: M.select([[0, 1]], 1),
                     lambda: M.select({1: [0, 1], "a": [1, 0]}, 1)):
            with self.assertRaises(ValueError):
                call()

    def test_non_list_rows_and_non_string_views_raise(self):
        for call in (lambda: M.ensemble_catch({"a": {0: "x", 1: "y"}}, ["a"]),
                     lambda: M.select({"a": {0: "miss", 1: "miss"}, "b": [0, 1]}, 1),
                     lambda: M.select({"a": {0, 1}}, 1),
                     lambda: M.select({"a": "01"}, 1),
                     lambda: M.hidden_view(["a", 1], 0),
                     lambda: M.hidden_view([["a"], "b"], 0),
                     lambda: M.ensemble_catch({"a": [1, 0]}, [["a"]])):
            with self.assertRaises(ValueError):
                call()

    def test_hidden_view_seeds_are_replay_stable(self):
        # Expected values computed from the current implementation (random.Random(seed).choice on sorted views).
        sel = ["actions", "board", "counts"]
        got = [M.hidden_view(sel, s) for s in (0, 1, 2, 3, 7, 42)]
        self.assertEqual(got, EXPECTED_HIDDEN)
        # Input order and container type must not matter (a set follows per-process string hashing).
        for sel in (["counts", "board", "actions"], {"counts", "actions", "board"}):
            self.assertEqual([M.hidden_view(sel, s) for s in (0, 1, 2, 3, 7, 42)], EXPECTED_HIDDEN)

    def test_hidden_view_covers_every_selected_view_across_seeds(self):
        sel = ["actions", "board", "counts"]
        self.assertEqual({M.hidden_view(sel, s) for s in range(50)}, set(sel))


if __name__ == "__main__":
    unittest.main()
