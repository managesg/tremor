import unittest

from lab import topology, topology_independent_budget as independent


class IndependentBudgetTests(unittest.TestCase):
    def test_tight_shares_keep_later_workers_and_preserve_the_union_on_reorder(self):
        fixture = topology.FIXTURES[0]
        arguments = {"worker_caps": {"a": 4, "b": 4, "c": 1}, "budget": 13,
                     "scoring_truth": {task: value.expected for task, value in fixture.tasks.items()}}
        forward = independent.run(fixture, **arguments)
        reverse = independent.run(fixture, **arguments, worker_order=("c", "b", "a"))
        self.assertEqual(forward, reverse)
        self.assertEqual(forward["verified_union"], ["left", "right"])
        self.assertEqual(forward["workers_stopped"], ["a", "b", "c"])
        self.assertEqual(forward["accounting"], {"worker_spent_including_seals": 9, "review_spent": 3,
                                                 "union_spent": 1, "spent": 13, "unused": 0})
        for worker, receipt in forward["workers"].items():
            self.assertLessEqual(receipt["spent"], forward["worker_caps"][worker])
            self.assertTrue(all(event["actor"] in (worker, "verifier") for event in receipt["trace"]))

    def test_duplicate_is_charged_and_credited_once_after_separate_review(self):
        fixture = topology.FIXTURES[1]
        caps = dict.fromkeys(fixture.observations, 9)
        truth = {task: value.expected for task, value in fixture.tasks.items()}
        first = independent.run(fixture, worker_caps=caps, budget=31, scoring_truth=truth)
        self.assertEqual(first["reviewed_tasks"], {"a": ["common"], "b": ["backup", "common"], "c": ["separate"]})
        self.assertEqual(first["verified_union"], ["backup", "common", "separate"])
        self.assertEqual(sum(receipt["costs"]["verify"] for receipt in first["workers"].values()), 4)
        self.assertEqual(first["accounting"]["spent"] + first["accounting"]["unused"], first["budget"])
        changed = independent.run(fixture, worker_caps=caps, budget=31, scoring_truth={**truth, "common": -1})
        self.assertEqual(changed["workers"], first["workers"])
        self.assertEqual(changed["verified_union"], ["backup", "separate"])

    def test_invalid_budget_or_roster_fails_before_execution(self):
        fixture = topology.FIXTURES[0]
        caps = dict.fromkeys(fixture.observations, 9)
        truth = {task: value.expected for task, value in fixture.tasks.items()}
        with self.assertRaisesRegex(ValueError, "allowance"):
            independent.run(fixture, worker_caps=caps, budget=32, scoring_truth=truth)
        with self.assertRaisesRegex(ValueError, "worker order"):
            independent.run(fixture, worker_caps=caps, budget=31, scoring_truth=truth, worker_order=("a", "b", "b"))
