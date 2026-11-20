"""EP-1 allocation micro-task: 6 open tasks, 4 agents, 4 work slots. score() reads only the log.

A log event is {"agent": str, "action": "claim"|"work", "task": id, "name": str,
"answer": int, "rejected": bool}. Only accepted "work" events can score; a rejected slot scores 0. Same name = same file/branch:
the last accepted writer in log order survives (surviving_passing). An answer passes only as a JSON integer
(30.0, "30" and true are not 30).

EP1 section 7 (option C): `extra_work_events` counts accepted work events on tasks in the set beyond the first
by the same agent. `valid` is true when every event is well formed, extra_work_events is 0 and there are at
most `slots` such work events; then Y = distinct_passing / slots, else Y is None (the episode is void, never
capped). Input is the episode action log only (ruling, orchestrator, owner-delegated): a malformed event (not
an object; `action` missing or not a string, so a board-shaped `type` event or board release is malformed too;
`agent`, `task` or `name` neither a string nor null; `rejected` neither a bool nor null) counts in no field
and makes the log invalid.
"""
import json
import random

N_TASKS, N_AGENTS = 6, 4
NAME_RULE = "{agent}-{task}"
RANGES = {"train": (10, 49), "heldout": (50, 99)}  # disjoint operand ranges, so disjoint checks


def gen(seed, split="train"):
    rnd = random.Random(f"alloc:{split}:{seed}")
    lo, hi = RANGES[split]
    tasks = []
    for i in range(N_TASKS):
        a, b = rnd.randint(lo, hi), rnd.randint(lo, hi)
        tasks.append({"id": f"{split[0]}{seed}t{i}", "check": f"sum {a} {b}", "expect": a + b})
    return {"split": split, "seed": seed, "n_agents": N_AGENTS, "name_rule": NAME_RULE, "tasks": tasks}


def dumps(taskset):
    return json.dumps(taskset, sort_keys=True)


def oracle_log(ts):
    return [{"agent": f"a{i}", "action": "work", "task": t["id"], "answer": t["expect"],
             "name": ts["name_rule"].format(agent=f"a{i}", task=t["id"])}
            for i, t in enumerate(ts["tasks"][:ts["n_agents"]])]


def floor_log(ts):
    t = ts["tasks"][0]
    return [{"agent": f"a{i}", "action": "work", "task": t["id"], "answer": t["expect"],
             "name": ts["name_rule"].format(agent=f"a{i}", task=t["id"])} for i in range(ts["n_agents"])]


def well_formed(e):
    return (isinstance(e, dict) and isinstance(e.get("action"), str)
            and all(e.get(k) is None or isinstance(e[k], str) for k in ("agent", "task", "name"))
            and (e.get("rejected") is None or isinstance(e["rejected"], bool)))


def score(log, ts):
    expect = {t["id"]: t["expect"] for t in ts["tasks"]}
    ok = [e for e in log if well_formed(e)]
    acc = [e for e in ok if e.get("action") == "work" and not e.get("rejected")]
    # EP1: an action on a task id outside the task set is a logged no-op; it changes no other field.
    work = [e for e in acc if e.get("task") in expect]
    unknown = len(acc) - len(work)

    def passes(e):  # EP1 rule 2: a JSON integer only; bool is an int subclass in Python, so it is excluded
        return type(e.get("answer")) is int and e["answer"] == expect[e["task"]]
    passing = {e["task"] for e in work if passes(e)}
    # clobber: per name only the last accepted work event in log order survives; a missing name is "".
    last = {}
    for e in work:
        last[e.get("name") or ""] = e
    surviving = {e["task"] for e in last.values() if passes(e)}
    extra = len(work) - len({e.get("agent") for e in work})
    valid = len(ok) == len(log) and extra == 0 and len(work) <= ts["n_agents"]
    # shortcut: a name that breaks the rule but is unique is not counted; upgrade if EP-1 needs it.
    return {"distinct_passing": len(passing), "surviving_passing": len(surviving), "slots": ts["n_agents"],
            "duplicates": len(work) - len({e["task"] for e in work}), "name_collisions": len(work) - len(last),
            "Y": len(passing) / ts["n_agents"] if valid else None, "unknown_task_events": unknown,
            "extra_work_events": extra, "valid": valid}
