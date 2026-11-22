from copy import deepcopy
import json
import subprocess
import sys
import unittest

from lab import replication_coverage as audit
from lab.tests import test_replication_pairing as fixtures


class ReplicationCoverageTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture = fixtures.ReplicationPairingTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)

    def evidence(self, *, reference=True):
        fixture = self.fixture
        inputs = fixture._inputs()
        if not reference:
            del inputs["reference"]
        self.document = {
            "schema": audit.SCHEMA,
            "line": inputs["line"],
            "schedule_pins": {name: value[1] for name, value in inputs.items() if name != "line"},
            "rows": [{
                "task_id": row["task_id"], "replicate_id": row["replicate_id"],
                "roles": {
                    role: {arm: {"state": "observed", "usage": dict.fromkeys(audit.RESOURCES, 0)}
                           for arm in audit.ARMS}
                    for role in inputs if role not in ("line", "splits")
                },
            } for row in fixture.rows],
        }
        return inputs

    def pinned(self):
        return self.fixture._pin("coverage", json.dumps(self.document))

    def test_cli_reports_one_cluster_and_keeps_partial_cost_unavailable(self):
        inputs = self.evidence()
        arm = self.document["rows"][1]["roles"]["recalibrated"]["comparator"]
        arm["state"] = "stopped"
        arm["usage"].update(input_tokens=15, gpu_wall_ns=None)
        args = [sys.executable, "-m", "lab.replication_coverage", "--line", inputs["line"]]
        for field in ("splits", "unchanged", "recalibrated", "reference", "coverage"):
            path, pin = self.pinned() if field == "coverage" else inputs[field]
            args.extend((f"--{field}", str(path), pin))
        process = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(process.returncode, 0, process.stderr)
        report = json.loads(process.stdout)
        cluster, = report["linked_clusters"]
        self.assertEqual(len(cluster["assignments"]), 3)
        self.assertEqual(cluster["complete_pairs"], {"reference": 3, "unchanged": 3, "recalibrated": 2})
        self.assertEqual(report["clusters_with_all_declared_pairs_observed"], 0)
        self.assertEqual(cluster["assignments"][1]["receipts"]["recalibrated"]["comparator"]["state"], "stopped")
        usage = report["usage_by_role_and_arm"]["recalibrated"]["comparator"]
        self.assertEqual(usage["gpu_wall_ns"],
                         {"known_subtotal": 0, "unavailable_records": 1, "complete_total": None})
        self.assertEqual(usage["input_tokens"]["complete_total"], 15)
        self.assertEqual(usage["output_tokens"]["complete_total"], 0)
        self.assertFalse(report["scientific_acceptance"])

    def test_relabeling_aliases_cannot_split_a_linked_cluster(self):
        fixture = self.fixture
        fixture.rows[1]["block_id"] = "separate-rerun-block"
        first, _, third = fixture.rows
        for field in audit.pairing.MATCH_FIELDS:
            third[field] = first[field]
        fixture.splits["members"][-1]["group_id"] = "separate-task-group"
        report = audit.verify(**self.evidence(), coverage=self.pinned())
        self.assertEqual(len(report["linked_clusters"]), 1)
        self.assertEqual(len(report["linked_clusters"][0]["assignments"]), 3)

    def test_equal_role_totals_keep_different_per_assignment_usage(self):
        inputs = self.evidence()
        for row in self.document["rows"]:
            row["roles"]["reference"]["technique"]["usage"]["input_tokens"] = 5
        balanced = audit.verify(**inputs, coverage=self.pinned())
        for row, tokens in zip(self.document["rows"], (9, 1, 5), strict=True):
            row["roles"]["reference"]["technique"]["usage"]["input_tokens"] = tokens
        redistributed = audit.verify(**inputs, coverage=self.pinned())
        self.assertEqual(redistributed["usage_by_role_and_arm"], balanced["usage_by_role_and_arm"])
        receipts = redistributed["linked_clusters"][0]["assignments"]
        self.assertEqual([row["receipts"]["reference"]["technique"]["usage"]["input_tokens"]
                          for row in receipts], [9, 1, 5])

    def test_separate_custody_group_and_distinct_bytes_can_form_another_cluster(self):
        self.fixture.splits["members"][-1]["group_id"] = "new-task-group"
        report = audit.verify(**self.evidence(), coverage=self.pinned())
        self.assertEqual([len(cluster["assignments"]) for cluster in report["linked_clusters"]], [2, 1])

    def test_declared_roles_stay_visible_without_common_reference(self):
        report = audit.verify(**self.evidence(reference=False), coverage=self.pinned())
        self.assertEqual(report["declared_roles"], ("unchanged", "recalibrated"))
        self.assertEqual(report["clusters_with_all_declared_pairs_observed"], 1)
        self.assertEqual(report["pairing"]["cross_family_pairing"], "withheld_missing_reference_holdout")

    def limits(self):
        return {
            "schema": audit.LIMIT_SCHEMA,
            "line": self.document["line"],
            "schedule_pins": self.document["schedule_pins"],
            "per_assignment_limits": {
                role: {row["block_id"]: {"calls": 2, "input_tokens": 10, "gpu_wall_ns": 100}
                       for row in self.fixture.rows}
                for role in self.document["schedule_pins"] if role != "splits"
            },
        }

    def test_pinned_limits_distinguish_observed_coverage_from_eligible_pairs(self):
        inputs = self.evidence()
        first, second, third = [row["roles"]["recalibrated"] for row in self.document["rows"]]
        first["technique"]["usage"].update(calls=3, input_tokens=11, gpu_wall_ns=20)
        second["technique"].update(state="stopped")
        second["technique"]["usage"].update(calls=3, input_tokens=None, gpu_wall_ns=20)
        third["technique"]["usage"].update(calls=2, input_tokens=10, gpu_wall_ns=100)
        self.document["rows"][2]["roles"]["reference"]["comparator"]["usage"]["gpu_wall_ns"] = None
        witness = self.fixture._pin("limits", json.dumps(self.limits()))
        inputs.update(coverage=self.pinned(), limits=witness)
        args = [sys.executable, "-B", "-m", "lab.replication_coverage", "--line", inputs["line"]]
        for field in ("splits", "unchanged", "recalibrated", "reference", "coverage", "limits"):
            path, pin = inputs[field]
            args.extend((f"--{field}", str(path), pin))
        result = subprocess.run(args, check=True, capture_output=True, text=True)
        report = json.loads(result.stdout)
        self.assertEqual(report["per_assignment_limits_sha256"], witness[1])
        cluster, = report["linked_clusters"]
        self.assertEqual(cluster["complete_pairs"]["recalibrated"], 2)
        self.assertEqual(cluster["observed_pairs_within_limits"]["recalibrated"], 1)
        self.assertEqual(cluster["complete_pairs"]["reference"], 3)
        self.assertEqual(cluster["observed_pairs_within_limits"]["reference"], 2)
        checks = [row["per_assignment_limit_checks"]["recalibrated"]["technique"]
                  for row in cluster["assignments"]]
        self.assertEqual(checks, [
            {"exceeded": ["calls", "input_tokens"], "unavailable": [], "eligible": False},
            {"exceeded": ["calls"], "unavailable": ["input_tokens"], "eligible": False},
            {"exceeded": [], "unavailable": [], "eligible": True},
        ])
        usage = report["usage_by_role_and_arm"]["recalibrated"]["technique"]
        self.assertEqual(usage["calls"]["complete_total"], 8)
        self.assertIsNone(usage["input_tokens"]["complete_total"])
        self.assertFalse(report["scientific_acceptance"])

    def test_limits_must_bind_the_exact_schedule_and_all_blocks(self):
        inputs = self.evidence()
        limits = self.limits()
        limits["per_assignment_limits"]["reference"].pop("block-case-a")
        witness = self.fixture._pin("limits", json.dumps(limits))
        with self.assertRaisesRegex(ValueError, "invalid limit blocks fields"):
            audit.verify(**inputs, coverage=self.pinned(), limits=witness)
        limits["schedule_pins"] = {**limits["schedule_pins"], "reference": "f" * 64}
        witness = self.fixture._pin("limits", json.dumps(limits))
        with self.assertRaisesRegex(ValueError, "limits refer to different pairing evidence"):
            audit.verify(**inputs, coverage=self.pinned(), limits=witness)

    def test_missing_duplicate_and_crossed_coverage_refused(self):
        inputs = self.evidence()
        missing = self.document["rows"].pop()
        with self.assertRaisesRegex(ValueError, "retain every matched assignment"):
            audit.verify(**inputs, coverage=self.pinned())
        self.document["rows"].append(deepcopy(self.document["rows"][0]))
        with self.assertRaisesRegex(ValueError, "extra or repeated"):
            audit.verify(**inputs, coverage=self.pinned())
        self.document["rows"][-1] = missing
        self.document["schedule_pins"]["unchanged"] = "a" * 64
        with self.assertRaisesRegex(ValueError, "different pairing evidence"):
            audit.verify(**inputs, coverage=self.pinned())
