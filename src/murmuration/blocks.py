"""Block-and-summarise, sized by coupling (Line 7 technique; PROPOSAL-RESIDENCY-V3.md, "Technique:
block-and-summarise, sized by coupling").

Group tasks by measured co-change coupling; assign a block of agents per group; each block publishes
one summary line upward; the level above treats a block as one agent.

Reading: coupling is a caller mapping {(task_a, task_b): weight}, e.g. from coupling.coupling; groups
are connected components over pairs with weight >= `threshold`, a required parameter with no default.
Reading: agents are split across groups in proportion to task count (largest remainder, ties by group
order), at least one agent per group; fewer agents than groups is an error.
Reading: the summariser is caller-supplied; a block's summary must be a single line.
"""


def groups(tasks, coupling, threshold):
    """Tasks partitioned into coupled groups, each sorted, groups ordered by their first task."""
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)):
        raise ValueError("threshold must be a number")
    tasks = sorted(set(tasks))
    parent = {t: t for t in tasks}

    def find(t):
        while parent[t] != t:
            parent[t] = parent[parent[t]]
            t = parent[t]
        return t

    for (a, b), w in coupling.items():
        if a not in parent or b not in parent:
            raise ValueError(f"coupling pair {(a, b)!r} names an unknown task")
        if w >= threshold:
            parent[find(a)] = find(b)
    out = {}
    for t in tasks:
        out.setdefault(find(t), []).append(t)
    return sorted(out.values())


def assign(agents, task_groups):
    """Agent blocks, one per group, sized in proportion to the group's task count."""
    agents, n = list(agents), len(task_groups)
    if n == 0:
        return []
    if len(agents) < n:
        raise ValueError("need at least one agent per group")
    total = sum(len(g) for g in task_groups)
    spare = len(agents) - n
    exact = [spare * len(g) / total for g in task_groups]
    sizes = [1 + int(x) for x in exact]
    left = len(agents) - sum(sizes)
    for i in sorted(range(n), key=lambda i: (-(exact[i] - int(exact[i])), i))[:left]:
        sizes[i] += 1
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
        if not isinstance(line, str) or "\n" in line:
            raise ValueError(f"block {i} summary must be a single line of text")
        out.append({"agent": f"block-{i}", "summary": line})
    return out
