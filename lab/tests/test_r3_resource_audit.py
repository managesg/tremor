from contextlib import redirect_stdout
from decimal import Decimal as D
import hashlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lab.r3_resource_audit import audit, charge_for_wall_time, main


def reserve():
    return {
        "admission_id": "synthetic", "batch": "r3-synthetic", "event": "reserve",
        "program_ceiling_gpu_hours": 70, "historical_t7_hold_gpu_hours": 4,
        "reserved_gpu_hours": D("0.1"),
        "available_program_before_gpu_hours": 66, "available_r2_r3_before_gpu_hours": D("7.5"),
        "available_program_after_gpu_hours": D("65.9"), "available_r2_r3_after_gpu_hours": D("7.4"),
    }


def terminal(seconds="83.24227687099483", cleanup=True):
    return {"admission_id": "synthetic", "container": "synthetic-container",
            "observed_wall_seconds": D(seconds), "cleanup_confirmed": cleanup}


def outcome(stop="completed"):
    return {"stop": stop, "min_memavailable_kib": 64_000_000}


def settle(**changes):
    return {"admission_id": "synthetic", "batch": "r3-synthetic", "event": "settle",
            "outcome": outcome(), "terminal": terminal(),
            "actual_charged_gpu_hours": D("0.023123"), "returned_reservation_gpu_hours": D("0.076877"),
            "available_program_gpu_hours": D("65.976877"), "available_r2_r3_gpu_hours": D("7.476877"),
            **changes}


class ResourceAuditTests(unittest.TestCase):
    def test_exact_ceiling_at_and_just_above_one_micro_hour(self):
        self.assertEqual(charge_for_wall_time(D("0.0036")), D("0.000001"))
        self.assertEqual(charge_for_wall_time(D("0.0036000000000000000000000000000000000000001")), D("0.000002"))
        self.assertEqual(charge_for_wall_time(D("359.999999")), D("0.100000"))
        for invalid in (True, D("-1"), D("NaN")):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                charge_for_wall_time(invalid)

    def test_settlement_matches_measured_wall_time_and_balances(self):
        receipt = audit([reserve(), settle()])
        self.assertEqual(receipt["status"], "verified_settlement")
        self.assertEqual(receipt["held_gpu_hours"], 0)
        self.assertEqual(receipt["actual_charged_gpu_hours"], D("0.023123"))
        self.assertEqual(receipt["returned_reservation_gpu_hours"], D("0.076877"))
        self.assertEqual(receipt["available_program_gpu_hours"], D("65.976877"))
        self.assertEqual(receipt["available_r2_r3_gpu_hours"], D("7.476877"))

    def test_no_receipt_watchdog_stops_and_unknown_cleanup_keep_full_hold(self):
        cases = ((None, None, "missing_terminal"), (outcome(), terminal(cleanup=False), "cleanup_unconfirmed"),
                 (None, terminal("0"), "missing_outcome"), (outcome(), terminal(), "missing_settlement"))
        cases += tuple((outcome(stop), terminal(), stop) for stop in ("memory_floor", "wall_limit", "child_error"))
        for watchdog, receipt, reason in cases:
            with self.subTest(reason=reason):
                result = audit([reserve()], outcome=watchdog, terminal=receipt)
                self.assertEqual((result["status"], result["reason"]), ("held", reason))
                self.assertEqual(result["held_gpu_hours"], D("0.1"))
                self.assertEqual(result["available_r2_r3_gpu_hours"], D("7.4"))
        for stop in ("memory_floor", "wall_limit"):
            with self.subTest(stop=stop), self.assertRaisesRegex(ValueError, "settlement requires"):
                audit([reserve(), settle(outcome=outcome(stop))])
        with self.assertRaisesRegex(ValueError, "settlement requires"):
            audit([reserve(), settle(terminal=terminal(cleanup=False))])

    def test_guard_duration_above_reservation_cannot_release(self):
        overrun = terminal("360.0000001")
        result = audit([reserve()], outcome=outcome(), terminal=overrun)
        self.assertEqual((result["reason"], result["measured_gpu_hours"]), ("reservation_overrun", D("0.100001")))
        self.assertEqual(result["held_gpu_hours"], D("0.1"))
        with self.assertRaisesRegex(ValueError, "settlement requires"):
            audit([reserve(), settle(terminal=overrun)])

    def test_duplicate_records_mismatched_receipts_and_wrong_arithmetic_are_rejected(self):
        for records in ([reserve(), reserve()], [reserve(), settle(), settle()],
                        [reserve(), settle(admission_id="wrong")],
                        [reserve(), settle(terminal=dict(terminal(), admission_id="wrong"))],
                        [reserve(), settle(available_r2_r3_gpu_hours=D("7.476878"))],
                        [dict(reserve(), available_program_after_gpu_hours=D("65.900001"))]):
            with self.subTest(events=[row["event"] for row in records]), self.assertRaises(ValueError):
                audit(records)

    def test_guard_log_is_corroborated_and_remains_unchanged(self):
        with TemporaryDirectory() as temp:
            ledger, log = Path(temp) / "ledger.jsonl", Path(temp) / "guard.log"
            receipt = terminal("90")
            receipt["observed_wall_seconds"] = 90
            raw = b"progress\rstatus\n" + b"".join(json.dumps(row).encode() + b"\n" for row in (outcome(), receipt))
            log.write_bytes(raw)
            rows = [reserve(), settle(terminal=receipt, actual_charged_gpu_hours=D("0.025"),
                                      returned_reservation_gpu_hours=D("0.075"),
                                      available_program_gpu_hours=D("65.975"), available_r2_r3_gpu_hours=D("7.475"),
                                      run_log_sha256=hashlib.sha256(raw).hexdigest())]
            ledger_raw = "".join(json.dumps(row, default=float) + "\n" for row in rows).encode()
            ledger.write_bytes(ledger_raw)
            output = io.StringIO()
            with redirect_stdout(output):
                main([str(ledger), "--guard-log", str(log)])
            self.assertEqual(json.loads(output.getvalue())["actual_charged_gpu_hours"], "0.025000")
            self.assertEqual(log.read_bytes(), raw)
            self.assertEqual(ledger.read_bytes(), ledger_raw)
