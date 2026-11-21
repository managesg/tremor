import unittest

from lab.quantum import cap_frontier


class GroverCapFrontierTests(unittest.TestCase):
    def test_exact_audited_frontier_matches_the_retained_full_cap(self):
        result = cap_frontier.summarize()
        self.assertEqual(result["audited_cells"], 1024)
        self.assertEqual(result["reference_sha256"], cap_frontier.REFERENCE_SHA256)
        self.assertEqual(result["first_cap_with_exact_reference_unions"], 27)
        self.assertIs(result["authorizes_execution"], False)
        self.assertEqual(result["units"], "abstract_scripted_cost_units")
        rows = {row["cap"]: row for row in result["caps"]}
        self.assertEqual([cap for cap, row in rows.items() if not row["different_cells"]], list(range(27, 33)))
        self.assertEqual(rows[26]["different_cells"], [{
            "regime": "sequential", "seed": 0, "mode": "rotating_lead", "access": "shared",
            "stage_union": ["confirm", "scout"], "reference_stage_union": ["confirm", "final", "scout"],
        }])
        self.assertEqual(rows[26]["verified_stage_credits"], 39)
        self.assertEqual(rows[27]["verified_stage_credits"], 40)
        self.assertEqual(rows[27]["total_spent"], rows[32]["total_spent"])

    def test_wrong_reference_digest_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "input digest mismatch"):
            cap_frontier.summarize("0" * 64)
