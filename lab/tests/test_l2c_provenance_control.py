from copy import deepcopy
from pathlib import Path
from shutil import copyfile
from tempfile import TemporaryDirectory
import unittest

from murmuration.board import Board, read_log

from lab.l2c_provenance_control import assess, detached, fixture, run, score
from lab.l2c_provenance_receipts import audit
from lab.l4_measured_compression import pin


class L2CProvenanceControlTests(unittest.TestCase):
    def setUp(self):
        scratch = TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name)
        self.initial = self.root / "initial.jsonl"
        self.plan = fixture(self.initial)
        self.plan_pin = pin(self.plan)

    def dispatch(self, mode):
        path = self.root / f"{mode}.jsonl"
        copyfile(self.initial, path)
        result = run(path, self.plan, mode=mode, expected_plan_pin=self.plan_pin)
        self.assertEqual(self.audit(path, result), result["physical_counts"])
        return path, result, {row["id"]: row for row in result["receipts"]}

    def audit(self, path, result, *, receipts=None, terminal=None, plan_pin=None):
        return audit(path, self.plan, result["receipts"] if receipts is None else receipts, mode=result["mode"],
                     expected_plan_pin=self.plan_pin if plan_pin is None else plan_pin,
                     **(result["terminal"] if terminal is None else terminal))

    def test_pending_support_only_qualifies_after_commit_and_reads_stay_available(self):
        expected = {"visible-read": True, "unavailable-read": False, "independent-read": True}
        for mode in ("permissive", "verified", "corroborated", "verified_or_corroborated"):
            with self.subTest(mode=mode):
                path, result, rows = self.dispatch(mode)
                count = result["physical_counts"]
                self.assertEqual((count["reads"], count["read_hits"], count["dispatch_attempts"]), (3, 2, 15))
                self.assertEqual({name: rows[name]["read_found"] for name in expected}, expected)
                self.assertEqual(count["posts"], count["committed"])
                if mode != "corroborated":
                    continue
                pending, committed = rows["pending-support"], rows["committed-support"]
                self.assertEqual(pending["support"], committed["support"])
                self.assertEqual((pending["status"], pending["reason"], pending["post_id"]),
                                 ("refused", "ancestry_unavailable", None))
                trace = read_log(path)
                self.assertEqual([event["type"] for event in trace[pending["prior_count"]:pending["closed_count"]]],
                                 ["end_round"])
                self.assertEqual(committed["status"], "admitted")
                post = trace[committed["prior_count"]]
                self.assertEqual(post["data"]["refs"], [committed["target"], *committed["support"]])

    def test_corroboration_refuses_shared_origin_and_invalid_ancestry(self):
        _, _, rows = self.dispatch("corroborated")
        refusals = {
            "same-origin": ("origin_overlap", 1),
            "dependent-support": ("ancestry_circular", 1),
            "cyclic-support": ("ancestry_circular", 1),
            "wrong-version": ("claim_mismatch", 1),
            "retired-support": ("ancestry_unavailable", 1),
            "missing-ancestor": ("ancestry_unavailable", 1),
            "duplicate-support": ("support_duplicate", 2),
            "retired-target": ("target_unavailable", 0),
        }
        for name, (reason, checks) in refusals.items():
            with self.subTest(name=name):
                row = rows[name]
                self.assertEqual((row["status"], row["reason"], row["checks"], row["post_id"]),
                                 ("refused", reason, checks, None))
        self.assertEqual(rows["independent-relay"]["status"], "admitted")

    def test_exact_evaluator_receipt_and_combined_branch_reference_policy(self):
        _, verified, checked = self.dispatch("verified")
        rejected = checked["incorrect-value"]
        self.assertEqual((rejected["status"], rejected["reason"], rejected["checks"]),
                         ("refused", "verification_mismatch", 1))
        self.assertEqual(verified["physical_counts"]["checks"], 13)
        path, combined, rows = self.dispatch("verified_or_corroborated")
        trace = read_log(path)
        for name, reason, charge in (("verified-promotion", "verified_receipt", 1),
                                     ("independent-relay", "corroborated", 2)):
            with self.subTest(branch=reason):
                row = rows[name]
                self.assertEqual((row["status"], row["reason"], row["checks"]), ("admitted", reason, charge))
                cites = row["support"] if reason == "corroborated" else []
                self.assertEqual(trace[row["prior_count"]]["data"]["refs"], [row["target"], *cites])
        self.assertEqual(combined["physical_counts"]["checks"], 25)

    def test_audit_rejects_omitted_refusal_partial_receipt_and_wrong_anchor(self):
        path, result, _ = self.dispatch("corroborated")
        receipts = result["receipts"]
        with self.assertRaises(ValueError):
            self.audit(path, result, receipts=receipts[1:])
        forged = deepcopy(receipts)
        del forged[0]["closed_head"]
        with self.assertRaises(ValueError):
            self.audit(path, result, receipts=forged)
        terminal = result["terminal"] | {"expected_terminal_head": receipts[-2]["closed_head"]}
        with self.assertRaises(ValueError):
            self.audit(path, result, terminal=terminal)
        with self.assertRaises(ValueError):
            self.audit(path, result, plan_pin="0" * 64)

        Board(path, seed=17).end_round()
        trace = read_log(path)
        with self.assertRaises(ValueError):
            self.audit(path, result)
        with self.assertRaises(ValueError):
            self.audit(path, result, terminal={"expected_terminal_head": trace[-1]["hash"],
                                              "expected_events": len(trace)})

    def test_detached_truth_and_report_require_independent_pins(self):
        _, result, _ = self.dispatch("permissive")
        actual_truth = detached(self.plan)
        report_pin, truth_pin = pin(result), pin(actual_truth)
        actual = score(result, actual_truth, expected_report_pin=report_pin, expected_truth_pin=truth_pin)
        self.assertEqual(actual["invalid_admitted"], 1)
        changed_truth = deepcopy(actual_truth)
        changed_truth["values"]["incorrect-value"] = True
        with self.assertRaises(ValueError):
            score(result, changed_truth, expected_report_pin=report_pin, expected_truth_pin=truth_pin)
        regraded = score(result, changed_truth, expected_report_pin=report_pin, expected_truth_pin=pin(changed_truth))
        self.assertEqual(regraded["invalid_admitted"], 0)
        self.assertEqual(pin(result), report_pin)
        with self.assertRaises(ValueError):
            score(result | {"mode": "verified"}, actual_truth, expected_report_pin=report_pin,
                  expected_truth_pin=truth_pin)

    def test_repinned_origin_alias_cannot_be_counted_as_independent(self):
        aliases = [item for item, source in self.plan["origins"].items() if source["origin"] == "source-a"]
        for index, (canonical, alias) in enumerate((("source-a", "source-a "), ("caf\u00e9", "cafe\u0301"))):
            path = self.root / f"alias-{index}.jsonl"
            copyfile(self.initial, path)
            plan = deepcopy(self.plan)
            for item, supplied in zip(aliases, (canonical, alias), strict=True):
                plan["origins"][item]["origin"] = supplied
            result = run(path, plan, mode="corroborated", expected_plan_pin=pin(plan))
            row = next(item for item in result["receipts"] if item["id"] == "same-origin")
            self.assertEqual((row["status"], row["reason"]), ("refused", "ancestry_invalid"))

    def test_public_assessment_rechecks_repinned_meter_and_status(self):
        path, result, _ = self.dispatch("corroborated")
        labels = detached(self.plan)
        for mutation in ("checks", "status"):
            forged = deepcopy(result)
            if mutation == "checks":
                forged["receipts"][0]["checks"] += 1
                forged["physical_counts"]["checks"] += 1
                error = "check count differs from policy replay"
            else:
                forged["receipts"][0].update(status="admitted", reason="admitted")
                error = "segment closure"
            with self.subTest(mutation=mutation), self.assertRaisesRegex(ValueError, error):
                assess(path, self.plan, forged, labels, expected_plan_pin=self.plan_pin,
                       expected_report_pin=pin(forged), expected_truth_pin=pin(labels), **result["terminal"])
