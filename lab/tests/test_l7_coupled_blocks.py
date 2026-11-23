from copy import deepcopy
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from lab import l7_coupled_blocks, topology


class L7CoupledBlocksTests(unittest.TestCase):
    join = topology.FIXTURES[0].tasks["join"]

    @staticmethod
    def pair_of_summaries():
        return [
            {"group": "first", "committed_round": 2,
             "items": [{"task": "left", "answer": 2, "proof_sha256": "1" * 64}]},
            {"group": "second", "committed_round": 2,
             "items": [{"task": "right", "answer": 3, "proof_sha256": "2" * 64}]},
        ]

    @staticmethod
    def pins(summaries):
        return {row["group"]: l7_coupled_blocks.digest(row) for row in summaries}

    def test_weighted_blocks_follow_strong_pairs_and_preserve_the_roster(self):
        roster = ("a", "b", "c", "d")
        pairs = {("a", "c"): 9, ("b", "d"): 8, ("a", "b"): 2, ("c", "d"): 1}
        blocks = l7_coupled_blocks.partition(roster, pairs)
        self.assertEqual(blocks, (("a", "c"), ("b", "d")))
        self.assertCountEqual([worker for block in blocks for worker in block], roster)
        self.assertEqual(l7_coupled_blocks.partition(roster, dict(reversed(tuple(pairs.items())))), blocks)

    def test_partition_resolves_zero_weight_ties_in_declared_roster_order(self):
        roster = ("z", "a", "y", "b")
        self.assertEqual(l7_coupled_blocks.partition(roster, {}), (("z", "a"), ("y", "b")))

    def test_only_genuinely_prior_pinned_summaries_can_supply_join_inputs(self):
        summaries = self.pair_of_summaries()
        pins = self.pins(summaries)
        accepted = l7_coupled_blocks.integrate(summaries, pins, self.join, read_round=3)
        self.assertIs(accepted["verified"], True)
        self.assertEqual(accepted["task"], "join")

        late = deepcopy(summaries)
        late[1]["committed_round"] = 3
        same_round = l7_coupled_blocks.integrate(late, self.pins(late), self.join, read_round=3)
        self.assertIs(same_round["verified"], False)
        self.assertTrue(same_round["reason"])

    def test_missing_changed_or_wrong_block_summary_is_refused(self):
        original = self.pair_of_summaries()
        pins = self.pins(original)
        changed_proof = deepcopy(original)
        changed_proof[1]["items"][0]["proof_sha256"] = "3" * 64
        wrong_block = deepcopy(original)
        wrong_block[1]["group"] = "undesignated"
        for name, summaries in (("missing", original[:1]), ("changed proof", changed_proof),
                                ("wrong block", wrong_block)):
            with self.subTest(name=name):
                result = l7_coupled_blocks.integrate(summaries, pins, self.join, read_round=3)
                self.assertIs(result["verified"], False)
                self.assertTrue(result["reason"])

    def test_demo_charges_summary_boundary_and_uses_matched_block_sizes(self):
        report = l7_coupled_blocks.demo()
        arms = report["arms"]
        self.assertEqual(set(arms), {"coupled", "random", "scope"})
        coupled = arms["coupled"]["groups"]
        roster = [worker for block in coupled for worker in block]
        sizes = sorted(len(block) for block in coupled)
        self.assertTrue(sizes)
        charge_fields = ("local", "publish", "summary_review", "summary_read", "upper_work", "upper_review", "terminal")
        for name, arm in {**arms, "withheld": report["withheld"]}.items():
            with self.subTest(arm=name):
                self.assertEqual(sorted(len(block) for block in arm["groups"]), sizes)
                self.assertCountEqual([worker for block in arm["groups"] for worker in block], roster)
                accounting = arm["accounting"]
                self.assertEqual(accounting["spent"], sum(accounting[field] for field in charge_fields))
                self.assertLessEqual(accounting["spent"], accounting["budget"])
                for field in ("local", "publish", "summary_review", "summary_read", "terminal"):
                    self.assertGreater(accounting[field], 0)
        self.assertIs(report["withheld"]["integration"]["verified"], False)
        self.assertEqual(report["withheld"]["accounting"]["upper_work"], 0)
        self.assertEqual(report["withheld"]["accounting"]["upper_review"], 0)

    def test_calibration_requires_an_immutable_commit_and_independent_counts_pin(self):
        commit = "1" * 40
        mapping = {"a.py": "a", "b.py": "b"}
        wrong_pin = "0" * 64
        replies = [SimpleNamespace(stdout=commit + "\n"), SimpleNamespace(stdout="false\n")]
        with patch.object(l7_coupled_blocks.subprocess, "run", side_effect=replies) as git:
            with patch.object(l7_coupled_blocks, "coupling", return_value={("a.py", "b.py"): 3}) as counts:
                with self.assertRaisesRegex(ValueError, "full immutable commit ID"):
                    l7_coupled_blocks.calibration_from_git("unused", "HEAD", mapping,
                                                           expected_counts_sha256=wrong_pin)
                git.assert_not_called()
                counts.assert_not_called()
                with self.assertRaisesRegex(ValueError, "differ from the independently pinned calibration export"):
                    l7_coupled_blocks.calibration_from_git("unused", commit, mapping,
                                                           expected_counts_sha256=wrong_pin)
                counts.assert_called_once_with("unused", commit, max_files=50)
