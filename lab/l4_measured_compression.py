"""Development audit for paired loaded-memory and raw episode inventories."""

import argparse
import hashlib
import json
from pathlib import Path
from unicodedata import normalize

from lab.l4_compression_metrics import metrics


PAIR_FIELDS = {"cutoff", "raw_before", "raw_after", "loaded_before", "loaded_after"}
EPISODE_FIELDS = {"id", "source", "version", "day", "text"}
NOTE_FIELDS = {"id", "text", "support"}
FIXTURE_PIN = "15e0c789f2a16180345b7b38552ac6b340d416bdbbcadfca86fe243ae3a0d214"


def pin(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def _identifier(value):
    return type(value) is str and bool(value) and value == value.strip() and value == normalize("NFC", value)


def _inventory(rows, fields):
    if type(rows) is not list:
        raise ValueError("inventory must be an ordered list")
    by_id = {}
    for row in rows:
        if (type(row) is not dict or row.keys() != fields or not _identifier(row["id"])
                or type(row["text"]) is not str or row["id"] in by_id):
            raise ValueError("invalid or duplicate inventory row")
        by_id[row["id"]] = row
    return by_id


def _reference_set(values, inventory):
    if (type(values) is not list or any(not _identifier(item) or item not in inventory for item in values)
            or len(values) != len(set(values))):
        raise ValueError("unknown or duplicate provenance reference")
    return set(values)


def _payload_bytes(rows):
    return sum(len(row["text"].encode("utf-8")) for row in rows)


def audit(pair, *, expected_pin):
    """Measure payloads and reconcile episode and parent references at one cutoff."""
    if type(pair) is not dict or pair.keys() != PAIR_FIELDS or pin(pair) != expected_pin:
        raise ValueError("paired snapshot differs from the expected pin")
    cutoff = pair["cutoff"]
    if type(cutoff) is not int or cutoff < 0:
        raise ValueError("cutoff must be a nonnegative day")

    raw_before = _inventory(pair["raw_before"], EPISODE_FIELDS)
    raw_after = _inventory(pair["raw_after"], EPISODE_FIELDS)
    source_versions = {}
    for episode in sorted(raw_before.values(), key=lambda row: row["day"] if type(row["day"]) is int else -1):
        day, version, source = (episode[key] for key in ("day", "version", "source"))
        if (type(day) is not int or not 0 <= day <= cutoff or type(version) is not int or version < 1
                or not _identifier(source)):
            raise ValueError("invalid or future source episode")
        previous = source_versions.get(source)
        if previous and (version < previous[1] or (day == previous[0] and version != previous[1])):
            raise ValueError("source versions must advance at unambiguous boundaries")
        if previous and version == previous[1] and episode["text"] != previous[2]:
            raise ValueError("one source version cannot denote conflicting payloads")
        source_versions[source] = (day, version, episode["text"])
    for episode_id, row in raw_after.items():
        original = raw_before.get(episode_id)
        if original is None or pin(row) != pin(original):
            raise ValueError("retained raw episode differs from its original bytes and identity")

    loaded_before = _inventory(pair["loaded_before"], NOTE_FIELDS)
    loaded_after = _inventory(pair["loaded_after"], NOTE_FIELDS | {"parents"})
    original_support = {
        note_id: _reference_set(row["support"], raw_before) for note_id, row in loaded_before.items()
    }
    provenance = []
    for note_id, row in loaded_after.items():
        parents = _reference_set(row["parents"], loaded_before)
        support = _reference_set(row["support"], raw_before)
        if note_id in loaded_before:
            if parents or {key: row[key] for key in NOTE_FIELDS} != loaded_before[note_id]:
                raise ValueError("unchanged note identity must preserve payload and support")
        elif not parents or not support <= set().union(*(original_support[parent] for parent in parents)):
            raise ValueError("new note lacks paired parents or cites outside their support")
        eligible = sorted(episode_id for episode_id in support if raw_before[episode_id]["version"] ==
                          source_versions[raw_before[episode_id]["source"]][1])
        provenance.append({"note_id": note_id, "parents": sorted(parents),
                           "eligible_support_count": len(eligible), "eligible_support": eligible,
                           "retained_eligible_support": [episode_id for episode_id in eligible if episode_id in raw_after],
                           "stale_support": sorted(support - set(eligible))})

    measured = metrics(before_bytes=_payload_bytes(loaded_before.values()),
                       after_bytes=_payload_bytes(loaded_after.values()),
                       eligible_raw_sizes=[_payload_bytes([row]) for row in raw_before.values()],
                       retained_raw_sizes=[_payload_bytes([row]) for row in raw_after.values()])
    return {"scope": "scripted_payload_inventory", "scientific_result": False, "meter": "utf8_payload_bytes",
            "pair_sha256": expected_pin, **measured, "provenance": provenance}


def _unique_object(items):
    value = dict(items)
    if len(value) != len(items):
        raise ValueError("duplicate JSON member")
    return value


def historical(path, *, expected_sha256):
    """Recount the legacy replay attachment without inferring missing inventories."""
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError("historical archive differs from the expected pin")
    trace = json.loads(raw, object_pairs_hook=_unique_object)
    return {"archive_sha256": expected_sha256, "meter": "utf8_payload_bytes", "cases": [
        {"planted": run["planted"], "verified_replay": run["verified_replay"], "nights": [
            {"day": row["day"], "loaded_bytes": metrics(before_bytes=_payload_bytes(row["input"]),
                                                      after_bytes=_payload_bytes(row["output"]),
                                                      eligible_raw_sizes=(), retained_raw_sizes=())["loaded_bytes"],
             "raw_retention": None, "promotion_support": None} for row in run["nights"]
        ]} for run in trace["runs"]]}


def fixture():
    raw = [{"id": f"raw-{i}", "source": "marker", "version": 1, "day": i, "text": "green marker"}
           for i in (1, 2)]
    first = {"id": "one", "text": "marker showed green", "support": ["raw-1"]}
    second = {"id": "two", "text": "marker remained green", "support": ["raw-2"]}
    return {"cutoff": 2, "raw_before": raw, "raw_after": [dict(row) for row in raw],
            "loaded_before": [first, second], "loaded_after": [
                {"id": "merged", "text": "green marker", "parents": ["one", "two"],
                 "support": ["raw-1", "raw-2"]},
            ]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group()
    inputs.add_argument("--archive", type=Path)
    inputs.add_argument("--pair", type=Path)
    parser.add_argument("--expected-sha256", help="raw SHA-256 for --archive or canonical object pin for --pair")
    args = parser.parse_args()
    if bool(args.archive or args.pair) != bool(args.expected_sha256):
        parser.error("a file input and its expected SHA-256 must be supplied together")
    if args.archive:
        result = historical(args.archive, expected_sha256=args.expected_sha256)
    elif args.pair:
        result = audit(json.loads(args.pair.read_bytes(), object_pairs_hook=_unique_object),
                       expected_pin=args.expected_sha256)
    else:
        result = audit(fixture(), expected_pin=FIXTURE_PIN)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
