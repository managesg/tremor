import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from lab import replication_inventory as inventory

QWEN = Path(__file__).resolve().parents[2] / "data" / "hf"


def _digest(raw):
    return hashlib.sha256(raw).hexdigest()


class ReplicationInventoryTests(unittest.TestCase):
    def setUp(self):
        self.scratch = Path(self.enterContext(TemporaryDirectory()))
        self.bundle = self.scratch / "snapshots"
        self.bundle.mkdir()
        self.plan = {"schema_version": 1, "candidates": {}}
        self.registry = {"schema_version": 1, "families": []}
        self.stage("reference", legacy=True)
        self.stage("transfer", legacy=False)

    def stage(self, role, *, legacy):
        folder = self.bundle / role
        folder.mkdir()
        repo, revision = f"fixture/{role}", ("a" if legacy else "b") * 40
        files = {
            "config.json": json.dumps({"model_type": f"toy-{role}", "architectures": ["Toy"]}).encode(),
            "LICENSE": b"fixture license",
            "tokenizer.json": b"fixture tokenizer",
        }
        if legacy:
            files["model.safetensors"] = b"synthetic weight bytes, not a model"
        else:
            files["model.safetensors.index.json"] = b'{"weight_map":{"x":"shards/part.safetensors"}}'
            files["shards/part.safetensors"] = b"synthetic shard, not a model"
        for name, content in files.items():
            path = folder / name
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(content)
        rows = ({"repo": repo, "revision": revision, "files": {
            name: {"size": len(raw), "sha256": _digest(raw), "hf_lfs_sha256": _digest(raw), "lfs_match": True}
            for name, raw in files.items()}}
            if legacy else {"model": repo, "revision": revision, "files": [
                {"path": name, "bytes": len(raw), "sha256": _digest(raw), "lfs_oid": _digest(raw)}
                for name, raw in files.items()]})
        self.plan["candidates"][role] = {"root": role, "repo": repo, "revision": revision, "manifest_sha256": ""}
        self.registry["families"].append({"repo": repo, "revision": revision, "family_id": f"toy-{role}"})
        self.manifest(role, rows)

    def manifest(self, role, rows):
        raw = json.dumps(rows).encode()
        (self.bundle / role / inventory.MANIFEST).write_bytes(raw)
        self.plan["candidates"][role]["manifest_sha256"] = _digest(raw)

    def pins(self):
        paths = self.scratch / "plan.json", self.scratch / "registry.json"
        pins = []
        for path, data in zip(paths, (self.plan, self.registry), strict=True):
            raw = json.dumps(data).encode()
            path.write_bytes(raw)
            pins.append(_digest(raw))
        return *paths, *pins

    def verify(self, limit=8192):
        plan, registry, p, r = self.pins()
        return inventory.verify(self.bundle, plan, registry, plan_sha256=p, registry_sha256=r, max_snapshot_bytes=limit)

    def test_normalizes_legacy_and_list_and_only_verifies_structure(self):
        result = self.verify()
        self.assertTrue(result["inventory_verified"])
        self.assertFalse(result["loader_verified"])
        self.assertFalse(result["scientific_acceptance"])
        self.assertEqual(result["snapshots"]["reference"]["weight_shards"], ["model.safetensors"])
        self.assertEqual(result["snapshots"]["transfer"]["weight_shards"], ["shards/part.safetensors"])
        self.assertEqual(result["snapshots"]["transfer"]["family_id"], "toy-transfer")

    def test_same_family_and_byte_limit_fail_before_weight_hashing(self):
        with patch.object(inventory, "_file_digest", side_effect=AssertionError("weight read")):
            self.registry["families"][1]["family_id"] = "toy-reference"
            with self.assertRaisesRegex(ValueError, "same reviewed family"):
                self.verify()
            self.registry["families"][1]["family_id"] = "toy-transfer"
            with self.assertRaisesRegex(ValueError, "exceeds the byte limit"):
                self.verify(limit=1)

    def test_identity_and_reviewed_registry_are_both_enforced(self):
        record = self.plan["candidates"]["transfer"]
        record["repo"] = "fixture/relabel"
        with self.assertRaisesRegex(ValueError, "snapshot identity mismatch"):
            self.verify()
        record["repo"] = "fixture/transfer"
        self.registry["families"].pop()
        with self.assertRaisesRegex(ValueError, "absent from reviewed family"):
            self.verify()

    def test_tampered_weight_and_unlisted_or_linked_inventory_rejected(self):
        path = self.bundle / "reference" / "model.safetensors"
        raw = path.read_bytes()
        path.write_bytes(b"x" * len(raw))
        with self.assertRaisesRegex(ValueError, "file digest mismatch"):
            self.verify()
        path.write_bytes(raw + b"x")
        with self.assertRaisesRegex(ValueError, "file type or size mismatch"):
            self.verify()
        path.unlink()
        path.symlink_to(self.bundle / "transfer" / "shards/part.safetensors")
        with self.assertRaisesRegex(ValueError, "linked snapshot entry"):
            self.verify()
        path.unlink()
        path.write_bytes(raw)
        (path.parent / "unlisted").write_bytes(b"no")
        with self.assertRaisesRegex(ValueError, "unexpected or linked"):
            self.verify()

    def test_shard_index_cannot_name_unlisted_payload_or_duplicate_member(self):
        folder = self.bundle / "transfer"
        rows = json.loads((folder / inventory.MANIFEST).read_bytes())
        indexed = next(row for row in rows["files"] if row["path"] == inventory.INDEX)
        for raw, reason in (
            (b'{"weight_map":{"x":"shards/other.safetensors"}}', "shard inventory differs"),
            (b'{"weight_map":{"x":"shards/other.safetensors","x":"shards/part.safetensors"}}', "duplicate JSON member"),
        ):
            with self.subTest(reason=reason):
                (folder / inventory.INDEX).write_bytes(raw)
                indexed.update(bytes=len(raw), sha256=_digest(raw), lfs_oid=_digest(raw))
                self.manifest("transfer", rows)
                with self.assertRaisesRegex(ValueError, reason):
                    self.verify()

    def test_cli_uses_external_plan_and_registry_pins(self):
        plan, registry, p, r = self.pins()
        command = [sys.executable, "-B", "-m", "lab.replication_inventory", str(self.bundle), str(plan),
                   str(registry), "--plan-sha256", p, "--registry-sha256", r, "--max-snapshot-bytes", "8192"]
        completed = subprocess.run(command, capture_output=True, text=True, check=True)
        self.assertFalse(json.loads(completed.stdout)["scientific_acceptance"])
        registry.write_bytes(registry.read_bytes() + b" ")
        refused = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(refused.returncode, 2)
        self.assertIn("digest mismatch: registry.json", refused.stderr)

    @unittest.skipUnless(all((QWEN / name / inventory.MANIFEST).is_file()
                             for name in ("Qwen3.5-0.8B", "Qwen3.5-4B")), "local checkpoints unavailable")
    def test_actual_qwen_pair_is_refused_without_reading_weights(self):
        self.bundle = QWEN
        self.registry["families"] = []
        for role, name in zip(inventory.ROLES, ("Qwen3.5-0.8B", "Qwen3.5-4B"), strict=True):
            raw = (QWEN / name / inventory.MANIFEST).read_bytes()
            data = json.loads(raw)
            identity = {"repo": data.get("repo") or data["model"], "revision": data["revision"]}
            self.plan["candidates"][role] = {**identity, "root": name, "manifest_sha256": _digest(raw)}
            self.registry["families"].append({**identity, "family_id": "Qwen3.5"})
        with patch.object(inventory, "_file_digest", side_effect=AssertionError("weight read")):
            with self.assertRaisesRegex(ValueError, "same reviewed family"):
                self.verify()


if __name__ == "__main__":
    unittest.main()
