import hashlib
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from lab.l2_reference_custody import verify_reference


def digest(data):
    return hashlib.sha256(data).hexdigest()


class ReferenceCustodyTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.case = "pair-01"
        self.manifest = "references.json"
        self.inventory = "truth.json"
        self.source = "paper-ledger.txt"
        self.source_bytes = b"Paper ledger marker: green"
        self.write_source(self.source_bytes)
        self.truth_sha = self.write_inventory(self.inventory, {"markers": {self.case: "green"}})

    def write_inventory(self, name, data):
        raw = json.dumps(data, sort_keys=True).encode()
        (self.root / name).write_bytes(raw)
        return digest(raw)

    def write_source(self, raw):
        (self.root / self.source).write_bytes(raw)
        self.manifest_sha = self.write_inventory(
            self.manifest, {"references": {self.case: {"path": self.source, "sha256": digest(raw)}}},
        )

    def verify(self, *, case=None, manifest_sha=None, truth_sha=None):
        return verify_reference(
            self.root, self.case if case is None else case,
            manifest=self.manifest, manifest_sha256=self.manifest_sha if manifest_sha is None else manifest_sha,
            truth_inventory=self.inventory, truth_sha256=self.truth_sha if truth_sha is None else truth_sha,
        )

    def test_returns_the_exact_checked_bytes_and_digest(self):
        verified = self.verify()
        self.assertEqual(verified.text.encode("ascii"), self.source_bytes)
        self.assertEqual(verified.sha256, digest(self.source_bytes))

    def test_repinned_reference_cannot_override_independent_truth(self):
        original_manifest_sha = self.manifest_sha
        self.write_source(b"Paper ledger marker: blue")
        with self.assertRaisesRegex(ValueError, "reference manifest digest mismatch"):
            self.verify(manifest_sha=original_manifest_sha)
        with self.assertRaisesRegex(ValueError, "contradicts the pinned marker"):
            self.verify()
        changed_truth_sha = self.write_inventory(self.inventory, {"markers": {self.case: "blue"}})
        with self.assertRaisesRegex(ValueError, "truth inventory digest mismatch"):
            self.verify()
        with self.assertRaisesRegex(ValueError, "differs from the current fixture scorer"):
            self.verify(truth_sha=changed_truth_sha)

    def test_rejects_missing_or_modified_source(self):
        source = self.root / self.source
        source.write_bytes(self.source_bytes + b"\n")
        with self.assertRaisesRegex(ValueError, "reference source digest mismatch"):
            self.verify()
        source.unlink()
        with self.assertRaisesRegex(ValueError, "missing reference source"):
            self.verify()

    def test_selected_case_must_exist_in_both_pinned_inventories(self):
        with self.assertRaisesRegex(ValueError, "case absent from references"):
            self.verify(case="other-case")
        truth_sha = self.write_inventory(self.inventory, {"markers": {"other-case": "green"}})
        with self.assertRaisesRegex(ValueError, "case absent from markers"):
            self.verify(truth_sha=truth_sha)

    def test_duplicate_inventory_keys_and_indirect_files_are_rejected(self):
        raw = b'{"markers":{"pair-01":"green","pair-01":"blue"}}'
        (self.root / self.inventory).write_bytes(raw)
        with self.assertRaisesRegex(ValueError, "duplicate keys"):
            self.verify(truth_sha=digest(raw))
        self.truth_sha = self.write_inventory(self.inventory, {"markers": {self.case: "green"}})
        path = self.root / self.source
        copy = self.root / "other.txt"
        path.rename(copy)
        path.symlink_to(copy)
        with self.assertRaisesRegex(ValueError, "regular bundle file"):
            self.verify()
