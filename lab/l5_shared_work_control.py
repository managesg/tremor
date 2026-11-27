"""Exercise shared-work duplication through the real Board and N1 router."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from lab import l5_taskset
from tremor import cell, router, team
from tremor.board import Board, read_log
from tremor.trapbench import alloc, alloc2

SEED = 86
SHARED_OWNER = "a2"


def _arm(path, taskset, *, enforced, disrupted):
    path.mkdir()
    jobs = alloc.oracle_log(taskset)
    workers = [job["agent"] for job in jobs]
    shared = jobs[1]["task"]
    jobs[2] = {**jobs[1], "agent": SHARED_OWNER,
               "name": taskset["name_rule"].format(agent=SHARED_OWNER, task=shared)}
    board_path = path / "board.jsonl"
    operations = Path(cell.create(path / "cell", "l5", "stub", "scripted", team.POLICY))
    handle = router.seal(Board(board_path, taskset["seed"]), operations, practices=("A",), agents=workers)
    dispatch = []
    work = []

    def submit(action):
        committed = team.view_of(board_path)
        status, reason = router.act(action, handle, enforced=enforced)
        dispatch.append({"round": committed["round"], "action": action, "status": status, "reason": reason})
        if action["type"] == "work":
            allowed = committed["claims"].get(action["task"]) == action["agent"]
            executed = status in team.EXECUTED
            row = {k: v for k, v in action.items() if k != "type"}
            work.append({"norm_allows": allowed, "executed": executed,
                         "action": row | {"action": "work", "rejected": not executed}})
        return status

    def claim(job):
        return submit({"type": "claim", "agent": job["agent"], "item": job["task"]})

    def attempt(job):
        submit({k: v for k, v in job.items() if k != "action"} | {"type": "work"})

    # The seed chooses a2 in the simultaneous Board tie. Dispatch a2 first
    # so code and observe share the same starting owner for the release probe.
    for index in (0, 2, 1, *range(3, len(jobs))):
        claim(jobs[index])
    router.end_round(handle)
    if team.view_of(board_path)["claims"].get(shared) != SHARED_OWNER:
        raise ValueError("the two policies must start with the same hot-task owner")

    attempt(jobs[0])
    if disrupted:
        release = {"type": "release", "agent": SHARED_OWNER, "item": shared, "done": False}
        if submit(release) != "admitted":
            raise ValueError("scripted release was refused")
    router.end_round(handle)

    owner_after_commit = team.view_of(board_path)["claims"].get(shared)
    if owner_after_commit != (None if disrupted else SHARED_OWNER):
        raise ValueError("unexpected holder after intervention commit")
    if disrupted and claim(jobs[2]) != "admitted":
        raise ValueError("committed release did not allow the fixed reclaim")
    router.end_round(handle)

    for job in jobs[1:]:
        attempt(job)
    router.end_round(handle)

    score = alloc2.second_scorer_gate([event["action"] for event in work], taskset, alloc.score)
    if not score["valid"] or not cell.verify_log(operations):
        raise ValueError("scripted work or refusal journal did not verify")
    board_trace = read_log(board_path)
    journal = operations / "log.jsonl"
    router_journal = [json.loads(line)["entry"] for line in journal.read_text().splitlines()]
    return {
        "mode": "code" if enforced else "observe",
        "disrupted": disrupted, "taskset": taskset, "shared_task": shared,
        "owner_after_intervention_commit": owner_after_commit,
        "attempted_work": len(work), "refused_work": sum(not row["executed"] for row in work),
        "executed_duplicate_work": score["duplicates"], "distinct_passing_work": score["distinct_passing"],
        "executed_norm_violations": sum(row["executed"] and not row["norm_allows"] for row in work),
        "blocked_legitimate_work": sum(not row["executed"] and row["norm_allows"] for row in work),
        "score": score, "dispatch": dispatch, "work": work,
        "board_head": board_trace[-1]["hash"], "board_trace": board_trace, "router_journal": router_journal,
    }


def compare():
    with TemporaryDirectory(prefix="tremor-l5-shared-work-") as scratch:
        output = Path(scratch)
        return {
            "evidence": "scripted_development",
            "fixture": "shared_work_duplicate_control",
            "rows": [
                _arm(output / f"{size}-{enforced}-{disrupted}", l5_taskset.generate(SEED, size),
                     enforced=enforced, disrupted=disrupted)
                for size in (4, 8)
                for enforced in (False, True)
                for disrupted in (False, True)
            ],
        }


if __name__ == "__main__":
    print(json.dumps(compare(), indent=2, sort_keys=True))
