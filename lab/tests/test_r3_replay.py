import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lab import l2_adoption_control, l5_carrier_fixture, r3_replay
from lab.r3_replay import replay


def inventory(line, conditions, blocks=3):
    return {"line": line, "conditions": conditions, "seed": 53,
            "blocks": [{"block_id": str(i), "stratum": "fixture"} for i in range(blocks)]}


class R3ReplayTests(unittest.TestCase):
    def setUp(self):
        self.l2 = inventory("L2", ["warning", "neutral"])

    def test_complete_replay_follows_schedule_and_resets_the_board(self):
        report = replay(self.l2)
        replayed = replay(self.l2)
        self.assertEqual(report["readouts_sha256"], replayed["readouts_sha256"])
        self.assertEqual(report["schedule_sha256"], replayed["schedule_sha256"])
        self.assertEqual((report["stop"], report["planned_arms"], report["attempted_arms"]), ("completed", 6, 6))
        self.assertEqual((report["mode"], report["cleanup_confirmed"], report["gpu_hours"]), ("scripted_cpu", True, 0))
        heads = {}
        prev_finish = 0
        for block in report["blocks"]:
            self.assertEqual([row["condition"] for row in block["observed"]], block["order"])
            for row in block["observed"]:
                condition, readout = row["condition"], row["readout"]
                self.assertEqual(heads.setdefault(condition, readout["board_head"]), readout["board_head"])
                self.assertEqual(readout["adoption_count"], {"warning": 1, "neutral": 2}[condition])
                self.assertLessEqual(prev_finish, row["start_offset_ns"])
                self.assertLessEqual(row["start_offset_ns"], row["finish_offset_ns"])
                prev_finish = row["finish_offset_ns"]
        self.assertLessEqual(prev_finish, report["observed_wall_ns"])

    def test_scripted_stop_retains_partial_rows_and_excludes_the_block(self):
        report = replay(self.l2, stop_after=3)
        self.assertEqual((report["stop"], report["attempted_arms"], report["planned_arms"]), ("scripted_stop", 3, 6))
        first, partial, last = report["blocks"]
        self.assertEqual([row["status"] for row in (first, partial, last)], ["complete", "partial", "unstarted"])
        self.assertEqual(report["complete_blocks"], [first["block_id"]])
        self.assertEqual(partial["missing"], partial["order"][1:])
        self.assertEqual(last["missing"], last["order"])

    def test_l5_replays_distinct_carrier_conditions(self):
        report = replay(inventory("L5", ["memory:clean", "memory:disrupted"], blocks=2))
        for block in report["blocks"]:
            for row in block["observed"]:
                passing = 3 if row["condition"] == "memory:clean" else 2
                self.assertEqual(row["readout"]["distinct_passing"], passing)
                self.assertEqual(row["readout"]["carrier_bytes_read"], 68)

    def test_refuses_off_schedule_conditions_and_stop_counts(self):
        with self.assertRaisesRegex(ValueError, "condition absent"):
            replay(inventory("L5", ["warning", "neutral"]))
        with self.assertRaisesRegex(ValueError, "within the schedule"):
            replay(self.l2, stop_after=7)

    def test_cli_emits_partial_evidence_and_nonzero_stop(self):
        with tempfile.TemporaryDirectory() as scratch:
            path = Path(scratch) / "inventory.json"
            path.write_text(json.dumps(self.l2))
            result = subprocess.run([sys.executable, "-B", "-m", "lab.r3_replay", str(path), "--stop-after", "1"],
                                    capture_output=True, text=True, timeout=5, check=False)
        self.assertEqual(result.returncode, 1, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual((report["stop"], report["complete_blocks"], report["attempted_arms"]),
                         ("scripted_stop", [], 1))

    def test_named_fixtures_refuse_to_reuse_existing_board_logs(self):
        with tempfile.TemporaryDirectory() as scratch:
            for index, fixture, args in ((0, l2_adoption_control.run, ("warning",)),
                                         (1, l5_carrier_fixture.run, ("memory", False))):
                path = Path(scratch) / f"arm-{index}.jsonl"
                fixture(path, *args)
                original = path.read_bytes()
                with self.assertRaises(FileExistsError):
                    fixture(path, *args)
                self.assertEqual(path.read_bytes(), original)

    def test_failed_fixture_retains_partial_output_and_cleans_scratch(self):
        original = r3_replay._run_arm
        paths = []

        def fail_third(line, path, parameters):
            paths.append(path)
            if len(paths) == 3:
                path.write_text("partial fixture bytes")
                raise RuntimeError("fixture fault")
            return original(line, path, parameters)

        with patch.object(r3_replay, "_run_arm", side_effect=fail_third):
            report = replay(self.l2)
        self.assertEqual((report["stop"], report["attempted_arms"], report["scored_arms"]),
                         ("fixture_error", 3, 2))
        first, failed, last = report["blocks"]
        self.assertEqual(report["complete_blocks"], [first["block_id"]])
        self.assertEqual([failed["status"], last["status"]], ["failed", "unstarted"])
        self.assertEqual(report["failed_arm"]["condition"], failed["order"][0])
        self.assertEqual(report["failed_arm"]["error_type"], "RuntimeError")
        self.assertTrue(report["cleanup_confirmed"])
        self.assertTrue(all(not path.parent.exists() for path in paths))
