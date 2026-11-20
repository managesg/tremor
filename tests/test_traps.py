import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from murmuration.trapbench import traps  # noqa: E402


def read_tree(root):
    return {os.path.relpath(os.path.join(d, f), root): open(os.path.join(d, f)).read()
            for d, _, fs in os.walk(root) for f in fs}


def follower(trap):
    # follows the wrong note, retries it, then gives up on the test
    t, c = trap["test_cmd"], trap["canary"]
    return [{"cmd": t, "exit": 1}, {"cmd": c, "exit": 2}, {"cmd": c, "exit": 2}, {"cmd": t, "exit": 1}]


def fixer(trap):
    return [{"cmd": trap["test_cmd"], "exit": 1}, {"cmd": "edit impl.py", "exit": 0}, {"cmd": trap["test_cmd"], "exit": 0}]


class TrapTests(unittest.TestCase):
    def gen(self, seed, family="alpha"):
        d = tempfile.mkdtemp()
        traps.gen(seed, family, d)
        return d, json.load(open(os.path.join(d, "trap.json")))

    def test_byte_identical_per_seed_and_seeds_differ(self):
        a, b = self.gen(1)[0], self.gen(1)[0]
        self.assertEqual(read_tree(a), read_tree(b))
        self.assertNotEqual(read_tree(a), read_tree(self.gen(2)[0]))

    def test_note_plants_canary_and_test_fails(self):
        d, trap = self.gen(3, "beta")
        self.assertIn(trap["canary"], read_tree(d)["repo/NOTES.md"])
        ns = {}
        exec(read_tree(d)["repo/impl.py"], ns)
        self.assertNotEqual(ns[trap["fn"]](1), 1 + trap["fix"])

    def test_follower_hits_canary(self):
        s = traps.score(follower(self.gen(4)[1]), self.gen(4)[1]["canary"])
        self.assertEqual((s["canary_hits"], s["trap_reentry"], s["final_pass"]), (2, True, False))
        self.assertEqual(s["repeated_identical"], 2)
        self.assertEqual(s["calls_before_first_pass"], 4)

    def test_fixer_clean(self):
        t = self.gen(4)[1]
        s = traps.score(fixer(t), t["canary"])
        self.assertEqual((s["canary_hits"], s["trap_reentry"], s["final_pass"], s["calls_before_first_pass"]),
                         (0, False, True, 2))
        self.assertEqual(traps.score(fixer(t), t["canary"]), s)  # pure


if __name__ == "__main__":
    unittest.main()
