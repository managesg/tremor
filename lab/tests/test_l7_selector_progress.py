from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lab import l7_selector_progress as audit


class SelectorProgressTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        scores = [{"candidate_id": key, "verified_tasks": []} for key in ("first", "second")]
        teams = {row["candidate_id"]: {"artifact_sha256": sha256(row["candidate_id"].encode()).hexdigest()}
                 for row in scores}
        self.base = {"scientific_result": False, "status": "completed", "plan_sha256": "a" * 64,
                     "reviewed": scores, "candidate_order": list(teams), "teams": teams,
                     "selected": scores[0], "utility": 0}
        self.reviews = [row | teams[row["candidate_id"]] | {"charge": 1} for row in scores]

    def write(self, name, value):
        path = self.root / name
        raw = json.dumps(value).encode()
        path.write_bytes(raw)
        return path, sha256(raw).hexdigest()

    def verify(self, selector=None, count=2):
        report, report_pin = self.write("replay.json", self.base)
        witness, witness_pin = self.write("witness.json", {
            "schema": audit.SCHEMA, "plan_sha256": self.base["plan_sha256"], "replay_sha256": report_pin,
            "reviews": self.reviews[:count], "selector": selector,
        })
        return audit.verify(report, witness, replay_sha256=report_pin, witness_sha256=witness_pin)

    def test_incomplete_review_keeps_prefix_and_utilities_unavailable(self):
        result = self.verify(count=1)
        self.assertEqual((result["completed_reviews"], result["known_review_cost"]), (1, 1))
        for field in ("complete_review_cost", "selection_charge", "utility", "selected", "started"):
            self.assertIsNone(result[field])
        self.assertFalse(result["native_execution_verified"])

    def test_interrupted_started_selector_charge_is_independent_of_outcome(self):
        for charge in (0, 1, None):
            with self.subTest(charge=charge):
                result = self.verify({"started": True, "terminal": "interrupted_after_start",
                                      "selected": None, "charge": charge})
                self.assertIs(result["selection_charge"], charge)
                self.assertIsNone(result["utility"])
        for charge in (1, None):
            with self.subTest(unavailable_terminal_charge=charge):
                result = self.verify({"started": True, "terminal": "terminal_unavailable",
                                      "selected": None, "charge": charge})
                self.assertTrue(result["started"])
                self.assertIs(result["selection_charge"], charge)
                self.assertIsNone(result["utility"])

    def test_complete_empty_result_is_measured_zero_with_charge(self):
        result = self.verify({"started": True, "terminal": "completed",
                              "selected": self.base["selected"], "charge": 1})
        self.assertEqual((result["utility"], result["selection_charge"]), (0, 1))
        self.assertIsNone(result["utility_unavailable_reason"])

    def test_refuses_premature_start_and_crossed_candidate_artifact(self):
        with self.assertRaisesRegex(ValueError, "started before candidate reviews"):
            self.verify({"started": True, "terminal": "interrupted_after_start",
                         "selected": None, "charge": None}, count=1)
        self.reviews[0]["artifact_sha256"] = self.reviews[1]["artifact_sha256"]
        with self.assertRaisesRegex(ValueError, "candidate review differs"):
            self.verify()

    def test_pre_start_cancel_preserves_unknown_review_cost(self):
        self.reviews = deepcopy(self.reviews)
        self.reviews[0]["charge"] = None
        result = self.verify({"started": False, "terminal": "cancelled_before_start",
                              "charge": 0, "selected": None})
        self.assertEqual(result["selection_charge"], 0)
        self.assertEqual(result["review_charges_unavailable"], 1)
        self.assertIsNone(result["complete_review_cost"])
