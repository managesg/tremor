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

    def test_root_note_not_released_by_its_own_verified_child(self):
        n = [{"id": "a", "parents": []}, {"id": "b", "parents": ["a"]}]
        self.assertEqual(Q.releasable(n, {"b"}, {"a": ["b"]}), {"b"})

    def test_unknown_supporter_does_not_release(self):
        n = [{"id": "a", "parents": []}, {"id": "b", "parents": ["a"]}]
        self.assertEqual(Q.releasable(n, {"ghost"}, {"a": ["ghost"]}), set())

    def test_non_list_support_value_is_rejected(self):
        for bad in (5, None):
            with self.assertRaises(ValueError):
                Q.releasable(NOTES, {"e"}, {"b": bad})

    def test_verified_string_is_rejected(self):
        with self.assertRaises(ValueError):
            Q.releasable(NOTES, "e")

    def test_non_mapping_support_is_rejected(self):
        for bad in (["b"], "b"):
            with self.assertRaises(ValueError):
                Q.releasable(NOTES, {"e"}, bad)

    def test_non_string_ids_are_rejected(self):
        mixed = [{"id": 1, "parents": []}, {"id": "x", "parents": []}]
        with self.assertRaises(ValueError):
            Q.verification_order(mixed, set())

    def test_grandparent_cannot_release_its_grandchild(self):
        # d derives from b, which derives from a: a is in d's lineage two levels up.
        self.assertEqual(Q.releasable(NOTES, {"a"}, {"d": ["a"]}), {"a"})
        self.assertEqual(Q.ancestors(NOTES, "d"), {"a", "b"})

    def test_one_shot_iterator_notes_are_rejected(self):
        # notes are read more than once; an iterator would be empty on the second pass.
        for call in (lambda: Q.releasable(iter(NOTES), {"a"}, {"d": ["a"]}),
                     lambda: Q.verification_order(iter(NOTES), set()),
                     lambda: Q.ancestors(iter(NOTES), "d")):
            with self.assertRaises(ValueError):
                call()


if __name__ == "__main__":
    unittest.main()
