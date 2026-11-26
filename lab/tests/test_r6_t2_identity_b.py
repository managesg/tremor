# helper work (Cursor), Opus-reviewed; adopted by the lane with these changes:
# (1) mutated copies live in a tempfile.TemporaryDirectory made in setUpClass and
#     removed in tearDownClass; nothing is written next to the test.
# (2) SRC_PATH is mod.__file__ (the module under test).
# (3) imports as `from lab import r6_t2_identity_b as mod` (PYTHONPATH=src:lab:tests:.).
# (4) new tests: x11 - x12 agrees with itself over F_3 and not with x12 - x11;
#     len(poly2.terms()) == 2 in test_sum_square_field_arithmetic.
# (5) every agrees_on_01 / identical_as_polynomials call passes gate_limit.
# (6) integer seeds only: seed '1' is refused, with a test.
# (7) a mutant counts as killed only on AssertionError; any other exception (or an
#     import crash) is reported as "broken mutant, not killed" and fails the test.
# (+) two reviewer survivors added as mutants 13 (swapped 0/1 subtraction) and
#     14 (zero filter removed in multiplication); mutants 07 and 11 pass gate_limit.
# Source sha256 3318a2f6c3ff4f1d1c32f6528d3fe724ef339ea546922ec593b5d24ad5e5138f.
"""Tests for the T2 identity checker, implementation B."""

import hashlib
import importlib.util
import os
import tempfile
import unittest

from lab import r6_t2_identity_b as mod

SRC_PATH = mod.__file__

EXPECT = {
    "correct": (True, True),
    "agrees_not_identical": (True, False),
    "wrong_coefficient": (False, False),
    "wrong_on_01": (False, False),
}


def _poly_at(poly, bits, p):
    total = 0
    for exp, coeff in poly.terms():
        acc = coeff
        for k, power in enumerate(exp):
            if power and ((bits >> k) & 1) == 0:
                acc = 0
                break
        total += acc
    return total % p


def _tag_digest(m, p, kind, seed):
    tag = "t2b|%s|%s|%s|%s" % (m, p, kind, seed)
    return hashlib.sha256(tag.encode("utf-8")).digest()


class TestTargets(unittest.TestCase):
    def test_perm2_hand(self):
        for p in (2, 3):
            target = mod.perm_target(2, p)
            self.assertEqual(target.coeff((1, 0, 0, 1)), 1)
            self.assertEqual(target.coeff((0, 1, 1, 0)), 1)
            self.assertEqual(target.coeff((1, 1, 0, 0)), 0)
            self.assertEqual(target.coeff((0, 0, 0, 0)), 0)
            self.assertEqual(len(target.terms()), 2)
            self.assertEqual(target.terms(), target.terms())

    def test_perm2_matches_hand_evaluation(self):
        for p in (2, 3):
            target = mod.perm_target(2, p)
            for bits in range(16):
                x11 = (bits >> 0) & 1
                x12 = (bits >> 1) & 1
                x21 = (bits >> 2) & 1
                x22 = (bits >> 3) & 1
                hand = (x11 * x22 + x12 * x21) % p
                self.assertEqual(_poly_at(target, bits, p), hand)

    def test_hc2_is_the_single_transposition(self):
        for p in (2, 3):
            target = mod.hc_target(2, p)
            self.assertEqual(len(target.terms()), 1)
            self.assertEqual(target.coeff((0, 1, 1, 0)), 1)
            self.assertEqual(target.coeff((1, 0, 0, 1)), 0)

    def test_hc3_two_explicit_cycles(self):
        # (123) = x12 x23 x31 at indices 1, 5, 6
        # (132) = x13 x21 x32 at indices 2, 3, 7
        cycle_a = [0] * 9
        cycle_a[1] = cycle_a[5] = cycle_a[6] = 1
        cycle_b = [0] * 9
        cycle_b[2] = cycle_b[3] = cycle_b[7] = 1
        identity = [0] * 9
        identity[0] = identity[4] = identity[8] = 1
        for p in (2, 3):
            target = mod.hc_target(3, p)
            self.assertEqual(len(target.terms()), 2)
            self.assertEqual(target.coeff(tuple(cycle_a)), 1)
            self.assertEqual(target.coeff(tuple(cycle_b)), 1)
            self.assertEqual(target.coeff(tuple(identity)), 0)

    def test_term_counts_and_shape(self):
        counts = {2: (2, 1), 3: (6, 2), 4: (24, 6)}
        for m in (2, 3, 4):
            for p in (2, 3):
                perm = mod.perm_target(m, p)
                hc = mod.hc_target(m, p)
                self.assertEqual(len(perm.terms()), counts[m][0])
                self.assertEqual(len(hc.terms()), counts[m][1])
                perm_exps = set()
                for exp, coeff in perm.terms():
                    self.assertEqual(coeff, 1)
                    self.assertEqual(sum(exp), m)
                    self.assertTrue(all(entry in (0, 1) for entry in exp))
                    perm_exps.add(exp)
                self.assertEqual(len(perm_exps), counts[m][0])
                for exp, coeff in hc.terms():
                    self.assertEqual(coeff, 1)
                    self.assertIn(exp, perm_exps)

    def test_bad_shape_rejected(self):
        for m, p in ((1, 2), (5, 2), (2, 4), (2, 1), (True, 2), (2, True)):
            with self.subTest(m=m, p=p):
                with self.assertRaises(ValueError):
                    mod.perm_target(m, p)
                with self.assertRaises(ValueError):
                    mod.hc_target(m, p)


class TestCircuits(unittest.TestCase):
    def test_hand_perm2_circuit(self):
        circuit = (
            ("mul", ("x", 1, 1), ("x", 2, 2)),
            ("mul", ("x", 1, 2), ("x", 2, 1)),
            ("add", 0, 1),
        )
        for p in (2, 3):
            poly = mod.circuit_poly(circuit, 2, p, 8)
            self.assertEqual(poly.coeff((1, 0, 0, 1)), 1)
            self.assertEqual(poly.coeff((0, 1, 1, 0)), 1)
            self.assertEqual(len(poly.terms()), 2)
            self.assertTrue(mod.identical_as_polynomials(circuit, mod.perm_target(2, p), 2, p, 4096))
            self.assertTrue(mod.agrees_on_01(circuit, mod.perm_target(2, p), 2, p, 4096))

    def test_hand_hc3_circuit(self):
        circuit = (
            ("mul", ("x", 1, 2), ("x", 2, 3)),
            ("mul", 0, ("x", 3, 1)),
            ("mul", ("x", 1, 3), ("x", 3, 2)),
            ("mul", 2, ("x", 2, 1)),
            ("add", 1, 3),
        )
        for p in (2, 3):
            self.assertTrue(
                mod.identical_as_polynomials(circuit, mod.hc_target(3, p), 3, p, 4096)
            )
            self.assertTrue(mod.agrees_on_01(circuit, mod.hc_target(3, p), 3, p, 4096))

    def test_square_is_formal_and_vanishes_on_01(self):
        circuit = (
            ("mul", ("x", 1, 1), ("x", 1, 1)),
            ("sub", 0, ("x", 1, 1)),
        )
        for p in (2, 3):
            poly = mod.circuit_poly(circuit, 2, p, 8)
            zero = mod.circuit_poly((("const", 0, None),), 2, p, 4)
            self.assertEqual(poly.coeff((2, 0, 0, 0)), 1)
            self.assertEqual(poly.coeff((1, 0, 0, 0)), p - 1)
            self.assertEqual(len(poly.terms()), 2)
            self.assertTrue(mod.agrees_on_01(circuit, zero, 2, p, 4096))
            self.assertFalse(mod.identical_as_polynomials(circuit, zero, 2, p, 4096))

    def test_sum_square_field_arithmetic(self):
        summed = (("add", ("x", 1, 1), ("x", 1, 2)),)
        squared = (
            ("add", ("x", 1, 1), ("x", 1, 2)),
            ("mul", 0, 0),
        )
        poly2 = mod.circuit_poly(squared, 2, 2, 8)
        self.assertEqual(poly2.coeff((2, 0, 0, 0)), 1)
        self.assertEqual(poly2.coeff((0, 2, 0, 0)), 1)
        self.assertEqual(poly2.coeff((1, 1, 0, 0)), 0)
        self.assertEqual(len(poly2.terms()), 2)
        poly3 = mod.circuit_poly(squared, 2, 3, 8)
        self.assertEqual(poly3.coeff((2, 0, 0, 0)), 1)
        self.assertEqual(poly3.coeff((0, 2, 0, 0)), 1)
        self.assertEqual(poly3.coeff((1, 1, 0, 0)), 2)
        target2 = mod.circuit_poly(summed, 2, 2, 4)
        target3 = mod.circuit_poly(summed, 2, 3, 4)
        self.assertTrue(mod.agrees_on_01(squared, target2, 2, 2, 4096))
        self.assertFalse(mod.agrees_on_01(squared, target3, 2, 3, 4096))
        self.assertFalse(mod.identical_as_polynomials(squared, target2, 2, 2, 4096))
        self.assertFalse(mod.identical_as_polynomials(squared, target3, 2, 3, 4096))

    def test_sub_and_cancellation(self):
        diff = (("sub", ("x", 1, 1), ("x", 1, 2)),)
        poly = mod.circuit_poly(diff, 2, 3, 4)
        self.assertEqual(poly.coeff((1, 0, 0, 0)), 1)
        self.assertEqual(poly.coeff((0, 1, 0, 0)), 2)
        cancelled = (("sub", ("x", 1, 1), ("x", 1, 1)),)
        self.assertEqual(mod.circuit_poly(cancelled, 2, 2, 4).terms(), ())
        self.assertEqual(mod.circuit_poly(cancelled, 2, 3, 4).terms(), ())
        neg = (("const", 0, None), ("const", 1, None), ("sub", 0, 1))
        self.assertEqual(mod.circuit_poly(neg, 2, 3, 8).coeff((0, 0, 0, 0)), 2)
        self.assertEqual(mod.circuit_poly(neg, 2, 2, 8).coeff((0, 0, 0, 0)), 1)
        doubled = (("add", ("x", 1, 1), ("x", 1, 1)),)
        self.assertEqual(mod.circuit_poly(doubled, 2, 2, 4).terms(), ())
        self.assertEqual(mod.circuit_poly(doubled, 2, 3, 4).coeff((1, 0, 0, 0)), 2)

    def test_subtraction_order_on_01(self):
        fwd = (("sub", ("x", 1, 1), ("x", 1, 2)),)
        rev = (("sub", ("x", 1, 2), ("x", 1, 1)),)
        tf = mod.circuit_poly(fwd, 2, 3, 4)
        tr = mod.circuit_poly(rev, 2, 3, 4)
        self.assertTrue(mod.agrees_on_01(fwd, tf, 2, 3, 4096))
        self.assertTrue(mod.agrees_on_01(rev, tr, 2, 3, 4096))
        self.assertFalse(mod.agrees_on_01(fwd, tr, 2, 3, 4096))
        self.assertFalse(mod.agrees_on_01(rev, tf, 2, 3, 4096))

    def test_checkers_require_gate_limit(self):
        circuit = (("const", 1, None),)
        target = mod.circuit_poly(circuit, 2, 2, 4)
        with self.assertRaises(TypeError):
            mod.agrees_on_01(circuit, target, 2, 2)
        with self.assertRaises(TypeError):
            mod.identical_as_polynomials(circuit, target, 2, 2)

    def test_list_gates_and_exact_limit(self):
        circuit = [("const", 1, None)]
        poly = mod.circuit_poly(circuit, 2, 2, 1)
        self.assertEqual(poly.coeff((0, 0, 0, 0)), 1)
        with self.assertRaises(ValueError):
            mod.circuit_poly(circuit, 2, 2, 0)

    def test_gate_limit_is_required(self):
        with self.assertRaises(TypeError):
            mod.circuit_poly((("const", 1, None),), 2, 2)

    def test_circuit_matches_its_own_polynomial_on_01(self):
        circuit = (
            ("mul", ("x", 1, 1), ("x", 1, 1)),
            ("sub", 0, ("x", 1, 1)),
            ("add", 1, ("x", 2, 2)),
            ("mul", 2, ("x", 1, 2)),
        )
        for m in (2, 3):
            for p in (2, 3):
                poly = mod.circuit_poly(circuit, m, p, 16)
                self.assertTrue(mod.agrees_on_01(circuit, poly, m, p, 4096))


class TestRefusals(unittest.TestCase):
    def _refuses(self, circuit, m=2, p=2, gate_limit=8):
        with self.assertRaises(ValueError):
            mod.circuit_poly(circuit, m, p, gate_limit)

    def test_structural(self):
        self._refuses(())
        self._refuses(None)
        self._refuses("add")
        self._refuses(5)
        self._refuses((("add", ("x", 1, 1)),))
        self._refuses((("add", ("x", 1, 1), ("x", 1, 2), ("x", 2, 1)),))
        self._refuses((("const", 1),))
        self._refuses((("const", 1, 0),))
        self._refuses((("add", ("x", 1, 1), None),))
        self._refuses((("div", ("x", 1, 1), ("x", 1, 2)),))
        self._refuses((("ADD", ("x", 1, 1), ("x", 1, 2)),))
        self._refuses((("mul", 1, ("x", 1, 1)), ("const", 1, None)))
        self._refuses((("add", 0, ("x", 1, 1)),))
        self._refuses((("add", -1, ("x", 1, 1)),))
        self._refuses((("mul", ("x", 0, 1), ("x", 1, 1)),))
        self._refuses((("mul", ("x", 3, 1), ("x", 1, 1)),))
        self._refuses((("mul", ("x", True, 1), ("x", 1, 1)),))
        self._refuses((("mul", ("y", 1, 1), ("x", 1, 1)),))
        self._refuses((("mul", ("x", 1), ("x", 1, 1)),))
        self._refuses((("const", True, None),))
        self._refuses((("const", 1.0, None),))
        self._refuses((("const", float("nan"), None),))
        self._refuses((("const", float("inf"), None),))
        self._refuses((("const", -1, None),))
        self._refuses((("const", 2, None),), p=2)
        self._refuses((("const", 3, None),), p=3)
        self._refuses((("const", "1", None),))
        with self.assertRaises(ValueError):
            mod.circuit_poly((("const", 1, None),), 2, 2, True)
        with self.assertRaises(ValueError):
            mod.circuit_poly((("const", 1, None),), 2, 2, -1)
        with self.assertRaises(ValueError):
            mod.agrees_on_01((("const", True, None),), mod.perm_target(2, 2), 2, 2, 4096)

    def test_bad_exponent_query(self):
        target = mod.perm_target(2, 2)
        with self.assertRaises(ValueError):
            target.coeff((1, 0, 0))
        with self.assertRaises(ValueError):
            target.coeff((True, 0, 0, 1))
        with self.assertRaises(ValueError):
            target.coeff((-1, 0, 0, 1))


class TestPlanted(unittest.TestCase):
    def test_truth_pairs_m2_m3(self):
        seen = set()
        for m in (2, 3):
            for p in (2, 3):
                for kind, expected in EXPECT.items():
                    for seed in (0, 1):
                        result = mod.planted(m, p, kind, seed)
                        again = mod.planted(m, p, kind, seed)
                        self.assertEqual(result["circuit"], again["circuit"])
                        self.assertEqual(result["target_name"], again["target_name"])
                        pair = (
                            result["agrees_on_01"],
                            result["identical_as_polynomials"],
                        )
                        self.assertEqual(pair, expected)
                        self.assertEqual(
                            mod.agrees_on_01(result["circuit"], result["target"], m, p, 4096),
                            expected[0],
                        )
                        self.assertEqual(
                            mod.identical_as_polynomials(
                                result["circuit"], result["target"], m, p, 4096
                            ),
                            expected[1],
                        )
                        seen.add(result["target_name"])
        self.assertEqual(seen, {"perm", "hc"})

    def test_hash_drives_choices(self):
        m, p, kind, seed = 3, 2, "agrees_not_identical", 4
        result = mod.planted(m, p, kind, seed)
        digest = _tag_digest(m, p, kind, seed)
        self.assertEqual(
            result["target_name"], "perm" if digest[7] % 2 == 0 else "hc"
        )
        vi, vj = divmod(digest[0] % (m * m), m)
        var = ("x", vi + 1, vj + 1)
        scalar = 1 + (digest[1] % (p - 1))
        self.assertIn(("mul", var, var), result["circuit"])
        self.assertIn(("const", scalar, None), result["circuit"])
        poly = mod.circuit_poly(result["circuit"], m, p, 400)
        self.assertTrue(any(power >= 2 for exp, _c in poly.terms() for power in exp))

    def test_wrong_on_01_has_a_constant_term(self):
        result = mod.planted(2, 3, "wrong_on_01", 5)
        poly = mod.circuit_poly(result["circuit"], 2, 3, 80)
        self.assertNotEqual(poly.coeff((0, 0, 0, 0)), 0)
        self.assertFalse(result["agrees_on_01"])
        self.assertFalse(result["identical_as_polynomials"])

    def test_agrees_not_identical_has_no_constant_term(self):
        result = mod.planted(2, 3, "agrees_not_identical", 5)
        poly = mod.circuit_poly(result["circuit"], 2, 3, 80)
        self.assertEqual(poly.coeff((0, 0, 0, 0)), 0)
        self.assertTrue(result["agrees_on_01"])
        self.assertFalse(result["identical_as_polynomials"])

    def test_m4_correct_scan(self):
        result = mod.planted(4, 2, "correct", 0)
        self.assertEqual(
            (result["agrees_on_01"], result["identical_as_polynomials"]),
            (True, True),
        )
        self.assertEqual(len(result["target"].terms()), {"perm": 24, "hc": 6}[result["target_name"]])

    def test_bad_planted_args(self):
        with self.assertRaises(ValueError):
            mod.planted(2, 2, "neither", 0)
        with self.assertRaises(ValueError):
            mod.planted(2, 2, "correct", True)
        with self.assertRaises(ValueError):
            mod.planted(2, 2, "correct", None)
        with self.assertRaises(ValueError):
            mod.planted(2, 2, "correct", 1.5)
        with self.assertRaises(ValueError):
            mod.planted(2, 2, "correct", "1")

    def test_str_seed_never_aliases_int_seed(self):
        good = mod.planted(2, 2, "agrees_not_identical", 1)
        self.assertEqual(good["seed"], 1)
        with self.assertRaises(ValueError):
            mod.planted(2, 2, "agrees_not_identical", "1")


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _outcome(killer, module):
    """'killed' only on AssertionError; any other exception is 'broken'."""
    try:
        killer(module)
    except AssertionError:
        return "killed"
    except Exception:
        return "broken"
    return "survived"


def _raises_value_error(fn):
    """True only when fn raises ValueError; a mutant crashing otherwise is not a pass."""
    try:
        fn()
    except ValueError:
        return True
    except Exception:
        return False
    return False


def check_cycle(module):
    assert len(module.hc_target(3, 2).terms()) == 2


def check_norm(module):
    circuit = (
        ("add", ("x", 1, 1), ("x", 1, 2)),
        ("mul", 0, 0),
    )
    poly = module.circuit_poly(circuit, 2, 2, 8)
    assert poly.coeff((1, 1, 0, 0)) == 0
    assert poly.coeff((2, 0, 0, 0)) == 1


def check_limit(module):
    circuit = (("const", 1, None), ("const", 1, None))
    assert _raises_value_error(lambda: module.circuit_poly(circuit, 2, 2, 1))


def check_forward(module):
    circuit = (("mul", 1, ("x", 1, 1)), ("const", 1, None))
    assert _raises_value_error(lambda: module.circuit_poly(circuit, 2, 2, 8))


def check_bool(module):
    assert _raises_value_error(lambda: module.circuit_poly((("const", True, None),), 2, 2, 4))


def check_sub(module):
    circuit = (("const", 0, None), ("const", 1, None), ("sub", 0, 1))
    poly = module.circuit_poly(circuit, 2, 3, 8)
    assert poly.coeff((0, 0, 0, 0)) == 2


def check_ident(module):
    circuit = (
        ("mul", ("x", 1, 1), ("x", 1, 1)),
        ("sub", 0, ("x", 1, 1)),
    )
    zero = module.circuit_poly((("const", 0, None),), 2, 2, 4)
    assert module.agrees_on_01(circuit, zero, 2, 2, 4096) is True
    assert module.identical_as_polynomials(circuit, zero, 2, 2, 4096) is False


def check_square(module):
    circuit = (("mul", ("x", 1, 1), ("x", 1, 1)),)
    poly = module.circuit_poly(circuit, 2, 2, 4)
    assert poly.coeff((2, 0, 0, 0)) == 1


def check_perm(module):
    target = module.perm_target(2, 2)
    assert len(target.terms()) == 2
    assert target.coeff((1, 0, 0, 1)) == 1
    assert target.coeff((0, 1, 1, 0)) == 1


def check_range(module):
    assert _raises_value_error(lambda: module.circuit_poly((("const", 2, None),), 2, 2, 4))


def check_agree(module):
    circuit = (
        ("mul", ("x", 1, 1), ("x", 1, 1)),
        ("sub", 0, ("x", 1, 1)),
    )
    zero = module.circuit_poly((("const", 0, None),), 2, 3, 4)
    assert module.agrees_on_01(circuit, zero, 2, 3, 4096) is True
    assert module.identical_as_polynomials(circuit, zero, 2, 3, 4096) is False


def check_support(module):
    doubled = (("const", 2, None), ("mul", ("x", 1, 1), 0))
    single = module.circuit_poly(
        (("const", 1, None), ("mul", ("x", 1, 1), 0)), 2, 3, 8
    )
    assert module.identical_as_polynomials(doubled, single, 2, 3, 4096) is False


def check_sub_eval(module):
    fwd = (("sub", ("x", 1, 1), ("x", 1, 2)),)
    rev = (("sub", ("x", 1, 2), ("x", 1, 1)),)
    tf = module.circuit_poly(fwd, 2, 3, 4)
    tr = module.circuit_poly(rev, 2, 3, 4)
    assert module.agrees_on_01(fwd, tf, 2, 3, 4096) is True
    assert module.agrees_on_01(fwd, tr, 2, 3, 4096) is False


def check_zero_filter(module):
    squared = (
        ("add", ("x", 1, 1), ("x", 1, 2)),
        ("mul", 0, 0),
    )
    assert len(module.circuit_poly(squared, 2, 2, 8).terms()) == 2


# (filename, old line, new line, killer)
MUTANTS = (
    (
        "01_cycle.py",
        "    return _is_single_cycle(perm)  # SENTINEL_CYCLE",
        "    return True  # SENTINEL_CYCLE",
        check_cycle,
    ),
    (
        "02_norm.py",
        "    return c % p  # SENTINEL_NORM",
        "    return c  # SENTINEL_NORM",
        check_norm,
    ),
    (
        "03_limit.py",
        "    return n_gates > gate_limit  # SENTINEL_LIMIT",
        "    return False  # SENTINEL_LIMIT",
        check_limit,
    ),
    (
        "04_forward.py",
        "    return type(idx) is not int or idx < 0 or idx >= current  # SENTINEL_FORWARD",
        "    return False  # SENTINEL_FORWARD",
        check_forward,
    ),
    (
        "05_bool.py",
        "    return type(value) is bool or type(value) is not int  # SENTINEL_BOOL",
        "    return not isinstance(value, int)  # SENTINEL_BOOL",
        check_bool,
    ),
    (
        "06_sub.py",
        "    return p - 1  # SENTINEL_SUB",
        "    return 1  # SENTINEL_SUB",
        check_sub,
    ),
    (
        "07_ident.py",
        "    return _polys_equal(poly, target, m, p)  # SENTINEL_IDENT",
        "    return agrees_on_01(circuit, target, m, p, gate_limit)  # SENTINEL_IDENT",
        check_ident,
    ),
    (
        "08_square.py",
        "    return tuple(a + b for a, b in zip(e1, e2))  # SENTINEL_SQUARE",
        "    return tuple((1 if a + b else 0) for a, b in zip(e1, e2))  # SENTINEL_SQUARE",
        check_square,
    ),
    (
        "09_perm.py",
        "    return list(itertools.permutations(range(m)))  # SENTINEL_PERM",
        "    return list(itertools.permutations(range(m)))[:-1]  # SENTINEL_PERM",
        check_perm,
    ),
    (
        "10_range.py",
        "    return value < 0 or value >= p  # SENTINEL_RANGE",
        "    return False  # SENTINEL_RANGE",
        check_range,
    ),
    (
        "11_agree.py",
        "    return _agrees_impl(circuit, target, m, p, gate_limit)  # SENTINEL_AGREE",
        "    return identical_as_polynomials(circuit, target, m, p, gate_limit)  # SENTINEL_AGREE",
        check_agree,
    ),
    (
        "12_support.py",
        "    return left == right  # SENTINEL_SUPPORT",
        "    return tuple(e for e, _c in left) == tuple(e for e, _c in right)  # SENTINEL_SUPPORT",
        check_support,
    ),
    (
        "13_sub_eval.py",
        "                vals[slot] = (vals[a] - vals[b]) % p",
        "                vals[slot] = (vals[b] - vals[a]) % p",
        check_sub_eval,
    ),
    (
        "14_zero_filter.py",
        "    items = [(exp, coeff) for exp, coeff in acc.items() if coeff]",
        "    items = [(exp, coeff) for exp, coeff in acc.items()]",
        check_zero_filter,
    ),
)


class TestMutants(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory(prefix="t2b_mut_")
        cls.mut_dir = cls._tmp.name
        with open(SRC_PATH, "r", encoding="utf-8") as handle:
            cls.source = handle.read()
        cls.paths = []
        for name, old, new, _killer in MUTANTS:
            count = cls.source.count(old)
            if count != 1:
                raise AssertionError("%s sentinel count %s" % (name, count))
            path = os.path.join(cls.mut_dir, name)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(cls.source.replace(old, new, 1))
            cls.paths.append(path)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_at_least_ten_mutants_written(self):
        self.assertGreaterEqual(len(MUTANTS), 10)
        self.assertGreaterEqual(len(os.listdir(self.mut_dir)), 10)

    def test_real_module_survives_every_killer(self):
        for name, _old, _new, killer in MUTANTS:
            with self.subTest(mutant=name):
                killer(mod)

    def test_each_mutant_is_killed(self):
        for path, (_name, _old, _new, killer) in zip(self.paths, MUTANTS):
            with self.subTest(mutant=os.path.basename(path)):
                try:
                    module = _load(path, "mutant_" + os.path.splitext(os.path.basename(path))[0])
                except Exception as exc:
                    self.fail("broken mutant, not killed (import crash): %r" % (exc,))
                with open(path, encoding="utf-8") as handle:
                    found = handle.read()
                self.assertNotEqual(found, self.source)
                outcome = _outcome(killer, module)
                if outcome == "broken":
                    self.fail("broken mutant, not killed (non-assertion exception)")
                self.assertEqual(outcome, "killed", "mutant survived")


if __name__ == "__main__":
    unittest.main()
