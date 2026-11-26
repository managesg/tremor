"""Spend ledger for paid API calls. Stdlib only. Unknown cost is never zero.

price sheet (JSON): {"fetched": "YYYY-MM-DD", "source_url": ..., "opened": bool,
  "aliases": {requested_id: [accepted returned ids]},
  "models": {id: {"input","output","cache_read","cache_write_5m","cache_write_1h"  (USD per million
  tokens, null if unread), optional "long_context": {"threshold_input_tokens": n, <same price keys>}}}}
ledger (JSONL, append-only): "reserve" lines (worst-case cost, written BEFORE a call), "charge" lines
(actual cost from the usage block). A reserve with no charge still counts at its worst case, so a call
that died mid-flight is never free.

Owner ceiling: HARD_CAP_USD (USD 10) is the program-wide ceiling across the pinned directory and no argument can raise it;
DEFAULT_CEILING (USD 9) is only the default PER LEDGER FILE, not a directory cap.
Unbatched reserves are refused (BatchStopped) in any directory that already holds a batch ledger, so an unbatched ledger can
never bypass batch caps (fail closed; unbatched spend made before a batch opens counts only toward HARD_CAP_USD). Every *.jsonl in the ledger's directory counts
toward it (so a fresh ledger path never resets the total); in PILOT_LEDGER_DIR (the only directory the real host
may use, enforced by ClaudeClient) EVERY file counts, whatever its extension or case. `ceiling` only lowers the
limit for ONE ledger file.
All reads-then-writes run under an exclusive flock on <dir>/.spend.lock, failing CLOSED on timeout. A batch driver
may hold that same lock for its full run. A corrupt line,
a non-finite number, or an OVERSPENT marker stops every ledger in the directory.
Batches (B1): a ledger may carry a batch id; every reserve/charge line is tagged with it. BATCH_SPECS (a constant, nested:
`canary` inside `ep1`) caps USD, calls and tokens (input+output, cache reads included) per batch across EVERY file in the
directory, a child's records also count toward its parents, and a child cap can never exceed its parent's (checked on every
Ledger()). Batched calls also get per-call token caps; the canary alone may declare `canary_input_tokens`. A batch stops
(BatchStopped, recorded as a batch_stop line, every later reserve in that lineage refused) on any cache_creation tokens, a bad
usage block or usage above the reservation. A batch counts as settled only with a complete/inconclusive record and no
stop anywhere in its subtree or its requires_settled dependencies (settle() and the requires_settled gate share the rule:
a stopped canary refuses the pilot and any settle of ep1, so ar1 never opens). The first reserve of a batch pins the price sheet sha256 and dated source.
shortcut: the cap is per directory; the real host is pinned to PILOT_LEDGER_DIR, test directories are not.
"""
import glob
import hashlib
import json
import math
import os
import re
import threading
import time
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone

import fcntl

KEYS = ("input", "output", "cache_read", "cache_write_5m", "cache_write_1h")
USAGE_FIELDS = ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
MAX_AGE_DAYS = 3
_HEX64 = re.compile(r"[0-9a-f]{64}")
HARD_CAP_USD = 10.0  # owner ceiling; never read from an argument
DEFAULT_CEILING = 9.00  # default per LEDGER FILE; the program-wide ceiling is HARD_CAP_USD
MAX_TOKENS_LIMIT = 64_000
LOCK_TIMEOUT = 10.0
PER_CALL_INPUT_TOKENS, PER_CALL_OUTPUT_TOKENS = 2_000, 300
CANARY = "canary"  # the only batch that may declare canary_input_tokens
SETTLED_REASONS = ("complete", "inconclusive")  # the only stop reasons that settle a batch
STOP_WHY = ("cap", "transport", "http400", "void_model", "invalid_log", "scorer_disagreement", "refusal_loop", "owner",
            "crash")  # stop_batch
BATCH_SPECS = {  # nested sub-caps, never read from an argument; the canary counts INSIDE ep1
    # 480 capped calls (2,000 + 300 each = 1,104,000) plus the 90,300-token canary fit at full reservation
    "ep1": {"usd": 5.0, "calls": 500, "tokens": 1_250_000, "parent": None},
    # auto-research over practice cards: sub-cap of the program ledger (HARD_CAP_USD still binds), no canary exception,
    # refuses to open until ep1 has settled
    # pilot: a sibling of ep1 (not inside it), refuses to open until the canary has run and completed
    "pilot": {"usd": 0.5, "calls": 150, "tokens": 345_000, "parent": None, "requires_settled": CANARY, "settled_reasons": ("complete",)},
    # pilot2: the same gate as pilot and independent of it (a stopped pilot does not block it); from the unallocated USD 1.50
    "pilot2": {"usd": 0.25, "calls": 260, "tokens": 598_000, "parent": None, "requires_settled": CANARY, "settled_reasons": ("complete",)},
    # pilot3 (prereg change 19): the pilot2 gate, independent of the stopped pilot and pilot2; from the unallocated USD 1.25
    "pilot3": {"usd": 0.25, "calls": 260, "tokens": 598_000, "parent": None, "requires_settled": CANARY, "settled_reasons": ("complete",)},
    # pilot4: the pilot3 gate and caps; round 2 of each episode asks for one JSON array in the array_only wording
    "pilot4": {"usd": 0.25, "calls": 260, "tokens": 598_000, "parent": None, "requires_settled": CANARY, "settled_reasons": ("complete",)},
    "ar1": {"usd": 3.0, "calls": 400, "tokens": 800_000, "parent": None, "requires_settled": "ep1"},
    CANARY: {"usd": 0.05, "calls": 1, "tokens": 90_300, "parent": "ep1", "canary_input_tokens_max": 90_000},  # G0-2R: bytes bound tokens; 90,000 + 300 output
}
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


class BatchStopped(SpendError):
    pass


def _lineage(name, specs):
    """name, its parent, ... up to the root."""
    out = []
    while name is not None and name not in out and len(out) <= len(specs):
        out.append(name)
        name = (specs.get(name) or {}).get("parent")
    return out


def _scope(name, specs, seen=None):
    """name's subtree (itself and every descendant) plus, recursively, the scope of every batch that subtree requires settled."""
    seen = set() if seen is None else seen
    if name in seen:
        return seen
    sub = [n for n in specs if name in _lineage(n, specs)]
    seen.update(sub)
    for n in sub:
        if specs[n].get("requires_settled") is not None:
            _scope(specs[n]["requires_settled"], specs, seen)
    return seen


def _stops_in_scope(stops, name):
    """Recorded stops (any batch_stop whose reason does not settle) in name's scope. A batch with one is never settled."""
    sc = _scope(name, BATCH_SPECS)
    return [(b, r) for b, r in stops if b in sc and r not in SETTLED_REASONS]


def _validate_specs(specs):
    for n, sp in specs.items():
        par = sp.get("parent")
        if par is not None and par not in specs:
            raise SpendError(f"batch {n!r} has unknown parent {par!r}")
        if specs[_lineage(n, specs)[-1]].get("parent") is not None:
            raise SpendError(f"batch {n!r} has a parent cycle")
        top = specs[par] if par else {"usd": DEFAULT_CEILING, "calls": 10**9, "tokens": 10**12}
        if not (_num(sp.get("usd")) and 0 < sp["usd"] <= top["usd"] and sp["usd"] <= HARD_CAP_USD):
            raise SpendError(f"batch {n!r} usd cap must be in (0, parent cap]")
        for k in ("calls", "tokens"):
            if not _pos_int(sp.get(k), top[k]):
                raise SpendError(f"batch {n!r} {k} cap must be a positive int not above its parent's")
        if "requires_settled" in sp and (sp["requires_settled"] not in specs or sp["requires_settled"] == n):
            raise SpendError(f"batch {n!r} requires an unknown batch to settle first")
        if "canary_input_tokens_max" in sp and (n != CANARY or not _pos_int(sp["canary_input_tokens_max"])):
            raise SpendError("only the canary batch may carry canary_input_tokens_max")


def _check_prices(model, p):
    bad = [k for k in KEYS if p.get(k) is not None and not _num(p.get(k))]
    if bad:
        raise PriceSheetRefused(f"price sheet has non-finite or negative {bad} for {model!r}")


def _check_age(fetched, today, max_age_days):
    age = ((today or datetime.now(timezone.utc).date()) - fetched).days
    if age > max_age_days or age < 0:
        raise PriceSheetRefused(f"price sheet fetched {fetched} is {age} days old (limit {max_age_days})")


class PriceSheet:
    def __init__(self, data, sha256):
        self.data, self.sha256, self.today = data, sha256, None

    @classmethod
    def load(cls, path, today=None, max_age_days=MAX_AGE_DAYS, allow_expired=False):
        """allow_expired skips ONLY the age check; it exists for the predecessor sheet of a sheet_continuity (see Ledger)."""
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
        if not allow_expired:
            _check_age(fetched, today, max_age_days)
        sheet = cls(data, hashlib.sha256(raw).hexdigest())
        sheet.today = today
        return sheet

    def check_age(self, today=None, max_age_days=MAX_AGE_DAYS):
        """The load-time check again, against the same `today` the sheet was loaded with (None: the clock)."""
        _check_age(date.fromisoformat(self.data["fetched"]), today or self.today, max_age_days)

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
    def __init__(self, path, sheet, ceiling=DEFAULT_CEILING, max_calls=None, batch=None, predecessor_sheet=None):
        if not path:
            raise SpendError("a spend ledger path is required")
        if not (_num(ceiling) and 0 < ceiling <= HARD_CAP_USD):
            raise SpendError(f"ceiling must be a number in (0, {HARD_CAP_USD}]")
        if max_calls is not None and not _pos_int(max_calls):
            raise SpendError("max_calls must be a positive integer")
        _validate_specs(BATCH_SPECS)
        if batch is not None and batch not in BATCH_SPECS:
            raise SpendError(f"unknown batch {batch!r}")
        self.path, self.sheet, self.ceiling, self.max_calls, self.batch = path, sheet, float(ceiling), max_calls, batch
        self.predecessor_sheet = predecessor_sheet  # PATH of the sheet an already-open batch pinned, for sheet_continuity only
        self.lock_timeout = LOCK_TIMEOUT
        self.dir = os.path.dirname(os.path.abspath(path))
        os.makedirs(self.dir, mode=0o700, exist_ok=True)
        self._exclusive_owner = None

    @contextmanager
    def exclusive_batch(self):
        """Exclude other ledger writers across preflight, requests and settlement."""
        owner = (os.getpid(), threading.get_ident())
        if self._exclusive_owner == owner:
            raise SpendError("a ledger batch is already active on this thread")
        with self._lock():
            self._exclusive_owner = owner
            try:
                yield
            finally:
                self._exclusive_owner = None

    @contextmanager
    def exclusive_request(self):
        """Keep an in-flight request and its charge under one ledger lock."""
        if self._exclusive_owner == (os.getpid(), threading.get_ident()):
            yield
        else:
            with self.exclusive_batch():
                yield

    @contextmanager
    def _lock(self):
        if self._exclusive_owner == (os.getpid(), threading.get_ident()):
            yield
            return
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
                except (ValueError, RecursionError) as err:  # deeply nested JSON is a corrupt line, not a crash
                    raise SpendError(f"corrupt ledger line in {os.path.basename(path)}: stopping") from err
                if (not isinstance(e, dict) or "kind" not in e or not isinstance(e.get("batch"), (str, type(None)))
                        or not isinstance(e.get("id"), (str, type(None))) or not isinstance(e.get("price_sheet"), (dict, type(None)))):
                    raise SpendError(f"corrupt ledger entry in {os.path.basename(path)}: stopping")
                out.append(e)
        return out

    def _lines(self):
        return self._read(self.path)

    def entries(self):
        """This ledger file's entries (public read for drivers)."""
        return self._read(self.path)

    def _append(self, entry, path=None):
        # one O_APPEND write of one line: a stopped run never leaves a torn line mid-file
        data = (json.dumps(entry, sort_keys=True, allow_nan=False) + "\n").encode()
        fd = os.open(path or self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        try:
            os.write(fd, data)
            os.fsync(fd)
        finally:
            os.close(fd)

    @staticmethod
    def _sum(lines):
        charged, reserved, calls, over = {}, {}, 0, False
        info, opens, stops = {}, {}, []
        for e in lines:
            if e["kind"] == "reserve":
                if not _num(e.get("worst_usd")):
                    raise SpendError("corrupt reserve entry: stopping")
                reserved[e["id"]] = e["worst_usd"]
                calls += 1
                b = e.get("batch")
                wtok = (e.get("input_tokens_ub") or 0) + (e.get("max_tokens") or 0)
                if b is not None and not (isinstance(b, str) and _pos_int(e.get("input_tokens_ub")) and _pos_int(e.get("max_tokens"))):
                    raise SpendError("corrupt batch reserve entry: stopping")
                info[e["id"]] = {"batch": b, "wtok": wtok, "usage": None}
            elif e["kind"] == "charge":
                if not _num(e.get("usd")):
                    raise SpendError("corrupt charge entry: stopping")
                charged[e["id"]] = e["usd"]
                if e["id"] in info:
                    info[e["id"]]["usage"] = e.get("usage")
            elif e["kind"] == "overspent":
                over = True
            elif e["kind"] == "batch_open":
                if e.get("batch") in opens:  # the real ledgers hold exactly one batch_open per batch: a second is forged or corrupt
                    raise SpendError("corrupt ledger: a second batch_open for the same batch: stopping")
                opens[e.get("batch")] = (e.get("price_sheet") or {}).get("sha256")
            elif e["kind"] == "sheet_continuity":
                # valid only AFTER this same file's batch_open of that batch and only from the digest pinned at that point
                # (so a line in any other file, before the open, or branching from an old digest is corrupt, never followed)
                b, old, new = e.get("batch"), e.get("old_sha256"), e.get("new_sha256")
                if not (isinstance(b, str) and all(isinstance(x, str) and _HEX64.fullmatch(x) for x in (old, new)) and old != new):
                    raise SpendError("corrupt sheet_continuity entry: stopping")
                if opens.get(b) != old:
                    raise SpendError("corrupt sheet_continuity entry (not after its batch_open or not from the pinned digest): stopping")
                opens[b] = new
            elif e["kind"] == "batch_stop":
                stops.append((e.get("batch"), e.get("reason")))
        spent = sum(charged.values()) + sum(v for k, v in reserved.items() if k not in charged)
        batches = {}
        for cid, i in info.items():
            if i["batch"] is None:
                continue
            a = batches.setdefault(i["batch"], {"usd": 0.0, "calls": 0, "tokens": 0, "input": 0, "output": 0,
                                                "cache_read": 0, "cache_creation": 0, "unmetered_worst": 0})
            a["calls"] += 1
            a["usd"] += charged.get(cid, reserved[cid])
            u = i["usage"] if cid in charged else None
            if isinstance(u, dict) and _num(u.get("input_tokens")) and _num(u.get("output_tokens")):
                for k, f in (("input", "input_tokens"), ("output", "output_tokens"), ("cache_read", "cache_read_input_tokens"),
                             ("cache_creation", "cache_creation_input_tokens")):
                    a[k] += u.get(f) or 0
                a["tokens"] += _prompt_tokens(u) + u["output_tokens"]
            else:  # no usable usage: the reservation's worst case stands
                a["unmetered_worst"] += i["wtok"]
                a["tokens"] += i["wtok"]
        return {"spent_usd": spent, "calls": calls, "charged_ids": set(charged), "reserved_ids": set(reserved),
                "reserved": reserved, "overspent": over, "info": info, "opens": opens, "stops": stops, "batches": batches}

    @staticmethod
    def _files_in(d):
        if os.path.realpath(d) != os.path.realpath(PILOT_LEDGER_DIR):
            return sorted(glob.glob(os.path.join(d, "*.jsonl")))
        out = []
        for n in sorted(os.listdir(d)):
            f = os.path.join(d, n)
            if n == ".spend.lock":
                continue
            if os.path.islink(f) or not os.path.isfile(f):
                raise SpendError(f"non-regular entry {n!r} in the pilot ledger directory: stopping")
            out.append(f)
        return out

    def _files(self):
        return self._files_in(self.dir)

    def totals(self):
        """This ledger file's totals, plus global_usd/overspent across every ledger file in the directory."""
        own = self._sum(self._lines())
        files = self._files()
        ofiles = [f for f in files if os.path.abspath(f) != os.path.abspath(self.path)]
        others = [self._sum(self._read(f)) for f in ofiles]
        own["global_usd"] = own["spent_usd"] + sum(o["spent_usd"] for o in others)
        own["overspent"] = own["overspent"] or any(o["overspent"] for o in others)
        bt, opens, stops, open_files = {}, {}, list(own["stops"]), {}
        for x, f in zip([own] + others, [self.path] + ofiles):  # batches are counted across EVERY file of the directory
            for n, a in x["batches"].items():
                b = bt.setdefault(n, dict.fromkeys(a, 0))
                for k in a:
                    b[k] += a[k]
            for n, sha in x["opens"].items():
                if n in opens:  # fail closed: the real ledgers never open a batch in two files (checked on a copy of runs/spend)
                    raise SpendError(f"corrupt ledger: batch {n!r} has a batch_open in two files: stopping")
                opens[n], open_files[n] = sha, f  # continuity is read from the file that holds the one batch_open
        for o in others:
            stops += o["stops"]
        own["batches"], own["opens"], own["stops"], own["open_files"] = bt, opens, stops, open_files
        return own

    def _batch_total(self, t, name):
        """name's totals including every descendant batch."""
        out = dict.fromkeys(("usd", "calls", "tokens"), 0)
        for tag, a in t["batches"].items():
            if name in _lineage(tag, BATCH_SPECS):
                for k in out:
                    out[k] += a[k]
        return out

    def _check_batch(self, t, worst, tok, sha):
        """Refuse a reserve that could cross any cap of this batch or its parents; returns batches still to open."""
        lin = _lineage(self.batch, BATCH_SPECS)
        for s_, why in t["stops"]:
            # a settled child (the canary completing) does not stop its parent; any other stop does
            if s_ in lin or (why not in SETTLED_REASONS and self.batch in _lineage(s_, BATCH_SPECS)):
                raise BatchStopped(f"batch {s_!r} is stopped ({why}): no further calls")
        need = BATCH_SPECS[self.batch].get("requires_settled")
        if need is not None:
            why = [r for b, r in t["stops"] if b == need]
            ok = BATCH_SPECS[self.batch].get("settled_reasons", SETTLED_REASONS)
            if not why or any(r not in ok for r in why) or _stops_in_scope(t["stops"], need):
                raise BatchStopped(f"batch {self.batch!r} cannot open until {need!r} has settled ({' or '.join(ok)})")
        to_open, moves = [], []
        for n in lin:
            sp, tot = BATCH_SPECS[n], self._batch_total(t, n)
            if n in t["opens"]:
                if t["opens"][n] != sha:
                    moves.append((t["open_files"][n], self._continuity(n, t["opens"][n], sha)))
            else:
                to_open.append(n)
            if not (tot["calls"] + 1 <= sp["calls"]):
                raise MaxCallsExceeded(f"batch {n!r}: {tot['calls']} calls already made, limit {sp['calls']}")
            if not (tot["usd"] + worst <= sp["usd"]):
                raise SpendCeilingExceeded(f"batch {n!r}: spent {tot['usd']:.4f} + worst case {worst:.4f} would cross {sp['usd']:.2f} USD")
            if not (tot["tokens"] + tok <= sp["tokens"]):
                raise SpendCeilingExceeded(f"batch {n!r}: {tot['tokens']} tokens + worst case {tok} would cross {sp['tokens']}")
        return to_open, moves

    def _continuity(self, n, pinned, sha):
        """The sheet_continuity entry for batch n, or PriceSheetRefused. Accepted only when the predecessor file hashes to the
        digest the batch pinned, and the two sheets are identical in every key but 'fetched' (so every rate, tier, unit and
        alias), and the current sheet is within its age window. Anything else is today's refusal."""
        why = "no predecessor price sheet given"
        if self.predecessor_sheet is not None:
            try:
                old = PriceSheet.load(self.predecessor_sheet, allow_expired=True)
                if old.sha256 != pinned:
                    why = "predecessor sheet is not the sheet this batch pinned"
                elif {k: v for k, v in old.data.items() if k != "fetched"} != {k: v for k, v in self.sheet.data.items() if k != "fetched"}:
                    why = "predecessor and current sheets differ beyond 'fetched'"
                else:
                    self.sheet.check_age()
                    return {"kind": "sheet_continuity", "batch": n, "old_sha256": pinned, "new_sha256": sha,
                            "old_fetched": old.data["fetched"], "new_fetched": self.sheet.data["fetched"]}
            except PriceSheetRefused as e:
                why = str(e)
        err = PriceSheetRefused(f"price sheet changed mid-batch {n!r}")  # the original text; the reason rides on .reason
        err.reason = why
        raise err

    def check_sheet(self):
        """Read-only twin of reserve's sheet checks, run BEFORE any reservation: the sheet's age and, for every already-open
        batch of this lineage pinned to another digest, the sheet_continuity proof. Raises PriceSheetRefused, writes nothing."""
        self.sheet.check_age()
        t = self.totals()
        for n in _lineage(self.batch, BATCH_SPECS):
            if n in t["opens"] and t["opens"][n] != self.sheet.sha256:
                self._continuity(n, t["opens"][n], self.sheet.sha256)

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

    def reserve(self, call_id, model, input_tokens_ub, max_tokens, canary_input_tokens=None):
        """Call BEFORE the request. Raises if the worst case would cross the ceiling, HARD_CAP_USD, max_calls or a batch cap.

        Batched calls are also capped per call (PER_CALL_INPUT_TOKENS / PER_CALL_OUTPUT_TOKENS); the canary batch alone may
        declare canary_input_tokens (<= its spec) in place of the input cap."""
        worst = self.worst_case(model, input_tokens_ub, max_tokens)
        if canary_input_tokens is not None:
            lim = (BATCH_SPECS.get(self.batch) or {}).get("canary_input_tokens_max")
            if self.batch != CANARY or not _pos_int(canary_input_tokens, lim) or input_tokens_ub > canary_input_tokens:
                raise SpendError("canary_input_tokens is only for the canary batch, up to its declared limit")
        if self.batch is not None:
            if input_tokens_ub > (canary_input_tokens or PER_CALL_INPUT_TOKENS) or max_tokens > PER_CALL_OUTPUT_TOKENS:
                raise SpendError(f"batched call over its per-call cap ({PER_CALL_INPUT_TOKENS} input, {PER_CALL_OUTPUT_TOKENS} output tokens)")
        with self._lock():
            t = self.totals()
            if t["overspent"]:
                raise Overspent("a ledger in this directory is marked OVERSPENT: no further calls")
            if self.batch is None and (t["opens"] or t["stops"]):  # an unbatched ledger would skip every batch cap
                raise BatchStopped("this directory holds a batch ledger: unbatched ledgers are refused (fail closed)")
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
            tag = {}
            if self.batch is not None:
                to_open, moves = self._check_batch(t, worst, input_tokens_ub + max_tokens, self.sheet.sha256)
                for path, m in moves:  # into the file that holds that batch's own batch_open
                    self._append(m, path)
                for n in to_open:
                    self._append({"kind": "batch_open", "batch": n, "price_sheet": self.sheet.source()})
                tag = {"batch": self.batch}
            self._append({"kind": "reserve", "id": call_id, "model": model, "worst_usd": worst,
                          "input_tokens_ub": input_tokens_ub, "max_tokens": max_tokens,
                          "price_sheet": self.sheet.source(), **tag})
        return worst

    def settle(self, reason):
        """Record this ledger's batch as settled (complete or inconclusive); no further calls in it. Refused (BatchStopped)
        while a stop is recorded on the batch, any child batch or any batch it depends on (requires_settled, recursively)."""
        if self.batch is None or reason not in SETTLED_REASONS:
            raise SpendError(f"settle needs a batch and one of {SETTLED_REASONS}")
        with self._lock():
            bad = _stops_in_scope(self.totals()["stops"], self.batch)
            if bad:
                raise BatchStopped(f"batch {self.batch!r} cannot settle: stopped in its subtree or dependencies {bad}")
            self._append({"kind": "batch_stop", "batch": self.batch, "id": None, "reason": reason})

    def stop_batch(self, reason):
        """Record this ledger's batch as STOPPED (`stopped:<why>`, why in STOP_WHY, with or without the prefix). A stop never
        settles: it blocks this batch and its children, and ar1/pilot stay refused. settle() keeps complete/inconclusive."""
        why = reason[len("stopped:"):] if isinstance(reason, str) and reason.startswith("stopped:") else reason
        if self.batch is None or why not in STOP_WHY:
            raise SpendError(f"stop_batch needs a batch and a why in {STOP_WHY}")
        with self._lock():
            self._stop_batch(self.batch, None, f"stopped:{why}")

    def _stop_batch(self, batch, call_id, reason):
        if batch is not None:
            self._append({"kind": "batch_stop", "batch": batch, "id": call_id, "reason": reason})

    def _overspend(self, call_id, reason, batch=None):
        self._stop_batch(batch, call_id, reason)
        self._append({"kind": "overspent", "id": call_id, "reason": reason})
        raise Overspent(f"{call_id}: {reason}; ledger marked OVERSPENT, no further calls")

    def charge(self, call_id, model, usage, returned_model=None, **record):
        """Write the actual cost (from usage) and the per-call record; returns USD.

        Fail-closed: an invalid usage block, or an actual cost above the reserved worst case, records the true
        (or worst-case) cost and marks the ledger OVERSPENT. A different returned model is priced at the dearer
        of the two, or at the worst case when its price is unknown.
        """
        with self._lock():
            sm = self._sum(self._lines())
            reserved = sm["reserved"].get(call_id)
            if reserved is None:
                raise SpendError(f"charge for {call_id!r} without a reserve")
            batch, problem, stop = sm["info"][call_id]["batch"], None, None
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
            if batch is not None and clean is not None:
                cc = clean.get("cache_creation") or {}
                if (clean.get("cache_creation_input_tokens") or 0) > 0 or any(cc.values()):
                    stop = "cache_creation_input_tokens > 0 (the write breakdown can undercharge)"
                elif _prompt_tokens(clean) + clean["output_tokens"] > sm["info"][call_id]["wtok"]:
                    stop = "usage exceeds the reserved token bound"
            self._append({"kind": "charge", "id": call_id, "model": model, "usd": usd, "usage": clean,
                          "returned_model": returned_model, "usage_invalid": problem, "batch": batch, **record})
            if problem:
                self._overspend(call_id, f"invalid usage ({problem}); charged the reserved worst case", batch)
            if stop:
                self._stop_batch(batch, call_id, stop)
                if usd > reserved:  # also the documented directory-wide stop on spend above the reservation
                    self._append({"kind": "overspent", "id": call_id, "reason": stop})
                raise BatchStopped(f"{call_id}: {stop}; batch {batch!r} stopped")
            if usd > reserved:
                self._overspend(call_id, f"actual {usd:.6f} USD exceeds reserved worst case {reserved:.6f}", batch)
        return usd

    def void_unknown(self, call_id, **record):
        """A reserved call that produced no usage block: stays charged at its worst case."""
        with self._lock():
            self._append({"kind": "unbilled_unknown", "id": call_id, **record})


def batch_report(ledger_dir, batch):
    """Calls, tokens by class, USD, stop reason and remaining caps of one batch (children included), across the directory."""
    _validate_specs(BATCH_SPECS)
    if batch not in BATCH_SPECS:
        raise SpendError(f"unknown batch {batch!r}")
    sums = [Ledger._sum(Ledger._read(f)) for f in Ledger._files_in(ledger_dir)]
    stops = [x for m in sums for x in m["stops"]]
    pins = {}
    for m in sums:
        for n, sha in m["opens"].items():
            if n in pins:  # same fail-closed rule as totals(): a batch is opened in exactly one file
                raise SpendError(f"corrupt ledger: batch {n!r} has a batch_open in two files: stopping")
            pins[n] = sha
    lin = _lineage(batch, BATCH_SPECS)
    tot = dict.fromkeys(("usd", "calls", "tokens", "input", "output", "cache_read", "cache_creation", "unmetered_worst"), 0)
    for m in sums:
        for tag, a in m["batches"].items():
            if batch in _lineage(tag, BATCH_SPECS):
                for k in tot:
                    tot[k] += a[k]
    rem = {"usd": float("inf"), "calls": float("inf"), "tokens": float("inf")}
    for n in lin:  # the effective headroom is the tightest cap up the chain
        t = dict.fromkeys(("usd", "calls", "tokens"), 0)
        for m in sums:
            for tag, a in m["batches"].items():
                if n in _lineage(tag, BATCH_SPECS):
                    for k in t:
                        t[k] += a[k]
        for k in rem:
            rem[k] = min(rem[k], BATCH_SPECS[n][k] - t[k])
    scoped = [r for b, r in stops if b in lin or (
        r not in SETTLED_REASONS and batch in _lineage(b, BATCH_SPECS))]
    # A successful child cannot settle its parent or hide a blocking stop.
    reason = next((r for r in scoped if r not in SETTLED_REASONS), None)
    if reason is None:
        reason = "overspent" if any(m["overspent"] for m in sums) else next(iter(scoped), None)
    return {"batch": batch, "calls": tot["calls"], "usd": tot["usd"], "tokens": tot["tokens"],
            "tokens_by_class": {k: tot[k] for k in ("input", "output", "cache_read", "cache_creation", "unmetered_worst")},
            "stop_reason": reason, "remaining": rem, "caps": dict(BATCH_SPECS[batch]),
            "price_sheet_sha256": pins.get(batch)}
