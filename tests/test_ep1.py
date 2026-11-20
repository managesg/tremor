"""EP-1 batch driver (ep1.py). Fake server only: no key, no network beyond 127.0.0.1, no GPU. The real pinned ledger
directory is never written: spend.PILOT_LEDGER_DIR is patched to a temp dir in every test (and checked at the end)."""
import contextlib
import hashlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import fakeclaude  # noqa: E402
from murmuration import __main__ as cli  # noqa: E402
from murmuration import analysis, ep1, formal_alloc, spend  # noqa: E402
from murmuration import backend_claude as bc  # noqa: E402
from murmuration.trapbench import alloc, alloc2  # noqa: E402

M = ep1.MODEL
KEY = "sk-ant-FAKEKEY-do-not-leak-0123456789"
REAL_DIR = spend.PILOT_LEDGER_DIR
_BEFORE = sorted(os.listdir(REAL_DIR)) if os.path.isdir(REAL_DIR) else None
INVALID = {"status": "INVALID", "reason": "lean missing (test stub)"}


def lean_ok(ts, log):
    """Stands in for the built Lean scorer: OK with a full Lean-shaped score (alloc2 fields first)."""
    s = dict(alloc.score(log, ts), **alloc2.score(log, ts))  # alloc2 has no unknown_task_events; Lean has every field
    return {"status": "OK", "score": {k: v for k, v in s.items() if k in formal_alloc.FIELDS}}


def with_stop(stop, text="OK"):
    return lambda p, h, b, n: (200, dict(fakeclaude.usage_ok(M, 90_000, 300, text=text)[1], stop_reason=stop))


def tearDownModule():
    after = sorted(os.listdir(REAL_DIR)) if os.path.isdir(REAL_DIR) else None
    assert after == _BEFORE, "a test wrote to the real pinned ledger directory"


class Crash(BaseException):
    pass


class Crashy:
    """Delegates to a real ClaudeClient; raises Crash on call number `at` (a process death mid-episode)."""

    def __init__(self, inner, at):
        self.inner, self.at, self.n, self.ledger = inner, at, 0, inner.ledger

    def call(self, *a, **kw):
        self.n += 1
        if self.n == self.at:
            raise Crash()
        return self.inner.call(*a, **kw)


def fail_first(k, status=500, then=ep1.worst_case_responder, body=None):
    return lambda p, h, b, n: (status, body or {"error": {"type": "api_error"}}) if n <= k else then(p, h, b, n)


def files_text(*dirs):
    out = []
    for d in dirs:
        for root, _, names in os.walk(d):
            for n in names:
                with open(os.path.join(root, n), "rb") as f:
                    out.append(f.read())
    return b"\n".join(out)


class Base(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d, True)
        self.ldir = os.path.join(self.d, "ledger")
        self.sheet = ep1._dry_sheet(os.path.join(self.d, "ps.json"))
        sha = hashlib.sha256(open(os.path.join(ep1.ROOT, "practices", "A.md"), "rb").read()).hexdigest()
        self.review = os.path.join(self.d, "review.md")
        with open(self.review, "w") as f:
            f.write(f"Reviewed by someone other than the author.\nreviewed_sha256: {sha}\n")
        for p in (mock.patch.object(spend, "PILOT_LEDGER_DIR", os.path.join(self.d, "pilot-real")),
                  mock.patch.object(ep1, "_lean", lean_ok)):
            p.start()
            self.addCleanup(p.stop)
        self.srvs = []
        self.addCleanup(lambda: [s.shutdown() for s in self.srvs])

    def client(self, responder, kind, wrap=None):
        srv, url, seen = fakeclaude.start(responder)
        self.srvs.append(srv)
        led = spend.Ledger(os.path.join(self.ldir, f"{kind}.jsonl"), self.sheet, batch=kind)
        cl = bc.ClaudeClient(KEY, led, url, allow_host="127.0.0.1")
        return (wrap(cl) if wrap else cl), led, seen

    def canary(self, responder=ep1.worst_case_responder):
        cl, led, seen = self.client(responder, "canary")
        out = ep1.run_batch("canary", cl, led, 0, os.path.join(self.d, "canary"), True)
        return out, seen

    def batch(self, kind, responder=ep1.worst_case_responder, n_sets=3, seed=0, out="out", wrap=None, canary=True, **kw):
        if canary and not os.path.exists(os.path.join(self.d, "canary", "canary.json")):
            self.canary()
        cl, led, seen = self.client(responder, kind, wrap)
        kw.setdefault("review", self.review)
        res = ep1.run_batch(kind, cl, led, seed, os.path.join(self.d, out), True, n_sets=n_sets, **kw)
        self.seen, self.led = seen, led
        return res

    def records(self, out="out"):
        return ep1._read_jsonl(os.path.join(self.d, out, "episodes.jsonl"))

    def stops(self):
        return [r for b, r in spend.Ledger._sum(spend.Ledger._read(self.led.path))["stops"]]


class FullScheduleTests(Base):
    def test_full_dry_run_within_all_caps_through_the_cli(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli.main(["ep1", "dry-run", "--out-dir", os.path.join(self.d, "dry"), "--review", self.review])
        self.assertEqual(rc, 0)
        out = json.loads(buf.getvalue())
        self.assertTrue(out["stamp"].startswith("FAKE"))
        self.assertTrue(out["ep1_report"].startswith("FAKE"))
        ldir = os.path.join(self.d, "dry", "ledger")
        rep = spend.batch_report(ldir, "ep1")
        self.assertEqual(rep["calls"], 481)  # canary inside ep1 + 480
        self.assertEqual(out["ep1"]["reason"], "inconclusive")
        self.assertLessEqual(rep["tokens"], 1_250_000)
        self.assertLessEqual(rep["usd"], 5.0)
        self.assertLessEqual(rep["calls"], 500)
        self.assertLessEqual(spend.batch_report(ldir, "pilot")["calls"], 150)
        recs = ep1._read_jsonl(os.path.join(self.d, "dry", "ep1", "episodes.jsonl"))
        self.assertEqual((len(recs), {r["ended"] for r in recs}, {r["stamp"] for r in recs}), (60, {"complete"}, {ep1.FAKE}))
        self.assertTrue(all(r["evidence"] == "fake" and r["instrument_validation"] for r in recs))
        self.assertEqual(spend.batch_report(ldir, "canary")["calls"], 1)

    def test_pairing_and_randomised_recorded_arm_order(self):
        p0, p0b, p1 = ep1.plan("ep1", 0), ep1.plan("ep1", 0), ep1.plan("ep1", 1)
        self.assertEqual(p0, p0b)
        self.assertNotEqual(p0, p1)
        self.assertGreater(len({tuple(b["order"]) for b in p0}), 1)  # not one fixed order
        self.assertTrue(all(sorted(b["order"]) == ["code", "none", "play"] for b in p0))
        self.assertEqual([b["set"] for b in p0], list(range(20)))
        res = self.batch("ep1", n_sets=4)
        recs = self.records()
        self.assertEqual(len(recs), 12)
        for blk in ep1.plan("ep1", 0, 4):
            rs = [r for r in recs if r["set"] == blk["set"]]
            self.assertEqual([r["cond"] for r in rs], blk["order"])  # run in the seeded order, recorded
            self.assertTrue(all(r["block_order"] == blk["order"] for r in rs))
            self.assertEqual(len({(r["taskset_sha256"], r["seed"], r["taskset_id"]) for r in rs}), 1)  # paired
            self.assertEqual(sorted(r["arm"] for r in rs), ["code", "none", "play"])
            self.assertEqual(rs[0]["taskset_id"], f"heldout:{blk['set']}")
        with open(os.path.join(self.d, "out", "schedule.json")) as f:
            self.assertEqual(json.load(f)["plan"], ep1.plan("ep1", 0, 4))
        self.assertEqual(res["episodes"], 12)

    def test_every_record_carries_what_analysis_needs_and_the_ledger_figures(self):
        self.batch("ep1", n_sets=1)
        r = self.records()[0]
        for k in ("taskset_id", "taskset_sha256", "agent_answers", "evidence", "model", "ended", "Y", "turns",
                  "refused", "stopped_agents", "malformed_by_reason"):
            self.assertIn(k, r)
        self.assertTrue(all("retries" in t for t in r["turns"]))
        self.assertEqual(r["ledger"]["reserve_lines"], 8)
        self.assertEqual(r["ledger"]["charge_lines"], 8)
        self.assertGreater(r["ledger"]["reserved_usd"], r["ledger"]["settled_usd"])
        self.assertGreater(r["ledger"]["settled_usd"], 0)
        self.assertEqual(set(r["scorers"]), {"alloc", "alloc2", "third", "disagreement"})
        self.assertEqual(r["scorers"]["third"]["status"], "OK")  # three agreeing verdicts


class ScorerTests(Base):
    def test_scorer_disagreement_voids_the_episode_and_stops(self):
        real = alloc2.score
        with mock.patch.object(alloc2, "score", lambda log, ts: dict(real(log, ts), Y=0.99)):
            res = self.batch("ep1", n_sets=2)
        self.assertEqual(res["reason"], "stopped:scorer_disagreement")
        recs = self.records()
        self.assertEqual(len(recs), 1)
        self.assertTrue(recs[0]["void"].startswith("scorer_disagreement"))
        self.assertIn("Y", recs[0]["scorers"]["disagreement"])
        self.assertEqual(self.stops(), ["stopped:scorer_disagreement"])

    def test_third_scorer_ok_is_recorded_and_a_disagreement_stops(self):
        res = self.batch("ep1", n_sets=1, third_scorer=lean_ok)
        self.assertEqual({r["scorers"]["third"]["status"] for r in self.records()}, {"OK"})
        self.assertIn(res["reason"], ("complete", "inconclusive"))
        self.setUp()
        third_bad = lambda ts, log: {"status": "OK", "score": {"distinct_passing": 99}}  # noqa: E731
        res = self.batch("ep1", n_sets=1, third_scorer=third_bad, out="out2")
        self.assertEqual(res["reason"], "stopped:scorer_disagreement")
        self.assertEqual(self.records("out2")[0]["scorers"]["third"]["status"], "DISAGREE")

    def test_a_partial_ok_lean_score_is_a_disagreement_not_agreement(self):
        part = lambda ts, log: {"status": "OK", "score": {k: alloc.score(log, ts)[k] for k in ("distinct_passing", "slots")}}  # noqa: E731
        g = ep1._score_gate([], alloc.gen(0, "heldout"), part)
        self.assertEqual(g["third"]["status"], "DISAGREE")
        self.assertIn("valid: missing", g["disagreement"])
        res = self.batch("ep1", n_sets=1, third_scorer=part)
        self.assertEqual((res["reason"], len(self.records())), ("stopped:scorer_disagreement", 1))

    def test_lean_invalid_stops_the_batch_before_any_call(self):
        """Orchestrator decision: INVALID (toolchain missing or unpinned, build or audit failed) means the third scorer is
        not running; the batch stops before the first call and no episode is counted."""
        def boom(ts, log):
            raise OSError("no lean")
        for i, third in enumerate((lambda ts, log: INVALID, boom, lambda ts, log: None,
                                   lambda ts, log: {"status": "REJECTED", "reason": "probe refused"})):
            self.setUp()  # a fresh directory and ledger per case
            res = self.batch("ep1", n_sets=2, third_scorer=third, out=f"inv{i}")
            self.assertEqual((res["reason"], res["detail"], res["episodes"]), ("stopped:scorer_disagreement", "scorer_invalid", 0))
            self.assertEqual((len(self.seen), self.records(f"inv{i}"), self.stops()), (0, [], ["stopped:scorer_disagreement"]))

    def test_lean_invalid_at_an_episode_voids_it_and_stops(self):
        n = {"calls": 0}

        def later(ts, log):  # OK for the probe, INVALID from the first episode on
            n["calls"] += 1
            return lean_ok(ts, log) if n["calls"] == 1 else INVALID
        res = self.batch("ep1", n_sets=2, third_scorer=later)
        recs = self.records()
        self.assertEqual((res["reason"], res["detail"], len(recs)), ("stopped:scorer_disagreement", "scorer_invalid", 1))
        self.assertTrue(recs[0]["void"].startswith("scorer_invalid"))
        self.assertEqual(res["voids"], {recs[0]["arm"]: 1})

    def test_lean_rejected_voids_that_episode_only_and_it_is_never_rerun(self):
        first = {}

        def rejects_one(ts, log):
            if log and not first:
                first["log"] = log
            return {"status": "REJECTED", "reason": "exit 2"} if log and log is first.get("log") else lean_ok(ts, log)
        res = self.batch("ep1", n_sets=1, third_scorer=rejects_one)
        recs = self.records()
        self.assertEqual(len(recs), 3)  # the void cell is not re-run
        self.assertTrue(recs[0]["void"].startswith("scorer_rejected"))
        self.assertEqual([bool(r.get("void")) for r in recs], [True, False, False])
        self.assertEqual((res["reason"], res["detail"]), ("inconclusive", None))  # not cells_lost, not a stop
        self.assertEqual(ep1._summary(recs, True)["n_task_sets_all_arms"], 0)  # its set has an incomplete arm
        with self.assertRaises(spend.BatchStopped):  # settled; a resume never re-runs the void cell
            self.batch("ep1", n_sets=1, third_scorer=lean_ok)


class StopRuleTests(Base):
    def test_cap_stops_before_an_episode_that_could_cross_it(self):
        for key, val, why in (("calls", 20, "cap_calls"), ("tokens", 110_000, "cap_tokens"), ("usd", 0.05, "cap_usd")):
            with self.subTest(key), mock.patch.dict(spend.BATCH_SPECS["ep1"], {key: val}):
                self.setUp()
                res = self.batch("ep1", n_sets=7)
                self.assertEqual((res["reason"], res["detail"]), ("stopped:cap", why))
                rep = spend.batch_report(self.ldir, "ep1")
                self.assertLessEqual(rep[key], val)
                self.assertTrue(1 <= len(self.records()) < 21)
                with self.assertRaises(spend.BatchStopped):  # a stopped batch never runs again
                    cl, led, _ = self.client(ep1.worst_case_responder, "ep1")
                    ep1.run_batch("ep1", cl, led, 0, os.path.join(self.d, "out"), True, n_sets=7, review=self.review)

    def test_three_transport_aborts_stop_the_batch(self):
        res = self.batch("ep1", fail_first(6))
        self.assertEqual((res["reason"], res["detail"]), ("stopped:transport", "transport_aborts"))
        recs = self.records()
        self.assertEqual([(r["ended"], r["attempt"]) for r in recs], [("infrastructure_abort", 0)] * 1 + [
            ("infrastructure_abort", 1), ("infrastructure_abort", 0)])
        self.assertEqual(len(self.seen), 6)
        self.assertEqual(res["aborts"], 3)

    def test_an_abort_is_rerun_once_with_a_new_id_tag(self):
        res = self.batch("ep1", fail_first(2), n_sets=1)
        self.assertIn(res["reason"], ("complete", "inconclusive"))
        recs = self.records()
        first = recs[0]
        cell = [r for r in recs if (r["set"], r["cond"]) == (first["set"], first["cond"])]
        self.assertEqual([(r["ended"], r["id_tag"].endswith("r1")) for r in cell], [("infrastructure_abort", False), ("complete", True)])
        self.assertNotEqual(cell[0]["episode_id"], cell[1]["episode_id"])
        self.assertEqual((cell[1]["seed"], cell[1]["taskset_sha256"]), (cell[0]["seed"], cell[0]["taskset_sha256"]))
        self.assertEqual(len(recs), 4)
        self.assertEqual(res["aborts"], 1)

    def test_a_rerun_that_aborts_loses_the_cell_and_is_not_rerun_again(self):
        res = self.batch("ep1", fail_first(4), n_sets=1)  # cell 1 aborts twice, the rest succeed
        self.assertEqual((res["reason"], res["detail"]), ("stopped:transport", "cells_lost"))
        self.assertEqual([r["ended"] for r in self.records()], ["infrastructure_abort"] * 2 + ["complete"] * 2)
        self.assertEqual(len(self.seen), 4 + 16)
        self.assertEqual(ep1._read_jsonl(os.path.join(self.d, "out", "events.jsonl")), [])  # no third attempt, even a refused one

    def test_http_400_stops_at_once_and_is_never_rerun(self):
        res = self.batch("ep1", fail_first(10 ** 6, status=400))
        self.assertEqual((res["reason"], res["detail"]), ("stopped:http400", "http_400"))
        self.assertEqual((len(self.seen), len(self.records())), (1, 1))
        self.assertEqual(self.stops(), ["stopped:http400"])

    def test_returned_model_mismatch_voids_and_stops(self):
        wrong = lambda p, h, b, n: fakeclaude.usage_ok("claude-sonnet-5-5", 100, 20, text="[]")  # noqa: E731
        res = self.batch("ep1", wrong)
        self.assertEqual((res["reason"], res["detail"]), ("stopped:void_model", "void_model_mismatch"))
        self.assertEqual((len(self.seen), self.records()[0]["ended"]), (1, "void"))

    def test_a_200_without_a_model_voids_and_stops(self):
        res = self.batch("ep1", lambda p, h, b, n: (200, {"content": [], "usage": {}}))
        self.assertEqual((res["reason"], res["detail"]), ("stopped:void_model", "void_no_model"))

    def test_usage_above_the_reservation_is_a_spend_stop(self):
        res = self.batch("ep1", lambda p, h, b, n: fakeclaude.usage_ok(M, 5000, 20, text="[]"))
        self.assertEqual((res["reason"], res["detail"]), ("stopped:cap", "spend_stop:BatchStopped"))
        self.assertEqual(len(self.seen), 1)

    def test_malformed_replies_in_the_first_block_stop_the_batch(self):
        res = self.batch("ep1", lambda p, h, b, n: fakeclaude.usage_ok(M, 900, 20, text="no json here"), n_sets=20)
        self.assertEqual((res["reason"], res["detail"]), ("stopped:void_model", "malformed_first_block"))
        self.assertEqual(len(self.records()), 3)

    def test_all_stopped_episodes_never_stop_the_batch(self):
        """Ruling 1 on section 2e: the batch stop at the third all-stopped episode is removed."""
        run = ep1._Run("ep1", mock.Mock(), mock.Mock(), 0, self.d, True, 1, None)
        run.ledger = mock.Mock(totals=lambda: {"overspent": False}, entries=lambda: [])
        run.recs = []
        for i in range(10):
            self.assertEqual(run._after({"ended": "episode_stopped", "void": None, "turns": [], "episode_id": f"x{i}"}), "ok")

    def test_heavy_refusal_in_the_code_arm_never_stops_the_batch_or_unbalances_a_block(self):
        """Every code episode ends all-stopped (seed 1 puts the third code cell FIRST in set 2, so the removed stop would
        have left that block with one arm). The batch finishes, every block has all three arms, and the count is per arm."""
        orig = ep1.tc.run_episode_model

        def refuse_all_in_code(ts, arm, *a, **kw):
            rec = orig(ts, arm, *a, **kw)
            if arm == "code":
                rec.update(ended="episode_stopped", stopped_agents=sorted({t["agent"] for t in rec["turns"]}))
            return rec
        with mock.patch.object(ep1.tc, "run_episode_model", refuse_all_in_code):
            res = self.batch("ep1", n_sets=4, seed=1)
        self.assertIn(res["reason"], ("complete", "inconclusive"))
        self.assertEqual(self.stops(), [res["reason"]])
        recs = self.records()
        self.assertEqual(len(recs), 12)
        for s in range(4):
            self.assertEqual(sorted(r["arm"] for r in recs if r["set"] == s and r["ended"] in analysis.SCORED_ENDS
                                    and not r.get("void")), ["code", "none", "play"])
        arms = ep1._summary(recs, True)["arms"]
        self.assertEqual({a: arms[a]["all_agents_stopped"] for a in arms}, {"code": 4, "none": 0, "play": 0})
        self.assertEqual({a: arms[a]["task_sets"] for a in arms}, {"code": 4, "none": 4, "play": 4})

    def test_an_unbilled_line_without_a_successful_retry_stops_the_batch(self):
        """G1b-R M13: an unbilled_unknown line of this episode stops the batch unless its retry (#r1) was charged."""
        run = ep1._Run("ep1", mock.Mock(), mock.Mock(), 0, self.d, True, 1, None)
        run.recs = []
        rec = {"ended": "complete", "void": None, "turns": [], "episode_id": "ep1-none-h0-s0"}
        lines = [{"kind": "unbilled_unknown", "id": "ep1-none-h0-s0:r0:a0"}]
        run.ledger = mock.Mock(totals=lambda: {"overspent": False}, entries=lambda: lines)
        with self.assertRaises(ep1._StopBatch) as c:
            run._after(dict(rec))
        self.assertEqual((str(c.exception), ep1._why(str(c.exception))), ("unbilled_unknown", "cap"))
        lines.append({"kind": "charge", "id": "ep1-none-h0-s0:r0:a0#r1"})  # the retry succeeded: no stop
        self.assertEqual(run._after(dict(rec)), "ok")
        lines[:] = [{"kind": "unbilled_unknown", "id": "ep1-play-h0-s0:r0:a0"}]  # another episode's line is not this one's
        self.assertEqual(run._after(dict(rec)), "ok")

    def test_pilot_and_ep1_cannot_open_before_the_canary(self):
        for kind in ("pilot", "ep1"):
            with self.assertRaises(spend.BatchStopped):
                self.batch(kind, canary=False)
            self.assertFalse(os.path.exists(os.path.join(self.d, "out", "episodes.jsonl")))
        self.canary(lambda p, h, b, n: fakeclaude.usage_ok("claude-sonnet-5-5", 10, 10))  # a failed canary
        with self.assertRaises(spend.BatchStopped):
            self.batch("pilot", canary=False)

    def test_a_fake_client_needs_dry_run(self):
        cl, led, _ = self.client(ep1.worst_case_responder, "ep1")
        with self.assertRaises(ValueError):
            ep1.run_batch("ep1", cl, led, 0, os.path.join(self.d, "x"), False, review=self.review)


class ResumeTests(Base):
    def test_resume_after_a_crash_never_double_charges(self):
        self.canary()
        cl, led, _ = self.client(ep1.worst_case_responder, "ep1", wrap=lambda c: Crashy(c, 12))
        with self.assertRaises(Crash):
            ep1.run_batch("ep1", cl, led, 0, os.path.join(self.d, "out"), True, n_sets=2, review=self.review)
        first = self.records()
        self.assertEqual(len(first), 1)
        res = self.batch("ep1", n_sets=2)
        recs = self.records()
        self.assertEqual(recs[0], first[0])  # the finished episode is untouched
        self.assertIn(res["reason"], ("complete", "inconclusive"))
        self.assertEqual(sorted((r["set"], r["cond"]) for r in recs if r["ended"] == "complete"),
                         sorted((b["set"], c) for b in ep1.plan("ep1", 0, 2) for c in b["order"]))
        lines = spend.Ledger._read(self.led.path)
        res_ids = [e["id"] for e in lines if e["kind"] == "reserve"]
        self.assertEqual(len(res_ids), len(set(res_ids)))
        self.assertEqual(len(res_ids), 6 * 8 + 3)  # 6 cells x 8 calls plus the 3 calls the crashed attempt had spent
        self.assertEqual(len([e for e in lines if e["kind"] == "charge"]), len(res_ids))
        ev = ep1._read_jsonl(os.path.join(self.d, "out", "events.jsonl"))
        self.assertEqual([(e["event"], e["attempt"]) for e in ev], [("interrupted", 0)])
        with self.assertRaises(spend.BatchStopped):  # settled: no further run
            self.batch("ep1", n_sets=2)

    def test_a_different_schedule_in_the_same_directory_is_refused(self):
        self.canary()
        cl, led, _ = self.client(ep1.worst_case_responder, "ep1", wrap=lambda c: Crashy(c, 3))
        with self.assertRaises(Crash):
            ep1.run_batch("ep1", cl, led, 0, os.path.join(self.d, "out"), True, n_sets=2, review=self.review)
        cl, led, _ = self.client(ep1.worst_case_responder, "ep1")
        with self.assertRaises(ValueError):
            ep1.run_batch("ep1", cl, led, 7, os.path.join(self.d, "out"), True, n_sets=2, review=self.review)


class CardAndPilotTests(Base):
    def test_missing_or_wrong_review_refuses_before_any_call(self):
        self.canary()
        for review in (os.path.join(self.d, "nope.md"), None):
            cl, led, seen = self.client(ep1.worst_case_responder, "ep1")
            with mock.patch.object(ep1, "REVIEW_FILE", os.path.join(self.d, "still-missing.md")):
                with self.assertRaises(ep1.PreflightError):
                    ep1.run_batch("ep1", cl, led, 0, os.path.join(self.d, "out"), True, review=review)
            self.assertEqual((len(seen), os.path.exists(led.path)), (0, False))
        bad = os.path.join(self.d, "bad.md")
        with open(bad, "w") as f:
            f.write("reviewed_sha256: " + "0" * 64)
        with self.assertRaises(ep1.PreflightError):
            self.batch("ep1", review=bad, canary=False)

    def test_pilot_runs_five_conditions_and_exports_a_trace(self):
        res = self.batch("pilot", n_sets=3)
        self.assertEqual(res["reason"], "complete")
        recs = self.records()
        self.assertEqual(len(recs), 15)
        self.assertEqual({r["cond"] for r in recs}, {"none", "play", "code", "states_check", "keyword_stuffed"})
        self.assertEqual({r["taskset_id"].split(":")[0] for r in recs}, {"train"})
        self.assertLessEqual(spend.batch_report(self.ldir, "pilot")["calls"], 150)
        texts = {"states_check": "A task scores only if", "keyword_stuffed": "Words from the report"}
        for c, needle in texts.items():
            users = [s["body"]["messages"][0]["content"] for s in self.seen]
            self.assertTrue(any(needle in u for u in users))
        tr = open(os.path.join(self.d, "out", "pilot_trace.txt")).read()
        self.assertEqual(tr.count("== "), 15)
        self.assertIn("cond=states_check", tr)
        self.assertEqual(len({r["episode_id"] for r in recs}), 15)  # pilot cards get their own ids

    def test_canary_is_one_padded_call_and_records_the_ledger_cost(self):
        out, seen = self.canary()
        self.assertEqual((out["reason"], out["ok"], len(seen)), ("complete", True, 1))
        self.assertEqual(len(json.dumps(seen[0]["body"], sort_keys=True)), 90_000)
        self.assertEqual(seen[0]["body"]["model"], M)
        led = spend.Ledger(os.path.join(self.ldir, "canary.jsonl"), self.sheet, batch="canary")
        charge = [e for e in spend.Ledger._read(led.path) if e["kind"] == "charge"]
        self.assertEqual((len(charge), charge[0]["usd"]), (1, out["ledger_usd"]))
        self.assertGreater(out["ledger_usd"], 0)
        self.assertEqual(out["usage"]["input_tokens"], 90_000)
        with open(os.path.join(self.d, "canary", "canary.json")) as f:
            self.assertEqual(json.load(f)["compare_with_console"][:6], "owner:")
        self.assertEqual(spend.batch_report(self.ldir, "ep1")["calls"], 1)  # counted inside ep1
        with self.assertRaises(analysis.AnalysisRefused):
            ep1.analyse(os.path.join(self.d, "canary"))

    def canary_case(self, out_dir, client, led):
        out = ep1.run_batch("canary", client, led, 0, out_dir, True)
        with open(os.path.join(out_dir, "canary.json")) as f:
            self.assertEqual(json.load(f), json.loads(json.dumps(out, default=str)))  # the record is written
        self.assertEqual(spend.Ledger._sum(spend.Ledger._read(led.path))["stops"], [("canary", out["reason"])])
        with self.assertRaises(spend.BatchStopped):  # a stopped canary keeps pilot and ep1 shut
            self.batch("ep1", canary=False)
        return out

    def test_a_cut_short_refused_or_malformed_canary_reply_is_recorded_charged_and_stops(self):
        """G1b-R R-4: every canary outcome writes canary.json, charges the ledger and stops with an explicit reason."""
        empty = lambda p, h, b, n: (200, dict(fakeclaude.usage_ok(M, 90_000, 5)[1], content="garbage"))  # noqa: E731
        for name, responder, detail in (("max_tokens", with_stop("max_tokens"), "malformed:truncated"),
                                        ("refusal", with_stop("refusal"), "malformed:declined"),
                                        ("odd_stop", with_stop("pause_turn"), "malformed:bad_stop_reason"),
                                        ("empty", empty, "malformed:empty")):
            with self.subTest(name):
                self.ldir = os.path.join(self.d, "ledger-" + name)
                cl, led, seen = self.client(responder, "canary")
                out = self.canary_case(os.path.join(self.d, "canary-" + name), cl, led)
                self.assertEqual((out["ok"], out["reason"], out["detail"], len(seen)), (False, "stopped:void_model", detail, 1))
                charge = [e for e in spend.Ledger._read(led.path) if e["kind"] == "charge"]
                self.assertEqual((len(charge), charge[0]["usd"], out["ledger"]["charge_lines"]), (1, out["ledger_usd"], 1))
                self.assertGreater(out["ledger_usd"], 0)

    def test_a_cut_short_canary_body_is_recorded_and_stops_as_transport(self):
        from test_team_claude import raw_server
        partial = lambda c: c.sendall(b"HTTP/1.1 200 OK\r\ncontent-type: application/json\r\n"  # noqa: E731
                                      b"content-length: 500\r\n\r\n{\"model\":")
        s, url = raw_server([partial])
        self.addCleanup(s.close)
        led = spend.Ledger(os.path.join(self.ldir, "canary.jsonl"), self.sheet, batch="canary")
        out = self.canary_case(os.path.join(self.d, "canary"), bc.ClaudeClient(KEY, led, url, allow_host="127.0.0.1"), led)
        self.assertEqual((out["ok"], out["reason"], out["detail"]), (False, "stopped:transport", "call_failed:IncompleteRead"))
        t = led.totals()
        self.assertEqual((t["calls"], t["charged_ids"], out["ledger"]["reserve_lines"], out["ledger"]["charge_lines"]),
                         (1, set(), 1, 0))
        self.assertAlmostEqual(t["spent_usd"], out["worst_case_usd"], places=12)  # the open reserve counts at worst case

    def test_a_canary_naming_another_model_stops_even_without_a_client_void(self):
        class Scripted:
            ledger = None

            def __init__(self, led):
                self.ledger = led

            def call(self, *a, **kw):
                return {"returned_model": "claude-sonnet-5-5", "usage": {"input_tokens": 1, "output_tokens": 1},
                        "usd": 0.0, "void": None, "text": "OK", "stop_reason": "end_turn"}
        led = spend.Ledger(os.path.join(self.ldir, "canary.jsonl"), self.sheet, batch="canary")
        out = self.canary_case(os.path.join(self.d, "canary"), Scripted(led), led)
        self.assertEqual((out["reason"], out["detail"]), ("stopped:void_model", "wrong_model"))


class AnalysisTests(Base):
    def test_analysis_refuses_fake_records_for_model_tables(self):
        self.batch("ep1", n_sets=2)
        recs = self.records()
        with self.assertRaises(analysis.AnalysisRefused):
            analysis.summarise(recs, "model")
        text = ep1.analyse(os.path.join(self.d, "out"))  # a dry run is analysed as scripted, stamped FAKE
        self.assertTrue(text.startswith("FAKE"))
        sp = os.path.join(self.d, "out", "schedule.json")
        sched = json.load(open(sp))
        sched["dry_run"] = False
        json.dump(sched, open(sp, "w"))
        with self.assertRaises(analysis.AnalysisRefused):  # FAKE records in a directory claiming to be real
            ep1.analyse(os.path.join(self.d, "out"))

    def test_real_model_records_make_a_model_table(self):
        self.batch("ep1", n_sets=2)
        real = [dict(r, evidence="model", instrument_validation=False, label=ep1.tc.REAL_LABEL, stamp=None) for r in self.records()]
        with open(os.path.join(self.d, "out", "episodes.jsonl"), "w") as f:
            f.write("".join(json.dumps(r) + "\n" for r in real))
        sp = os.path.join(self.d, "out", "schedule.json")
        sched = json.load(open(sp))
        sched["dry_run"] = False
        json.dump(sched, open(sp, "w"))
        text = ep1.analyse(os.path.join(self.d, "out"))
        self.assertNotIn("FAKE", text.split("\n")[0])
        self.assertIn("Y_play - Y_none", text)


class CliTests(Base):
    def run_cli(self, argv, env=None):
        buf = io.StringIO()
        with mock.patch.dict(os.environ, env or {}, clear=False), contextlib.redirect_stdout(buf):
            os.environ.pop(ep1.KEY_ENV, None) if env is None else None
            rc = cli.main(argv)
        return rc, buf.getvalue()

    def test_refuses_without_the_confirm_flag_and_without_the_key(self):
        out = os.path.join(self.d, "cliout")
        for cmd in ("canary", "pilot", "run"):
            rc, text = self.run_cli(["ep1", cmd, "--out-dir", out], {ep1.KEY_ENV: KEY})  # key but no confirm
            self.assertEqual(rc, 2)
            self.assertIn("--i-have-owner-confirm", text)
            rc, text = self.run_cli(["ep1", cmd, "--out-dir", out, "--i-have-owner-confirm"])  # confirm but no key
            self.assertEqual(rc, 2)
            self.assertIn(ep1.KEY_ENV, text)
            self.assertNotIn(KEY, text)
        self.assertFalse(os.path.exists(out))
        self.assertFalse(os.path.exists(spend.PILOT_LEDGER_DIR))  # nothing created before the gates passed
        rc, text = self.run_cli(["ep1", "run", "--out-dir", out, "--i-have-owner-confirm"], {ep1.KEY_ENV: ""})
        self.assertEqual(rc, 2)

    def test_paid_commands_with_both_gates_run_and_the_key_never_reaches_an_output(self):
        echo = {"error": {"type": "api_error", "message": f"bad key {KEY}"}}  # a server that echoes the key
        srv, url, seen = fakeclaude.start(lambda p, h, b, n: (500, echo) if n == 2 else ep1.worst_case_responder(p, h, b, n))
        self.srvs.append(srv)
        sheet = os.path.join(self.d, "ps2.json")
        shutil.copy(os.path.join(self.d, "ps.json"), sheet)
        common = ["--i-have-owner-confirm", "--base-url", url, "--ledger-dir", self.ldir, "--price-sheet", sheet,
                  "--review", self.review]
        outs = []
        for cmd, out in (("canary", "c"), ("pilot", "p")):
            rc, text = self.run_cli(["ep1", cmd, "--out-dir", os.path.join(self.d, out)] + common, {ep1.KEY_ENV: KEY})
            outs.append(text)
            self.assertNotIn(KEY, text)
            self.assertEqual(rc, 0, text)
        self.assertEqual(json.loads(outs[1])["reason"], "complete")
        self.assertNotIn(KEY.encode(), files_text(self.d))  # ledger, schedule, episodes, trace, canary, final
        self.assertTrue(all(KEY not in t for t in outs))
        self.assertIn(b"[redacted]", files_text(self.ldir))  # the echoed key was scrubbed, not stored
        rc, text = self.run_cli(["ep1", "analyse", os.path.join(self.d, "p")])
        self.assertEqual(rc, 0)

    def test_ledger_dir_alone_is_refused(self):
        rc, text = self.run_cli(["ep1", "run", "--out-dir", os.path.join(self.d, "z"), "--i-have-owner-confirm",
                                 "--ledger-dir", self.ldir], {ep1.KEY_ENV: KEY})
        self.assertEqual(rc, 2)

    def test_base_url_alone_is_refused(self):  # G0-2R3 N10: a fake canary must not settle in the real runs/spend
        for cmd in ("canary", "pilot", "run"):
            rc, text = self.run_cli(["ep1", cmd, "--out-dir", os.path.join(self.d, "z" + cmd), "--i-have-owner-confirm",
                                     "--base-url", "http://127.0.0.1:9"], {ep1.KEY_ENV: KEY})
            self.assertEqual(rc, 2, text)
            self.assertIn("needs --ledger-dir", text)
        self.assertFalse(os.path.exists(spend.PILOT_LEDGER_DIR))


class DryRunBracketTests(Base):
    def dry(self, **kw):
        return ep1.dry_run_all(os.path.join(self.d, "dry"), 0, review=self.review, n_sets=2, **kw)

    def test_floor_fails_and_oracle_passes_through_the_driver(self):
        out = self.dry()
        b = out["bracket"]
        self.assertEqual(out["verdict"], "GREEN")
        self.assertTrue(b["floor_fails"] and b["oracle_passes"])
        self.assertEqual((b["floor_Y"], b["oracle_Y"]), ([ep1.FLOOR_Y] * 3, [ep1.ORACLE_Y] * 3))
        self.assertEqual((ep1.FLOOR_Y, ep1.ORACLE_Y), (0.25, 1.0))  # rung0-expected-v2 section 2; prereg sections 10, 12

    def test_a_floor_above_one_quarter_makes_the_dry_run_void(self):
        """G1b-R M12: the floor responder lets a1 work task 1, so the floor scores 0.5 in the unenforced arms."""
        real = ep1.worst_case_responder

        def m12(p, h, b, n):
            code, resp = real(p, h, b, n)
            user = b["messages"][0]["content"]
            if "Round 2 of 2. You are a1." in user:
                t = re.findall(r"^(\w+): sum (\d+) (\d+)$", user, re.M)[1]
                resp["content"][0]["text"] = json.dumps({"type": "work", "task": t[0], "answer": int(t[1]) + int(t[2]),
                                                         "name": "a1-x"})
            return code, resp
        with mock.patch.object(ep1, "worst_case_responder", m12):
            out = self.dry()
        self.assertIn(0.5, out["bracket"]["floor_Y"])
        self.assertEqual((out["verdict"], out["bracket"]["floor_fails"], out["bracket"]["oracle_passes"]), ("VOID", False, True))

    def test_an_oracle_that_fails_makes_the_dry_run_void(self):
        with mock.patch.object(ep1, "oracle_responder", ep1.worst_case_responder):
            out = self.dry()
        self.assertEqual((out["verdict"], out["bracket"]["oracle_passes"], out["bracket"]["floor_fails"]), ("VOID", False, True))

    def test_cli_dry_run_exits_nonzero_on_void(self):
        buf = io.StringIO()
        with mock.patch.object(ep1, "oracle_responder", ep1.worst_case_responder), contextlib.redirect_stdout(buf):
            rc = cli.main(["ep1", "dry-run", "--out-dir", os.path.join(self.d, "dv"), "--review", self.review])
        self.assertEqual((rc, json.loads(buf.getvalue())["verdict"]), (1, "VOID"))


class NoPrivateLedgerTests(unittest.TestCase):
    def test_ep1_never_touches_a_private_ledger_member(self):
        import ast
        tree = ast.parse(open(os.path.join(ep1.ROOT, "src", "murmuration", "ep1.py"), encoding="utf-8").read())
        bad = []
        for n in ast.walk(tree):
            if isinstance(n, ast.Attribute) and n.attr.startswith("_") and not n.attr.startswith("__"):
                v = n.value
                name = v.id if isinstance(v, ast.Name) else v.attr if isinstance(v, ast.Attribute) else ""
                if name in ("ledger", "led", "Ledger", "spend") or name.endswith("ledger"):
                    bad.append((n.lineno, name, n.attr))
        self.assertEqual(bad, [])


class ResolvedAgreesWithAnalysisTests(Base):
    def resolved_by_summarise(self, recs):
        s = ep1._summary(recs, True)
        c, t = s["hdi"]["contrasts"]["play_none"], (s["exploratory"]["paired_t"] or {}).get("play_none")
        if c["d"] is None:
            return False
        boot = (c["lo"] > 0) - (c["hi"] < 0)  # +1 above 0, -1 below 0, 0 straddles
        if boot == 0:
            return False
        return t is None or (t["ci95_lo"] > 0 and boot > 0) or (t["ci95_hi"] < 0 and boot < 0)

    def test_driver_and_analysis_agree_on_synthetic_records(self):
        import random
        self.batch("ep1", n_sets=4)
        base = [dict(r, set=r["set"] + 4 * k, taskset_id=f"heldout:{r['set'] + 4 * k}") for k in range(3) for r in self.records()]
        seen = set()
        for seed in range(40):
            rnd = random.Random(seed)
            gap, noise = rnd.choice([0, 0.05, 0.2, 0.5]) * rnd.choice([-1, 1]), rnd.choice([0.01, 0.2, 0.4])
            ys = {}
            recs = []
            for r in base:
                y = ys.setdefault((r["set"], r["arm"]), 0.5 + (gap if r["arm"] == "play" else 0) + rnd.uniform(-noise, noise))
                recs.append(dict(r, Y=min(1.0, max(0.0, y))))
            run = ep1._Run("ep1", mock.Mock(), mock.Mock(), 0, self.d, True, 12, None)
            run.recs = recs
            want = self.resolved_by_summarise(recs)
            seen.add(want)
            self.assertEqual(run._resolved(), want, (seed, gap, noise))
        self.assertEqual(seen, {True, False})


class NoTextParsingTests(unittest.TestCase):
    TEXT_OPS = {"render", "splitlines", "startswith", "endswith", "find", "index", "count", "split", "search", "match",
                "findall", "fullmatch", "rsplit", "partition", "__contains__"}

    def test_decisions_read_structured_fields_not_rendered_text(self):
        import ast
        tree = ast.parse(open(ep1.__file__, encoding="utf-8").read())
        fns = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        renders = [f.name for f in fns.values() for n in ast.walk(f)
                   if isinstance(n, ast.Attribute) and n.attr == "render" and isinstance(n.value, ast.Name) and n.value.id == "analysis"]
        self.assertEqual(renders, ["analyse"])  # display only; never in a decision
        res = fns["_resolved"]
        bad = [n.lineno for n in ast.walk(res)
               if (isinstance(n, ast.Attribute) and n.attr in self.TEXT_OPS) or (isinstance(n, ast.Name) and n.id == "re")
               or (isinstance(n, ast.Compare) and any(isinstance(o, (ast.In, ast.NotIn)) for o in n.ops))]
        self.assertEqual(bad, [])


class InvalidLogTests(Base):
    def twice(self):
        orig = ep1.tc._ModelEpisode.run

        def run_twice(ep):
            out = orig(ep)
            ep.log.append(dict(next(e for e in ep.log if e.get("action") == "work")))
            return out
        return mock.patch.object(ep1.tc._ModelEpisode, "run", run_twice)

    def test_an_invalid_log_is_void_logged_excluded_and_stops_the_batch(self):
        with self.twice():
            res = self.batch("ep1", n_sets=2)
        rec = self.records()[0]
        self.assertEqual((rec["Y"], rec["valid"], rec["status"], rec["void"]), (None, False, "void:invalid_log", "invalid_log"))
        self.assertEqual((res["reason"], res["detail"], res["voids"]), ("stopped:invalid_log", "invalid_log", {rec["arm"]: 1}))
        self.assertEqual(self.stops(), ["stopped:invalid_log"])  # not void_model: the model identity was fine
        self.assertEqual(len(self.records()), 1)

    def test_invalid_log_and_model_voids_keep_distinct_stop_reasons(self):
        self.assertEqual([ep1._why(d) for d in ("invalid_log", "void_model_mismatch", "void_no_model", "void_other")],
                         ["invalid_log", "void_model", "void_model", "void_model"])
        self.assertIn("invalid_log", spend.STOP_WHY)
        self.assertIn("void_model", spend.STOP_WHY)

    def test_a_disagreement_on_valid_is_a_scorer_disagreement(self):
        real = alloc2.score
        with mock.patch.object(alloc2, "score", lambda log, ts: dict(real(log, ts), valid=False, Y=None)):
            res = self.batch("ep1", n_sets=2)
        self.assertEqual(res["reason"], "stopped:scorer_disagreement")
        self.assertIn("valid", self.records()[0]["scorers"]["disagreement"])

    def test_analysis_never_sees_a_numeric_y_for_an_invalid_log(self):
        self.batch("ep1", n_sets=2)
        recs = [dict(r) for r in self.records()]
        ep1._summary(recs, True)  # control: valid records pass
        recs[0].update(valid=False, status="void:invalid_log")  # Y still numeric: refused, never averaged
        with self.assertRaises(analysis.AnalysisRefused):
            ep1._summary(recs, True)
        out = os.path.join(self.d, "out")
        with open(os.path.join(out, "episodes.jsonl"), "w") as f:
            for r in recs:
                f.write(json.dumps(r) + "\n")
        with self.assertRaises(analysis.AnalysisRefused):
            ep1.analyse(out)
        recs[0].update(Y=None, void="invalid_log")  # the void shape the driver writes: excluded, counted as censored
        arms = ep1._summary(recs, True)["arms"]
        self.assertEqual(arms[recs[0]["arm"]]["censored_task_sets"], 1)


if __name__ == "__main__":
    unittest.main()
