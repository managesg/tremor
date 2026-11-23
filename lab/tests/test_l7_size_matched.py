from copy import deepcopy
import unittest
from unittest.mock import patch

from lab import l7_parallel_selection, l7_size_matched, topology


class L7SizeMatchedTests(unittest.TestCase):
    def assert_matched_activity_denominator(self, report, size):
        self.assertEqual(len(report["roster"]), size)
        self.assertEqual(len(set(report["roster"])), size)
        for key in ("flat", "parallel"):
            with self.subTest(arm=key):
                arm = report[key]
                activity = arm["activity"]
                self.assertEqual(activity["roster_count"], size)
                self.assertEqual(activity["planned_opportunities"], size * topology.ROUNDS)
                self.assertLessEqual(arm["spent"], report["budget"])
                self.assertEqual(arm["spent"] + arm["unused"], report["budget"])
                self.assertEqual(activity["observed_attempt_share"], activity["attempted_work_workers"] / size)

    def test_default_comparisons_separate_cross_team_from_within_team_dependencies(self):
        for size in (4, 8, 16, 32):
            placements = {}
            for case, parallel_utility in (("cross_subteam", 1), ("within_subteam", 3)):
                with self.subTest(size=size, case=case):
                    report = l7_size_matched.run(size, case)
                    placements[case] = report
                    self.assertIs(report["scientific_result"], False)
                    self.assertEqual(report["flat"]["utility"], 3)
                    self.assertEqual(report["parallel"]["utility"], parallel_utility)
                    self.assert_matched_activity_denominator(report, size)
                    for key in ("flat", "parallel"):
                        activity = report[key]["activity"]
                        self.assertEqual(activity["observed_opportunities"], activity["planned_opportunities"])
                        self.assertEqual(activity["full_window_attempt_share"], activity["observed_attempt_share"])
                    parallel = report["parallel"]["report"]
                    partition = [worker for members in parallel["candidate_rosters"].values() for worker in members]
                    self.assertCountEqual(partition, report["roster"])
                    self.assertEqual(parallel["accounting"]["budget"], report["budget"])
                    self.assertEqual(parallel["accounting"]["spent"], report["parallel"]["spent"])
                    self.assertEqual(len(parallel["selected"]["verified_tasks"]), parallel_utility)
            with self.subTest(size=size):
                cross, within = placements["cross_subteam"], placements["within_subteam"]
                self.assertEqual(cross["observations_sha256"], within["observations_sha256"])
                self.assertEqual(cross["flat"]["receipt"], within["flat"]["receipt"])
                self.assertNotEqual(cross["parallel"]["report"]["candidate_rosters"],
                                    within["parallel"]["report"]["candidate_rosters"])

    def test_short_cap_keeps_both_planned_denominators_and_withholds_full_window_shares(self):
        report = l7_size_matched.run(8, "cross_subteam", budget=17)
        self.assertEqual(report["budget"], 17)
        self.assert_matched_activity_denominator(report, 8)
        for key in ("flat", "parallel"):
            with self.subTest(arm=key):
                activity = report[key]["activity"]
                self.assertLess(activity["observed_opportunities"], activity["planned_opportunities"])
                self.assertIsNone(activity["full_window_attempt_share"])

    def test_partition_refuses_overlaps_omissions_and_observation_rewrites_before_execution(self):
        observations = {"a": {"answer": 7}, "b": {}, "c": {}, "d": {}}
        fixture = topology.Fixture("partition-control", {"answer": topology.Task(7)}, observations)
        rosters = {"first": ("a", "b"), "second": ("c", "d")}
        caps = {"first": 16, "second": 16}

        def compare(partition, evidence):
            return l7_parallel_selection.run(fixture, evidence, team_caps=caps, budget=35,
                                             candidate_rosters=partition)

        def split(partition):
            return {candidate: {worker: deepcopy(observations[worker]) for worker in workers}
                    for candidate, workers in partition.items()}

        original = compare(rosters, split(rosters))
        self.assertEqual(original["selected"], {"candidate_id": "first", "verified_tasks": ["answer"]})
        overlap = {"first": ("a", "b"), "second": ("b", "c", "d")}
        omission = {"first": ("a",), "second": ("c", "d")}
        rewritten = split(rosters)
        rewritten["first"]["a"]["answer"] = 9
        with patch.object(topology, "run", side_effect=AssertionError("invalid partition executed")):
            for partition, evidence in ((overlap, split(overlap)), (omission, split(omission)),
                                        (rosters, rewritten)):
                with self.subTest(partition=partition, evidence=evidence), self.assertRaises(ValueError):
                    compare(partition, evidence)

    def test_unsupported_size_and_case_are_refused(self):
        for size, case in ((3, "cross_subteam"), (4, "unsupported")):
            with self.subTest(size=size, case=case), self.assertRaises(ValueError):
                l7_size_matched.run(size, case)
