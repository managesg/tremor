import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from tremor.trapbench import alloc  # noqa: E402


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
                         {"distinct_passing": 2, "surviving_passing": 2, "slots": 4, "duplicates": 1, "name_collisions": 1,
                          "Y": 0.5, "unknown_task_events": 0, "extra_work_events": 0, "valid": True})
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

    def test_unknown_task_is_a_noop(self):  # EP1: unknown task = logged no-op; changes no other field
        ts = {"n_agents": 4, "name_rule": alloc.NAME_RULE,
              "tasks": [{"id": f"h14t{i}", "check": "", "expect": 150 + i} for i in range(6)]}
        log = [w("a0", "t6", 1, name="x"), w("a2", "h14t2", 152, name="x")]  # minimal repro
        r = alloc.score(log, ts)
        self.assertEqual((r["name_collisions"], r["duplicates"], r["unknown_task_events"]), (0, 0, 1))
        base = [w("a1", "h14t0", 150), w("a2", "h14t2", 152, name="x"), w("a3", "h14t2", 0, name="y")]
        want = {k: v for k, v in alloc.score(base, ts).items() if k != "unknown_task_events"}
        for junk in (w("a0", "t6", 1, name="x"), w("a0", "t6", 152, name="y"), w("a0", "t6", 150, name=""),
                     w("a0", None, 150), {"agent": "a0", "action": "work", "answer": 150}, w("a0", "t6", 150)):
            for pos in range(len(base) + 1):  # every log position
                got = alloc.score(base[:pos] + [junk] + base[pos:], ts)
                self.assertEqual(got.pop("unknown_task_events"), 1)
                self.assertEqual(got, want)
        rej = alloc.score(base + [w("a0", "t6", 1, rejected=True)], ts)  # rejected unknown is not counted
        self.assertEqual(rej["unknown_task_events"], 0)

    def test_answer_is_a_json_integer_only(self):  # EP1 7, rule 2: 30.0, "30", true are not 30
        ts = {"n_agents": 4, "tasks": [{"id": "x0", "expect": 1}, {"id": "x1", "expect": 30}]}
        for a in (30.0, "30", True, 30.5, [30], None):
            self.assertEqual(alloc.score([w("a0", "x1", a)], ts)["distinct_passing"], 0, a)
        self.assertEqual(alloc.score([w("a0", "x0", True)], ts)["distinct_passing"], 0)  # True == 1 in Python
        self.assertEqual(alloc.score([w("a0", "x1", 30)], ts)["distinct_passing"], 1)

    def test_invalid_log_is_void_not_capped(self):  # EP1 7, option C
        ts = alloc.gen(2)
        five = [w(f"a{i}", t["id"], t["expect"]) for i, t in enumerate(ts["tasks"][:5])]
        r = alloc.score(five, ts)
        self.assertEqual((r["distinct_passing"], r["extra_work_events"], r["valid"], r["Y"]), (5, 0, False, None))
        t0, t1 = ts["tasks"][:2]
        r = alloc.score([w("a0", t0["id"], t0["expect"]), w("a0", t1["id"], t1["expect"])], ts)
        self.assertEqual((r["distinct_passing"], r["extra_work_events"], r["valid"], r["Y"]), (2, 1, False, None))
        ok = alloc.score([w("a0", t0["id"], t0["expect"]), w("a0", t1["id"], 0, rejected=True), w("a0", "zz", 1)], ts)
        self.assertEqual((ok["extra_work_events"], ok["valid"], ok["Y"]), (0, True, 0.25))
        for log in (alloc.oracle_log(ts), alloc.floor_log(ts), []):
            self.assertTrue(alloc.score(log, ts)["valid"])

    def test_malformed_event_makes_log_invalid(self):
        ts = alloc.gen(2)
        good = alloc.oracle_log(ts)[:1]
        for ev in (3, None, {"action": 1}, dict(good[0], agent=5), dict(good[0], task=["x"]),
                   dict(good[0], name=5), dict(good[0], rejected="yes")):
            r = alloc.score(good + [ev], ts)
            self.assertEqual((r["valid"], r["Y"], r["distinct_passing"]), (False, None, 1), ev)

    def test_event_without_action_is_malformed(self):  # ruling: scorer input is the episode action log only
        ts = alloc.gen(2)
        good = alloc.oracle_log(ts)[:1]
        t = ts["tasks"][1]
        for ev in ({"agent": "a1", "task": t["id"], "answer": t["expect"]},
                   {"type": "work", "agent": "a1", "task": t["id"], "answer": t["expect"]},
                   {"type": "release", "agent": None, "data": {"item": "t9", "done": True}, "rejected": False}, {}):
            r = alloc.score(good + [ev], ts)
            self.assertEqual((r["valid"], r["Y"], r["distinct_passing"]), (False, None, 1), ev)


if __name__ == "__main__":
    unittest.main()
