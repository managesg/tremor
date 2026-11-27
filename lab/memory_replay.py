"""Three-night scripted control for the L4 memory replay instrument."""

import json

from tremor import night

DAY_NOTES = (
    (("pH", "pH was seven", "pH was seven"),),
    (("flow", "flow was steady", "flow was steady"),),
    (("level", "level was three", "level was three"),),
)
PLANTED_NOTE = ("flag", "valve was open", "valve was shut")


def run(*, planted, verify):
    """Replay synthetic observations, keeping each day's input and output store."""
    store, records, source_log = [], [], {}
    for day, notes in enumerate(DAY_NOTES, start=1):
        if day == 1 and planted:
            notes = (*notes, PLANTED_NOTE)
        for note_id, statement, source_text in notes:
            source_id = f"day-{day}:{note_id}"
            source_log[source_id] = source_text
            store = night.add_note(store, note_id, statement, "scripted-worker", day, (source_id,))

        def matches_source(note):
            return len(note["sources"]) == 1 and source_log.get(note["sources"][0]) == note["text"]

        before = store
        checks = []

        def check(note):
            matches = matches_source(note)
            checks.append({"note_id": note["id"], "sources": note["sources"], "matched": matches})
            return matches

        result = (night.consolidate(before, 1, day, verifier=check) if verify
                  else night.placebo(before, day))
        store = result.pop("store")
        discrepancies = [note["id"] for note in store if not matches_source(note)]
        records.append({
            "day": day,
            "input": before,
            "output": store,
            "verification": checks,
            "unverified_notes": discrepancies,
            **result,
        })
    return {"planted": planted, "verified_replay": verify, "source_log": source_log, "nights": records}


def compare():
    return {"instrument_validation": True,
            "runs": [run(planted=planted, verify=verify)
                     for planted in (False, True) for verify in (False, True)]}


if __name__ == "__main__":
    print(json.dumps(compare(), sort_keys=True, indent=2))
