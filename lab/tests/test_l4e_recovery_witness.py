"""Exercise the paired L4-E readout with exact per-arm recovery histories."""

import json
import subprocess
import sys
import unittest

from lab import l4e_matched_outcomes as audit
from lab.tests import test_l4e_matched_outcomes as fixtures


class L4ERecoveryWitnessTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.L4EMatchedOutcomesTests()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.setUp()
        self.plan = self.fixture.plan
        self.plan.update(schema=audit.RECOVERY_PLAN_SCHEMA, recovery_hold_nights=2)
        self.rows = self.fixture.rows
        self.hold = 2
        self.history = [
            {**self.fixture.identity, "arm": arm, "terminal": "window_complete",
             "samples": [{"night": night, "predicate": threshold is not None and night >= threshold}
                         for night in range(7)]}
            for arm, threshold in (("adapter", None), ("context", 2))
        ]

    def inputs(self):
        plan, plan_pin = self.fixture.write("plan.json", self.plan)
        observed, observed_pin = self.fixture.write("outcomes.json", {
            "schema": audit.OBSERVATION_SCHEMA,
            **self.fixture.pins, "plan_sha256": plan_pin, "rows": self.rows,
        })
        path, pin = self.fixture.write("recovery.json", {
            "schema": "tremor.l4e_matched_recovery_witness.v1",
            "plan_sha256": plan_pin, "observations_sha256": observed_pin,
            "hold": self.hold, "rows": self.history,
        })
        return plan, observed, {"plan_sha256": plan_pin, "observations_sha256": observed_pin,
                                "recovery_witness": (path, pin)}

    def verify(self):
        plan, observed, options = self.inputs()
        return audit.verify(plan, observed, **options)

    def test_raw_recovery_witness_works_through_cli(self):
        plan, observed, options = self.inputs()
        command = [sys.executable, "-B", "-m", "lab.l4e_matched_outcomes", str(plan), str(observed),
                   "--plan-sha256", options["plan_sha256"], "--observations-sha256", options["observations_sha256"],
                   "--recovery-witness", *map(str, options["recovery_witness"])]
        process = subprocess.run(command, capture_output=True, text=True, timeout=10, check=False)
        self.assertEqual(process.returncode, 0, process.stderr)
        report = json.loads(process.stdout)
        self.assertEqual(report["recovery"]["adapter_over_context"], "2")
        self.assertEqual(report["recovery_witness"]["matched_arm_histories"], 2)
        self.assertFalse(report["scientific_acceptance"])

    def test_operational_stop_after_confirmation_keeps_confirmation_and_terminal(self):
        context = self.history[1]
        context["terminal"] = "operational_stop"
        context["samples"] = context["samples"][:4]
        self.rows[1]["recovery"]["observed_through_night"] = 3
        result = self.verify()
        matched = result["recovery_witness"]["histories"][1]
        self.assertEqual((matched["classification"], matched["terminal"]), ("recovered", "operational_stop"))
        self.assertEqual(matched["confirmation_night"], 3)
        self.assertEqual(result["recovery"]["adapter_over_context"], "2")

    def test_gap_before_candidate_withholds_recovery(self):
        self.history[1]["samples"][1]["predicate"] = None
        with self.assertRaisesRegex(ValueError, "differs from observed confirmation"):
            self.verify()
        self.rows[1]["recovery"].update(state="unavailable", confirmation_night=None,
                                       observed_through_night=0, reason="night gap")
        result = self.verify()
        matched = result["recovery_witness"]["histories"][1]
        self.assertEqual((matched["classification"], matched["candidate_confirmation_night"]),
                         ("incomplete_followup", 3))
        self.assertEqual(matched["continuous_through_night"], 0)
        self.assertEqual(matched["latest_sampled_night"], 6)
        self.assertIsNone(result["recovery"]["adapter_over_context"])
        self.assertEqual(result["norm"]["adapter_minus_context"], "1")

    def test_no_observed_night_keeps_follow_up_unavailable(self):
        self.history[0].update(terminal="operational_stop", samples=[])
        self.rows[0]["recovery"].update(state="unavailable", observed_through_night=None, reason="no night")
        matched = self.verify()["recovery_witness"]["histories"][0]
        self.assertIsNone(matched["continuous_through_night"])
        self.assertIsNone(matched["latest_sampled_night"])
        self.assertEqual(matched["known_nights"], 0)

    def test_short_window_is_not_censoring(self):
        self.history[0]["samples"].pop()
        with self.assertRaisesRegex(ValueError, "differs from observed confirmation"):
            self.verify()

    def test_freshly_pinned_changed_hold_and_crossed_arm_are_refused(self):
        self.hold = 1
        with self.assertRaisesRegex(ValueError, "hold differs from frozen plan"):
            self.verify()
        self.hold = 2
        self.history[1]["task_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "mismatched recovery history"):
            self.verify()

    def test_new_schema_cannot_skip_history(self):
        plan, observed, options = self.inputs()
        del options["recovery_witness"]
        with self.assertRaisesRegex(ValueError, "plan and recovery witness"):
            audit.verify(plan, observed, **options)
