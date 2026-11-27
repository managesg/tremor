"""Throwaway-live rehearsal of the Pilot 4 command on a loopback fake server (dummy key, temp ledger dir).

Not evidence for any check. No real key, no network beyond 127.0.0.1, no paid call. Run with
`PYTHONPATH=src:tests python3 -m lab.tests.test_pilot4_rehearsal` to print the outputs, or via unittest.
"""
import contextlib
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
import fakeclaude  # noqa: E402
from lab import pilot_clearance, tremor_spend_total  # noqa: E402
from tremor import __main__ as cli  # noqa: E402
from tremor import ep1, formal_alloc, spend  # noqa: E402
from tremor.trapbench import alloc, alloc2  # noqa: E402

DUMMY_KEY = "sk-ant-DUMMY-loopback-rehearsal-0000"  # never a real key
_RUNS_SHEET = ROOT / "runs" / "d8-price-refetch.20261126T0050Z" / "price-sheet.json"  # git-ignored
SHEET = _RUNS_SHEET if _RUNS_SHEET.is_file() else ROOT / "docs" / "reports" / "tremor" / "price-sheet-20261126.json"  # tracked byte copy
SHEET_SHA256 = "2edb8b5ca979694eefe720d0fb3f0bf2a33cda73966b5c26f856392342a7a0f2"


def _lean_stub(ts, log):  # same stand-in tests/test_ep1.py uses for the unbuilt Lean scorer
    s = dict(alloc.score(log, ts), **alloc2.score(log, ts))
    return {"status": "OK", "score": {k: v for k, v in s.items() if k in formal_alloc.FIELDS}}


def _cli(argv):
    buf = io.StringIO()
    with mock.patch.dict(os.environ, {ep1.KEY_ENV: DUMMY_KEY}), contextlib.redirect_stdout(buf):
        rc = cli.main(argv)
    return rc, buf.getvalue()


def rehearse(tmp, copy_real_ledgers=False):
    """Canary then Pilot 4 against a fake server. Returns {"canary": (rc, out), "pilot4": (rc, out), ...}.
    copy_real_ledgers: read-only copy of runs/spend/*.jsonl into the throwaway dir (the real canary and its old
    price-sheet pin), so only pilot4 runs, on the refetched sheet, exactly as the real command will."""
    ldir, review = os.path.join(tmp, "ledger"), os.path.join(tmp, "review.md")
    if copy_real_ledgers:
        os.makedirs(ldir)
        for f in (ROOT / "runs" / "spend").glob("*.jsonl"):
            if f.name == "pilot4.jsonl":  # a real Pilot 4 ledger (after the real run) must not make the rehearsal refuse
                continue
            shutil.copyfile(f, os.path.join(ldir, f.name))
    sha = hashlib.sha256((ROOT / "practices" / "A.md").read_bytes()).hexdigest()
    Path(review).write_text(f"Reviewed by someone other than the author.\nreviewed_sha256: {sha}\n")
    srv, url, seen = fakeclaude.start(ep1.worst_case_responder)
    res = {}
    try:
        with mock.patch.object(spend, "PILOT_LEDGER_DIR", os.path.join(tmp, "pilot-real")), \
                mock.patch.object(ep1, "_lean", _lean_stub):
            common = ["--i-have-owner-confirm", "--base-url", url, "--ledger-dir", ldir, "--price-sheet", str(SHEET),
                      "--review", review, "--schedule-seed", "0"]
            for kind in (("pilot4",) if copy_real_ledgers else ("canary", "pilot4")):
                res[kind] = _cli(["ep1", kind, "--out-dir", os.path.join(tmp, kind)] + common)
    finally:
        srv.shutdown()
    res["requests_seen"] = len(seen)
    res["ledger"] = os.path.join(ldir, "pilot4.jsonl")
    res["outdir"] = os.path.join(tmp, "pilot4")
    return res


def _need_real_ledgers():
    """One helper: the tests that read the real, git-ignored runs/spend ledgers skip (never silently pass) when they are absent."""
    if not (ROOT / "runs" / "spend" / "canary.jsonl").is_file():
        raise unittest.SkipTest("real ledgers absent: unverified here, run in the lane checkout")


class Pilot4RehearsalTests(unittest.TestCase):
    def test_sheet_pin(self):
        self.assertEqual(hashlib.sha256(SHEET.read_bytes()).hexdigest(), SHEET_SHA256)

    def test_pilot4_opens_on_the_real_canary_lineage_with_the_new_sheet(self):
        _need_real_ledgers()
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        r = rehearse(tmp, copy_real_ledgers=True)
        self.assertEqual(r["pilot4"][0], 0, r["pilot4"][1])
        self.assertEqual(r["requests_seen"], 240)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(tremor_spend_total.main([os.path.dirname(r["ledger"]), "--batch", "pilot4"]), 0)
        self.assertIn("total_usd=0.11", out.getvalue())  # 0.0413027 prior + 0.0706710 fake pilot4

    def test_pilot4_runs_on_loopback_and_clearance_refuses_the_fake_output(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        real = spend.PILOT_LEDGER_DIR
        before = sorted(os.listdir(real)) if os.path.isdir(real) else None
        r = rehearse(tmp)
        self.assertEqual(r["canary"][0], 0, r["canary"][1])
        self.assertEqual(r["pilot4"][0], 0, r["pilot4"][1])
        self.assertNotIn(DUMMY_KEY, r["pilot4"][1])
        out = json.loads(r["pilot4"][1])
        self.assertEqual((out["kind"], out["reason"], out["episodes"]), ("pilot4", "complete", 30))
        self.assertEqual(r["requests_seen"], 1 + 240)  # one canary call, 240 Pilot 4 calls
        # clearance must refuse loopback output: the schedule says dry_run true
        with self.assertRaises(SystemExit) as ctx, contextlib.redirect_stderr(io.StringIO()):
            pilot_clearance.main([r["outdir"], r["ledger"], "--batch", "pilot4"])
        self.assertEqual(ctx.exception.code, 2)
        self.assertEqual(sorted(os.listdir(real)) if os.path.isdir(real) else None, before)  # real ledger dir untouched


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "unittest":
        unittest.main(argv=sys.argv[:1])
    d = tempfile.mkdtemp()
    try:
        r = rehearse(d, copy_real_ledgers="real" in sys.argv[1:])
        for k in [k for k in ("canary", "pilot4") if k in r]:
            print(f"## ep1 {k} rc={r[k][0]}\n{r[k][1][:3000]}")
        print("requests_seen", r["requests_seen"])
        led = [json.loads(x) for x in Path(r["ledger"]).read_text().splitlines()]
        print("ledger lines", len(led), "first", led[0].get("kind"), "last", {k: led[-1].get(k) for k in ("kind", "reason")})
        buf, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
            try:
                pilot_clearance.main([r["outdir"], r["ledger"], "--batch", "pilot4"])
            except SystemExit as e:
                print("exit", e.code)
        print("## pilot_clearance --batch pilot4 (loopback output)\n", buf.getvalue()[:3000], err.getvalue()[:1500])
    finally:
        shutil.rmtree(d, ignore_errors=True)
