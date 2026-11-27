"""Apply settled scalar screening decisions to real scripted Board dispatches."""

from collections.abc import Mapping
from functools import partial

from tremor.board import Board, read_log

from lab.l2c_provenance_receipts import audit
from lab.l4_measured_compression import pin


_MODE = "screened"
_WORKER = "fixture-worker"
_PLAN_FIELDS = {"initial_head", "initial_count", "origins", "verified", "steps"}
_STEP_FIELDS = {"id", "operation", "target", "support"}
_SETTLED_STATUSES = ("unchecked", "matched", "mismatch", "unavailable")


def _identifier(value):
    return type(value) is str and bool(value) and value == value.strip()


def _screening(settled):
    if not isinstance(settled, Mapping):
        raise ValueError("settled screening must map targets to scalar statuses")
    snapshot = dict(settled)
    if any(not _identifier(target) or status not in _SETTLED_STATUSES for target, status in snapshot.items()):
        raise ValueError("invalid target or status in settled screening")
    return snapshot


def _validate_plan(plan, expected_pin):
    if (type(plan) is not dict or plan.keys() != _PLAN_FIELDS or type(plan["steps"]) is not list
            or not plan["steps"] or type(plan["origins"]) is not dict or type(plan["verified"]) is not dict
            or type(plan["initial_count"]) is not int or plan["initial_count"] < 1
            or not _identifier(plan["initial_head"]) or pin(plan) != expected_pin):
        raise ValueError("invalid or changed screened dispatch plan")
    seen = set()
    for step in plan["steps"]:
        if (type(step) is not dict or step.keys() != _STEP_FIELDS or not _identifier(step["id"])
                or step["id"] in seen or step["operation"] not in ("read", "relay", "promotion")
                or not _identifier(step["target"]) or type(step["support"]) is not list
                or any(not _identifier(target) for target in step["support"])
                or (step["operation"] == "read" and step["support"])):
            raise ValueError("invalid or repeated screened dispatch step")
        seen.add(step["id"])


def _decide(active, step, *, screening):
    target = step["target"]
    if target not in active:
        return {"admitted": False, "reason": "target_unavailable", "checks": 0}
    status = screening.get(target, "unchecked")
    admitted = status in ("unchecked", "matched")
    return {"admitted": admitted, "reason": "admitted" if admitted else f"screening_{status}",
            "checks": int(status != "unchecked")}


def _report(plan_pin, screening, terminal, receipts, counts):
    return {"mode": _MODE, "plan_sha256": plan_pin, "settled_sha256": pin(screening),
            "terminal": terminal, "receipts": receipts, "physical_counts": counts,
            "cached_lookups": counts["checks"]}


def dispatch(path, plan, settled, *, expected_plan_pin):
    """Commit the pinned schedule, charging only per-attempt cached lookups here."""
    screening = _screening(settled)
    _validate_plan(plan, expected_plan_pin)
    previous = read_log(path)
    if len(previous) != plan["initial_count"] or previous[-1]["hash"] != plan["initial_head"]:
        raise ValueError("initial Board differs from the screened dispatch plan")
    board = Board(path, seed=17)
    receipts = []
    for step in plan["steps"]:
        operation, target = step["operation"], step["target"]
        post_id = read_found = None
        if operation == "read":
            read_found = board.read(_WORKER, target) is not None
            status, reason, checks = "read", None, 0
        else:
            active = board.snapshot()["items"]
            outcome = _decide(active, step, screening=screening)
            status = "admitted" if outcome["admitted"] else "refused"
            reason, checks = outcome["reason"], outcome["checks"]
            if outcome["admitted"]:
                post_id = board.post(_WORKER, active[target]["text"], kind=operation, refs=(target,))
        board.end_round()
        closed = read_log(path)
        receipts.append({**step, "mode": _MODE, "prior_head": previous[-1]["hash"], "prior_count": len(previous),
                         "status": status, "reason": reason, "checks": checks, "post_id": post_id,
                         "closed_head": closed[-1]["hash"], "closed_count": len(closed), "read_found": read_found})
        previous = closed
    terminal = {"expected_terminal_head": previous[-1]["hash"], "expected_events": len(previous)}
    counts = audit(path, plan, receipts, mode=_MODE, expected_plan_pin=expected_plan_pin,
                   decide_step=partial(_decide, screening=screening), **terminal)
    return _report(expected_plan_pin, screening, terminal, receipts, counts)


def verify(path, plan, settled, report, *, expected_plan_pin, expected_terminal_head, expected_events):
    """Verify physical events, cached decisions and full report from separate evidence."""
    screening = _screening(settled)
    _validate_plan(plan, expected_plan_pin)
    if type(report) is not dict or report.get("settled_sha256") != pin(screening):
        raise ValueError("report differs from the settled screening snapshot")
    terminal = {"expected_terminal_head": expected_terminal_head, "expected_events": expected_events}
    receipts = report.get("receipts")
    counts = audit(path, plan, receipts, mode=_MODE, expected_plan_pin=expected_plan_pin,
                   decide_step=partial(_decide, screening=screening), **terminal)
    independently_verified = _report(expected_plan_pin, screening, terminal, receipts, counts)
    if pin(report) != pin(independently_verified):
        raise ValueError("reported screening accounting differs from the verified Board and cached lookups")
    return independently_verified
