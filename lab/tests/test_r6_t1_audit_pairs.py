"""Tests for lab/r6_t1_audit_pairs.py: real file (tracked copy if present, else runs/ copy) and a toy fixture with non-ASCII."""
import hashlib
import os
import tempfile
import unittest

from lab import r6_t1_audit_pairs as t

_REAL = t.SOURCE_PATH if os.path.exists(t.SOURCE_PATH) else t.FALLBACK_PATH
# MINIMAL-DIFF code-point [start, end) in the defective text, derived by hand once (str.find on the raw file, then
# trimming the common prefix and suffix by hand: hc deletes `On Set.univ` after `IsCycle` so it is [1411, 1411];
# charp trims `[`/`]`; vnp trims the 37-char common suffix ` fun i => if e i then 1 else 0) (g n)`), NOT by the code
# under test.
PINNED_SPANS = {
    "beyond_exponent_nat": [1573, 1574], "computes_self_reference": [858, 859], "vp_degree_bound_dropped": [3526, 3530],
    "main_quantifier_swap": [1892, 1917], "hc_cycle_predicate": [1411, 1411], "main_charp_dropped": [1954, 1964],
    "separation_subset_weak": [4425, 4426], "vnp_equality_on_01": [4209, 4366],
}
LEN_DELTA = {"beyond_exponent_nat": 0, "computes_self_reference": 0, "vp_degree_bound_dropped": -30,
             "main_quantifier_swap": 0, "hc_cycle_predicate": -11, "main_charp_dropped": 1,
             "separation_subset_weak": 0, "vnp_equality_on_01": 105}


def _min_diff(f, d):
    """Independent minimal diff: prefix via commonprefix, suffix via commonprefix of the reversed remainders."""
    p = len(os.path.commonprefix([f, d]))
    q = len(os.path.commonprefix([f[p:][::-1], d[p:][::-1]]))
    return [p, len(d) - q]

# sha256 of the rendered prompt (convention sentence, "INFORMAL (source: lean-docstring):\ndef f", FORMAL toy defective text), computed once outside the module
PINNED_PROMPT_SHA = "dbf8457eeb6eb1cbf6e547768544b5131d3420bb00ec0bfc5cbd377d52eee704"

TOY = "def f := ∀ x, x < 3 ∧ ℝ\ndef g := ∑ y, y < 3 ∧ ok\n"
TOY_SPECS = [
    {"id": "t_le", "before": "def f := ∀ x, x ", "old": "<", "after": " 3 ∧ ℝ", "new": "≤", "informal": "def f", "why": "w",
     "may_elaborate": "likely", "evidence": t.EVIDENCE},
    {"id": "t_amb", "before": "", "old": "<", "after": " 3", "new": "≤", "informal": "def f", "why": "w",
     "may_elaborate": "likely", "evidence": t.EVIDENCE},
    {"id": "t_same", "before": "def f := ", "old": "∀", "after": " x", "new": "∀", "informal": "def f", "why": "w",
     "may_elaborate": "likely", "evidence": t.EVIDENCE},
    {"id": "t_empty", "before": "def f := ", "old": "∀", "after": " x", "new": "", "informal": "def f", "why": "w",
     "may_elaborate": "likely", "evidence": t.EVIDENCE},
    {"id": "t_miss", "before": "zzz", "old": "<", "after": "", "new": "≤", "informal": "def f", "why": "w",
     "may_elaborate": "likely", "evidence": t.EVIDENCE},
    {"id": "t_inf", "before": "def f := ∀ x, x ", "old": "<", "after": " 3 ∧ ℝ", "new": "≤", "informal": "nope", "why": "w",
     "may_elaborate": "likely", "evidence": t.EVIDENCE},
]


@unittest.skipUnless(os.path.exists(_REAL), "Statement.lean not available")
class RealFile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = t.load_source(_REAL)

    def test_digest_and_nonascii(self):
        self.assertEqual(hashlib.sha256(self.text.encode()).hexdigest(), t.SOURCE_SHA256)
        self.assertLess(len(self.text), len(self.text.encode()))

    def test_eight_distinct_defects(self):
        ids = [s["id"] for s in t.defect_specs()]
        self.assertEqual(len(ids), 8)
        self.assertEqual(len(set(ids)), 8)

    def test_each_defect_one_edit_exact_span(self):
        for s in t.defect_specs():
            p = t.build_pair(s["id"], self.text)
            a, b = p["span"]
            f, d = p["faithful"], p["defective"]
            self.assertEqual(f, self.text)
            self.assertNotEqual(f, d)
            self.assertEqual(p["span"], _min_diff(f, d))
            self.assertEqual(d[:a], f[:a])
            self.assertEqual(d[b:], f[len(f) - (len(d) - b):])  # nothing outside the span changed
            self.assertEqual(len(d) - len(f), LEN_DELTA[s["id"]])
            self.assertEqual(p["informal_source"], "lean-docstring")
            self.assertEqual(t.placements(f, d, p["span"]), 1)
            self.assertEqual(f.count(s["before"] + s["old"] + s["after"]), 1)
            self.assertEqual(s["evidence"], "semantic change by inspection")
            self.assertIn(s["may_elaborate"], ("likely", "uncertain"))
            self.assertTrue(s["why"])

    def test_pinned_spans(self):
        self.assertEqual({s["id"] for s in t.defect_specs()}, set(PINNED_SPANS))
        for i, span in PINNED_SPANS.items():
            self.assertEqual(t.build_pair(i, self.text)["span"], span, i)

    def test_uncertain_defects_flagged(self):
        u = {s["id"] for s in t.defect_specs() if s["may_elaborate"] == "uncertain"}
        self.assertEqual(u, {"vnp_equality_on_01"})

    def test_sealed_build_refuses_caller_text(self):
        for fn in (t.build_pair, t.defective_task):
            with self.assertRaises(ValueError):
                fn("beyond_exponent_nat", text=self.text, sealed=True)
            with self.assertRaises(ValueError):
                fn("beyond_exponent_nat", specs=t.defect_specs(), sealed=True)
        with self.assertRaises(ValueError):
            t.faithful_pairs(text=self.text, sealed=True)
        self.assertEqual(len(t.faithful_pairs(sealed=True)), 8)
        self.assertEqual(t.build_pair("beyond_exponent_nat", sealed=True)["faithful"], self.text)

    def test_prompt_states_span_convention(self):
        r = t.render_prompt(t.defective_task("hc_cycle_predicate", self.text))
        self.assertIn("smallest contiguous region you would change to restore the original", r)
        self.assertIn("source: lean-docstring", r)

    def test_spans_are_code_points_not_bytes(self):
        p = t.build_pair("main_quantifier_swap", self.text)
        a, b = p["span"]
        self.assertEqual(p["defective"][a:b], "∀ p : ℕ, ∃ c : ℝ, 0 < c ∧")
        self.assertEqual(t.build_pair("hc_cycle_predicate", self.text)["span"], [1411, 1411])  # pure deletion
        self.assertNotEqual(len(p["defective"][:a].encode()), a)

    def test_oracle_and_faithful(self):
        for s in t.defect_specs():
            task = t.defective_task(s["id"], self.text)
            self.assertEqual(t.oracle(task, {"faithful": False, "span": task["span"]}), 1)
            a, b = task["span"]
            self.assertEqual(t.oracle(task, {"faithful": False, "span": [a, b + 1]}), 0)
            self.assertEqual(t.oracle(task, {"faithful": False, "span": [a - 1, b]}), 0)
            self.assertEqual(t.oracle(task, {"faithful": True, "span": None}), 0)
        fp = t.faithful_pairs(self.text)
        self.assertEqual(len(fp), 8)
        for task in fp:
            self.assertEqual(task["formal"], self.text)
            self.assertEqual(t.oracle(task, {"faithful": True}), 1)
            self.assertEqual(t.oracle(task, {"faithful": False, "span": [0, 1]}), 0)

    def test_prompt_sha_distinct(self):
        shas = {t.prompt_sha256(t.defective_task(s["id"], self.text)) for s in t.defect_specs()}
        self.assertEqual(len(shas), 8)
        self.assertNotIn(t.prompt_sha256(t.faithful_pairs(self.text)[0]), shas)


class Refusals(unittest.TestCase):
    def test_load_source_mismatch(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "S.lean")
            with open(p, "wb") as fh:
                fh.write(b"x")
            with self.assertRaises(ValueError):
                t.load_source(p)
            self.assertEqual(t.load_source(p, hashlib.sha256(b"x").hexdigest()), "x")
            with self.assertRaises(FileNotFoundError):
                t.load_source(os.path.join(d, "none"))

    def test_toy_ok_and_span_code_points(self):
        p = t.build_pair("t_le", TOY, TOY_SPECS)
        self.assertEqual(p["span"], [TOY.index("<"), TOY.index("<") + 1])
        self.assertEqual(p["defective"], TOY.replace("<", "≤", 1))

    def test_toy_refusals(self):
        for i in ("t_amb", "t_same", "t_empty", "t_miss", "t_inf"):
            with self.assertRaises(ValueError, msg=i):
                t.build_pair(i, TOY, TOY_SPECS)
        with self.assertRaises(KeyError):
            t.build_pair("nope", TOY, TOY_SPECS)

    def test_prompt_sha_pinned(self):
        self.assertEqual(t.prompt_sha256(t.defective_task("t_le", TOY, TOY_SPECS)), PINNED_PROMPT_SHA)

    def test_minimal_span_edges(self):
        self.assertEqual(t.minimal_span("abc", "xbc"), [0, 1])
        self.assertEqual(t.minimal_span("abc", "abx"), [2, 3])
        self.assertEqual(t.minimal_span("aXa", "aa"), [1, 1])  # deletion
        self.assertEqual(t.minimal_span("aa", "aXa"), [1, 2])  # insertion
        self.assertEqual(t.minimal_span("aab", "ab"), [1, 1])  # the suffix bound: without it the end is 0 < start
        self.assertEqual(t.minimal_span("xabcabcy", "xabcy"), [4, 4])  # repeated text, deletion in the middle
        with self.assertRaises(ValueError):
            t.minimal_span("a", "a")

    def test_ambiguous_placement_refused(self):
        spec = [{"id": "amb", "before": "", "old": "aab", "after": "", "new": "ab", "informal": "aab", "why": "w",
                 "may_elaborate": "likely", "evidence": t.EVIDENCE}]
        self.assertEqual(t.placements("aab", "ab", [1, 1]), 2)
        with self.assertRaises(ValueError):
            t.build_pair("amb", "aab", spec)
        self.assertEqual(t.placements("xaby", "xay", [2, 2]), 1)
        self.assertEqual(t.placements("xaa", "xa", [1, 1]), 2)  # the last position counts

    def test_toy_faithful(self):
        fp = t.faithful_pairs(TOY, TOY_SPECS)
        self.assertEqual(len(fp), len(TOY_SPECS))
        self.assertTrue(all(x["formal"] == TOY and not x["defective"] and x["span"] is None for x in fp))


if __name__ == "__main__":
    unittest.main()
