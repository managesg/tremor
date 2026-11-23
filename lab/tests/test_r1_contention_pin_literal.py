import json
import tempfile
import unittest
from pathlib import Path

from lab import r1_episode_v3

# Intentionally fails if the pinned generator (lab/r1_episode_v3.py) changes; see docs/reports/workplan-ep/R1-row157-contention-pin.md.
PIN = "6fa1d9e56fad0a74829e6f9de4a9f70b73118165c696e044923b0efffd69f588"
GENERATOR = "edfe7750f721aa3695ea194c0ab72e1510955ab31b2673d300b4e21b0185d236"


class ContentionPinLiteralTests(unittest.TestCase):
    def test_early_error_pin_is_frozen(self):
        with tempfile.TemporaryDirectory() as tmp:
            r1_episode_v3.run(Path(tmp) / "ep", case="early_error")
            sc = json.loads((Path(tmp) / "ep" / "plan.json").read_text())["scheduled_contention"]
        self.assertEqual(sc["pin_sha256"], PIN)
        self.assertEqual(sc["pin_meta"]["generator_sha256"], GENERATOR)


if __name__ == "__main__":
    unittest.main()
