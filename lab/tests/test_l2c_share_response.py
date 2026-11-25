from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lab import l2c_share_response as response
from lab.l2c_share_audit import audit
from lab.l4_measured_compression import pin
from murmuration.board import read_log


class L2CShareResponseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        directory = TemporaryDirectory()
        cls.addClassCleanup(directory.cleanup)
        cls.root = Path(directory.name)
        cls.report = response.compare(cls.root)
        cls.rows = {(row["condition"], row["arm"], row["checks"]): row for row in cls.report["rows"]}

    def test_fifty_rows_use_prefixes_of_five_frozen_orders_and_match_denominators(self):
        report = self.report
        self.assertEqual(report["orders"], {
            "direct_relays": ["p3", "p5", "p2", "p4"], "outdegree": ["p2", "p3", "p5", "p4"],
            "retrievals": ["p5", "p3", "p2", "p4"], "recency": ["p4", "p2", "p5", "p3"],
            "random": ["p4", "p5", "p2", "p3"],
        })
        self.assertEqual(report["selection"]["arms"]["random"], ["p4", "p2", "p3", "p1"])
        self.assertEqual(len(report["rows"]), 50)
        self.assertEqual(len(self.rows), 50)
        for (condition, arm, checks), row in self.rows.items():
            with self.subTest(condition=condition, arm=arm, checks=checks):
                self.assertEqual(row["selected"], report["orders"][arm][:checks])
                self.assertEqual(row["cached_lookups"], 2 * checks)
                self.assertEqual((row["reads"], row["read_hits"], row["attempts"]), (4, 4, 8))
                self.assertEqual(row["invalid_admitted"] + row["invalid_refused"], 2)
                self.assertEqual(row["valid_admitted"] + row["valid_refused"], 6)
                self.assertEqual(row["committed"], row["invalid_admitted"] + row["valid_admitted"])

    def test_exact_dose_curves_and_separate_minima(self):
        invalid = {"direct_relays": [2, 0, 0, 0, 0], "outdegree": [2, 2, 0, 0, 0],
                   "retrievals": [2, 2, 0, 0, 0], "recency": [2, 2, 2, 2, 0], "random": [2, 2, 2, 2, 0]}
        blocked = {"direct_relays": [0, 0, 0, 2, 2], "outdegree": [0, 2, 2, 2, 2],
                   "retrievals": [0, 0, 0, 2, 2], "recency": [0, 0, 2, 2, 2], "random": [0, 0, 0, 2, 2]}
        for condition in ("unavailable", "restored"):
            invalid_minima, both_minima = [], []
            for arm in response.ORDERINGS:
                observed = [self.rows[condition, arm, checks] for checks in range(5)]
                actual_invalid = [row["invalid_admitted"] for row in observed]
                actual_blocked = [row["valid_refused"] for row in observed]
                self.assertEqual(actual_invalid, invalid[arm])
                self.assertEqual(actual_blocked, blocked[arm] if condition == "unavailable" else [0] * 5)
                invalid_minima.append(actual_invalid.index(actual_invalid[-1]))
                both_minima.append(list(zip(actual_invalid, actual_blocked, strict=True)).index(
                    (actual_invalid[-1], actual_blocked[-1])))
            self.assertEqual(invalid_minima, [1, 2, 2, 4, 4])
            self.assertEqual(both_minima, [3, 2, 3, 4, 4] if condition == "unavailable" else [1, 2, 2, 4, 4])
            frontier = self.report["audit"]["nondominated"][condition]
            self.assertEqual({(row["arm"], row["checks"]) for row in frontier},
                             {(arm, 0) for arm in response.ORDERINGS} | {("direct_relays", 1)})
        self.assertIs(self.report["scientific_result"], False)
        unavailable, restored = (self.report["descriptive"][key] for key in ("unavailable", "restored"))
        self.assertEqual(list(unavailable["first_point_matching_full_invalid_admissions"].values()), [1, 2, 2, 4, 4])
        for condition, expected_valid in ((unavailable, 1), (restored, 0)):
            one = condition["uniform_permutation_expected_counts"][1]
            self.assertEqual(one["invalid_admitted"], {"numerator": 3, "denominator": 2})
            self.assertEqual(one["valid_refused"], {"numerator": expected_valid, "denominator": 2 if expected_valid else 1})

    def test_archived_ledger_and_closed_board_for_every_cell(self):
        receipts = self.report["receipts"]
        self.assertEqual(len(receipts), 50)
        for (condition, arm, checks), row in self.rows.items():
            identity = f"{condition}-{arm}-{checks}"
            saved = json.loads((self.root / f"{identity}-receipt.json").read_bytes())
            trace = read_log(self.root / f"{identity}.jsonl")
            recorded = saved["dispatch"]["receipts"]
            self.assertEqual(receipts[identity], {"receipt_sha256": pin(saved),
                                                  "expected_terminal_head": trace[-1]["hash"],
                                                  "expected_events": len(trace)})
            self.assertEqual(len(recorded), 12)
            self.assertEqual(saved["ledger"]["checks"], checks)
            self.assertEqual(sum(item["status"] == "admitted" for item in recorded), row["committed"])
            for record in recorded:
                self.assertEqual(trace[record["prior_count"] - 1]["hash"], record["prior_head"])
                closing = trace[record["closed_count"] - 1]
                self.assertEqual((closing["hash"], closing["type"]), (record["closed_head"], "end_round"))

    def test_restoring_one_reference_only_changes_boards_that_selected_it(self):
        changed = 0
        target = self.report["restored_target"]
        for arm, order in self.report["orders"].items():
            for checks in range(5):
                old = (self.root / f"unavailable-{arm}-{checks}.jsonl").read_bytes()
                restored = (self.root / f"restored-{arm}-{checks}.jsonl").read_bytes()
                expected_change = target in order[:checks]
                self.assertEqual(old != restored, expected_change)
                changed += expected_change
        self.assertEqual(changed, 13)
        self.assertEqual(self.report["audit"]["affected_cells"], 13)

    def test_auditor_refuses_missing_duplicate_or_malformed_twins(self):
        report = self.report
        rows = report["rows"]
        fake_twins = [dict(row, condition=condition) for condition in ("unavailable", "restored")
                      for row in rows if row["condition"] == "unavailable"]
        malformed = deepcopy(rows)
        malformed[-1]["cached_lookups"] += 1
        for candidate, message in (
            (rows[:-1], "incomplete"),
            ([*rows[:-1], rows[0]], "exactly one row"),
            (malformed, "dispatch counters do not reconcile"),
            (fake_twins, "target effect differs"),
        ):
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    self.audit(candidate)

    def audit(self, rows, *, orders=None):
        report = self.report
        return audit(rows, orders=report["orders"] if orders is None else orders,
                     restored_target=report["restored_target"], statuses=report["expected_settlements"],
                     invalid_uses=report["invalid_opportunities_by_target"])

    def test_auditor_rejects_coherent_category_swaps_and_incomplete_arm_scope(self):
        statuses, outcomes = (deepcopy(self.report["rows"]) for _ in range(2))
        for row in statuses:
            row["settlements"]["unavailable"] += row["settlements"]["mismatch"]
            row["settlements"]["mismatch"] = 0
        for row in outcomes:
            if "p3" in row["selected"]:
                row["invalid_refused"] -= 1
                row["valid_refused"] += 1
                row["valid_admitted"] -= 1
                row["invalid_admitted"] += 1
        for forgery in (statuses, outcomes, [dict(row, read_hits=0) for row in self.report["rows"]]):
            with self.assertRaises(ValueError):
                self.audit(forgery)
        arm = "direct_relays"
        with self.assertRaisesRegex(ValueError, "five-arm"):
            self.audit([row for row in self.report["rows"] if row["arm"] == arm],
                       orders={arm: self.report["orders"][arm]})
