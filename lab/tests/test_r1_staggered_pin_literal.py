"""Literal pins for episode v4 (docs/reports/workplan-ep/R1-row157-staggered-reads-pin.md).

Intentionally fails if the pinned v4 generator, its read schedule or its contention schedule changes.
"""
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from lab import r1_episode_v4 as episode

READS_PIN = "8a11207d7f1a2cc843e5dedfbf7092ffa118641808239d93eb8460d17c71a028"
CONTENTION_PIN = "5600a4ee2c359c000376260245fab0b8c85f4650f542feef6f85ccafe09ca1e4"
GENERATOR_SHA256 = "6bca8a4deb45397fc13d02377cecc1c951fc36284dbea10e0d98be0b69eac0f4"


class StaggeredPinLiteral(unittest.TestCase):
    def test_v4_pins_match_the_frozen_values(self):
        with TemporaryDirectory() as root:
            out = Path(root) / "ep"
            episode.run(out, case="early_error")
            plan = json.loads((out / "plan.json").read_bytes())
        self.assertEqual(plan["scheduled_reads"]["pin_sha256"], READS_PIN)
        self.assertEqual(plan["scheduled_contention"]["pin_sha256"], CONTENTION_PIN)
        self.assertEqual(plan["scheduled_reads"]["pin_meta"]["generator_sha256"], GENERATOR_SHA256)


if __name__ == "__main__":
    unittest.main()
