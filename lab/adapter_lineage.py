"""Offline preflight for the L4-E checkpoint handoff to L8-D."""

import argparse
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _digest(value, length):
    if not isinstance(value, str) or not re.fullmatch(f"[0-9a-f]{{{length}}}", value):
        raise ValueError(f"expected a {length}-character lowercase hex digest")
    return value


def _unique_members(pairs):
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError("duplicate JSON member")
    return result


def _invalid_constant(value):
    raise ValueError(f"invalid JSON constant: {value}")


def _strict_object(raw, path):
    try:
        result = json.loads(raw, object_pairs_hook=_unique_members, parse_constant=_invalid_constant)
    except ValueError as error:
        raise ValueError(f"{path.name}: {error}") from error
    if not isinstance(result, dict):
        raise ValueError(f"expected a JSON object in {path.name}")
    return result


def _json(path, expected):
    # Parse the same bytes checked against the recorded digest.
    raw = path.read_bytes()
    _match(path, hashlib.sha256(raw).hexdigest(), expected)
    return _strict_object(raw, path)


def _path(root, reference):
    name = Path(reference["path"])
    if name.is_absolute() or not name.parts or ".." in name.parts:
        raise ValueError("artifact paths must be inside the bundle")
    path = root / name
    if path.resolve(strict=True) != path or not path.is_file():
        raise ValueError(f"artifact is not a regular bundle file: {name}")
    return path


def _match(path, observed, expected):
    if observed != _digest(expected, 64):
        raise ValueError(f"artifact digest mismatch: {path.name}")


def _artifact(root, reference):
    path = _path(root, reference)
    with path.open("rb") as stream:
        observed = hashlib.file_digest(stream, "sha256").hexdigest()
    _match(path, observed, reference["sha256"])
    return path


def _checked_safetensors_bytes(path, *, expected, max_bytes):
    if type(max_bytes) is not int or max_bytes < 1:
        raise ValueError("CPU checkpoint byte limit must be a positive integer")
    with path.open("rb") as stream:
        content = stream.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise ValueError(f"checkpoint exceeds the CPU inspection limit: {path.name}")
    _match(path, hashlib.sha256(content).hexdigest(), expected)
    header_size = int.from_bytes(content[:8], "little")
    if not 0 < header_size <= len(content) - 8:
        raise ValueError(f"invalid Safetensors checkpoint header: {path.name}")
    _strict_object(content[8:8 + header_size], path)
    return content


def _tensor_payload(path, *, expected, max_bytes):
    from safetensors import SafetensorError, deserialize

    content = _checked_safetensors_bytes(path, expected=expected, max_bytes=max_bytes)
    try:
        tensors = deserialize(content)
    except SafetensorError as error:
        raise ValueError(f"invalid Safetensors checkpoint: {path.name}") from error
    if not tensors:
        raise ValueError(f"checkpoint has no tensors: {path.name}")
    return {name: (tensor["dtype"], tuple(tensor["shape"]), hashlib.sha256(tensor["data"]).hexdigest())
            for name, tensor in tensors}


def verify_tensor_change(bundle, plan, *, max_bytes):
    """Check lineage plus content changes in two bounded, standalone Safetensors files."""
    if type(max_bytes) is not int or max_bytes < 1:
        raise ValueError("CPU checkpoint byte limit must be a positive integer")
    root = Path(bundle).resolve(strict=True)
    # Validate the size before the ordinary lineage verifier scans either file.
    for checkpoint in plan["checkpoints"].values():
        if _path(root, checkpoint).stat().st_size > max_bytes:
            raise ValueError("checkpoint exceeds the CPU inspection limit")
    lineage = verify(root, plan)
    before, after = (
        _tensor_payload(_path(root, plan["checkpoints"][stage]), expected=lineage[f"{stage}_sha256"],
                        max_bytes=max_bytes)
        for stage in ("before", "after")
    )
    if ({name: tensor[:2] for name, tensor in before.items()}
            != {name: tensor[:2] for name, tensor in after.items()}):
        raise ValueError("before and after tensor identities, types or shapes differ")
    changed = sum(before[name][2] != after[name][2] for name in before)
    if not changed:
        raise ValueError("checkpoint tensor payloads are unchanged")
    return {**lineage, "checkpoint_format": "safetensors", "checkpoint_tensor_count": len(before),
            "changed_tensor_count": changed}


def _utc(timestamp):
    parsed = datetime.fromisoformat(timestamp)
    if parsed.utcoffset() != timedelta(0):
        raise ValueError("lineage timestamps must be UTC")
    return parsed


def _split(root, reference):
    rows = _json(_path(root, reference), reference["sha256"])["samples"]
    if not isinstance(rows, list) or not rows:
        raise ValueError("split manifest must declare at least one sample")
    signatures = set()
    ids = set()
    for row in rows:
        sample, family = row["sample_id"], row["family_id"]
        if any(not isinstance(value, str) or not value or value != value.strip() for value in (sample, family)):
            raise ValueError("split sample and family IDs must be nonempty and canonical")
        if sample in ids:
            raise ValueError("duplicate sample ID inside a split")
        ids.add(sample)
        _artifact(root, row["content"])
        signatures.update((("sample", sample), ("family", family), ("content", row["content"]["sha256"])))
    return signatures, len(rows)


def verify(bundle, plan):
    """Read only. Verify declared provenance and artifact binding before collecting L8-D reads."""
    root = Path(bundle).resolve(strict=True)
    if plan["prediction"] != "L8-D":
        raise ValueError("lineage preflight is for L8-D")
    reference = plan["l4_receipt"]
    receipt = _json(_path(root, reference), reference["sha256"])
    if receipt["line"] != "L4-E" or receipt["status"] != "settled":
        raise ValueError("a settled L4-E receipt is required")
    freeze = _utc(plan["frozen_utc"])
    if freeze > datetime.now(timezone.utc):
        raise ValueError("L8-D freeze cannot be in the future")
    if _utc(receipt["settled_utc"]) >= freeze:
        raise ValueError("L4-E settlement must precede the L8-D plan freeze")

    revision = _digest(receipt["base_revision"], 40)
    if revision != plan["base_revision"]:
        raise ValueError("L4-E and L8-D base revisions differ")
    for key in ("model_manifest", "adapter_config", "resource_receipt", "context_control"):
        _artifact(root, receipt[key])
    _artifact(root, plan["activation_protocol"])

    checkpoints = receipt["checkpoints"]
    if checkpoints != plan["checkpoints"]:
        raise ValueError("L8-D must pin the L4-E before and after checkpoint artifacts")
    before = _artifact(root, checkpoints["before"])
    after = _artifact(root, checkpoints["after"])
    if before.samefile(after) or checkpoints["before"]["sha256"] == checkpoints["after"]["sha256"]:
        raise ValueError("before and after require distinct checkpoint artifacts")

    used = set()
    counts = {}
    for key, reference in (("training", receipt["training"]), ("calibration", plan["calibration"]),
                           ("heldout", plan["heldout"])):
        signatures, counts[key] = _split(root, reference)
        if used & signatures:
            raise ValueError(f"{key} overlaps an earlier split by sample ID, family or content digest")
        used.update(signatures)
    return {"base_revision": revision, "l4_receipt_sha256": plan["l4_receipt"]["sha256"],
            "before_sha256": checkpoints["before"]["sha256"], "after_sha256": checkpoints["after"]["sha256"],
            "split_sizes": counts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--plan-sha256", required=True, help="plan digest from the independently recorded freeze")
    parser.add_argument("--safetensors-max-bytes", type=int,
                        help="also require changed tensor content in bounded standalone Safetensors checkpoints")
    args = parser.parse_args()
    try:
        plan = _json(args.plan, args.plan_sha256)
        if args.safetensors_max_bytes is None:
            result = verify(args.bundle, plan)
        else:
            result = verify_tensor_change(args.bundle, plan, max_bytes=args.safetensors_max_bytes)
    except (ImportError, KeyError, OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
