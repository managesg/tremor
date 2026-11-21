from dataclasses import replace
from fractions import Fraction
import unittest
from unittest.mock import Mock

from lab import topology
from lab.quantum.topology_transfer import adapt, compare
from lab.quantum.transfer_fixtures import Fixture, Stage, development_fixture


class TopologyTransferTests(unittest.TestCase):
    def test_crossed_comparison_counts_stages_and_preserves_fixed_worker_order(self):
        cases = compare()["cases"]
        self.assertEqual(len(cases), 4)
        for case, expected in zip(cases, ((0, 1), (0, 1), (2, 2), (1, 3)), strict=True):
            arms = {(a["mode"], a["evidence_access"]): a for a in case["arms"]}
            self.assertEqual(len(arms), 8)
            for (mode, access), arm in arms.items():
                self.assertEqual(arm["stage_utility"], expected[access == "shared"])
                self.assertEqual(arm["gain_over_independent_union"], expected[access == "shared"] - expected[0])
                self.assertEqual(arm["gain_over_independent_at_same_access"], 0)
                self.assertEqual(arm["spent"], sum(row["cost"] for row in arm["trace"]))
                self.assertLessEqual(arm["spent"], 32)
                for round_id in range(topology.ROUNDS):
                    reads = [row["actor"] for row in arm["trace"] if row["kind"] == "read" and row["round"] == round_id]
                    self.assertEqual(reads, list(topology.WORKERS))
                self.assertFalse(any(name.startswith("shard/") for name in arm["verified_stage_union"]))

    def test_complementary_correct_answer_needs_visible_authentic_earlier_shards(self):
        fixture, protocol = adapt(development_fixture("complementary", 9))
        self.assertNotIn("marked_indices", fixture.observations["c"]["join"])
        run = topology.run(fixture, "independent", evidence_access="shared", work_protocol=protocol)
        work = next(row for row in run["trace"] if row["kind"] == "work" and row["task"] == "join")
        self.assertEqual(work["answer"], [1, "1"])
        receipts = []
        for event in work["inputs"]:
            verdict = run["trace"][event]
            proposal = run["trace"][verdict["submission"]]
            receipts.append(dict(event=event, worker=proposal["actor"], task=proposal["task"],
                                 round=verdict["round"], answer=proposal["answer"]))

        def accepted(records, submission=work, access="shared"):
            return topology._valid_work(fixture, records, "independent", submission,
                                        evidence_access=access, work_protocol=protocol)

        self.assertTrue(accepted(receipts))
        self.assertFalse(accepted(receipts, access="own"))
        self.assertFalse(accepted(receipts[:-1]))
        self.assertFalse(accepted(receipts, {**work, "inputs": list(reversed(work["inputs"]))}))
        self.assertFalse(accepted([dict(row, round=work["round"]) for row in receipts]))
        self.assertFalse(accepted([dict(receipts[0], answer=[99]), receipts[1]]))
        self.assertFalse(protocol.verify(work, {}))

    def test_partial_mark_sources_can_publish_and_solve_in_separate_roles(self):
        for solvers in (("a", "b"), ("a", "c")):
            with self.subTest(solvers=solvers):
                stage = Stage("join", 3, 1, Fraction(1), (("a", (0,)), ("b", (1,))), solvers)
                fixture, protocol = adapt(Fixture("complementary", (stage,)))
                self.assertEqual(fixture.observations["a"]["shard/join/a"]["marked_indices"], [0])
                self.assertNotIn("marked_indices", fixture.observations["a"]["join"])
                self.assertNotIn("shard/join/b", fixture.observations["a"])
                for solver in solvers:
                    self.assertEqual(fixture.observations[solver]["join"]["mark_sources"], ["a", "b"])

                shared = topology.run(fixture, "independent", evidence_access="shared", work_protocol=protocol)
                own = topology.run(fixture, "independent", evidence_access="own", work_protocol=protocol)
                self.assertEqual(shared["verified_union"], ["join", "shard/join/a", "shard/join/b"])
                self.assertEqual(own["verified_union"], ["shard/join/a", "shard/join/b"])
                work = next(event for event in shared["trace"] if event.get("task") == "join"
                            and event["kind"] == "work")
                self.assertEqual(work["answer"], [1, "1"])
                self.assertEqual(len(work["inputs"]), 2)

    def test_complete_redundant_mark_sources_keep_direct_questions(self):
        stage = Stage("join", 3, 1, Fraction(1), (("a", (0, 1)), ("b", (1, 0))), ("a", "b"))
        fixture, protocol = adapt(Fixture("redundant", (stage,)))
        self.assertEqual(set(fixture.tasks), {"join"})
        self.assertEqual(fixture.observations["a"]["join"]["marked_indices"], [0, 1])
        self.assertNotIn("mark_sources", fixture.observations["a"]["join"])
        result = topology.run(fixture, "independent", evidence_access="own", work_protocol=protocol)
        self.assertEqual(result["verified_union"], ["join"])

    def test_sequential_verified_no_hit_releases_fallback(self):
        fixture, protocol = adapt(development_fixture("sequential", 0))
        result = topology.run(fixture, "independent", evidence_access="shared", work_protocol=protocol)
        work = {row["task"]: row for row in result["trace"] if row["kind"] == "work"}
        self.assertEqual(work["scout"]["answer"], [2, "121/128"])
        self.assertIsNone(work["confirm"]["answer"])
        self.assertEqual(work["final"]["answer"], [2, "121/128"])
        self.assertEqual(result["trace"][work["final"]["inputs"][0]]["submission"], work["confirm"]["event"])

    def test_duplicate_work_is_metered_and_stage_is_deduplicated(self):
        fixture, protocol = adapt(development_fixture("redundant", 0))
        result = topology.run(fixture, "independent", evidence_access="own", work_protocol=protocol)
        common = [row for row in result["trace"] if row["kind"] == "work" and row["task"] == "common"]
        self.assertGreaterEqual(len(common), 2)
        self.assertEqual(result["verified_union"].count("common"), 1)
        verdicts = [row for row in result["trace"] if row.get("submission") in {work["event"] for work in common}]
        self.assertEqual(len(verdicts), len(common))
        self.assertTrue(all(row["accepted"] and row["cost"] == 1 for row in verdicts))

    def test_budget_stop_does_not_invoke_unmetered_solver(self):
        fixture, protocol = adapt(development_fixture("redundant", 0))
        guarded = replace(protocol, propose=Mock(side_effect=AssertionError("unmetered solve")))
        result = topology.run(fixture, "independent", budget=3, work_protocol=guarded)
        self.assertTrue(result["budget_stopped"])
        self.assertEqual(result["spent"], 2)
        guarded.propose.assert_not_called()
