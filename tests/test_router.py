import json
import os
import sys
import subprocess
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from murmuration import cell, router  # noqa: E402

POL = {"allow": ["read"], "deny": ["write"], "max_tokens": 1000, "max_seconds": 10}
EXTRACT = {"id": "t1", "class": "extract", "payload": {"text": "b a b c"}, "expect": ["a", "b", "c"], "cell": "s"}


class RouterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = self.tmp.name

    def mk(self, cid, kind, model, pol=POL):
        return cell.create(os.path.join(self.d, cid), cid, kind, model, pol)

    def test_contract_same_spec_stub_and_strong(self):
        stub, strong = self.mk("s", "stub", "scripted-stub"), self.mk("h", "scripted_strong", "scripted-strong")
        b1, b2 = router.run_task(EXTRACT, stub), router.run_task(EXTRACT, strong)
        self.assertEqual((b1["status"], b2["status"]), ("done", "done"))
        self.assertEqual(b1["result"], b2["result"])
        self.assertEqual(set(b1), set(b2))  # no new file type or field
        self.assertTrue(router.verify(EXTRACT, b1, self.d) and router.verify(EXTRACT, b2, self.d))

    def test_plan_task_cost_in_bundle(self):
        strong = self.mk("h", "scripted_strong", "scripted-strong")
        plan = {"id": "p1", "class": "plan", "payload": {"goal": "g", "steps": ["x y", "z"]}}
        b = router.run_task(plan, strong)
        self.assertEqual(b["class"], "plan")
        self.assertGreater(b["cost"]["tokens_in"] + b["cost"]["tokens_out"], 0)
        self.assertGreater(b["cost"]["seconds"], 0)
        self.assertEqual([s["class"] for s in b["result"]], ["extract", "extract"])
        with open(os.path.join(strong, "outbox", "p1.json")) as f:
            self.assertEqual(json.load(f)["cost"], b["cost"])

    def test_planned_specs_run_on_a_stub(self):
        strong, stub = self.mk("h", "scripted_strong", "scripted-strong"), self.mk("s", "stub", "scripted-stub")
        steps = router.run_task({"id": "p", "class": "plan", "payload": {"goal": "g", "steps": ["a b"]}}, strong)["result"]
        self.assertEqual(router.run_task(steps[0], stub)["result"], ["a", "b"])

    def test_ceiling_deny_wins_and_default_deny(self):
        c = self.mk("s", "stub", "scripted")
        for act in ("write", "net"):
            b = router.run_task(dict(EXTRACT, id="t-" + act, actions=["read", act]), c)
            self.assertEqual((b["status"], b["actions_denied"], b["result"]), ("escalate", [act], None))
        self.assertEqual(router.run_task(dict(EXTRACT, id="t-ok", actions=["read"]), c)["status"], "done")

    def test_budget_tokens_and_time(self):
        strong = self.mk("h", "scripted_strong", "scripted")
        self.assertEqual(router.run_task(dict(EXTRACT, budget={"tokens": 1}), strong)["status"], "budget_exceeded")
        self.assertEqual(router.run_task(dict(EXTRACT, id="t-slow", extra_seconds=60.0), strong)["status"], "budget_exceeded")
        tight = self.mk("t", "stub", "scripted", dict(POL, max_tokens=1))
        self.assertEqual(router.run_task(EXTRACT, tight)["status"], "budget_exceeded")

    def test_same_model_cannot_verify_without_deterministic_check(self):
        a, b = self.mk("a", "stub", "scripted-a"), self.mk("b", "scripted_strong", "scripted-b")  # one family
        spec = {"id": "t2", "class": "extract", "payload": {"text": "q"}, "cell": "a"}  # no expect
        bundle = router.run_task(spec, a)
        with self.assertRaises(router.IndependenceError):
            router.verify(spec, bundle, self.d, verifier_dir=b)
        with self.assertRaises(router.IndependenceError):
            router.verify(spec, bundle, self.d)
        self.assertTrue(router.verify(dict(spec, expect=["q"]), bundle, self.d, verifier_dir=b))  # deterministic check
        other = self.mk("c", "scripted_strong", "claude-opus-5-5")
        self.assertFalse(router.verify(spec, bundle, None, verifier_dir=other))  # no cell root: cannot anchor
        self.assertFalse(router.verify(dict(spec, expect=["q"]), bundle, None))  # not on the expect path either
        self.assertTrue(router.verify(spec, bundle, self.d, verifier_dir=other))

    def test_run_dir_reads_specs_and_logs_chain(self):
        self.mk("s", "stub", "scripted")
        td = os.path.join(self.d, "tasks")
        os.makedirs(td)
        for i in range(2):
            with open(os.path.join(td, f"{i}.json"), "w") as f:
                json.dump(dict(EXTRACT, id=f"t{i}", cell="s"), f)
        bs = router.run_dir(td, self.d)
        self.assertEqual([b["task_id"] for b in bs], ["t0", "t1"])
        self.assertTrue(cell.verify_log(os.path.join(self.d, "s"), bs[-1]["log_head"]))

    def test_log_entry_carries_cost(self):  # kills: cost dropped from the log entry
        c = self.mk("s", "stub", "scripted")
        b = router.run_task(EXTRACT, c)
        with open(os.path.join(c, "log.jsonl")) as f:
            e = json.loads(f.readline())["entry"]
        self.assertEqual((e["task"], e["status"], e["cost"], e["actions"]), ("t1", "done", b["cost"], []))

    def test_plan_cost_both_sides_positive(self):  # kills: plan tokens_in zeroed
        b = router.run_task({"id": "p", "class": "plan", "payload": {"goal": "g", "steps": ["x y z w v u t s"]}},
                            self.mk("s", "stub", "scripted"))
        self.assertGreater(b["cost"]["tokens_in"], 0)
        self.assertGreater(b["cost"]["tokens_out"], 0)

    def test_deny_wins_over_allow(self):  # kills: allow-list only
        c = self.mk("s", "stub", "scripted", dict(POL, allow=["read", "write"], deny=["write"]))
        b = router.run_task(dict(EXTRACT, actions=["write"]), c)
        self.assertEqual((b["status"], b["actions_denied"]), ("escalate", ["write"]))

    def test_task_id_path_traversal(self):
        c = self.mk("s", "stub", "scripted")
        for bad in ("../../escape/pwn", "../x", "a/b", "", "..", "/abs/x", "a\\b"):
            with self.assertRaises(ValueError):
                router.run_task(dict(EXTRACT, id=bad), c)
        self.assertFalse(os.path.exists(os.path.join(self.d, "escape")))

    def test_cell_name_path_traversal_in_run_dir(self):
        self.mk("s", "stub", "scripted")
        outside = os.path.join(self.tmp.name + "-outside")
        self.addCleanup(lambda: __import__("shutil").rmtree(outside, ignore_errors=True))
        cell.create(outside, "o", "stub", "scripted", POL)
        for bad in (outside, "../" + os.path.basename(outside), ".."):
            td = os.path.join(self.d, "tasks")
            os.makedirs(td, exist_ok=True)
            with open(os.path.join(td, "0.json"), "w") as f:
                json.dump(dict(EXTRACT, cell=bad), f)
            with self.assertRaises(ValueError):
                router.run_dir(td, self.d)
        self.assertFalse(os.path.exists(os.path.join(outside, "outbox")))

    def test_cell_symlink_escape_in_run_dir(self):
        outside = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(outside, ignore_errors=True))
        cell.create(os.path.join(outside, "o"), "o", "stub", "scripted", POL)
        os.symlink(os.path.join(outside, "o"), os.path.join(self.d, "link"))
        td = os.path.join(self.d, "tasks")
        os.makedirs(td)
        with open(os.path.join(td, "0.json"), "w") as f:
            json.dump(dict(EXTRACT, cell="link"), f)
        with self.assertRaises(ValueError):
            router.run_dir(td, self.d)

    def test_verifier_rejects_a_wrong_answer_but_accepts_the_right_one(self):
        a, v = self.mk("a", "stub", "scripted"), self.mk("v", "scripted_strong", "claude-opus-5-5")
        spec = {"id": "t3", "class": "extract", "payload": {"text": "b a"}, "cell": "a"}
        good = router.run_task(spec, a)
        self.assertTrue(router.verify(spec, good, self.d, verifier_dir=v))
        self.assertFalse(router.verify(spec, dict(good, result=["totally", "wrong"]), self.d, verifier_dir=v))
        plan = {"id": "p9", "class": "plan", "payload": {"goal": "g", "steps": ["x y"]}, "cell": "a"}
        pb = router.run_task(plan, a)
        self.assertTrue(router.verify(plan, pb, self.d, verifier_dir=v))
        self.assertFalse(router.verify(plan, dict(pb, result=[]), self.d, verifier_dir=v))
        real = cell.work  # a worker that honestly logs a wrong answer: anchoring holds, the verifier cell rejects it
        with mock.patch.object(cell, "work", lambda c, sp: dict(real(c, sp), answer=["wrong"])):
            bad = router.run_task(dict(spec, id="t3w"), a)
        self.assertFalse(router.verify(dict(spec, id="t3w"), bad, self.d, verifier_dir=v))
        self.assertTrue(router.verify(dict(spec, id="t3w", expect=["wrong"]), bad, self.d))  # anchored, as logged

    def test_bundle_bound_to_its_spec(self):
        a = self.mk("a", "stub", "scripted")
        sa = {"id": "A", "class": "extract", "payload": {"text": "q"}, "expect": ["q"], "cell": "a"}
        sb = {"id": "B", "class": "extract", "payload": {"text": "q"}, "expect": ["q"], "cell": "a"}
        ba = router.run_task(sa, a)
        self.assertTrue(router.verify(sa, ba, self.d))
        self.assertFalse(router.verify(sb, ba, self.d))  # other task id
        self.assertFalse(router.verify(dict(sa, payload={"text": "z"}), ba, self.d))  # same id, other payload

    def test_model_identity_alias_case_and_forged_bundle(self):
        a = self.mk("a", "stub", "claude-haiku-5-5")
        spec = {"id": "t4", "class": "extract", "payload": {"text": "q"}, "cell": "a"}
        bundle = router.run_task(spec, a)
        for i, alias in enumerate(("claude-haiku-5-5-20261001", "Claude-Haiku-5-5 ", "CLAUDE-HAIKU-5-5")):
            v = self.mk(f"v{i}", "scripted_strong", alias)
            with self.assertRaises(router.IndependenceError):
                router.verify(spec, bundle, self.d, verifier_dir=v)
        vy = self.mk("vy", "stub", "claude-haiku-5-5")
        self.assertFalse(router.verify(spec, dict(bundle, model="claude-opus-5-5"), self.d, verifier_dir=vy))
        with open(os.path.join(a, "cell.json"), "w") as f:  # cell.json and bundle relabelled together after the run
            json.dump({"id": "a", "kind": "stub", "model": "claude-opus-5-5"}, f)
        self.assertFalse(router.verify(spec, dict(bundle, model="claude-opus-5-5"), self.d, verifier_dir=vy))

    def test_missing_limits_never_mean_unlimited(self):
        c = self.mk("s", "stub", "scripted")
        with open(os.path.join(c, "policy.json"), "w") as f:
            json.dump({"allow": ["read"], "deny": []}, f)
        with self.assertRaises(ValueError):
            router.run_task(EXTRACT, c)
        with self.assertRaises(ValueError):
            self.mk("t", "stub", "scripted", {"allow": ["read"], "deny": []})

    def test_bundles_reproducible_and_plan_ids_distinct(self):
        b1 = router.run_task(EXTRACT, self.mk("s1", "stub", "scripted"))
        b2 = router.run_task(EXTRACT, cell.create(os.path.join(self.d, "copy", "s1"), "s1", "stub", "scripted", POL))
        # same cell (id, kind, model, policy) under another root: the log line binds the cell, so identical
        self.assertEqual((b1["cost"], b1["log_head"]), (b2["cost"], b2["log_head"]))
        s = self.mk("s3", "stub", "scripted")
        ids = [router.run_task({"id": f"p{i}", "class": "plan", "payload": {"goal": "g", "steps": ["a"]}}, s)["result"][0]["id"]
               for i in (1, 2)]
        self.assertEqual(len(set(ids)), 2)

    def test_two_racing_bundle_writers_one_success(self):
        """kills: no cell lock around check, append and exclusive create (orphan log lines, forked chain,
        double success). 2 processes, same task, same cell, 10 trials."""
        src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
        code = (f"import os, sys, time, json; sys.path.insert(0, {src!r})\n"
                "from murmuration import router\n"
                "while not os.path.exists(sys.argv[2]): time.sleep(0.0005)\n"
                "try:\n    router.run_task(json.loads(sys.argv[3]), sys.argv[1]); print('ok')\n"
                "except ValueError as e:\n    print('refused', e)\n")
        self.mk("s", "stub", "scripted")  # the cell EXTRACT names; each r<trial> has the same policy
        for trial in range(10):
            c = self.mk(f"r{trial}", "stub", "scripted")
            go = os.path.join(self.d, f"go{trial}")
            ps = [subprocess.Popen([sys.executable, "-B", "-I", "-c", code, c, go, json.dumps(EXTRACT)],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(2)]
            open(go, "w").close()
            outs = [p.communicate(timeout=60) for p in ps]
            self.assertEqual(sorted((o[0].split() or ["crashed"])[0] for o in outs), ["ok", "refused"], (trial, outs))
            self.assertEqual(cell.log_count(c), 1, trial)  # no orphan line from the refused writer
            self.assertTrue(cell.verify_log(c), trial)
            with open(os.path.join(c, "outbox", "t1.json")) as f:
                self.assertTrue(router.verify(EXTRACT, json.load(f), self.d))

    def test_spec_named_strict_cell_run_on_a_lax_cell_is_rejected(self):
        """kills: spec["cell"] not bound (R4 probe: accepted on both paths)."""
        self.mk("strict", "stub", "scripted", dict(POL, deny=["write", "net"]))
        lax = self.mk("lax", "stub", "scripted", dict(POL, allow=["read", "net"]))
        v = self.mk("v", "scripted_strong", "claude-opus-5-5")
        spec = dict(EXTRACT, id="sl", cell="strict", actions=["read", "net"])
        b = router.run_task(spec, lax)
        self.assertEqual(b["status"], "done")
        self.assertFalse(router.verify(spec, b, self.d))
        self.assertFalse(router.verify({k: x for k, x in spec.items() if k != "expect"}, b, self.d, verifier_dir=v))
        self.assertEqual(router.run_task(spec, cell.join(self.d, "strict"))["status"], "escalate")
        with open(os.path.join(lax, "log.jsonl")) as f:  # the log records which cell ran, and its policy hash
            e = json.loads(f.readline())["entry"]
        self.assertEqual((e["cell"], e["policy_sha256"]), ("lax", router._h(cell.load(lax)[1])))

    def test_bundle_create_is_exclusive_even_if_the_exists_check_misses(self):
        """kills: the bundle write not exclusive (masked by the lexists check)."""
        c = self.mk("s", "stub", "scripted")
        router.run_task(EXTRACT, c)
        path = os.path.join(c, "outbox", "t1.json")
        before = open(path).read()
        with mock.patch.object(router.os.path, "lexists", lambda p: False), self.assertRaises(FileExistsError):
            router.run_task(EXTRACT, c)
        self.assertEqual(open(path).read(), before)


if __name__ == "__main__":
    unittest.main()
