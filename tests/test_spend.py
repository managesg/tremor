import json
import multiprocessing
import os
import sys
import tempfile
import unittest
from unittest import mock
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from murmuration import spend  # noqa: E402

M = "claude-sonnet-5-5"
P = {"input": 2, "output": 10, "cache_read": 0.1, "cache_write_5m": 2.5, "cache_write_1h": 4}


def sheet_file(d, fetched=None, models=None):
    p = os.path.join(d, "ps.json")
    with open(p, "w") as f:
        json.dump({"fetched": (fetched or datetime.now(timezone.utc).date()).isoformat(), "source_url": "https://x", "models": models or {M: P}}, f)
    return p


def _race(d, i, barrier, out):
    """Child process: reserve until refused; each process opens its own Ledger object on the one shared file."""
    led = spend.Ledger(os.path.join(d, "race.jsonl"), spend.PriceSheet.load(os.path.join(d, "ps.json")), ceiling=0.5)
    barrier.wait()
    n = 0
    for k in range(150):
        try:
            led.reserve(f"p{i}-{k}", M, 500, 400)  # worst 0.006
            n += 1
        except spend.SpendError:
            break
    out.put(n)


class SpendTests(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()

    def ledger(self, **kw):
        return spend.Ledger(os.path.join(self.d, "l.jsonl"), spend.PriceSheet.load(sheet_file(self.d)), **kw)

    def _pilot(self):
        pilot = os.path.join(os.path.realpath(tempfile.mkdtemp()), "spend")
        os.mkdir(pilot, 0o700)
        return pilot

    def test_r1_every_file_in_pilot_dir_counts(self):
        pilot = self._pilot()
        line = json.dumps({"kind": "reserve", "id": "x", "worst_usd": 4.0}) + "\n"
        for n in ("a.json", "b.log", "c.JSONL"):  # none of these matched the old *.jsonl glob
            with open(os.path.join(pilot, n), "w") as f:
                f.write(line)
        with mock.patch.object(spend, "PILOT_LEDGER_DIR", pilot):
            led = spend.Ledger(os.path.join(pilot, "d.jsonl"), spend.PriceSheet.load(sheet_file(self.d)))
            self.assertAlmostEqual(led.totals()["global_usd"], 12.0)
            with self.assertRaises(spend.SpendCeilingExceeded):
                led.reserve("n", M, 1000, 1000)
            self.assertEqual(oct(os.stat(pilot).st_mode & 0o777), "0o700")

    def test_r1_pilot_dir_refuses_symlink_or_subdir_entries(self):
        pilot = self._pilot()
        led_path = os.path.join(pilot, "d.jsonl")
        for make in (lambda: os.mkdir(os.path.join(pilot, "sub")), lambda: os.symlink(self.d, os.path.join(pilot, "lnk"))):
            make()
            with mock.patch.object(spend, "PILOT_LEDGER_DIR", pilot):
                led = spend.Ledger(led_path, spend.PriceSheet.load(sheet_file(self.d)))
                with self.assertRaises(spend.SpendError):
                    led.reserve("n", M, 1000, 1000)
            for n in os.listdir(pilot):
                p = os.path.join(pilot, n)
                os.rmdir(p) if os.path.isdir(p) and not os.path.islink(p) else os.unlink(p)

    def test_non_pilot_dir_still_counts_only_jsonl(self):  # the sheet lives beside the ledgers in tests
        led = self.ledger()
        sheet_file(self.d)
        led.reserve("a", M, 1000, 1000)

    def test_sheet_missing_stale_null_refused(self):
        with self.assertRaises(spend.PriceSheetRefused):
            spend.PriceSheet.load(os.path.join(self.d, "nope.json"))
        with self.assertRaises(spend.PriceSheetRefused):
            spend.PriceSheet.load(sheet_file(self.d, datetime.now(timezone.utc).date() - timedelta(days=4)))
        spend.PriceSheet.load(sheet_file(self.d, datetime.now(timezone.utc).date() - timedelta(days=3)))
        s = spend.PriceSheet.load(sheet_file(self.d, models={M: {**P, "output": None}}))
        with self.assertRaises(spend.PriceSheetRefused):
            spend.Ledger(os.path.join(self.d, "l2"), s).estimate(M, {"input_tokens": 1})

    def test_estimate_all_fields(self):
        u = {"input_tokens": 1_000_000, "output_tokens": 1_000_000, "cache_read_input_tokens": 1_000_000,
             "cache_creation_input_tokens": 2_000_000,
             "cache_creation": {"ephemeral_5m_input_tokens": 1_000_000, "ephemeral_1h_input_tokens": 1_000_000}}
        self.assertAlmostEqual(self.ledger().estimate(M, u), 2 + 10 + 0.1 + 2.5 + 4)
        u2 = {"input_tokens": 0, "cache_creation_input_tokens": 1_000_000}  # no breakdown: dearer 1h rate
        self.assertAlmostEqual(self.ledger().estimate(M, u2), 4)

    def test_ceiling_before_call(self):
        led = self.ledger(ceiling=0.001)
        with self.assertRaises(spend.SpendCeilingExceeded):
            led.reserve("a", M, 1000, 1000)  # worst = 0.012
        self.assertFalse(os.path.exists(led.path))  # nothing written, so no call was reserved
        led.reserve("b", M, 10, 10)  # 0.00012
        self.assertEqual(led.totals()["calls"], 1)

    def test_unfinished_reserve_counts_and_dup_refused(self):
        led = self.ledger(ceiling=0.02)
        led.reserve("a", M, 1000, 1000)  # 0.012 stays reserved: the call may have run
        with self.assertRaises(spend.SpendCeilingExceeded):
            led.reserve("b", M, 1000, 1000)
        with self.assertRaises(spend.SpendError):
            led.reserve("a", M, 1, 1)

    def test_max_calls(self):
        led = self.ledger(max_calls=2)
        led.reserve("a", M, 1, 1)
        led.reserve("b", M, 1, 1)
        with self.assertRaises(spend.MaxCallsExceeded):
            led.reserve("c", M, 1, 1)

    def test_charge_replaces_reserve_and_survives_reopen(self):
        led = self.ledger()
        led.reserve("a", M, 1000, 1000)
        usd = led.charge("a", M, {"input_tokens": 10, "output_tokens": 10})
        self.assertAlmostEqual(self.ledger().totals()["spent_usd"], usd)

    def test_long_context_tier(self):
        s = spend.PriceSheet.load(sheet_file(self.d, models={M: {**P, "long_context": {"threshold_input_tokens": 100, **{k: v * 5 for k, v in P.items()}}}}))
        self.assertEqual(s.prices(M, 100)["input"], 2)
        self.assertEqual(s.prices(M, 101)["input"], 10)

    def test_d1_global_cap_across_ledgers(self):
        self.assertEqual(spend.HARD_CAP_USD, 10.0)
        sh = spend.PriceSheet.load(sheet_file(self.d))
        n = 0
        for i in range(14):  # each fresh ledger is under its own 9.00 ceiling; 1.0 USD worst case each
            try:
                spend.Ledger(os.path.join(self.d, f"fresh{i}.jsonl"), sh).reserve("a", M, 100_000, 60_000)  # 1.0 USD
                n += 1
            except spend.SpendCeilingExceeded:
                pass
        self.assertEqual(n, 10)  # 10 x 1.0 fits the 10.00 cap exactly, an 11th would not
        total = sum(spend.Ledger(os.path.join(self.d, f"fresh{i}.jsonl"), sh).totals()["spent_usd"] for i in range(14))
        self.assertLessEqual(total, 10.0)

    def test_d1_cap_counts_other_ledgers_even_for_a_low_ceiling(self):
        sh = spend.PriceSheet.load(sheet_file(self.d))
        spend.Ledger(os.path.join(self.d, "a.jsonl"), sh, ceiling=10.0).reserve("x", M, 2_300_000, 60_000)  # 9.2 + 0.6 = 9.8 USD
        with self.assertRaises(spend.SpendCeilingExceeded):
            spend.Ledger(os.path.join(self.d, "b.jsonl"), sh).reserve("y", M, 100_000, 10_000)  # 0.5
        spend.Ledger(os.path.join(self.d, "b.jsonl"), sh).reserve("y", M, 1000, 1000)  # 0.014: fits under 10.00

    def test_d2_processes_never_exceed_ceiling(self):
        sheet_file(self.d)
        ctx = multiprocessing.get_context("fork")
        bar, out = ctx.Barrier(4), ctx.Queue()
        ps = [ctx.Process(target=_race, args=(self.d, i, bar, out)) for i in range(4)]
        for p in ps:
            p.start()
        counts = [out.get(timeout=60) for _ in ps]
        for p in ps:
            p.join(30)
        self.assertEqual(sum(counts), 83)  # 0.5 / 0.006 worst case: exact, no overshoot, no lost slot
        t = spend.Ledger(os.path.join(self.d, "race.jsonl"), spend.PriceSheet.load(os.path.join(self.d, "ps.json"))).totals()
        self.assertLessEqual(t["global_usd"], 0.5 + 1e-9)

    def test_d2_lock_timeout_fails_closed(self):
        import fcntl
        led = self.ledger()
        led.lock_timeout = 0.2
        fd = os.open(os.path.join(self.d, ".spend.lock"), os.O_RDWR | os.O_CREAT)
        fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            with self.assertRaises(spend.SpendError):
                led.reserve("a", M, 10, 10)
        finally:
            os.close(fd)
        self.assertFalse(os.path.exists(led.path))

    def test_d3_nonfinite_refused_everywhere(self):
        nan, inf = float("nan"), float("inf")
        for bad in (nan, inf, -1, "2", True):  # price sheet values
            with self.assertRaises(spend.PriceSheetRefused, msg=repr(bad)):
                spend.PriceSheet.load(sheet_file(self.d, models={M: {**P, "input": bad}}))
        with open(os.path.join(self.d, "nan.json"), "w") as f:  # a literal NaN token in the file
            f.write('{"fetched": "%s", "source_url": "https://x", "models": {"%s": {"input": NaN, "output": 1, "cache_read": 1, "cache_write_5m": 1, "cache_write_1h": 1}}}'
                    % (datetime.now(timezone.utc).date().isoformat(), M))
        with self.assertRaises(spend.PriceSheetRefused):
            spend.PriceSheet.load(os.path.join(self.d, "nan.json"))
        led = self.ledger()
        for bad in (nan, inf, -5, "x", True, 1.5):
            with self.assertRaises(spend.SpendError, msg=repr(bad)):
                led.estimate(M, {"input_tokens": bad, "output_tokens": 1})
        led.reserve("a", M, 10, 10)
        with self.assertRaises(spend.SpendError):
            led.charge("a", M, {"input_tokens": nan, "output_tokens": 1})
        self.assertNotIn("NaN", open(led.path).read())

    def test_d3_corrupt_ledger_line_stops_the_run(self):
        led = self.ledger()
        led.reserve("a", M, 10, 10)
        for junk in (b"{not json\n", b'{"kind":"reserve","id":"z","worst_usd":NaN}\n', b'{"kind":"charge","id":"a","usd":-5}\n'):
            with open(led.path, "ab") as f:
                f.write(junk)
            with self.assertRaises(spend.SpendError):
                led.reserve("b", M, 10, 10)
            with self.assertRaises(spend.SpendError):
                self.ledger().totals()
            with open(led.path, "rb") as f:
                good = f.read().splitlines()[:-1]
            with open(led.path, "wb") as f:
                f.write(b"\n".join(good) + b"\n")
        # a corrupt line in ANOTHER ledger of the directory stops this one too
        with open(os.path.join(self.d, "other.jsonl"), "wb") as f:
            f.write(b"garbage\n")
        with self.assertRaises(spend.SpendError):
            led.reserve("c", M, 10, 10)

    def test_d4_argument_validation(self):
        sh = spend.PriceSheet.load(sheet_file(self.d))
        p = os.path.join(self.d, "v.jsonl")
        for c in (0, -1, 10.01, 1000, float("nan"), float("inf"), "9", None, True):
            with self.assertRaises(spend.SpendError, msg=repr(c)):
                spend.Ledger(p, sh, ceiling=c)
        for mc in (0, -1, 1.5, "3", True):
            with self.assertRaises(spend.SpendError, msg=repr(mc)):
                spend.Ledger(p, sh, max_calls=mc)
        spend.Ledger(p, sh, ceiling=10.0)  # the cap itself is allowed, never above
        led = spend.Ledger(p, sh)
        for ub, mt in ((10, -10**6), (-5, 10), (10, 0), (0, 10), (10, 1.5), (1.5, 10), (10, float("nan")), (10, spend.MAX_TOKENS_LIMIT + 1), (True, 10)):
            with self.assertRaises(spend.SpendError, msg=repr((ub, mt))):
                led.reserve("n", M, ub, mt)
        self.assertFalse(os.path.exists(p))

    def test_d6_charge_over_reserved_marks_overspent_across_ledgers(self):
        led = self.ledger()
        led.reserve("a", M, 10, 10)
        with self.assertRaises(spend.Overspent):
            led.charge("a", M, {"input_tokens": 5_000_000, "output_tokens": 1})
        self.assertGreater(led.totals()["spent_usd"], 10)  # true cost recorded
        other = spend.Ledger(os.path.join(self.d, "o.jsonl"), spend.PriceSheet.load(sheet_file(self.d)))
        with self.assertRaises(spend.Overspent):
            other.reserve("b", M, 1, 1)
        with self.assertRaises(spend.SpendError):
            led.charge("zzz", M, {"input_tokens": 1, "output_tokens": 1})  # no reserve

    def test_expiry_date(self):
        s = spend.PriceSheet.load(sheet_file(self.d))
        self.assertEqual(s.expires_on(), datetime.now(timezone.utc).date() + timedelta(days=3))

    def test_default_ceiling(self):
        self.assertEqual(self.ledger().ceiling, 9.0)


if __name__ == "__main__":
    unittest.main()
