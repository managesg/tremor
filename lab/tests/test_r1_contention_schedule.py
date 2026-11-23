import copy
import hashlib
import json
from fractions import Fraction
import unittest

from lab import r1_contention_schedule as sched


def plan(roster, tasks):
    return {"rounds": len(roster), "roster": roster,
            "tasks": [{"id": i, "release": r, "complete": c} for i, r, c in tasks]}


# Round 1: 3 agents, x open (released 1, done 2) and y open (released 1, never done) -> 3/2.
# Round 2: 2 agents, x still open, y open, z released at 2 -> 2/3. Round 3: 2 agents, only y open (never done) -> 2.
TINY = plan([["a", "b", "c"], ["a", "b"], ["a", "b"]], [("x", 1, 2), ("y", 1, None), ("z", 2, 2), ("w", None, None)])


def rows(*pairs):
    return [{"round": i, "scheduled_agents": a, "scheduled_open_tasks": t, "kappa": Fraction(a, t) if t else None}
            for i, (a, t) in enumerate(pairs, start=1)]


class ScheduleTests(unittest.TestCase):
    def test_tiny_plan_by_hand(self):
        got = sched.schedule(TINY)
        self.assertEqual([(r["round"], r["scheduled_agents"], r["scheduled_open_tasks"], r["kappa"]) for r in got],
                         [(1, 3, 2, Fraction(3, 2)), (2, 2, 3, Fraction(2, 3)), (3, 2, 1, Fraction(2))])

    def test_undefined_round_has_no_kappa(self):
        got = sched.schedule(plan([["a"], ["a"]], [("x", 1, 1)]))
        self.assertEqual((got[1]["scheduled_open_tasks"], got[1]["kappa"]), (0, None))

    def test_satisfies_true(self):
        self.assertTrue(sched.satisfies(rows((3, 2), (4, 1), (5, 4), (2, 1))))

    def test_fewer_than_four_rounds_never_satisfies(self):
        # policy row 157: "four or more rounds"; the same counts over three rounds are not eligible
        self.assertFalse(sched.satisfies(rows((3, 2), (4, 1), (5, 4))))

    def test_round_one_failing_alone(self):
        self.assertFalse(sched.satisfies(rows((2, 2), (4, 1), (4, 1))))

    def test_equal_counts_fail_and_later_round_fails(self):
        self.assertFalse(sched.satisfies(rows((3, 2), (3, 3))))

    def test_undefined_round_is_excluded(self):
        self.assertTrue(sched.satisfies(rows((3, 2), (1, 0), (3, 2), (2, 1))))

    def test_no_eligible_round_is_not_eligible(self):
        self.assertFalse(sched.satisfies(rows((3, 0), (3, 0))))
        self.assertFalse(sched.satisfies([]))

    def test_satisfies_rejects_inconsistent_rows(self):
        bad = rows((3, 2))
        bad[0]["kappa"] = Fraction(1)
        with self.assertRaises(ValueError):
            sched.satisfies(bad)
        with self.assertRaises(ValueError):
            sched.satisfies([{"round": 1}])

    def test_malformed_plans_raise(self):
        def mutated(change):
            p = copy.deepcopy(TINY)
            change(p)
            return p
        for change in (
            lambda p: p.update(rounds=0),
            lambda p: p.update(rounds=True),
            lambda p: p.update(rounds=4),  # roster length differs
            lambda p: p["roster"].__setitem__(0, ["a", "a"]),
            lambda p: p["roster"].__setitem__(0, [""]),
            lambda p: p["tasks"][0].update(release=0),
            lambda p: p["tasks"][0].update(release=4),
            lambda p: p["tasks"][0].update(complete=0),  # before release
            lambda p: p["tasks"][3].update(complete=1),  # completes without release
            lambda p: p["tasks"][1].update(id="x"),
            lambda p: p["tasks"][0].update(release=1.0),
            lambda p: p.pop("tasks"),
            lambda p: p["tasks"][0].pop("complete"),
        ):
            with self.subTest(), self.assertRaises(ValueError):
                sched.schedule(mutated(change))
        with self.assertRaises(ValueError):
            sched.schedule([])

    def test_pin_is_canonical_and_deterministic(self):
        meta = {"generator_path": "lab/g.py", "generator_sha256": "ab" * 32, "seed": 17, "rule": "r1"}
        raw, digest = sched.pin(sched.schedule(TINY), meta)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), digest)
        self.assertEqual(sched.pin(sched.schedule(TINY), dict(meta)), (raw, digest))
        self.assertEqual(json.loads(raw)["rows"][0],
                         {"kappa": "3/2", "round": 1, "scheduled_agents": 3, "scheduled_open_tasks": 2})
        self.assertNotEqual(sched.pin(sched.schedule(TINY), meta | {"rule": "r2"})[1], digest)
        self.assertNotEqual(sched.pin(sched.schedule(TINY), meta | {"seed": 18})[1], digest)
        other = copy.deepcopy(TINY)
        other["tasks"][1]["complete"] = 1
        self.assertNotEqual(sched.pin(sched.schedule(other), meta)[1], digest)

    def test_pin_rejects_bad_meta(self):
        for meta in ({}, {"generator_path": "p", "generator_sha256": "s", "seed": "17", "rule": "r"},
                     {"generator_path": "p", "generator_sha256": "s", "seed": 1, "rule": ""}):
            with self.assertRaises(ValueError):
                sched.pin(sched.schedule(TINY), meta)


if __name__ == "__main__":
    unittest.main()
