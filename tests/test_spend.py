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


def _batch_race(d, i, barrier, out):
    led = spend.Ledger(os.path.join(d, f"proc{i}.jsonl"), spend.PriceSheet.load(os.path.join(d, "ps.json")), batch="ep1")
    barrier.wait()
    n = 0
    for k in range(40):
        try:
            led.reserve(f"p{i}-{k}", M, 100, 100)
            n += 1
        except spend.SpendError:
            break
    out.put(n)


SMALL = {"ep1": {"usd": 5.0, "calls": 10, "tokens": 3000, "parent": None},
         "canary": {"usd": 0.05, "calls": 1, "tokens": 2500, "parent": "ep1", "canary_input_tokens_max": 20_000}}


class BatchTests(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.sheet = spend.PriceSheet.load(sheet_file(self.d))

    def led(self, batch="ep1", name="l.jsonl", **kw):
        return spend.Ledger(os.path.join(self.d, name), self.sheet, batch=batch, **kw)

    def cheap(self, name):  # Haiku-like prices: a 90,000-byte canary fits USD 0.05
        return spend.Ledger(os.path.join(self.d, name), spend.PriceSheet.load(sheet_file(self.d, models={M: {**P, "input": 0.1, "output": 0.5, "cache_write_5m": 0.2, "cache_write_1h": 0.2}})), batch="canary")

    def test_usage_over_reservation_in_a_batch_writes_overspent(self):  # R1
        led = self.led()
        led.reserve("a", M, 100, 100)
        with self.assertRaises(spend.BatchStopped):
            led.charge("a", M, {"input_tokens": 100_000, "output_tokens": 100})
        kinds = [e["kind"] for e in led._lines()]
        self.assertIn("overspent", kinds)
        self.assertIn("batch_stop", kinds)
        with self.assertRaises(spend.Overspent):  # the whole directory, any file
            self.led("ep1", "other.jsonl").reserve("b", M, 100, 100)

    def test_unbatched_ledger_cannot_bypass_batch_caps(self):  # R2
        self.led().reserve("a", M, 100, 100)
        with self.assertRaises(spend.BatchStopped):
            self.led(batch=None, name="u.jsonl").reserve("b", M, 100, 100)

    def test_default_specs_are_the_program_caps(self):
        e, c = spend.BATCH_SPECS["ep1"], spend.BATCH_SPECS["canary"]
        self.assertEqual((e["usd"], e["calls"], e["tokens"]), (5.0, 500, 1_250_000))
        self.assertEqual((c["usd"], c["parent"]), (0.05, "ep1"))
        self.assertLessEqual(e["usd"], spend.DEFAULT_CEILING)
        self.assertLessEqual(spend.DEFAULT_CEILING, spend.HARD_CAP_USD)
        with self.assertRaises(spend.SpendError):
            self.led(batch="ep2")

    def test_subcap_cannot_exceed_parent(self):
        for k, v in (("usd", 5.01), ("calls", 501), ("tokens", 1_250_001)):
            bad = {"ep1": dict(spend.BATCH_SPECS["ep1"]), "canary": {**spend.BATCH_SPECS["canary"], k: v}}
            with mock.patch.object(spend, "BATCH_SPECS", bad), self.assertRaises(spend.SpendError, msg=k):
                self.led()
        bad = {"ep1": {**spend.BATCH_SPECS["ep1"], "usd": 9.5}, "canary": spend.BATCH_SPECS["canary"]}  # root above the 9.00 default
        with mock.patch.object(spend, "BATCH_SPECS", bad), self.assertRaises(spend.SpendError):
            self.led()
        cyc = {"a": {"usd": 1, "calls": 1, "tokens": 1, "parent": "b"}, "b": {"usd": 1, "calls": 1, "tokens": 1, "parent": "a"}}
        with mock.patch.object(spend, "BATCH_SPECS", cyc), self.assertRaises(spend.SpendError):
            self.led(batch="a")

    def test_records_tagged_and_sheet_pinned_in_first_record(self):
        led = self.led()
        led.reserve("a", M, 100, 100)
        lines = led._lines()
        self.assertEqual(lines[0]["kind"], "batch_open")
        self.assertEqual(lines[0]["price_sheet"], self.sheet.source())  # sha256 + dated source
        self.assertEqual(lines[1]["batch"], "ep1")
        led.charge("a", M, {"input_tokens": 10, "output_tokens": 5})
        self.assertEqual(led._lines()[-1]["batch"], "ep1")

    def test_sheet_change_mid_batch_refused(self):
        self.led().reserve("a", M, 100, 100)
        other = os.path.join(self.d, "sub")
        os.mkdir(other)
        p2 = sheet_file(other, models={M: {**P, "input": 3}})
        led2 = spend.Ledger(os.path.join(self.d, "l2.jsonl"), spend.PriceSheet.load(p2), batch="ep1")
        with self.assertRaises(spend.PriceSheetRefused):
            led2.reserve("b", M, 100, 100)

    def test_per_call_caps_and_one_canary_exception(self):
        led = self.led()
        led.reserve("a", M, 2000, 300)
        for ub, mt in ((2001, 10), (10, 301)):
            with self.assertRaises(spend.SpendError):
                led.reserve(f"x{ub}", M, ub, mt)
        with self.assertRaises(spend.SpendError):  # the exception is not available to ep1
            led.reserve("b", M, 5000, 100, canary_input_tokens=5000)
        with self.assertRaises(spend.SpendError):  # nor to an unbatched ledger
            self.led(batch=None, name="u.jsonl").reserve("c", M, 5000, 100, canary_input_tokens=5000)
        self.d = tempfile.mkdtemp()  # a different sheet than ep1's pinned one needs a different directory
        can = self.cheap("c.jsonl")
        for bad in (90_001, 0, -1, True, 1.5, float('nan'), float('inf'), float('-inf')):
            with self.assertRaises(spend.SpendError, msg=repr(bad)):
                can.reserve("k", M, 100, 100, canary_input_tokens=bad)
        with self.assertRaises(spend.SpendError):  # ub above the declared figure
            can.reserve("k", M, 6000, 100, canary_input_tokens=5000)
        with self.assertRaises(spend.SpendError):  # without the declaration the 2,000 cap applies
            can.reserve("k", M, 5000, 100)
        can.reserve("k", M, 90_000, 300, canary_input_tokens=90_000)  # exactly the cap, once

    def test_canary_cap_is_exactly_90000_and_nonfinite_or_negative_refused(self):
        self.assertEqual(spend.BATCH_SPECS["canary"]["canary_input_tokens_max"], 90_000)
        self.assertEqual(spend.BATCH_SPECS["canary"]["tokens"], 90_300)
        self.assertEqual((spend.PER_CALL_INPUT_TOKENS, spend.PER_CALL_OUTPUT_TOKENS), (2_000, 300))
        can = self.cheap("c.jsonl")
        for ub, decl in ((90_001, 90_001), (90_001, 90_000), (50_000, 90_001), (50_000, float("nan")), (50_000, float("inf")), (50_000, -90_000)):
            with self.assertRaises(spend.SpendError, msg=(ub, decl)):
                can.reserve("k", M, ub, 100, canary_input_tokens=decl)
        with self.assertRaises(spend.SpendError):  # output stays capped at 300 even in the canary
            can.reserve("k", M, 90_000, 301, canary_input_tokens=90_000)
        self.assertEqual(spend.batch_report(self.d, "canary")["calls"], 0)  # nothing was reserved by the refusals
        can.reserve("k", M, 90_000, 300, canary_input_tokens=90_000)
        self.assertEqual(spend.batch_report(self.d, "canary")["calls"], 1)

    def test_canary_worst_case_at_haiku_price_is_below_its_subcap(self):
        sheet = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "reports", "price-sheet.json")))
        h = sheet["models"]["claude-haiku-5-5"]
        self.assertLess(90_000, h["long_context"]["threshold_input_tokens"])  # the standard (not long-context) tier applies
        top_in = max(h["input"], h["cache_write_5m"], h["cache_write_1h"])  # the ledger reserves at the dearest input rate
        worst = (90_000 * top_in + 300 * h["output"]) / 1e6
        self.assertAlmostEqual(worst, 0.01815, places=9)  # 0.018 input + 0.00015 output, real sheet numbers
        self.assertLess(worst, spend.BATCH_SPECS["canary"]["usd"])  # USD 0.05 sub-cap holds, not raised
        self.assertEqual(spend.BATCH_SPECS["canary"]["usd"], 0.05)
        hk = "claude-haiku-5-5"
        prices = {k: h[k] for k in ("input", "output", "cache_read", "cache_write_5m", "cache_write_1h")}
        led = spend.Ledger(os.path.join(self.d, "h.jsonl"), spend.PriceSheet.load(sheet_file(self.d, models={hk: prices})), batch="canary")
        self.assertAlmostEqual(led.reserve("k", hk, 90_000, 300, canary_input_tokens=90_000), worst, places=9)

    def test_canary_exception_cannot_be_reused(self):
        can = self.cheap("c.jsonl")
        can.reserve("k1", M, 90_000, 100, canary_input_tokens=90_000)
        with self.assertRaises(spend.MaxCallsExceeded):  # same ledger
            can.reserve("k2", M, 90_000, 100, canary_input_tokens=90_000)
        with self.assertRaises(spend.MaxCallsExceeded):  # a fresh Ledger object on another file of the directory
            self.cheap("c2.jsonl").reserve("k3", M, 90_000, 100, canary_input_tokens=90_000)
        with self.assertRaises(spend.SpendError):
            self.led("ep1", "e.jsonl").reserve("k4", M, 90_000, 100, canary_input_tokens=90_000)
        for alias in ("Canary", "canary ", "canary2", "ep1/canary"):  # nor under another batch-id spelling
            with self.assertRaises(spend.SpendError, msg=alias):
                spend.Ledger(os.path.join(self.d, "a.jsonl"), self.sheet, batch=alias)

    def test_canary_exception_refused_in_ep1_at_any_size(self):
        ep = self.led("ep1", "e.jsonl")
        for n in (2_001, 20_000, 90_000):
            with self.assertRaises(spend.SpendError, msg=n):
                ep.reserve(f"e{n}", M, n, 100, canary_input_tokens=n)
        with self.assertRaises(spend.SpendError):
            ep.reserve("e-plain", M, 90_000, 100)

    def test_canary_counts_inside_ep1(self):
        with mock.patch.object(spend, "BATCH_SPECS", SMALL):
            self.led("canary", "c.jsonl").reserve("k", M, 1000, 100)
            e = self.led("ep1", "e.jsonl")
            rep = spend.batch_report(self.d, "ep1")
            self.assertEqual((rep["calls"], rep["tokens"]), (1, 1100))
            self.assertEqual(rep["remaining"]["calls"], 9)
            for i in range(9):
                e.reserve(f"e{i}", M, 100, 100)  # ep1's 10 calls include the canary's one
            with self.assertRaises(spend.MaxCallsExceeded):
                e.reserve("e9", M, 100, 100)

    def test_token_meter_refuses_a_call_that_could_cross(self):
        with mock.patch.object(spend, "BATCH_SPECS", SMALL):
            led = self.led()
            led.reserve("a", M, 1000, 100)
            led.charge("a", M, {"input_tokens": 600, "output_tokens": 50})  # meter = recorded usage 650 (not the 1100 reserved)
            self.assertEqual(spend.batch_report(self.d, "ep1")["tokens"], 650)
            led.reserve("b", M, 1000, 100)  # in flight: worst case counts
            led.reserve("c", M, 700, 50)  # 650 + 1100 + 750 = 2500
            with self.assertRaises(spend.SpendCeilingExceeded):
                led.reserve("d", M, 300, 201)
            led.reserve("d", M, 300, 200)  # exactly 3000

    def test_cache_creation_stops_the_batch(self):
        led = self.led()
        led.reserve("a", M, 100, 100)
        with self.assertRaises(spend.BatchStopped):
            led.charge("a", M, {"input_tokens": 10, "output_tokens": 5, "cache_creation_input_tokens": 1})
        with self.assertRaises(spend.BatchStopped):
            self.led(name="other.jsonl").reserve("b", M, 100, 100)
        with self.assertRaises(spend.BatchStopped):  # the canary sits inside the stopped ep1
            self.led("canary", "c.jsonl").reserve("c", M, 100, 100)
        self.assertIn("cache_creation", spend.batch_report(self.d, "ep1")["stop_reason"])
        self.assertTrue(spend.batch_report(self.d, "ep1")["calls"] == 1)

    def test_breakdown_only_cache_creation_also_stops(self):
        led = self.led()
        led.reserve("a", M, 100, 100)
        with self.assertRaises(spend.BatchStopped):
            led.charge("a", M, {"input_tokens": 1, "output_tokens": 1, "cache_creation": {"ephemeral_1h_input_tokens": 3}})

    def test_missing_or_nonfinite_usage_stops_the_batch(self):
        for i, bad in enumerate(({"output_tokens": 5}, {"input_tokens": float("nan"), "output_tokens": 1}, None)):
            d = tempfile.mkdtemp()
            led = spend.Ledger(os.path.join(d, "l.jsonl"), spend.PriceSheet.load(sheet_file(d)), batch="ep1")
            led.reserve("a", M, 100, 100)
            with self.assertRaises(spend.SpendError):
                led.charge("a", M, bad)
            with self.assertRaises(spend.SpendError):
                led.reserve("b", M, 100, 100)
            self.assertIn("invalid usage", spend.batch_report(d, "ep1")["stop_reason"])  # a batch_stop line, not only the global overspent
            self.assertEqual(spend.batch_report(d, "ep1")["tokens_by_class"]["unmetered_worst"], 200)  # worst case stands

    def test_usage_above_the_reservation_stops(self):
        led = self.led()
        led.reserve("a", M, 100, 100)
        with self.assertRaises(spend.BatchStopped):
            led.charge("a", M, {"input_tokens": 150, "output_tokens": 100})

    def test_unbatched_ledger_is_unchanged(self):
        led = spend.Ledger(os.path.join(self.d, "u.jsonl"), self.sheet)
        led.reserve("a", M, 50_000, 5000)  # beyond the per-call caps: fine without a batch
        led.charge("a", M, {"input_tokens": 1, "output_tokens": 1, "cache_creation_input_tokens": 5})

    def test_report_fields(self):
        led = self.led()
        led.reserve("a", M, 100, 100)
        led.charge("a", M, {"input_tokens": 10, "output_tokens": 5, "cache_read_input_tokens": 3})
        led.reserve("b", M, 100, 100)  # in flight
        r = spend.batch_report(self.d, "ep1")
        self.assertEqual((r["calls"], r["tokens"]), (2, 218))
        self.assertEqual(r["tokens_by_class"], {"input": 10, "output": 5, "cache_read": 3, "cache_creation": 0, "unmetered_worst": 200})
        self.assertIsNone(r["stop_reason"])
        self.assertEqual(r["remaining"]["calls"], 498)
        self.assertEqual(r["remaining"]["tokens"], 1_250_000 - 218)
        self.assertEqual(r["price_sheet_sha256"], self.sheet.sha256)
        self.assertAlmostEqual(r["usd"], led.totals()["spent_usd"])
        with self.assertRaises(spend.SpendError):
            spend.batch_report(self.d, "nope")

    def test_fuzz_worst_case_schedule_of_500_calls(self):
        # every call as large as allowed and reporting its full reservation: USD binds nowhere, calls and tokens do
        led = self.led()
        for i in range(500):
            led.reserve(f"w{i}", M, 2000, 300)
            led.charge(f"w{i}", M, {"input_tokens": 2000, "output_tokens": 300})
        with self.assertRaises(spend.MaxCallsExceeded):
            led.reserve("w500", M, 1, 1)
        r = spend.batch_report(self.d, "ep1")
        self.assertEqual((r["calls"], r["tokens"]), (500, 1_150_000))
        self.assertLessEqual(r["tokens"], 1_250_000)
        self.assertLessEqual(r["usd"], 5.0)

    def test_fuzz_random_schedule_never_crosses_any_cap(self):
        import random
        pricey = os.path.join(self.d, "pricey")
        os.mkdir(pricey)
        sh = spend.PriceSheet.load(sheet_file(pricey, models={M: {**P, "input": 400, "output": 2000, "cache_write_5m": 400, "cache_write_1h": 400}}))
        led = spend.Ledger(os.path.join(pricey, "f.jsonl"), sh, batch="ep1")  # worst call 1.4 USD: USD binds first
        rng, ok = random.Random(7), 0
        for i in range(500):
            ub, mt = rng.randint(1, 2000), rng.randint(1, 300)
            try:
                led.reserve(f"f{i}", M, ub, mt)
            except spend.SpendError:
                continue
            ok += 1
            led.charge(f"f{i}", M, {"input_tokens": rng.randint(0, ub), "output_tokens": rng.randint(0, mt)})
            r = spend.batch_report(pricey, "ep1")
            self.assertLessEqual(r["usd"], 5.0)
            self.assertLessEqual(r["calls"], 500)
            self.assertLessEqual(r["tokens"], 1_250_000)
        self.assertGreater(ok, 3)
        self.assertLess(ok, 500)

    def test_second_process_cannot_double_the_budget(self):
        sheet_file(self.d)
        with mock.patch.object(spend, "BATCH_SPECS", SMALL):
            ctx = multiprocessing.get_context("fork")
            bar, out = ctx.Barrier(3), ctx.Queue()
            ps = [ctx.Process(target=_batch_race, args=(self.d, i, bar, out)) for i in range(3)]
            for p in ps:
                p.start()
            counts = [out.get(timeout=60) for _ in ps]
            for p in ps:
                p.join(30)
            self.assertEqual(sum(counts), 10)  # three files, one budget
            self.assertEqual(spend.batch_report(self.d, "ep1")["calls"], 10)
        # the same holds across Ledger objects in one process (new file = no fresh budget)
        self.assertEqual(spend.batch_report(self.d, "ep1")["remaining"]["calls"], 490)

    def test_ep1_cap_fits_480_calls_plus_canary_at_full_reservation(self):
        self.assertEqual(spend.BATCH_SPECS["ep1"]["tokens"], 1_250_000)
        sh = spend.PriceSheet.load(sheet_file(self.d, models={M: {**P, "input": 0.1, "output": 0.5, "cache_write_5m": 0.2, "cache_write_1h": 0.2}}))
        cn = spend.Ledger(os.path.join(self.d, "c.jsonl"), sh, batch="canary")
        cn.reserve("c", M, 90_000, 300, canary_input_tokens=90_000)  # counted inside ep1
        led = spend.Ledger(os.path.join(self.d, "l.jsonl"), sh, batch="ep1")
        for i in range(480):
            led.reserve(f"w{i}", M, 2000, 300)  # never charged: the full reservation stands
        self.assertEqual(spend.batch_report(self.d, "ep1")["tokens"], 90_300 + 480 * 2300)
        for i in range(480, 499):  # canary + 499 full calls = the 500-call cap; tokens (1,238,000) still fit
            led.reserve(f"w{i}", M, 2000, 300)
        self.assertEqual(spend.batch_report(self.d, "ep1")["tokens"], 90_300 + 499 * 2300)
        with self.assertRaises(spend.MaxCallsExceeded):  # one more call is refused
            led.reserve("w499", M, 1, 1)

    def test_ep1_overrun_refused(self):
        led = self.led()
        with self.assertRaises(spend.SpendError):
            led.reserve("x", M, 2000, 301)  # over the per-call output cap
        with self.assertRaises(spend.SpendError):
            led.reserve("y", M, 2001, 300)  # over the per-call input cap
        led.reserve("ok", M, 2000, 300)
        with self.assertRaises(spend.BatchStopped):  # an overrun of the reservation stops the batch
            led.charge("ok", M, {"input_tokens": 2001, "output_tokens": 300})


class AR1Tests(unittest.TestCase):
    PRICEY = {**P, "input": 400, "output": 2000, "cache_write_5m": 400, "cache_write_1h": 400}  # 2,000 + 300 tokens = 1.4 USD

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.sheet = spend.PriceSheet.load(sheet_file(self.d))

    def led(self, batch, name="l.jsonl"):
        return spend.Ledger(os.path.join(self.d, name), self.sheet, batch=batch)

    def settle(self, reason="complete"):
        e = self.led("ep1", "e.jsonl")
        e.reserve("e0", M, 100, 100)
        e.charge("e0", M, {"input_tokens": 10, "output_tokens": 10})
        e.settle(reason)

    def test_spec(self):
        a = spend.BATCH_SPECS["ar1"]
        self.assertEqual((a["usd"], a["calls"], a["tokens"], a["parent"]), (3.0, 400, 800_000, None))
        self.assertNotIn("canary_input_tokens_max", a)

    def test_refused_before_ep1_exists_or_settles(self):
        with self.assertRaises(spend.BatchStopped):
            self.led("ar1").reserve("a", M, 100, 100)
        self.led("ep1", "e.jsonl").reserve("e0", M, 100, 100)  # open, not settled
        with self.assertRaises(spend.BatchStopped):
            self.led("ar1").reserve("a", M, 100, 100)

    def test_refused_after_ep1_stop_with_another_reason(self):
        e = self.led("ep1", "e.jsonl")
        e.reserve("e0", M, 100, 100)
        with self.assertRaises(spend.BatchStopped):
            e.charge("e0", M, {"input_tokens": 100_000, "output_tokens": 100})
        with self.assertRaises(spend.SpendError):
            self.led("ar1").reserve("a", M, 100, 100)

    def test_settle_refuses_other_reasons(self):
        with self.assertRaises(spend.SpendError):
            self.led("ep1", "e.jsonl").settle("budget")

    def test_accepted_after_complete_or_inconclusive(self):
        for reason in spend.SETTLED_REASONS:
            self.d = tempfile.mkdtemp()
            self.sheet = spend.PriceSheet.load(sheet_file(self.d))
            self.settle(reason)
            self.led("ar1").reserve("a", M, 100, 100)
            self.assertEqual(spend.batch_report(self.d, "ar1")["calls"], 1)

    def test_ar1_token_cap_binds_at_347_full_calls(self):  # 800,000 / 2,300; the 400-call cap is not reached
        self.sheet = spend.PriceSheet.load(sheet_file(self.d, models={M: {**P, "input": 0.1, "output": 0.5, "cache_write_5m": 0.2, "cache_write_1h": 0.2}}))
        self.settle()
        a = self.led("ar1")
        n = 0
        with self.assertRaises(spend.SpendCeilingExceeded):
            for i in range(400):
                a.reserve(f"a{i}", M, 2000, 300)
                n += 1
        self.assertEqual(n, 347)

    def test_ar1_call_cap(self):
        self.settle()
        a = self.led("ar1")
        for i in range(400):
            a.reserve(f"a{i}", M, 10, 10)
        with self.assertRaises(spend.MaxCallsExceeded):
            a.reserve("a400", M, 10, 10)

    def test_ar1_usd_cap(self):
        self.sheet = spend.PriceSheet.load(sheet_file(self.d, models={M: self.PRICEY}))
        self.settle()
        a = self.led("ar1")
        a.reserve("a0", M, 2000, 300)
        a.reserve("a1", M, 2000, 300)  # 2.8 USD
        with self.assertRaises(spend.SpendCeilingExceeded):
            a.reserve("a2", M, 2000, 300)

    def test_ar1_has_no_canary_exception(self):
        self.settle()
        with self.assertRaises(spend.SpendError):
            self.led("ar1").reserve("a", M, 50_000, 100, canary_input_tokens=50_000)
        with self.assertRaises(spend.SpendError):
            self.led("ar1").reserve("a", M, 2001, 100)

    def test_program_hard_cap_binds_across_batches_and_unbatched(self):
        self.sheet = spend.PriceSheet.load(sheet_file(self.d, models={M: self.PRICEY}))
        with open(os.path.join(self.d, "u.jsonl"), "w") as f:  # unbatched spend recorded before any batch opened
            f.write(json.dumps({"kind": "reserve", "id": "u", "model": M, "worst_usd": 6.0, "input_tokens_ub": 1, "max_tokens": 1}) + "\n")
            f.write(json.dumps({"kind": "charge", "id": "u", "usd": 6.0, "usage": {"input_tokens": 1, "output_tokens": 1}}) + "\n")
        e = self.led("ep1", "e.jsonl")
        e.reserve("e0", M, 2000, 300)  # 7.4 total
        e.settle("complete")
        a = self.led("ar1")
        a.reserve("a0", M, 2000, 300)  # 8.8 total
        with self.assertRaises(spend.SpendCeilingExceeded):  # 10.2 > 10 although ar1 itself is under 3.00
            a.reserve("a1", M, 2000, 300)

    def test_other_spellings_of_batch_ids_refused(self):
        for alias in ("AR1", "ar1 ", "ar-1", "ar1/ep1", "ep1/ar1", "Ep1"):
            with self.assertRaises(spend.SpendError):
                self.led(alias)


class PilotTests(unittest.TestCase):
    MID = {**P, "input": 100, "output": 650, "cache_write_5m": 100, "cache_write_1h": 100}  # 2,000 + 300 tokens = 0.395 USD
    PRICEY = {**P, "input": 400, "output": 2000, "cache_write_5m": 400, "cache_write_1h": 400}  # 1.4 USD

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.use(None)

    def use(self, model_prices):
        self.sheet = spend.PriceSheet.load(sheet_file(self.d, models={M: model_prices or P}))

    def led(self, batch, name=None):
        return spend.Ledger(os.path.join(self.d, name or f"{batch}.jsonl"), self.sheet, batch=batch)

    def canary(self, reason="complete"):
        c = self.led("canary")
        c.reserve("c0", M, 10, 10, canary_input_tokens=10)
        c.charge("c0", M, {"input_tokens": 5, "output_tokens": 5})
        c.settle(reason)

    def test_spec(self):
        p = spend.BATCH_SPECS["pilot"]
        self.assertEqual((p["usd"], p["calls"], p["tokens"], p["parent"]), (0.5, 150, 345_000, None))
        self.assertNotIn("canary_input_tokens_max", p)

    def test_refused_before_the_canary_completes(self):
        with self.assertRaises(spend.BatchStopped):
            self.led("pilot").reserve("p", M, 100, 100)
        self.led("canary").reserve("c0", M, 10, 10, canary_input_tokens=10)  # run, not settled
        with self.assertRaises(spend.BatchStopped):
            self.led("pilot").reserve("p", M, 100, 100)

    def test_refused_when_only_ep1_settled_or_canary_stopped_otherwise(self):
        e = self.led("ep1")
        e.reserve("e0", M, 100, 100)
        e.settle("complete")
        with self.assertRaises(spend.BatchStopped):
            self.led("pilot").reserve("p", M, 100, 100)
        d = self.d = tempfile.mkdtemp()
        self.use(None)
        c = self.led("canary")
        c.reserve("c0", M, 10, 10, canary_input_tokens=10)
        with self.assertRaises(spend.BatchStopped):  # usage over the reservation stops the canary
            c.charge("c0", M, {"input_tokens": 5000, "output_tokens": 5})
        with self.assertRaises(spend.SpendError):
            self.led("pilot").reserve("p", M, 100, 100)

    def test_inconclusive_canary_does_not_open_the_pilot(self):
        self.canary("inconclusive")
        with self.assertRaises(spend.BatchStopped):
            self.led("pilot").reserve("p", M, 100, 100)

    def test_accepted_after_the_canary_completes_and_ep1_is_not_blocked(self):
        self.canary()
        self.led("pilot").reserve("p", M, 100, 100)
        self.led("ep1").reserve("e0", M, 100, 100)  # a completed canary does not stop its parent
        self.assertEqual(spend.batch_report(self.d, "pilot")["calls"], 1)

    def test_pilot_cap_150_full_calls_is_exactly_345000_tokens(self):
        self.use({**P, "input": 0.1, "output": 0.5, "cache_write_5m": 0.2, "cache_write_1h": 0.2})  # USD does not bind first
        self.canary()
        p = self.led("pilot")
        for i in range(150):
            p.reserve(f"p{i}", M, 2000, 300)
        self.assertEqual(spend.batch_report(self.d, "pilot")["tokens"], 345_000)
        with self.assertRaises(spend.MaxCallsExceeded):
            p.reserve("p150", M, 1, 1)

    def test_pilot_token_cap_binds(self):
        self.canary()
        with mock.patch.object(spend, "BATCH_SPECS", {**spend.BATCH_SPECS, "pilot": {**spend.BATCH_SPECS["pilot"], "tokens": 4_600}}):
            p = self.led("pilot")
            p.reserve("p0", M, 2000, 300)
            p.reserve("p1", M, 2000, 300)
            with self.assertRaises(spend.SpendCeilingExceeded):
                p.reserve("p2", M, 2000, 300)

    def test_pilot_usd_cap(self):
        self.use(self.MID)
        self.canary()
        p = self.led("pilot")
        p.reserve("p0", M, 2000, 300)  # 0.395
        with self.assertRaises(spend.SpendCeilingExceeded):
            p.reserve("p1", M, 2000, 300)
        self.use(self.PRICEY)  # a single call above 0.50 is refused outright
        self.d = tempfile.mkdtemp()
        self.use(self.PRICEY)
        self.canary()
        with self.assertRaises(spend.SpendCeilingExceeded):
            self.led("pilot").reserve("q0", M, 2000, 300)

    def test_pilot_has_no_canary_exception(self):
        self.canary()
        with self.assertRaises(spend.SpendError):
            self.led("pilot").reserve("p", M, 50_000, 100, canary_input_tokens=50_000)
        with self.assertRaises(spend.SpendError):
            self.led("pilot").reserve("p", M, 2001, 100)

    def test_program_cap_binds_across_ep1_canary_pilot_ar1_and_unbatched(self):
        self.use(self.MID)
        with open(os.path.join(self.d, "u.jsonl"), "w") as f:  # unbatched spend recorded before any batch opened
            f.write(json.dumps({"kind": "reserve", "id": "u", "model": M, "worst_usd": 9.0, "input_tokens_ub": 1, "max_tokens": 1}) + "\n")
            f.write(json.dumps({"kind": "charge", "id": "u", "usd": 9.0, "usage": {"input_tokens": 1, "output_tokens": 1}}) + "\n")
        self.canary()  # about 9.001
        e = self.led("ep1")
        e.reserve("e0", M, 2000, 300)  # 9.396
        e.settle("complete")
        self.led("pilot").reserve("p0", M, 2000, 300)  # 9.79
        with self.assertRaises(spend.SpendCeilingExceeded):  # 10.19 > 10 although ar1 itself is under 3.00
            self.led("ar1").reserve("a0", M, 2000, 300)
        with self.assertRaises(spend.SpendCeilingExceeded):
            self.led("pilot").reserve("p1", M, 2000, 300)

    def test_other_spellings_refused(self):
        for alias in ("Pilot", "pilot ", "PILOT", "pilot1", "ep1/pilot", "canary/pilot"):
            with self.assertRaises(spend.SpendError):
                self.led(alias, "x.jsonl")


class StopBatchTests(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.sheet = spend.PriceSheet.load(sheet_file(self.d))

    def led(self, batch, name=None):
        return spend.Ledger(os.path.join(self.d, name or f"{batch}.jsonl"), self.sheet, batch=batch)

    def stops(self, led):
        return [r for _, r in spend.Ledger._sum(spend.Ledger._read(led.path))["stops"]]

    def test_records_stopped_why_for_each_closed_value_with_or_without_prefix(self):
        for i, why in enumerate(spend.STOP_WHY):
            led = self.led("ep1", f"e{i}.jsonl")
            led.stop_batch(f"stopped:{why}" if i % 2 else why)
            self.assertEqual(self.stops(led), [f"stopped:{why}"])

    def test_refuses_an_unknown_why_an_unbatched_ledger_and_settle_keeps_its_set(self):
        for bad in ("complete", "inconclusive", "budget", "stopped:budget", "stopped:", "", None):
            with self.assertRaises(spend.SpendError):
                self.led("ep1").stop_batch(bad)
        with self.assertRaises(spend.SpendError):
            spend.Ledger(os.path.join(self.d, "n.jsonl"), self.sheet).stop_batch("cap")
        for bad in ("stopped:cap", "cap", "owner"):
            with self.assertRaises(spend.SpendError):
                self.led("ep1").settle(bad)
        self.assertEqual(self.stops(self.led("ep1")), [])

    def test_a_stop_blocks_further_reserves_in_the_batch_and_its_children(self):
        e = self.led("ep1", "e.jsonl")
        e.stop_batch("owner")
        with self.assertRaises(spend.BatchStopped):
            e.reserve("e0", M, 100, 100)
        with self.assertRaises(spend.BatchStopped):  # the canary lives inside ep1
            self.led("canary", "c.jsonl").reserve("c0", M, 10, 10, canary_input_tokens=10)

    def test_ar1_stays_refused_after_an_ep1_stop_whatever_the_why(self):
        for i, why in enumerate(spend.STOP_WHY):
            d = os.path.join(self.d, str(i))
            os.makedirs(d)
            e = spend.Ledger(os.path.join(d, "e.jsonl"), self.sheet, batch="ep1")
            e.reserve("e0", M, 100, 100)
            e.charge("e0", M, {"input_tokens": 10, "output_tokens": 10})
            e.stop_batch(why)
            with self.assertRaises(spend.BatchStopped):
                spend.Ledger(os.path.join(d, "a.jsonl"), self.sheet, batch="ar1").reserve("a", M, 100, 100)

    def test_ar1_opens_after_settle_but_not_after_a_stop_in_the_same_directory(self):
        e = self.led("ep1", "e.jsonl")
        e.settle("inconclusive")
        self.led("ar1", "a.jsonl").reserve("a", M, 100, 100)  # control: the refusals above are about the stop
        e.stop_batch("crash")  # a later stop line: the batch is no longer purely settled
        with self.assertRaises(spend.BatchStopped):
            self.led("ar1", "a.jsonl").reserve("a2", M, 100, 100)

    def test_pilot_stays_refused_after_a_canary_stop_whatever_the_why(self):
        for i, why in enumerate(spend.STOP_WHY):
            d = os.path.join(self.d, str(i))
            os.makedirs(d)
            c = spend.Ledger(os.path.join(d, "c.jsonl"), self.sheet, batch="canary")
            c.reserve("c0", M, 10, 10, canary_input_tokens=10)
            c.charge("c0", M, {"input_tokens": 5, "output_tokens": 5})
            c.stop_batch(why)
            with self.assertRaises(spend.BatchStopped):
                spend.Ledger(os.path.join(d, "p.jsonl"), self.sheet, batch="pilot").reserve("p", M, 100, 100)


class SettledMeansNoStopTests(unittest.TestCase):
    """A batch is settled only with no stop anywhere in its subtree or its requires_settled dependencies (G0-2R2 N1)."""
    # independent oracle: the batches whose stop forbids settling (and opening the dependants of) each batch
    SCOPE = {"canary": {"canary"}, "ep1": {"ep1", "canary"}, "pilot": {"pilot", "canary"}, "ar1": {"ar1", "ep1", "canary"}}

    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.d = t.name
        self.sheet = spend.PriceSheet.load(sheet_file(self.d))

    def led(self, batch, d=None):
        return spend.Ledger(os.path.join(d or self.d, f"{batch}.jsonl"), self.sheet, batch=batch)

    def canary_call(self, d=None):
        c = self.led("canary", d)
        c.reserve("c0", M, 10, 10, canary_input_tokens=10)
        c.charge("c0", M, {"input_tokens": 5, "output_tokens": 5})
        return c

    def test_g0_2r2_probe_canary_stopped_then_ep1_settled_by_hand_never_opens_ar1(self):
        self.canary_call().stop_batch("transport")
        with self.assertRaises(spend.BatchStopped):
            spend.Ledger(os.path.join(self.d, "ep1.jsonl"), self.sheet, batch="ep1").settle("complete")
        with self.assertRaises(spend.BatchStopped):
            self.led("ar1").reserve("a", M, 100, 100)
        self.assertEqual([b for b, _ in spend.Ledger(os.path.join(self.d, "ep1.jsonl"), self.sheet, batch="ep1").totals()["stops"]],
                         ["canary"])  # the refused settle wrote nothing

    def test_a_charge_time_canary_stop_also_blocks_the_ep1_settle_and_ar1(self):
        c = self.led("canary")
        c.reserve("c0", M, 10, 10, canary_input_tokens=10)
        with self.assertRaises(spend.BatchStopped):  # a cache write: a stop reason without the stopped: prefix, no overspent
            c.charge("c0", M, {"input_tokens": 5, "output_tokens": 5, "cache_creation_input_tokens": 1})
        self.assertFalse(self.led("ep1").totals()["overspent"])
        with self.assertRaises(spend.BatchStopped):
            self.led("ep1").settle("inconclusive")
        with self.assertRaises(spend.BatchStopped):
            self.led("ar1").reserve("a", M, 100, 100)

    def test_a_stop_recorded_after_the_settle_still_closes_the_gates(self):
        """The gate itself checks the subtree, whatever the record order (old code read only ep1's own lines)."""
        self.canary_call().settle("complete")
        self.led("ep1").settle("complete")
        self.led("pilot").reserve("p0", M, 100, 100)  # control: both gates open
        self.led("ar1").reserve("a0", M, 100, 100)
        self.led("canary").stop_batch("owner")
        with self.assertRaises(spend.BatchStopped):
            self.led("ar1").reserve("a1", M, 100, 100)
        with self.assertRaises(spend.BatchStopped):
            self.led("pilot").reserve("p1", M, 100, 100)

    def test_settle_refused_after_a_stop_on_the_batch_itself_or_its_dependency(self):
        e = self.led("ep1")
        e.stop_batch("cap")
        for reason in spend.SETTLED_REASONS:
            with self.assertRaises(spend.BatchStopped):
                e.settle(reason)
        d = os.path.join(self.d, "p")
        os.makedirs(d)
        self.canary_call(d).settle("complete")
        p = self.led("pilot", d)
        p.reserve("p0", M, 100, 100)
        self.led("canary", d).stop_batch("crash")
        with self.assertRaises(spend.BatchStopped):
            p.settle("complete")

    def test_a_canary_stop_blocks_an_ep1_reserve_at_the_spend_level(self):  # G0-2R2 N3 / mutant M1
        self.canary_call().stop_batch("void_model")
        with self.assertRaises(spend.BatchStopped):
            self.led("ep1").reserve("e0", M, 100, 100)

    def test_property_ar1_and_pilot_never_open_and_nothing_settles_after_a_stop_in_scope(self):
        import random
        opened = {"ar1": 0, "pilot": 0, "settles": 0}
        for seed in range(150):
            rng = random.Random(seed)
            d = os.path.join(self.d, str(seed))
            os.makedirs(d)
            stopped, n = set(), 0
            for _ in range(14):
                b = rng.choice(("canary", "ep1", "pilot", "ar1"))
                op = rng.choices(("reserve", "settle", "stop"), (5, 3, 1))[0]
                led = self.led(b, d)
                if op == "stop":
                    led.stop_batch(rng.choice(spend.STOP_WHY))
                    stopped.add(b)
                elif op == "settle":
                    try:
                        led.settle(rng.choice(spend.SETTLED_REASONS))
                        ok = True
                    except spend.BatchStopped:
                        ok = False
                    self.assertEqual(ok, not (stopped & self.SCOPE[b]), (seed, b, stopped))
                    opened["settles"] += ok
                else:
                    n += 1
                    kw = {"canary_input_tokens": 10} if b == "canary" else {}
                    try:
                        led.reserve(f"x{n}", M, 10, 10, **kw)
                    except spend.SpendError:
                        continue
                    if b in ("ar1", "pilot"):
                        self.assertFalse(stopped & self.SCOPE["ep1" if b == "ar1" else "canary"], (seed, b, stopped))
                        opened[b] += 1
                    if b == "ep1":
                        self.assertNotIn("canary", stopped, seed)
                    bad = rng.random() < 0.2  # a cache write: a charge-time stop (no overspent marker)
                    try:
                        led.charge(f"x{n}", M, {"input_tokens": 5, "output_tokens": 5, "cache_creation_input_tokens": int(bad)})
                    except spend.BatchStopped:
                        stopped.add(b)
        self.assertTrue(opened["ar1"] and opened["pilot"] and opened["settles"], opened)  # not vacuous


class Pilot2Tests(unittest.TestCase):
    """Pre-freeze change 16: pilot2 is a sibling of ep1, gated on a completed canary, independent of the stopped pilot."""
    MID, setUp, use, led, canary = PilotTests.MID, PilotTests.setUp, PilotTests.use, PilotTests.led, PilotTests.canary

    def test_pilot2_spec(self):
        p = spend.BATCH_SPECS["pilot2"]
        self.assertEqual((p["usd"], p["calls"], p["tokens"], p["parent"], p["requires_settled"], p["settled_reasons"]),
                         (0.25, 260, 598_000, None, spend.CANARY, ("complete",)))
        self.assertNotIn("canary_input_tokens_max", p)
        self.assertEqual(p["tokens"], p["calls"] * (spend.PER_CALL_INPUT_TOKENS + spend.PER_CALL_OUTPUT_TOKENS))
        self.assertEqual((spend.PER_CALL_OUTPUT_TOKENS, spend.BATCH_SPECS["ep1"]["tokens"],
                          spend.BATCH_SPECS["pilot"]["tokens"]), (300, 1_250_000, 345_000))  # unchanged

    def test_worst_case_across_all_batches_stays_within_the_owner_ceiling(self):
        roots = [n for n, sp in spend.BATCH_SPECS.items() if sp["parent"] is None]
        for n, sp in spend.BATCH_SPECS.items():  # a child's spend counts inside its root, so the roots bound the total
            self.assertIn(spend._lineage(n, spend.BATCH_SPECS)[-1], roots)
            self.assertLessEqual(sp["usd"], spend.BATCH_SPECS[spend._lineage(n, spend.BATCH_SPECS)[-1]]["usd"])
        total = sum(spend.BATCH_SPECS[n]["usd"] for n in roots)
        self.assertLessEqual(total, spend.HARD_CAP_USD)
        self.assertAlmostEqual(spend.HARD_CAP_USD - total, 1.00)  # pilot2 and pilot3 came out of the unallocated 1.50

    def test_pilot2_refused_unless_the_canary_completed(self):
        with self.assertRaises(spend.BatchStopped):  # canary never ran
            self.led("pilot2").reserve("q", M, 100, 100)
        for why in ("inconclusive",) + spend.STOP_WHY:
            self.d = tempfile.mkdtemp()
            self.use(None)
            c = self.led("canary")
            c.reserve("c0", M, 10, 10, canary_input_tokens=10)
            c.charge("c0", M, {"input_tokens": 5, "output_tokens": 5})
            if why in spend.SETTLED_REASONS:
                c.settle(why)
            else:
                c.stop_batch(why)
            with self.assertRaises(spend.BatchStopped, msg=why):
                self.led("pilot2").reserve("q", M, 100, 100)

    def test_pilot2_refused_after_a_canary_stop_even_following_completion(self):
        self.canary()
        self.led("canary", "canary-late.jsonl").stop_batch("owner")
        with self.assertRaises(spend.BatchStopped):
            self.led("pilot2").reserve("q", M, 100, 100)

    def test_a_stopped_pilot_does_not_block_pilot2(self):
        self.canary()
        p = self.led("pilot")
        p.reserve("p0", M, 100, 100)
        p.stop_batch("void_model")  # the real state after pilot 1
        with self.assertRaises(spend.BatchStopped):
            p.reserve("p1", M, 100, 100)
        self.led("pilot2").reserve("q0", M, 100, 100)
        self.assertEqual((spend.batch_report(self.d, "pilot2")["calls"], spend.batch_report(self.d, "pilot")["calls"]), (1, 1))

    def test_pilot2_cap_260_full_calls_is_exactly_598000_tokens(self):
        self.use({**P, "input": 0.1, "output": 0.5, "cache_write_5m": 0.2, "cache_write_1h": 0.2})
        self.canary()
        q = self.led("pilot2")
        for i in range(260):
            q.reserve(f"q{i}", M, 2000, 300)
        self.assertEqual(spend.batch_report(self.d, "pilot2")["tokens"], 598_000)
        with self.assertRaises(spend.MaxCallsExceeded):
            q.reserve("q260", M, 1, 1)

    def test_pilot2_usd_cap_binds(self):
        self.use(self.MID)  # 0.395 USD per full call: one call crosses 0.25
        self.canary()
        with self.assertRaises(spend.SpendCeilingExceeded):
            self.led("pilot2").reserve("q0", M, 2000, 300)


class Pilot3Tests(unittest.TestCase):
    """Prereg change 19: pilot3 has the pilot2 caps and gate, independent of the stopped pilot and pilot2."""
    MID, setUp, use, led, canary = PilotTests.MID, PilotTests.setUp, PilotTests.use, PilotTests.led, PilotTests.canary

    def test_pilot3_spec(self):
        p = spend.BATCH_SPECS["pilot3"]
        self.assertEqual(p, spend.BATCH_SPECS["pilot2"])
        self.assertEqual((p["usd"], p["calls"], p["tokens"], p["parent"], p["requires_settled"], p["settled_reasons"]),
                         (0.25, 260, 598_000, None, spend.CANARY, ("complete",)))
        self.assertEqual(spend.HARD_CAP_USD, 10.0)  # unchanged in this round

    def test_pilot3_refused_unless_the_canary_completed(self):
        with self.assertRaises(spend.BatchStopped):
            self.led("pilot3").reserve("q", M, 100, 100)
        self.canary()
        self.led("canary", "canary-late.jsonl").stop_batch("owner")
        with self.assertRaises(spend.BatchStopped):
            self.led("pilot3").reserve("q", M, 100, 100)

    def test_stopped_pilot_and_pilot2_do_not_block_pilot3_and_do_not_share_its_caps(self):
        self.canary()
        for b in ("pilot", "pilot2"):
            p = self.led(b)
            p.reserve(b + "0", M, 100, 100)
            p.stop_batch("void_model")
        self.led("pilot3").reserve("r0", M, 100, 100)
        self.assertEqual([spend.batch_report(self.d, b)["calls"] for b in ("pilot", "pilot2", "pilot3")], [1, 1, 1])

    def test_pilot3_cap_260_full_calls_is_exactly_598000_tokens(self):
        self.use({**P, "input": 0.1, "output": 0.5, "cache_write_5m": 0.2, "cache_write_1h": 0.2})
        self.canary()
        q = self.led("pilot3")
        for i in range(260):
            q.reserve(f"r{i}", M, 2000, 300)
        self.assertEqual(spend.batch_report(self.d, "pilot3")["tokens"], 598_000)
        with self.assertRaises(spend.MaxCallsExceeded):
            q.reserve("r260", M, 1, 1)

    def test_pilot3_usd_cap_binds(self):
        self.use(self.MID)
        self.canary()
        with self.assertRaises(spend.SpendCeilingExceeded):
            self.led("pilot3").reserve("r0", M, 2000, 300)


if __name__ == "__main__":
    unittest.main()
