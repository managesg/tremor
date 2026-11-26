import time
import unittest

from lab import r6_predicates as rp
from lab import r6_t3_lemmas as T

SL, TOTAL = 5000, 10**9
SIZES = (3, 4, 7, 10, 14)
T0 = time.time()


def pc(x):
    return bin(x).count("1")


def balanced(s, k):
    return k <= 3 * pc(s) <= 2 * k


def holds_a(s, k):
    return (not balanced(s, k)) or 9 * pc(s) * (k - pc(s)) >= 2 * k * k


def holds_b(s, k):
    w = [((s >> a) & 1) * (k - 1 - a) - pc(s >> (a + 1)) for a in range(k)]
    return (not balanced(s, k)) or 81 * sum(x * x for x in w) >= 4 * k ** 3


PURE = {"a": holds_a, "b": holds_b}


def lab(t):
    return T.label(t, SL, TOTAL)


class TrueLemmaTests(unittest.TestCase):
    def test_true_holds_over_whole_domain_and_matches_independent_python(self):
        for kind in T.KINDS:
            for k in SIZES:
                with self.subTest(kind=kind, k=k):
                    self.assertEqual(lab(T.generate(kind, k, 1, "true")), T.Label(True, None))
                    if k <= 10:
                        self.assertTrue(all(PURE[kind](s, k) for s in range(1 << k)))

    def test_every_k_3_to_9_true(self):
        for kind in T.KINDS:
            for k in range(3, 10):
                self.assertTrue(lab(T.generate(kind, k, 5, "true")).holds, (kind, k))


class PlantedFalseTests(unittest.TestCase):
    def test_every_mutation_is_false_for_every_k(self):
        for kind in T.KINDS:
            for i, (old, new) in enumerate(T.MUTATIONS[kind]):
                for k in range(T.K_MIN, T.K_MAX + 1):
                    with self.subTest(kind=kind, mutation=i, k=k):
                        src = T.SOURCES[kind].format(k=k)
                        m = T.TIGHT_B[k] + 1
                        old_s, new_s = old.format(k=k, m=m), new.format(k=k, m=m)
                        self.assertEqual(src.count(old_s), 1)
                        t = T.Task(kind, k, 0, "planted_false", src.replace(old_s, new_s))
                        L = lab(t)
                        self.assertFalse(L.holds)
                        self.assertFalse(rp.parse(t.source).evaluate({"S": L.counterexample}, SL))
                        self.assertIsNot(L.counterexample, None)

    def test_domain_includes_zero_and_top_value(self):
        # a predicate false only at S = 2**k - 1 (resp. only at 0) must be labelled false with that counterexample
        for k in range(T.K_MIN, T.K_MAX + 1):
            top = (1 << k) - 1
            for target in (0, top):
                src = f"S != {target}"
                bad = rp.check_lemma(rp.parse(src), T._domain(T.generate(T.KINDS[0], k, 0, "true")), SL, TOTAL)
                self.assertEqual(bad, {"S": target})

    def test_all_mutations_are_reached_by_some_seed(self):
        for kind in T.KINDS:
            seen = {T.generate(kind, 6, s, "planted_false").source for s in range(200)}
            self.assertEqual(len(seen), len(T.MUTATIONS[kind]))

    def test_k14_planted_false_has_counterexample(self):
        for kind in T.KINDS:
            for seed in range(3):
                L = lab(T.generate(kind, 14, seed, "planted_false"))
                self.assertFalse(L.holds)
                self.assertTrue(0 <= L.counterexample < 1 << 14)

    def test_planted_source_differs_from_true_in_one_fragment(self):
        for kind in T.KINDS:
            tr = T.generate(kind, 9, 3, "true").source
            pl = T.generate(kind, 9, 3, "planted_false").source
            self.assertNotEqual(tr, pl)
            self.assertLessEqual(abs(len(tr) - len(pl)), 3)


class LabelNotFromTemplateTests(unittest.TestCase):
    def test_swapping_variant_does_not_change_label(self):
        for kind in T.KINDS:
            for k in (4, 8):
                for v, w in (("true", "planted_false"), ("planted_false", "true")):
                    t = T.generate(kind, k, 2, v)
                    self.assertEqual(lab(t), lab(t._replace(variant=w)))
        self.assertTrue(lab(T.generate("a", 8, 2, "true")._replace(variant="planted_false")).holds)
        self.assertFalse(lab(T.generate("a", 8, 2, "planted_false")._replace(variant="true")).holds)

    def test_label_follows_source_not_kind(self):
        a = T.generate("a", 8, 0, "true")
        self.assertFalse(lab(a._replace(kind="b", source=T.generate("a", 8, 0, "planted_false").source)).holds)

    def test_first_counterexample_is_smallest_failing_element(self):
        t = T.generate("a", 8, 0, "planted_false")
        L = lab(t)
        p = rp.parse(t.source)
        self.assertFalse(any(not p.evaluate({"S": s}, SL) for s in range(L.counterexample)))

    def test_budget_exhaustion_is_refused_not_labelled(self):
        t = T.generate("b", 10, 0, "true")
        with self.assertRaises(rp.StepLimitExceeded):
            T.label(t, SL, 1000)
        with self.assertRaises(rp.PredicateRefused):
            T.label(t, 5, TOTAL)


class OracleTests(unittest.TestCase):
    def cc(self, t, ans):
        return T.check_claim(t, ans, SL, TOTAL)

    def test_true_lemma(self):
        t = T.generate("a", 8, 0, "true")
        self.assertEqual(self.cc(t, "true"), "correct")
        self.assertEqual(self.cc(t, 0), "wrong")      # S=0 is unbalanced: predicate True
        self.assertEqual(self.cc(t, 255), "wrong")

    def test_false_lemma_accepts_only_a_valid_counterexample(self):
        for kind in T.KINDS:
            t = T.generate(kind, 8, 0, "planted_false")
            ce = lab(t).counterexample
            p = rp.parse(t.source)
            self.assertEqual(self.cc(t, "true"), "wrong")
            self.assertEqual(self.cc(t, ce), "correct")
            for s in range(1 << 8):
                self.assertEqual(self.cc(t, s), "wrong" if p.evaluate({"S": s}, SL) else "correct", s)

    def test_malformed_answers(self):
        t = T.generate("a", 5, 0, "planted_false")
        for bad in (True, False, -1, 32, 3.0, "false", "True", None, [1], "1", b"true"):
            self.assertEqual(self.cc(t, bad), "malformed", repr(bad))

    def test_oracle_ignores_variant(self):
        t = T.generate("a", 8, 0, "planted_false")._replace(variant="true")
        self.assertEqual(self.cc(t, "true"), "wrong")


class DeterminismAndPromptTests(unittest.TestCase):
    def test_determinism(self):
        for kind in T.KINDS:
            for v in T.VARIANTS:
                self.assertEqual(T.generate(kind, 9, 7, v), T.generate(kind, 9, 7, v))
                self.assertEqual(T.prompt_sha256(T.generate(kind, 9, 7, v)), T.prompt_sha256(T.generate(kind, 9, 7, v)))

    def test_seed_changes_planted_choice_somewhere(self):
        self.assertNotEqual({T.generate("a", 7, s, "planted_false").source for s in range(30)}, {T.generate("a", 7, 0, "planted_false").source})

    def test_seed_helper_vector_and_checks(self):
        import hashlib
        self.assertEqual(T._task_seed("t", 5, 2), int.from_bytes(hashlib.sha256(b"t:5:2").digest()[:8], "big") >> 1)
        for bad in (("", 0, 0), (1, 0, 0), ("t", True, 0), ("t", 0, -1), ("t", 0, 10**12 + 1), ("t", 2**63, 0)):
            with self.assertRaises(ValueError):
                T._task_seed(*bad)
        from lab.l3c_harness import task_seed
        self.assertEqual(T._task_seed("gen-T3:a:5", -9, 0), task_seed("gen-T3:a:5", -9, 0))

    def test_prompt_bytes_and_hash_pinned(self):
        t = T.generate("a", 3, 0, "true")
        want = (
            "Finite lemma over bitmasks.\n"
            "Domain: every integer S with 0 <= S < 2**3; bit a of S set means a is in the subset.\n"
            "Predicate (Python-like expression over S; popcount(x) counts set bits, bit(x, i) is bit i of x,\n"
            "x >> n shifts right, sum(e for a in range(n)) adds e over a = 0..n-1):\n"
            "(3*popcount(S) < 3 or 3*popcount(S) > 2*3) or 9*popcount(S)*(3-popcount(S)) >= 2*3*3\n"
            "Question: is the predicate True for every S in the domain?\n"
            "Answer with the single word true, or with one integer S in the domain for which it is False.\n")
        self.assertEqual(T.render_prompt(t), want)
        self.assertEqual(T.prompt_sha256(t), "3aa62fee2357522dc0bc1fd5595aaab85737d8dacd8901e3e91aebce030d27a8")
        self.assertNotIn("true\n(", T.render_prompt(t))

    def test_prompt_does_not_leak_variant_or_label(self):
        for kind in T.KINDS:
            p = T.render_prompt(T.generate(kind, 6, 0, "planted_false"))
            for w in ("planted", "variant", "counterexample is", "paper"):
                self.assertNotIn(w, p)
            self.assertTrue(p.isascii())

    def test_prompts_differ_between_true_and_planted(self):
        for kind in T.KINDS:
            self.assertNotEqual(T.prompt_sha256(T.generate(kind, 6, 0, "true")), T.prompt_sha256(T.generate(kind, 6, 0, "planted_false")))

    def test_sources_fit_the_whitelist_for_all_sizes(self):
        for kind in T.KINDS:
            for k in range(T.K_MIN, T.K_MAX + 1):
                for v in T.VARIANTS:
                    self.assertIsNotNone(rp.parse(T.generate(kind, k, 0, v).source))


class RefusalTests(unittest.TestCase):
    def test_generate_refusals(self):
        bad = [("c", 5, 0, "true"), ("a", 2, 0, "true"), ("a", 15, 0, "true"), ("a", True, 0, "true"), ("a", 5.0, 0, "true"),
               ("a", 5, True, "true"), ("a", 5, 2**63, "true"), ("a", 5, 0, "false"), ("a", 5, 0, None), (None, 5, 0, "true")]
        for args in bad:
            with self.assertRaises(ValueError, msg=repr(args)):
                T.generate(*args)

    def test_no_defaults_for_open_parameters(self):
        for f in (T.generate, T.label, T.check_claim):
            with self.assertRaises(TypeError):
                f()
        with self.assertRaises(TypeError):
            T.generate("a", 5, 0)
        with self.assertRaises(TypeError):
            T.label(T.generate("a", 5, 0, "true"))
        with self.assertRaises(TypeError):
            T.check_claim(T.generate("a", 5, 0, "true"), "true")

    def test_task_refusals(self):
        t = T.generate("a", 5, 0, "true")
        for bad in (None, (1,), t._replace(k=15), t._replace(k=2), t._replace(kind="z"), t._replace(variant="x"),
                    t._replace(source=3), t._replace(k=True)):
            for f in (lambda x: T.label(x, SL, TOTAL), T.render_prompt, T.prompt_sha256,
                      lambda x: T.check_claim(x, "true", SL, TOTAL)):
                with self.assertRaises(ValueError):
                    f(bad)

    def test_non_whitelisted_source_refused(self):
        t = T.generate("a", 5, 0, "true")._replace(source="__import__('os')")
        with self.assertRaises(rp.PredicateRefused):
            lab(t)
        with self.assertRaises(rp.PredicateRefused):
            T.check_claim(t, 1, SL, TOTAL)

    def test_check_claim_budget_refusal(self):
        with self.assertRaises(rp.PredicateRefused):
            T.check_claim(T.generate("b", 9, 0, "true"), "true", SL, 100)


def count_failures(t):
    p = rp.parse(t.source)
    return sum(1 for s in range(1 << t.k) if not p.evaluate({"S": s}, SL))


def mutated(kind, k, idx):
    old, new = T.MUTATIONS[kind][idx]
    m = T.TIGHT_B[k] + 1
    src = T.SOURCES[kind].format(k=k)
    return T.Task(kind, k, 0, "planted_false", src.replace(old.format(k=k, m=m), new.format(k=k, m=m)))


class TightVariantTests(unittest.TestCase):
    def test_tight_b_constant_is_exact_by_check_lemma(self):
        for k in range(T.K_MIN, T.K_MAX + 1):
            with self.subTest(k=k):
                held = T.Task("b", k, 0, "true", T.SOURCES["b"].format(k=k).replace(
                    "4*%d*%d*%d" % (k, k, k), str(T.TIGHT_B[k])))
                self.assertTrue(lab(held).holds)          # TIGHT_B[k] is the true minimum: still holds
                L = lab(mutated("b", k, 3))               # one past it fails
                self.assertFalse(L.holds)
                self.assertTrue(balanced(L.counterexample, k))

    def test_tight_b_fails_on_few_S(self):
        for k in range(T.K_MIN, T.K_MAX + 1):
            if k > 12:
                continue
            n = count_failures(mutated("b", k, 3))
            self.assertGreaterEqual(n, 1)
            if k >= 9:
                self.assertLessEqual(n / (1 << k), 1 / 32 + 1e-9, k)
            self.assertLessEqual(n, 1 << (k - 1))  # k=3: 4 of 8 balanced-minimal sets

    def test_tight_a_fails_only_on_size_just_below_third(self):
        from math import comb
        for k in range(T.K_MIN, 13):
            s0 = -(-k // 3)
            t = mutated("a", k, 3)
            self.assertEqual(count_failures(t), comb(k, s0 - 1), k)
            if k >= 8:
                self.assertLessEqual(count_failures(t) / (1 << k), 0.12)
        self.assertFalse(lab(mutated("a", 14, 3)).holds)

    def test_easy_variants_fail_on_many_S_so_tight_is_harder(self):
        self.assertGreater(count_failures(mutated("a", 10, 0)), 10 * count_failures(mutated("a", 10, 3)) // 2)


class SubclassAndDistinctTests(unittest.TestCase):
    def test_int_subclass_answer_is_malformed_not_a_crash(self):
        class MyInt(int):
            pass

        class Bool2(int):
            pass
        t = T.generate("a", 6, 0, "planted_false")
        for bad in (MyInt(3), Bool2(0), True):
            self.assertEqual(T.check_claim(t, bad, SL, TOTAL), "malformed")

    def test_distinct_instances_are_exactly_the_distinct_prompts(self):
        inst = T.distinct_instances()
        self.assertEqual(len(inst), 120)
        self.assertEqual(len({T.prompt_sha256(t) for t in inst}), 120)
        self.assertEqual(sum(t.variant == "true" for t in inst), 24)
        pool = {T.prompt_sha256(T.generate(kd, k, sd, v)) for kd in T.KINDS for k in range(3, 15) for v in T.VARIANTS
                for sd in range(300)}
        self.assertEqual(pool, {T.prompt_sha256(t) for t in inst})   # no other prompt exists
        self.assertEqual(T.distinct_instances(), inst)


class RuntimeTest(unittest.TestCase):
    def test_runtime_under_90s(self):
        self.assertLess(time.time() - T0, 90)


if __name__ == "__main__":
    unittest.main()
