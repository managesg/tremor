"""Independently reconcile scripted quarantine receipts with Board events."""

from murmuration.board import read_log

from lab.l4_measured_compression import pin


_MODE = ("permissive", "verified", "corroborated", "verified_or_corroborated", "screened")
_DIRECT_ADMISSION = ("verified_receipt", "corroborated")
_OPERATION = ("read", "relay", "promotion")
_WORKER = "fixture-worker"
_PLAN_FIELDS = {"initial_head", "initial_count", "origins", "verified", "steps"}
_STEP_FIELDS = {"id", "operation", "target", "support"}
_RECEIPT_FIELDS = _STEP_FIELDS | {
    "mode", "prior_head", "prior_count", "status", "reason", "checks", "post_id",
    "closed_head", "closed_count", "read_found",
}
_POST_FIELDS = {"id", "kind", "text", "refs", "facts", "supersedes", "position"}
_EVENT_FIELDS = {"seq", "round", "type", "agent", "data", "prev", "hash"}


def _identifier(value):
    return type(value) is str and bool(value) and value == value.strip()


def _matches_anchor(trace, count, head):
    return (type(count) is int and 0 < count <= len(trace) and type(head) is str
            and trace[count - 1]["hash"] == head)


def _record_post(event, pending):
    data = event["data"]
    if (type(data) is not dict or data.keys() != _POST_FIELDS
            or data["id"] != f"p{event['seq']}" or type(data["text"]) is not str
            or type(data["supersedes"]) is not list
            or any(not _identifier(item) for item in data["supersedes"])):
        raise ValueError("invalid physical Board post")
    pending.append({**data, "round": event["round"]})


def _commit(active, pending):
    for post in pending:
        for removed in post["supersedes"]:
            active.pop(removed, None)
        active[post["id"]] = post
    pending.clear()


def _is_closure(event):
    data = event["data"]
    return (event["type"] == "end_round" and event["agent"] is None
            and type(data) is dict and data.keys() == {"expired", "resolved"}
            and all(type(value) is list for value in data.values()))


def _initial_state(trace):
    active, pending = {}, []
    round_id = 0
    for index, event in enumerate(trace):
        kind = event["type"]
        if (type(event["round"]) is not int or event["round"] != round_id
                or (kind == "init") != (index == 0)):
            raise ValueError("invalid initial Board round sequence")
        if kind == "post":
            _record_post(event, pending)
        elif kind == "end_round":
            if not _is_closure(event):
                raise ValueError("invalid initial Board commit")
            _commit(active, pending)
            round_id += 1
        elif kind not in ("init", "read", "claim", "release"):
            raise ValueError("unexpected initial Board event")
    return active, pending, round_id


def _check_receipt(step, receipt, mode, trace, ordinal, cursor, seen):
    if (type(step) is not dict or step.keys() != _STEP_FIELDS or not _identifier(step["id"])
            or step["id"] in seen or step["operation"] not in _OPERATION or not _identifier(step["target"])
            or type(step["support"]) is not list or any(not _identifier(item) for item in step["support"])):
        raise ValueError(f"invalid or duplicate planned Board step at ordinal {ordinal}")
    seen.add(step["id"])
    if (type(receipt) is not dict or receipt.keys() != _RECEIPT_FIELDS
            or any(receipt[key] != step[key] for key in _STEP_FIELDS) or receipt["mode"] != mode
            or type(receipt["checks"]) is not int or receipt["checks"] < 0
            or (receipt["reason"] is not None and not _identifier(receipt["reason"]))
            or receipt["prior_count"] != cursor
            or not _matches_anchor(trace, receipt["prior_count"], receipt["prior_head"])):
        raise ValueError(f"receipt differs from planned Board step at ordinal {ordinal}")


def _physical_read(receipt, active, event):
    target = receipt["target"]
    found = target in active
    data = event["data"]
    if (receipt["status"] != "read" or receipt["reason"] is not None or receipt["read_found"] is not found
            or receipt["checks"] != 0 or receipt["post_id"] is not None or receipt["support"]
            or event["type"] != "read" or event["agent"] != _WORKER
            or type(data) is not dict or data.keys() != {"item", "n"} or data["item"] != target
            or type(data["n"]) is not int or data["n"] != int(found)):
        raise ValueError("named read does not match its Board receipt or committed visibility")
    return found


def _physical_post(receipt, active, event, pending):
    target = active.get(receipt["target"])
    mode = receipt["mode"]
    corroborated = mode == "corroborated" or (mode == "verified_or_corroborated" and receipt["reason"] == "corroborated")
    support = receipt["support"] if corroborated else []
    expected = {"id": receipt["post_id"], "kind": receipt["operation"],
                "text": target["text"] if target else None,
                "refs": [receipt["target"], *support], "facts": [], "supersedes": [], "position": None}
    if (target is None or any(item not in active for item in support)
            or event["type"] != "post" or event["agent"] != _WORKER
            or event["data"] != expected):
        raise ValueError("admitted dispatch does not match its exact Board post")
    _record_post(event, pending)


def audit(path, plan, receipts, *, mode, expected_plan_pin, expected_terminal_head, expected_events, decide_step=None):
    """Rebuild physical effects, with optional semantic replay on committed state."""
    if (type(plan) is not dict or plan.keys() != _PLAN_FIELDS or pin(plan) != expected_plan_pin
            or mode not in _MODE or type(plan["origins"]) is not dict or type(plan["verified"]) is not dict
            or type(plan["steps"]) is not list or not plan["steps"]):
        raise ValueError("invalid provenance Board plan, mode or independent pin")
    if type(receipts) is not list or len(receipts) != len(plan["steps"]):
        raise ValueError("receipts must cover every planned Board step")

    trace = read_log(path)
    cursor = plan["initial_count"]
    if (len(trace) != expected_events or not _matches_anchor(trace, expected_events, expected_terminal_head)
            or not _matches_anchor(trace, cursor, plan["initial_head"])):
        raise ValueError("Board differs from the independent initial or terminal anchor")
    if any(event.keys() != _EVENT_FIELDS or type(event["seq"]) is not int for event in trace):
        raise ValueError("invalid physical Board event envelope")
    active, pending, round_id = _initial_state(trace[:cursor])
    counts = dict.fromkeys(("reads", "read_hits", "dispatch_attempts", "admitted", "refused", "posts", "committed", "checks"), 0)
    seen = set()
    valid_admissions = _DIRECT_ADMISSION if mode == "verified_or_corroborated" else ("admitted",)
    for ordinal, (step, receipt) in enumerate(zip(plan["steps"], receipts, strict=True)):
        _check_receipt(step, receipt, mode, trace, ordinal, cursor, seen)
        operation, status = receipt["operation"], receipt["status"]
        is_read, admitted = operation == "read", status == "admitted"
        closed = cursor + (2 if is_read or admitted else 1)
        if (receipt["closed_count"] != closed
                or not _matches_anchor(trace, receipt["closed_count"], receipt["closed_head"])):
            raise ValueError("receipt does not match the expected Board segment closure")
        segment = trace[cursor:closed]
        if (any(type(event["round"]) is not int or event["round"] != round_id for event in segment)
                or not _is_closure(segment[-1])):
            raise ValueError("step must end at a single commit in its expected Board round")

        if is_read:
            counts["reads"] += 1
            counts["read_hits"] += _physical_read(receipt, active, segment[0])
        else:
            reason = receipt["reason"]
            if (status not in ("admitted", "refused") or receipt["read_found"] is not None
                    or reason is None or admitted != (reason in valid_admissions)
                    or (not admitted and reason in ("admitted", *_DIRECT_ADMISSION))
                    or (not admitted and receipt["post_id"] is not None)):
                raise ValueError("invalid dispatch status or side-effect fields")
            if decide_step is not None:
                outcome = decide_step(active, step)
                if outcome != {"admitted": admitted, "reason": reason, "checks": receipt["checks"]}:
                    raise ValueError("dispatch decision or check count differs from policy replay")
            counts["dispatch_attempts"] += 1
            counts[status] += 1
            counts["checks"] += receipt["checks"]
            if admitted:
                _physical_post(receipt, active, segment[0], pending)
                counts["posts"] += 1

        _commit(active, pending)
        if admitted and not is_read:
            if receipt["post_id"] not in active:
                raise ValueError("posted dispatch did not survive its physical Board commit")
            counts["committed"] += 1
        cursor = closed
        round_id += 1
    if cursor != len(trace):
        raise ValueError("Board contains unaccounted events after the final receipt")
    return counts
