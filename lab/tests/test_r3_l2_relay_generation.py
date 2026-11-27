import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lab import l2_relay_control as relay, r3_l2_relay_generation as generation
from lab.spark_decision import Generation
from tremor.board import read_log


def reply(payload, at_limit=False):
    text = payload if isinstance(payload, str) else json.dumps(payload, sort_keys=True)
    return Generation(text, 12, 16 if at_limit else 8, 100, at_limit)


class R3RelayGenerationTests(unittest.TestCase):
    def setUp(self):
        self.scratch = Path(self.enterContext(TemporaryDirectory()))

    def run_case(self, name, produce, *, clean=False):
        board = self.scratch / f"{name}.jsonl"
        report = generation.run(board, generate=lambda prompt, **_: produce(json.loads(prompt)),
                                render=json.dumps, max_input_tokens=20, max_output_tokens=16, clean=clean)
        tape = board.with_suffix(".relay-generation.jsonl")
        return board, report, [json.loads(row) for row in tape.read_text().splitlines()]

    def test_same_decisions_and_opportunities_can_yield_different_relay_R(self):
        def produce(observed, relay_enabled):
            parent = observed["source_id"]
            slot = observed["opportunity"]
            text = relay.FALSE_STATEMENT
            if slot == 5:
                return reply({"kind": "decision", "parent_id": parent, "text": text})
            if not relay_enabled:
                return reply({"kind": "abstain"})
            if not parent:
                parent = observed["visible"][0]["id"]
            if slot == 3:
                text = relay.CORRECT_STATEMENT
            return reply({"kind": "relay", "parent_id": parent, "text": text})

        for enabled, expected in ((True, [2, 0]), (False, [0, 0])):
            board, report, tape = self.run_case(str(enabled), lambda observed: produce(observed, enabled))
            readout = report["readout"]
            self.assertEqual(list(readout["first_generation_relay_counts"].values()), expected)
            self.assertEqual(readout["first_generation_relay_mean"], sum(expected) / 2)
            self.assertEqual((readout["decision_posts_excluded"], readout["named_root_exposures"]), (1, 4))
            self.assertEqual(report["usage"], {"input_tokens": 72, "output_tokens": 48,
                                              "generation_ns": 600, "unknown_attempts": 0})
            self.assertEqual(tape[-1]["event"], "complete")
            for attempt in (row for row in tape if row["event"] == "attempt"):
                read = read_log(board)[attempt["read_seq"]]
                self.assertEqual((read["type"], read["agent"], read["hash"]),
                                 ("read", attempt["worker"], attempt["read_head"]))
            if enabled:
                self.assertEqual([row["status"] for row in readout["relays"]],
                                 ["eligible", "eligible", "different_value", "repeated_author_parent"])
                self.assertEqual([row["disposition"] for row in tape if row["event"] == "response"][2],
                                 "unobserved_parent")

    def test_wrong_parent_and_duplicate_json_are_metered_and_do_not_post(self):
        def produce(observed):
            if observed["opportunity"] == 0:
                return reply('{"kind":"relay","kind":"decision","parent_id":"p1","text":"Marker: blue"}')
            return reply({"kind": "relay", "parent_id": "p2", "text": relay.FALSE_STATEMENT})

        board, report, tape = self.run_case("bad", produce)
        self.assertEqual(report["readout"]["first_generation_relay_mean"], 0)
        self.assertEqual(len([event for event in read_log(board) if event["type"] == "post"]), 2)
        responses = [row for row in tape if row["event"] == "response"]
        self.assertEqual([row["disposition"] for row in responses], ["malformed"] + ["unobserved_parent"] * 5)
        self.assertIn('"kind":"relay","kind":"decision"', responses[0]["raw"])
        self.assertEqual(report["usage"]["output_tokens"], 48)

    def test_clean_store_has_no_R_denominator(self):
        _, report, tape = self.run_case("clean", lambda _: reply({"kind": "abstain"}), clean=True)
        self.assertEqual((report["status"], report["readout"], tape[0]["planted_roots"]),
                         ("no_planted_roots", None, []))
        self.assertEqual(tape[-1]["event"], "complete")

    def test_interruption_or_output_cap_withholds_R_and_retains_known_usage(self):
        def interrupt(observed):
            if observed["opportunity"] == 4:
                raise RuntimeError("scripted interruption")
            if observed["opportunity"] == 0:
                return reply({"kind": "relay", "parent_id": observed["source_id"], "text": relay.FALSE_STATEMENT})
            return reply({"kind": "abstain"})

        board, report, tape = self.run_case("interrupted", interrupt)
        self.assertEqual((report["status"], report["anchor"], report["readout"]), ("incomplete_generation", None, None))
        self.assertEqual((report["usage"]["output_tokens"], report["usage"]["unknown_attempts"]), (32, 1))
        self.assertEqual([row["event"] for row in tape[-2:]], ["attempt", "incomplete"])
        prefix = read_log(board)
        self.assertTrue(any(e["type"] == "post" and e["data"]["kind"] == "relay" for e in prefix))
        with self.assertRaisesRegex(ValueError, "window did not finish"):
            relay.measure(board, planted_roots=tape[0]["planted_roots"],
                          expected_head=prefix[-1]["hash"], expected_events=len(prefix))

        _, report, tape = self.run_case("capped", lambda p: reply({"kind": "abstain"}, p["opportunity"] == 0))
        self.assertEqual((report["status"], report["anchor"], report["readout"]), ("output_limit", None, None))
        self.assertEqual((report["usage"]["output_tokens"], report["usage"]["unknown_attempts"]), (56, 0))
        self.assertEqual(tape[-1]["output_limit_replies"], 1)
