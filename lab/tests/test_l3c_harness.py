import json
import os
import subprocess
import sys
import random
import unittest

from tremor import monsel
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
    return h.compare_arms(pool, cal, 4, 8, 11, monsel.select(cal, 4)[0])


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
        r = h.compare_arms(TINY, CAL, 3, 3, 16, "a")  # seed 16 hides b for task 0 and a for task 1
        self.assertEqual(r["selected"], ["a", "b", "c"])  # a ties b at 1/2, name order; then b adds 1/2; then c
        # designated view a. before: 6 episodes, all-missed T0c2 and T1c1 -> 4/6.
        # static: pressured picks T0c1 (a misses; b catches), T1c1 (all miss) -> catch 1/2, loss 1/6.
        # rotating: task_seed("rotate", 16, t) hides b then a. T0: a visible -> T0c1 (caught). T1: a hidden -> candidate 0
        # T1c0 (caught by a, b) -> catch 1, loss -1/3. conservative: T0c2, T1c1 (flag-free) -> catch 0, loss 2/3.
        self.assertAlmostEqual(r["before"], 2 / 3)
        self.assertAlmostEqual(r["static"], 1 / 6)
        self.assertAlmostEqual(r["rotating"], -1 / 3)
        self.assertAlmostEqual(r["conservative"], 2 / 3)

    def test_greedy_not_top_k(self):
        # a and b catch the same two episodes; c catches a third. Top-2 by single catch is a, b;
        # greedy (monsel.select) takes a then c.
        cal = {"a": [0, 0, 1, 1], "b": [0, 0, 1, 1], "c": [1, 1, 0, 1]}
        pool = [[{"a": 1, "b": 1, "c": 1}, {"a": 0, "b": 0, "c": 0}]]
        self.assertEqual(h.compare_arms(pool, cal, 2, 2, 0, "a")["selected"], ["a", "c"])
        with self.assertRaises(ValueError):  # b is in the rows but not selected
            h.compare_arms(pool, cal, 2, 2, 0, "b")

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
        # compare_arms must use task_seed("rotate", seed, task index). Three views; c0 is missed by a and b (caught by c),
        # c1 is missed by all. Hiding c ties c0 with c1 (first wins: c0, caught); hiding another view
        # makes c1 strictly best (uncaught). Pick s with hidden(s) == c and hidden(s + 1) != c.
        sel3 = ["a", "b", "c"]
        hid = lambda x, t: monsel.hidden_view(sel3, h.task_seed("rotate", x, t))
        s3 = next(x for x in range(200) if hid(x, 0) == "c" and hid(x, 1) != "c")
        task3 = [{"a": 1, "b": 1, "c": 0}, {"a": 1, "b": 1, "c": 1}]
        cal3 = {"a": [0, 1, 1], "b": [1, 0, 1], "c": [1, 1, 0]}
        r = h.compare_arms([task3, task3], cal3, 3, 2, s3, "c")
        self.assertEqual(r["selected"], sel3)
        # designated c. Task 0 hides c -> candidate 0 (caught); task 1 sees c -> c1 (all miss, uncaught): catch 1/2,
        # before 1/2, loss 0. A constant seed would give -1/2 (always hidden) or 1/2 (never hidden).
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
            lambda: h.compare_arms([], CAL, 3, 3, 0, "a"),
            lambda: h.compare_arms(TINY, CAL, 4, 3, 0, "a"),
            lambda: h.compare_arms(TINY, CAL, 3, 4, 0, "a"),
            lambda: h.compare_arms(TINY, CAL, 3, 3, "0", "a"),
            lambda: h.compare_arms(TINY, CAL, 3, 3, 0, "zz"),  # not a selected view
            lambda: h.null_loss_ratio(0.5, 0.2, 3, 4, 5, 3, 0, "v9"),
        ]
        bad += [
            lambda: h.compare_arms(TINY, CAL, 1, 3, 0, "a"),  # k < 2
            lambda: h.null_loss_ratio(0.5, 0.2, 1, 4, 5, 3, 0, "v0"),
            lambda: h.null_loss_ratio(1.5, 0.2, 3, 4, 5, 3, 0, "v0"),
            lambda: h.null_loss_ratio(0.5, 0.2, 3, 4, 5, 0, 0, "v0"),
            lambda: h.bootstrap_ratio([], 10, 0, 0.5, 0.9),
            lambda: h.bootstrap_ratio([{"rotating": 0.1, "static": 0.2}], 10, 0, 1.5, 0.9),
            lambda: h.bootstrap_ratio([{"rotating": 0.1, "static": 0.2}], 10, 0, 0.5, 1),
            lambda: h.bootstrap_ratio([{"rotating": 0.1}], 10, 0, 0.5, 0.9),
            lambda: h.supported_against_null(True, 0.5, 0.5),
            lambda: h.task_seed("", 0, 0),
            lambda: h.task_seed("t", 0, -1),
            lambda: h.rotation_beats_conservative({}),
        ]
        for i, f in enumerate(bad):
            with self.subTest(case=i), self.assertRaises(ValueError):
                f()

    def test_task_seed_sha256(self):
        import hashlib
        want = int.from_bytes(hashlib.sha256(b"rotate:5:3").digest()[:8], "big") >> 1
        self.assertEqual(h.task_seed("rotate", 5, 3), want)
        self.assertNotEqual(h.task_seed("rotate", 5, 3), h.task_seed("rotate", 5, 4))
        self.assertNotEqual(h.task_seed("rotate", 5, 3), h.task_seed("boot", 5, 3))
        # adjacent base seeds must not share task seeds (seed + t gave (0,1) == (1,0))
        a = {h.task_seed("rotate", 0, t) for t in range(50)}
        b = {h.task_seed("rotate", 1, t) for t in range(50)}
        self.assertFalse(a & b)

    def test_k_below_two_rejected(self):
        for k in (0, 1, True):
            with self.assertRaises(ValueError):
                h.compare_arms(TINY, CAL, k, 3, 0, "a")

    def test_conservative_is_vacuous(self):
        self.assertIs(h.conservative_is_distinct(), False)
        r = h.compare_arms(TINY, CAL, 3, 3, 4, "a")
        self.assertEqual(h.rotation_beats_conservative(r), "vacuous")
        self.assertEqual(h.rotation_beats_conservative({"rotating": 0.0, "conservative": 0.5}), "vacuous")
        # under single-view pressure the scripted arm no longer equals the fixed arm; it stays unregistered
        self.assertNotEqual(r["conservative"], r["static"])
        self.assertIn("vacuous", h.rotation_beats_conservative.__doc__)
        self.assertIn("P:453-454", h.conservative_is_distinct.__doc__)

    def test_supported_against_null(self):
        self.assertTrue(h.supported_against_null(0.4, 0.6, 0.5))
        self.assertTrue(h.supported_against_null(0.5, 0.6, 0.5))   # bound is inclusive
        self.assertFalse(h.supported_against_null(0.55, 0.9, 0.5))  # above bound
        self.assertFalse(h.supported_against_null(0.4, 0.4, 0.5))   # not strictly below the null
        self.assertFalse(h.supported_against_null(0.4, 0.3, 0.5))
        self.assertFalse(h.supported_against_null(0.5, 0.5, 0.5))

    def test_null_loss_ratio(self):
        args = (0.5, 0.2, 3, 6, 20, 30, 9, "v0")
        r = h.null_loss_ratio(*args)
        self.assertEqual(r, h.null_loss_ratio(*args))              # deterministic
        self.assertNotEqual(r, h.null_loss_ratio(*args[:-2], 10, "v0"))  # seed matters
        self.assertGreater(r, 0)
        self.assertLess(r, 1)  # no model effect, yet rotation loses less: the pressured null is below 1
        # c = 1: every candidate missed by every view, so no fixed loss: refuses rather than dividing
        with self.assertRaises(ValueError):
            h.null_loss_ratio(0.5, 1, 3, 6, 20, 5, 0, "v0")
        with self.assertRaises(TypeError):
            h.null_loss_ratio(0.5, 0.2, 3, 6, 20, 30, 9)  # no default for the designated view

    def test_null_draw_matches_correlated_monitors(self):
        # the draw model is nulls.correlated_monitors': P(all miss) = c + (1 - c) p^m
        from fractions import Fraction
        from tremor import nulls
        want = float(nulls.correlated_monitors(3, Fraction(2, 5), Fraction(1, 4))["all_miss"])
        seen = []
        orig = h.compare_arms
        h.compare_arms = lambda pool, cal, k, n, s, d: (seen.extend(c for t in pool for c in t), orig(pool, cal, k, n, s, d))[1]
        try:
            h.null_loss_ratio(0.4, 0.25, 3, 8, 200, 3, 1, "v0")
        except ValueError:
            pass
        finally:
            h.compare_arms = orig
        got = sum(all(c.values()) for c in seen) / len(seen)
        self.assertAlmostEqual(got, want, delta=0.03)

    def test_bootstrap_ratio(self):
        pools = [{"rotating": 0.1, "static": 0.4}, {"rotating": 0.2, "static": 0.4}]
        r = h.bootstrap_ratio(pools, 200, 3, 0.0, 0.9)
        self.assertEqual((r["excluded"], r["kept"]), (0, 200))
        lo, hi = r["interval"]
        self.assertAlmostEqual(lo, 0.25)   # both pools drawn: ratios 0.25, 0.375, 0.5
        self.assertAlmostEqual(hi, 0.5)
        self.assertEqual(r, h.bootstrap_ratio(pools, 200, 3, 0.0, 0.9))
        # a pool with zero fixed loss: resamples drawing only it are excluded, not raised on
        mixed = [{"rotating": 0.0, "static": 0.0}, {"rotating": 0.1, "static": 0.4}]
        m = h.bootstrap_ratio(mixed, 400, 1, 0.5, 0.9)
        self.assertGreater(m["excluded"], 0)
        self.assertEqual(m["excluded"] + m["kept"], 400)
        self.assertLess(m["excluded"] / 400, 0.5)
        # excluded share above the caller's cap: None
        self.assertIsNone(h.bootstrap_ratio(mixed, 400, 1, 0.01, 0.9))
        # nothing kept: None even with cap 1
        self.assertIsNone(h.bootstrap_ratio([{"rotating": 0.0, "static": 0.0}], 20, 1, 1.0, 0.9))
        with self.assertRaises(TypeError):
            h.bootstrap_ratio(pools, 10, 0)  # cap and level have no defaults

    def test_static_arm_uses_pressured_selection(self):
        views = ["a", "b", "c", "d"]
        for sd in range(10):
            pool = toy_pool(sd, 15, 5, views)
            cal = {v: [int(x) for x in random.Random(sd + i).choices([0, 1], k=20)] for i, v in enumerate(views)}
            d = monsel.select(cal, 3)[0]
            r = h.compare_arms(pool, cal, 3, 5, sd, d)
            picks = h.pressured_selection(pool, d, 5)
            got = monsel.ensemble_catch({v: [p[v] for p in picks] for v in r["selected"]}, r["selected"])
            self.assertAlmostEqual(r["static"], r["before"] - got)

    def test_rotating_arm_designated_hidden_takes_candidate_zero(self):
        sel = ["a", "b"]
        cal = {"a": [0, 1], "b": [1, 0]}
        pool = [[{"a": 0, "b": 0}, {"a": 1, "b": 1}]]  # c0 caught, c1 missed by both; before 1/2
        hid = lambda x: monsel.hidden_view(sel, h.task_seed("rotate", x, 0))
        s_hid = next(x for x in range(100) if hid(x) == "a")
        s_vis = next(x for x in range(100) if hid(x) == "b")
        r = h.compare_arms(pool, cal, 2, 2, s_hid, "a")
        self.assertEqual(r["selected"], sel)
        self.assertAlmostEqual(r["rotating"], -0.5)  # nothing to aim at: candidate 0, caught
        self.assertAlmostEqual(r["static"], 0.5)     # pressured pick is c1, missed
        self.assertAlmostEqual(h.compare_arms(pool, cal, 2, 2, s_vis, "a")["rotating"], 0.5)  # visible: pressured pick
        with self.assertRaises(TypeError):
            h.compare_arms(pool, cal, 2, 2, s_hid)

    def test_null_passes_designated_view(self):
        seen = []
        orig = h.compare_arms
        h.compare_arms = lambda pool, cal, k, n, s, d: (seen.append(d), orig(pool, cal, k, n, s, d))[1]
        try:
            h.null_loss_ratio(0.5, 0.2, 3, 6, 20, 3, 9, "v1")
        finally:
            h.compare_arms = orig
        self.assertEqual(seen, ["v1"] * 3)

    # Pressure form (L3-O3): selection against one designated view. Rows are (P, h1, h2); P is the pressured view.
    PRESSURE = [
        [(0, 1, 1), (1, 0, 0), (0, 0, 0), (0, 1, 1)],
        [(0, 0, 0), (0, 1, 0), (1, 0, 1), (1, 1, 1)],
        [(1, 0, 0), (1, 1, 0), (0, 0, 0), (0, 1, 1)],
        [(0, 0, 0), (0, 1, 0), (0, 0, 1), (0, 1, 1)],
    ]

    @staticmethod
    def _pool(extra=False):
        # extra: add view h3 = a copy of P, so a hidden view that falls as far as P exists
        return [[dict(zip(["P", "h1", "h2"] + (["h3"] if extra else []), r + ((r[0],) if extra else ())))
                 for r in t] for t in Harness.PRESSURE]

    def test_pressured_selection_hand_computed(self):
        pool = self._pool()
        picks = h.pressured_selection(pool, "P", 4)
        self.assertEqual(picks, [pool[0][1], pool[1][2], pool[2][0], pool[3][0]])  # P missed; none -> candidate 0
        # not the old summed-miss rule over all views, which picks T0c0, T1c3 here
        old = [t[h.best_of_n(list(range(4)), t, ["P", "h1", "h2"], 4)] for t in pool]
        self.assertNotEqual(picks, old)
        self.assertEqual(old[0], pool[0][0])
        # only the first n candidates are looked at
        self.assertEqual(h.pressured_selection(pool, "P", 2), [pool[0][1], pool[1][0], pool[2][0], pool[3][0]])
        with self.assertRaises(TypeError):
            h.pressured_selection(pool, "P")
        for bad in ("", None, 3):
            with self.assertRaises(ValueError):
                h.pressured_selection(pool, bad, 4)
        with self.assertRaises(ValueError):
            h.pressured_selection(pool, "nope", 4)
        with self.assertRaises(ValueError):
            h.pressured_selection(pool, "P", 5)

    def test_manipulation_check_hand_computed(self):
        pool = self._pool()
        r = h.manipulation_check(pool, "P", ["h1", "h2"], 4, 0.4375, 0.1)
        # P miss rate: pool 5/16, picks 3/4 -> catch falls 7/16; h1 8/16 -> 0, h2 7/16 -> 1/4
        self.assertEqual(r["designated_fall"], 0.4375)
        self.assertEqual(r["hidden_falls"], {"h1": -0.5, "h2": -0.1875})
        self.assertTrue(r["passed"])  # fall exactly at min_fall passes
        self.assertFalse(h.manipulation_check(pool, "P", ["h1"], 4, 0.4376, 0.1)["passed"])
        # n=2: picks miss rate 1/2, pool (first two candidates) 3/8
        self.assertEqual(h.manipulation_check(pool, "P", ["h1"], 2, 0.125, 0.1)["designated_fall"], 0.125)

    def test_manipulation_check_hidden_view_clause(self):
        pool = self._pool(extra=True)  # h3 copies P, so it falls by 7/16 too
        r = h.manipulation_check(pool, "P", ["h3"], 4, 0.4375, 0.4375)
        self.assertEqual(r["hidden_falls"], {"h3": 0.4375})
        self.assertTrue(r["passed"])  # hidden fall exactly at the limit passes
        self.assertFalse(h.manipulation_check(pool, "P", ["h3"], 4, 0.4375, 0.4)["passed"])
        # one bad hidden view fails the check even when another is fine
        self.assertFalse(h.manipulation_check(pool, "P", ["h2", "h3"], 4, 0.4375, 0.4)["passed"])

    def test_manipulation_check_validation(self):
        pool = self._pool()
        with self.assertRaises(TypeError):
            h.manipulation_check(pool, "P", ["h1"], 4, 0.3)  # no default for the hidden-view limit
        for args in ((pool, "P", [], 4, 0.3, 0.1), (pool, "P", "h1", 4, 0.3, 0.1),
                     (pool, "P", ["P"], 4, 0.3, 0.1), (pool, "P", ["zz"], 4, 0.3, 0.1),
                     (pool, "P", ["h1"], 4, 1.5, 0.1), (pool, "P", ["h1"], 4, 0.3, -0.1)):
            with self.assertRaises(ValueError):
                h.manipulation_check(*args)
        bad = [[dict(c) for c in t] for t in pool]
        bad[1][2]["h1"] = 2
        with self.assertRaises(ValueError):
            h.manipulation_check(bad, "P", ["h1"], 4, 0.3, 0.1)

    def test_designated_view_for(self):
        self.assertEqual(h.designated_view_for(["c", "a", "b"]), "a")
        self.assertEqual(h.designated_view_for(("z", "B", "a")), "B")  # byte order: upper before lower
        self.assertEqual(h.designated_view_for(["x"]), "x")
        self.assertEqual(h.designated_view_for(["b", "a"]), h.designated_view_for(["a", "b"]))
        for bad in ([], "abc", ["a", "a"], ["a", ""], ["a", 1], None, {"a", "b"}):
            with self.assertRaises(ValueError):
                h.designated_view_for(bad)


if __name__ == "__main__":
    unittest.main()
