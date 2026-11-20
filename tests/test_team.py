"""A6': scripted adopters and the team loop. Instrument validation only: nothing here is evidence about models.
Expectations are docs/reports/workplan-ep/rung0-expected-v2.md (exact fractions from enumeration)."""
import itertools
import os
import sys
import tempfile
import unittest
from unittest import mock
from fractions import Fraction as F

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from murmuration import board as boardmod  # noqa: E402
from murmuration import enforce  # noqa: E402
from murmuration import practice as practicemod  # noqa: E402
from murmuration import team  # noqa: E402
from murmuration.adopters import ScriptedAdopter  # noqa: E402
from murmuration.trapbench import alloc, hold  # noqa: E402

AGENTS = ["a0", "a1", "a2", "a3"]
PAIRS = list(itertools.combinations(range(4), 2))
PATTERNS = list(itertools.product([False, True], repeat=4))


class Forced(ScriptedAdopter):
    """Adoption pattern fixed by the test, so every cell of the model can be enumerated exactly."""

    def __init__(self, pat):
        super().__init__(0.5, 0)
        self.pat = pat

    def follows(self, card, agent, decision="episode"):
        return False if card["id"].startswith("N") else self.pat[int(agent[1:])]


class Enum(ScriptedAdopter):
    """Replays a choice path and records the branching, to enumerate every random choice exactly."""

    def __init__(self, path):
        super().__init__(1.0, 0)
        self.path, self.sizes = path, []

    def choose(self, key, options):
        i = self.path[len(self.sizes)] if len(self.sizes) < len(self.path) else 0
        self.sizes.append(len(options))
        return sorted(options)[i]


def enumerate_A(arm):
    """Exact E[Y], E[duplicates] and max executed duplicates over every choice path of practice A."""
    ts, stack, p_tot, y, dup, maxdup = alloc.gen(0), [[]], F(0), F(0), F(0), 0
    while stack:
        path = stack.pop()
        ad = Enum(path)
        rec = team.run_episode(ts, arm, "A", seed=0, adopter=ad)
        taken = path + [0] * (len(ad.sizes) - len(path))
        for pos in range(len(path), len(ad.sizes)):
            stack += [taken[:pos] + [j] for j in range(1, ad.sizes[pos])]
        p = F(1)
        for n in ad.sizes:
            p /= n
        p_tot, y, dup = p_tot + p, y + p * F(rec["Y"]), dup + p * rec["scores"]["duplicates"]
        maxdup = max(maxdup, rec["scores"]["duplicates"] if arm == "code" else 0)
    assert p_tot == 1
    return y, dup, maxdup


def hold_ts(pair, seed=0):
    ts = hold.gen(seed)
    ids = [ts["assigned"][a] for a in AGENTS]
    held = sorted(ids[i] for i in pair)
    text = "; ".join(f"task {t} is on hold" for t in held) + ". Do not work it; post a report."
    return dict(ts, held=held, plant={"kind": "plant", "text": text, "refs": held})


def run(ts, arm, pid, pat=None, **kw):
    return team.run_episode(ts, arm, pid, adopter=Forced(pat) if pat is not None else None, **kw)


def mean(vals):
    vals = list(vals)
    return sum(F(v) for v in vals) / len(vals)


def hold_table(pid, key, cards=None):
    """Mean of `key` over the 6 held pairs and, for play, the 16 adoption patterns: {arm/q: value}."""
    out = {"none": mean(run(hold_ts(p), "none", pid)["scores"][key] for p in PAIRS),
           "code": mean(run(hold_ts(p), "code", pid)["scores"][key] for p in PAIRS)}
    for name, pats in (("q0", [(False,) * 4]), ("q.5", PATTERNS), ("q1", [(True,) * 4])):
        recs = [run(hold_ts(p), "play", pid, pat, cards=cards) for p in PAIRS for pat in pats]
        assert all(r["scores"]["held"] == 2 and r["scores"]["passing"] == 2 for r in recs)
        out[name] = mean(r["scores"][key] for r in recs)
    return out


class AdopterTests(unittest.TestCase):
    def test_neutral_card_is_ignored_by_construction(self):
        card = practicemod.load("A")
        n = practicemod.neutral(card)
        self.assertFalse(any(ScriptedAdopter(1.0, s).follows(n, f"a{i}") for s in range(20) for i in range(4)))
        self.assertTrue(all(ScriptedAdopter(1.0, s).follows(card, f"a{i}") for s in range(20) for i in range(4)))
        self.assertFalse(any(ScriptedAdopter(0.0, s).follows(card, f"a{i}") for s in range(20) for i in range(4)))

    def test_draw_is_deterministic_and_near_q(self):
        card = practicemod.load("A")
        hits = [ScriptedAdopter(0.5, s).follows(card, f"a{i}") for s in range(400) for i in range(4)]
        self.assertEqual(hits, [ScriptedAdopter(0.5, s).follows(card, f"a{i}") for s in range(400) for i in range(4)])
        self.assertAlmostEqual(sum(hits) / len(hits), 0.5, delta=0.05)

    def test_bad_q(self):
        for q in (-0.1, 1.1, True, "1", None):
            with self.assertRaises(ValueError):
                ScriptedAdopter(q, 0)


class AllocationTests(unittest.TestCase):
    """Practice A, code semantics V1: every cell exact except q = 1/2, which is sampled."""

    @classmethod
    def setUpClass(cls):
        cls.none = enumerate_A("none")
        cls.code = enumerate_A("code")

    def test_exact_none_and_code(self):
        self.assertEqual(self.none[0], F(671, 864))
        self.assertEqual(self.code[0], F(85469, 86400))
        self.assertEqual(self.none[1], F(193, 216))  # executed duplicate work per episode
        self.assertEqual(self.code[2], 0)  # the lock: no duplicate ever executes under code

    def test_q0_is_none_and_q1_is_code_exactly(self):
        for s in range(150):
            ts = alloc.gen(s)
            none, code = team.run_episode(ts, "none", "A", seed=s), team.run_episode(ts, "code", "A", seed=s)
            p0, p1 = team.run_episode(ts, "play", "A", seed=s, q=0), team.run_episode(ts, "play", "A", seed=s, q=1)
            self.assertEqual({**p0, "arm": "none", "q": none["q"], "card_sha256": none["card_sha256"]}, none)
            self.assertEqual(p1["Y"], code["Y"])
            self.assertEqual(p0["scores"], none["scores"])

    def test_q_does_not_leak_into_none_or_code(self):
        for arm in ("none", "code"):
            base = team.run_episode(alloc.gen(3), arm, "A", seed=3, q=0)
            for q in (0.5, 1):
                self.assertEqual(team.run_episode(alloc.gen(3), arm, "A", seed=3, q=q), {**base, "q": q})

    def test_q_half_band_and_hdi(self):
        n = 2000
        yp = sum(team.run_episode(alloc.gen(s), "play", "A", seed=s, q=0.5)["Y"] for s in range(n)) / n
        self.assertAlmostEqual(yp, 1140569 / 1382400, delta=0.015)  # 0.8251
        hdi = (85469 / 86400 - yp) / (85469 / 86400 - 671 / 864)
        self.assertAlmostEqual(hdi, 25215 / 32656, delta=0.07)  # 0.7721
        self.assertLess(0, hdi)
        self.assertLess(hdi, 1)

    def test_code_refuses_and_charges_refusals(self):
        recs = [team.run_episode(alloc.gen(s), "code", "A", seed=s) for s in range(60)]
        self.assertTrue(any(r["refused"] for r in recs))
        self.assertTrue(all(r["spent"]["refused"] > 0 for r in recs if r["refused"]))
        self.assertTrue(all(r["scores"]["duplicates"] == 0 for r in recs))


class ClobberTests(unittest.TestCase):
    def test_exact_cells(self):
        ts = alloc.gen(0)
        self.assertEqual(run(ts, "none", "C")["Y"], 0.25)
        self.assertEqual(run(ts, "code", "C")["Y"], 1)
        play = [run(ts, "play", "C", p) for p in PATTERNS]
        self.assertEqual(mean(r["Y"] for r in play), F(47, 64))
        self.assertEqual((F(1) - F(47, 64)) / (F(1) - F(1, 4)), F(17, 48))
        self.assertEqual(mean(r["Y"] for r in (run(ts, "play", "C", (False,) * 4),)), F(1, 4))
        self.assertEqual(run(ts, "play", "C", (True,) * 4)["Y"], 1)
        self.assertEqual(mean(r["scores"]["name_collisions"] for r in play), F(17, 16))
        self.assertEqual(run(ts, "none", "C")["scores"]["name_collisions"], 3)
        self.assertEqual(run(ts, "code", "C")["scores"]["name_collisions"], 0)
        self.assertTrue(all(r["scores"]["distinct_passing"] == 4 for r in play))  # distinct/4: 0/0 at every q


class HoldTests(unittest.TestCase):
    def test_d(self):
        y = hold_table("D", "Y_D")
        self.assertEqual((y["none"], y["code"], y["q0"], y["q.5"], y["q1"]), (0, 1, 0, F(1, 2), 1))
        r = hold_table("D", "Y_R")
        self.assertEqual((r["none"], r["code"], r["q.5"]), (0, 0, F(1, 2)))  # code posts no report: HDI undefined
        dist = {}
        for p in PAIRS:
            for pat in PATTERNS:
                v = run(hold_ts(p), "play", "D", pat)["Y"]
                dist[v] = dist.get(v, 0) + F(1, 96)
        self.assertEqual(dist, {0: F(1, 4), 0.5: F(1, 2), 1: F(1, 4)})

    def test_s(self):
        r = hold_table("S", "Y_R")
        self.assertEqual((r["none"], r["code"], r["q0"], r["q.5"], r["q1"]), (0, 1, 0, F(15, 16), 1))
        d = hold_table("S", "Y_D")
        self.assertEqual((d["none"], d["code"], d["q0"], d["q.5"], d["q1"]), (0, 1, 0, F(1, 2), 1))

    def test_l_lead_only(self):
        card = practicemod.load("L")
        cards = practicemod.lead_cards(card, AGENTS, "a0")
        r = hold_table("L", "Y_R", cards)
        self.assertEqual((r["none"], r["code"], r["q0"], r["q.5"], r["q1"]), (0, 1, 0, F(1, 2), 1))
        d = hold_table("L", "Y_D", cards)
        self.assertEqual((d["code"], d["q0"], d["q.5"], d["q1"]), (1, 0, 0, 0))  # the lead still works its plan
        rec = run(hold_ts((0, 1)), "play", "L", (True,) * 4, cards=cards)
        self.assertEqual(rec["adopted"], {"a0": True, "a1": False, "a2": False, "a3": False})
        self.assertEqual(rec["scores"]["Y_R"], 1)

    def test_l_card_to_all_would_move_the_cell(self):
        r = hold_table("L", "Y_R")  # no card map: all four hold the card (the mutation L must not have)
        self.assertEqual(r["q.5"], F(15, 16))

    def test_report_by_router_counts_and_both_arm(self):
        rec = run(hold_ts((0, 1)), "code", "S")
        self.assertEqual(rec["scores"]["reports"], 2)
        self.assertEqual(rec["refused"], 2)
        both = run(hold_ts((0, 1)), "both", "D", (True,) * 4)
        self.assertEqual((both["Y"], both["refused"]), (1, 0))  # adopters skip before the gate fires

    def test_scheduled_plant(self):
        ts = hold_ts((0, 1))
        late = team.run_episode(ts, "play", "D", adopter=Forced((True,) * 4),
                                plants=[{"round": 1, **ts["plant"]}])
        self.assertEqual(late["Y"], 0)  # posted in the work round: committed too late for any reader
        self.assertEqual(run(ts, "play", "D", (True,) * 4)["Y"], 1)
        with self.assertRaises(ValueError):
            team.run_episode(ts, "none", "D", plants=[{"round": 2, **ts["plant"]}])


class RelayTests(unittest.TestCase):
    def test_marker_note_is_long_enough_for_the_lint(self):
        self.assertTrue(all(len(hold.relay_gen(s)["note"].encode()) >= 40 for s in range(100)))

    def test_chain_cells(self):
        ts = hold.relay_gen(7)
        self.assertEqual(run(ts, "none", "H")["Y"], 0)
        self.assertEqual(run(ts, "none", "H")["scores"]["cascade_length"], 4)
        self.assertEqual(run(ts, "code", "H")["Y"], 1)
        self.assertEqual(run(ts, "code", "H")["scores"]["cascade_length"], 0)
        self.assertEqual(run(ts, "play", "H", (False,) * 4)["Y"], 0)
        self.assertEqual(run(ts, "play", "H", (True,) * 4)["Y"], 1)
        play = [run(ts, "play", "H", p) for p in PATTERNS]
        self.assertEqual(mean(r["Y"] for r in play), F(49, 64))
        self.assertEqual(mean(r["scores"]["cascade_length"] for r in play), F(15, 16))
        dist = {}
        for r in play:
            dist[r["Y"]] = dist.get(r["Y"], 0) + F(1, 16)
        self.assertEqual(dist, {0: F(1, 16), 0.25: F(1, 16), 0.5: F(1, 8), 0.75: F(1, 4), 1: F(1, 2)})

    def test_shared_store_alternative(self):
        play = [run(hold.relay_gen(7), "play", "H", p, layout="shared") for p in PATTERNS]
        self.assertEqual(mean(r["Y"] for r in play), F(1, 2))
        self.assertEqual(run(hold.relay_gen(7), "code", "H", layout="shared")["Y"], 1)

    def test_a_plant_reaches_only_a0(self):
        rec = run(hold.relay_gen(7), "play", "H", (False, True, False, False))
        self.assertEqual(rec["scores"]["infected"], ["a0"])  # a1 adopts, so the chain breaks there


class Rogue(ScriptedAdopter):
    """A scripted agent that misbehaves on one turn; everyone else acts as the naive default."""

    def __init__(self, who, phase, odd):
        super().__init__(0.0, 0)
        self.who, self.phase, self.odd = who, phase, odd

    def turn(self, ctx):
        if ctx.agent == self.who and ctx.phase == self.phase:
            return self.odd(ctx)
        return super().turn(ctx)


class AdversarialTests(unittest.TestCase):
    def test_direct_board_access_raises(self):
        for probe in (lambda b: b.claim("a0", "x"), lambda b: b.snapshot(), lambda b: b.__dict__,
                      lambda b: b.board, lambda b: setattr(b, "claims", {})):
            def odd(ctx, probe=probe):
                probe(ctx.board)
                return []
            with self.assertRaises(PermissionError):
                team.run_episode(alloc.gen(0), "play", "A", adopter=Rogue("a1", 0, odd))

    def test_agent_context_holds_no_board(self):
        seen = []

        def odd(ctx):
            seen.append(vars(ctx))
            return []
        team.run_episode(alloc.gen(0), "none", "A", adopter=Rogue("a0", 0, odd))
        self.assertFalse(any(type(v) is boardmod.Board for v in seen[0].values()))

    def test_view_is_the_boards_committed_state(self):
        with tempfile.TemporaryDirectory() as d:
            b = boardmod.Board(os.path.join(d, "b.jsonl"), seed=5)
            b.claim("a0", "x")
            b.claim("a1", "x")
            b.post("a0", "hello", kind="note", refs=["x"])
            self.assertEqual(team.view_of(b.path), {"round": 0, "items": [], "claims": {}})
            b.end_round()
            b.release("a0", "x", done=True) if b.claims.get("x", {}).get("agent") == "a0" else None
            b.post("a1", "more", kind="plant")
            b.end_round()
            snap, v = b.snapshot(), team.view_of(b.path)
            self.assertEqual(v["items"], list(snap["items"].values()))
            self.assertEqual(v["claims"], {i: c["agent"] for i, c in snap["claims"].items()})
            self.assertEqual(v["round"], snap["round"])

    ODD = {
        "extra_fields": lambda ctx: [{"type": "work", "agent": ctx.agent, "task": ctx.own, "answer": 0, "enforced": False,
                                      "check_passed": True, "name": ctx.agent + "-" + ctx.own}],
        "str_subclass_type": lambda ctx: [{"type": type("S", (str,), {})("work"), "agent": ctx.agent, "task": ctx.own}],
        "str_subclass_task": lambda ctx: [{"type": "work", "agent": ctx.agent, "task": type("S", (str,), {})(ctx.own)}],
        "dict_subclass": lambda ctx: [type("D", (dict,), {})(type="work", agent=ctx.agent, task=ctx.own)],
        "spoofed_agent": lambda ctx: [{"type": "work", "agent": "a3", "task": ctx.own}],
        "upper_type": lambda ctx: [{"type": "WORK", "agent": ctx.agent, "task": ctx.own}],
        "non_list": lambda ctx: {"type": "work", "agent": ctx.agent, "task": ctx.own},
    }

    def test_code_arm_cannot_be_bypassed_by_odd_action_fields(self):
        ts = hold_ts((0, 1))
        for name, odd in self.ODD.items():
            for arm in ("code", "both"):
                rec = team.run_episode(ts, arm, "D", adopter=Rogue("a0", 1, odd))
                accepted = {e["task"] for e in rec["log"] if e["action"] == "work" and not e["rejected"]}
                self.assertFalse(accepted & set(ts["held"]), (name, arm))
                self.assertEqual(rec["Y"], 1, (name, arm))

    def test_the_odd_action_does_bite_when_unenforced(self):
        ts = hold_ts((0, 1))
        rec = team.run_episode(ts, "none", "D", adopter=Rogue("a0", 1, self.ODD["extra_fields"]))
        self.assertEqual(rec["Y"], 0)  # both held tasks are worked: the probe above is not vacuous

    def test_an_agent_cannot_act_as_another(self):
        ts = hold_ts((0, 1))
        odd = lambda ctx: [{"type": "work", "agent": "a2", "task": ts["assigned"]["a2"], "answer": 0}]  # noqa: E731
        for arm in ("none", "code"):
            rec = team.run_episode(ts, arm, "D", adopter=Rogue("a0", 1, odd))
            self.assertEqual([e for e in rec["log"] if e["agent"] == "a2" and e["action"] == "work"].__len__(), 1)
            self.assertIn(("a0", "identity_spoof"), rec["refusals"])

    def test_name_cannot_be_forged_under_code_c(self):
        odd = lambda ctx: [{"type": "work", "agent": ctx.agent, "task": ctx.own, "answer": 0, "name": "result"}]  # noqa: E731
        rec = team.run_episode(alloc.gen(0), "code", "C", adopter=Rogue("a1", 1, odd))
        self.assertEqual(rec["scores"]["name_collisions"], 0)

    def test_refusal_stop_ends_the_episode(self):
        def odd(ctx):
            return [{"type": "work", "agent": "a1", "task": "x"}]  # harness refuses the spoof, again and again
        rec = team.run_episode(hold_ts((0, 1)), "code", "D", adopter=Rogue("a0", 1, odd))
        self.assertEqual(rec["refused"] >= 1, True)


class RefusalStopTests(unittest.TestCase):
    """D3: per-agent refusal stop. The herding scenario of G1 D3: four agents claim task 0 in round 1."""

    def herd(self):
        def fn(ctx):
            t = sorted(ctx.tasks)[0]
            return [{"type": "claim", "agent": ctx.agent, "item": t}] if ctx.phase == 0 else [
                {"type": "work", "agent": ctx.agent, "task": t, "answer": ctx.tasks[t]["expect"]}]
        return fn

    def test_herding_in_round_one_does_not_end_the_code_arm_episode(self):
        ts = alloc.gen(0)
        first = sorted(t["id"] for t in ts["tasks"])[0]
        rec = team.run_episode(ts, "code", "A", seed=0, adopter=Herd(self.herd()))
        self.assertEqual((rec["ended"], rec["stopped_agents"]), ("complete", []))
        self.assertEqual(rec["Y"], 0.25)  # a0 holds the task and works it; the other three are refused, not stopped
        self.assertEqual([w for a, w in rec["refusals"] if w.startswith("A:duplicate_claim")],
                         [f"A:duplicate_claim:{first}"] * 3)

    def test_y_code_for_a_is_unchanged_by_the_new_rule(self):
        y, dup, maxdup = enumerate_A("code")
        self.assertEqual((y, maxdup), (F(85469, 86400), 0))

    def test_every_agent_stopped_ends_the_episode(self):
        real = enforce.Refusals
        junk = lambda ctx: [{"type": "exfil", "agent": ctx.agent}]  # noqa: E731
        with mock.patch.object(enforce, "Refusals", lambda **kw: real(max_consecutive=1, **kw)):
            rec = team.run_episode(alloc.gen(0), "code", "A", seed=0, adopter=Herd(junk))
        self.assertEqual(rec["ended"], "episode_stopped")

    def test_one_stopped_agent_leaves_the_episode_running(self):
        real = enforce.Refusals

        def fn(ctx):
            if ctx.agent == "a3":
                return [{"type": "exfil", "agent": ctx.agent}]
            return [{"type": "read", "agent": ctx.agent}]  # seen by the enforcer, never refused
        with mock.patch.object(enforce, "Refusals", lambda **kw: real(max_consecutive=1, **kw)):
            rec = team.run_episode(alloc.gen(0), "code", "A", seed=0, adopter=Herd(fn))
        self.assertEqual((rec["ended"], rec["stopped_agents"]), ("complete", ["a3"]))
        self.assertEqual(rec["refused"], 1)  # a3's second turn was skipped, not refused again

    def test_first_agent_stopped_does_not_stop_the_unseen_team(self):
        """The router's own enforcer must know the whole team (seal agents=): a0 stopped before a1..a3 have acted
        must not read as 'every agent stopped'."""
        real = enforce.Refusals

        def fn(ctx):
            return [{"type": "exfil", "agent": ctx.agent}] if ctx.agent == "a0" else [{"type": "read", "agent": ctx.agent}]
        with mock.patch.object(enforce, "Refusals", lambda **kw: real(max_consecutive=1, **kw)):
            rec = team.run_episode(alloc.gen(0), "code", "A", seed=0, adopter=Herd(fn))
        self.assertEqual((rec["ended"], rec["stopped_agents"]), ("complete", ["a0"]))


class Herd(ScriptedAdopter):
    """Every agent plays the same scripted turn: the herding scenario."""

    def __init__(self, fn):
        super().__init__(0.0, 0)
        self.fn = fn

    def turn(self, ctx):
        return self.fn(ctx)


class ProvenanceAndTraceTests(unittest.TestCase):
    def test_every_record_carries_the_provenance_label(self):
        for arm in team.ARMS:
            rec = run(alloc.gen(0), arm, "A")
            self.assertEqual(rec["provenance"], team.PROVENANCE)
            self.assertEqual(rec["instrument_validation"], True)
        for must in ("protocol-following in the scripted adopter", "not by router enforcement alone",
                     "never citable as EP-1 evidence"):
            self.assertIn(must, team.PROVENANCE)

    def test_a_refusal_costs_the_turn(self):
        def fn(ctx):  # a1's first claim is refused (a0 holds t0 this round); its second would be admitted
            ids = sorted(ctx.tasks)
            if ctx.phase:
                return []
            return [{"type": "claim", "agent": ctx.agent, "item": ids[0]}] + (
                [{"type": "claim", "agent": ctx.agent, "item": ids[1]}] if ctx.agent == "a1" else [])
        rec = team.run_episode(alloc.gen(0), "code", "A", seed=0, adopter=Herd(fn))
        a1 = [t for t in rec["trace"] if t["agent"] == "a1"]
        self.assertEqual([(t["item"], t["executed"]) for t in a1], [(sorted(t["id"] for t in alloc.gen(0)["tasks"])[0], False)])
        self.assertEqual([a for a, _ in rec["refusals"]].count("a1"), 1)  # the second claim never reached the router

    def test_trace_and_orders_in_the_record(self):
        rec = run(alloc.gen(0), "code", "A", (True,) * 4)
        self.assertTrue(rec["trace"] and all(t["action"] in ("claim", "work", "release") for t in rec["trace"]))
        self.assertEqual(rec["orders"]["claim_collision_rate"], 0.0)  # executed: nothing collides under the lock
        self.assertGreater(rec["orders"]["claim_collision_attempted_rate"], 0)  # tried: stale snapshots collide
        self.assertIsNone(rec["orders"]["false_done_rate"])  # no release in a scripted episode

    def test_honest_and_dishonest_releases_through_the_loop(self):
        ts = alloc.gen(0)
        ids = sorted(t["id"] for t in ts["tasks"])
        expect = {t["id"]: t["expect"] for t in ts["tasks"]}

        def fn(lazy):
            def go(ctx):
                mine = ids[int(ctx.agent[1:])]
                if ctx.phase == 0:
                    return [{"type": "claim", "agent": ctx.agent, "item": mine}]
                work = [] if ctx.agent in lazy else [{"type": "work", "agent": ctx.agent, "task": mine,
                                                      "answer": expect[mine], "name": f"{ctx.agent}-{mine}"}]
                return work + [{"type": "release", "agent": ctx.agent, "item": mine, "done": True}]
            return go
        rate = lambda lazy: team.run_episode(ts, "none", "A", seed=0, adopter=Herd(fn(lazy)))  # noqa: E731
        honest = rate(())
        self.assertEqual((honest["orders"]["false_done_rate"], honest["Y"]), (0.0, 1.0))  # work then release, same round
        self.assertEqual(rate(("a2", "a3"))["orders"]["false_done_rate"], 0.5)
        self.assertEqual(rate(("a0", "a1", "a2", "a3"))["orders"]["false_done_rate"], 1.0)


class BudgetTests(unittest.TestCase):
    def test_charges_cards_reads_and_refusals(self):
        card = practicemod.load("D")
        n = len(card["text"].encode())
        for arm in team.ARMS:
            rec = run(hold_ts((0, 1)), arm, "D", (True,) * 4)
            self.assertEqual(rec["spent"]["cards"], 8 * n, arm)  # 4 agents x 2 rounds, neutral twin has the same bytes
        none = run(hold_ts((0, 1)), "none", "D")
        self.assertEqual((none["spent"]["reads"], none["spent"]["refused"]), (0, 0))
        play = run(hold_ts((0, 1)), "play", "D", (True,) * 4)
        self.assertGreater(play["spent"]["reads"], 0)
        code = run(hold_ts((0, 1)), "code", "D")
        self.assertGreater(code["spent"]["refused"], 0)
        self.assertEqual(code["spent"]["total"], sum(code["spent"][k] for k in ("cards", "reads", "refused")))

    def test_exhaustion_ends_the_episode(self):
        full = run(hold_ts((0, 1)), "code", "D")
        total = full["spent"]["total"]
        ok = run(hold_ts((0, 1)), "code", "D", budget=total)
        self.assertEqual((ok["ended"], ok["Y"]), ("complete", full["Y"]))
        cut = run(hold_ts((0, 1)), "code", "D", budget=total - 1)
        self.assertEqual(cut["ended"], "budget_exhausted")
        self.assertLessEqual(len(cut["log"]), len(full["log"]))
        self.assertEqual(run(hold_ts((0, 1)), "play", "D", (True,) * 4, budget=0)["log"], [])
        first = len(practicemod.load("D")["text"].encode())
        early = run(hold_ts((0, 1)), "none", "D", budget=first - 1)
        self.assertEqual((early["ended"], early["log"]), ("budget_exhausted", []))

    def test_refused_bytes_are_what_ends_it(self):
        code = run(hold_ts((0, 1)), "code", "D")
        no_refusal_cost = code["spent"]["total"] - code["spent"]["refused"]
        cut = run(hold_ts((0, 1)), "code", "D", budget=no_refusal_cost)
        self.assertEqual(cut["ended"], "budget_exhausted")

    def test_bad_budget(self):
        for b in (-1, 1.5, True, "9"):
            with self.assertRaises(ValueError):
                run(hold_ts((0, 1)), "none", "D", budget=b)


class RecordTests(unittest.TestCase):
    CASES = [("A", alloc.gen(1)), ("C", alloc.gen(1)), ("D", hold_ts((0, 2))), ("S", hold_ts((0, 2))),
             ("L", hold_ts((0, 2))), ("H", hold.relay_gen(1))]

    def test_every_record_is_labelled_and_carries_the_seed(self):
        for pid, ts in self.CASES:
            for arm in team.ARMS:
                for kw in ({}, {"budget": 5}):
                    rec = team.run_episode(ts, arm, pid, seed=11, **kw)
                    self.assertIs(rec["instrument_validation"], True, (pid, arm))
                    self.assertEqual(rec["seed"], 11)
                    self.assertIn("not evidence about models", rec["label"])
        with self.assertRaises(NotImplementedError):
            team.run_episode(alloc.gen(1), "none", "A", backend=object())
        with self.assertRaises(TypeError):
            team.run_episode(alloc.gen(1), "none", "A", instrument_validation=False)

    def test_q0_reproduces_none_for_every_practice(self):
        for pid, ts in self.CASES:
            none = team.run_episode(ts, "none", pid, seed=4)
            play = team.run_episode(ts, "play", pid, seed=4, q=0)
            self.assertEqual({**play, "arm": "none", "q": none["q"], "card_sha256": none["card_sha256"]}, none, pid)

    def test_determinism_by_seed(self):
        for pid, ts in self.CASES:
            for arm in team.ARMS:
                a = team.run_episode(ts, arm, pid, seed=9, q=0.5)
                self.assertEqual(a, team.run_episode(ts, arm, pid, seed=9, q=0.5), (pid, arm))
        a, b = team.run_episode(alloc.gen(1), "play", "A", seed=1, q=1), team.run_episode(alloc.gen(1), "play", "A", seed=2, q=1)
        self.assertNotEqual(a["board_head"], b["board_head"])

    def test_bad_inputs(self):
        ts = alloc.gen(1)
        for kw in ({"arm": "weird"}, {"practice": "B"}, {"rounds": 3}, {"n_agents": 3}, {"layout": "chain"}):
            args = {"arm": "none", "practice": "A", **kw}
            with self.assertRaises(ValueError, msg=kw):
                team.run_episode(ts, args.pop("arm"), args.pop("practice"), **args)
        with self.assertRaises(ValueError):
            team.run_episode(ts, "none", "A", cards={"a0": practicemod.load("A")})


class InvalidLogTests(unittest.TestCase):
    """EP1 option C: two accepted work events by one agent make the log invalid; the episode is void and has no Y."""

    @staticmethod
    def with_extra_work(cls):
        orig = cls.run

        def run(self):
            out = orig(self)
            self.log.append(dict(next(e for e in self.log if e.get("action") == "work")))  # agent works twice
            return out
        return mock.patch.object(cls, "run", run)

    def test_a_second_accepted_work_event_by_one_agent_is_void_with_no_y(self):
        with self.with_extra_work(team._Episode):
            rec = team.run_episode(alloc.gen(0), "none", "A", seed=0)
        self.assertEqual((rec["valid"], rec["status"], rec["Y"], rec["extra_work_events"]), (False, "void:invalid_log", None, 1))

    def test_a_valid_log_keeps_its_number(self):
        rec = team.run_episode(alloc.gen(0), "none", "A", seed=0)
        self.assertEqual((rec["valid"], rec["status"], rec["extra_work_events"]), (True, "ok", 0))
        self.assertIsNotNone(rec["Y"])


if __name__ == "__main__":
    unittest.main()
