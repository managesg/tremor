import time
import types
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


# ---------------------------------------------------------------------------------------------------------------
# Part 2: (c) transversal rank additivity, (d) sqrt-rank triangle; per-task registry function rk = rank_f2.
# ---------------------------------------------------------------------------------------------------------------
def span_rank(x, r, c):
    """Independent brute force: rank = log2 of the number of distinct XOR combinations of the r rows."""
    rows = [(x >> (c * i)) & ((1 << c) - 1) for i in range(r)]
    span = {0}
    for v in rows:
        span |= {a ^ v for a in span}
    return len(span).bit_length() - 1


def pure_cd(kind, x, y, mu):
    m2, M = mu * mu, (1 << mu) - 1
    p, q, r = span_rank(x, mu, mu), span_rank(y, mu, mu), span_rank(x ^ y, mu, mu)
    if kind == "d":
        return (r - p - q) ** 2 <= 4 * p * q
    rs = span_rank(x | (y << m2), 2 * mu, mu)
    cs = span_rank(sum(((((x >> (mu * i)) & M) << (2 * mu * i)) | (((y >> (mu * i)) & M) << (2 * mu * i + mu)))
                       for i in range(mu)), mu, 2 * mu)
    return not (rs == p + q and cs == p + q) or r == p + q


def rk_of(mu):
    return T.registry_cd(mu)["rk"][1]


def refused(src, mu=3, env=None):
    try:
        rp.parse(src, T.registry_cd(mu)).run(env or {}, 5000)
    except rp.PredicateRefused:
        return True
    return False


class RankF2BruteForceTests(unittest.TestCase):
    def test_square_every_input_mu_1_to_3_agrees_with_span_count(self):
        for mu in (2, 3):
            f = rk_of(mu)
            for x in range(1 << (mu * mu)):
                self.assertEqual(f(x, mu, mu), span_rank(x, mu, mu), (mu, x))

    def test_every_allowed_shape_agrees_and_every_other_is_refused(self):
        for mu in (2, 3):
            f = rk_of(mu)
            ok = {(mu, mu), (2 * mu, mu), (mu, 2 * mu)}
            for r in range(0, 2 * mu + 2):
                for c in range(0, 2 * mu + 2):
                    if (r, c) not in ok:
                        with self.assertRaises(rp.PredicateRefused, msg=(mu, r, c)):
                            f(0, r, c)
                        continue
                    for x in list(range(0, 1 << (r * c), 1 if r * c <= 12 else 61)) + [(1 << (r * c)) - 1]:
                        self.assertEqual(f(x, r, c), span_rank(x, r, c), (mu, r, c, x))
                    with self.assertRaises(rp.PredicateRefused):
                        f(1 << (r * c), r, c)

    def test_ranks_are_ints_below_2_64_and_deterministic(self):
        f = rk_of(3)
        a = [f(x, 3, 3) for x in range(512)]
        self.assertEqual(a, [f(x, 3, 3) for x in range(512)])
        self.assertTrue(all(type(v) is int and 0 <= v <= 3 for v in a))
        self.assertEqual(a[0], 0)
        self.assertEqual(f(0b100010001, 3, 3), 3)


class RegistrySandboxTests(unittest.TestCase):
    def test_direct_calls_refuse_bad_arguments(self):
        f = rk_of(3)
        for bad in ((1 << 20, 3, 3), (-1, 3, 3), (True, 3, 3), (1, True, 3), (1, 0, 3), (1, 3, 0), (1, 3, 7), (1, 7, 3),
                    (1.0, 3, 3), (1, 3.0, 3), (1, 3, 3.0), (0, 3, 0), (0, 0, 3), (1, 0, 0), (1, 2, 3), ("1", 3, 3), (None, 3, 3), (1 << 64, 3, 3), (1 << 9, 3, 3), (1 << 62, 6, 6)):
            with self.assertRaises(rp.PredicateRefused, msg=repr(bad)):
                f(*bad)
        for bad_arity in ((), (1,), (1, 3), (1, 3, 3, 3)):
            with self.assertRaises(TypeError):
                f(*bad_arity)
        with self.assertRaises(rp.PredicateRefused):
            rk_of(2)(1, 5, 2)    # cap is 2*mu = 4

    def test_function_exposes_nothing(self):
        f = rk_of(3)
        self.assertEqual(vars(f), {})
        self.assertTrue(all(type(c.cell_contents) is tuple and all(type(v) is int for sh in c.cell_contents for v in sh)
                            for c in f.__closure__))
        self.assertEqual(set(T.registry_cd(3)), {"rk"})
        self.assertEqual(T.registry_cd(3)["rk"][0], 3)
        self.assertNotIn("task", f.__code__.co_freevars)
        self.assertEqual(T.SCORER_IDS, ("rank_f2",))
        self.assertEqual(f.__name__, T.SCORER_IDS[0])
        self.assertEqual(len(T.SCORER_IDS), len(T.registry_cd(3)))

    def test_escape_attempts_refused(self):
        for src in ("rk.__class__", "rk(1, 3, 3).__class__", "rk.__closure__", "rk.__globals__", "__import__('os')",
                    "open('f')", "eval('1')", "globals()", "vars(rk)", "getattr(rk, 'x')", "rk", "rk == rk",
                    "rk(x=1, r=3, c=3)", "rk(*[1, 3, 3])", "[rk(i, 3, 3) for i in range(9)]",
                    "sum(rk(i, 3, 3) for i in range(9) for j in range(2))", "sum(rk(i, 3, 3) for i in [1, 2])",
                    "(lambda: 1)()", "rk(1, 3, 3)[0]", "rk(1, 3)", "rk(1, 3, 3, 3)", "rk()",
                    "rk(rk, 3, 3) == 0", "rk(i, 3, 3) for i in range(2)", "rk(1, 3, 3) == 1; 1",
                    "rk(18446744073709551616, 3, 3)", "rk(2**64, 3, 3)", "S.__class__", "rk(1, 3, 3) == 1 and __builtins__",
                    "sum(rk(i, 3, 3) for i in range(70000)) > 0"):
            self.assertTrue(refused(src, env={"S": 1}), src)

    def test_runtime_refusals_negative_huge_out_of_range(self):
        for src in ("rk(-1, 3, 3) == 0", "rk(1 << 64, 3, 3) == 0", "rk(1 << 63, 3, 3) == 0", "rk(512, 3, 3) == 0",
                    "rk(1, 0, 3) == 0", "rk(1, 3, 7) == 0", "rk(1, -3, 3) == 0", "rk(1 << 40, 6, 6) == 0"):
            self.assertTrue(refused(src), src)

    def test_bool_is_coerced_by_the_sandbox_before_the_call(self):
        # the sandbox (unchanged) turns True into 1 before calling; the function itself refuses a bool (above)
        self.assertEqual(rp.parse("rk(True, 3, 3) == 1", T.registry_cd(3)).evaluate({}, 100), True)

    def test_each_call_is_one_step_whatever_it_computes(self):
        reg = T.registry_cd(3)
        for x in (0, 1, 511):
            p = rp.parse(f"rk({x}, 3, 3) == rk(0, 3, 3)", reg)
            p.evaluate({}, 100)
            self.assertEqual(p.last_steps, 9)    # Compare + 2 calls + 6 constants, independent of the matrix

    def test_non_int_result_is_refused_by_the_sandbox(self):
        reg = {"rk": (3, lambda x, r, c: 1.0)}
        with self.assertRaises(rp.PredicateRefused):
            rp.parse("rk(1, 3, 3) == 1", reg).evaluate({}, 100)
        reg = {"rk": (3, lambda x, r, c: 1 << 64)}
        with self.assertRaises(rp.PredicateRefused):
            rp.parse("rk(1, 3, 3) == 1", reg).evaluate({}, 100)

    def test_registry_is_per_task_and_mu_checked(self):
        for bad in (1, 4, True, "2", None):
            with self.assertRaises(ValueError):
                T.registry_cd(bad)
        self.assertIsNot(T.registry_cd(3)["rk"][1], T.registry_cd(3)["rk"][1])
        with self.assertRaises(rp.PredicateRefused):
            rp.parse("rk(1, 3, 3) == 1")    # not registered: not a call to a whitelisted function


class CDLemmaTests(unittest.TestCase):
    def test_true_lemmas_hold_and_match_independent_python_mu2(self):
        for kind in T.KINDS_CD:
            t = T.generate_cd(kind, 2, 0, "true")
            self.assertEqual(T.label_cd(t, SL, TOTAL), T.Label(True, None))
            self.assertTrue(all(pure_cd(kind, x, y, 2) for x in range(16) for y in range(16)))

    def test_planted_labels_match_independent_python_mu2(self):
        # the planted source differs from the true one, so compare predicate values pair by pair with the sandbox
        for kind in T.KINDS_CD:
            for seed in range(12):
                t = T.generate_cd(kind, 2, seed, "planted_false")
                p = rp.parse(t.source, T.registry_cd(2))
                L = T.label_cd(t, SL, TOTAL)
                self.assertFalse(L.holds)
                self.assertFalse(p.evaluate({"x": L.counterexample[0], "y": L.counterexample[1]}, SL))

    def test_true_lemmas_hold_mu3_exhaustively(self):
        for kind in T.KINDS_CD:
            self.assertEqual(T.label_cd(T.generate_cd(kind, 3, 0, "true"), SL, TOTAL), T.Label(True, None), kind)
        for x, y in ((0, 0), (1, 8), (73, 292), (511, 511), (341, 170), (7, 56), (7, 7), (1, 2)):
            for kind in T.KINDS_CD:
                self.assertTrue(pure_cd(kind, x, y, 3), (kind, x, y))

    def test_every_mutation_reached_and_false_for_mu_2_3(self):
        for kind in T.KINDS_CD:
            for mu in (2, 3):
                srcs = {T.generate_cd(kind, mu, s, "planted_false").source for s in range(60)}
                self.assertEqual(len(srcs), 4, (kind, mu))
                for src in srcs:
                    L = T.label_cd(T.TaskCD(kind, mu, 0, "planted_false", src), SL, TOTAL)
                    self.assertFalse(L.holds, (kind, mu, src))

    def test_dropping_transversal_is_false_with_a_non_transversal_witness(self):
        t = T.generate_cd("c", 3, 0, "true")
        src = T._sources_cd("c", 3)
        bare = src[src.index(" or ") + 4:]
        L = T.label_cd(t._replace(source=bare), SL, TOTAL)
        self.assertEqual(L, T.Label(False, (1, 1)))     # x = y != 0: rank(x + y) = 0 != 2 rank(x)
        self.assertNotEqual(span_rank(1 ^ 1, 3, 3), 2 * span_rank(1, 3, 3))

    def test_label_ignores_variant_and_kind(self):
        for kind in T.KINDS_CD:
            for v, w in (("true", "planted_false"), ("planted_false", "true")):
                t = T.generate_cd(kind, 2, 1, v)
                self.assertEqual(T.label_cd(t, SL, TOTAL), T.label_cd(t._replace(variant=w), SL, TOTAL))
        a = T.generate_cd("c", 2, 0, "true")
        self.assertFalse(T.label_cd(a._replace(kind="d", source=T.generate_cd("c", 2, 5, "planted_false").source),
                                    SL, TOTAL).holds)

    def test_domain_covers_the_top_pair_and_zero(self):
        for mu in (2, 3):
            top = (1 << (mu * mu)) - 1
            for src, want in ((f"x + y != {2 * top}", (top, top)), ("x + y != 0", (0, 0)), (f"x != {top} or y != 0", (top, 0))):
                L = T.label_cd(T.TaskCD("c", mu, 0, "true", src), SL, TOTAL)
                self.assertEqual(L, T.Label(False, want), src)

    def test_determinism_and_refusals(self):
        for kind in T.KINDS_CD:
            for v in T.VARIANTS:
                self.assertEqual(T.generate_cd(kind, 3, 4, v), T.generate_cd(kind, 3, 4, v))
        self.assertEqual(T.label_cd(T.generate_cd("c", 2, 3, "planted_false"), SL, TOTAL),
                         T.label_cd(T.generate_cd("c", 2, 3, "planted_false"), SL, TOTAL))
        for args in (("a", 2, 0, "true"), ("c", 1, 0, "true"), ("c", 4, 0, "true"), ("c", True, 0, "true"),
                     ("c", 2, True, "true"), ("c", 2, 0, "false"), ("d", 2.0, 0, "true")):
            with self.assertRaises(ValueError, msg=repr(args)):
                T.generate_cd(*args)
        for bad in (None, T.generate_cd("c", 2, 0, "true")._replace(mu=4), T.generate_cd("c", 2, 0, "true")._replace(source=3)):
            with self.assertRaises(ValueError):
                T.label_cd(bad, SL, TOTAL)
        with self.assertRaises(rp.PredicateRefused):
            T.label_cd(T.generate_cd("d", 3, 0, "true"), SL, 100)     # budget refusal, not a label

    def test_sources_are_integer_only_and_fit_the_limits(self):
        for kind in T.KINDS_CD:
            for mu in (2, 3):
                src = T._sources_cd(kind, mu)
                self.assertTrue(src.isascii() and len(src) <= rp.MAX_SOURCE and "/" not in src and "." not in src)
                rp.parse(src, T.registry_cd(mu))


# Mutants of the module itself: each is ONE textual change applied to a COPY of lab/r6_t3_lemmas.py, loaded as a
# separate module; the battery must detect every one.
MUTANTS = {
    "rank_off_by_one": ("        return len(basis)\n", "        return len(basis) + 1\n"),
    "wrong_field_add_not_xor": ("v = min(v, v ^ b)", "v = min(v, v + b)"),
    "zero_rows_counted": ("            if v:\n", "            if True:\n"),
    "last_row_dropped": ("for i in range(r):", "for i in range(r - 1):"),
    "wrong_row_stride": ("(x >> (c * i)) & mask", "(x >> (r * i)) & mask"),
    "wrong_mask": ("mask = (1 << c) - 1", "mask = (1 << r) - 1"),
    "registry_returns_float": ("        return len(basis)\n", "        return float(len(basis))\n"),
    "no_input_bound": (" or not 0 <= x < 1 << (r * c)", ""),
    "shape_cap_plus_one": ("(mu, 2 * mu))", "(mu, 2 * mu), (mu, 2 * mu + 1))"),
    "c_zero_accepted": ("shapes = ((mu, mu),", "shapes = ((mu, 0), (mu, mu),"),
    "rank_capped_at_2": ("        return len(basis)\n", "        return min(len(basis), 2)\n"),
    "r_type_unchecked": ("type(r) is not int or", ""),
    "namespace_leak": ("    return rank_f2\n", "    rank_f2.ns = globals()\n    return rank_f2\n"),
    "wrong_arity_registered": ('"rk": (3, _make_rank(mu))', '"rk": (2, _make_rank(mu))'),
    "transversal_dropped": ('return f"not ({row} and {col}) or {concl}"', "return concl"),
    "constant_changed_c": ('return f"not ({row} and {col}) or {concl}"', 'return f"not ({row} and {col}) or {concl} + 1"'),
    "constant_changed_d": (') <= 4 * {rx} * {ry}"', ') <= 3 * {rx} * {ry}"'),
    "label_taken_from_variant": ('return Label(True, None) if bad is None else Label(False, (bad["x"], bad["y"]))',
                                 'return Label(t.variant == "true", None)'),
    "domain_misses_last_x": ("for x in range(n) for y in range(n)", "for x in range(n - 1) for y in range(n)"),
    "bool_accepted_by_function": ("type(x) is not int or", "type(x) not in (int, bool) or"),
}


def read_source():
    with open(T.__file__, encoding="utf-8") as fh:
        return fh.read()


def load_copy(old, new):
    src = read_source()
    assert src.count(old) == 1, old
    mod = types.ModuleType("r6_t3_copy")
    mod.__file__ = T.__file__
    exec(compile(src.replace(old, new), "r6_t3_copy.py", "exec"), mod.__dict__)
    return mod


def battery(M):
    """Names of the checks that fail on module M (a copy); empty for the real module."""
    bad = []

    def chk(name, fn):
        try:
            if not fn():
                bad.append(name)
        except Exception:
            bad.append(name + "!")

    def brute():
        for mu in (2, 3):
            f = M.registry_cd(mu)["rk"][1]
            if any(f(x, mu, mu) != span_rank(x, mu, mu) for x in range(1 << (mu * mu))):
                return False
            for r, c in ((2 * mu, mu), (mu, 2 * mu)):
                if any(f(x, r, c) != span_rank(x, r, c) for x in range(0, 1 << (r * c), 97)):
                    return False
        return True

    def raises(f, *a):
        try:
            f(*a)
        except rp.PredicateRefused:
            return True
        except TypeError:
            return len(a) != 3    # wrong arity only
        return False

    def refuses():
        f, g = M.registry_cd(3)["rk"][1], M.registry_cd(2)["rk"][1]
        return all(raises(f, *a) for a in ((1 << 20, 3, 3), (-1, 3, 3), (True, 3, 3), (1, 0, 3), (0, 3, 0), (1, 3, 7), (1, 7, 3), (1, 3.0, 3), (1, 3))) \
            and raises(g, 1, 5, 2)

    def clean():
        f = M.registry_cd(3)["rk"][1]
        return (type(f(5, 3, 3)) is int and vars(f) == {} and all(type(c.cell_contents) is tuple for c in f.__closure__)
                and M.registry_cd(3)["rk"][0] == 3)

    def sandbox():
        p = rp.parse("rk(10, 3, 3) == 2", M.registry_cd(3))
        return p.evaluate({}, 100) is True and p.last_steps == 6

    def labels():
        for kind in M.KINDS_CD:
            if M.label_cd(M.generate_cd(kind, 2, 0, "true"), SL, TOTAL).holds is not True:
                return False
            for seed in range(12):
                t = M.generate_cd(kind, 2, seed, "planted_false")
                L = M.label_cd(t, SL, TOTAL)
                if L.holds or L != M.label_cd(t._replace(variant="true"), SL, TOTAL):
                    return False
        return True

    def top():
        L = M.label_cd(M.TaskCD("c", 2, 0, "true", "x + y != 30"), SL, TOTAL)
        return L == M.Label(False, (15, 15))

    def true3_c_spot():
        t = M.generate_cd("c", 3, 0, "true")
        p = rp.parse(t.source, M.registry_cd(3))
        return all(p.evaluate({"x": x, "y": y}, SL) == pure_cd("c", x, y, 3)
                   for x, y in ((1, 8), (1, 1), (73, 292), (511, 511), (7, 56), (7, 7), (1, 2), (0, 0)))

    for name, fn in (("brute", brute), ("refuses", refuses), ("clean", clean), ("sandbox", sandbox), ("labels", labels),
                     ("top", top), ("spot", true3_c_spot)):
        chk(name, fn)
    return bad


class CopyAndMutantTests(unittest.TestCase):
    def test_battery_passes_on_the_unmodified_copy(self):
        src = read_source()
        mod = types.ModuleType("r6_t3_copy")
        exec(compile(src, "r6_t3_copy.py", "exec"), mod.__dict__)
        self.assertEqual(battery(mod), [])
        self.assertEqual(battery(T), [])

    def test_at_least_ten_mutants_and_every_one_is_killed(self):
        self.assertGreaterEqual(len(MUTANTS), 10)
        survivors = []
        for name, (old, new) in MUTANTS.items():
            with self.subTest(mutant=name):
                failed = battery(load_copy(old, new))
                if not failed:
                    survivors.append(name)
                self.assertTrue(failed, name)
        self.assertEqual(survivors, [])

    def test_mutants_are_single_changes_that_really_differ(self):
        src = read_source()
        for name, (old, new) in MUTANTS.items():
            self.assertEqual(src.count(old), 1, name)
            self.assertNotEqual(old, new, name)


if __name__ == "__main__":
    unittest.main()
