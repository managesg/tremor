from copy import deepcopy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lab import l1_dispatch_audit as dispatch, l1_verification_allocation as allocation


class L1DispatchAuditTests(unittest.TestCase):
    claims = tuple(allocation.Claim(name, "public", True) for name in ("first", "second", "third"))

    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))

    @staticmethod
    def start(index):
        return {"event": "start", "attempt_index": index}

    @staticmethod
    def answer(index, *, result=True, units=1):
        return {"event": "answer", "attempt_index": index, "result": result, "used_units": units}

    @staticmethod
    def failure(index, *, units=None):
        return {"event": "failure", "attempt_index": index, "reason": "scripted_failure", "used_units": units}

    @staticmethod
    def terminal(status="completed", reason=None):
        return {"event": "terminal", "status": status, "reason": reason}

    def plan(self, mode="uniform", budget=12):
        return allocation.make_plan(self.claims, {}, mode=mode, budget=budget)

    def journal(self, name, plan, actions):
        plan_sha256 = allocation.digest(plan)
        attempts = []
        for choice in plan["choices"]:
            retries = choice["action"] == "retry_pair"
            for ordinal in ((1, 2) if retries else (1,)):
                attempts.append({"attempt_index": len(attempts), "claim_id": choice["claim_id"],
                                 "action": "retry" if retries else "check", "ordinal": ordinal,
                                 "units": 1 if retries else 4})
        rows = [{"event": "plan", "plan_sha256": plan_sha256}]
        for action in actions:
            row = dict(action)
            if "attempt_index" in row:
                attempt = attempts[row["attempt_index"]]
                row.setdefault("attempt_sha256", allocation.digest({"plan_sha256": plan_sha256, "attempt": attempt}))
            rows.append(row)
        content = "".join(json.dumps({"seq": seq, **row}, sort_keys=True) + "\n" for seq, row in enumerate(rows))
        path = self.root / f"{name}.jsonl"
        raw = content.encode()
        path.write_bytes(raw)
        return path, hashlib.sha256(raw).hexdigest()

    def audit(self, plan, name, actions):
        journal, pin = self.journal(name, plan, actions)
        return dispatch.audit(plan, self.claims, journal, plan_sha256=allocation.digest(plan), journal_sha256=pin)

    def test_ordered_stopped_prefix_keeps_returned_open_and_unstarted_attempts(self):
        plan = self.plan()
        actions = [self.start(0), self.answer(0, result=False, units=3), self.start(1),
                   self.terminal("stopped", "wall_limit")]
        report = self.audit(plan, "stopped-prefix", actions)
        self.assertEqual(report["status"], "stopped")
        self.assertEqual(report["reason"], "wall_limit")
        self.assertEqual({key: report[key] for key in ("planned", "started", "answered", "failed", "open", "unstarted")},
                         {"planned": 3, "started": 2, "answered": 1, "failed": 0, "open": 1, "unstarted": 1})
        self.assertEqual((report["planned_dispatch_units"], report["started_planned_units"]), (12, 8))
        self.assertEqual((report["known_actual_units"], report["unknown_actual_count"]), (3, 1))
        self.assertEqual([(row["status"], row["result"], row["used_units"]) for row in report["attempts"]],
                         [("answered", False, 3), ("open", None, None), ("unstarted", None, None)])
        self.assertIsNone(report["scientific_rate"])

    def test_retry_pair_expands_to_two_ordered_attempts_and_preserves_failure(self):
        plan = self.plan(mode="majority_retry", budget=2)
        completed = self.audit(plan, "retry-complete", [self.start(0), self.answer(0), self.start(1),
                                                        self.answer(1, result=False), self.terminal()])
        failed = self.audit(plan, "retry-failed", [self.start(0), self.answer(0), self.start(1), self.failure(1),
                                                    self.terminal("stopped", "scripted_failure")])
        self.assertEqual(completed["status"], "completed")
        self.assertEqual(failed["status"], "stopped")
        self.assertEqual(failed["reason"], "scripted_failure")
        self.assertEqual([row["claim_id"] for row in completed["attempts"]], ["first", "first"])
        self.assertEqual([row["attempt_index"] for row in completed["attempts"]], [0, 1])
        self.assertEqual([row["ordinal"] for row in completed["attempts"]], [1, 2])
        self.assertEqual([row["units"] for row in completed["attempts"]], [1, 1])
        self.assertEqual((completed["planned"], completed["answered"], completed["known_actual_units"]), (2, 2, 2))
        self.assertEqual((failed["answered"], failed["failed"], failed["open"], failed["unstarted"]), (1, 1, 0, 0))
        self.assertEqual((failed["known_actual_units"], failed["unknown_actual_count"]), (1, 1))
        self.assertEqual((failed["attempts"][1]["status"], failed["attempts"][1]["result"],
                          failed["attempts"][1]["used_units"]), ("failed", None, None))

        known_failure = self.audit(plan, "retry-known-failure", [self.start(0), self.answer(0), self.start(1),
                                                                self.failure(1, units=1), self.terminal()])
        self.assertEqual((known_failure["status"], known_failure["failed"]), ("completed", 1))
        self.assertEqual((known_failure["known_actual_units"], known_failure["unknown_actual_count"]), (2, 0))

    def test_measurement_plan_is_separate_from_observed_dispatch_charges(self):
        calibration = {"public": (("cal-first", (0, 1) * 5), ("cal-second", (1, 0) * 5))}
        plan = allocation.make_plan(self.claims, calibration, mode="overdispersion", budget=28)
        report = self.audit(plan, "measured", [self.start(0), self.answer(0, units=2),
                                                self.terminal("stopped", "operator_limit")])
        self.assertEqual(report["measurement_units_planned"], 20)
        self.assertEqual(report["planned_dispatch_units"], 8)
        self.assertEqual(report["started_planned_units"], 4)
        self.assertEqual(report["known_actual_units"], 2)
        self.assertEqual(report["unknown_actual_count"], 0)

    def test_forged_charge_above_the_attempt_allocation_is_rejected_even_when_repinned(self):
        plan = self.plan(budget=4)
        for label, charge in (("larger-than-reservation", 5), ("boolean-meter", True)):
            with self.subTest(label=label), self.assertRaises(ValueError):
                self.audit(plan, label, [self.start(0), self.answer(0, units=charge), self.terminal()])

    def test_external_plan_and_journal_pins_are_independent(self):
        plan = self.plan(budget=4)
        path, journal_pin = self.journal("pinned", plan, [self.start(0), self.answer(0), self.terminal()])
        wrong = "0" * 64
        with self.assertRaises(ValueError):
            dispatch.audit(plan, self.claims, path, plan_sha256=allocation.digest(plan), journal_sha256=wrong)
        with self.assertRaises(ValueError):
            dispatch.audit(plan, self.claims, path, plan_sha256=wrong, journal_sha256=journal_pin)

        changed = deepcopy(plan)
        changed["choices"][0]["cost"] = 3
        changed["allocated"] = 3
        changed["unused"] = 1
        with self.assertRaises(ValueError):
            self.audit(changed, "forged-plan", [self.start(0), self.answer(0), self.terminal()])

    def test_same_length_plan_cannot_rebind_a_journal_by_replacing_its_header_pin(self):
        original = self.plan(budget=4)
        reversed_claims = tuple(reversed(self.claims))
        different = allocation.make_plan(reversed_claims, {}, mode="uniform", budget=4)
        self.assertEqual(len(original["choices"]), len(different["choices"]))
        self.assertNotEqual(original["choices"], different["choices"])
        actions = [self.start(0), self.answer(0), self.terminal()]
        source, _ = self.journal("original", original, actions)
        alternate, alternate_pin = self.journal("alternate", different, actions)
        different_pin = allocation.digest(different)
        self.assertEqual(dispatch.audit(different, reversed_claims, alternate, plan_sha256=different_pin,
                                        journal_sha256=alternate_pin)["answered"], 1)
        raw = source.read_bytes().replace(allocation.digest(original).encode(), different_pin.encode(), 1)
        rebound = self.root / "rebound.jsonl"
        rebound.write_bytes(raw)
        with self.assertRaisesRegex(ValueError, "dispatch does not match its exact planned attempt"):
            dispatch.audit(different, reversed_claims, rebound, plan_sha256=different_pin,
                           journal_sha256=hashlib.sha256(raw).hexdigest())

        wrong_receipt = {**self.answer(0), "attempt_sha256": "0" * 64}
        with self.assertRaisesRegex(ValueError, "dispatch does not match its exact planned attempt"):
            self.audit(original, "wrong-receipt", [self.start(0), wrong_receipt, self.terminal()])

    def test_duplicate_out_of_order_or_post_stop_actions_are_refused(self):
        plan = self.plan(budget=8)
        cases = {
            "double-answer": [self.start(0), self.answer(0), self.answer(0), self.terminal("stopped", "operator_limit")],
            "out-of-order": [self.start(1), self.answer(1), self.terminal("stopped", "operator_limit")],
            "after-stop": [self.start(0), self.answer(0), self.terminal("stopped", "operator_limit"), self.start(1)],
        }
        for label, actions in cases.items():
            with self.subTest(label=label), self.assertRaises(ValueError):
                self.audit(plan, label, actions)

    def test_incomplete_run_cannot_claim_completion_without_all_ordered_returns(self):
        plan = self.plan(budget=8)
        for label, prefix in (("unstarted", [self.start(0), self.answer(0)]), ("open", [self.start(0)])):
            with self.subTest(label=label), self.assertRaises(ValueError):
                self.audit(plan, label, [*prefix, self.terminal()])

    def test_strict_jsonl_rejects_duplicate_key_and_truncated_final_line_after_repinning(self):
        plan = self.plan(budget=4)
        path, _ = self.journal("strict", plan, [self.start(0), self.answer(0), self.terminal()])
        original = path.read_bytes()
        variants = {
            "duplicate key": original.replace(b'"event": "start"', b'"event": "start", "event": "start"', 1),
            "missing line terminator": original.removesuffix(b"\n"),
        }
        for label, raw in variants.items():
            with self.subTest(label=label):
                self.assertNotEqual(raw, original)
                path.write_bytes(raw)
                with self.assertRaises(ValueError):
                    dispatch.audit(plan, self.claims, path, plan_sha256=allocation.digest(plan),
                                   journal_sha256=hashlib.sha256(raw).hexdigest())
