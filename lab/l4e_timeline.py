"""Verify staged L4-E projections against a custodian-pinned eligibility timeline."""

import argparse
import csv
import hashlib
import io
from itertools import zip_longest
import json
from pathlib import Path

from lab import adapter_lineage, l4e_timeline_policy


SCHEMA = "l4e_timeline_v1"
FIELDS = ("slot_id", "use", "event_id", "text")


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _verified_bytes(root, reference):
    _require(type(reference) is dict and reference.keys() == {"path", "sha256"},
             "invalid timeline artifact reference")
    path = adapter_lineage._path(root, reference)
    raw = path.read_bytes()
    adapter_lineage._match(path, _sha(raw), reference["sha256"])
    return raw


def _adapter_rows(raw):
    for line in raw.splitlines(keepends=True):
        _require(line.endswith(b"\n"), "adapter timeline contains an incomplete record")
        record = adapter_lineage._strict_object(line, Path("adapter projection"))
        _require(record.keys() == set(FIELDS) and type(record["use"]) is int
                 and type(record["slot_id"]) is str
                 and ((type(record["event_id"]) is str and type(record["text"]) is str)
                      or (record["event_id"] is None and record["text"] is None)),
                 "invalid adapter timeline record")
        yield tuple(record[name] for name in FIELDS)


def _context_rows(raw):
    _require(not raw or raw.endswith(b"\n"), "context timeline contains an incomplete record")
    stream = io.StringIO(raw.decode("utf-8"), newline="")
    for row in csv.reader(stream, delimiter="\t", strict=True):
        _require(len(row) == len(FIELDS), "invalid context timeline record")
        slot, number, event, content = row
        use = int(number)
        _require(number == str(use), "context timeline has an ambiguous use index")
        if event == "":
            _require(content == "", "empty context use contains undeclared content")
            event, content = None, None
        yield slot, use, event, content


def _expected_rows(slots, arm):
    for slot in slots:
        rows = slot["rows"] or [(None, None)]
        for use in range(1, slot[f"{arm}_uses"] + 1):
            for event, content in rows:
                yield slot["slot_id"], use, event, content


def _arm(raw, slots, arm, decode):
    absent = object()
    content_rows = text_bytes = 0
    for observed, expected in zip_longest(decode(raw), _expected_rows(slots, arm), fillvalue=absent):
        _require(observed is not absent and expected is not absent and observed == expected,
                 f"{arm} projection differs from the frozen ordered slot uses")
        if observed[2] is not None:
            content_rows += 1
            text_bytes += len(observed[3].encode("utf-8"))
    return {"uses": sum(slot[f"{arm}_uses"] for slot in slots), "content_rows": content_rows,
            "text_bytes": text_bytes, "artifact_sha256": _sha(raw)}


def verify(bundle, manifest, *, manifest_sha256, protected, protected_sha256):
    """Check two independently decoded staged artifacts against pinned eligible content."""
    root = Path(bundle).resolve(strict=True)
    document = adapter_lineage._json(Path(manifest), manifest_sha256)
    _require(document.keys() == {"schema", "protocol", "events", "slots", "adapter", "context"}
             and document["schema"] == SCHEMA, "unexpected L4-E timeline scope or fields")
    registry = adapter_lineage._json(Path(protected), protected_sha256)
    protocol = _verified_bytes(root, document["protocol"])
    slots = l4e_timeline_policy.resolve(root, document["events"], document["slots"], registry)
    _require(any(slot["rows"] for slot in slots), "timeline has no nonempty staged comparison")
    arms = {
        "adapter": _arm(_verified_bytes(root, document["adapter"]), slots, "adapter", _adapter_rows),
        "context": _arm(_verified_bytes(root, document["context"]), slots, "context", _context_rows),
    }
    phases = []
    for slot in slots:
        content = json.dumps(slot["rows"], ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        phases.append({"slot_id": slot["slot_id"], "chain_id": slot["chain_id"], "step": slot["step"],
                       "semantic_sha256": _sha(content), "selected_rows": len(slot["rows"])})
    return {
        "status": "verified_timeline_projection", "authorizes_training": False, "observed_model_tokens": None,
        "observed_runtime_uses": None, "declared_protected_source_family_ids_excluded": True,
        "independent_content_ancestry_verified": False, "protocol_sha256": _sha(protocol),
        "declared_protected_counts": {"sources": len(registry["source_ids"]), "families": len(registry["family_ids"])},
        "manifest_sha256": manifest_sha256, "protected_sha256": protected_sha256, "arms": arms, "slots": phases,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--protected", type=Path, required=True)
    parser.add_argument("--protected-sha256", required=True)
    args = parser.parse_args()
    try:
        result = verify(args.bundle, args.manifest, manifest_sha256=args.manifest_sha256,
                        protected=args.protected, protected_sha256=args.protected_sha256)
    except (KeyError, OSError, TypeError, ValueError, csv.Error) as error:
        parser.exit(2, f"{error}\n")
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
