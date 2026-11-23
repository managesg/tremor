from copy import deepcopy
from fractions import Fraction
import json
import unittest

from lab import l1_nested_model_control as model


def contrast(row, mask):
    return (-1)**((row & mask).bit_count() % 2)


def conditions(*, signal=2, noise=1, alias_susceptibility=False):
    rows = []
    for index in range(8):
        mean, size, activity, susceptibility, error = (contrast(index, mask) for mask in (1, 2, 3, 4, 5))
        slope = 2 + (size if alias_susceptibility else susceptibility)
        rows.append({"id": f"condition-{index}", "mean": Fraction(2 + mean, 4), "team_size": 8 + 2 * size,
                     "activity": 10 + activity,
                     "response": 20 + 2 * mean + 3 * size + 4 * activity + signal * susceptibility + noise * error,
                     "dose_counts": [(dose, 12 + slope * dose) for dose in (-1, 0, 1)]})
    return rows


class L1NestedModelControlTests(unittest.TestCase):
    def test_orthogonal_positive_and_null_have_exact_nested_statistics(self):
        for signal, reduced_rss, partial, f_statistic in ((2, 40, Fraction(4, 5), 12), (0, 8, Fraction(0), 0)):
            with self.subTest(signal=signal):
                result = model.nested_rehearsal(conditions(signal=signal))
                self.assertEqual(result["status"], "computed")
                self.assertIsNone(result["reason"])
                self.assertEqual((result["reduced_rank"], result["full_rank"]), (4, 5))
                self.assertEqual((result["df_numerator"], result["df_denominator"]), (1, 3))
                self.assertEqual((result["rss_reduced"], result["rss_full"]), (reduced_rss, 8))
                self.assertEqual(result["partial_r2"], partial)
                self.assertEqual(result["f_statistic"], f_statistic)

    def test_rank_deficiency_withholds_the_incremental_statistics(self):
        redundant_nuisance = conditions()
        for row in redundant_nuisance:
            row["activity"] = row["team_size"]
        for reason, rows in (("nuisance_rank_deficient", redundant_nuisance),
                             ("susceptibility_rank_deficient", conditions(alias_susceptibility=True))):
            with self.subTest(reason=reason):
                result = model.nested_rehearsal(rows)
                self.assertEqual((result["status"], result["reason"]), ("undefined", reason))
                self.assertIsNone(result["partial_r2"])
                self.assertIsNone(result["f_statistic"])

    def test_no_residual_degrees_and_perfect_fit_do_not_produce_f_values(self):
        saturated = model.nested_rehearsal(conditions()[:5])
        self.assertEqual((saturated["status"], saturated["reason"]),
                         ("undefined", "no_residual_degrees_of_freedom"))
        self.assertEqual(saturated["df_denominator"], 0)
        self.assertIsNone(saturated["f_statistic"])

        for signal, expected_partial in ((2, Fraction(1)), (0, None)):
            with self.subTest(signal=signal):
                perfect = model.nested_rehearsal(conditions(signal=signal, noise=0))
                self.assertEqual((perfect["status"], perfect["reason"]), ("undefined", "perfect_fit_f_undefined"))
                self.assertEqual(perfect["rss_full"], 0)
                self.assertEqual(perfect["partial_r2"], expected_partial)
                self.assertIsNone(perfect["f_statistic"])

    def test_count_slopes_are_exact_with_repeated_doses_and_reported_by_condition(self):
        points = [(-2, 7), (0, 10), (2, 13), (2, 13)]
        self.assertEqual(model.count_scale_slope(points), Fraction(3, 2))
        result = model.nested_rehearsal(conditions())
        self.assertEqual(result["susceptibility_by_id"], {
            f"condition-{index}": Fraction(2 + contrast(index, 4)) for index in range(8)
        })

    def test_bad_rows_or_insufficient_distinct_doses_are_rejected(self):
        rows = conditions()
        repeated_id = [*rows, rows[0]]
        unvalidated_float = deepcopy(rows)
        unvalidated_float[0]["mean"] = 0.75
        for inputs in (repeated_id, unvalidated_float):
            with self.subTest(inputs=inputs[0]), self.assertRaises(ValueError):
                model.nested_rehearsal(inputs)
        with self.assertRaises(ValueError):
            model.count_scale_slope([(0, 0), (0, 0), (1, 1)])

    def test_serialized_rehearsal_replays_deterministically(self):
        encoded = json.dumps(model.demo(), sort_keys=True, allow_nan=False)
        self.assertEqual(encoded, json.dumps(model.demo(), sort_keys=True, allow_nan=False))
        report = json.loads(encoded)
        self.assertIs(report["scientific_result"], False)
        self.assertEqual(report["cases"]["positive"]["partial_r2"], {"numerator": 4, "denominator": 5})
        self.assertIsNone(report["cases"]["collinear"]["f_statistic"])
