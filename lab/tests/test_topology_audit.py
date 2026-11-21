import hashlib
import json
import unittest

from lab.quantum.topology_audit import audit
from lab.quantum.topology_transfer import compare


class TopologyAuditTests(unittest.TestCase):
    def test_serialized_full_grid_and_external_digest(self):
        raw = json.dumps(compare()).encode()
        report = audit(raw, expected_sha256=hashlib.sha256(raw).hexdigest())
        cells = [cell for case in report["cases"] for cell in case["cells"]]
        self.assertTrue(report["external_digest_checked"])
        self.assertFalse(report["actors_authenticated"])
        self.assertEqual(len(cells), 32)
        self.assertEqual(sum(c["events"] for c in cells), 665)
        self.assertEqual(sum(c["verified_work"] for c in cells), 77)
        self.assertEqual(sum(c["spent"] for c in cells), 665)
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            audit(raw + b" ", expected_sha256=report["sha256"])

    def test_budget_boundaries_and_stage_utility(self):
        for budget in (1, 3, 13, 22):
            with self.subTest(budget=budget):
                result = audit(json.dumps(compare(budget=budget)).encode())
                self.assertTrue(all(0 < c["spent"] <= budget for case in result["cases"] for c in case["cells"]))
        report = compare()
        report["cases"][0]["arms"][4]["verified_stage_union"].append("shard/join/a")
        with self.assertRaisesRegex(ValueError, "verified union or utility"):
            audit(json.dumps(report).encode())

    def test_refuses_nonvisible_and_nonchronological_receipts(self):
        for access, replacement in (("own", 2), ("shared", 100)):
            report = compare()
            arm = next(a for a in report["cases"][0]["arms"]
                       if a["mode"] == "independent" and a["evidence_access"] == access)
            read = next(row for row in arm["trace"] if row["kind"] == "read"
                        and row["round"] == 1 and row["actor"] == "c")
            read["visible"] = [replacement]
            with self.assertRaisesRegex(ValueError, "unauthorized or premature"):
                audit(json.dumps(report).encode())

    def test_redecodes_mathematics_and_receipt_ownership(self):
        report = compare()
        arm = report["cases"][1]["arms"][4]
        work = next(row for row in arm["trace"] if row["kind"] == "work" and row["task"] == "join")
        original = work["answer"]
        work["answer"] = None
        with self.assertRaisesRegex(ValueError, "work verdict"):
            audit(json.dumps(report).encode())
        work["answer"] = original
        shard = next(row for row in arm["trace"] if row["kind"] == "work" and row["task"] == "shard/join/b")
        shard["actor"] = "a"
        with self.assertRaisesRegex(ValueError, "wrong shard publisher"):
            audit(json.dumps(report).encode())

    def test_cost_and_lead_authority_mutations_fail(self):
        report = compare()
        arm = report["cases"][0]["arms"][1]
        plan = next(row for row in arm["trace"] if row["kind"] == "plan")
        plan["actor"] = "c"
        with self.assertRaisesRegex(ValueError, "plan authority"):
            audit(json.dumps(report).encode())
        plan["actor"] = "a"
        plan["cost"] = 0
        with self.assertRaisesRegex(ValueError, "event cost"):
            audit(json.dumps(report).encode())


    def test_rejects_unknown_actors_for_worker_metadata(self):
        for kind, budget, message in (
            ("blocked", 32, "invalid dependency or conflict actor"),
            ("claim_conflict", 32, "invalid dependency or conflict actor"),
            ("budget_stop", 1, "invalid read stop actor"),
        ):
            with self.subTest(kind=kind):
                report = compare(budget=budget)
                row = next(row for case in report["cases"] for arm in case["arms"]
                           for row in arm["trace"] if row["kind"] == kind)
                row["actor"] = "outsider"
                with self.assertRaisesRegex(ValueError, message):
                    audit(json.dumps(report).encode())

    def test_rotating_handoff_cannot_be_substituted_or_miscounted(self):
        report = compare()
        arm = report["cases"][0]["arms"][2]
        handoff = next(row for row in arm["trace"] if row["kind"] == "handoff")
        handoff["kind"] = "blocked"
        with self.assertRaisesRegex(ValueError, "missing rotating handoff"):
            audit(json.dumps(report).encode())
        handoff["kind"] = "handoff"
        arm["handoffs"] = 1
        with self.assertRaisesRegex(ValueError, "incorrect accounting"):
            audit(json.dumps(report).encode())

    def test_numeric_summary_fields_require_integers(self):
        for field, value, message in (
            ("utility", 2.0, "verified union or utility"),
            ("stage_utility", False, "verified union or utility"),
            ("spent", 17.0, "incorrect accounting"),
            ("gain_over_independent_union", False, "incorrect comparison baseline"),
        ):
            with self.subTest(field=field):
                report = compare()
                arm = report["cases"][0]["arms"][0]
                self.assertEqual(arm[field], value)
                arm[field] = value
                with self.assertRaisesRegex(ValueError, message):
                    audit(json.dumps(report).encode())


if __name__ == "__main__":
    unittest.main()
