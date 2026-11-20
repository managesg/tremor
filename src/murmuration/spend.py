"""Spend ledger for paid API calls. Stdlib only. Unknown cost is never zero.

price sheet (JSON): {"fetched": "YYYY-MM-DD", "source_url": ..., "opened": bool,
  "aliases": {requested_id: [accepted returned ids]},
  "models": {id: {"input","output","cache_read","cache_write_5m","cache_write_1h"  (USD per million
  tokens, null if unread), optional "long_context": {"threshold_input_tokens": n, <same price keys>}}}}
ledger (JSONL, append-only): "reserve" lines (worst-case cost, written BEFORE a call), "charge" lines
(actual cost from the usage block). A reserve with no charge still counts at its worst case, so a call
that died mid-flight is never free.

Owner ceiling: HARD_CAP_USD is a constant no argument can raise. Every *.jsonl in the ledger's directory counts
toward it (so a fresh ledger path never resets the total); in PILOT_LEDGER_DIR (the only directory the real host
may use, enforced by ClaudeClient) EVERY file counts, whatever its extension or case. `ceiling` only lowers the
limit for ONE ledger file.
All reads-then-writes run under an exclusive flock on <dir>/.spend.lock, failing CLOSED on timeout. A corrupt line,
a non-finite number, or an OVERSPENT marker stops every ledger in the directory.
shortcut: the cap is per directory; the real host is pinned to PILOT_LEDGER_DIR, test directories are not.
"""
import glob
import hashlib
import json
import math
import os
import time
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone

import fcntl

KEYS = ("input", "output", "cache_read", "cache_write_5m", "cache_write_1h")
USAGE_FIELDS = ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
MAX_AGE_DAYS = 3
HARD_CAP_USD = 10.0  # owner ceiling; never read from an argument
DEFAULT_CEILING = 9.00  # per-batch default
MAX_TOKENS_LIMIT = 64_000
LOCK_TIMEOUT = 10.0
# the one directory every ledger for api.anthropic.com must live in (resolved from the package location)
PILOT_LEDGER_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))), "runs", "spend")


def _refuse_constant(name):
    raise ValueError(f"non-finite JSON constant {name}")


def _num(x):  # finite number >= 0 (bool is not a number here)
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) and x >= 0


def _pos_int(x, hi=None):
    return isinstance(x, int) and not isinstance(x, bool) and x > 0 and (hi is None or x <= hi)


class SpendError(Exception):
    pass


class SpendCeilingExceeded(SpendError):
    pass


class MaxCallsExceeded(SpendError):
    pass


class PriceSheetRefused(SpendError):
    pass


class Overspent(SpendError):
    pass


def _check_prices(model, p):
    bad = [k for k in KEYS if p.get(k) is not None and not _num(p.get(k))]
    if bad:
        raise PriceSheetRefused(f"price sheet has non-finite or negative {bad} for {model!r}")


class PriceSheet:
    def __init__(self, data, sha256):
        self.data, self.sha256 = data, sha256

    @classmethod
    def load(cls, path, today=None, max_age_days=MAX_AGE_DAYS):
        try:
            with open(path, "rb") as f:
                raw = f.read()
            data = json.loads(raw, parse_constant=_refuse_constant)
            fetched = date.fromisoformat(data["fetched"])
            models = data["models"]
        except (OSError, ValueError, KeyError, TypeError) as e:
            raise PriceSheetRefused(f"price sheet missing or unreadable: {type(e).__name__}") from e
        if not isinstance(models, dict) or not data.get("source_url"):
            raise PriceSheetRefused("price sheet needs 'models' and 'source_url'")
        for name, m in models.items():
            if not isinstance(m, dict):
                raise PriceSheetRefused(f"price sheet entry {name!r} is not an object")
            _check_prices(name, m)
            if m.get("long_context") is not None:
                _check_prices(name, m["long_context"])
                if not _pos_int(m["long_context"].get("threshold_input_tokens")):
                    raise PriceSheetRefused(f"bad long_context threshold for {name!r}")
        age = ((today or datetime.now(timezone.utc).date()) - fetched).days
        if age > max_age_days or age < 0:
            raise PriceSheetRefused(f"price sheet fetched {fetched} is {age} days old (limit {max_age_days})")
        return cls(data, hashlib.sha256(raw).hexdigest())

    def expires_on(self):
        return date.fromisoformat(self.data["fetched"]) + timedelta(days=MAX_AGE_DAYS)

    def source(self):
        return {"source_url": self.data["source_url"], "fetched": self.data["fetched"], "sha256": self.sha256}

    def accepts(self, requested, returned):
        return returned == requested or returned in self.data.get("aliases", {}).get(requested, [])

    def prices(self, model, prompt_tokens=0):
        m = self.data["models"].get(model)
        if m is None:
            raise PriceSheetRefused(f"no price for model {model!r}")
        lc = m.get("long_context")
        p = lc if lc and prompt_tokens > lc["threshold_input_tokens"] else m
        missing = [k for k in KEYS if p.get(k) is None]
        if missing:
            raise PriceSheetRefused(f"price sheet has null {missing} for {model!r}; unknown cost is not zero")
        return p


def clean_usage(u):
    """Validated token counts (ints >= 0) from a usage block, else SpendError. Unknown fields are dropped, never stored."""
    if not isinstance(u, dict):
        raise SpendError("usage block missing or not an object")
    out = {}
    for k in USAGE_FIELDS:
        v = u.get(k)
        if v is not None and not (isinstance(v, int) and not isinstance(v, bool) and v >= 0):
            raise SpendError(f"usage field {k} is not a non-negative integer")
        if v is not None:
            out[k] = v
    cc = u.get("cache_creation")
    if cc is not None:
        if not isinstance(cc, dict):
            raise SpendError("usage cache_creation is not an object")
        sub = {}
        for k in ("ephemeral_5m_input_tokens", "ephemeral_1h_input_tokens"):
            v = cc.get(k)
            if v is not None and not (isinstance(v, int) and not isinstance(v, bool) and v >= 0):
                raise SpendError(f"usage cache_creation.{k} is not a non-negative integer")
            if v is not None:
                sub[k] = v
        out["cache_creation"] = sub
    return out


def _prompt_tokens(u):
    return (u.get("input_tokens") or 0) + (u.get("cache_read_input_tokens") or 0) + (u.get("cache_creation_input_tokens") or 0)


class Ledger:
    def __init__(self, path, sheet, ceiling=DEFAULT_CEILING, max_calls=None):
        if not path:
            raise SpendError("a spend ledger path is required")
        if not (_num(ceiling) and 0 < ceiling <= HARD_CAP_USD):
            raise SpendError(f"ceiling must be a number in (0, {HARD_CAP_USD}]")
        if max_calls is not None and not _pos_int(max_calls):
            raise SpendError("max_calls must be a positive integer")
        self.path, self.sheet, self.ceiling, self.max_calls = path, sheet, float(ceiling), max_calls
        self.lock_timeout = LOCK_TIMEOUT
        self.dir = os.path.dirname(os.path.abspath(path))
        os.makedirs(self.dir, mode=0o700, exist_ok=True)

    @contextmanager
    def _lock(self):
        fd = os.open(os.path.join(self.dir, ".spend.lock"), os.O_RDWR | os.O_CREAT, 0o600)
        try:
            end = time.monotonic() + self.lock_timeout
            while True:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except OSError:
                    if time.monotonic() >= end:
                        raise SpendError("spend lock timeout: failing closed") from None
                    time.sleep(0.005)
            yield
        finally:
            os.close(fd)  # closing the fd releases the flock

    @staticmethod
    def _read(path):
        if not os.path.exists(path):
            return []
        out = []
        with open(path, "rb") as f:
            for x in f.read().splitlines():
                if not x.strip():
                    continue
                try:
                    e = json.loads(x, parse_constant=_refuse_constant)
                except ValueError as err:
                    raise SpendError(f"corrupt ledger line in {os.path.basename(path)}: stopping") from err
                if not isinstance(e, dict) or "kind" not in e:
                    raise SpendError(f"corrupt ledger entry in {os.path.basename(path)}: stopping")
                out.append(e)
        return out

    def _lines(self):
        return self._read(self.path)

    def _append(self, entry):
        # one O_APPEND write of one line: a stopped run never leaves a torn line mid-file
        data = (json.dumps(entry, sort_keys=True, allow_nan=False) + "\n").encode()
        fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        try:
            os.write(fd, data)
            os.fsync(fd)
        finally:
            os.close(fd)

    @staticmethod
    def _sum(lines):
        charged, reserved, calls, over = {}, {}, 0, False
        for e in lines:
            if e["kind"] == "reserve":
                if not _num(e.get("worst_usd")):
                    raise SpendError("corrupt reserve entry: stopping")
                reserved[e["id"]] = e["worst_usd"]
                calls += 1
            elif e["kind"] == "charge":
                if not _num(e.get("usd")):
                    raise SpendError("corrupt charge entry: stopping")
                charged[e["id"]] = e["usd"]
            elif e["kind"] == "overspent":
                over = True
        spent = sum(charged.values()) + sum(v for k, v in reserved.items() if k not in charged)
        return {"spent_usd": spent, "calls": calls, "charged_ids": set(charged), "reserved_ids": set(reserved),
                "reserved": reserved, "overspent": over}

    def _files(self):
        if os.path.realpath(self.dir) != os.path.realpath(PILOT_LEDGER_DIR):
            return sorted(glob.glob(os.path.join(self.dir, "*.jsonl")))
        out = []
        for n in sorted(os.listdir(self.dir)):
            f = os.path.join(self.dir, n)
            if n == ".spend.lock":
                continue
            if os.path.islink(f) or not os.path.isfile(f):
                raise SpendError(f"non-regular entry {n!r} in the pilot ledger directory: stopping")
            out.append(f)
        return out

    def totals(self):
        """This ledger file's totals, plus global_usd/overspent across every ledger file in the directory."""
        own = self._sum(self._lines())
        files = self._files()
        others = [self._sum(self._read(f)) for f in files if os.path.abspath(f) != os.path.abspath(self.path)]
        own["global_usd"] = own["spent_usd"] + sum(o["spent_usd"] for o in others)
        own["overspent"] = own["overspent"] or any(o["overspent"] for o in others)
        return own

    def estimate(self, model, usage):
        """USD for one response's usage block. Thinking tokens are billed inside output_tokens."""
        usage = clean_usage(usage)
        p = self.sheet.prices(model, _prompt_tokens(usage))
        cc = usage.get("cache_creation") or {}
        w5, w1 = cc.get("ephemeral_5m_input_tokens"), cc.get("ephemeral_1h_input_tokens")
        if w5 is None and w1 is None:  # no breakdown: bill the whole write at the dearer 1h rate
            w5, w1 = 0, usage.get("cache_creation_input_tokens") or 0
        tok = {"input": usage.get("input_tokens") or 0, "output": usage.get("output_tokens") or 0,
               "cache_read": usage.get("cache_read_input_tokens") or 0,
               "cache_write_5m": w5 or 0, "cache_write_1h": w1 or 0}
        return sum(tok[k] * p[k] for k in KEYS) / 1e6

    def worst_case(self, model, input_tokens_ub, max_tokens):
        if not _pos_int(input_tokens_ub) or not _pos_int(max_tokens, MAX_TOKENS_LIMIT):
            raise SpendError(f"input_tokens_ub and max_tokens must be positive ints (max_tokens <= {MAX_TOKENS_LIMIT})")
        p = self.sheet.prices(model, input_tokens_ub)
        top_in = max(p["input"], p["cache_write_5m"], p["cache_write_1h"])
        return (input_tokens_ub * top_in + max_tokens * p["output"]) / 1e6

    def reserve(self, call_id, model, input_tokens_ub, max_tokens):
        """Call BEFORE the request. Raises if the worst case would cross the ceiling, HARD_CAP_USD or max_calls."""
        worst = self.worst_case(model, input_tokens_ub, max_tokens)
        with self._lock():
            t = self.totals()
            if t["overspent"]:
                raise Overspent("a ledger in this directory is marked OVERSPENT: no further calls")
            if call_id in t["reserved_ids"]:
                raise SpendError(f"call id {call_id!r} already used; retries need their own attempt id")
            if self.max_calls is not None and t["calls"] >= self.max_calls:
                raise MaxCallsExceeded(f"{t['calls']} calls already made, limit {self.max_calls}")
            # written so NaN fails: a comparison with NaN is False, so test the 'allowed' side
            if not (t["spent_usd"] + worst <= self.ceiling):
                raise SpendCeilingExceeded(
                    f"spent {t['spent_usd']:.4f} + worst case {worst:.4f} would cross ceiling {self.ceiling:.2f} USD")
            if not (t["global_usd"] + worst <= HARD_CAP_USD):
                raise SpendCeilingExceeded(
                    f"all ledgers {t['global_usd']:.4f} + worst case {worst:.4f} would cross the owner cap {HARD_CAP_USD:.2f} USD")
            self._append({"kind": "reserve", "id": call_id, "model": model, "worst_usd": worst,
                          "input_tokens_ub": input_tokens_ub, "max_tokens": max_tokens,
                          "price_sheet": self.sheet.source()})
        return worst

    def _overspend(self, call_id, reason):
        self._append({"kind": "overspent", "id": call_id, "reason": reason})
        raise Overspent(f"{call_id}: {reason}; ledger marked OVERSPENT, no further calls")

    def charge(self, call_id, model, usage, returned_model=None, **record):
        """Write the actual cost (from usage) and the per-call record; returns USD.

        Fail-closed: an invalid usage block, or an actual cost above the reserved worst case, records the true
        (or worst-case) cost and marks the ledger OVERSPENT. A different returned model is priced at the dearer
        of the two, or at the worst case when its price is unknown.
        """
        with self._lock():
            reserved = self._sum(self._lines())["reserved"].get(call_id)
            if reserved is None:
                raise SpendError(f"charge for {call_id!r} without a reserve")
            problem = None
            try:
                clean = clean_usage(usage)
                if clean.get("input_tokens") is None or clean.get("output_tokens") is None:
                    raise SpendError("usage lacks input_tokens or output_tokens")
                usd = self.estimate(model, clean)
                if returned_model not in (None, model):
                    try:
                        usd = max(usd, self.estimate(returned_model, clean))
                    except SpendError:  # unknown price: unknown cost is not zero
                        usd = max(usd, reserved)
            except SpendError as e:
                problem, clean, usd = str(e), None, reserved
            self._append({"kind": "charge", "id": call_id, "model": model, "usd": usd, "usage": clean,
                          "returned_model": returned_model, "usage_invalid": problem, **record})
            if problem:
                self._overspend(call_id, f"invalid usage ({problem}); charged the reserved worst case")
            if usd > reserved:
                self._overspend(call_id, f"actual {usd:.6f} USD exceeds reserved worst case {reserved:.6f}")
        return usd

    def void_unknown(self, call_id, **record):
        """A reserved call that produced no usage block: stays charged at its worst case."""
        with self._lock():
            self._append({"kind": "unbilled_unknown", "id": call_id, **record})
