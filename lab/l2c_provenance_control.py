"""Board-backed defensive dispatch control for finite synthetic scalar claims."""

import json
from pathlib import Path
from shutil import copyfile
from tempfile import TemporaryDirectory

from tremor.board import Board, read_log

from lab.l2c_provenance_policy import decide
from lab.l2c_provenance_receipts import audit
from lab.l4_measured_compression import pin


MODES = ("permissive", "verified", "corroborated", "verified_or_corroborated")
WORKER = "fixture-worker"


def _scalar(value, version=1):
    return json.dumps({"subject": "fixture-counter", "value": value, "version": version}, sort_keys=True)


def fixture(path):
    Path(path).touch(exist_ok=False)
    board = Board(path, seed=17)
    origins = {}
    valid, invalid, newer = _scalar(7), _scalar(9), _scalar(7, 2)

    def observation(origin, text=valid):
        item = board.post("source", text, kind="observation")
        origins[item] = {"origin": origin, "text": text}
        return item

    first = observation("source-a")
    alias = observation("source-a")
    independent = observation("source-b")
    retired = observation("source-c")
    wrong = observation("source-d", invalid)
    newer_support = observation("source-b", newer)
    board.end_round()
    target = board.post("worker", valid, refs=(first,))
    verified = board.post("worker", valid, refs=(first,))
    bad = board.post("worker", invalid, refs=(wrong,))
    retired_target = board.post("worker", valid, refs=(first,))
    unknown = board.post("worker", valid, refs=("unavailable-parent",))
    board.end_round()
    dependent = board.post("worker", valid, refs=(target,))
    self_reference = f"p{len(read_log(path))}"
    board.post("worker", valid, refs=(self_reference,))
    board.post("source", newer, supersedes=(retired, retired_target))
    board.end_round()
    pending = observation("source-e")
    trace = read_log(path)

    def step(identifier, operation, target_id, *support):
        return {"id": identifier, "operation": operation, "target": target_id, "support": list(support)}

    return {"initial_head": trace[-1]["hash"], "initial_count": len(trace), "origins": origins,
            "verified": {verified: valid, bad: valid}, "steps": [
                step("pending-support", "relay", target, pending),
                step("visible-read", "read", target),
                step("unavailable-read", "read", retired_target),
                step("independent-read", "read", independent),
                step("independent-relay", "relay", target, independent),
                step("verified-promotion", "promotion", verified, independent),
                step("committed-support", "promotion", target, pending),
                step("same-origin", "relay", target, alias),
                step("dependent-support", "promotion", target, dependent),
                step("retired-support", "relay", target, retired),
                step("wrong-version", "promotion", target, newer_support),
                step("missing-ancestor", "relay", target, unknown),
                step("cyclic-support", "promotion", target, self_reference),
                step("duplicate-support", "promotion", target, independent, independent),
                step("incorrect-value", "relay", bad, independent),
                step("retired-target", "relay", retired_target, independent),
                step("missing-target", "promotion", "unavailable-target", independent),
                step("verified-only", "relay", verified),
            ]}


def _policy(items, plan, mode, step):
    action = {key: step[key] for key in ("operation", "target", "support")}
    if mode != "verified_or_corroborated":
        return decide(items, plan["origins"], plan["verified"], mode=mode, **action)
    verified = decide(items, plan["origins"], plan["verified"], mode="verified", **action)
    if verified["admitted"]:
        return verified | {"reason": "verified_receipt"}
    if verified["reason"] == "target_unavailable":
        return verified
    corroborated = decide(items, plan["origins"], plan["verified"], mode="corroborated", **action)
    return corroborated | {"reason": "corroborated" if corroborated["admitted"] else corroborated["reason"],
                           "checks": verified["checks"] + corroborated["checks"]}


def run(path, plan, *, mode, expected_plan_pin):
    """Dispatch the same pinned attempt tape against actual committed Board state."""
    if mode not in MODES or pin(plan) != expected_plan_pin:
        raise ValueError("invalid mode or changed dispatch plan")
    previous = read_log(path)
    if (len(previous) != plan["initial_count"] or not previous or previous[-1]["hash"] != plan["initial_head"]):
        raise ValueError("initial Board differs from the dispatch plan")
    board = Board(path, seed=17)
    receipts = []
    for step in plan["steps"]:
        operation, target, support = (step[key] for key in ("operation", "target", "support"))
        items = board.snapshot()["items"]
        post_id = read_found = None
        if operation == "read":
            read_found = board.read(WORKER, target) is not None
            status, reason, checks = "read", None, 0
        else:
            policy = _policy(items, plan, mode, step)
            status = "admitted" if policy["admitted"] else "refused"
            reason, checks = policy["reason"], policy["checks"]
            if policy["admitted"]:
                substantiated = support if mode == "corroborated" or reason == "corroborated" else ()
                post_id = board.post(WORKER, items[target]["text"], kind=operation, refs=(target, *substantiated))
        board.end_round()
        closed = read_log(path)
        receipts.append({**step, "mode": mode, "prior_head": previous[-1]["hash"], "prior_count": len(previous),
                         "status": status, "reason": reason, "checks": checks, "post_id": post_id,
                         "closed_head": closed[-1]["hash"], "closed_count": len(closed), "read_found": read_found})
        previous = closed
    terminal = {"expected_terminal_head": previous[-1]["hash"], "expected_events": len(previous)}
    counts = audit(path, plan, receipts, mode=mode, expected_plan_pin=expected_plan_pin,
                   decide_step=lambda items, step: _policy(items, plan, mode, step), **terminal)
    return {"mode": mode, "plan_sha256": expected_plan_pin, "terminal": terminal,
            "receipts": receipts, "physical_counts": counts}


def detached(plan):
    return {"plan_sha256": pin(plan), "values": {step["id"]: step["id"] != "incorrect-value"
                                                 for step in plan["steps"] if step["operation"] != "read"}}


def score(report, truth, *, expected_report_pin, expected_truth_pin):
    """Apply separately pinned scalar correctness labels after dispatch."""
    if (pin(report) != expected_report_pin or pin(truth) != expected_truth_pin
            or truth["plan_sha256"] != report["plan_sha256"]):
        raise ValueError("score inputs differ from the pinned reports or plan")
    attempts = [row for row in report["receipts"] if row["operation"] != "read"]
    values = truth["values"]
    if set(values) != {row["id"] for row in attempts} or any(type(value) is not bool for value in values.values()):
        raise ValueError("exact Boolean scalar labels required for every scheduled attempt")
    outcomes = {"valid_admitted": 0, "valid_refused": 0, "invalid_admitted": 0, "invalid_refused": 0}
    for row in attempts:
        validity = "valid" if values[row["id"]] else "invalid"
        outcomes[f"{validity}_{row['status']}"] += 1
    return {"report_sha256": expected_report_pin, "truth_sha256": expected_truth_pin, **outcomes}


def assess(path, plan, report, truth, *, expected_plan_pin, expected_report_pin, expected_truth_pin,
           expected_terminal_head, expected_events):
    """Verify a retained dispatch artifact against its Board before scoring labels."""
    terminal = {"expected_terminal_head": expected_terminal_head, "expected_events": expected_events}
    if (pin(report) != expected_report_pin or report["plan_sha256"] != expected_plan_pin
            or report["terminal"] != terminal):
        raise ValueError("dispatch report differs from its expected plan, report or terminal pin")
    mode = report["mode"]
    counts = audit(path, plan, report["receipts"], mode=mode, expected_plan_pin=expected_plan_pin,
                   decide_step=lambda items, step: _policy(items, plan, mode, step), **terminal)
    if counts != report["physical_counts"]:
        raise ValueError("reported physical counts differ from the Board audit")
    return score(report, truth, expected_report_pin=expected_report_pin, expected_truth_pin=expected_truth_pin)


def compare(root):
    initial = root / "initial.jsonl"
    plan = fixture(initial)
    plan_pin = pin(plan)
    reports = {}
    for mode in MODES:
        path = root / f"{mode}.jsonl"
        copyfile(initial, path)
        reports[mode] = run(path, plan, mode=mode, expected_plan_pin=plan_pin)
    truth = detached(plan)
    scores = {mode: assess(root / f"{mode}.jsonl", plan, result, truth, expected_plan_pin=plan_pin,
                           expected_report_pin=pin(result), expected_truth_pin=pin(truth), **result["terminal"])
              for mode, result in reports.items()}
    return {"scope": "scripted_inert_scalar_dispatch", "scientific_result": False,
            "plan": plan, "arm_results": reports, "detached_scores": scores}


def demo():
    with TemporaryDirectory(prefix="tremor-l2c-provenance-") as tmp:
        return compare(Path(tmp))


if __name__ == "__main__":
    print(json.dumps(demo(), sort_keys=True, indent=2, allow_nan=False))
