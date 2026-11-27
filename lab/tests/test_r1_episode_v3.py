import hashlib
import json
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from lab import r1_contention_schedule as sched
from lab import r1_episode_v2, r1_episode_v3 as episode
from tremor.board import read_log
from tremor.trapbench import alloc


def table(rows):
    return [(r["round"], r["scheduled_agents"], r["scheduled_open_tasks"], r["kappa"]) for r in rows]


class R1EpisodeV3Tests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))

    def test_v2_schedule_is_below_one_in_round_one(self):
        # v2: all six tasks open from round 1; one task completes per round for four rounds; four agents throughout.
        run = r1_episode_v2.run(self.root / "v2", case="late_error")
        taskset = json.loads((self.root / "v2" / "plan.json").read_bytes())["taskset"]
        workers = [job["agent"] for job in alloc.oracle_log(taskset)]
        self.assertEqual(run["planned_rounds"], 4)
        v2 = {"rounds": 4, "roster": [workers] * 4,
              "tasks": [{"id": t["id"], "release": 1, "complete": i + 1 if i < 4 else None}
                        for i, t in enumerate(taskset["tasks"])]}
        rows = sched.schedule(v2)
        self.assertEqual(table(rows), [(1, 4, 6, Fraction(2, 3)), (2, 4, 5, Fraction(4, 5)),
                                       (3, 4, 4, Fraction(1)), (4, 4, 3, Fraction(4, 3))])
        self.assertFalse(sched.satisfies(rows))

    def test_v3_schedule_by_hand_satisfies(self):
        taskset = alloc.gen(17)
        workers = ["a0", "a1", "a2", "a3"]
        rows = sched.schedule(episode.schedule_plan(taskset, workers))
        # open: r1 {t0,t1,t4}, r2 {t1,t2,t4}, r3 {t2,t3,t4}, r4 {t3,t4}; t5 never released
        self.assertEqual(table(rows), [(1, 4, 3, Fraction(4, 3)), (2, 4, 3, Fraction(4, 3)),
                                       (3, 4, 3, Fraction(4, 3)), (4, 4, 2, Fraction(2))])
        self.assertTrue(sched.satisfies(rows))

    def test_pin_is_deterministic_and_tracks_seed_and_rule(self):
        taskset, workers = alloc.gen(17), ["a0", "a1", "a2", "a3"]
        first = episode.pinned_schedule(17, taskset, workers)
        self.assertEqual(episode.pinned_schedule(17, taskset, workers), first)
        self.assertEqual(first["pin_meta"]["generator_sha256"],
                         hashlib.sha256(Path(episode.__file__).read_bytes()).hexdigest())
        self.assertNotEqual(episode.pinned_schedule(18, alloc.gen(18), workers)["pin_sha256"], first["pin_sha256"])
        with patch.object(episode, "RULE", "another-rule"):
            self.assertNotEqual(episode.pinned_schedule(17, taskset, workers)["pin_sha256"], first["pin_sha256"])

    def test_a_design_that_fails_contention_is_refused(self):
        with patch.object(episode, "schedule_plan", return_value={
                "rounds": 4, "roster": [["a0"]] * 4, "tasks": [{"id": "t", "release": 1, "complete": 4}]}):
            with self.assertRaises(ValueError):
                episode.pinned_schedule(17, alloc.gen(17), ["a0", "a1", "a2", "a3"])
        with self.assertRaises(ValueError):
            episode.schedule_plan(alloc.gen(17), ["a0"])

    def test_plan_carries_the_table_and_its_pin(self):
        output = self.root / "plan"
        report = episode.run(output, case="late_error")
        plan = json.loads((output / "plan.json").read_bytes())
        scheduled = plan["scheduled_contention"]
        self.assertEqual([(r["round"], r["scheduled_agents"], r["scheduled_open_tasks"], r["kappa"])
                          for r in scheduled["table"]],
                         [(1, 4, 3, "4/3"), (2, 4, 3, "4/3"), (3, 4, 3, "4/3"), (4, 4, 2, "2")])
        self.assertEqual(report["scheduled_contention_pin_sha256"], scheduled["pin_sha256"])
        self.assertEqual(scheduled["pin_sha256"], episode.pinned_schedule(
            17, plan["taskset"], ["a0", "a1", "a2", "a3"])["pin_sha256"])
        self.assertEqual(hashlib.sha256((output / "plan.json").read_bytes()).hexdigest(), report["plan_sha256"])

    def test_commits_named_reads_staggered_claims_and_round_one_collision(self):
        output = self.root / "complete"
        report = episode.run(output, case="late_error")
        main = read_log(output / "board.jsonl")
        delivery = read_log(output / "delivery.jsonl")
        for trace in (main, delivery):
            self.assertEqual([row["round"] for row in trace if row["type"] == "end_round"], [0, 1, 2, 3, 4])
        reads = [row for row in delivery if row["type"] == "read"]
        self.assertEqual([(row["round"], row["agent"]) for row in reads], [(i + 1, f"a{i}") for i in range(4)])
        taskset = json.loads((output / "plan.json").read_bytes())["taskset"]
        ids = [t["id"] for t in taskset["tasks"]]
        claims = [(row["round"], row["agent"], ids.index(row["data"]["item"]))
                  for row in main if row["type"] == "claim"]
        self.assertEqual(sorted(claims), [(0, "a0", 0), (1, "a1", 1), (1, "a2", 4), (1, "a3", 4),
                                          (2, "a2", 2), (3, "a3", 3)])
        resolution = report["contention"]["resolution"]
        self.assertEqual((resolution["item"], resolution["claimants"], resolution["collision"]),
                         (ids[4], ["a2", "a3"], True))
        self.assertIn(resolution["winner"], ["a2", "a3"])
        commits = [row for row in main if row["type"] == "end_round" and row["round"] > 1]
        self.assertFalse(any(item["collision"] for row in commits for item in row["data"]["resolved"]))
        self.assertEqual(report["final_score"]["distinct_passing"], 3)
        self.assertTrue(report["final_score"]["valid"])

    def test_round_one_is_scored_apart(self):
        late = episode.run(self.root / "late", case="late_error")
        early = episode.run(self.root / "early", case="early_error")
        self.assertEqual(early["final_score"], late["final_score"])
        self.assertEqual((early["first_round_score"]["distinct_passing"],
                          late["first_round_score"]["distinct_passing"]), (0, 1))
        self.assertEqual(late["first_round_score"]["settled_work"], 1)

    def test_controlled_stop_and_pins(self):
        stopped = episode.run(self.root / "stop", case="late_error", stop_after_round=1)
        self.assertEqual((stopped["status"], stopped["committed_measured_rounds"], stopped["final_score"]),
                         ("incomplete_committed_prefix", 1, None))
        output = self.root / "pinned"
        report = episode.run(output, case="early_error")
        for name, key in (("plan.json", "plan_sha256"), ("dispatch.json", "dispatch_sha256"),
                          ("board.jsonl", "board_sha256"), ("delivery.jsonl", "delivery_sha256")):
            self.assertEqual(hashlib.sha256((output / name).read_bytes()).hexdigest(), report[key])
        with self.assertRaises(FileExistsError):
            episode.run(output, case="early_error")
        with self.assertRaises(ValueError):
            episode.run(self.root / "bad", case="nope")


if __name__ == "__main__":
    unittest.main()
