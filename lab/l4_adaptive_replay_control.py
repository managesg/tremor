"""Source-gated execution for a scripted L4 replay night."""

from copy import deepcopy

from tremor import night


def replay_day(store, *, day, source_prefix, strength, seed=0, rewrite=None):
    """Check original notes and proposed rewrites against only the supplied source prefix.

    Input words count every submitted note. Consolidation reads count the notes that
    pass the source gate and enter the rewrite pass.
    """
    notes = deepcopy(list(store))
    sources = dict(source_prefix)
    input_words = night.tokens(notes)
    source_checks, rewrite_checks = [], []
    admitted, rejected = [], []
    if len({note["id"] for note in notes}) != len(notes):
        raise ValueError("replay note IDs must be unique")

    def check(note, log, original_references=None):
        references, text = note.get("sources"), note.get("text")
        source_words = None
        if type(references) not in (list, tuple) or len(references) != 1 or type(references[0]) is not str:
            disposition = "invalid_reference"
        elif original_references is not None and references != original_references:
            disposition = "source_rebound"
        else:
            source = sources.get(references[0])
            if type(source) is not str:
                disposition = "missing_source"
            else:
                source_words = len(source.split())
                disposition = "matched" if type(text) is str and source == text else "source_mismatch"
        matched = disposition == "matched"
        log.append({"note_id": note["id"], "sources": deepcopy(references), "matched": matched,
                    "disposition": disposition, "source_words": source_words})
        return matched

    for note in notes:
        if check(note, source_checks):
            admitted.append(note)
        else:
            rejected.append(note["id"])
    original_sources = {note["id"]: note["sources"] for note in admitted}

    def propose(note, rng):
        # A rewrite cannot mutate the admitted original, including its nested provenance.
        return deepcopy(rewrite(deepcopy(note), rng))

    def verify_rewrite(note):
        return check(note, rewrite_checks, original_sources[note["parents"][0]])

    result = night.consolidate(admitted, strength, day, verifier=verify_rewrite,
                               mode="gated", rewrite=propose if rewrite is not None else None, seed=seed)
    return {**result, "dropped": rejected + result["dropped"], "source_checks": source_checks,
            "rewrite_checks": rewrite_checks, "input_words": input_words}
