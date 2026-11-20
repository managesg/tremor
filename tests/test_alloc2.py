import os
import random
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from murmuration.trapbench import alloc2  # noqa: E402

TS = {"n_agents": 4, "tasks": [{"id": f"t{i}", "expect": 10 + i} for i in range(6)]}


def W(agent, task, answer=None, name=None, rejected=False):
    return {"agent": agent, "action": "work", "task": task,
            "answer": 10 + int(task[1:]) if answer is None and task in {t["id"] for t in TS["tasks"]} else answer,
            "name": name if name is not None else f"{agent}-{task}", "rejected": rejected}


def C(agent, task):
    return {"agent": agent, "action": "claim", "task": task, "answer": None, "name": None, "rejected": False}


def R(agent, item, done=True):
    return {"agent": agent, "action": "release", "task": item, "done": done, "rejected": False}


S = alloc2.score


class Rules(unittest.TestCase):
    def test_honest(self):
        s = S([W(f"a{i}", f"t{i}") for i in range(4)], TS)
        self.assertEqual((s["distinct_passing"], s["surviving_passing"], s["slots"], s["duplicates"],
                          s["name_collisions"], s["Y"]), (4, 4, 4, 0, 0, 1.0))

    def test_empty_log(self):
        s = S([], TS)
        self.assertEqual((s["distinct_passing"], s["Y"], s["false_done_rate"]), (0, 0.0, None))

    def test_floor_duplicates(self):
        s = S([W(f"a{i}", "t0") for i in range(4)], TS)
        self.assertEqual((s["distinct_passing"], s["duplicates"], s["Y"]), (1, 3, 0.25))
        self.assertEqual(s["surviving_passing"], 1)

    def test_same_name_clobber(self):
        s = S([W(f"a{i}", f"t{i}", name="x") for i in range(4)], TS)
        self.assertEqual((s["distinct_passing"], s["surviving_passing"], s["name_collisions"]), (4, 1, 3))

    def test_last_in_log_order_wins(self):
        s = S([W("a0", "t0", name="x"), W("a1", "t1", answer=0, name="x")], TS)
        self.assertEqual((s["distinct_passing"], s["surviving_passing"]), (1, 0))
        s = S([W("a0", "t0", answer=0, name="x"), W("a1", "t1", name="x")], TS)
        self.assertEqual((s["distinct_passing"], s["surviving_passing"]), (1, 1))

    def test_empty_and_missing_name_are_one_name(self):
        a, b = W("a0", "t0"), W("a1", "t1")
        a["name"], b["name"] = "", None
        s = S([a, b], TS)
        self.assertEqual((s["surviving_passing"], s["name_collisions"]), (1, 1))
        b["name"] = "y"
        self.assertEqual(S([a, b], TS)["surviving_passing"], 2)

    def test_rejected_scores_zero(self):
        s = S([W(f"a{i}", f"t{i}", rejected=True) for i in range(4)], TS)
        self.assertEqual((s["distinct_passing"], s["surviving_passing"], s["duplicates"], s["name_collisions"]), (0, 0, 0, 0))

    def test_rejected_does_not_clobber(self):
        s = S([W("a0", "t0", name="x"), W("a1", "t1", name="x", rejected=True)], TS)
        self.assertEqual((s["surviving_passing"], s["name_collisions"]), (1, 0))

    def test_unknown_task_ids(self):
        s = S([W("a0", "t9", answer=19), W("a1", "t1")], TS)
        self.assertEqual((s["distinct_passing"], s["duplicates"]), (1, 0))

    def test_wrong_answer_not_passing(self):
        s = S([W("a0", "t0", answer=999), W("a1", "t0", answer=True)], TS)
        self.assertEqual((s["distinct_passing"], s["duplicates"]), (0, 1))
        self.assertEqual(S([W("a0", "t0", answer="10")], TS)["distinct_passing"], 0)

    def test_late_claims_ignored(self):
        base = [W("a0", "t0")]
        self.assertEqual(S(base + [C("a0", "t0"), C("a1", "t0")], TS), S(base, TS))

    def test_work_without_claim_scores(self):
        self.assertEqual(S([W("a3", "t5")], TS)["distinct_passing"], 1)

    def test_five_works_are_void_not_capped(self):
        # EP1 7 option C: more than `slots` accepted works, or two by one agent, is an invalid log: Y is None
        s = S([W(f"a{i}", f"t{i}") for i in range(5)], TS)
        self.assertEqual((s["distinct_passing"], s["extra_work_events"], s["valid"], s["Y"]), (5, 0, False, None))
        s = S([W("a0", "t0"), W("a0", "t1")], TS)
        self.assertEqual((s["distinct_passing"], s["extra_work_events"], s["valid"], s["Y"]), (2, 1, False, None))
        s = S([W("a0", "t0"), W("a0", "t1", rejected=True), W("a0", "t9", answer=1)], TS)
        self.assertEqual((s["extra_work_events"], s["valid"], s["Y"]), (0, True, 0.25))

    def test_answer_is_a_json_integer_only(self):
        for a in (10.0, "10", True, 10.5, [10]):
            self.assertEqual(S([W("a0", "t0", answer=a)], TS)["distinct_passing"], 0, a)
        self.assertEqual(S([W("a0", "t1", answer=True)], TS)["distinct_passing"], 0)  # True == 1 == ... in Python

    def test_malformed_event_makes_log_invalid(self):
        for ev in (3, None, {"action": 1}, dict(W("a1", "t1"), agent=5), dict(W("a1", "t1"), task=["t1"]),
                   dict(W("a1", "t1"), name=5), dict(W("a1", "t1"), rejected="yes")):
            s = S([W("a0", "t0"), ev], TS)
            self.assertEqual((s["valid"], s["Y"], s["distinct_passing"]), (False, None, 1), ev)

    def test_type_keyed_events_are_malformed(self):  # ruling: the scorer input is the episode action log only
        for ev in ({"type": "work", "agent": "a0", "task": "t0", "answer": 10},  # smallest residual case
                   {"type": "release", "agent": "a0", "data": {"item": "t0", "done": True}},  # board shape
                   {"agent": "a0", "task": "t0", "answer": 10}):  # no action key at all
            s = S([ev], TS)
            self.assertEqual((s["valid"], s["Y"], s["distinct_passing"], s["done_releases"]), (False, None, 0, 0), ev)
        self.assertEqual(S([{"type": "work", "agent": "a0", "task": "t0", "answer": 30}], TS)["valid"], False)

    def test_refused_and_unknown_task_releases_are_not_done(self):  # EP1 7, rule 1
        refused = dict(R("a0", "t0"), rejected=True)
        act = {"agent": "a0", "action": "release", "task": "t0", "done": True, "rejected": True}
        s = S([refused, act, R("a0", "t9"), R("a0", "zz")], TS)
        self.assertEqual((s["done_releases"], s["false_done"], s["false_done_rate"]), (0, 0, None))

    def test_release_without_work_is_false_done(self):
        s = S([C("a0", "t0"), R("a0", "t0")], TS)
        self.assertEqual((s["done_releases"], s["false_done"], s["false_done_rate"]), (1, 1, 1.0))

    def test_release_after_passing_work_is_not_false(self):
        s = S([W("a0", "t0"), R("a0", "t0")], TS)
        self.assertEqual((s["false_done"], s["false_done_rate"]), (0, 0.0))

    def test_release_before_work_and_other_agent_work_are_false(self):
        s = S([R("a0", "t0"), W("a0", "t0"), W("a1", "t1"), R("a0", "t1")], TS)
        self.assertEqual((s["done_releases"], s["false_done"]), (2, 2))

    def test_not_done_release_ignored_and_failed_work_false(self):
        s = S([R("a0", "t0", done=False), W("a1", "t1", answer=0, rejected=False), R("a1", "t1")], TS)
        self.assertEqual((s["done_releases"], s["false_done"]), (1, 1))
        s = S([W("a1", "t1", rejected=True), R("a1", "t1")], TS)
        self.assertEqual(s["false_done"], 1)

    def test_done_twice_counts_twice(self):
        s = S([W("a0", "t0"), R("a0", "t0"), R("a0", "t0")], TS)
        self.assertEqual((s["done_releases"], s["false_done"], s["false_done_rate"]), (2, 0, 0.0))
        s = S([R("a0", "t0"), W("a0", "t0"), R("a0", "t0")], TS)
        self.assertEqual((s["done_releases"], s["false_done"], s["false_done_rate"]), (2, 1, 0.5))


def rand_log(rng):
    log = []
    for _ in range(rng.randint(0, 14)):
        a, t = f"a{rng.randrange(4)}", f"t{rng.randrange(7)}"
        k = rng.random()
        if k < .5:
            log.append(W(a, t, answer=rng.choice([None, None, None, 0, 5]), name=rng.choice([None, "", "x", "y"]),
                         rejected=rng.random() < .2))
        elif k < .75:
            log.append(C(a, t))
        else:
            log.append(R(a, t, done=rng.random() < .8))
    return log


class Properties(unittest.TestCase):
    def test_seeded_random_logs(self):
        rng = random.Random(7)
        for _ in range(500):
            log = rand_log(rng)
            s = S(log, TS)
            self.assertEqual(s, S(list(log), TS))  # deterministic, does not mutate
            self.assertLessEqual(s["surviving_passing"], s["distinct_passing"])
            self.assertLessEqual(s["distinct_passing"], 6)
            self.assertEqual(s["Y"], s["distinct_passing"] / 4 if s["valid"] else None)
            self.assertEqual(s["valid"], s["extra_work_events"] == 0 and len(
                [e for e in log if e.get("action") == "work" and not e["rejected"] and e["task"] != "t6"]) <= 4)
            self.assertLessEqual(s["false_done"], s["done_releases"])
            acc = [e for e in log if e["action"] == "work" and not e["rejected"] and e["task"] != "t6"] if all("action" in e for e in log) else None
            if acc is not None:
                self.assertEqual(s["duplicates"], len(acc) - len({e["task"] for e in acc}))
            self.assertEqual(S([e for e in log if _is_claim(e)] + log, TS), s)  # claims never matter
            self.assertEqual(S([dict(e, rejected=True) if e.get("action") == "work" else e for e in log], TS)["distinct_passing"], 0)

    def test_unique_names_survive_all(self):
        rng = random.Random(3)
        for _ in range(200):
            log = [W(f"a{i}", f"t{rng.randrange(6)}", name=f"n{i}") for i in range(rng.randint(0, 4))]
            s = S(log, TS)
            self.assertEqual(s["surviving_passing"], s["distinct_passing"])
            self.assertEqual(s["name_collisions"], 0)


def _is_claim(e):
    return e.get("action") == "claim"


class Gate(unittest.TestCase):
    def test_compare(self):
        a = S([W("a0", "t0")], TS)
        self.assertEqual(alloc2.compare(a, dict(a)), [])
        self.assertEqual(alloc2.compare(a, {"distinct_passing": 0, "extra": 1}), ["distinct_passing: 1 != 0"])

    def test_gate_equal_and_void(self):
        log = [W("a0", "t0")]
        self.assertEqual(alloc2.second_scorer_gate(log, TS, S)["distinct_passing"], 1)
        with self.assertRaises(alloc2.ScorerDisagreement):
            alloc2.second_scorer_gate(log, TS, lambda l, t: dict(S(l, t), duplicates=9))


class Differential(unittest.TestCase):
    def test_against_primary_2000_logs(self):
        try:
            from murmuration.trapbench import alloc
        except ImportError as e:
            self.skipTest(str(e))
        rng, bad = random.Random(20261120), []
        for _ in range(2000):
            log = rand_log(rng)
            ts = alloc.gen(rng.randrange(20), "heldout")
            ids = [t["id"] for t in ts["tasks"]]
            for e in log:  # retarget ids and answers to this primary task set
                if "task" in e and e["task"] != "t6":
                    e["task"] = ids[int(e["task"][1:]) % len(ids)]
                if e.get("action") == "work":
                    e["answer"] = {t["id"]: t["expect"] for t in ts["tasks"]}.get(e["task"]) if e["answer"] in (None,) or e["answer"] not in (0, 5) else e["answer"]
                if e.get("type") == "release":
                    e["data"]["item"] = ids[int(e["data"]["item"][1:]) % len(ids)]
            diff = alloc2.compare(alloc.score(log, ts), alloc2.score(log, ts))
            if diff:
                bad.append((diff, log, ts))
        print(f"\nDIFFERENTIAL: {len(bad)} disagreements in 2000 logs")
        if bad:
            diff, log, ts = min(bad, key=lambda b: len(b[1]))
            print("first minimal:", diff, log, [(t["id"], t["expect"]) for t in ts["tasks"]], sep="\n")
        self.assertEqual(len(bad), 0)


if __name__ == "__main__":
    unittest.main()
