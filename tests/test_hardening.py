"""Class-level hardening of cell.py and router.py: every test generates many seeded inputs per bug class
(numbers, model identity, names and paths) instead of replaying the one example a report named."""
import hashlib
import itertools
import json
import math
import os
import random
import re
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tremor import cell, router  # noqa: E402

POL = {"allow": ["read"], "deny": [], "max_tokens": 1000, "max_seconds": 10}
SPEC = {"id": "t1", "class": "extract", "payload": {"text": "b a"}, "cell": "w"}
DROP = object()  # a field removed from a mutated bundle


def hostile_numbers(rnd, n=150):
    """Everything that must never pass as a finite non-negative number, plus generated variants."""
    fixed = [float("nan"), float("inf"), float("-inf"), -1, -0.5, -1e-9, 1e13, 10**13, 10**400, -(10**400), 1e308,
             "5", "nan", "inf", "1e3", " 7", "0x10", True, False, None, [], [1], {}, {"a": 1}, b"5", (1,), 1j, object()]
    gen = []
    for _ in range(n):
        c = rnd.choice(("neg", "huge", "str", "special"))
        x = rnd.uniform(1e-9, 1e6)
        gen.append(-x if c == "neg" else 10 ** rnd.randint(13, 500) if c == "huge" else str(x) if c == "str"
                   else rnd.choice([float("nan"), float("inf"), float("-inf")]))
    return fixed + gen


def good_numbers(rnd, n=100):
    return [1, 2, 10**12, 0.001, 1e-9] + [rnd.uniform(1e-6, 1e9) for _ in range(n)] + [rnd.randint(1, 10**9) for _ in range(n)]


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = self.tmp.name

    def mk(self, cid, kind="stub", model="scripted", pol=POL):
        return cell.create(os.path.join(self.d, cid), cid, kind, model, pol)


class NumberClass(Base):
    def test_validator_refuses_every_hostile_value_and_accepts_good_ones(self):
        rnd = random.Random(1)
        for v in hostile_numbers(rnd):
            for pos in (False, True):
                with self.assertRaises(ValueError, msg=repr(v)):
                    cell.num(v, "x", positive=pos)
        for v in good_numbers(rnd):
            self.assertEqual(cell.num(v, "x", positive=True), v)
        self.assertEqual(cell.num(0, "x"), 0)
        with self.assertRaises(ValueError):
            cell.num(0, "x", positive=True)

    def test_policy_create_and_load_refuse_hostile_limits(self):
        rnd = random.Random(2)
        for key in ("max_tokens", "max_seconds"):
            for i, v in enumerate(hostile_numbers(rnd, 40)):
                with self.assertRaises(ValueError, msg=(key, repr(v))):
                    cell.create(os.path.join(self.d, "c"), "c", "stub", "scripted", dict(POL, **{key: v}))
                p = self.mk(f"l{key[4]}{i}")
                with open(os.path.join(p, "policy.json"), "w") as f:  # json.dump writes NaN/Infinity literally
                    json.dump(dict(POL, **{key: v}), f, default=repr)
                with self.assertRaises(ValueError, msg=(key, repr(v))):
                    cell.load(p)
        with self.assertRaises(ValueError):
            cell.create(os.path.join(self.d, "z"), "z", "stub", "scripted", dict(POL, allow="read"))

    def test_spec_budget_and_other_numbers_refused_at_every_entry(self):
        rnd = random.Random(3)
        c = self.mk("s")
        n = 0
        for v in hostile_numbers(rnd, 40):
            for field in ({"budget": {"tokens": v}}, {"budget": {"seconds": v}}, {"extra_seconds": v}, {"version": v}):
                n += 1
                with self.assertRaises(ValueError, msg=(field, repr(v))):
                    router.run_task(dict(SPEC, id=f"i{n}", **field), c)
        for bad in (None, [], "x", 5, [1]):  # the budget itself must be an object
            with self.assertRaises(ValueError):
                router.run_task(dict(SPEC, id="b", budget=bad), c)
        for bad in (None, float("nan")):  # present-but-null limits do not mean "absent"
            with self.assertRaises(ValueError):
                router.run_task(dict(SPEC, id="b", budget={"tokens": bad}), c)
        self.assertEqual(os.listdir(os.path.join(c)) and sorted(os.listdir(c)), ["cell.json", "policy.json"])  # nothing ran

    def test_nan_budget_cannot_loosen_the_policy_cap(self):
        c = self.mk("s", pol=dict(POL, max_tokens=1))
        with self.assertRaises(ValueError):
            router.run_task(dict(SPEC, budget={"tokens": float("nan")}), c)
        self.assertEqual(router.run_task(dict(SPEC, id="t2"), c)["status"], "budget_exceeded")

    def test_good_budgets_only_tighten(self):
        rnd = random.Random(4)
        c = self.mk("s", "scripted_strong")
        for i, v in enumerate(good_numbers(rnd, 30)):
            b = router.run_task(dict(SPEC, id=f"g{i}", budget={"tokens": v, "seconds": 5}), c)
            tokens = b["cost"]["tokens_in"] + b["cost"]["tokens_out"]
            self.assertEqual(b["status"], "done" if tokens <= min(v, 1000) else "budget_exceeded")


PREFIXES = ("", "", "anthropic/", "Anthropic/", "us.anthropic.", "eu.anthropic.", "models/", "azure/", "aws/",
            "anthropic:", "bedrock/", "openrouter/anthropic/", "vertex_ai/", "claude.")
SUFFIXES = ("", "-latest", ":latest", ":0", "-20261001", "@20261001", "-2026-10-01", "_20261001", "-latest:0",
            "@2026-11-01", "_2026-11-01", "-preview", "-001", "-0", "-thinking", ".", "/", "-v1:0", "-v2")


def spellings(base, rnd):
    """One random equivalent spelling of a canonical id like 'claude-haiku-5-5'."""
    s = base
    if rnd.random() < .5:
        s = s.replace("5-", rnd.choice(("5.", "5_", "5-")))
    if rnd.random() < .3:
        s = s.replace("-", rnd.choice("._"))
    if rnd.random() < .5:
        s = "".join(chr(ord(c) + 0xFEE0) if c.isascii() and c.isalnum() and rnd.random() < .5 else c for c in s)
    s = "".join(c + (rnd.choice("\u200b\u2060\ufeff\u00ad\u200d\u202e\u200f") if rnd.random() < .15 else "") for c in s)
    s = "".join(rnd.choice("\u2011\u2010\u2212\u2013\u2014-") if c == "-" else c for c in s)
    s = "".join(c.upper() if rnd.random() < .4 else c for c in s)
    s = rnd.choice(PREFIXES) + s + rnd.choice(SUFFIXES)
    return rnd.choice(("", " ", "\t", "\n")) + s + rnd.choice(("", " ", "\r\n", "\u200b"))


# R3's end-to-end bypasses of the old denylist: each named the worker's model, and each passed as independent
R3_SPELLINGS = ("claude.haiku-5-5", "claude.haiku.5.5", "claude_haiku_5_5", "models/claude-haiku-5-5",
                "azure/claude-haiku-5-5", "aws/claude-haiku-5-5", "anthropic:claude-haiku-5-5",
                "claude-haiku-5-5@2026-11-01", "claude-haiku-5-5_2026-11-01", "claude-haiku-5-5-preview",
                "claude-haiku-5-5-001", "claude-haiku-5-5-0", "claude-haiku-5-5-thinking", "claude-haiku-5-5.",
                "claude-haiku-5-5/", "bedrock/us.anthropic.claude-haiku-5-5-v1:0")

# near misses: another version, another family, two families, homoglyphs, ids outside the allowlist
NEAR_MISSES = ("claude-haiku-5-4", "claude-haiku-5", "claude-haiku-5-50", "claude-haiku-05-05", "claude-haiku-55",
               "claude-haiku-6-5", "claude-h\u0430iku-5-5", "claude-\u043epus-5-5", "claude-haiku-5-5-opus-5-5",
               "scripted-haiku-5-5", "local-opus-5-5", "claude-sonnet-5-2", "claude-fable-5-5", "haiku",
               "claude", "gpt-6-1-sol", "k3-1", "m", "glm-5-3", "claude-haiku-4-5", "claude-3-5-haiku",
               "claude-5-5-haiku", "sonnet-5-2-fable-5-5")  # reordered ids are refused, never guessed


class ModelClass(Base):
    BASES = {"claude-haiku-5-5": "haiku-5-5", "claude-opus-5-5": "opus-5-5", "claude-sonnet-5-5": "sonnet-5-5",
             "claude-fable-5-2": "fable-5-2"}

    def test_equivalent_spellings_map_to_one_allowlisted_key(self):
        rnd = random.Random(5)
        for base, key in self.BASES.items():
            for _ in range(600):
                sp = spellings(base, rnd)
                self.assertEqual(cell.model_key(sp), key, repr(sp))
        for sp in R3_SPELLINGS:
            self.assertEqual(cell.model_key(sp), "haiku-5-5", sp)

    def test_near_misses_and_unknown_ids_are_refused(self):
        for bad in NEAR_MISSES:
            with self.assertRaises(ValueError, msg=bad):
                cell.model_key(bad)

    def test_negative_fuzz_never_maps_outside_the_table_or_to_the_wrong_family(self):
        """Generated ids: a family word, a version (right or wrong) and noise. Each is refused, or maps to the
        key whose family word and version it carries; nothing maps outside MODEL_FAMILIES."""
        rnd = random.Random(8)
        fams = {"haiku": "5-5", "sonnet": "5-5", "opus": "5-5", "fable": "5-2"}
        words = ("claude", "anthropic", "models", "us", "eu", "preview", "latest", "thinking", "beta", "x", "pro")
        n_ok = n_refused = 0
        for _ in range(3000):
            w = rnd.choice(sorted(fams))
            ver = rnd.choice((fams[w], fams[w], "5-4", "4-5", "5", "5-50", "05-05", "6-5", "5-2", "5-5", "55"))
            pre = "-".join(rnd.choice(words) for _ in range(rnd.randint(0, 2)))
            post = "-".join(rnd.choice(words + ("0", "001", "20261001", "v1")) for _ in range(rnd.randint(0, 2)))
            sid = rnd.choice("-._/:").join(x for x in (pre, w, ver, post) if x)
            pairs = [(w, ver)]
            if rnd.random() < .15:  # a second family word and version
                w2, v2 = rnd.choice(sorted(set(fams) - {w})), fams[rnd.choice(sorted(fams))]
                sid, pairs = f"{sid}-{w2}-{v2}", pairs + [(w2, v2)]
            named = {f"{a}-{b}" for a, b in pairs if fams[a] == b}  # the allowlisted families the id spells out
            try:
                k = cell.model_key(sid)
            except ValueError:
                n_refused += 1
                self.assertFalse(len(pairs) == 1 and named, sid)  # a clean id of an allowlisted family maps
                continue
            n_ok += 1
            self.assertIn(k, cell.MODEL_FAMILIES, sid)
            self.assertIn(k, named, sid)  # only a family and exact version the id carries, never a near miss
        self.assertGreater(n_ok, 300)
        self.assertGreater(n_refused, 300)

    def test_distinct_families_stay_distinct(self):
        keys = {cell.model_key(x) for x in ("claude-haiku-5-5", "claude-opus-5-5", "claude-sonnet-5-5",
                                             "claude-fable-5-2", "local-qwen", "scripted-stub")}
        self.assertEqual(keys, set(cell.MODEL_FAMILIES))

    def test_unusable_ids_refused(self):
        for bad in ("", " ", "\u200b", "\x00", "a\x00b", "claude\x00", "claude-haiku-5-5\x00", "\u043c\u043e\u0434\u0435\u043b\u044c",
                    "\u65e5\u672c", "claude haiku", "a b", "caf\u00e9", None, 5, b"x", ["a"], "anthropic/", "-latest", "\u2011",
                    "m", "gpt-6-1-sol"):
            with self.assertRaises(ValueError, msg=repr(bad)):
                cell.model_key(bad)
            with self.assertRaises(ValueError, msg=repr(bad)):
                cell.create(os.path.join(self.d, "q"), "q", "stub", bad, POL)

    def test_independence_check_catches_equivalent_spellings(self):
        rnd = random.Random(6)
        w = self.mk("w", model="claude-haiku-5-5")
        spec = dict(SPEC, id="ind")
        bundle = router.run_task(spec, w)
        for i in range(40):
            v = self.mk(f"v{i}", "scripted_strong", spellings("claude-haiku-5-5", rnd))
            with self.assertRaises(router.IndependenceError):
                router.verify(spec, bundle, self.d, verifier_dir=v)
        self.assertTrue(router.verify(spec, bundle, self.d, verifier_dir=self.mk("ok", "scripted_strong", "claude-opus-5-5")))

    def test_r3_spellings_end_to_end_never_pass_as_independent(self):
        """kills: the denylist normaliser (7 of 7 of these verified True as 'independent')."""
        w = self.mk("w", model="claude-haiku-5-5")
        spec = dict(SPEC, id="r3")
        bundle = router.run_task(spec, w)
        for i, sp in enumerate(R3_SPELLINGS + NEAR_MISSES):
            try:
                v = self.mk(f"x{i}", "scripted_strong", sp)
            except ValueError:
                continue  # refused at create: fail closed
            with self.assertRaises(router.IndependenceError, msg=sp):
                router.verify(spec, bundle, self.d, verifier_dir=v)

    def test_scripted_and_local_cells_are_one_family_each(self):
        for a, b in (("scripted-a", "Scripted_B"), ("local-qwen", "local-llama-3")):
            w = self.mk("w" + a[0], model=a)
            spec = dict(SPEC, id="fam" + a[0], cell="w" + a[0])
            bnd = router.run_task(spec, w)
            with self.assertRaises(router.IndependenceError):
                router.verify(spec, bnd, self.d, verifier_dir=self.mk("v" + a[0], "scripted_strong", b))
            self.assertTrue(router.verify(spec, bnd, self.d, verifier_dir=self.mk("o" + a[0], "scripted_strong", "claude-fable-5-2")))

    def test_single_normaliser(self):
        self.assertIs(router.model_key, cell.model_key)
        self.assertIs(router.MODEL_FAMILIES, cell.MODEL_FAMILIES)


def oracle_valid(s):
    return isinstance(s, str) and re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.\-]{0,127}", s, re.ASCII) is not None and ".." not in s


class NameAndPathClass(Base):
    def test_valid_name_matches_strict_ascii_oracle(self):
        rnd = random.Random(7)
        alpha = list("abcXYZ019_.-/\\ \n\r\t\x00٣ａé") + ["..", "a.b", "\n"]
        n_valid = 0
        for _ in range(4000):
            s = "".join(rnd.choice(alpha) for _ in range(rnd.randint(0, 8)))
            self.assertEqual(cell.valid_name(s), oracle_valid(s), repr(s))
            if oracle_valid(s):
                n_valid += 1
                for tail in ("\n", "\r\n", "\x00", " "):
                    self.assertFalse(cell.valid_name(s + tail), repr(s + tail))
        self.assertGreater(n_valid, 100)
        self.assertFalse(cell.valid_name("a" * 129))
        for bad in (None, 5, b"a", ["a"]):
            self.assertFalse(cell.valid_name(bad))

    def test_trailing_newline_ids_refused_everywhere(self):
        c = self.mk("s")
        for bad in ("x\n", "\nx", "x\r"):
            with self.assertRaises(ValueError):
                router.run_task(dict(SPEC, id=bad), c)
            with self.assertRaises(ValueError):
                cell.create(os.path.join(self.d, "n"), bad, "stub", "scripted", POL)
        self.assertEqual(os.listdir(c) and sorted(os.listdir(c)), ["cell.json", "policy.json"])

    def test_join_refuses_every_traversal_shape(self):
        root = os.path.join(self.d, "r")
        os.makedirs(root)
        for bad in ("..", "../x", "a/b", "/abs", "", "x\n", "a\\b", ".", "\x00", "a/../b"):
            with self.assertRaises(ValueError, msg=repr(bad)):
                cell.join(root, bad)
        self.assertTrue(cell.join(root, "outbox", "t.json").endswith(os.path.join("outbox", "t.json")))

    def test_symlinks_inside_a_cell_are_refused(self):
        out = os.path.join(self.d, "outside")
        os.makedirs(out)
        for target in ("log.jsonl", "outbox", "log.head", "cell.json"):
            c = self.mk("c" + target.replace(".", ""))
            dest = os.path.join(out, "t" + target)
            if target == "outbox":
                os.makedirs(dest)
            else:
                open(dest, "w").write("{}")
                if target.startswith("cell"):
                    open(dest, "w").write(open(os.path.join(c, "cell.json")).read())
            if os.path.lexists(os.path.join(c, target)):
                os.remove(os.path.join(c, target))
            os.symlink(dest, os.path.join(c, target))
            with self.assertRaises(ValueError, msg=target):
                router.run_task(dict(SPEC, id="s"), c)
            self.assertEqual(os.listdir(out).count("s.json"), 0)
            self.assertFalse(os.path.exists(os.path.join(dest, "s.json")) if target == "outbox" else False)
        self.assertEqual(open(os.path.join(out, "tlog.jsonl")).read(), "{}")  # untouched
        link = os.path.join(self.d, "lnk")
        os.symlink(self.mk("real"), link)
        with self.assertRaises(ValueError):
            router.run_task(dict(SPEC, id="s"), link)

    def test_bundle_overwrite_refused_unless_versioned(self):
        c = self.mk("s")
        b1 = router.run_task(SPEC, c)
        path = os.path.join(c, "outbox", "t1.json")
        before = open(path).read()
        with self.assertRaises(ValueError):
            router.run_task(SPEC, c)
        self.assertEqual(open(path).read(), before)
        self.assertEqual(cell.log_count(c), 1)  # the refused run did not log either
        b2 = router.run_task(dict(SPEC, version=2), c)
        self.assertTrue(os.path.exists(os.path.join(c, "outbox", "t1.v2.json")))
        self.assertNotEqual(b1["spec_sha256"], b2["spec_sha256"])
        with self.assertRaises(ValueError):
            router.run_task(dict(SPEC, version=2), c)
        for bad in (0, 1.5, True, "2", -1):
            with self.assertRaises(ValueError):
                router.run_task(dict(SPEC, version=bad), c)

    def test_verify_rederives_the_worker_from_cell_root_and_log(self):
        w, v = self.mk("w"), self.mk("v", "scripted_strong", "claude-opus-5-5")
        decoy = self.mk("decoy")
        spec = dict(SPEC, id="vv")
        good = router.run_task(spec, w)
        self.assertTrue(router.verify(spec, good, self.d, verifier_dir=v))
        self.assertTrue(router.verify(spec, good, self.d, verifier_dir=v))  # repeatable: verifier runs are versioned
        fabricated = dict(good, log_head="0" * 64)
        forged_cell = dict(good, cell="decoy")  # decoy cell.json has the right model but no such log line
        forged_cost = dict(good, cost=dict(good["cost"], tokens_in=0))
        forged_model = dict(good, model="claude-sonnet-5-5")
        missing_cell = dict(good, cell="nope")
        bad_name = dict(good, cell="../w")
        for name, b in (("fabricated", fabricated), ("forged_cell", forged_cell), ("forged_cost", forged_cost),
                        ("forged_model", forged_model), ("missing_cell", missing_cell), ("bad_name", bad_name)):
            self.assertFalse(router.verify(spec, b, self.d, verifier_dir=v), name)
        with self.assertRaises(TypeError):  # the caller no longer names the worker directory
            router.verify(spec, good, self.d, worker_dir=decoy)
        # the worker's log was tampered after the bundle was made
        with open(os.path.join(w, "log.jsonl"), "a") as f:
            f.write("{}\n")
        self.assertFalse(router.verify(spec, good, self.d, verifier_dir=v))

    def test_verify_log_never_raises_on_malformed_files(self):
        for head in ('[]', '5', 'null', '"x"', '{"head": 5, "n": "x"}', '{', '', '{"head": [], "n": []}'):
            with tempfile.TemporaryDirectory() as d:
                h = cell.append_log(d, {"i": 1})
                with open(os.path.join(d, "log.head"), "w") as f:
                    f.write(head)
                self.assertIs(cell.verify_log(d), False, head)
                self.assertIs(cell.verify_log(d, h), False, head)
        for junk in ('[]', '5', 'null', '"x"', '{"prev": 5}', '\xff', ''):
            with tempfile.TemporaryDirectory() as d:
                h = cell.append_log(d, {"i": 1})
                with open(os.path.join(d, "log.jsonl"), "wb") as f:
                    f.write(junk.encode("latin-1") + b"\n")
                self.assertIs(cell.verify_log(d, h), False, junk)
        with tempfile.TemporaryDirectory() as d:  # both files gone while a head is expected
            h = cell.append_log(d, {"i": 1})
            os.remove(os.path.join(d, "log.jsonl"))
            os.remove(os.path.join(d, "log.head"))
            self.assertIs(cell.verify_log(d, h), False)


class VerifyClass(Base):
    """verify is one total check: every path, the expect path included, recomputes the bundle from the cell root
    and the log, and accepts only a bundle equal to that recomputation with status done."""
    EXP = ["a", "b"]

    def setUp(self):
        super().setUp()
        self.w = self.mk("w")
        self.mk("w2")  # another cell, so a bundle can be pointed at a real cell that did not run it
        self.v = self.mk("v", "scripted_strong", "claude-opus-5-5")
        self.specs = {"done": dict(SPEC, id="ok", expect=self.EXP),
                      "escalate": dict(SPEC, id="esc", actions=["read", "write"], expect=self.EXP),
                      "budget_exceeded": dict(SPEC, id="bud", budget={"tokens": 1}, expect=self.EXP)}
        self.bundles = {k: router.run_task(sp, self.w) for k, sp in self.specs.items()}
        self.assertEqual({k: b["status"] for k, b in self.bundles.items()}, {k: k for k in self.specs})

    def _never(self, spec, b, msg):
        """verify(b) is False on the expect path and, without expect, on the verifier path; it never raises."""
        self.assertIs(router.verify(spec, b, self.d), False, msg)
        noexp = {k: v for k, v in spec.items() if k != "expect"}
        self.assertIs(router.verify(noexp, b, self.d, verifier_dir=self.v), False, msg)

    def test_relabelled_refused_bundles_are_rejected(self):
        """kills: the expect path returning before anchoring (R3: relabelled escalate/budget_exceeded accepted)."""
        for k in ("escalate", "budget_exceeded"):
            b = self.bundles[k]
            self._never(self.specs[k], b, k)
            relabel = dict(b, status="done", result=self.EXP)
            self._never(self.specs[k], relabel, k)
            full = dict(relabel, actions_allowed=["read"], actions_denied=[])
            self._never(self.specs[k], full, k)
        self.assertTrue(router.verify(self.specs["done"], self.bundles["done"], self.d))

    def test_fabricated_and_malformed_bundles_are_rejected_without_raising(self):
        spec = self.specs["done"]
        fab = {"status": "done", "task_id": "ok", "spec_sha256": router._sha(spec), "result": self.EXP}
        good = self.bundles["done"]
        for b in (fab, dict(fab, cell="w"), dict(fab, cell="w", log_head=good["log_head"]), {}, [], None, "x", 5,
                  {"cell": None}, {"cell": "w", "log_head": 5}, {"cell": ["w"]}, dict(good, cell="../w"),
                  dict(good, cell="nope"), dict(good, log_head=None), dict(good, cost=None), dict(good, cost={})):
            self._never(spec, b, repr(b)[:80])
        for bad_spec in (None, [], "x", {}, {"id": "ok"}, dict(spec, budget=None)):
            self.assertIs(router.verify(bad_spec, good, self.d), False, repr(bad_spec))
        self.assertIs(router.verify(dict(spec, expect=object()), good, self.d), False)

    def _pool(self, key, b):
        others = [x for x in self.bundles.values()]
        vals = [None, True, False, 0, 1, -1, 0.5, "", "x", "done", [], {}, self.EXP, ["a"], ["read"], ["write"],
                [b.get(key)], 1e12, float("nan")]
        vals += [o.get(key) for o in others] + ["escalate", "budget_exceeded", "w2", "v", "claude-opus-5-5", "extract",
                                               "verify", "plan", "0" * 64, router._sha(SPEC)]
        if isinstance(b.get(key), dict):
            for sk, sv in b[key].items():
                vals += [dict(b[key], **{sk: x}) for x in (0, sv + 1 if isinstance(sv, (int, float)) else 1, -1, 0.0,
                                                           None, str(sv), True)]
                vals.append({x: y for x, y in b[key].items() if x != sk})
            vals.append(dict(b[key], extra=1))
        if isinstance(b.get(key), (int, float)) and not isinstance(b.get(key), bool):
            vals += [float(b[key]), b[key] + 1, -b[key]]
        return vals

    def test_property_every_field_mutation_of_a_valid_and_a_refused_bundle_is_rejected(self):
        """Every field of a done, an escalate and a budget_exceeded bundle, set to every value of a hostile pool,
        deleted, or joined by an extra field, alone and in random combinations: verify accepts only the unchanged
        done bundle, so a bundle whose recomputed status differs is never accepted."""
        n = 0
        for k, b in self.bundles.items():
            spec = self.specs[k]
            muts = [{f: v} for f in b for v in self._pool(f, b)] + [{f: DROP} for f in b] + [{"extra": 1}]
            rnd = random.Random(9)
            for _ in range(300):
                fs = rnd.sample(sorted(b), rnd.randint(2, 5))
                muts.append({f: rnd.choice(self._pool(f, b)) for f in fs} | {"status": "done", "result": self.EXP})
            for m in muts:
                mb = {f: v for f, v in dict(b, **m).items() if v is not DROP}
                same = json.dumps(mb, sort_keys=True) == json.dumps(b, sort_keys=True)
                got = router.verify(spec, mb, self.d)
                self.assertIs(got, same and k == "done", (k, m))
                n += 1
        self.assertGreater(n, 1500)

    def _loosen(self, **pol):
        with open(os.path.join(self.w, "policy.json"), "w") as f:
            json.dump(dict(POL, **pol), f)

    def _forged(self, spec, result, head):
        """An attacker's best bundle: exactly what _bundle recomputes from the cell's current files and log entry."""
        c, pol = cell.load(self.w)
        return router._bundle(spec, c, pol, cell.log_entry(self.w, head), head, result)

    def test_escalate_then_policy_loosened_then_relabelled_done_is_rejected(self):
        """kills: the R4 double mutant (entry policy_sha256 unbound and entry status unchecked together): an escalate
        run, policy.json then loosened to allow the denied action, the bundle rebuilt as done, expect null."""
        spec = dict(self.specs["escalate"], expect=None)
        self._loosen(allow=["read", "write"])
        forged = self._forged(spec, None, self.bundles["escalate"]["log_head"])
        self.assertEqual(forged["status"], "done")  # what the loosened cell recomputes: only the log can refuse it
        self._never(spec, forged, "loosened+relabelled")

    def test_any_policy_edit_voids_an_earlier_done_bundle(self):
        """kills: the entry's policy_sha256 not bound (alone): a compatible, tighter edit still voids the bundle."""
        spec, good = self.specs["done"], self.bundles["done"]
        self._loosen(max_tokens=999)
        self.assertEqual(self._forged(spec, self.EXP, good["log_head"]), good)  # the recomputed bundle is unchanged
        self.assertIs(router.verify(spec, good, self.d), False)

    def _rewrite_log(self, edit):
        """Rewrite w's log with edit(entry) on the first line and a fresh chain and log.head (hashes are unkeyed)."""
        lines = open(os.path.join(self.w, "log.jsonl"), "rb").read().splitlines()
        prev, out = cell.GENESIS, []
        for i, line in enumerate(lines):
            row = json.loads(line)
            row["prev"] = prev
            if i == 0:
                edit(row["entry"])
            out.append(json.dumps(row, sort_keys=True).encode())
            prev = hashlib.sha256(out[-1]).hexdigest()
        with open(os.path.join(self.w, "log.jsonl"), "wb") as f:
            f.write(b"\n".join(out) + b"\n")
        with open(os.path.join(self.w, "log.head"), "w") as f:
            json.dump({"head": prev, "n": len(out)}, f)
        return hashlib.sha256(out[0]).hexdigest()

    def test_a_logged_status_other_than_done_is_rejected(self):
        """kills: the entry status check dropped (alone). A forged chain whose first entry says escalate, with the
        policy and every hash unchanged; the control (a harmless extra field) verifies, so only the status refuses."""
        spec, good = self.specs["done"], self.bundles["done"]
        head = self._rewrite_log(lambda e: e.update(note=1))
        self.assertIs(router.verify(spec, dict(good, log_head=head), self.d), True)  # the forged chain itself verifies
        head = self._rewrite_log(lambda e: e.update(status="escalate"))
        self.assertIs(router.verify(spec, dict(good, log_head=head), self.d), False)

    def test_deeply_nested_result_or_expect_returns_false(self):
        deep = []
        for _ in range(100_000):
            deep = [deep]
        spec, good = self.specs["done"], self.bundles["done"]
        self.assertIs(router.verify(spec, dict(good, result=deep), self.d), False)
        self.assertIs(router.verify(dict(spec, expect=deep), good, self.d), False)

    def test_property_relabelled_done_with_every_pair_of_field_mutations_is_rejected(self):
        """A refused bundle relabelled done, plus every single mutation of each other field and 3 random values for
        every pair of other fields; checked with expect and expect null, before and after policy.json is loosened
        to allow what the run tried (the attacker also rebuilds the bundle from the loosened cell)."""
        rnd, n = random.Random(11), 0
        for loosened in (False, True):
            if loosened:
                self._loosen(allow=["read", "write"], max_tokens=10**9)
            for k in ("escalate", "budget_exceeded"):
                spec, b0 = self.specs[k], self.bundles[k]
                for b in ([b0, self._forged(dict(spec, expect=None), None, b0["log_head"])] if loosened else [b0]):
                    fields = sorted(f for f in b if f != "status")
                    pool = {f: self._pool(f, b) + [DROP] for f in fields}
                    muts = [{"status": "done"}] + [{"status": "done", f: v} for f in fields for v in pool[f]]
                    muts += [{"status": "done", f: rnd.choice(pool[f]), g: rnd.choice(pool[g])}
                             for f, g in itertools.combinations(fields, 2) for _ in range(3)]
                    for m in muts:
                        mb = {f: v for f, v in dict(b, **m).items() if v is not DROP}
                        for sp in (spec, dict(spec, expect=None)):
                            self.assertIs(router.verify(sp, mb, self.d), False, (k, loosened, m))
                            n += 1
        self.assertGreater(n, 5000)


class PolicyBindingClass(Base):
    """verify binds the verdict to the cell the spec names: a run cell looser on any policy dimension fails."""
    ACTS = ("read", "write", "net", "exec", "fs", "git")

    def test_property_a_run_cell_looser_than_the_named_cell_on_any_dimension_never_verifies(self):
        """kills: spec["cell"] not bound (R4: a spec naming a strict cell, run on a lax one, verified True).
        25 generated named policies; for each, one run cell loosened on each dimension (allow entry added, deny entry
        dropped, deny absent, token cap up, seconds cap up, an extra key) gives a done bundle that fails verify on
        both paths; the equal and the tighter controls verify."""
        rnd, v, n = random.Random(10), self.mk("v", "scripted_strong", "claude-opus-5-5"), 0
        for i in range(25):
            allow = rnd.sample(self.ACTS, rnd.randint(1, 4))
            outside = [a for a in self.ACTS if a not in allow]
            deny = rnd.sample(outside, rnd.randint(1, len(outside)))
            named = {"allow": allow, "deny": deny, "max_tokens": rnd.randint(100, 10**6), "max_seconds": rnd.uniform(5, 1e3)}
            self.mk(f"n{i}", pol=named)
            use = [rnd.choice(allow)]
            spec = dict(SPEC, id=f"p{i}", cell=f"n{i}", actions=use, expect=["a", "b"])
            noexp = {x: y for x, y in spec.items() if x != "expect"}
            loose = {"allow": dict(named, allow=allow + [rnd.choice(outside)]),
                     "deny": dict(named, deny=deny[1:]),
                     "noDeny": {x: y for x, y in named.items() if x != "deny"},
                     "tokens": dict(named, max_tokens=named["max_tokens"] + rnd.randint(1, 1000)),
                     "seconds": dict(named, max_seconds=named["max_seconds"] + rnd.uniform(1e-3, 100)),
                     "extra": dict(named, net=True)}
            tight = {"equal": named, "tighter": dict(named, allow=use, deny=outside + ["sudo"], max_tokens=named["max_tokens"] - 1,
                                                       max_seconds=named["max_seconds"] / 2)}
            for dim, pol in list(loose.items()) + list(tight.items()):
                b = router.run_task(spec, self.mk(f"r{i}-{dim}", pol=pol))
                self.assertEqual(b["status"], "done", (i, dim))  # acceptable but for the binding
                ok = dim in tight
                self.assertIs(router.verify(spec, b, self.d), ok, (i, dim, pol))
                self.assertIs(router.verify(noexp, b, self.d, verifier_dir=v), ok, (i, dim, pol))
                n += 1
        self.assertEqual(n, 25 * 8)
        self.assertIs(router.verify({x: y for x, y in spec.items() if x != "cell"}, b, self.d), False)  # names no cell

    def test_no_cell_spec_run_itself_is_not_verified(self):
        """kills: spec["cell"] -> spec.get("cell", bundle["cell"]) (the old no-cell assertion only changed the spec
        hash). The bundle is run FROM the no-cell spec, so its hash matches and only the missing cell can refuse it."""
        self.mk("w")
        v = self.mk("v", "scripted_strong", "claude-opus-5-5")
        nocell = {x: y for x, y in SPEC.items() if x != "cell"}
        b = router.run_task(dict(nocell, expect=["a", "b"]), os.path.join(self.d, "w"))
        self.assertEqual(b["status"], "done")
        self.assertIs(router.verify(dict(nocell, expect=["a", "b"]), b, self.d), False)
        b2 = router.run_task(dict(nocell, id="t2"), os.path.join(self.d, "w"))
        self.assertIs(router.verify(dict(nocell, id="t2"), b2, self.d, verifier_dir=v), False)
        c = dict(SPEC, id="t3", expect=["a", "b"])  # control: the same task naming its cell verifies
        self.assertIs(router.verify(c, router.run_task(c, os.path.join(self.d, "w")), self.d), True)


if __name__ == "__main__":
    unittest.main()
