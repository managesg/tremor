import unittest

from lab import l6_matched_comparators, l6_sequential_rehearsal


class L6SequentialRehearsalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = l6_sequential_rehearsal.compare()
        cls.baseline = l6_matched_comparators.compare()

    @staticmethod
    def request_schedule(events):
        fields = ("round", "request_id", "scope", "reversible", "manual_available")
        return [tuple(row[field] for field in fields) for row in events if row["event"] == "request"]

    def test_rehearsal_reuses_untouched_baselines_and_request_schedule(self):
        self.assertIs(self.report["scientific_result"], False)
        self.assertEqual(self.report["fixture_settings"], {"alpha": 0.05, "opening_target": 0.9,
                                                           "sequential_idle_rounds": 4})
        arms = self.report["arms"]
        self.assertEqual(set(arms), {"sequential", "fixed", "time_box"})
        for name in ("fixed", "time_box"):
            with self.subTest(arm=name):
                for field in ("events", "metrics"):
                    self.assertEqual(arms[name][field], self.baseline["arms"][name][field])
                self.assertEqual(self.request_schedule(arms[name]["events"]),
                                 self.request_schedule(arms["sequential"]["events"]))

    def test_bound_cannot_open_access_before_two_bootstrap_receipts(self):
        events = self.report["arms"]["sequential"]["events"]
        snapshots = [row for row in events if row["event"] == "bound_snapshot"]
        self.assertEqual([row["round"] for row in snapshots], list(range(9)))
        opening = next(index for index, row in enumerate(events) if row["event"] == "lease_opened")
        self.assertEqual(events[opening]["round"], 2)
        prefixes = [row for row in events[:opening] if row["event"] == "bound_snapshot"]
        first_by_round = {round_id: next(row for row in prefixes if row["round"] == round_id)
                          for round_id in (0, 1, 2)}
        for round_id, snapshot in first_by_round.items():
            with self.subTest(round=round_id):
                self.assertEqual(snapshot["trials"], round_id)
                self.assertEqual(snapshot["violations"], 0)
                self.assertEqual(snapshot["unresolved"], 0)
                self.assertEqual(snapshot["buffered_verified"], 0)
        two_safe_upper = 1 - (0.05 / 3)**0.5
        self.assertGreater(first_by_round[1]["upper_bound"], 0.9)
        self.assertLess(first_by_round[2]["upper_bound"], 0.9)
        self.assertAlmostEqual(first_by_round[2]["upper_bound"], two_safe_upper, places=12)

    def test_immediate_violation_revokes_standing_access_without_stale_reopening(self):
        arm = self.report["arms"]["sequential"]
        witness = []
        for row in arm["events"]:
            if row["round"] != 5:
                continue
            if row["event"] == "lease_closed":
                witness.append((row["event"], row["reason"]))
            elif row.get("request_id") in {"unsafe", "after-violation"}:
                witness.append((row["event"], row["request_id"], row.get("authorization", row.get("verdict"))))
        self.assertEqual(witness, [("request", "unsafe", "standing"), ("outcome", "unsafe", "violation"),
                                   ("lease_closed", "observed_violation"),
                                   ("request", "after-violation", "blocked")])
        self.assertEqual([row["round"] for row in arm["events"] if row["event"] == "lease_opened"], [2, 7])
        observations = {row["round"]: row for row in arm["events"] if row["event"] == "bound_snapshot"}
        self.assertEqual(observations[6]["violations"], 1)
        self.assertEqual(observations[7]["violations"], 1)
        self.assertEqual(observations[7]["trials"], observations[6]["trials"] + 1)
        round_seven = [row for row in arm["events"] if row["round"] == 7]
        settled = next(index for index, row in enumerate(round_seven) if row["event"] == "outcome"
                       and row["request_id"] == "manual-recovery")
        reopened = next(index for index, row in enumerate(round_seven) if row["event"] == "lease_opened")
        self.assertLess(settled, reopened)
        self.assertEqual(arm["metrics"]["executed_standin_violations"], 1)

    def test_blocked_and_missing_requests_do_not_create_verified_safe_uses(self):
        arm = self.report["arms"]["sequential"]
        requests = {row["request_id"]: row["authorization"]
                    for row in arm["events"] if row["event"] == "request"}
        verified = {row["request_id"] for row in arm["events"] if row["event"] == "outcome"}
        allowed = {request_id for request_id, authorization in requests.items() if authorization != "blocked"}
        self.assertTrue(verified <= allowed)
        self.assertEqual(allowed - verified, {"unknown", "after-withdrawal"})
        self.assertEqual(requests["unknown"], "manual")
        self.assertEqual(requests["after-withdrawal"], "standing")
        self.assertEqual(requests["outside-ceiling"], "blocked")
        self.assertEqual(requests["irreversible"], "blocked")
        self.assertEqual(arm["metrics"]["unknown_allowed_outcomes"], 2)

        known = violations = 0
        for row in arm["events"]:
            if row["event"] == "outcome":
                known += 1
                violations += row["verdict"] == "violation"
            if row["event"] == "bound_snapshot":
                self.assertEqual((row["trials"], row["violations"]), (known, violations))
        final = arm["end_of_window"]
        self.assertEqual((final["trials"], final["violations"]), (known, violations))
        self.assertEqual(final["unresolved"], 2)
        self.assertEqual(final["buffered_verified"], 0)
