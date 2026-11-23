"""Evaporating claims (Line 5 technique; PROPOSAL-RESIDENCY-V3.md, "Technique: evaporating claims").

A claim is a mark whose strength decays each round unless a work event renews it. Agents see mark
strengths and take the weakest-marked open task, with a per-agent tie-break. The mechanism is the
ant-robot covering rule plus a lease (Wagner, Lindenbaum, Bruckstein 1999; Gray and Cheriton 1989).

Reading: decay is multiplicative by a caller-supplied `retain` factor in (0, 1); the proposal fixes
no rate, so it has no default.
Reading: a renewing work event restores the mark to full strength 1.0; an unmarked task has strength 0.
Reading: the per-agent tie-break picks, among equally weak open tasks sorted by id, index
`agent_rank mod count`, so tied agents spread instead of colliding.
"""


def _tasks(x, name):
    if isinstance(x, (str, bytes, dict)) or not isinstance(x, (list, tuple, set, frozenset)):
        raise ValueError(f"{name} must be a list, tuple or set of task ids, not a string")
    if any(not isinstance(t, str) for t in x):
        raise ValueError(f"{name} must hold string task ids")
    return set(x)


def _check_strength(task, s):
    if isinstance(s, bool) or not isinstance(s, (int, float)) or not 0 <= s <= 1:
        raise ValueError(f"mark strength for {task!r} must be a number in [0, 1]")


def evaporate(marks, renewed, retain):
    """One round: tasks in `renewed` go to 1.0, every other mark is multiplied by `retain`."""
    if isinstance(retain, bool) or not isinstance(retain, (int, float)) or not 0 < retain < 1:
        raise ValueError("retain must be a number strictly between 0 and 1")
    if not isinstance(marks, dict) or any(not isinstance(t, str) for t in marks):
        raise ValueError("marks must be a dict of string task id -> strength")
    renewed = _tasks(renewed, "renewed")
    out = {}
    for task, s in marks.items():
        _check_strength(task, s)
        out[task] = 1.0 if task in renewed else s * retain
    for task in renewed - out.keys():
        out[task] = 1.0
    return out


def choose(marks, open_tasks, agent_rank):
    """The weakest-marked open task for this agent, or None when no task is open."""
    if isinstance(agent_rank, bool) or not isinstance(agent_rank, int) or agent_rank < 0:
        raise ValueError("agent_rank must be a non-negative integer")
    if not isinstance(marks, dict) or any(not isinstance(t, str) for t in marks):
        raise ValueError("marks must be a dict of string task id -> strength")
    tasks = _tasks(open_tasks, "open_tasks")
    if any(not isinstance(t, str) for t in tasks):
        raise ValueError("task ids must be strings")
    tasks = sorted(tasks)
    if not tasks:
        return None
    for task in tasks:
        if task in marks:
            _check_strength(task, marks[task])
    weakest = min(marks.get(t, 0) for t in tasks)
    tied = [t for t in tasks if marks.get(t, 0) == weakest]
    return tied[agent_rank % len(tied)]
