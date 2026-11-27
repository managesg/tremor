"""Generate four- and eight-worker development allocations for L5."""

from tremor.trapbench import alloc


def generate(seed, team_size, *, split="train"):
    """Share the first six tasks across sizes and keep two unassigned tasks."""
    if type(seed) is not int or seed < 0:
        raise ValueError("seed must be a nonnegative integer")
    if type(team_size) is not int or team_size not in (4, 8):
        raise ValueError("L5 development teams must have four or eight workers")
    if type(split) is not str or split not in alloc.RANGES:
        raise ValueError("unknown allocation split")

    task_count = team_size + 2
    source = alloc.gen(2 * seed, split)
    tasks = list(source["tasks"])
    if len(tasks) < task_count:
        tasks += alloc.gen(2 * seed + 1, split)["tasks"]
    tasks = [
        {**task, "id": f"l5-{split}-{seed}-t{index}"}
        for index, task in enumerate(tasks[:task_count])
    ]
    return {**source, "seed": seed, "n_agents": team_size, "tasks": tasks}
