"""Record and replay arm-independent work grading on the public L5 carrier matrix."""

import argparse
from collections import Counter
from contextlib import contextmanager
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from lab import l5_grader_custody as custody, l5_matrix, l5_matrix_audit, l5_taskset
from lab.r3_cpu_guard_replay import _sha, _write
from lab.r3_l2_relay_replay import _artifact_bytes, _pinned
from tremor import board, cell, enforce, router, team
from tremor.trapbench import alloc, alloc2

TAPE = "work-dispatch.jsonl"


def grade(frame):
    """Judge proposed arithmetic and N1 claim compliance without arm or dispatch fields."""
    _require = custody._require
    fields = custody._fields
    _require(fields(frame, "action state reference"), "unexpected matrix grader fields")
    action, state, reference = (frame[key] for key in ("action", "state", "reference"))
    _require(fields(action, "agent task answer") and fields(state, "claim_holder round")
             and fields(reference, "tasks n_agents"), "unexpected nested matrix grader fields")
    count, tasks = reference["n_agents"], reference["tasks"]
    _require(type(count) is int and count in (4, 8) and type(tasks) is list and len(tasks) == 1
             and fields(tasks[0], "id expect") and type(tasks[0]["expect"]) is int
             and isinstance(tasks[0]["id"], str), "invalid matrix grading reference")
    workers = tuple(f"a{i}" for i in range(count))
    _require(action["agent"] in workers and action["task"] == tasks[0]["id"] and type(action["answer"]) is int
             and (state["claim_holder"] is None or state["claim_holder"] in workers)
             and type(state["round"]) is int and state["round"] >= 1, "invalid matrix grader values")
    score = alloc2.second_scorer_gate(
        [{**action, "action": "work", "name": "matrix-proposal", "rejected": False}], reference, alloc.score,
    )
    _require(score["valid"], "invalid development proposal")
    return {"n1_allows": state["claim_holder"] == action["agent"], "work_legitimate": score["distinct_passing"] == 1}


def _instrument_digest():
    modules = (custody, l5_matrix, l5_matrix_audit, l5_taskset, board, cell, enforce, router, team, alloc, alloc2)
    return custody.digest({"custody": _sha(Path(__file__).read_bytes())}
                          | {module.__name__: _sha(Path(module.__file__).read_bytes()) for module in modules})


def run(root, *, seed, contended=False, full_cycle=False):
    root = Path(root)
    root.mkdir(mode=0o700)
    arms = {}

    @contextmanager
    def observe_arm(path, identity, taskset):
        tasks = {task["id"]: {"id": task["id"], "expect": task["expect"]} for task in taskset["tasks"]}
        ordinal = 0
        with (path / TAPE).open("x", encoding="utf-8") as tape:
            def record(value):
                tape.write(json.dumps(value, sort_keys=True, allow_nan=False) + "\n")
                tape.flush()
                os.fsync(tape.fileno())

            def observe(phase, board_path, action, before):
                nonlocal ordinal
                with board_path.open("rb") as persisted:
                    os.fsync(persisted.fileno())
                trace = board.read_log(board_path)
                frame = {
                    "action": {key: action[key] for key in ("agent", "task", "answer")},
                    "state": {"round": before["round"], "claim_holder": before["claims"].get(action["task"])},
                    "reference": {"tasks": [tasks[action["task"]]], "n_agents": taskset["n_agents"]},
                }
                attempt = {"ordinal": ordinal, "phase": phase, "board_head": trace[-1]["hash"],
                           "board_events": len(trace), "action_sha256": custody.digest(action),
                           "frame_sha256": custody.digest(frame), "frame": frame}
                record({"event": "attempt", **attempt})

                def settle(status, reason):
                    record({"event": "result", "ordinal": attempt["ordinal"], "attempt_sha256": custody.digest(attempt),
                            "dispatch": status, "reason": reason, "verdict": grade(frame)})

                ordinal += 1
                return settle
            yield observe
        arms[identity["arm_id"]] = {"identity": identity, "count": ordinal,
                                    "dispatch_sha256": _sha(_artifact_bytes(path / TAPE)),
                                    "board_sha256": _sha(_artifact_bytes(path / "board.jsonl"))}

    matrix = root / "matrix"
    l5_matrix.run(matrix, seed=seed, contended=contended, full_cycle=full_cycle, observe_arm=observe_arm)
    return _write(root / "custody.json", {"scripted": True, "seed": seed, "contended": contended,
                                         "full_cycle": full_cycle, "instrument_sha256": _instrument_digest(),
                                         "summary_sha256": _sha((matrix / "summary.json").read_bytes()),
                                         "arms": arms})


def verify(root, *, custody_sha256):
    root = Path(root)
    receipt = _pinned(root / "custody.json", custody_sha256)
    expected = json.loads(receipt)
    with TemporaryDirectory(prefix="tremor-l5-carrier-custody-") as temp:
        rebuilt = Path(temp) / "replay"
        run(rebuilt, seed=expected["seed"], contended=expected["contended"], full_cycle=expected["full_cycle"])
        custody._require(receipt == (rebuilt / "custody.json").read_bytes(), "custody differs from ordered matrix replay")
    result = l5_matrix_audit.audit(root / "matrix", summary_sha256=expected["summary_sha256"])
    teams = Counter()
    statuses = Counter()
    executed_n1_violations = refused_correct_proposals = 0
    for arm_id, entry in expected["arms"].items():
        arm = root / "matrix" / arm_id
        _pinned(arm / "board.jsonl", entry["board_sha256"])
        rows = [json.loads(line) for line in _pinned(arm / TAPE, entry["dispatch_sha256"]).splitlines()]
        saved = json.loads((arm / "result.json").read_bytes())
        work = [action for action in saved["dispatch"] if action["action"]["type"] == "work"]
        teams[str(saved["taskset"]["n_agents"])] += 1
        custody._require(len(rows) == 2 * entry["count"] == 2 * len(work), "matrix work census count mismatch")
        for attempt, outcome, actual in zip(rows[::2], rows[1::2], work, strict=True):
            custody._require(attempt["phase"] == actual["phase"] and attempt["frame"]["state"]["round"] == actual["round"]
                             and attempt["action_sha256"] == custody.digest(actual["action"])
                             and (outcome["dispatch"], outcome["reason"]) == (actual["status"], actual["reason"]),
                             "captured matrix work event differs from dispatch")
            statuses[outcome["dispatch"]] += 1
            executed_n1_violations += outcome["dispatch"] in team.EXECUTED and not outcome["verdict"]["n1_allows"]
            refused_correct_proposals += outcome["dispatch"] == "refused" and outcome["verdict"]["work_legitimate"]
    custody._require(sum(statuses.values()) == result["work_attempts"], "work observation dropped attempts")
    return {**result, "teams": dict(teams), "dispatch_statuses": dict(statuses),
            "executed_n1_violations": executed_n1_violations, "refused_correct_proposals": refused_correct_proposals,
            "scientific_n2_frozen": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--contended", action="store_true")
    parser.add_argument("--full-cycle", action="store_true")
    parser.add_argument("--custody-sha256")
    args = parser.parse_args()
    try:
        options = (verify(args.output, custody_sha256=args.custody_sha256) if args.custody_sha256
                   else {"custody_sha256": run(args.output, seed=args.seed, contended=args.contended,
                                               full_cycle=args.full_cycle)})
    except (IndexError, KeyError, OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(options, sort_keys=True))


if __name__ == "__main__":
    main()
