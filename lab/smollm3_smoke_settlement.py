"""Verify one pinned replication smoke reservation and optional settlement offline."""

import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re

from lab import r3_resource_audit as guard

BATCH = "spark-smollm3-3b-technical-smoke"
ALLOCATION = "spark-replication"
IDENTITY = {"event", "admission_id", "batch", "allocation"}
RESERVE = IDENTITY | {
    "program_ceiling_gpu_hours", "historical_t7_hold_gpu_hours", "reserved_gpu_hours",
    "available_program_before_gpu_hours", "available_replication_before_gpu_hours",
    "available_program_after_gpu_hours", "available_replication_after_gpu_hours",
}
SETTLE = IDENTITY | {
    "reservation_sha256", "host_capture_sha256", "actual_charged_gpu_hours", "returned_reservation_gpu_hours",
    "available_program_gpu_hours", "available_replication_gpu_hours",
}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _pinned(path, digest):
    raw = guard._private_capture_bytes(Path(path), 16 * 1024)
    _require(hashlib.sha256(raw).hexdigest() == digest, f"external digest mismatch: {Path(path).name}")
    return json.loads(raw, parse_float=Decimal, object_pairs_hook=guard._unique_object)


def _identity(record, fields, event):
    _require(type(record) is dict and record.keys() == fields and record["event"] == event
             and record["batch"] == BATCH and record["allocation"] == ALLOCATION,
             f"invalid replication {event} record")
    identifier = record["admission_id"]
    _require(type(identifier) is str and re.fullmatch(r"[A-Za-z0-9_-]{1,80}", identifier),
             "invalid replication admission ID")
    return identifier


def _number(record, field):
    amount = guard._number(record[field], field)
    _require(amount <= 70 and amount == amount.quantize(Decimal("0.000001")),
             f"{field} exceeds the program or micro-hour precision")
    return amount


def _has_created_inspection(host_capture, created):
    try:
        view = _pinned(Path(host_capture).with_name("prestart-inspect.json"), created["prestart_inspect_sha256"])
    except FileNotFoundError:
        return False
    _require(type(view) is dict and view.get("id") == created["container_id"]
             and view.get("name") == "/" + created["container"]
             and view.get("attempt") == created["container"] and view.get("state") == "created",
             "pre-start inspection does not prove the exact created container")
    return True


def verify(reservation, *, reservation_sha256, host_capture=None, host_capture_sha256=None,
           worker_log_sha256=None, settlement=None, settlement_sha256=None):
    """Verify exact receipts, holding the reservation until clean settlement is proven."""
    _require((host_capture is None) == (host_capture_sha256 is None)
             and (settlement is None) == (settlement_sha256 is None),
             "each optional receipt needs its independent path and digest")
    _require(worker_log_sha256 is None or host_capture is not None, "worker pin requires a host capture")
    reserve = _pinned(reservation, reservation_sha256)
    identifier = _identity(reserve, RESERVE, "reserve")
    ceiling = _number(reserve, "program_ceiling_gpu_hours")
    historical_hold = _number(reserve, "historical_t7_hold_gpu_hours")
    reserved = _number(reserve, "reserved_gpu_hours")
    program = _number(reserve, "available_program_before_gpu_hours")
    replication = _number(reserve, "available_replication_before_gpu_hours")
    _require(ceiling == 70 and 0 < reserved <= replication <= program <= ceiling - historical_hold,
             "reservation exceeds the reconciled replication or program balance")
    program_after, replication_after = program - reserved, replication - reserved
    _require(_number(reserve, "available_program_after_gpu_hours") == program_after
             and _number(reserve, "available_replication_after_gpu_hours") == replication_after,
             "replication reservation balance mismatch")

    reason, measured = "missing_host_capture", None
    if host_capture is not None:
        outcome, terminal, decision, _, created = guard._read_host_capture(
            Path(host_capture), host_capture_sha256, exact_container=True, admission_id=identifier, include_created=True,
        )
        reason, measured = guard._guard_measurement(identifier, outcome, terminal, decision, True)
        worker = terminal.get("worker_output") if terminal is not None else None
        if worker_log_sha256 is not None and worker is not None:
            _require(worker["sha256"] == worker_log_sha256, "external worker log digest mismatch")
        if reason == "completed":
            if measured > reserved:
                reason = "reservation_overrun"
            elif not worker or worker["bytes"] == 0 or worker_log_sha256 is None:
                reason = "missing_independent_worker_evidence"
        elif (reason == "missing_outcome" and decision is None and created.get("prestart_inspect_sha256")
              and terminal["attachment_status"] == "not_started" and terminal["observed_wall_seconds"] == 0
              and worker["bytes"] == 0 and worker_log_sha256 is not None):
            if _has_created_inspection(host_capture, created):
                reason, measured = "verified_no_attachment", Decimal(0)
            else:
                reason = "missing_prestart_inspection"

    report = {
        "admission_id": identifier, "batch": BATCH, "allocation": ALLOCATION,
        "status": "held", "reason": {"completed": "missing_settlement",
                                    "verified_no_attachment": "missing_cancellation"}.get(reason, reason),
        "reservation_sha256": reservation_sha256, "host_capture_sha256": host_capture_sha256,
        "measured_gpu_hours": measured, "held_gpu_hours": reserved,
        "available_program_gpu_hours": program_after, "available_replication_gpu_hours": replication_after,
    }
    if settlement is None:
        return report

    _require(reason in ("completed", "verified_no_attachment"), f"cannot release an uncertain reservation: {reason}")
    event = "settle" if reason == "completed" else "cancel"
    settled = _pinned(settlement, settlement_sha256)
    _require(_identity(settled, SETTLE, event) == identifier
             and settled["reservation_sha256"] == reservation_sha256
             and host_capture_sha256 is not None and settled["host_capture_sha256"] == host_capture_sha256,
             "settlement does not bind the reviewed host capture and reservation identity")
    returned = reserved - measured
    amounts = {
        "actual_charged_gpu_hours": measured, "returned_reservation_gpu_hours": returned,
        "available_program_gpu_hours": program_after + returned,
        "available_replication_gpu_hours": replication_after + returned,
    }
    for field, expected in amounts.items():
        _require(_number(settled, field) == expected, f"settlement mismatch for {field}")
    status = "verified_settlement" if event == "settle" else "verified_unused_reservation_return"
    return {**report, **amounts, "status": status, "reason": reason,
            "held_gpu_hours": Decimal(0), "settlement_sha256": settlement_sha256,
            "worker_log_sha256": worker_log_sha256}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reservation", type=Path)
    parser.add_argument("--reservation-sha256", required=True)
    parser.add_argument("--host-capture", type=Path)
    parser.add_argument("--host-capture-sha256")
    parser.add_argument("--worker-log-sha256")
    parser.add_argument("--settlement", type=Path)
    parser.add_argument("--settlement-sha256")
    args = parser.parse_args()
    try:
        report = verify(**vars(args))
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(report, default=str, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
