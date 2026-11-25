"""Offline L4-C harness: night loop around vreplay, the seven arms of protocol section 3, a token meter,
false share and cost per pass (prereg/R2-L4-C-protocol.md sections 3, 6, 12, 16, decisions D1-D6; open
item L4-O9). Standard library plus murmuration (vreplay, readouts) and the scripted scorer only.

No parameter the protocol leaves OPEN has a default: daily error rate, nights per chain, store size,
cap, tolerance, tokenizer, rendering policy, search attempts and the per-check and per-reading charges are
required keyword arguments (including `shuffle_seed`). A missing one raises TypeError; a bool, NaN or negative one raises ValueError.
No model call is made here: `model(kind, prompt)` is supplied by the caller (kind is "work", "search" or
"dream"; "work" and "search" return a string or None, "dream" returns a list of note dicts).

Layout. A note or episode is {"id", "text", "sources": [source_id]} (the shape lab.l4c_scripted_scoring
reads). A chain is {"id", "nights": [{"episodes": [note, ...], "tasks": [{"id", "source", "prompt"}]}]}.
Each night the team works from the store left by the night before (section 4); then the consolidation pass
reads that day's log and writes a new store. Truth is supplied only to the scoring functions, after a run.

Readings (each is a decision the protocol states, or the narrowest reading of it):
- Equal budget: every arm gets the same token `cap` per chain. A call is made only if its prompt still
  fits; its completion may overshoot, so realized tokens can differ under the cap (LC:43; D1).
- Charge rule (L4-O2): every model call in the day work and the consolidation pass counts for every arm;
  each scripted re-check costs `check_tokens` and each controller reading `reading_tokens`, charged to
  the arm that runs it.
- Controller R is caller-supplied: `readings(night, store) -> (recovery_time, R)`, either None (D6). It is
  meant to be the first-generation reading; readouts.reproduction_number returns the descendant share
  (section 12) and is not used here.
- Payment: a replay night first spends on the dream call, then needs room for every re-check plus the
  reading; if they do not fit, the night is withheld (store and rung unchanged) and the dream tokens stay
  spent. A night can therefore spend on a dream and keep nothing; it is counted in `withheld_nights`.
- Withholding is counted in three separate figures: `withheld_tasks` (a work prompt that did not fit, task
  left unanswered), `withheld_searches` (a task whose search stopped because the next attempt did not fit)
  and `withheld_nights` (a night's dream, gate or write that did not fit or could not be paid for). None of
  them is the section 9 step 7 unused-budget figure; that is `unused_tokens` = cap - realized tokens
  (negative when a completion overshot the cap).
- Seeds: night t of a run uses seed `_night_seed(seed, t, tag)`, an integer from the first 8 bytes of
  sha256(f"{tag}:{seed}:{t}") with tag "errors" or "shuffle". Consecutive seeds or nights therefore do not
  give shifted copies of the same random stream, and the error and shuffle draws are independent. The
  planted errors use the same mixed seed in every arm of a chain.
- Placebo: texts are permuted among the night's episodes with random.Random(that mixed seed). A permutation
  can be the identity (always so below two episodes, and by chance otherwise); every night whose dream ran
  with shuffled texts equal to the originals is listed in the run's `unshuffled`. A night whose dream was
  skipped for budget is not listed; it is in `withheld_nights`.
- A chain belongs to the setting it starts at (D6, section 16 step 3): `setting_of`.
- Use count of a note or raw episode = tasks so far whose source it names; retention is by use (vreplay.retain).
"""
from fractions import Fraction
import hashlib
import math
import random

from murmuration import readouts, vreplay

from lab.l4c_scripted_scoring import score

# Section 3 table, rows in order (protocol lines 73-79).
ARMS = ("replay", "search", "gated_write", "plain_dream", "placebo_dream", "raw_history", "no_memory")


def _int(x, name, low=0):
    if isinstance(x, bool) or not isinstance(x, int) or x < low:
        raise ValueError(f"{name} must be an integer of at least {low}")
    return x


def _rate(x, name):
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not (isinstance(x, int) or math.isfinite(x)) \
            or not 0 <= x <= 1:
        raise ValueError(f"{name} must be a number in [0, 1]")
    return x


def _fn(x, name):
    if not callable(x):
        raise ValueError(f"{name} must be callable")
    return x


def _tokens(tokenizer, text):
    if not isinstance(text, str):
        raise ValueError("only text is metered")
    return _int(tokenizer(text), "tokenizer result")


def realized_tokens(ledger, tokenizer):
    """Realized total tokens of a ledger: tokenizer(prompt) + tokenizer(completion) per model call, plus the
    explicit charges ({"kind": "check" | "reading", "tokens": n}). Recomputed from the texts every time."""
    _fn(tokenizer, "tokenizer")
    total = 0
    for e in ledger:
        if e["kind"] in ("check", "reading"):
            total += _int(e["tokens"], "charge")
        else:
            total += _tokens(tokenizer, e["prompt"]) + _tokens(tokenizer, e["completion"])
    return total


def false_share(resident, truth):
    """False resident notes over resident notes at the close of the last night, as an exact Fraction.
    None (undefined, not zero) for an empty store or a note whose source has no truth (LC:38-41)."""
    counts = score(tasks=[], submissions={}, resident=resident, truth=truth)["resident_counts"]
    if not resident or counts["unknown_truth"]:
        return None
    return Fraction(counts["false"], len(resident))


def cost_per_pass(tokens, task_counts):
    """Tokens spent over tasks passed, exact; None when nothing passed or a submitted answer has no label."""
    _int(tokens, "tokens")
    if task_counts["unknown_truth"] or not task_counts["passed"]:
        return None
    return Fraction(tokens, task_counts["passed"])


def token_ratio(replay_tokens, reference_tokens):
    """C2: realized tokens of verified replay over the reference arm, the gated write (D1). None if 0."""
    _int(replay_tokens, "replay_tokens")
    _int(reference_tokens, "reference_tokens")
    return Fraction(replay_tokens, reference_tokens) if reference_tokens else None


def recovery_reading(series, shock, *, tol):
    """readouts.recovery_time with the tolerance required (L4-O13 leaves it OPEN)."""
    if isinstance(tol, bool) or not isinstance(tol, (int, float)) or not math.isfinite(tol) or tol < 0:
        raise ValueError("tol must be a finite non-negative number")
    return readouts.recovery_time(series, shock, tol=tol)


def plant_errors(episodes, *, error_rate, seed, corrupt):
    """Each episode independently gets `corrupt(text)` with probability error_rate (seeded, reproducible)."""
    _rate(error_rate, "error_rate")
    _int(seed, "seed", -2**63)
    _fn(corrupt, "corrupt")
    rng = random.Random(seed)
    return [{**e, "text": corrupt(e["text"])} if rng.random() < error_rate else dict(e) for e in episodes]


def setting_of(run):
    """The setting a chain belongs to: the rung it starts at, whatever rung it ends at (D6)."""
    return run["start_rung"]


def group_by_setting(runs):
    out = {}
    for r in runs:
        out.setdefault(setting_of(r), []).append(r)
    return out


class _State:
    def __init__(self, cap, tokenizer):
        self.cap, self.tokenizer, self.ledger, self._total = cap, tokenizer, [], 0
        self.withheld_tasks = self.withheld_searches = self.withheld_nights = 0

    def total(self):  # running sum, equal to realized_tokens(self.ledger, self.tokenizer)
        return self._total

    def fits(self, prompt, extra=0):
        return self.total() + _tokens(self.tokenizer, prompt) + extra <= self.cap

    def spend(self, kind, tokens):
        self.ledger.append({"kind": kind, "tokens": tokens})
        self._total += tokens

    def call(self, model, kind, prompt, render):
        out = model(kind, prompt)
        # The completion of a dream is its rendered notes; of work and search, the answer text (None is empty).
        done = render(out) if kind == "dream" else (out or "")
        self.ledger.append({"kind": kind, "prompt": prompt, "completion": done})
        self._total += _tokens(self.tokenizer, prompt) + _tokens(self.tokenizer, done)
        return out


def _uses(uses, items, tasks):
    sources = [t["source"] for t in tasks]
    for it in {i["id"]: i for i in items}.values():
        uses[it["id"]] = uses.get(it["id"], 0) + sum(it["sources"][0] == s for s in sources)


def _cap_store(store, uses, store_size):
    keep = set(vreplay.retain([n["id"] for n in store], uses, store_size))
    return [n for n in store if n["id"] in keep]


def _night_seed(seed, night, tag):
    return int.from_bytes(hashlib.sha256(f"{tag}:{seed}:{night}".encode()).digest()[:8], "big")


def _shuffle_texts(episodes, seed):
    rng = random.Random(seed)
    texts = [e["text"] for e in episodes]
    rng.shuffle(texts)
    return [{**e, "text": t} for e, t in zip(episodes, texts)]


def run_arm(arm, chain, *, model, check, tokenizer, render, cap, nights, store_size, error_rate, corrupt,
            rung0, readings, check_tokens, reading_tokens, search_attempts, seed, shuffle_seed):
    """One arm on one chain at equal token cap. Returns the execution record (no truth involved):
    {"arm", "chain", "start_rung", "rungs", "ledger", "tokens", "unused_tokens",
    "withheld_tasks", "withheld_searches", "withheld_nights", "nights": [{"submissions",
    "resident", "tasks"}], "unshuffled"}. `rungs` is the rung after each night (the controller runs in "replay" only)."""
    if arm not in ARMS:
        raise ValueError(f"arm must be one of {ARMS}")
    for name, fn in (("model", model), ("check", check), ("tokenizer", tokenizer), ("render", render),
                     ("corrupt", corrupt), ("readings", readings)):
        _fn(fn, name)
    cap, store_size = _int(cap, "cap"), _int(store_size, "store_size")
    nights, rung0 = _int(nights, "nights", 1), _int(rung0, "rung0")
    check_tokens, reading_tokens = _int(check_tokens, "check_tokens"), _int(reading_tokens, "reading_tokens")
    search_attempts, seed = _int(search_attempts, "search_attempts", 1), _int(seed, "seed", -2**63)
    shuffle_seed = _int(shuffle_seed, "shuffle_seed", -2**63)
    _rate(error_rate, "error_rate")
    if not isinstance(chain, dict) or not isinstance(chain.get("nights"), list) or len(chain["nights"]) != nights:
        raise ValueError("chain must hold exactly `nights` nights")

    st = _State(cap, tokenizer)
    store, raw, history, uses = [], [], [], {}
    rung, last = rung0, (None, None)
    rungs, rows, unshuffled = [], [], []
    for t, day in enumerate(chain["nights"]):
        episodes = plant_errors(day["episodes"], error_rate=error_rate, seed=_night_seed(seed, t, "errors"), corrupt=corrupt)
        tasks = day["tasks"]
        context = render(history) if arm == "raw_history" else "" if arm in ("no_memory", "search") else render(store)
        # Day work, from the store the last night left.
        subs = dict.fromkeys(task["id"] for task in tasks)
        for task in tasks:
            if arm == "search":
                for k in range(search_attempts):
                    prompt = f"{task['prompt']}\nattempt {k}"
                    if not st.fits(prompt):
                        st.withheld_searches += 1
                        break
                    ans = st.call(model, "search", prompt, render)
                    if ans is not None:
                        subs[task["id"]] = ans
                        break
            else:
                prompt = f"{task['prompt']}\n{context}"
                if not st.fits(prompt):
                    st.withheld_tasks += 1
                    continue
                subs[task["id"]] = st.call(model, "work", prompt, render)
        _uses(uses, store + raw, tasks)
        # Night consolidation.
        if arm == "raw_history":
            history = history + episodes
        elif arm in ("no_memory", "search"):
            pass  # no store, no consolidation
        elif arm == "gated_write":
            if st.total() + check_tokens * len(episodes) <= cap:
                for _ in episodes:
                    st.spend("check", check_tokens)
                store = _cap_store(store + vreplay.gate(episodes, check), uses, store_size)
            else:
                st.withheld_nights += 1
        else:  # replay, plain_dream, placebo_dream
            new = episodes
            if arm == "placebo_dream":
                new = _shuffle_texts(episodes, _night_seed(shuffle_seed, t, "shuffle"))
            batch = vreplay.replay_batch(raw if arm == "replay" else store, new)
            prompt = f"rung={rung}\n{render(batch)}"
            if not st.fits(prompt):
                st.withheld_nights += 1
            else:
                if arm == "placebo_dream" and [e["text"] for e in new] == [e["text"] for e in episodes]:
                    unshuffled.append(t)  # the dream ran on the original order
                claims = st.call(model, "dream", prompt, render)
                if arm == "replay":
                    # Whole-gate reservation: no partially checked night is kept.
                    if st.total() + check_tokens * len(claims) + reading_tokens <= cap:
                        for _ in claims:
                            st.spend("check", check_tokens)
                        store = vreplay.gate(claims, check)
                        keep = set(vreplay.retain([x["id"] for x in batch], uses, store_size))
                        raw = [e for e in batch if e["id"] in keep]
                        now = readings(t, store)
                        st.spend("reading", reading_tokens)
                        rung, last = vreplay.next_strength(rung, last, now), now
                    else:
                        st.withheld_nights += 1
                else:
                    store = claims
                store = _cap_store(store, uses, store_size)
        rungs.append(rung)
        rows.append({"submissions": subs, "resident": [dict(n) for n in store],
                     "tasks": [(task["id"], task["source"]) for task in tasks]})
    return {"arm": arm, "chain": chain["id"], "start_rung": rung0, "rungs": rungs, "ledger": st.ledger,
            "tokens": st.total(), "cap": cap, "unused_tokens": cap - st.total(),
            "withheld_tasks": st.withheld_tasks, "withheld_searches": st.withheld_searches,
            "withheld_nights": st.withheld_nights, "nights": rows,
            "unshuffled": unshuffled}


def run_all(chain, **cfg):
    """All seven arms on one chain at the same cap, same planted errors (same seed), in section 3 order."""
    return {arm: run_arm(arm, chain, **cfg) for arm in ARMS}


def score_run(run, truth_by_night, tokenizer):
    """Grade a run with truth supplied after dispatch. Tokens are recounted from the ledger."""
    if not isinstance(truth_by_night, (list, tuple)) or len(truth_by_night) != len(run["nights"]):
        raise ValueError("one truth map per night required")
    counts = dict.fromkeys(("passed", "incorrect", "unanswered", "unknown_truth"), 0)
    for row, truth in zip(run["nights"], truth_by_night):
        got = score(tasks=row["tasks"], submissions=row["submissions"], resident=row["resident"],
                    truth=truth)["task_counts"]
        for k in counts:
            counts[k] += got[k]
    tokens = realized_tokens(run["ledger"], tokenizer)
    final = run["nights"][-1]["resident"]
    return {"arm": run["arm"], "setting": setting_of(run), "rungs": run["rungs"], "tokens": tokens,
            "task_counts": counts, "false_share": false_share(final, truth_by_night[-1]),
            "cost_per_pass": cost_per_pass(tokens, counts)}


def compare_arms(runs, truth_by_night, tokenizer):
    """Per-arm scores plus C2 (replay tokens over gated-write tokens, D1) and C3 (replay cost per pass below
    search's; None if either is undefined)."""
    if set(runs) != set(ARMS):
        raise ValueError("runs must hold exactly the seven arms")
    out = {arm: score_run(runs[arm], truth_by_night, tokenizer) for arm in ARMS}
    r, s = out["replay"]["cost_per_pass"], out["search"]["cost_per_pass"]
    out["c2"] = token_ratio(out["replay"]["tokens"], out["gated_write"]["tokens"])
    out["c3"] = None if r is None or s is None else r < s
    return out
