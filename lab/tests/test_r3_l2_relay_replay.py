import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lab import l2_relay_control as relay
from lab import r3_l2_relay_generation as generation
from lab import r3_l2_relay_replay as replay
from lab.spark_decision import Generation
from tremor.board import GENESIS, _digest, read_log


class R3RelayReplayTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))

    def fixture(self, name, *, interrupted=False, capped=False, clean=False):
        board = self.root / (name + ".jsonl")
        journal = board.with_suffix(".relay-generation.jsonl")

        def reply(prompt, **_):
            context = json.loads(prompt)
            opportunity = context["opportunity"]
            if interrupted and opportunity == 4:
                raise RuntimeError("fixture interrupt")
            parent = context["source_id"]
            if opportunity in (0, 1, 4) and not clean:
                result = {"kind": "relay", "text": relay.FALSE_STATEMENT, "parent_id": parent}
            elif opportunity == 5 and not clean:
                result = {"kind": "decision", "text": "blue", "parent_id": parent}
            else:
                result = {"kind": "abstain"}
            limit = capped and opportunity == 0
            return Generation(json.dumps(result), 12, 16 if limit else 8, 100, limit)

        outcome = generation.run(board, generate=reply, render=json.dumps, max_input_tokens=20,
                                 max_output_tokens=16, clean=clean)
        return board, journal, outcome

    @staticmethod
    def verify(board, journal, *, renderer=json.dumps, board_sha256=None, generation_sha256=None):
        return replay.verify(
            board, board_sha256=board_sha256 or hashlib.sha256(board.read_bytes()).hexdigest(),
            generation_sha256=generation_sha256 or hashlib.sha256(journal.read_bytes()).hexdigest(),
            render=renderer,
        )

    @staticmethod
    def rows(path):
        return [json.loads(line) for line in path.read_bytes().splitlines()]

    @staticmethod
    def write(path, rows):
        path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))

    def test_complete_and_clean_controls_replay_exact_runner_outcome(self):
        for clean in (False, True):
            with self.subTest(clean=clean):
                board, journal, outcome = self.fixture(f"clean-{clean}", clean=clean)
                verified = self.verify(board, journal)
                for field in ("status", "usage", "readout", "anchor"):
                    self.assertEqual(verified[field], outcome[field])
                if clean:
                    self.assertEqual(verified["status"], "no_planted_roots")
                    self.assertIsNone(verified["readout"])
                else:
                    self.assertEqual(verified["status"], "complete")
                    self.assertEqual(list(verified["readout"]["first_generation_relay_counts"].values()), [2, 0])
                    self.assertEqual(verified["readout"]["decision_posts_excluded"], 1)

    def test_bad_external_digests_and_other_renderer_refused(self):
        board, journal, _ = self.fixture("wrong-pins")
        with self.assertRaises(ValueError):
            self.verify(board, journal, board_sha256="0" * 64)
        with self.assertRaises(ValueError):
            self.verify(board, journal, generation_sha256="0" * 64)
        with self.assertRaises(ValueError):
            self.verify(board, journal, renderer=lambda context: json.dumps(context) + " ")

    def test_repinned_journal_cannot_move_request_to_later_valid_read_by_same_author(self):
        board, journal, _ = self.fixture("later-read")
        rows = self.rows(journal)
        requests = [row for row in rows if row["event"] == "attempt"]
        first, later = requests[0], requests[4]
        self.assertEqual((first["worker"], first["source_id"]), (later["worker"], later["source_id"]))
        self.assertLess(first["read_seq"], later["read_seq"])
        first.update(read_seq=later["read_seq"], read_head=later["read_head"])
        self.write(journal, rows)
        with self.assertRaises(ValueError):
            self.verify(board, journal)

    def test_repinned_board_cannot_change_proposal_kind_or_text(self):
        for field, replacement in (("kind", "decision"), ("text", relay.CORRECT_STATEMENT)):
            with self.subTest(field=field):
                board, journal, _ = self.fixture("board-" + field)
                trace = read_log(board)
                post = next(event for event in trace if event["type"] == "post"
                            and event["data"]["kind"] == "relay")
                post["data"][field] = replacement
                previous = GENESIS
                heads = {}
                for row in trace:
                    row["prev"] = previous
                    previous = row["hash"] = _digest(row)
                    heads[row["seq"]] = previous
                self.write(board, trace)
                rows = self.rows(journal)
                for request in (row for row in rows if row["event"] == "attempt"):
                    request["read_head"] = heads[request["read_seq"]]
                rows[-1]["expected_head"] = previous
                self.write(journal, rows)
                with self.assertRaises(ValueError):
                    self.verify(board, journal)

    def test_repinned_usage_must_reconcile_and_cannot_exceed_cap(self):
        for output, pair_total in ((7, None), (17, 57)):
            with self.subTest(output=output):
                board, journal, _ = self.fixture(f"usage-{output}")
                rows = self.rows(journal)
                response = next(row for row in rows if row["event"] == "response")
                response["output_tokens"] = output
                if pair_total is not None:
                    rows[-1]["usage"]["output_tokens"] = pair_total
                self.write(journal, rows)
                with self.assertRaises(ValueError):
                    self.verify(board, journal)

    def test_interrupted_and_capped_arms_retain_usage_but_withhold_relay_score(self):
        for name, settings, tokens, unknown in (
            ("interrupted", {"interrupted": True}, 32, 1),
            ("capped", {"capped": True}, 56, 0),
        ):
            with self.subTest(name=name):
                board, journal, outcome = self.fixture(name, **settings)
                verified = self.verify(board, journal)
                self.assertEqual(verified["status"], outcome["status"])
                self.assertEqual(verified["usage"], outcome["usage"])
                self.assertEqual((verified["usage"]["output_tokens"], verified["usage"]["unknown_attempts"]),
                                 (tokens, unknown))
                self.assertIsNone(verified["readout"])
                self.assertIsNone(verified["anchor"])

    def test_interrupted_prefix_cannot_claim_completion_with_its_own_valid_head(self):
        board, journal, _ = self.fixture("fake-completion", interrupted=True)
        trace = read_log(board)
        rows = self.rows(journal)
        rows[-1] = {"event": "complete", "expected_head": trace[-1]["hash"], "expected_events": len(trace),
                    "usage": rows[-1]["usage"] | {"unknown_attempts": 0}}
        self.write(journal, rows)
        with self.assertRaises(ValueError):
            self.verify(board, journal)
