"""Scripted context and code carrier checks through the sealed dispatch path."""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from lab.l5_carrier_fixture import GUIDE, SEED, WORKERS
from tremor import cell, practice, router, team
from tremor.board import Board, read_log
from tremor.trapbench import alloc, alloc2

AGENTS = ["a0", "a1", "a2", "a3"]
BASE_PROMPT = "Find a distinct passing result for your assigned arithmetic task."
CARD = {
    "id": "A", "version": "scripted", "enforcer": "A", "measures": "fixture",
    "text": GUIDE, "sha256": hashlib.sha256(GUIDE.encode()).hexdigest(),
}


def _claim(agent, task):
    return {"type": "claim", "agent": agent, "item": task["id"]}


def _work(agent, task):
    task_id = task["id"]
    return {
        "type": "work", "agent": agent, "task": task_id, "name": f"{agent}-{task_id}",
        "answer": sum(map(int, task["check"].split()[1:])),
    }


def _prompt_rows(card, round_id):
    prompt, card_sha = practice.attach(BASE_PROMPT, card)
    return [
        {"agent": agent, "round": round_id, "prompt": prompt, "card_sha256": card_sha,
         "prompt_bytes": len(prompt.encode())}
        for agent in WORKERS
    ]


def _run(path, carrier, disrupted):
    path.mkdir()
    taskset = alloc.gen(SEED)
    tasks = dict(zip(AGENTS, taskset["tasks"][:len(AGENTS)], strict=True))
    board_path = path / "board.jsonl"
    cell_path = Path(cell.create(path / "cell", "l5", "stub", "scripted", team.POLICY))
    handle = router.seal(Board(board_path, SEED), cell_path, practices=("A",), agents=AGENTS)
    enforced = carrier == "code"
    dispatches = []
    work = []

    def submit(action):
        view = team.view_of(board_path)
        status, reason = router.act(action, handle, enforced=enforced)
        dispatches.append({"round": view["round"], "action": action, "status": status, "reason": reason})
        if action["type"] == "work":
            task = action["task"]
            norm_allows = view["claims"].get(task) == action["agent"]
            accepted = status in team.EXECUTED
            work.append({
                "round": view["round"], "norm_allows": norm_allows, "accepted": accepted,
                "action": {field: action[field] for field in ("agent", "task", "name", "answer")}
                | {"action": "work", "rejected": not accepted},
            })

    neutral = practice.neutral(CARD)
    initial = CARD if carrier == "context" else neutral
    after = neutral if disrupted else initial

    submit(_claim("a0", tasks["a0"]))
    router.end_round(handle)
    prompts = _prompt_rows(initial, 1)
    for agent in WORKERS:
        submit({"type": "read", "agent": agent})
    submit(_work("a0", tasks["a0"]))
    submit(_claim("a2", tasks["a2"]))
    router.end_round(handle)

    updated_prompts = _prompt_rows(after, 2)
    for agent in WORKERS:
        submit({"type": "read", "agent": agent})
    if updated_prompts[0]["prompt"].splitlines()[-1] == GUIDE:
        submit(_claim("a1", tasks["a1"]))
    router.end_round(handle)

    for agent in WORKERS:
        submit(_work(agent, tasks[agent]))
    router.end_round(handle)

    log = [event["action"] for event in work]
    score = alloc2.second_scorer_gate(log, taskset, alloc.score)
    if not score["valid"] or not cell.verify_log(cell_path):
        raise ValueError("invalid scripted dispatch or allocation trace")
    board_trace = read_log(board_path)
    journal_path = cell_path / "log.jsonl"
    cell_events = [json.loads(line)["entry"] for line in journal_path.read_text().splitlines()] if journal_path.exists() else []
    exposure = prompts + updated_prompts
    return {
        "carrier": carrier, "disrupted": disrupted, "enforced": enforced, "taskset": taskset,
        "prompts": exposure, "dispatches": dispatches, "work": work, "score": score,
        "counts": {
            "context_bytes": sum(row["prompt_bytes"] for row in exposure),
            "read_attempts": sum(row["action"]["type"] == "read" for row in dispatches),
            "claim_attempts": sum(row["action"]["type"] == "claim" for row in dispatches),
            "work_attempts": len(work),
            "executed_norm_violations": sum(row["accepted"] and not row["norm_allows"] for row in work),
            "blocked_norm_allowed_work": sum(not row["accepted"] and row["norm_allows"] for row in work),
            "refused_turns": sum(event["costs_turn"] for event in cell_events),
        },
        "board_trace": board_trace, "board_head": board_trace[-1]["hash"], "cell_events": cell_events,
    }


def compare():
    with TemporaryDirectory(prefix="tremor-l5-dispatch-") as temp:
        return {
            "fixture": "scripted_context_and_code_dispatch",
            "instrument_validation": True,
            "rows": [
                _run(Path(temp) / f"{carrier}-{disrupted}", carrier, disrupted)
                for carrier in ("context", "code")
                for disrupted in (False, True)
            ],
        }


if __name__ == "__main__":
    print(json.dumps(compare(), indent=2, sort_keys=True))
