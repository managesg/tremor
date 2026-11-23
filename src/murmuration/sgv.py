"""Susceptibility-guided verification (Line 1 technique; PROPOSAL-RESIDENCY-V3.md, "Technique:
susceptibility-guided verification").

Rerun each unit of work cheaply, estimate its dispersion, and spend the verification budget in
proportion. A variance from 3 reruns is too noisy, so a unit needs at least 10 reruns or pools by task
type. The reruns are charged to the budget.

Reading: a unit's overdispersion is the sample variance of its rerun outcomes in [0, 1] divided by
m (1 - m), the largest variance a [0, 1] outcome with mean m can have (Bernoulli). It is undefined (None)
when m is 0 or 1, since then every rerun agrees.
Reading: a unit with fewer than `min_reruns` reruns takes the mean variance of the units of its task
type that have enough reruns; with none, its estimate is None and it receives no share.
Reading: if every estimate is zero or None there is no signal to allocate on, and the result is None.
"""
import statistics as st

MIN_RERUNS = 10  # stated in the proposal, not tuned here


def _overdispersion(outcomes):
    if not outcomes or any(isinstance(x, bool) or not isinstance(x, (int, float)) or not 0 <= x <= 1
                           for x in outcomes):
        raise ValueError("rerun outcomes must be a nonempty list of numbers in [0, 1]")
    m = st.fmean(outcomes)
    if len(outcomes) < 2 or m in (0, 1):
        return None
    return st.variance(outcomes) / (m * (1 - m))


def dispersion(reruns, task_type=None, min_reruns=MIN_RERUNS):
    """Per-unit overdispersion estimate, pooled by task type for under-sampled units."""
    if isinstance(min_reruns, bool) or not isinstance(min_reruns, int) or min_reruns < 2:
        raise ValueError("min_reruns must be an integer >= 2")
    task_type = task_type or {}
    own = {u: _overdispersion(xs) for u, xs in reruns.items()}
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
