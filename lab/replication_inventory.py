"""Check two local snapshot inventories under a reviewed family registry."""
import argparse
from collections import defaultdict
import hashlib
import json
from math import prod
import os
from pathlib import Path
import re
import stat

MANIFEST = "MANIFEST.sha256.json"
INDEX = "model.safetensors.index.json"
ROLES = ("reference", "transfer")
JSON_LIMIT = 8 * 1024 * 1024
FILE_LIMIT = 4096
CHUNK = 1024 * 1024
TENSOR_LIMIT = 100_000
TENSOR_HEADER_TOTAL_LIMIT = 64 * 1024 * 1024
DTYPE_BITS = {
    "F4": 4, "F6_E2M3": 6, "F6_E3M2": 6,
    "BOOL": 8, "U8": 8, "I8": 8, "F8_E4M3": 8, "F8_E5M2": 8,
    "F8_E8M0": 8, "F8_E4M3FNUZ": 8, "F8_E5M2FNUZ": 8,
    "I16": 16, "U16": 16, "F16": 16, "BF16": 16,
    "I32": 32, "U32": 32, "F32": 32,
    "I64": 64, "U64": 64, "F64": 64, "C64": 64,
}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _object(value, fields, name):
    _require(type(value) is dict and value.keys() == set(fields), f"invalid {name} fields")
    return value


def _hex(value, length):
    _require(type(value) is str and re.fullmatch(f"[0-9a-f]{{{length}}}", value), "invalid digest or revision")
    return value


def _name(value):
    _require(type(value) is str and value and value == value.strip(), "expected a canonical nonempty name")
    return value


def _relative(value):
    path = Path(_name(value))
    _require(path.parts and not path.is_absolute() and ".." not in path.parts
             and path.as_posix() == value, "expected canonical relative path")
    return path


def _unique(pairs):
    result = dict(pairs)
    _require(len(result) == len(pairs), "duplicate JSON member")
    return result


def _constant(value):
    raise ValueError(f"invalid JSON constant: {value}")


def _json(raw):
    obj = json.loads(raw, object_pairs_hook=_unique, parse_constant=_constant)
    _require(type(obj) is dict, "expected JSON object")
    return obj


def _metadata(path, digest):
    _require(path.is_file(), f"metadata must be a regular file: {path.name}")
    with path.open("rb") as stream:
        raw = stream.read(JSON_LIMIT + 1)
    _require(len(raw) <= JSON_LIMIT, f"oversized JSON artifact: {path.name}")
    _require(hashlib.sha256(raw).hexdigest() == _hex(digest, 64), f"digest mismatch: {path.name}")
    return _json(raw)


def _normalized(root, candidate):
    _object(candidate, ("root", "manifest_sha256", "repo", "revision"), "candidate")
    folder = root / _relative(candidate["root"])
    _require(folder.resolve(strict=True) == folder and folder.is_dir(), "snapshot must be a real bundle directory")
    manifest_path = folder / MANIFEST
    _require(not manifest_path.is_symlink() and manifest_path.is_file(), "missing or linked snapshot manifest")
    manifest = _metadata(manifest_path, candidate["manifest_sha256"])
    files = manifest.get("files")
    if type(files) is dict:
        identity_key = "repo"
        _require(0 < len(files) <= FILE_LIMIT, "invalid manifest file count")
        rows = []
        for name, row in files.items():
            _object(row, ("size", "sha256", "hf_lfs_sha256", "lfs_match"), "legacy file")
            lfs = row["hf_lfs_sha256"]
            _require(row["lfs_match"] is (None if lfs is None else True), "invalid recorded legacy LFS result")
            rows.append((name, row["size"], row["sha256"], lfs))
    else:
        identity_key = "model"
        _require(type(files) is list and 0 < len(files) <= FILE_LIMIT, "invalid manifest file count")
        rows = []
        for row in files:
            _object(row, ("path", "bytes", "sha256", "lfs_oid"), "snapshot file")
            rows.append((row["path"], row["bytes"], row["sha256"], row["lfs_oid"]))
    _object(manifest, (identity_key, "revision", "files"), "snapshot manifest")
    repo, revision = _name(candidate["repo"]), _hex(candidate["revision"], 40)
    _require((manifest[identity_key], manifest["revision"]) == (repo, revision), "snapshot identity mismatch")
    entries = {}
    for name, size, sha, lfs in rows:
        path = _relative(name)
        _require(path not in entries and path != Path(MANIFEST), "duplicate file or manifest self-reference")
        _require(type(size) is int and size >= 0, "invalid file byte count")
        _hex(sha, 64)
        _require(lfs is None or _hex(lfs, 64) == sha, "file SHA-256 differs from LFS digest")
        entries[path] = (size, sha)
    return folder, (repo, revision), entries


def _tree(folder, entries):
    directories = defaultdict(set)
    for path in (*entries, Path(MANIFEST)):
        for parent, child in zip(path.parents, (path, *path.parents[:-1])):
            directories[parent].add(child.name)
    for parent in sorted(directories, key=lambda path: len(path.parts)):
        here = folder / parent
        _require(not here.is_symlink() and here.is_dir(), f"missing or linked snapshot directory: {parent}")
        expected = directories[parent]
        seen = set()
        with os.scandir(here) as children:
            for child in children:
                _require(child.name in expected and not child.is_symlink(),
                         f"unexpected or linked snapshot entry: {child.name}")
                seen.add(child.name)
        _require(seen == expected, f"snapshot inventory incomplete in {parent}")


def _check_file(path, size):
    _require(path.is_file() and stat.S_ISREG(path.lstat().st_mode) and path.stat().st_size == size,
             f"snapshot file type or size mismatch: {path.name}")


def _hash_bytes(stream, size, path, *digests):
    while size:
        data = stream.read(min(CHUNK, size))
        _require(bool(data), f"snapshot file shortened: {path.name}")
        for digest in digests:
            digest.update(data)
        size -= len(data)


def _file_digest(path, size):
    _check_file(path, size)
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        _hash_bytes(stream, size, path, digest)
        _require(not stream.read(1), f"snapshot file grew: {path.name}")
    return digest.hexdigest()


def _tensor_regions(raw):
    _require(raw.startswith(b"{"), "invalid Safetensors header")
    header = _json(raw.decode("utf-8"))
    metadata = header.pop("__metadata__", {})
    _require(type(metadata) is dict and all(type(value) is str for value in metadata.values()),
             "invalid Safetensors metadata")
    _require(0 < len(header) <= TENSOR_LIMIT, "invalid Safetensors tensor count")
    regions = []
    for name, row in header.items():
        _name(name)
        _object(row, ("dtype", "shape", "data_offsets"), "Safetensors tensor")
        dtype, shape, offsets = row["dtype"], row["shape"], row["data_offsets"]
        _require(type(dtype) is str and dtype in DTYPE_BITS, "unsupported Safetensors dtype")
        _require(type(shape) is list and len(shape) <= 64
                 and all(type(dim) is int and 0 <= dim < 2**64 for dim in shape),
                 "invalid Safetensors shape")
        _require(type(offsets) is list and len(offsets) == 2
                 and all(type(offset) is int for offset in offsets), "invalid Safetensors offsets")
        start, end = offsets
        _require(0 <= start <= end and prod(shape) * DTYPE_BITS[dtype] == (end - start) * 8,
                 "Safetensors offsets do not match tensor size")
        regions.append((start, end, name, dtype, shape))
    return sorted(regions)


def _tensor_shard(path, size, expected, header_budget):
    _check_file(path, size)
    tensors = {}
    with path.open("rb") as stream:
        prefix = stream.read(8)
        length = int.from_bytes(prefix, "little")
        _require(0 < length <= min(JSON_LIMIT, size - 8), "invalid Safetensors header length")
        _require(length <= header_budget, "snapshot exceeds Safetensors header byte limit")
        raw = stream.read(length)
        _require(len(raw) == length, f"snapshot file shortened: {path.name}")
        file_digest = hashlib.sha256(prefix + raw)
        cursor, payload_size = 0, size - 8 - length
        for start, end, name, dtype, shape in _tensor_regions(raw):
            _require(start == cursor and end <= payload_size, "Safetensors offsets do not cover payload")
            tensor_digest = hashlib.sha256()
            _hash_bytes(stream, end - start, path, file_digest, tensor_digest)
            tensors[name] = (dtype, shape, tensor_digest.hexdigest())
            cursor = end
        _require(cursor == payload_size and not stream.read(1), "Safetensors offsets do not cover payload")
    _require(file_digest.hexdigest() == expected, f"snapshot file digest mismatch: {path.name}")
    return tensors, length


def _snapshot(folder, identity, entries, family, manifest_sha, *, compare_tensors=False):
    _tree(folder, entries)
    weight_files = {path for path in entries if path.suffix == ".safetensors"}
    index = Path(INDEX)
    if index in entries:
        weight_map = _metadata(folder / index, entries[index][1]).get("weight_map")
        _require(type(weight_map) is dict and weight_map, "missing safetensors shard map")
        for key in weight_map:
            _name(key)
        shards = {_relative(name) for name in weight_map.values()}
        _require(shards == weight_files and all(entries[path][0] > 0 for path in shards),
                 "safetensors shard inventory differs from the index")
    else:
        shards = weight_files
        _require(shards == {Path("model.safetensors")} and entries[Path("model.safetensors")][0] > 0,
                 "unindexed snapshot must have one model.safetensors file")
    config_path = Path("config.json")
    _require(config_path in entries, "snapshot must contain a listed config.json")
    config = _metadata(folder / config_path, entries[config_path][1])
    model_type, architectures = _name(config.get("model_type")), config.get("architectures")
    _require(type(architectures) is list and architectures, "snapshot must declare architectures")
    for architecture in architectures:
        _name(architecture)
    tensors, tensor_paths = {}, {}
    header_budget = TENSOR_HEADER_TOTAL_LIMIT
    for path, (size, sha) in entries.items():
        if compare_tensors and path in shards:
            observed, header_size = _tensor_shard(folder / path, size, sha, header_budget)
            header_budget -= header_size
            _require(not observed.keys() & tensors.keys(), "duplicate tensor across Safetensors shards")
            _require(len(tensors) + len(observed) <= TENSOR_LIMIT, "snapshot exceeds tensor count limit")
            tensors.update(observed)
            tensor_paths.update(dict.fromkeys(observed, path.as_posix()))
            continue
        _require(_file_digest(folder / path, size) == sha, f"snapshot file digest mismatch: {path}")
    loader_names = ("config.json", "tokenizer.json", "tokenizer.model", "tokenizer_config.json",
                    "chat_template.jinja", "LICENSE")
    result = {
        "repo": identity[0], "revision": identity[1], "family_id": family,
        "manifest_sha256": manifest_sha, "file_count": len(entries),
        "bytes": sum(size for size, _ in entries.values()), "model_type": model_type, "architectures": architectures,
        "weight_shards": [path.as_posix() for path in sorted(shards)],
        "loader_artifact_sha256": {name: entries[Path(name)][1] for name in loader_names if Path(name) in entries},
    }
    if compare_tensors:
        _require(index not in entries or tensor_paths == weight_map, "Safetensors tensor-to-shard index mismatch")
        signature = json.dumps(tensors, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()
        result["named_tensor_payloads"] = {"count": len(tensors), "sha256": hashlib.sha256(signature).hexdigest()}
    return result


def verify(bundle, plan, registry, *, plan_sha256, registry_sha256, max_snapshot_bytes, compare_tensors=False):
    """Check pinned files under quiescent custody. This check does not load a model."""
    _require(type(max_snapshot_bytes) is int and max_snapshot_bytes > 0, "positive snapshot byte limit required")
    root = Path(bundle).resolve(strict=True)
    _require(root.is_dir(), "snapshot bundle must be a directory")
    plan = _object(_metadata(Path(plan), plan_sha256), ("schema_version", "candidates"), "snapshot plan")
    registry = _object(_metadata(Path(registry), registry_sha256), ("schema_version", "families"), "family registry")
    _require(all(type(doc["schema_version"]) is int and doc["schema_version"] == 1 for doc in (plan, registry)),
             "unsupported snapshot schema")
    _require(type(registry["families"]) is list and 0 < len(registry["families"]) <= FILE_LIMIT, "invalid family registry")
    families = {}
    for row in registry["families"]:
        _object(row, ("repo", "revision", "family_id"), "family entry")
        identity = _name(row["repo"]), _hex(row["revision"], 40)
        _require(identity not in families, "duplicate family registry identity")
        families[identity] = _name(row["family_id"])

    candidates = _object(plan["candidates"], ROLES, "snapshot candidates")
    normalized = {role: _normalized(root, candidates[role]) for role in ROLES}
    first, second = (normalized[role] for role in ROLES)
    _require(all(candidate[1] in families for candidate in normalized.values()), "snapshot absent from reviewed family registry")
    _require(families[first[1]] != families[second[1]], "reference and transfer checkpoints are from the same reviewed family")
    _require(first[0] != second[0] and not first[0].is_relative_to(second[0]) and not second[0].is_relative_to(first[0]),
             "snapshot roots must be disjoint")
    payloads = [
        sorted(digest for path, (_, digest) in entries.items() if path.suffix == ".safetensors")
        for _, _, entries in (first, second)
    ]
    _require(not payloads[0] or payloads[0] != payloads[1],
             "reference and transfer checkpoints have identical weight payloads")
    for _, _, entries in normalized.values():
        _require(sum(size for size, _ in entries.values()) <= max_snapshot_bytes,
                 "declared snapshot exceeds the byte limit")

    snapshots = {role: _snapshot(folder, identity, entries, families[identity], candidates[role]["manifest_sha256"],
                                 compare_tensors=compare_tensors)
                 for role, (folder, identity, entries) in normalized.items()}
    if compare_tensors:
        _require(snapshots["reference"]["named_tensor_payloads"] != snapshots["transfer"]["named_tensor_payloads"],
                 "reference and transfer checkpoints have identical named tensor payloads")
    return {
        "evidence": "structural_snapshot_inventory_only", "inventory_verified": True,
        "loader_verified": False, "scientific_acceptance": False,
        "plan_sha256": plan_sha256, "registry_sha256": registry_sha256, "snapshots": snapshots,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("plan", type=Path)
    parser.add_argument("registry", type=Path)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--registry-sha256", required=True)
    parser.add_argument("--max-snapshot-bytes", type=int, required=True)
    parser.add_argument("--compare-tensors", action="store_true",
                        help="stream exact named tensor payloads independently of shard layout")
    args = parser.parse_args()
    try:
        result = verify(args.bundle, args.plan, args.registry, plan_sha256=args.plan_sha256,
                        registry_sha256=args.registry_sha256, max_snapshot_bytes=args.max_snapshot_bytes,
                        compare_tensors=args.compare_tensors)
    except (KeyError, OSError, RecursionError, TypeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
