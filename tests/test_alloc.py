import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from murmuration.trapbench import alloc  # noqa: E402


def w(agent, task, answer, name=None, **kw):
    return {"agent": agent, "action": "work", "task": task, "answer": answer,
            "name": name or f"{agent}-{task}", **kw}


class AllocTest(unittest.TestCase):
    def test_gen_deterministic_shape(self):
        a, b = alloc.gen(3), alloc.gen(3)
        self.assertEqual(alloc.dumps(a), alloc.dumps(b))
        self.assertEqual(len(a["tasks"]), 6)
        self.assertEqual(len({t["id"] for t in a["tasks"]}), 6)
        self.assertNotEqual(alloc.dumps(a), alloc.dumps(alloc.gen(4)))
        self.assertIn("{agent}", a["name_rule"])

    def test_train_heldout_disjoint(self):
        tr = [t for s in range(15) for t in alloc.gen(s, "train")["tasks"]]
        ho = [t for s in range(15) for t in alloc.gen(s, "heldout")["tasks"]]
        self.assertFalse({t["id"] for t in tr} & {t["id"] for t in ho})
        self.assertFalse({t["check"] for t in tr} & {t["check"] for t in ho})

    def test_hand_written_log(self):  # adversarial: score reads only the log
        ts = {"n_agents": 4, "name_rule": alloc.NAME_RULE,
              "tasks": [{"id": f"x{i}", "check": "", "expect": i} for i in range(6)]}
        log = [w("a0", "x0", 0), w("a1", "x0", 0), w("a2", "x2", 99, name="same"),
               w("a3", "x3", 3, name="same"), {"agent": "a0", "action": "claim", "task": "x5"}]
        before = copy.deepcopy(log)
        self.assertEqual(alloc.score(log, ts),
                         {"distinct_passing": 2, "surviving_passing": 2, "slots": 4, "duplicates": 1, "name_collisions": 1})
        self.assertEqual(log, before)

    def test_floor_and_oracle(self):
        for s in range(15):
            ts = alloc.gen(s)
            o, f = alloc.score(alloc.oracle_log(ts), ts), alloc.score(alloc.floor_log(ts), ts)
            self.assertEqual((o["distinct_passing"], o["slots"]), (4, 4))
            self.assertEqual((o["duplicates"], o["name_collisions"]), (0, 0))
            self.assertEqual((f["distinct_passing"], f["duplicates"]), (1, 3))

    def test_rejected_slot_scores_zero(self):  # adversarial: enforcement is not free
        ts = alloc.gen(1)
        log = alloc.oracle_log(ts)
        log[0]["rejected"] = True
        r = alloc.score(log, ts)
        self.assertEqual(r["distinct_passing"], 3)
        self.assertEqual(r["slots"], 4)

    def test_unique_names_survive_all(self):
        for s in range(15):
            ts = alloc.gen(s)
            for log in (alloc.oracle_log(ts), alloc.floor_log(ts)):
                r = alloc.score(log, ts)
                self.assertEqual(r["surviving_passing"], r["distinct_passing"])

    def test_one_name_four_works_survive_as_one(self):  # adversarial
        ts = alloc.gen(2)
        log = [w(f"a{i}", t["id"], t["expect"], name="out.txt") for i, t in enumerate(ts["tasks"][:4])]
        r = alloc.score(log, ts)
        self.assertEqual((r["distinct_passing"], r["surviving_passing"]), (4, 1))

    def test_last_in_log_order_wins(self):
        ts = alloc.gen(2)
        t0, t1 = ts["tasks"][:2]
        good, bad = w("a0", t0["id"], t0["expect"], name="n"), w("a1", t1["id"], t1["expect"] + 1, name="n")
        self.assertEqual(alloc.score([good, bad], ts)["surviving_passing"], 0)
        self.assertEqual(alloc.score([bad, good], ts)["surviving_passing"], 1)
        rej = w("a1", t1["id"], t1["expect"] + 1, name="n", rejected=True)  # rejected never overwrites
        self.assertEqual(alloc.score([good, rej], ts)["surviving_passing"], 1)

    def test_empty_name_is_a_name(self):  # adversarial: "", None and missing all collide
        ts = alloc.gen(2)
        log = [{"agent": f"a{i}", "action": "work", "task": t["id"], "answer": t["expect"], **extra}
               for i, (t, extra) in enumerate(zip(ts["tasks"], [{"name": ""}, {"name": None}, {}, {"name": ""}]))]
        self.assertEqual(alloc.score(log, ts)["surviving_passing"], 1)


if __name__ == "__main__":
    unittest.main()
