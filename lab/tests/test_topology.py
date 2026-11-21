import unittest

from lab import topology


class TopologyTests(unittest.TestCase):
    def test_assignment_and_evidence_access_are_crossed(self):
        expected = {"complementary": (2, 3), "redundant": (3, 3), "sequential": (1, 3)}
        for fixture in topology.compare(cross_evidence=True)["comparisons"]:
            cells = {(arm["mode"], arm["evidence_access"]): arm for arm in fixture["arms"]}
            self.assertEqual(set(cells), {(mode, access) for mode in topology.MODES
                                         for access in topology.EVIDENCE_ACCESS})
            own, shared = expected[fixture["fixture"]]
            for mode in topology.MODES:
                with self.subTest(fixture=fixture["fixture"], mode=mode):
                    low, high = cells[mode, "own"], cells[mode, "shared"]
                    self.assertEqual((low["utility"], high["utility"]), (own, shared))
                    self.assertEqual(high["gain_over_own_evidence_at_same_mode"], shared - own)
                    for cell in (low, high):
                        self.assertEqual(cell["gain_over_self_assignment_at_same_access"], 0)
                        self.assertEqual(cell["budget"], cell["spent"] + cell["unused"])

    def test_shared_evidence_does_not_grant_assignment_authority(self):
        arm = topology.run(topology.FIXTURES[2], "independent", evidence_access="shared")
        self.assertEqual(arm["verified_union"], ["final", "middle", "root"])
        self.assertFalse(any(event["kind"] in ("assign", "claim", "plan", "handoff")
                             for event in arm["trace"]))
        middle = next(event for event in arm["trace"] if event["kind"] == "work" and event["task"] == "middle")
        root_verdict = arm["trace"][middle["inputs"][0]]
        self.assertEqual(arm["trace"][root_verdict["submission"]]["actor"], "a")
        self.assertEqual(middle["actor"], "b")

    def test_matched_fixtures_and_independent_union(self):
        comparisons = topology.compare()["comparisons"]
        expected = {
            "complementary": (2, 3, 3, 3),
            "redundant": (3, 3, 3, 3),
            "sequential": (1, 3, 3, 3),
        }
        for fixture in comparisons:
            with self.subTest(fixture=fixture["fixture"]):
                arms = fixture["arms"]
                self.assertEqual(tuple(arm["mode"] for arm in arms), topology.MODES)
                self.assertEqual(tuple(arm["utility"] for arm in arms), expected[fixture["fixture"]])
                for arm in arms:
                    self.assertEqual(arm["gain_over_independent"], arm["utility"] - arms[0]["utility"])
                    self.assertEqual(arm["budget"], topology.BUDGET)
                    self.assertEqual(arm["budget"], arm["spent"] + arm["unused"])
                    self.assertEqual(arm["spent"], sum(event["cost"] for event in arm["trace"]))
                    self.assertFalse(arm["budget_stopped"])
        redundant = comparisons[1]["arms"]
        self.assertEqual([arm["duplicate_work"] for arm in redundant], [1, 0, 0, 0])
        self.assertEqual(redundant[0]["verified_union"], ["backup", "common", "separate"])
        conflicts = [event for event in redundant[3]["trace"] if event["kind"] == "claim_conflict"]
        self.assertEqual([(event["task"], event["actor"], event["holder"], event["cost"])
                          for event in conflicts], [("common", "b", "a", 1)])

    def test_authority_and_dependencies_appear_in_trace(self):
        arms = topology.compare()["comparisons"][2]["arms"]
        independent, fixed, rotating, peers = [arm["trace"] for arm in arms]
        for trace in (independent, fixed, rotating, peers):
            self.assertTrue(any(event["kind"] == "blocked" for event in trace))
        self.assertFalse(any(event["kind"] in ("assign", "claim") for event in independent))
        self.assertEqual({event["actor"] for event in fixed if event["kind"] == "assign"}, {"a"})
        self.assertEqual([(event["actor"], event["recipient"]) for event in rotating
                          if event["kind"] == "handoff"], [("a", "b"), ("b", "c")])
        self.assertEqual({event["actor"] for event in rotating if event["kind"] == "assign"}, {"a", "b", "c"})
        self.assertTrue(all(event["actor"] == event["worker"] for event in peers if event["kind"] == "claim"))
        self.assertFalse(any(event["kind"] == "plan" for event in peers))

    def test_verifier_checks_correctness_and_dependency_provenance(self):
        fixture = topology.FIXTURES[2]
        evidence = [dict(event=4, round=0, worker="a", task="root", answer=2)]
        work = dict(round=1, actor="b", task="middle", answer=5, inputs=[4])
        self.assertTrue(topology._valid_work(fixture, evidence, "peers", work))
        self.assertFalse(topology._valid_work(fixture, evidence, "independent", work))
        self.assertFalse(topology._valid_work(fixture, evidence, "peers", dict(work, round=0)))
        self.assertFalse(topology._valid_work(fixture, evidence, "peers", dict(work, answer=7)))
        self.assertFalse(topology._valid_work(fixture, evidence, "peers", dict(work, inputs=[9])))

    def test_budget_stops_without_unverified_work(self):
        for mode in topology.MODES:
            for budget in range(1, topology.BUDGET):
                with self.subTest(mode=mode, budget=budget):
                    arm = topology.run(topology.FIXTURES[0], mode, budget)
                    trace = arm["trace"]
                    self.assertEqual(trace[-1]["kind"], "merge")
                    self.assertLessEqual(arm["spent"], budget)
                    self.assertEqual(
                        [event["event"] for event in trace if event["kind"] == "work"],
                        [event["submission"] for event in trace if event["kind"] == "verify"],
                    )

    def test_budget_requires_positive_integer(self):
        for budget in (0, -1, float("nan"), float("inf"), 3.5, True):
            with self.subTest(budget=budget), self.assertRaises(ValueError):
                topology.run(topology.FIXTURES[0], "independent", budget)
