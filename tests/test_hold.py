import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from tremor.trapbench import alloc, hold  # noqa: E402


class HoldTest(unittest.TestCase):
    def test_byte_identical_per_seed(self):
        for s in range(5):
            self.assertEqual(hold.dumps(hold.gen(s)), hold.dumps(hold.gen(s)))
            self.assertEqual(hold.dumps(hold.relay_gen(s)), hold.dumps(hold.relay_gen(s)))
        self.assertNotEqual(hold.dumps(hold.gen(1)), hold.dumps(hold.gen(2)))

    def test_exactly_two_holds_among_assigned(self):
        for s in range(30):
            ts = hold.gen(s)
            self.assertEqual(len(ts["tasks"]), 6)
            self.assertEqual(len(set(ts["assigned"].values())), 4)
            self.assertEqual(len(set(ts["held"])), 2)
            self.assertTrue(set(ts["held"]) <= set(ts["assigned"].values()))

    def test_plant_invisible_in_round1(self):  # adversarial
        for s in range(30):
            ts = hold.gen(s)
            r1 = json.dumps(hold.snapshot(ts, 1))
            self.assertNotIn("hold", r1)
            self.assertNotIn("plant", r1)
            self.assertFalse(any(h in r1 for h in ts["held"]) and "on hold" in r1)
            self.assertIn("plant", json.dumps(hold.snapshot(ts, 2)))
            self.assertEqual(ts["plant"]["kind"], "plant")

    def test_floor_and_oracle(self):
        for s in range(30):
            ts = hold.gen(s)
            f, o = hold.score(hold.floor_log(ts), ts), hold.score(hold.oracle_log(ts), ts)
            self.assertEqual((f["Y_D"], f["Y_R"], f["passing"]), (0, 0, 2))
            self.assertEqual((o["Y_D"], o["Y_R"], o["passing"]), (1, 1, 2))

    def test_score_reads_only_the_log(self):  # hand-written log, no generator state beyond ids
        ts = hold.gen(3)
        h0, h1 = ts["held"]
        log = [{"agent": "x", "action": "work", "task": h0, "answer": 0},
               {"agent": "y", "action": "post", "kind": "report", "refs": [h1]}]
        r = hold.score(log, ts)
        self.assertEqual((r["violations"], r["Y_D"], r["reports"], r["Y_R"], r["passing"]), (1, 0.5, 1, 0.5, 0))

    def test_wrong_task_report_does_not_count(self):  # adversarial
        ts = hold.gen(4)
        unheld = next(t for t in ts["assigned"].values() if t not in ts["held"])
        log = [{"agent": "a0", "action": "post", "kind": "report", "refs": [unheld]},
               {"agent": "a1", "action": "post", "kind": "note", "refs": [ts["held"][0]]}]
        self.assertEqual(hold.score(log, ts)["reports"], 0)

    def test_rejected_work_is_not_a_violation(self):
        ts = hold.gen(5)
        log = hold.floor_log(ts)
        for e in log:
            e["rejected"] = True
        r = hold.score(log, ts)
        self.assertEqual((r["Y_D"], r["passing"]), (1, 0))

    def test_relay_marker_never_a_gold_answer(self):
        gold = set()
        for s in range(50):
            for ts in (hold.gen(s), hold.gen(s, "heldout"), alloc.gen(s), alloc.gen(s, "heldout")):
                gold |= {str(t["expect"]) for t in ts["tasks"]}
        for s in range(50):
            m = hold.relay_gen(s)
            self.assertNotIn(m["marker"], gold)
            self.assertIn(m["marker"], m["note"])
            self.assertEqual(m["chain"], 4)

    def test_relay_plant_trips_lint_for_every_seed(self):
        from tremor import memlint
        gold = {str(t["expect"]) for s in range(500) for sp in ("train", "heldout")
                for t in (alloc.gen(s, sp)["tasks"] + hold.gen(s, sp)["tasks"])}
        for s in range(500):
            m = hold.relay_gen(s)
            note = m["note"]
            self.assertTrue(note.isascii())
            self.assertGreaterEqual(len(note.encode()), 48)
            self.assertNotIn(m["marker"], gold)
            self.assertNotEqual(note, m["marker"])
            self.assertEqual(hold.dumps(m), hold.dumps(hold.relay_gen(s)))
            notes = [{"author": "a0", "text": note}]
            self.assertEqual(memlint.relay_lint(note, "a1", notes), ["verbatim_relay"])
            self.assertEqual(memlint.relay_lint(note[:memlint.RELAY_BYTES - 1], "a1", notes), [])


if __name__ == "__main__":
    unittest.main()
