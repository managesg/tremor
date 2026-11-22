from collections import Counter
from fractions import Fraction
import hashlib
import json
import unittest
from unittest.mock import patch

from lab.quantum import topology_audit, topology_transfer
from lab.quantum.topology_audit import audit
from lab.quantum.topology_transfer import compare
from lab.quantum.transfer_fixtures import Fixture, Stage


class TopologyAuditTests(unittest.TestCase):
    def test_solver_with_local_partial_marks_still_requires_all_shards(self):
        fixture = Fixture("complementary", (Stage(
            "join", 3, 1, Fraction(1), (("a", (0,)), ("b", (1,))), ("a", "b"),
        ),))
        with patch.object(topology_transfer, "development_fixture", return_value=fixture), \
                patch.object(topology_audit, "development_fixture", return_value=fixture):
            trace = compare((("complementary", 0),))
            cells = audit(json.dumps(trace).encode())["cases"][0]["cells"]
            shared = next(row for row in cells if (row["mode"], row["access"]) == ("independent", "shared"))
            self.assertEqual(shared["stage_union"], ["join"])
            arm = next(row for row in trace["cases"][0]["arms"]
                       if (row["mode"], row["evidence_access"]) == ("independent", "shared"))
            work = next(row for row in arm["trace"] if row["kind"] == "work" and row["task"] == "join")
            work["inputs"].pop()
            with self.assertRaisesRegex(ValueError, "bad work receipt inputs"):
                audit(json.dumps(trace).encode())

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
        for budget in range(1, 32):
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

    def test_refuses_extra_projected_worker_metadata_at_fresh_digest(self):
        for kind in ("read", "work"):
            with self.subTest(kind=kind):
                report = compare()
                case = next(item for item in report["cases"]
                            if item["regime"] == "complementary" and item["development_seed"] == 9)
                arm = next(item for item in case["arms"]
                           if item["mode"] == "fixed_lead" and item["evidence_access"] == "own")
                row = next(event for event in arm["trace"] if event["kind"] == kind)
                row["projected_input"] = {
                    "full_marked_indices": [0, 1], "threshold_answer": [1, "1"], "development_seed": 9,
                }
                raw = json.dumps(report).encode()
                with self.assertRaisesRegex(ValueError, f"unexpected {kind} event fields"):
                    audit(raw, expected_sha256=hashlib.sha256(raw).hexdigest())

    def test_refuses_premature_nonstopped_merge_at_fresh_digest(self):
        report = compare()
        case = next(item for item in report["cases"] if item["regime"] == "sequential")
        arm = next(item for item in case["arms"] if item["mode"] == "peers" and item["evidence_access"] == "shared")
        prefix = [event for event in arm["trace"] if event["round"] == 0]
        union = ["scout"]
        trace = prefix + [{"event": len(prefix), "round": 1, "kind": "merge", "actor": "verifier",
                           "cost": 1, "verified_union": union}]
        costs = Counter(event["kind"] for event in trace)
        spent = sum(costs.values())
        arm.update(trace=trace, verified_union=union, verified_stage_union=union, utility=1, stage_utility=1,
                   costs=dict(costs), spent=spent, unused=arm["budget"] - spent, valid_integrations=0,
                   blocked_dependencies=costs["blocked"], gain_over_independent_union=0,
                   gain_over_independent_at_same_access=-2)
        raw = json.dumps(report).encode()
        with self.assertRaisesRegex(ValueError, "non-stopped trace did not complete all planned rounds"):
            audit(raw, expected_sha256=hashlib.sha256(raw).hexdigest())

    def test_refuses_omitted_scheduled_work_even_with_all_reads_and_fresh_digest(self):
        report = compare()
        case = next(item for item in report["cases"] if item["regime"] == "sequential")
        arm = next(item for item in case["arms"] if item["mode"] == "peers" and item["evidence_access"] == "shared")
        trace = arm["trace"]
        removed_work = {event["event"] for event in trace if event["kind"] == "work"
                        and event["task"] in {"confirm", "final"}}
        removed = removed_work | {event["event"] for event in trace if
                                  (event["kind"] == "claim" and event["task"] in {"confirm", "final"})
                                  or (event["kind"] == "verify" and event["submission"] in removed_work)}
        kept = [event for event in trace if event["event"] not in removed]
        new_ordinals = {event["event"]: ordinal for ordinal, event in enumerate(kept)}
        for event in kept:
            event["event"] = new_ordinals[event["event"]]
            for field in event.keys() & {"visible", "inputs"}:
                event[field] = [new_ordinals[ref] for ref in event[field] if ref not in removed]
            if "submission" in event:
                event["submission"] = new_ordinals[event["submission"]]
        union = ["scout"]
        kept[-1]["verified_union"] = union
        costs = Counter(event["kind"] for event in kept)
        spent = sum(costs.values())
        self.assertEqual(costs["read"], 9)
        self.assertEqual(kept[-1]["round"], 3)
        self.assertFalse(arm["budget_stopped"])
        arm.update(trace=kept, verified_union=union, verified_stage_union=union, utility=1, stage_utility=1,
                   costs=dict(costs), spent=spent, unused=arm["budget"] - spent, valid_integrations=0,
                   blocked_dependencies=costs["blocked"], gain_over_independent_union=0,
                   gain_over_independent_at_same_access=-2)
        raw = json.dumps(report).encode()
        with self.assertRaisesRegex(ValueError, "trace differs from the complete public scripted dispatch"):
            audit(raw, expected_sha256=hashlib.sha256(raw).hexdigest())

    def test_nondefault_public_case_subset_and_cap_replay(self):
        report = compare((("complementary", 31), ("sequential", 11)), budget=21)
        raw = json.dumps(report).encode()
        result = audit(raw, expected_sha256=hashlib.sha256(raw).hexdigest())
        self.assertEqual([(case["regime"], case["seed"]) for case in result["cases"]],
                         [("complementary", 31), ("sequential", 11)])

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

    def test_rejects_extra_plan_fields_and_assignments_even_with_fresh_digests(self):
        for method, field, value, message in (
            ("row", "raw_answers", {"a": [0]}, "unexpected plan event fields"),
            ("assignments", "outsider", "shard/join/a", "plan assignments differ"),
            ("assignments", "c", "join", "plan assignments differ"),
        ):
            with self.subTest(method=method, field=field):
                report = compare()
                arm = next(arm for arm in report["cases"][0]["arms"]
                           if arm["mode"] == "fixed_lead" and arm["evidence_access"] == "own")
                plan = next(row for row in arm["trace"] if row["kind"] == "plan")
                self.assertEqual(plan["assignments"], {"a": "shard/join/a", "b": "shard/join/b"})
                target = plan if method == "row" else plan["assignments"]
                target[field] = value
                raw = json.dumps(report).encode()
                with self.assertRaisesRegex(ValueError, message):
                    audit(raw, expected_sha256=hashlib.sha256(raw).hexdigest())


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
