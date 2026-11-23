"""Susceptibility-guided verification (Line 1 technique; PROPOSAL-RESIDENCY-V3.md, "Technique:
susceptibility-guided verification").

Rerun each unit of work cheaply, estimate its dispersion, and spend the verification budget in
proportion. A variance from 3 reruns is too noisy, so a unit needs at least 10 reruns or pools by task
type. The reruns are charged to the budget.

Reading: a unit's dispersion is the sample variance of its rerun outcomes in [0, 1].
Reading: a unit with fewer than `min_reruns` reruns takes the mean variance of the units of its task
type that have enough reruns; with none, its estimate is None and it receives no share.
Reading: if every estimate is zero or None there is no signal to allocate on, and the result is None.
"""
import statistics as st

MIN_RERUNS = 10  # stated in the proposal, not tuned here


def _variance(outcomes):
    if not outcomes or any(isinstance(x, bool) or not isinstance(x, (int, float)) or not 0 <= x <= 1
                           for x in outcomes):
        raise ValueError("rerun outcomes must be a nonempty list of numbers in [0, 1]")
    return st.variance(outcomes) if len(outcomes) > 1 else None


def dispersion(reruns, task_type=None, min_reruns=MIN_RERUNS):
    """Per-unit dispersion estimate, pooled by task type for under-sampled units."""
    task_type = task_type or {}
    own = {u: _variance(xs) for u, xs in reruns.items()}
    enough = {u: v for u, v in own.items() if len(reruns[u]) >= min_reruns}
    out = {}
    for u in reruns:
        if u in enough:
            out[u] = enough[u]
            continue
        kind = task_type.get(u)
        peers = [v for p, v in enough.items() if kind is not None and task_type.get(p) == kind]
        out[u] = st.fmean(peers) if peers else None
    return out


def allocate(reruns, budget, rerun_cost, task_type=None, min_reruns=MIN_RERUNS):
    """Verification budget per unit, proportional to dispersion, after charging the reruns."""
    for name, x in (("budget", budget), ("rerun_cost", rerun_cost)):
        if isinstance(x, bool) or not isinstance(x, (int, float)) or x < 0:
            raise ValueError(f"{name} must be a non-negative number")
    remaining = budget - rerun_cost * sum(len(xs) for xs in reruns.values())
    if remaining < 0:
        raise ValueError("reruns cost more than the budget")
    est = dispersion(reruns, task_type, min_reruns)
    total = sum(v for v in est.values() if v)
    if total == 0:
        return None
    return {u: (remaining * v / total if v else 0.0) for u, v in est.items()}
