import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lab.r1_episode_board_coupling import run
from murmuration.board import read_log
from murmuration.trapbench import alloc


class R1BoardCouplingTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))

    def test_scoring_consumes_the_same_committed_board_as_reads_and_contention(self):
        winners = set()
        for seed in range(6):
            with self.subTest(seed=seed):
                path = self.root / str(seed)
                report = run(path, case="late_error", seed=seed)
                trace = read_log(path / "board.jsonl")
                note, = [e for e in trace if e["type"] == "post" and e["data"]["kind"] == "fixture_inputs"]
                receipts = [e for e in trace if e["type"] == "post" and e["data"]["kind"] == "fixture_work_receipt"]
                self.assertEqual([e["round"] for e in receipts], [1, 2, 3, 4])
                self.assertEqual(report["contention"]["claimants"], ["a0", "a1"])
                winner = report["contention"]["winner"]
                winners.add(winner)
                self.assertEqual(receipts[1]["agent"], winner)
                self.assertEqual(json.loads(receipts[1]["data"]["text"])["task"], report["contention"]["item"])
                self.assertEqual(len({e["agent"] for e in receipts}), 4)
                source = json.loads(note["data"]["text"])
                for archived, receipt in zip(report["committed_input_reads"], receipts, strict=True):
                    result = json.loads(receipt["data"]["text"])
                    read, = [e for e in trace if e["hash"] == result["read_head"]]
                    self.assertLess(note["seq"], read["seq"])
                    self.assertLess(read["seq"], receipt["seq"])
                    self.assertEqual((read["type"], read["round"], read["agent"]),
                                     ("read", archived["round"], receipt["agent"]))
                    self.assertEqual(receipt["data"]["refs"], [note["data"]["id"]])
                    task, = [t for t in alloc.gen(seed)["tasks"] if t["id"] == result["task"]]
                    self.assertEqual(result["answer"], source[task["id"]] + int(task["check"].split()[-1]))
        self.assertEqual(winners, {"a0", "a1"})

    def test_location_of_a_wrong_committed_input_changes_only_prefix_score(self):
        early = run(self.root / "early", case="early_error")
        late = run(self.root / "late", case="late_error")
        self.assertEqual(early["final_score"]["distinct_passing"], 3)
        self.assertEqual(early["final_score"], late["final_score"])
        self.assertEqual(early["first_round_score"]["distinct_passing"], 0)
        self.assertEqual(late["first_round_score"]["distinct_passing"], 1)
        self.assertIs(late["scientific_result"], False)

    def test_controlled_stops_only_expose_scores_for_closed_boundaries(self):
        for stop in range(4):
            result = run(self.root / str(stop), case="late_error", stop_after_round=stop)
            self.assertEqual(result["status"], "incomplete_committed_prefix")
            self.assertEqual(result["unstarted_work"], 4 - stop)
            self.assertIsNone(result["final_score"])
            self.assertEqual(result["first_round_score"] is not None, stop > 0)
