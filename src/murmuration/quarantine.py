"""Quarantine with verification targeted by measured R (Line 2 technique; PROPOSAL-RESIDENCY-V3.md,
"Technique: quarantine with verification targeted by measured R").

(1) Provenance on every note. (2) New notes are readable but cannot be relayed or promoted until
verified by a scripted re-check or supported by an independent source; support that traces back to the
note itself does not count (a cycle check on the provenance graph). (3) The verification budget goes
first to the notes with the highest measured R.

Reading: notes are dicts with "id" and "parents" (provenance), as in readouts.reproduction_number.
Reading: support is a caller mapping note id -> ids of notes offered as corroboration; a supporter counts
only if it shares no provenance with the note: the two lineages (each note plus all its ancestors) are
disjoint. This covers the cycle check (support descending from the note), a note's own source, and a
sibling derived from the same source. A supporter must itself be verified: two unverified notes
cannot release each other (planted copies of one wrong note need not be linked by provenance).
Reading: a note's measured R is readouts.reproduction_number with that note as the only planted root;
ties are broken by note id.
"""
from collections.abc import Mapping

from murmuration.readouts import reproduction_number


def _index(notes):
    if not isinstance(notes, (list, tuple)):  # notes are read more than once: a one-shot iterator would empty
        raise ValueError("notes must be a list or tuple of note dicts")
    byid = {}
    for n in notes:
        if not isinstance(n, dict) or "id" not in n or not isinstance(n.get("parents"), (list, tuple)):
            raise ValueError("each note needs an 'id' and a 'parents' list")
        if not isinstance(n["id"], str):
            raise ValueError(f"note id {n['id']!r} must be a string")
        if any(not isinstance(p, str) for p in n["parents"]):
            raise ValueError(f"parent ids of {n['id']!r} must be strings")
        if n["id"] in byid:
            raise ValueError(f"duplicate note id {n['id']!r}")
        byid[n["id"]] = n
    return byid


def ancestors(notes, note_id):
    byid = _index(notes)
    seen, todo = set(), list(byid.get(note_id, {"parents": []})["parents"])
    while todo:
        p = todo.pop()
        if p not in seen:
            seen.add(p)
            todo.extend(byid.get(p, {"parents": []})["parents"])
    return seen


def releasable(notes, verified, support=None):
    """Ids that may be relayed or promoted: verified, or with at least one independent supporter."""
    byid = _index(notes)
    if isinstance(verified, (str, bytes)) or not isinstance(verified, (set, frozenset, list, tuple)):
        raise ValueError("verified must be a set of note ids")
    if any(not isinstance(v, str) for v in verified):
        raise ValueError("verified must hold string note ids")
    verified = set(verified)
    support = {} if support is None else support
    if not isinstance(support, Mapping):
        raise ValueError("support must map note ids to lists of note ids")
    out = set()
    for nid in byid:
        if nid in verified:
            out.add(nid)
            continue
        own = ancestors(notes, nid) | {nid}
        offered = support.get(nid, ())
        if not isinstance(offered, (list, tuple, set, frozenset)):
            raise ValueError(f"support for {nid!r} must be a list of note ids")
        if any(not isinstance(s, str) for s in offered):
            raise ValueError(f"support for {nid!r} must hold string note ids")
        for s in offered:
            if s in byid and s in verified and own.isdisjoint(ancestors(notes, s) | {s}):
                out.add(nid)
                break
    return out


def verification_order(notes, verified, support=None):
    """Quarantined note ids, highest measured R first."""
    held = set(_index(notes)) - releasable(notes, verified, support)
    return sorted(held, key=lambda nid: (-reproduction_number(notes, [nid])[0], nid))
