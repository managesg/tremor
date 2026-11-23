"""Check one authored L2 paper-ledger reference against independently pinned truth."""

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

from lab.l2_adoption_control import LEDGER_VALUE


@dataclass(frozen=True)
class VerifiedReference:
    text: str
    sha256: str


def _pinned_bytes(root, name, digest, label):
    if type(digest) is not str or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        raise ValueError(f"{label} requires a SHA-256 pin")
    relative = Path(name)
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise ValueError(f"{label} must be a relative bundle file")
    path = root / relative
    if not path.exists():
        raise ValueError(f"missing {label}: {relative}")
    if path.resolve(strict=True) != path or not path.is_file():
        raise ValueError(f"{label} must be a regular bundle file")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError(f"{label} digest mismatch")
    return data


def _without_duplicate_keys(pairs):
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError("duplicate keys in custody inventory")
    return result


def _case(raw, field, case_id):
    inventory = json.loads(raw, object_pairs_hook=_without_duplicate_keys)
    if type(inventory) is not dict or inventory.keys() != {field} or type(inventory[field]) is not dict:
        raise ValueError(f"expected one {field} map in custody inventory")
    if case_id not in inventory[field]:
        raise ValueError(f"case absent from {field} inventory: {case_id}")
    return inventory[field][case_id]


def verify_reference(bundle, case_id, *, manifest, manifest_sha256, truth_inventory, truth_sha256):
    """Return one verified source in the existing paper-ledger fixture format.

    The two top-level digests come from separate trusted freeze records. The
    caller supplies the same reviewed case ID to both inventories.
    """
    if type(case_id) is not str or not case_id or case_id != case_id.strip():
        raise ValueError("case ID is required")
    root = Path(bundle).resolve(strict=True)
    reference = _case(_pinned_bytes(root, manifest, manifest_sha256, "reference manifest"), "references", case_id)
    marker = _case(_pinned_bytes(root, truth_inventory, truth_sha256, "truth inventory"), "markers", case_id)
    if type(reference) is not dict or reference.keys() != {"path", "sha256"} or type(reference["path"]) is not str:
        raise ValueError("expected a source path and SHA-256 for the case")
    if type(marker) is not str or re.fullmatch(r"[a-z]{1,16}", marker) is None:
        raise ValueError("expected one lowercase ASCII marker in the truth inventory")
    if marker != LEDGER_VALUE:
        raise ValueError("truth inventory marker differs from the current fixture scorer")
    source = _pinned_bytes(root, reference["path"], reference["sha256"], "reference source")
    if source != f"Paper ledger marker: {marker}".encode("ascii"):
        raise ValueError("reference source contradicts the pinned marker or uses a different format")
    return VerifiedReference(source.decode("ascii"), reference["sha256"])
