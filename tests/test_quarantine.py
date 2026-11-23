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
        # Supporters d, e and c are verified. d supporting b does not count: d descends from b.
        # e supporting a counts: e is independent. c supporting itself does not count.
        out = Q.releasable(NOTES, verified={"d", "e"}, support={"b": ["d"], "a": ["e"], "c": ["c"]})
        self.assertEqual(out, {"a", "d", "e"})

    def test_source_cannot_corroborate_its_own_derivative(self):
        # a is b's parent, so a (verified) supporting b is not independent; verified e is.
        self.assertEqual(Q.releasable(NOTES, {"a"}, support={"b": ["a"]}), {"a"})
        self.assertEqual(Q.releasable(NOTES, {"e"}, support={"b": ["e"]}), {"b", "e"})

    def test_sibling_from_same_source_is_not_independent(self):
        # b and c both derive from a: verified c supporting b shares provenance; so does d for c.
        self.assertEqual(Q.releasable(NOTES, {"c", "d"}, support={"b": ["c"], "c": ["d"]}), {"c", "d"})

    def test_unverified_notes_cannot_release_each_other(self):
        # row-169 verifier: two unrelated unverified copies offered as support for each other.
        copies = [{"id": "p1", "parents": []}, {"id": "p2", "parents": []}]
        self.assertEqual(Q.releasable(copies, set(), {"p1": ["p2"], "p2": ["p1"]}), set())
        self.assertEqual(Q.releasable(copies, {"p2"}, {"p1": ["p2"]}), {"p1", "p2"})

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
        with self.assertRaises(ValueError):
            Q.releasable(NOTES, None)
        with self.assertRaises(ValueError):
            Q.releasable(NOTES, {"e"}, {"b": "e"})  # a string support list


if __name__ == "__main__":
    unittest.main()
