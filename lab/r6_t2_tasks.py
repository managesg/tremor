"""R6 task T2: formal identity versus 0/1 agreement for PERM_m / HC_m over F_p (F5 / Red Team arm).

A task is a planted arithmetic circuit (gates in the format of `r6_t2_identity`, implementation A). The prompt
shows the circuit as plain text and asks two verdicts: (1) does it agree with the target at every 0/1 point of
the m*m variables, (2) is it equal to the target as a formal polynomial (exponents not reduced).
The label comes ONLY from implementations A (`r6_t2_identity`) and B (`r6_t2_identity_b`) agreeing on both
verdicts; if they disagree, `label` raises LabelDisagreement and never returns. The kind (the generator's
intent) and the seed are never read by `label`, `render_prompt` or `check_claim`.
Answer format (exact, lowercase, no spaces): `agrees=yes;identical=no`. Anything else is wrong, never skipped.
Standard library plus the two checkers; offline.
"""

import hashlib
import itertools
import re
from typing import NamedTuple

from lab import r6_t2_identity as A
from lab import r6_t2_identity_b as B

M_VALUES, P_VALUES, KINDS = A.M_VALUES, A.P_VALUES, A.KINDS
TARGETS = ("perm", "hc")
GATE_LIMIT = 4096
TAG = "gen-T2"
_ANSWER = re.compile(r"agrees=(yes|no);identical=(yes|no)")
_OPSYM = {"add": "+", "sub": "-", "mul": "*"}


class T2TaskError(ValueError):
    """Bad input to generate, render_prompt, label, check_claim or the registry."""


class LabelDisagreement(Exception):
    """Implementations A and B gave different verdicts: no label is emitted."""


class Task(NamedTuple):
    m: int
    p: int
    kind: str       # the generator's intent; never read by label(), render_prompt() or check_claim()
    seed: int
    target: str     # "perm" or "hc"
    circuit: tuple  # A-format gates


class Label(NamedTuple):
    agrees_on_01: bool
    identical: bool


def _int(v, name, lo, hi):
    if isinstance(v, bool) or not isinstance(v, int) or v < lo or v > hi:
        raise T2TaskError(f"{name} must be an integer in [{lo}, {hi}]")
    return v


def _check_mp(m, p):
    if isinstance(m, bool) or not isinstance(m, int) or m not in M_VALUES:
        raise T2TaskError(f"m must be one of {M_VALUES}")
    if isinstance(p, bool) or not isinstance(p, int) or p not in P_VALUES:
        raise T2TaskError(f"p must be one of {P_VALUES}")


def _check_task(t):
    """Validates only what label and render use: not the kind, not the seed."""
    if not isinstance(t, Task):
        raise T2TaskError("task must be a Task")
    _check_mp(t.m, t.p)
    if t.target not in TARGETS:
        raise T2TaskError("target must be perm or hc")
    _check_circuit(t.circuit, t.m)
    return t


def _check_circuit(circuit, m):
    """Once, for every consumer: tuple of tuple gates, known ops, no forward refs, variables in range, size bound.
    A constant may be any non-negative int (eval reduces it mod p); label then refuses it via A and B."""
    if not isinstance(circuit, tuple) or not circuit or len(circuit) > GATE_LIMIT:
        raise T2TaskError("circuit must be a non-empty tuple of at most GATE_LIMIT gates")
    for idx, g in enumerate(circuit):
        if not isinstance(g, tuple) or len(g) != 3:
            raise T2TaskError(f"gate {idx}: must be a 3-tuple")
        op, a, b = g
        if op == "const":
            if isinstance(a, bool) or not isinstance(a, int) or a < 0 or b is not None:
                raise T2TaskError(f"gate {idx}: bad constant")
        elif op in _OPSYM:
            for x in (a, b):
                if isinstance(x, int) and not isinstance(x, bool):
                    if not 0 <= x < idx:
                        raise T2TaskError(f"gate {idx}: operand is not an earlier gate")
                elif not (isinstance(x, tuple) and len(x) == 3 and x[0] == "var"
                          and all(isinstance(v, int) and not isinstance(v, bool) and 0 <= v < m for v in x[1:])):
                    raise T2TaskError(f"gate {idx}: bad operand")
        else:
            raise T2TaskError(f"gate {idx}: unknown op")


def generate(m, p, kind, seed):
    """Same (m, p, kind, seed) gives the same Task. The seed is hashed before it reaches the planter."""
    _check_mp(m, p)
    if not isinstance(kind, str) or kind not in KINDS:
        raise T2TaskError("kind must be one of " + repr(KINDS))
    _int(seed, "seed", -2**63, 2**63 - 1)
    digest = hashlib.sha256(f"{TAG}:{m}:{p}:{kind}:{seed}".encode()).digest()
    inst = A.planted(m, p, kind, int.from_bytes(digest[:8], "big") >> 1)
    return Task(m, p, kind, seed, inst["target"], tuple(inst["circuit"]))


def _to_b(circuit):
    """A format -> B format: variables 1-based, B's gate and constant spelling."""
    def op(x):
        return x[1] if x[0] == "g" else ("x", x[1] + 1, x[2] + 1)

    return tuple(("const", l[1], None) if o == "const" else (o, op(l), op(r))
                 for o, l, r in A.circuit_to_canonical(circuit))


def label(task):
    """(agrees_on_01, identical) from A and B; raises LabelDisagreement if they differ, T2TaskError on a bad task."""
    t = _check_task(task)
    try:
        return _label(t)
    except A.T2Refusal as e:  # e.g. a constant >= p
        raise T2TaskError(str(e)) from e


def _label(t):
    ta = A.target_by_name(t.target, t.m, t.p)
    tb = B.perm_target(t.m, t.p) if t.target == "perm" else B.hc_target(t.m, t.p)
    a = (A.agrees_on_01(t.circuit, ta, t.m, t.p, gate_limit=GATE_LIMIT),
         A.identical_as_polynomials(t.circuit, ta, t.m, t.p, gate_limit=GATE_LIMIT))
    cb = _to_b(t.circuit)
    b = (B.agrees_on_01(cb, tb, t.m, t.p, GATE_LIMIT), B.identical_as_polynomials(cb, tb, t.m, t.p, GATE_LIMIT))
    if a != b:
        raise LabelDisagreement(f"A={a} B={b}")
    return Label(*a)


def _operand(x):
    return f"g{x}" if isinstance(x, int) else f"x[{x[1] + 1},{x[2] + 1}]"


def render_prompt(task):
    t = _check_task(task)
    lines = []
    for i, (op, a, b) in enumerate(t.circuit):
        lines.append(f"g{i} = const {a}" if op == "const" else f"g{i} = {_operand(a)} {_OPSYM[op]} {_operand(b)}")
    name = "PERM" if t.target == "perm" else "HC"
    cyc = "all permutations s" if t.target == "perm" else "all permutations s that are one cycle of length " + str(t.m)
    return (
        f"Arithmetic circuit over F_{t.p} (integers mod {t.p}) in the variables x[i,j], 1 <= i,j <= {t.m}.\n"
        "Gates, in order; the last gate is the output; gK is the value of gate K:\n"
        + "\n".join(lines) + "\n"
        f"Target {name}_{t.m} = sum over {cyc} of {{1..{t.m}}} of x[1,s(1)]*x[2,s(2)]*...*x[{t.m},s({t.m})].\n"
        f"Question 1: does the circuit equal {name}_{t.m} at every point where each variable is 0 or 1?\n"
        "Question 2: are the circuit and the target equal as polynomials (same coefficients on every monomial,\n"
        "exponents not reduced, so x*x and x are different monomials)?\n"
        "Answer exactly, lowercase, no spaces: agrees=yes;identical=no (each verdict yes or no).\n"
    )


def prompt_sha256(task):
    return hashlib.sha256(render_prompt(task).encode("ascii")).hexdigest()


def parse_claim(claim):
    """(agrees, identical) as bools, or None when the claim is not exactly the answer format."""
    if type(claim) is not str:
        return None
    m = _ANSWER.fullmatch(claim)
    return None if m is None else (m.group(1) == "yes", m.group(2) == "yes")


def check_claim(task, claim):
    """"correct" only when the claim is well formed and both verdicts equal the label; else "wrong"."""
    t = _check_task(task)
    got = parse_claim(claim)
    if got is None:
        return "wrong"
    return "correct" if got == tuple(label(t)) else "wrong"


def registry(task):
    """Functions closed over the circuit, exposing only what the prompt shows (not the kind, seed or label).
    eval_circuit(point) and eval_target(point): point is a flat row-major tuple of m*m ints in 0..p-1.

    Unlike the plan's registry (int -> int below 2^64), these take a tuple and recompute on every call: the
    circuit has at most GATE_LIMIT gates and eval_target sums at most 4! = 24 permutations (m <= 4), so each
    call is bounded work with no precomputed table; the plan's int signature is for unbounded functions."""
    t = _check_task(task)
    circuit, m, p, target = t.circuit, t.m, t.p, t.target

    def _point(pt):
        if (not isinstance(pt, tuple) or len(pt) != m * m
                or any(isinstance(v, bool) or not isinstance(v, int) or not 0 <= v < p for v in pt)):
            raise T2TaskError("point must be a tuple of m*m ints in 0..p-1")
        return pt

    def eval_circuit(pt):
        pt = _point(pt)
        vals = []
        for op, a, b in circuit:
            if op == "const":
                vals.append(a % p)
                continue
            x, y = (vals[o] if isinstance(o, int) else pt[o[1] * m + o[2]] for o in (a, b))
            vals.append((x * y if op == "mul" else x + y if op == "add" else x - y) % p)
        return vals[-1]

    def eval_target(pt):
        pt = _point(pt)
        total = 0
        for s in itertools.permutations(range(m)):
            if target == "hc":
                i, n = s[0], 1
                while i != 0:
                    i, n = s[i], n + 1
                if n != m:
                    continue
            prod = 1
            for i in range(m):
                prod *= pt[i * m + s[i]]
            total += prod
        return total % p

    return {"eval_circuit": eval_circuit, "eval_target": eval_target}
