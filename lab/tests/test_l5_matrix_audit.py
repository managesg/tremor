import hashlib
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest

from lab.l5_matrix import run
from lab.l5_matrix_audit import audit


class L5ArchivedMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.archive = Path(cls.enterClassContext(TemporaryDirectory())) / "archive"
        cls.report = run(cls.archive, seed=86, contended=True)
        cls.pin = hashlib.sha256((cls.archive / "summary.json").read_bytes()).hexdigest()

    def test_contention_keeps_matched_opportunities_and_captures_board_vs_dispatch(self):
        result = audit(self.archive, summary_sha256=self.pin)
        self.assertEqual((result["arms"], result["work_attempts"], result["named_reads"]), (20, 120, 96))
        for row in self.report["rows"]:
            cell = row["contention"]
            code = row["carrier"] == "code"
            self.assertEqual(cell["status"], "refused" if code else "violation_executed")
            self.assertIs(cell["resolution"]["collision"], not code)
            self.assertEqual(cell["resolution"]["winner"], "a1")

    def test_same_archive_with_wrong_external_pin_is_refused(self):
        with self.assertRaisesRegex(ValueError, "summary.json digest mismatch"):
            audit(self.archive, summary_sha256="0" * 64)

    def test_successful_named_delivery_trace_cannot_be_shortened(self):
        target = next(row for row in self.report["rows"] if row["delivery_board"] is not None)
        with TemporaryDirectory() as scratch:
            clone = Path(scratch) / "truncated"
            shutil.copytree(self.archive, clone)
            log = clone / target["arm_id"] / "delivery.jsonl"
            log.write_bytes(b"\n".join(log.read_bytes().splitlines()[:-1]) + b"\n")
            with self.assertRaisesRegex(ValueError, "delivery.jsonl terminal mismatch"):
                audit(clone, summary_sha256=self.pin)

    def test_missing_dispatch_log_cannot_stand_in_for_a_refusal(self):
        with TemporaryDirectory() as scratch:
            clone = Path(scratch) / "missing"

            def omit_outcomes(directory, entries):
                return {"log.jsonl", "log.head"} & set(entries) if Path(directory).name == "cell" else ()

            shutil.copytree(self.archive, clone, ignore=omit_outcomes)
            with self.assertRaises(ValueError):
                audit(clone, summary_sha256=self.pin)

    def test_full_cycle_recounts_every_order_position_and_directed_neighbor(self):
        with TemporaryDirectory() as scratch:
            archive = Path(scratch) / "full-cycle"
            launch = run(archive, seed=86, contended=True, full_cycle=True)
            summary_path = archive / "summary.json"
            pin = hashlib.sha256(summary_path.read_bytes()).hexdigest()
            result = audit(archive, summary_sha256=pin)
            self.assertEqual((result["arms"], result["work_attempts"], result["named_reads"]), (200, 1200, 960))
            self.assertEqual(result["complete_cycles"], {"team-4": 1, "team-8": 1})

            plan_path = archive / "plan.json"
            plan = json.loads(plan_path.read_bytes())
            counts = plan["schedule"]["strata"]["team-8"]["positions"]
            counts[plan["schedule"]["conditions"][0]][0] += 1
            plan_path.write_text(json.dumps(plan))
            launch["schedule"] = plan["schedule"]
            launch["plan_sha256"] = hashlib.sha256(plan_path.read_bytes()).hexdigest()
            summary_path.write_text(json.dumps(launch))
            bad_pin = hashlib.sha256(summary_path.read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError, "position or neighbor counts"):
                audit(archive, summary_sha256=bad_pin)
