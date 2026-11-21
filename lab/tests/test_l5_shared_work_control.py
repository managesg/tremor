import unittest

from lab.l5_shared_work_control import compare


class SharedWorkControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = compare()
        cls.rows = {(row["taskset"]["n_agents"], row["mode"], row["disrupted"]): row
                    for row in cls.report["rows"]}

    def test_fixed_work_attempts_and_separate_output_and_legitimacy(self):
        self.assertEqual(len(self.rows), 8)
        for (size, mode, disrupted), row in self.rows.items():
            with self.subTest(size=size, mode=mode, disrupted=disrupted):
                attempts = [entry["action"] for entry in row["dispatch"] if entry["action"]["type"] == "work"]
                baseline = [entry["action"] for entry in self.rows[size, "observe", False]["dispatch"]
                            if entry["action"]["type"] == "work"]
                self.assertEqual(attempts, baseline)
                self.assertEqual(len({action["agent"] for action in attempts}), size)
                self.assertEqual(row["attempted_work"], size)
                self.assertEqual(row["distinct_passing_work"], size - 1)
                self.assertEqual(row["refused_work"], int(mode == "code"))
                self.assertEqual(row["executed_duplicate_work"], int(mode == "observe"))
                self.assertEqual(row["executed_norm_violations"], int(mode == "observe"))
                self.assertEqual(row["blocked_legitimate_work"], 0)
                self.assertTrue(row["score"]["valid"])

    def test_attempted_contention_board_collision_and_router_refusal_differ(self):
        for row in self.rows.values():
            shared = row["shared_task"]
            claims = [event for event in row["dispatch"]
                      if event["round"] == 0 and event["action"].get("item") == shared]
            self.assertEqual([claim["action"]["agent"] for claim in claims], ["a2", "a1"])
            observation = row["mode"] == "observe"
            self.assertEqual([claim["status"] for claim in claims],
                             ["admitted", "violation_executed" if observation else "refused"])
            opening = next(event for event in row["board_trace"] if event["type"] == "end_round")
            resolution = next(event for event in opening["data"]["resolved"] if event["item"] == shared)
            self.assertEqual(resolution["winner"], "a2")
            self.assertEqual(resolution["claimants"], ["a1", "a2"] if observation else ["a2"])
            self.assertIs(resolution["collision"], observation)
            contested_work = [event for event in row["router_journal"] if event["action_type"] == "work"]
            self.assertEqual(len(contested_work), 1)
            self.assertIs(contested_work[0]["costs_turn"], not observation)

    def test_reclaim_follows_the_real_commit_barrier(self):
        for row in self.rows.values():
            shared = row["shared_task"]
            intervention = [event for event in row["board_trace"] if event["type"] == "release"]
            self.assertEqual(len(intervention), int(row["disrupted"]))
            if not row["disrupted"]:
                self.assertEqual(row["owner_after_intervention_commit"], "a2")
                continue
            release = intervention[0]
            self.assertEqual((release["agent"], release["round"], release["data"]["item"]), ("a2", 1, shared))
            self.assertIsNone(row["owner_after_intervention_commit"])
            reclaim, = [event for event in row["board_trace"]
                        if event["type"] == "claim" and event["round"] == 2 and event["data"]["item"] == shared]
            commit, = [event for event in row["board_trace"]
                       if event["type"] == "end_round" and event["round"] == 1]
            self.assertLess(release["seq"], commit["seq"])
            self.assertLess(commit["seq"], reclaim["seq"])
            self.assertEqual(reclaim["agent"], "a2")

    def test_repeat_is_deterministic(self):
        self.assertEqual(self.report, compare())


if __name__ == "__main__":
    unittest.main()
