"""R6 task T3: finite lemmas on bitmasks, planted true or false (F5 / Red Team arm).

The statements (a) and (b) are candidate statements taken from the review `VPVNP_CLAIM_REVIEW_20261126.md`
(T3). The source paper is only where the idea came from: no label here comes from it, from the template, or
from the variant. A label is the result of `r6_predicates.check_lemma` over the whole declared domain.

Domain: S in range(2**k), 3 <= k <= 14, S read as a subset of {0..k-1} (bit a set = a in S). S is balanced
when k/3 <= |S| <= 2k/3, tested in integers (3|S| >= k and 3|S| <= 2k). Both predicates are vacuously true
for unbalanced S.
  kind "a": 9|S|(k-|S|) >= 2k^2.
  kind "b": w[a] = [a in S](k-1-a) - |{b in S : b > a}| for a < k, and 81 * sum(w[a]^2) >= 4k^3.
Variant "planted_false" changes ONE constant or comparison of the true source (list MUTATIONS); the test
suite checks that every mutation has a counterexample for every k in 3..14. Standard library only.

Protocol notes. (1) The seed only chooses among the mutations, so a true prompt is the same for every seed and
there are only len(distinct_instances()) = 120 distinct prompts (24 true, 96 false): a pooled run must
deduplicate by prompt_sha256 and use n <= 120. (2) The true source is fixed by (kind, k): a proposer shown the
generator or the true source reveals the label by diffing the prompt against it, so the proposer must never
be given the source. (3) Some mutations fail on most balanced S (easy); the "tight" ones fail on few S: kind a
admits only the size just below k/3 (fails exactly on |S| = ceil(k/3)-1); kind b replaces the right-hand side by
TIGHT_B[k] + 1, one past the smallest value of 81|w|^2 over balanced S (TIGHT_B comes from an offline brute
force; the tests re-check by check_lemma that the constant holds and the constant + 1 fails).
"""

import hashlib
from typing import NamedTuple

from lab import r6_predicates as rp

K_MIN, K_MAX = 3, 14
KINDS = ("a", "b")
VARIANTS = ("true", "planted_false")
TAG = "gen-T3"
BAL = "(3*popcount(S) < {k} or 3*popcount(S) > 2*{k}) or "
SOURCES = {
    "a": BAL + "9*popcount(S)*({k}-popcount(S)) >= 2*{k}*{k}",
    "b": BAL + "81*sum((bit(S, a)*({k}-1-a) - popcount(S >> (a+1)))*(bit(S, a)*({k}-1-a) - popcount(S >> (a+1)))"
              " for a in range({k})) >= 4*{k}*{k}*{k}",
}
# Smallest 81*sum(w^2) over balanced S, per k (offline brute force; re-verified by the tests via check_lemma).
TIGHT_B = {3: 162, 4: 486, 5: 810, 6: 1134, 7: 2268, 8: 2997, 9: 3726, 10: 6156, 11: 7452, 12: 8748, 13: 12960,
           14: 14985}
# (old fragment, new fragment): exactly one occurrence in the true source; one constant or comparison changes.
# {m} = TIGHT_B[k] + 1.
MUTATIONS = {
    "a": (("2*{k}*{k}", "3*{k}*{k}"), ("9*popcount", "7*popcount"), ("3*popcount(S) < {k}", "3*popcount(S) < 0"),
          ("3*popcount(S) < {k}", "3*popcount(S) < {k}-3")),
    "b": (("4*{k}*{k}*{k}", "8*{k}*{k}*{k}"), (">= 4*", "<= 4*"), ("3*popcount(S) > 2*{k}", "3*popcount(S) > 3*{k}"),
          ("4*{k}*{k}*{k}", "{m}")),
}


def _int(v, name, lo, hi=None):
    if isinstance(v, bool) or not isinstance(v, int) or v < lo or (hi is not None and v > hi):
        raise ValueError(f"{name} must be an integer >= {lo}" + (f" and <= {hi}" if hi is not None else ""))
    return v


def _task_seed(tag, seed, task):
    """Copy of lab.l3c_harness.task_seed (same bytes), kept local so this module imports nothing from the L3 code."""
    _int(seed, "seed", -2**63, 2**63 - 1)
    _int(task, "task", 0, 10**12)
    if not isinstance(tag, str) or not tag:
        raise ValueError("tag must be a nonempty string")
    return int.from_bytes(hashlib.sha256(f"{tag}:{seed}:{task}".encode()).digest()[:8], "big") >> 1


class Task(NamedTuple):
    kind: str
    k: int          # domain: every S in range(2**k)
    seed: int
    variant: str    # the generator's intent; never read by label() or check_claim()
    source: str     # predicate in the r6_predicates language; free variable S


class Label(NamedTuple):
    holds: bool
    counterexample: object  # the first failing S (int) when holds is False, else None


def _check_task(t):
    if not isinstance(t, Task):
        raise ValueError("task must be a Task")
    if t.kind not in KINDS or t.variant not in VARIANTS or not isinstance(t.source, str):
        raise ValueError("bad task fields")
    _int(t.k, "k", K_MIN, K_MAX)
    _int(t.seed, "seed", -2**63, 2**63 - 1)
    return t


def generate(kind, k, seed, variant):
    """Same (kind, k, seed, variant) gives the same Task. The seed picks which mutation a planted variant gets."""
    if kind not in KINDS:
        raise ValueError("kind must be one of " + repr(KINDS))
    if variant not in VARIANTS:
        raise ValueError("variant must be one of " + repr(VARIANTS))
    _int(k, "k", K_MIN, K_MAX)
    src = SOURCES[kind].format(k=k)
    if variant == "planted_false":
        ms = MUTATIONS[kind]
        old, new = ms[_task_seed(f"{TAG}:{kind}:{k}", seed, 0) % len(ms)]
        old, new = old.format(k=k, m=TIGHT_B[k] + 1), new.format(k=k, m=TIGHT_B[k] + 1)
        if src.count(old) != 1:
            raise AssertionError("mutation fragment must occur exactly once")
        src = src.replace(old, new)
    else:
        _task_seed(f"{TAG}:{kind}:{k}", seed, 0)  # validates the seed
    return Task(kind, k, seed, variant, src)


def _domain(t):
    return ({"S": s} for s in range(1 << t.k))


def label(task, step_limit, total_steps):
    """Truth by exhaustive check_lemma over the declared domain. Raises PredicateRefused (with .env, .steps)
    when a budget is hit; the template, the variant and the kind are never consulted."""
    t = _check_task(task)
    p = rp.parse(t.source)
    bad = rp.check_lemma(p, _domain(t), step_limit, total_steps)
    if bad is None:
        return Label(True, None)
    return Label(False, bad["S"])


def render_prompt(task):
    t = _check_task(task)
    return (
        "Finite lemma over bitmasks.\n"
        f"Domain: every integer S with 0 <= S < 2**{t.k}; bit a of S set means a is in the subset.\n"
        "Predicate (Python-like expression over S; popcount(x) counts set bits, bit(x, i) is bit i of x,\n"
        "x >> n shifts right, sum(e for a in range(n)) adds e over a = 0..n-1):\n"
        f"{t.source}\n"
        "Question: is the predicate True for every S in the domain?\n"
        "Answer with the single word true, or with one integer S in the domain for which it is False.\n"
    )


def prompt_sha256(task):
    return hashlib.sha256(render_prompt(task).encode("ascii")).hexdigest()


def check_claim(task, answer, step_limit, total_steps):
    """Verdict "correct", "wrong" or "malformed". 'true' is correct only if check_lemma finds no counterexample
    over the whole domain; an int answer is correct only if the predicate is re-evaluated False on it."""
    t = _check_task(task)
    if answer == "true" and isinstance(answer, str):
        return "correct" if label(t, step_limit, total_steps).holds else "wrong"
    if type(answer) is not int or not 0 <= answer < 1 << t.k:  # subclasses (bool included) are refused
        return "malformed"
    p = rp.parse(t.source)
    return "wrong" if rp.check_lemma(p, [{"S": answer}], step_limit, total_steps) is None else "correct"


def distinct_instances():
    """One Task per distinct prompt (24 true, 96 false, 120 in all), seeds chosen so each mutation is reached."""
    out, seen = [], set()
    for kind in KINDS:
        for k in range(K_MIN, K_MAX + 1):
            for variant in VARIANTS:
                for seed in range(200 if variant == "planted_false" else 1):
                    t = generate(kind, k, seed, variant)
                    h = prompt_sha256(t)
                    if h not in seen:
                        seen.add(h)
                        out.append(t)
    return out


# ---------------------------------------------------------------------------------------------------------------
# Part 2: (c) transversal rank additivity and (d) the square-root-of-rank triangle on Mat_mu(F_2), 2 <= mu <= 3.
# A matrix is an int of mu*mu bits, row-major (bit mu*i+j = entry (i,j)); W + W' over F_2 is x ^ y. The ranks come
# from ONE per-task registry function rk(x, r, c) = F_2 rank of the r x c row-major matrix x (r, c <= 2*mu), which
# lies outside the step limit (one step per call, plan section 3). Labels still come only from check_lemma over
# every pair (x, y) in range(2**(mu*mu))**2. Transversal = row spaces meet in 0 and column spaces meet in 0,
# written with rk of the row stack (2mu x mu) and of the column stack (mu x 2mu): rk(stack) == rk x + rk y.
# (d) is integer-only: sqrt(r) <= sqrt(p)+sqrt(q) and the reverse, with p, q, r = rk x, rk y, rk(x+y), is
# (r-p-q)^2 <= 4pq. Planted false variants change one fragment (MUTATIONS_CD) and have a counterexample for mu=2,3.
# ---------------------------------------------------------------------------------------------------------------
MU_MIN, MU_MAX = 2, 3
KINDS_CD = ("c", "d")
# Every per-task registry function. The plan's `scorer_ids` must list each of them (plan section 3, registry rule).
SCORER_IDS = ("rank_f2",)
TAG_CD = "gen-T3cd"


def _make_rank(mu):
    """Pure registry function for one task; closes over the three shapes (r, c) the lemmas use, as ints only."""
    shapes = ((mu, mu), (2 * mu, mu), (mu, 2 * mu))

    def rank_f2(x, r, c):
        if (type(x) is not int or type(r) is not int or type(c) is not int or (r, c) not in shapes
                or not 0 <= x < 1 << (r * c)):
            raise rp.PredicateRefused("rank_f2 argument")
        mask = (1 << c) - 1
        basis = []
        for i in range(r):
            v = (x >> (c * i)) & mask
            for b in basis:
                v = min(v, v ^ b)
            if v:
                basis.append(v)
        return len(basis)
    return rank_f2


def registry_cd(mu):
    _int(mu, "mu", MU_MIN, MU_MAX)
    return {"rk": (3, _make_rank(mu))}


def _parts_cd(mu):
    m2, M = mu * mu, (1 << mu) - 1
    rx, ry = f"rk(x, {mu}, {mu})", f"rk(y, {mu}, {mu})"
    rs = f"rk(x | (y << {m2}), {2 * mu}, {mu})"
    cs = (f"rk(sum((((x >> ({mu}*i)) & {M}) << ({2 * mu}*i)) | (((y >> ({mu}*i)) & {M}) << ({2 * mu}*i+{mu}))"
          f" for i in range({mu})), {mu}, {2 * mu})")
    return rx, ry, rs, cs


def _sources_cd(kind, mu):
    rx, ry, rs, cs = _parts_cd(mu)
    if kind == "c":
        row, col = f"{rs} == {rx} + {ry}", f"{cs} == {rx} + {ry}"
        concl = f"rk(x ^ y, {mu}, {mu}) == {rx} + {ry}"
        return f"not ({row} and {col}) or {concl}"
    r = f"rk(x ^ y, {mu}, {mu})"
    return f"({r} - {rx} - {ry}) * ({r} - {rx} - {ry}) <= 4 * {rx} * {ry}"


def _mutations_cd(kind, mu):
    rx, ry, rs, cs = _parts_cd(mu)
    if kind == "c":
        row, col = f"{rs} == {rx} + {ry}", f"{cs} == {rx} + {ry}"
        concl = f"rk(x ^ y, {mu}, {mu}) == {rx} + {ry}"
        return ((f"not ({row} and {col}) or ", ""), (f" and {col}", ""), (f"not ({row} and ", "not ("),
                (concl, concl + " + 1"))
    return (("<= 4 *", "<= 3 *"), ("<= 4 *", "< 4 *"), ("<= 4 *", "<= 2 *"),
            (f"4 * {rx} * {ry}", f"4 * {rx} + {ry}"))


class TaskCD(NamedTuple):
    kind: str       # "c" or "d"
    mu: int         # domain: every pair (x, y), x and y in range(2**(mu*mu))
    seed: int
    variant: str    # the generator's intent; never read by label_cd()
    source: str


def generate_cd(kind, mu, seed, variant):
    if kind not in KINDS_CD:
        raise ValueError("kind must be one of " + repr(KINDS_CD))
    if variant not in VARIANTS:
        raise ValueError("variant must be one of " + repr(VARIANTS))
    _int(mu, "mu", MU_MIN, MU_MAX)
    h = _task_seed(f"{TAG_CD}:{kind}:{mu}", seed, 0)
    src = _sources_cd(kind, mu)
    if variant == "planted_false":
        ms = _mutations_cd(kind, mu)
        old, new = ms[h % len(ms)]
        if src.count(old) != 1:
            raise AssertionError("mutation fragment must occur exactly once")
        src = src.replace(old, new)
    return TaskCD(kind, mu, seed, variant, src)


def label_cd(task, step_limit, total_steps):
    """Truth by exhaustive check_lemma over all pairs, with the per-task registry; variant and kind are not read."""
    t = task
    if not isinstance(t, TaskCD) or t.kind not in KINDS_CD or t.variant not in VARIANTS or not isinstance(t.source, str):
        raise ValueError("bad task")
    _int(t.mu, "mu", MU_MIN, MU_MAX)
    p = rp.parse(t.source, registry_cd(t.mu))
    n = 1 << (t.mu * t.mu)
    bad = rp.check_lemma(p, ({"x": x, "y": y} for x in range(n) for y in range(n)), step_limit, total_steps)
    return Label(True, None) if bad is None else Label(False, (bad["x"], bad["y"]))
