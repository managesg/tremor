import unittest

from murmuration import vreplay as V


class VerifiedReplay(unittest.TestCase):
    def test_gate_keeps_only_checked_claims(self):
        world = {"x": 1, "y": 2}
        claims = [("x", 1), ("y", 3), ("z", 0)]
        self.assertEqual(V.gate(claims, lambda c: world.get(c[0]) == c[1]), [("x", 1)])
        self.assertEqual(V.gate(claims, lambda c: 1), [])  # truthy is not True

    def test_replay_keeps_old_episodes(self):
        self.assertEqual(V.replay_batch(["d1", "d2"], ["d3"]), ["d1", "d2", "d3"])

    def test_controller_lowers_on_rise_only(self):
        # (recovery_time, R): R rose 0.2 -> 0.4, so rung 3 -> 2.
        self.assertEqual(V.next_strength(3, (4, 0.2), (4, 0.4)), 2)
        self.assertEqual(V.next_strength(3, (4, 0.4), (2, 0.1)), 3)   # both fell: unchanged
        self.assertEqual(V.next_strength(0, (1, 0.1), (5, 0.1)), 0)   # floor at the weakest rung
        self.assertEqual(V.next_strength(2, (None, 0.1), (9, 0.1)), 2)  # missing reading: unchanged

    def test_retain_by_use_not_age(self):
        # "old" is oldest but least used; capacity 2 keeps the two most used.
        uses = {"old": 0, "mid": 5, "new": 2}
        self.assertEqual(V.retain(["old", "mid", "new"], uses, 2), ["mid", "new"])

    def test_malformed_inputs_raise(self):
        with self.assertRaises(ValueError):
            V.gate([], check=None)
        with self.assertRaises(ValueError):
            V.next_strength(-1, (1, 1), (1, 1))
        with self.assertRaises(ValueError):
            V.next_strength(3, (5,), (5, 9))  # was silently truncated by zip, hiding the rise in R
        # row-169 verifier: text compared as text, NaN read as missing, strings read as lists, duplicates
        for call in (lambda: V.next_strength(3, ("10", 0), ("9", 0)),
                     lambda: V.next_strength(3, (float("nan"), 0.1), (9, 0.1)),
                     lambda: V.next_strength(3, None, (1, 1)),
                     lambda: V.retain(["a", "a"], {"a": 5}, 2),
                     lambda: V.retain(["a", 1], {}, 2),
                     lambda: V.retain(["a"], None, 1),
                     lambda: V.gate("xy", lambda c: True),
                     lambda: V.replay_batch("ab", ["c"])):
            with self.assertRaises(ValueError):
                call()

    def test_huge_ints_are_finite_readings(self):
        self.assertEqual(V.next_strength(3, (10**400, 0), (10**401, 0)), 2)
        self.assertEqual(V.next_strength(3, (1, 0), (1, 10**309)), 2)
        self.assertEqual(V.next_strength(3, (10**401, 0), (10**400, 0)), 3)
        self.assertEqual(V.next_strength(3, (1.5, 0), (10**400, 0)), 2)

    def test_inf_readings_refused(self):
        for bad in (float("inf"), float("-inf")):
            with self.assertRaises(ValueError):
                V.next_strength(3, (bad, 0), (1, 0))
            with self.assertRaises(ValueError):
                V.next_strength(3, (1, 0), (1, bad))

    def test_retain_capacity_validation(self):
        for cap in (True, False, -1, 1.0, "1", None):
            with self.assertRaises(ValueError):
                V.retain(["a"], {"a": 1}, cap)
        self.assertEqual(V.retain(["a", "b"], {"a": 1}, 0), [])

    def test_crashing_check_drops_the_claim(self):
        self.assertEqual(V.gate([1, 2], lambda c: 1 / (c - 1) > 0), [2])

    def test_retain_ties_and_unrecorded_use(self):
        # "c" has 1 use; "a" and "b" have none recorded (0) and tie, broken by id.
        self.assertEqual(V.retain(["b", "a", "c"], {"c": 1}, 2), ["c", "a"])
        with self.assertRaises(ValueError):
            V.retain(["a"], {"a": -1}, 1)


if __name__ == "__main__":
    unittest.main()
