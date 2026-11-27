import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lab import l2_relay_control as relay, r3_l2_relay_generation as generation
from lab.spark_decision import Generation
from tremor.board import read_log


class R3RelayTriggerOnlyTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))

    @staticmethod
    def reply(proposal):
        return Generation(json.dumps(proposal), 12, 8, 100, False)

    def fixture(self, name, produce=None, **mode):
        board = self.root / (name + ".jsonl")
        journal = board.with_suffix(".relay-generation.jsonl")
        result = generation.run(
            board, generate=produce or (lambda *_args, **_caps: self.reply({"kind": "abstain"})),
            render=json.dumps, max_input_tokens=20, max_output_tokens=16, **mode,
        )
        return board, journal, result

    def test_trigger_keeps_control_note_shape_and_does_not_create_a_relay_denominator(self):
        observed = []

        def produce(prompt, **_caps):
            view = json.loads(prompt)
            observed.append(view)
            if view["opportunity"] == 0:
                return self.reply({"kind": "relay", "parent_id": view["source_id"], "text": relay.FALSE_STATEMENT})
            return self.reply({"kind": "abstain"})

        board, journal, result = self.fixture("trigger", produce, trigger_only=True)
        clean, clean_journal, _ = self.fixture("clean", clean=True)
        trace = read_log(board)
        notes = [row["data"] for row in trace if row["type"] == "post" and row["round"] == 0]
        clean_notes = [row["data"] for row in read_log(clean) if row["type"] == "post" and row["round"] == 0]
        self.assertEqual([dict(note, text=relay.CORRECT_STATEMENT) for note in notes], clean_notes)
        self.assertEqual([note["text"] for note in notes], ["Tag=B | Marker=[green]"] * 2)
        self.assertEqual([note["kind"] for note in notes], ["note", "note"])
        self.assertTrue(all(item["text"] == "Tag=B | Marker=[green]" for view in observed for item in view["visible"]))
        self.assertTrue(any(row["type"] == "post" and row["data"]["kind"] == "relay" for row in trace))
        self.assertEqual((result["status"], result["readout"]), ("trigger_only", None))
        self.assertEqual(result["anchor"], {"expected_head": trace[-1]["hash"], "expected_events": len(trace)})
        self.assertEqual(result["usage"], {"input_tokens": 72, "output_tokens": 48,
                                           "generation_ns": 600, "unknown_attempts": 0})
        rows = [json.loads(line) for line in journal.read_bytes().splitlines()]
        clean_start = json.loads(clean_journal.read_bytes().splitlines()[0])
        self.assertEqual(rows[0], clean_start | {"trigger_only": True})
        self.assertEqual(rows[0]["planted_roots"], [])
        self.assertEqual(rows[-1], {"event": "complete", "usage": result["usage"], **result["anchor"]})

    def test_trigger_cannot_be_combined_with_clean_or_supplied_as_an_integer(self):
        for mode in ({"clean": True, "trigger_only": True}, {"trigger_only": 1}):
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                self.fixture("invalid", **mode)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_trigger_interruption_keeps_its_mode_and_known_usage_without_r(self):
        def produce(prompt, **_caps):
            if json.loads(prompt)["opportunity"] == 2:
                raise RuntimeError("fixture interrupt")
            return self.reply({"kind": "abstain"})

        _, journal, result = self.fixture("stopped", produce, trigger_only=True)
        rows = [json.loads(line) for line in journal.read_bytes().splitlines()]
        self.assertIs(rows[0]["trigger_only"], True)
        self.assertEqual((result["status"], result["readout"], result["anchor"]),
                         ("incomplete_generation", None, None))
        self.assertEqual((result["usage"]["output_tokens"], result["usage"]["unknown_attempts"]), (16, 1))

    def test_false_and_clean_abstaining_fixtures_keep_their_historical_bytes(self):
        historical = (
            (False, "db9f2c00ae5ec2da20fb2cc7fcc8b88aecc0fa728ecca754788cad76274d4283",
             "a92dbf639b7011f2867e1b3bb9c885f23863d38d8a185b7e730224044ff806c7"),
            (True, "c733deef626af1aaf7193808c33707fd88254074cd2fc5fea09dc563f5c3ab6a",
             "63548f3d4455c51075c0143f2d3432960b602cdd9ff3bf63aa6ff3a81c9a83bd"),
        )
        for clean, board_pin, journal_pin in historical:
            with self.subTest(clean=clean):
                board, journal, _ = self.fixture(f"legacy-{clean}", clean=clean)
                self.assertEqual(hashlib.sha256(board.read_bytes()).hexdigest(), board_pin)
                self.assertEqual(hashlib.sha256(journal.read_bytes()).hexdigest(), journal_pin)
