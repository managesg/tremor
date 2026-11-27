import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from lab import r1_episode_v2 as episode
from tremor.board import read_log
from tremor.trapbench import alloc, alloc2


class R1EpisodeV2Tests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))

    def test_commits_actual_named_reads_in_distinct_rounds_and_two_claimants(self):
        output = self.root / "complete"
        report = episode.run(output, case="late_error")
        main = read_log(output / "board.jsonl")
        delivery = read_log(output / "delivery.jsonl")
        for trace in (main, delivery):
            self.assertEqual([row["round"] for row in trace if row["type"] == "end_round"], [0, 1, 2, 3, 4])
        marker, = [row for row in delivery if row["type"] == "post"]
        reads = [row for row in delivery if row["type"] == "read"]
        self.assertEqual([(row["round"], row["agent"], row["data"]) for row in reads],
                         [(index + 1, f"a{index}", {"item": marker["data"]["id"], "n": 1}) for index in range(4)])
        contention = report["contention"]
        commit = main[contention["commit_seq"]]
        resolution = contention["resolution"]
        claims = [row["agent"] for row in main if row["round"] == 1 and row["type"] == "claim"
                  and row["data"]["item"] == resolution["item"]]
        self.assertEqual(claims, ["a1", "a2"])
        self.assertIn(resolution, commit["data"]["resolved"])
        self.assertTrue(resolution["collision"])
        self.assertEqual(resolution["claimants"], claims)
        self.assertIn(resolution["winner"], claims)

    def test_first_round_score_distinguishes_equal_terminal_scores(self):
        late_dir = self.root / "late"
        with patch.object(alloc2, "second_scorer_gate", wraps=alloc2.second_scorer_gate) as scored:
            late = episode.run(late_dir, case="late_error")
        early = episode.run(self.root / "early", case="early_error")
        self.assertEqual([len(call.args[0]) for call in scored.call_args_list], [1, 4])
        self.assertEqual(early["final_score"], late["final_score"])
        self.assertEqual(early["final_score"]["distinct_passing"], 3)
        self.assertEqual((early["first_round_score"]["distinct_passing"],
                          late["first_round_score"]["distinct_passing"]), (0, 1))
        prefix = late["first_round_score"]
        self.assertEqual((prefix["scheduled_work"], prefix["settled_work"]), (1, 1))
        trace = read_log(late_dir / "board.jsonl")
        self.assertEqual(prefix["board_head"], trace[prefix["board_event_count"] - 1]["hash"])
        self.assertEqual(trace[prefix["board_event_count"] - 1]["round"], 1)
        dispatch = json.loads((late_dir / "dispatch.json").read_bytes())
        first, = [entry for entry in dispatch["settled"] if entry["round"] == 1 and entry["action"]["type"] == "work"]
        action = first["action"]
        row = {key: value for key, value in action.items() if key != "type"} | {"action": "work", "rejected": False}
        taskset = json.loads((late_dir / "plan.json").read_bytes())["taskset"]
        self.assertEqual(alloc.score([row], taskset)["distinct_passing"], prefix["distinct_passing"])
        self.assertEqual(alloc2.score([row], taskset)["distinct_passing"], prefix["distinct_passing"])

    def test_controlled_stops_preserve_only_closed_scores(self):
        first = episode.run(self.root / "after-one", case="late_error", stop_after_round=1)
        setup = episode.run(self.root / "after-setup", case="late_error", stop_after_round=0)
        for report, committed in ((first, 1), (setup, 0)):
            self.assertEqual(report["status"], "incomplete_committed_prefix")
            self.assertEqual(report["committed_measured_rounds"], committed)
            self.assertEqual(report["unstarted_work"], 4 - committed)
            self.assertIsNone(report["final_score"])
        self.assertEqual(first["first_round_score"]["distinct_passing"], 1)
        self.assertIsNone(setup["first_round_score"])

    def test_artifact_pins_and_refusal_to_overwrite(self):
        output = self.root / "pinned"
        report = episode.run(output, case="early_error")
        for name, key in (("plan.json", "plan_sha256"), ("dispatch.json", "dispatch_sha256"),
                          ("board.jsonl", "board_sha256"), ("delivery.jsonl", "delivery_sha256")):
            self.assertEqual(hashlib.sha256((output / name).read_bytes()).hexdigest(), report[key])
        self.assertEqual(json.loads((output / "summary.json").read_bytes()), report)
        with self.assertRaises(FileExistsError):
            episode.run(output, case="early_error")

    def test_abrupt_loss_before_work_return_has_no_scored_summary(self):
        output = self.root / "interrupted"
        actual_act = episode.router.act

        def interrupt(action, handle, *, enforced):
            if action["type"] == "work":
                raise RuntimeError("scripted loss before return")
            return actual_act(action, handle, enforced=enforced)

        with patch.object(episode.router, "act", side_effect=interrupt), self.assertRaises(RuntimeError):
            episode.run(output, case="late_error")
        self.assertTrue((output / "plan.json").is_file())
        self.assertFalse((output / "summary.json").exists())
