from collections import Counter
from fractions import Fraction
from itertools import combinations
import unittest

from lab.r1_l2_immunity_null import first_generation_null


def enumerate_counts(population, immune, draws):
    targets = [0] * immune + [1] * (population - immune)
    counts = Counter(sum(draw) for draw in combinations(targets, draws))
    total = sum(counts.values())
    return {count: Fraction(frequency, total) for count, frequency in counts.items()}


class L2ImmunityNullTests(unittest.TestCase):
    def test_five_targets_have_the_hand_counted_distribution(self):
        # Among ten target pairs, one has zero eligible targets, six have one, and three have two.
        expected = {0: Fraction(1, 10), 1: Fraction(6, 10), 2: Fraction(3, 10)}
        self.assertEqual(enumerate_counts(5, 2, 2), expected)
        self.assertEqual(first_generation_null(population=5, immune=2, draws=2),
                         {"pmf": expected, "mean": Fraction(6, 5)})

    def test_exact_distribution_matches_enumeration_for_small_populations(self):
        for population in range(9):
            for immune in range(population + 1):
                for draws in range(population + 1):
                    with self.subTest(population=population, immune=immune, draws=draws):
                        expected = enumerate_counts(population, immune, draws)
                        result = first_generation_null(population=population, immune=immune, draws=draws)
                        self.assertEqual(result["pmf"], expected)
                        self.assertEqual(result["mean"],
                                         sum(count * probability for count, probability in expected.items()))

    def test_invalid_draw_setup_is_rejected(self):
        for population, immune, draws in ((4, 0, 5), (0, 1, 0), (4, -1, 1), (4, 1, True), (4, 1, 1.0)):
            with self.subTest(population=population, immune=immune, draws=draws), self.assertRaises(ValueError):
                first_generation_null(population=population, immune=immune, draws=draws)
