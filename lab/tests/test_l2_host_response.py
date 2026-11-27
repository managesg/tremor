import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lab import l2_generation_audit, l2_host_response, r3_l2_generation, r3_schedule
from lab.spark_decision import Generation
from tremor.board import read_log


class L2HostResponseTests(unittest.TestCase):
    def fixture(self, generate, *, allow_limit=False):
        root = Path(self.enterContext(TemporaryDirectory()))
        board, responses = root / "board.jsonl", root / "host.jsonl"
        with l2_host_response.capture(responses, generate) as observed:
            r3_l2_generation.run(board, "warning", generate=observed, render=l2_generation_audit.render_scripted_prompt,
                                 max_input_tokens=50, max_output_tokens=10, accept_at_limit=allow_limit,
                                 reference_text="Paper ledger marker: green")
        return board, board.with_suffix(".generation.jsonl"), responses

    def replay(self, files):
        board, journal, responses = files
        return l2_host_response.replay(board, journal, responses, board_head=read_log(board)[-1]["hash"],
                                       journal_sha256=hashlib.sha256(journal.read_bytes()).hexdigest(),
                                       responses_sha256=hashlib.sha256(responses.read_bytes()).hexdigest())

    @staticmethod
    def generate(prompt, **_):
        observed = json.loads(prompt)
        if observed["worker"] == "a" and observed["verification"] is None:
            return Generation('{"action":"verify"}', 20, 3, 50, False)
        value = "green" if observed["verification"] is not None else "blue"
        return Generation(json.dumps({"value": value, "source_id": observed["source"]}), 20, 8, 50, False)

    def test_raw_responses_reproduce_one_adoption_and_verification_request(self):
        result = self.replay(self.fixture(self.generate))
        self.assertEqual((result["exposures"], result["adoptions"], result["replayed_decisions"]), (2, 1, 2))
        self.assertEqual((result["reference_reads"], result["output_tokens_known"]), (1, 19))

    def test_missing_raw_semantics_allowed_by_digest_only_replay_are_refused(self):
        board, journal, responses = self.fixture(self.generate)
        turns = [json.loads(line) for line in journal.read_bytes().splitlines()]
        records = [json.loads(line) for line in responses.read_bytes().splitlines()]
        records[1]["text"] = '{"value":"blue","source_id":"p2"}'
        turns[2]["reply_sha256"] = hashlib.sha256(records[1]["text"].encode()).hexdigest()
        for path, rows in ((journal, turns), (responses, records)):
            path.write_text("".join(json.dumps(row) + "\n" for row in rows))
        self.assertEqual(l2_generation_audit.audit(board, journal,
                         renderer=l2_generation_audit.render_scripted_prompt)["reference_reads"], 1)
        with self.assertRaisesRegex(ValueError, "lacks an observed verification request"):
            self.replay((board, journal, responses))

    def test_bad_and_capped_replies_keep_usage(self):
        def generate(prompt, **_):
            worker = json.loads(prompt)["worker"]
            if worker == "a":
                return Generation('{"value":"blue","value":"green","source_id":"p2"}', 20, 8, 50, False)
            return Generation('{"value":"blue","source_id":"p2"}', 20, 10, 50, True)

        for allow in (False, True):
            with self.subTest(allow=allow):
                result = self.replay(self.fixture(generate, allow_limit=allow))
                self.assertEqual((result["exposures"], result["adoptions"], result["output_tokens_known"]),
                                 (2, int(allow), 18))

    def test_forged_reference_source_and_repeated_verify_do_not_score(self):
        def generate(prompt, **_):
            view = json.loads(prompt)
            if view["verification"] is not None and view["worker"] == "b":
                answer = {"value": "blue", "source_id": view["verification"]["id"]}
            else:
                answer = {"action": "verify"}
            return Generation(json.dumps(answer), 20, 8, 50, False)

        result = self.replay(self.fixture(generate))
        self.assertEqual((result["reference_reads"], result["replayed_decisions"], result["adoptions"]), (2, 0, 0))

    def test_host_return_before_worker_acknowledgment_stays_unscored(self):
        board, journal, responses = self.fixture(self.generate)
        journal.write_bytes(b"\n".join(journal.read_bytes().splitlines()[:2]) + b"\n")
        responses.write_bytes(b"\n".join(responses.read_bytes().splitlines()[:2]) + b"\n")
        result = self.replay((board, journal, responses))
        self.assertEqual((result["status"], result["unknown_usage_attempts"], result["adoptions"]),
                         ("incomplete", 1, None))
        self.assertEqual(result["host_only_return_usage"]["output_tokens"], 3)

    def test_host_failure_never_fabricates_usage(self):
        root = Path(self.enterContext(TemporaryDirectory()))
        board, responses = root / "board.jsonl", root / "host.jsonl"

        def generate(*_, **__):
            raise TimeoutError("injected")

        with l2_host_response.capture(responses, generate) as observed, self.assertRaises(TimeoutError):
            r3_l2_generation.run(board, "neutral", generate=observed, render=l2_generation_audit.render_scripted_prompt,
                                 max_input_tokens=50, max_output_tokens=10, accept_at_limit=False)
        result = self.replay((board, board.with_suffix(".generation.jsonl"), responses))
        self.assertEqual((result["unknown_usage_attempts"], result["output_tokens_known"], result["adoptions"]),
                         (1, 0, None))

    def test_validator_rejection_keeps_raw_payload_but_never_scores(self):
        root = Path(self.enterContext(TemporaryDirectory()))
        board, responses = root / "board.jsonl", root / "host.jsonl"

        def invalid(*_, **__):
            return Generation('{"value":"blue","source_id":"p2"}', 20, 11, 50, False)

        with l2_host_response.capture(responses, invalid) as observed, self.assertRaisesRegex(ValueError, "caps"):
            r3_l2_generation.run(board, "neutral", generate=observed, render=l2_generation_audit.render_scripted_prompt,
                                 max_input_tokens=50, max_output_tokens=10, accept_at_limit=False)
        result = self.replay((board, board.with_suffix(".generation.jsonl"), responses))
        self.assertEqual((result["unknown_usage_attempts"], result["output_tokens_known"], result["adoptions"]),
                         (1, 0, None))
        self.assertEqual(json.loads(responses.read_bytes().splitlines()[-1])["output_tokens"], 11)

    def test_archive_requires_each_separate_raw_response_pin(self):
        root = Path(self.enterContext(TemporaryDirectory()))
        export = root / "export"
        export.mkdir()
        schedule = r3_schedule.plan(["neutral", "warning"], [{"block_id": "matched", "stratum": "dev"}], seed=86)
        digest = hashlib.sha256(json.dumps(schedule, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        archive_id = "a" * 32
        observed, responses = {}, {}
        for position, condition in enumerate(schedule["blocks"][0]["order"]):
            board = export / f"block-0000-arm-{position:02d}.jsonl"
            journal = board.with_suffix(".generation.jsonl")
            host_file = root / f"host-{position}.jsonl"
            with l2_host_response.capture(host_file, self.generate) as callback:
                r3_l2_generation.run(board, condition, generate=callback, render=l2_generation_audit.render_scripted_prompt,
                                     max_input_tokens=50, max_output_tokens=10, accept_at_limit=False,
                                     reference_text="Paper ledger marker: green",
                                     identity={"archive_id": archive_id, "schedule_sha256": digest,
                                               "block_id": "matched", "arm_position": position})
            observed["matched", position] = {"board_sha256": hashlib.sha256(board.read_bytes()).hexdigest(),
                                            "journal_sha256": hashlib.sha256(journal.read_bytes()).hexdigest()}
            responses["matched", position] = host_file, hashlib.sha256(host_file.read_bytes()).hexdigest()
        plan = {"schedule": schedule, "archive_id": archive_id, "observed_pins": observed}
        result = l2_host_response.verify_archive(export, **plan, response_pins=responses)
        self.assertEqual([arm["raw_replay"]["adoptions"] for arm in result["arms"]], [1, 1])
        reference_sha = hashlib.sha256(b"Paper ledger marker: green").hexdigest()
        terms = {"reference_sha256": reference_sha, "max_input_tokens": 50,
                 "max_output_tokens": 10, "accept_at_limit": False}
        frozen = {key: dict(terms) for key in observed}
        governed = l2_host_response.verify_archive(export, **plan, response_pins=responses, frozen_governance=frozen)
        self.assertEqual(governed["evidence"], "scripted_host_response_governed_verified")
        self.assertTrue(all(arm["governance"] == terms for arm in governed["arms"]))
        frozen["matched", 0]["accept_at_limit"] = True
        with self.assertRaisesRegex(ValueError, "governance differs for accept_at_limit"):
            l2_host_response.verify_archive(export, **plan, response_pins=responses, frozen_governance=frozen)
        with self.assertRaisesRegex(ValueError, "cover every scheduled arm"):
            l2_host_response.verify_archive(export, **plan, response_pins={})
        missing_digest = responses | {("matched", 0): (responses["matched", 0][0], "0" * 64)}
        with self.assertRaisesRegex(ValueError, "external host response digest"):
            l2_host_response.verify_archive(export, **plan, response_pins=missing_digest)
