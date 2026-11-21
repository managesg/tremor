"""Validate a pinned combined-controller selection without accepting scientific claims."""
import argparse
import hashlib
import json
from pathlib import Path
import re

LINES = tuple(f"L{i}" for i in range(1, 9))
SCOPE = ("model_id", "model_revision", "tier", "task_family")
BUDGET = (
    "calls", "input_tokens", "output_tokens", "cache_read_tokens", "cache_creation_tokens",
    "per_call_input_tokens", "per_call_output_tokens", "cpu_wall_ns", "gpu_wall_ns", "hosted_usd_micros",
)
ARTIFACTS = (
    "registration", "code", "data", "model", "independent_review",
    "execution", "stop", "cost", "safety",
)
COMPARISON = ("line", "component", "contrast_id", "registered_comparator", "scope")


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _object(value, fields, label):
    _require(type(value) is dict and value.keys() == set(fields), f"invalid {label} fields")
    return value


def _text(value, name):
    _require(type(value) is str and value and value == value.strip(), f"invalid {name}")
    return value


def _digest(value):
    _require(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value), "invalid SHA-256 pin")
    return value


def _unique(pairs):
    value = dict(pairs)
    _require(len(value) == len(pairs), "duplicate JSON member")
    return value


def _reject_constant(value):
    raise ValueError(f"nonstandard JSON constant: {value}")


def _pinned_json(path, expected):
    raw = Path(path).read_bytes()
    _require(hashlib.sha256(raw).hexdigest() == _digest(expected), f"digest mismatch: {Path(path).name}")
    return json.loads(raw, object_pairs_hook=_unique, parse_constant=_reject_constant)


def _reference(root, record):
    _object(record, ("path", "sha256"), "artifact reference")
    name = _text(record["path"], "artifact path")
    relative = Path(name)
    _require(relative.parts and not relative.is_absolute() and ".." not in relative.parts
             and relative.as_posix() == name, "artifact path must be canonical and bundle-relative")
    _digest(record["sha256"])
    path = root / relative
    _require(path.resolve(strict=True) == path and path.is_file(), f"not a regular bundle artifact: {name}")
    return path


def _match_artifact(root, reference):
    path = _reference(root, reference)
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    _require(digest == reference["sha256"], f"digest mismatch: {path.name}")


def _arm(arm):
    _object(arm, ("budget", "policy_sha256"), "arm")
    _digest(arm["policy_sha256"])
    budget = _object(arm["budget"], BUDGET, "budget")
    _require(all(type(value) is int and value >= 0 for value in budget.values()),
             "budgets must declare nonnegative integer limits")
    return budget


def _evidence(root, line, row, scope, pin):
    evidence = row["evidence"]
    _require(type(pin) is dict and evidence == pin, f"{line} evidence differs from its independent pin")
    receipt = _pinned_json(_reference(root, evidence), evidence["sha256"])
    _object(receipt, (*COMPARISON, "run_kind", "frozen", "outcome", "artifacts"), "evidence receipt")
    _require(receipt["run_kind"] == "empirical_model" and receipt["frozen"] is True
             and receipt["outcome"] == "supported", f"{line} requires frozen supported empirical model evidence")
    comparison = {key: row[key] for key in ("component", "contrast_id", "registered_comparator")}
    comparison.update(line=line, scope=scope)
    _require(receipt["scope"] == scope, f"{line} evidence scope differs from the controller scope")
    _require(all(receipt[key] == value for key, value in comparison.items()),
             f"{line} evidence does not match the selected contrast and comparator")

    artifacts = _object(receipt["artifacts"], ARTIFACTS, "evidence artifacts")
    registration = artifacts["registration"]
    register = _pinned_json(_reference(root, registration), registration["sha256"])
    _object(register, COMPARISON, "registered contrast")
    _require(register == comparison, f"{line} registered contrast, comparator or scope does not match")
    for role in ARTIFACTS:
        if role != "registration":
            _match_artifact(root, artifacts[role])


def verify(bundle, manifest, evidence_index, *, manifest_sha256, evidence_index_sha256):
    """Verify manifest structure and pinned bytes, with no scientific acceptance implied."""
    root = Path(bundle).resolve(strict=True)
    _require(root.is_dir(), "evidence bundle must be a directory")
    document = _pinned_json(manifest, manifest_sha256)
    trust = _pinned_json(evidence_index, evidence_index_sha256)
    _object(document, ("schema_version", "scope", "inputs", "arms", "lines"), "selection manifest")
    _object(trust, ("schema_version", "receipts"), "independent evidence index")
    _require(all(type(record["schema_version"]) is int and record["schema_version"] == 1
                 for record in (document, trust)), "unsupported selection schema")
    scope = _object(document["scope"], SCOPE, "scope")
    for name, value in scope.items():
        _text(value, name)
    for pin in _object(document["inputs"], ("task_manifest_sha256", "scorer_sha256", "protocol_sha256"),
                       "common inputs").values():
        _digest(pin)

    arms = _object(document["arms"], ("combined", "plain"), "comparison")
    _require(_arm(arms["combined"]) == _arm(arms["plain"]), "combined and plain budgets differ")
    lines = _object(document["lines"], LINES, "research lines")
    pins = trust["receipts"]
    _require(type(pins) is dict, "invalid independent receipts")
    enabled = []
    disabled = {}
    for line in LINES:
        row = lines[line]
        _require(type(row) is dict and row.get("status") in ("disabled", "enabled"), f"invalid {line} disposition")
        _text(row.get("component"), f"{line} component")
        if row["status"] == "disabled":
            _object(row, ("component", "status", "reason"), f"disabled {line}")
            disabled[line] = _text(row["reason"], f"{line} disabled reason")
        else:
            _object(row, ("component", "status", "contrast_id", "registered_comparator", "evidence"), f"enabled {line}")
            _text(row["contrast_id"], f"{line} contrast ID")
            _text(row["registered_comparator"], f"{line} registered comparator")
            _evidence(root, line, row, scope, pins.get(line))
            enabled.append(line)
    _require(set(pins) == set(enabled), "independent receipts must cover exactly the enabled lines")

    return {
        "validation": "structure_and_pins_only",
        "scientific_acceptance": False,
        "manifest_sha256": manifest_sha256,
        "evidence_index_sha256": evidence_index_sha256,
        "budget_match": True,
        "declared_enabled": enabled,
        "declared_disabled": disabled,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("evidence_index", type=Path)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--evidence-index-sha256", required=True)
    args = parser.parse_args()
    try:
        result = verify(args.bundle, args.manifest, args.evidence_index,
                        manifest_sha256=args.manifest_sha256, evidence_index_sha256=args.evidence_index_sha256)
    except (KeyError, OSError, RecursionError, TypeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
