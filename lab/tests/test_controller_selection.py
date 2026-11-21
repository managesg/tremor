import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from lab import controller_selection as selection


class ControllerSelectionTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.bundle = self.root / "bundle"
        self.bundle.mkdir()
        self.manifest = {
            "schema_version": 1,
            "scope": {"model_id": "test-model", "model_revision": "test-revision",
                      "tier": "test-only", "task_family": "toy-tasks"},
            "inputs": {key: "1" * 64 for key in ("task_manifest_sha256", "scorer_sha256", "protocol_sha256")},
            "arms": {
                name: {"budget": dict.fromkeys(selection.BUDGET, 10), "policy_sha256": "2" * 64}
                for name in ("combined", "plain")
            },
            "lines": {
                line: {"component": f"test-{line}", "status": "disabled", "reason": "Awaiting frozen results"}
                for line in selection.LINES
            },
        }
        self.index = {"schema_version": 1, "receipts": {}}

    def write(self, name, data):
        raw = data if isinstance(data, bytes) else json.dumps(data, sort_keys=True).encode()
        name.write_bytes(raw)
        return hashlib.sha256(raw).hexdigest()

    def artifact(self, filename, content):
        return {"path": filename, "sha256": self.write(self.bundle / filename, content)}

    def fake_receipt(self, **changes):
        comparison = {"line": "L1", "component": "test-L1", "contrast_id": "test-L1-B",
                      "registered_comparator": "uniform", "scope": self.manifest["scope"]}
        artifacts = {key: self.artifact(key, f"TEST FIXTURE ONLY: {key}".encode()) for key in selection.ARTIFACTS}
        artifacts["registration"] = self.artifact("registration", comparison)
        self.bind_receipt({
            **comparison, "run_kind": "empirical_model", "frozen": True,
            "outcome": "supported", "artifacts": artifacts, **changes,
        })
        self.manifest["lines"]["L1"] = {
            key: comparison[key] for key in ("component", "contrast_id", "registered_comparator")
        } | {"status": "enabled", "evidence": self.index["receipts"]["L1"]}

    def bind_receipt(self, receipt):
        pin = self.artifact("L1-test-receipt.json", receipt)
        self.index["receipts"]["L1"] = pin
        if self.manifest["lines"]["L1"]["status"] == "enabled":
            self.manifest["lines"]["L1"]["evidence"] = pin

    def freeze(self):
        manifest, evidence_index = self.root / "selection.json", self.root / "reviewer-pins.json"
        return (manifest, evidence_index, self.write(manifest, self.manifest),
                self.write(evidence_index, self.index))

    def verify(self):
        manifest, index, manifest_pin, index_pin = self.freeze()
        return selection.verify(self.bundle, manifest, index, manifest_sha256=manifest_pin,
                                evidence_index_sha256=index_pin)

    def test_all_disabled_and_synthetic_structural_positive(self):
        report = self.verify()
        self.assertEqual(report["declared_enabled"], [])
        self.assertEqual(set(report["declared_disabled"]), set(selection.LINES))
        self.fake_receipt()
        report = self.verify()
        self.assertEqual(report["declared_enabled"], ["L1"])
        self.assertTrue(report["budget_match"])
        self.assertFalse(report["scientific_acceptance"])
        self.assertEqual(report["validation"], "structure_and_pins_only")

    def test_unfrozen_nonsupporting_and_cpu_receipts_refused(self):
        for change in ({"run_kind": "scripted_cpu"}, {"outcome": "killed"},
                       {"outcome": "inconclusive"}, {"outcome": "unavailable"}, {"frozen": False}):
            with self.subTest(change=change):
                self.fake_receipt(**change)
                with self.assertRaisesRegex(ValueError, "frozen supported empirical"):
                    self.verify()

    def test_scope_and_registered_comparator_refused(self):
        self.fake_receipt(scope={**self.manifest["scope"], "model_revision": "other"})
        with self.assertRaisesRegex(ValueError, "scope differs"):
            self.verify()
        self.fake_receipt()
        receipt = json.loads((self.bundle / "L1-test-receipt.json").read_bytes())
        registration = json.loads((self.bundle / "registration").read_bytes())
        registration.pop("registered_comparator")
        receipt["artifacts"]["registration"] = self.artifact("registration", registration)
        self.bind_receipt(receipt)
        with self.assertRaisesRegex(ValueError, "registered contrast fields"):
            self.verify()
        self.fake_receipt()
        self.manifest["lines"]["L1"].pop("registered_comparator")
        with self.assertRaisesRegex(ValueError, "enabled L1 fields"):
            self.verify()

    def test_required_pins_cover_only_enabled_and_bytes_match(self):
        self.fake_receipt()
        self.index["receipts"].clear()
        with self.assertRaisesRegex(ValueError, "independent pin"):
            self.verify()
        self.fake_receipt()
        self.index["receipts"]["L2"] = self.index["receipts"]["L1"]
        with self.assertRaisesRegex(ValueError, "exactly the enabled"):
            self.verify()
        self.index["receipts"].pop("L2")
        (self.bundle / "independent_review").write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "digest mismatch: independent_review"):
            self.verify()

    def test_strict_shape_reasons_and_budgets(self):
        self.manifest["lines"]["L8"]["reason"] = ""
        with self.assertRaisesRegex(ValueError, "disabled reason"):
            self.verify()
        self.manifest["lines"]["L8"]["reason"] = "Awaiting frozen results"
        self.manifest["arms"]["plain"]["budget"]["calls"] = 11
        with self.assertRaisesRegex(ValueError, "budgets differ"):
            self.verify()
        self.manifest["arms"]["plain"]["budget"]["calls"] = True
        with self.assertRaisesRegex(ValueError, "nonnegative integer"):
            self.verify()
        self.manifest["arms"]["plain"]["budget"]["calls"] = 10
        self.manifest["lines"].pop("L8")
        with self.assertRaisesRegex(ValueError, "research lines fields"):
            self.verify()

    def test_cli_requires_both_external_pins_and_rejects_duplicate_keys(self):
        manifest, index, manifest_pin, index_pin = self.freeze()
        command = [sys.executable, "-B", "-m", "lab.controller_selection", str(self.bundle),
                   str(manifest), str(index), "--manifest-sha256", manifest_pin,
                   "--evidence-index-sha256", index_pin]
        valid = subprocess.run(command, capture_output=True, text=True, check=True)
        self.assertFalse(json.loads(valid.stdout)["scientific_acceptance"])
        index.write_text('{"schema_version":1,"receipts":{},"receipts":{}}')
        stale = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(stale.returncode, 2)
        self.assertIn("digest mismatch", stale.stderr)
        command[-1] = hashlib.sha256(index.read_bytes()).hexdigest()
        ambiguous = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(ambiguous.returncode, 2)
        self.assertIn("duplicate JSON member", ambiguous.stderr)


if __name__ == "__main__":
    unittest.main()
