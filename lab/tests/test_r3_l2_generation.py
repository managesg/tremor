import json
import tempfile
import unittest
from pathlib import Path

from lab.r3_l2_generation import run
from lab.spark_decision import Generation


def render(worker, instruction, source_id, source_text):
    return json.dumps(dict(worker=worker, instruction=instruction, source_id=source_id, source_text=source_text))


class L2GenerationTests(unittest.TestCase):
    def run_arm(self, condition, generate, *, accept_at_limit=True):
        with tempfile.TemporaryDirectory() as scratch:
            return run(Path(scratch) / "board.jsonl", condition, generate=generate, render=render,
                       max_input_tokens=40, max_output_tokens=10, accept_at_limit=accept_at_limit)

    def test_uses_only_observed_input_and_independent_adoption_scoring(self):
        seen = []

        def generate(prompt, **caps):
            observed = json.loads(prompt)
            seen.append(observed)
            self.assertEqual(caps, {"max_input_tokens": 40, "max_output_tokens": 10})
            value = "blue" if observed["worker"] == "a" else "green"
            return Generation(json.dumps(dict(value=value, source_id=observed["source_id"])), 18, 9, 100, False)

        report = self.run_arm("warning", generate)
        self.assertEqual((report["input_tokens"], report["output_tokens"]), (36, 18))
        self.assertEqual((report["readout"]["scored_decisions"], report["readout"]["adoption_count"]), (2, 1))
        self.assertEqual([row["source_text"] for row in seen], ["Marker: blue"] * 2)
        self.assertTrue(all(set(row) == {"worker", "instruction", "source_id", "source_text"} for row in seen))

    def test_duplicate_keys_and_forged_source_leave_metered_unscored_turns(self):
        def generate(prompt, **caps):
            worker = json.loads(prompt)["worker"]
            text = ('{"value":"blue","value":"green","source_id":"invented"}' if worker == "a"
                    else '{"value":"blue","source_id":"unobserved"}')
            return Generation(text, 18, 10, 100, True)

        report = self.run_arm("neutral", generate)
        self.assertEqual((report["input_tokens"], report["output_tokens"]), (36, 20))
        self.assertEqual([row["json_object"] for row in report["generation_turns"]], [False, True])
        self.assertEqual((report["readout"]["scored_decisions"], report["readout"]["adoption_count"]), (0, 0))
        self.assertEqual(report["readout"]["eligible_without_scored_decision"], ["a", "b"])

    def test_unseen_parent_is_never_supplied_in_the_rendering(self):
        def generate(prompt, **caps):
            observed = json.loads(prompt)
            self.assertEqual(observed["source_text"], "Other marker: orange")
            return Generation(json.dumps(dict(value="blue", source_id=observed["source_id"])), 18, 9, 100, False)

        report = self.run_arm("unseen_parent", generate)
        self.assertEqual(report["readout"]["exposure_denominator"], 0)
        self.assertEqual(report["readout"]["scored_decisions"], 0)
        self.assertIsNone(report["readout"]["adoption_rate"])

    def test_at_limit_rule_changes_scoring_without_discarding_cost(self):
        def generate(prompt, **caps):
            observed = json.loads(prompt)
            return Generation(json.dumps(dict(value="blue", source_id=observed["source_id"])), 18, 10, 100, True)

        allowed = self.run_arm("neutral", generate, accept_at_limit=True)
        held = self.run_arm("neutral", generate, accept_at_limit=False)
        self.assertEqual((allowed["output_tokens"], held["output_tokens"]), (20, 20))
        self.assertEqual((allowed["readout"]["scored_decisions"], held["readout"]["scored_decisions"]), (2, 0))
        self.assertTrue(all(row["held_at_limit"] for row in held["generation_turns"]))

    def test_generation_failure_keeps_prior_receipt_and_failed_attempt(self):
        def generate(prompt, **caps):
            observed = json.loads(prompt)
            if observed["worker"] == "b":
                raise RuntimeError("synthetic generation failure")
            return Generation(json.dumps(dict(value="blue", source_id=observed["source_id"])), 18, 9, 100, False)

        with tempfile.TemporaryDirectory() as directory:
            board = Path(directory) / "board.jsonl"
            with self.assertRaisesRegex(RuntimeError, "synthetic generation failure"):
                run(board, "neutral", generate=generate, render=render, max_input_tokens=40,
                    max_output_tokens=10, accept_at_limit=True)
            rows = [json.loads(line) for line in board.with_suffix(".generation.jsonl").read_text().splitlines()]
        self.assertEqual([row["event"] for row in rows], ["arm_start", "start", "completed", "start", "failed"])
        self.assertEqual(rows[0], {"event": "arm_start", "condition": "neutral", "accept_at_limit": True,
                                   "max_input_tokens": 40, "max_output_tokens": 10})
        self.assertEqual((rows[2]["worker"], rows[2]["output_tokens"]), ("a", 9))
        self.assertEqual((rows[-1]["worker"], rows[-1]["error_type"], rows[-1]["usage"]), ("b", "RuntimeError", None))

    def test_matched_reference_access_is_explicit_and_metered_in_both_arms(self):
        reference_text = "Paper ledger marker: green"

        def renderer(worker, instruction, source_id, source_text, *, verification):
            return json.dumps({"worker": worker, "instruction": instruction, "source_id": source_id,
                               "source_text": source_text, "verification": verification})

        with tempfile.TemporaryDirectory() as directory:
            initial_prompts = []
            for condition in ("warning", "neutral"):
                with self.subTest(condition=condition):
                    def generate(prompt, **caps):
                        observed = json.loads(prompt)
                        reference = observed["verification"]
                        if reference is None:
                            self.assertNotIn(reference_text, prompt)
                            initial_prompts.append(observed)
                            body = ({"action": "verify"} if observed["worker"] == "a"
                                    else {"source_id": observed["source_id"], "value": "blue"})
                        else:
                            self.assertEqual(reference["text"], reference_text)
                            body = {"source_id": observed["source_id"], "value": "green"}
                        return Generation(json.dumps(body), 18, 8, 100, False)

                    board = Path(directory) / f"{condition}.jsonl"
                    report = run(board, condition, generate=generate, render=renderer, max_input_tokens=40,
                                 max_output_tokens=10, accept_at_limit=False, reference_text=reference_text)
                    self.assertEqual((report["input_tokens"], report["output_tokens"], report["verification_reads"]),
                                     (54, 24, 1))
                    self.assertEqual((report["readout"]["scored_decisions"], report["readout"]["adoption_count"]), (2, 1))
                    trace = report["readout"]["trace"]
                    reference, = [row for row in trace if row["type"] == "post" and row["data"]["kind"] == "verification"]
                    read, = [row for row in trace if row["type"] == "read" and row["data"]["item"] == reference["data"]["id"]]
                    self.assertEqual((read["agent"], read["data"]["n"]), ("a", 1))
                    journal = [json.loads(row) for row in board.with_suffix(".generation.jsonl").read_text().splitlines()]
                    lookup, = [row for row in journal if row["event"] == "reference_read"]
                    self.assertEqual(lookup["reference_sha256"], journal[0]["reference_sha256"])
                    self.assertEqual(lookup["reference_id"], read["data"]["item"])
                    self.assertEqual(report["verification_read_ns"], lookup["reference_read_ns"])
                    self.assertGreaterEqual(report["verification_read_ns"], 0)
                    self.assertEqual([row["stage"] for row in report["generation_turns"]],
                                     ["initial", "after_verification", "initial"])
        self.assertEqual(len(initial_prompts), 4)
        for warning, neutral in zip(initial_prompts[:2], initial_prompts[2:], strict=True):
            self.assertNotEqual(warning.pop("instruction"), neutral.pop("instruction"))
            self.assertEqual(warning, neutral)

    def test_repeat_verify_request_does_not_create_another_lookup(self):
        def renderer(worker, instruction, source_id, source_text, *, verification):
            return "synthetic verification turn"

        def generate(prompt, **caps):
            return Generation('{"action":"verify"}', 18, 8, 100, False)

        with tempfile.TemporaryDirectory() as directory:
            report = run(Path(directory) / "board.jsonl", "warning", generate=generate, render=renderer,
                         max_input_tokens=40, max_output_tokens=10, accept_at_limit=False, reference_text="ledger")
        self.assertEqual(report["verification_reads"], 2)
        self.assertEqual(len(report["generation_turns"]), 4)
        self.assertEqual(report["readout"]["scored_decisions"], 0)

    def test_forged_usage_or_limit_flag_cannot_reach_scoring(self):
        for input_count, output_count, at_limit in ((41, 8, False), (18, 11, False), (18, 8, True)):
            with self.subTest(input_count=input_count, output_count=output_count, at_limit=at_limit):
                def generate(prompt, **caps):
                    observed = json.loads(prompt)
                    body = {"value": "blue", "source_id": observed["source_id"]}
                    return Generation(json.dumps(body), input_count, output_count, 100, at_limit)

                with tempfile.TemporaryDirectory() as directory:
                    board = Path(directory) / "board.jsonl"
                    with self.assertRaisesRegex(ValueError, "generation"):
                        run(board, "neutral", generate=generate, render=render, max_input_tokens=40,
                            max_output_tokens=10, accept_at_limit=True)
                    journal = [json.loads(row) for row in board.with_suffix(".generation.jsonl").read_text().splitlines()]
                self.assertEqual([row["event"] for row in journal], ["arm_start", "start", "failed"])
                self.assertIsNone(journal[-1]["usage"])
