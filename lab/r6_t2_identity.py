"""R6 T2 (implementation A): formal identity versus 0/1 agreement for PERM_m and HC_m over F_p.

Polynomials are sparse dicts {exponent tuple (length m*m, index i*m+j): coeff in 1..p-1}.
Circuit: tuple of gates (op, a, b), the last gate is the output.
  ("add"|"sub"|"mul", a, b): a, b are earlier gate indices (int) or ("var", i, j) with 0 <= i, j < m.
  ("const", c, None): c an int in 0..p-1.
Pure Python, offline, no files, no randomness except the sha256-tagged seed in planted().
"""
import hashlib
import itertools
import random

M_VALUES = (2, 3, 4)
P_VALUES = (2, 3)
KINDS = ("correct", "agrees_not_identical", "wrong_coefficient", "wrong_on_01")
TERM_LIMIT = 200000  # fixed refusal bound on intermediate terms, not a tunable
_BINARY = ("add", "sub", "mul")


class T2Refusal(ValueError):
    pass


def _isint(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _check_mp(m, p):
    if not _isint(m) or m not in M_VALUES:
        raise T2Refusal(f"m must be one of {M_VALUES}, got {m!r}")
    if not _isint(p) or p not in P_VALUES:
        raise T2Refusal(f"p must be one of {P_VALUES}, got {p!r}")


def _check_limit(gate_limit):
    if not _isint(gate_limit) or gate_limit < 1:
        raise T2Refusal(f"gate_limit must be a positive int, got {gate_limit!r}")


def _operand(x, idx, m):
    """Return canonical operand; m None skips the variable range check."""
    if _isint(x):
        if not 0 <= x < idx:
            raise T2Refusal(f"gate {idx}: operand {x} is not an earlier gate")
        return ("g", x)
    if isinstance(x, tuple) and len(x) == 3 and x[0] == "var" and _isint(x[1]) and _isint(x[2]):
        if x[1] < 0 or x[2] < 0 or (m is not None and (x[1] >= m or x[2] >= m)):
            raise T2Refusal(f"gate {idx}: variable {x[1:]} out of range")
        return ("x", x[1], x[2])
    raise T2Refusal(f"gate {idx}: bad operand {x!r}")


def _canon(circuit, m, p):
    if not isinstance(circuit, (tuple, list)) or not circuit:
        raise T2Refusal("circuit must be a non-empty tuple of gates")
    out = []
    for idx, gate in enumerate(circuit):
        if not isinstance(gate, (tuple, list)) or len(gate) != 3:
            raise T2Refusal(f"gate {idx}: arity must be 3")
        op, a, b = gate
        if op == "const":
            if not _isint(a) or a < 0 or (p is not None and a >= p) or b is not None:
                raise T2Refusal(f"gate {idx}: bad constant {a!r}")
            out.append(("const", ("c", a), None))
        elif op in _BINARY:
            out.append((op, _operand(a, idx, m), _operand(b, idx, m)))
        else:
            raise T2Refusal(f"gate {idx}: unknown op {op!r}")
    return out


def circuit_to_canonical(circuit):
    """[(op, a, b)] with operands ('g', index), ('x', i, j) or ('c', value); const is ('const', ('c', v), None)."""
    return _canon(circuit, None, None)


def _cyc(perm):
    i, n = 0, 0
    while True:
        i = perm[i]
        n += 1
        if i == 0:
            return n


def _target(m, p, cyclic_only):
    _check_mp(m, p)
    poly = {}
    for perm in itertools.permutations(range(m)):
        if cyclic_only and _cyc(perm) != m:
            continue
        e = [0] * (m * m)
        for i, j in enumerate(perm):
            e[i * m + j] = 1
        poly[tuple(e)] = 1 % p
    return poly


def perm_target(m, p):
    return _target(m, p, False)


def hc_target(m, p):
    return _target(m, p, True)


def target_by_name(name, m, p):
    if name not in ("perm", "hc"):
        raise T2Refusal(f"unknown target {name!r}")
    return perm_target(m, p) if name == "perm" else hc_target(m, p)


def _padd(a, b, p, sign):
    r = dict(a)
    for e, c in b.items():
        v = (r.get(e, 0) + sign * c) % p
        if v:
            r[e] = v
        else:
            r.pop(e, None)
    if len(r) > TERM_LIMIT:
        raise T2Refusal("intermediate polynomial exceeds the term limit")
    return r


def _pmul(a, b, p):
    if len(a) * len(b) > TERM_LIMIT:  # refuse before building, even if terms might cancel
        raise T2Refusal("product would exceed the term limit")
    r = {}
    for e1, c1 in a.items():
        for e2, c2 in b.items():
            e = tuple(x + y for x, y in zip(e1, e2))
            r[e] = (r.get(e, 0) + c1 * c2) % p
    r = {e: c for e, c in r.items() if c}
    if len(r) > TERM_LIMIT:
        raise T2Refusal("intermediate polynomial exceeds the term limit")
    return r


def _validated(circuit, m, p, gate_limit):
    _check_mp(m, p)
    _check_limit(gate_limit)
    if isinstance(circuit, (tuple, list)) and len(circuit) > gate_limit:
        raise T2Refusal(f"circuit has {len(circuit)} gates, over gate_limit {gate_limit}")
    return _canon(circuit, m, p)


def circuit_poly(circuit, m, p, *, gate_limit):
    """Formal polynomial of the output gate; exponents are not reduced."""
    canon = _validated(circuit, m, p, gate_limit)
    n = m * m
    vals = []

    def get(o):
        if o[0] == "g":
            return vals[o[1]]
        e = [0] * n
        e[o[1] * m + o[2]] = 1
        return {tuple(e): 1 % p}

    for op, a, b in canon:
        if op == "const":
            v = a[1] % p
            vals.append({(0,) * n: v} if v else {})
        elif op == "mul":
            vals.append(_pmul(get(a), get(b), p))
        else:
            vals.append(_padd(get(a), get(b), p, 1 if op == "add" else -1))
    return vals[-1]


def _check_poly(poly, m, p):
    if not isinstance(poly, dict):
        raise T2Refusal("target must be a dict polynomial")
    for e, c in poly.items():
        if not (isinstance(e, tuple) and len(e) == m * m and all(_isint(x) and x >= 0 for x in e)):
            raise T2Refusal(f"bad exponent {e!r}")
        if not _isint(c) or not 0 < c < p:
            raise T2Refusal(f"bad coefficient {c!r}")


def agrees_on_01(circuit, target, m, p, *, gate_limit):
    """Direct gate-by-gate evaluation at all 2^(m*m) 0/1 points, compared with the target's values."""
    canon = _validated(circuit, m, p, gate_limit)
    _check_poly(target, m, p)
    n = m * m
    masks = [(sum(1 << k for k, x in enumerate(e) if x), c) for e, c in target.items()]
    for pt in range(1 << n):
        want = sum(c for mk, c in masks if mk & pt == mk) % p
        vals = []

        def get(o):
            return vals[o[1]] if o[0] == "g" else (pt >> (o[1] * m + o[2])) & 1

        for op, a, b in canon:
            if op == "const":
                vals.append(a[1] % p)
            elif op == "mul":
                vals.append(get(a) * get(b) % p)
            else:
                vals.append((get(a) + (1 if op == "add" else -1) * get(b)) % p)
        if vals[-1] != want:
            return False
    return True


def identical_as_polynomials(circuit, target, m, p, *, gate_limit):
    _check_poly(target, m, p)
    return circuit_poly(circuit, m, p, gate_limit=gate_limit) == target


class _B:
    def __init__(self):
        self.g = []

    def add(self, op, a, b):
        self.g.append((op, a, b))
        return len(self.g) - 1

    def term(self, e, m):
        vs = [("var", k // m, k % m) for k, x in enumerate(e) if x]
        acc = vs[0]
        for v in vs[1:]:
            acc = self.add("mul", acc, v)
        return acc

    def total(self, terms, m, p):
        if not terms:
            return self.add("const", 0, None)
        acc = None
        for e in terms:
            t = self.term(e, m)
            acc = t if acc is None else self.add("add", acc, t)
        return acc


def planted(m, p, kind, seed):
    """Seeded planted circuit. Returns {'circuit','target','kind','m','p'}; target is 'perm' or 'hc'."""
    _check_mp(m, p)
    if kind not in KINDS:
        raise T2Refusal(f"unknown kind {kind!r}")
    if not _isint(seed):
        raise T2Refusal("seed must be an int")
    tag = hashlib.sha256(f"r6_t2|{m}|{p}|{kind}|{seed}".encode()).digest()
    rng = random.Random(int.from_bytes(tag, "big"))
    name = rng.choice(("perm", "hc"))
    terms = sorted(target_by_name(name, m, p))
    rng.shuffle(terms)
    b = _B()
    if kind == "wrong_on_01":
        terms = terms[1:]  # drop one term: wrong at that permutation's 0/1 point
    out = b.total(terms, m, p)
    if kind == "agrees_not_identical":
        v = ("var", rng.randrange(m), rng.randrange(m))
        c = b.add("const", rng.randrange(1, p), None)
        sq = b.add("mul", v, v)
        d = b.add("sub", sq, v)
        out = b.add("add", out, b.add("mul", c, d))
    elif kind == "wrong_coefficient":
        e = terms[rng.randrange(len(terms))]
        c = b.add("const", rng.randrange(1, p), None)
        out = b.add("add", out, b.add("mul", c, b.term(e, m)))
    return {"circuit": tuple(b.g), "target": name, "kind": kind, "m": m, "p": p}
