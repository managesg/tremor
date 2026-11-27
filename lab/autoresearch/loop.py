"""Autoresearch loop scaffold: one editable practice card, sealed evaluator, deterministic keep/revert, hash-chained log.

Interfaces (duck-typed, no real backend is ever called here):
  proposer.propose(card_text, history) -> new card text. history holds TRAIN scores only.
  evaluator.evaluate(card_text, families) -> {family: Y}; attributes train_families, heldout_families,
    sealed_paths (evaluator code + answer keys), answer_texts() (for leak_check), optional usage (dict after a call).
  budget: {usd, max_iterations, max_reverts, margin, heldout_margin, model, input_tokens_ub, max_tokens, ledger}
    ledger duck-types spend.Ledger: worst_case(), reserve(call_id, model, in_ub, max_tokens), charge(call_id, model, usage).
Shortcut: the overfit alarm compares to the baseline held-out only, and a stop is the one bit it tells the proposer.
"""
import copy
import hashlib
import json
import math
import os
import random

from tremor import practice, seal  # noqa: E402  (path set by the package __init__)

MAX_CARD = practice.MAX_CARD


def _sha(s):
    return hashlib.sha256(s if isinstance(s, bytes) else s.encode("utf-8")).hexdigest()


def _canon(o):
    return json.dumps(o, sort_keys=True, separators=(",", ":"))


class ResultsLog:
    """Append-only JSONL; each line carries prev hash and its own hash over (prev + canonical record)."""

    def __init__(self, path):
        self.path, self.head = path, "0" * 64
        if os.path.exists(path):
            raise FileExistsError(path)

    def append(self, rec):
        h = _sha(self.head + _canon(rec))
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(_canon({"prev": self.head, "rec": rec, "hash": h}) + "\n")
        self.head = h


def verify_log(path):
    """Return (ok, n_lines, reason). A log without its closing 'end' record is reported as truncated."""
    prev, n, last = "0" * 64, 0, None
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                e = json.loads(line)
                ok = e["prev"] == prev and e["hash"] == _sha(prev + _canon(e["rec"]))
            except (ValueError, KeyError, TypeError):
                return False, n, f"line {n + 1} malformed"
            if not ok:
                return False, n, f"line {n + 1} chain broken"
            prev, n, last = e["hash"], n + 1, e["rec"]
    if not last or last.get("event") != "end":
        return False, n, "no end record (truncated)"
    return True, n, "ok"


def random_edit(rng, text):
    """Control edit: swap two words, drop one, or repeat one. Seeded, content-blind."""
    w = text.split(" ")
    if len(w) < 2:
        return text
    i, j = rng.randrange(len(w)), rng.randrange(len(w))
    op = rng.choice(("swap", "drop", "dup"))
    if op == "swap":
        w[i], w[j] = w[j], w[i]
    elif op == "drop":
        del w[i]
    else:
        w.insert(i, w[j])
    return " ".join(w)


class RandomEditProposer:
    def __init__(self, seed):
        self.rng = random.Random(seed)

    def propose(self, card_text, history):
        return random_edit(self.rng, card_text)


class RevertedBaselineProposer:
    """Always returns the card it was given, so every iteration is evaluated against the unchanged baseline."""

    def propose(self, card_text, history):
        return card_text


def _raw(card, text):
    head = "".join(f"{k}: {card[k]}\n" for k in practice.FIELDS)
    return (head + "---\n" + text + "\n").encode("utf-8")


def _mean(ys, fams):
    if not isinstance(ys, dict) or set(ys) != set(fams):
        raise ValueError("evaluator must return exactly one Y per requested family")
    for v in ys.values():
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError("evaluator Y must be a finite number")
    return sum(ys.values()) / len(ys)


class _Stop(Exception):
    def __init__(self, reason):
        self.reason = reason


class _Run:
    def __init__(self, evaluator, budget, arm):
        self.ev, self.b, self.arm = evaluator, budget, arm
        self.spent = 0.0
        self.unknown = False

    def evaluate(self, text, tag):
        """Reserve, evaluate train then held-out, settle. Returns (train_y, held_y, reserved, settled)."""
        b, led = self.b, self.b["ledger"]
        worst = led.worst_case(b["model"], b["input_tokens_ub"], b["max_tokens"])
        if not (self.spent + 2 * worst <= b["usd"]):  # written so NaN refuses; checked BEFORE any reservation
            raise _Stop("budget")
        out, reserved, settled = [], 0.0, 0.0
        for split, fams in (("train", self.ev.train_families), ("heldout", self.ev.heldout_families)):
            cid = f"{self.arm}-{tag}-{split}"
            try:
                reserved += led.reserve(cid, b["model"], b["input_tokens_ub"], b["max_tokens"])
            except Exception as e:  # the ledger refusing is a stop, whatever its class
                raise _Stop(f"ledger_refused:{type(e).__name__}")
            self.ev.usage = None
            out.append(_mean(self.ev.evaluate(text, list(fams)), fams))
            usage = getattr(self.ev, "usage", None)
            if usage is None:  # unknown cost is not zero: keep the worst case
                self.unknown = True
                if hasattr(led, "void_unknown"):
                    led.void_unknown(cid)
                settled += worst
            else:
                settled += led.charge(cid, b["model"], usage)
        self.spent += settled
        return out[0], out[1], reserved, settled


def run(card_id, proposer, evaluator, budget, seed, workdir, arm="main", practices_root=None):
    train, held = list(evaluator.train_families), list(evaluator.heldout_families)
    if not train or not held:
        raise ValueError("need at least one train and one held-out family")
    hashes = [_sha(str(f)) for f in train + held]
    if len(set(hashes)) != len(hashes) or {_sha(str(f)) for f in train} & {_sha(str(f)) for f in held}:
        raise ValueError("train and held-out families must be disjoint (hash check)")
    card = practice.load(card_id, practices_root)
    text = card["text"]
    if len(_raw(card, text)) > MAX_CARD:
        raise ValueError("starting card over the byte cap")
    d = os.path.join(workdir, arm)
    os.makedirs(d)
    card_path = os.path.join(d, "card.md")
    log = ResultsLog(os.path.join(d, "results.jsonl"))
    sl = seal.seal(evaluator.sealed_paths)
    answers = list(evaluator.answer_texts())
    rng_seed = seed  # recorded; proposers own their randomness
    r = _Run(evaluator, budget, arm)
    history, reverts, voided, stop = [], 0, False, None
    best_train = held0 = None

    def write(t):
        with open(card_path, "wb") as f:
            f.write(_raw(card, t))

    def close_seal():
        return sl.close()

    log.append({"event": "start", "arm": arm, "card_id": card_id, "seed": rng_seed, "card_sha256": _sha(_raw(card, text)),
                "seal_before": sl.before, "train": [str(f) for f in train], "heldout_n": len(held),
                "budget_usd": budget["usd"], "max_iterations": budget["max_iterations"]})
    write(text)
    try:
        ty, hy, rsv, stl = r.evaluate(text, "0")
        best_train, held0 = ty, hy
        log.append({"event": "iter", "i": 0, "card_sha256": _sha(_raw(card, text)), "train_y": ty, "heldout_y": hy,
                    "reserved_usd": rsv, "settled_usd": stl, "kept": True, "reason": "baseline"})
        history.append({"i": 0, "card_sha256": _sha(_raw(card, text)), "train_y": ty, "kept": True, "reason": "baseline"})
        for i in range(1, budget["max_iterations"] + 1):
            cand = proposer.propose(text, copy.deepcopy(history))
            rec = {"event": "iter", "i": i, "train_y": None, "heldout_y": None, "reserved_usd": 0.0, "settled_usd": 0.0}
            s = close_seal()
            if s["voided"]:
                voided, stop = True, "seal_violation"
                log.append({**rec, "card_sha256": None, "kept": False, "reason": "seal_violation: " + "; ".join(s["reasons"])})
                break
            raw = _raw(card, cand) if isinstance(cand, str) else b""
            rec["card_sha256"] = _sha(raw)
            reason = kept = None
            if not isinstance(cand, str):
                reason = "reject: proposal not text"
            elif len(raw) > MAX_CARD:
                reason = f"reject: {len(raw)} bytes > {MAX_CARD}"
            elif practice.leak_check({"text": cand}, answers):
                reason = "reject: leak_check found an answer in the card"
            if reason is None:
                write(cand)
                try:
                    ty, hy, rsv, stl = r.evaluate(cand, str(i))
                except _Stop as e:
                    write(text)
                    stop = e.reason
                    log.append({**rec, "kept": False, "reason": "stop: " + e.reason})
                    break
                rec.update(train_y=ty, heldout_y=hy, reserved_usd=rsv, settled_usd=stl)
                s = close_seal()
                if s["voided"]:
                    write(text)
                    voided, stop = True, "seal_violation"
                    log.append({**rec, "train_y": None, "heldout_y": None, "kept": False,
                                "reason": "seal_violation: " + "; ".join(s["reasons"])})
                    break
                if hy < held0 - budget["heldout_margin"]:
                    write(text)
                    stop = "overfit_alarm"
                    log.append({**rec, "kept": False, "reason": "overfit_alarm: held-out fell beyond the margin"})
                    break
                if ty >= best_train + budget["margin"]:
                    text, best_train, kept, reason = cand, ty, True, "keep: train Y improved by the margin"
                else:
                    kept, reason = False, "revert: train Y did not improve by the margin"
            else:
                kept = False
            if not kept:
                write(text)
            log.append({**rec, "kept": kept, "reason": reason})
            history.append({"i": i, "card_sha256": rec["card_sha256"], "train_y": rec["train_y"], "kept": kept, "reason": reason})
            reverts = 0 if kept else reverts + 1
            if reverts >= budget["max_reverts"]:
                stop = "consecutive_reverts"
                break
        else:
            stop = "iteration_cap"
    except _Stop as e:  # baseline could not be afforded
        stop = e.reason
    final = {"event": "end", "stop": stop, "voided": voided, "best_train_y": best_train, "baseline_heldout_y": held0,
             "final_card_sha256": _sha(_raw(card, text)), "spent_usd": r.spent, "cost_unknown": r.unknown}
    log.append(final)
    return {**final, "arm": arm, "log_path": log.path, "log_head": log.head, "card_path": card_path, "card_text": text}


def run_controls(card_id, proposer, evaluator, budget, seed, workdir, **kw):
    """The proposer arm plus a random-edit arm and a reverted-baseline arm, same iteration and USD budget each.
    budget["make_ledger"](arm), if present, supplies a fresh ledger per arm so the arms are compute-matched."""
    out = {}
    for arm, p in (("proposer", proposer), ("random_edit", RandomEditProposer(seed)), ("reverted_baseline", RevertedBaselineProposer())):
        b = dict(budget)
        if "make_ledger" in b:
            b["ledger"] = b["make_ledger"](arm)
        out[arm] = run(card_id, p, evaluator, b, seed, workdir, arm=arm, **kw)
    return out
