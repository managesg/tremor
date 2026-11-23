"""Verify one Spark GPU reservation and optional settlement without modifying the ledger."""

import argparse
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import stat

from lab.spark_calibration_guard import CONTAINER_ID, FLOOR_KIB, WORKER_LOG_LIMIT

CAPTURE_FIELDS = {
    "start": {"admission_id", "container", "worker_log_limit"},
    "decision": {"admission_id", "container", "attachment_pid", "watchdog_decision", "sample_kib"},
    "outcome": {"admission_id", "container", "attachment_pid", "stop", "min_memavailable_kib"},
    "terminal": {"admission_id", "container", "attachment_pid", "attachment_returncode", "attachment_status",
                 "cleanup_confirmed", "container_cleanup_confirmed", "observed_wall_seconds", "worker_output"},
}
EXACT_CAPTURE_FIELDS = {
    "start": CAPTURE_FIELDS["start"],
    "created": {"admission_id", "container", "container_id"},
    "decision": CAPTURE_FIELDS["decision"] | {"container_id"},
    "outcome": CAPTURE_FIELDS["outcome"] | {"container_id"},
    "terminal": CAPTURE_FIELDS["terminal"] | {"container_id"},
}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _number(value, field):
    _require(type(value) in (int, Decimal), f"{field} must be a JSON number")
    value = Decimal(value)
    _require(value.is_finite() and value >= 0, f"invalid {field}")
    return value


def charge_for_wall_time(seconds):
    """Round conservative single-GPU start-through-cleanup wall time to a micro-hour."""
    numerator, denominator = _number(seconds, "observed_wall_seconds").as_integer_ratio()
    units, remainder = divmod(numerator * 1_000_000, denominator * 3600)
    return Decimal((0, Decimal(units + bool(remainder)).as_tuple().digits, -6))


def _guard_measurement(admission_id, outcome, terminal, decision, require_attachment_proof):
    if terminal is None:
        return "missing_terminal", None
    _require(terminal["admission_id"] == admission_id, "terminal receipt admission mismatch")
    _require(isinstance(terminal["container"], str) and terminal["container"].strip(),
             "terminal receipt has no container")
    _require(type(terminal["cleanup_confirmed"]) is bool, "invalid cleanup confirmation")
    attachment_fields = {"attachment_status", "attachment_pid", "attachment_returncode", "container_cleanup_confirmed"}
    fields = terminal.keys() & attachment_fields
    if fields:
        _require(fields == attachment_fields, "incomplete attachment cleanup receipt")
        attachment = terminal["attachment_status"]
        container_clean = terminal["container_cleanup_confirmed"]
        pid, rc = terminal["attachment_pid"], terminal["attachment_returncode"]
        _require(attachment in ("not_started", "reaped", "unconfirmed") and type(container_clean) is bool,
                 "invalid attachment or container cleanup state")
        _require((attachment == "reaped" and type(pid) is int and pid > 0 and type(rc) is int)
                 or (attachment == "not_started" and pid is None and rc is None)
                 or (attachment == "unconfirmed" and (pid is None or (type(pid) is int and pid > 0)) and rc is None),
                 "invalid attachment PID or exit code")
        _require(terminal["cleanup_confirmed"] is (container_clean and attachment != "unconfirmed"),
                 "combined cleanup confirmation differs from its components")
    elif require_attachment_proof:
        return "missing_attachment_proof", None
    if decision is not None:
        _require(decision["admission_id"] == admission_id and decision["container"] == terminal["container"],
                 "watchdog decision identity differs from terminal")
        if fields:
            _require(type(decision.get("attachment_pid")) is int and decision["attachment_pid"] == pid,
                     "watchdog decision attachment PID differs from terminal")
        _require(decision["watchdog_decision"] in ("memory_floor", "wall_limit")
                 and type(decision["sample_kib"]) is int and decision["sample_kib"] >= 0,
                 "invalid watchdog decision")
        if fields:
            _require((decision["sample_kib"] <= FLOOR_KIB) == (decision["watchdog_decision"] == "memory_floor"),
                     "watchdog decision conflicts with memory floor")
        _require(outcome is None or (outcome["stop"], outcome["min_memavailable_kib"]) ==
                 (decision["watchdog_decision"], decision["sample_kib"]), "watchdog decision conflicts with outcome")
    measured = charge_for_wall_time(terminal["observed_wall_seconds"])
    if not terminal["cleanup_confirmed"]:
        return "cleanup_unconfirmed", None
    if terminal.get("worker_output") and terminal["worker_output"]["limit_reached"]:
        return "worker_output_limit", None
    if outcome is None:
        return "missing_outcome", None
    stop = outcome["stop"]
    _require(stop in ("completed", "memory_floor", "wall_limit", "child_error"), "unknown guard stop reason")
    minimum = outcome["min_memavailable_kib"]
    _require(type(minimum) is int and minimum >= 0, "invalid guard memory sample")
    if fields:
        _require(outcome.get("admission_id") == admission_id and outcome.get("container") == terminal["container"],
                 "guard outcome identity differs from terminal")
        _require(type(outcome.get("attachment_pid")) is int and outcome["attachment_pid"] == pid,
                 "guard outcome attachment PID differs from terminal")
        _require(terminal["attachment_status"] == "reaped" and (stop != "completed" or rc == 0),
                 "outcome has no eligible attachment exit")
        _require(stop != "child_error" or rc != 0, "child error cannot have a zero exit")
        _require((minimum <= FLOOR_KIB) == (stop == "memory_floor"), "guard outcome conflicts with memory floor")
        _require(stop not in ("memory_floor", "wall_limit") or decision is not None,
                 "watchdog stop lacks the pre-termination decision")
    _require(measured > 0, "guard outcome requires a positive start-through-cleanup interval")
    return stop, measured


def audit(records, *, outcome=None, terminal=None, decision=None, require_attachment_proof=False):
    """Check the Spark reserve/settle arithmetic for one admission, or report its full hold."""
    _require(1 <= len(records) <= 2, "expected one reserve and at most one settlement")
    reserve = records[0]
    _require(reserve["event"] == "reserve", "the first record must be a reserve")
    identifier, batch = reserve["admission_id"], reserve["batch"]
    _require(all(isinstance(value, str) and value.strip() for value in (identifier, batch)),
             "missing admission or batch identifier")
    ceiling = _number(reserve["program_ceiling_gpu_hours"], "program ceiling")
    historical = _number(reserve["historical_t7_hold_gpu_hours"], "historical hold")
    reserved = _number(reserve["reserved_gpu_hours"], "GPU reservation")
    program_before = _number(reserve["available_program_before_gpu_hours"], "program balance before reserve")
    joint_before = _number(reserve["available_r2_r3_before_gpu_hours"], "R2/R3 balance before reserve")
    _require(0 < reserved <= min(program_before, joint_before) and program_before <= ceiling - historical,
             "reservation exceeds an available balance")
    program_after, joint_after = program_before - reserved, joint_before - reserved
    _require(program_after == _number(reserve["available_program_after_gpu_hours"], "program balance after reserve")
             and joint_after == _number(reserve["available_r2_r3_after_gpu_hours"], "R2/R3 balance after reserve"),
             "reservation balance mismatch")

    settlement = records[1] if len(records) == 2 else None
    if settlement is not None:
        _require(settlement["event"] == "settle" and settlement["admission_id"] == identifier
                 and settlement["batch"] == batch, "settlement must match the only reserve")
        _require(outcome is None or outcome == settlement["outcome"], "guard outcome differs from settlement")
        _require(terminal is None or terminal == settlement["terminal"], "guard terminal differs from settlement")
        outcome, terminal = settlement["outcome"], settlement["terminal"]

    reason, measured = _guard_measurement(identifier, outcome, terminal, decision, require_attachment_proof)
    if reason == "completed" and measured > reserved:
        reason = "reservation_overrun"
    report = {
        "admission_id": identifier, "status": "held", "reason": reason,
        "measured_gpu_hours": measured, "held_gpu_hours": reserved,
        "available_program_gpu_hours": program_after, "available_r2_r3_gpu_hours": joint_after,
    }
    if decision is not None:
        report["watchdog_decision"] = decision["watchdog_decision"]
    if settlement is None:
        if reason == "completed":
            report["reason"] = "missing_settlement"
        return report

    _require(reason == "completed", "settlement requires clean completion within reserve and confirmed cleanup")
    returned = reserved - measured
    for field, expected in {
        "actual_charged_gpu_hours": measured,
        "returned_reservation_gpu_hours": returned,
        "available_program_gpu_hours": program_after + returned,
        "available_r2_r3_gpu_hours": joint_after + returned,
    }.items():
        _require(_number(settlement[field], field) == expected, f"settlement mismatch for {field}")
        report[field] = expected
    report.update(status="verified_settlement", held_gpu_hours=Decimal(0))
    return report


def _read_guard_log(path):
    raw = path.read_bytes()
    rows = [json.loads(line, parse_float=Decimal) for line in raw.splitlines() if line.startswith(b"{")]
    keys = ("watchdog_decision", "stop", "cleanup_confirmed")
    indexed = [[(i, row) for i, row in enumerate(rows) if key in row] for key in keys]
    _require(all(len(group) <= 1 for group in indexed), "multiple guard receipts for one admission")
    positions = [group[0][0] for group in indexed if group]
    _require(positions == sorted(set(positions)), "guard receipts are out of order")
    decision, outcome, terminal = (group[0][1] if group else None for group in indexed)
    return outcome, terminal, decision, hashlib.sha256(raw).hexdigest()


def _private_capture_bytes(path, limit):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        metadata = os.fstat(stream.fileno())
        _require(stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1 and metadata.st_mode & 0o077 == 0,
                 f"capture requires a private single-link regular file: {path.name}")
        _require(metadata.st_size <= limit, f"capture exceeds its size limit: {path.name}")
        raw = stream.read(limit + 1)
        _require(len(raw) == metadata.st_size, f"capture changed size while reading: {path.name}")
        return raw


def _unique_object(pairs):
    result = dict(pairs)
    _require(len(result) == len(pairs), "duplicate host capture JSON member")
    return result


def _read_host_capture(path, expected, *, exact_container=False, admission_id=None):
    raw = _private_capture_bytes(path, 16 * 1024)
    digest = hashlib.sha256(raw).hexdigest()
    _require(digest == expected, "external host capture digest mismatch")
    _require(raw.endswith(b"\n"), "host capture ended with an incomplete record")
    events = {}
    version = None
    for sequence, line in enumerate(raw.splitlines()):
        row = json.loads(line, parse_float=Decimal, object_pairs_hook=_unique_object)
        _require(type(row) is dict and row.keys() == {"version", "sequence", "event", "record"}
                 and type(row["version"]) is int and row["version"] in (1, 2)
                 and type(row["sequence"]) is int and row["sequence"] == sequence, "invalid host capture envelope")
        if version is None:
            version = row["version"]
            _require(not exact_container or version == 2, "exact container identity requires a version 2 capture")
            fields = EXACT_CAPTURE_FIELDS if version == 2 else CAPTURE_FIELDS
        _require(row["version"] == version, "host capture mixes envelope versions")
        event, record = row["event"], row["record"]
        _require(event in fields and event not in events and type(record) is dict
                 and record.keys() == fields[event], "unknown, duplicate or malformed host capture event")
        events[event] = record
    _require("start" in events and list(events) == [event for event in fields if event in events],
             "host capture events are out of order")
    start = events["start"]
    _require(admission_id is None or start["admission_id"] == admission_id, "host capture admission differs from reserve")
    _require(type(start["worker_log_limit"]) is int and start["worker_log_limit"] == WORKER_LOG_LIMIT,
             "host capture worker limit differs from the watcher")
    _require(all((record["admission_id"], record["container"]) == (start["admission_id"], start["container"])
                 for record in events.values()), "host capture mixes admission or container identity")
    terminal = events.get("terminal")
    if version == 2:
        created = events.get("created")
        if created is None:
            _require("decision" not in events and "outcome" not in events, "unbound capture records a worker action")
            _require(terminal is None or (terminal["container_id"] is None
                     and terminal["container_cleanup_confirmed"] is False
                     and terminal["attachment_status"] == "not_started"),
                     "unbound capture cannot claim attachment or container cleanup")
        else:
            identity = created["container_id"]
            _require(isinstance(identity, str) and CONTAINER_ID.fullmatch(identity),
                     "invalid full Docker container ID")
            _require(all(record["container_id"] == identity for event, record in events.items() if event != "start"),
                     "host receipt container ID differs from create")
    if terminal is not None:
        export = terminal["worker_output"]
        if terminal["attachment_status"] == "unconfirmed":
            _require(export is None, "unreaped attachment cannot attest worker output")
        else:
            path = path.with_name("worker.log")
            worker = _private_capture_bytes(path, WORKER_LOG_LIMIT)
            size = len(worker)
            _require(type(export) is dict and export.keys() == {"bytes", "sha256", "limit_reached"}
                     and type(export["bytes"]) is int and export["bytes"] == size <= WORKER_LOG_LIMIT
                     and export["limit_reached"] is (size == WORKER_LOG_LIMIT),
                     "worker evidence size or capture-limit receipt differs")
            _require(hashlib.sha256(worker).hexdigest() == export["sha256"],
                     "worker evidence digest differs from the host terminal")
    return events.get("outcome"), terminal, events.get("decision"), digest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger", type=Path, help="one admission's reserve and optional settlement JSONL")
    parser.add_argument("--guard-log", type=Path, help="optional independent source for the guard receipts")
    parser.add_argument("--require-attachment-proof", action="store_true",
                        help="require the new attachment and container cleanup receipt in the guard log")
    parser.add_argument("--host-capture-sha256", help="independently recorded pin of a separate guard.jsonl capture")
    parser.add_argument("--require-container-identity", action="store_true", help="require version 2 host evidence")
    args = parser.parse_args(argv)
    if (args.require_attachment_proof or args.host_capture_sha256 is not None) and args.guard_log is None:
        parser.error("attachment or host capture verification requires --guard-log")
    if args.require_container_identity and args.host_capture_sha256 is None:
        parser.error("exact container identity requires --host-capture-sha256")
    try:
        records = [json.loads(line, parse_float=Decimal) for line in args.ledger.read_bytes().splitlines()]
        if args.guard_log is None:
            report = audit(records)
        else:
            if args.host_capture_sha256 is not None:
                _require(bool(records), "missing reserve record")
                outcome, terminal, decision, digest = _read_host_capture(
                    args.guard_log, args.host_capture_sha256, exact_container=args.require_container_identity,
                    admission_id=records[0]["admission_id"],
                )
            else:
                outcome, terminal, decision, digest = _read_guard_log(args.guard_log)
            if len(records) == 2:
                _require(outcome is not None and terminal is not None, "guard log lacks settlement receipts")
                _require(records[1]["run_log_sha256"] == digest, "guard log digest mismatch")
            report = audit(records, outcome=outcome, terminal=terminal, decision=decision,
                           require_attachment_proof=args.require_attachment_proof or args.host_capture_sha256 is not None)
            report["guard_log_sha256"] = digest
    except (AttributeError, KeyError, OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(report, default=str, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
