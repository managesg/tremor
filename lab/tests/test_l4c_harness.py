import json
import math
import os
import subprocess
import sys
import unittest
from fractions import Fraction
from unittest import mock

from tremor import vreplay
from lab import l4c_harness as h

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

WORLD = {"a": "a ok", "b": "b ok", "c": "c ok"}
TRUTH = [dict(WORLD), dict(WORLD)]


def note(i, source):
    return {"id": i, "text": WORLD[source], "sources": [source]}


# Two nights. Night 0 logs two episodes and asks about a; night 1 logs nothing and asks about b.
CHAIN = {"id": "c1", "nights": [
    {"episodes": [note("e1", "a"), note("e2", "b")], "tasks": [{"id": "t0", "source": "a", "prompt": "Q a"}]},
    {"episodes": [], "tasks": [{"id": "t1", "source": "b", "prompt": "Q b"}]},
]}


def render(notes):
    return "\n".join(f"{n['id']}|{n['sources'][0]}|{n['text']}" for n in notes)


def model(kind, prompt):
    lines = [x.split("|") for x in prompt.split("\n") if x.count("|") == 2]
    if kind == "dream":  # a faithful rewrite of whatever it was shown
        return [{"id": "n-" + i, "text": t, "sources": [s]} for i, s, t in lines]
    if kind == "search":  # the first attempt finds nothing, the second reads the source
        return None if prompt.endswith("attempt 0") else WORLD[prompt.split()[1]]
    src = prompt.split()[1]
    hits = [t for _, s, t in lines if s == src]
    return hits[-1] if hits else None


def check(claim):
    return claim["text"] == WORLD[claim["sources"][0]]


def words(text):
    return len(text.split())


def cfg(**over):
    base = dict(model=model, check=check, tokenizer=words, render=render, cap=1000, nights=2, store_size=5,
                error_rate=0, corrupt=lambda t: t + "!", rung0=2, readings=lambda t, store: (None, None),
                check_tokens=3, reading_tokens=1, search_attempts=2, seed=0, shuffle_seed=0)
    base.update(over)
    return base


def fixture():
    runs = h.run_all(CHAIN, **cfg(error_rate=0.5, seed=3))
    out = h.compare_arms(runs, TRUTH, words)
    return {k: (str(v) if isinstance(v, Fraction) else v) for k, v in out.items()
            if k in ("c2", "c3")} | {a: {k: str(v) for k, v in out[a].items()} for a in h.ARMS}


class Meter(unittest.TestCase):
    def test_realized_tokens_hand_computed(self):
        ledger = [{"kind": "work", "prompt": "a b c", "completion": "d e"},
                  {"kind": "check", "tokens": 4}, {"kind": "reading", "tokens": 1}]
        self.assertEqual(h.realized_tokens(ledger, words), 3 + 2 + 4 + 1)
        self.assertEqual(h.realized_tokens(ledger, len), 5 + 3 + 4 + 1)  # tokenizer is the caller's

    def test_meter_refuses_bad_tokenizer_output(self):
        ledger = [{"kind": "work", "prompt": "a", "completion": "b"}]
        for bad in (lambda t: True, lambda t: -1, lambda t: 1.5, lambda t: float("nan")):
            with self.assertRaises(ValueError):
                h.realized_tokens(ledger, bad)
        with self.assertRaises(ValueError):
            h.realized_tokens(ledger, "words")


class Scoring(unittest.TestCase):
    def test_false_share_exact(self):
        res = [note("x", "a"), {**note("y", "a"), "text": "stale"}, note("z", "b"), {**note("w", "b"), "text": "no"}]
        self.assertEqual(h.false_share(res, WORLD), Fraction(1, 2))
        self.assertEqual(h.false_share(res[:1], WORLD), Fraction(0))

    def test_false_share_undefined_is_not_zero(self):
        self.assertIsNone(h.false_share([], WORLD))
        self.assertIsNone(h.false_share([note("x", "a")], {"b": "b ok"}))  # no truth for the source

    def test_cost_per_pass(self):
        c = {"passed": 4, "incorrect": 1, "unanswered": 1, "unknown_truth": 0}
        self.assertEqual(h.cost_per_pass(10, c), Fraction(5, 2))
        self.assertIsNone(h.cost_per_pass(10, {**c, "passed": 0}))
        self.assertIsNone(h.cost_per_pass(10, {**c, "unknown_truth": 1}))
        with self.assertRaises(ValueError):
            h.cost_per_pass(True, c)

    def test_token_ratio(self):
        self.assertEqual(h.token_ratio(21, 14, reference_unused=5), Fraction(3, 2))
        self.assertIsNone(h.token_ratio(5, 0, reference_unused=5))
        with self.assertRaises(ValueError):
            h.token_ratio(-1, 4, reference_unused=5)
        with self.assertRaises(TypeError):
            h.token_ratio(21, 14)

    def test_token_ratio_is_undefined_when_the_reference_hit_the_cap(self):
        for unused in (0, -3):  # at the cap, or overshot by a completion
            self.assertIsNone(h.token_ratio(21, 14, reference_unused=unused))
        self.assertEqual(h.token_ratio(21, 14, reference_unused=1), Fraction(3, 2))


class Arms(unittest.TestCase):
    def runs(self, **over):
        return h.run_all(CHAIN, **cfg(**over))

    def test_seven_arms_in_section_3_order(self):
        self.assertEqual(h.ARMS, ("replay", "search", "gated_write", "plain_dream", "placebo_dream",
                                  "raw_history", "no_memory"))
        self.assertEqual(list(self.runs()), list(h.ARMS))

    def test_hand_computed_tokens(self):
        r = self.runs(rung0=2)
        # replay: work 2 + dream 5+4 + 2 checks of 3 + reading 1 = 18; night 1: work 6+2, dream 5+4, 6, 1 = 24.
        self.assertEqual(r["replay"]["tokens"], 42)
        self.assertEqual(r["gated_write"]["tokens"], 16)   # 2 + 6 checks, then 6 + 2
        self.assertEqual(r["search"]["tokens"], 20)        # two attempts per task, 4 words each, answer 2
        self.assertEqual(r["no_memory"]["tokens"], 4)      # prompts "Q a\n" and "Q b\n", empty answers
        for arm in h.ARMS:
            self.assertLessEqual(r[arm]["tokens"], 1000)

    def test_no_memory_and_raw_history_have_no_store(self):
        r = self.runs()
        self.assertEqual(r["no_memory"]["nights"][-1]["resident"], [])
        self.assertEqual(r["raw_history"]["nights"][-1]["resident"], [])
        # raw history reads the whole log in context on night 1: "Q b" + e1, e2 lines = 6 words
        self.assertEqual(r["raw_history"]["ledger"][1]["prompt"], "Q b\ne1|a|a ok\ne2|b|b ok")
        self.assertEqual(r["no_memory"]["ledger"][1]["prompt"], "Q b\n")

    def test_equal_cap_withholds_instead_of_overspending_prompts(self):
        r = self.runs(cap=3)
        self.assertGreater(r["replay"]["withheld_nights"], 0)
        self.assertEqual(r["replay"]["nights"][-1]["resident"], [])
        for arm in h.ARMS:  # every prompt that was sent fit under the cap when it was sent
            self.assertLessEqual(r[arm]["tokens"], 3 + 2 * 2)

    def test_gate_decides_replay_false_share(self):
        r = self.runs(error_rate=1)  # every day-log episode is corrupted
        s = h.compare_arms(r, TRUTH, words)
        self.assertIsNone(s["replay"]["false_share"])           # gate dropped all: empty store, undefined
        self.assertEqual(s["gated_write"]["false_share"], None)  # same, nothing passed the re-check
        self.assertEqual(s["plain_dream"]["false_share"], Fraction(1))  # ungated dream keeps the errors
        self.assertEqual(s["placebo_dream"]["false_share"], Fraction(1))

    def test_placebo_on_single_line_episodes_changes_nothing(self):
        r = self.runs(seed=0)
        texts = lambda arm: [(n["sources"][0], n["text"]) for n in r[arm]["nights"][0]["resident"]]
        self.assertEqual(texts("plain_dream"), texts("placebo_dream"))
        self.assertEqual(r["placebo_dream"]["unshuffled"], [[0, "e1"], [0, "e2"]])

    def test_same_errors_for_every_arm(self):
        r = self.runs(error_rate=0.5, seed=4)
        dream = next(e for e in r["plain_dream"]["ledger"] if e["kind"] == "dream")
        expected = render(h.plant_errors(CHAIN["nights"][0]["episodes"], error_rate=0.5,
                                         seed=h._night_seed(4, 0, "errors"), corrupt=lambda t: t + "!"))
        self.assertEqual(dream["prompt"].split("\n", 1)[1], expected)
        for arm in ("replay", "placebo_dream"):  # the other dreaming arms are shown the same count of episodes
            other = next(e for e in r[arm]["ledger"] if e["kind"] == "dream")
            self.assertEqual(len(other["prompt"].split("\n")), len(dream["prompt"].split("\n")))

    def test_store_size_caps_resident_notes(self):
        r = self.runs(store_size=1)
        self.assertEqual(len(r["gated_write"]["nights"][0]["resident"]), 1)
        self.assertEqual(len(r["plain_dream"]["nights"][0]["resident"]), 1)

    def test_compare_arms_c2_and_c3(self):
        s = h.compare_arms(self.runs(), TRUTH, words)
        self.assertEqual(s["replay"]["task_counts"]["passed"], 1)   # night 0 had no memory, night 1 answered
        self.assertEqual(s["search"]["task_counts"]["passed"], 2)
        self.assertEqual(s["c2"], Fraction(42, 16))
        self.assertEqual(s["cap_hit"], dict.fromkeys(h.ARMS, False))
        self.assertEqual(s["search"]["cost_per_pass"], Fraction(10))
        self.assertEqual(s["replay"]["cost_per_pass"], Fraction(42))
        self.assertIs(s["c3"], False)


class Controller(unittest.TestCase):
    SEQ = [(5, 0.2), (6, 0.2), (6, 0.3)]  # night 1 only recovery rises, night 2 only R rises

    def run3(self, **over):
        chain = {"id": "c3", "nights": CHAIN["nights"] + [{"episodes": [], "tasks": []}]}
        return h.run_arm("replay", chain, **cfg(nights=3, rung0=3, readings=lambda t, s: self.SEQ[t], **over))

    def test_lowers_when_either_reading_rises(self):
        self.assertEqual(self.run3()["rungs"], [3, 2, 1])
        self.assertEqual(self.run3()["start_rung"], 3)

    def test_mutant_both_rise_is_caught(self):
        def both(rung, last, now):
            return max(rung - 1, 0) if all(b > a for a, b in zip(last, now) if a is not None) and None not in last \
                else rung
        with mock.patch.object(vreplay, "next_strength", both):
            self.assertNotEqual(self.run3()["rungs"], [3, 2, 1])

    def test_missing_reading_leaves_rung(self):
        r = h.run_arm("replay", CHAIN, **cfg(rung0=2, readings=lambda t, s: (None, None)))
        self.assertEqual(r["rungs"], [2, 2])

    def test_rung_never_below_zero_and_never_rises(self):
        r = h.run_arm("replay", CHAIN, **cfg(rung0=0, readings=lambda t, s: (t, t)))
        self.assertEqual(r["rungs"], [0, 0])

    def test_only_replay_runs_the_controller(self):
        calls = []
        h.run_all(CHAIN, **cfg(readings=lambda t, s: calls.append(t) or (None, None)))
        self.assertEqual(calls, [0, 1])

    def test_reading_is_charged_to_replay_only(self):
        kinds = {a: [e["kind"] for e in r["ledger"]] for a, r in h.run_all(CHAIN, **cfg()).items()}
        self.assertEqual(kinds["replay"].count("reading"), 2)
        for arm in h.ARMS[1:]:
            self.assertNotIn("reading", kinds[arm])

    def test_recovery_reading_requires_tol(self):
        self.assertEqual(h.recovery_reading([1, 1, 5, 3, 1.1], 2, tol=0.2), 2)
        with self.assertRaises(TypeError):
            h.recovery_reading([1, 5], 1)
        for bad in (True, -0.1, float("nan"), "x"):
            with self.assertRaises(ValueError):
                h.recovery_reading([1, 5], 1, tol=bad)


class Mutants(unittest.TestCase):
    def test_dropped_check_charge_is_caught(self):
        real = h._State.spend

        def drop(self, kind, tokens):
            if kind != "check":
                real(self, kind, tokens)
        base = h.run_arm("replay", CHAIN, **cfg())["tokens"]
        self.assertEqual(base, 42)
        with mock.patch.object(h._State, "spend", drop):
            self.assertEqual(h.run_arm("replay", CHAIN, **cfg())["tokens"], 42 - 12)

    def test_dropped_gate_is_caught(self):
        with mock.patch.object(vreplay, "gate", lambda claims, chk: list(claims)):
            r = h.run_arm("replay", CHAIN, **cfg(error_rate=1))
        self.assertEqual(h.false_share(r["nights"][-1]["resident"], WORLD), Fraction(1))  # real gate: None

    def test_swapped_setting_is_caught(self):
        chain = {"id": "c3", "nights": CHAIN["nights"] + [{"episodes": [], "tasks": []}]}
        low = h.run_arm("replay", chain, **cfg(nights=3, rung0=3, readings=lambda t, s: Controller.SEQ[t]))
        flat = h.run_arm("replay", chain, **cfg(nights=3, rung0=1))
        self.assertEqual({k: len(v) for k, v in h.group_by_setting([low, flat]).items()}, {3: 1, 1: 1})
        self.assertEqual(h.setting_of(low), 3)  # it ends at rung 1 but belongs to setting 3
        with mock.patch.object(h, "setting_of", lambda run: run["rungs"][-1]):
            self.assertEqual(len(h.group_by_setting([low, flat])[1]), 2)  # mutant merges the two settings

    def test_stored_tokens_match_recount(self):
        for run in h.run_all(CHAIN, **cfg()).values():
            self.assertEqual(run["tokens"], h.realized_tokens(run["ledger"], words))
            self.assertEqual(h.score_run(run, TRUTH, words)["tokens"], run["tokens"])


class Refusals(unittest.TestCase):
    OPEN = ("model", "check", "tokenizer", "render", "cap", "nights", "store_size", "error_rate", "corrupt",
            "rung0", "readings", "check_tokens", "reading_tokens", "search_attempts", "seed", "shuffle_seed")

    def test_every_parameter_is_required(self):
        for name in self.OPEN:
            args = cfg()
            del args[name]
            with self.subTest(name), self.assertRaises(TypeError):
                h.run_arm("replay", CHAIN, **args)

    def test_bad_numbers_refused(self):
        bad = {"cap": (True, -1, 1.5, float("nan")), "nights": (True, 0, -2, 2.0), "store_size": (True, -1, 1.0),
               "error_rate": (True, -0.1, 1.1, float("nan"), float("inf")), "rung0": (True, -1, 0.5),
               "check_tokens": (True, -1, float("nan")), "reading_tokens": (True, -1, 2.5),
               "search_attempts": (True, 0, -1), "seed": (True, 1.5, "0"), "shuffle_seed": (True, 0.5, "0")}
        for name, values in bad.items():
            for v in values:
                with self.subTest(name=name, value=v), self.assertRaises(ValueError):
                    h.run_arm("replay", CHAIN, **cfg(**{name: v}))

    def test_bad_callables_and_arm(self):
        for name in ("model", "check", "tokenizer", "render", "corrupt", "readings"):
            with self.subTest(name), self.assertRaises(ValueError):
                h.run_arm("replay", CHAIN, **cfg(**{name: None}))
        with self.assertRaises(ValueError):
            h.run_arm("learned_consolidator", CHAIN, **cfg())

    def test_nights_must_match_chain(self):
        with self.assertRaises(ValueError):
            h.run_arm("replay", CHAIN, **cfg(nights=3))
        with self.assertRaises(ValueError):
            h.run_arm("replay", {"id": "x", "nights": "ab"}, **cfg(nights=2))

    def test_plant_errors_refusals(self):
        eps = CHAIN["nights"][0]["episodes"]
        for bad in (True, -0.5, 2, float("nan")):
            with self.assertRaises(ValueError):
                h.plant_errors(eps, error_rate=bad, seed=0, corrupt=str)
        with self.assertRaises(TypeError):
            h.plant_errors(eps, seed=0, corrupt=str)
        self.assertEqual(h.plant_errors(eps, error_rate=0, seed=0, corrupt=str.upper), eps)
        self.assertTrue(all(e["text"].endswith("!") for e in
                            h.plant_errors(eps, error_rate=1, seed=0, corrupt=lambda t: t + "!")))
        self.assertEqual(h.plant_errors(eps, error_rate=0.5, seed=9, corrupt=str.upper),
                         h.plant_errors(eps, error_rate=0.5, seed=9, corrupt=str.upper))

    def test_scoring_refusals(self):
        runs = h.run_all(CHAIN, **cfg())
        with self.assertRaises(ValueError):
            h.compare_arms({k: v for k, v in runs.items() if k != "search"}, TRUTH, words)
        with self.assertRaises(ValueError):
            h.score_run(runs["replay"], TRUTH[:1], words)
        with self.assertRaises(ValueError):
            h.false_share([{"id": "x", "text": "t"}], WORLD)  # a note with no source

    def test_truth_does_not_change_execution(self):
        runs = h.run_all(CHAIN, **cfg())
        before = json.dumps(runs, sort_keys=True)
        a = h.score_run(runs["replay"], TRUTH, words)
        b = h.score_run(runs["replay"], [{"a": "other", "b": "other"}] * 2, words)
        self.assertNotEqual(a["task_counts"], b["task_counts"])
        self.assertEqual(json.dumps(runs, sort_keys=True), before)


def chain_of(nights, cid="cx"):
    return {"id": cid, "nights": [{"episodes": e, "tasks": [{"id": f"t{i}-{n}", "source": s, "prompt": f"Q {s}"}
                                                           for n, s in enumerate(t)]}
                                  for i, (e, t) in enumerate(nights)]}


def dreams(run):
    return [e["prompt"].split("\n") for e in run["ledger"] if e["kind"] == "dream"]


def _json_dream(kind, prompt):  # a faithful rewrite of the JSON-rendered batch
    if kind == "dream":
        return [{**c, "id": "n-" + c["id"]} for c in json.loads(prompt.split("\n", 1)[1])]
    return None


JSON = dict(model=_json_dream, render=json.dumps)


def shown(run):
    """The batch each night's dream was shown (JSON render), as lists of episodes."""
    return [json.loads(e["prompt"].split("\n", 1)[1]) for e in run["ledger"] if e["kind"] == "dream"]


def synthetic(arm, tokens, passed):
    """A settled run with a known charge and `passed` correct answers, for boundary checks on the scorer."""
    subs = {f"t{i}": WORLD["a"] for i in range(passed)}
    tasks = [(f"t{i}", "a") for i in range(2)]
    return {"arm": arm, "start_rung": 0, "rungs": [0], "tokens": tokens, "cap": 99, "unused_tokens": 0, "withheld_tasks": 0, "withheld_searches": 0,
            "withheld_nights": 0, "unshuffled": [], "cap_hit": False,
            "ledger": [{"kind": "check", "tokens": tokens}],
            "nights": [{"submissions": {**dict.fromkeys(("t0", "t1")), **subs}, "resident": [], "tasks": tasks}]}


class Strict(unittest.TestCase):
    """Each test is written to fail on a named mutant of l4c_harness (checked by mutating a copy)."""

    def test_placebo_arm_shuffles_the_night_it_is_shown(self):  # M1
        eps = lambda t: [{"id": f"q{t}{i}", "text": "\n".join(f"{i}l{j}" for j in range(4)), "sources": ["abc"[i % 3]]}
                         for i in range(6)]
        chain = chain_of([(eps(t), []) for t in range(4)])
        plain = h.run_arm("plain_dream", chain, **cfg(nights=4, **JSON))
        placebo = h.run_arm("placebo_dream", chain, **cfg(nights=4, **JSON))
        orig = {e["id"]: e for e in eps(0)}
        a, b = shown(plain)[0], shown(placebo)[0]
        self.assertEqual(a, list(orig.values()))
        self.assertNotEqual(a, b)
        for x in b:  # same id, same source, same set of lines: only the order is destroyed
            self.assertEqual(x["sources"], orig[x["id"]]["sources"])
            self.assertEqual(sorted(x["text"].split("\n")), sorted(orig[x["id"]]["text"].split("\n")))
        self.assertTrue(any(x["text"] != orig[x["id"]]["text"] for x in b))

    def test_placebo_keeps_each_note_to_its_own_episode_lines(self):  # M1, swapped texts
        eps = [{"id": f"q{i}", "text": f"{i}a\n{i}b\n{i}c", "sources": [f"s{i}"]} for i in range(6)]
        r = h.run_arm("placebo_dream", chain_of([(eps, [])]), **cfg(nights=1, **JSON))
        for x in shown(r)[0]:  # each note still carries its own episode's lines, none of another's
            own = next(e for e in eps if e["id"] == x["id"])
            self.assertEqual(set(x["text"].split("\n")), set(own["text"].split("\n")))

    def test_placebo_seed_is_the_callers(self):  # M1, (c)
        eps = [{"id": f"q{i}", "text": "\n".join(f"{i}l{j}" for j in range(5)), "sources": ["a"]} for i in range(6)]
        big = chain_of([(eps, [])] * 3)
        seen = {json.dumps(shown(h.run_arm("placebo_dream", big, **cfg(nights=3, shuffle_seed=k, **JSON)))[0])
                for k in range(5)}
        self.assertGreater(len(seen), 1)  # the argument, not a constant, drives the permutation

    def test_placebo_permutation_changes_from_night_to_night(self):  # mutant: shuffle_seed alone, no night
        eps = [{"id": f"q{i}", "text": "\n".join(f"{i}l{j}" for j in range(5)), "sources": ["a"]} for i in range(6)]
        r = h.run_arm("placebo_dream", chain_of([(eps, [])] * 4), **cfg(nights=4, store_size=100, **JSON))
        new_part = [json.dumps(d[-6:]) for d in shown(r)]  # the day's six episodes close each batch
        self.assertGreater(len(set(new_part)), 1)

    def test_unshuffled_lists_episodes_that_could_not_move(self):
        a = {"id": "A", "text": "x\ny", "sources": ["a"]}
        b = {"id": "B", "text": "z", "sources": ["b"]}
        same = lambda k: h._shuffle_lines([a, b], h._night_seed(k, 0, "shuffle"))[0][0]["text"] == "x\ny"
        ident = next(k for k in range(100) if same(k))
        moved = next(k for k in range(100) if not same(k))
        chain = chain_of([([a, b], []), ([], [])])
        r = h.run_arm("placebo_dream", chain, **cfg(nights=2, shuffle_seed=ident))
        self.assertEqual(r["unshuffled"], [[0, "A"], [0, "B"]])  # identity order, and one line cannot move
        r = h.run_arm("placebo_dream", chain, **cfg(nights=2, shuffle_seed=moved))
        self.assertEqual(r["unshuffled"], [[0, "B"]])             # A really moved
        self.assertEqual(h.run_arm("replay", chain, **cfg(nights=2))["unshuffled"], [])
        # A skipped dream is not reported: cap 2 leaves no room for night 0's prompt.
        r = h.run_arm("placebo_dream", chain, **cfg(nights=2, cap=2, shuffle_seed=ident))
        self.assertEqual((r["unshuffled"], r["withheld_nights"]), ([], 1))

    def test_search_stops_at_first_answer(self):  # M2
        def answer_at(k):
            return lambda kind, prompt: WORLD[prompt.split()[1]] if prompt.endswith(f"attempt {k}") else None
        for k in (0, 1):
            r = h.run_arm("search", CHAIN, **cfg(model=answer_at(k), search_attempts=3, nights=2))
            self.assertEqual([e["kind"] for e in r["ledger"]], ["search"] * (k + 1) * 2)
            self.assertEqual(r["nights"][1]["submissions"], {"t1": "b ok"})
        r = h.run_arm("search", CHAIN, **cfg(model=lambda kind, p: None, search_attempts=3))
        self.assertEqual(len(r["ledger"]), 6)  # no answer: every attempt is spent, and no more

    def test_c3_is_strict_at_the_bound(self):  # M3
        def runs(replay_tokens, search_tokens):
            r = {a: synthetic(a, 10, 1) for a in h.ARMS}
            r["replay"], r["search"] = synthetic("replay", replay_tokens, 1), synthetic("search", search_tokens, 1)
            return h.compare_arms(r, [WORLD], words)
        self.assertIs(runs(10, 10)["c3"], False)  # equal cost per pass does not beat equal-token search
        self.assertIs(runs(9, 10)["c3"], True)
        self.assertIs(runs(11, 10)["c3"], False)
        self.assertEqual(runs(10, 10)["replay"]["cost_per_pass"], Fraction(10))

    def test_scores_last_night_store_and_last_night_truth(self):  # M4
        row = lambda resident: {"submissions": {}, "tasks": [], "resident": resident}
        mk = lambda i, text: {"id": i, "text": text, "sources": ["a"]}
        run = {"arm": "plain_dream", "start_rung": 1, "rungs": [1, 1, 1], "ledger": [], "tokens": 0, "cap": 9,
               "unused_tokens": 9, "withheld_tasks": 0, "withheld_searches": 0, "withheld_nights": 0, "unshuffled": [],
               "nights": [row([mk("x", "a0")]), row([mk("x", "a1")]), row([mk("y", "a2"), mk("z", "bad")])]}
        truth = [{"a": "a0"}, {"a": "a1"}, {"a": "a2"}]
        self.assertEqual(h.score_run(run, truth, words)["false_share"], Fraction(1, 2))
        # night 0's store against night 2's truth would read 1; night 2's store against night 0's truth, also 1.

    def test_planted_errors_differ_every_night(self):  # M14
        chain = chain_of([([{"id": f"g{t}{i}", "text": WORLD["a"], "sources": ["a"]} for i in range(6)], [])
                          for t in range(4)])
        c = cfg(nights=4, error_rate=0.5, seed=1, store_size=100)
        r = h.run_arm("gated_write", chain, **c)
        alive = lambda rows: {n["id"] for n in rows}
        expected = [[e["id"] for e in h.plant_errors(night["episodes"], error_rate=0.5, seed=h._night_seed(1, t, "errors"),
                                                      corrupt=c["corrupt"]) if e["text"] == WORLD["a"]]
                    for t, night in enumerate(chain["nights"])]
        positions = [{i for i in range(6) if f"g{t}{i}" in expected[t]} for t in range(4)]
        self.assertGreater(len({frozenset(p) for p in positions}), 1)  # the fixture does vary night to night
        self.assertEqual(alive(r["nights"][-1]["resident"]), {i for night in expected for i in night})

    def test_raw_retention_is_capped_by_use_and_replayed_not_the_store(self):  # M5 M6 M10
        chain = chain_of([([note("p1", "a"), note("p2", "b"), note("p3", "c")], []),
                          ([note("a1", "a"), note("a2", "b")], ["b"]), ([], [])])
        r = h.run_arm("replay", chain, **cfg(nights=3, store_size=2))
        d = dreams(r)
        # Night 0: no use anywhere, the later arrivals p2, p3 are kept (not p1, p2 by id).
        # Night 1 replays those raw episodes (not the n- notes); its task read b, so p2 and a2 are used once
        # and the later arrival a2 wins no tie against nothing: both are kept, p3 and a1 are dropped.
        self.assertEqual(d[1], ["rung=2", "p2|b|b ok", "p3|c|c ok", "a1|a|a ok", "a2|b|b ok"])
        self.assertEqual(d[2], ["rung=2", "p2|b|b ok", "a2|b|b ok"])

    def test_full_store_ties_go_to_the_later_arrival_not_to_the_id(self):  # M15
        # store_size 1: the old note's id sorts first, so only id order would keep it.
        chain = chain_of([([note("a-old", "a")], []), ([note("z-new", "b")], [])])
        r = h.run_arm("gated_write", chain, **cfg(nights=2, store_size=1))
        self.assertEqual([n["id"] for n in r["nights"][0]["resident"]], ["a-old"])
        self.assertEqual([n["id"] for n in r["nights"][1]["resident"]], ["z-new"])
        chain = chain_of([([note("z-old", "a")], []), ([note("a-new", "b")], [])])  # and the reverse id order
        r = h.run_arm("gated_write", chain, **cfg(nights=2, store_size=1))
        self.assertEqual([n["id"] for n in r["nights"][1]["resident"]], ["a-new"])
        self.assertEqual(h.run_arm("plain_dream", chain, **cfg(nights=2, store_size=1))["nights"][1]["resident"][0]["id"],
                         "n-a-new")

    def test_new_episodes_are_counted_as_used_when_they_arrive(self):  # M16
        # Tonight's task reads b: the new b note has one use, the old a note none, whatever the ids say.
        chain = chain_of([([note("a-old", "a")], []), ([note("z-new", "b")], ["b"])])
        r = h.run_arm("gated_write", chain, **cfg(nights=2, store_size=1))
        self.assertEqual([n["id"] for n in r["nights"][1]["resident"]], ["z-new"])
        # An old used note still beats a newer unused one.
        chain = chain_of([([note("z-old", "a")], ["a"]), ([note("a-new", "b")], [])])
        r = h.run_arm("gated_write", chain, **cfg(nights=2, store_size=1))
        self.assertEqual([n["id"] for n in r["nights"][1]["resident"]], ["z-old"])

    def test_new_raw_episodes_are_counted_as_used_on_the_night_they_arrive(self):  # M16, replay
        # Both arrive tonight; tonight's task reads b. Neither id order nor recency picks z-used.
        chain = chain_of([([note("z-used", "b"), note("a-other", "a")], ["b"]), ([], [])])
        r = h.run_arm("replay", chain, **cfg(nights=2, store_size=1))
        self.assertEqual(dreams(r)[1], ["rung=2", "z-used|b|b ok"])

    def test_every_source_of_a_multi_source_note_counts_as_a_use(self):  # M17
        multi = {"id": "z-multi", "text": WORLD["a"], "sources": ["a", "b"]}
        chain = chain_of([([multi, note("a-one", "a")], ["b"])])
        r = h.run_arm("gated_write", chain, **cfg(nights=1, store_size=1))
        self.assertEqual([n["id"] for n in r["nights"][0]["resident"]], ["z-multi"])
        # The same note is used once per matching task, not once per source.
        chain = chain_of([([multi, note("m2", "a")], ["a", "b"])])
        r = h.run_arm("gated_write", chain, **cfg(nights=1, store_size=1))
        self.assertEqual([n["id"] for n in r["nights"][0]["resident"]], ["z-multi"])

    def test_gated_write_accumulates_and_fits_exactly(self):  # M7 M11
        chain = chain_of([([note("g00", "a"), note("g01", "b")], []), ([note("g10", "c")], []),
                          ([note("g20", "a"), note("g21", "b")], [])])
        r = h.run_arm("gated_write", chain, **cfg(nights=3, store_size=100))
        self.assertEqual([len(n["resident"]) for n in r["nights"]], [2, 3, 5])
        exact = h.run_arm("gated_write", chain_of([([note("g00", "a"), note("g01", "b")], []), ([], []), ([], [])]),
                          **cfg(nights=3, cap=6))
        self.assertEqual((exact["tokens"], exact["withheld_nights"], len(exact["nights"][0]["resident"])), (6, 0, 2))
        over = h.run_arm("gated_write", chain_of([([note("g00", "a"), note("g01", "b")], []), ([], []), ([], [])]),
                         **cfg(nights=3, cap=5))
        self.assertEqual((over["tokens"], over["withheld_nights"], over["nights"][0]["resident"]), (0, 1, []))

    def test_a_prompt_that_exactly_fits_is_sent(self):  # M9
        r = h.run_arm("no_memory", CHAIN, **cfg(cap=2))
        self.assertEqual((len(r["ledger"]), r["withheld_tasks"], r["withheld_nights"]), (1, 1, 0))  # "Q a\n" is 2 tokens: fits; "Q b\n" does not

    def test_replay_pays_for_checks_and_reading_before_keeping_a_night(self):  # M8 M12 (a)
        chain = chain_of([([note("e1", "a"), note("e2", "b")], []), ([], []), ([], [])])
        # Dream: prompt 5 + completion 4 = 9; two checks of 3 and one reading of 1 make 16.
        fit = h.run_arm("replay", chain, **cfg(nights=3, cap=16))
        self.assertEqual(len(fit["nights"][0]["resident"]), 2)
        self.assertEqual([e["kind"] for e in fit["ledger"]][:4], ["dream", "check", "check", "reading"])
        self.assertEqual(fit["tokens"], 16)
        short = h.run_arm("replay", chain, **cfg(nights=3, cap=15))  # checks alone fit (15), the reading does not
        self.assertEqual(short["nights"][0]["resident"], [])
        self.assertNotIn("check", [e["kind"] for e in short["ledger"]])
        self.assertEqual(short["ledger"][0]["kind"], "dream")  # the dream was paid for and nothing was kept
        self.assertGreaterEqual(short["withheld_nights"], 1)
        tight = h.run_arm("replay", chain, **cfg(nights=3, cap=14))  # the checks do not fit either
        self.assertEqual(tight["nights"][0]["resident"], [])
        self.assertNotIn("check", [e["kind"] for e in tight["ledger"]])

    def test_rung_reaches_the_model(self):  # M13
        chain = {"id": "c3", "nights": CHAIN["nights"] + [{"episodes": [], "tasks": []}]}
        r = h.run_arm("replay", chain, **cfg(nights=3, rung0=3, readings=lambda t, s: Controller.SEQ[t]))
        self.assertEqual([d[0] for d in dreams(r)], ["rung=3", "rung=3", "rung=2"])
        self.assertEqual(r["rungs"], [3, 2, 1])

    def test_withholding_has_separate_counters_and_unused_budget(self):
        r = h.run_arm("search", CHAIN, **cfg(cap=4, model=lambda kind, p: None, search_attempts=3))
        self.assertEqual((r["withheld_searches"], r["withheld_tasks"], r["withheld_nights"]), (2, 0, 0))
        self.assertEqual((r["tokens"], r["unused_tokens"]), (4, 0))  # one 4-word attempt, then nothing fits
        r = h.run_arm("no_memory", CHAIN, **cfg(cap=3))
        self.assertEqual((r["withheld_tasks"], r["withheld_searches"], r["withheld_nights"]), (1, 0, 0))
        self.assertEqual(r["unused_tokens"], 3 - r["tokens"])
        r = h.run_arm("plain_dream", CHAIN, **cfg(cap=2))
        self.assertEqual((r["withheld_tasks"], r["withheld_nights"]), (1, 2))
        self.assertNotIn("withheld", r)

    def test_c2_is_undefined_when_the_gated_write_hit_the_cap(self):  # M18
        r = Arms().runs(cap=16)
        self.assertEqual((r["gated_write"]["tokens"], r["gated_write"]["unused_tokens"]), (16, 0))
        self.assertIs(r["gated_write"]["cap_hit"], True)
        s = h.compare_arms(r, TRUTH, words)
        self.assertIsNone(s["c2"])  # 16 over 16 would be a finite ratio set by the cap, not by the arm
        self.assertIs(s["cap_hit"]["gated_write"], True)
        self.assertIs(s["gated_write"]["cap_hit"], True)
        free = h.compare_arms(Arms().runs(), TRUTH, words)
        self.assertEqual(free["c2"], Fraction(42, 16))
        runs = {a: synthetic(a, 10, 1) for a in h.ARMS}
        runs["gated_write"] = {**synthetic("gated_write", 99, 1), "cap": 99}
        self.assertIsNone(h.compare_arms(runs, [WORLD], words)["c2"])

    def test_total_is_a_running_sum(self):
        calls = []
        st = h._State(100, lambda t: calls.append(t) or len(t.split()))
        for _ in range(3):
            st.call(model, "work", "Q a\n", render)
        st.spend("check", 3)
        before = len(calls)
        self.assertEqual(st.total(), 3 * 2 + 3)
        self.assertEqual(len(calls), before)  # reading the total does not re-tokenize the ledger
        self.assertEqual(st.total(), h.realized_tokens(st.ledger, words))


class Determinism(unittest.TestCase):
    def test_across_hash_seeds(self):
        outs = set()
        for hs in ("0", "1", "12345", "random"):
            env = dict(os.environ, PYTHONHASHSEED=hs)
            env["PYTHONPATH"] = os.pathsep.join(
                [os.path.join(REPO, "src"), os.path.join(REPO, "lab"), os.path.join(REPO, "tests"), REPO])
            p = subprocess.run(
                [sys.executable, "-B", "-c",
                 "import json; from lab.tests import test_l4c_harness as t; print(json.dumps(t.fixture(), sort_keys=True))"],
                cwd=REPO, env=env, capture_output=True, text=True, check=True)
            outs.add(p.stdout)
        self.assertEqual(len(outs), 1)
        self.assertEqual(json.loads(outs.pop()), json.loads(json.dumps(fixture(), sort_keys=True)))

    def test_no_nan_in_reports(self):
        s = h.compare_arms(h.run_all(CHAIN, **cfg()), TRUTH, words)
        for arm in h.ARMS:
            self.assertFalse(isinstance(s[arm]["tokens"], float) and math.isnan(s[arm]["tokens"]))


if __name__ == "__main__":
    unittest.main()
