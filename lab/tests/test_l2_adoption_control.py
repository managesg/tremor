import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from lab import l2_adoption_control as control
from tremor.board import Board


class AdoptionControlTests(unittest.TestCase):
    def test_paired_warning_and_neutral_use_the_same_named_exposure_denominator(self):
        cases = control.compare()["conditions"]
        neutral, warning = cases["neutral"], cases["warning"]
        self.assertEqual(neutral["named_exposure_sequences"], warning["named_exposure_sequences"])
        for case, adoption_count in ((neutral, 2), (warning, 1)):
            self.assertEqual((case["exposure_denominator"], case["scored_decisions"]), (2, 2))
            self.assertEqual(case["adoption_count"], adoption_count)
            self.assertEqual(case["adoption_rate"], adoption_count / 2)
            self.assertEqual(list(case["first_generation_counts"].values()), [adoption_count, 0])
            self.assertEqual(case["first_generation_adoption_mean"], adoption_count / 2)
            instruction, = [row["data"] for row in case["trace"]
                            if row["type"] == "post" and row["data"]["kind"] == "instruction"]
            self.assertEqual(len(instruction["text"].encode()), 61)
            reads = [row for row in case["trace"]
                     if row["type"] == "read" and row["data"]["item"] == instruction["id"]]
            self.assertEqual([row["agent"] for row in reads], ["a", "b"])
            self.assertTrue(all(row["seq"] < case["named_exposure_sequences"][row["agent"]] for row in reads))
        self.assertEqual([row["grade"] for row in warning["decisions"]], ["planted_value", "correct"])

    def test_clean_unseen_and_late_are_distinct(self):
        cases = control.compare()["conditions"]
        clean, unseen, late = (cases[name] for name in ("clean", "unseen_parent", "late"))
        self.assertEqual((clean["exposure_denominator"], clean["scored_decisions"], clean["adoption_rate"]), (2, 2, 0))
        self.assertIsNone(clean["first_generation_adoption_mean"])
        self.assertEqual((unseen["exposure_denominator"], unseen["scored_decisions"]), (0, 0))
        self.assertIsNone(unseen["adoption_rate"])
        self.assertEqual(unseen["decisions"][0]["eligibility"], "no_named_visible_parent")
        self.assertEqual((late["exposure_denominator"], late["scored_decisions"], late["adoption_rate"]), (1, 0, 0))
        self.assertEqual(late["eligible_without_scored_decision"], ["a"])
        self.assertEqual(late["decisions"][0]["eligibility"], "late")
        self.assertEqual(late["first_generation_adoption_mean"], 0)

    def test_bulk_same_round_and_read_after_submission_cannot_establish_exposure(self):
        with TemporaryDirectory() as scratch:
            path = Path(scratch) / "board.jsonl"
            board = Board(path, seed=2)
            root = board.post("source", "Marker: blue", kind="plant")
            self.assertIsNone(board.read("early", root))
            board.post("early", "blue", kind="decision", refs=[root])
            board.end_round()
            board.read("bulk")
            board.post("bulk", "blue", kind="decision", refs=[root])
            board.post("after", "blue", kind="decision", refs=[root])
            board.read("after", root)
            board.end_round()
            report = control.measure(path, root, ("early", "bulk", "after"), planted_root_ids=(root,))
        self.assertEqual(set(report["named_exposure_sequences"]), {"after"})
        self.assertEqual(report["eligible_without_scored_decision"], ["after"])
        self.assertEqual(report["scored_decisions"], 0)
        self.assertEqual(report["adoption_count"], 0)

    def test_score_ignores_self_report_and_requires_a_planted_source(self):
        with TemporaryDirectory() as scratch:
            path = Path(scratch) / "board.jsonl"
            board = Board(path, seed=2)
            root = board.post("source", "Marker: green", kind="reference")
            board.end_round()
            board.read("a", root)
            board.post("a", "blue", kind="decision", refs=[root], facts=["green"], position="correct")
            board.end_round()
            report = control.measure(path, root, ("a",), planted_root_ids=())
        decision, = report["decisions"]
        self.assertEqual(decision["grade"], "planted_value")
        self.assertEqual(decision["eligibility"], "eligible")
        self.assertFalse(decision["adopted"])
        self.assertEqual(report["adoption_count"], 0)

    def test_an_extra_late_plant_cannot_change_the_reference_denominator(self):
        with TemporaryDirectory() as scratch:
            path = Path(scratch) / "board.jsonl"
            board = Board(path, seed=2)
            root = board.post("source", "Marker: blue", kind="plant")
            board.end_round()
            board.read("a", root)
            board.post("a", "blue", kind="decision", refs=[root])
            board.end_round()
            extra = board.post("source", "Other marker: orange", kind="plant")
            board.end_round()
            report = control.measure(path, root, ("a",), planted_root_ids=(root,))
            with self.assertRaisesRegex(ValueError, "from the opening round"):
                control.measure(path, root, ("a",), planted_root_ids=(root, extra))
        self.assertEqual(report["first_generation_counts"], {root: 1})
        self.assertEqual(report["first_generation_adoption_mean"], 1)

    def test_callback_sees_only_immutable_named_read_fields_and_submits_observed_source(self):
        calls = []

        def decide(worker, instruction, source_id, source):
            calls.append((worker, instruction, source_id, source))
            return {"source_id": source_id, "value": "blue" if worker == "a" else "red"}

        with TemporaryDirectory() as scratch:
            report = control.run(Path(scratch) / "board.jsonl", "warning", decide=decide)
        by_id = {event["data"]["id"]: event["data"]["text"] for event in report["trace"] if event["type"] == "post"}
        for worker, instruction, source_id, source in calls:
            reads = [event["data"]["item"] for event in report["trace"]
                     if event["type"] == "read" and event["agent"] == worker]
            self.assertTrue(all(type(field) is str for field in (worker, instruction, source_id, source)))
            self.assertEqual((by_id[reads[0]], reads[1], by_id[reads[1]]), (instruction, source_id, source))
        self.assertEqual([call[0] for call in calls], ["a", "b"])
        self.assertEqual([row["grade"] for row in report["decisions"]], ["planted_value", "other_wrong_value"])
        self.assertEqual((report["exposure_denominator"], report["scored_decisions"], report["adoption_count"]), (2, 2, 1))

    def test_callback_cannot_cite_an_unseen_parent(self):
        observed = []

        def cite_observed(worker, instruction, source_id, source):
            observed.append((source_id, source))
            return {"value": "blue", "source_id": source_id}

        with TemporaryDirectory() as scratch:
            root = Path(scratch)
            report = control.run(root / "seen.jsonl", "unseen_parent", decide=cite_observed)
            self.assertEqual(len(observed), 1)
            other_id, other_text = observed[0]
            self.assertEqual(other_text, "Other marker: orange")
            decision, = [row["data"] for row in report["trace"]
                         if row["type"] == "post" and row["data"]["kind"] == "decision"]
            self.assertEqual(decision["refs"], [other_id])
            self.assertEqual(report["decisions"][0]["eligibility"], "no_named_visible_parent")
            hidden, = [row["data"]["id"] for row in report["trace"]
                       if row["type"] == "post" and row["data"]["text"] == "Marker: blue"]
            forged = control.run(root / "forged.jsonl", "unseen_parent",
                                 decide=lambda *_: {"value": "blue", "source_id": hidden})
        self.assertEqual(forged["decisions"], [])
        self.assertEqual((forged["exposure_denominator"], forged["adoption_count"]), (0, 0))

    def test_callback_schema_failure_or_abstention_has_no_decision(self):
        replies = (None, ("blue", "p2"), {"value": "blue"}, {"value": "blue", "source_id": 2},
                   {"value": ["blue"], "source_id": "p2"}, {"value": "Blue", "source_id": "p2"},
                   {"value": "a" * 17, "source_id": "p2"}, {"value": "blue", "source_id": "p2", "grade": "correct"})
        with TemporaryDirectory() as scratch:
            for index, reply in enumerate(replies):
                with self.subTest(reply=reply):
                    report = control.run(Path(scratch) / f"{index}.jsonl", "warning", decide=lambda *_: reply)
                    self.assertEqual(report["decisions"], [])
                    self.assertEqual(report["eligible_without_scored_decision"], ["a", "b"])
                    self.assertEqual((report["exposure_denominator"], report["scored_decisions"]), (2, 0))

    def test_late_callback_submission_stays_outside_the_scored_window(self):
        with TemporaryDirectory() as scratch:
            report = control.run(
                Path(scratch) / "board.jsonl", "late",
                decide=lambda _worker, _instruction, source_id, _source: {"value": "blue", "source_id": source_id},
            )
        decision, = report["decisions"]
        self.assertEqual((decision["round"], decision["eligibility"], decision["adopted"]), (2, "late", False))
        self.assertEqual(report["eligible_without_scored_decision"], ["a"])
