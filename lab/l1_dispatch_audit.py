"""Audit the exact ordered dispatch and cost receipts of a scripted L1 plan."""

import hashlib
import math
from pathlib import Path
import random

from lab import adapter_lineage, l1_verification_allocation as allocation


PLAN_FIELDS = (
    "mode budget measurement_spent allocated unused scores choices calibration_sha256 claim_inventory_sha256"
)
JOURNAL_FIELDS = {
    "plan": "seq event plan_sha256",
    "start": "seq event attempt_index attempt_sha256",
    "answer": "seq event attempt_index attempt_sha256 result used_units",
    "failure": "seq event attempt_index attempt_sha256 reason used_units",
    "terminal": "seq event status reason",
}


def _fields(record, names):
    if type(record) is not dict or record.keys() != set(names.split()):
        raise ValueError("unexpected L1 dispatch fields")


def _units(value):
    if type(value) is not int or value < 0:
        raise ValueError("dispatch cost must be a nonnegative integer")
    return value


def _plan_choices(plan, claims):
    mode = plan.get("mode")
    if mode not in allocation.MODES + allocation.ADDITIONAL_CHECK_MODES:
        raise ValueError("unknown L1 dispatch mode")
    additional = mode in allocation.ADDITIONAL_CHECK_MODES
    _fields(plan, PLAN_FIELDS + (" provenance" if additional else ""))
    budget, measurement, allocated, unused = (_units(plan[name]) for name in ("budget", "measurement_spent",
                                                                            "allocated", "unused"))
    if bool(measurement) != (mode in allocation.MEASURED_MODES):
        raise ValueError("allocation measurement cost does not reconcile")
    if measurement:
        adapter_lineage._digest(plan["calibration_sha256"], 64)
    elif plan["calibration_sha256"] is not None:
        raise ValueError("unmeasured plan contains a calibration pin")
    scores = plan["scores"]
    expected = ({claim.stratum for claim in claims} if mode in ("overdispersion", "disagreement", "proportional")
                else {claim.identifier for claim in claims} if mode == "pilot_predictor" else set())
    if (type(scores) is not dict or scores.keys() != expected
            or any(type(score) not in (int, float) or (type(score) is float and not math.isfinite(score))
                   for score in scores.values())):
        raise ValueError("invalid allocation score inventory")
    if additional:
        provenance = plan["provenance"]
        extra = {"random": " order_seed", "pilot_predictor": " fitted_coefficients"}.get(mode, "")
        _fields(provenance, "features_sha256" + extra)
        adapter_lineage._digest(provenance["features_sha256"], 64)
        if mode == "random" and type(provenance["order_seed"]) is not int:
            raise ValueError("random allocation needs its integer order seed")
    action, cost = ("retry_pair", allocation.RETRIES * allocation.RETRY_COST) if mode == "majority_retry" else (
        "check", allocation.CHECK_COST
    )
    choices = plan["choices"]
    if (type(choices) is not list or measurement > budget
            or len(choices) != min(len(claims), (budget - measurement) // cost)
            or allocated != measurement + len(choices) * cost or allocated + unused != budget):
        raise ValueError("allocation budget or planned cost does not reconcile")

    by_id = {claim.identifier: claim for claim in claims}
    ordered_ids = []
    for choice in choices:
        _fields(choice, "claim_id stratum action cost")
        identifier = choice["claim_id"]
        if (type(identifier) is not str or identifier not in by_id or choice["stratum"] != by_id[identifier].stratum
                or choice["action"] != action or _units(choice["cost"]) != cost):
            raise ValueError("choice differs from the claim inventory or dispatch cost")
        ordered_ids.append(identifier)
    if len(ordered_ids) != len(set(ordered_ids)):
        raise ValueError("duplicate scheduled claim choices")

    order = list(claims)
    if mode in ("overdispersion", "disagreement"):
        order.sort(key=lambda claim: -scores[claim.stratum])
    elif mode == "random":
        random.Random(plan["provenance"]["order_seed"]).shuffle(order)
    # Feature-ranked choices already have an external order pin; their input rows are not supplied here.
    if mode in allocation.MODES + ("random",):
        if ordered_ids != [claim.identifier for claim in order[:len(ordered_ids)]]:
            raise ValueError("choice order differs from the pinned allocation mode")
    return action, ordered_ids


def attempts(plan, claims, *, plan_sha256):
    """Expand the pinned plan into indexed check and retry starts."""
    if type(plan) is not dict or allocation.digest(plan) != adapter_lineage._digest(plan_sha256, 64):
        raise ValueError("allocation plan digest mismatch")
    claims = tuple(claims)
    if allocation.digest(allocation._claim_inventory(claims)) != plan.get("claim_inventory_sha256"):
        raise ValueError("allocation claim inventory digest mismatch")
    action, ordered_ids = _plan_choices(plan, claims)
    expanded = []
    count, units = (allocation.RETRIES, allocation.RETRY_COST) if action == "retry_pair" else (1, allocation.CHECK_COST)
    for identifier in ordered_ids:
        for ordinal in range(1, count + 1):
            expanded.append({"attempt_index": len(expanded), "claim_id": identifier,
                             "action": "retry" if action == "retry_pair" else "check", "ordinal": ordinal, "units": units})
    return expanded


def _event(record, seq):
    kind = record.get("event")
    if type(kind) is not str or kind not in JOURNAL_FIELDS:
        raise ValueError("unknown L1 dispatch journal event")
    _fields(record, JOURNAL_FIELDS[kind])
    if type(record["seq"]) is not int or record["seq"] != seq:
        raise ValueError("dispatch journal sequence differs")
    return kind


def _bind(record, planned, plan_sha256, index):
    expected = allocation.digest({"plan_sha256": plan_sha256, "attempt": planned[index]})
    if (type(record["attempt_index"]) is not int or record["attempt_index"] != index
            or record["attempt_sha256"] != expected):
        raise ValueError("dispatch does not match its exact planned attempt")


def audit(plan, claims, journal, *, plan_sha256, journal_sha256):
    """Verify a serial journal and preserve unresolved attempts and unknown charges."""
    planned = attempts(plan, claims, plan_sha256=plan_sha256)
    path = Path(journal)
    raw = path.read_bytes()
    adapter_lineage._match(path, hashlib.sha256(raw).hexdigest(), journal_sha256)
    lines = raw.split(b"\n")
    if len(lines) < 3 or lines[-1] or len(lines) > 2 * len(planned) + 3:
        raise ValueError("dispatch journal needs a complete plan and terminal envelope")
    rows = [{**attempt, "status": "unstarted", "result": None, "used_units": None} for attempt in planned]
    opened, started, terminal = None, 0, None
    for seq, line in enumerate(lines[:-1]):
        record = adapter_lineage._strict_object(line, path)
        kind = _event(record, seq)
        if seq == 0:
            if kind != "plan" or record["plan_sha256"] != plan_sha256:
                raise ValueError("dispatch journal does not start with its pinned plan")
        elif kind == "terminal":
            if seq != len(lines) - 2:
                raise ValueError("dispatch journal contains records after terminal")
            terminal = (record["status"], record["reason"])
        elif kind == "start":
            if opened is not None or started == len(planned):
                raise ValueError("dispatch starts must be a serial prefix of the plan")
            _bind(record, planned, plan_sha256, started)
            opened = started
            rows[opened]["status"] = "open"
            started += 1
        elif kind in ("answer", "failure"):
            if opened is None:
                raise ValueError("dispatch settlement lacks an open attempt")
            _bind(record, planned, plan_sha256, opened)
            used = record["used_units"]
            if kind == "answer":
                if type(record["result"]) is not bool or used is None:
                    raise ValueError("answered attempts require a Boolean result and known cost")
                rows[opened].update(status="answered", result=record["result"], used_units=used)
            else:
                if record["reason"] != "scripted_failure":
                    raise ValueError("unsupported dispatch failure reason")
                rows[opened].update(status="failed", used_units=used)
            if used is not None and _units(used) > planned[opened]["units"]:
                raise ValueError("used units exceed the planned attempt cost")
            opened = None
        else:
            raise ValueError("dispatch journal repeats its plan")
    if terminal is None:
        raise ValueError("dispatch journal lacks a terminal record")
    status, reason = terminal
    if status == "completed":
        if reason is not None or opened is not None or started != len(planned):
            raise ValueError("completed dispatch requires every planned attempt to settle")
    elif status != "stopped" or reason not in ("operator_limit", "wall_limit", "scripted_failure"):
        raise ValueError("invalid dispatch terminal status or reason")
    elif reason == "scripted_failure" and (not started or rows[started - 1]["status"] != "failed"):
        raise ValueError("scripted failure stop requires a final recorded failure")

    return {
        "status": status, "reason": reason, "plan_sha256": plan_sha256, "journal_sha256": journal_sha256,
        "planned": len(planned), "started": started,
        "answered": sum(row["status"] == "answered" for row in rows),
        "failed": sum(row["status"] == "failed" for row in rows), "open": int(opened is not None),
        "unstarted": len(planned) - started, "attempts": rows,
        "measurement_units_planned": plan["measurement_spent"],
        "planned_dispatch_units": sum(row["units"] for row in planned),
        "started_planned_units": sum(row["units"] for row in planned[:started]),
        "known_actual_units": sum(row["used_units"] for row in rows if row["used_units"] is not None),
        "unknown_actual_count": sum(row["used_units"] is None for row in rows[:started]),
        "scientific_rate": None,
    }
