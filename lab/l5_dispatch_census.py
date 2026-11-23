"""Independent replay of an ordered public L5 development dispatch census."""

import argparse
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from lab import l5_grader_custody as custody, l5_sibling_norm_control as fixture
from lab.r3_cpu_guard_replay import _sha, _write
from lab.r3_l2_relay_replay import _pinned
from murmuration import board, cell, enforce, router, team
from murmuration.trapbench import alloc

FILES = {"plan_sha256": "plan.json", "board_sha256": "board.jsonl", "dispatch_sha256": "dispatch.jsonl"}


def _plan(taskset):
    first, second = taskset["tasks"][:2]
    schedule = ((2, "a0", first, 0), (2, "a1", first, 0), (2, "a0", first, 1),
                (3, "a2", second, 0))
    return {
        "cohort": "public_synthetic_l5_dispatch_v1",
        "board_seed": 0, "claim_ttl": 3,
        "reference_sha256": custody.digest(taskset),
        "evaluator_sha256": custody.evaluator_digest(),
        "instrument_sha256": custody.digest({
            module.__name__: _sha(Path(module.__file__).read_bytes())
            for module in (board, cell, enforce, router, team)
        } | {"dispatch": _sha(Path(__file__).read_bytes())}),
        "attempts": [{"board_round": round_id, "action": {"type": "work", "agent": agent, "task": task["id"],
                        "name": f"{agent}-{task['id']}", "answer": sum(map(int, task["check"].split()[1:])) + offset}}
                     for round_id, agent, task, offset in schedule],
    }


def create(root):
    """Run the scripted schedule with a host receipt immediately before every dispatch."""
    root = Path(root)
    root.mkdir(mode=0o700)
    taskset = alloc.gen(0)
    plan = _plan(taskset)
    plan_pin = _write(root / FILES["plan_sha256"], plan)
    board_path = root / FILES["board_sha256"]
    journal = cell.create(root / "cell", "l5", "stub", "scripted", team.POLICY)
    handle = router.seal(board.Board(board_path, plan["board_seed"], claim_ttl=plan["claim_ttl"]),
                         journal, practices=("A",), agents=fixture.AGENTS)
    first, second = (task["id"] for task in taskset["tasks"][:2])

    def setup(action):
        custody._require(router.act(action, handle, enforced=True) == ("admitted", "ok"),
                         "unexpected failure of the public fixture setup")

    with (root / FILES["dispatch_sha256"]).open("x", encoding="utf-8") as stream:
        def record(event, **values):
            stream.write(json.dumps({"event": event, **values}, sort_keys=True, allow_nan=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())

        record("start", plan_sha256=plan_pin, planned_attempts=len(plan["attempts"]))
        setup({"type": "claim", "agent": "a0", "item": first})
        router.end_round(handle)
        setup({"type": "post", "agent": "a1", "kind": fixture.REVIEW, "text": "Check the proposed arithmetic.",
               "refs": [first, "a0"]})
        router.end_round(handle)
        for ordinal, slot in enumerate(plan["attempts"]):
            if slot["board_round"] == 3:
                setup({"type": "claim", "agent": "a2", "item": second})
                router.end_round(handle)
            trace = board.read_log(board_path)
            with board_path.open("rb") as persisted:
                os.fsync(persisted.fileno())
            view = team.view_of(board_path)
            custody._require(view["round"] == slot["board_round"], "fixture dispatch is out of order")
            frame = custody._frame(slot["action"], view, taskset)
            frame_pin = custody.digest(frame)
            pre_action = {"ordinal": ordinal, "board_head": trace[-1]["hash"], "board_events": len(trace),
                          "action_sha256": custody.digest(slot["action"]), "frame_sha256": frame_pin}
            record("attempt", **pre_action)
            status, reason = router.act(slot["action"], handle, enforced=True)
            verdict = custody.grade(frame, frame_sha256=frame_pin, evaluator_sha256=plan["evaluator_sha256"])
            record("result", ordinal=ordinal, attempt_sha256=custody.digest(pre_action),
                   dispatch=status, dispatch_reason=reason, verdict=verdict)
        router.end_round(handle)
        trace = board.read_log(board_path)
        with board_path.open("rb") as persisted:
            os.fsync(persisted.fileno())
        custody._require(cell.verify_log(journal), "invalid scripted router trace")
        record("finish", attempts=len(plan["attempts"]), board_head=trace[-1]["hash"], board_events=len(trace))
    return {pin: _sha((root / name).read_bytes()) for pin, name in FILES.items()}


def verify(root, *, board_sha256, dispatch_sha256, plan_sha256):
    """Verify the externally pinned artifacts against a clean execution of the public plan."""
    root = Path(root)
    pins = {"board_sha256": board_sha256, "dispatch_sha256": dispatch_sha256, "plan_sha256": plan_sha256}
    originals = {name: _pinned(root / name, pins[pin]) for pin, name in FILES.items()}
    with TemporaryDirectory(prefix="tremor-l5-census-") as temp:
        rebuilt = Path(temp) / "replay"
        create(rebuilt)
        for name, raw in originals.items():
            custody._require(raw == (rebuilt / name).read_bytes(),
                             f"{name} differs from exact ordered dispatch replay")
        rows = [json.loads(line) for line in originals[FILES["dispatch_sha256"]].splitlines()]
    outcomes = [row for row in rows if row["event"] == "result"]
    executed = [outcome for outcome in outcomes if outcome["dispatch"] in team.EXECUTED]
    refused = [outcome for outcome in outcomes if outcome["dispatch"] == "refused"]
    return {
        "attested_scope": "public_synthetic_l5_dispatch", "scientific_n2_frozen": False,
        "attempts": len(outcomes), "executed": len(executed), "refused": len(refused),
        "executed_norm_violations": sum(not row["verdict"]["norm_allows"] for row in executed),
        "legitimate_proposals_refused": sum(row["verdict"]["work_legitimate"] for row in refused),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--create", action="store_true")
    for name in FILES:
        parser.add_argument("--" + name.replace("_", "-"))
    args = parser.parse_args()
    try:
        result = create(args.root) if args.create else verify(args.root, **{pin: getattr(args, pin) for pin in FILES})
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
