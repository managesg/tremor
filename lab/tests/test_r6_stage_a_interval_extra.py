"""Extra tests for lab/r6_stage_a.in_interval (closed interval [lo, hi]); each case pins one mutant class."""
import math
import unittest

from lab import r6_stage_a as a


class InIntervalTests(unittest.TestCase):
    def test_lower_bound_closed(self):
        self.assertTrue(a.in_interval(0.2, (0.2, 0.5)))

    def test_upper_bound_closed(self):
        self.assertTrue(a.in_interval(0.5, (0.2, 0.5)))

    def test_just_below_lower_excluded(self):
        self.assertFalse(a.in_interval(math.nextafter(0.2, 0), (0.2, 0.5)))
        self.assertFalse(a.in_interval(-1, (0, 1)))

    def test_just_above_upper_excluded(self):
        self.assertFalse(a.in_interval(math.nextafter(0.5, 1), (0.2, 0.5)))
        self.assertFalse(a.in_interval(2, (0, 1)))

    def test_interior_included(self):
        self.assertTrue(a.in_interval(0.3, (0.2, 0.5)))
        self.assertTrue(a.in_interval(-0.5, (-1, 0)))

    def test_degenerate_interval_contains_its_point_only(self):
        self.assertTrue(a.in_interval(0.4, (0.4, 0.4)))
        self.assertFalse(a.in_interval(0.41, (0.4, 0.4)))
        self.assertFalse(a.in_interval(0.39, (0.4, 0.4)))

    def test_reversed_bounds_contain_nothing(self):
        self.assertFalse(a.in_interval(0.3, (0.5, 0.2)))

    def test_bounds_not_confused_with_each_other(self):
        # distinguishes lo/lo, hi/hi and swapped-variable mutants
        self.assertFalse(a.in_interval(0.9, (0.2, 0.5)))
        self.assertFalse(a.in_interval(0.0, (0.2, 0.5)))

    def test_returns_bool(self):
        self.assertIs(a.in_interval(0.3, (0.2, 0.5)), True)
        self.assertIs(a.in_interval(0.9, (0.2, 0.5)), False)


if __name__ == "__main__":
    unittest.main()
