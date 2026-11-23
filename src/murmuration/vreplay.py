"""Verified replay with adaptive strength (Line 4 technique; PROPOSAL-RESIDENCY-V3.md, "Technique:
verified replay with adaptive strength").

(1) Each stored claim is re-checked against the environment by a script before it is kept.
(2) Retained raw episodes are replayed with new ones so that old facts are not overwritten.
(3) A controller reads recovery time and R each night and lowers consolidation strength when they rise.
(4) Notes are retained by measured use, not by age.

Reading: the re-check is a caller-supplied script `check(claim) -> bool`; anything but True drops it.
Reading: strength is a rung index on the measured consolidation ladder, 0 the weakest; the controller
lowers it by one rung when recovery time or R rose since last night and never raises it (the proposal
only states lowering). A missing measurement (None) leaves the rung unchanged.
Reading: retention keeps the `capacity` most-used notes, ties broken by note id; age is never read.
"""


def gate(claims, check):
    """Claims that pass the scripted re-check."""
    if not callable(check):
        raise ValueError("check must be callable")
    return [c for c in claims if check(c) is True]


def replay_batch(retained, new):
    """Training batch for tonight: every retained raw episode plus the new ones, old first."""
    return list(retained) + list(new)


def next_strength(rung, last, now):
    """Tonight's rung from last night's and tonight's (recovery_time, R) readings."""
    if isinstance(rung, bool) or not isinstance(rung, int) or rung < 0:
        raise ValueError("rung must be a non-negative integer")
    rose = any(a is not None and b is not None and b > a for a, b in zip(last, now))
    return max(rung - 1, 0) if rose else rung


def retain(note_ids, uses, capacity):
    """The `capacity` note ids with the most measured uses."""
    if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity < 0:
        raise ValueError("capacity must be a non-negative integer")
    for n in note_ids:
        u = uses.get(n, 0)
        if isinstance(u, bool) or not isinstance(u, int) or u < 0:
            raise ValueError(f"use count for {n!r} must be a non-negative integer")
    return sorted(note_ids, key=lambda n: (-uses.get(n, 0), n))[:capacity]
