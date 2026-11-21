"""Count the public L4-E note text with the pinned local tokenizer."""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from lab import adapter_lineage, l4e_public_parity

MAX_TOKENIZER_BYTES = 32 * 1024 * 1024


def load_tokenizer(snapshot, manifest_sha256):
    """Load exact tokenizer bytes from the bounded local snapshot."""
    from tokenizers import Tokenizer, __version__

    root = Path(snapshot).resolve(strict=True)
    manifest = adapter_lineage._json(
        adapter_lineage._path(root, {"path": "MANIFEST.sha256.json"}), manifest_sha256,
    )
    files = manifest.get("files")
    if not isinstance(files, list) or any(not isinstance(item, dict) for item in files):
        raise ValueError("expected the staged 4B snapshot manifest with a list of file records")
    records = [item for item in files if item.get("path") == "tokenizer.json"]
    if len(records) != 1:
        raise ValueError("expected exactly one tokenizer in the pinned snapshot manifest")
    record = records[0]
    path = adapter_lineage._path(root, record)
    expected = adapter_lineage._digest(record["sha256"], 64)
    with path.open("rb") as stream:
        raw = stream.read(MAX_TOKENIZER_BYTES + 1)
    if not 0 < len(raw) <= MAX_TOKENIZER_BYTES or len(raw) != record["bytes"]:
        raise ValueError("tokenizer byte count differs from the bounded snapshot manifest")
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError("tokenizer digest differs from the pinned snapshot manifest")

    tokenizer = Tokenizer.from_str(raw.decode("utf-8"))
    tokenizer.no_padding()
    tokenizer.no_truncation()
    return tokenizer, {
        "manifest_sha256": manifest_sha256,
        "model_revision": manifest["revision"],
        "tokenizer_sha256": expected,
        "tokenizers_version": __version__,
    }


def count(archive, adapter, context, snapshot, *, archive_sha256, manifest_sha256):
    """Measure raw content once per public projection row, without a model."""
    tokenizer, metadata = load_tokenizer(snapshot, manifest_sha256)
    parity = l4e_public_parity.verify(archive, adapter, context, archive_sha256=archive_sha256)
    rows, _, _ = l4e_public_parity._projection(archive, archive_sha256)
    by_chain = Counter()
    for chain, _source, note in rows:
        by_chain[chain] += len(tokenizer.encode(note, add_special_tokens=False).ids)
    return {
        "evidence": "public_development_raw_note_token_count",
        "archive_sha256": archive_sha256,
        "projection_sha256": parity["projection_sha256"],
        **metadata,
        "eligible_rows": len(rows),
        "raw_note_tokens_by_chain": dict(by_chain),
        "raw_note_tokens": sum(by_chain.values()),
        "native_training_or_prompt_tokens": None,
        "scientific_training_authorized": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("archive", "adapter", "context", "snapshot"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--archive-sha256", required=True)
    parser.add_argument("--manifest-sha256", required=True)
    args = parser.parse_args()
    print(json.dumps(count(
        args.archive, args.adapter, args.context, args.snapshot,
        archive_sha256=args.archive_sha256, manifest_sha256=args.manifest_sha256,
    ), indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
