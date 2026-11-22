"""Verify attached review documents without deciding native R3-L5 admission."""

from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from lab import r3_l5_intake as intake


class R3L5ReviewReceiptTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.reviews = self.root / "review"
        self.reviews.mkdir()
        self.plan = "a" * 64
        self.role = "mount_and_capture_review"
        self.record = {
            "schema": "r3_l5_review_receipt_v1",
            "batch": "R3-L5", "plan_sha256": self.plan, "role": self.role,
            "disposition": "awaiting_changes", "reason": "Separate runtime capture is still needed",
        }
        self.index = {"batch": "R3-L5", "plan_sha256": self.plan, "references": {}}

    def attach(self, record=None, role=None):
        payload = json.dumps(self.record if record is None else record).encode()
        digest = sha256(payload).hexdigest()
        (self.reviews / digest).write_bytes(payload)
        role = self.role if role is None else role
        self.index["references"][role] = {"plan_sha256": self.plan, "reference_sha256": digest}
        return digest

    def test_cli_reads_exact_review_and_keeps_authority_with_owners(self):
        digest = self.attach()
        path = self.root / "index.json"
        payload = json.dumps(self.index).encode()
        path.write_bytes(payload)
        result = subprocess.run(
            [sys.executable, "-B", "-m", "lab.r3_l5_intake", "--review-index", str(path),
             "--review-index-sha256", sha256(payload).hexdigest(), "--review-root", str(self.root)],
            text=True, capture_output=True, timeout=10, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        receipt = data["review_receipt_bytes"]["receipts"][self.role]
        self.assertEqual(receipt["reference_sha256"], digest)
        self.assertEqual(receipt["receipt_asserted_disposition"], "awaiting_changes")
        self.assertFalse(data["independent_review_verified"])
        self.assertFalse(data["authorizes_execution"])

    def verify(self):
        return intake.inventory(intake.ROOT, self.index, review_root=self.root)

    def test_attachment_digest_is_checked_before_disposition(self):
        digest = self.attach()
        (self.reviews / digest).write_text(json.dumps(self.record | {"disposition": "reviewed"}))
        with self.assertRaisesRegex(ValueError, "captured review digest mismatch"):
            self.verify()

    def test_fresh_wrong_plan_or_role_does_not_match_the_index(self):
        for changed in ({"plan_sha256": "b" * 64}, {"role": "native_runner"}, {"batch": "R3-L2"}):
            with self.subTest(changed=changed):
                self.attach(self.record | changed)
                with self.assertRaisesRegex(ValueError, "differs from the indexed plan or role"):
                    self.verify()

    def test_legacy_reference_alone_stays_metadata(self):
        self.attach()
        legacy = intake.inventory(intake.ROOT, self.index)
        self.assertNotIn("review_receipt_bytes", legacy)
        self.assertEqual(legacy["review_references"][self.role]["disposition"], "reference_supplied")
        with self.assertRaisesRegex(ValueError, "pinned review index"):
            intake.inventory(intake.ROOT, review_root=self.root)

    def test_complete_byte_inventory_does_not_authorize_execution(self):
        for role in intake.REVIEW_ROLES:
            self.attach(self.record | {"role": role, "disposition": "reviewed"}, role=role)
        report = self.verify()
        self.assertEqual(report["missing_references"], [])
        self.assertEqual(report["review_receipt_bytes"]["matched_receipts"], 7)
        for field in ("independent_review_verified", "protected_custody_verified", "authorizes_execution"):
            self.assertFalse(report[field])
        self.assertFalse(report["review_receipt_bytes"]["reviewer_identity_verified"])

    def test_linked_receipt_and_malformed_disposition_are_refused(self):
        digest = self.attach(self.record | {"disposition": True})
        with self.assertRaisesRegex(ValueError, "invalid review receipt disposition"):
            self.verify()
        path = self.reviews / digest
        original = path.with_name("retained")
        path.rename(original)
        path.symlink_to(original)
        with self.assertRaisesRegex(ValueError, "missing or inaccessible review capture file"):
            self.verify()
