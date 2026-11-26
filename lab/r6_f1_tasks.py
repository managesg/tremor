"""R6 family F1 (SAT, #SAT): deterministic 3-CNF generator and a mechanical oracle (n <= 20).

Claim = a witness (a satisfying assignment) or a model count. The oracle is the satisfying set as a 2^n-bit
integer: bit i is set iff assignment i satisfies the formula, where variable v (1-based) is true in
assignment i iff bit v-1 of i is set. Verdicts come only from `check_witness` / `check_count`; nothing here
reads gates, rubric or confidence.
"""

import hashlib
import random
from typing import NamedTuple

N_MIN, N_MAX = 3, 20
# Measured on this host (n=20): solve takes 0.12 s at m=85 and 0.74 s at m=4000, linear in m at about 0.16 ms per
# clause (one 2^20-bit big-int op per literal). The cap keeps every oracle call near 1 s; a larger m is refused.
M_MAX = 4000
KINDS = ("sat", "count")
TAG = "gen-F1"


def _task_seed(tag, seed, task):
    """Copy of lab.l3c_harness.task_seed (same bytes), kept local so this module imports nothing from the L3 code."""
    _int(seed, "seed", -2**63, 2**63 - 1)
    _int(task, "task", 0, 10**12)
    if not isinstance(tag, str) or not tag:
        raise ValueError("tag must be a nonempty string")
    return int.from_bytes(hashlib.sha256(f"{tag}:{seed}:{task}".encode()).digest()[:8], "big") >> 1


class Formula(NamedTuple):
    n: int
    clauses: tuple  # tuple of 3-tuples of distinct-variable signed ints, +v = x_v, -v = NOT x_v


def _int(v, name, lo, hi=None):
    if isinstance(v, bool) or not isinstance(v, int) or v < lo or (hi is not None and v > hi):
        raise ValueError(f"{name} must be an integer >= {lo}" + (f" and <= {hi}" if hi is not None else ""))
    return v


def _check_formula(f):
    if not isinstance(f, Formula):
        raise ValueError("formula must be a Formula")
    _int(f.n, "n", N_MIN, N_MAX)
    if not isinstance(f.clauses, tuple) or not f.clauses:
        raise ValueError("clauses must be a nonempty tuple")
    for c in f.clauses:
        if not (isinstance(c, tuple) and len(c) == 3):
            raise ValueError("each clause must be a 3-tuple")
        for lit in c:
            _int(abs(lit) if isinstance(lit, int) and not isinstance(lit, bool) else lit, "literal", 1, f.n)
        if len({abs(x) for x in c}) != 3:
            raise ValueError("a clause needs 3 distinct variables")
    return f


def generate(n, m, seed):
    """Random 3-CNF over n variables with m clauses (m <= M_MAX); same (n, m, seed) gives the same formula.

    The formula may be unsatisfiable; answer it with check_sat_claim (WITNESS: NONE is the right answer then)."""
    _int(n, "n", N_MIN, N_MAX)
    _int(m, "m", 1, M_MAX)
    _int(seed, "seed", -2**63, 2**63 - 1)
    rng = random.Random(_task_seed(f"{TAG}:{n}:{m}", seed, 0))
    clauses = tuple(tuple(v * rng.choice((1, -1)) for v in rng.sample(range(1, n + 1), 3)) for _ in range(m))
    return Formula(n, clauses)


def _lit(lit):
    return f"x{lit}" if lit > 0 else f"NOT x{-lit}"


def _cnf_text(f):
    return "\n".join("(" + " OR ".join(_lit(x) for x in c) + ")" for c in f.clauses)


def render_prompt(formula, kind):
    """Synthetic prompt text (ASCII, fixed template, no private data); same input gives the same bytes."""
    _check_formula(formula)
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}")
    n = formula.n
    head = (f"Below is a Boolean formula in conjunctive normal form over variables x1..x{n}. "
            f"It is the AND of the {len(formula.clauses)} clauses listed, one per line; "
            "each clause is the OR of its three literals.\n\n" + _cnf_text(formula) + "\n\n")
    if kind == "sat":
        ask = ("Task: give one assignment that satisfies every clause. Answer on one line as "
               f"'WITNESS: ' followed by exactly {n} characters, each 0 or 1, the character at position v "
               "being the value of xv (0 = false, 1 = true). If no assignment satisfies every clause, "
               "answer 'WITNESS: NONE'.")
    else:
        ask = (f"Task: count the assignments of x1..x{n} (out of 2^{n}) that satisfy every clause. "
               "Answer on one line as 'COUNT: ' followed by a non-negative decimal integer.")
    return head + ask + "\n"


def prompt_sha256(formula, kind):
    return hashlib.sha256(render_prompt(formula, kind).encode("ascii")).hexdigest()


def _var_mask(v, n):
    """2^n-bit mask of the assignments in which variable v (1-based) is true."""
    half = 1 << (v - 1)
    period = 2 * half
    unit = ((1 << half) - 1) << half
    return unit * (((1 << (1 << n)) - 1) // ((1 << period) - 1))


def solve(formula):
    """Satisfying set as a 2^n-bit integer, computed bit-parallel (one big-int op per literal)."""
    _check_formula(formula)
    n = formula.n
    full = (1 << (1 << n)) - 1
    pos = {v: _var_mask(v, n) for v in range(1, n + 1)}
    sat = full
    for c in formula.clauses:
        cl = 0
        for lit in c:
            cl |= pos[lit] if lit > 0 else full ^ pos[-lit]
        sat &= cl
    return sat


def model_count(formula):
    return solve(formula).bit_count()


def check_witness(formula, assignment):
    """True iff `assignment` (a tuple/list of n ints, each 0 or 1, entry v-1 = value of xv) satisfies the formula.

    Malformed claims (bools, non-0/1 entries, wrong length, non-sequence) raise ValueError; the caller must
    treat a raise as pass 0, never as an error to skip."""
    _check_formula(formula)
    if not isinstance(assignment, (tuple, list)) or len(assignment) != formula.n:
        raise ValueError(f"assignment must be a sequence of exactly {formula.n} entries")
    for a in assignment:
        if isinstance(a, bool) or not isinstance(a, int) or a not in (0, 1):
            raise ValueError("assignment entries must be the integers 0 or 1")
    return all(any((assignment[abs(x) - 1] == 1) == (x > 0) for x in c) for c in formula.clauses)


def check_sat_claim(formula, answer):
    """Verdict for the 'sat' prompt: `answer` is the string "NONE" or an assignment as in check_witness.

    "NONE" is correct iff the formula has no model; a witness is correct iff it satisfies every clause (so on an
    unsatisfiable formula every witness is wrong). Malformed answers raise ValueError: treat a raise as pass 0."""
    _check_formula(formula)
    if isinstance(answer, str):
        if answer != "NONE":
            raise ValueError('a string answer must be exactly "NONE"')
        return solve(formula) == 0
    return check_witness(formula, answer)


def check_count(formula, claimed):
    """True iff `claimed` equals the number of satisfying assignments. Bool, negative or > 2^n raise ValueError
    (the caller must treat a raise as pass 0)."""
    _check_formula(formula)
    _int(claimed, "claimed", 0, 1 << formula.n)
    return claimed == model_count(formula)


def performance_row(task, n, rerun, agent, passed, conf):
    """R5 harness row matching lab/r6_scorecard.py `performance_row` (pass is 0/1; conf None or in [0, 1]).

    `n` is the TEAM SIZE of the H2 row, not the number of variables. `passed` must come straight from the
    check_* functions (a ValueError there is pass False), never from a gate, rubric or confidence."""
    if not isinstance(task, str):
        raise ValueError("task must be a string")
    _int(n, "n", 0)
    _int(rerun, "rerun", 0)
    _int(agent, "agent", 0)
    if not isinstance(passed, bool):
        raise ValueError("passed must be a bool")
    if conf is not None and (isinstance(conf, bool) or not isinstance(conf, (int, float)) or not 0 <= conf <= 1):
        raise ValueError("conf must be None or a number in [0, 1]")
    return {"task": task, "family": "F1", "n": n, "rerun": rerun, "agent": agent, "pass": int(passed),
            "conf": conf}
