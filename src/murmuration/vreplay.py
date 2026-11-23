"""Verified replay with adaptive strength (Line 4 technique; PROPOSAL-RESIDENCY-V3.md, "Technique:
verified replay with adaptive strength").

(1) Each stored claim is re-checked against the environment by a script before it is kept.
(2) Retained raw episodes are replayed with new ones so that old facts are not overwritten.
(3) A controller reads recovery time and R each night and lowers consolidation strength when they rise.
(4) Notes are retained by measured use, not by age.

Reading: the re-check is a caller-supplied script `check(claim) -> bool`; anything but True drops the
claim, including a check that raises (an unverifiable claim is not kept).
Reading: strength is a rung index on the measured consolidation ladder, 0 the weakest; the controller
lowers it by one rung when recovery time or R rose since last night and never raises it (the proposal
only states lowering). A missing measurement (None) leaves the rung unchanged; readings must otherwise
be finite numbers.
Reading: retention keeps the `capacity` most-used notes, ties broken by note id; a note with no recorded
use has 0 uses; age is never read.
"""
import math


def _seq(x, name):
    if isinstance(x, (str, bytes, dict)) or not isinstance(x, (list, tuple)):
        raise ValueError(f"{name} must be a list or tuple")
    return list(x)


def _reading(x):
    if x is None:
        return None
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        raise ValueError("readings must be finite numbers or None")
    return x


def gate(claims, check):
    """Claims that pass the scripted re-check."""
    if not callable(check):
        raise ValueError("check must be callable")
    kept = []
    for c in _seq(claims, "claims"):
        try:
            ok = check(c) is True
        except Exception:  # a crashing re-check verifies nothing
            ok = False
        if ok:
            kept.append(c)
    return kept


def replay_batch(retained, new):
    """Training batch for tonight: every retained raw episode plus the new ones, old first."""
    return _seq(retained, "retained") + _seq(new, "new")


def next_strength(rung, last, now):
    """Tonight's rung from last night's and tonight's (recovery_time, R) readings."""
    if isinstance(rung, bool) or not isinstance(rung, int) or rung < 0:
        raise ValueError("rung must be a non-negative integer")
    last, now = _seq(last, "last"), _seq(now, "now")
    if len(last) != 2 or len(now) != 2:
        raise ValueError("readings must be (recovery_time, R) pairs")
    last, now = [_reading(x) for x in last], [_reading(x) for x in now]
    rose = any(a is not None and b is not None and b > a for a, b in zip(last, now))
    return max(rung - 1, 0) if rose else rung


def retain(note_ids, uses, capacity):
    """The `capacity` note ids with the most measured uses."""
    if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity < 0:
        raise ValueError("capacity must be a non-negative integer")
    note_ids = _seq(note_ids, "note_ids")
    if not isinstance(uses, dict):
        raise ValueError("uses must be a dict of note id -> use count")
    if len(set(note_ids)) != len(note_ids):
        raise ValueError("note ids must not repeat")
    if any(not isinstance(n, str) for n in note_ids):
        raise ValueError("note ids must be strings")
    for n in note_ids:
        u = uses.get(n, 0)
        if isinstance(u, bool) or not isinstance(u, int) or u < 0:
            raise ValueError(f"use count for {n!r} must be a non-negative integer")
    return sorted(note_ids, key=lambda n: (-uses.get(n, 0), n))[:capacity]
