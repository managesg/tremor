"""R6 M1: exact minimum formula size and circuit size for all Boolean functions, n <= 4.

Cost models (prereg/R6-pvsnp-research-line-plan.md, M1):
  formula (De Morgan): leaves = variable occurrences; AND/OR; negation free anywhere; no constant leaves.
  formula (binary):    same leaf count, all 16 two-input operations.
  circuit:             number of two-input gates over all 16 operations; inputs free,
                       negation free, unbounded fan-out, no constants.
A truth table is an int; bit i is f(x) with x_j = (i >> j) & 1. Standard library only.
Method: dynamic programming over truth tables, closed by size, on NPN class representatives
(input negation, input permutation, output negation leave both costs unchanged).
"""
import itertools
from functools import lru_cache

BASES = ("demorgan", "binary")
RECALLED = {  # plan M1, "recalled, unverified"
    "classes": {2: 4, 3: 14, 4: 222},
    "parity4_demorgan_formula": 16,
    "max_circuit_size_n4": 7,
}


def _check_n(n):
    if type(n) is not int or not 1 <= n <= 4:
        raise ValueError("n must be an int in 1..4, got %r" % (n,))
    return n


def var_table(n, j):
    _check_n(n)
    if type(j) is not int or not 0 <= j < n:
        raise ValueError("variable index out of range: %r" % (j,))
    return sum(1 << i for i in range(1 << n) if (i >> j) & 1)


class _Sym:
    """The 2^n * n! input negation/permutation maps on truth tables, as byte lookup tables."""

    def __init__(self, n):
        self.n, self.N = n, 1 << n
        self.full = (1 << self.N) - 1
        self.tabs = []
        for perm in itertools.permutations(range(n)):
            for m in range(1 << n):
                dest = [0] * self.N  # old bit position -> new bit position
                for i in range(self.N):
                    old = 0
                    for j in range(n):
                        old |= (((i >> j) & 1) ^ ((m >> j) & 1)) << perm[j]
                    dest[old] = i
                lo = [0] * 256
                hi = [0] * 256
                for v in range(256):
                    for i in range(min(8, self.N)):
                        if (v >> i) & 1:
                            lo[v] |= 1 << dest[i]
                    for i in range(8, self.N):
                        if (v >> (i - 8)) & 1:
                            hi[v] |= 1 << dest[i]
                self.tabs.append((lo, hi))

    def apply(self, t, f):
        lo, hi = self.tabs[t]
        return lo[f & 255] | hi[f >> 8]

    def orbit(self, f):
        """All truth tables NPN-equivalent to f (output negation included)."""
        s = {self.apply(t, f) for t in range(len(self.tabs))}
        return s | {self.full ^ g for g in s}

    def norm(self, f):
        return self.full ^ f if f & 1 else f


@lru_cache(maxsize=None)
def _sym(n):
    return _Sym(_check_n(n))


@lru_cache(maxsize=None)
def _classes(n):
    """(rep_of: f -> least member of its NPN class, orbit_size: rep -> int)."""
    s = _sym(n)
    rep_of, orbit_size = {}, {}
    for f in range(1 << s.N):
        if f in rep_of:
            continue
        orb = s.orbit(f)
        for g in orb:
            rep_of[g] = f
        orbit_size[f] = len(orb)
    return rep_of, orbit_size


def npn_class_count(n):
    return len(_classes(n)[1])


def npn_orbit_sizes(n):
    """rep -> number of truth tables in the class; the sizes sum to 2^(2^n)."""
    return dict(_classes(n)[1])


@lru_cache(maxsize=None)
def _formula(n, basis):
    s = _sym(n)
    rep_of, _ = _classes(n)
    full = s.full
    binary = basis == "binary"
    level = {1: set()}
    for j in range(n):
        v = var_table(n, j)
        level[1] |= {v, full ^ v}
    cost = {rep_of[next(iter(level[1]))]: 1}
    todo = set(rep_of.values()) - set(cost)
    k = 1
    while todo:
        k += 1
        level[k] = set()
        for r in sorted(todo):
            hit = False
            for a in range(1, k // 2 + 1):
                A, B = level[a], level[k - a]
                if binary and any((g ^ r) in B for g in A):
                    hit = True
                    break
                for t in (r, full ^ r):  # AND on t covers AND (t=r) and OR (t=~r)
                    ga = [g for g in A if g & t == t]
                    hb = [h for h in B if h & t == t]
                    if any(g & h == t for g in ga for h in hb):
                        hit = True
                        break
                if hit:
                    break
            if hit:
                cost[r] = k
        for r in cost:  # new classes of this level enter the table after the level is done
            if r in todo:
                level[k] |= s.orbit(r)
        todo -= set(cost)
    return {f: cost[rep_of[f]] for f in range(1 << s.N)}


def min_formula_size(n, basis="demorgan"):
    """truth table int -> minimum leaf count, for every Boolean function of n inputs."""
    _check_n(n)
    if basis not in BASES:
        raise ValueError("basis must be one of %r, got %r" % (BASES, basis))
    return dict(_formula(n, basis))


def _gates(a, b, full):
    for x in (a, full ^ a):
        for y in (b, full ^ b):
            yield x & y
    yield a ^ b


@lru_cache(maxsize=None)
def _circuit(n):
    """(exact: f -> size, lower_bounds: f -> proven lower bound for classes left open)."""
    s = _sym(n)
    rep_of, _ = _classes(n)
    full, norm = s.full, s.norm
    inputs = [var_table(n, j) for j in range(n)]
    cost = {rep_of[inputs[0]]: 0}
    cost.setdefault(rep_of[0], 1)  # x XOR x
    reps = set(rep_of.values())
    ntr = len(s.tabs)

    def canon(state):
        return min(tuple(sorted(norm(s.apply(t, g)) for g in state)) for t in range(ntr))

    level = {()}
    d = 0
    while len(cost) < len(reps) and not (n == 4 and d == 4):
        d += 1
        nxt = set()
        for st in level:
            sig = inputs + list(st)
            have = set(sig)
            for i in range(len(sig)):
                for j in range(i + 1, len(sig)):
                    for g in _gates(sig[i], sig[j], full):
                        g = norm(g)
                        if g and g not in have:
                            nxt.add(canon(st + (g,)))
        level = nxt
        for st in level:
            for g in st:
                cost.setdefault(rep_of[g], d)
    if len(cost) < len(reps):  # n == 4: depth 5 and 6 by one gate over each depth-4 state
        c5, c6 = set(), set()
        for st in level:
            sig = inputs + list(st)
            have = set(sig)
            for i in range(len(sig)):
                for j in range(i + 1, len(sig)):
                    for g in _gates(sig[i], sig[j], full):
                        g = norm(g)
                        if not g or g in have:
                            continue
                        c5.add(g)
                        # a minimal 6-gate chain must use its fifth gate in its sixth
                        for x in sig:
                            c6.update(norm(h) for h in _gates(g, x, full))
        for g in c5:
            cost.setdefault(rep_of[g], 5)
        for g in c6:
            if g:
                cost.setdefault(rep_of[g], 6)
    exact = {f: cost[rep_of[f]] for f in range(1 << s.N) if rep_of[f] in cost}
    lower = {}
    open_reps = sorted(reps - set(cost))
    if open_reps:  # not computable in 6 gates: tree-shaped upper bounds, cost(g)+cost(h)+1 <= 7
        found = {}
        bound = 7  # nothing is computable in 6 gates, so 7 is a proven lower bound
        by_cost = sorted(exact.items(), key=lambda kv: kv[1])
        for r in open_reps:
            hit = False
            for g, cg in by_cost:
                if cg + 1 > bound:
                    break
                if (g ^ r) in exact and cg + exact[g ^ r] + 1 <= bound:
                    hit = True
                    break
            for t in (r, full ^ r):
                if hit:
                    break
                sup = [(c, g) for g, c in by_cost if g & t == t]
                for c1, g in sup:
                    for c2, h in sup:
                        if c1 + c2 + 1 > bound:
                            break
                        if g & h == t:
                            hit = True
                            break
                    if hit:
                        break
            for f in rep_of:
                if rep_of[f] == r:
                    (found if hit else lower)[f] = bound
        exact.update(found)
    return exact, lower


def min_circuit_size(n):
    """truth table int -> exact minimum gate count, for every function whose class is resolved.

    Functions whose class could not be bounded above are absent here; see circuit_open(n).
    """
    return dict(_circuit(_check_n(n))[0])


def circuit_open(n):
    """truth table int -> proven lower bound, for classes not resolved exactly (normally empty)."""
    return dict(_circuit(_check_n(n))[1])


def max_size(sizes):
    return max(sizes.values())


def crosscheck_report():
    """Computed values next to the plan's recalled, unverified ones. A mismatch is an investigation."""
    circ = min_circuit_size(4)
    parity4 = 0
    for i in range(16):
        if bin(i).count("1") % 2:
            parity4 |= 1 << i
    return {
        "classes": {n: npn_class_count(n) for n in (2, 3, 4)},
        "classes_recalled": dict(RECALLED["classes"]),
        "parity4_demorgan_formula": min_formula_size(4)[parity4],
        "parity4_demorgan_formula_recalled": RECALLED["parity4_demorgan_formula"],
        "max_circuit_size_n4": max_size(circ),
        "max_circuit_size_n4_recalled": RECALLED["max_circuit_size_n4"],
        "circuit_open_n4": len(circuit_open(4)),
        "max_formula_size": {n: max_size(min_formula_size(n)) for n in (2, 3, 4)},
        "max_formula_size_binary": {n: max_size(min_formula_size(n, "binary")) for n in (2, 3, 4)},
        "max_circuit_size": {n: max_size(min_circuit_size(n)) for n in (2, 3, 4)},
    }
