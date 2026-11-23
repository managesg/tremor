from copy import deepcopy
import unittest

from lab import l7_activity, topology


class L7ActivityTests(unittest.TestCase):
    roster = ("a", "b", "c", "d")
    tasks = {
        "accepted": topology.Task(7), "rejected": topology.Task(5),
        "prerequisite": topology.Task(3), "dependent": topology.Task(10, ("prerequisite",)),
    }

    def receipt(self, *, budget=32, read_only=False):
        observations = {"a": {}, "b": {}, "c": {"dependent": 7}, "d": {}}
        if not read_only:
            observations["a"]["accepted"] = 7
            observations["b"]["rejected"] = 99
        fixture = topology.Fixture("activity", self.tasks, observations)
        return topology.run(fixture, "independent", budget=budget, workers=self.roster)

    def test_reading_and_blocked_proposals_leave_a_measured_zero(self):
        receipt = self.receipt(read_only=True)
        self.assertEqual({row["actor"] for row in receipt["trace"] if row["kind"] == "read"}, set(self.roster))
        self.assertTrue(any(row["kind"] == "blocked" for row in receipt["trace"]))
        report = l7_activity.measure(self.roster, receipt)
        self.assertEqual(report["roster_count"], 4)
        self.assertEqual(report["attempted_work_workers"], 0)
        self.assertEqual(report["verified_work_workers"], 0)
        self.assertEqual(report["observed_attempt_share"], 0.0)
        self.assertEqual(report["full_window_attempt_share"], 0.0)
        self.assertIsNone(report["first_budget_stop"])

    def test_repeated_rejected_work_counts_its_worker_once_and_never_as_verified(self):
        receipt = self.receipt()
        trace = receipt["trace"]
        rejected = [row for row in trace if row["kind"] == "verify" and not row["accepted"]]
        self.assertGreater(len(rejected), 1)
        self.assertEqual({trace[row["submission"]]["actor"] for row in rejected}, {"b"})
        report = l7_activity.measure(self.roster, receipt)
        self.assertEqual(report["roster_count"], 4)
        self.assertEqual(report["attempted_work_workers"], 2)
        self.assertEqual(report["verified_work_workers"], 1)
        self.assertEqual(report["observed_attempt_share"], 0.5)
        self.assertEqual(report["full_window_attempt_share"], 0.5)

    def test_budget_stop_marks_only_the_observed_prefix_and_retains_full_roster(self):
        for budget, stop_kind, worker, attempts in ((4, "read", "b", 1), (2, "work", "a", 0)):
            with self.subTest(budget=budget):
                receipt = self.receipt(budget=budget)
                self.assertIs(receipt["budget_stopped"], True)
                stop = next(row for row in receipt["trace"] if row["kind"] == "budget_stop")
                self.assertEqual(stop["attempted"], stop_kind)
                report = l7_activity.measure(self.roster, receipt)
                self.assertEqual(report["roster_count"], 4)
                self.assertEqual(report["attempted_work_workers"], attempts)
                self.assertEqual(report["verified_work_workers"], attempts)
                self.assertEqual(report["observed_attempt_share"], attempts / 4)
                self.assertIsNone(report["full_window_attempt_share"])
                self.assertEqual(report["first_budget_stop"], {"worker": worker, "round": 0, "attempted": stop_kind})

    def test_unknown_work_actor_cannot_expand_the_roster(self):
        receipt = deepcopy(self.receipt())
        work = next(row for row in receipt["trace"] if row["kind"] == "work")
        work["actor"] = "outsider"
        with self.assertRaisesRegex(ValueError, "activity event actor is outside the roster"):
            l7_activity.measure(self.roster, receipt)

    def test_noncanonical_work_cost_is_rejected_even_if_totals_reconcile(self):
        receipt = deepcopy(self.receipt())
        work = next(row for row in receipt["trace"] if row["kind"] == "work")
        work["cost"] += 1
        receipt["costs"]["work"] += 1
        receipt["spent"] += 1
        receipt["unused"] -= 1
        with self.assertRaises(ValueError):
            l7_activity.measure(self.roster, receipt)

    def test_forged_budget_stop_cannot_explain_a_short_window_with_slack(self):
        receipt = self.receipt(budget=4)
        original = l7_activity.measure(self.roster, receipt)
        self.assertIsNone(original["full_window_attempt_share"])
        receipt["budget"] = 32
        receipt["unused"] = receipt["budget"] - receipt["spent"]
        with self.assertRaisesRegex(ValueError, "budget stop does not exhaust the available cap"):
            l7_activity.measure(self.roster, receipt)

    def test_forged_stop_cannot_name_terminal_merge_or_reserved_verification(self):
        for attempted in ("merge", "verify"):
            with self.subTest(attempted=attempted):
                receipt = self.receipt(budget=4)
                stop = next(row for row in receipt["trace"] if row["kind"] == "budget_stop")
                self.assertEqual(stop["attempted"], "read")
                self.assertGreater(receipt["spent"] + topology.UNIT_COST[attempted], receipt["budget"])
                stop["attempted"] = attempted
                with self.assertRaises(ValueError):
                    l7_activity.measure(self.roster, receipt)
