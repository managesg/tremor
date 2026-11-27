from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lab import l2c_provenance_control, l2c_ranked_dispatch as ranked
from lab.l2c_screening_ledger import verify as verify_ledger
from lab.l4_measured_compression import pin
from tremor.board import Board


class L2CRankedDispatchTests(unittest.TestCase):
    def test_mismatch_purchase_refuses_two_dispatches_and_unavailable_is_distinct(self):
        report = ranked.demo()
        self.assertIs(report["scientific_result"], False)
        for arm, state, reason, refused_ids in (
            ("direct_relays", "mismatch", "screening_mismatch", ["relay-0", "promotion-0"]),
            ("outdegree", "unavailable", "screening_unavailable", ["relay-2", "promotion-2"]),
            ("retrievals", "matched", None, []),
        ):
            with self.subTest(arm=arm):
                result = report["arms"][arm]
                self.assertEqual(result["evaluator_checks"], 1)
                self.assertEqual(list(result["settled"].values()), [state])
                self.assertEqual(result["dispatch"]["cached_lookups"], 2)
                self.assertEqual([event["event"] for event in result["ledger"]["events"]], ["start", "settle"])
                self.assertEqual(result["ledger"]["events"][1]["used_checks"], 1)
                refused = [row for row in result["dispatch"]["receipts"] if row["status"] == "refused"]
                self.assertEqual([row["id"] for row in refused], refused_ids)
                for row in refused:
                    self.assertEqual(row["reason"], reason)
                    self.assertIsNone(row["post_id"])
        results = report["arms"]
        self.assertEqual(results["direct_relays"]["assessment"]["invalid_refused"], 2)
        self.assertEqual(results["outdegree"]["assessment"]["valid_refused"], 2)
        self.assertEqual(results["retrievals"]["assessment"]["valid_admitted"], 6)
        self.assertEqual(results["retrievals"]["dispatch"]["terminal"], results["none"]["dispatch"]["terminal"])

    def test_matched_budgets_full_and_zero_share_exact_dispatch_and_read_denominators(self):
        report = ranked.demo()
        plan = report["dispatch_plan"]
        arms = report["arms"]
        expected = {"direct_relays": (1, 6), "outdegree": (1, 6), "retrievals": (1, 8), "recency": (1, 8),
                    "random": (1, 8), "none": (0, 8), "full": (4, 4)}
        self.assertEqual(set(arms), set(expected))
        for name, (checks, commits) in expected.items():
            with self.subTest(name=name):
                arm = arms[name]
                self.assertEqual(arm["evaluator_checks"], checks)
                self.assertEqual(arm["dispatch"]["cached_lookups"], 2 * checks)
                self.assertEqual(arm["dispatch"]["physical_counts"], {
                    "reads": 4, "read_hits": 4, "dispatch_attempts": 8, "admitted": commits,
                    "refused": 8 - commits, "posts": commits, "committed": commits, "checks": 2 * checks,
                })
                self.assertEqual(arm["dispatch"]["plan_sha256"], pin(plan))
                self.assertEqual([row["id"] for row in arm["dispatch"]["receipts"]],
                                 [row["id"] for row in plan["steps"]])

    def test_detached_reversal_changes_assessment_with_identical_ledger_and_board(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            rank, initial, selection, plan, bridge, reference, truth = ranked.fixture(root)
            original_path, reversed_path = root / "original.jsonl", root / "reversed.jsonl"
            original = ranked.evaluate_arm(rank, initial, original_path, selection, plan, bridge, reference, truth,
                                           arm="direct_relays", expected_bridge_pin=pin(bridge), expected_truth_pin=pin(truth))
            alternate = deepcopy(truth)
            alternate["values"] = {key: not value for key, value in truth["values"].items()}
            reversed_ = ranked.evaluate_arm(rank, initial, reversed_path, selection, plan, bridge, reference, alternate,
                                            arm="direct_relays", expected_bridge_pin=pin(bridge), expected_truth_pin=pin(alternate))
            self.assertEqual(original_path.read_bytes(), reversed_path.read_bytes())
        self.assertEqual({key: value for key, value in original.items() if key != "assessment"},
                         {key: value for key, value in reversed_.items() if key != "assessment"})
        self.assertEqual(original["assessment"]["invalid_refused"], 2)
        self.assertEqual(reversed_["assessment"]["valid_refused"], 2)
        self.assertEqual(reversed_["assessment"]["invalid_admitted"], 6)

    def test_repinned_bridge_rejects_claim_version_and_duplicate_target(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            rank, initial, selection, plan, bridge, reference, truth = ranked.fixture(root)
            for violation in ("version", "duplicate"):
                with self.subTest(violation=violation):
                    altered = deepcopy(bridge)
                    row = altered["targets"][0]
                    if violation == "version":
                        claim = Board(initial, seed=17).snapshot()["items"][row["target"]]["text"]
                        updated = json.loads(claim)
                        updated["version"] += 1
                        row["claim_sha256"] = pin(json.dumps(updated, sort_keys=True))
                    else:
                        other = altered["targets"][1]
                        row.update(target=other["target"], claim_sha256=other["claim_sha256"])
                    path = root / f"{violation}.jsonl"
                    with self.assertRaisesRegex(ValueError, "unique visible targets and exact claims"):
                        ranked.evaluate_arm(rank, initial, path, selection, plan, altered, reference, truth,
                                            arm="direct_relays", expected_bridge_pin=pin(altered), expected_truth_pin=pin(truth))
                    self.assertFalse(path.exists())

    def test_screening_ledger_rejects_self_repinned_status_and_unmetered_settlement(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            rank, initial, selection, plan, bridge, reference, truth = ranked.fixture(root)
            arm = ranked.evaluate_arm(rank, initial, root / "arm.jsonl", selection, plan, bridge, reference, truth,
                                      arm="direct_relays", expected_bridge_pin=pin(bridge), expected_truth_pin=pin(truth))
            active = Board(initial, seed=17).snapshot()["items"]
            claims = {row["target"]: active[row["target"]]["text"] for row in bridge["targets"]}
            for mutation in ({"status": "matched"}, {"used_checks": 0}):
                with self.subTest(mutation=mutation):
                    ledger = deepcopy(arm["ledger"])
                    ledger["events"][1].update(mutation)
                    with self.assertRaisesRegex(ValueError, "independently pinned replay"):
                        verify_ledger(ledger, arm["selected_targets"], claims, reference,
                                      context_pin=arm["ledger"]["context_sha256"],
                                      expected_reference_pin=bridge["reference_sha256"], expected_ledger_pin=pin(ledger))

    def test_existing_provenance_modes_keep_physical_counts(self):
        previous = l2c_provenance_control.demo()
        for mode, (admitted, checks) in zip(l2c_provenance_control.MODES, ((13, 0), (2, 13), (3, 13), (4, 25)), strict=True):
            with self.subTest(mode=mode):
                actual = previous["arm_results"][mode]["physical_counts"]
                self.assertEqual((actual["reads"], actual["read_hits"], actual["dispatch_attempts"]), (3, 2, 15))
                self.assertEqual((actual["admitted"], actual["committed"], actual["checks"]), (admitted, admitted, checks))

    def test_crossed_labels_leave_the_output_path_available_for_retry(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            rank, initial, selection, plan, bridge, reference, truth = ranked.fixture(root)
            path = root / "retry.jsonl"
            crossed = truth | {"bridge_sha256": "0" * 64}
            with self.assertRaisesRegex(ValueError, "terminal labels differ"):
                ranked.evaluate_arm(rank, initial, path, selection, plan, bridge, reference, crossed,
                                    arm="direct_relays", expected_bridge_pin=pin(bridge), expected_truth_pin=pin(crossed))
            self.assertFalse(path.exists())
            result = ranked.evaluate_arm(rank, initial, path, selection, plan, bridge, reference, truth,
                                         arm="direct_relays", expected_bridge_pin=pin(bridge), expected_truth_pin=pin(truth))
            self.assertEqual(result["assessment"]["invalid_refused"], 2)
