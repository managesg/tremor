import unittest

from lab.pilot_reply_diagnostics import describe
from murmuration.team_claude import parse


PASS = '[{"type":"pass"}]'


def turn(call_id, cond="code", output=150, stop_reason="end_turn", reply=PASS, round=1):
    return {
        "call_id": call_id, "cond": cond, "round": round,
        "usage": {"output_tokens": output}, "stop_reason": stop_reason, "reply": reply,
    }


class PilotReplyDiagnosticsTests(unittest.TestCase):
    def test_reports_both_scopes_and_keeps_length_distinct_from_stop_reason(self):
        result = describe([
            turn("boundary"),
            turn("augmented", cond="states_check", output=151, reply=f"Explanation. {PASS}"),
            turn("truncated", cond="none", output=150, stop_reason="max_tokens"),
        ])
        self.assertEqual(result["all_conditions"]["max_output_tokens"], 151)
        self.assertEqual(result["all_conditions"]["above_ceiling_call_ids"], ["augmented"])
        self.assertEqual(result["all_conditions"]["max_tokens_stop_call_ids"], ["truncated"])
        self.assertEqual(result["core"]["max_output_tokens"], 150)
        self.assertEqual(result["core"]["above_ceiling_call_ids"], [])
        self.assertEqual(result["per_condition"]["states_check"]["second_round_non_array_call_ids"], ["augmented"])
        self.assertIsNone(result["per_condition"]["play"]["max_output_tokens"])

    def test_exact_array_shape_is_distinct_from_action_parser_acceptance(self):
        bare_object = '{"type":"pass"}'
        prefixed = f"Explanation. {PASS}"
        for reply in (prefixed, bare_object, PASS):
            self.assertEqual(parse(reply, 1, []), ([{"type": "pass"}], None))
        rows = [
            turn("prefix", reply=prefixed),
            turn("object", reply=bare_object),
            turn("first_round", reply=prefixed, round=0),
            turn("two_values", reply=f"{PASS} {PASS}"),
            turn("nonfinite", reply="[NaN]"),
            turn("duplicate", reply='[{"type":"pass","type":"pass"}]'),
            turn("json_whitespace", reply=f" \t{PASS}\r\n"),
        ]
        output = describe(rows)["core"]
        self.assertEqual(output["second_round_turns"], 6)
        self.assertEqual(output["second_round_non_array_call_ids"],
                         ["duplicate", "nonfinite", "object", "prefix", "two_values"])

    def test_invalid_metering_and_duplicate_ids_refuse(self):
        for output in (None, -1, True, "150", 150.0):
            with self.subTest(output=output), self.assertRaisesRegex(ValueError, "output_tokens"):
                describe([turn("invalid", output=output)])
        with self.assertRaisesRegex(ValueError, "output_tokens"):
            describe([{**turn("missing"), "usage": {}}])
        with self.assertRaisesRegex(ValueError, "unique"):
            describe([turn("duplicate"), turn("duplicate", cond="play")])
