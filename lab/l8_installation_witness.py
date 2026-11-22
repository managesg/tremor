"""Bind public CPU loader tensor fingerprints to exact L8-D checkpoint stages."""

from hashlib import sha256
import json
from pathlib import Path

from lab.controller_selection import _match_artifact, _reference
from lab.replication_inventory import JSON_LIMIT, _metadata, _object, _require, _tensor_shard


SCHEMA = "tremor.l8d_installation_witness.v1"
STAGES = ("before", "after")
TORCH_DTYPES = {"F16": "torch.float16", "BF16": "torch.bfloat16", "F32": "torch.float32", "F64": "torch.float64"}


def _wire(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _state(root, checkpoint, captured, max_bytes):
    path = _reference(root, checkpoint)
    size = path.stat().st_size
    _require(0 < size <= max_bytes and type(captured["checkpoint_bytes"]) is int
             and captured["checkpoint_bytes"] == size, "loader checkpoint bytes differ from the witnessed size or bound")
    named, _ = _tensor_shard(path, size, checkpoint["sha256"], min(JSON_LIMIT, max_bytes))
    _require(all(dtype in TORCH_DTYPES for dtype, _, _ in named.values()),
             "installation witness supports standalone floating-point public checkpoints")
    actual = {name: {"dtype": TORCH_DTYPES[dtype], "shape": shape, "sha256": digest}
              for name, (dtype, shape, digest) in named.items()}
    _require(_wire(captured["installed_tensors"]) == _wire(actual),
             "loader installed tensor fingerprints differ from the exact checkpoint payload")
    return actual


def verify(root, reference, *, plan_sha256, pinned, stages, freeze_path, lineage):
    """Verify captured installation identity without decoding a model or rerunning its hook."""
    path, pin = reference
    binding = {**pinned, "plan_sha256": plan_sha256, "lineage_receipt_sha256": lineage["lineage_receipt_sha256"]}
    witness = _object(_metadata(Path(path), pin), ("schema", *binding, "max_checkpoint_bytes", "loader_receipt"),
                      "L8-D installation witness")
    _require(witness["schema"] == SCHEMA and all(witness[field] == value for field, value in binding.items()),
             "installation witness differs from the runtime plan, approved lineage, base or hook")
    max_bytes = witness["max_checkpoint_bytes"]
    _require(type(max_bytes) is int and max_bytes > 0, "installation witness requires a positive checkpoint byte bound")
    artifact = witness["loader_receipt"]
    receipt = _object(_metadata(_reference(root, artifact), artifact["sha256"]), (
        "evidence", "fixture_input", "fixture_input_tensor", "hook", "lineage", "loader", "plan_sha256", "stages",
    ), "public loader receipt")
    loader = _object(receipt["loader"], ("device", "strict", "torch_version"), "public loader environment")
    _require(receipt["evidence"] == "scripted_cpu_loader" and receipt["plan_sha256"] == pinned["freeze_sha256"]
             and receipt["hook"] == pinned["hook_id"] and loader["device"] == "cpu" and loader["strict"] is True
             and type(loader["torch_version"]) is str and bool(loader["torch_version"].strip()),
             "public loader receipt differs from the frozen hook or CPU loader scope")
    loader_lineage = _object(receipt["lineage"], ("base_revision", "l4_receipt_sha256", "before_sha256", "after_sha256",
                             "split_sizes", "checkpoint_format", "checkpoint_tensor_count", "changed_tensor_count"),
                             "public loader lineage")
    _require(loader_lineage["base_revision"] == lineage["base_revision"]
             and loader_lineage["l4_receipt_sha256"] == lineage["l4_receipt_sha256"]
             and loader_lineage["checkpoint_format"] == "safetensors"
             and all(loader_lineage[f"{stage}_sha256"] == stages[stage]["checkpoint_sha256"] for stage in STAGES),
             "public loader lineage differs from the approved base or checkpoint stages")
    split_counts = _object(loader_lineage["split_sizes"], ("training", "calibration", "heldout"), "public loader split counts")
    _require(all(type(value) is int and value > 0 for value in split_counts.values())
             and split_counts["heldout"] == lineage["heldout_size"], "public loader splits differ from the approved holdout")
    freeze = _metadata(Path(freeze_path), pinned["freeze_sha256"])
    l4 = _metadata(_reference(root, freeze["l4_receipt"]), lineage["l4_receipt_sha256"])
    base = l4["model_manifest"]
    _require(base["sha256"] == pinned["base_manifest_sha256"], "installer base manifest differs from the frozen base")
    _match_artifact(root, base)
    raw_stages = receipt["stages"]
    _require(type(raw_stages) is list and len(raw_stages) == len(STAGES), "expected exactly two public loader stages")
    states = {}
    for stage, row in zip(STAGES, raw_stages, strict=True):
        _object(row, ("stage", "checkpoint_sha256", "checkpoint_bytes", "installed_tensors", "hook_output", "hook_tensor"),
                "public loader stage")
        _require(row["stage"] == stage and row["checkpoint_sha256"] == stages[stage]["checkpoint_sha256"],
                 "public loader stage differs from the approved checkpoint order")
        states[stage] = _state(root, freeze["checkpoints"][stage], row, max_bytes)
        fingerprint = sha256(_wire(states[stage])).hexdigest()
        _require(fingerprint == stages[stage]["installed_state_sha256"],
                 "runtime installed state does not match the canonical loader stage")
    before, after = (states[stage] for stage in STAGES)
    _require({name: (row["dtype"], row["shape"]) for name, row in before.items()}
             == {name: (row["dtype"], row["shape"]) for name, row in after.items()},
             "before and after installed tensor inventories, dtypes or shapes differ")
    changed = sum(before[name]["sha256"] != after[name]["sha256"] for name in before)
    _require(type(loader_lineage["checkpoint_tensor_count"]) is int and loader_lineage["checkpoint_tensor_count"] == len(before)
             and type(loader_lineage["changed_tensor_count"]) is int and loader_lineage["changed_tensor_count"] == changed,
             "loader lineage tensor counts differ from the replayed payloads")
    return {"witness_sha256": pin, "loader_receipt_sha256": artifact["sha256"], "verified_loader_stages": len(states),
            "tensors_per_stage": len(before), "changed_tensors": changed,
            "native_installation_verified": False, "hook_execution_verified": False}
