"""Quarantine with verification targeted by measured R (Line 2 technique; PROPOSAL-RESIDENCY-V3.md,
"Technique: quarantine with verification targeted by measured R").

(1) Provenance on every note. (2) New notes are readable but cannot be relayed or promoted until
verified by a scripted re-check or supported by an independent source; support that traces back to the
note itself does not count (a cycle check on the provenance graph). (3) The verification budget goes
first to the notes with the highest measured R.

Reading: notes are dicts with "id" and "parents" (provenance), as in readouts.reproduction_number.
Reading: support is a caller mapping note id -> ids of notes offered as corroboration; a supporter counts
only if it is a different note and the quarantined note is not among the supporter's ancestors.
Reading: a note's measured R is readouts.reproduction_number with that note as the only planted root;
ties are broken by note id.
"""
from murmuration.readouts import reproduction_number


def _index(notes):
    byid = {}
    for n in notes:
        if not isinstance(n, dict) or "id" not in n or not isinstance(n.get("parents"), (list, tuple)):
            raise ValueError("each note needs an 'id' and a 'parents' list")
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
    support = support or {}
    out = set()
    for nid in byid:
        if nid in verified:
            out.add(nid)
            continue
        for s in support.get(nid, ()):
            if s in byid and s != nid and nid not in ancestors(notes, s):
                out.add(nid)
                break
    return out


def verification_order(notes, verified, support=None):
    """Quarantined note ids, highest measured R first."""
    held = set(_index(notes)) - releasable(notes, verified, support)
    return sorted(held, key=lambda nid: (-reproduction_number(notes, [nid])[0], nid))
