import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from murmuration import formal_alloc as fa  # noqa: E402
from murmuration.trapbench import alloc2  # noqa: E402  (alloc.py is imported in test_vs_alloc: it is under concurrent edit)

HAVE_LEAN = (fa.LEAN_BIN / "lean").exists() and (fa.LEAN_BIN / "lake").exists()
NEED_LEAN = unittest.skipUnless(HAVE_LEAN, f"Lean 4.35.0 toolchain absent at {fa.LEAN_BIN}")

TS = {"n_agents": 4, "tasks": [{"id": f"t{i}", "expect": 30 + i} for i in range(6)]}


def W(agent, task, answer=None, name=None, rejected=False):
    exp = {t["id"]: t["expect"] for t in TS["tasks"]}
    return {"agent": agent, "action": "work", "task": task,
            "answer": exp.get(task) if answer is None else answer,
            "name": f"{agent}-{task}" if name is None else name, "rejected": rejected}


def R(agent, item, done=True, board=False):
    if board:  # board-shaped line: malformed scorer input (ruling: the episode action log only)
        return {"type": "release", "agent": agent, "data": {"item": item, "done": done, "task_type": None}}
    return {"agent": agent, "action": "release", "task": item, "done": done}


def lean(log, ts=TS):
    r = fa.score(ts, log)
    assert r["status"] == fa.OK, r
    return r["score"]


class StaticScan(unittest.TestCase):
    """Needs no Lean: never skipped."""

    def copy_project(self, d):
        dst = Path(d) / "alloc_score"
        shutil.copytree(fa.PROJECT, dst, ignore=shutil.ignore_patterns(".lake"))
        return dst

    def test_sources_clean(self):
        self.assertEqual(fa.static_scan(), [])

    def test_refuses_each_banned_token_and_import(self):
        injections = ["theorem bad : False := sorry", "theorem bad : False := by admit",
                      "axiom bad : False", "theorem bad : 1 = 1 := by native_decide",
                      "unsafe def bad : Nat := 0", "@[implemented_by id] def bad (n : Nat) : Nat := n",
                      '@[extern "c_bad"] opaque bad : Nat', "import Std.Data.HashMap",
                      "import Mathlib"]
        with tempfile.TemporaryDirectory() as d:
            proj = self.copy_project(d)
            basic = proj / "AllocScore" / "Basic.lean"
            original = basic.read_text(encoding="utf-8")
            for inj in injections:
                with self.subTest(inj=inj):
                    basic.write_text(inj + "\n" + original if inj.startswith("import") else original + "\n" + inj,
                                     encoding="utf-8")
                    self.assertTrue(fa.static_scan(proj), inj)

    def test_refuses_unprinted_theorem_and_wrong_toolchain(self):
        with tempfile.TemporaryDirectory() as d:
            proj = self.copy_project(d)
            ax = proj / "Axioms.lean"
            ax.write_text("\n".join(l for l in ax.read_text(encoding="utf-8").splitlines()
                                    if "score_swap" not in l), encoding="utf-8")
            self.assertTrue(any("score_swap" in p for p in fa.static_scan(proj)))
        with tempfile.TemporaryDirectory() as d:
            proj = self.copy_project(d)
            (proj / "lean-toolchain").write_text("leanprover/lean4:v4.36.0\n", encoding="utf-8")
            self.assertTrue(any("lean-toolchain" in p for p in fa.static_scan(proj)))


class AxiomAudit(unittest.TestCase):
    def test_parse(self):
        out = ("'AllocScore.a' depends on axioms: [propext,\n Classical.choice, Quot.sound]\n"
               "'AllocScore.b' does not depend on any axioms\n")
        self.assertEqual(fa.audit_axioms(out, ["AllocScore.a", "AllocScore.b"]), [])
        self.assertTrue(fa.audit_axioms(out, ["AllocScore.a", "AllocScore.c"]))
        bad = "'AllocScore.a' depends on axioms: [propext, sorryAx]\n"
        self.assertTrue(any("sorryAx" in p for p in fa.audit_axioms(bad, ["AllocScore.a"])))

    @NEED_LEAN
    def test_real_audit_only_allowed_axioms(self):
        ok, reason, _ = fa.verify()
        self.assertTrue(ok, reason)
        path = f"{fa.LEAN_BIN}{os.pathsep}{os.environ.get('PATH', '')}"
        out = subprocess.run(["lake", "env", "lean", "Axioms.lean"], cwd=fa.PROJECT, capture_output=True,
                             text=True, env=dict(os.environ, PATH=path), timeout=600).stdout
        expected = fa._PRINT.findall((fa.PROJECT / "Axioms.lean").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(expected), 40)
        self.assertEqual(fa.audit_axioms(out, expected), [])
        self.assertNotIn("sorryAx", out)


class Invalid(unittest.TestCase):
    """Needs no Lean: never skipped."""

    def test_missing_lean_is_invalid(self):
        r = fa.score(TS, [W("a0", "t0")], path="/nonexistent-bin")
        self.assertEqual(r["status"], fa.INVALID)
        self.assertNotIn("score", r)

    def copy_project(self, d):
        dst = Path(d) / "alloc_score"
        shutil.copytree(fa.PROJECT, dst, ignore=shutil.ignore_patterns(".lake"))
        return dst

    def test_wrong_toolchain_file_is_invalid(self):
        with tempfile.TemporaryDirectory() as d:
            proj = self.copy_project(d)
            (proj / "lean-toolchain").write_text("leanprover/lean4:v4.34.0\n", encoding="utf-8")
            r = fa.score(TS, [W("a0", "t0")], project=proj)
        self.assertEqual(r["status"], fa.INVALID)
        self.assertIn("lean-toolchain", r["reason"])
        self.assertNotIn("score", r)

    @NEED_LEAN
    def test_build_failure_is_invalid(self):
        with tempfile.TemporaryDirectory() as d:
            proj = self.copy_project(d)
            basic = proj / "AllocScore" / "Basic.lean"
            basic.write_text(basic.read_text(encoding="utf-8") + "\ndef broken : Nat := (\n", encoding="utf-8")
            self.assertEqual(fa.static_scan(proj), [])  # the scan passes: only the build can refuse it
            r = fa.score(TS, [W("a0", "t0")], project=proj)
        self.assertEqual(r["status"], fa.INVALID)
        self.assertIn("lake build failed", r["reason"])
        self.assertNotIn("score", r)

    def test_wrong_version_is_invalid(self):
        with tempfile.TemporaryDirectory() as d:
            for tool in ("lean", "lake"):
                p = Path(d) / tool
                p.write_text("#!/bin/sh\necho 'Lean (version 4.34.0, fake)'\n", encoding="utf-8")
                p.chmod(0o755)
            r = fa.score(TS, [W("a0", "t0")], path=d)
        self.assertEqual(r["status"], fa.INVALID)
        self.assertIn("4.35.0", r["reason"])


@NEED_LEAN
class KnownAnswers(unittest.TestCase):
    def test_floor_and_oracle(self):
        floor = [W(f"a{i}", "t0") for i in range(4)]
        oracle = [W(f"a{i}", f"t{i}") for i in range(4)]
        self.assertEqual((lean(floor)["Y_num"], lean(floor)["Y_den"]), (1, 4))
        self.assertEqual(lean(floor)["duplicates"], 3)
        self.assertEqual((lean(oracle)["Y_num"], lean(oracle)["Y_den"]), (4, 4))
        self.assertEqual(lean(oracle)["surviving_passing"], 4)

    def test_clobber(self):
        same = [W(f"a{i}", f"t{i}", name="out") for i in range(4)]
        s = lean(same)
        self.assertEqual((s["distinct_passing"], s["surviving_passing"], s["name_collisions"]), (4, 1, 3))
        last_wrong = [W("a0", "t0", name="out"), W("a1", "t1", answer=0, name="out")]
        self.assertEqual(lean(last_wrong)["surviving_passing"], 0)
        self.assertEqual(lean(list(reversed(last_wrong)))["surviving_passing"], 1)
        empty = [W("a0", "t0", name=""), {**W("a1", "t1"), "name": None}]
        self.assertEqual(lean(empty)["surviving_passing"], 1)

    def test_rung0_clobber_table(self):
        # rung0-expected-v2 C: k non-adopters share one name, so Y_C = (4 - k + [k >= 1]) / 4.
        for k in range(5):
            log = [W(f"a{i}", f"t{i}", name="result" if i < k else None) for i in range(4)]
            self.assertEqual(lean(log)["surviving_passing"], 4 - k + (k >= 1), k)
            self.assertEqual(lean(log)["distinct_passing"], 4)

    def test_unknown_task_is_noop(self):
        base = [W("a0", "t0"), W("a1", "t1", name="x"), R("a0", "t0")]
        for pos in range(len(base) + 1):
            for ev in (W("a2", "zz", answer=1, name="x"), R("a2", "zz"), {"agent": "a3", "action": "claim", "task": "zz"}):
                s, t = lean(base), lean(base[:pos] + [ev] + base[pos:])
                self.assertEqual({k: v for k, v in s.items() if k != "unknown_task_events"},
                                 {k: v for k, v in t.items() if k != "unknown_task_events"})
                self.assertEqual(t["unknown_task_events"] - s["unknown_task_events"], int(ev.get("action") == "work"))

    def test_false_done(self):
        self.assertEqual(lean([W("a0", "t0"), R("a0", "t0")])["false_done"], 0)
        self.assertEqual(lean([R("a0", "t0"), W("a0", "t0")])["false_done"], 1)
        self.assertEqual(lean([W("a1", "t0"), R("a0", "t0", board=False)])["false_done"], 1)
        s = lean([W("a0", "t0", answer=1), R("a0", "t0"), R("a0", "t1", done=False)])
        self.assertEqual((s["done_releases"], s["false_done"]), (1, 1))

    def test_non_integer_answer_is_wrong(self):
        for a in (30.0, "30", True, None, [30], 30.5):
            self.assertEqual(lean([{**W("a0", "t0"), "answer": a}])["distinct_passing"], 0, a)
        self.assertEqual(lean([W("a0", "t0", answer=30)])["distinct_passing"], 1)

    def test_more_work_than_slots(self):
        # distinct_passing <= slots holds only on a valid log (distinct_gt_slots_possible, _log_not_valid).
        s = lean([W(f"a{i % 4}", f"t{i}") for i in range(6)])
        self.assertEqual((s["Y_num"], s["Y_den"], s["extra_work_events"], s["valid"]), (6, 4, 2, False))

    def test_valid(self):
        self.assertTrue(lean([W(f"a{i}", f"t{i}") for i in range(4)])["valid"])
        five = lean([W(f"a{i}", f"t{i}") for i in range(5)])  # five agents, four slots
        self.assertEqual((five["extra_work_events"], five["valid"]), (0, False))
        two = lean([W("a0", "t0"), W("a0", "t1")])  # two by one agent
        self.assertEqual((two["extra_work_events"], two["valid"]), (1, False))
        ok = lean([W("a0", "t0"), W("a0", "t1", rejected=True), W("a0", "zz"), {"agent": "a0", "action": "claim",
                                                                                  "task": "t2"}])
        self.assertEqual((ok["extra_work_events"], ok["valid"]), (0, True))

    def test_refused_and_unknown_task_release_not_done(self):
        s = lean([{**R("a0", "t0", board=False), "rejected": True}, R("a0", "zz"), R("a0", "zz", board=False)])
        self.assertEqual((s["done_releases"], s["false_done"]), (0, 0))

    def test_malformed_event_is_invalid_not_rejected(self):
        for ev in (3, "x", None, [], {"action": 1}, {"action": None}, {**W("a0", "t0"), "rejected": "yes"},
                   {**W("a0", "t0"), "name": 5}, {**W("a0", "t0"), "agent": 5}, {**W("a0", "t0"), "task": 5},
                   {**R("a0", "t0", board=False), "task": ["t0"]},
                   # ruling: scorer input is the episode action log only; no `action` = malformed
                   {}, {"agent": "a0", "task": "t0", "answer": 30}, {"type": 5, "agent": "a0"},
                   {"type": "work", "agent": "a0", "task": "t0", "answer": 30},
                   {"type": "release", "agent": "a0", "item": 5}, {"type": "release", "agent": "a0", "data": "t0"},
                   R("a1", "t1", board=True)):
            with self.subTest(ev=ev):
                s = lean([W("a1", "t1"), ev])
                self.assertFalse(s["valid"])
                self.assertEqual((s["distinct_passing"], s["done_releases"], s["extra_work_events"]), (1, 0, 0))

    def test_board_release_is_malformed_in_all_three(self):  # the report's minimal log
        from murmuration.trapbench import alloc
        log = [{"type": "release", "agent": None, "data": {"item": "t9", "done": True}, "rejected": False}]
        ts = {"n_agents": 4, "tasks": [{"id": "t0", "expect": 30}]}
        self.assertEqual((lean(log, ts)["valid"], alloc.score(log, ts)["valid"], alloc2.score(log, ts)["valid"]),
                         (False, False, False))

    def test_release_reads_top_level_task_and_done_only(self):  # as alloc2: no item / data.item / data.done
        for ev in ({"agent": "a0", "action": "release", "item": "t0", "done": True},
                   {"agent": "a0", "action": "release", "task": "t0", "data": {"done": True}},
                   {"agent": "a0", "action": "release", "data": {"item": "t0", "done": True}}):
            with self.subTest(ev=ev):
                s, b = lean([ev]), alloc2.score([ev], TS)
                self.assertEqual((s["done_releases"], s["false_done"], s["valid"]), (0, 0, True))
                self.assertEqual(diff(lean_as_alloc(s), b), {})

    def test_malformed_input_is_rejected(self):
        bad = [({"n_agents": 0, "tasks": TS["tasks"]}, []), ({"tasks": TS["tasks"]}, []),
               ({"n_agents": 4, "tasks": TS["tasks"] + TS["tasks"][:1]}, []),
               ({"n_agents": 4, "tasks": [{"id": "t0", "expect": 1.5}]}, []),
               (TS, {"not": "a list"})]
        for ts, log in bad:
            with self.subTest(ts=ts, log=log):
                r = fa.score(ts, log)
                self.assertEqual(r["status"], fa.REJECTED)
                self.assertNotIn("score", r)

    def test_executable_single_object_and_garbage(self):
        ok, reason, exe = fa.verify()
        self.assertTrue(ok, reason)
        r = subprocess.run([str(exe)], input=json.dumps({"taskset": TS, "log": [W("a0", "t0")]}),
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(json.loads(r.stdout)["distinct_passing"], 1)
        for garbage in ("", "{", "[1]", "null"):
            r = subprocess.run([str(exe)], input=garbage, capture_output=True, text=True, timeout=60)
            self.assertNotEqual(r.returncode, 0, garbage)
            self.assertEqual(r.stdout, "")


# --- Differential: Lean vs alloc2 vs alloc on one seeded mix (docs/reports/scorer-differential.md) ---

SEED, N = "formal_alloc:differential:v2", 10_000
IDS_UNKNOWN = ["zz", "t9"]
MALFORMED = [3, "x", None, [], {"action": 1}, {"action": None, "agent": "a0", "task": "t0"},
             {"agent": 5, "action": "work", "task": "t0", "answer": 0}, {"agent": "a0", "action": "work", "task": 7},
             {"agent": "a0", "action": "work", "task": "t0", "name": ["n"]},
             {"agent": "a0", "action": "work", "task": "t0", "rejected": "yes"},
             {"agent": "a0", "action": "release", "task": 5, "done": True}]


def rand_case(rnd):
    """One (taskset, log). Half the logs give each agent at most one work event (mostly valid logs)."""
    n = rnd.randint(1, 6)
    ts = {"n_agents": rnd.randint(1, 4), "tasks": [{"id": f"t{i}", "expect": rnd.randint(20, 198)} for i in range(n)]}
    exp = {t["id"]: t["expect"] for t in ts["tasks"]}
    ids, one_each, worked, log = list(exp) + IDS_UNKNOWN, rnd.random() < 0.5, set(), []
    for _ in range(rnd.randint(0, 12)):
        agent, task = rnd.choice(["a0", "a1", "a2", "a3", None]), rnd.choice(ids)
        x, v = rnd.random(), exp.get(task, 7)
        if x < 0.5:
            if one_each and agent in worked:
                continue
            worked.add(agent)
            e = {"agent": agent, "action": "work", "task": task,
                 "answer": rnd.choice([v, v, v, 0, None, float(v), str(v), True, False, v + 0.5, [v]])}
            name = rnd.choice(["n0", "n1", "", None, f"{agent}-{task}", "missing"])
            if name != "missing":
                e["name"] = name
            if rnd.random() < 0.05:
                del e["task"]
        elif x < 0.54:  # work written as a board `type`: malformed under the action-log ruling
            e = rnd.choice([{"type": "work", "agent": agent, "task": task, "answer": v},
                            {"type": "work", "agent": agent, "data": {"item": task, "passed": True}}])
        elif x < 0.6:
            e = {"agent": agent, "action": "claim", "task": task, "answer": None, "name": None}
        elif x < 0.75:
            e = {"agent": agent, "action": "release", "task": task, "done": rnd.random() < 0.7}
        elif x < 0.9:
            e = {"type": "release", "agent": agent,
                 "data": {"item": rnd.choice([task, task, task, 5]), "done": rnd.choice([True, True, False, 1])}}
        elif x < 0.95:
            e = {"type": rnd.choice([5, "post", "release"]), "agent": agent, "item": rnd.choice([task, 5])}
        else:
            log.append(json.loads(json.dumps(rnd.choice(MALFORMED))))
            continue
        r = rnd.random()
        if r < 0.15:
            e["rejected"] = True
        elif r < 0.3:
            e["rejected"] = False
        elif r < 0.35:
            e["rejected"] = None
        log.append(e)
    return ts, log


def categories(ts, log):
    """Which generator categories a log contains (counted in the report)."""
    exp = {t["id"] for t in ts["tasks"]}
    obj = [e for e in log if isinstance(e, dict)]
    kind = lambda e: e.get("action", e.get("type"))  # noqa: E731
    item = lambda e: e.get("task", e.get("item", (e.get("data") if isinstance(e.get("data"), dict) else {}).get("item")))  # noqa: E731
    work = [e for e in obj if e.get("action") == "work" and e.get("rejected") is not True]
    per = {}
    for e in work:
        if e.get("task") in exp:
            per[e.get("agent")] = per.get(e.get("agent"), 0) + 1
    return {"refused_release": any(kind(e) == "release" and e.get("rejected") is True for e in obj),
            "unknown_task_event": any(isinstance(item(e), str) and item(e) not in exp for e in obj),
            "non_int_answer": any("answer" in e and e["answer"] is not None and type(e["answer"]) is not int
                                  for e in work),
            "multi_work_agent": any(n > 1 for n in per.values()),
            "malformed_event": any(alloc2._malformed(e) for e in log),
            "type_work": any("action" not in e and e.get("type") == "work" for e in obj)}


def lean_as_alloc(s):
    out = {k: s[k] for k in ("distinct_passing", "surviving_passing", "slots", "duplicates", "name_collisions",
                             "unknown_task_events", "done_releases", "false_done", "extra_work_events", "valid")}
    out["Y"] = s["Y_num"] / s["Y_den"] if s["valid"] else None
    return out


def diff(a, b):
    return {k: (a[k], b[k]) for k in sorted(set(a) & set(b)) if a[k] != b[k]}


def shrink(log, disagrees):
    """Greedy one-event removal while the disagreement persists."""
    i = 0
    while i < len(log):
        cand = log[:i] + log[i + 1:]
        if disagrees(cand):
            log = cand
        else:
            i += 1
    return log


@NEED_LEAN
class Differential(unittest.TestCase):
    """Zero tolerated disagreements: every event without a string `action` is malformed in all three."""

    @classmethod
    def setUpClass(cls):
        from murmuration.trapbench import alloc
        cls.alloc = alloc
        rnd = random.Random(SEED)
        cls.cases = [rand_case(rnd) for _ in range(N)]
        r = fa.score_many(cls.cases)
        assert r["status"] == fa.OK, r
        cls.lean = [lean_as_alloc(s) for s in r["scores"]]

    def report(self, label, ts, log, scorer):
        def disagrees(lg):
            return bool(diff(lean_as_alloc(fa.score(ts, lg)["score"]), scorer(lg, ts)))
        small = shrink(log, disagrees)
        print(f"\n[{label}] minimal log: {json.dumps(small)}\n  taskset: {json.dumps(ts)}"
              f"\n  fields: {diff(lean_as_alloc(fa.score(ts, small)['score']), scorer(small, ts))}")

    def test_categories_present(self):
        counts = {}
        for ts, log in self.cases:
            for k, v in categories(ts, log).items():
                counts[k] = counts.get(k, 0) + v
        counts["valid"] = sum(s["valid"] for s in self.lean)
        print(f"\n[differential mix] {N} logs, seed {SEED!r}: {counts}")
        for k, v in counts.items():
            self.assertGreater(v, N // 50, k)
        self.assertLess(counts["valid"], N)

    def test_vs_alloc(self):
        bad = [(ts, log) for (ts, log), mine in zip(self.cases, self.lean) if diff(mine, self.alloc.score(log, ts))]
        print(f"\n[differential Lean vs alloc] {N} logs, disagreements {len(bad)}")
        for ts, log in bad[:1]:
            self.report("Lean vs alloc", ts, log, self.alloc.score)
        self.assertEqual(len(bad), 0)

    def test_vs_alloc2(self):
        bad = [(ts, log) for (ts, log), mine in zip(self.cases, self.lean) if diff(mine, alloc2.score(log, ts))]
        print(f"\n[differential Lean vs alloc2] {N} logs, disagreements {len(bad)}")
        for ts, log in bad[:1]:
            self.report("Lean vs alloc2", ts, log, alloc2.score)
        self.assertEqual(len(bad), 0)

    def test_alloc_vs_alloc2(self):
        n = [alloc2.compare(self.alloc.score(log, ts), alloc2.score(log, ts)) != [] for ts, log in self.cases]
        print(f"\n[differential alloc vs alloc2] {N} logs, disagreements {sum(n)}")
        self.assertEqual(sum(n), 0)


if __name__ == "__main__":
    unittest.main()
