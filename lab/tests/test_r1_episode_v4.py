import hashlib
import json
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from lab import r1_contention_schedule as sched
from lab import r1_episode_v3 as v3
from lab import r1_episode_v4 as episode
from lab import r1_read_schedule as reads
from tremor import team
from tremor.board import read_log
from tremor.trapbench import alloc

WORKERS = ["a0", "a1", "a2", "a3"]


def prefix_view(board_path, commits, root):
    """Replay the log up to and including the given number of end_round commits (setup is commit 0)."""
    kept, seen = [], -1
    for line in read_log(board_path):
        kept.append(line)
        seen += line["type"] == "end_round"
        if seen == commits and line["type"] == "end_round":
            break
    path = Path(root) / f"prefix{commits}.jsonl"
    path.write_text("".join(json.dumps(line, sort_keys=True, separators=(",", ":")) + "\n" for line in kept))
    return team.view_of(path), kept[-1]["hash"]


class R1EpisodeV4Tests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))

    def test_v3_has_no_staggered_board_reads(self):
        # v3 reads only a fixed marker (definition 1: not a board read), by one named reader per round, so it
        # schedules no per-agent lag at all; read as a lag table it would be one latest-commit read per round.
        report = v3.run(self.root / "v3", case="late_error")
        self.assertEqual([(r["reader"], r["round"]) for r in report["named_reads"]], [(f"a{i}", i + 1) for i in range(4)])
        self.assertEqual({r["item"] for r in report["named_reads"]}, {"p1"})  # the one fixed marker post
        self.assertFalse(hasattr(v3, "read_schedule"))
        self.assertNotIn("board_reads", report)

    def test_contention_equals_v3_and_satisfies(self):
        taskset = alloc.gen(17)
        plan = v3.schedule_plan(taskset, WORKERS)
        rows = sched.schedule(plan)
        self.assertEqual([(r["scheduled_agents"], r["scheduled_open_tasks"], r["kappa"]) for r in rows],
                         [(4, 3, Fraction(4, 3))] * 3 + [(4, 2, Fraction(2))])
        self.assertTrue(sched.satisfies(rows))
        pinned = episode.pinned_schedules(17, taskset, WORKERS)
        self.assertEqual(pinned["contention"]["table"], v3.pinned_schedule(17, taskset, WORKERS)["table"])
        self.assertTrue(reads.staggered(reads.lags(plan), plan["roster"]))

    def test_each_recorded_read_saw_round_minus_lag(self):
        report = episode.run(self.root / "ep", case="late_error")
        plan = json.loads((self.root / "ep" / "plan.json").read_bytes())
        lag = {(row["round"], a): v for row in plan["scheduled_reads"]["lags"] for a, v in row["lags"].items()}
        self.assertEqual(len(report["board_reads"]), 16)
        for read in report["board_reads"]:
            self.assertEqual(read["scheduled_lag"], lag[(read["round"], read["reader"])])
            self.assertEqual(read["seen_round"], read["round"] - read["scheduled_lag"])
        # by hand: round 2 lags 1,2,1,2 -> seen rounds 1,0,1,0; round 3 lags 2,1,2,1 -> 1,2,1,2; round 4 -> 3,2,3,2
        self.assertEqual([r["seen_round"] for r in report["board_reads"]],
                         [0] * 4 + [1, 0, 1, 0] + [1, 2, 1, 2] + [3, 2, 3, 2])

    def test_reads_match_the_committed_board_at_the_seen_round(self):
        report = episode.run(self.root / "ep", case="late_error")
        board = self.root / "ep" / "board.jsonl"
        for read in report["board_reads"]:
            view, commit_hash = prefix_view(board, read["seen_round"], self.root)
            self.assertEqual(read["seen_commit_hash"], commit_hash)
            self.assertEqual(read["claims"], view["claims"])
            self.assertEqual(read["items"], sorted(item["id"] for item in view["items"]))
        # not a fixed marker: setup holds only t0 (a0); the latest commit in round 4 holds all five claimed tasks
        by = {(r["round"], r["reader"]): r for r in report["board_reads"]}
        self.assertEqual(by[(2, "a1")]["claims"], {"t17t0": "a0"})
        self.assertEqual(len(by[(4, "a0")]["claims"]), 5)
        self.assertNotEqual(by[(4, "a0")]["claims"], by[(4, "a1")]["claims"])

    def test_pins_are_deterministic_and_track_the_rule(self):
        taskset = alloc.gen(17)
        first = episode.pinned_schedules(17, taskset, WORKERS)
        self.assertEqual(episode.pinned_schedules(17, taskset, WORKERS), first)
        self.assertEqual(first["reads"]["pin_meta"]["generator_sha256"],
                         hashlib.sha256(Path(episode.__file__).read_bytes()).hexdigest())
        with patch.object(episode, "READ_RULE", "another"):
            changed = episode.pinned_schedules(17, taskset, WORKERS)
        self.assertNotEqual(changed["reads"]["pin_sha256"], first["reads"]["pin_sha256"])
        self.assertEqual(changed["contention"]["pin_sha256"], first["contention"]["pin_sha256"])
        with patch.object(episode, "CONTENTION_RULE", "another"):
            self.assertNotEqual(episode.pinned_schedules(17, taskset, WORKERS)["contention"]["pin_sha256"],
                                first["contention"]["pin_sha256"])
        report = episode.run(self.root / "ep", case="late_error")
        self.assertEqual(report["scheduled_reads_pin_sha256"], first["reads"]["pin_sha256"])
        self.assertEqual(report["scheduled_contention_pin_sha256"], first["contention"]["pin_sha256"])

    def test_unstaggered_reads_are_refused(self):
        with patch.object(reads, "lags", return_value=[dict.fromkeys(WORKERS, 1)] * 4):
            with self.assertRaises(ValueError):
                episode.pinned_schedules(17, alloc.gen(17), WORKERS)

    def test_malformed_input_raises(self):
        with self.assertRaises(ValueError):
            episode.pinned_schedules(17, alloc.gen(17), ["a0"])
        for kwargs in ({"case": "nope"}, {"case": "late_error", "seed": -1}, {"case": "late_error", "stop_after_round": 5}):
            with self.assertRaises(ValueError):
                episode.run(self.root / "bad", **kwargs)

    def test_controlled_stop_keeps_only_committed_reads(self):
        report = episode.run(self.root / "stop", case="late_error", stop_after_round=1)
        self.assertEqual(report["status"], "incomplete_committed_prefix")
        self.assertEqual({r["round"] for r in report["board_reads"]}, {1})


if __name__ == "__main__":
    unittest.main()
