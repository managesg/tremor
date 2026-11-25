"""Tie frozen inert Board rankings to once-per-target scripted screening."""

import json
from pathlib import Path
from shutil import copyfileobj
from tempfile import TemporaryDirectory

from murmuration.board import Board, read_log

from lab.l2c_detached_scoring import validate_selection
from lab.l2c_provenance_control import score
from lab.l2c_screening_dispatch import dispatch, verify as verify_dispatch
from lab.l2c_screening_ledger import settle, verify as verify_ledger
from lab.l2c_verification_ranking import fixture as ranking_fixture, select
from lab.l4_measured_compression import pin


BRIDGE_FIELDS = {"ranking_sha256", "ranking_head", "ranking_events", "dispatch_plan_sha256",
                 "reference_sha256", "targets"}


def _binding(rank_path, initial_path, selection, plan, bridge, expected_bridge_pin):
    if type(bridge) is not dict or bridge.keys() != BRIDGE_FIELDS or pin(bridge) != expected_bridge_pin:
        raise ValueError("rank-to-dispatch bridge differs from its expected pin")
    if pin(selection) != bridge["ranking_sha256"] or pin(plan) != bridge["dispatch_plan_sha256"]:
        raise ValueError("bridge carries a different selection or dispatch plan")
    validate_selection(selection, bridge["ranking_sha256"])
    replay = select(rank_path, candidates=selection["candidates"], expected_head=bridge["ranking_head"],
                    expected_events=bridge["ranking_events"], check_budget=selection["check_budget"],
                    seed=selection["random_seed"])
    if replay != selection:
        raise ValueError("ranking plan differs from the pinned Board replay")
    trace = read_log(initial_path)
    if (not trace or len(trace) != plan["initial_count"] or trace[-1]["hash"] != plan["initial_head"]
            or trace[-1]["type"] != "end_round"):
        raise ValueError("held-out Board differs from the anchored dispatch plan")
    active = Board(initial_path, seed=17).snapshot()["items"]
    route, claims = {}, {}
    if type(bridge["targets"]) is not list:
        raise ValueError("bridge targets must be an ordered list")
    for row in bridge["targets"]:
        if type(row) is not dict or row.keys() != {"rank_id", "target", "claim_sha256"}:
            raise ValueError("invalid rank-to-dispatch bridge row")
        rank_id, target, claim_pin = (row[key] for key in ("rank_id", "target", "claim_sha256"))
        if (type(rank_id) is not str or type(target) is not str or rank_id in route or target in claims
                or target not in active or pin(active[target]["text"]) != claim_pin):
            raise ValueError("bridge must bind unique visible targets and exact claims")
        route[rank_id], claims[target] = target, active[target]["text"]
    scheduled = {step["target"] for step in plan["steps"] if step["operation"] != "read"}
    if route.keys() != set(selection["candidates"]) or claims.keys() != scheduled:
        raise ValueError("bridge must cover the ranked and scheduled inventories exactly")
    return route, claims


def evaluate_arm(rank_path, initial_path, arm_path, selection, plan, bridge, reference, truth, *,
                 arm, expected_bridge_pin, expected_truth_pin, check_count=None):
    """Verify the identity bridge, settle selected checks, and execute matched dispatch."""
    route, claims = _binding(rank_path, initial_path, selection, plan, bridge, expected_bridge_pin)
    if arm not in selection["arms"]:
        raise ValueError("unknown ranked dispatch arm")
    ranked = selection["arms"][arm]
    context_fields = {"bridge_sha256": expected_bridge_pin, "arm": arm}
    if check_count is not None:
        if type(check_count) is not int or not 0 <= check_count <= len(ranked):
            raise ValueError("requested checks are outside the frozen ranked order")
        context_fields["check_count"] = check_count
        ranked = ranked[:check_count]
    selected = [route[candidate] for candidate in ranked]
    context = pin(context_fields)
    reference_pin = bridge["reference_sha256"]
    ledger = settle(selected, claims, reference, context_pin=context, expected_reference_pin=reference_pin)
    ledger_pin = pin(ledger)
    settled = verify_ledger(ledger, selected, claims, reference, context_pin=context,
                            expected_reference_pin=reference_pin, expected_ledger_pin=ledger_pin)
    opportunities = {step["id"] for step in plan["steps"] if step["operation"] != "read"}
    if (type(truth) is not dict or truth.keys() != {"bridge_sha256", "plan_sha256", "values"}
            or truth["bridge_sha256"] != expected_bridge_pin or truth["plan_sha256"] != bridge["dispatch_plan_sha256"]
            or pin(truth) != expected_truth_pin or type(truth["values"]) is not dict
            or truth["values"].keys() != opportunities or any(type(value) is not bool for value in truth["values"].values())):
        raise ValueError("terminal labels differ from the pinned dispatch bridge or opportunity inventory")
    with Path(initial_path).open("rb") as source, Path(arm_path).open("xb") as target:
        copyfileobj(source, target)
    result = dispatch(arm_path, plan, settled, expected_plan_pin=bridge["dispatch_plan_sha256"])
    verify_dispatch(arm_path, plan, settled, result, expected_plan_pin=bridge["dispatch_plan_sha256"],
                    **result["terminal"])
    assessment = score(result, truth, expected_report_pin=pin(result), expected_truth_pin=expected_truth_pin)
    return {"arm": arm, "selected_targets": selected, "evaluator_checks": ledger["checks"],
            "ledger": ledger, "ledger_sha256": ledger_pin, "settled": settled, "dispatch": result,
            "assessment": assessment}


def fixture(root):
    rank_path = root / "ranking.jsonl"
    candidates, anchor = ranking_fixture(rank_path, activity=True)
    selection = select(rank_path, candidates=candidates, check_budget=1, seed=17, **anchor)
    initial_path = root / "initial.jsonl"
    initial_path.touch(exist_ok=False)
    board = Board(initial_path, seed=17)
    board.post("observer", "Unrelated inert observation")

    def scalar(position, value):
        return json.dumps({"subject": f"heldout-{position}", "value": value, "version": 1}, sort_keys=True)

    targets, observed = {}, {}
    for position in (2, 0, 3, 1):
        observed[position] = scalar(position, 9 if position == 0 else 7)
        targets[position] = board.post("observer", observed[position])
    board.end_round()
    trace = read_log(initial_path)
    steps = [{"id": f"{operation}-{index}", "operation": operation, "target": targets[index], "support": []}
             for operation in ("read", "relay", "promotion") for index in range(4)]
    plan = {"initial_head": trace[-1]["hash"], "initial_count": len(trace), "origins": {}, "verified": {}, "steps": steps}
    reference = {targets[i]: None if i == 2 else scalar(i, 7) for i in range(4)}
    bridge = {"ranking_sha256": pin(selection), "ranking_head": anchor["expected_head"],
              "ranking_events": anchor["expected_events"], "dispatch_plan_sha256": pin(plan),
              "reference_sha256": pin(reference), "targets": [
                  {"rank_id": rank_id, "target": targets[i], "claim_sha256": pin(observed[i])}
                  for i, rank_id in enumerate(candidates)
              ]}
    truth = {"bridge_sha256": pin(bridge), "plan_sha256": pin(plan),
             "values": {step["id"]: step["target"] != targets[0] for step in steps if step["operation"] != "read"}}
    return rank_path, initial_path, selection, plan, bridge, reference, truth


def compare(root):
    rank_path, initial_path, selection, plan, bridge, reference, truth = fixture(root)
    bridge_pin = pin(bridge)
    return {"scope": "scripted_ranked_board_screening", "scientific_result": False,
            "selection": selection, "dispatch_plan": plan, "bridge_sha256": bridge_pin, "bridge": bridge,
            "reference": reference, "detached_labels": truth,
            "arms": {arm: evaluate_arm(rank_path, initial_path, root / f"{arm}.jsonl", selection, plan, bridge,
                                       reference, truth, arm=arm, expected_bridge_pin=bridge_pin,
                                       expected_truth_pin=pin(truth)) for arm in selection["arms"]}}


def demo():
    with TemporaryDirectory(prefix="tremor-l2c-screened-") as tmp:
        return compare(Path(tmp))


if __name__ == "__main__":
    print(json.dumps(demo(), sort_keys=True, indent=2, allow_nan=False))
