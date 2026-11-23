from datetime import datetime
import json
import unittest
from unittest.mock import patch

from lab import smollm3_smoke_preflight as preflight
from lab.tests import test_smollm3_opening_balance as fixture


class OpeningPreflightTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture.OpeningBalanceTests()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.setUp()
        self.root = self.fixture.directory

    def verify(self, paths, *, now=fixture.CUT, include_opening=True, placement_pin=None):
        opening = (paths["ledger_path"], paths["r2_guard_path"], paths["placement_path"],
                   placement_pin if placement_pin is not None else paths["placement_sha256"])
        with (patch.object(preflight, "_verify_worker"),
              patch.object(preflight.replication_inventory, "_normalized", return_value=()),
              patch.object(preflight.replication_inventory, "_snapshot", return_value={"bytes": 1})):
            return preflight.verify(
                paths["admission_path"], paths["reserve_path"], self.root, self.root, self.root,
                admission_sha256=paths["admission_sha256"], now=datetime.fromisoformat(now),
                opening_balance=opening if include_opening else None,
            )

    def test_current_receipt_binds_exact_opening_pin(self):
        paths = self.fixture.packet()
        result = self.verify(paths)
        self.assertEqual(result["opening_placement_sha256"], paths["placement_sha256"])
        self.assertFalse(result["starts_container"])
        legacy = self.verify(paths, include_opening=False)
        self.assertNotIn("opening_placement_sha256", legacy)

    def test_repinning_reserve_cannot_restore_spent_hours_or_erase_hold(self):
        for changes, field in (
            ({"available_program_before_gpu_hours": 66, "available_program_after_gpu_hours": 65.9},
             "available_program_before_gpu_hours"),
            ({"historical_t7_hold_gpu_hours": 0, "available_program_before_gpu_hours": 70,
              "available_program_after_gpu_hours": 69.9}, "historical_t7_hold_gpu_hours"),
            ({"available_replication_before_gpu_hours": 10, "available_replication_after_gpu_hours": 9.9},
             "available_replication_before_gpu_hours"),
        ):
            with self.subTest(field=field):
                paths = self.fixture.packet(reserve=self.fixture.reserve | changes)
                legacy = self.verify(paths, include_opening=False)
                self.assertFalse(legacy["starts_container"])
                with self.assertRaisesRegex(ValueError, field):
                    self.verify(paths)

    def test_repinning_both_ledgers_cannot_release_the_t7_hold(self):
        paths = self.fixture.packet()
        first, second = (json.loads(line) for line in paths["ledger_path"].read_bytes().splitlines())
        first.update(historical_t7_hold_gpu_hours=0, available_program_before_gpu_hours=70,
                     available_program_after_gpu_hours=69.9)
        second["available_program_gpu_hours"] = 69.976877
        raw = "\n".join(json.dumps(row) for row in (first, second)).encode() + b"\n"
        ledger, pin = self.fixture.write("rolled-back-ledger.jsonl", raw)
        crossed = self.fixture.packet(
            ledger_path=ledger, ledger_pin=pin, reserve=self.fixture.reserve | {
                "historical_t7_hold_gpu_hours": 0, "available_program_before_gpu_hours": 69.976877,
                "available_program_after_gpu_hours": 69.876877,
            },
        )
        with self.assertRaisesRegex(ValueError, "retain the provisional T7 hold"):
            self.verify(crossed)

    def test_future_cut_and_wrong_placement_hash_fail(self):
        paths = self.fixture.packet()
        with self.assertRaisesRegex(ValueError, "after the launch preflight"):
            self.verify(paths, now="2026-11-21T19:59:59Z")
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            self.verify(paths, placement_pin="0" * 64)


if __name__ == "__main__":
    unittest.main()
