from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lab import l4e_matched_outcomes as audit


class L4EMatchedOutcomesTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.identity = {"pair_id": "trial-1", "task_sha256": "a" * 64, "seed_sha256": "b" * 64}
        self.pins = {"scorer_sha256": "c" * 64, "l4e_receipt_sha256": "d" * 64,
                     "content_parity_sha256": "e" * 64}
        self.plan = {"schema": audit.PLAN_SCHEMA, "scope": "scripted_development", **self.pins,
                     "horizon_nights": 6, "pairs": [self.identity]}
        self.rows = [
            self.arm("adapter", True, state="right_censored", night=None, through=6),
            self.arm("context", False, state="recovered", night=3, through=6),
        ]

    def arm(self, arm, passed, *, state, night, through, reason=None):
        return {**self.identity, "arm": arm, "norm": {"passed": passed, "reason": None},
                "recovery": {"state": state, "confirmation_night": night,
                             "observed_through_night": through, "reason": reason},
                "usage": {"input_tokens": 4, "output_tokens": 2, "gpu_wall_ns": 8}}

    def write(self, name, content):
        path = self.root / name
        raw = json.dumps(content).encode()
        path.write_bytes(raw)
        return path, sha256(raw).hexdigest()

    def verify(self, pin_changes=None):
        plan, plan_pin = self.write("plan.json", self.plan)
        recorded, actual_pin = self.write("recorded.json", {"schema": audit.OBSERVATION_SCHEMA, **self.pins,
                                                          "plan_sha256": plan_pin, "rows": self.rows}
                                          | (pin_changes or {}))
        return audit.verify(plan, recorded, plan_sha256=plan_pin, observations_sha256=actual_pin)

    def test_matched_norm_gain_and_ratio_of_restricted_night_means(self):
        result = self.verify()
        self.assertEqual(result["norm"]["adapter_minus_context"], "1")
        self.assertEqual(result["recovery"]["adapter_over_context"], "2")
        self.assertEqual(result["recovery"]["means"], {"adapter": "6", "context": "3"})
        self.assertFalse(result["settlement_verified"])

    def test_shorter_follow_up_and_unknown_cost_remain_unavailable(self):
        self.rows[0]["recovery"]["observed_through_night"] = 4
        with self.assertRaisesRegex(ValueError, "administrative censoring"):
            self.verify()
        self.rows[0]["recovery"].update(state="unavailable", reason="operational stop")
        self.rows[0]["usage"]["gpu_wall_ns"] = None
        result = self.verify()
        self.assertEqual(result["norm"]["adapter_minus_context"], "1")
        self.assertIsNone(result["recovery"]["adapter_over_context"])
        usage = result["declared_usage"]["adapter"]["gpu_wall_ns"]
        self.assertEqual(usage, {"known_subtotal": 0, "unavailable_records": 1, "complete_total": None})

    def test_zero_context_mean_is_an_unavailable_ratio(self):
        self.rows[1]["recovery"]["confirmation_night"] = 0
        recovery = self.verify()["recovery"]
        self.assertEqual(recovery["adapter_minus_context"], "6")
        self.assertIsNone(recovery["adapter_over_context"])
        self.assertEqual(recovery["unavailable_reason"], "zero_context_mean")

    def test_rejects_crossed_assignment_and_newly_pinned_wrong_scorer(self):
        with self.assertRaisesRegex(ValueError, "scorer or L4-E receipt differs"):
            self.verify({"scorer_sha256": "0" * 64})
        self.rows[0]["task_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "mismatched observed arm"):
            self.verify()
        self.rows.pop(0)
        with self.assertRaisesRegex(ValueError, "record both arms"):
            self.verify()

    def capture(self, kind, value):
        raw = value if type(value) is bytes else json.dumps(value, sort_keys=True).encode()
        pin = sha256(raw).hexdigest()
        folder = self.root / kind
        folder.mkdir(exist_ok=True)
        (folder / pin).write_bytes(raw)
        return pin

    def norm_inputs(self):
        scorer = self.capture("norm-scorer", b"synthetic captured scorer artifact")
        self.pins["scorer_sha256"] = self.plan["scorer_sha256"] = scorer
        plan, plan_pin = self.write("plan.json", self.plan)
        binding = {"plan_sha256": plan_pin, "scorer_sha256": scorer, "endpoint": audit.NORM_ENDPOINT}
        observed, observed_pin = self.write("norm-outcomes.json", {
            "schema": audit.OBSERVATION_SCHEMA, **self.pins, "plan_sha256": plan_pin, "rows": self.rows,
        })
        records = []
        for row in self.rows:
            scope = {field: row[field] for field in (*audit.IDENTITY, "arm")} | {"plan_sha256": plan_pin}
            frame_pin = grade_pin = None
            if row["norm"]["passed"] is not None:
                frame_pin = self.capture("norm-frame", {"schema": audit.NORM_FRAME_SCHEMA, **scope,
                                                        "frame": {"public_proposal": "synthetic input"}})
                grade_pin = self.capture("norm-grade", {"schema": audit.NORM_GRADE_SCHEMA, **scope,
                                                        "scorer_sha256": scorer, "frame_sha256": frame_pin,
                                                        "endpoint": audit.NORM_ENDPOINT, "norm": row["norm"]})
            records.append({field: row[field] for field in (*audit.IDENTITY, "arm")} | {
                "reason": row["norm"]["reason"], "frame_sha256": frame_pin, "grade_sha256": grade_pin,
            })
        witness = {"schema": audit.NORM_WITNESS_SCHEMA, **binding, "observations_sha256": observed_pin, "rows": records}
        return plan, observed, witness

    def verify_norm(self, plan, observed, witness):
        path, pin = self.write("norm-witness.json", witness)
        return audit.verify(plan, observed, plan_sha256=witness["plan_sha256"],
                            observations_sha256=witness["observations_sha256"], norm_witness=(self.root, path, pin))

    def test_captured_norms_bind_both_arms_without_changing_recovery(self):
        report = self.verify_norm(*self.norm_inputs())
        self.assertEqual(report["norm"]["adapter_minus_context"], "1")
        self.assertEqual(report["recovery"]["adapter_over_context"], "2")
        self.assertEqual(report["norm_witness"]["verified_grade_captures"], 2)
        self.assertEqual(report["norm_witness"]["endpoint"], "proposal_norm_allows")
        self.assertFalse(report["norm_witness"]["grader_execution_verified"])
        self.assertFalse(report["scientific_acceptance"])

    def test_freshly_pinned_flip_or_crossed_grade_cannot_change_norm(self):
        plan, observed, witness = self.norm_inputs()
        original = witness["rows"][0]["grade_sha256"]
        witness["rows"][0]["grade_sha256"] = witness["rows"][1]["grade_sha256"]
        with self.assertRaisesRegex(ValueError, "norm grade differs"):
            self.verify_norm(plan, observed, witness)
        witness["rows"][0]["grade_sha256"] = original

        declaration = json.loads(observed.read_bytes())
        declaration["rows"][0]["norm"]["passed"] = False
        changed, new_pin = self.write("changed.json", declaration)
        witness["observations_sha256"] = new_pin
        without_witness = audit.verify(plan, changed, plan_sha256=witness["plan_sha256"], observations_sha256=new_pin)
        self.assertEqual(without_witness["norm"]["adapter_minus_context"], "0")
        with self.assertRaisesRegex(ValueError, "norm grade differs"):
            self.verify_norm(plan, changed, witness)

    def test_retains_unavailable_norm_and_requires_all_scheduled_arms(self):
        self.rows[0]["norm"].update(passed=None, reason="no captured proposal")
        plan, observed, witness = self.norm_inputs()
        report = self.verify_norm(plan, observed, witness)
        self.assertEqual(report["norm_witness"]["verified_grade_captures"], 1)
        self.assertEqual(report["norm_witness"]["unavailable_arms"], 1)
        self.assertIsNone(report["norm"]["adapter_minus_context"])
        self.assertEqual(report["recovery"]["adapter_over_context"], "2")
        witness["rows"].pop()
        with self.assertRaisesRegex(ValueError, "retain every scheduled arm"):
            self.verify_norm(plan, observed, witness)
