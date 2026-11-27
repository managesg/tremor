"""WORKPLAN-RESIDENCY-V3 row 159: the nine susceptibility readouts in one module, ports equal to lab originals."""
import unittest

from tremor import readouts as R
from tremor import susceptibility as S
from lab import r1_kish_spread as lab_kish
from lab import r1_response_fluctuation as lab_fluct

NAMES = ("rerun_variance", "dose_slope", "response_fluctuation_ratio", "adoption", "cascade_depth",
         "reproduction_number", "recovery_time", "pairwise_miss", "kish_spread_check")


def _notes(edges):
    """edges: {id: [parents]}"""
    return [{"id": i, "parents": p} for i, p in edges.items()]


class Exports(unittest.TestCase):
    def test_all_nine_callable_and_reexports_are_the_originals(self):
        for n in NAMES:
            self.assertTrue(callable(getattr(S, n)), n)
            self.assertIn(n, S.__all__)
        for n in ("rerun_variance", "dose_slope", "reproduction_number", "recovery_time", "pairwise_miss"):
            self.assertIs(getattr(S, n), getattr(R, n))


class Cascade(unittest.TestCase):
    # tree: A -> B, A -> C, B -> D, E (second root, no kids), X unrelated
    TREE = _notes({"A": [], "B": ["A"], "C": ["A"], "D": ["B"], "E": [], "X": []})

    def test_tree(self):
        # planted {A}: adopters A,B,C,D = 4; deepest D is 2 generations from A.
        self.assertEqual(S.adoption(self.TREE, ["A"]), 4)
        self.assertEqual(S.cascade_depth(self.TREE, ["A"]), 2)
        # planted {A,E}: adopters A,B,C,D,E = 5; depth still 2.
        self.assertEqual(S.adoption(self.TREE, ["A", "E"]), 5)
        self.assertEqual(S.cascade_depth(self.TREE, ["A", "E"]), 2)
        # planted {B}: B,D = 2, depth 1. Roots only {E}: 1 adopter, depth 0.
        self.assertEqual((S.adoption(self.TREE, ["B"]), S.cascade_depth(self.TREE, ["B"])), (2, 1))
        self.assertEqual((S.adoption(self.TREE, ["E"]), S.cascade_depth(self.TREE, ["E"])), (1, 0))

    def test_multi_parent_uses_shortest_path(self):
        # A -> B -> C and A -> C directly: C is 1 generation away.
        notes = _notes({"A": [], "B": ["A"], "C": ["A", "B"]})
        self.assertEqual((S.adoption(notes, ["A"]), S.cascade_depth(notes, ["A"])), (3, 1))

    def test_cycle_terminates(self):
        # A -> B -> C -> B (cycle): adopters 3, depth 2.
        notes = _notes({"A": [], "B": ["A", "C"], "C": ["B"]})
        self.assertEqual((S.adoption(notes, ["A"]), S.cascade_depth(notes, ["A"])), (3, 2))
        # pure cycle with planted member: B -> C -> B; planted B: adopters 2, depth 1.
        notes = _notes({"B": ["C"], "C": ["B"]})
        self.assertEqual((S.adoption(notes, ["B"]), S.cascade_depth(notes, ["B"])), (2, 1))

    def test_empty_planted(self):
        self.assertEqual(S.adoption(self.TREE, []), 0)
        self.assertIsNone(S.cascade_depth(self.TREE, []))


class FluctuationPort(unittest.TestCase):
    CASES = [
        (list(enumerate(((0, 0, 1, 1, 1), (0, 1, 1, 1, 2), (1, 1, 1, 2, 2)))), 2, 1),   # ordinary
        (list(enumerate(((0, 0, 1, 1, 1), (1,) * 5, (1, 1, 1, 2, 2)))), 2, 1),          # zero observed variance
        (list(enumerate(((0,) * 5,) * 3)), 2, 1),                                       # zero binomial variance
        ([(0, (0, 1)), (1, (1,)), (2, (2,))], 2, 1),                                    # single rerun: variance None
    ]

    def test_identical_to_lab(self):
        for groups, team, ref in self.CASES:
            self.assertEqual(S.response_fluctuation_ratio(groups, team_size=team, reference_dose=ref),
                             lab_fluct.measure(groups, team_size=team, reference_dose=ref))

    def test_degenerate_values_are_none(self):
        r = S.response_fluctuation_ratio(self.CASES[1][0], team_size=2, reference_dose=1)
        self.assertIsNone(r["candidate_slope_per_sample_count_variance"])
        r = S.response_fluctuation_ratio(self.CASES[2][0], team_size=2, reference_dose=1)
        self.assertIsNone(r["reference_overdispersion"])
        r = S.response_fluctuation_ratio(self.CASES[3][0], team_size=2, reference_dose=1)
        self.assertIsNone(r["reference_sample_count_variance"])

    def test_same_validation_errors(self):
        bad = [
            (dict(dose_counts=[(0, (1,)), (1, (1,))], team_size=2, reference_dose=1)),   # <3 doses
            (dict(dose_counts=list(enumerate(((1,),) * 3)), team_size=0, reference_dose=1)),
            (dict(dose_counts=list(enumerate(((1,),) * 3)), team_size=2, reference_dose=9)),
            (dict(dose_counts=list(enumerate(((3,),) * 3)), team_size=2, reference_dose=1)),
            (dict(dose_counts=[(0, (1,)), (0, (1,)), (1, (1,))], team_size=2, reference_dose=1)),
            (dict(dose_counts=[(0.5, (1,)), (1, (1,)), (2, (1,))], team_size=2, reference_dose=1)),
        ]
        for kw in bad:
            with self.assertRaises(ValueError):
                S.response_fluctuation_ratio(**kw)

    def test_hand_value(self):
        r = S.response_fluctuation_ratio(self.CASES[0][0], team_size=2, reference_dose=1)
        # means 3/5, 1, 7/5 at doses 0, 1, 2; mean of means 1; slope = ((-1)(-2/5) + 0 + (1)(2/5)) / 2 = 2/5
        self.assertEqual(str(r["count_scale_slope"]), "2/5")
        # reference counts (0,1,1,1,2): mean 1, sample var = 2/4 = 1/2; binomial 2*(1/2)*(1/2) = 1/2; ratio 1
        self.assertEqual(str(r["reference_overdispersion"]), "1")


class KishPort(unittest.TestCase):
    CASES = [
        [[1, 0, 0, 1], [1, 1, 0, 0], [0, 1, 1, 0]],     # all pairs defined
        [[1, 1, 1], [1, 1, 1], [0, 0, 0]],              # no defined pair
        [[1, 0, 0], [0, 1, 0], [0, 0, 1]],              # denominator near zero
        [[1, 0], [0, 1]],                               # anticorrelated
        [[1, 0, 1], [1, 1, 1], [0, 1, 0]],              # constant monitor: partial pairs
        [[1, 0]],                                       # single monitor
    ]

    def test_identical_to_lab(self):
        for misses in self.CASES:
            self.assertEqual(S.kish_spread_check(misses), lab_kish.diagnose(misses))

    def test_degenerate_none(self):
        self.assertIsNone(S.kish_spread_check(self.CASES[1])["kish_effective_size"])
        self.assertIsNone(S.kish_spread_check(self.CASES[2])["kish_effective_size"])
        self.assertIsNone(S.kish_spread_check(self.CASES[4])["kish_denominator"])  # 1 of 3 pairs observed

    def test_hand_value(self):
        # two identical varying monitors: phi = 1, denominator (2+2)/2 = 2, n_eff = 1.
        r = S.kish_spread_check([[1, 0], [1, 0]])
        self.assertEqual((r["observed_mean_phi"], r["kish_effective_size"]), (1.0, 1.0))

    def test_same_validation_errors(self):
        for bad in ([], [[]], [[1, 0], [1]], [[2, 0]], "x", [[1, 0.5]]):
            with self.assertRaises(ValueError):
                lab_kish.diagnose(bad)
            with self.assertRaises(ValueError):
                S.kish_spread_check(bad)


if __name__ == "__main__":
    unittest.main()
