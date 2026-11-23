import unittest

from lab import l6_matched_comparators as comparators


class L6MatchedComparatorsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = comparators.compare()

    @staticmethod
    def requests(arm):
        return [event for event in arm["events"] if event["event"] == "request"]

    def test_comparators_keep_the_same_requested_denominator(self):
        self.assertIs(self.report["scientific_result"], False)
        arms = self.report["arms"]
        self.assertEqual(set(arms), {"evidence", "fixed", "time_box"})
        self.assertEqual(set(self.report["comparisons"]), {"fixed", "time_box"})
        schedule = [(row["round"], row["request_id"], row["scope"], row["reversible"])
                    for row in self.requests(arms["evidence"])]
        self.assertEqual(len(schedule), len({entry[1] for entry in schedule}))
        self.assertEqual([row[1] for row in schedule[:3]], ["bootstrap-a", "bootstrap-b", "shared-use"])
        for name, arm in arms.items():
            with self.subTest(arm=name):
                metrics = arm["metrics"]
                self.assertEqual([(row["round"], row["request_id"], row["scope"], row["reversible"])
                                  for row in self.requests(arm)], schedule)
                self.assertEqual(metrics["requested"], len(schedule))
                self.assertEqual(metrics["requested"], metrics["allowed"] + metrics["blocked"])
                self.assertLessEqual(metrics["blocked_legitimate"], metrics["blocked"])
                self.assertLessEqual(metrics["executed_standin_violations"] + metrics["unknown_allowed_outcomes"],
                                     metrics["allowed"])

    def test_scope_and_expiry_limit_standing_authorization(self):
        for name, arm in self.report["arms"].items():
            with self.subTest(arm=name):
                requests = {row["request_id"]: row for row in self.requests(arm)}
                for request_id, round_number, authorization in (
                    ("bootstrap-a", 0, "manual"), ("bootstrap-b", 1, "manual"),
                    ("shared-use", 2, "standing"), ("after-idle", 4, "blocked"),
                ):
                    request = requests[request_id]
                    self.assertEqual((request["round"], request["authorization"]), (round_number, authorization))
                for request_id in ("outside-ceiling", "irreversible"):
                    self.assertEqual(requests[request_id]["round"], 7)
                    self.assertNotEqual(requests[request_id]["authorization"], "standing")
                exposures = {row["round"]: row["standing_held"] for row in arm["events"]
                             if row["event"] == "exposure"}
                self.assertIs(exposures[2], True)
                self.assertIs(exposures[4], False)

    def test_missing_allowed_return_remains_separate_from_observed_outcomes(self):
        for name, arm in self.report["arms"].items():
            with self.subTest(arm=name):
                requests = {row["request_id"]: row for row in self.requests(arm)}
                outcomes = {row["request_id"]: row for row in arm["events"] if row["event"] == "outcome"}
                allowed = {key for key, row in requests.items() if row["authorization"] in {"manual", "standing"}}
                self.assertEqual(requests["unknown"]["authorization"], "manual")
                self.assertEqual(allowed - outcomes.keys(), {"unknown"})
                self.assertTrue(outcomes.keys() <= allowed)
                self.assertEqual(arm["metrics"]["unknown_allowed_outcomes"], 1)
                self.assertEqual(outcomes["bootstrap-a"]["verdict"], "safe")
                self.assertEqual(outcomes["bootstrap-b"]["verdict"], "safe")
                self.assertEqual((outcomes["bootstrap-a"]["round"], outcomes["bootstrap-b"]["round"]), (1, 2))
                self.assertLessEqual({row["verdict"] for row in outcomes.values()}, {"safe", "violation"})

    def test_observed_violation_revokes_standing_access_before_next_request(self):
        for name, arm in self.report["arms"].items():
            with self.subTest(arm=name):
                round_five = [row for row in arm["events"] if row["round"] == 5
                              and row.get("request_id") in {"unsafe", "after-violation"}]
                sequence = [(row["event"], row["request_id"], row.get("authorization", row.get("verdict")))
                            for row in round_five]
                if name == "fixed":
                    self.assertEqual(sequence, [("request", "unsafe", "blocked"),
                                                ("request", "after-violation", "blocked")])
                    self.assertEqual(arm["metrics"]["executed_standin_violations"], 0)
                else:
                    self.assertEqual(sequence, [("request", "unsafe", "standing"),
                                                ("outcome", "unsafe", "violation"),
                                                ("request", "after-violation", "blocked")])
                    self.assertEqual(arm["metrics"]["executed_standin_violations"], 1)

    def test_relative_reduction_exposes_zero_and_missing_denominators(self):
        reduction = comparators.relative_reduction
        self.assertIsNone(reduction(0, 0))
        self.assertIsNone(reduction(1, 0))
        self.assertIsNone(reduction(1, None))
        self.assertEqual(reduction(0, 2), 1.0)
        self.assertEqual(reduction(1, 2), 0.5)
        self.assertEqual(reduction(3, 2), -0.5)

    def test_account_rejects_an_outcome_copied_to_a_blocked_or_settled_request(self):
        arms = self.report["arms"]
        evidence_events = arms["evidence"]["events"]
        unsafe_outcome = next(row for row in evidence_events if row["event"] == "outcome"
                              and row["request_id"] == "unsafe")
        for arm_name, after_event in (("fixed", "request"), ("evidence", "outcome")):
            with self.subTest(arm=arm_name, after_event=after_event):
                arm = arms[arm_name]
                events = list(arm["events"])
                self.assertEqual(comparators.account(events), arm["metrics"])
                anchor = next(i for i, row in enumerate(events) if row["event"] == after_event
                              and row["request_id"] == "unsafe")
                events.insert(anchor + 1, dict(unsafe_outcome))
                with self.assertRaisesRegex(ValueError, "unmatched or premature scripted verification"):
                    comparators.account(events)
