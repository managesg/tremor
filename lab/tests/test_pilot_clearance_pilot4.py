import json
import os
import unittest
from pathlib import Path

import test_ep1
from lab import pilot_clearance


class Pilot4ClearanceTest(test_ep1.Base):
    """pilot_clearance on a fake pilot4 output; the batch parameter defaults to pilot3 elsewhere."""

    def run_fake(self):
        self.batch("pilot4", n_sets=6, out="p4")
        out = Path(self.d) / "p4"
        schedule = json.loads((out / "schedule.json").read_text())
        schedule["dry_run"] = False  # a fake run stamps dry_run; the clearance replays live-shaped records
        (out / "schedule.json").write_text(json.dumps(schedule))
        return out, Path(self.ldir) / "pilot4.jsonl"

    def test_pilot4_output_clears_only_as_pilot4(self):
        out, ledger = self.run_fake()
        result = pilot_clearance.audit(out, ledger, "pilot4")
        self.assertEqual(result["batch"], "pilot4")
        self.assertEqual(result["readouts"]["all_conditions"]["episodes"], 30)
        with self.assertRaises(ValueError):
            pilot_clearance.audit(out, ledger)  # default batch pilot3 refuses pilot4 records

    def test_main_accepts_batch_option(self):
        out, ledger = self.run_fake()
        with self.assertRaises(SystemExit) as cm:
            pilot_clearance.main([str(out), str(ledger)])
        self.assertEqual(cm.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
