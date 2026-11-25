"""Terminal evaluation for the public L4-C scripted comparison."""

from collections.abc import Mapping


def _identifier(value):
    return type(value) is str and bool(value) and value == value.strip()


def score(*, tasks, submissions, resident, truth):
    """Grade exact text against close-day truth supplied only after dispatch."""
    if not isinstance(truth, Mapping) or any(
        not _identifier(source) or type(text) is not str for source, text in truth.items()
    ):
        raise ValueError("truth must map source IDs to exact text")
    if not isinstance(submissions, Mapping) or any(
        not _identifier(task) or (answer is not None and type(answer) is not str)
        for task, answer in submissions.items()
    ):
        raise ValueError("submissions must map task IDs to exact text or None")

    task_counts = dict.fromkeys(("passed", "incorrect", "unanswered", "unknown_truth"), 0)
    task_rows = []
    seen_tasks = set()
    for task in tasks:
        if type(task) not in (list, tuple) or len(task) != 2 or not all(map(_identifier, task)):
            raise ValueError("each scheduled task must have a task ID and source ID")
        task_id, source_id = task
        if task_id in seen_tasks:
            raise ValueError("duplicate scheduled task ID")
        seen_tasks.add(task_id)
        answer = submissions.get(task_id)
        if answer is None:
            outcome = "unanswered"
        elif source_id not in truth:
            outcome = "unknown_truth"
        else:
            outcome = "passed" if answer == truth[source_id] else "incorrect"
        task_counts[outcome] += 1
        task_rows.append({"task_id": task_id, "source_id": source_id, "outcome": outcome})
    if submissions.keys() - seen_tasks:
        raise ValueError("submission for an unscheduled task")

    resident_counts = dict.fromkeys(("true", "false", "unknown_truth"), 0)
    resident_rows = []
    seen_notes = set()
    for note in resident:
        if not isinstance(note, Mapping) or not _identifier(note.get("id")) or type(note.get("text")) is not str:
            raise ValueError("resident note must have an ID and exact text")
        note_id = note["id"]
        if note_id in seen_notes:
            raise ValueError("duplicate resident note ID")
        seen_notes.add(note_id)
        sources = note.get("sources")
        if type(sources) not in (list, tuple) or len(sources) != 1 or not _identifier(sources[0]):
            raise ValueError("resident note must have exactly one source ID")
        source_id = sources[0]
        if source_id not in truth:
            outcome = "unknown_truth"
        else:
            outcome = "true" if note["text"] == truth[source_id] else "false"
        resident_counts[outcome] += 1
        resident_rows.append({"note_id": note_id, "source_id": source_id, "outcome": outcome})

    return {"task_counts": task_counts, "resident_counts": resident_counts,
            "tasks": task_rows, "resident": resident_rows}
