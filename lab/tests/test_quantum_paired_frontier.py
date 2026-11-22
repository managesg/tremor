from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lab.quantum import paired_frontier, topology_transfer


class GroverPairedFrontierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = paired_frontier.summarize()

    def arm(self, cap, regime, mode, access):
        cases = self.report["caps"][cap - 1]["cases"]
        case = next(case for case in cases if case["regime"] == regime and case["seed"] == 0)
        return next(arm for arm in case["arms"] if (arm["mode"], arm["access"]) == (mode, access))

    def test_same_stage_union_can_be_budget_stopped(self):
        self.assertEqual(self.report["audited_arm_cap_views"], 1024)
        self.assertEqual(self.report["same_union_as_full_cap_but_budget_stopped"], 317)
        self.assertEqual(self.report["same_union_as_full_cap_but_different_spend"], 317)
        prefix = self.arm(4, "sequential", "independent", "own")
        full = self.arm(32, "sequential", "independent", "own")
        self.assertEqual(prefix["verified_stage_union"], full["verified_stage_union"])
        self.assertEqual((prefix["spent_scripted_units"], full["spent_scripted_units"]), (4, 18))
        self.assertTrue(prefix["budget_stopped"])
        self.assertFalse(full["budget_stopped"])
        self.assertIsNone(prefix["against_independent_at_same_access"]["completed_pair_stage_difference"])

    def test_completed_equal_utility_can_have_unequal_cost(self):
        arm = self.arm(32, "sequential", "peers", "shared")
        self.assertEqual(arm["against_independent_at_same_access"], {
            "achieved_stage_difference": 0,
            "completed_pair_stage_difference": 0,
            "spent_scripted_unit_difference": 3,
        })

    def test_wrong_reference_digest_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "input digest mismatch"):
            paired_frontier.summarize("0" * 64)

    def test_archived_arms_require_equal_caps_and_keep_stopped_costs(self):
        with TemporaryDirectory() as folder:
            path = Path(folder)
            selections = {}
            for cap in (19, 21):
                trace = path / f"cap-{cap}.json"
                raw = (json.dumps(topology_transfer.compare(budget=cap), indent=2, sort_keys=True) + "\n").encode()
                trace.write_bytes(raw)
                selections[cap] = (trace, sha256(raw).hexdigest())
            common = {
                "treatment": selections[21], "regime": "sequential", "seed": 0,
                "treatment_arm": ("peers", "shared"), "control_arm": ("peers", "own"),
            }
            with self.assertRaisesRegex(ValueError, "different resource caps"):
                paired_frontier.verify_pair(control=selections[19], **common)
            report = paired_frontier.verify_pair(control=selections[21], **common)
            self.assertEqual((report["treatment"]["cap"], report["control"]["cap"]), (21, 21))
            self.assertEqual(report["treatment"]["spent_scripted_units"], 20)
            self.assertEqual(report["treatment"]["unused_scripted_units"], 1)
            self.assertIsNotNone(report["treatment"]["stopped_on_event"])
            self.assertEqual(report["control"]["spent_scripted_units"], 19)
            self.assertEqual(report["control"]["unused_scripted_units"], 2)
            self.assertEqual(report["comparison"], {
                "achieved_stage_difference": 1,
                "completed_pair_stage_difference": None,
                "spent_scripted_unit_difference": 1,
            })
