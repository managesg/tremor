"""Join the archived public CPU loader receipt without running the loader."""

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from shutil import copytree
import struct
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from lab import l8_installation_witness as installation, l8_runtime_join as audit


FIXTURE = Path(__file__).resolve().parent / "fixtures" / "l8_cpu_loader"
LOADER_PIN = "56f3f97be5ff3f28764c6022a779d5c53323816d680d75b178ccbf6790e1db12"


def digest(raw):
    return sha256(raw).hexdigest()


def state_pin(inventory):
    return digest(json.dumps(inventory, sort_keys=True, separators=(",", ":"), allow_nan=False).encode())


class L8InstallationWitnessTests(unittest.TestCase):
    def setUp(self):
        self.base = Path(self.enterContext(TemporaryDirectory())).resolve()
        self.root = self.base / "bundle"
        copytree(FIXTURE, self.root)
        self.loader = self.read("loader-receipt.json")
        self.assertEqual(digest((self.root / "loader-receipt.json").read_bytes()), LOADER_PIN)
        self.bind_freeze()

    def read(self, name):
        return json.loads((self.root / name).read_bytes())

    def artifact(self, name):
        return {"path": name, "sha256": digest((self.root / name).read_bytes())}

    def write(self, name, document):
        (self.root / name).write_text(json.dumps(document, sort_keys=True, allow_nan=False), encoding="utf-8")
        return self.artifact(name)

    def bind_freeze(self):
        stored = self.read("l8.json")
        l4 = self.read("l4.json")
        lineage = self.loader["lineage"]
        binding = {"freeze_sha256": self.artifact("l8.json")["sha256"],
                   "protocol_sha256": stored["activation_protocol"]["sha256"],
                   "base_manifest_sha256": l4["model_manifest"]["sha256"], "hook_id": self.loader["hook"]}
        self.anchors = self.write("approved-lineage.json", {
            "evidence": "l8_native_base_manifest_binding", "plan_sha256": binding["freeze_sha256"],
            "base_manifest_sha256": binding["base_manifest_sha256"], "base_revision": lineage["base_revision"],
            "l4_receipt_sha256": lineage["l4_receipt_sha256"], "before_sha256": lineage["before_sha256"],
            "after_sha256": lineage["after_sha256"], "split_sizes": lineage["split_sizes"],
        })
        self.sample = {"sample_id": "holdout", "prompt_sha256": self.artifact("holdout.prompt")["sha256"],
                       "token_indices": [0]}
        self.plan = {"schema": audit.PLAN_SCHEMA, **binding, "samples": [self.sample], "stages": {
            row["stage"]: {"checkpoint_sha256": row["checkpoint_sha256"],
                           "installed_state_sha256": state_pin(row["installed_tensors"])}
            for row in self.loader["stages"]}}

    def build(self, *, witness_change=None, loader_change=None):
        if loader_change is not None:
            loader = deepcopy(self.loader)
            loader_change(loader)
            self.write("loader-receipt.json", loader)
        runtime = self.write("runtime-plan.json", self.plan)
        rows, observed = [], []
        for ordinal, stage in enumerate(audit.STAGES):
            name = f"{stage}.raw"
            (self.root / name).write_bytes(struct.pack("<f", 11.0 + ordinal))
            raw = self.artifact(name)
            rows.append({**self.sample, **self.plan["stages"][stage], "stage": stage, "raw": raw})
            observed.append({"sample_id": self.sample["sample_id"], "stage": stage, "raw_sha256": raw["sha256"],
                             "dtype": "f32", "shape": [1, 1]})
        bindings = {field: self.plan[field] for field in audit.BINDINGS}
        capture = self.write("runtime-capture.json", {"schema": audit.CAPTURE_SCHEMA, **bindings, "rows": rows})
        raw = self.write("raw-witness.json", {"schema": audit.RAW_WITNESS_SCHEMA, "plan_sha256": runtime["sha256"],
                                             "rows": observed})
        tensor = self.write("tensor.json", {"schema": audit.TENSOR_CONTRACT_SCHEMA, "plan_sha256": runtime["sha256"],
                                           "encoding": "little_endian_row_major", "dtype": "f32", "features": 1})
        tokens = self.write("tokens.json", {"schema": audit.TOKENIZED_SAMPLE_SCHEMA, "sample_id": "holdout",
                                           "prompt_sha256": self.sample["prompt_sha256"], "token_ids": [3]})
        selection = self.write("selection.json", {"schema": audit.ACTIVATION_CONTRACT_SCHEMA, **bindings,
                                                 "samples": [{**self.sample, "tokenized_input": tokens}]})
        document = {"schema": installation.SCHEMA, **bindings, "plan_sha256": runtime["sha256"],
                    "lineage_receipt_sha256": self.anchors["sha256"], "max_checkpoint_bytes": 2048,
                    "loader_receipt": self.artifact("loader-receipt.json")}
        if witness_change is not None:
            witness_change(document)
        witness = self.write("installation.json", document)
        reference = lambda artifact: (self.root / artifact["path"], artifact["sha256"])
        return (self.root, self.root / runtime["path"], self.root / capture["path"]), {
            "plan_sha256": runtime["sha256"], "capture_sha256": capture["sha256"], "raw_witness": reference(raw),
            "tensor_contract": reference(tensor), "activation_contract": reference(selection),
            "lineage_receipt": reference(self.anchors), "lineage_plan": self.root / "l8.json",
            "installation_witness": reference(witness)}

    def test_archive_passes_normal_cli_with_exact_stage_state(self):
        paths, options = self.build()
        command = [sys.executable, "-B", "-m", "lab.l8_runtime_join", *map(str, paths)]
        for key, value in options.items():
            if key != "installation_witness":
                values = value if isinstance(value, tuple) else (value,)
                command.extend(("--" + key.replace("_", "-"), *map(str, values)))
        prior = subprocess.check_output(command, text=True, timeout=10)
        result = json.loads(subprocess.check_output(
            [*command, "--installation-witness", *map(str, options["installation_witness"])], text=True, timeout=10))
        install = result.pop("installation_witness")
        self.assertEqual(json.dumps(result, sort_keys=True) + "\n", prior)
        self.assertEqual(install["loader_receipt_sha256"], LOADER_PIN)
        self.assertEqual((install["verified_loader_stages"], install["tensors_per_stage"], install["changed_tensors"]),
                         (2, 1, 1))
        self.assertTrue(result["declared_installed_state_changed"])
        self.assertFalse(install["native_installation_verified"] or install["hook_execution_verified"])

    def test_freshly_repinned_swapped_runtime_states_cannot_follow_the_other_stage(self):
        before, after = (self.plan["stages"][name] for name in audit.STAGES)
        before["installed_state_sha256"], after["installed_state_sha256"] = (
            after["installed_state_sha256"], before["installed_state_sha256"])
        paths, options = self.build()
        old = audit.verify(*paths, **{key: value for key, value in options.items() if key != "installation_witness"})
        self.assertEqual((old["verified_capture_rows"], old["finite_encoded_scalars"]), (2, 2))
        with self.assertRaisesRegex(ValueError, "canonical loader stage"):
            audit.verify(*paths, **options)

    def test_new_loader_pin_cannot_move_the_stage_or_forge_tensor_bytes(self):
        before, after = (row["installed_tensors"] for row in self.loader["stages"])
        cases = ((lambda receipt: receipt["stages"].reverse(), "approved checkpoint order"),
                 (lambda receipt: receipt["stages"][0].update(installed_tensors=after), "exact checkpoint payload"),
                 (lambda receipt: receipt["stages"][0].update(checkpoint_bytes=True), "witnessed size or bound"),
                 (lambda receipt: receipt["stages"][0].update(installed_tensors=before | {"phantom": before["weight"]}),
                  "exact checkpoint payload"))
        for edit, reason in cases:
            paths, options = self.build(loader_change=edit)
            with self.subTest(reason=reason), self.assertRaisesRegex(ValueError, reason):
                audit.verify(*paths, **options)

    def test_mutated_hook_freeze_or_base_cannot_reuse_loader_receipt(self):
        cases = ((lambda receipt: receipt.update(hook="linear.other"), "frozen hook"),
                 (lambda receipt: receipt.update(plan_sha256="0" * 64), "frozen hook"),
                 (lambda receipt: receipt["lineage"].update(base_revision="0" * 40), "approved base"))
        for edit, reason in cases:
            paths, options = self.build(loader_change=edit)
            with self.subTest(reason=reason), self.assertRaisesRegex(ValueError, reason):
                audit.verify(*paths, **options)
        paths, options = self.build(loader_change=lambda receipt: None)
        (self.root / "model_manifest").write_bytes(b"another base")
        with self.assertRaisesRegex(ValueError, "digest mismatch: model_manifest"):
            audit.verify(*paths, **options)

    def test_witness_itself_cannot_change_scope_or_drop_the_bound(self):
        for field, value, error in (("base_manifest_sha256", "0" * 64, "base or hook"),
                                    ("lineage_receipt_sha256", "0" * 64, "approved lineage"),
                                    ("hook_id", "linear.other", "base or hook"),
                                    ("max_checkpoint_bytes", 79, "witnessed size or bound")):
            paths, options = self.build(witness_change=lambda row: row.update({field: value}))
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, error):
                audit.verify(*paths, **options)

    def test_distinct_packages_can_carry_equal_verified_tensor_states(self):
        raw = (self.root / "before.safetensors").read_bytes()
        header_size = int.from_bytes(raw[:8], "little")
        header = json.loads(raw[8:8 + header_size])
        header["__metadata__"] = {"synthetic_control": "same installed weights"}
        edited = json.dumps(header, separators=(",", ":")).encode()
        edited += b" " * (-len(edited) % 8)
        after_path = self.root / "after.safetensors"
        after_path.write_bytes(len(edited).to_bytes(8, "little") + edited + raw[8 + header_size:])
        after_ref = self.artifact("after.safetensors")
        l4, freeze = self.read("l4.json"), self.read("l8.json")
        l4["checkpoints"]["after"] = freeze["checkpoints"]["after"] = after_ref
        freeze["l4_receipt"] = self.write("l4.json", l4)
        saved = self.write("l8.json", freeze)
        self.loader.update(plan_sha256=saved["sha256"])
        self.loader["lineage"].update(after_sha256=after_ref["sha256"], l4_receipt_sha256=freeze["l4_receipt"]["sha256"],
                                      changed_tensor_count=0)
        before, after = self.loader["stages"]
        after.update(checkpoint_sha256=after_ref["sha256"], checkpoint_bytes=after_path.stat().st_size,
                     installed_tensors=deepcopy(before["installed_tensors"]), hook_output=deepcopy(before["hook_output"]),
                     hook_tensor=deepcopy(before["hook_tensor"]))
        self.write("loader-receipt.json", self.loader)
        self.bind_freeze()
        paths, options = self.build()
        result = audit.verify(*paths, **options)
        self.assertFalse(result["declared_installed_state_changed"])
        self.assertEqual(result["installation_witness"]["changed_tensors"], 0)
