from copy import deepcopy
import unittest
from unittest.mock import patch

from lab import l7_parallel_selection as selection, topology


class L7ParallelSelectionTests(unittest.TestCase):
    fixture = topology.FIXTURES[0]
    subteams = {
        "zulu": {"a": {"left": 2}, "b": {}, "c": {"join": 7}},
        "alpha": {"a": {}, "b": {"right": 3}, "c": {}},
    }
    caps = {"zulu": 32, "alpha": 32}
    budget = 80

    def run_fixture(self, *, subteams=None, budget=None, cancel_selection=False):
        return selection.run(self.fixture, self.subteams if subteams is None else subteams,
                             team_caps=self.caps, budget=self.budget if budget is None else budget,
                             cancel_selection=cancel_selection)

    def verify_report(self, report):
        return selection.audit(self.fixture, self.subteams, report, team_caps=self.caps, budget=self.budget)

    def test_complementary_teams_do_not_receive_credit_for_their_union(self):
        report = self.run_fixture()
        self.assertEqual(report["status"], "completed")
        self.assertEqual(report["selected"], {"candidate_id": "zulu", "verified_tasks": ["left"]})
        self.assertEqual(report["diagnostic_union"], ["left", "right"])
        self.assertEqual(report["utility"], 1)
        self.assertEqual(set(report["teams"]), set(self.subteams))
        accounting = report["accounting"]
        self.assertEqual(accounting["budget"], self.budget)
        self.assertEqual(accounting["verification_spent"], len(self.subteams))
        self.assertEqual(accounting["selection_spent"], 1)
        self.assertEqual(accounting["spent"], sum(accounting[field] for field in
                                                ("team_spent", "verification_spent", "selection_spent")))
        self.assertEqual(accounting["spent"] + accounting["unused"], self.budget)
        self.assertEqual(self.verify_report(report), report)

    def test_declared_order_breaks_ties_rather_than_candidate_name(self):
        original = self.run_fixture()
        reversed_teams = dict(reversed(tuple(self.subteams.items())))
        reversed_report = self.run_fixture(subteams=reversed_teams)
        self.assertEqual(original["selected"]["candidate_id"], "zulu")
        self.assertEqual(reversed_report["selected"], {"candidate_id": "alpha", "verified_tasks": ["right"]})
        self.assertEqual(original["diagnostic_union"], reversed_report["diagnostic_union"])

    def test_prerequisite_verified_in_another_team_cannot_enable_work(self):
        report = self.run_fixture()
        left_trace = report["teams"]["zulu"]["trace"]
        self.assertTrue(any(row["kind"] == "blocked" and row["task"] == "join" and "right" in row["missing"]
                            for row in left_trace))
        self.assertFalse(any(row["kind"] == "work" and row["task"] == "join" for row in left_trace))
        self.assertEqual(report["teams"]["zulu"]["artifact"], [{"task": "left", "answer": 2, "inputs": []}])
        self.assertEqual(report["teams"]["alpha"]["artifact"], [{"task": "right", "answer": 3, "inputs": []}])

    def test_overcommitted_budget_is_rejected_before_any_subteam_execution(self):
        required = sum(self.caps.values()) + len(self.subteams) + 1
        with patch.object(topology, "run", side_effect=AssertionError("budget application reached topology")):
            with self.assertRaises(ValueError):
                self.run_fixture(budget=required - 1)
        self.assertEqual(self.run_fixture(budget=required)["status"], "completed")

    def test_cancelling_selection_retains_team_work_without_a_selected_candidate(self):
        report = self.run_fixture(cancel_selection=True)
        complete = self.run_fixture()
        self.assertEqual(report["status"], "incomplete_selection")
        self.assertIsNone(report["selected"])
        self.assertIsNone(report["utility"])
        self.assertEqual(report["diagnostic_union"], ["left", "right"])
        self.assertEqual(report["teams"], complete["teams"])
        self.assertEqual(report["accounting"]["selection_spent"], 0)
        self.assertEqual(report["accounting"]["spent"], complete["accounting"]["spent"] - 1)
        self.assertEqual(self.verify_report(report), report)

    def test_audit_rejects_relabelled_priority_and_forged_selected_union(self):
        report = self.run_fixture()
        changed = deepcopy(report)
        changed["selected"] = {"candidate_id": "alpha", "verified_tasks": ["right"]}
        with self.assertRaises(ValueError):
            self.verify_report(changed)
        changed["selected"] = {"candidate_id": "zulu", "verified_tasks": report["diagnostic_union"]}
        changed["utility"] = len(changed["selected"]["verified_tasks"])
        with self.assertRaises(ValueError):
            self.verify_report(changed)

    def test_changing_final_assessment_truth_does_not_change_team_traces(self):
        original = self.run_fixture()
        alternate_truth = {"left": 99, "right": 3, "join": 12}
        alternate = selection.run(self.fixture, self.subteams, team_caps=self.caps, budget=self.budget,
                                  assessment_truth=alternate_truth)
        self.assertEqual(original["teams"], alternate["teams"])
        self.assertNotEqual(original["assessment_sha256"], alternate["assessment_sha256"])
        self.assertEqual(original["selected"], {"candidate_id": "zulu", "verified_tasks": ["left"]})
        self.assertEqual(alternate["selected"], {"candidate_id": "alpha", "verified_tasks": ["right"]})
        self.assertEqual(selection.audit(self.fixture, self.subteams, alternate, team_caps=self.caps,
                                         budget=self.budget, assessment_truth=alternate_truth), alternate)
        with self.assertRaises(ValueError):
            self.verify_report(alternate)

    def test_completed_zero_retains_the_selected_empty_candidate(self):
        empty = {candidate: {worker: {} for worker in topology.WORKERS} for candidate in self.subteams}
        report = self.run_fixture(subteams=empty)
        self.assertEqual(report["status"], "completed")
        self.assertEqual(report["selected"], {"candidate_id": "zulu", "verified_tasks": []})
        self.assertEqual(report["diagnostic_union"], [])
        self.assertEqual(report["utility"], 0)
