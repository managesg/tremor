"""Rotating hidden view on an ensemble chosen from the joint miss table (Line 3 technique;
PROPOSAL-RESIDENCY-V3.md, "Technique: a rotating hidden view, on an ensemble chosen from the joint miss
table").

From a calibration set, estimate each view's catch rate and the joint misses; choose the k views that
maximise predicted ensemble catch (greedy); and each run hide one randomly chosen view from whatever is
selecting outputs.

Reading: misses[view] is a list of 0/1 over the same calibration failure episodes, 1 meaning missed.
Reading: the ensemble catches an episode when at least one selected view catches it, so predicted
ensemble catch is the share of episodes not missed by every selected view (the joint miss table).
Reading: greedy ties are broken by view name; the hidden view uses an explicit seed.
"""
import random


def _check(misses):
    if not misses:
        raise ValueError("at least one view is required")
    lengths = {len(row) for row in misses.values()}
    if len(lengths) != 1 or 0 in lengths:
        raise ValueError("every view needs the same nonzero number of calibration episodes")
    for row in misses.values():
        if any(type(x) is not int or x not in (0, 1) for x in row):
            raise ValueError("misses must be 0 or 1")
    return lengths.pop()


def ensemble_catch(misses, views):
    """Share of calibration episodes caught by at least one of `views`."""
    episodes = _check(misses)
    unknown = set(views) - set(misses)
    if unknown:
        raise ValueError(f"unknown views: {sorted(unknown)}")
    if not views:
        return 0.0
    all_missed = sum(all(misses[v][e] for v in views) for e in range(episodes))
    return 1 - all_missed / episodes


def select(misses, k):
    """Greedy k-view ensemble maximising predicted ensemble catch."""
    _check(misses)
    if isinstance(k, bool) or not isinstance(k, int) or not 1 <= k <= len(misses):
        raise ValueError("k must be an integer between 1 and the number of views")
    chosen = []
    for _ in range(k):
        best, best_score = None, -1.0
        for v in sorted(set(misses) - set(chosen)):  # first strictly better in name order wins ties
            score = ensemble_catch(misses, chosen + [v])
            if score > best_score:
                best, best_score = v, score
        chosen.append(best)
    return chosen


def hidden_view(selected, seed):
    """The one view hidden from the output selector for this run."""
    if not selected:
        raise ValueError("no selected views to hide")
    return random.Random(seed).choice(sorted(selected))
