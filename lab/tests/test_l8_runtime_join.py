"""Exercise the offline L8-D runtime receipt join on public fixture bytes."""

from copy import deepcopy
from hashlib import sha256
import json
import os
import struct
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from lab import l8_runtime_join


class L8RuntimeJoinTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory())).resolve()
        self.plan_path = self.root / "plan.json"
        self.capture_path = self.root / "capture.json"
        bindings = {"freeze_sha256": "a" * 64, "protocol_sha256": "b" * 64,
                    "base_manifest_sha256": "c" * 64, "hook_id": "model.language_model.layers.31"}
        self.plan = {"schema": l8_runtime_join.PLAN_SCHEMA, **bindings, "stages": {
            "before": {"checkpoint_sha256": "1" * 64, "installed_state_sha256": "2" * 64},
            "after": {"checkpoint_sha256": "3" * 64, "installed_state_sha256": "4" * 64},
        }, "samples": [{"sample_id": sample, "prompt_sha256": sha256(sample.encode()).hexdigest(),
                        "token_indices": [1, offset]} for sample, offset in (("p1", 3), ("p2", 4))]}
        self.capture = {"schema": l8_runtime_join.CAPTURE_SCHEMA, **bindings, "rows": []}
        for sample in self.plan["samples"]:
            for stage, identity in self.plan["stages"].items():
                raw_name = f"{sample['sample_id']}-{stage}.raw"
                raw = raw_name.encode()
                (self.root / raw_name).write_bytes(raw)
                self.capture["rows"].append({**deepcopy(sample), "stage": stage, **identity,
                                             "raw": {"path": raw_name, "sha256": sha256(raw).hexdigest()}})

    @staticmethod
    def write(path, document):
        raw = json.dumps(document, sort_keys=True, allow_nan=False).encode()
        path.write_bytes(raw)
        return sha256(raw).hexdigest()

    def pins(self):
        return {"plan_sha256": self.write(self.plan_path, self.plan),
                "capture_sha256": self.write(self.capture_path, self.capture)}

    def verify(self, **overrides):
        return l8_runtime_join.verify(self.root, self.plan_path, self.capture_path, **(self.pins() | overrides))

    def lineage(self, *, change=None):
        def artifact(name, body):
            path = self.root / name
            path.write_bytes(body)
            return {"path": name, "sha256": sha256(body).hexdigest()}

        def document(name, value):
            return artifact(name, json.dumps(value, sort_keys=True).encode())

        protocol = artifact("activation-protocol", b"fixture protocol")
        manifest = artifact("base-manifest", b"fixture manifest")
        stages = {stage: artifact(f"{stage}.checkpoint", stage.encode()) for stage in self.plan["stages"]}
        revision = "a" * 40
        l4 = document("l4.json", {
            "line": "L4-E", "status": "settled", "base_revision": revision,
            "model_manifest": manifest, "checkpoints": stages,
        })
        holdout = document("heldout.json", {"samples": [
            {"sample_id": row["sample_id"], "family_id": f"family-{row['sample_id']}",
             "content": artifact(f"{row['sample_id']}.prompt", row["sample_id"].encode())}
            for row in self.plan["samples"]
        ]})
        freeze = document("lineage-plan.json", {"prediction": "L8-D", "base_revision": revision,
                                                  "l4_receipt": l4, "checkpoints": stages,
                                                  "activation_protocol": protocol, "heldout": holdout})
        receipt = {"evidence": "l8_native_base_manifest_binding", "plan_sha256": freeze["sha256"],
                   "base_manifest_sha256": manifest["sha256"], "base_revision": revision,
                   "l4_receipt_sha256": l4["sha256"], "before_sha256": stages["before"]["sha256"],
                   "after_sha256": stages["after"]["sha256"], "split_sizes": {"heldout": 2}}
        binding = {"freeze_sha256": freeze["sha256"], "base_manifest_sha256": manifest["sha256"],
                   "protocol_sha256": protocol["sha256"]}
        self.plan.update(binding)
        self.capture.update(binding)
        for stage in stages:
            self.plan["stages"][stage]["checkpoint_sha256"] = stages[stage]["sha256"]
        for row in self.capture["rows"]:
            row.update(self.plan["stages"][row["stage"]])
        if change is not None:
            change(receipt)
        saved = document("lineage-receipt.json", receipt)
        return {"lineage_receipt": (self.root / saved["path"], saved["sha256"]),
                "lineage_plan": self.root / freeze["path"]}

    def activation_contract(self, *, replace=None):
        rows = []
        for sample in self.plan["samples"]:
            identifier = sample["sample_id"]
            tokenized = {"schema": "tremor.l8d_tokenized_sample.v1", "sample_id": identifier,
                         "prompt_sha256": sample["prompt_sha256"], "token_ids": [10, 22, 34, 56, 78]}
            path = self.root / f"{identifier}.tokens.json"
            rows.append(deepcopy(sample) | {
                "tokenized_input": {"path": path.name, "sha256": self.write(path, tokenized)},
            })
        document = {"schema": "tremor.l8d_activation_selection_contract.v1",
                    **{field: self.plan[field] for field in l8_runtime_join.BINDINGS}, "samples": rows}
        if replace is not None:
            replace(document)
        path = self.root / "activation-selection.json"
        return path, self.write(path, document)

    def change_positions(self, token_indices):
        first = self.plan["samples"][0]
        first["token_indices"] = token_indices
        for row in self.capture["rows"]:
            if row["sample_id"] == first["sample_id"]:
                row["token_indices"] = list(token_indices)

    def test_independent_activation_contract_through_normal_cli(self):
        lineage = self.lineage()
        contract = self.activation_contract()
        pins = self.pins()
        command = [sys.executable, "-B", "-m", "lab.l8_runtime_join", str(self.root), str(self.plan_path),
                   str(self.capture_path), "--plan-sha256", pins["plan_sha256"], "--capture-sha256",
                   pins["capture_sha256"], "--lineage-receipt", *map(str, lineage["lineage_receipt"]),
                   "--lineage-plan", str(lineage["lineage_plan"]), "--activation-contract", *map(str, contract)]
        run = subprocess.run(command, capture_output=True, text=True, timeout=10)
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        selection = report["activation_selection"]
        self.assertEqual(selection["contract_sha256"], contract[1])
        self.assertEqual(selection["hook_id"], self.plan["hook_id"])
        self.assertEqual(selection["samples"]["p1"]["sequence_tokens"], 5)
        self.assertEqual(selection["samples"]["p1"]["selected_tokens"], 2)
        self.assertFalse(selection["observed_hook_verified"])
        self.assertFalse(selection["tokenizer_execution_verified"])
        self.assertFalse(report["native_execution_verified"])

    def test_repinned_wrong_hook_still_conflicts_with_independent_contract(self):
        lineage = self.lineage()
        contract = self.activation_contract()
        self.plan["hook_id"] = self.capture["hook_id"] = "model.language_model.layers.999999"
        self.assertEqual(self.verify(**lineage)["verified_capture_rows"], 4)
        with self.assertRaisesRegex(ValueError, "contract differs from"):
            self.verify(**lineage, activation_contract=contract)

    def test_repinned_out_of_range_token_cannot_pass_even_with_new_contract(self):
        lineage = self.lineage()
        contract = self.activation_contract()
        # Position 5 is outside the tokenized sequence of length 5.
        self.change_positions([1, 5])
        self.assertEqual(self.verify(**lineage)["verified_capture_rows"], 4)
        with self.assertRaisesRegex(ValueError, "sample differs from the runtime prompt or selected tokens"):
            self.verify(**lineage, activation_contract=contract)
        contract = self.activation_contract()
        with self.assertRaisesRegex(ValueError, "out-of-range token index"):
            self.verify(**lineage, activation_contract=contract)

    def test_contract_requires_lineage_and_every_exact_sample(self):
        lineage = self.lineage()
        contract = self.activation_contract()
        with self.assertRaisesRegex(ValueError, "requires the independent lineage"):
            self.verify(activation_contract=contract)
        contract = self.activation_contract(replace=lambda document: document["samples"].pop())
        with self.assertRaisesRegex(ValueError, "cover every frozen held-out sample"):
            self.verify(**lineage, activation_contract=contract)

    def test_tokenized_receipt_cannot_be_crossed_with_another_prompt(self):
        lineage = self.lineage()
        def cross(document):
            document["samples"][0]["tokenized_input"] = document["samples"][1]["tokenized_input"]
        contract = self.activation_contract(replace=cross)
        with self.assertRaisesRegex(ValueError, "tokenized input differs from the selected sample"):
            self.verify(**lineage, activation_contract=contract)

    def test_joins_lineage_freeze_checkpoint_pair_and_exact_heldout_prompts(self):
        report = self.verify(**self.lineage())
        self.assertEqual(report["approved_lineage_binding"]["heldout_size"], 2)
        self.assertFalse(report["settlement_verified"])
        self.assertFalse(report["native_execution_verified"])

    def test_reviewed_stage_binding_refuses_repinned_runtime_checkpoint(self):
        inputs = self.lineage()
        self.plan["stages"]["after"]["checkpoint_sha256"] = "9" * 64
        for row in self.capture["rows"]:
            row.update(self.plan["stages"][row["stage"]])
        self.assertEqual(self.verify()["verified_capture_rows"], 4)
        with self.assertRaisesRegex(ValueError, "runtime checkpoint differs from approved lineage"):
            self.verify(**inputs)

    def test_exact_holdout_binding_refuses_replacement_prompt_and_tampered_bytes(self):
        inputs = self.lineage()
        prompt_pin = self.plan["samples"][0]["prompt_sha256"]
        self.plan["samples"][0]["prompt_sha256"] = "f" * 64
        for row in self.capture["rows"][:2]:
            row["prompt_sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "sample inventory differs from the lineage holdout"):
            self.verify(**inputs)
        self.plan["samples"][0]["prompt_sha256"] = prompt_pin
        for row in self.capture["rows"][:2]:
            row["prompt_sha256"] = prompt_pin
        (self.root / "p1.prompt").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "digest mismatch: p1.prompt"):
            self.verify(**inputs)

    def test_exact_lineage_receipt_cannot_be_crossed_or_supplied_alone(self):
        inputs = self.lineage(change=lambda receipt: receipt.update(plan_sha256="f" * 64))
        with self.assertRaisesRegex(ValueError, "does not bind the runtime freeze"):
            self.verify(**inputs)
        with self.assertRaisesRegex(ValueError, "must be supplied together"):
            self.verify(lineage_receipt=inputs["lineage_receipt"])

    def test_exact_join_is_order_independent_and_declares_no_scientific_acceptance(self):
        self.capture["rows"].reverse()
        result = self.verify()
        self.assertEqual((result["samples"], result["verified_capture_rows"]), (2, 4))
        self.assertIs(result["declared_installed_state_changed"], True)
        for key in ("native_execution_verified", "settlement_verified", "activation_values_verified",
                    "scientific_acceptance"):
            self.assertIs(result[key], False)
        pins = self.pins()
        command = [sys.executable, "-B", "-m", "lab.l8_runtime_join", str(self.root), str(self.plan_path),
                   str(self.capture_path), "--plan-sha256", pins["plan_sha256"],
                   "--capture-sha256", pins["capture_sha256"]]
        actual = subprocess.run(command, capture_output=True, check=True, text=True, timeout=5)
        self.assertEqual(json.loads(actual.stdout), result)

    def test_repinned_capture_cannot_change_freeze_protocol_base_or_hook(self):
        for key, substitute in (("freeze_sha256", "d" * 64), ("protocol_sha256", "d" * 64),
                                ("base_manifest_sha256", "d" * 64), ("hook_id", "model.language_model.layers.0")):
            with self.subTest(key=key):
                original = self.capture[key]
                self.capture[key] = substitute
                with self.assertRaisesRegex(ValueError, f"differs from approved {key}"):
                    self.verify()
                self.capture[key] = original

    def test_repinned_capture_cannot_change_a_prompt_token_selection_or_stage(self):
        row = self.capture["rows"][0]
        for field, substituted, error in (
            ("prompt_sha256", "d" * 64, "prompt or token selection"),
            ("token_indices", [3, 1], "prompt or token selection"),
            ("token_indices", [True, 3], "expected distinct"),
            ("checkpoint_sha256", self.plan["stages"]["after"]["checkpoint_sha256"], "approved stage"),
            ("installed_state_sha256", self.plan["stages"]["after"]["installed_state_sha256"], "approved stage"),
        ):
            with self.subTest(field=field):
                original = row[field]
                row[field] = substituted
                with self.assertRaisesRegex(ValueError, error):
                    self.verify()
                row[field] = original

    def test_inventory_and_raw_bytes_must_match_exactly(self):
        last = self.capture["rows"].pop()
        with self.assertRaisesRegex(ValueError, "every frozen sample and stage"):
            self.verify()
        self.capture["rows"].append(deepcopy(self.capture["rows"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate L8-D sample-stage"):
            self.verify()
        self.capture["rows"][-1] = last
        (self.root / last["raw"]["path"]).write_bytes(b"modified")
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            self.verify()

    def test_refuses_stale_capture_pin_and_unexpected_row_field(self):
        with self.assertRaisesRegex(ValueError, "digest mismatch: capture.json"):
            self.verify(capture_sha256="0" * 64)
        self.capture["rows"][0]["injected_score"] = 1
        with self.assertRaisesRegex(ValueError, "invalid L8-D activation row fields"):
            self.verify()

    def test_requires_distinct_checkpoint_digests_but_records_identical_installed_state(self):
        self.plan["stages"]["after"]["installed_state_sha256"] = self.plan["stages"]["before"]["installed_state_sha256"]
        for row in self.capture["rows"]:
            row.update(self.plan["stages"][row["stage"]])
        self.assertIs(self.verify()["declared_installed_state_changed"], False)
        self.plan["stages"]["after"]["checkpoint_sha256"] = self.plan["stages"]["before"]["checkpoint_sha256"]
        with self.assertRaisesRegex(ValueError, "distinct approved checkpoint digests"):
            self.verify()

    def test_missing_or_empty_raw_capture_is_refused(self):
        raw = self.capture["rows"][0]["raw"]
        path = self.root / raw["path"]
        path.unlink()
        with self.assertRaises(FileNotFoundError):
            self.verify()
        path.write_bytes(b"")
        raw["sha256"] = sha256(b"").hexdigest()
        with self.assertRaisesRegex(ValueError, "must not be empty"):
            self.verify()

    def test_raw_files_must_be_distinct_but_bytes_can_match(self):
        first, second = self.capture["rows"][:2]
        original = second["raw"]
        second["raw"] = dict(first["raw"])
        with self.assertRaisesRegex(ValueError, "file reused across rows"):
            self.verify()
        path = self.root / original["path"]
        first_path = self.root / first["raw"]["path"]
        path.unlink()
        os.link(first_path, path)
        second["raw"]["path"] = original["path"]
        with self.assertRaisesRegex(ValueError, "file reused across rows"):
            self.verify()
        path.unlink()
        path.write_bytes(first_path.read_bytes())
        self.assertEqual(self.verify()["verified_capture_rows"], 4)

    def dense_witness(self):
        rows = []
        for row in self.capture["rows"]:
            value = 4.0 if row["stage"] == "before" else 8.0
            raw = struct.pack("<2f", value, value)
            (self.root / row["raw"]["path"]).write_bytes(raw)
            digest = sha256(raw).hexdigest()
            row["raw"]["sha256"] = digest
            rows.append({"sample_id": row["sample_id"], "stage": row["stage"], "raw_sha256": digest,
                         "dtype": "f32", "shape": [2, 1]})
        return {"schema": l8_runtime_join.RAW_WITNESS_SCHEMA, "plan_sha256": self.pins()["plan_sha256"],
                "rows": rows}

    def test_independent_raw_witness_refuses_rehashed_stage_swap(self):
        witness = self.dense_witness()
        path = self.root / "raw-witness.json"
        pin = self.write(path, witness)
        report = self.verify(raw_witness=(path, pin))
        self.assertEqual(report["witnessed_raw_rows"], 4)
        self.assertFalse(report["activation_values_verified"])
        first, second = self.capture["rows"][:2]
        first["raw"], second["raw"] = second["raw"], first["raw"]
        self.assertEqual(self.verify()["verified_capture_rows"], 4)
        with self.assertRaisesRegex(ValueError, "independently witnessed sample and stage"):
            self.verify(raw_witness=(path, pin))

    def test_dense_witness_checks_tensor_size_across_selected_tokens(self):
        witness = self.dense_witness()
        path = self.root / "raw-witness.json"
        witness["rows"][0]["shape"] = [2, 2]
        with self.assertRaisesRegex(ValueError, "independently witnessed sample and stage"):
            self.verify(raw_witness=(path, self.write(path, witness)))
        witness["rows"][0]["shape"] = [1, 2]
        with self.assertRaisesRegex(ValueError, "token-by-feature tensor shape"):
            self.verify(raw_witness=(path, self.write(path, witness)))

    def tensor_contract(self, dtype):
        path = self.root / "tensor-contract.json"
        return path, self.write(path, {"schema": l8_runtime_join.TENSOR_CONTRACT_SCHEMA,
                                      "plan_sha256": self.pins()["plan_sha256"],
                                      "encoding": "little_endian_row_major", "dtype": dtype, "features": 1})

    def test_layout_contract_refuses_same_byte_count_with_different_dtype(self):
        witness = self.dense_witness()
        witness["rows"][0].update(dtype="f16", shape=[2, 2])
        path = self.root / "witness.json"
        raw_witness = path, self.write(path, witness)
        self.assertEqual(self.verify(raw_witness=raw_witness)["verified_capture_rows"], 4)
        contract = self.tensor_contract("f32")
        with self.assertRaisesRegex(ValueError, "differs from the pinned dtype or feature width"):
            self.verify(raw_witness=raw_witness, tensor_contract=contract)
        with self.assertRaisesRegex(ValueError, "requires an independent raw witness"):
            self.verify(tensor_contract=contract)

    def test_tensor_contract_checks_finiteness_of_f32_f16_and_bf16(self):
        values = (
            ("f32", "<2I", 0x3F800000, (0x7F800000, 0xFFC00000)),
            ("f16", "<2H", 0x3C00, (0x7C00, 0xFE00)),
            ("bf16", "<2H", 0x3F80, (0x7F80, 0xFFC0)),
        )
        witness = self.dense_witness()
        path = self.root / "witness.json"

        def update(index, data, dtype):
            raw = self.capture["rows"][index]["raw"]
            (self.root / raw["path"]).write_bytes(data)
            raw["sha256"] = sha256(data).hexdigest()
            witness["rows"][index].update(raw_sha256=raw["sha256"], dtype=dtype)

        for dtype, binary_format, finite, invalid in values:
            with self.subTest(dtype=dtype):
                for index in range(len(witness["rows"])):
                    update(index, struct.pack(binary_format, finite, 0), dtype)
                contract = self.tensor_contract(dtype)
                result = self.verify(raw_witness=(path, self.write(path, witness)), tensor_contract=contract)
                self.assertEqual(result["finite_encoded_scalars"], 8)
                self.assertEqual(result["tensor_contract_sha256"], contract[1])
                self.assertFalse(result["activation_values_verified"])
                self.assertFalse(result["native_execution_verified"])
                for nonfinite in invalid:
                    update(0, struct.pack(binary_format, finite, nonfinite), dtype)
                    witness_pin = path, self.write(path, witness)
                    self.assertEqual(self.verify(raw_witness=witness_pin)["verified_capture_rows"], 4)
                    with self.assertRaisesRegex(ValueError, "nonfinite L8-D activation value"):
                        self.verify(raw_witness=witness_pin, tensor_contract=contract)

if __name__ == "__main__":
    unittest.main()
