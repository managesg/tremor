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
import statistics as st

MIN_RERUNS = 10  # stated in the proposal, not tuned here


def _int(x, lo):
    return not isinstance(x, bool) and isinstance(x, int) and x >= lo


def _overdispersion(counts, n):
    if not _int(n, 1):
        raise ValueError("items per unit must be a positive integer")
    if not counts or any(not _int(c, 0) or c > n for c in counts):
        raise ValueError("rerun pass counts must be a nonempty list of integers in [0, items]")
    p = st.fmean(counts) / n
    if n == 1 or len(counts) < 2 or p in (0, 1):
        return None
    return st.variance(counts) / (n * p * (1 - p))


def dispersion(reruns, items, task_type=None, min_reruns=MIN_RERUNS):
    """Per-unit overdispersion estimate, pooled by task type for under-sampled units."""
    if not _int(min_reruns, 2):
        raise ValueError("min_reruns must be an integer >= 2")
    missing = set(reruns) - set(items)
    if missing:
        raise ValueError(f"no item count for units {sorted(missing)}")
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
        out[u] = st.fmean(peers) if peers else None
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
    try:
        remaining = budget - rerun_cost * sum(len(cs) for cs in reruns.values())
    except OverflowError:  # a cost too large to represent cannot fit in a finite budget
        raise ValueError("reruns cost more than the budget") from None
    if remaining < 0:
        raise ValueError("reruns cost more than the budget")
    est = dispersion(reruns, items, task_type, min_reruns)
    total = sum(v for v in est.values() if v)
    if total == 0:
        return None
    return {u: (remaining * (v / total) if v else 0.0) for u, v in est.items()}  # share first: no overflow
