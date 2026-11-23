from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lab import smollm3_opening_balance as opening
from lab import smollm3_smoke_admission as admission
from lab import smollm3_smoke_settlement as smoke


FIXTURE = Path(__file__).resolve().parent / "fixtures" / "smollm3_opening"  # committed copy of the xlu84i fixture
LEDGER_PIN = "4394d1c6d09eabd9b463b08e03956d9977bd6c28fbe74c2f1fb7a34ee65cdadd"
GUARD_PIN = "369cbc6ee59dc9ae50a0b0dde8189d7be418fca4c91a658f6245e0707fa48af9"
CUT = "2026-11-21T20:00:00Z"


class OpeningBalanceTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path(self.enterContext(TemporaryDirectory()))
        self.identity = {"admission_id": "offline-first-smoke", "batch": smoke.BATCH, "allocation": smoke.ALLOCATION}
        self.reserve = {
            **self.identity, "event": "reserve", "program_ceiling_gpu_hours": 70,
            "historical_t7_hold_gpu_hours": 4, "reserved_gpu_hours": 0.1,
            "available_program_before_gpu_hours": 65.976877, "available_program_after_gpu_hours": 65.876877,
            "available_replication_before_gpu_hours": 9.5, "available_replication_after_gpu_hours": 9.4,
        }

    def write(self, filename, document):
        path = self.directory / filename
        path.touch(mode=0o600)
        raw = document if type(document) is bytes else (json.dumps(document, sort_keys=True) + "\n").encode()
        path.write_bytes(raw)
        return path, sha256(raw).hexdigest()

    def packet(self, *, reserve=None, accepted=None, placement=None, cut=CUT,
               ledger_path=None, ledger_pin=LEDGER_PIN, guard_pin=GUARD_PIN):
        reserve_path, reserve_pin = self.write("reserve.json", self.reserve if reserve is None else reserve)
        receipt = {
            **self.identity, "schema": admission.SCHEMA, "reserved_gpu_hours": 0.1,
            "valid_from_utc": "2026-11-21T03:00:00Z", "valid_until_utc": "2026-11-21T20:10:00Z",
            "worker_plan_sha256": admission.WORKER_PLAN_SHA256, "model_manifest_sha256": admission.MODEL_MANIFEST_SHA256,
            "reservation_sha256": reserve_pin, "outer_wall_seconds": admission.OUTER_WALL_SECONDS,
            "review_reference": "synthetic replay only", "authorization_reference": "no live authority",
        }
        admission_path, admission_pin = self.write("admission.json", receipt | (accepted or {}))
        located = {
            **self.identity, "schema": opening.SCHEMA, "cut_utc": cut, "ledger_sha256": ledger_pin,
            "r2_guard_sha256": guard_pin, "admission_sha256": admission_pin, "reserve_sha256": reserve_pin,
            "available_replication_before_gpu_hours": 9.5,
        }
        placement_path, placement_pin = self.write("placement.json", located | (placement or {}))
        paths = {
            "ledger_path": ledger_path or FIXTURE / "resource-ledger.jsonl",
            "r2_guard_path": FIXTURE / "r2-calibration.log",
            "placement_path": placement_path, "admission_path": admission_path, "reserve_path": reserve_path,
        }
        pins = {"ledger_sha256": ledger_pin, "r2_guard_sha256": guard_pin, "placement_sha256": placement_pin,
                "admission_sha256": admission_pin, "reserve_sha256": reserve_pin, "cut_utc": cut}
        return paths | pins

    def test_real_archived_r2_recomputes_opening_and_synthetic_placement(self):
        report = opening.verify(**self.packet())
        self.assertEqual(report["r2"]["actual_charged_gpu_hours"], Decimal(".023123"))
        self.assertEqual(report["opening"]["historical_t7_hold_gpu_hours"], Decimal(4))
        self.assertEqual(report["projected_program_gpu_hours_after_reserve"], Decimal("65.876877"))
        self.assertEqual(report["projected_replication_gpu_hours_after_reserve"], Decimal("9.4"))
        for name in ("ledger_changed", "live_head_verified", "authorizes_launch"):
            self.assertIs(report[name], False)

    def test_legacy_reserve_arithmetic_cannot_roll_back_or_erase_history(self):
        for changes, field in (
            ({"available_program_before_gpu_hours": 66, "available_program_after_gpu_hours": 65.9},
             "available_program_before_gpu_hours"),
            ({"historical_t7_hold_gpu_hours": 0, "available_program_before_gpu_hours": 70,
              "available_program_after_gpu_hours": 69.9}, "historical_t7_hold_gpu_hours"),
            ({"available_replication_before_gpu_hours": 10, "available_replication_after_gpu_hours": 9.9},
             "available_replication_before_gpu_hours"),
        ):
            with self.subTest(field=field):
                packet = self.packet(reserve=self.reserve | changes)
                self.assertEqual(smoke.verify(packet["reserve_path"], reservation_sha256=packet["reserve_sha256"])["status"], "held")
                with self.assertRaisesRegex(ValueError, field):
                    opening.verify(**packet)

    def test_late_row_and_pre_settlement_cuts_refuse(self):
        with self.assertRaisesRegex(ValueError, "exceeds the declared cut"):
            opening.verify(**self.packet(cut="2026-11-21T03:57:00Z"))
        later = (FIXTURE / "resource-ledger.jsonl").read_bytes() + b'{"event":"reserve"}\n'
        ledger, pin = self.write("ledger-with-other-activity.jsonl", later)
        with self.assertRaisesRegex(ValueError, "R2-only ledger cut"):
            opening.verify(**self.packet(ledger_path=ledger, ledger_pin=pin))

    def test_exact_r2_settlement_is_recomputed_not_accepted_at_fresh_pin(self):
        raw = (FIXTURE / "resource-ledger.jsonl").read_bytes().splitlines()
        row = json.loads(raw[1])
        row.update(actual_charged_gpu_hours=0.01, returned_reservation_gpu_hours=0.09,
                   available_program_gpu_hours=65.99, available_r2_r3_gpu_hours=7.49)
        ledger, pin = self.write("reconciled-false-ledger.jsonl", raw[0] + b"\n" + json.dumps(row).encode() + b"\n")
        with self.assertRaisesRegex(ValueError, "settlement mismatch"):
            opening.verify(**self.packet(ledger_path=ledger, ledger_pin=pin))
        with self.assertRaisesRegex(ValueError, "guard evidence"):
            opening.verify(**self.packet(guard_pin="0" * 64))

    def test_crossed_admission_placement_and_pin_changes_refuse(self):
        with self.assertRaisesRegex(ValueError, "crosses an admission"):
            opening.verify(**self.packet(accepted={"admission_id": "different"}))
        with self.assertRaisesRegex(ValueError, "crosses an admission"):
            opening.verify(**self.packet(accepted={"reservation_sha256": "0" * 64}))
        with self.assertRaisesRegex(ValueError, "pinned cut_utc"):
            opening.verify(**self.packet(placement={"cut_utc": "2026-11-21T20:01:00Z"}))
        packet = self.packet()
        with self.assertRaisesRegex(ValueError, "placement digest"):
            opening.verify(**(packet | {"placement_sha256": "0" * 64}))


if __name__ == "__main__":
    unittest.main()
