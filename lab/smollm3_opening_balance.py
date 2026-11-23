"""Verify the first SmolLM3 smoke proposal against a pinned Spark ledger cut."""

import argparse
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path

from lab import r3_resource_audit as accounting
from lab import smollm3_smoke_admission as admission
from lab import smollm3_smoke_settlement as smoke
from lab import spark_calibration_guard as spark

SCHEMA = "tremor.smollm3_first_smoke_opening_balance.v1"
PLACEMENT_FIELDS = {
    "schema", "cut_utc", "ledger_sha256", "r2_guard_sha256", "admission_sha256", "reserve_sha256",
    "admission_id", "batch", "allocation", "available_replication_before_gpu_hours",
}


def _require(condition, error):
    if not condition:
        raise ValueError(error)


def _invalid_constant(value):
    raise ValueError(f"invalid accounting JSON constant: {value}")


def _json(raw):
    return json.loads(raw, parse_float=Decimal, parse_constant=_invalid_constant,
                      object_pairs_hook=accounting._unique_object)


def _r2_balance(ledger_path, r2_guard_path, *, ledger_sha256, r2_guard_sha256, cut):
    raw = Path(ledger_path).read_bytes()
    _require(sha256(raw).hexdigest() == ledger_sha256, "Spark ledger cut digest mismatch")
    records = [_json(row) for row in raw.splitlines()]
    _require(len(records) == 2 and all(type(row) is dict for row in records),
             "first-smoke reconciliation requires an R2-only ledger cut")
    reserve, settle = records
    _require(reserve["event"] == "reserve" and settle["event"] == "settle"
             and reserve["batch"] == settle["batch"] == spark.BATCH,
             "first-smoke reconciliation requires the exact R2 reserve and settlement")
    _require(admission._timestamp(reserve["utc"]) <= admission._timestamp(settle["utc"]) <= cut,
             "R2 ledger chronology exceeds the declared cut")
    outcome, terminal, decision, digest = accounting._read_guard_log(Path(r2_guard_path))
    _require(digest == settle["run_log_sha256"] == r2_guard_sha256 and outcome is not None and terminal is not None,
             "exact R2 guard evidence does not bind the settled ledger cut")
    report = accounting.audit(records, outcome=outcome, terminal=terminal, decision=decision)
    _require(report["status"] == "verified_settlement", "R2 ledger cut did not settle")
    return {
        "admission_id": report["admission_id"],
        "program_ceiling_gpu_hours": smoke._number(reserve, "program_ceiling_gpu_hours"),
        "historical_t7_hold_gpu_hours": smoke._number(reserve, "historical_t7_hold_gpu_hours"),
        "available_program_gpu_hours": report["available_program_gpu_hours"],
        "actual_charged_gpu_hours": report["actual_charged_gpu_hours"],
    }


def verify(ledger_path, r2_guard_path, placement_path, admission_path, reserve_path, *,
           ledger_sha256, r2_guard_sha256, placement_sha256, admission_sha256, reserve_sha256, cut_utc):
    """Compare separately pinned receipts at the declared cut without changing balances."""
    cut = admission._timestamp(cut_utc)
    raw = accounting._private_capture_bytes(Path(placement_path), 16 * 1024)
    _require(sha256(raw).hexdigest() == placement_sha256, "replication placement digest mismatch")
    placement = _json(raw)
    _require(type(placement) is dict and placement.keys() == PLACEMENT_FIELDS,
             "unexpected opening placement fields")
    for field, expected in {
        "schema": SCHEMA, "cut_utc": cut_utc, "ledger_sha256": ledger_sha256,
        "r2_guard_sha256": r2_guard_sha256, "admission_sha256": admission_sha256,
        "reserve_sha256": reserve_sha256, "batch": smoke.BATCH, "allocation": smoke.ALLOCATION,
    }.items():
        _require(placement[field] == expected, f"opening placement differs from pinned {field}")

    r2 = _r2_balance(ledger_path, r2_guard_path, ledger_sha256=ledger_sha256,
                     r2_guard_sha256=r2_guard_sha256, cut=cut)
    candidate = admission.verify(admission_path, admission_sha256=admission_sha256, now=cut)
    reserve = smoke._pinned(reserve_path, reserve_sha256)
    verification = smoke.verify(reserve_path, reservation_sha256=reserve_sha256)
    identifier = verification["admission_id"]
    _require(identifier == candidate["admission_id"] == placement["admission_id"]
             and identifier != r2["admission_id"] and candidate["reservation_sha256"] == reserve_sha256
             and verification["held_gpu_hours"] == admission.RESERVED_GPU_HOURS,
             "replication opening placement crosses an admission or reserved amount")

    expected_opening = {
        "program_ceiling_gpu_hours": r2["program_ceiling_gpu_hours"],
        "historical_t7_hold_gpu_hours": r2["historical_t7_hold_gpu_hours"],
        "available_program_before_gpu_hours": r2["available_program_gpu_hours"],
        "available_replication_before_gpu_hours": smoke._number(placement, "available_replication_before_gpu_hours"),
    }
    for field, expected in expected_opening.items():
        _require(smoke._number(reserve, field) == expected, f"replication reserve differs from opening {field}")
    return {
        "evidence": "verified_first_smoke_opening_at_supplied_cut",
        "cut_utc": cut_utc,
        "ledger_sha256": ledger_sha256,
        "r2_guard_sha256": r2_guard_sha256,
        "placement_sha256": placement_sha256,
        "admission_sha256": admission_sha256,
        "reserve_sha256": reserve_sha256,
        "admission_id": identifier,
        "r2": r2,
        "opening": expected_opening,
        "projected_program_gpu_hours_after_reserve": verification["available_program_gpu_hours"],
        "projected_replication_gpu_hours_after_reserve": verification["available_replication_gpu_hours"],
        "ledger_changed": False,
        "live_head_verified": False,
        "authorizes_launch": False,
    }


def verify_for_launch(ledger, guard, placement, placement_pin, *, receipt, admission_pin,
                      reservation, reservation_pin, now):
    """Bind the launch to an independently placed first-smoke reservation."""
    document = smoke._pinned(placement, placement_pin)
    _require(type(document) is dict and document.keys() == PLACEMENT_FIELDS,
             "unexpected opening placement fields")
    cut = document["cut_utc"]
    _require(admission._timestamp(cut) <= now, "opening ledger cut is after the launch preflight")
    report = verify(
        ledger, guard, placement, receipt, reservation,
        ledger_sha256=document["ledger_sha256"], r2_guard_sha256=document["r2_guard_sha256"],
        placement_sha256=placement_pin, admission_sha256=admission_pin,
        reserve_sha256=reservation_pin, cut_utc=cut,
    )
    _require(report["opening"]["historical_t7_hold_gpu_hours"] >= Decimal("4.0"),
             "first smoke must retain the provisional T7 hold")
    _require(report["r2"]["actual_charged_gpu_hours"] == Decimal("0.023123"),
             "first smoke must retain the measured R2 settlement")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("ledger_path", "r2_guard_path", "placement_path", "admission_path", "reserve_path"):
        parser.add_argument(name, type=Path)
    for name in ("ledger-sha256", "r2-guard-sha256", "placement-sha256", "admission-sha256",
                 "reserve-sha256", "cut-utc"):
        parser.add_argument(f"--{name}", required=True)
    try:
        report = verify(**vars(parser.parse_args()))
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(report, default=str, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
