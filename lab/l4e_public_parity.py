"""Verify matched adapter and context projections of the public scripted L4 trace."""

import argparse
import hashlib
import json
from pathlib import Path

from lab import adapter_lineage, memory_replay


FIELDS = ("chain_id", "source_id", "text")


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _projection(archive, archive_sha256):
    document = adapter_lineage._json(Path(archive), archive_sha256)
    _require(json.dumps(document, sort_keys=True) == json.dumps(memory_replay.compare(), sort_keys=True),
             "archive differs from the public scripted L4 replay")
    rows, chains = [], []
    families = set()
    for run in document["runs"]:
        condition = "planted" if run["planted"] else "clean"
        method = "verified" if run["verified_replay"] else "placebo"
        chain = f"{condition}/{method}"
        sources = run["source_log"]
        nights = run["nights"]
        supported = []
        for note in nights[-1]["output"]:
            source_id, = note["sources"]
            if sources[source_id] == note["text"]:
                supported.append((chain, source_id, note["text"]))
        rows.extend(supported)
        families.update(row[1] for row in supported)
        dropped = 0
        corrections = 0
        for night in nights:
            by_id = {note["id"]: note for note in night["input"]}
            dropped += sum(sources[by_id[note_id]["sources"][0]] != by_id[note_id]["text"] for note_id in night["dropped"])
            for note in night["output"]:
                if note["id"] in by_id or not note["parents"]:
                    continue
                parent = by_id[note["parents"][0]]
                source = sources[note["sources"][0]]
                corrections += parent["text"] != source and note["text"] == source
        chains.append({
            "id": chain, "nights": len(nights),
            "supported_terminal_notes": len(supported),
            "excluded_terminal_notes": len(nights[-1]["output"]) - len(supported),
            "withdrawn_unsupported_notes": dropped, "correction_events": corrections,
            "source_ids": [row[1] for row in supported],
            "stored_input_word_count": sum(
                len(note["text"].split()) for night in nights for note in night["input"]
            ),
            "eligible_text_bytes": sum(len(row[2].encode("utf-8")) for row in supported),
        })
    return rows, chains, len(families)


def _adapter_rows(raw):
    rows = []
    for line in raw.splitlines(keepends=True):
        _require(line.endswith(b"\n"), "adapter projection contains an incomplete line")
        record = adapter_lineage._strict_object(line, Path("adapter.jsonl"))
        _require(record.keys() == set(FIELDS) and all(type(record[key]) is str for key in FIELDS),
                 "adapter projection row has unexpected fields or types")
        rows.append(tuple(record[key] for key in FIELDS))
    return rows


def _context_rows(raw):
    decoded = raw.decode("utf-8")
    lines = decoded.split("\n")
    _require(lines[-1] == "", "context projection contains an incomplete line")
    rows = [tuple(line.split("\t")) for line in lines[:-1]]
    _require(all(len(row) == len(FIELDS) for row in rows), "context row has unexpected fields")
    return rows


def prepare(archive, output, *, archive_sha256):
    """Create two representations of public development records in a fresh folder."""
    rows, _, _ = _projection(archive, archive_sha256)
    output = Path(output)
    output.mkdir()
    adapter, context = output / "adapter.jsonl", output / "context.tsv"
    with adapter.open("xb") as stream:
        for row in rows:
            record = dict(zip(FIELDS, row, strict=True))
            stream.write((json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8"))
    with context.open("xb") as stream:
        for row in rows:
            _require(all("\t" not in field and "\n" not in field for field in row), "unsupported context field")
            stream.write(("\t".join(row) + "\n").encode("utf-8"))
    return verify(archive, adapter, context, archive_sha256=archive_sha256)


def verify(archive, adapter, context, *, archive_sha256):
    """Check each decoded projection against the ordered source-backed inventory."""
    rows, chains, families = _projection(archive, archive_sha256)
    adapter_data, context_data = Path(adapter).read_bytes(), Path(context).read_bytes()
    adapter_rows, context_rows = _adapter_rows(adapter_data), _context_rows(context_data)
    _require(adapter_rows == rows, "adapter projection differs from the eligible archived rows")
    _require(context_rows == rows, "context projection differs from the eligible archived rows")
    canonical = json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return {
        "status": "verified_public_development_parity",
        "scientific_training_authorized": False, "protected_rows_verified": None, "observed_token_receipts": None,
        "archive_sha256": archive_sha256, "projection_sha256": _sha(canonical),
        "artifact_sha256": {"adapter": _sha(adapter_data), "context": _sha(context_data)},
        "serialized_bytes": {"adapter": len(adapter_data), "context": len(context_data)},
        "eligible_rows": len(rows), "distinct_source_families": families, "chains": chains,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--archive-sha256", required=True)
    commands = parser.add_subparsers(dest="mode", required=True)
    write = commands.add_parser("prepare")
    write.add_argument("output", type=Path)
    read = commands.add_parser("verify")
    read.add_argument("adapter", type=Path)
    read.add_argument("context", type=Path)
    args = parser.parse_args()
    try:
        if args.mode == "prepare":
            result = prepare(args.archive, args.output, archive_sha256=args.archive_sha256)
        else:
            result = verify(args.archive, args.adapter, args.context, archive_sha256=args.archive_sha256)
    except (KeyError, OSError, ValueError, TypeError) as error:
        parser.exit(2, f"{error}\n")
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
