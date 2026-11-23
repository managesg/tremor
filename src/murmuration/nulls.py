"""Scripted nulls with exact expected values (WORKPLAN-RESIDENCY-V3, R1 "Scripted nulls, one per line").

Each null is computed by exact enumeration in Fractions; the tests compare it with a hand-derived
closed form. This module covers L1, L2, L3, L4, L6 and L7. The L5 (random-order task choice) control is
lab/r1_l5_random_order_null.py; lab/r1_readout_controls.py keeps fixed-trace L3 readout checks.

Reading (L1): scripted adopters adopt independently with a caller-given probability per dose.
Reading (L3): correlated monitors share a common cause: each episode, with probability c every view
misses together; otherwise each view misses independently with probability p.
Reading (L2): well-mixed epidemic with immunity is the Reed-Frost chain binomial over all generations
in a population of fixed size; immune members are part of the population but never become infected, so
susceptibles = population - immune - seeds; each infective-susceptible contact transmits independently
with probability q.
Reading (L4): iterated-map consolidation is the linear map x' = keep * x + add on the false-note share
(daily errors `add`, consolidation retains a `keep` fraction); recovery is the first night a planted
false share `x0` with no new errors falls to or below `tol`.
Reading (L6): the fixed rule asks for each requested action while ungranted; K asked uses open a grant
from the next round; a granted round with no request is idle (exposure); D consecutive idle rounds close
the grant and reset the use count. Each round requests independently with probability u.
Reading (L7): random blocks are uniformly random partitions of n labelled agents into blocks of size s.
"""
from fractions import Fraction
from itertools import combinations, product
from math import comb

EXACT_BITS = 2 ** 22  # compute guard for recovery_nights (about 1 s of exact arithmetic), not a scientific parameter


def _frac(x, name, lo=0, hi=1):
    if type(x) not in (int, Fraction) or not lo <= x <= hi:
        raise ValueError(f"{name} must be an exact number in [{lo}, {hi}]")
    return Fraction(x)


def _posint(x, name, minimum=1):
    if type(x) is not int or x < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return x


def scripted_adopters(n, p_by_dose):
    """L1: exact mean and variance of the adoption count at each dose, by enumerating all 2^n outcomes."""
    _posint(n, "n")
    if not isinstance(p_by_dose, dict):
        raise ValueError("p_by_dose must be a dict of dose -> adoption probability")
    out = {}
    for dose, p in p_by_dose.items():
        p = _frac(p, "adoption probability")
        dist = {}
        for bits in product((0, 1), repeat=n):
            k = sum(bits)
            dist[k] = dist.get(k, 0) + p ** k * (1 - p) ** (n - k)
        mean = sum(k * w for k, w in dist.items())
        out[dose] = (mean, sum((k - mean) ** 2 * w for k, w in dist.items()))
    return out


def reed_frost(population, immune, seeds, q):
    """L2: exact final-size distribution (total infected, seeds included) of the Reed-Frost chain."""
    _posint(population, "population")
    _posint(immune, "immune", 0)
    _posint(seeds, "seeds")
    if immune + seeds > population:
        raise ValueError("immune members and seeds cannot exceed the population")
    susceptible = population - immune - seeds
    q = _frac(q, "q")
    final, live = {}, {(susceptible, seeds, seeds): Fraction(1)}  # (S, I, total) -> probability
    while live:
        nxt = {}
        for (s, i, total), w in live.items():
            if i == 0 or s == 0:
                final[total] = final.get(total, 0) + w
                continue
            hit = 1 - (1 - q) ** i
            for k in range(s + 1):
                key = (s - k, k, total + k)
                nxt[key] = nxt.get(key, 0) + w * comb(s, k) * hit ** k * (1 - hit) ** (s - k)
        live = nxt
    return {size: w for size, w in final.items() if w}  # drop outcomes of probability zero


def iterated_map(x0, keep, add, nights):
    """L4: exact false-note share after each night, x_{t+1} = keep * x_t + add."""
    x, keep, add = _frac(x0, "x0"), _frac(keep, "keep"), _frac(add, "add")
    if keep + add > 1:
        raise ValueError("keep + add must not exceed 1")
    out = [x]
    for _ in range(_posint(nights, "nights", 0)):
        x = keep * x + add
        out.append(x)
    return out


def recovery_nights(x0, keep, tol):
    """L4: first night a planted share x0 (no new errors) is at or below tol; None if it never is."""
    x, keep, tol = _frac(x0, "x0"), _frac(keep, "keep"), _frac(tol, "tol")
    if x <= tol:
        return 0
    if keep in (0, 1):
        return 1 if keep == 0 else None
    if tol == 0:  # keep^t * x stays positive for every finite t
        return None
    # Exact search by binary lifting: x * keep^t falls as t grows. Square keep until x * keep^(2^i) is at
    # or below tol, then build the answer bit by bit, one exact integer multiplication per step. Every
    # comparison is exact, so the answer cannot be overshot.
    bits = max(keep.numerator.bit_length(), keep.denominator.bit_length())
    # x and tol enter every comparison too, so they count against the guard
    fixed = sum(v.bit_length() for v in (x.numerator, x.denominator, tol.numerator, tol.denominator))

    def low_enough(num, den):  # x * (num / den) <= tol, cross-multiplied in integers
        return x.numerator * num * tol.denominator <= tol.numerator * x.denominator * den

    if fixed > EXACT_BITS // 4:  # keep most of the guard for keep's powers, else every step is near the cap
        raise ValueError("x, keep and tol are too large to compare exactly")
    powers = [(keep.numerator, keep.denominator)]  # keep^(2^i)
    while not low_enough(*powers[-1]):
        # shortcut: powers are exact integers, so refuse rather than guess past EXACT_BITS; raise the
        # limit if an experiment needs keep closer to 1.
        if 2 ** len(powers) * bits + fixed > EXACT_BITS:
            raise ValueError(f"recovery takes more than {2 ** (len(powers) - 1)} nights: "
                             "too many to settle exactly")
        n, d = powers[-1]
        powers.append((n * n, d * d))
    if len(powers) == 1:
        return 1
    t, (an, ad) = 2 ** (len(powers) - 2), powers[-2]  # x * keep^t > tol
    for i in range(len(powers) - 3, -1, -1):
        cn, cd = an * powers[i][0], ad * powers[i][1]
        if not low_enough(cn, cd):
            t, an, ad = t + 2 ** i, cn, cd
    return t + 1


def correlated_monitors(m, p, c):
    """L3: exact P(all m views miss) and pairwise miss correlation phi, by enumerating 2^m miss patterns."""
    _posint(m, "m", 2)
    p, c = _frac(p, "p"), _frac(c, "c")
    all_miss = pair_miss = Fraction(0)
    for bits in product((0, 1), repeat=m):
        k = sum(bits)
        w = (c if k == m else 0) + (1 - c) * p ** k * (1 - p) ** (m - k)
        all_miss += w if k == m else 0
        pair_miss += w if bits[0] and bits[1] else 0
    q = c + (1 - c) * p  # one view's miss probability
    phi = (pair_miss - q * q) / (q * (1 - q)) if 0 < q < 1 else None
    return {"all_miss": all_miss, "pair_miss": pair_miss, "phi": phi}


def fixed_kd(k, d, rounds, u):
    """L6: exact expected (asked actions, idle granted rounds) over all request sequences."""
    _posint(k, "K"), _posint(d, "D"), _posint(rounds, "rounds")
    u = _frac(u, "u")
    asks = exposure = Fraction(0)
    for seq in product((0, 1), repeat=rounds):
        w = Fraction(1)
        for r in seq:
            w *= u if r else 1 - u
        granted, uses, idle, a, e = False, 0, 0, 0, 0
        for r in seq:
            if granted:
                if r:
                    idle = 0
                else:
                    e, idle = e + 1, idle + 1
                    if idle >= d:
                        granted, uses, idle = False, 0, 0
            elif r:
                a, uses = a + 1, uses + 1
                if uses >= k:
                    granted, idle = True, 0
        asks += w * a
        exposure += w * e
    return asks, exposure


def _partitions(items, s):
    if not items:
        yield []
        return
    first, rest = items[0], items[1:]
    for mates in combinations(rest, s - 1):
        left = [x for x in rest if x not in mates]
        for p in _partitions(left, s):
            yield [(first, *mates)] + p


def random_blocks(n, s, pairs):
    """L7: exact expected number of `pairs` placed in the same block, over all equal-size partitions."""
    _posint(n, "n"), _posint(s, "s")
    if n % s:
        raise ValueError("block size must divide the number of agents")
    if isinstance(pairs, (str, bytes)) or not isinstance(pairs, (list, tuple)):
        raise ValueError("pairs must be a list of (agent, agent) tuples")
    for pair in pairs:
        if not isinstance(pair, tuple) or len(pair) != 2 or any(type(x) is not int for x in pair):
            raise ValueError("each pair must be a tuple of two integer agent ids")
        a, b = pair
        if not (0 <= a < n and 0 <= b < n) or a == b:
            raise ValueError("pairs must name two distinct agents in range")
    total = hits = 0
    for part in _partitions(list(range(n)), s):
        where = {x: i for i, block in enumerate(part) for x in block}
        total += 1
        hits += sum(where[a] == where[b] for a, b in pairs)
    return Fraction(hits, total)
