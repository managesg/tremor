from copy import deepcopy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from lab import r3_l2_admission_inventory as admission


class R3L2AdmissionInventoryTests(unittest.TestCase):
    def setUp(self):
        self.scratch = Path(self.enterContext(TemporaryDirectory())).resolve()
        self.repository = self.scratch / "repository"
        self.inventory = self.make_repository(self.repository)
        self.manifest = self.repository / "admission.json"
        self.manifest_sha256 = self.write_manifest(self.manifest, self.inventory)

    @staticmethod
    def sha(data):
        return hashlib.sha256(data).hexdigest()

    def make_repository(self, repository, *, symlink_role=None):
        repository.mkdir()
        artifacts = {}
        for role, relative in admission.ARTIFACTS.items():
            path = repository / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            content = f"Synthetic artifact for {role}\n".encode()
            if role == symlink_role:
                target = self.scratch / "outside-artifact"
                target.write_bytes(content)
                path.symlink_to(target)
            else:
                path.write_bytes(content)
            artifacts[role] = {"path": relative, "sha256": self.sha(content)}
        return {"schema": "r3_l2_admission_inventory_v1", "batch": "R3-L2", "artifacts": artifacts,
                "launch_inputs": dict.fromkeys(admission.LAUNCH_INPUTS)}

    def write_manifest(self, path, inventory):
        raw = (json.dumps(inventory, sort_keys=True, allow_nan=False) + "\n").encode()
        path.write_bytes(raw)
        return self.sha(raw)

    def refuse_before_replay(self, *, repository=None, manifest=None, pin=None):
        with (
            mock.patch.object(admission, "_check_calibration") as calibration,
            mock.patch.object(admission, "_check_cpu_evidence") as cpu,
            self.assertRaises(ValueError),
        ):
            admission.verify(self.repository if repository is None else repository,
                             self.manifest if manifest is None else manifest,
                             manifest_sha256=self.manifest_sha256 if pin is None else pin)
        calibration.assert_not_called()
        cpu.assert_not_called()

    def test_pinned_inventory_is_reported_without_authorizing_execution(self):
        historical, cpu_evidence = {"synthetic_calibration": True}, {"synthetic_cpu_evidence": True}
        with (
            mock.patch.object(admission, "_check_calibration", return_value=historical) as calibration,
            mock.patch.object(admission, "_check_cpu_evidence", return_value=cpu_evidence) as cpu,
        ):
            report = admission.verify(self.repository, self.manifest, manifest_sha256=self.manifest_sha256)
        calibration.assert_called_once_with(self.repository, self.inventory["artifacts"])
        cpu.assert_called_once_with(self.repository, self.inventory["artifacts"])
        self.assertEqual(report["batch"], "R3-L2")
        self.assertEqual(report["status"], "awaiting_inputs")
        self.assertIs(report["authorizes_execution"], False)
        self.assertIsNone(report["native_entrypoint"])
        self.assertEqual(report["historical_calibration"], historical)
        self.assertEqual(report["cpu_evidence"], cpu_evidence)
        self.assertEqual(report["manifest_sha256"], self.manifest_sha256)
        self.assertEqual(report["missing_inputs"], admission.LAUNCH_INPUTS)
        self.assertEqual(report["artifacts"], self.inventory["artifacts"])

    def test_wrong_external_pin_and_changed_artifact_are_refused_before_replay(self):
        self.refuse_before_replay(pin="0" * 64)
        role = next(iter(admission.ARTIFACTS))
        (self.repository / admission.ARTIFACTS[role]).write_bytes(b"Altered synthetic receipt\n")
        self.refuse_before_replay()

    def test_pinned_manifest_cannot_redirect_an_artifact_to_an_unsafe_path(self):
        role = next(iter(admission.ARTIFACTS))
        for path in ("../outside", str(self.repository / admission.ARTIFACTS[role])):
            with self.subTest(path=path):
                changed = deepcopy(self.inventory)
                changed["artifacts"][role]["path"] = path
                self.refuse_before_replay(pin=self.write_manifest(self.manifest, changed))

        repository = self.scratch / "symlinked-repository"
        inventory = self.make_repository(repository, symlink_role=role)
        manifest = repository / "admission.json"
        self.refuse_before_replay(repository=repository, manifest=manifest, pin=self.write_manifest(manifest, inventory))

    def test_duplicate_json_keys_are_rejected_even_when_pinned(self):
        original = self.manifest.read_text(encoding="utf-8")
        launch_field = json.dumps(next(iter(admission.LAUNCH_INPUTS))) + ": null"
        variants = (
            original.replace('"batch": "R3-L2"', '"batch": "R3-L2", "batch": "R3-L2"', 1),
            original.replace(launch_field, f"{launch_field}, {launch_field}", 1),
        )
        for index, changed in enumerate(variants):
            with self.subTest(variant=index):
                self.assertNotEqual(changed, original)
                raw = changed.encode()
                self.manifest.write_bytes(raw)
                self.refuse_before_replay(pin=self.sha(raw))

    def test_duplicate_or_missing_artifact_roles_are_rejected_even_when_pinned(self):
        first, second, *_ = admission.ARTIFACTS
        duplicated = deepcopy(self.inventory)
        duplicated["artifacts"][second] = duplicated["artifacts"][first]
        missing = deepcopy(self.inventory)
        del missing["artifacts"][first]
        for label, changed in (("duplicated path", duplicated), ("missing role", missing)):
            with self.subTest(label=label):
                self.refuse_before_replay(pin=self.write_manifest(self.manifest, changed))

    def test_pinned_inventory_cannot_claim_authorization_or_filled_launch_inputs(self):
        claimed = {**self.inventory, "authorizes_execution": True}
        entrypoint = {**self.inventory, "native_entrypoint": "unapproved-fixture"}
        filled = deepcopy(self.inventory)
        filled["launch_inputs"][next(iter(admission.LAUNCH_INPUTS))] = "unreviewed-slot-value"
        wrong_batch = {**self.inventory, "batch": "R3-L5"}
        for label, changed in (("authorization", claimed), ("entrypoint", entrypoint),
                               ("launch input", filled), ("different batch", wrong_batch)):
            with self.subTest(label=label):
                self.refuse_before_replay(pin=self.write_manifest(self.manifest, changed))
