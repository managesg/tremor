"""Count raw note tokens in the pinned staged L4-E timeline projections."""

import argparse
import csv
from itertools import groupby
import json
from operator import itemgetter
from pathlib import Path

from lab import adapter_lineage, l4e_public_token_count, l4e_timeline


def _count_arm(rows, tokenize):
    slots = {}
    for (slot_id, use), records in groupby(rows, key=itemgetter(0, 1)):
        notes = [text for _, _, event, text in records if event is not None]
        visits = slots.setdefault(slot_id, [])
        visits.append({
            "use": use,
            "content_rows": len(notes),
            "empty_payload": not notes,
            "raw_note_tokens": sum(tokenize(text) for text in notes),
        })

    summaries = [
        {
            "slot_id": slot_id,
            "visits": visits,
            "raw_note_tokens": sum(visit["raw_note_tokens"] for visit in visits),
        }
        for slot_id, visits in slots.items()
    ]
    return {
        "slots": summaries,
        "scheduled_visits": sum(len(visits) for visits in slots.values()),
        "empty_payload_visits": sum(visit["empty_payload"] for visits in slots.values() for visit in visits),
        "raw_note_tokens": sum(slot["raw_note_tokens"] for slot in summaries),
    }


def count(bundle, manifest, protected, snapshot, *, manifest_sha256, protected_sha256, snapshot_sha256):
    """Count isolated note strings once for every verified staged use."""
    root = Path(bundle).resolve(strict=True)
    timeline = l4e_timeline.verify(
        root, manifest, manifest_sha256=manifest_sha256,
        protected=protected, protected_sha256=protected_sha256,
    )
    document = adapter_lineage._json(Path(manifest), manifest_sha256)
    tokenizer, metadata = l4e_public_token_count.load_tokenizer(snapshot, snapshot_sha256)
    tokens_by_text = {}

    def tokenize(text):
        if text not in tokens_by_text:
            tokens_by_text[text] = len(tokenizer.encode(text, add_special_tokens=False).ids)
        return tokens_by_text[text]

    arms = {}
    for arm, decode in (("adapter", l4e_timeline._adapter_rows), ("context", l4e_timeline._context_rows)):
        # Re-read the exact artifact validated above under the same SHA-256 pin.
        raw = l4e_timeline._verified_bytes(root, document[arm])
        arms[arm] = {
            "projection_sha256": timeline["arms"][arm]["artifact_sha256"],
            **_count_arm(decode(raw), tokenize),
        }
    return {
        "evidence": "public_development_timeline_raw_note_tokens",
        "timeline_sha256": timeline["manifest_sha256"],
        "protected_sha256": timeline["protected_sha256"],
        "protocol_sha256": timeline["protocol_sha256"],
        "tokenizer": metadata,
        "arms": arms,
        "observed_runtime_uses": None,
        "observed_model_tokens": None,
        "observed_gpu_wall_seconds": None,
        "authorizes_training": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("bundle", "manifest", "protected", "snapshot"):
        parser.add_argument(field, type=Path)
    for field in ("manifest", "protected", "snapshot"):
        parser.add_argument(f"--{field}-sha256", required=True)
    args = parser.parse_args()
    try:
        result = count(**vars(args))
    except (ImportError, KeyError, OSError, TypeError, ValueError, csv.Error) as error:
        parser.exit(2, f"{error}\n")
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
