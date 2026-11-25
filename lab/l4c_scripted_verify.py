"""Independent semantic checks for the public L4-C execution receipt."""

from dataclasses import asdict
import hashlib
import json


_ARMS = ("replay", "write_only", "search")


def plan_pin(days, *, cap):
    """Bind the full schedule, including unused options, without scoring labels."""
    envelope = {"days": [asdict(day) for day in days], "per_night_operation_cap": cap}
    canonical = json.dumps(envelope, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(canonical).hexdigest()


def _same(actual, expected):
    if type(actual) is not type(expected):
        return False
    if type(expected) is dict:
        return actual.keys() == expected.keys() and all(
            _same(actual[key], value) for key, value in expected.items()
        )
    if type(expected) in (list, tuple):
        return len(actual) == len(expected) and all(
            _same(observed, planned) for observed, planned in zip(actual, expected)
        )
    return actual == expected


def _memory(arm, day, arrivals, prior, active, versions, cap):
    fresh = [
        {"id": note_id, "text": text, "author": "scripted-worker", "episode": day,
         "sources": [source], "parents": [], "authored_source_version": versions.get(source)}
        for note_id, text, source in arrivals
    ]
    replay = arm == "replay"
    candidates = [*prior, *fresh] if replay else fresh
    if len(candidates) * (2 if replay else 1) > cap:
        return prior, "budget_withheld", []
    if len({note["id"] for note in candidates}) != len(candidates):
        raise ValueError("duplicate candidate note identity")

    checks, accepted = [], []
    for note in candidates:
        source = note["sources"][0]
        if source not in active:
            disposition = "missing_source"
        elif active[source] == note["text"]:
            disposition = "matched"
            accepted.append(note)
        else:
            disposition = "source_mismatch"
        checks.append({"kind": "source_check", "subject": note["id"], "outcome": disposition})

    if replay:
        resident = []
        for note in accepted:
            rewrite_id = f"n{day}-{note['id']}"
            checks.append({"kind": "rewrite_check", "subject": rewrite_id, "outcome": "matched"})
            resident.append({**note, "id": rewrite_id, "parents": [note["id"]]})
    else:
        resident = [*prior, *accepted]
    return resident, "completed", checks


def _answers(arm, tasks, active, resident, status, operations, cap):
    submissions = dict.fromkeys(task.id for task in tasks)
    if status == "budget_withheld":
        return submissions
    if arm == "search":
        for task in tasks:
            for candidate in task.candidates:
                if len(operations) == cap:
                    break
                answer = active.get(candidate)
                operations.append({"kind": "search_read", "subject": f"{task.id}/{candidate}",
                                   "outcome": "missing" if answer is None else "returned"})
                if answer is not None:
                    submissions[task.id] = answer
                    break
        return submissions

    by_source = {note["sources"][0]: note["text"] for note in resident}
    for task in tasks[:cap - len(operations)]:
        answer = by_source.get(task.source)
        operations.append({"kind": "memory_lookup", "subject": task.id,
                           "outcome": "missing" if answer is None else "returned"})
        submissions[task.id] = answer
    return submissions


def verify(execution, days, *, cap):
    """Rebuild ordered operations and provenance against a separately supplied plan.

    This checks deterministic development receipts. It does not authenticate the
    plan or use evaluator truth.
    """
    days = tuple(days)
    if type(cap) is not int or cap < 0 or not days:
        raise ValueError("invalid scripted verification plan or cap")
    if type(execution) is not dict or execution.keys() != {"records", "raw_source_revisions", "plan_sha256"}:
        raise ValueError("unexpected scripted execution fields")
    if execution["plan_sha256"] != plan_pin(days, cap=cap):
        raise ValueError("execution receipt differs from the supplied plan pin")
    records, history = execution["records"], execution["raw_source_revisions"]
    if type(records) is not list or len(records) != len(days) * len(_ARMS):
        raise ValueError("execution records do not cover the planned arm schedule")
    if type(history) is not list or len(history) != len(days):
        raise ValueError("source revision history does not cover the planned days")

    active, versions = {}, {}
    stores = {arm: [] for arm in _ARMS}
    note_ids, task_ids = set(), set()
    for day, plan in enumerate(days, 1):
        received = history[day - 1]
        if (type(received) is not dict or received.keys() != {"day", "revisions"}
                or not _same(received["day"], day) or type(received["revisions"]) is not list):
            raise ValueError(f"source revision history differs on day {day}")
        revisions = received["revisions"]
        if len(revisions) != len(plan.revisions) or any(
            type(observed) not in (list, tuple) or not _same(tuple(observed), tuple(expected))
            for observed, expected in zip(revisions, plan.revisions)
        ):
            raise ValueError(f"source revision history differs on day {day}")

        revised = set()
        for source, version, text in plan.revisions:
            if (type(source) is not str or type(text) is not str or type(version) is not int
                    or source in revised or version != versions.get(source, 0) + 1):
                raise ValueError(f"invalid source version path on day {day}")
            active[source], versions[source] = text, version
            revised.add(source)

        for note_id, text, source in plan.arrivals:
            if any(type(field) is not str for field in (note_id, text, source)) or note_id in note_ids:
                raise ValueError(f"invalid note opportunity on day {day}")
            note_ids.add(note_id)
        tasks = tuple(plan.tasks)
        for task in tasks:
            if (type(task.id) is not str or type(task.source) is not str or task.id in task_ids
                    or type(task.candidates) not in (tuple, list)
                    or any(type(candidate) is not str for candidate in task.candidates)):
                raise ValueError(f"invalid task opportunity on day {day}")
            task_ids.add(task.id)

        for offset, arm in enumerate(_ARMS):
            if arm == "search":
                resident, status, operations = [], "search_without_memory", []
            else:
                resident, status, operations = _memory(arm, day, plan.arrivals, stores[arm], active, versions, cap)
            submissions = _answers(arm, tasks, active, resident, status, operations, cap)
            expected = {"day": day, "arm": arm, "operations": operations, "spent": len(operations),
                        "unused": cap - len(operations), "gate_status": status, "resident": resident,
                        "submissions": submissions}
            if not _same(records[(day - 1) * len(_ARMS) + offset], expected):
                raise ValueError(f"semantic execution mismatch on day {day}, arm {arm}")
            stores[arm] = resident
