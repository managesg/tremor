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
