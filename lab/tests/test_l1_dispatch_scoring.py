from copy import deepcopy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lab import l1_dispatch_scoring as scoring, l1_verification_allocation as allocation


class L1DispatchScoringTests(unittest.TestCase):
    cohort = "public-fixture"
    claims = tuple(allocation.Claim(name, "public", True) for name in ("a", "b", "c", "d", "e"))

    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.plan = allocation.make_plan(self.claims, {}, mode="uniform", budget=16)
        self.records = [self.start(0), self.answer(0, False), self.start(1), self.failure(1), self.start(2),
                        self.terminal("stopped", "wall_limit")]
        self.journal, self.journal_sha256 = self.write_journal("dispatch", self.plan, self.records)
        self.labels = self.root / "labels.json"
        self.label_document = {"schema": "l1_public_claim_labels_v1", "cohort": self.cohort,
                               "claim_inventory_sha256": self.plan["claim_inventory_sha256"],
                               "labels": [{"claim_id": claim.identifier, "case_id": f"case-{claim.identifier}",
                                           "source_id": f"source-{claim.identifier}", "legitimate": claim.identifier in "ad"}
                                          for claim in self.claims]}
        self.labels_sha256 = self.write_labels(self.label_document)

    @staticmethod
    def start(index):
        return {"event": "start", "attempt_index": index}

    @staticmethod
    def answer(index, result):
        return {"event": "answer", "attempt_index": index, "result": result, "used_units": 1}

    @staticmethod
    def failure(index):
        return {"event": "failure", "attempt_index": index, "reason": "scripted_failure", "used_units": 0}

    @staticmethod
    def terminal(status="completed", reason=None):
        return {"event": "terminal", "status": status, "reason": reason}

    def write_journal(self, name, plan, events):
        pin = allocation.digest(plan)
        rows = [{"event": "plan", "plan_sha256": pin}]
        retries = plan["mode"] == "majority_retry"
        for event in events:
            row = dict(event)
            if "attempt_index" in row:
                index = row["attempt_index"]
                choice = plan["choices"][index // 2 if retries else index]
                attempt = {"attempt_index": index, "claim_id": choice["claim_id"],
                           "action": "retry" if retries else "check", "ordinal": index % 2 + 1 if retries else 1,
                           "units": 1 if retries else 4}
                row["attempt_sha256"] = allocation.digest({"plan_sha256": pin, "attempt": attempt})
            rows.append(row)
        raw = "".join(json.dumps({"seq": seq, **row}, sort_keys=True) + "\n" for seq, row in enumerate(rows)).encode()
        path = self.root / f"{name}.jsonl"
        path.write_bytes(raw)
        return path, hashlib.sha256(raw).hexdigest()

    def write_labels(self, document):
        raw = (json.dumps(document, sort_keys=True, allow_nan=False) + "\n").encode()
        self.labels.write_bytes(raw)
        return hashlib.sha256(raw).hexdigest()

    def score(self, *, plan=None, archive=None, labels_sha256=None, expected_cohort=None):
        plan = self.plan if plan is None else plan
        journal, journal_sha256 = (self.journal, self.journal_sha256) if archive is None else archive
        return scoring.score(plan, self.claims, journal, self.labels, plan_sha256=allocation.digest(plan),
                             journal_sha256=journal_sha256,
                             labels_sha256=self.labels_sha256 if labels_sha256 is None else labels_sha256,
                             expected_cohort=self.cohort if expected_cohort is None else expected_cohort)

    def test_answered_false_and_zero_cost_failure_have_distinct_dispositions(self):
        report = self.score()
        self.assertEqual(report["status"], "scored_public_dispatch")
        self.assertEqual(report["dispatch_status"], "stopped")
        self.assertEqual(report["dispatch_reason"], "wall_limit")
        self.assertIsNone(report["scientific_rate"])
        self.assertEqual(report["cohort"], self.cohort)
        self.assertEqual(report["claim_inventory_sha256"], self.plan["claim_inventory_sha256"])
        self.assertEqual((report["plan_sha256"], report["journal_sha256"], report["labels_sha256"]),
                         (allocation.digest(self.plan), self.journal_sha256, self.labels_sha256))
        self.assertEqual([row["claim_id"] for row in report["claims"]], [claim.identifier for claim in self.claims])
        self.assertEqual([(row["category"], row["completion"]) for row in report["claims"]], [
            ("selected_resolved", False), ("selected_unresolved", None), ("selected_unresolved", None),
            ("selected_unresolved", None), ("unallocated", True),
        ])
        self.assertEqual([row["attempts"][0]["status"] for row in report["claims"][:4]],
                         ["answered", "failed", "open", "unstarted"])
        self.assertEqual(report["claims"][4]["attempts"], [])
        self.assertEqual(report["counts"], {
            "selected_resolved": {"claims": 1, "known_false_completions": 0, "legitimate_rejections": 1,
                                  "unknown_legitimate": 0, "unknown_illegitimate": 0},
            "selected_unresolved": {"claims": 3, "known_false_completions": 0, "legitimate_rejections": 0,
                                    "unknown_legitimate": 1, "unknown_illegitimate": 2},
            "unallocated": {"claims": 1, "known_false_completions": 1, "legitimate_rejections": 0,
                            "unknown_legitimate": 0, "unknown_illegitimate": 0},
        })

    def test_retry_waits_for_both_answers_even_when_the_first_makes_a_mathematical_majority(self):
        plan = allocation.make_plan(self.claims, {}, mode="majority_retry", budget=2)
        first_return = [self.start(0), self.answer(0, True), self.start(1)]
        partial = self.write_journal("partial-retry", plan, [*first_return, self.terminal("stopped", "operator_limit")])
        completed = self.write_journal("completed-retry", plan, [*first_return, self.answer(1, False), self.terminal()])
        pending = self.score(plan=plan, archive=partial)["claims"][0]
        resolved = self.score(plan=plan, archive=completed)["claims"][0]
        self.assertIsNone(pending["completion"])
        self.assertEqual(pending["category"], "selected_unresolved")
        self.assertEqual([row["status"] for row in pending["attempts"]], ["answered", "open"])
        self.assertIs(resolved["completion"], True)
        self.assertEqual(resolved["category"], "selected_resolved")
        self.assertEqual([row["result"] for row in resolved["attempts"]], [True, False])

    def test_truth_inventory_must_match_the_exact_claims_and_expected_cohort(self):
        with self.assertRaisesRegex(ValueError, "public label cohort differs from the expected cohort"):
            self.score(expected_cohort="different-cohort")
        for case in ("wrong-inventory", "missing", "duplicate-claim", "duplicate-case", "injected-return"):
            with self.subTest(case=case):
                labels = deepcopy(self.label_document)
                rows = labels["labels"]
                if case == "wrong-inventory":
                    labels["claim_inventory_sha256"] = "0" * 64
                elif case == "missing":
                    rows.pop()
                elif case == "duplicate-claim":
                    rows[1]["claim_id"] = rows[0]["claim_id"]
                elif case == "duplicate-case":
                    rows[1]["case_id"] = rows[0]["case_id"]
                else:
                    rows[0]["checker"] = True
                with self.assertRaises(ValueError):
                    self.score(labels_sha256=self.write_labels(labels))

    def test_changed_label_bytes_and_wrong_journal_are_independently_refused(self):
        original = self.score()
        with self.assertRaisesRegex(ValueError, "artifact digest mismatch: dispatch.jsonl"):
            self.score(archive=(self.journal, "0" * 64))
        different_plan = allocation.make_plan(self.claims, {}, mode="uniform", budget=4)
        different_journal = self.write_journal("different-plan", different_plan,
                                               [self.start(0), self.answer(0, False), self.terminal()])
        with self.assertRaisesRegex(ValueError, "dispatch journal does not start with its pinned plan"):
            self.score(archive=different_journal)
        labels = deepcopy(self.label_document)
        labels["labels"][0]["legitimate"] = False
        changed_pin = self.write_labels(labels)
        self.assertNotEqual(changed_pin, self.labels_sha256)
        with self.assertRaisesRegex(ValueError, "artifact digest mismatch: labels.json"):
            self.score()
        changed = self.score(labels_sha256=changed_pin)
        self.assertEqual([row["completion"] for row in original["claims"]],
                         [row["completion"] for row in changed["claims"]])
        self.assertEqual(changed["counts"]["selected_resolved"]["legitimate_rejections"], 0)
