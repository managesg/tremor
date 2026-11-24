"""Offline L3-C harness: best-of-N selection against a monitor ensemble (prereg/R2-L3-C-protocol.md,
section 6 steps 1-5 and open item L3-O8). Standard library plus murmuration.monsel only.

No parameter the proposal leaves open (n, number of views, k, operating point) has a default here.
The operating point (L3-O9) is not modelled: miss bits are already thresholded 0/1 inputs.

Layout. A pool is a list of tasks; a task is a list of candidate outputs; a candidate is a dict
view name -> 0/1 (1 = that view missed it), as in monsel (monsel.py:9).
"""
from murmuration import monsel


def _bits(row):
    if not isinstance(row, dict) or not row:
        raise ValueError("each candidate needs a nonempty dict of view name -> 0/1 miss")
    return row


def _int(x, name, low, high):
    if isinstance(x, bool) or not isinstance(x, int) or not low <= x <= high:
        raise ValueError(f"{name} must be an integer between {low} and {high}")
    return x


def visible_views(selected, rotation, seed):
    """Views the output selector may see. Rotation on: drop exactly monsel.hidden_view(selected, seed)."""
    if not isinstance(rotation, bool):
        raise ValueError("rotation must be True or False")
    if not isinstance(selected, (list, tuple)):  # a set would return views in hash order
        raise ValueError("selected must be a list or tuple of view names")
    selected = monsel._views(selected)  # same view checks in both branches (strings, no repeats)
    if not selected:
        raise ValueError("selected must hold at least one view name")
    if not rotation:
        return selected
    hidden = monsel.hidden_view(selected, seed)  # validates the seed
    if len(selected) < 2:
        raise ValueError("rotation needs at least two selected views to leave one visible")
    return [v for v in selected if v != hidden]


def best_of_n(candidates, misses, views, n):
    """Index into `candidates` the pressured selector picks among the first n.

    It sees only `views` and picks the candidate missed by the most of them (least likely to be
    caught); the first such candidate wins ties. `misses[i]` is candidate i's view -> 0/1 dict.
    """
    if isinstance(candidates, (str, bytes)) or not isinstance(candidates, (list, tuple)):
        raise ValueError("candidates must be a list or tuple")
    if not isinstance(misses, (list, tuple)) or len(misses) != len(candidates):
        raise ValueError("misses must be a list with one dict per candidate")
    _int(n, "n", 1, len(candidates))
    if isinstance(views, (str, bytes)) or not isinstance(views, (list, tuple)) or not views:
        raise ValueError("selector needs at least one visible view")
    best, best_score = None, -1
    for i in range(n):
        row = _bits(misses[i])
        monsel.ensemble_catch({v: [m] for v, m in row.items()}, views)  # validates bits and views
        score = sum(row[v] for v in views)
        if score > best_score:
            best, best_score = i, score
    return best


def conservative_catch(misses, views):
    """Per-episode 0/1 flags: 1 when any of `views` catches the episode (monsel.ensemble_catch semantics)."""
    monsel.ensemble_catch(misses, views)  # validates; its mean is the mean of these flags
    episodes = len(next(iter(misses.values())))
    return [int(any(not misses[v][e] for v in views)) for e in range(episodes)]


def pressure_loss(catch_before, catch_after):
    # Proposal, Line 3 prediction C: "rotation halves the ensemble's loss and beats conservative aggregation."
    # Loss = catch without pressure minus catch under pressure (prereg/R2-L3-C-protocol.md section 6, step 4).
    # Negative when catch rises. The primary, loss(rotating) / loss(fixed), is section 6 step 5.
    for x in (catch_before, catch_after):
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not 0 <= x <= 1:
            raise ValueError("catch rates must be numbers in [0, 1]")
    return catch_before - catch_after


def loss_ratio(loss_rotating, loss_fixed):
    """Primary endpoint (protocol section 6 step 5): loss(rotating) / loss(fixed).

    shortcut: refuses only a fixed-arm loss at or below zero; the near-zero rule is OPEN (L3-O10)."""
    for x in (loss_rotating, loss_fixed):
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not -1 <= x <= 1:
            raise ValueError("losses must be numbers in [-1, 1]")
    if loss_fixed <= 0:
        raise ValueError("fixed-arm loss must be positive for a ratio (near-zero rule is OPEN, L3-O10)")
    return loss_rotating / loss_fixed


def _check_pool(pool, n):
    if not isinstance(pool, (list, tuple)) or not pool:
        raise ValueError("pool must be a nonempty list of tasks")
    for task in pool:
        if not isinstance(task, (list, tuple)) or len(task) < n:
            raise ValueError("every task needs at least n candidates")
        for cand in task[:n]:
            _bits(cand)


def compare_arms(pool, calibration, k, n, seed):
    """Scripted toy comparison; returns {"selected", "before", "static", "rotating", "conservative"} losses.

    selected = monsel.select(calibration, k). Pressure is best-of-n per task over the first n candidates.
    Every arm is scored by the full selected ensemble; arms differ only in what the selector sees:
    static: all selected views; rotating: all but monsel.hidden_view(selected, seed + task index);
    conservative: all selected views, but it only knows flagged/unflagged (conservative_catch) and takes
    the first unflagged candidate, else candidate 0. Before-pressure catch averages all n candidates.
    """
    _int(seed, "seed", -2**63, 2**63)
    _int(n, "n", 1, 10**9)
    _check_pool(pool, n)
    selected = monsel.select(calibration, k)
    for task in pool:
        for cand in task[:n]:
            monsel.ensemble_catch({v: [m] for v, m in cand.items()}, selected)

    def catch(episodes):
        return monsel.ensemble_catch({v: [e[v] for e in episodes] for v in selected}, selected)

    before = catch([c for task in pool for c in task[:n]])
    picks = {"static": [], "rotating": [], "conservative": []}
    for t, task in enumerate(pool):
        cands, rows = list(range(n)), list(task[:n])
        picks["static"].append(rows[best_of_n(cands, rows, selected, n)])
        seen = visible_views(selected, True, seed + t)
        picks["rotating"].append(rows[best_of_n(cands, rows, seen, n)])
        flags = [conservative_catch({v: [r[v]] for v in selected}, selected)[0] for r in rows]
        picks["conservative"].append(rows[flags.index(0) if 0 in flags else 0])
    out = {arm: pressure_loss(before, catch(p)) for arm, p in picks.items()}
    return {"selected": selected, "before": before, **out}
