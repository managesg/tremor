import json
import shutil
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lab import r1_contention_readouts as ro
from lab import r1_episode_v3 as episode


def row(r, a, t, rho, claims, distinct, c):
    return {"round": r, "realized_active_agents": a, "realized_open_tasks": t, "rho": rho,
            "claim_actions": claims, "distinct_claimed_tasks": distinct, "c": c}


class R1ContentionReadoutsTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.run = self.root / "ep"
        episode.run(self.run, case="early_error")

    def test_default_run_by_hand(self):
        # Released by round r (plan: t0,t1,t4 in 1; t2 in 2; t3 in 3). Held at start: r1 {t0}; r2 {t0,t1,t4};
        # r3 adds t2; r4 adds t3 (no board release, TTL 4 keeps all held). Claims: r1 t1 once, t4 twice.
        self.assertEqual(ro.readouts(self.run), [
            row(1, 4, 2, Fraction(2), 3, 2, Fraction(3, 2)),
            row(2, 4, 1, Fraction(4), 1, 1, Fraction(1)),
            row(3, 4, 1, Fraction(4), 1, 1, Fraction(1)),
            row(4, 4, 0, None, 0, 0, None)])

    def test_rho_is_distinct_from_scheduled_kappa(self):
        plan = json.loads((self.run / "plan.json").read_bytes())
        kappa = [Fraction(r["kappa"]) for r in plan["scheduled_contention"]["table"]]
        self.assertEqual(kappa, [Fraction(4, 3)] * 3 + [Fraction(2)])
        rho = [r["rho"] for r in ro.readouts(self.run)]
        self.assertEqual([k == p for k, p in zip(kappa, rho)], [False, False, False, False])

    def test_undefined_when_no_open_task_or_no_claim(self):
        last = ro.readouts(self.run)[3]
        self.assertIsNone(last["rho"])
        self.assertIsNone(last["c"])

    def test_stopped_run_reports_committed_rounds_only(self):
        stopped = self.root / "stopped"
        episode.run(stopped, case="late_error", stop_after_round=1)
        self.assertEqual(ro.readouts(stopped), ro.readouts(self.run)[:1])

    def test_malformed_input_raises(self):
        with self.assertRaises(ValueError):
            ro.readouts(self.root / "missing")
        for name in ("plan.json", "board.jsonl", "dispatch.json"):
            bad = self.root / ("no-" + name)
            shutil.copytree(self.run, bad)
            (bad / name).unlink()
            with self.assertRaises(ValueError, msg=name):
                ro.readouts(bad)
        tampered = self.root / "tampered"
        shutil.copytree(self.run, tampered)
        text = (tampered / "board.jsonl").read_text().replace('"a1"', '"a9"', 1)
        (tampered / "board.jsonl").write_text(text)
        with self.assertRaises(ValueError):
            ro.readouts(tampered)
        plan_bad = self.root / "plan-bad"
        shutil.copytree(self.run, plan_bad)
        plan = json.loads((plan_bad / "plan.json").read_bytes())
        plan["scheduled_contention"]["table"][0]["scheduled_open_tasks"] = 9
        (plan_bad / "plan.json").write_text(json.dumps(plan))
        with self.assertRaises(ValueError):
            ro.readouts(plan_bad)

    def test_holder_release_completes_the_task(self):
        # Review defect 1: claims were stored as the winner's name but read as a dict, so a release crashed.
        events = [
            {"type": "claim", "agent": "a0", "data": {"item": "t"}},
            {"type": "end_round", "agent": None, "round": 0,
             "data": {"expired": [], "resolved": [{"item": "t", "winner": "a0"}]}},
            {"type": "release", "agent": "a0", "data": {"item": "t", "done": True}},
            {"type": "end_round", "agent": None, "round": 1, "data": {"expired": [], "resolved": []}},
        ]
        states = ro._states(events, ["a0"], {"t"})
        self.assertEqual(states, [(frozenset({"t"}), frozenset()), (frozenset(), frozenset({"t"}))])

    def test_truncated_board_is_not_a_stopped_run(self):
        # Review defect 2: a board cut before a commit read as a shorter, stopped run.
        cut = self.root / "cut"
        shutil.copytree(self.run, cut)
        lines = (cut / "board.jsonl").read_text().splitlines(keepends=True)
        last = max(i for i, line in enumerate(lines) if json.loads(line)["type"] == "end_round")
        (cut / "board.jsonl").write_text("".join(lines[:last]))
        with self.assertRaises(ValueError):
            ro.readouts(cut)

    def test_edited_plan_and_malformed_dispatch_raise(self):
        # Review defects 3 and 4: an edited plan.json was accepted; a non-dict action raised AttributeError.
        edited = self.root / "edited"
        shutil.copytree(self.run, edited)
        plan = json.loads((edited / "plan.json").read_bytes())
        plan["extra"] = 1
        (edited / "plan.json").write_text(json.dumps(plan))
        with self.assertRaises(ValueError):
            ro.readouts(edited)
        bad = self.root / "bad-dispatch"
        shutil.copytree(self.run, bad)
        record = json.loads((bad / "dispatch.json").read_bytes())
        record["settled"][0]["action"] = "x"
        (bad / "dispatch.json").write_text(json.dumps(record))
        with self.assertRaises(ValueError):
            ro.readouts(bad)


if __name__ == "__main__":
    unittest.main()
