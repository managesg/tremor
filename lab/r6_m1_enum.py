"""R6 M1 (worker W2): exact minimum formula size and circuit size of all Boolean
functions on n = 2, 3, 4 inputs, by exhaustive enumeration.

Truth table = int, bit i = output on input i, input j = bit j of i (little-endian).

Cost models (prereg/R6-pvsnp-research-line-plan.md, M1):
  formula, basis "demorgan": leaves = variable occurrences, AND/OR, negation free, no constants.
  formula, basis "binary":   same leaf count, all 16 two-input operations.
  circuit: number of two-input gates over all 16 operations; inputs and negation free.

Method (no table DP over function pairs):
  formulas: level s holds every function whose cheapest formula has s leaves; level s is
    built by joining a level-a and a level-b function, a+b=s.  The left operand runs over
    one representative per input-symmetry orbit, the right over all (sound: the symmetry
    group acts on both operands at once).
  circuits: explicit gate sequences, deduplicated as unordered sets of node functions and
    canonicalised under input permutation/negation (size is invariant).  Depth K states are
    enumerated in full; one more gate gives size K+1; a second gate that must read the
    new one gives size K+2 (any (K+2)-gate circuit has a sink gate).  What the bounded
    search cannot reach is reported as a lower bound, then an upper bound by
    "gate over two disjoint sub-circuits".

Plan ambiguities (see report): a gate reading the same node twice (default: not allowed,
so a constant costs 2 gates; const_gate=True makes it 1); constants as formula
leaves are banned, so a constant formula is x AND NOT x (2 leaves).
"""
from functools import lru_cache
from itertools import permutations

SUPPORTED = (2, 3, 4)
_K = {2: 3, 3: 3, 4: 4}  # circuit states enumerated in full up to this gate count


def _check_n(n):
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError("n must be an int")
    if n not in SUPPORTED:
        raise ValueError("n must be one of %r" % (SUPPORTED,))


class _Ctx:
    def __init__(self, n):
        self.n = n
        self.W = 1 << n
        self.M = (1 << self.W) - 1
        self.nfun = 1 << self.W
        self.vars = [sum(1 << j for j in range(self.W) if (j >> i) & 1) for i in range(n)]
        self.elems = [self._chunks(p, m) for p in permutations(range(n)) for m in range(self.W)]
        # generators of the group: swap(0,1), cycle, negate var 0
        swap = list(range(n)); swap[0], swap[1] = 1, 0
        cyc = [(i + 1) % n for i in range(n)]
        self.gens = [self._table(self._chunks(tuple(swap), 0)),
                     self._table(self._chunks(tuple(cyc), 0)),
                     self._table(self._chunks(tuple(range(n)), 1))]

    def _chunks(self, perm, mask):
        # f'(j) = f(idx[j]); source bit p goes to the j with idx[j] == p
        W = self.W
        dest = [0] * W
        for j in range(W):
            k = sum(((j >> perm[i]) & 1) << i for i in range(self.n)) ^ mask
            dest[k] = j
        lo = [sum(((b >> i) & 1) << dest[i] for i in range(min(8, W))) for b in range(256)]
        hi = [sum(((b >> i) & 1) << dest[8 + i] for i in range(8)) for b in range(256)] if W > 8 else [0] * 256
        return lo, hi

    def _table(self, lh):
        lo, hi = lh
        return [lo[f & 255] | hi[f >> 8] for f in range(self.nfun)]

    def orbit_ids(self, with_complement):
        """class id for every function; classes under the group (and output negation)."""
        gens = list(self.gens) + ([[f ^ self.M for f in range(self.nfun)]] if with_complement else [])
        cid = [-1] * self.nfun
        reps = []
        for f in range(self.nfun):
            if cid[f] >= 0:
                continue
            c = len(reps)
            reps.append(f)
            cid[f] = c
            stack = [f]
            while stack:
                x = stack.pop()
                for g in gens:
                    y = g[x]
                    if cid[y] < 0:
                        cid[y] = c
                        stack.append(y)
        return cid, reps


@lru_cache(maxsize=None)
def _ctx(n):
    _check_n(n)
    return _Ctx(n)


# ---------------------------------------------------------------- formulas
@lru_cache(maxsize=None)
def _formula(n, basis):
    c = _ctx(n)
    M = c.M
    gens = c.gens
    size = {}
    members = {}   # s -> all functions whose minimum is s
    reps = {}      # s -> one function per input-symmetry orbit
    binary = basis == "binary"

    def add(s, cands):
        mem, rp = [], []
        for f in cands:
            for h in (f, f ^ M):
                if h in size:
                    continue
                rp.append(h)
                size[h] = s
                stack = [h]
                while stack:
                    x = stack.pop()
                    mem.append(x)
                    for g in gens:
                        y = g[x]
                        if y not in size:
                            size[y] = s
                            stack.append(y)
        members[s], reps[s] = mem, rp

    add(1, list(c.vars) + [v ^ M for v in c.vars])
    s = 1
    while len(size) < c.nfun:
        s += 1
        cand = set()
        for a in range(1, s // 2 + 1):
            b = s - a
            if not members.get(a) or not members.get(b):
                continue
            eb = members[b]
            for r in reps[a]:
                cand.update([r & g for g in eb])
                cand.update([r | g for g in eb])
                if binary:
                    cand.update([r ^ g for g in eb])
        add(s, [f for f in cand if f not in size])
    return size


def min_formula_size(n, basis="demorgan"):
    """dict truth_table_int -> minimum formula size (leaves) for all 2**(2**n) functions."""
    _check_n(n)
    if basis not in ("demorgan", "binary"):
        raise ValueError("basis must be 'demorgan' or 'binary'")
    return dict(sorted(_formula(n, basis).items()))


# ---------------------------------------------------------------- circuits
def _gate_outs(nodes, M):
    out = set()
    for i, u in enumerate(nodes):
        nu = u ^ M
        for v in nodes[i + 1:]:
            nv = v ^ M
            for x in (u & v, nu & v, u & nv, nu & nv, u ^ v):
                out.add(x if x < M - x else M ^ x)
    return out


@lru_cache(maxsize=None)
def _circuit_core(n):
    """(exact, lower, upper): canonical-class bookkeeping; see circuit_size_bounds."""
    c = _ctx(n)
    M = c.M
    K = _K[n]
    cid, creps = c.orbit_ids(True)
    ncls = len(creps)
    canon_f = lambda x: x if x < M - x else M ^ x
    elems = c.elems

    def canon(state):
        best = None
        for lo, hi in elems:
            t = sorted([canon_f(lo[x & 255] | hi[x >> 8]) for x in state])
            if best is None or t < best:
                best = t
        return tuple(best)

    inputs = sorted(canon_f(v) for v in c.vars)
    csize = {cid[v]: 0 for v in inputs}      # class id -> minimum gates seen
    level = [()]
    complete = len(csize) == ncls
    top = level
    for k in range(K + 1):
        if complete:
            break
        top = level
        nxt = set()
        for S in level:
            nodes = inputs + list(S)
            nset = set(nodes)
            for w in _gate_outs(nodes, M):
                csize.setdefault(cid[w], k + 1)
                if k < K and w != 0 and w not in nset:
                    nxt.add(canon(tuple(sorted(S + (w,)))))
        level = sorted(nxt)
        complete = len(csize) == ncls
    reached = K + 1
    if not complete:
        # second half-step: sink gate must read the new gate w1
        for S in top:
            nodes = inputs + list(S)
            nset = set(nodes)
            for w1 in _gate_outs(nodes, M):
                if w1 == 0 or w1 in nset:
                    continue
                for v in nodes:
                    for x in _gate_outs([w1, v], M):
                        csize.setdefault(cid[x], K + 2)
        reached = K + 2
        complete = len(csize) == ncls
    return cid, creps, csize, reached, complete


@lru_cache(maxsize=None)
def _circuit_bounds(n, const_gate):
    _check_n(n)
    c = _ctx(n)
    cid, creps, csize, reached, complete = _circuit_core(n)
    M = c.M
    lower = {}
    upper = {}
    cls_up = {k: v for k, v in csize.items()}
    if not complete:
        # tree bound: gate over two disjoint sub-circuits of total size reached-?; sound upper bound
        known = {f: csize[cid[f]] for f in range(c.nfun) if cid[f] in csize}
        gcid, greps = c.orbit_ids(False)
        by_size = {}
        for f, s in known.items():
            by_size.setdefault(s, []).append(f)
        grep_seen = set()
        urep = {}
        for f in sorted(known):
            if gcid[f] not in grep_seen:
                grep_seen.add(gcid[f])
                urep.setdefault(known[f], []).append(f)
        target = reached + 1
        for su, us in urep.items():
            vs = [f for s2, fs in by_size.items() if s2 + su <= target - 1 for f in fs]
            for u in us:
                nu = u ^ M
                for v in vs:
                    nv = v ^ M
                    for x in (u & v, nu & v, u & nv, nu & nv, u ^ v):
                        k = cid[x]
                        if k not in cls_up:
                            cls_up[k] = target
    for f in range(c.nfun):
        k = cid[f]
        if k in csize:
            lower[f] = csize[k]
            upper[f] = csize[k]
        else:
            lower[f] = reached + 1
            if k in cls_up:
                upper[f] = cls_up[k]
    if const_gate:
        # the 16 operations include the two constant operations: a constant costs 1 gate
        # (the search itself used only the 14 others, which need 2)
        for tab in (lower, upper):
            tab[0] = tab[M] = 1
    return lower, upper


def circuit_size_bounds(n, const_gate=True):
    """(lower, upper): dicts tt -> bound; upper lacks functions with no proven upper bound."""
    _check_n(n)
    lo, up = _circuit_bounds(n, bool(const_gate))
    return dict(sorted(lo.items())), dict(sorted(up.items()))


def min_circuit_size(n, const_gate=True):
    """dict tt -> exact minimum circuit size. Raises RuntimeError if the bounded search
    could not make every value exact (use circuit_size_bounds)."""
    lo, up = circuit_size_bounds(n, const_gate)
    if lo != up:
        raise RuntimeError("circuit sizes for n=%d are not all exact; see circuit_size_bounds" % n)
    return lo


# ---------------------------------------------------------------- classes, maxima
def class_count(n):
    """classes under input negation, input permutation and output negation."""
    _check_n(n)
    return len(_ctx(n).orbit_ids(True)[1])


def class_counts():
    return {n: class_count(n) for n in SUPPORTED}


def max_size(table):
    return max(table.values())
