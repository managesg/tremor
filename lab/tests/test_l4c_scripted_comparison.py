from copy import deepcopy
from dataclasses import replace
import json
import unittest

from lab.l4c_scripted_comparison import ARMS, evaluate, execute, fixture


class L4CScriptedComparisonTests(unittest.TestCase):
    def setUp(self):
        self.days, self.truth = fixture(revise=True)
        self.cap = 8
        self.run = execute(self.days, cap=self.cap)

    def assessment(self, run=None, truth=None):
        return evaluate(self.run if run is None else run, self.days,
                        truth_by_day=self.truth if truth is None else truth, cap=self.cap)

    def test_matched_revisions_expose_stale_write_only_note(self):
        records = self.run["records"]
        self.assertEqual([(row["day"], row["arm"]) for row in records],
                         [(day, arm) for day in (1, 2) for arm in ARMS])
        for row in records[:2]:
            self.assertIn({"kind": "source_check", "subject": "bad-note", "outcome": "source_mismatch"},
                          row["operations"])
        replay, write_only, search = records[3:]
        self.assertIn(("valve", 1, "valve was shut"), self.run["raw_source_revisions"][0]["revisions"])
        self.assertEqual(self.run["raw_source_revisions"][1]["revisions"], [("valve", 2, "valve was open")])
        self.assertIn({"kind": "source_check", "subject": "n1-valve-note", "outcome": "source_mismatch"},
                      replay["operations"])
        self.assertEqual([entry["kind"] for entry in write_only["operations"]], ["memory_lookup"] * 2)
        self.assertEqual([row["submissions"]["day2-valve"] for row in (replay, write_only, search)],
                         [None, "valve was shut", "valve was open"])
        self.assertEqual([row["authored_source_version"] for row in write_only["resident"]], [1, 1])
        assessed = self.assessment()
        self.assertEqual([row["false_share"] for row in assessed["scored"][3:]],
                         [{"numerator": 0, "denominator": 1}, {"numerator": 1, "denominator": 2}, None])
        self.assertEqual(assessed["meter"], {"days": 2, "rows": 6, "total_operations": 25})

    def test_unchanged_source_control_preserves_prefix_and_ties_passes(self):
        days, truth = fixture(revise=False)
        unchanged = execute(days, cap=self.cap)
        self.assertEqual(self.run["records"][:3], unchanged["records"][:3])
        evaluated = evaluate(unchanged, days, truth_by_day=truth, cap=self.cap)
        self.assertEqual([(row["passed"], row["spent"]) for row in evaluated["totals"].values()],
                         [(4, 13), (4, 7), (4, 6)])

    def test_detached_truth_changes_only_scores_and_can_be_missing(self):
        relabeled = deepcopy(self.truth)
        relabeled[1]["valve"] = "independent detached label"
        sealed = json.dumps(self.run, sort_keys=True)
        previous = self.assessment()
        altered = self.assessment(truth=relabeled)
        self.assertEqual(json.dumps(self.run, sort_keys=True), sealed)
        self.assertNotIn("independent detached label", json.dumps(altered))
        self.assertEqual(previous["totals"]["search"]["passed"], 4)
        self.assertEqual(altered["totals"]["search"]["passed"], 3)
        del relabeled[1]["valve"]
        missing = self.assessment(truth=relabeled)
        self.assertEqual(missing["totals"]["search"]["unknown_truth"], 1)
        self.assertIsNone(missing["totals"]["search"]["units_per_pass"])
        self.assertIsNone(missing["scored"][4]["false_share"])

    def test_search_miss_exhausts_cap_with_spent_and_no_passes(self):
        run = execute(self.days, cap=1)
        assessed = evaluate(run, self.days, truth_by_day=self.truth, cap=1)
        for row in run["records"][2::3]:
            self.assertEqual((row["spent"], row["unused"]), (1, 0))
            self.assertEqual(row["operations"][0]["outcome"], "missing")
            self.assertTrue(all(answer is None for answer in row["submissions"].values()))
        self.assertEqual(assessed["totals"]["search"],
                         {"spent": 2, "passed": 0, "unknown_truth": 0, "units_per_pass": None})
        self.assertEqual(run["records"][0]["gate_status"], "budget_withheld")

    def test_independent_audit_refuses_recounted_deleted_search_attempt(self):
        forged = deepcopy(self.run)
        row = forged["records"][2]
        row["operations"].pop(0)
        row["spent"] -= 1
        row["unused"] += 1
        with self.assertRaises(ValueError):
            self.assessment(run=forged)

    def test_independent_audit_refuses_output_and_revision_tampering(self):
        for mutation in (
            lambda run: run["records"][3]["submissions"].update({"day2-valve": "valve was open"}),
            lambda run: run["records"][4]["resident"][0].update({"authored_source_version": 2}),
            lambda run: run["raw_source_revisions"][0]["revisions"].pop(0),
            lambda run: run["records"][0].update({"day": 8}),
        ):
            forged = deepcopy(self.run)
            mutation(forged)
            with self.assertRaises(ValueError):
                self.assessment(run=forged)
        self.assertEqual(self.assessment(run=json.loads(json.dumps(self.run))), self.assessment())

    def test_revisions_and_opportunities_follow_schedule(self):
        first, second = self.days
        for invalid in (replace(second, revisions=(("valve", 3, "skipped"),)),
                        replace(second, tasks=first.tasks), replace(second, arrivals=first.arrivals)):
            with self.assertRaises(ValueError):
                execute((first, invalid), cap=self.cap)

    def test_plan_pin_includes_unexecuted_search_options(self):
        first, second = self.days
        first_task, other_task = first.tasks
        adjusted = replace(first_task, candidates=(*first_task.candidates, "unreached"))
        alternative = (replace(first, tasks=(adjusted, other_task)), second)
        alternate_run = execute(alternative, cap=self.cap)
        self.assertEqual(alternate_run["records"], self.run["records"])
        self.assertNotEqual(alternate_run["plan_sha256"], self.run["plan_sha256"])
        with self.assertRaisesRegex(ValueError, "supplied plan pin"):
            evaluate(self.run, alternative, truth_by_day=self.truth, cap=self.cap)
