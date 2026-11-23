from copy import deepcopy
import unittest

from lab import l1_verification_allocation as allocation


class L1VerificationAllocationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = allocation.demo()

    def test_all_policies_charge_measurement_and_actions_to_the_same_budget(self):
        expected = {
            "overdispersion": (40, 4, "check"), "uniform": (0, 14, "check"),
            "disagreement": (40, 4, "check"), "majority_retry": (0, 28, "retry_pair"),
        }
        for scenario in ("positive", "null"):
            self.assertIs(self.report[scenario]["scientific_result"], False)
            arms = self.report[scenario]["arms"]
            self.assertEqual(set(arms), set(expected))
            for mode, (measurement, decisions, action) in expected.items():
                with self.subTest(scenario=scenario, mode=mode):
                    plan = arms[mode]["plan"]
                    choices = plan["choices"]
                    self.assertEqual(plan["measurement_spent"], measurement)
                    self.assertEqual(len(choices), decisions)
                    self.assertEqual({choice["action"] for choice in choices}, {action})
                    self.assertEqual(len({choice["claim_id"] for choice in choices}), decisions)
                    self.assertEqual({choice["cost"] for choice in choices}, {2 if action == "retry_pair" else 4})
                    self.assertEqual(plan["allocated"], measurement + sum(choice["cost"] for choice in choices))
                    self.assertEqual(plan["budget"], 56)
                    self.assertEqual(plan["allocated"] + plan["unused"], plan["budget"])

    def test_overdispersion_and_rerun_disagreement_buy_different_checks(self):
        arms = self.report["positive"]["arms"]
        first = {choice["stratum"] for choice in arms["overdispersion"]["plan"]["choices"]}
        second = {choice["stratum"] for choice in arms["disagreement"]["plan"]["choices"]}
        self.assertEqual(first, {"variable"})
        self.assertEqual(second, {"stable"})

    def test_fixture_truth_variants_reuse_the_same_pinned_allocation(self):
        positive, null = self.report["positive"]["arms"], self.report["null"]["arms"]
        for mode in positive:
            with self.subTest(mode=mode):
                self.assertEqual(positive[mode]["plan"], null[mode]["plan"])
                self.assertEqual(positive[mode]["plan_sha256"], null[mode]["plan_sha256"])
                self.assertEqual(positive[mode]["plan_sha256"], allocation.digest(positive[mode]["plan"]))
        self.assertGreater(positive["disagreement"]["metrics"]["undetected_false_completions"], 0)
        self.assertEqual(null["uniform"]["metrics"]["undetected_false_completions"], 0)
        self.assertIsNone(self.report["null"]["overdispersion_vs_uniform"])

    def test_detached_grader_preserves_plan_and_distinguishes_lost_checker_reply(self):
        claims = (allocation.Claim("reported", "public", True), allocation.Claim("dismissed", "public", False))
        plan = allocation.make_plan(claims, {}, mode="uniform", budget=4)
        pin = allocation.digest(plan)
        oracle = {"reported": allocation.Outcome(False, None, (None, None)),
                  "dismissed": allocation.Outcome(True, None, (None, None))}
        before = allocation.grade(plan, claims, oracle, expected_plan_sha256=pin)
        changed_truth = {**oracle, "reported": allocation.Outcome(True, None, (None, None))}
        after = allocation.grade(plan, claims, changed_truth, expected_plan_sha256=pin)
        self.assertEqual(allocation.digest(plan), pin)
        self.assertEqual(before["unknown_checks"], 1)
        self.assertEqual(before["undetected_false_completions"], 1)
        self.assertEqual(after["undetected_false_completions"], 0)
        self.assertEqual(before["missed_legitimate"], 1)
        self.assertEqual(before["unresolved_completions"], 0)
        changed_plan = deepcopy(plan)
        changed_plan["choices"][0]["claim_id"] = "dismissed"
        with self.assertRaisesRegex(ValueError, "allocation or claim inventory pin differs"):
            allocation.grade(changed_plan, claims, oracle, expected_plan_sha256=pin)

    def test_retry_tie_and_missing_vote_stay_unresolved(self):
        retry = self.report["positive"]["arms"]["majority_retry"]["metrics"]
        self.assertEqual(retry["retried"], 56)
        self.assertEqual(retry["retry_returns"], 55)
        self.assertEqual(retry["unresolved_completions"], 1)
        self.assertEqual(retry["missed_legitimate"], 0)
        self.assertEqual(retry["undetected_false_completions"], 0)
        tied = next(row for row in retry["outcomes"] if row["final_completion"] is None)
        self.assertEqual(tied["returned"], (False, None))
        self.assertEqual(tied["claim_id"], "test-07")

    def test_relative_reduction_reports_undefined_zero_baseline(self):
        self.assertIsNone(allocation.relative_reduction(0, 0))
        self.assertIsNone(allocation.relative_reduction(1, 0))
        self.assertEqual(allocation.relative_reduction(1, 4), 0.75)
        self.assertEqual(allocation.relative_reduction(5, 4), -0.25)
