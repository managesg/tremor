import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from lab import memory_transmission
from tremor.board import Board


class MemoryTransmissionTests(unittest.TestCase):
    def test_first_generation_tracks_explicit_relays_and_zero_roots(self):
        report = memory_transmission.compare()
        self.assertEqual(report["no_relay"]["first_generation_mean"], 0)
        traced = report["relay"]
        self.assertEqual(traced["counts"], {traced["root"]: 3, traced["unread_root"]: 0})
        self.assertEqual(traced["first_generation_mean"], 1.5)
        self.assertEqual(sum(event["type"] == "post" and event["data"]["kind"] == "relay"
                             for event in traced["trace"]), 4)

    def test_relay_without_named_read_is_rejected(self):
        with TemporaryDirectory() as scratch:
            path = Path(scratch) / "board.jsonl"
            board = Board(path, seed=0)
            root = board.post("source", "indicator was green", kind="plant")
            board.end_round()
            board.read("worker")  # no record of which item the worker relied on
            board.post("worker", "indicator was green", kind="relay", refs=(root,))
            board.end_round()
            with self.assertRaisesRegex(ValueError, "named read"):
                memory_transmission.measure(path)
