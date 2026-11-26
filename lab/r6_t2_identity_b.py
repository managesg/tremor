# helper work (Cursor), Opus-reviewed; adopted by the lane with these changes:
# (5) gate_limit is REQUIRED in agrees_on_01 and identical_as_polynomials (no 4096
#     default); `planted` passes DEFAULT_GATE_LIMIT explicitly.
# (6) `planted` accepts integer seeds only (bool, str, float, None raise ValueError),
#     so seed 1 and '1' cannot give the same circuit.
# Logic is otherwise the helper's. Source sha256 e5d56c1a10d1b17db626f12a9c631660cde7150ff345d347ad0eb4b45beaba32.
"""Formal identity versus 0/1 agreement for PERM_m and HC_m.

Representation (independent of any other checker): a polynomial is an
immutable sorted tuple of ``(exponent_vector, coefficient)`` pairs.
``exponent_vector`` has length ``m * m``, row-major, 1-based variable
``x_{i,j}`` at index ``(i - 1) * m + (j - 1)``. Coefficients live in
``1 .. p-1``. Exponents are formal: ``x**2`` is not reduced to ``x``.

Circuit: a sequence of gates ``(op, a, b)`` with ``op`` in
``add``, ``sub``, ``mul``, ``const``. The last gate is the output.
An operand of ``add`` / ``sub`` / ``mul`` is an earlier gate index
(plain ``int``) or a variable ``('x', i, j)``. An integer constant mod
``p`` appears only as ``('const', k, None)`` with ``0 <= k < p``.
That split keeps gate index ``0`` distinct from the constant ``0``.

``circuit_poly``, ``agrees_on_01`` and ``identical_as_polynomials`` all
require ``gate_limit`` (no default). ``planted`` passes ``DEFAULT_GATE_LIMIT``.

``planted`` (integer ``seed`` only) draws its choices from
``sha256("t2b|{m}|{p}|{kind}|{seed}")``:
byte 0 selects the variable, byte 1 the nonzero scalar, bytes 2..5
the term index, byte 6 the replacement coefficient, byte 7 the target
(even ``perm``, odd ``hc``).
"""

from __future__ import annotations

import hashlib
import itertools

DEFAULT_GATE_LIMIT = 4096

_KINDS = (
    "correct",
    "agrees_not_identical",
    "wrong_coefficient",
    "wrong_on_01",
)

_OPS = ("add", "sub", "mul", "const")


class Poly:
    """Sorted sparse polynomial. ``terms()`` returns a tuple of pairs."""

    __slots__ = ("_terms", "m", "p", "nvars")

    def __init__(self, terms, m, p):
        self._terms = terms
        self.m = m
        self.p = p
        self.nvars = m * m

    def coeff(self, exponent_vector):
        key = tuple(exponent_vector)
        if len(key) != self.nvars:
            raise ValueError("exponent length")
        for entry in key:
            if type(entry) is bool or type(entry) is not int or entry < 0:
                raise ValueError("exponent entry")
        terms = self._terms
        lo = 0
        hi = len(terms)
        while lo < hi:
            mid = (lo + hi) // 2
            if terms[mid][0] < key:
                lo = mid + 1
            else:
                hi = mid
        if lo < len(terms) and terms[lo][0] == key:
            return terms[lo][1]
        return 0

    def terms(self):
        return self._terms

    def __repr__(self):
        return "Poly(m=%s, p=%s, nterms=%s)" % (self.m, self.p, len(self._terms))


def _bad_int(value):
    return type(value) is bool or type(value) is not int  # SENTINEL_BOOL


def _const_out_of_range(value, p):
    return value < 0 or value >= p  # SENTINEL_RANGE


def _bad_gate_ref(idx, current):
    return type(idx) is not int or idx < 0 or idx >= current  # SENTINEL_FORWARD


def _over_gate_limit(n_gates, gate_limit):
    return n_gates > gate_limit  # SENTINEL_LIMIT


def _normalize_coeff(c, p):
    return c % p  # SENTINEL_NORM


def _sub_sign(p):
    return p - 1  # SENTINEL_SUB


def _exponent_add(e1, e2):
    if len(e1) != len(e2):
        raise ValueError("exponent rank")
    return tuple(a + b for a, b in zip(e1, e2))  # SENTINEL_SQUARE


def _check_mp(m, p):
    if type(m) is not int or m not in (2, 3, 4):
        raise ValueError("m must be 2, 3, or 4")
    if type(p) is not int or p not in (2, 3):
        raise ValueError("p must be 2 or 3")


def _perm_list(m):
    return list(itertools.permutations(range(m)))  # SENTINEL_PERM


def _is_single_cycle(perm):
    """True when ``perm`` is one cycle through every index."""
    m = len(perm)
    seen = 0
    x = 0
    for _step in range(m):
        bit = 1 << x
        if seen & bit:
            return False
        seen |= bit
        x = perm[x]
    return x == 0 and seen == (1 << m) - 1


def _keep_cycle(perm):
    return _is_single_cycle(perm)  # SENTINEL_CYCLE


def _exp_from_perm(perm, m):
    exp = [0] * (m * m)
    for i, j in enumerate(perm):
        exp[i * m + j] = 1
    return (tuple(exp), 1)


def perm_target(m, p):
    """Permanent polynomial: one monomial per permutation, coefficient 1."""
    _check_mp(m, p)
    terms = [_exp_from_perm(perm, m) for perm in _perm_list(m)]
    terms.sort()
    return Poly(tuple(terms), m, p)


def hc_target(m, p):
    """Hamiltonian-cycle polynomial: one monomial per m-cycle, coefficient 1."""
    _check_mp(m, p)
    terms = [
        _exp_from_perm(perm, m)
        for perm in _perm_list(m)
        if _keep_cycle(perm)
    ]
    terms.sort()
    return Poly(tuple(terms), m, p)


def _var_terms(i, j, m):
    exp = [0] * (m * m)
    exp[(i - 1) * m + (j - 1)] = 1
    return ((tuple(exp), 1),)


def _const_terms(k, m, p):
    k = _normalize_coeff(k, p)
    if k == 0:
        return ()
    return (((0,) * (m * m), k),)


def _add_terms(left, right, p, sign):
    i = 0
    j = 0
    out = []
    nleft = len(left)
    nright = len(right)
    while i < nleft or j < nright:
        if j == nright or (i < nleft and left[i][0] < right[j][0]):
            out.append(left[i])
            i += 1
        elif i == nleft or right[j][0] < left[i][0]:
            coeff = _normalize_coeff(sign * right[j][1], p)
            if coeff:
                out.append((right[j][0], coeff))
            j += 1
        else:
            coeff = _normalize_coeff(left[i][1] + sign * right[j][1], p)
            if coeff:
                out.append((left[i][0], coeff))
            i += 1
            j += 1
    return tuple(out)


def _mul_terms(left, right, p):
    acc = {}
    for exp1, c1 in left:
        for exp2, c2 in right:
            exp = _exponent_add(exp1, exp2)
            acc[exp] = _normalize_coeff(acc.get(exp, 0) + c1 * c2, p)
    items = [(exp, coeff) for exp, coeff in acc.items() if coeff]
    items.sort()
    return tuple(items)


def _require_variable(operand, m):
    if len(operand) != 3 or operand[0] != "x":
        raise ValueError("variable")
    _op, i, j = operand
    if _bad_int(i) or _bad_int(j) or i < 1 or i > m or j < 1 or j > m:
        raise ValueError("variable index")


def _require_operand(operand, current, m):
    if type(operand) is tuple:
        _require_variable(operand, m)
        return
    if _bad_gate_ref(operand, current):
        raise ValueError("bad gate reference")


def _validate(circuit, m, p, gate_limit):
    _check_mp(m, p)
    if type(gate_limit) is not int or gate_limit < 0:
        raise ValueError("gate limit")
    if type(circuit) not in (tuple, list):
        raise ValueError("circuit")
    n_gates = len(circuit)
    if _over_gate_limit(n_gates, gate_limit):
        raise ValueError("circuit exceeds gate limit")
    if n_gates == 0:
        raise ValueError("empty circuit")
    gates = []
    for index, gate in enumerate(circuit):
        if type(gate) not in (tuple, list) or len(gate) != 3:
            raise ValueError("gate arity")
        op, left, right = gate
        if op not in _OPS:
            raise ValueError("op")
        if op == "const":
            if right is not None:
                raise ValueError("const arity")
            if _bad_int(left) or _const_out_of_range(left, p):
                raise ValueError("constant")
            gates.append(("const", left, None))
            continue
        _require_operand(left, index, m)
        _require_operand(right, index, m)
        gates.append(
            (
                op,
                tuple(left) if type(left) is tuple else left,
                tuple(right) if type(right) is tuple else right,
            )
        )
    return gates


def _operand_terms(operand, polys, m, p):
    if type(operand) is tuple:
        _require_variable(operand, m)
        return _var_terms(operand[1], operand[2], m)
    if _bad_gate_ref(operand, len(polys)):
        raise ValueError("bad gate reference")
    return polys[operand].terms()


def circuit_poly(circuit, m, p, gate_limit):
    """Formal polynomial of ``circuit``. ``gate_limit`` is required.

    Exponents are not reduced by ``x**p = x``.
    """
    gates = _validate(circuit, m, p, gate_limit)
    polys = []
    for op, left, right in gates:
        if op == "const":
            polys.append(Poly(_const_terms(left, m, p), m, p))
            continue
        lt = _operand_terms(left, polys, m, p)
        rt = _operand_terms(right, polys, m, p)
        if op == "add":
            terms = _add_terms(lt, rt, p, 1)
        elif op == "sub":
            terms = _add_terms(lt, rt, p, _sub_sign(p))
        elif op == "mul":
            terms = _mul_terms(lt, rt, p)
        else:
            raise ValueError("op")
        polys.append(Poly(terms, m, p))
    return polys[-1]


def _canonical(obj, m, p):
    n = m * m
    terms_fn = getattr(obj, "terms", None)
    if not callable(terms_fn):
        raise ValueError("target has no terms")
    acc = {}
    for exp, coeff in terms_fn():
        if _bad_int(coeff):
            raise ValueError("coefficient")
        key = tuple(exp)
        if len(key) != n:
            raise ValueError("exponent length")
        for entry in key:
            if _bad_int(entry) or entry < 0:
                raise ValueError("exponent entry")
        acc[key] = _normalize_coeff(acc.get(key, 0) + coeff, p)
    items = [(key, coeff) for key, coeff in acc.items() if coeff]
    items.sort()
    return tuple(items)


def _polys_equal(poly, target, m, p):
    left = _canonical(poly, m, p)
    right = _canonical(target, m, p)
    return left == right  # SENTINEL_SUPPORT


def identical_as_polynomials(circuit, target, m, p, gate_limit):
    """True when ``circuit`` and ``target`` have the same formal polynomial."""
    poly = circuit_poly(circuit, m, p, gate_limit)
    return _polys_equal(poly, target, m, p)  # SENTINEL_IDENT


def _masks(target, m, p):
    n = m * m
    terms_fn = getattr(target, "terms", None)
    if not callable(terms_fn):
        raise ValueError("target has no terms")
    acc = {}
    for exp, coeff in terms_fn():
        if _bad_int(coeff):
            raise ValueError("coefficient")
        key = tuple(exp)
        if len(key) != n:
            raise ValueError("exponent length")
        mask = 0
        for bit, entry in enumerate(key):
            if _bad_int(entry) or entry < 0:
                raise ValueError("exponent entry")
            if entry:
                mask |= 1 << bit
        acc[mask] = _normalize_coeff(acc.get(mask, 0) + coeff, p)
    return tuple((mask, coeff) for mask, coeff in acc.items() if coeff)


def _compile(gates, m):
    n = m * m
    code = []
    for op, left, right in gates:
        if op == "const":
            code.append((0, left, 0))
        elif op == "add":
            code.append((1, _slot(left, n, m), _slot(right, n, m)))
        elif op == "sub":
            code.append((2, _slot(left, n, m), _slot(right, n, m)))
        else:
            code.append((3, _slot(left, n, m), _slot(right, n, m)))
    return code


def _slot(operand, n, m):
    if type(operand) is tuple:
        return (operand[1] - 1) * m + (operand[2] - 1)
    return n + operand


def _scan(code, masks, m, p):
    n = m * m
    n_gates = len(code)
    vals = [0] * (n + n_gates)
    runtime = []
    for gi, (op, a, b) in enumerate(code):
        slot = n + gi
        if op == 0:
            vals[slot] = a
        else:
            runtime.append((op, a, b, slot))
    last = n + n_gates - 1
    limit = 1 << n
    bits = 0
    while bits < limit:
        bb = bits
        k = 0
        while k < n:
            vals[k] = bb & 1
            bb >>= 1
            k += 1
        for op, a, b, slot in runtime:
            if op == 3:
                vals[slot] = (vals[a] * vals[b]) % p
            elif op == 1:
                vals[slot] = (vals[a] + vals[b]) % p
            else:
                vals[slot] = (vals[a] - vals[b]) % p
        cv = vals[last]
        tv = 0
        for mask, coeff in masks:
            if (bits & mask) == mask:
                tv += coeff
        if (cv - tv) % p != 0:
            return False
        bits += 1
    return True


def _agrees_impl(circuit, target, m, p, gate_limit):
    _check_mp(m, p)
    gates = _validate(circuit, m, p, gate_limit)
    return _scan(_compile(gates, m), _masks(target, m, p), m, p)


def agrees_on_01(circuit, target, m, p, gate_limit):
    """True when circuit and target agree on every 0/1 matrix over F_p."""
    return _agrees_impl(circuit, target, m, p, gate_limit)  # SENTINEL_AGREE


def _emit_monomial(gates, exp, coeff, m, p):
    coeff = _normalize_coeff(coeff, p)
    if coeff == 0:
        gates.append(("const", 0, None))
        return len(gates) - 1
    factors = []
    for idx, power in enumerate(exp):
        i, j = divmod(idx, m)
        var = ("x", i + 1, j + 1)
        for _rep in range(power):
            factors.append(var)
    if not factors:
        gates.append(("const", coeff, None))
        return len(gates) - 1
    if len(factors) == 1:
        gates.append(("const", 1, None))
        gates.append(("mul", factors[0], len(gates) - 1))
        acc = len(gates) - 1
    else:
        acc = factors[0]
        for factor in factors[1:]:
            gates.append(("mul", acc, factor))
            acc = len(gates) - 1
    if coeff != 1:
        gates.append(("const", coeff, None))
        gates.append(("mul", acc, len(gates) - 1))
        acc = len(gates) - 1
    return acc


def _circuit_from_terms(terms, m, p, coeff_of=None):
    gates = []
    outputs = []
    for index, (exp, coeff) in enumerate(terms):
        if coeff_of is not None and index in coeff_of:
            coeff = coeff_of[index]
        outputs.append(_emit_monomial(gates, exp, coeff, m, p))
    if not outputs:
        gates.append(("const", 0, None))
        return gates
    acc = outputs[0]
    for gate in outputs[1:]:
        gates.append(("add", acc, gate))
        acc = len(gates) - 1
    return gates


def _append_vanish(gates, i, j, c):
    """Append ``c * (x_{i,j}^2 - x_{i,j})`` and add it to the current output."""
    out = len(gates) - 1
    var = ("x", i, j)
    gates.append(("mul", var, var))
    x2 = len(gates) - 1
    gates.append(("const", c, None))
    cg = len(gates) - 1
    gates.append(("mul", cg, x2))
    cx2 = len(gates) - 1
    gates.append(("mul", cg, var))
    cx = len(gates) - 1
    gates.append(("sub", cx2, cx))
    diff = len(gates) - 1
    gates.append(("add", out, diff))


def _append_const(gates, c):
    out = len(gates) - 1
    gates.append(("const", c, None))
    gates.append(("add", out, len(gates) - 1))


def _digest(m, p, kind, seed):
    if type(seed) is not int:
        raise ValueError("seed")
    tag = "t2b|%s|%s|%s|%s" % (m, p, kind, seed)
    return hashlib.sha256(tag.encode("utf-8")).digest()


def _freeze(gates):
    frozen = []
    for op, left, right in gates:
        if type(left) is tuple:
            left = tuple(left)
        if type(right) is tuple:
            right = tuple(right)
        frozen.append((op, left, right))
    return tuple(frozen)


def planted(m, p, kind, seed):
    """Deterministic circuit of ``kind`` plus exhaustive truths for (i) and (ii).

    Kinds: ``correct``, ``agrees_not_identical``, ``wrong_coefficient``,
    ``wrong_on_01``. The booleans are computed by ``agrees_on_01`` and
    ``identical_as_polynomials``, not stored as constants.
    """
    _check_mp(m, p)
    if type(kind) is not str or kind not in _KINDS:
        raise ValueError("kind")
    digest = _digest(m, p, kind, seed)
    name = "perm" if digest[7] % 2 == 0 else "hc"
    target = perm_target(m, p) if name == "perm" else hc_target(m, p)
    n = m * m
    vi, vj = divmod(digest[0] % n, m)
    vi += 1
    vj += 1
    scalar = 1 + (digest[1] % (p - 1))
    if kind == "wrong_coefficient":
        replacement = digest[6] % p
        if replacement == 1:
            replacement = 0
        term_index = int.from_bytes(digest[2:6], "big") % len(target.terms())
        gates = _circuit_from_terms(
            target.terms(), m, p, {term_index: replacement}
        )
    else:
        gates = _circuit_from_terms(target.terms(), m, p)
        if kind == "agrees_not_identical":
            _append_vanish(gates, vi, vj, scalar)
        elif kind == "wrong_on_01":
            _append_const(gates, scalar)
        elif kind != "correct":
            raise ValueError("kind")
    circuit = _freeze(gates)
    agrees = agrees_on_01(circuit, target, m, p, DEFAULT_GATE_LIMIT)
    identical = identical_as_polynomials(circuit, target, m, p, DEFAULT_GATE_LIMIT)
    return {
        "circuit": circuit,
        "target_name": name,
        "target": target,
        "agrees_on_01": agrees,
        "identical_as_polynomials": identical,
        "kind": kind,
        "m": m,
        "p": p,
        "seed": seed,
    }
