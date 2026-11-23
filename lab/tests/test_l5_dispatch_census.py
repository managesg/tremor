import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lab import l5_dispatch_census as census, l5_grader_custody as custody


class L5DispatchCensusTests(unittest.TestCase):
    def setUp(self):
        self.scratch = Path(self.enterContext(TemporaryDirectory()))

    def fixture(self, name):
        root = self.scratch / name
        pins = census.create(root)
        return root, pins

    @staticmethod
    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    @staticmethod
    def tape(root):
        return [json.loads(line) for line in (root / "dispatch.jsonl").read_bytes().splitlines()]

    def replace_tape(self, root, rows, pins):
        path = root / "dispatch.jsonl"
        path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))
        return pins | {"dispatch_sha256": self.digest(path)}

    @staticmethod
    def renumber(rows):
        for ordinal, (attempt, result) in enumerate(zip(rows[1:-1:2], rows[2:-1:2], strict=True)):
            attempt["ordinal"] = result["ordinal"] = ordinal
            result["attempt_sha256"] = custody.digest({key: value for key, value in attempt.items() if key != "event"})

    def test_original_census_binds_each_artifact_and_accounts_for_every_attempt(self):
        root, pins = self.fixture("original")
        filenames = {"board_sha256": "board.jsonl", "dispatch_sha256": "dispatch.jsonl", "plan_sha256": "plan.json"}
        self.assertEqual(pins, {key: self.digest(root / filename) for key, filename in filenames.items()})
        report = census.verify(root, **pins)
        self.assertIs(report["scientific_n2_frozen"], False)
        self.assertEqual(report["attested_scope"], "public_synthetic_l5_dispatch")
        self.assertEqual({key: report[key] for key in ("attempts", "executed", "refused",
                                                       "executed_norm_violations", "legitimate_proposals_refused")},
                         {"attempts": 4, "executed": 3, "refused": 1,
                          "executed_norm_violations": 1, "legitimate_proposals_refused": 1})
        self.assertEqual([row["event"] for row in self.tape(root)], ["start", *(["attempt", "result"] * 4), "finish"])

    def test_changed_external_pin_is_refused_for_each_artifact(self):
        root, pins = self.fixture("wrong-pins")
        for pin in pins:
            with self.subTest(pin=pin), self.assertRaises(ValueError):
                census.verify(root, **(pins | {pin: "0" * 64}))

    def test_removed_refusal_is_rejected_even_after_repinning_dispatch(self):
        root, pins = self.fixture("missing-refusal")
        rows = self.tape(root)
        refusal, = [index for index, row in enumerate(rows)
                    if row["event"] == "result" and row["dispatch"] == "refused"]
        edited = rows[:refusal - 1] + rows[refusal + 1:]
        edited[0]["planned_attempts"] = edited[-1]["attempts"] = 3
        self.renumber(edited)
        with self.assertRaises(ValueError):
            census.verify(root, **self.replace_tape(root, edited, pins))

    def test_same_head_attempt_pairs_cannot_be_exchanged_and_repinned(self):
        root, pins = self.fixture("swapped-attempts")
        rows = self.tape(root)
        first, second, third = rows[1], rows[3], rows[5]
        self.assertEqual(first["board_head"], second["board_head"])
        self.assertEqual(second["board_head"], third["board_head"])
        self.assertEqual(first["board_events"], second["board_events"])
        self.assertEqual(second["board_events"], third["board_events"])
        edited = rows[:1] + rows[3:5] + rows[1:3] + rows[5:]
        self.renumber(edited)
        with self.assertRaises(ValueError):
            census.verify(root, **self.replace_tape(root, edited, pins))
