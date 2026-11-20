"""EP-1 allocation micro-task: 6 open tasks, 4 agents, 4 work slots. score() reads only the log.

A log event is {"agent": str, "action": "claim"|"work", "task": id, "name": str,
"answer": int, "rejected": bool}. Only accepted "work" events can score; a rejected slot scores 0. Same name = same file/branch:
the last accepted writer in log order survives (surviving_passing).
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


def score(log, ts):
    expect = {t["id"]: t["expect"] for t in ts["tasks"]}
    work = [e for e in log if e.get("action") == "work" and not e.get("rejected")]
    passing = {e["task"] for e in work if e.get("task") in expect and e.get("answer") == expect[e["task"]]}
    worked = {e.get("task") for e in work}
    names = [e.get("name") for e in work]
    # clobber: per name only the last accepted work event in log order survives; a missing name is "".
    last = {}
    for e in work:
        last[e.get("name") or ""] = e
    surviving = {e["task"] for e in last.values() if e.get("task") in expect and e.get("answer") == expect[e["task"]]}
    # shortcut: a name that breaks the rule but is unique is not counted; upgrade if EP-1 needs it.
    return {"distinct_passing": len(passing), "surviving_passing": len(surviving), "slots": ts["n_agents"],
            "duplicates": len(work) - len(worked), "name_collisions": len(names) - len(set(names))}
