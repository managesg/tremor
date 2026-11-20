import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from murmuration import tokens  # noqa: E402

CANARY = "CANARY-7f3a-secret-prompt"


def line(typ, mid, usage, tools=(), side=False, sid="S1", agent=None):
    content = [{"type": "text", "text": CANARY}] + [
        {"type": "tool_use", "id": f"tu_{mid}_{t}", "name": t, "input": {"file_path": CANARY}} for t in tools]
    o = {"type": typ, "sessionId": sid, "isSidechain": side,
         "message": {"id": mid, "content": content, "usage": usage}}
    if agent:
        o["agentId"] = agent
    return json.dumps(o)


def U(i, o, cr, cw):
    return {"input_tokens": i, "output_tokens": o, "cache_read_input_tokens": cr,
            "cache_creation_input_tokens": cw}


class TokensTest(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.addCleanup(self.d.cleanup)
        with open(os.path.join(self.d.name, "main.jsonl"), "w") as f:
            f.write(line("user", "u", None) + "\n")
            f.write(line("assistant", "m1", U(1, 5, 0, 100), ["Read", "Grep"]) + "\n")
            f.write(line("assistant", "m1", U(1, 7, 0, 100), ["Read", "Grep"]) + "\n")  # stream dup
            f.write(line("assistant", "m2", U(2, 3, 300, 0), ["Edit"]) + "\n")
            f.write("not json\n")
        with open(os.path.join(self.d.name, "sub.jsonl"), "w") as f:
            f.write(line("assistant", "a1", U(1, 1, 0, 900), side=True, sid="S2", agent="x") + "\n")

    def test_probe_keys_and_counts(self):
        p = tokens.probe([self.d.name])
        self.assertEqual(p["files"], 2)
        self.assertEqual(p["with_usage"], 4)
        self.assertEqual(p["usage_keys"]["cache_read_input_tokens"], 4)

    def test_ledger_values(self):
        L = {s["subagent"]: s for s in tokens.ledger([self.d.name], "salt")}
        m = L[False]
        self.assertEqual((m["input"], m["output"], m["cache_read"], m["cache_write"]), (3, 10, 300, 100))
        self.assertAlmostEqual(m["cache_hit"], 300 / 403)
        self.assertEqual((m["reads"], m["writes"], m["reads_per_write"]), (2, 1, 2.0))  # m1 streamed twice: its Read and Grep count once
        self.assertIsNone(m["cold_start_cache_write"])
        self.assertEqual(L[True]["cold_start_cache_write"], 900)
        self.assertIsNone(L[True]["reads_per_write"])

    def test_missing_usage_is_none_not_zero(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        with open(os.path.join(d.name, "miss.jsonl"), "w") as f:
            f.write(line("assistant", "x1", {"input_tokens": 4, "output_tokens": 2}, sid="S3") + "\n")
            f.write(line("assistant", "x2", {"input_tokens": 1, "output_tokens": 1, "cache_read_input_tokens": 0,
                                             "cache_creation_input_tokens": "n/a"}, sid="S3") + "\n")
        (s,) = tokens.ledger([d.name], "s")
        self.assertEqual((s["input"], s["output"]), (5, 3))
        self.assertEqual(s["cache_read"], 0)  # a reported 0 stays 0
        self.assertEqual(s["missing"], {"input": 0, "output": 0, "cache_read": 1, "cache_write": 2})
        self.assertIsNone(s["cache_write"])
        self.assertIsNone(s["cache_hit"])  # cache_write class missing: denominator unknown

    def test_repeated_tool_use_id_counted_once(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        with open(os.path.join(d.name, "rep.jsonl"), "w") as f:
            for k in range(3):  # same tool_use id streamed in 3 records, different message ids
                o = json.loads(line("assistant", f"r{k}", U(1, 1, 0, 0), sid="S4"))
                o["message"]["content"] = [{"type": "tool_use", "id": "toolu_1", "name": "Read", "input": {}}]
                f.write(json.dumps(o) + "\n")
        (s,) = tokens.ledger([d.name], "s")
        self.assertEqual(s["reads"], 1)

    def test_distinct_tool_use_ids_in_one_message_both_count(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        with open(os.path.join(d.name, "two.jsonl"), "w") as f:
            for tid in ("toolu_a", "toolu_b"):  # same message id and index, different tool_use ids
                o = json.loads(line("assistant", "same", U(1, 1, 0, 0), sid="S5"))
                o["message"]["content"] = [{"type": "tool_use", "id": tid, "name": "Read", "input": {}}]
                f.write(json.dumps(o) + "\n")
        (s,) = tokens.ledger([d.name], "s")
        self.assertEqual(s["reads"], 2)

    def test_salt_changes_ids_and_is_required(self):
        a = {s["session"] for s in tokens.ledger([self.d.name], "a")}
        b = {s["session"] for s in tokens.ledger([self.d.name], "b")}
        self.assertFalse(a & b)
        self.assertNotIn("S1", "".join(a))
        with self.assertRaises(ValueError):
            tokens.ledger([self.d.name], "")

    def test_canary_never_in_output(self):
        out = json.dumps(tokens.probe([self.d.name])) + json.dumps(tokens.ledger([self.d.name], "s"))
        self.assertNotIn(CANARY, out)
        self.assertNotIn("file_path", out)


if __name__ == "__main__":
    unittest.main()
