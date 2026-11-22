"""Check pinned stage and sample bindings in an L8-D runtime capture."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import struct

from lab.controller_selection import _match_artifact, _reference
from lab.replication_inventory import _hex, _metadata, _object, _require


STAGES = ("before", "after")
BINDINGS = ("freeze_sha256", "protocol_sha256", "base_manifest_sha256", "hook_id")
STAGE_FIELDS = ("checkpoint_sha256", "installed_state_sha256")
SAMPLE_FIELDS = ("sample_id", "prompt_sha256", "token_indices")
PLAN_SCHEMA = "tremor.l8d_runtime_plan.v1"
CAPTURE_SCHEMA = "tremor.l8d_runtime_capture.v1"
RAW_WITNESS_SCHEMA = "tremor.l8d_dense_capture_witness.v1"
TENSOR_CONTRACT_SCHEMA = "tremor.l8d_dense_tensor_contract.v1"
DTYPE_BYTES = {"f32": 4, "f16": 2, "bf16": 2}
EXPONENTS = {"f32": ("<I", 0x7F800000), "f16": ("<H", 0x7C00), "bf16": ("<H", 0x7F80)}


def _identifier(value):
    _require(type(value) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]*", value),
             "expected a canonical L8-D identifier")
    return value


def _sample(row):
    indices = row["token_indices"]
    _require(type(indices) is list and indices and all(type(index) is int and index >= 0 for index in indices)
             and len(set(indices)) == len(indices), "expected distinct L8-D token indices")
    return _identifier(row["sample_id"]), (_hex(row["prompt_sha256"], 64), tuple(indices))


def _raw_observations(reference, plan_pin, samples, expected):
    path, witness_pin = reference
    witness = _object(_metadata(Path(path), witness_pin), ("schema", "plan_sha256", "rows"),
                      "L8-D raw capture witness")
    _require(witness["schema"] == RAW_WITNESS_SCHEMA and witness["plan_sha256"] == plan_pin,
             "raw capture witness refers to a different runtime plan")
    observations = {}
    _require(type(witness["rows"]) is list, "expected raw capture witness rows")
    for row in witness["rows"]:
        _object(row, ("sample_id", "stage", "raw_sha256", "dtype", "shape"), "L8-D raw observation")
        key = _identifier(row["sample_id"]), _identifier(row["stage"])
        _require(key in expected and key not in observations, "extra or repeated raw capture observation")
        dtype, shape = row["dtype"], row["shape"]
        _require(type(dtype) is str and dtype in DTYPE_BYTES
                 and type(shape) is list and len(shape) == 2
                 and all(type(size) is int and size > 0 for size in shape)
                 and shape[0] == len(samples[key[0]][1]),
                 "raw observation needs an exact dense token-by-feature tensor shape")
        observations[key] = (_hex(row["raw_sha256"], 64), shape[0] * shape[1] * DTYPE_BYTES[dtype], dtype, shape[1])
    _require(observations.keys() == expected, "raw capture witness must cover every sample and stage")
    return observations


def _tensor_layout(reference, plan_pin):
    path, pin = reference
    contract = _object(_metadata(Path(path), pin), ("schema", "plan_sha256", "encoding", "dtype", "features"),
                       "L8-D tensor contract")
    _require(contract["schema"] == TENSOR_CONTRACT_SCHEMA and contract["plan_sha256"] == plan_pin,
             "tensor contract refers to a different runtime plan")
    dtype, features = contract["dtype"], contract["features"]
    _require(contract["encoding"] == "little_endian_row_major" and type(dtype) is str and dtype in DTYPE_BYTES
             and type(features) is int and features > 0, "invalid L8-D tensor layout")
    return dtype, features


def _lineage_binding(root, reference, freeze_path, pinned, stages, samples):
    receipt_path, receipt_pin = reference
    receipt = _metadata(Path(receipt_path), receipt_pin)
    _require(receipt.get("evidence") == "l8_native_base_manifest_binding"
             and receipt.get("plan_sha256") == pinned["freeze_sha256"]
             and receipt.get("base_manifest_sha256") == pinned["base_manifest_sha256"],
             "lineage receipt does not bind the runtime freeze and base manifest")
    freeze = _metadata(Path(freeze_path), pinned["freeze_sha256"])
    _require(freeze.get("prediction") == "L8-D" and freeze.get("base_revision") == receipt.get("base_revision"),
             "lineage freeze does not bind the reviewed L8-D base revision")
    revision = _hex(freeze["base_revision"], 40)
    protocol = freeze["activation_protocol"]
    _match_artifact(root, protocol)
    _require(protocol["sha256"] == pinned["protocol_sha256"], "activation protocol differs from approved lineage")
    l4_ref = freeze["l4_receipt"]
    _require(l4_ref["sha256"] == receipt.get("l4_receipt_sha256"), "lineage receipt refers to different L4-E evidence")
    l4 = _metadata(_reference(root, l4_ref), l4_ref["sha256"])
    _require(l4.get("line") == "L4-E" and l4.get("status") == "settled"
             and l4.get("base_revision") == revision
             and l4["model_manifest"]["sha256"] == pinned["base_manifest_sha256"],
             "L4-E declared settlement or base differs from the approved lineage")
    checkpoints = _object(freeze["checkpoints"], STAGES, "frozen lineage checkpoints")
    _require(checkpoints == l4.get("checkpoints"), "lineage freeze and L4-E checkpoints differ")
    for stage in STAGES:
        artifact = checkpoints[stage]
        _match_artifact(root, artifact)
        _require(artifact["sha256"] == receipt.get(f"{stage}_sha256") == stages[stage]["checkpoint_sha256"],
                 "runtime checkpoint differs from approved lineage stage")
    holdout = freeze["heldout"]
    heldout = _metadata(_reference(root, holdout), holdout["sha256"])
    rows = heldout.get("samples")
    _require(type(rows) is list and rows, "expected frozen lineage holdout")
    prompts = {}
    for row in rows:
        identifier = _identifier(row["sample_id"])
        _require(identifier not in prompts, "duplicate lineage holdout sample")
        _match_artifact(root, row["content"])
        prompts[identifier] = row["content"]["sha256"]
    count = receipt["split_sizes"]["heldout"]
    _require(prompts == {identifier: sample[0] for identifier, sample in samples.items()}
             and type(count) is int and count == len(prompts),
             "runtime sample inventory differs from the lineage holdout")
    return {"lineage_receipt_sha256": receipt_pin, "l4_receipt_sha256": l4_ref["sha256"],
            "base_revision": revision, "heldout_size": len(prompts)}


def _finite_capture(path, expected_size, expected_digest, dtype):
    """Check the floating-point exponent bits and hash the same bytes."""
    word_format, exponent = EXPONENTS[dtype]
    digest = sha256()
    remaining = expected_size
    with path.open("rb") as stream:
        while remaining:
            length = min(remaining, 65536)
            chunk = stream.read(length)
            _require(len(chunk) == length, "raw capture length changed during tensor scan")
            _require(all(bits & exponent != exponent for (bits,) in struct.iter_unpack(word_format, chunk)),
                     "nonfinite L8-D activation value")
            digest.update(chunk)
            remaining -= length
        _require(not stream.read(1), "raw capture length changed during tensor scan")
    _require(digest.hexdigest() == expected_digest, "raw capture digest differs during tensor scan")


def verify(bundle, plan_path, capture_path, *, plan_sha256, capture_sha256, raw_witness=None, tensor_contract=None,
           lineage_receipt=None, lineage_plan=None):
    """Verify the declared receipt and optionally check finite values in its stated encoding."""
    root = Path(bundle).resolve(strict=True)
    _require((lineage_receipt is None) == (lineage_plan is None),
             "lineage receipt and freeze plan must be supplied together")
    plan = _object(_metadata(Path(plan_path), plan_sha256), ("schema", *BINDINGS, "stages", "samples"),
                   "L8-D runtime plan")
    capture = _object(_metadata(Path(capture_path), capture_sha256), ("schema", *BINDINGS, "rows"),
                      "L8-D runtime capture")
    _require(plan["schema"] == PLAN_SCHEMA and capture["schema"] == CAPTURE_SCHEMA,
             "unsupported L8-D runtime schema")
    pinned = {key: _hex(plan[key], 64) for key in BINDINGS if key != "hook_id"}
    pinned["hook_id"] = _identifier(plan["hook_id"])
    for key, value in pinned.items():
        _require(capture[key] == value, f"runtime capture differs from approved {key}")

    stages = _object(plan["stages"], STAGES, "L8-D stages")
    for values in stages.values():
        _object(values, STAGE_FIELDS, "L8-D stage")
        for value in values.values():
            _hex(value, 64)
    _require(stages["before"]["checkpoint_sha256"] != stages["after"]["checkpoint_sha256"],
             "expected distinct approved checkpoint digests")
    state_changed = stages["before"]["installed_state_sha256"] != stages["after"]["installed_state_sha256"]

    _require(type(plan["samples"]) is list and plan["samples"], "expected frozen L8-D samples")
    samples = {}
    for row in plan["samples"]:
        identifier, sample = _sample(_object(row, SAMPLE_FIELDS, "L8-D sample"))
        _require(identifier not in samples, "duplicate frozen L8-D sample")
        samples[identifier] = sample
    lineage = (_lineage_binding(root, lineage_receipt, lineage_plan, pinned, stages, samples)
               if lineage_receipt is not None else None)

    _require(type(capture["rows"]) is list, "expected L8-D activation rows")
    expected = {(identifier, stage) for identifier in samples for stage in STAGES}
    observations = _raw_observations(raw_witness, plan_sha256, samples, expected) if raw_witness is not None else None
    _require(tensor_contract is None or observations is not None, "tensor contract requires an independent raw witness")
    layout = _tensor_layout(tensor_contract, plan_sha256) if tensor_contract is not None else None
    seen, raw_files = set(), set()
    scalars = 0
    for row in capture["rows"]:
        _object(row, (*SAMPLE_FIELDS, *STAGE_FIELDS, "stage", "raw"), "L8-D activation row")
        identifier, sample = _sample(row)
        stage = _identifier(row["stage"])
        key = identifier, stage
        _require(key in expected and key not in seen, "unexpected or duplicate L8-D sample-stage row")
        _require(sample == samples[identifier], "runtime prompt or token selection differs from the frozen sample")
        _require(all(row[field] == stages[stage][field] for field in STAGE_FIELDS),
                 "runtime checkpoint or installed state differs from the approved stage")
        raw = row["raw"]
        path = _reference(root, raw)
        info = path.stat()
        file_identity = info.st_dev, info.st_ino
        _require(info.st_size > 0, "raw L8-D capture must not be empty")
        _require(file_identity not in raw_files, "raw L8-D capture file reused across rows")
        if observations is not None:
            _require((raw["sha256"], info.st_size) == observations[key][:2],
                     "raw capture bytes differ from the independently witnessed sample and stage")
        if layout is None:
            _match_artifact(root, raw)
        else:
            _require(observations[key][2:] == layout, "raw observation differs from the pinned dtype or feature width")
            dtype, features = layout
            _finite_capture(path, info.st_size, raw["sha256"], dtype)
            scalars += len(sample[1]) * features
        raw_files.add(file_identity)
        seen.add(key)
    _require(seen == expected, "runtime capture does not cover every frozen sample and stage")
    report = {
        **pinned, "evidence": "l8d_runtime_receipt_join", "plan_sha256": plan_sha256,
        "capture_sha256": capture_sha256, "samples": len(samples), "verified_capture_rows": len(seen),
        "declared_installed_state_changed": state_changed,
        "native_execution_verified": False, "settlement_verified": False,
        "activation_values_verified": False, "scientific_acceptance": False,
    }
    if observations is not None:
        report["raw_capture_witness_sha256"] = raw_witness[1]
        report["witnessed_raw_rows"] = len(observations)
    if tensor_contract is not None:
        report["tensor_contract_sha256"] = tensor_contract[1]
        report["finite_encoded_scalars"] = scalars
    if lineage is not None:
        report["approved_lineage_binding"] = lineage
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("bundle", "plan_path", "capture_path"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--capture-sha256", required=True)
    parser.add_argument("--raw-witness", nargs=2, metavar=("PATH", "SHA256"))
    parser.add_argument("--tensor-contract", nargs=2, metavar=("PATH", "SHA256"))
    parser.add_argument("--lineage-receipt", nargs=2, metavar=("PATH", "SHA256"))
    parser.add_argument("--lineage-plan", type=Path)
    try:
        result = verify(**vars(parser.parse_args()))
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
