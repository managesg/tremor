import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lab import l2_host_response, r3_l2_relay_generation as generation, r3_l2_relay_replay as replay
from lab.spark_decision import Generation


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RelayHostCaptureTests(unittest.TestCase):
    def setUp(self):
        root = Path(self.enterContext(TemporaryDirectory()))
        self.board = root / "board.jsonl"
        self.tape = root / "board.relay-generation.jsonl"
        self.host = root / "host.jsonl"

    def produce(self, behavior):
        def callback(prompt, **_caps):
            return behavior(json.loads(prompt))
        with l2_host_response.capture(self.host, callback) as observed:
            return generation.run(self.board, generate=observed, render=json.dumps,
                                  max_input_tokens=20, max_output_tokens=16)

    def verify(self, **kwargs):
        return replay.verify(self.board, board_sha256=digest(self.board), generation_sha256=digest(self.tape),
                             render=json.dumps, **kwargs)

    def strict(self):
        return self.verify(host_response_path=self.host, host_response_sha256=digest(self.host))

    def rewrite(self, path, mutate):
        rows = [json.loads(line) for line in path.read_bytes().splitlines()]
        mutate(rows)
        path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))

    def test_host_observation_confirms_raw_reply_and_usage(self):
        original = self.produce(lambda _: Generation('{"kind":"abstain"}', 12, 7, 100, False))
        self.assertEqual(self.strict(), {**original, "host_responses_verified": True})

        def substitute(rows):
            response = next(row for row in rows if row["event"] == "response")
            response["raw"] += " "
            response["generation_ns"] += 5
            rows[-1]["usage"]["generation_ns"] += 5
        self.rewrite(self.tape, substitute)
        self.assertEqual(self.verify()["usage"]["generation_ns"], 605)
        with self.assertRaisesRegex(ValueError, "tape differs"):
            self.strict()

    def test_host_wrong_request_caps_and_missing_observation_are_inconclusive(self):
        self.produce(lambda _: Generation('{"kind":"abstain"}', 12, 7, 100, False))
        before = self.host.read_bytes()
        for mutate in (lambda rows: rows[0].update(max_output_tokens=17), lambda rows: rows.pop()):
            self.host.write_bytes(before)
            self.rewrite(self.host, mutate)
            with self.assertRaises(ValueError):
                self.strict()

    def test_generation_exception_and_invalid_meter_stay_unscored(self):
        def behavior(context):
            if context["opportunity"] == 1:
                raise RuntimeError("scripted")
            return Generation('{"kind":"abstain"}', 12, 7, 100, False)

        result = self.produce(behavior)
        self.assertEqual(self.strict(), {**result, "host_responses_verified": True})
        self.assertEqual(result["usage"]["unknown_attempts"], 1)
        self.assertIsNone(result["readout"])

    def test_valid_host_return_cannot_corroborate_an_invalid_meter_terminal(self):
        invalid = self.produce(lambda _: Generation('{"kind":"abstain"}', 12, 17, 100, False))
        self.assertEqual(self.strict(), {**invalid, "host_responses_verified": True})
        self.assertEqual(invalid["usage"]["unknown_attempts"], 1)
        self.rewrite(self.host, lambda rows: rows[-1].update(output_tokens=7))
        with self.assertRaises(ValueError):
            self.strict()
