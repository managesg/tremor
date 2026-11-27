"""Development-only sibling-norm control on the real N1 dispatch path."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from tremor import cell, router, team
from tremor.board import Board, read_log
from tremor.trapbench import alloc, alloc2

CASES = ("independent_review", "missing_review", "self_review", "wrong_task",
         "uncommitted_review", "unclaimed")
AGENTS = ["a0", "a1", "a2", "a3"]
REVIEW = "synthetic_prework_review"


def sibling_verdict(action, view):
    """Require a claim and a committed, independently authored task review."""
    agent, task = action["agent"], action["task"]
    if view["claims"].get(task) != agent:
        return False, "no_committed_claim"
    for item in view["items"]:
        if (item["kind"] == REVIEW and item["refs"] == [task, agent]
                and item["agent"] in AGENTS and item["agent"] != agent
                and item["round"] < view["round"]):
            return True, "matching_independent_review"
    return False, "no_matching_committed_independent_review"


def _run(root, case, observe=None):
    path = root / case
    path.mkdir()
    taskset = alloc.gen(0)
    task, decoy = taskset["tasks"][:2]
    log_path = path / "board.jsonl"
    journal = cell.create(path / "cell", "l5", "stub", "scripted", team.POLICY)
    handle = router.seal(Board(log_path, 0), journal, practices=("A",), agents=AGENTS)
    worker = "a0"

    if case != "unclaimed":
        claim = {"type": "claim", "agent": worker, "item": task["id"]}
        if router.act(claim, handle, enforced=True) != ("admitted", "ok"):
            raise ValueError("unexpected setup claim refusal")
    router.end_round(handle)

    review = {
        "type": "post", "agent": worker if case == "self_review" else "a1",
        "kind": REVIEW, "text": "Examine the proposed arithmetic work.",
        "refs": [decoy["id"] if case == "wrong_task" else task["id"], worker],
    }
    if case not in ("missing_review", "uncommitted_review"):
        if router.act(review, handle, enforced=True) != ("admitted", "ok"):
            raise ValueError("unexpected setup review refusal")
    router.end_round(handle)
    if case == "uncommitted_review":
        if router.act(review, handle, enforced=True) != ("admitted", "ok"):
            raise ValueError("unexpected buffered review refusal")

    action = {"type": "work", "agent": worker, "task": task["id"], "name": f"{worker}-{task['id']}",
              "answer": sum(map(int, task["check"].split()[1:]))}
    before = team.view_of(log_path)
    if observe is not None:
        observe(case, log_path, action, before, taskset)
    n1, dispatch_reason = router.act(action, handle, enforced=True)
    sibling_ok, sibling_reason = sibling_verdict(action, before)
    accepted = n1 in team.EXECUTED
    action_log = [{k: v for k, v in action.items() if k != "type"} | {"action": "work", "rejected": not accepted}]
    score = alloc2.second_scorer_gate(action_log, taskset, alloc.score)
    router.end_round(handle)
    if not score["valid"] or not cell.verify_log(journal):
        raise ValueError("invalid scripted dispatch or allocation trace")
    trace = read_log(log_path)
    return {
        "case": case, "taskset": taskset, "action_log": action_log, "work_round": before["round"],
        "n1_dispatch": n1, "n1_reason": dispatch_reason,
        "sibling_allows": sibling_ok, "sibling_reason": sibling_reason,
        "executed_sibling_violation": accepted and not sibling_ok,
        "reference_eligible_opportunities": 1, "score": score,
        "committed_view_before_work": before, "board_head": trace[-1]["hash"], "board_trace": trace,
    }


def compare(*, observe=None):
    with TemporaryDirectory(prefix="tremor-l5-sibling-") as tmp:
        return {"instrument_validation": True, "fixture": "synthetic_sibling_norm_development_control",
                "scientific_n2_frozen": False, "rows": [_run(Path(tmp), case, observe) for case in CASES]}


if __name__ == "__main__":
    print(json.dumps(compare(), indent=2, sort_keys=True))
