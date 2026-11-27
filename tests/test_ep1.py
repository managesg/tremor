"""EP-1 batch driver (ep1.py). Fake server only: no key, no network beyond 127.0.0.1, no GPU. The real pinned ledger
directory is never written: spend.PILOT_LEDGER_DIR is patched to a temp dir in every test (and checked at the end)."""
import contextlib
import hashlib
import io
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import fakeclaude  # noqa: E402
from tremor import __main__ as cli  # noqa: E402
from tremor import analysis, ep1, formal_alloc, manifest, router, spend, team_claude  # noqa: E402
from tremor import backend_claude as bc  # noqa: E402
from tremor.trapbench import alloc, alloc2  # noqa: E402

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


class EnforcementStopTests(Base):
    def check_executed_violation(self, action_kind, requests_in_code):
        original = router.act

        def fault(action, handle, enforced):
            allow_fault = enforced and action.get("type") == action_kind
            return original(action, handle, False if allow_fault else enforced)

        prior_arms = ep1.plan("ep1", 0, 1)[0]["order"].index("code")
        with mock.patch.object(router, "act", fault):
            final = self.batch("ep1", n_sets=1)
        self.assertEqual(len(self.seen), prior_arms * 8 + requests_in_code)
        self.assertEqual(final["episodes"], prior_arms + 1)
        self.assertEqual((final["reason"], final["detail"]), ("stopped:invalid_log", "enforcement_violation"))
        self.assertEqual(final["ledger"]["stop_reason"], "stopped:invalid_log")
        last = self.records()[-1]
        self.assertEqual((last["arm"], last["ended"], last["violations_executed"]), ("code", "void", 1))
        self.assertFalse(last["rerunnable"])
        self.assertIsNone(last["Y"])
        with self.assertRaisesRegex(analysis.AnalysisRefused, "enforcement violation"):
            ep1.analyse(os.path.join(self.d, "out"))

    def test_executed_duplicate_claim_stops_in_the_first_round(self):
        self.check_executed_violation("claim", 4)

    def test_executed_unclaimed_work_stops_in_the_second_round(self):
        self.check_executed_violation("work", 8)


class ActionBoundaryTests(Base):
    def check_parser_fault(self, actions, seed, arm):
        self.canary()
        third = mock.Mock(side_effect=lean_ok)
        original = router.act
        routed = []

        def route(action, handle, enforced):
            routed.append(action["type"])
            return original(action, handle, enforced)

        with mock.patch.object(ep1.tc, "parse", side_effect=actions), mock.patch.object(router, "act", route), \
                mock.patch.object(ep1.tc.team, "_score", side_effect=AssertionError("invalid episode reached scorer")):
            final = self.batch("ep1", n_sets=1, seed=seed, canary=False, third_scorer=third)
        third.assert_called_once()  # only the startup probe
        self.assertEqual(routed, ["read"])
        self.assertEqual(len(self.seen), 1)
        self.assertEqual((final["reason"], final["detail"]), ("stopped:invalid_log", "action_boundary"))
        self.assertEqual(final["ledger"]["stop_reason"], "stopped:invalid_log")
        rec, = self.records()
        self.assertEqual((rec["arm"], rec["ended"], rec["valid"], rec["Y"], rec["rerunnable"]),
                         (arm, "void", False, None, False))
        self.assertEqual((rec["ledger"]["reserve_lines"], rec["ledger"]["charge_lines"]), (1, 1))
        with self.assertRaisesRegex(analysis.AnalysisRefused, "invalid action crossed the parser boundary"):
            ep1.analyse(os.path.join(self.d, "out"))

    def test_router_only_action_is_refused_before_dispatch(self):
        self.check_parser_fault(lambda *_: ([{"type": "post", "kind": "note", "text": "benign fixture"}], None),
                                seed=0, arm="none")

    def test_duplicate_claim_reply_is_refused_before_any_claim_dispatch(self):
        def duplicate(_text, _round, ids, _max_bytes):
            return ([{"type": "claim", "item": item} for item in sorted(ids)[:2]], None)

        self.check_parser_fault(duplicate, seed=2, arm="play")


class LedgerExclusionTests(Base):
    def test_second_process_is_refused_while_first_request_is_in_flight(self):
        script = """
import sys
from pathlib import Path
from tremor import ep1, spend

directory, review, out = map(Path, sys.argv[1:])
sheet = spend.PriceSheet.load(str(directory.parent / 'ps.json'))
shared = spend.Ledger(directory / 'ep1.jsonl', sheet, batch='ep1')
sibling = spend.Ledger(directory / 'pilot.jsonl', sheet, batch='pilot')
shared.lock_timeout = sibling.lock_timeout = 0.05

class Fake:
    def call(self, *args, **kwargs):
        raise AssertionError('contender reached a request')

def denied(action):
    try:
        action()
    except spend.SpendError as error:
        assert 'spend lock timeout' in str(error), str(error)
    else:
        raise AssertionError('contender entered the ledger')

denied(lambda: ep1.run_batch('ep1', Fake(), shared, 0, str(out), True, n_sets=1,
                             review=str(review), third_scorer=lambda *args: {'status': 'OK'}))
denied(lambda: sibling.reserve('contender:0', ep1.MODEL, 10, 10))
assert not out.exists()
assert not Path(sibling.path).exists()
"""
        loser = os.path.join(self.d, "contender")
        attempts = []

        def responder(path, headers, body, call_number):
            if call_number == 1:
                ledger_path = Path(self.ldir) / "ep1.jsonl"
                before = ledger_path.read_bytes()
                result = subprocess.run(
                    [sys.executable, "-c", script, self.ldir, self.review, loser],
                    env=dict(os.environ, PYTHONPATH=os.path.join(ep1.ROOT, "src")),
                    capture_output=True, text=True, timeout=5, check=False,
                )
                attempts.append((result, before == ledger_path.read_bytes()))
            return ep1.worst_case_responder(path, headers, body, call_number)

        final = self.batch("ep1", responder, n_sets=1)
        self.assertEqual(len(attempts), 1)
        result, unchanged = attempts[0]
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(unchanged)
        self.assertEqual(len(self.seen), 24)
        self.assertEqual(final["stamp"], ep1.FAKE)
        next_ledger = spend.Ledger(Path(self.ldir) / "next.jsonl", self.sheet)
        next_ledger.lock_timeout = 0.05
        with next_ledger.exclusive_batch():
            self.assertIn(("ep1", final["reason"]), next_ledger.totals()["stops"])

    def test_killed_owner_releases_lock_and_preserves_outstanding_reservation(self):
        self.canary()
        script = """
import os
import signal
import sys
from pathlib import Path
from tremor import ep1, spend

directory = Path(sys.argv[1])
sheet = spend.PriceSheet.load(str(directory.parent / 'ps.json'))
ledger = spend.Ledger(directory / 'ep1.jsonl', sheet, batch='ep1')
with ledger.exclusive_batch():
    ledger.reserve('killed-owner:0', ep1.MODEL, 10, 10)
    os.kill(os.getpid(), signal.SIGKILL)
"""
        result = subprocess.run(
            [sys.executable, "-c", script, self.ldir],
            env=dict(os.environ, PYTHONPATH=os.path.join(ep1.ROOT, "src")),
            capture_output=True, text=True, timeout=5, check=False,
        )
        self.assertEqual(result.returncode, -signal.SIGKILL, result.stderr)
        path = Path(self.ldir) / "ep1.jsonl"
        previous = path.read_bytes()
        final = self.batch("ep1", n_sets=1, canary=False)
        self.assertTrue(path.read_bytes().startswith(previous))
        lines = self.led.entries()
        self.assertEqual([e["kind"] for e in lines if e.get("id") == "killed-owner:0"], ["reserve"])
        self.assertEqual(final["ledger"]["calls"], 26)

    def test_driver_refuses_a_client_using_a_different_ledger(self):
        client, _, seen = self.client(ep1.worst_case_responder, "ep1")
        ledger = spend.Ledger(Path(self.ldir) / "other.jsonl", self.sheet, batch="ep1")
        out = Path(self.d) / "mismatched"
        with self.assertRaisesRegex(ValueError, "same ledger instance"):
            ep1.run_batch("ep1", client, ledger, 0, out, True, review=self.review)
        self.assertFalse(out.exists())
        self.assertFalse(seen)
        self.assertFalse(Path(ledger.path).exists())

    def test_batch_cannot_start_during_a_standalone_client_request(self):
        self.canary()
        other = spend.Ledger(Path(self.ldir) / "ep1.jsonl", self.sheet, batch="ep1")
        other.lock_timeout = 0.05
        contender = mock.Mock(ledger=other)
        contender.call.side_effect = AssertionError("contender reached a request")
        out = Path(self.d) / "contender"
        refusals = []

        def responder(path, headers, body, call_number):
            try:
                ep1.run_batch("ep1", contender, other, 0, out, True, n_sets=1, review=self.review)
            except spend.SpendError as error:
                refusals.append(str(error))
            return ep1.worst_case_responder(path, headers, body, call_number)

        client, ledger, seen = self.client(responder, "pilot")
        client.call(bc.Episode("standalone", 2_000, 10), "standalone:0", M,
                    [{"role": "user", "content": "OK"}], 300)
        self.assertEqual(len(seen), 1)
        self.assertEqual(refusals, ["spend lock timeout: failing closed"])
        self.assertFalse(out.exists())
        contender.call.assert_not_called()
        self.assertEqual([e["kind"] for e in ledger.entries() if e.get("id") == "standalone:0"],
                         ["reserve", "charge"])


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
            [os.environ.pop(k, None) for k in (ep1.KEY_ENV, ep1.LEGACY_KEY_ENV)] if env is None else None
            rc = cli.main(argv)
        return rc, buf.getvalue()

    def test_refuses_without_the_confirm_flag_and_without_the_key(self):
        out = os.path.join(self.d, "cliout")
        for cmd in ("canary", "pilot", "pilot2", "pilot3", "pilot4", "run"):
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

    def _key_gate(self, env):
        """Confirm flag plus --ledger-dir without --base-url: refused after the key check passes, before any run or write."""
        argv = ["ep1", "run", "--out-dir", os.path.join(self.d, "kout"), "--i-have-owner-confirm", "--ledger-dir", self.d]
        return self.run_cli(argv, env)

    def test_key_env_names_tremor_first_and_murmuration_as_fallback(self):
        self.assertEqual((ep1.KEY_ENV, ep1.LEGACY_KEY_ENV), ("TREMOR_EP1_KEY", "MURMURATION_EP1_KEY"))
        rc, text = self._key_gate({})  # neither set
        self.assertEqual(rc, 2)
        self.assertIn("set TREMOR_EP1_KEY", text)
        for env in ({"TREMOR_EP1_KEY": KEY}, {"MURMURATION_EP1_KEY": KEY}, {"TREMOR_EP1_KEY": KEY, "MURMURATION_EP1_KEY": KEY}):
            rc, text = self._key_gate(env)  # the key is accepted: the next gate answers
            self.assertEqual(rc, 2)
            self.assertIn("needs --base-url", text)
            self.assertNotIn(KEY, text)
        rc, text = self._key_gate({"TREMOR_EP1_KEY": "", "MURMURATION_EP1_KEY": KEY})  # empty counts as unset
        self.assertIn("needs --base-url", text)

    def test_both_key_names_set_and_different_is_refused_by_name(self):
        other = KEY + "-other"
        rc, text = self._key_gate({"TREMOR_EP1_KEY": KEY, "MURMURATION_EP1_KEY": other})
        self.assertEqual(rc, 2)
        self.assertIn("both set and differ", text)
        self.assertIn("MURMURATION_EP1_KEY", text)
        self.assertNotIn(KEY, text)
        self.assertNotIn(other, text)

    def _freeze_fixture(self):
        root = Path(self.d) / "checkout"
        frozen_files = ("src/model.py", "practices/A.md", "tests/test_model.py",
                        "formal/alloc_score/AllocScore/Basic.lean", "formal/alloc_score/lakefile.toml",
                        "formal/alloc_score/lake-manifest.json", "formal/alloc_score/lean-toolchain")
        for name in (*frozen_files, "train/local.py", "formal/alloc_score/.lake/Generated.lean"):
            f = root / name
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(name, encoding="utf-8")
        prereg = root / "prereg" / "EP1.md"
        prereg.parent.mkdir()
        digest = manifest.tree_hash([root / name for name in frozen_files], root=root)
        return root, prereg, digest

    def test_real_ep1_cli_refuses_unfrozen_or_changed_tree_before_any_side_effect(self):
        root, prereg, digest = self._freeze_fixture()
        out = os.path.join(self.d, "cliout")
        args = ["ep1", "run", "--out-dir", out, "--i-have-owner-confirm"]
        with mock.patch.object(ep1, "ROOT", root), mock.patch.object(spend, "Ledger") as ledger, \
                mock.patch.object(bc, "ClaudeClient") as client:
            cases = (("FROZEN", "", "missing, blank or invalid"), ("FROZEN", "0" * 64, "mismatch"),
                     ("DRAFT. Not cleared.", digest, "must declare Status: FROZEN"))
            for status, field, error in cases:
                with self.subTest(status=status, error=error):
                    prereg.write_text(f"Status: {status}\ncode_tree_hash: {field}\n", encoding="utf-8")
                    rc, text = self.run_cli(args, {ep1.KEY_ENV: KEY})
                    self.assertEqual(rc, 2, text)
                    self.assertIn(error, text)
            prereg.write_text(f"Status: FROZEN\ncode_tree_hash: {digest}\n", encoding="utf-8")
            (root / "tests/test_model.py").write_text("changed", encoding="utf-8")
            rc, text = self.run_cli(args, {ep1.KEY_ENV: KEY})
            self.assertEqual(rc, 2, text)
            self.assertIn("mismatch", text)
            ledger.assert_not_called()
            client.assert_not_called()
        self.assertFalse(os.path.exists(out))
        self.assertFalse(os.path.exists(spend.PILOT_LEDGER_DIR))

    def test_direct_real_ep1_run_checks_freeze_and_preserves_card_review(self):
        root, prereg, digest = self._freeze_fixture()
        out = os.path.join(self.d, "direct")
        ledger = mock.Mock(batch="ep1", exclusive_batch=lambda: contextlib.nullcontext())
        client = mock.Mock(ledger=ledger)
        with mock.patch.object(ep1, "ROOT", root), mock.patch.object(ep1.tc, "_is_real", return_value=True), \
                mock.patch.object(ep1, "_Run") as runner:
            prereg.write_text("code_tree_hash:\n", encoding="utf-8")
            with self.assertRaisesRegex(ep1.PreflightError, "freeze it first"):
                ep1.run_batch("ep1", client, ledger, 0, out, review=self.review)
            self.assertEqual(ledger.mock_calls, [])
            runner.assert_not_called()
            self.assertFalse(os.path.exists(out))

            prereg.write_text(f"Status: FROZEN\ncode_tree_hash: {digest}\n", encoding="utf-8")
            (root / "train/local.py").write_text("changed", encoding="utf-8")
            (root / "formal/alloc_score/.lake/Generated.lean").write_text("changed", encoding="utf-8")
            ledger.totals.return_value = {"stops": [("canary", "complete")]}
            with self.assertRaisesRegex(ep1.PreflightError, "no recorded review"):
                ep1.run_batch("ep1", client, ledger, 0, out, review=os.path.join(self.d, "missing.md"))
            runner.assert_not_called()
            ep1.run_batch("ep1", client, ledger, 0, out, review=self.review)
            runner.return_value.start.assert_called_once_with()
            runner.return_value.go.assert_called_once_with()

    def test_real_ep1_resume_requires_the_same_frozen_inputs(self):
        root, prereg, digest = self._freeze_fixture()
        frozen = f"Status: FROZEN\ncode_tree_hash: {digest}\n"
        prereg.write_text(frozen, encoding="utf-8")
        prompts = root / "prompts"
        prompts.mkdir()
        for name in ("system.md", "turn.md"):
            (prompts / name).write_text(name, encoding="utf-8")
        out = Path(self.d) / "resume"
        schedule = out / "schedule.json"
        ledger = mock.Mock(batch="ep1", exclusive_batch=lambda: contextlib.nullcontext())
        ledger.totals.return_value = {"stops": [("canary", "complete")]}
        client = mock.Mock(ledger=ledger)
        with (mock.patch.object(ep1, "ROOT", root),
              mock.patch.object(ep1.tc, "PROMPT_DIR", prompts),
              mock.patch.object(ep1.tc, "_is_real", return_value=True),
              mock.patch.object(ep1._Run, "go") as go):
            def run():
                return ep1.run_batch("ep1", client, ledger, 0, out, review=self.review)

            run()
            initial = schedule.read_bytes()
            self.assertEqual(json.loads(initial)["freeze"], {
                "code_tree_hash": digest,
                "prereg_sha256": hashlib.sha256(frozen.encode()).hexdigest(),
                "template_sha256": ep1.tc.template_hashes(),
            })
            run()
            self.assertEqual(go.call_count, 2)

            changed = root / "src/model.py"
            original_code = changed.read_bytes()
            changed.write_text("new code", encoding="utf-8")
            lean = root / "formal/alloc_score"
            new_digest = manifest.tree_hash([
                root / "src", root / "practices", root / "tests", lean / "AllocScore/Basic.lean",
                lean / "lakefile.toml", lean / "lake-manifest.json", lean / "lean-toolchain",
            ], root=root)
            prereg.write_text(frozen.replace(digest, new_digest), encoding="utf-8")
            with self.assertRaisesRegex(ep1.PreflightError, "different freeze"):
                run()
            changed.write_bytes(original_code)

            prereg.write_text(frozen + "Changed preregistration text.\n", encoding="utf-8")
            with self.assertRaisesRegex(ep1.PreflightError, "different freeze"):
                run()
            prereg.write_text(frozen, encoding="utf-8")
            (prompts / "turn.md").write_text("Different prompt.", encoding="utf-8")
            with self.assertRaisesRegex(ep1.PreflightError, "different freeze"):
                run()
            self.assertEqual(schedule.read_bytes(), initial)

            legacy = json.loads(initial)
            del legacy["freeze"]
            schedule.write_text(json.dumps(legacy), encoding="utf-8")
            with self.assertRaisesRegex(ep1.PreflightError, "schedule has no recorded freeze"):
                run()
            schedule.unlink()
            (out / "episodes.jsonl").write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(ep1.PreflightError, "output has no schedule"):
                run()
            self.assertFalse(schedule.exists())
            self.assertEqual(go.call_count, 2)

    def _assert_midrun_integrity_stop(self, retryable):
        root, prereg, digest = self._freeze_fixture()
        prereg.write_text(f"Status: FROZEN\ncode_tree_hash: {digest}\n", encoding="utf-8")
        self.canary()
        out = os.path.join(self.d, "integrity")

        def respond(path, headers, body, n):
            (root / "src/model.py").write_text("changed during the loopback run", encoding="utf-8")
            return fail_first(1)(path, headers, body, n) if retryable else ep1.worst_case_responder(path, headers, body, n)

        client, ledger, seen = self.client(respond, "ep1")
        with mock.patch.object(ep1, "ROOT", root):
            runner = ep1._Run("ep1", client, ledger, 0, out, True, 1, lean_ok, freeze=ep1._check_freeze())
            runner.start()
            result = runner.go()
        self.assertEqual(len(seen), 1)
        self.assertEqual(result["ledger"]["calls"], 2)  # one loopback canary and one EP-1 request
        self.assertEqual((result["reason"], result["detail"]), ("stopped:crash", "input_integrity"))
        self.assertEqual(ep1._read_jsonl(runner.vpath), [{"event": "input_integrity"}])
        current, = self.records("integrity")
        self.assertEqual(current["void"], "input_integrity")
        self.assertIsNone(current["Y"])
        self.assertFalse(current["rerunnable"])
        with self.assertRaisesRegex(analysis.AnalysisRefused, "frozen input changed"):
            ep1.analyse(out)

    def test_changed_frozen_inputs_stop_before_the_next_request(self):
        self._assert_midrun_integrity_stop(retryable=False)

    def test_changed_frozen_inputs_stop_before_the_retry(self):
        self._assert_midrun_integrity_stop(retryable=True)

    def test_paid_commands_with_both_gates_run_and_the_key_never_reaches_an_output(self):
        echo = {"error": {"type": "api_error", "message": f"bad key {KEY}"}}  # a server that echoes the key
        srv, url, seen = fakeclaude.start(lambda p, h, b, n: (500, echo) if n == 2 else ep1.worst_case_responder(p, h, b, n))
        self.srvs.append(srv)
        sheet = os.path.join(self.d, "ps2.json")
        shutil.copy(os.path.join(self.d, "ps.json"), sheet)
        common = ["--i-have-owner-confirm", "--base-url", url, "--ledger-dir", self.ldir, "--price-sheet", sheet,
                  "--review", self.review]
        outs = []
        for cmd, out in (("canary", "c"), ("pilot", "p"), ("pilot2", "p2"), ("pilot3", "p3"), ("pilot4", "p4")):
            rc, text = self.run_cli(["ep1", cmd, "--out-dir", os.path.join(self.d, out)] + common, {ep1.KEY_ENV: KEY})
            outs.append(text)
            self.assertNotIn(KEY, text)
            self.assertEqual(rc, 0, text)
        self.assertEqual([json.loads(t)["reason"] for t in outs[1:]], ["complete"] * 4)
        self.assertNotIn(KEY.encode(), files_text(self.d))  # ledger, schedule, episodes, trace, canary, final
        self.assertTrue(all(KEY not in t for t in outs))
        self.assertIn(b"[redacted]", files_text(self.ldir))  # the echoed key was scrubbed, not stored
        rc, text = self.run_cli(["ep1", "analyse", os.path.join(self.d, "p")])
        self.assertEqual(rc, 0)

    def _continuity_cli(self, extra):
        """A real `ep1 run` on a loopback ledger whose ep1 batch pinned an OLDER (expired) sheet with identical rates."""
        from datetime import date, timedelta
        with open(os.path.join(self.d, "ps.json"), encoding="utf-8") as f:
            data = json.load(f)
        old_day = date.fromisoformat(data["fetched"]) - timedelta(days=6)
        data["fetched"] = old_day.isoformat()
        old = os.path.join(self.d, "old-ps.json")
        with open(old, "w", encoding="utf-8") as f:
            json.dump(data, f)
        spend.Ledger(os.path.join(self.ldir, "ep1.jsonl"), spend.PriceSheet.load(old, today=old_day), batch="ep1") \
            .reserve("pre", ep1.MODEL, 100, 100)
        reserved = []

        def fake_run(kind, cl, led, seed, out, dry_run=False, review=None):
            reserved.append(led.reserve("c1", ep1.MODEL, 100, 100))
            return {"ok": True}
        args = ["ep1", "run", "--out-dir", os.path.join(self.d, "z"), "--i-have-owner-confirm", "--base-url", "http://127.0.0.1:9",
                "--ledger-dir", self.ldir, "--price-sheet", os.path.join(self.d, "ps.json"), "--review", self.review]
        with mock.patch.object(ep1, "run_batch", fake_run):
            rc, text = self.run_cli(args + [x.replace("OLD", old) for x in extra], {ep1.KEY_ENV: KEY})
        lines = spend.Ledger._read(os.path.join(self.ldir, "ep1.jsonl"))
        return rc, text, reserved, [e for e in lines if e["kind"] == "sheet_continuity"]

    def test_predecessor_price_sheet_flag_continues_a_batch_pinned_to_an_equal_older_sheet(self):
        rc, text, reserved, conts = self._continuity_cli(["--predecessor-price-sheet", "OLD"])
        self.assertEqual(rc, 0, text)
        self.assertEqual(len(reserved), 1)
        self.assertEqual([c["batch"] for c in conts], ["ep1"])

    def test_without_the_predecessor_flag_the_changed_sheet_is_still_refused(self):
        rc, text, reserved, conts = self._continuity_cli([])
        self.assertEqual(rc, 2, text)
        self.assertIn("changed mid-batch", text)
        self.assertEqual((reserved, conts), ([], []))

    def test_predecessor_flag_has_no_default(self):
        ns = cli.build_parser().parse_args(["ep1", "run", "--out-dir", "x"])
        self.assertIsNone(ns.predecessor_price_sheet)

    def _sheet_variant(self, name, days=0, rate=0.0):
        from datetime import date, timedelta
        with open(os.path.join(self.d, "ps.json"), encoding="utf-8") as f:
            data = json.load(f)
        data["fetched"] = (date.fromisoformat(data["fetched"]) - timedelta(days=days)).isoformat()
        m = data["models"][ep1.MODEL]
        m["output"] = m["output"] + rate
        path = os.path.join(self.d, name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        return path
    def _world(self, kind, tag=""):
        """A loopback ledger dir with the canary complete and `kind` already open, both pinned to ps.json."""
        ldir = os.path.join(self.d, "L-" + kind + tag)
        srv, url, seen = fakeclaude.start(lambda p, h, b, n: (400, {"type": "error", "error": {"type": "invalid_request_error", "message": "fake"}}))
        self.srvs.append(srv)
        if kind != "canary":
            srv2, url2, _ = fakeclaude.start(ep1.worst_case_responder)
            self.srvs.append(srv2)
            led = spend.Ledger(os.path.join(ldir, "canary.jsonl"), self.sheet, batch="canary")
            ep1.run_batch("canary", bc.ClaudeClient(KEY, led, url2, allow_host="127.0.0.1"), led, 0, os.path.join(self.d, "c-" + kind), True)
        if kind != "ep1" and not tag:  # a tagged world is fresh: nothing open yet. ep1 is opened by the canary; a canary run is gated by its parent ep1 (the canary has one call only)
            b = "ep1" if kind == "canary" else kind
            spend.Ledger(os.path.join(ldir, b + ".jsonl"), self.sheet, batch=b).reserve("pre", ep1.MODEL, 100, 100)
        return ldir, url, seen
    @staticmethod
    def _snap(ldir):
        return {f: open(os.path.join(ldir, f), "rb").read() for f in sorted(os.listdir(ldir) if os.path.isdir(ldir) else []) if f.endswith(".jsonl")}
    def _cli_err(self, kind, ldir, url, sheet, predecessor=None, tag="o"):
        argv = ["ep1", {"ep1": "run"}.get(kind, kind), "--i-have-owner-confirm", "--base-url", url, "--ledger-dir", ldir,
                "--price-sheet", sheet, "--review", self.review, "--out-dir", os.path.join(self.d, f"{kind}-{tag}")]
        if predecessor:
            argv += ["--predecessor-price-sheet", predecessor]
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, {ep1.KEY_ENV: KEY}), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = cli.main(argv)
        self.assertNotIn(KEY, out.getvalue() + err.getvalue())
        return rc, out.getvalue(), err.getvalue()
    def test_a_sheet_refusal_before_any_reservation_writes_nothing_and_the_right_invocation_still_opens_the_batch(self):
        for kind in ("canary", "pilot", "pilot2", "pilot3", "pilot4", "run"):
            ledger_kind = "ep1" if kind == "run" else kind
            with self.subTest(kind=kind):
                ldir, url, seen = self._world(ledger_kind)
                new = self._sheet_variant(f"new-{kind}.json", days=1)  # same rates, other digest: needs the predecessor proof
                before = self._snap(ldir)
                cases = {  # name -> (price sheet, predecessor, text the refusal must show)
                    "forgotten flag": (new, None, "no predecessor"),
                    "wrong predecessor path": (new, os.path.join(self.d, "nope.json"), "unreadable"),
                    "predecessor not the pinned sheet": (new, self._sheet_variant(f"p-{kind}.json", days=2, rate=0.01), "not the sheet this batch pinned"),
                    "current sheet differs by a rate": (self._sheet_variant(f"r-{kind}.json", days=1, rate=0.01),
                                                        os.path.join(self.d, "ps.json"), "differ beyond"),
                    "expired sheet": (self._sheet_variant(f"e-{kind}.json", days=30), os.path.join(self.d, "ps.json"), "days old"),
                    "wrong sheet path": (os.path.join(self.d, "nope.json"), None, "unreadable"),
                }
                for name, (sheet, pred, want) in cases.items():
                    rc, out, err = self._cli_err(kind, ldir, url, sheet, pred, tag=name[:6])
                    self.assertEqual(rc, 2, (name, out))
                    self.assertIn(want, err, name)
                    self.assertEqual(self._snap(ldir), before, name)  # byte-identical: no batch_stop, no reserve, no continuity
                    self.assertEqual(seen, [], name)
                rc, out, err = self._cli_err(kind, ldir, url, new, os.path.join(self.d, "ps.json"), tag="ok")
                self.assertEqual(rc, 0, out)
                self.assertNotIn("price sheet refused", err)  # the batch was never stopped: the correct call opens it
                self.assertEqual(len(seen), 1)  # first reservation reached the fake, which answered a mid-run HTTP 400
                lines = [e for f in self._snap(ldir).values() for e in map(json.loads, f.decode().splitlines())]
                self.assertEqual([e["batch"] for e in lines if e["kind"] == "sheet_continuity"], ["ep1" if kind == "canary" else ledger_kind])
                stop = [e["reason"] for e in lines if e["kind"] == "batch_stop" and e["batch"] == ledger_kind]
                self.assertEqual(len(stop), 1)
                self.assertTrue(stop[0].startswith("stopped:"))
                if kind != "canary":
                    self.assertEqual(stop, ["stopped:http400"])  # a refusal after a call keeps today's stop semantics
    def test_canary_refuses_a_sheet_without_a_usable_price_and_writes_nothing(self):
        for name, edit in (("missing model", lambda m, d: m.pop(ep1.MODEL)),
                           ("null rate", lambda m, d: m[ep1.MODEL].__setitem__("output", None))):
            with self.subTest(name):
                ldir, url, seen = self._world("canary", name[:4])
                with open(os.path.join(self.d, "ps.json"), encoding="utf-8") as f:
                    data = json.load(f)
                edit(data["models"], data)
                bad = os.path.join(self.d, "bad.json")
                with open(bad, "w", encoding="utf-8") as f:
                    json.dump(data, f)
                before = self._snap(ldir)
                rc, out, err = self._cli_err("canary", ldir, url, bad, tag="bad")
                self.assertEqual(rc, 2, out)
                self.assertIn("price sheet refused", err)
                self.assertEqual((self._snap(ldir), seen), (before, []))
                self.assertFalse(os.path.exists(os.path.join(self.d, "canary-bad", "canary.json")))
    def test_a_forged_batch_open_in_another_ledger_file_is_refused_with_exit_2_and_nothing_written(self):
        for kind in ("pilot4", "run"):
            ledger_kind = "ep1" if kind == "run" else kind
            with self.subTest(kind=kind):
                ldir, url, seen = self._world(ledger_kind)
                forged = {"kind": "batch_open", "batch": ledger_kind, "price_sheet": {"sha256": "f" * 64}}
                with open(os.path.join(ldir, "a-forged.jsonl"), "w", encoding="utf-8") as f:  # sorts before the real file
                    f.write(json.dumps(forged) + "\n")
                before = self._snap(ldir)
                rc, out, err = self._cli_err(kind, ldir, url, os.path.join(self.d, "ps.json"), tag="forged")
                self.assertEqual(rc, 2, out)
                self.assertIn("two files", out)
                self.assertEqual((self._snap(ldir), seen), (before, []))
    def test_a_malformed_ledger_line_is_refused_with_exit_2_and_nothing_written(self):
        for name, line in (("list batch", '{"kind": "batch_open", "batch": ["pilot4"]}'), ("list sheet", '{"kind": "batch_open", "batch": "pilot4", "price_sheet": [1]}'),
                           ("deep", "[" * 200000)):
            with self.subTest(name):
                ldir, url, seen = self._world("pilot4", name[:3] + name[-2:])
                spend.Ledger(os.path.join(ldir, "pilot4.jsonl"), self.sheet, batch="pilot4")  # directory exists
                with open(os.path.join(ldir, "a-bad.jsonl"), "w", encoding="utf-8") as f:
                    f.write(line + "\n")
                before = self._snap(ldir)
                rc, out, err = self._cli_err("pilot4", ldir, url, os.path.join(self.d, "ps.json"), tag="mal")
                self.assertEqual(rc, 2, out)
                self.assertIn("corrupt ledger", out)
                self.assertEqual((self._snap(ldir), seen), (before, []))
    def test_ledger_dir_alone_is_refused(self):
        rc, text = self.run_cli(["ep1", "run", "--out-dir", os.path.join(self.d, "z"), "--i-have-owner-confirm",
                                 "--ledger-dir", self.ldir], {ep1.KEY_ENV: KEY})
        self.assertEqual(rc, 2)

    def test_base_url_alone_is_refused(self):  # G0-2R3 N10: a fake canary must not settle in the real runs/spend
        for cmd in ("canary", "pilot", "pilot2", "pilot3", "pilot4", "run"):
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
        tree = ast.parse(open(os.path.join(ep1.ROOT, "src", "tremor", "ep1.py"), encoding="utf-8").read())
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


def thinking_responder(p, h, b, n):
    code, resp = ep1.worst_case_responder(p, h, b, n)
    resp["content"] = [{"type": "thinking", "thinking": ""}] + resp["content"]
    return code, resp


class Pilot1ChangesTests(Base):
    """Pre-freeze changes 13 to 16 at the driver: thinking off on the wire, the thinking-block stop, pilot2."""

    def test_canary_wire_body_is_exactly_the_probe_and_carries_thinking_off(self):
        out, seen = self.canary()
        self.assertEqual(out["reason"], "complete", out)
        self.assertEqual(seen[0]["body"]["thinking"], {"type": "disabled"})
        self.assertEqual(len(json.dumps(seen[0]["body"], sort_keys=True).encode()), ep1.CANARY_BYTES)

    def test_pilot2_plan_six_train_sets_five_conditions(self):
        pl = ep1.plan("pilot2", 0)
        self.assertEqual(len(pl), 6)
        self.assertTrue(all(b["split"] == "train" and sorted(b["order"]) == sorted(ep1.BASE_CONDS + tuple(ep1.PILOT_CARDS))
                            for b in pl))
        self.assertEqual(len(pl) * 5 * ep1.CALLS_PER_EPISODE, 240)
        self.assertLessEqual(240, spend.BATCH_SPECS["pilot2"]["calls"])

    def test_pilot2_after_a_stopped_pilot_runs_with_its_own_episode_ids(self):
        self.batch("pilot", n_sets=1, out="p1")
        # pilot 1 settled complete here; record a stop as well, the real state after pilot 1
        led = spend.Ledger(os.path.join(self.ldir, "pilot-stop.jsonl"), self.sheet, batch="pilot")
        led.stop_batch("void_model")
        res = self.batch("pilot2", n_sets=1, out="p2")
        self.assertEqual(res["reason"], "complete", res)
        recs, old = self.records("p2"), self.records("p1")
        self.assertEqual(len(recs), 5)
        self.assertTrue(all(r["attempt"] == 0 and r["kind"] == "pilot2" for r in recs))
        self.assertFalse(os.path.exists(os.path.join(self.d, "p2", "events.jsonl")))  # no fake "interrupted" attempts
        self.assertFalse({r["episode_id"] for r in recs} & {r["episode_id"] for r in old})
        self.assertTrue(os.path.exists(os.path.join(self.d, "p2", "pilot_trace.txt")))
        self.assertIn("cond", ep1.analyse(os.path.join(self.d, "p2")))

    def test_pilot2_refused_after_a_canary_stop(self):
        out, _ = self.canary(with_stop("max_tokens"))
        self.assertTrue(out["reason"].startswith("stopped:"))
        with self.assertRaises(spend.BatchStopped):
            self.batch("pilot2", n_sets=1, canary=False)

    def test_a_thinking_block_stops_the_batch_at_the_first_call(self):
        res = self.batch("pilot2", thinking_responder, n_sets=1)
        self.assertEqual((res["reason"], res["detail"]), ("stopped:void_model", "void_thinking_block"))
        self.assertEqual(len(self.seen), 1)
        first = ep1.plan("pilot2", 0)[0]["order"][0]
        self.assertEqual(res["voids"], {first: 1})  # keyed on the condition, not the folded arm
        self.assertEqual(self.records()[0]["turns"][0]["block_types"], ["thinking", "text"])

    def test_a_request_without_thinking_off_is_a_400_and_stops_the_batch(self):
        bad = {"type": "adaptive"}
        self.canary()
        with mock.patch.object(bc, "THINKING_OFF", bad), mock.patch.dict(ep1.tc.CAPS, thinking=bad):
            res = self.batch("pilot2", n_sets=1)
        self.assertEqual(res["reason"], "stopped:http400", res)
        self.assertEqual(self.seen[0]["body"]["thinking"], bad)

    def test_dry_run_bracket_holds(self):
        b = ep1._bracket(self.d, 0, self.review, None)
        self.assertTrue(b["floor_fails"] and b["oracle_passes"], b)


# sha256 of the 48 EP-1 request bodies (canary excluded) for n_sets=2, seed 0, recorded before the task-order factor
EP1_BODIES_SHA = "8a8e4766a9f264c528d85ce953814088283069c0d39a1de7ed593988b9c2ea8d"


class TaskOrderTests(Base):
    """Owner 2026-11-20 (prereg 16b): pilot 2 runs both task orders, one per task set, balanced, seeded without the arm."""

    def test_pilot2_task_orders_are_balanced_and_other_kinds_carry_none(self):
        for seed in range(6):
            orders = [b["task_order"] for b in ep1.plan("pilot2", seed)]
            self.assertEqual(sorted(orders), ["per_agent"] * 3 + ["shared"] * 3, seed)
        self.assertGreater(len({tuple(b["task_order"] for b in ep1.plan("pilot2", s)) for s in range(6)}), 1)  # seeded
        for kind in ("pilot", "ep1"):
            self.assertFalse(any("task_order" in b for b in ep1.plan(kind, 0)))
        self.assertEqual(len(ep1.plan("pilot2", 0)) * 5 * ep1.CALLS_PER_EPISODE, 240)
        self.assertEqual((spend.BATCH_SPECS["pilot2"]["calls"], spend.BATCH_SPECS["pilot2"]["usd"],
                          spend.BATCH_SPECS["pilot2"]["tokens"]), (260, 0.25, 598_000))

    def test_task_order_assignment_is_independent_of_the_arms(self):
        want = [b["task_order"] for b in ep1.plan("pilot2", 3)]
        with mock.patch.object(ep1, "BASE_CONDS", ("code", "none")), mock.patch.dict(ep1.PILOT_CARDS, clear=True):
            self.assertEqual([b["task_order"] for b in ep1.plan("pilot2", 3)], want)

    def test_every_arm_of_a_task_set_runs_its_order_and_the_order_is_recorded(self):
        res = self.batch("pilot2", n_sets=2)
        self.assertEqual(res["reason"], "complete", res)
        plan = {b["set"]: b["task_order"] for b in ep1.plan("pilot2", 0, 2)}
        self.assertEqual(sorted(plan.values()), ["per_agent", "shared"])
        recs = self.records()
        self.assertEqual(len(recs), 10)
        for s, o in plan.items():
            have = [r for r in recs if r["set"] == s]
            self.assertEqual({r["cond"] for r in have}, set(ep1.BASE_CONDS) | set(ep1.PILOT_CARDS))
            self.assertEqual({r["task_order"] for r in have}, {o})
            self.assertTrue(all(("pa" in r["id_tag"]) == (o == "per_agent") for r in have))
        ids = [r["episode_id"] for r in recs]
        self.assertEqual(len(set(ids)), 10)
        self.assertTrue(all(r["id_tag"].startswith("p2") for r in recs))
        tr = open(os.path.join(self.d, "out", "pilot_trace.txt")).read()
        self.assertEqual((tr.count("task_order=shared"), tr.count("task_order=per_agent")), (5, 5))
        # on the wire: per_agent sets show agents different task orders in one round, shared sets never do
        views = {}
        for x in self.seen:
            u = x["body"]["messages"][0]["content"]
            m = re.search(r"Round (\d) of 2\. You are (a\d)\.", u)
            sid = re.findall(r"^(\w+): sum \d+ \d+$", u, re.M)
            views.setdefault(tuple(sorted(sid)), {}).setdefault(m.group(1), set()).add(tuple(sid))
        self.assertEqual(sorted(any(len(v) > 1 for v in r.values()) for r in views.values()), [False, True])

    def test_pilot_report_shows_mean_y_by_order_and_arm_as_exploratory(self):
        self.batch("pilot2", n_sets=2)
        rep = ep1.analyse(os.path.join(self.d, "out"))
        self.assertIn("exploratory, not a pre-registered contrast", rep)
        for o in ("shared", "per_agent"):
            for c in ep1.BASE_CONDS + tuple(ep1.PILOT_CARDS):
                self.assertRegex(rep, rf"(?m)^{o}\s+{c}\s+1\s+\d\.\d{{3}}$")

    def test_pilot_report_prints_the_order_rule_as_a_design_decision(self):
        self.batch("pilot2", n_sets=2)
        rep = ep1.analyse(os.path.join(self.d, "out"))
        self.assertIn("order rule (prereg 16b): design decision, not a confirmatory result", rep)
        self.assertRegex(rep, r"(?m)^picked order: .*design decision, not a confirmatory result\)$")
        for o in ("shared", "per_agent"):
            self.assertRegex(rep, rf"(?m)^{o}: sets \[\d\], 1/1 with scored none and code; duplicates none=\d+ code=0")

    def test_ep1_requests_are_byte_identical_and_shared(self):
        self.batch("ep1", n_sets=2)
        bodies = [json.dumps(x["body"], sort_keys=True) for x in self.seen]
        self.assertEqual((len(bodies), hashlib.sha256("\n".join(bodies).encode()).hexdigest()), (48, EP1_BODIES_SHA))
        self.assertEqual({r["task_order"] for r in self.records()}, {"shared"})
        self.assertFalse(any("pa" in r["id_tag"] for r in self.records()))


class Pilot3Tests(Base):
    """Prereg change 19: pilot 3 repeats the pilot 2 design under its own batch and episode ids."""

    def test_pilot3_plan_is_the_pilot2_design(self):
        for seed in range(6):
            self.assertEqual(ep1.plan("pilot3", seed), ep1.plan("pilot2", seed))
        pl = ep1.plan("pilot3", 0)
        self.assertEqual((len(pl), sorted(b["task_order"] for b in pl)), (6, ["per_agent"] * 3 + ["shared"] * 3))
        self.assertEqual(len(pl) * 5 * ep1.CALLS_PER_EPISODE, 240)
        self.assertLessEqual(240, spend.BATCH_SPECS["pilot3"]["calls"])

    def test_pilot3_after_stopped_pilot_and_pilot2_runs_with_its_own_episode_ids(self):
        self.batch("pilot", n_sets=1, out="p1")
        self.batch("pilot2", n_sets=2, out="p2")
        for b in ("pilot", "pilot2"):  # the real state: both stopped
            spend.Ledger(os.path.join(self.ldir, f"{b}-stop.jsonl"), self.sheet, batch=b).stop_batch("void_model")
        res = self.batch("pilot3", n_sets=2, out="p3", canary=False)
        self.assertEqual(res["reason"], "complete", res)
        recs = self.records("p3")
        self.assertEqual(len(recs), 10)
        self.assertTrue(all(r["attempt"] == 0 and r["kind"] == "pilot3" for r in recs))
        self.assertFalse(os.path.exists(os.path.join(self.d, "p3", "events.jsonl")))  # no id collision, no "interrupted"
        old = {r["episode_id"] for r in self.records("p1") + self.records("p2")}
        self.assertFalse({r["episode_id"] for r in recs} & old)
        self.assertTrue(all(r["id_tag"].startswith("p3pa" if r["task_order"] == "per_agent" else "p3") for r in recs))
        self.assertIn("picked order:", ep1.analyse(os.path.join(self.d, "p3")))

    def test_pilot3_refused_after_a_canary_stop(self):
        out, _ = self.canary(with_stop("max_tokens"))
        self.assertTrue(out["reason"].startswith("stopped:"))
        with self.assertRaises(spend.BatchStopped):
            self.batch("pilot3", n_sets=1, canary=False)


class Pilot4Tests(Base):
    """Pilot 4 is the pilot 3 design; only the round-2 instruction line differs (array_only wording)."""
    BASE = team_claude.TURN_BASELINE_LAST
    WORDING = "Return exactly one JSON action array, starting with [ and ending with ]. Do not include any other text."

    def bodies(self, kind, out):
        self.batch(kind, n_sets=1, out=out, canary=kind != "pilot4")
        return [json.dumps(x["body"], sort_keys=True) for x in self.seen]

    def test_pilot4_registration_and_plan_equal_pilot3(self):
        for seed in range(6):
            self.assertEqual(ep1.plan("pilot4", seed), ep1.plan("pilot3", seed))
        self.assertEqual(spend.BATCH_SPECS["pilot4"], spend.BATCH_SPECS["pilot3"])
        self.assertEqual((ep1.ID_PREFIX["pilot4"], ep1.DEFAULT_SETS["pilot4"], ep1.SPLIT["pilot4"]), ("p4", 6, "train"))

    def test_round1_identical_and_round2_differs_only_in_the_instruction_line(self):
        b3 = self.bodies("pilot3", "p3")
        b4 = self.bodies("pilot4", "p4")
        self.assertEqual(len(b3), len(b4))
        self.assertEqual(len(b3), 40)
        r1 = r2 = 0
        for x, y in zip(b3, b4):
            if "Round 1 of 2" in x:
                self.assertEqual(x, y)
                r1 += 1
            else:
                self.assertIn("Round 2 of 2", x)
                self.assertNotEqual(x, y)
                self.assertEqual(x.replace(self.BASE, self.WORDING), y)
                self.assertEqual(x.count(self.BASE), 1)
                r2 += 1
        self.assertEqual((r1, r2), (20, 20))

    def test_wording_digest_is_recorded_only_for_pilot4(self):
        self.batch("pilot3", n_sets=1, out="p3")
        self.batch("pilot4", n_sets=1, out="p4", canary=False)
        digest = hashlib.sha256(self.WORDING.encode()).hexdigest()
        self.assertEqual(team_claude.PILOT4_ROUND2_WORDING, self.WORDING)
        self.assertEqual({r["round2_wording_sha256"] for r in self.records("p4")}, {digest})
        self.assertTrue(all("round2_wording_sha256" not in r for r in self.records("p3")))

    def test_pilot4_refused_after_a_canary_stop(self):
        out, _ = self.canary(with_stop("max_tokens"))
        self.assertTrue(out["reason"].startswith("stopped:"))
        with self.assertRaises(spend.BatchStopped):
            self.batch("pilot4", n_sets=1, canary=False)


def _gate(cells, n_sets=6):
    """order_gate on a synthetic pilot2 plan; cells: {set: {cond: (Y, duplicates)}}."""
    sched = {"plan": ep1.plan("pilot2", 0, n_sets)}
    recs = [{"set": s, "cond": c, "Y": y, "ended": "complete", "scores": {"duplicates": d}}
            for s, cs in cells.items() for c, (y, d) in cs.items()]
    return sched, ep1.order_gate(sched, recs)


class OrderGateTests(unittest.TestCase):
    """Prereg 16b order rule: (a) mean Y_none 0.30 to 0.80, (b) >= 2 duplicates under none, (c) Y_code != Y_none."""

    def sets(self):
        pl = ep1.plan("pilot2", 0)
        return ([b["set"] for b in pl if b["task_order"] == "shared"], [b["set"] for b in pl if b["task_order"] == "per_agent"])

    def cells(self, sh, pa):  # sh/pa: lists of (Y_none, dup_none, Y_code) per set of that order
        out = {}
        for sets, rows in ((self.sets()[0], sh), (self.sets()[1], pa)):
            for s, (yn, dn, yc) in zip(sets, rows):
                out[s] = {"none": (yn, dn), "code": (yc, 0), "play": (0.5, 0)}
        return out

    GOOD = [(0.5, 1, 0.75), (0.5, 1, 0.5), (0.25, 0, 0.5)]  # mean 5/12, 2 duplicates, code moves

    def test_both_usable_tie_goes_to_shared(self):
        _, g = _gate(self.cells(self.GOOD, self.GOOD))
        self.assertTrue(g["orders"]["shared"]["usable"] and g["orders"]["per_agent"]["usable"])
        self.assertEqual(g["picked"], "shared")
        self.assertEqual(g["label"], "design decision, not a confirmatory result")

    def test_exactly_one_usable_is_picked(self):
        locked = [(y, d, y) for y, d, _ in self.GOOD]  # (c) fails: code equals none in every set
        _, g = _gate(self.cells(locked, self.GOOD))
        self.assertEqual((g["orders"]["shared"]["c_not_locked"], g["picked"]), (False, "per_agent"))

    def test_neither_usable_picks_nothing(self):
        few = [(y, 0, c) for y, _, c in self.GOOD]  # (b) fails: 0 duplicates
        _, g = _gate(self.cells(few, few))
        self.assertIsNone(g["picked"])
        self.assertIn("criterion 5 fails", g["why"])

    def test_room_bounds(self):
        for ys, want in (([0.25, 0.25, 0.5], True), ([0.25, 0.25, 0.25], False),  # 4/12 in, 3/12 out
                         ([0.75, 0.75, 0.75], True), ([1.0, 0.75, 0.75], False)):  # 9/12 in, 10/12 out
            rows = [(y, 1, 0.0) for y in ys]
            _, g = _gate(self.cells(rows, self.GOOD))
            self.assertEqual(g["orders"]["shared"]["a_room"], want, ys)

    def test_one_duplicate_fails_b(self):
        rows = [(0.5, 1, 0.75), (0.5, 0, 0.5), (0.25, 0, 0.5)]
        _, g = _gate(self.cells(rows, self.GOOD))
        self.assertEqual((g["orders"]["shared"]["b_duplicates"], g["picked"]), (False, "per_agent"))

    def test_incomplete_order_is_not_decidable(self):
        c = self.cells(self.GOOD, self.GOOD)
        del c[self.sets()[1][2]]["code"]
        _, g = _gate(c)
        self.assertIsNone(g["orders"]["per_agent"]["usable"])
        self.assertEqual((g["picked"], g["why"]), (None, "not decidable: an order is incomplete"))
        self.assertIn("n/a (incomplete)", "\n".join(ep1._render_gate(g)))

    def test_void_episode_does_not_count(self):
        sched, _ = _gate({})
        recs = [{"set": s, "cond": c, "Y": 0.5, "ended": "complete", "scores": {"duplicates": 1}, "void": "x"}
                for s in range(6) for c in ("none", "code")]
        self.assertIsNone(ep1.order_gate(sched, recs)["picked"])


if __name__ == "__main__":
    unittest.main()
