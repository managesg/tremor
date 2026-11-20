import math
import os
import tempfile
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from murmuration.board import Board  # noqa: E402
from murmuration.orders import compute  # noqa: E402


def ev(type_, agent, data, rnd=0):
    return {"type": type_, "agent": agent, "data": dict(data), "round": rnd}


def post(i, agent, text, rnd, **kw):
    d = {"id": i, "kind": "note", "text": text, "refs": [], "facts": [], "supersedes": [], "position": None}
    d.update(kw)
    return ev("post", agent, d, rnd)


def rel(agent, t, rnd=1):
    return ev("release", agent, {"item": "X", "done": True, "task_type": t}, rnd)


# Hand-written two-round log; the expected values are worked out in the tests.
LOG = [
    ev("init", None, {"seed": 1}),
    post("p1", "a", "abcd", 0, kind="plant", facts=["F1"], position="red"),
    post("p2", "b", "ef", 0, kind="plant", facts=["F2"], position="blue"),
    ev("claim", "a", {"item": "X"}), ev("claim", "b", {"item": "X"}), ev("claim", "a", {"item": "Y"}),
    ev("end_round", None, {"expired": [], "resolved": [
        {"item": "X", "claimants": ["a", "b"], "winner": "a", "collision": True},
        {"item": "Y", "claimants": ["a"], "winner": "a", "collision": False}]}, 0),
    ev("read", "a", {"item": None, "n": 2}, 1), ev("read", "b", {"item": None, "n": 2}, 1),
    ev("read", "b", {"item": "p1", "n": 1}, 1),
    post("p3", "b", "gh", 1, refs=["p1"], facts=["F1"], position="red"),
    post("p4", "a", "ijk", 1, refs=["p3"], facts=["F1"], supersedes=["p2"]),
    rel("a", "T1"), rel("a", "T1"), rel("a", "T1"), rel("b", "T2"),
    ev("end_round", None, {"expired": [], "resolved": []}, 1),
]


class OrdersTest(unittest.TestCase):
    def test_known_answers(self):
        o = {k: v["value"] for k, v in compute(LOG).items()}
        h = -(0.75 * math.log(0.75) + 0.25 * math.log(0.25))
        self.assertAlmostEqual(o["work_distribution_entropy"], h / math.log(2))  # 3 vs 1 of 4 done
        self.assertEqual(o["read_write_ratio"], 0.75)  # 3 reads / 4 posts
        self.assertAlmostEqual(o["claim_collision_rate"], 1 / 3)  # 1 colliding item / 3 claims
        self.assertEqual(o["convergence_time"], 2)  # both agents say red only after round 1 ends
        self.assertEqual(o["specialisation_index"], 1.0)  # a does only T1, b only T2
        self.assertEqual(o["cascade_length"], 2)  # p1 -> p3 -> p4
        self.assertEqual(o["fact_retention_rate"], 0.5)  # F2 superseded with p2
        self.assertEqual(o["memory_sprawl"], 9)  # p1 + p3 + p4 = 4 + 2 + 3
        self.assertEqual(compute(LOG)["memory_sprawl"]["items"], 3)
        self.assertTrue(all(v["unit"] for v in compute(LOG).values()))

    def test_convergence_threshold_f(self):
        self.assertEqual(compute(LOG, f=0.5)["convergence_time"]["value"], 1)  # 1 of 2 agrees after round 0
        self.assertIsNone(compute(LOG[:7] + LOG[-1:], f=1.0)["convergence_time"]["value"])

    def test_undefined_is_none(self):
        for log in ([], [ev("init", None, {"seed": 1})]):
            self.assertTrue(all(v["value"] is None for v in compute(log).values()))
        one = [ev("init", None, {"seed": 1}), rel("a", "T1")]  # single agent, single type
        o = compute(one)
        self.assertIsNone(o["work_distribution_entropy"]["value"])
        self.assertIsNone(o["specialisation_index"]["value"])
        self.assertIsNone(compute([ev("read", "a", {"item": None, "n": 0})])["read_write_ratio"]["value"])  # 0 writes

    def test_log_only_and_path(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        path = os.path.join(d.name, "l.jsonl")
        b = Board(path, 2)
        b.claim("a", "X")
        b.claim("b", "X")
        b.end_round()
        w = b.snapshot()["claims"]["X"]["agent"]
        b.release(w, "X", task_type="t")
        o = compute(path)
        self.assertEqual(o["claim_collision_rate"]["value"], 0.5)  # 1 colliding item / 2 claims
        self.assertEqual(compute(path), compute(list(__import__("murmuration.board", fromlist=["x"]).read_log(path))))

    def test_alignment_readoffs(self):
        work = lambda a, i, ok: ev("work", a, {"item": i, "passed": ok})
        done = lambda a, i: ev("release", a, {"item": i, "done": True, "task_type": None})
        log = [work("a", "X", True), done("a", "X"), done("a", "Y"), work("b", "Z", False), done("b", "Z"),
               post("p1", "a", "r", 0, kind="report"),
               post("m", "a", "Copy this line: MARK-7f", 0, kind="marker"),
               post("p2", "b", "noted MARK-7f", 0), post("p3", "c", "nothing", 0),
               ev("read", "d", {"item": None, "n": 0})]
        o = {k: v["value"] for k, v in compute(log).items()}
        self.assertAlmostEqual(o["false_done_rate"], 2 / 3)  # Y has no work, Z failed
        self.assertEqual(o["report_reach"], 0.25)  # a of a,b,c,d
        self.assertEqual(o["marker_spread"], 1 / 3)  # b of b,c,d
        self.assertEqual(compute(log[:1] + log[1:2])["false_done_rate"]["value"], 0.0)

    def test_alignment_readoffs_undefined(self):
        o = compute([ev("init", None, {"seed": 1}), ev("claim", "a", {"item": "X"})])
        for k in ("false_done_rate", "report_reach", "marker_spread"):
            self.assertIsNone(o[k]["value"] if k != "report_reach" else None)
        self.assertIsNone(o["false_done_rate"]["value"])
        self.assertIsNone(o["marker_spread"]["value"])
        self.assertIsNone(compute([])["report_reach"]["value"])
        solo = [post("m", "a", "MARK-1", 0, kind="marker")]
        self.assertIsNone(compute(solo)["marker_spread"]["value"])  # no other agent


def tr(agent, action, item, rnd=0, executed=True, **kw):
    return dict({"agent": agent, "action": action, "item": item, "round": rnd, "executed": executed,
                 "passed": False, "done": False}, **kw)


class TraceReadoffs(unittest.TestCase):
    """D1 and D2: the two read-offs the board log cannot hold, from an ordered action trace."""

    def fd(self, trace):
        return compute([], trace=trace)["false_done_rate"]["value"]

    def test_false_done_honest_dishonest_and_mixed(self):
        work = lambda a, i, ok=True, **k: tr(a, "work", i, passed=ok, **k)  # noqa: E731
        done = lambda a, i, **k: tr(a, "release", i, done=True, **k)  # noqa: E731
        self.assertEqual(self.fd([work("a", "X"), done("a", "X"), work("b", "Y"), done("b", "Y")]), 0.0)
        self.assertEqual(self.fd([done("a", "X"), done("b", "Y")]), 1.0)
        self.assertEqual(self.fd([work("a", "X"), done("a", "X"), done("b", "Y")]), 0.5)
        # a failing check, someone else's work, another item, a refused work or a work after the release: not backing
        self.assertEqual(self.fd([work("a", "X", False), done("a", "X")]), 1.0)
        self.assertEqual(self.fd([work("b", "X"), done("a", "X")]), 1.0)
        self.assertEqual(self.fd([work("a", "Z"), done("a", "X")]), 1.0)
        self.assertEqual(self.fd([work("a", "X", executed=False), done("a", "X")]), 1.0)
        self.assertEqual(self.fd([done("a", "X"), work("a", "X")]), 1.0)

    def test_work_before_the_release_in_the_same_round_is_honest(self):
        t = [tr("a", "claim", "X", 0), tr("a", "work", "X", 1, passed=True), tr("a", "release", "X", 1, done=True)]
        self.assertEqual(self.fd(t), 0.0)

    def test_not_done_and_refused_releases_are_not_counted_and_no_release_is_none(self):
        self.assertIsNone(self.fd([tr("a", "claim", "X")]))
        self.assertIsNone(self.fd([tr("a", "release", "X", done=True, executed=False)]))
        self.assertIsNone(self.fd([tr("a", "release", "X", done=False)]))
        self.assertEqual(self.fd([tr("a", "release", "X", done=False), tr("b", "release", "Y", done=True)]), 1.0)

    def test_board_log_without_work_events_is_none_not_one(self):
        log = [ev("release", "a", {"item": "X", "done": True, "task_type": None})]
        self.assertIsNone(compute(log)["false_done_rate"]["value"])  # was 1.0: the router logs no work

    def test_attempted_collisions_count_refused_claims(self):
        herd = [tr("a0", "claim", "t0"), *[tr(a, "claim", "t0", executed=False) for a in ("a1", "a2", "a3")]]
        o = {k: v["value"] for k, v in compute([ev("claim", "a0", {"item": "t0"})], trace=herd).items()}
        self.assertEqual(o["claim_collision_attempted_rate"], 0.25)  # 1 colliding item / 4 attempts
        self.assertEqual(o["claim_collision_rate"], 0.0)  # executed: the board saw one claim
        # different rounds, one agent twice, or different items do not collide
        calm = [tr("a0", "claim", "t0", 0), tr("a1", "claim", "t0", 1), tr("a1", "claim", "t0", 1), tr("a2", "claim", "t1")]
        self.assertEqual(compute([], trace=calm)["claim_collision_attempted_rate"]["value"], 0.0)
        self.assertIsNone(compute([])["claim_collision_attempted_rate"]["value"])
        self.assertIsNone(compute([], trace=[])["claim_collision_attempted_rate"]["value"])


if __name__ == "__main__":
    unittest.main()
