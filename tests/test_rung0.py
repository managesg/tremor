"""A9' tests: the rung-0 table is GREEN on the built instrument and each listed mutation turns it RED (or VOID).
Mutations edit an in-memory copy of the module source (or monkeypatch), never the file on disk. Scripted only."""
import contextlib
import inspect
import os
import sys
import tempfile
import types
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tremor import adopters, enforce, router, rung0, stats, team  # noqa: E402
from tremor import board as boardmod  # noqa: E402


def mutated(mod, *edits):
    """A copy of module `mod` whose source has each (old, new) edit applied (each `old` must occur exactly once)."""
    src = inspect.getsource(mod)
    for old, new in edits:
        assert src.count(old) == 1, f"mutation anchor not unique in {mod.__name__}: {old!r}"
        src = src.replace(old, new)
    m = types.ModuleType(mod.__name__)
    m.__file__, m.__package__ = mod.__file__, mod.__package__
    exec(compile(src, mod.__file__, "exec"), m.__dict__)
    return m


@contextlib.contextmanager
def patched(*pairs):
    with contextlib.ExitStack() as st:
        for obj, name, val in pairs:
            st.enter_context(mock.patch.object(obj, name, val))
        yield


def fresh_view(path):
    """No stale snapshot: committed state plus everything still pending in the current round."""
    items, claims, rnd = {}, {}, 0
    for ln in boardmod.read_log(path):
        t, d = ln["type"], ln["data"]
        if t == "post":
            items[d["id"]] = dict(d, agent=ln["agent"], round=ln["round"])
        elif t == "claim":
            claims.setdefault(d["item"], ln["agent"])
        elif t == "end_round":
            for r in d["resolved"]:
                if r["winner"] is not None:
                    claims[r["item"]] = r["winner"]
            rnd += 1
    return {"round": rnd, "items": list(items.values()), "claims": claims}


def failed(table):
    return [c["name"] for c in table["checks"] if not c["ok"]] + table["failures"]


class Base(unittest.TestCase):
    def assertRed(self, table, *needles):
        self.assertNotEqual(table["verdict"], "GREEN", "the mutation left the table green")
        self.assertIn(table["verdict"], ("RED", "VOID"))
        for n in needles:
            self.assertTrue(any(n in f for f in failed(table)), f"{n!r} not among failures {failed(table)}")


class TestTable(Base):
    @classmethod
    def setUpClass(cls):
        cls.table = rung0.run()

    def test_green_and_complete(self):
        t = self.table
        self.assertEqual(t["verdict"], "GREEN", failed(t))
        self.assertFalse(t["void"])
        self.assertEqual(t["episodes"], 6 * 15 * 3 * 4)
        self.assertTrue(t["instrument_validation"] and all(r["instrument_validation"] is True for r in t["rows"]))
        arms = {(c["practice"], c["arm"]) for c in t["cells"]}
        self.assertEqual(arms, {(p, a) for p in "ACDSLH" for a in team.ARMS})
        self.assertTrue(all(c["ok"] is not False for c in t["cells"]) and all(h["ok"] is not False for h in t["hdi"]))

    def test_every_outcome_cell_present_and_undefined_has_reason(self):
        got = {(c["practice"], c["outcome"]) for c in self.table["cells"]}
        for p, o in [("A", "distinct/4"), ("A", "claim_collision_attempted_rate"), ("A", "claim_collision_executed_rate"), ("C", "surviving/4"), ("C", "distinct/4"),
                     ("D", "Y_D"), ("D", "Y_R"), ("S", "Y_D"), ("L", "Y_D"), ("H", "cascade_length")]:
            self.assertIn((p, o), got)
        und = [c for c in self.table["cells"] if c["value"] is None]
        self.assertTrue(und and all(c["reason"] for c in und))
        self.assertTrue(all(c["value"] is not None for c in self.table["cells"] if c["reason"] is None))
        a = next(c for c in self.table["cells"] if c["practice"] == "A" and c["outcome"] == "claim_collision_attempted_rate"
                 and c["arm"] == "none")
        self.assertIsNone(a["value"])  # no claims: None, never 0

    def test_hdi_endpoints_and_undefined_cells(self):
        h = {(x["practice"], x["outcome"], x["q"]): x for x in self.table["hdi"]}
        for p, o in [("A", "distinct/4"), ("C", "surviving/4"), ("D", "Y_D"), ("S", "Y_R"), ("L", "Y_R"), ("H", "clean_fraction")]:
            self.assertAlmostEqual(h[p, o, 0]["point"], 1, 9)
            self.assertAlmostEqual(h[p, o, 1]["point"], 0, 9)
        for k in [("C", "distinct/4", q) for q in (0, 0.5, 1)] + [("D", "Y_R", q) for q in (0, 0.5, 1)]:
            self.assertTrue(h[k]["undefined"] and h[k]["point"] is None and h[k]["reason"])

    def test_report_lists_pass_fail(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "out", "rung0.md")
            text = rung0.report(self.table, path)
            self.assertEqual(open(path, encoding="utf-8").read(), text)
        self.assertIn("# Rung 0 report: GREEN", text)
        self.assertIn("| floor:alloc fails | PASS |", text)
        self.assertNotIn("FAIL", text.replace("## Failures", ""))
        self.assertIsInstance(rung0.report(self.table), str)

    def test_report_and_every_record_carry_the_provenance(self):
        sentence = ("Y_code for a neutral-card agent is produced by protocol-following in the scripted adopter "
                    "(follow = adopts or (A and enforced)), not by router enforcement alone; rung-0 numbers are "
                    "never citable as EP-1 evidence.")
        self.assertIn(sentence, rung0.report(self.table))
        self.assertEqual(self.table["provenance"], sentence)
        self.assertTrue(all(r["provenance"] == sentence for r in self.table["rows"]))
        for arm in team.ARMS:
            self.assertEqual(team.run_episode(team.alloc.gen(0), arm, "A", seed=0)["provenance"], sentence)

    def test_driver_refuses_a_record_without_the_provenance(self):
        real = team.run_episode
        strip = lambda *a, **k: {x: v for x, v in real(*a, **k).items() if x != "provenance"}
        with patched((team, "run_episode", strip)), self.assertRaises(RuntimeError):
            rung0.run(("D",), sets=1)

    def test_claim_collisions_attempted_and_executed_are_reported_apart(self):
        cell = lambda name, arm, q=None: next(c for c in self.table["cells"] if c["practice"] == "A" and c["outcome"] == name
                                              and c["arm"] == arm and c["q"] == q)
        att, exe = "claim_collision_attempted_rate", "claim_collision_executed_rate"
        self.assertGreater(cell(att, "code")["value"], 0)  # refused duplicates are counted as attempts
        self.assertEqual(cell(exe, "code")["value"], 0.0)
        self.assertEqual(cell(exe, "code")["tol"], rung0.EXACT)  # exact: a wrong 0 elsewhere cannot hide in a wide band
        self.assertLess(cell(att, "code")["tol"], cell(att, "code")["expected"])  # a 0 would fail the cell
        self.assertEqual(cell(att, "code")["value"], cell(att, "play", 1)["value"])
        names = [c["name"] for c in self.table["checks"]]
        for n in ("claims:A code attempted == play(q=1) attempted per set",
                  "claims:A code executed collisions are 0 in every set",
                  "probe:claim collisions from attempts (herd under code: attempted 1/4, executed 0, 3 refused)",
                  "probe:false done (honest 0, half dishonest 1/2, all dishonest 1, no releases None)"):
            self.assertIn(n, names)

    def test_report_names_failures(self):
        bad = dict(self.table, checks=self.table["checks"] + [{"name": "x:forced", "ok": False, "detail": ""}],
                   verdict="RED", failures=["x:forced"])
        self.assertIn("| x:forced | FAIL |", rung0.report(bad))

    def test_refuses_records_without_the_flag(self):
        real = team.run_episode
        strip = lambda *a, **k: {x: v for x, v in real(*a, **k).items() if x != "instrument_validation"}
        with patched((team, "run_episode", strip)), self.assertRaises(RuntimeError):
            rung0.run(("D",), sets=1)
        with self.assertRaises(ValueError):
            rung0.report(dict(self.table, rows=[{"practice": "A"}]))
        with self.assertRaises(ValueError):
            rung0.run(("Z",))

    def test_deterministic(self):
        a, b = rung0.run(("D", "A"), sets=4, seed=3), rung0.run(("D", "A"), sets=4, seed=3)
        self.assertEqual(a["cells"], b["cells"])
        self.assertEqual(a["hdi"], b["hdi"])


class TestMutations(Base):
    def test_no_claim_lock(self):
        m = mutated(enforce, ('return (False, f"duplicate_claim:{item}") if other else OK', "return OK"),
                    ('return OK if mine else (False, f"work_without_claim:{item}")', "return OK"))
        with patched((team, "enforce", m), (router, "enforce", m)):
            t = rung0.run(("A",))
        self.assertRed(t, "probe:claim lock", "code:A no executed duplicate work", "cell A dup_executed code")

    def test_no_stale_snapshot(self):
        with patched((team, "view_of", fresh_view)):
            t = rung0.run(("A",))
        self.assertRed(t, "probe:stale snapshot")

    def test_scoring_from_agent_state_not_the_log(self):
        a = mutated(team.alloc, ('if e.get("action") == "work" and not e.get("rejected")', 'if e.get("action") == "work"'))
        h = mutated(team.hold, ('ok = [e for e in log if not e.get("rejected")]', "ok = list(log)"))
        with patched((team, "alloc", a), (team, "hold", h)):
            t = rung0.run(("A", "D"))
        self.assertRed(t, "probe:scoring ignores rejected events", "cell D Y_D code")

    def test_clobber_scoring_off(self):
        a = mutated(team.alloc, ('last[e.get("name") or ""] = e', "last[id(e)] = e"))
        with patched((team, "alloc", a)):
            t = rung0.run(("C",))
        self.assertRed(t, "probe:clobber scoring on", "cell C surviving/4 none")

    def test_plant_visible_in_round_one(self):
        orig = team._Episode.plant

        def early(self, rnd):
            orig(self, rnd)
            if any(p["round"] == rnd for p in self.plants):
                router.end_round(self.handle)  # committed before anyone reads
        with patched((team._Episode, "plant", early)):
            t = rung0.run(("D",))
        self.assertRed(t, "probe:plant hidden in round 1")

    def test_report_counted_for_the_wrong_task(self):
        h = mutated(team.hold, (" & held  # a report on an unheld task is not counted", ""))
        with patched((team, "hold", h)):
            t = rung0.run(("D", "S"))
        self.assertRed(t, "probe:report for the wrong task")

    def test_changed_tie_break(self):
        with patched((adopters.ScriptedAdopter, "choose", lambda self, key, options: min(options))):
            t = rung0.run(("A",))
        self.assertRed(t, "probe:tie-break uniform", "cell A distinct/4 code")

    def test_hdi_wrong_denominator(self):
        s = mutated(stats, ('lambda r: r["code"] - r["none"], []', 'lambda r: r["play"] - r["none"], []'))
        with patched((rung0, "stats", s)):
            t = rung0.run(("D",))
        self.assertRed(t, "probe:HDI denominator", "hdi D Y_D")


class TestPairingMutations(Base):
    """The four mutants that survived G1: each must now turn the table RED."""
    PAR = dict(sets=8)

    def test_control_is_green(self):
        self.assertEqual(rung0.run(("A",), **self.PAR)["verdict"], "GREEN")

    def test_pairing_broken_play_rows_from_another_set(self):  # M12
        real = stats.hdi

        def shifted(data, key, **kw):
            return real([dict(r, play=data[(i + 1) % len(data)]["play"]) for i, r in enumerate(data)], key, **kw)
        with patched((stats, "hdi", shifted)):
            t = rung0.run(("A",), **self.PAR)
        self.assertRed(t, "hdi A distinct/4 q=0")

    def test_one_cluster_id_for_every_set(self):  # M13
        real = stats.hdi
        one = lambda data, key, **kw: real([dict(r, **{key: 0}) for r in data], key, **kw)  # noqa: E731
        with patched((stats, "hdi", one)):
            t = rung0.run(("A",), **self.PAR)
        self.assertRed(t, "hdi A distinct/4 q=0.5")

    def test_the_code_arm_gets_a_different_task_set(self):  # M14
        real = team.run_episode

        def other(ts, arm, practice, **kw):
            return real(rung0._taskset(practice, kw["seed"] + 1000) if arm == "code" else ts, arm, practice, **kw)
        with patched((team, "run_episode", other)):
            t = rung0.run(("A",), **self.PAR)
        self.assertRed(t, "pair:A set 0 one task set in every arm and q")

    def test_claim_collision_read_off_multiplied_by_zero(self):  # M22 on the real loop's logs
        real = team.orders.compute

        def zero(log, f=0.75, trace=None):
            out = real(log, f, trace)
            out["claim_collision_attempted_rate"]["value"] = 0 if out["claim_collision_attempted_rate"]["value"] else None
            return out
        with patched((team.orders, "compute", zero)):
            t = rung0.run(("A",), **self.PAR)
        self.assertRed(t, "cell A claim_collision_attempted_rate code", "probe:claim collisions from attempts")


class TestInstrumentChecks(Base):
    def test_floor_that_passes_voids_the_batch(self):
        with patched((team.hold, "floor_log", team.hold.oracle_log)):
            t = rung0.run(("D",), sets=3)
        self.assertEqual(t["verdict"], "VOID")
        self.assertTrue(t["void"])
        self.assertRed(t, "floor:hold fails")

    def test_oracle_that_fails_voids_the_batch(self):
        with patched((team.hold, "oracle_log", team.hold.floor_log)):
            t = rung0.run(("D",), sets=3)
        self.assertEqual(t["verdict"], "VOID")
        self.assertRed(t, "oracle:hold passes")

    def test_q_leak_into_none_is_red(self):
        real = team.run_episode

        def leaky(ts, arm, practice, **kw):
            if arm == "none" and kw.get("q", 0) == 1:
                arm = "play"  # q leaks into the none arm
            return real(ts, arm, practice, **kw)
        with patched((team, "run_episode", leaky)):
            t = rung0.run(("D",), sets=4)
        self.assertRed(t, "q leak:D none")


if __name__ == "__main__":
    unittest.main()
