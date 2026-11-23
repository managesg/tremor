import hashlib
import json
import unittest

from lab import l5_carrier_fixture
from lab.l5_dispatch_carriers import compare


class L5DispatchCarrierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = compare()
        cls.rows = {(row["carrier"], row["disrupted"]): row for row in cls.result["rows"]}

    def test_context_disruption_changes_the_rendered_prompt(self):
        clean = self.rows["context", False]
        disrupted = self.rows["context", True]
        self.assertEqual(clean["prompts"][:2], disrupted["prompts"][:2])
        self.assertNotEqual(clean["prompts"][2:], disrupted["prompts"][2:])
        for row in self.rows.values():
            self.assertEqual(row["taskset"], clean["taskset"])
            self.assertEqual(row["counts"]["context_bytes"], clean["counts"]["context_bytes"])
            self.assertEqual(row["counts"]["read_attempts"], 4)
            self.assertEqual(row["counts"]["work_attempts"], 3)
            self.assertEqual(len([e for e in row["board_trace"] if e["type"] == "end_round"]), 4)

    def test_same_unclaimed_attempt_is_executed_or_refused_at_dispatch(self):
        context = self.rows["context", True]
        code = self.rows["code", False]
        context_attempt, = [e for e in context["dispatches"]
                            if e["action"]["agent"] == "a1" and e["action"]["type"] == "work"]
        code_attempt, = [e for e in code["dispatches"]
                         if e["action"]["agent"] == "a1" and e["action"]["type"] == "work"]
        self.assertEqual(context_attempt["action"], code_attempt["action"])
        self.assertEqual(context_attempt["status"], "violation_executed")
        self.assertEqual(code_attempt["status"], "refused")
        self.assertEqual(context_attempt["reason"], code_attempt["reason"])
        self.assertIs(context["cell_events"][0]["costs_turn"], False)
        self.assertIs(code["cell_events"][0]["costs_turn"], True)
        self.assertEqual(context["score"]["distinct_passing"], 3)
        self.assertEqual(code["score"]["distinct_passing"], 2)

    def test_legitimate_work_admitted_and_code_sham_preserves_results(self):
        for row in self.rows.values():
            control, = [e for e in row["work"] if e["action"]["agent"] == "a2"]
            self.assertTrue(control["norm_allows"])
            self.assertTrue(control["accepted"])
            self.assertEqual(row["counts"]["blocked_norm_allowed_work"], 0)
        clean = self.rows["code", False]
        sham = self.rows["code", True]
        self.assertEqual(clean["board_head"], sham["board_head"])
        self.assertEqual(clean["prompts"], sham["prompts"])
        self.assertEqual(clean["cell_events"], sham["cell_events"])

    def test_replay_is_deterministic_and_preserves_original_fixture(self):
        self.assertEqual(self.result, compare())
        original = json.dumps(l5_carrier_fixture.compare(), indent=2, sort_keys=True) + "\n"
        self.assertEqual(hashlib.sha256(original.encode()).hexdigest(),
                         "882118126039067194e74342903405b1fc8c290a00307bf64654657b8d347077")


if __name__ == "__main__":
    unittest.main()
