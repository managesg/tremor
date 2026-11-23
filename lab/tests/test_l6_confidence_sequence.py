from fractions import Fraction
import math
import unittest

from lab.l6_confidence_sequence import Execution, Verification, log_e_value, snapshot, upper_bound


def exact_e_value(violations, trials, risk):
    # Integrate q**violations * (1-q)**(trials-violations) on the unit interval.
    safe = trials - violations
    predictive = sum(Fraction((-1)**power * math.comb(safe, power), violations + power + 1)
                     for power in range(safe + 1))
    return predictive / (risk**violations * (1 - risk)**safe)


class L6ConfidenceSequenceTests(unittest.TestCase):
    def test_log_e_values_match_exact_uniform_mixture_on_small_grid(self):
        for trials in range(8):
            for violations in range(trials + 1):
                for numerator in (1, 3, 8, 11, 15):
                    risk = Fraction(numerator, 16)
                    with self.subTest(trials=trials, violations=violations, risk=risk):
                        exact = exact_e_value(violations, trials, risk)
                        self.assertAlmostEqual(log_e_value(violations, trials, float(risk)), math.log(exact), places=12)

    def test_upper_bound_agrees_with_independent_mixed_likelihood_inequalities(self):
        alpha = Fraction(1, 20)
        threshold = 1 / alpha
        self.assertEqual(upper_bound(0, 0, alpha=float(alpha)), 1.0)
        self.assertEqual(upper_bound(6, 6, alpha=float(alpha)), 1.0)
        for failures, trials in ((0, 1), (0, 7), (3, 7), (6, 7)):
            with self.subTest(failures=failures, trials=trials):
                bound = upper_bound(failures, trials, alpha=float(alpha))
                self.assertGreater(bound, failures / trials)
                self.assertLess(bound, 1)
                self.assertLess(exact_e_value(failures, trials, Fraction(bound - 1e-7)), threshold)
                self.assertGreater(exact_e_value(failures, trials, Fraction(bound + 1e-7)), threshold)
        self.assertAlmostEqual(upper_bound(0, 7, alpha=float(alpha)), 1 - (float(alpha) / 8)**(1 / 7), places=12)

    def test_upper_bound_rejects_invalid_alpha(self):
        for alpha in (0, -0.1, 1, 1.1, float("nan"), float("inf")):
            with self.subTest(alpha=alpha), self.assertRaises(ValueError):
                upper_bound(0, 1, alpha=alpha)

    def test_latest_available_receipt_waits_for_in_scope_execution_prefix(self):
        executions = [Execution("a", "notes", 1), Execution("other", "outside", 2),
                      Execution("b", "notes", 3), Execution("c", "notes", 4),
                      Execution("missing", "notes", 9)]
        receipts = [Verification("a", "notes", 5, False), Verification("c", "notes", 6, True),
                    Verification("b", "notes", 8, False)]
        for as_of, expected in ((4, (0, 0, 3, 0)), (7, (1, 0, 1, 1)),
                                (8, (3, 1, 0, 0)), (10, (3, 1, 1, 0))):
            with self.subTest(as_of=as_of):
                report = snapshot(executions, receipts, scope="notes", as_of=as_of, alpha=0.05)
                fields = ("trials", "violations", "unresolved", "buffered_verified")
                self.assertEqual(tuple(report[field] for field in fields), expected)
                trials, violations, _, _ = expected
                self.assertEqual(report["upper_bound"], upper_bound(violations, trials, alpha=0.05))

    def test_snapshot_rejects_duplicate_mismatched_or_premature_records(self):
        execution = Execution("a", "notes", 1)
        receipt = Verification("a", "notes", 2, False)
        for name, executions, receipts in (
            ("duplicate execution", [execution, execution], [receipt]),
            ("duplicate receipt", [execution], [receipt, receipt]),
            ("unknown attempt", [execution], [Verification("other", "notes", 2, False)]),
            ("different scope", [execution], [Verification("a", "other", 2, False)]),
            ("premature receipt", [execution], [Verification("a", "notes", 1, False)]),
        ):
            with self.subTest(name=name), self.assertRaises(ValueError):
                snapshot(executions, receipts, scope="notes", as_of=3, alpha=0.05)
