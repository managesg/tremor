from fractions import Fraction
from math import factorial
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lab import r1_l5_random_order_null as fixture
from murmuration.board import Board, read_log


class R1L5RandomOrderNullTests(unittest.TestCase):
    @staticmethod
    def counts(arm):
        return {(row["distinct_first_choices"], row["duplicate_first_choices"], row["colliding_tasks"]): row["profiles"]
                for row in arm["histogram"]}

    def test_uniform_independent_ranking_matches_exact_occupancy_arithmetic(self):
        report = fixture.compare()
        self.assertIs(report["scientific_result"], False)
        self.assertEqual(report["scope"], "scripted_first_simultaneous_choice")
        self.assertEqual(report["rankings_by_first_task_per_worker"], {task: factorial(3) for task in fixture.TASKS})
        random = report["arms"]["independent_random_order"]
        self.assertEqual(random["first_choice_profiles"], 4**4)
        self.assertEqual(self.counts(random), {
            (1, 3, 1): 4, (2, 2, 1): 48, (2, 2, 2): 36, (3, 1, 1): 144, (4, 0, 0): 24,
        })

        p_empty = Fraction(3, 4)**4
        p_one = 4 * Fraction(1, 4) * Fraction(3, 4)**3
        expected = {"distinct_first_choices": 4 * (1 - p_empty), "duplicate_first_choices": 4 * p_empty,
                    "colliding_tasks": 4 * (1 - p_empty - p_one)}
        for metric, count in expected.items():
            with self.subTest(metric=metric):
                exact = random["expected"][metric]
                self.assertEqual(Fraction(exact["numerator"], exact["denominator"]), count)
        chance = random["probability_of_any_collision"]
        self.assertEqual(Fraction(chance["numerator"], chance["denominator"]), 1 - Fraction(factorial(4), 4**4))

    def test_static_partition_and_identical_order_have_deterministic_contrasting_profiles(self):
        arms = fixture.compare()["arms"]
        static, shared = arms["static_rank_partition"], arms["shared_identical_order"]
        self.assertEqual(self.counts(static), {(4, 0, 0): 1})
        self.assertEqual(self.counts(shared), {(1, 3, 1): 1})
        self.assertEqual(static["probability_of_any_collision"], {"numerator": 0, "denominator": 1})
        self.assertEqual(shared["probability_of_any_collision"], {"numerator": 1, "denominator": 1})

    def test_colliding_task_count_agrees_with_the_real_board_first_commit(self):
        profiles = (fixture.TASKS, ("t0",) * 4, ("t0", "t0", "t1", "t1"))
        with TemporaryDirectory() as scratch:
            for index, profile in enumerate(profiles):
                with self.subTest(profile=profile):
                    path = Path(scratch) / f"profile-{index}.jsonl"
                    board = Board(path, seed=6)
                    for worker, task in zip(fixture.WORKERS, profile, strict=True):
                        board.claim(worker, task)
                    self.assertEqual(board.snapshot()["claims"], {})
                    board.end_round()
                    rows = read_log(path)[-1]["data"]["resolved"]
                    observed = (len(rows), sum(len(row["claimants"]) - 1 for row in rows),
                                sum(row["collision"] for row in rows))
                    self.assertEqual(fixture._choice_counts(profile), observed)
