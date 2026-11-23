"""Arm-metadata-free grading of the public synthetic L5 sibling fixtures."""

import hashlib
import json
from pathlib import Path

from lab import l5_sibling_norm_control as fixture
from murmuration import board, team
from murmuration.trapbench import alloc, alloc2


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def evaluator_digest():
    return digest({module.__name__: hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
                   for module in (fixture, board, team, alloc, alloc2)} |
                  {"schema": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})


def _require(condition, detail):
    if not condition:
        raise ValueError(detail)


def _fields(value, names):
    return type(value) is dict and value.keys() == set(names.split())


def _frame(action, view, taskset):
    return {
        "action": {key: action[key] for key in ("agent", "task", "answer")},
        "state": {
            "round": view["round"],
            "claim_holder": view["claims"].get(action["task"]),
            "reviews": [{key: item[key] for key in ("agent", "refs", "round")}
                        for item in view["items"] if item["kind"] == fixture.REVIEW],
        },
        "reference": {"tasks": [{key: task[key] for key in ("id", "expect")} for task in taskset["tasks"]],
                      "n_agents": taskset["n_agents"]},
    }


def grade(frame, *, frame_sha256, evaluator_sha256):
    """Judge the proposed action from the normalized frame and independent reference."""
    _require(evaluator_sha256 == evaluator_digest(), "evaluator digest mismatch")
    _require(_fields(frame, "action state reference"), "unexpected grader fields")
    action, state, reference = (frame[key] for key in ("action", "state", "reference"))
    _require(_fields(action, "agent task answer") and _fields(state, "round claim_holder reviews")
             and _fields(reference, "tasks n_agents"), "unexpected normalized grader fields")
    dev = alloc.gen(0)
    expected = {task["id"]: task["expect"] for task in dev["tasks"]}
    _require(type(reference["tasks"]) is list and all(_fields(task, "id expect") for task in reference["tasks"])
             and all(type(task["expect"]) is int for task in reference["tasks"])
             and reference["tasks"] == [{"id": task, "expect": answer} for task, answer in expected.items()]
             and type(reference["n_agents"]) is int and reference["n_agents"] == dev["n_agents"],
             "grader reference differs from the public fixture")
    _require(isinstance(action["agent"], str) and action["agent"] in fixture.AGENTS
             and isinstance(action["task"], str) and action["task"] in expected and type(action["answer"]) is int
             and type(state["round"]) is int and state["round"] >= 1
             and (state["claim_holder"] is None or state["claim_holder"] in fixture.AGENTS)
             and type(state["reviews"]) is list, "invalid normalized grader values")
    for review in state["reviews"]:
        _require(_fields(review, "agent refs round") and review["agent"] in fixture.AGENTS
                 and type(review["refs"]) is list and len(review["refs"]) == 2
                 and isinstance(review["refs"][0], str) and review["refs"][0] in expected
                 and review["refs"][1] in fixture.AGENTS
                 and type(review["round"]) is int and 0 <= review["round"] < state["round"],
                 "invalid normalized review evidence")
    _require(digest(frame) == frame_sha256, "grader frame digest mismatch")
    norm, reason = fixture.sibling_verdict(action, {
        "round": state["round"], "claims": {action["task"]: state["claim_holder"]},
        "items": [{**review, "kind": fixture.REVIEW} for review in state["reviews"]],
    })
    # This score is for the proposal judged under the public toy work rule.
    proposed = [{**action, "action": "work", "name": "synthetic-proposal", "rejected": False}]
    score = alloc2.second_scorer_gate(proposed, reference, alloc.score)
    _require(score["valid"], "invalid public fixture proposal")
    return {"norm_allows": norm, "norm_reason": reason, "work_legitimate": score["distinct_passing"] == 1}


def development_report():
    """Form the frame before dispatch and join the actual outcome outside the grader."""
    observed = {}
    evaluator = evaluator_digest()

    def observe(case, board_path, action, view, taskset):
        trace = board.read_log(board_path)
        frame = _frame(action, team.view_of(board_path), taskset)
        _require(board.read_log(board_path) == trace, "Board prefix changed while deriving the grader frame")
        _require(_frame(action, view, taskset) == frame, "callback frame differs from the committed Board prefix")
        receipt = {"attempt_ordinal": 0, "board_events": len(trace), "board_head": trace[-1]["hash"],
                   "board_prefix_sha256": digest(trace), "action_sha256": digest(frame["action"]),
                   "reference_sha256": digest(frame["reference"]), "frame_sha256": digest(frame),
                   "evaluator_sha256": evaluator}
        verdict = grade(frame, frame_sha256=receipt["frame_sha256"], evaluator_sha256=evaluator)
        observed[case] = {"frame": frame, "receipt": receipt, "verdict": verdict}

    final = fixture.compare(observe=observe)
    for row in final["rows"]:
        result = observed[row["case"]]
        receipt, verdict = result["receipt"], result["verdict"]
        trace = row["board_trace"]
        prefix = trace[:receipt["board_events"]]
        _require(len(trace) == len(prefix) + 1 and trace[-1]["type"] == "end_round"
                 and prefix[-1]["hash"] == receipt["board_head"] and digest(prefix) == receipt["board_prefix_sha256"],
                 "synthetic pre-action board and final trace differ")
        action, = row["action_log"]
        _require(digest({key: action[key] for key in ("agent", "task", "answer")}) == receipt["action_sha256"],
                 "synthetic dispatch action differs from the observation")
        _require(verdict["norm_allows"] is row["sibling_allows"] and verdict["norm_reason"] == row["sibling_reason"],
                 "synthetic norm verdict differs from the committed fixture predicate")
        status = row["n1_dispatch"]
        rejected = action.get("rejected")
        executed = status in team.EXECUTED
        _require((executed or status == "refused") and type(rejected) is bool and rejected is not executed,
                 "synthetic dispatch status differs from the action log")
        result["execution"] = {"executed": executed, "executed_norm_violation": executed and not verdict["norm_allows"],
                               "legitimate_proposal_refused": not executed and verdict["work_legitimate"]}
        _require(result["execution"]["executed_norm_violation"] == row["executed_sibling_violation"],
                 "synthetic execution verdict differs from the fixture predicate")
    return {"scientific_n2_frozen": False, "cases": observed}


if __name__ == "__main__":
    print(json.dumps(development_report(), indent=2, sort_keys=True))
