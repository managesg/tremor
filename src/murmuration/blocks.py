"""Block-and-summarise, sized by coupling (Line 7 technique; PROPOSAL-RESIDENCY-V3.md, "Technique:
block-and-summarise, sized by coupling").

Group tasks by measured co-change coupling; assign a block of agents per group; each block publishes
one summary line upward; the level above treats a block as one agent.

Reading: coupling is a caller mapping {(task_a, task_b): weight}, e.g. from coupling.coupling; groups
are connected components over pairs with weight >= `threshold`, a required parameter with no default.
Reading: "sized by coupling" is read as sized by the number of coupled tasks: agents are split across
groups in proportion to task count by largest remainder (ties by group order); a group left with none
then takes one agent from the most over-served block. Fewer agents than groups is an error.
Reading: the summariser is caller-supplied; a block's summary must be a single line.
"""
import math


def _ids(x, name):
    if isinstance(x, (str, bytes, dict)) or not isinstance(x, (list, tuple, set, frozenset)):
        raise ValueError(f"{name} must be a list, tuple or set of task ids, not a string")
    if any(not isinstance(t, str) for t in x):
        raise ValueError(f"{name} must hold string task ids")
    if len(set(x)) != len(x):
        raise ValueError(f"{name} must not repeat a task id")
    return set(x)


def groups(tasks, coupling, threshold):
    """Tasks partitioned into coupled groups, each sorted, groups ordered by their first task."""
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or not math.isfinite(threshold):
        raise ValueError("threshold must be a finite number")
    tasks = _ids(tasks, "tasks")
    if not isinstance(coupling, dict):
        raise ValueError("coupling must be a dict of (task_a, task_b) -> weight")
    for pair in coupling:
        if not isinstance(pair, tuple) or len(pair) != 2:
            raise ValueError(f"coupling key {pair!r} must be a (task_a, task_b) tuple")
    tasks = sorted(tasks)
    parent = {t: t for t in tasks}

    def find(t):
        while parent[t] != t:
            parent[t] = parent[parent[t]]
            t = parent[t]
        return t

    for (a, b), w in coupling.items():
        if a not in parent or b not in parent:
            raise ValueError(f"coupling pair {(a, b)!r} names an unknown task")
        if isinstance(w, bool) or not isinstance(w, (int, float)) or not math.isfinite(w):
            raise ValueError(f"coupling weight for {(a, b)!r} must be a finite number")
        if w >= threshold:
            parent[find(a)] = find(b)
    out = {}
    for t in tasks:
        out.setdefault(find(t), []).append(t)
    return sorted(out.values())


def assign(agents, task_groups):
    """Agent blocks, one per group, sized in proportion to the group's task count."""
    if isinstance(task_groups, (str, bytes, dict)) or not isinstance(task_groups, (list, tuple)):
        raise ValueError("task_groups must be a list of task-id lists")
    agents, n = list(agents), len(task_groups)
    if n == 0:
        return []
    for g in task_groups:
        _ids(g, "each group")
    if any(len(g) == 0 for g in task_groups):
        raise ValueError("every group needs at least one task")
    if len(agents) < n:
        raise ValueError("need at least one agent per group")
    total = sum(len(g) for g in task_groups)
    exact = [len(agents) * len(g) / total for g in task_groups]
    sizes = [int(x) for x in exact]  # largest-remainder (Hamilton) apportionment
    by_remainder = sorted(range(n), key=lambda i: (-(exact[i] - int(exact[i])), i))
    for i in by_remainder[:len(agents) - sum(sizes)]:  # fewer than n seats left, largest fraction first
        sizes[i] += 1
    for j in range(n):  # then the minimum of one: move a seat from the most over-served block
        if sizes[j] == 0:
            i = max((i for i in range(n) if sizes[i] > 1), key=lambda i: (sizes[i] - exact[i], -i))
            sizes[i], sizes[j] = sizes[i] - 1, 1
    blocks, at = [], 0
    for s in sizes:
        blocks.append(agents[at:at + s])
        at += s
    return blocks


def upward(block_lines, summarise):
    """One summary line per block; the level above sees each block as one agent."""
    out = []
    for i, lines in enumerate(block_lines):
        line = summarise(lines)
        if not isinstance(line, str) or (line and line.splitlines() != [line]):  # any line boundary
            raise ValueError(f"block {i} summary must be a single line of text")
        out.append({"agent": f"block-{i}", "summary": line})
    return out
