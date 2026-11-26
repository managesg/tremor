import itertools
import unittest

from lab import r6_f1_tasks as F
from lab import r6_scorecard


def brute(formula):
    """Independent slow oracle: test every assignment against every clause."""
    mask = 0
    for i in range(1 << formula.n):
        if all(any(bool(i >> (abs(x) - 1) & 1) == (x > 0) for x in c) for c in formula.clauses):
            mask |= 1 << i
    return mask


def excluding(n, a):
    """Clause over x1..x3 that is false exactly on the assignments whose first 3 bits equal a's."""
    return tuple(-v if a >> (v - 1) & 1 else v for v in (1, 2, 3))


class HandCheckedTests(unittest.TestCase):
    def test_unsat(self):
        clauses = tuple(excluding(3, a) for a in range(8))
        f = F.Formula(3, clauses)
        self.assertEqual(F.solve(f), 0)
        self.assertEqual(F.model_count(f), 0)
        self.assertTrue(F.check_count(f, 0))
        self.assertFalse(F.check_count(f, 1))

    def test_exactly_one_model(self):
        f = F.Formula(3, tuple(excluding(3, a) for a in range(8) if a != 5))
        self.assertEqual(F.solve(f), 1 << 5)
        self.assertTrue(F.check_witness(f, (1, 0, 1)))
        for other in itertools.product((0, 1), repeat=3):
            self.assertEqual(F.check_witness(f, other), other == (1, 0, 1))
        self.assertTrue(F.check_count(f, 1))

    def test_single_clauses(self):
        self.assertEqual(F.solve(F.Formula(3, ((1, 2, 3),))), 0b11111110)  # only the all-false assignment fails
        self.assertEqual(F.solve(F.Formula(3, ((-1, -2, -3),))), 0b01111111)
        self.assertEqual(F.solve(F.Formula(3, ((1, 2, 3), (-1, -2, -3)))), 0b01111110)
        self.assertEqual(F.solve(F.Formula(4, ((1, 2, 3),))).bit_count(), 14)

    def test_mixed_signs_on_four_variables(self):
        # (x1 or not x2 or x4) and (not x1 or x3 or not x4): enumerated by hand
        f = F.Formula(4, ((1, -2, 4), (-1, 3, -4)))
        self.assertEqual(F.model_count(f), 16 - 2 - 2 + 0)  # each clause kills 2; they cannot both fail (x1 differs)
        self.assertFalse(F.check_witness(f, (0, 1, 0, 0)))  # first clause false
        self.assertFalse(F.check_witness(f, (1, 0, 0, 1)))  # second clause false
        self.assertTrue(F.check_witness(f, (1, 0, 1, 1)))

    def test_n20_single_clause_count_and_speed(self):
        f = F.Formula(20, ((1, 10, 20),))
        self.assertEqual(F.model_count(f), 2**20 - 2**17)


class GeneratorTests(unittest.TestCase):
    def test_deterministic_and_wellformed(self):
        a = F.generate(12, 40, 7)
        self.assertEqual(a, F.generate(12, 40, 7))
        self.assertNotEqual(a, F.generate(12, 40, 8))
        self.assertNotEqual(a.clauses, F.generate(13, 40, 7).clauses)
        self.assertEqual((a.n, len(a.clauses)), (12, 40))
        for c in a.clauses:
            self.assertEqual(len(c), 3)
            self.assertEqual(len({abs(x) for x in c}), 3)
            self.assertTrue(all(1 <= abs(x) <= 12 for x in c))
        self.assertTrue(any(x < 0 for c in a.clauses for x in c) and any(x > 0 for c in a.clauses for x in c))

    def test_pinned_instance(self):
        # pins the seed derivation (task_seed of "gen-F1:n:m", seed, 0), so a changed stream is caught
        self.assertEqual(F.generate(5, 3, 0).clauses, PINNED_CLAUSES)

    def test_parameters_are_explicit_and_checked(self):
        with self.assertRaises(TypeError):
            F.generate(5, 3)
        for args in ((2, 3, 0), (21, 3, 0), (5, 0, 0), (5, -1, 0), (5, F.M_MAX + 1, 0), (5, 3, 2**63), (5, 3, -2**63 - 1), (True, 3, 0), (5, True, 0), (5, 3, True),
                     (5.0, 3, 0), (5, 3.0, 0), (5, 3, "0"), (None, 3, 0)):
            with self.assertRaises(ValueError, msg=str(args)):
                F.generate(*args)
        self.assertEqual(F.M_MAX, 4000)
        F.generate(3, 1, 0)
        F.generate(5, F.M_MAX, 2**63 - 1)
        F.generate(5, 3, -2**63)
        F.generate(20, 1, 0)


class SeedCopyTests(unittest.TestCase):
    def test_equals_l3_task_seed(self):
        from lab.l3c_harness import task_seed
        for i in range(50):
            args = (f"gen-F1:{i}:{i * 7}" if i % 2 else "t", (i - 25) * 10**15 + i, i * 3)
            self.assertEqual(F._task_seed(*args), task_seed(*args))
        for bad in (("", 0, 0), (1, 0, 0), ("t", True, 0), ("t", 0, -1), ("t", 0, 10**12 + 1), ("t", 2**63, 0)):
            with self.assertRaises(ValueError):
                F._task_seed(*bad)


class SolveAgreementTests(unittest.TestCase):
    def test_brute_force_agreement_small_n(self):
        seen_sat = seen_unsat = 0
        for n in range(3, 11):
            for seed in range(6):
                for m in (1, 2 * n, 4 * n, 6 * n):
                    f = F.generate(n, m, seed)
                    got = F.solve(f)
                    self.assertEqual(got, brute(f), (n, m, seed))
                    seen_sat += got != 0
                    seen_unsat += got == 0
        self.assertGreater(seen_sat, 20)
        self.assertGreater(seen_unsat, 5)

    def test_count_n16_against_slow_path(self):
        for seed, m in ((1, 40), (2, 75)):
            f = F.generate(16, m, seed)
            slow = sum(all(any(bool(i >> (abs(x) - 1) & 1) == (x > 0) for x in c) for c in f.clauses)
                       for i in range(1 << 16))
            self.assertEqual(F.model_count(f), slow)
            self.assertTrue(F.check_count(f, slow))
            self.assertFalse(F.check_count(f, slow + 1))
            self.assertFalse(F.check_count(f, slow - 1 if slow else 1))

    def test_n20_witnesses_agree_with_mask(self):
        f = F.generate(20, 85, 3)
        mask = F.solve(f)
        self.assertEqual(mask.bit_count(), F.model_count(f))
        sat_i = (mask & -mask).bit_length() - 1
        bits = lambda i: tuple(i >> v & 1 for v in range(20))
        self.assertTrue(F.check_witness(f, bits(sat_i)))
        unsat_i = next(i for i in range(1 << 20) if not mask >> i & 1)
        self.assertFalse(F.check_witness(f, bits(unsat_i)))

    def test_witness_matches_mask_everywhere_small(self):
        f = F.generate(8, 30, 5)
        mask = F.solve(f)
        for i in range(256):
            self.assertEqual(F.check_witness(f, tuple(i >> v & 1 for v in range(8))), bool(mask >> i & 1))


class PromptTests(unittest.TestCase):
    F0 = F.Formula(4, ((1, -2, 4), (-1, 3, -4)))

    def test_exact_text(self):
        self.assertEqual(
            F.render_prompt(self.F0, "count"),
            "Below is a Boolean formula in conjunctive normal form over variables x1..x4. "
            "It is the AND of the 2 clauses listed, one per line; each clause is the OR of its three literals.\n\n"
            "(x1 OR NOT x2 OR x4)\n(NOT x1 OR x3 OR NOT x4)\n\n"
            "Task: count the assignments of x1..x4 (out of 2^4) that satisfy every clause. "
            "Answer on one line as 'COUNT: ' followed by a non-negative decimal integer.\n")
        sat = F.render_prompt(self.F0, "sat")
        self.assertIn("'WITNESS: ' followed by exactly 4 characters", sat)
        self.assertTrue(sat.endswith("If no assignment satisfies every clause, answer 'WITNESS: NONE'.\n"))
        self.assertNotIn("NONE", F.render_prompt(self.F0, "count"))
        self.assertNotEqual(sat, F.render_prompt(self.F0, "count"))

    def test_stable_bytes_and_hash(self):
        a = F.render_prompt(F.generate(9, 20, 4), "sat")
        self.assertEqual(a, F.render_prompt(F.generate(9, 20, 4), "sat"))
        self.assertTrue(a.isascii())
        self.assertEqual(F.prompt_sha256(self.F0, "sat"), PINNED_SAT_SHA)
        self.assertEqual(F.prompt_sha256(self.F0, "count"), PINNED_COUNT_SHA)
        self.assertNotEqual(F.prompt_sha256(self.F0, "sat"), F.prompt_sha256(F.Formula(4, ((1, -2, 4), (-1, 3, 4))), "sat"))

    def test_refusals(self):
        for kind in ("", "SAT", "unsat", None, 1):
            with self.assertRaises(ValueError):
                F.render_prompt(self.F0, kind)
        with self.assertRaises(ValueError):
            F.render_prompt(((1, 2, 3),), "sat")


class SatClaimTests(unittest.TestCase):
    unsat = F.Formula(3, tuple(excluding(3, a) for a in range(8)))
    one = F.Formula(3, tuple(excluding(3, a) for a in range(8) if a != 5))

    def test_none_and_witness(self):
        self.assertTrue(F.check_sat_claim(self.unsat, "NONE"))
        for w in itertools.product((0, 1), repeat=3):
            self.assertFalse(F.check_sat_claim(self.unsat, w))
        self.assertFalse(F.check_sat_claim(self.one, "NONE"))
        self.assertTrue(F.check_sat_claim(self.one, (1, 0, 1)))
        self.assertFalse(F.check_sat_claim(self.one, (1, 1, 1)))
        self.assertTrue(F.check_sat_claim(self.one, [1, 0, 1]))

    def test_generated_unsat_instance_exists_and_none_is_right(self):
        f = next(g for g in (F.generate(3, 40, s) for s in range(50)) if F.solve(g) == 0)
        self.assertTrue(F.check_sat_claim(f, "NONE"))

    def test_refusals(self):
        for bad in ("none", "None", "1011", "", None, 5, (True, False, True), (1, 0), b"NONE"):
            with self.assertRaises(ValueError, msg=repr(bad)):
                F.check_sat_claim(self.one, bad)


class RefusalTests(unittest.TestCase):
    f = F.Formula(4, ((1, -2, 4), (-1, 3, -4)))

    def test_witness_refusals(self):
        good = (1, 0, 1, 1)
        self.assertTrue(F.check_witness(self.f, good))
        self.assertTrue(F.check_witness(self.f, list(good)))
        for bad in ((True, False, True, True), (1, 0, 1), (1, 0, 1, 1, 0), (1, 0, 1, 2), (1, 0, 1, -1),
                    (1, 0, 1, 1.0), (1, 0, 1, "1"), "1011", 11, None, (1, 0, 1, None), ()):
            with self.assertRaises(ValueError, msg=repr(bad)):
                F.check_witness(self.f, bad)

    def test_count_refusals(self):
        self.assertTrue(F.check_count(self.f, 12))
        self.assertFalse(F.check_count(self.f, 11))
        for bad in (True, False, -1, 17, 12.0, "12", None, 2**64):
            with self.assertRaises(ValueError, msg=repr(bad)):
                F.check_count(self.f, bad)
        self.assertFalse(F.check_count(F.Formula(3, tuple(excluding(3, a) for a in range(8))), 1))

    def test_malformed_formulas_refused(self):
        for bad in (F.Formula(2, ((1, 2, 1),)), F.Formula(3, ((1, 1, 2),)), F.Formula(3, ((1, 2, 4),)),
                    F.Formula(3, ((0, 1, 2),)), F.Formula(3, ((1, 2),)), F.Formula(3, ()), F.Formula(21, ((1, 2, 3),)),
                    F.Formula(3, ([1, 2, 3],)), F.Formula(3, ((True, 2, 3),)), F.Formula(True, ((1, 2, 3),)),
                    F.Formula(3, [(1, 2, 3)])):
            for fn in (F.solve, F.model_count):
                with self.assertRaises(ValueError, msg=repr(bad)):
                    fn(bad)
        with self.assertRaises(ValueError):
            F.check_witness(F.Formula(3, ((1, 2, 4),)), (1, 1, 1))


class PerformanceRowTests(unittest.TestCase):
    def errors(self, row):
        e = []
        r6_scorecard._walk("performance_row", row, r6_scorecard._SPEC["performance_row"], e)
        return e

    def test_matches_scorecard_schema(self):
        row = F.performance_row("F1-n12-0", 12, 2, 3, True, 0.75)
        self.assertEqual(row, {"task": "F1-n12-0", "family": "F1", "n": 12, "rerun": 2, "agent": 3, "pass": 1,
                               "conf": 0.75})
        self.assertEqual(self.errors(row), [])
        row0 = F.performance_row("t", 0, 0, 0, False, None)
        self.assertEqual((row0["pass"], row0["conf"]), (0, None))
        self.assertIs(type(row0["pass"]), int)
        self.assertEqual(self.errors(row0), [])
        self.assertEqual(set(row), set(r6_scorecard._SPEC["performance_row"]))
        self.assertTrue(self.errors(dict(row, **{"pass": True})))  # the schema refuses a bool pass

    def test_refusals(self):
        for args in ((1, 12, 0, 0, True, None), ("t", True, 0, 0, True, None), ("t", -1, 0, 0, True, None),
                     ("t", 1, -1, 0, True, None), ("t", 1, 0, 1.5, True, None), ("t", 1, 0, 0, 1, None),
                     ("t", 1, 0, 0, True, 1.5), ("t", 1, 0, 0, True, -0.1), ("t", 1, 0, 0, True, True),
                     ("t", 1, 0, 0, True, "0.5")):
            with self.assertRaises(ValueError, msg=repr(args)):
                F.performance_row(*args)


PINNED_CLAUSES = ((-3, -2, -1), (2, -5, -4), (3, 4, -5))
PINNED_SAT_SHA = "b36f0a2a3fcffde88887f6a636e28a55469d7937502ed628c004f41b5774f75e"
PINNED_COUNT_SHA = "aa607059157384de6b906e1b9eb8d314f34903c118c910f02e92943260cc37f5"

if __name__ == "__main__":
    unittest.main()
