import unittest

from lab import r6_predicates as rp
from lab.r6_predicates import PredicateRefused, StepLimitExceeded, parse, check_lemma

BIG = 10000


def ok(src, env=None, limit=BIG):
    return parse(src).evaluate(env or {}, limit)


class ValidTests(unittest.TestCase):
    def test_arith_and_compare(self):
        self.assertIs(ok("x + 2 * y == 8", {"x": 2, "y": 3}), True)
        self.assertIs(ok("1 < x <= 3", {"x": 3}), True)
        self.assertIs(ok("1 < x < 3", {"x": 3}), False)
        self.assertIs(ok("(x >> 1) & 1 == 1", {"x": 6}), True)
        self.assertIs(ok("~x == -6", {"x": 5}), True)
        self.assertIs(ok("x // 2 + x % 2 == 3", {"x": 5}), True)
        self.assertIs(ok("not (x and y) or (x ^ y) == 1", {"x": 1, "y": 1}), False)
        self.assertIs(ok("x == 1 and y == 2", {"x": 1, "y": 2}), True)
        self.assertIs(ok("x == 1 and y == 3", {"x": 1, "y": 2}), False)
        self.assertIs(ok("x == 0 or y == 2", {"x": 1, "y": 2}), True)
        self.assertIs(ok("x == 0 or y == 3", {"x": 1, "y": 2}), False)
        self.assertIs(ok("(1 if x else 2) == 2", {"x": 0}), True)

    def test_helpers(self):
        self.assertIs(ok("popcount(x) == 3 and bit(x, 0) == 1", {"x": 7}), True)
        self.assertIs(ok("max(x, 3) - min(x, 3) == abs(x - 3)", {"x": 9}), True)

    def test_quantifiers(self):
        self.assertIs(ok("all(popcount(i) <= i for i in range(1, 16))"), True)
        self.assertIs(ok("any(i * i == 49 for i in range(10))"), True)
        self.assertIs(ok("sum(bit(x, i) for i in range(8)) == popcount(x)", {"x": 201}), True)
        self.assertIs(ok("all(i != j for i in range(4) for j in range(4))"
                         if False else "all(all(i + j == j + i for j in range(4)) for i in range(4))"), True)
        self.assertIs(ok("max(i for i in range(5) if i < 3) == 2"), True)
        self.assertIs(ok("all([i < 3 for i in range(3)])"), True)

    def test_names(self):
        self.assertEqual(parse("all(i < n for i in range(n)) and x").names, {"n", "x"})

    def test_result_must_be_bool(self):
        for s in ("x + 1", "x and 5"):
            with self.assertRaises(PredicateRefused):
                ok(s, {"x": 1})

    def test_missing_or_bad_env(self):
        for env in ({}, {"x": "1"}, {"x": 1.0}, {"x": None}, {"x": 1 << 64}):
            with self.assertRaises(PredicateRefused):
                parse("x == 1").evaluate(env, BIG)
        with self.assertRaises(PredicateRefused):
            parse("x == 1").evaluate([("x", 1)], BIG)

    def test_runtime_errors_refused(self):
        for s in ("x // 0 == 1", "x % 0 == 1", "1 << -1 == 0", "x >> -1 == 0", "popcount(-1) == 1",
                  "bit(x, 64) == 0", "bit(x, -1) == 0", "x << 65 == 0"):
            with self.assertRaises(PredicateRefused, msg=s):
                ok(s, {"x": 1})


class WhitelistViolationTests(unittest.TestCase):
    BAD = [
        "x.real == 1", "(1).bit_length() == 1", "x[0] == 1", "x ** 2 == 4", "x @ y",
        "x in (1, 2)", "x is 1", "x is not None", "(1, 2) == (1, 2)", "[1] == [1]", "{1} == {1}",
        "{1: 2} == {}", "'a' == 'a'", "b'a' == b'a'", "1.5 == 1.5", "1j == 1j", "None == None",
        "... == ...", "lambda: 1", "(lambda: 1)() == 1", "(y := 1) == 1", "f'{x}' == '1'",
        "x == 1; y == 2", "import os", "x if", "", "   ", "print(x)", "len([1]) == 1",
        "int(x) == 1", "str(x) == 1", "range(3) == range(3)", "popcount == popcount",
        "all(x)", "sum(1, 2) == 3", "all(i for i in range(3) for j in range(3) for k in range(3))"
        if False else "any(i for i, j in range(3))", "all(i for i in [1, 2])", "all(i for i in x)",
        "all(i for i in range(3), 1)", "sum(*[1]) == 1", "all(i for i in range(3) async)" if False else "min(*[1, 2]) == 1",
        "popcount(x=1) == 1", "(x for x in range(3))", "[i for i in range(3)]", "{i for i in range(3)}",
        "all(i for i in range(3) if (j := 1))", "await x", "x if y else", "-x.real",
        "all(popcount for popcount in range(3))", "all(i for x.a in range(3))",
        "x == y == z.q", "x if y else z.__class__", "min(x, [1]) == 1", "popcount(*x) == 1",
        "popcount(i for i in range(3)) == 1", "abs(all(i for i in range(2))) == 1 and (x)[0]",
    ]

    def test_bad_syntax_and_nodes(self):
        for s in self.BAD:
            with self.subTest(s=s):
                with self.assertRaises(PredicateRefused):
                    parse(s)

    def test_non_str_and_size(self):
        for s in (None, 5, b"x == 1"):
            with self.assertRaises(PredicateRefused):
                parse(s)
        with self.assertRaises(PredicateRefused):
            parse("x == 1 " + " " * rp.MAX_SOURCE)
        with self.assertRaises(PredicateRefused):
            parse("x == " + "1 + " * 600 + "1")  # over size limit

    def test_integer_constant_limit(self):
        parse("x == %d" % ((1 << 64) - 1))
        with self.assertRaises(PredicateRefused):
            parse("x == %d" % (1 << 64))
        with self.assertRaises(PredicateRefused):
            parse("x == -%d" % (1 << 64))

    def test_depth_limit(self):
        parse("x" + " + 1" * 50 + " > 0")  # left-deep chain evaluates at depth 50
        with self.assertRaises(PredicateRefused):
            parse("x == " + "(" * 40 + "1" + ")" * 40 + " + " + "-" * 100 + "1")
        with self.assertRaises(PredicateRefused):
            parse("x == " + "-" * 1000 + "1")


class EscapeTests(unittest.TestCase):
    ATTACKS = [
        "__import__('os').system('true')", "__import__('os')", "().__class__.__bases__[0].__subclasses__()",
        "x.__class__.__mro__", "''.__class__", "getattr(x, '__class__')", "getattr(1, 'real')",
        "eval('1')", "exec('1')", "compile('1', 'a', 'eval')", "open('/etc/passwd')", "globals()",
        "locals()", "vars()", "dir()", "breakpoint()", "input()", "__builtins__", "__builtins__['eval']('1')",
        "x.__globals__", "print.__self__", "(lambda: 0).__globals__", "[c for c in ().__class__.__base__.__subclasses__()]",
        "'%s' % x", "'{0.__class__}'.format(x)", "f'{x.__class__}'", "f'{__import__(\"os\")}'",
        "(y := __import__('os'))", "__debug__", "type(x)", "super()", "chr(65) == 'A'",
        "ord('a') == 97", "bit_length(x)", "x.bit_length()", "True.__class__", "(1).__add__(2)",
        "_ == 1", "_x == 1", "x_ == 1 and __name__", "__x__", "all(__i for __i in range(3))",
        "all(i.real for i in range(3))", "all(__import__ for i in range(3))",
    ]

    def test_all_refused_at_parse(self):
        for s in self.ATTACKS:
            with self.subTest(s=s):
                with self.assertRaises(PredicateRefused):
                    parse(s)

    def test_unicode_lookalikes(self):
        for s in ("ｘ == 1", "x​ == 1", "х == 1", "all(ι for ι in range(3))",
                  "＿＿import＿＿('os')", "x == 1  ", "pоpcount(x) == 1",
                  "x == ١", "x́ == 1", "\U0001d429opcount(x) == 1"):
            with self.subTest(s=repr(s)):
                with self.assertRaises(PredicateRefused):
                    parse(s)

    def test_nul_and_odd_whitespace(self):
        for s in ("x == 1\x00", "x ==\x001"):
            with self.assertRaises(PredicateRefused):
                parse(s)

    def test_names_are_not_helpers_or_shadow(self):
        for s in ("range == 1", "all == 1", "all(range for range in range(3))",
                  "all(all for i in range(3))", "min == 1"):
            with self.assertRaises(PredicateRefused):
                parse(s)

    def test_env_cannot_smuggle_helpers(self):
        # a variable named like a helper is a refused name, so env cannot shadow helpers
        with self.assertRaises(PredicateRefused):
            parse("popcount == 1")

    def test_huge_ints_refused(self):
        p = parse("(x << 60) << 60 == 0")
        with self.assertRaises(PredicateRefused):
            p.evaluate({"x": 1}, BIG)
        for s in ("x * x * x == 0", "x << 64 == 0", "(x + x) * (x + x) * x == 0", "-(x << 63) * 4 == 0"):
            with self.assertRaises(PredicateRefused, msg=s):
                ok(s, {"x": (1 << 63) + 1})
        self.assertIs(ok("x << 63 > 0", {"x": 1}), True)
        self.assertIs(ok("x * x == 1", {"x": (1 << 32) - 1}), False)
        with self.assertRaises(PredicateRefused):
            ok("sum(1 << 63 for i in range(4)) > 0")  # sum overflows 64 bits

    def test_step_bombs(self):
        bombs = [
            "all(sum(1 for j in range(60000) if j > i) > 0 for i in range(60000))",
            "any(all(any(all(i + j > 1000 for j in range(300)) for k in range(300)) for i in range(300)) for m in range(300))",
            "sum(i for i in range(65536)) < 0 and all(i < 0 for i in range(65536))",
        ]
        for s in bombs:
            with self.subTest(s=s[:40]):
                with self.assertRaises(StepLimitExceeded):
                    ok(s, limit=50000)

    def test_shift_guard_and_iter_form(self):
        with self.assertRaises(PredicateRefused):
            ok("x << 65 == 0", {"x": 0})
        for s in ("any(i for i in popcount(3))", "any(i for i in min(3, 4))", "all(i for i in abs(3))"):
            with self.assertRaises(PredicateRefused, msg=s):
                parse(s)

    def test_range_cap(self):
        parse("any(i > 3 for i in range(65536))").evaluate({}, 1 << 22)
        with self.assertRaises(PredicateRefused):
            ok("any(i > 70000 for i in range(65537))", limit=1 << 22)
        with self.assertRaises(PredicateRefused):
            ok("any(i < 0 for i in range(10000000000))", limit=1 << 22)

    def test_recursion_does_not_leak(self):
        for src in ("x" + " + 1" * 400 + " > 0", "x == " + "-" * 900 + "1", "x == " + "(" * 250 + "1" + ")" * 250):
            with self.assertRaises(PredicateRefused):
                parse(src)

    def test_refusal_returns_no_value_and_never_true(self):
        for s, env in (("x // 0 == 0", {"x": 1}), ("all(i < 0 for i in range(10 ** 6))", {})):
            try:
                v = parse(s).evaluate(env, 100)
            except PredicateRefused:
                continue
            self.fail("returned %r" % (v,))

    def test_bad_step_limits(self):
        p = parse("x == 1")
        for lim in (-1, True, 1.5, None, "5", rp.MAX_STEPS + 1):
            with self.assertRaises(PredicateRefused, msg=repr(lim)):
                p.evaluate({"x": 1}, lim)
        p.evaluate({"x": 1}, rp.MAX_STEPS)

    def test_unexpected_exception_is_refusal_not_true(self):
        # an exception inside the evaluator (here a hostile int subclass is impossible,
        # so force one via a mapping whose .get raises) must surface as PredicateRefused
        class Boom(dict):
            def get(self, *a):
                raise RuntimeError("boom")
        with self.assertRaises(PredicateRefused):
            parse("x == 1").evaluate(Boom(x=1), BIG)


class StepCountTests(unittest.TestCase):
    def test_exact_step_counts(self):
        # nodes: Compare, Constant 1, Constant 1 -> 3
        self.assertEqual(parse("1 == 1").run({}, 100), (True, 3))
        # Compare, BinOp, x, 1, 2 -> 5
        self.assertEqual(parse("x + 1 == 2").run({"x": 1}, 100), (True, 5))
        # Call, then per iteration 1 + Compare, i, 5 (4 steps): 1 + 3*4 = 13, plus bounds Constant 3
        self.assertEqual(parse("all(i < 5 for i in range(3))").run({}, 100), (True, 1 + 1 + 3 * 4))
        # short-circuit: all stops after first False: 1 call + 1 bound + 1 iter(4)
        self.assertEqual(parse("all(i > 5 for i in range(3))").run({}, 100), (False, 1 + 1 + 4))

    def test_deterministic(self):
        p = parse("all(popcount(i) <= i for i in range(1, 16)) and x > 0")
        runs = {p.run({"x": 3}, BIG)[1] for _ in range(5)}
        self.assertEqual(len(runs), 1)
        self.assertEqual(p.last_steps, runs.pop())

    def test_limit_boundary_is_exact(self):
        p = parse("x + 1 == 2")
        self.assertEqual(p.run({"x": 1}, 5), (True, 5))
        with self.assertRaises(StepLimitExceeded):
            p.run({"x": 1}, 4)
        with self.assertRaises(StepLimitExceeded):
            parse("1 == 1").run({}, 0)

    def test_loop_iteration_limit_boundary(self):
        p = parse("all(True for i in range(3))")  # call 1 + bound 1 + 3 * (iter 1 + const 1)
        self.assertEqual(p.run({}, 8), (True, 8))
        with self.assertRaises(StepLimitExceeded):
            p.run({}, 7)

    def test_condition_steps_counted(self):
        p = parse("sum(1 for i in range(4) if i > 1) == 2")
        # Compare 1 + Call 1 + bound 1 + 4 iters * (1 + cond 3) + 2 elts * 1 + const 1 = 22
        self.assertEqual(p.run({}, BIG), (True, 22))


class CheckLemmaTests(unittest.TestCase):
    def test_true_lemma(self):
        p = parse("popcount(x) <= 4")
        self.assertIsNone(check_lemma(p, ({"x": v} for v in range(16)), 100, 10 ** 6))

    def test_first_counterexample(self):
        p = parse("popcount(x) <= 2")
        self.assertEqual(check_lemma(p, ({"x": v} for v in range(16)), 100, 10 ** 6), {"x": 7})

    def test_empty_domain(self):
        self.assertIsNone(check_lemma(parse("x == 1"), iter(()), 10, 10 ** 6))

    def test_refusal_propagates(self):
        with self.assertRaises(PredicateRefused):
            check_lemma(parse("x // y == 0"), [{"x": 1, "y": 0}], 100, 10 ** 6)
        with self.assertRaises(StepLimitExceeded):
            check_lemma(parse("x == 1"), [{"x": 1}], 1, 10 ** 6)

    def test_stops_at_first(self):
        seen = []

        def dom():
            for v in range(10):
                seen.append(v)
                yield {"x": v}
        check_lemma(parse("x < 3"), dom(), 100, 10 ** 6)
        self.assertEqual(seen, [0, 1, 2, 3])

    def test_truth_table_lemma(self):
        # all 2-input truth tables f (4 bits): bit-reversal-free sanity lemma
        p = parse("popcount(f) + popcount(15 ^ f) == 4")
        self.assertIsNone(check_lemma(p, ({"f": f} for f in range(16)), 200, 10 ** 6))
        q = parse("popcount(f) != 2")
        self.assertEqual(check_lemma(q, ({"f": f} for f in range(16)), 200, 10 ** 6), {"f": 3})


class TotalBudgetTests(unittest.TestCase):
    def test_cheap_per_element_expensive_overall(self):
        p = parse("x >= 0")  # 3 steps per element
        dom = ({"x": v} for v in range(1000))
        with self.assertRaises(StepLimitExceeded) as cm:
            check_lemma(p, dom, 100, 50)
        self.assertEqual(cm.exception.env, {"x": 16})
        self.assertEqual(cm.exception.steps, 48)

    def test_total_exact_boundary(self):
        p = parse("x >= 0")
        self.assertIsNone(check_lemma(p, ({"x": v} for v in range(10)), 100, 30))
        with self.assertRaises(StepLimitExceeded):
            check_lemma(p, ({"x": v} for v in range(10)), 100, 29)

    def test_total_required_and_validated(self):
        p = parse("x >= 0")
        with self.assertRaises(TypeError):
            check_lemma(p, [{"x": 1}], 100)
        for bad in (-1, True, 1.5, None):
            with self.assertRaises(PredicateRefused):
                check_lemma(p, [{"x": 1}], 100, bad)

    def test_step_limit_type_validated(self):
        p = parse("x >= 0")
        for bad in (None, "5", 1.5, True, -1, rp.MAX_STEPS + 1):
            with self.assertRaises(PredicateRefused, msg=repr(bad)):
                check_lemma(p, [{"x": 1}], bad, 100)

    def test_exception_carries_env_and_steps(self):
        p = parse("x // y == 0")
        with self.assertRaises(PredicateRefused) as cm:
            check_lemma(p, [{"x": 0, "y": 1}, {"x": 1, "y": 0}], 100, 1000)
        self.assertEqual(cm.exception.env, {"x": 1, "y": 0})
        self.assertEqual(cm.exception.steps, 5)

    def test_per_element_limit_still_applies(self):
        with self.assertRaises(StepLimitExceeded) as cm:
            check_lemma(parse("x >= 0"), [{"x": 1}], 2, 1000)
        self.assertEqual(cm.exception.env, {"x": 1})


class RegistryTests(unittest.TestCase):
    REG = {"sq": (1, lambda a: a * a), "add3": (3, lambda a, b, c: a + b + c)}

    def test_default_empty(self):
        with self.assertRaises(PredicateRefused):
            parse("sq(x) == 4")

    def test_toy_function(self):
        p = parse("sq(x) == 4 and add3(1, 2, x) == 5", self.REG)
        self.assertIs(p.evaluate({"x": 2}, BIG), True)
        self.assertIs(parse("all(sq(i) >= i for i in range(5))", self.REG).evaluate({}, BIG), True)

    def test_arity_and_forms_checked(self):
        for s in ("sq(1, 2) == 1", "sq() == 1", "sq(*x) == 1", "sq(x=1) == 1", "sq == 1",
                  "sq(i for i in range(2)) == 1", "all(sq for sq in range(2))"):
            with self.assertRaises(PredicateRefused, msg=s):
                parse(s, self.REG)

    def test_result_checked(self):
        p = parse("sq(x) == 0", {"sq": (1, lambda a: 1 << 70)})
        with self.assertRaises(PredicateRefused):
            p.evaluate({"x": 1}, BIG)
        p = parse("sq(x) == 0", {"sq": (1, lambda a: "s")})
        with self.assertRaises(PredicateRefused):
            p.evaluate({"x": 1}, BIG)
        p = parse("sq(x) == 0", {"sq": (1, lambda a: 1 / 0)})
        with self.assertRaises(PredicateRefused):
            p.evaluate({"x": 1}, BIG)

    def test_registered_call_costs_one_step(self):
        p = parse("sq(x) == 4", self.REG)
        self.assertEqual(p.run({"x": 2}, BIG)[1], 4)  # Compare, Call, x, Constant: the call is one step
        self.assertIn("bounded-cost", rp.__doc__)
        self.assertIn("registrar", rp.__doc__)

    def test_bad_registry(self):
        for r in ({"__x": (1, abs)}, {"all": (1, abs)}, {"f": abs}, {"f": (1, 5)}, {"f": (-1, abs)},
                  {"f": (True, abs)}, {"f ": (1, abs)}, {1: (1, abs)}):
            with self.assertRaises(PredicateRefused, msg=repr(r)):
                parse("x == 1", r)


class MinorFixTests(unittest.TestCase):
    def test_bool_env_encoding_is_int(self):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            self.assertEqual(parse("~x == -2").evaluate({"x": True}, BIG), True)
            self.assertEqual(parse("~x == -1").evaluate({"x": False}, BIG), True)

    def test_last_steps_reset_on_refusal(self):
        p = parse("x // y == 0")
        p.run({"x": 0, "y": 1}, 100)
        self.assertIsNotNone(p.last_steps)
        with self.assertRaises(PredicateRefused):
            p.run({"x": 1, "y": 0}, 100)
        self.assertIsNone(p.last_steps)

    def test_missing_variable_message_sorted(self):
        p = parse("c + b + a == 0")
        with self.assertRaises(PredicateRefused) as cm:
            p.evaluate({}, BIG)
        self.assertIn("variable a", str(cm.exception))

    def test_depth_limit_boundary_documented(self):
        parse("x" + " + 1" * 59 + " > 0")
        with self.assertRaises(PredicateRefused):
            parse("x" + " + 1" * 61 + " > 0")


if __name__ == "__main__":
    unittest.main()
