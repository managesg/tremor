import json
from pathlib import Path
import shutil
import tempfile
import unittest

from lab import pilot_clearance
from tremor import ep1


ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / "runs" / "ep1-live" / "pilot3"
LEDGER = ROOT / "runs" / "spend" / "pilot3.jsonl"


class MissingEvidenceTest(unittest.TestCase):
    def test_absent_archive_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            with self.assertRaises(FileNotFoundError):
                pilot_clearance.audit(path, path / "pilot3.jsonl")

    def test_empty_records_fail_against_a_full_schedule(self):
        schedule = {"kind": "pilot3", "dry_run": False, "schedule_seed": 0, "plan": ep1.plan("pilot3", 0)}
        with self.assertRaisesRegex(ValueError, "complete scheduled cells"):
            pilot_clearance._validate_episodes(schedule, [])


@unittest.skipUnless((ARCHIVE / "episodes.jsonl").exists() and LEDGER.exists(),
                     "the local historical Pilot 3 archive is required")
class HistoricalReplayTest(unittest.TestCase):
    def test_historical_readout_and_clearance(self):
        audit = pilot_clearance.audit(ARCHIVE, LEDGER)
        self.assertEqual(audit["clearance"], "failed")
        self.assertEqual(tuple(audit["criteria"].values()),
                         ("pass", "fail", "pass", "pass", "pass", "unavailable", "unavailable"))
        self.assertEqual(audit["order_rule"]["picked"], "shared")
        self.assertEqual(audit["local_ledger"], {
            "calls": 240, "tokens": 126665, "usd": "0.0182501", "transport_aborts": 0,
            "voided_episodes": 0, "reservations": 240, "charges": 240,
        })
        readouts = audit["readouts"]
        all_rows = readouts["all_conditions"]
        self.assertEqual((all_rows["max_output_tokens"], all_rows["over_150"], all_rows["end_turn"]), (263, 25, 240))
        core = readouts["core"]
        self.assertEqual((core["max_output_tokens"], core["over_150"], core["stop_max_tokens"]), (263, 13, 0))
        self.assertEqual(core["over_150_by_round"], {"0": 0, "1": 13})
        self.assertEqual((core["admitted_work"], core["wrong_admitted_work"]), (65, 0))
        self.assertEqual(readouts["per_order"]["shared"]["core"]["over_150"], 9)
        self.assertEqual(readouts["per_order"]["per_agent"]["core"]["over_150"], 4)

    def test_wrong_schedule_cannot_reach_the_clearance_readout(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            shutil.copytree(ARCHIVE, path, dirs_exist_ok=True)
            schedule_path = path / "schedule.json"
            schedule = json.loads(schedule_path.read_text())
            schedule["plan"].pop()
            schedule_path.write_text(json.dumps(schedule))
            with self.assertRaisesRegex(ValueError, "differs from the Pilot 3 design"):
                pilot_clearance.audit(path, LEDGER)

    def test_missing_episode_cannot_reach_the_clearance_readout(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            shutil.copytree(ARCHIVE, path, dirs_exist_ok=True)
            episodes = path / "episodes.jsonl"
            episodes.write_text("\n".join(episodes.read_text().splitlines()[:-1]) + "\n")
            with self.assertRaisesRegex(ValueError, "complete scheduled cells"):
                pilot_clearance.audit(path, LEDGER)

    def test_mismatched_ledger_cannot_reach_the_clearance_readout(self):
        with tempfile.TemporaryDirectory() as temp:
            altered = Path(temp) / "pilot3.jsonl"
            lines = LEDGER.read_text().splitlines()
            first_charge = json.loads(lines[2])
            first_charge["usage"]["output_tokens"] -= 1
            lines[2] = json.dumps(first_charge)
            altered.write_text("\n".join(lines) + "\n")
            with self.assertRaisesRegex(ValueError, "ledger disagrees with recorded call"):
                pilot_clearance.audit(ARCHIVE, altered)

    def test_modified_reply_or_empty_block_manifest_fails_closed(self):
        for changes, reason in (({"reply": "altered reply"}, "ledger disagrees"),
                                ({"block_types": []}, "incomplete or unexpected call record"),
                                ({"returned_model": "unrecorded"}, "ledger disagrees")):
            with self.subTest(changes=changes), tempfile.TemporaryDirectory() as temp:
                path = Path(temp)
                shutil.copytree(ARCHIVE, path, dirs_exist_ok=True)
                episodes = path / "episodes.jsonl"
                lines = episodes.read_text().splitlines()
                first = json.loads(lines[0])
                first["turns"][0].update(changes)
                lines[0] = json.dumps(first)
                episodes.write_text("\n".join(lines) + "\n")
                with self.assertRaisesRegex(ValueError, reason):
                    pilot_clearance.audit(path, LEDGER)


if __name__ == "__main__":
    unittest.main()
