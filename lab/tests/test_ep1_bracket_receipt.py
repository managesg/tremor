import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lab import ep1_bracket_receipt as receipt
from tremor import ep1
from tremor.trapbench import alloc, alloc2


class FakeBracketReceiptTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory())).resolve()
        self.plan = ep1.plan("ep1", 0, n_sets=1)
        taskset = alloc.gen(self.plan[0]["set"], self.plan[0]["split"])
        task_pin = hashlib.sha256(alloc.dumps(taskset).encode()).hexdigest()
        self.controls = {}
        for role, make_log in (("floor", alloc.floor_log), ("oracle", alloc.oracle_log)):
            log = make_log(taskset)
            score = alloc.score(log, taskset)
            self.controls[role] = [
                {"episode_id": f"fake-{cond}", "kind": "ep1", "batch": "ep1", "arm": cond, "cond": cond,
                 "stamp": receipt.FAKE_STAMP, "instrument_validation": True, "evidence": "fake",
                 "schedule_seed": 0, "set": self.plan[0]["set"], "taskset_sha256": task_pin, "attempt": 0,
                 "ended": "complete", "valid": True, "void": None, "log": log, "Y": score["Y"],
                 "scores": score, "scorers": {"alloc": score, "alloc2": alloc2.score(log, taskset),
                                            "disagreement": None}}
                for cond in self.plan[0]["order"]
            ]

    def write(self, role, *, terminal_stamp=receipt.FAKE_STAMP):
        directory = self.root / role / "ep1"
        directory.mkdir(parents=True, exist_ok=True)
        rows = self.controls[role]
        values = {
            "schedule.json": json.dumps({"kind": "ep1", "dry_run": True, "schedule_seed": 0, "plan": self.plan}),
            "episodes.jsonl": "".join(json.dumps(row) + "\n" for row in rows),
            "final.json": json.dumps({"kind": "ep1", "stamp": terminal_stamp, "episodes": len(rows),
                                      "aborts": 0, "voids": dict.fromkeys(ep1.BASE_CONDS, 0),
                                      "ledger": {"batch": "ep1", "stop_reason": "complete"}}),
        }
        for name, value in values.items():
            (directory / name).write_text(value, encoding="utf-8")
        return {name: hashlib.sha256(value.encode()).hexdigest() for name, value in values.items()}

    def test_exact_arms_and_scores_are_historical_only(self):
        report = receipt.audit(self.root, floor_pins=self.write("floor"), oracle_pins=self.write("oracle"))
        self.assertFalse(report["authorizes_execution"])
        self.assertIsNone(report["pilot4_clearance"])
        for role, expected in (("floor", 0.25), ("oracle", 1.0)):
            arms = report["controls"][role]["arms"]
            self.assertEqual(set(arms), set(ep1.BASE_CONDS))
            self.assertEqual({arm["Y"] for arm in arms.values()}, {expected})

    def test_repinned_duplicate_arm_is_refused(self):
        self.controls["floor"][1] = self.controls["floor"][0]
        with self.assertRaisesRegex(ValueError, "each scheduled arm"):
            receipt.audit(self.root, floor_pins=self.write("floor"), oracle_pins=self.write("oracle"))

    def test_repinned_wrong_score_fails_independent_rescoring(self):
        self.controls["oracle"][0]["log"] = []
        with self.assertRaisesRegex(ValueError, "scored result differs"):
            receipt.audit(self.root, floor_pins=self.write("floor"), oracle_pins=self.write("oracle"))

    def test_wrong_external_pin_and_nonfake_terminal_fail(self):
        floor, oracle = self.write("floor"), self.write("oracle")
        wrong = {**floor, "schedule.json": "0" * 64}
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            receipt.audit(self.root, floor_pins=wrong, oracle_pins=oracle)
        with self.assertRaisesRegex(ValueError, "zero-void fake terminal"):
            receipt.audit(self.root, floor_pins=floor, oracle_pins=self.write("oracle", terminal_stamp="LIVE"))
