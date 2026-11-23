import json
import unittest

from lab import r1_read_schedule as reads

A = ["a0", "a1", "a2", "a3"]
META = {"generator_path": "g.py", "generator_sha256": "ab" * 32, "seed": 17, "rule": "r"}


def plan(roster):
    return {"rounds": len(roster), "roster": roster, "tasks": []}


class StaggeredTests(unittest.TestCase):
    def test_alternating_lags_by_hand(self):
        # index i, round r >= 2: 1 + (i + r) % 2; round 1 all 1
        self.assertEqual(reads.lags(plan([A] * 4)), [
            dict(a0=1, a1=1, a2=1, a3=1), dict(a0=1, a1=2, a2=1, a3=2),
            dict(a0=2, a1=1, a2=2, a3=1), dict(a0=1, a1=2, a2=1, a3=2)])

    def test_generated_lags_are_staggered(self):
        self.assertTrue(reads.staggered(reads.lags(plan([A] * 4)), [A] * 4))

    def test_all_equal_lags_in_a_round_fail(self):
        rows = [dict(a0=1, a1=1), dict(a0=1, a1=2), dict(a0=2, a1=2)]
        self.assertFalse(reads.staggered(rows, [["a0", "a1"]] * 3))

    def test_round_one_is_exempt(self):
        rows = [dict(a0=1, a1=1), dict(a0=1, a1=2)]
        self.assertTrue(reads.staggered(rows, [["a0", "a1"]] * 2))

    def test_single_agent_round_is_exempt(self):
        rows = [dict(a0=1), dict(a0=1), dict(a0=2, a1=1)]
        self.assertTrue(reads.staggered(rows, [["a0"], ["a0"], ["a0", "a1"]]))

    def test_no_round_after_the_first_is_vacuously_true(self):
        self.assertTrue(reads.staggered([dict(a0=1, a1=1)], [["a0", "a1"]]))

    def test_malformed_input_raises(self):
        good = [dict(a0=1, a1=1), dict(a0=1, a1=2)]
        roster = [["a0", "a1"]] * 2
        for rows, ros in [
            ([dict(a0=0, a1=1), dict(a0=1, a1=2)], roster),   # lag below 1
            ([dict(a0=1, a1=2), dict(a0=1, a1=2)], roster),   # lag above the round (no earlier commit)
            ([dict(a0=1, a1=True), good[1]], roster),         # bool is not an int
            ([dict(a0=1), good[1]], roster),                  # agent missing
            (good[:1], roster),                               # round count differs
            ("x", roster), (good, None),
        ]:
            with self.assertRaises(ValueError):
                reads.staggered(rows, ros)
        for bad in (None, {"rounds": 4}, plan([A, A, A])):
            with self.assertRaises(ValueError):
                reads.lags(bad if bad != plan([A, A, A]) else dict(plan([A] * 3), rounds=4))

    def test_pin_is_deterministic_and_changes_with_rule_or_lags(self):
        rows = reads.lags(plan([A] * 4))
        raw, digest = reads.pin(rows, META)
        self.assertEqual(reads.pin(rows, META), (raw, digest))
        self.assertEqual(json.loads(raw)["rows"][1], {"round": 2, "lags": dict(a0=1, a1=2, a2=1, a3=2)})
        self.assertNotEqual(reads.pin(rows, META | {"rule": "other"})[1], digest)
        self.assertNotEqual(reads.pin(rows, META | {"seed": 18})[1], digest)
        changed = [dict(row) for row in rows]
        changed[2]["a0"] = 1
        self.assertNotEqual(reads.pin(changed, META)[1], digest)

    def test_pin_rejects_bad_meta_and_rows(self):
        rows = reads.lags(plan([A] * 4))
        for meta in (None, {}, META | {"seed": "17"}, META | {"rule": ""}, {k: v for k, v in META.items() if k != "seed"}):
            with self.assertRaises(ValueError):
                reads.pin(rows, meta)
        with self.assertRaises(ValueError):
            reads.pin([dict(a0=0)], META)


if __name__ == "__main__":
    unittest.main()
