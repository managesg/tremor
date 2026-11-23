import unittest

from murmuration import quarantine as Q

# Provenance: a is a root; b and c derive from a; d derives from b. e is unrelated.
NOTES = [
    {"id": "a", "parents": []},
    {"id": "b", "parents": ["a"]},
    {"id": "c", "parents": ["a"]},
    {"id": "d", "parents": ["b"]},
    {"id": "e", "parents": []},
]


class Quarantine(unittest.TestCase):
    def test_cycle_check_rejects_self_tracing_support(self):
        # d supporting b does not count: d descends from b. e supporting a counts: e is independent.
        out = Q.releasable(NOTES, verified=set(), support={"b": ["d"], "a": ["e"], "c": ["c"]})
        self.assertEqual(out, {"a"})

    def test_source_cannot_corroborate_its_own_derivative(self):
        # a is b's parent, so a supporting b is not independent; e is.
        self.assertEqual(Q.releasable(NOTES, set(), support={"b": ["a"]}), set())
        self.assertEqual(Q.releasable(NOTES, set(), support={"b": ["e"]}), {"b"})

    def test_verified_notes_are_released(self):
        self.assertEqual(Q.releasable(NOTES, verified={"c"}), {"c"})

    def test_budget_goes_to_highest_r_first(self):
        # R with one root: a -> {a,b,c,d}: (4-1)/4 = 0.75; b -> {b,d}: 1/2 = 0.5; c, d, e: 0.
        order = Q.verification_order(NOTES, verified={"e"})
        self.assertEqual(order, ["a", "b", "c", "d"])

    def test_malformed_inputs_raise(self):
        with self.assertRaises(ValueError):
            Q.releasable([{"id": "x"}], set())
        with self.assertRaises(ValueError):
            Q.releasable([{"id": "x", "parents": []}, {"id": "x", "parents": []}], set())


if __name__ == "__main__":
    unittest.main()
