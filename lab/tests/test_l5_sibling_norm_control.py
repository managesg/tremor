import unittest

from lab.l5_sibling_norm_control import compare, sibling_verdict


class L5SiblingNormControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = compare()
        cls.rows = {row["case"]: row for row in cls.report["rows"]}

    def test_n1_admits_correct_work_missing_sibling_evidence(self):
        self.assertEqual(len(self.rows), 6)
        for name in ("missing_review", "self_review", "wrong_task", "uncommitted_review"):
            with self.subTest(case=name):
                row = self.rows[name]
                self.assertEqual(row["n1_dispatch"], "admitted")
                self.assertEqual(row["sibling_reason"], "no_matching_committed_independent_review")
                self.assertTrue(row["executed_sibling_violation"])
                self.assertEqual(row["score"]["distinct_passing"], 1)

    def test_committed_independent_review_satisfies_both(self):
        row = self.rows["independent_review"]
        self.assertTrue(row["sibling_allows"])
        self.assertFalse(row["executed_sibling_violation"])
        self.assertEqual(row["n1_dispatch"], "admitted")
        self.assertEqual(row["score"]["distinct_passing"], 1)
        self.assertFalse(self.report["scientific_n2_frozen"])

    def test_uncommitted_review_never_changes_earlier_work_verdict(self):
        row = self.rows["uncommitted_review"]
        self.assertFalse(row["committed_view_before_work"]["items"])
        review, = [event for event in row["board_trace"] if event["type"] == "post"]
        self.assertEqual(review["round"], row["work_round"])
        self.assertFalse(sibling_verdict(row["action_log"][0], row["committed_view_before_work"])[0])

    def test_n1_refusal_is_excluded_from_executed_sibling_violation(self):
        row = self.rows["unclaimed"]
        self.assertEqual(row["n1_dispatch"], "refused")
        self.assertEqual(row["sibling_reason"], "no_committed_claim")
        self.assertFalse(row["executed_sibling_violation"])
        self.assertEqual(row["score"]["distinct_passing"], 0)

    def test_repeated_replay_is_identical(self):
        self.assertEqual(self.report, compare())


if __name__ == "__main__":
    unittest.main()
