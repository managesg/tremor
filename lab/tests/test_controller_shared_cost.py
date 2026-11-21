import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lab import controller_pair_audit, controller_shared_cost


class ControllerSharedCostTests(unittest.TestCase):
    def setUp(self):
        self.bundle = Path(self.enterContext(TemporaryDirectory()))
        self.scopes = {"combined": ["combined-0"], "plain": ["plain-0"],
                       "common": ["score-0", "calibration-0"]}
        self.charges = [
            self.charge("combined-0", "combined", "worker", 20),
            self.charge("plain-0", "plain", "worker", 18),
            self.charge("score-0", "common", "independent_scoring", 4),
            self.charge("calibration-0", "common", "calibration", 15, previous="a" * 64),
        ]

    @staticmethod
    def charge(identifier, scope, role, gpu, previous=None):
        return {"id": identifier, "scope": scope, "role": role,
                "prior_settlement_sha256": previous,
                "usage": dict.fromkeys(controller_pair_audit.USAGE, 0) | {"gpu_wall_ns": gpu}}

    def write(self, name, document):
        path = self.bundle / name
        raw = json.dumps(document).encode()
        path.write_bytes(raw)
        return path, hashlib.sha256(raw).hexdigest()

    def verify(self, *, bind=None):
        index, index_pin = self.write("index.json", {"schema": "controller_unit_charges_v1",
                                                     "receipts": self.charges})
        placement, placement_pin = self.write("placement.json", {
            "schema": "controller_cost_placement_v1", "charge_index_sha256": bind or index_pin,
            "charges_by_scope": self.scopes,
        })
        return controller_shared_cost.verify(placement, index, placement_sha256=placement_pin,
                                             charge_index_sha256=index_pin)

    def test_charges_shared_evaluation_once_and_keeps_prior_cost_visible(self):
        report = self.verify()
        self.assertFalse(report["authorizes_execution"])
        self.assertTrue(report["coverage_complete"])
        self.assertEqual(report["incremental_usage"]["gpu_wall_ns"], 42)
        self.assertEqual(report["known_prior_usage"]["gpu_wall_ns"], 15)
        common = report["by_scope"]["common"]
        self.assertEqual(common["incremental_usage"]["gpu_wall_ns"], 4)
        self.assertEqual(common["known_prior_usage"]["gpu_wall_ns"], 15)

    def test_missing_and_unsettled_receipts_withhold_complete_increment(self):
        self.charges[2]["usage"] = None
        self.charges.pop(1)
        report = self.verify()
        self.assertFalse(report["coverage_complete"])
        self.assertIsNone(report["incremental_usage"])
        self.assertEqual(report["known_incremental_usage"]["gpu_wall_ns"], 20)
        self.assertEqual(report["by_scope"]["plain"]["missing_charge_ids"], ["plain-0"])
        self.assertEqual(report["by_scope"]["common"]["unsettled_charge_ids"], ["score-0"])
        self.assertIsNone(report["by_scope"]["common"]["incremental_usage"])

    def test_rejects_duplicate_placement_receipt_and_crossed_scope(self):
        self.scopes["combined"].append("score-0")
        with self.assertRaisesRegex(ValueError, "placed more than once"):
            self.verify()
        self.scopes["combined"].pop()
        self.charges.append(self.charges[2].copy())
        with self.assertRaisesRegex(ValueError, "duplicate unit charge"):
            self.verify()
        self.charges.pop()
        self.charges[2]["scope"], self.charges[2]["role"] = "plain", "verification"
        with self.assertRaisesRegex(ValueError, "crossed unit charge"):
            self.verify()

    def test_rejects_unbound_index_and_unsubstantiated_prior_usage(self):
        with self.assertRaisesRegex(ValueError, "independently pinned charge index"):
            self.verify(bind="0" * 64)
        self.charges[-1]["usage"] = None
        with self.assertRaisesRegex(ValueError, "known settled usage"):
            self.verify()
