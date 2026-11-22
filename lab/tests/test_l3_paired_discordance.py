from copy import deepcopy
from fractions import Fraction
from hashlib import sha256
from itertools import product
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lab import l3_paired_discordance as audit


class PairedDiscordanceTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path(self.enterContext(TemporaryDirectory()))
        goal = {"numerator": 1, "denominator": 20}
        zero = {"numerator": 0, "denominator": 1}
        self.case = {
            "heldout_clean_count": 20, "heldout_failure_count": 4,
            "heldout_target_matched": True,
            "heldout_catch_gain": {"numerator": 1, "denominator": 4},
            "paired_clean_flags": {"both": 1, "selected_only": 0, "top_only": 0, "neither": 19},
            "paired_failure_flags": {"both": 2, "selected_only": 1, "top_only": 0, "neither": 1},
            "arms": {
                arm: {
                    "heldout_false_positives": 1, "heldout_false_positive_rate": goal,
                    "threshold_fit_false_positives": 1, "threshold_fit_false_positive_rate": goal, "heldout_catches": catches,
                    "heldout_catch_rate": {"numerator": catches, "denominator": 4},
                }
                for arm, catches in (("top", 2), ("selected", 3))
            },
        }
        self.case["fit"] = {
            "threshold_fit_clean_ids": [f"fit-{i}" for i in range(20)],
            "target_false_positive_rate": goal,
            "arms": {arm: {"threshold_fit_false_positives": 1} for arm in audit.ARMS},
        }
        self.pin_fit()
        self.zero = zero

    def pin_fit(self):
        content = json.dumps(self.case["fit"], sort_keys=True, separators=(",", ":"), allow_nan=False)
        self.case["plan_sha256"] = sha256(content.encode()).hexdigest()

    def replay(self):
        report = self.directory / "report.json"
        raw = json.dumps({"scope": "L3_B_fallback_development", "scientific_result": False,
                          "cases": {"public": self.case}}).encode()
        report.write_bytes(raw)
        return audit.verify(report, report_sha256=sha256(raw).hexdigest())["cases"]["public"]

    def test_tail_matches_direct_sign_enumeration(self):
        for discordance in range(10):
            signs = [sum(row) for row in product((-1, 1), repeat=discordance)]
            for selected in range(discordance + 1):
                cutoff = abs(2 * selected - discordance)
                expected = Fraction(sum(abs(value) >= cutoff for value in signs), len(signs))
                self.assertEqual(audit.conditional_two_sided(discordance - selected, selected), expected)

    def test_implausibly_large_count_is_refused_before_exact_calculation(self):
        with self.assertRaisesRegex(ValueError, "too many scripted pairs"):
            audit.conditional_two_sided(10**100, 0)

    def test_one_directional_discordance_and_fixture_floor(self):
        result = self.replay()
        self.assertEqual(result["failure_discordant_pairs"], 1)
        self.assertEqual(result["catch_gain_at_matched_target"], "1/4")
        self.assertEqual(result["illustrative_two_sided_tail"], "1")
        self.assertEqual(result["illustrative_minimum_tail_at_fixture_size"], "1/8")

    def test_changed_clean_margins_withhold_gain_and_tail(self):
        self.case["paired_clean_flags"].update(both=0, top_only=1)
        self.case["arms"]["selected"]["heldout_false_positives"] = 0
        self.case["arms"]["selected"]["heldout_false_positive_rate"] = self.zero
        self.case["heldout_target_matched"] = False
        self.case["heldout_catch_gain"] = None
        result = self.replay()
        self.assertEqual(result["clean_discordant_pairs"], 1)
        self.assertIsNone(result["catch_gain_at_matched_target"])
        self.assertIsNone(result["illustrative_two_sided_tail"])

    def test_equal_table_total_does_not_substitute_for_marginal_agreement(self):
        table = deepcopy(self.case["paired_failure_flags"])
        table.update(selected_only=0, top_only=1)
        self.case["paired_failure_flags"] = table
        with self.assertRaisesRegex(ValueError, "differs from the reported margin"):
            self.replay()

    def test_re_pinned_zero_fit_count_cannot_be_reported_as_one_twentieth(self):
        for arm in audit.ARMS:
            self.case["fit"]["arms"][arm]["threshold_fit_false_positives"] = 0
            self.case["arms"][arm]["threshold_fit_false_positives"] = 0
        self.pin_fit()
        with self.assertRaisesRegex(ValueError, "threshold-fit rate differs"):
            self.replay()

        for arm in audit.ARMS:
            self.case["arms"][arm]["threshold_fit_false_positive_rate"] = self.zero
        self.case.update(heldout_target_matched=False, heldout_catch_gain=None)
        self.assertIsNone(self.replay()["catch_gain_at_matched_target"])

    def test_refuses_crossed_inner_pin_and_disagreement_between_fit_copies(self):
        fit = self.case["fit"]
        original = fit["threshold_fit_clean_ids"][0]
        fit["threshold_fit_clean_ids"][0] = "changed"
        with self.assertRaisesRegex(ValueError, "inner plan digest"):
            self.replay()
        fit["threshold_fit_clean_ids"][0] = original
        self.case["arms"]["selected"]["threshold_fit_false_positives"] = 0
        with self.assertRaisesRegex(ValueError, "threshold-fit count differs"):
            self.replay()

    def test_re_pinned_threshold_fit_denominator_cannot_repeat_a_clean_id(self):
        ids = self.case["fit"]["threshold_fit_clean_ids"]
        ids[1] = ids[0]
        self.pin_fit()
        with self.assertRaisesRegex(ValueError, "threshold-fit clean inventory"):
            self.replay()
