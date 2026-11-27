import json
import os
import tempfile
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from tremor.board import Board, read_log  # noqa: E402


class BoardTest(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.addCleanup(self.d.cleanup)
        self.path = os.path.join(self.d.name, "log.jsonl")

    def test_writes_invisible_until_end_round(self):
        b = Board(self.path, 1)
        pid = b.post("a", "hello")
        self.assertEqual(b.read("b"), [])
        self.assertEqual(b.snapshot()["items"], {})
        b.end_round()
        self.assertEqual([i["id"] for i in b.read("b")], [pid])
        self.assertEqual(b.read("b", pid)["text"], "hello")

    def test_claim_collision_logged_and_resolved(self):
        b = Board(self.path, 7)
        b.claim("a", "X")
        b.claim("b", "X")
        self.assertEqual(b.snapshot()["claims"], {})  # same snapshot: neither sees the other
        b.end_round()
        res = [l for l in read_log(self.path) if l["type"] == "end_round"][0]["data"]["resolved"][0]
        self.assertTrue(res["collision"])
        self.assertEqual(res["claimants"], ["a", "b"])
        self.assertIn(res["winner"], ("a", "b"))
        self.assertEqual(b.snapshot()["claims"]["X"]["agent"], res["winner"])
        b.claim("c", "X")  # held: the late claimant loses, no collision
        b.end_round()
        res = [l for l in read_log(self.path) if l["type"] == "end_round"][1]["data"]["resolved"][0]
        self.assertIsNone(res["winner"])
        self.assertFalse(res["collision"])

    def winner(self, seed, name):
        b = Board(os.path.join(self.d.name, name), seed)
        b.claim("a", "X")
        b.claim("b", "X")
        b.end_round()
        return b.snapshot()["claims"]["X"]["agent"]

    def test_seeded_resolution_deterministic(self):
        self.assertEqual(self.winner(3, "1"), self.winner(3, "2"))
        self.assertEqual({self.winner(s, f"s{s}") for s in range(20)}, {"a", "b"})

    def test_replay_equals_state(self):
        b = Board(self.path, 5)
        p = b.post("a", "one", facts=["F"])
        b.claim("a", "X")
        b.claim("b", "X")
        b.end_round()
        w = b.snapshot()["claims"]["X"]["agent"]
        b.read("a")
        b.post("b", "two", refs=[p], supersedes=[p])
        b.release(w, "X", task_type="t")
        b.post("a", "pending")
        self.assertEqual(Board(self.path, 5).state, b.state)
        b.end_round()
        self.assertEqual(Board(self.path, 5).state, b.state)
        with self.assertRaises(ValueError):
            Board(self.path, 6)

    def test_release_requires_holder(self):
        b = Board(self.path, 1)
        with self.assertRaises(ValueError):
            b.release("a", "X")
        b.claim("a", "X")
        b.end_round()
        b.release("a", "X")
        b.end_round()
        self.assertEqual(b.snapshot()["claims"], {})

    def test_claim_expiry(self):
        b = Board(self.path, 1, claim_ttl=2)
        b.claim("a", "X")
        b.end_round()  # granted in round 0
        b.end_round()  # round 1
        self.assertIn("X", b.snapshot()["claims"])
        b.end_round()  # round 2: age 2 >= ttl
        self.assertNotIn("X", b.snapshot()["claims"])
        self.assertEqual([l for l in read_log(self.path) if l["type"] == "end_round"][2]["data"]["expired"],
                         [{"item": "X", "agent": "a"}])
        b.claim("b", "X")
        b.end_round()
        self.assertEqual(b.snapshot()["claims"]["X"]["agent"], "b")

    def test_tamper_detected(self):
        b = Board(self.path, 1)
        b.post("a", "honest")
        b.post("a", "second")
        b.end_round()
        with open(self.path, encoding="utf-8") as f:
            lines = f.read().splitlines()
        edited = json.loads(lines[1])
        edited["data"]["text"] = "forged"
        lines[1] = json.dumps(edited, sort_keys=True, separators=(",", ":"))
        with open(self.path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        with self.assertRaises(ValueError):
            Board(self.path, 1)
        # deleting a middle line breaks the chain too
        del lines[1]
        with open(self.path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        with self.assertRaises(ValueError):
            read_log(self.path)


if __name__ == "__main__":
    unittest.main()
