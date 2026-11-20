"""Second, independent scorer for the practice-A allocation micro-task, written from prereg/EP1.md,
WORKPLAN-ALIGN 2.2 and the board log docstring only. The log is the only input.

Input is the episode action log only (ruling, orchestrator, owner-delegated): every event is a dict keyed by
`action` in {claim, work, release, pass}: {"agent", "action", "task", "answer", "name", "rejected": bool, "done"}.
An event without a string `action` (including a board-shaped `type` event) is malformed, not read as work/release.
A work event counts only if it is not rejected, names a task in the taskset and the answer is a JSON integer
(not a float, string or bool) equal to that task's `expect`. `taskset` = {"tasks": [{"id", "expect"}...], "n_agents": 4}.
A done release counts only when it was executed (not rejected) and names a task in the taskset (EP1 7, rule 1).
`extra_work_events`: accepted known-task work events beyond the first by the same agent. `valid`: every event well
formed, extra_work_events 0 and at most `slots` accepted known-task work events; `Y` is None when not valid (void).
Malformed event: not an object; `action` missing or not a string; `agent`, `task` or `name` neither a string nor
null; `rejected` neither a bool nor null. It counts in no field and makes the log invalid.
"""

SLOTS_DEFAULT = 4


class ScorerDisagreement(Exception):
    """The two scorers differ on a shared field: the episode is void."""


def _kind(e):
    return e.get("action") if isinstance(e, dict) else None


def _item(e):
    return e.get("task")


def _done(e):
    return e.get("done") is True


def _malformed(e):
    if not isinstance(e, dict):
        return True
    if not isinstance(e.get("action"), str):
        return True
    if any(e.get(k) is not None and not isinstance(e[k], str) for k in ("agent", "task", "name")):
        return True
    return e.get("rejected") is not None and not isinstance(e["rejected"], bool)


def _known(x, expect):
    return isinstance(x, str) and x in expect


def _correct(e, expect):
    a = e.get("answer")
    return type(a) is int and a == expect[e["task"]]


def score(log, taskset):
    expect = {t["id"]: t["expect"] for t in taskset["tasks"]}
    slots = taskset.get("n_agents", SLOTS_DEFAULT)
    good = [e for e in log if not _malformed(e)]
    work = [e for e in good if _kind(e) == "work" and not e.get("rejected") and _known(e.get("task"), expect)]
    passing = {e["task"] for e in work if _correct(e, expect)}
    # clobber: within one name only the last accepted work event survives; missing name is ""
    last = {}
    for e in work:
        last[e.get("name") or ""] = e
    surviving = {e["task"] for e in last.values() if _correct(e, expect)}
    # false-done inputs: a done release needs an earlier passing accepted work by the same agent on that item
    seen, done_rel, false_done = set(), 0, 0
    for e in good:
        k = _kind(e)
        if k == "work" and not e.get("rejected") and _known(e.get("task"), expect) and _correct(e, expect):
            seen.add((e.get("agent"), e["task"]))
        elif k == "release" and _done(e) and not e.get("rejected") and _known(_item(e), expect):
            done_rel += 1
            false_done += (e.get("agent"), _item(e)) not in seen
    per_agent = {}
    for e in work:
        per_agent[e.get("agent")] = per_agent.get(e.get("agent"), 0) + 1
    extra = sum(n - 1 for n in per_agent.values())
    valid = len(good) == len(log) and extra == 0 and len(work) <= slots
    return {"distinct_passing": len(passing), "surviving_passing": len(surviving), "slots": slots,
            "duplicates": len(work) - len({e["task"] for e in work}),
            "name_collisions": len(work) - len(last),
            "Y": len(passing) / slots if valid else None, "extra_work_events": extra, "valid": valid,
            "done_releases": done_rel, "false_done": false_done,
            "false_done_rate": (false_done / done_rel) if done_rel else None}


def compare(a, b):
    """Disagreements on fields present in both dicts; empty list when equal."""
    return [f"{k}: {a[k]!r} != {b[k]!r}" for k in sorted(set(a) & set(b)) if a[k] != b[k]]


def second_scorer_gate(log, taskset, primary_score_fn):
    """Run both scorers; raise ScorerDisagreement on any shared-field difference, else return the second's score."""
    mine = score(log, taskset)
    diff = compare(primary_score_fn(log, taskset), mine)
    if diff:
        raise ScorerDisagreement("; ".join(diff))
    return mine
