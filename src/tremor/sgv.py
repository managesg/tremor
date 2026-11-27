"""Susceptibility-guided verification (Line 1 technique; PROPOSAL-RESIDENCY-V3.md, "Technique:
susceptibility-guided verification").

Rerun each unit of work cheaply, estimate its overdispersion, and spend the verification budget in
proportion. A variance from 3 reruns is too noisy, so a unit needs at least 10 reruns or pools by task
type. The reruns are charged to the budget.

Reading: a unit has `items[u]` checked items; each rerun yields the count of items that passed. Its
overdispersion is the sample variance of those counts over the binomial variance n p (1 - p), with p the
mean pass share (McCullagh and Nelder, as in readouts.overdispersion): 1 when items pass independently,
above 1 when reruns swing together. It is undefined (None) when p is 0 or 1, with fewer than 2 reruns,
and when n is 1, because a single pass/fail item's variance is fixed by its mean and carries no
overdispersion signal.
Reading: a unit with fewer than `min_reruns` reruns takes the mean overdispersion of the units of its
task type that have enough reruns and a defined estimate; with none, its estimate is None and it
receives no share.
Reading: if every estimate is zero or None there is no signal to allocate on, and the result is None.
"""
import math
from fractions import Fraction

MIN_RERUNS = 10  # stated in the proposal, not tuned here


def _int(x, lo):
    return not isinstance(x, bool) and isinstance(x, int) and x >= lo


def _overdispersion(counts, n):
    if not _int(n, 1):
        raise ValueError("items per unit must be a positive integer")
    if not isinstance(counts, (list, tuple)) or not counts or any(not _int(c, 0) or c > n for c in counts):
        raise ValueError("rerun pass counts must be a nonempty list of integers in [0, items]")
    k, total = len(counts), sum(counts)
    if n == 1 or k < 2 or total in (0, n * k):  # decided on the integer sum, not a rounded float
        return None
    # sample variance over n p (1 - p) with p = total / (n k), in exact integers
    num = n * k * (k * sum(c * c for c in counts) - total * total)
    try:
        return num / ((k - 1) * total * (n * k - total))
    except OverflowError:  # a ratio too large for a float
        raise ValueError("overdispersion is too large to represent") from None


def dispersion(reruns, items, task_type=None, min_reruns=MIN_RERUNS):
    """Per-unit overdispersion estimate, pooled by task type for under-sampled units."""
    if not _int(min_reruns, 2):
        raise ValueError("min_reruns must be an integer >= 2")
    if not isinstance(reruns, dict) or not isinstance(items, dict):
        raise ValueError("reruns and items must be dicts keyed by unit")
    if task_type is not None and not isinstance(task_type, dict):
        raise ValueError("task_type must be a dict keyed by unit")
    missing = set(reruns) - set(items)
    if missing:
        raise ValueError(f"no item count for units {sorted(missing, key=repr)}")
    task_type = task_type or {}
    own = {u: _overdispersion(cs, items[u]) for u, cs in reruns.items()}
    enough = {u: v for u, v in own.items() if len(reruns[u]) >= min_reruns}
    out = {}
    for u in reruns:
        if u in enough:
            out[u] = enough[u]
            continue
        kind = task_type.get(u)
        peers = [v for p, v in enough.items()
                 if v is not None and kind is not None and task_type.get(p) == kind]
        # exact mean: a float sum of finite peers can overflow, the exact mean cannot exceed the largest peer
        out[u] = float(sum(map(Fraction, peers)) / len(peers)) if peers else None
    return out


def allocate(reruns, items, budget, rerun_cost, task_type=None, min_reruns=MIN_RERUNS):
    """Verification budget per unit, proportional to overdispersion, after charging the reruns."""
    for name, x in (("budget", budget), ("rerun_cost", rerun_cost)):
        try:
            finite = not isinstance(x, bool) and isinstance(x, (int, float)) and math.isfinite(x)
        except OverflowError:  # an int too large for a float
            finite = False
        if not finite or x < 0:
            raise ValueError(f"{name} must be a finite non-negative number")
    if not isinstance(reruns, dict) or not isinstance(items, dict):
        raise ValueError("reruns and items must be dicts keyed by unit")
    est = dispersion(reruns, items, task_type, min_reruns)  # validates the rerun lists first
    try:
        remaining = budget - rerun_cost * sum(len(cs) for cs in reruns.values())
    except OverflowError:  # a cost too large to represent cannot fit in a finite budget
        raise ValueError("reruns cost more than the budget") from None
    if remaining < 0:
        raise ValueError("reruns cost more than the budget")
    total = sum(Fraction(v) for v in est.values() if v)  # exact: a float total can overflow to inf
    if total == 0:
        return None
    return {u: (float(Fraction(remaining) * Fraction(v) / total) if v else 0.0) for u, v in est.items()}
