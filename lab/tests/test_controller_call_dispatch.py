from copy import deepcopy
import unittest

from lab import controller_pair_audit as audit
from lab.tests import test_controller_pair_audit as fixtures


class ControllerCallDispatchTests(unittest.TestCase):
    def setUp(self):
        self.case = case = fixtures.ControllerPairAuditTests()
        self.addCleanup(case.doCleanups)
        case.setUp()
        for arm in case.fixture.manifest["arms"].values():
            arm["budget"]["calls"] = 1
        self.arm = case.rows[1]
        self.arm["attempts"][0]["usage"]["calls"] = 1

    def report(self):
        return audit.verify(**self.case.freeze())

    def test_positive_call_after_exhaustion_fails_even_if_arm_stopped(self):
        self.arm["terminal"] = "stopped"
        for status in ("completed", "failed", "refused"):
            with self.subTest(status=status):
                self.arm["attempts"][-1] = self.case.attempt(2, "verification", calls=1, status=status)
                with self.assertRaisesRegex(ValueError, "recorded call after the dispatch cap was exhausted"):
                    self.report()

    def test_exact_cap_applies_across_matched_blocks(self):
        case = self.case
        second = case.block | {"block_id": "next-block", "condition": "disrupted"}
        case.inputs["task_manifest_sha256"] = case.fixture.artifact("tasks.json", {"blocks": [case.block, second]})
        case.fixture.manifest["inputs"]["task_manifest_sha256"] = case.inputs["task_manifest_sha256"]["sha256"]
        case.rows.extend(deepcopy(row) | {"block_id": second["block_id"], "condition": "disrupted"}
                         for row in case.rows[:2])
        for row in case.rows:
            row["inputs"] = case.fixture.manifest["inputs"].copy()
        terminal = case.rows[3]
        terminal["terminal"] = "stopped"
        terminal["attempts"] = [case.attempt(0, "verification", calls=1)]
        with self.assertRaisesRegex(ValueError, "recorded call after the dispatch cap was exhausted"):
            self.report()
        terminal["attempts"][0]["usage"]["calls"] = 0
        report = self.report()
        self.assertEqual([pair["paired_delta"] for pair in report["pairs"]], ["1/6", None])
        self.assertEqual(report["arm_resource_receipts"]["combined"]["known_usage"]["calls"], 1)

    def test_zero_call_work_and_cleanup_remain_distinct_from_provider_dispatch(self):
        report = self.report()
        self.assertEqual(report["pairs"][0]["paired_delta"], "1/6")
        self.assertEqual(report["arm_resource_receipts"]["combined"]["known_usage"]["calls"], 1)

        self.arm["terminal"] = "stopped"
        self.arm["attempts"].append(self.case.attempt(3, "cleanup", calls=1))
        report = self.report()
        usage = report["arm_resource_receipts"]["combined"]
        self.assertEqual((usage["known_usage"]["calls"], usage["exceeded_caps"]), (2, ["calls"]))
        self.assertIsNone(report["pairs"][0]["paired_delta"])

    def test_unknown_and_measured_overrun_stay_in_stopped_resource_accounting(self):
        case = self.case
        self.arm["terminal"] = "stopped"
        for arm in case.fixture.manifest["arms"].values():
            arm["budget"]["cpu_wall_ns"] = 8
        self.arm["attempts"].extend([
            case.attempt(3, "observation", cpu=3, calls=0),
            case.attempt(4, "cleanup", status="failed") | {"usage": None},
        ])
        report = self.report()
        usage = report["arm_resource_receipts"]["combined"]
        self.assertEqual((usage["known_usage"]["calls"], usage["known_usage"]["cpu_wall_ns"]), (1, 9))
        self.assertEqual(usage["exceeded_caps"], ["cpu_wall_ns"])
        self.assertEqual(usage["unknown_usage_attempts"], 1)
        self.assertIsNone(report["pairs"][0]["paired_delta"])
