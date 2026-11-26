"""The EP-1 price-sheet continuity path (`ep1 run ... --predecessor-price-sheet PATH`) driven through the real CLI main.

Loopback fake server on a dynamic port, a throwaway COPY of the real ledgers (the canary and the ep1 batch_open pinned to
the old sheet docs/reports/price-sheet.json), a dummy key. Not evidence for any check. No real key, no network beyond
127.0.0.1, no paid call, and nothing is written to runs/spend (its sha256 is compared before and after).
Run: PYTHONPATH=src:tests:. python3 -B -m unittest lab.tests.test_ep1_continuity_cli

Every run stops at its first reservation: the fake answers HTTP 400, so the client voids the episode and the driver stops the
batch (`http400`). The ep1 batch is never run past one call.
"""
import contextlib
import copy
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
import fakeclaude  # noqa: E402
from murmuration import __main__ as cli  # noqa: E402
from murmuration import ep1, spend  # noqa: E402

DUMMY_KEY = "sk-ant-DUMMY-loopback-continuity-0000"  # never a real key
OLD = ROOT / "docs" / "reports" / "price-sheet.json"
NEW = ROOT / "runs" / "d8-price-refetch.20261126T0050Z" / "price-sheet.json"
OLD_SHA = "16b204c23aa5ce3b169e44a3b2608ee39e3aa8da14b6b1838d8cb15a3356984f"
NEW_SHA = "2edb8b5ca979694eefe720d0fb3f0bf2a33cda73966b5c26f856392342a7a0f2"
REAL_LEDGERS = ROOT / "runs" / "spend"
# the new sheet is 3 days fresh; pin the clock to the day after its fetch so the test does not age out
CLOCK = datetime(2026, 11, 27, 12, 0, tzinfo=timezone.utc)


class _Clock(datetime):
    @classmethod
    def now(cls, tz=None):
        return CLOCK if tz is None else CLOCK.astimezone(tz)


def _digests():
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(REAL_LEDGERS.glob("*.jsonl"))}


def _lines(path):
    return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]


def _http400(path, headers, body, n):
    return 400, {"type": "error", "error": {"type": "invalid_request_error", "message": "fake: stop after the first reservation"}}


class ContinuityCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.real_before = _digests()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        t = Path(self.tmp.name)
        self.ldir = t / "ledger"
        self.ldir.mkdir()
        for f in REAL_LEDGERS.glob("*.jsonl"):
            if f.name != "ep1.jsonl":  # a real ep1 ledger (after the real run) must not make the test refuse
                shutil.copyfile(f, self.ldir / f.name)
        sha = hashlib.sha256((ROOT / "practices" / "A.md").read_bytes()).hexdigest()
        self.review = t / "review.md"
        self.review.write_text(f"Reviewed by someone other than the author.\nreviewed_sha256: {sha}\n")
        self.t = t
        self.canary_before = _lines(self.ldir / "canary.jsonl")
        self.srv, self.url, self.seen = fakeclaude.start(_http400)
        self.addCleanup(self.srv.server_close)
        self.addCleanup(self.srv.shutdown)

    def tearDown(self):
        self.assertEqual(_digests(), self.real_before, "runs/spend changed")

    def run_cli(self, sheet, predecessor=None, out="out"):
        argv = ["ep1", "run", "--i-have-owner-confirm", "--base-url", self.url, "--ledger-dir", str(self.ldir),
                "--price-sheet", str(sheet), "--review", str(self.review), "--schedule-seed", "0",
                "--out-dir", str(self.t / out)]
        if predecessor is not None:
            argv += ["--predecessor-price-sheet", str(predecessor)]
        buf, self.err = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, {ep1.KEY_ENV: DUMMY_KEY}), mock.patch.object(spend, "datetime", _Clock), \
                mock.patch.object(spend, "PILOT_LEDGER_DIR", str(self.t / "pilot-real")), \
                contextlib.redirect_stdout(buf), contextlib.redirect_stderr(self.err):
            rc = cli.main(argv)
        self.assertNotIn(DUMMY_KEY, buf.getvalue())
        return rc, buf.getvalue()

    def continuity(self):
        return [(f.name, e) for f in sorted(self.ldir.glob("*.jsonl")) for e in _lines(f) if e["kind"] == "sheet_continuity"]

    def ep1_ledger(self):
        f = self.ldir / "ep1.jsonl"
        return _lines(f) if f.exists() else []

    def assert_refused_up_front(self, rc, out, err=None):
        """A sheet refusal is raised before any reservation: exit 2, the reason on stderr, the ledger untouched."""
        self.assertEqual(rc, 2, out)
        self.assertEqual(self.continuity(), [])
        self.assertEqual(self.seen, [])
        self.assertEqual(self.ep1_ledger(), [])
        self.assertEqual(_lines(self.ldir / "canary.jsonl"), self.canary_before)
    def mutated_sheet(self, src, name):
        d = json.loads(Path(src).read_text())
        m = d["models"][sorted(d["models"])[0]]
        k = "input" if "input" in m else sorted(k for k, v in m.items() if isinstance(v, (int, float)))[0]
        m[k] = m[k] + 0.01
        p = self.t / name
        p.write_text(json.dumps(d))
        return p

    def test_pins(self):
        self.assertEqual(hashlib.sha256(OLD.read_bytes()).hexdigest(), OLD_SHA)
        self.assertEqual(hashlib.sha256(NEW.read_bytes()).hexdigest(), NEW_SHA)
        opens = {e["batch"]: e["price_sheet"]["sha256"] for e in _lines(self.ldir / "canary.jsonl") if e["kind"] == "batch_open"}
        self.assertEqual(opens, {"canary": OLD_SHA, "ep1": OLD_SHA})  # ep1's batch_open lives in canary.jsonl

    def test_a_without_predecessor_the_batch_is_refused_up_front_and_stays_openable(self):
        rc, out = self.run_cli(OLD)  # loading refuses before any ledger is touched
        self.assertEqual(rc, 2, out)
        self.assertIn("days old", out)
        self.assertEqual((self.continuity(), self.seen, self.ep1_ledger()), ([], [], []))
        rc, out = self.run_cli(NEW)  # the forgotten flag
        self.assert_refused_up_front(rc, out)
        self.assertIn("no predecessor price sheet given", self.err.getvalue())
    def test_a2_a_forgotten_flag_does_not_stop_the_batch(self):
        """The refusal wrote nothing, so the right invocation afterwards opens the batch."""
        self.run_cli(NEW)
        rc, out = self.run_cli(NEW, OLD)
        self.assertEqual(rc, 0, out)
        self.assertEqual(json.loads(out)["reason"], "stopped:http400")
        self.assertEqual(len(self.continuity()), 1)
    def test_b_correct_predecessor_opens_one_continuity_line_and_a_second_run_adds_none(self):
        rc, out = self.run_cli(NEW, OLD)
        c = self.continuity()
        self.assertEqual(c[0][0], "canary.jsonl")  # the file holding ep1's batch_open, not ep1.jsonl
        self.assertEqual([x[1] for x in c], [{"kind": "sheet_continuity", "batch": "ep1", "old_sha256": OLD_SHA,
                                              "new_sha256": NEW_SHA, "old_fetched": "2026-11-20", "new_fetched": "2026-11-26"}])
        self.assertEqual(len(self.seen), 1)  # the first reservation reached the fake, which answered 400 and stopped the run
        led = self.ep1_ledger()
        self.assertEqual([e["kind"] for e in led if e["kind"] in ("reserve", "charge")], ["reserve"])
        self.assertEqual([e["reason"] for e in led if e["kind"] == "batch_stop"], ["stopped:http400"])
        self.assertEqual(json.loads(out)["reason"], "stopped:http400")
        self.assertEqual(rc, 0, out)
        n = len(_lines(self.ldir / "canary.jsonl"))
        rc2, out2 = self.run_cli(NEW, OLD, out="out2")  # the batch is stopped: refused, and no second continuity line
        self.assertEqual(rc2, 2, out2)
        self.assertEqual((len(self.continuity()), len(_lines(self.ldir / "canary.jsonl")), len(self.seen)), (1, n, 1))
        self.assertFalse([e for e in self.ep1_ledger() if e["kind"] == "charge"])  # the fake answered 400: nothing billed

    def test_c_current_sheet_differing_by_one_rate_is_refused(self):
        rc, out = self.run_cli(self.mutated_sheet(NEW, "new-one-rate.json"), OLD)
        self.assert_refused_up_front(rc, out)

    def test_c2_predecessor_file_differing_by_one_rate_is_refused(self):
        rc, out = self.run_cli(NEW, self.mutated_sheet(OLD, "old-one-rate.json"))
        self.assert_refused_up_front(rc, out)

    def test_d_wrong_predecessor_digest_is_refused(self):
        rc, out = self.run_cli(NEW, NEW)  # a valid sheet, but not the one the batch pinned
        self.assert_refused_up_front(rc, out)
        rc, out = self.run_cli(NEW, self.t / "missing.json", out="out2")  # unreadable predecessor: refused up front too
        self.assert_refused_up_front(rc, out)


if __name__ == "__main__":
    unittest.main()
