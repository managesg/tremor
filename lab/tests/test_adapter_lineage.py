import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from lab import adapter_lineage


class AdapterLineageTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.receipt = {
            "line": "L4-E", "status": "settled", "settled_utc": "2024-01-01T04:00:00+00:00",
            "base_revision": "a" * 40,
            "checkpoints": {"before": self.artifact("before.weights", b"base"),
                            "after": self.artifact("after.weights", b"adapter")},
            "training": self.split("train"),
        }
        for key in ("model_manifest", "adapter_config", "resource_receipt", "context_control"):
            self.receipt[key] = self.artifact(key, key.encode())
        self.plan = {
            "prediction": "L8-D", "frozen_utc": "2024-01-01T05:00:00+00:00",
            "base_revision": "a" * 40, "checkpoints": dict(self.receipt["checkpoints"]),
            "calibration": self.split("calibration"), "heldout": self.split("heldout"),
            "activation_protocol": self.artifact("activation-protocol", b"protocol"),
        }

    def artifact(self, name, content):
        if not isinstance(content, bytes):
            content = json.dumps(content, sort_keys=True).encode()
        (self.root / name).write_bytes(content)
        return {"path": name, "sha256": hashlib.sha256(content).hexdigest()}

    def split(self, name, **fields):
        row = {"sample_id": name, "family_id": name + "-family", "content": self.artifact(name + ".prompt", name.encode())}
        return self.artifact(name + ".json", {"samples": [dict(row, **fields)]})

    def verify(self):
        self.plan["l4_receipt"] = self.artifact("l4.json", self.receipt)
        return adapter_lineage.verify(self.root, self.plan)

    def test_pins_checkpoint_digests_and_separate_splits(self):
        result = self.verify()
        self.assertEqual(result["split_sizes"], {"training": 1, "calibration": 1, "heldout": 1})
        self.assertEqual(result["after_sha256"], self.receipt["checkpoints"]["after"]["sha256"])
        self.assertEqual(result["l4_receipt_sha256"], self.plan["l4_receipt"]["sha256"])

    def test_modified_or_unpinned_weights_refused(self):
        (self.root / "after.weights").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "artifact digest mismatch"):
            self.verify()
        self.plan["checkpoints"]["after"] = self.artifact("other.weights", b"other")
        with self.assertRaisesRegex(ValueError, "must pin"):
            self.verify()

    def test_equal_checkpoint_bytes_and_future_freeze_refused(self):
        original = self.receipt["checkpoints"]["after"]
        duplicate = self.artifact("duplicate.weights", b"base")
        self.receipt["checkpoints"]["after"] = self.plan["checkpoints"]["after"] = duplicate
        with self.assertRaisesRegex(ValueError, "distinct checkpoint"):
            self.verify()
        self.receipt["checkpoints"]["after"] = self.plan["checkpoints"]["after"] = original
        self.plan["frozen_utc"] = "9998-01-01T00:00:00+00:00"
        with self.assertRaisesRegex(ValueError, "cannot be in the future"):
            self.verify()

    def test_requires_settlement_before_freeze_on_same_base(self):
        for change, reason in (({"status": "reserved"}, "settled L4-E"),
                               ({"settled_utc": self.plan["frozen_utc"]}, "must precede"),
                               ({"base_revision": "b" * 40}, "base revisions differ")):
            with self.subTest(change=change):
                original = self.receipt.copy()
                self.receipt.update(change)
                with self.assertRaisesRegex(ValueError, reason):
                    self.verify()
                self.receipt = original

    def test_split_aliases_are_refused(self):
        for change in ({"sample_id": "train"}, {"family_id": "calibration-family"},
                       {"content": self.artifact("copied.prompt", b"train")}):
            with self.subTest(change=change):
                self.plan["heldout"] = self.split("heldout", **change)
                with self.assertRaisesRegex(ValueError, "heldout overlaps"):
                    self.verify()

    def test_claimed_prompt_digest_must_match_the_prompt_bytes(self):
        (self.root / "heldout.prompt").write_bytes(b"train")
        with self.assertRaisesRegex(ValueError, "artifact digest mismatch: heldout.prompt"):
            self.verify()

    def test_rejects_path_escapes_and_symbolic_checkpoints(self):
        self.plan["activation_protocol"]["path"] = "../protocol"
        with self.assertRaisesRegex(ValueError, "must be inside"):
            self.verify()
        self.plan["activation_protocol"]["path"] = "protocol-link"
        (self.root / "protocol-link").symlink_to(self.root / "activation-protocol")
        with self.assertRaisesRegex(ValueError, "not a regular bundle file"):
            self.verify()

    def test_cli_refuses_a_plan_rewritten_after_its_digest_was_recorded(self):
        self.verify()
        reference = self.artifact("l8.json", self.plan)
        filename = str(self.root / reference["path"])
        command = [sys.executable, "-B", "-m", "lab.adapter_lineage", str(self.root), filename,
                   "--plan-sha256", reference["sha256"]]
        completed = subprocess.run(command, capture_output=True, text=True, timeout=5, check=True)
        self.assertEqual(json.loads(completed.stdout)["base_revision"], self.plan["base_revision"])
        self.artifact("l8.json", {**self.plan, "frozen_utc": "2024-01-01T06:00:00+00:00"})
        refused = subprocess.run(command, capture_output=True, text=True, timeout=5, check=False)
        self.assertEqual(refused.returncode, 2)
        self.assertIn("artifact digest mismatch: l8.json", refused.stderr)
