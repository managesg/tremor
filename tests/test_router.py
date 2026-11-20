import json
import os
import sys
import subprocess
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from murmuration import board as boardmod, cell, router  # noqa: E402

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


class ActTests(unittest.TestCase):
    """A7': router.act routes every board action through enforce.PREDICATES (default deny)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = self.tmp.name
        self.c = cell.create(os.path.join(self.d, "s"), "s", "stub", "scripted", POL)
        self.blog = os.path.join(self.d, "board.jsonl")

    def seal(self, **kw):
        return router.seal(boardmod.Board(self.blog, seed=1), self.c, **kw)

    def clog(self):
        with open(os.path.join(self.c, "log.jsonl")) as f:
            return [json.loads(x)["entry"] for x in f]

    def test_refusal_is_logged_with_predicate_id_and_reason(self):
        g = self.seal()
        self.assertEqual(router.act({"type": "claim", "agent": "a", "item": "x"}, g, True), ("admitted", "ok"))
        st = router.act({"type": "claim", "agent": "b", "item": "x"}, g, True)
        self.assertEqual(st, ("refused", "A:duplicate_claim:x"))
        e = self.clog()[-1]
        self.assertEqual((e["type"], e["status"], e["predicate"], e["reason"], e["costs_turn"], e["agent"]),
                         ("action", "refused", "A", "A:duplicate_claim:x", True, "b"))
        self.assertEqual([x["type"] for x in boardmod.read_log(self.blog)].count("claim"), 1)  # not executed

    def test_default_deny_unknown_action(self):
        g = self.seal()
        for bad in ({"type": "exfil", "agent": "a"}, {"type": "claim"}, "claim", None, {"type": "claim", "agent": "a"}):
            st, why = router.act(bad, g, True)
            self.assertEqual(st, "refused", bad)
            self.assertIsNone(self.clog()[-1]["predicate"])  # a validation refusal names no predicate

    def test_bundle_log_verify_still_pass_after_wiring(self):
        g = self.seal()
        router.act({"type": "claim", "agent": "a", "item": "x"}, g, True)
        router.act({"type": "claim", "agent": "b", "item": "x"}, g, True)
        b = router.run_task(EXTRACT, self.c)
        self.assertEqual(b["status"], "done")
        self.assertTrue(cell.verify_log(self.c, b["log_head"]) and cell.verify_log(self.c))
        self.assertTrue(router.verify(EXTRACT, b, self.d))
        router.act({"type": "claim", "agent": "b", "item": "x"}, g, True)  # a refusal after the bundle: chain intact
        self.assertTrue(cell.verify_log(self.c) and cell.verify_log(self.c, b["log_head"]))
        self.assertTrue(router.verify(EXTRACT, b, self.d))

    def test_symlinked_cell_log_fails_closed(self):
        outside = os.path.join(self.d, "outside.txt")
        with open(outside, "w") as f:
            f.write("keep")
        g = self.seal()
        os.symlink(outside, os.path.join(self.c, "log.jsonl"))
        with self.assertRaises((ValueError, OSError)):
            router.act({"type": "exfil", "agent": "a"}, g, True)
        with open(outside) as f:
            self.assertEqual(f.read(), "keep")

    def test_board_reachable_only_through_act(self):
        raw = boardmod.Board(self.blog, seed=1)
        g = router.seal(raw, self.c)
        for name in ("claim", "post", "snapshot", "round", "items", "path", "_b", "__dict__", "board"):
            with self.assertRaises(PermissionError, msg=name):
                getattr(g, name)
        with self.assertRaises(PermissionError):
            g.claim = None
        with self.assertRaises(TypeError):
            router.act({"type": "read", "agent": "a"}, raw, True)  # a raw board is not accepted
        with self.assertRaises(TypeError):
            router.act({"type": "read", "agent": "a"}, g, 1)  # enforced must be a bool

    def test_three_consecutive_refusals_stop_the_episode(self):
        g = self.seal()
        bad = {"type": "exfil", "agent": "a"}
        self.assertEqual([router.act(bad, g, True)[0] for _ in range(3)], ["refused"] * 3)
        self.assertEqual(router.act({"type": "read", "agent": "a"}, g, True), ("refused", "episode_stopped"))

    def test_stops_reports_a_stop_reached_by_the_last_action_without_acting(self):
        g = self.seal(agents=["a", "b"])
        bad = {"type": "exfil", "agent": "a"}
        self.assertEqual(router.stops(g), (False, []))
        for _ in range(3):
            router.act(bad, g, True)
        n = len(boardmod.read_log(self.blog)), len(self.clog())
        self.assertEqual(router.stops(g), (False, ["a"]))  # visible before any further act
        self.assertEqual((len(boardmod.read_log(self.blog)), len(self.clog())), n)  # read-only: nothing logged
        router.act({"type": "read", "agent": "b"}, g, False)  # unenforced: nobody is out (Enforcer.act rule)
        self.assertEqual(router.stops(g), (False, []))
        with self.assertRaises(TypeError):
            router.stops(object())

    def test_twenty_total_refusals_stop_but_admits_reset_the_run(self):
        g = self.seal()
        bad, ok = {"type": "exfil", "agent": "a"}, {"type": "read", "agent": "a"}
        for _ in range(9):  # 18 refusals, never 3 in a row
            router.act(bad, g, True), router.act(bad, g, True)
            self.assertEqual(router.act(ok, g, True), ("admitted", "ok"))
        router.act(bad, g, True)
        self.assertEqual(router.act(ok, g, True), ("admitted", "ok"))  # 19 refusals: still running
        router.act(bad, g, True)  # the 20th
        self.assertEqual(router.act(ok, g, True), ("refused", "episode_stopped"))

    def test_enforcement_off_executes_and_logs_violation_executed(self):
        g = self.seal()
        router.act({"type": "claim", "agent": "a", "item": "x"}, g, True)
        for _ in range(30):  # never stops, never refuses
            st = router.act({"type": "claim", "agent": "b", "item": "x"}, g, False)
        self.assertEqual(st, ("violation_executed", "A:duplicate_claim:x"))
        self.assertEqual([x["agent"] for x in boardmod.read_log(self.blog) if x["type"] == "claim"].count("b"), 30)
        e = self.clog()[-1]
        self.assertEqual((e["status"], e["predicate"], e["costs_turn"]), ("violation_executed", "A", False))

    def test_refused_turn_costs_the_turn_and_admitted_executes(self):
        g = self.seal()
        router.act({"type": "post", "agent": "a", "kind": "note", "text": "hello"}, g, True)  # F: no source/expiry
        self.assertEqual([x["type"] for x in boardmod.read_log(self.blog)], ["init"])
        self.assertEqual(router.act({"type": "post", "agent": "a", "kind": "question", "text": "hi"}, g, True)[0], "admitted")
        router.end_round(g)
        self.assertEqual([x["type"] for x in boardmod.read_log(self.blog)], ["init", "post", "end_round"])

    def test_seal_refuses_bad_agents(self):
        for bad in ([], (), ("a", "b"), "ab", ["a", "a"], ["a", 1], ["a", ""], ["a", None], {"a"}):
            with self.assertRaises(ValueError, msg=repr(bad)):
                self.seal(agents=bad)

    def herd(self, g):
        for a in ("a0", "a1", "a2", "a3"):
            router.act({"type": "claim", "agent": a, "item": "t0"}, g, True)

    def test_per_agent_stop_through_sealed_router_herding_does_not_end_episode(self):
        g = self.seal(agents=["a0", "a1", "a2", "a3"])
        self.herd(g)  # a0 admitted, a1-a3 refused once each
        self.assertEqual(router.act({"type": "read", "agent": "a0"}, g, True), ("admitted", "ok"))
        self.assertEqual(router.act({"type": "claim", "agent": "a1", "item": "t0"}, g, True)[0], "refused")
        self.assertEqual(router.act({"type": "claim", "agent": "a1", "item": "t0"}, g, True)[0], "refused")  # a1: 3rd
        self.assertEqual(router.act({"type": "claim", "agent": "a1", "item": "t0"}, g, True), ("refused", "agent_stopped"))
        self.assertEqual(router.act({"type": "read", "agent": "a0"}, g, True), ("admitted", "ok"))  # episode lives
        self.assertEqual(router.act({"type": "read", "agent": "a2"}, g, True), ("admitted", "ok"))

    def test_agent_known_before_it_acts_keeps_the_episode_alive(self):
        g = self.seal(agents=["a0", "a1", "a2", "a3"])  # without the list only a0 is visible and it is stopped
        for _ in range(3):
            router.act({"type": "exfil", "agent": "a0"}, g, True)
        self.assertEqual(router.act({"type": "read", "agent": "a0"}, g, True), ("refused", "agent_stopped"))
        self.assertEqual(router.act({"type": "read", "agent": "a1"}, g, True), ("admitted", "ok"))

    def test_board_error_counts_against_that_agent_only(self):
        g = self.seal(agents=["a", "b"])
        rel = {"type": "release", "agent": "a", "item": "nothing"}  # not held: the board itself refuses
        for _ in range(2):
            st, why = router.act(rel, g, True)
            self.assertEqual(st, "refused")
            self.assertTrue(why.startswith("board_error:"), why)
        self.assertEqual(router.act({"type": "read", "agent": "b"}, g, True), ("admitted", "ok"))
        self.assertEqual(router.act(rel, g, True)[0], "refused")  # a's third: a is out, b plays on
        self.assertEqual(router.act({"type": "read", "agent": "a"}, g, True), ("refused", "agent_stopped"))
        self.assertEqual(router.act({"type": "read", "agent": "b"}, g, True), ("admitted", "ok"))

    def test_malformed_agent_id_does_not_crash_or_reset_counters(self):
        g = self.seal(agents=["a", "b"])
        router.act({"type": "exfil", "agent": "a"}, g, True)
        router.act({"type": "exfil", "agent": "a"}, g, True)
        for bad in (None, 7, ["a"], {"x": 1}, ""):
            st, _ = router.act({"type": "read", "agent": bad}, g, True)
            self.assertEqual(st, "refused", repr(bad))
        enf = router._parts(g)[1]
        self.assertEqual(enf.refusals.consecutive["a"], 2)  # not reset
        self.assertEqual(router.act({"type": "exfil", "agent": "a"}, g, True)[0], "refused")
        self.assertEqual(router.act({"type": "read", "agent": "a"}, g, True), ("refused", "agent_stopped"))
        self.assertEqual(router.act({"type": "read", "agent": "b"}, g, True), ("admitted", "ok"))

    def test_board_error_with_malformed_agent_is_failclosed(self):
        g = self.seal(agents=["a", "b"])
        with mock.patch.object(router, "_execute", side_effect=ValueError("x")):
            st, why = router.act({"type": "read", "agent": "a"}, g, True)
        self.assertEqual((st, why), ("refused", "board_error:ValueError"))
        enf = router._parts(g)[1]
        enf.act = lambda *a, **k: {"status": "admitted", "reason": "ok", "executed": True, "costs_turn": False, "log": []}
        with mock.patch.object(router, "_execute", side_effect=ValueError("x")):
            st, _ = router.act({"type": "read", "agent": ["unhashable"]}, g, True)  # must not crash
        self.assertEqual(st, "refused")
        self.assertEqual(enf.refusals.consecutive.get(None), 1)
        self.assertEqual(enf.refusals.consecutive["a"], 1)

    def test_group_key_never_shared_across_cells(self):
        def bun(c, m):
            return {"cell": c, "model": m}
        a, b = router.group_key(bun("a", "claude-opus-5-5")), router.group_key(bun("b", "claude-opus-5-5"))
        self.assertNotEqual(a, b)
        self.assertEqual(a, router.group_key(bun("a", "Claude-Opus-5-5-20261001")))  # same cell, same family
        self.assertNotEqual(a, router.group_key(bun("a", "claude-haiku-5-5")))
        keys = {router.group_key(bun(c, m)) for c in ("a", "b", "ab", "a.b") for m in ("scripted", "local")}
        self.assertEqual(len(keys), 8)
        for bad in (None, {}, bun("../x", "scripted"), bun("a", "gpt"), bun("a", None)):
            with self.assertRaises(ValueError):
                router.group_key(bad)


if __name__ == "__main__":
    unittest.main()
