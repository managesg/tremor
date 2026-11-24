import json
import os
import subprocess
import sys
import random
import unittest

from murmuration import monsel
from lab import l3c_harness as h

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Hand-built pool: 2 tasks x 3 candidates, views a b c (1 = missed).
TINY = [
    [{"a": 0, "b": 0, "c": 0}, {"a": 1, "b": 0, "c": 1}, {"a": 1, "b": 1, "c": 1}],
    [{"a": 0, "b": 0, "c": 1}, {"a": 1, "b": 1, "c": 1}, {"a": 0, "b": 1, "c": 0}],
]
CAL = {"a": [0, 1], "b": [1, 0], "c": [1, 1]}


def toy_pool(seed, tasks, cands, views):
    rng = random.Random(seed)
    return [[{v: int(rng.random() < 0.5) for v in views} for _ in range(cands)] for _ in range(tasks)]


def fixture():
    views = ["a", "b", "c", "d", "e"]
    pool = toy_pool(7, 40, 8, views)
    cal = {v: [int(x) for x in random.Random(i).choices([0, 1], k=30)] for i, v in enumerate(views)}
    return h.compare_arms(pool, cal, 4, 8, 11)


class Harness(unittest.TestCase):
    def test_best_of_n_hand_computed(self):
        c = [0, 1, 2]
        self.assertEqual(h.best_of_n(c, TINY[0], ["a", "b", "c"], 3), 2)  # 0, 2, 3 misses
        self.assertEqual(h.best_of_n(c, TINY[0], ["a", "c"], 3), 1)       # 0, 2, 2: first max wins
        self.assertEqual(h.best_of_n(c, TINY[0], ["a", "c"], 1), 0)       # only first n looked at
        self.assertEqual(h.best_of_n(c, TINY[1], ["b", "c"], 3), 1)       # 1, 2, 1

    def test_conservative_catch(self):
        m = {"a": [0, 1, 1], "b": [1, 1, 0]}
        self.assertEqual(h.conservative_catch(m, ["a", "b"]), [1, 0, 1])
        self.assertEqual(h.conservative_catch(m, ["a"]), [1, 0, 0])
        self.assertAlmostEqual(sum(h.conservative_catch(m, ["a", "b"])) / 3, monsel.ensemble_catch(m, ["a", "b"]))

    def test_pressure_loss(self):
        self.assertAlmostEqual(h.pressure_loss(0.8, 0.4), 0.4)
        self.assertEqual(h.pressure_loss(0.5, 0.5), 0.0)
        self.assertAlmostEqual(h.pressure_loss(0.5, 0.75), -0.25)

    def test_rotation_excludes_exactly_hidden_view(self):
        sel = ["a", "b", "c"]
        self.assertEqual(monsel.hidden_view(sel, 0), "b")
        self.assertEqual(h.visible_views(sel, True, 0), ["a", "c"])
        self.assertEqual(h.visible_views(sel, True, 1), ["b", "c"])  # hidden "a"
        self.assertEqual(h.visible_views(sel, False, 0), sel)
        for s in range(20):
            hid = monsel.hidden_view(sel, s)
            self.assertEqual(sorted(h.visible_views(sel, True, s) + [hid]), sel)

    def test_arms_hand_computed(self):
        r = h.compare_arms(TINY, CAL, 3, 3, 0)
        self.assertEqual(r["selected"], ["a", "b", "c"])  # a ties b at 1/2, name order; then b adds 1/2; then c
        # before: 6 episodes, all-missed T0c2 and T1c1 -> 4/6. static and conservative end at 0 catch -> loss 2/3.
        # rotating: seeds 0,1 hide b then a; picks T0c1 (caught by b), T1c1 (missed) -> 1/2; loss 2/3 - 1/2 = 1/6.
        self.assertAlmostEqual(r["before"], 2 / 3)
        self.assertAlmostEqual(r["static"], 2 / 3)
        self.assertAlmostEqual(r["rotating"], 1 / 6)
        self.assertAlmostEqual(r["conservative"], 2 / 3)

    def test_greedy_not_top_k(self):
        # a and b catch the same two episodes; c catches a third. Top-2 by single catch is a, b;
        # greedy (monsel.select) takes a then c.
        cal = {"a": [0, 0, 1, 1], "b": [0, 0, 1, 1], "c": [1, 1, 0, 1]}
        pool = [[{"a": 1, "b": 1, "c": 1}, {"a": 0, "b": 0, "c": 0}]]
        self.assertEqual(h.compare_arms(pool, cal, 2, 2, 0)["selected"], ["a", "c"])

    def test_rotation_seed_is_per_task(self):
        # Two views; candidate 0 is missed only by a, candidate 1 only by b. Hiding a makes the selector
        # pick candidate 1, hiding b makes it pick candidate 0. Seeds s and s+1 must hide different views.
        sel = ["a", "b"]
        s = next(x for x in range(100) if monsel.hidden_view(sel, x) != monsel.hidden_view(sel, x + 1))
        task = [{"a": 1, "b": 0}, {"a": 0, "b": 1}]
        picks = []
        for t in range(2):
            seen = h.visible_views(sel, True, s + t)
            picks.append(h.best_of_n([0, 1], task, seen, 2))
        self.assertNotEqual(picks[0], picks[1])
        # compare_arms must use seed + task index. Three views; c0 is missed by a and b (caught by c),
        # c1 is missed by all. Hiding c ties c0 with c1 (first wins: c0, caught); hiding another view
        # makes c1 strictly best (uncaught). Pick s with hidden(s) == c and hidden(s + 1) != c.
        sel3 = ["a", "b", "c"]
        s3 = next(x for x in range(200)
                  if monsel.hidden_view(sel3, x) == "c" and monsel.hidden_view(sel3, x + 1) != "c")
        task3 = [{"a": 1, "b": 1, "c": 0}, {"a": 1, "b": 1, "c": 1}]
        cal3 = {"a": [0, 1, 1], "b": [1, 0, 1], "c": [1, 1, 0]}
        r = h.compare_arms([task3, task3], cal3, 3, 2, s3)
        self.assertEqual(r["selected"], sel3)
        # before 1/2; rotating: task 0 caught, task 1 not -> 1/2, loss 0. A constant seed would give -1/2.
        self.assertAlmostEqual(r["before"], 0.5)
        self.assertAlmostEqual(r["rotating"], 0.0)

    def test_loss_ratio(self):
        self.assertAlmostEqual(h.loss_ratio(0.1, 0.4), 0.25)
        for bad in ((0.1, 0), (0.1, -0.2), (True, 0.4), (0.1, "x")):
            with self.assertRaises(ValueError):
                h.loss_ratio(*bad)

    def test_views_checked_without_rotation(self):
        for bad in ({"a", "b"}, ["a", "a"], ["a", 1], []):
            with self.assertRaises(ValueError):
                h.visible_views(bad, False, 0)

    def test_determinism_across_hash_seeds(self):
        outs = set()
        for hs in ("0", "1", "12345", "random"):
            env = dict(os.environ, PYTHONHASHSEED=hs)
            env["PYTHONPATH"] = os.pathsep.join(
                [os.path.join(REPO, "src"), os.path.join(REPO, "lab"), os.path.join(REPO, "tests"), REPO])
            p = subprocess.run(
                [sys.executable, "-B", "-c",
                 "import json; from lab.tests import test_l3c_harness as t; print(json.dumps(t.fixture(), sort_keys=True))"],
                cwd=REPO, env=env, capture_output=True, text=True, check=True)
            outs.add(p.stdout)
        self.assertEqual(len(outs), 1)
        self.assertEqual(json.loads(outs.pop()), fixture())

    def test_malformed_input(self):
        c = [0, 1, 2]
        bad = [
            lambda: h.best_of_n("abc", TINY[0], ["a"], 1),
            lambda: h.best_of_n(c, TINY[0][:2], ["a"], 1),
            lambda: h.best_of_n(c, TINY[0], ["a"], 0),
            lambda: h.best_of_n(c, TINY[0], ["a"], 4),
            lambda: h.best_of_n(c, TINY[0], True, 1),
            lambda: h.best_of_n(c, TINY[0], [], 1),
            lambda: h.best_of_n(c, TINY[0], ["z"], 1),
            lambda: h.best_of_n(c, [{"a": 2}] * 3, ["a"], 1),
            lambda: h.conservative_catch({}, ["a"]),
            lambda: h.conservative_catch({"a": [0, 1], "b": [0]}, ["a"]),
            lambda: h.conservative_catch({"a": [0]}, ["b"]),
            lambda: h.pressure_loss(1.5, 0.5),
            lambda: h.pressure_loss(0.5, "x"),
            lambda: h.visible_views(["a"], True, 0),
            lambda: h.visible_views(["a", "b"], True, None),
            lambda: h.visible_views(["a", "b"], 1, 0),
            lambda: h.compare_arms([], CAL, 3, 3, 0),
            lambda: h.compare_arms(TINY, CAL, 4, 3, 0),
            lambda: h.compare_arms(TINY, CAL, 3, 4, 0),
            lambda: h.compare_arms(TINY, CAL, 3, 3, "0"),
        ]
        for i, f in enumerate(bad):
            with self.subTest(case=i), self.assertRaises(ValueError):
                f()


if __name__ == "__main__":
    unittest.main()
