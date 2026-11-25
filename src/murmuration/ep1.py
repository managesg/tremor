"""EP-1 batch driver: canary, pilot and the pre-registered EP-1 schedule (prereg/EP1.md sections 6, 10, 12). stdlib only.

`run_batch(kind, client, ledger, schedule_seed, outdir, dry_run=False)` for kind in canary, pilot, pilot2, pilot3, pilot4, ep1. One process, one
ledger file per batch, one episode at a time. Output directory: `schedule.json` (the plan), `episodes.jsonl` (append-only,
one line per episode attempt), `events.jsonl` (interrupted attempts), `final.json` (stop reason and ledger report), and for
the pilot `pilot_trace.txt` (compact per-episode trace for manual review).

Resolved transport rules (owner-delegated, 2026-11-20). After an HTTP 429 or 5xx or any transport failure (timeout, reset,
cut-short body) the episode is an infrastructure abort. It is re-run ONCE from its first call, same seeds, a NEW id_tag
(`r1` appended). A third transport abort in the batch stops the batch. An HTTP 400 stops the batch at once and is never
re-run: our request is malformed, an instrument bug. A re-run that itself aborts is lost (its cell is incomplete), and
a re-run that the remaining calls cannot pay for (8 calls, with every still-pending cell kept affordable) stops the batch.

Other stops (batch settles `stopped:<why>` and runs no more): any batch cap before an episode could start (calls, tokens,
USD), a void (returned-model mismatch, a 200 with no model, usage above the per-call cap), either scorer disagreement,
an invalid log (`invalid_log`), malformed replies above 1/4 of the first block or 10% overall or 15% in one condition,
an `overspent` ledger, an unexplained `unbilled_unknown`, a spend stop inside the loop, a prompt over the cap.
An episode in which every agent was stopped by the refusal rule (`episode_stopped`) never stops the batch, however many
there are: it is scored, included and counted per arm (design notes, orchestrator ruling 1 on section 2e).
Final reason: `complete`, `inconclusive` (all episodes done, primary contrast unresolved) or `stopped:<why>`.

Every episode is scored by alloc.score, alloc2.score and the Lean scorer (formal_alloc; prereg section 7: three agreeing
verdicts or the episode does not count). Lean outcomes (orchestrator decision, 2026-11-20): INVALID (toolchain missing or
unpinned, build or axiom audit failed; the third scorer is not running) stops the batch, before the first call through a
probe and at any later episode; REJECTED (the Lean scorer refused this input) voids that episode only; any field
disagreement between two scorers, or an OK Lean score missing a shared field, voids the episode and stops the batch.
A void cell is done: it is never re-run. Resumable: ids are idempotent (a used episode id is never re-sent), a crashed
attempt is logged as interrupted and its cell re-run under the next id_tag. A stopped or settled batch refuses to run again.

A stop is written with the public Ledger.stop_batch (closed `why` set, see _WHY); the detailed cause stays in final.json
"detail". A contrast is "resolved" by analysis.resolve's rule only (bootstrap AND paired-t both exclude 0 on one side), read from the
structured summary["contrasts"], never from rendered text.
The key is read from MURMURATION_EP1_KEY in `cli` only and handed to the client; it is never printed or stored.
"""
import hashlib
import importlib.util
import json
import os
import random
import re
import tempfile

from . import analysis, backend_claude as bc, cardcheck, formal_alloc, manifest, practice as practicemod, spend, team_claude as tc
from .trapbench import alloc, alloc2

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MODEL = tc.CAPS["model"]
KEY_ENV = "MURMURATION_EP1_KEY"
REVIEW_FILE = os.path.join(ROOT, "docs", "reports", "card-A-review.md")  # non-author review; names the card sha256
PRICE_SHEET = os.path.join(ROOT, "docs", "reports", "price-sheet.json")
PILOT_DIR = os.path.join(ROOT, "practices", "pilot")
KINDS = ("canary", "pilot", "pilot2", "pilot3", "pilot4", "ep1")
PILOTS = ("pilot", "pilot2", "pilot3", "pilot4")  # pilots 2 to 4: same 5 conditions, own batch and ids (design notes, prereg change 19)
BASE_CONDS = ("none", "play", "code")
PILOT_CARDS = {"states_check": "states_the_check.md", "keyword_stuffed": "keyword_stuffed.md"}
COND_TAG = {"states_check": "sc", "keyword_stuffed": "kw"}
DEFAULT_SETS = {"ep1": 20, "pilot": 3, "pilot2": 6, "pilot3": 6, "pilot4": 6}  # pilot: 3 x 5 x 8 = 120 of 150; pilot2/3: 6 x 5 x 8 = 240 of 260
SPLIT = {"ep1": "heldout", "pilot": "train", "pilot2": "train", "pilot3": "train", "pilot4": "train"}
ID_PREFIX = {"pilot2": "p2", "pilot3": "p3", "pilot4": "p4"}  # pilots 2 to 4 rerun pilot 1's train sets: ids must not collide in the ledger directory
# Owner 2026-11-20 (prereg 16b): pilot 2 runs both task orders (team_claude.TASK_ORDERS). Each task set gets one order,
# balanced and seeded without the arm; every condition of a set runs with that order, so arm contrasts are within-order.
# Other kinds carry no task_order in their plan and run the default shared order.
ORDER_KINDS = ("pilot2", "pilot3", "pilot4")  # pilot 3 repeats the pilot 2 design (prereg change 19)
ORDER_TAG = {"per_agent": "pa"}  # in the episode id after the kind prefix; shared adds nothing (ids as before)
CALLS_PER_EPISODE = 8
CANARY_BYTES = 90_000
NBOOT = 10_000
FAKE = "FAKE: loopback fake server; not evidence about any model"
MAX_ATTEMPTS = 2  # the original and one re-run
# Exact bracket values for the alloc family (practice A, Y = distinct_passing / 4 slots): rung0-expected-v2.md section 2;
# prereg/EP1.md section 10 ("the fully herded floor is 0.25") and section 12 (void if the scripted floor scores above
# 1/4 or the scripted oracle below 4/4). Every bracket episode must hit its value exactly, in every arm.
FLOOR_Y, ORACLE_Y = 0.25, 1.0


class PreflightError(ValueError):
    pass


class _StopBatch(Exception):
    pass


def _lean(ts, log):  # tests patch this; INVALID stops the batch, REJECTED voids the episode
    return formal_alloc.score(ts, log)


def plan(kind, schedule_seed, n_sets=None):
    """[{set, split, order}]: the task block s runs its conditions in an order seeded per block. schedule_seed 0 is the
    prereg's random.Random(f"ep1:order:{s}"); another seed adds itself to the key. pilot2 blocks also carry task_order."""
    conds = BASE_CONDS + (tuple(PILOT_CARDS) if kind in PILOTS else ())
    out = []
    for s in range(n_sets or DEFAULT_SETS[kind]):
        order = list(conds)
        random.Random(f"ep1:order:{s}" if not schedule_seed else f"ep1:order:{schedule_seed}:{s}").shuffle(order)
        out.append({"set": s, "split": SPLIT[kind], "order": order})
    if kind in ORDER_KINDS:
        orders = (list(tc.TASK_ORDERS) * len(out))[:len(out)]  # half each (one more shared when the count is odd)
        random.Random(f"ep1:task_order:{schedule_seed}").shuffle(orders)
        for b, o in zip(out, orders):
            b["task_order"] = o
    return out


def _pilot_card(name):
    with open(os.path.join(PILOT_DIR, PILOT_CARDS[name]), "rb") as f:
        raw = f.read()
    text = raw.decode().partition("\n---\n")[2].rstrip("\n")
    return {"id": "A", "version": "1", "enforcer": "none", "measures": f"pilot:{name}", "text": text,
            "sha256": hashlib.sha256(raw).hexdigest()}


def _check_freeze():
    """Verify the canonical EP-1 code tree and identify the paid run's frozen inputs."""
    prereg = os.path.join(ROOT, "prereg", "EP1.md")
    lean_root = os.path.join(ROOT, "formal", "alloc_score")
    try:
        with open(prereg, "rb") as f:
            prereg_bytes = f.read()
        text = prereg_bytes.decode("utf-8")
        fields = re.findall(r"^code_tree_hash:(.*)$", text, re.M)
        if len(fields) != 1 or not re.fullmatch(r"[0-9a-f]{64}", fields[0].strip()):
            raise PreflightError("refused: EP-1 code_tree_hash is missing, blank or invalid; freeze it first")
        frozen = fields[0].strip()
        statuses = re.findall(r"^Status:(.*)$", text, re.M)
        if len(statuses) != 1 or statuses[0].strip() not in ("FROZEN", "FROZEN."):
            raise PreflightError("refused: EP-1 preregistration must declare Status: FROZEN")

        # The preregistration seals Lean sources and manifests, not the build.
        paths = [os.path.join(ROOT, d) for d in ("src", "practices", "tests")]
        paths.extend(os.path.join(lean_root, name) for name in ("lakefile.toml", "lake-manifest.json", "lean-toolchain"))
        for directory, subdirs, files in os.walk(lean_root):
            subdirs[:] = [name for name in subdirs if name != ".lake"]
            paths.extend(os.path.join(directory, name) for name in files if name.endswith(".lean"))
        actual = manifest.tree_hash(paths, root=ROOT)
        if actual != frozen:
            raise PreflightError(f"refused: EP-1 code_tree_hash mismatch: frozen {frozen}, now {actual}")
        return {"code_tree_hash": actual, "prereg_sha256": hashlib.sha256(prereg_bytes).hexdigest(),
                "template_sha256": tc.template_hashes()}
    except (OSError, UnicodeError) as e:
        raise PreflightError(f"refused: cannot verify EP-1 freeze: {e}") from None


def _preflight(review):
    """Card A passes cardcheck with a recorded non-author review, and its neutral twin matches its bytes; else refuse."""
    path = os.path.join(practicemod.ROOT, "A.md")
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    if not review or not os.path.isfile(review):
        raise PreflightError(f"refused: the play card has no recorded review file ({review!r} is missing)")
    with open(review, encoding="utf-8") as f:
        m = re.search(r"reviewed_sha256:\s*([0-9a-f]{64})", f.read())
    res = cardcheck.check_card(raw, kind="play", reviewer=review, reviewed_sha256=m.group(1) if m else None)
    if not res["ok"]:
        raise PreflightError("refused: card check failed: " + "; ".join(res["reasons"]))
    card = practicemod.load("A")
    if not cardcheck.match_report({"A": card["text"], "N": practicemod.neutral(card)["text"]})["ok"]:
        raise PreflightError("refused: card and neutral twin differ in length")


def _read_jsonl(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(x) for x in f.read().splitlines() if x.strip()]


def _append(path, obj):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, sort_keys=True, default=str) + "\n")
        f.flush()
        os.fsync(f.fileno())


_WHY = (("input_integrity", "crash"), ("enforcement_violation", "invalid_log"), ("action_boundary", "invalid_log"),
        ("cap", "cap"), ("no_rerun_calls_left", "cap"), ("overspent", "cap"), ("unbilled_unknown", "cap"),
        ("spend_stop", "cap"), ("transport", "transport"), ("cells_lost", "transport"), ("http_400", "http400"),
        ("invalid_log", "invalid_log"), ("void", "void_model"), ("malformed", "void_model"),
        ("scorer_disagreement", "scorer_disagreement"), ("scorer_invalid", "scorer_disagreement"))


def _why(detail):
    """Map a driver stop cause to the ledger's closed set of why values; an unknown cause is a crash."""
    return next((w for p, w in _WHY if detail.startswith(p)), "crash")


_CANARY_WHY = {"EpisodeVoided": "void_model", "EpisodeCapExceeded": "cap", "BatchStopped": "cap", "SpendCeilingExceeded": "cap", "MaxCallsExceeded": "cap",
               "Overspent": "cap", "RuntimeError": "transport"}


def _finish(ledger, reason):
    """Settle the batch: complete/inconclusive through settle, `stopped:<why>` through the public stop_batch."""
    if reason in spend.SETTLED_REASONS:
        ledger.settle(reason)
    else:
        ledger.stop_batch(reason)


def _check_open(ledger, kind):
    stops = ledger.totals()["stops"]
    if any(b == kind for b, _ in stops):
        raise spend.BatchStopped(f"batch {kind!r} is already stopped or settled: {[r for b, r in stops if b == kind]}")
    if kind != "canary" and not any(b == "canary" and r == "complete" for b, r in stops):
        raise spend.BatchStopped(f"batch {kind!r} cannot open until the canary has completed")


def _cost(ledger, eid):
    lines = ledger.entries()
    res = {e["id"]: e["worst_usd"] for e in lines if e["kind"] == "reserve" and e["id"].startswith(eid + ":")}
    chg = {e["id"]: e["usd"] for e in lines if e["kind"] == "charge" and e["id"] in res}
    return {"reserved_usd": sum(res.values()), "settled_usd": sum(chg.get(k, v) for k, v in res.items()),
            "reserve_lines": len(res), "charge_lines": len(chg)}


def _score_gate(log, ts, third):
    p = alloc.score(log, ts)
    out = {"alloc": p, "alloc2": None, "third": None, "disagreement": None}
    try:
        out["alloc2"] = alloc2.second_scorer_gate(log, ts, alloc.score)
    except alloc2.ScorerDisagreement as e:
        out["disagreement"] = f"alloc2: {e}"
    try:
        r = third(ts, log)
    except Exception as e:  # noqa: BLE001 - a broken third scorer is INVALID, never agreement
        r = {"status": "INVALID", "reason": f"{type(e).__name__}"}
    if isinstance(r, dict) and r.get("status") == "OK":
        s = r.get("score") if isinstance(r.get("score"), dict) else {}
        diff = [f"{k}: missing" for k in formal_alloc.FIELDS if k in p and k not in s] + alloc2.compare(p, s)
        out["third"] = {"status": "DISAGREE" if diff else "OK", "score": r.get("score"), "diff": diff}
        if diff and not out["disagreement"]:
            out["disagreement"] = "third: " + "; ".join(diff)
    else:
        st = r.get("status") if isinstance(r, dict) else None
        out["third"] = {"status": st if st in ("INVALID", "REJECTED") else "INVALID",
                        "reason": str(r.get("reason") if isinstance(r, dict) else r)[:200]}
    return out


def _scorer_void(gate):
    """The void an episode's scorer gate imposes, or None. Disagreement and INVALID stop the batch; REJECTED does not."""
    if gate["disagreement"]:
        return "scorer_disagreement: " + gate["disagreement"]
    st = gate["third"]["status"]
    return None if st == "OK" else f"scorer_{st.lower()}: {gate['third']['reason']}"


def _void_reason(v):
    v = str(v)
    if "thinking block" in v:
        return "void_thinking_block"
    if "returned model" in v:
        return "void_model_mismatch"
    return "void_no_model" if "no model" in v or "without a model" in v else "void_other"


def _trace(rec):
    L = [f"== {rec['episode_id']} cond={rec['cond']} set={rec['taskset_id']} ended={rec['ended']} Y={rec['Y']} "
         f"order={rec['block_order']} task_order={rec['task_order']}"]
    for t in rec["turns"]:
        L.append(f"  r{t['round'] + 1} {t['agent']} {t.get('status')} {t.get('actions') or ''} "
                 f"{(t.get('reason') or '')[:60]} | {str(t.get('reply', ''))[:300]!r}")
    L.append(f"  refusals={rec['refusals']} stopped={rec['stopped_agents']} scores={rec['scores']}")
    return "\n".join(L) + "\n"


class _Run:
    def __init__(self, kind, client, ledger, seed, outdir, dry_run, n_sets, third, freeze=None):
        self.kind, self.client, self.ledger, self.seed, self.dry = kind, client, ledger, seed, dry_run
        self.out, self.third = outdir, third or _lean
        self.plan = plan(kind, seed, n_sets)
        self.cells = [(b, c) for b in self.plan for c in b["order"]]
        self.sched = {"kind": kind, "schedule_seed": seed, "dry_run": dry_run, "plan": self.plan,
                      "model": MODEL, "stamp": FAKE if dry_run else None}
        if freeze is not None:
            self.sched["freeze"] = freeze
        self.epath, self.vpath = os.path.join(outdir, "episodes.jsonl"), os.path.join(outdir, "events.jsonl")

    def start(self):
        os.makedirs(self.out, exist_ok=True)
        sp = os.path.join(self.out, "schedule.json")
        if os.path.exists(sp):
            with open(sp, encoding="utf-8") as f:
                prior = json.load(f)
            if "freeze" in self.sched:
                if not isinstance(prior, dict) or not prior.get("freeze"):
                    raise PreflightError("refused: existing EP-1 schedule has no recorded freeze")
                if prior["freeze"] != self.sched["freeze"]:
                    raise PreflightError("refused: existing EP-1 schedule belongs to a different freeze")
            if prior != json.loads(json.dumps(self.sched)):
                raise ValueError("refused: this output directory holds a different schedule")
        else:
            if "freeze" in self.sched and any(os.path.lexists(path) for path in (
                self.epath, self.vpath, os.path.join(self.out, "final.json"),
            )):
                raise PreflightError("refused: existing EP-1 output has no schedule recording its freeze")
            with open(sp, "x", encoding="utf-8") as f:
                json.dump(self.sched, f, sort_keys=True, indent=1)
        self.recs = _read_jsonl(self.epath)
        self.aborts = sum(r["ended"] == "infrastructure_abort" for r in self.recs)

    def _have(self, s, cond):
        return [r for r in self.recs if r["set"] == s and r["cond"] == cond]

    def _valid(self, r):
        return r["ended"] in ("complete", "episode_stopped") and not r.get("void")

    def _done(self, s, cond):
        """A cell is finished when it has a valid record, a void record (a void is never re-run) or no attempts left."""
        have = self._have(s, cond)
        return any(self._valid(r) or r.get("void") for r in have) or len(have) >= MAX_ATTEMPTS

    def _probe_third(self):
        """Before any call: the Lean scorer must answer OK on an empty log of the first task set, else nothing runs."""
        blk = self.plan[0]
        try:
            r = self.third(alloc.gen(blk["set"], blk["split"]), [])
        except Exception:  # noqa: BLE001 - a broken third scorer is INVALID
            r = None
        if not (isinstance(r, dict) and r.get("status") == "OK"):
            raise _StopBatch("scorer_invalid")

    def _room(self):
        rem = spend.batch_report(self.ledger.dir, self.kind)["remaining"]
        w = self.ledger.worst_case(MODEL, tc.CAPS["input_tokens"], tc.CAPS["output_tokens"])
        need = {"calls": CALLS_PER_EPISODE, "tokens": CALLS_PER_EPISODE * (tc.CAPS["input_tokens"] + tc.CAPS["output_tokens"]),
                "usd": CALLS_PER_EPISODE * w}
        for k, v in need.items():
            if not rem[k] >= v:
                raise _StopBatch(f"cap_{k}")

    def _require_integrity(self):
        expected = self.sched.get("freeze")
        if expected is None:
            return
        try:
            current = _check_freeze()
        except (PreflightError, ValueError) as error:
            raise bc.InputIntegrityError from error
        if current != expected:
            raise bc.InputIntegrityError

    def go(self):
        try:
            self._require_integrity()
            self._probe_third()
            for i, (blk, cond) in enumerate(self.cells):
                if not self._done(blk["set"], cond):
                    self._cell(blk, cond, i)
            # cells lost to transport aborts stop the batch; a scorer-REJECTED void only leaves its set incomplete
            lost = sum(not any(self._valid(r) or r.get("void") for r in self._have(b["set"], c)) for b, c in self.cells)
            if lost:
                raise _StopBatch("cells_lost")
            detail = None
            self._require_integrity()
            reason = "complete" if self.kind != "ep1" or self._resolved() else "inconclusive"
        except bc.InputIntegrityError:
            self._record_integrity_stop()
            reason, detail = "stopped:crash", "input_integrity"
        except _StopBatch as e:
            reason, detail = f"stopped:{_why(str(e))}", str(e)
        _finish(self.ledger, reason)
        out = {"kind": self.kind, "reason": reason, "detail": detail, "stamp": FAKE if self.dry else None, "episodes": len(self.recs),
               "aborts": self.aborts,
               "voids": {c: sum(1 for r in self.recs if r["cond"] == c and r.get("void")) for c in sorted({r["cond"] for r in self.recs})},
               "ledger": spend.batch_report(self.ledger.dir, self.kind)}
        with open(os.path.join(self.out, "final.json"), "w", encoding="utf-8") as f:
            json.dump(out, f, sort_keys=True, indent=1, default=str)
        return out

    def _resolved(self):
        return _summary(self.recs, self.dry)["contrasts"][analysis.CONTRASTS[0][0]]["resolved"] != "unresolved"

    def _record_integrity_stop(self):
        _append(self.vpath, {"event": "input_integrity"})

    def _cell(self, blk, cond, idx):
        self._require_integrity()
        s, split = blk["set"], blk["split"]
        ts = alloc.gen(s, split)
        arm = cond if cond in BASE_CONDS else "play"
        card = "A" if cond in BASE_CONDS else _pilot_card(cond)
        i = len(self._have(s, cond))
        while i < MAX_ATTEMPTS:
            self._room()
            order = blk.get("task_order", tc.CAPS["task_order"])
            tag = ID_PREFIX.get(self.kind, "") + ORDER_TAG.get(order, "") + COND_TAG.get(cond, "") + ("" if i == 0 else "r1")
            guard = {"before_request": self._require_integrity} if "freeze" in self.sched else {}
            try:
                rec = tc.run_episode_model(ts, arm, card, self.client, seed=s, batch=self.kind,
                                           caps={"id_tag": tag, "task_order": order}, **guard)
            except ValueError as e:
                if "already used" not in str(e):
                    raise
                if len(self._have(s, cond)) <= i:  # ledger spent calls under this id, but no record: a crashed attempt
                    _append(self.vpath, {"event": "interrupted", "set": s, "cond": cond, "attempt": i})
                i += 1
                continue
            rec.update(kind=self.kind, cond=cond, set=s, schedule_seed=self.seed, block_order=blk["order"], attempt=i,
                       stamp=FAKE if self.dry else None, ledger=_cost(self.ledger, rec["episode_id"]))
            try:
                self._require_integrity()
            except bc.InputIntegrityError:
                rec["void"] = "input_integrity"
            if rec.get("void") == "input_integrity":
                self._record_integrity_stop()
            if rec.get("void") in ("input_integrity", "enforcement_violation", "action_boundary"):
                detail = rec["void"]
                rec.update(Y=None, valid=False, status=f"void:{detail}", ended="void", rerunnable=False)
                _append(self.epath, rec)
                self.recs.append(rec)
                raise _StopBatch(detail)
            rec["scorers"] = _score_gate(rec["log"], ts, self.third)
            # a loop void (model, usage) keeps its own reason and stop; an abort is re-run, never voided by a scorer
            sv = None if rec.get("void") or rec["ended"] == "infrastructure_abort" else _scorer_void(rec["scorers"])
            if sv:
                rec["void"] = sv
            elif rec.get("valid") is not True or rec["scorers"]["alloc"].get("valid") is not True:
                rec.update(Y=None, valid=False, status="void:invalid_log", void=rec.get("void") or "invalid_log")
            _append(self.epath, rec)
            self.recs.append(rec)
            if self.kind in PILOTS:
                with open(os.path.join(self.out, "pilot_trace.txt"), "a", encoding="utf-8") as f:
                    f.write(_trace(rec))
            if self._after(rec) != "abort":
                return
            i += 1
            pending = sum(not any(self._valid(r) for r in self._have(b["set"], c)) for b, c in self.cells[idx + 1:])
            if i < MAX_ATTEMPTS:  # the re-run must leave every other pending cell affordable
                rem = spend.batch_report(self.ledger.dir, self.kind)["remaining"]["calls"]
                if rem - CALLS_PER_EPISODE * pending < CALLS_PER_EPISODE:
                    raise _StopBatch("no_rerun_calls_left")

    def _after(self, rec):
        end = rec["ended"]
        if str(rec.get("void") or "").startswith("scorer_disagreement"):
            raise _StopBatch("scorer_disagreement")
        if str(rec.get("void") or "").startswith("scorer_invalid"):  # the third scorer stopped running
            raise _StopBatch("scorer_invalid")
        if str(rec.get("void") or "").startswith("invalid_log"):  # logged and excluded; the instrument must not write one
            raise _StopBatch("invalid_log")
        if end == "infrastructure_abort":
            if any("HTTP 400" in str(t.get("reason")) for t in rec["turns"]):
                raise _StopBatch("http_400")
            self.aborts += 1
            if self.aborts >= 3:
                raise _StopBatch("transport_aborts")
            return "abort"
        if end == "void":
            raise _StopBatch(_void_reason(rec["void"]))
        # ruling 1 (design notes, 2026-11-20): an all-stopped episode never stops the batch; it is scored and counted per arm
        if end not in ("complete", "episode_stopped"):
            raise _StopBatch(end)
        if self.ledger.totals()["overspent"]:
            raise _StopBatch("overspent")
        lines = self.ledger.entries()
        pre = rec["episode_id"] + ":"
        charged = {e["id"] for e in lines if e["kind"] == "charge"}
        for e in lines:  # only a retry that then succeeded may leave an unbilled line
            if e["kind"] == "unbilled_unknown" and e["id"].startswith(pre) and e["id"] + "#r1" not in charged:
                raise _StopBatch("unbilled_unknown")
        self._malformed()
        return "ok"

    def _malformed(self):
        good = [r for r in self.recs if r["ended"] != "infrastructure_abort"]
        first = self.plan[0]
        first_n = sum(r["malformed"] for r in good if r["set"] == first["set"])
        if first_n > len(first["order"]) * CALLS_PER_EPISODE // 4 and all(
                any(self._valid(r) for r in self._have(first["set"], c)) for c in first["order"]):
            raise _StopBatch("malformed_first_block")
        planned = len(self.cells) * CALLS_PER_EPISODE
        if sum(r["malformed"] for r in good) > planned // 10:
            raise _StopBatch("malformed_overall")
        per = len(self.plan) * CALLS_PER_EPISODE
        for c in {r["cond"] for r in good}:
            if sum(r["malformed"] for r in good if r["cond"] == c) > per * 15 // 100:
                raise _StopBatch(f"malformed_{c}")


def _refuse_invalid(recs):
    """No numeric Y may reach an analysis for a log the scorers called invalid (EP1 section 7: such an episode is void)."""
    bad = [r.get("episode_id") for r in recs if r.get("Y") is not None and (
        r.get("valid") is False or str(r.get("status", "")).startswith("void") or (r.get("scores") or {}).get("valid") is False)]
    if bad:
        raise analysis.AnalysisRefused(f"refused: invalid-log episodes carry a numeric Y: {bad}")


def _summary(recs, fake):
    _refuse_invalid(recs)
    if fake:  # fake records are never model records; analysis wants the scripted: prefix for that table
        return analysis.summarise([dict(r, episode_id="scripted:" + r["episode_id"]) for r in recs], "scripted", n_boot=NBOOT)
    return analysis.summarise(recs, "model", n_boot=NBOOT)


def _canary_body(n):
    head = "Reply with the single word OK. Ignore the filler text below.\n"
    msg = [{"role": "user", "content": head + ("lorem ipsum dolor sit amet " * (n // 27 + 1))[:n]}]
    return json.dumps({"max_tokens": 300, "messages": msg, "model": MODEL, "temperature": 1.0, "thinking": bc.THINKING_OFF},
                      sort_keys=True), msg


def _canary(client, ledger, outdir, dry_run):
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "schedule.json"), "w", encoding="utf-8") as f:
        json.dump({"kind": "canary", "dry_run": dry_run, "model": MODEL, "stamp": FAKE if dry_run else None}, f)
    n = CANARY_BYTES - len(_canary_body(0)[0])
    body, msg = _canary_body(n)
    assert len(body.encode()) == CANARY_BYTES
    out = {"kind": "canary", "stamp": FAKE if dry_run else None, "request_bytes": CANARY_BYTES, "ok": False,
           "compare_with_console": "owner: Console cost and tokens for this one request must equal ledger_usd and usage"}
    why = stop = None
    try:
        out["worst_case_usd"] = ledger.worst_case(MODEL, CANARY_BYTES, 300)
        rec = client.call(bc.Episode("canary", CANARY_BYTES + 1000, 180), "canary:0", MODEL, msg, 300, 1.0,
                          canary_input_tokens=CANARY_BYTES, batch="canary")
        rec = rec if isinstance(rec, dict) else {}
        u = rec.get("usage") if isinstance(rec.get("usage"), dict) else {}
        out.update(returned_model=rec.get("returned_model"), usage=u, ledger_usd=rec.get("usd"),
                   stop_reason=rec.get("stop_reason"), reply=str(rec.get("text"))[:200])
        if rec.get("void") or not tc.model_matches(MODEL, rec.get("returned_model")):
            why, stop = "wrong_model", "void_model"
        elif u.get("input_tokens") is None or u.get("output_tokens") is None:
            why, stop = "missing_usage", "void_model"
        elif rec.get("stop_reason") != "end_turn":  # cut short (max_tokens), a refusal or another stop: malformed
            why, stop = "malformed:" + tc.STOP_MALFORMED.get(rec.get("stop_reason"), "bad_stop_reason"), "void_model"
        elif not isinstance(rec.get("text"), str) or not rec["text"].strip():
            why, stop = "malformed:empty", "void_model"
        elif ledger.totals()["overspent"]:
            why, stop = "overspent", "cap"
    except Exception as e:  # noqa: BLE001 - every failure leaves a record and a stopped batch, never a bare crash
        why = f"call_failed:{type(e).__name__}"
        stop = "transport" if tc._http_exception(e) else _CANARY_WHY.get(type(e).__name__, "crash")
    out["ok"], out["reason"], out["detail"] = why is None, "complete" if why is None else "stopped:" + stop, why
    try:
        out["ledger"] = _cost(ledger, "canary")
    except Exception as e:  # noqa: BLE001 - the record is written even when the ledger cannot be read
        out["ledger"] = f"unreadable: {type(e).__name__}"
    with open(os.path.join(outdir, "canary.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, sort_keys=True, indent=1, default=str)
    _finish(ledger, out["reason"])
    return out


def run_batch(kind, client, ledger, schedule_seed, outdir, dry_run=False, *, n_sets=None, review=None, third_scorer=None):
    """Run one batch; returns the final dict. A real client needs dry_run=False, a fake one dry_run=True (stamped FAKE)."""
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}")
    if getattr(ledger, "batch", None) != kind:
        raise ValueError(f"the ledger's batch {getattr(ledger, 'batch', None)!r} is not {kind!r}")
    if bool(dry_run) == tc._is_real(client):
        raise ValueError("refused: dry_run needs a fake client and a real client needs dry_run=False")
    if getattr(client, "ledger", ledger if dry_run else None) is not ledger:
        raise ValueError("refused: client and driver must share the same ledger instance")
    freeze = _check_freeze() if kind == "ep1" and not dry_run else None
    with ledger.exclusive_batch():
        _check_open(ledger, kind)
        if kind == "canary":
            return _canary(client, ledger, outdir, dry_run)
        _preflight(REVIEW_FILE if review is None else review)
        r = _Run(kind, client, ledger, schedule_seed, outdir, dry_run, n_sets, third_scorer, freeze=freeze)
        r.start()
        return r.go()


def _load(outdir):
    with open(os.path.join(outdir, "schedule.json"), encoding="utf-8") as f:
        sched = json.load(f)
    return sched, _read_jsonl(os.path.join(outdir, "episodes.jsonl"))


GATE_LABEL = "design decision, not a confirmatory result"
Y_NONE_ROOM = (0.30, 0.80)  # prereg 16b order rule (a), inclusive
MIN_NONE_DUPLICATES = 2  # rule (b)


def order_gate(sched, recs):
    """Prereg 16b order rule, per task order on the sets the plan gave it: Y per set and condition, executed duplicates
    (alloc's `duplicates`) under none and code, tests (a) room, (b) >= 2 duplicates under none, (c) Y_code != Y_none in
    some set. Decidable only when every set of the order has a scored none and code episode; the pick needs both orders
    decided (exactly one usable: it; both: shared; neither: criterion 5 fails)."""
    ok = [r for r in recs if r["ended"] in analysis.SCORED_ENDS and not r.get("void") and r.get("Y") is not None]
    out = {"label": GATE_LABEL, "orders": {}}
    for o in tc.TASK_ORDERS:
        sets = [b["set"] for b in sched["plan"] if b.get("task_order") == o]
        y = {s: {r["cond"]: r["Y"] for r in ok if r["set"] == s} for s in sets}
        full = [s for s in sets if "none" in y[s] and "code" in y[s]]
        dup = {c: sum((r.get("scores") or {}).get("duplicates") or 0 for r in ok if r["set"] in sets and r["cond"] == c)
               for c in ("none", "code")}
        g = {"sets": sets, "complete_sets": len(full), "Y": y, "duplicates": dup, "mean_Y_none": None,
             "a_room": None, "b_duplicates": None, "c_not_locked": None, "usable": None}
        if sets and len(full) == len(sets):
            g["mean_Y_none"] = sum(y[s]["none"] for s in sets) / len(sets)
            g["a_room"] = Y_NONE_ROOM[0] <= g["mean_Y_none"] <= Y_NONE_ROOM[1]
            g["b_duplicates"] = dup["none"] >= MIN_NONE_DUPLICATES
            g["c_not_locked"] = any(y[s]["code"] != y[s]["none"] for s in sets)
            g["usable"] = g["a_room"] and g["b_duplicates"] and g["c_not_locked"]
        out["orders"][o] = g
    use = {o: g["usable"] for o, g in out["orders"].items()}
    if None in use.values():
        out["picked"], out["why"] = None, "not decidable: an order is incomplete"
    elif not any(use.values()):
        out["picked"], out["why"] = None, "no usable order: criterion 5 fails, EP-1 not cleared"
    else:
        out["picked"] = "shared" if use["shared"] else "per_agent"
        out["why"] = "both usable: tie goes to shared" if all(use.values()) else "the only usable order"
    return out


def _render_gate(g):
    pf = {True: "pass", False: "fail", None: "n/a (incomplete)"}
    L = [f"order rule (prereg 16b): {g['label']}"]
    for o, x in g["orders"].items():
        L.append(f"{o}: sets {x['sets']}, {x['complete_sets']}/{len(x['sets'])} with scored none and code; "
                 f"duplicates none={x['duplicates']['none']} code={x['duplicates']['code']}; mean Y_none="
                 + ("n/a" if x["mean_Y_none"] is None else f"{x['mean_Y_none']:.3f}"))
        for s in x["sets"]:
            L.append(f"  set {s}: " + (" ".join(f"{c}={x['Y'][s][c]}" for c in sorted(x["Y"][s])) or "no scored episode"))
        L.append(f"  (a) Y_none {Y_NONE_ROOM[0]:.2f}-{Y_NONE_ROOM[1]:.2f}: {pf[x['a_room']]}; "
                 f"(b) >= {MIN_NONE_DUPLICATES} duplicates under none: {pf[x['b_duplicates']]}; "
                 f"(c) Y_code != Y_none in a set: {pf[x['c_not_locked']]}; usable: {pf[x['usable']]}")
    L.append(f"picked order: {g['picked'] or 'none'} ({g['why']}; {g['label']})")
    return L


def analyse(outdir):
    """Report text for an EP-1 or pilot output directory. A model table refuses FAKE/scripted records; a dry run is
    analysed as scripted and stamped FAKE. The canary never enters an analysis."""
    sched, recs = _load(outdir)
    if sched["kind"] == "canary":
        raise analysis.AnalysisRefused("refused: canary data never enters an analysis")
    if sched.get("freeze") and any(event.get("event") == "input_integrity"
                                  for event in _read_jsonl(os.path.join(outdir, "events.jsonl"))):
        raise analysis.AnalysisRefused("refused: a frozen input changed during EP-1")
    if any(r.get("arm") == "code" and r.get("violations_executed") for r in recs):
        raise analysis.AnalysisRefused("refused: an enforcement violation executed in the code arm")
    if any(r.get("void") == "action_boundary" for r in recs):
        raise analysis.AnalysisRefused("refused: an invalid action crossed the parser boundary")
    fake = bool(sched.get("dry_run"))
    _refuse_invalid(recs)
    if sched["kind"] in PILOTS:
        analysis._check([dict(r, episode_id="scripted:" + r["episode_id"]) if fake else r for r in recs],
                        "scripted" if fake else "model")
        L = [(FAKE if fake else "pilot: instrument check, not an estimate"), "cond  episodes  meanY"]
        for c in sorted({r["cond"] for r in recs}):
            ys = [r["Y"] for r in recs if r["cond"] == c and r["ended"] in analysis.SCORED_ENDS and not r.get("void")]
            L.append(f"{c:<16} {len(ys):>3}  " + (f"{sum(ys) / len(ys):.3f}" if ys else "n/a"))
        if sched["kind"] in ORDER_KINDS:
            L.append("exploratory, not a pre-registered contrast: mean Y by task order and arm (arms compared within an order)")
            L.append("task_order  cond  episodes  meanY")
            for o in sorted({r["task_order"] for r in recs}):
                for c in sorted({r["cond"] for r in recs}):
                    ys = [r["Y"] for r in recs if r["task_order"] == o and r["cond"] == c
                          and r["ended"] in analysis.SCORED_ENDS and not r.get("void")]
                    L.append(f"{o:<10} {c:<16} {len(ys):>3}  " + (f"{sum(ys) / len(ys):.3f}" if ys else "n/a"))
            L += _render_gate(order_gate(sched, recs))
        return "\n".join(L) + "\n"
    return (FAKE + "\n\n" if fake else "") + analysis.render(_summary(recs, fake))


# ---- dry run and CLI -------------------------------------------------------------------------------------------

def worst_case_responder(path, headers, body, n):
    """Fake Messages API reply at worst-case usage (input = request bytes, output 300). Plays the floor (all agents
    claim and work task 0), so refusals and long status lines stay in every prompt."""
    user = body["messages"][0]["content"]
    m = re.search(r"Round (\d) of 2\. You are (a\d)\.", user)
    text = "OK"
    if m:
        tasks = sorted(re.findall(r"^(\w+): sum (\d+) (\d+)$", user, re.M))  # canonical order; prompts show it shuffled
        t = tasks[0]
        text = json.dumps({"type": "claim", "item": t[0]} if m.group(1) == "1" else
                          {"type": "work", "task": t[0], "answer": int(t[1]) + int(t[2]), "name": f"{m.group(2)}-{t[0]}"})
    return 200, {"model": MODEL, "stop_reason": "end_turn", "content": [{"type": "text", "text": text}],
                 "usage": {"input_tokens": len(json.dumps(body, sort_keys=True)), "output_tokens": 300,
                           "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}}


def oracle_responder(path, headers, body, n):
    """Scripted oracle: agent aK claims and works its own task K with the right sum and the unique name rule."""
    user = body["messages"][0]["content"]
    m = re.search(r"Round (\d) of 2\. You are a(\d)\.", user)
    code, resp = worst_case_responder(path, headers, body, n)
    if m:
        # shortcut: lexical id order equals task order only below 10 tasks per set; alloc sets have 6
        t = sorted(re.findall(r"^(\w+): sum (\d+) (\d+)$", user, re.M))[int(m.group(2))]
        text = json.dumps({"type": "claim", "item": t[0]} if m.group(1) == "1" else
                          {"type": "work", "task": t[0], "answer": int(t[1]) + int(t[2]),
                           "name": alloc.NAME_RULE.format(agent=f"a{m.group(2)}", task=t[0])})
        resp["content"][0]["text"] = text
    return code, resp
def _fakeclaude():
    spec = importlib.util.spec_from_file_location("murmuration_fakeclaude", os.path.join(ROOT, "tests", "fakeclaude.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _dry_sheet(path):
    from datetime import datetime, timezone
    with open(PRICE_SHEET, encoding="utf-8") as f:
        data = json.load(f)
    data["fetched"] = datetime.now(timezone.utc).date().isoformat()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return spend.PriceSheet.load(path)


def dry_run_all(outdir, schedule_seed=0, review=None, third_scorer=None, n_sets=None):
    """Canary, pilot and the whole EP-1 schedule against the loopback fake server at worst-case usage. No key, no network."""
    os.makedirs(outdir, exist_ok=True)
    ldir = os.path.join(outdir, "ledger")
    sheet = _dry_sheet(os.path.join(outdir, "price-sheet.json"))
    srv, url, _seen = _fakeclaude().start(worst_case_responder)
    out = {"stamp": FAKE}
    try:
        for kind in KINDS:
            led = spend.Ledger(os.path.join(ldir, f"{kind}.jsonl"), sheet, batch=kind)
            cl = bc.ClaudeClient("sk-ant-dry-run-not-a-key-0000", led, url, allow_host="127.0.0.1")
            out[kind] = run_batch(kind, cl, led, schedule_seed, os.path.join(outdir, kind), True, review=review,
                                  third_scorer=third_scorer, n_sets=None if kind == "canary" else n_sets)
    finally:
        srv.shutdown()
    out["ep1_report"] = analyse(os.path.join(outdir, "ep1"))
    out["pilot2_report"] = analyse(os.path.join(outdir, "pilot2"))
    out["pilot3_report"] = analyse(os.path.join(outdir, "pilot3"))
    out["pilot4_report"] = analyse(os.path.join(outdir, "pilot4"))
    out["bracket"] = _bracket(outdir, schedule_seed, review, third_scorer)
    out["verdict"] = "GREEN" if out["bracket"]["floor_fails"] and out["bracket"]["oracle_passes"] else "VOID"
    return out
def _bracket(outdir, schedule_seed, review, third_scorer):
    """Scripted FLOOR (naive agents, no card: all claim and work task 0) and ORACLE through the full driver path (canary then
    ep1, one task set, its own ledger directory) on the fake server. Every floor episode must score exactly FLOOR_Y and
every oracle episode exactly ORACLE_Y, all three arms complete; anything else makes the dry run VOID."""
    sheet = _dry_sheet(os.path.join(outdir, "bracket-price-sheet.json"))
    ys = {}
    for name, responder in (("floor", worst_case_responder), ("oracle", oracle_responder)):
        srv, url, _seen = _fakeclaude().start(responder)
        try:
            for kind in ("canary", "ep1"):
                led = spend.Ledger(os.path.join(outdir, "bracket", name, "ledger", f"{kind}.jsonl"), sheet, batch=kind)
                cl = bc.ClaudeClient("sk-ant-dry-run-not-a-key-0000", led, url, allow_host="127.0.0.1")
                run_batch(kind, cl, led, schedule_seed, os.path.join(outdir, "bracket", name, kind), True, review=review,
                          third_scorer=third_scorer, n_sets=None if kind == "canary" else 1)
        finally:
            srv.shutdown()
        ys[name] = [r["Y"] for r in _read_jsonl(os.path.join(outdir, "bracket", name, "ep1", "episodes.jsonl"))]
    def exact(name, want):  # one complete episode per arm, each at the exact expected value
        rs = _read_jsonl(os.path.join(outdir, "bracket", name, "ep1", "episodes.jsonl"))
        return len(rs) == len(BASE_CONDS) and all(r["ended"] == "complete" and r["Y"] == want for r in rs)
    return {"floor_Y": ys["floor"], "oracle_Y": ys["oracle"], "expected": {"floor": FLOOR_Y, "oracle": ORACLE_Y},
            "floor_fails": exact("floor", FLOOR_Y), "oracle_passes": exact("oracle", ORACLE_Y)}


def cli(a):
    """`ep1` subcommands. canary/pilot/run refuse unless --i-have-owner-confirm AND MURMURATION_EP1_KEY is set; the key
    is read here only. Raises ValueError for a refusal (the caller prints it as an error, exit 2)."""
    c = a.ep1_cmd
    if c == "analyse":
        print(analyse(a.outdir))
        return 0
    if c == "dry-run":
        out = dry_run_all(a.out_dir, a.schedule_seed, review=a.review)
        print(json.dumps(out, sort_keys=True, indent=1, default=str))
        return 0 if out["verdict"] == "GREEN" else 1  # VOID: the floor/oracle bracket did not hold
    if not a.i_have_owner_confirm:
        raise ValueError("refused: a paid run needs the explicit --i-have-owner-confirm flag")
    key = os.environ.get(KEY_ENV)
    if not key:
        raise ValueError(f"refused: set {KEY_ENV} in the environment (the key is never taken from a file or argument)")
    if a.ledger_dir and not a.base_url:
        raise ValueError("refused: --ledger-dir is a test hook that needs --base-url")
    if a.base_url and not a.ledger_dir:  # G0-2R3 N10: a fake run must never settle a batch in the real pinned ledger
        raise ValueError("refused: --base-url is a test hook that needs --ledger-dir")
    kind = {"canary": "canary", "pilot": "pilot", "pilot2": "pilot2", "pilot3": "pilot3", "pilot4": "pilot4", "run": "ep1"}[c]
    if kind == "ep1" and not a.base_url:
        _check_freeze()  # Before the Ledger constructor can create its directory.
    try:
        sheet = spend.PriceSheet.load(a.price_sheet or PRICE_SHEET)
        led = spend.Ledger(os.path.join(a.ledger_dir or spend.PILOT_LEDGER_DIR, f"{kind}.jsonl"), sheet, batch=kind)
        if a.base_url:  # test hook: the client itself refuses any non-loopback host other than api.anthropic.com
            from urllib.parse import urlsplit
            cl = bc.ClaudeClient(key, led, a.base_url, allow_host=urlsplit(a.base_url).hostname)
        else:
            cl = bc.ClaudeClient(key, led)
        out = run_batch(kind, cl, led, a.schedule_seed, a.out_dir, dry_run=bool(a.base_url), review=a.review)
    except (spend.SpendError, bc.EpisodeVoided, bc.EpisodeCapExceeded) as e:
        raise ValueError(f"refused: {type(e).__name__}: {e}") from None
    print(json.dumps(out, sort_keys=True, indent=1, default=str))
    return 0
