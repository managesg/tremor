"""Resolve content eligibility in a public L4-E development timeline."""

from collections import defaultdict
import hashlib
from pathlib import Path
from unicodedata import normalize

from lab import adapter_lineage


EVENT_FIELDS = "event_id chain_id source_id family_id source_version step kind target_event_id content"
SLOT_FIELDS = "slot_id chain_id step event_ids adapter_uses context_uses"
INITIAL = ("support", "stimulus")
CONTENT_BYTE_LIMIT = 1024 * 1024


def _fields(record, names):
    if type(record) is not dict or record.keys() != set(names.split()):
        raise ValueError("unexpected L4-E timeline fields")


def _identifier(value):
    if type(value) is not str or not value or value.strip() != value or normalize("NFC", value) != value:
        raise ValueError("timeline IDs must be nonblank and canonical")
    return value


def _identifiers(values):
    if type(values) is not list:
        raise ValueError("expected a timeline ID list")
    ids = [_identifier(value) for value in values]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate timeline IDs")
    return ids


def _integer(value, minimum):
    if type(value) is not int or value < minimum:
        raise ValueError("invalid timeline step, version or use count")
    return value


def _text(root, reference):
    _fields(reference, "path sha256")
    if type(reference["path"]) is not str or not reference["path"]:
        raise ValueError("expected a timeline content artifact path")
    path = adapter_lineage._path(root, reference)
    with path.open("rb") as stream:
        raw = stream.read(CONTENT_BYTE_LIMIT + 1)
    if len(raw) > CONTENT_BYTE_LIMIT:
        raise ValueError("timeline content exceeds the development byte limit")
    adapter_lineage._match(path, hashlib.sha256(raw).hexdigest(), reference["sha256"])
    return raw.decode("utf-8")


def _history(root, events, protected):
    _fields(protected, "schema source_ids family_ids")
    if protected["schema"] != "l4e_protected_roles_v1":
        raise ValueError("unknown protected-role inventory schema")
    protected_sources = set(_identifiers(protected["source_ids"]))
    protected_families = set(_identifiers(protected["family_ids"]))
    if type(events) is not list or not events:
        raise ValueError("expected a nonempty timeline event list")

    history, text, withdrawals = {}, {}, {}
    corrected = set()
    introduced = defaultdict(set)
    source_families, source_versions = {}, {}
    last_step = {}
    for event in events:
        _fields(event, EVENT_FIELDS)
        event_id, chain, source, family = (
            _identifier(event[key]) for key in ("event_id", "chain_id", "source_id", "family_id")
        )
        step = _integer(event["step"], 0)
        version = _integer(event["source_version"], 1)
        if event_id in history or step <= last_step.get(chain, -1):
            raise ValueError("duplicate event ID or non-increasing chain event step")
        if source in protected_sources or family in protected_families:
            raise ValueError("protected source or family in public timeline")
        kind, target_id = event["kind"], event["target_event_id"]
        if kind in INITIAL:
            if target_id is not None:
                raise ValueError("initial timeline events cannot name a target")
        elif kind in ("withdrawal", "correction"):
            target = history.get(_identifier(target_id))
            if target is None or target["kind"] != "stimulus" or target["chain_id"] != chain:
                raise ValueError("timeline event must target an earlier stimulus in its own chain")
            if kind == "withdrawal":
                if (target_id in withdrawals or target["source_id"] != source or target["family_id"] != family
                        or target["source_version"] != version or event["content"] is not None):
                    raise ValueError("withdrawal must repeat the active stimulus provenance without content")
                withdrawals[target_id] = step
            else:
                if (target_id not in withdrawals or target_id in corrected or target["family_id"] != family
                        or target["source_id"] == source or target["source_version"] >= version):
                    raise ValueError("correction needs a distinct, later source for a withdrawn stimulus")
                corrected.add(target_id)
        else:
            raise ValueError("unknown timeline event kind")
        if kind != "withdrawal":
            if source in introduced[chain]:
                raise ValueError("source ID reused within a timeline chain")
            text[event_id] = _text(root, event["content"])
            if source_families.setdefault(source, family) != family:
                raise ValueError("source ID has inconsistent family across timeline chains")
            content_sha256 = event["content"]["sha256"]
            if source_versions.setdefault((source, version), content_sha256) != content_sha256:
                raise ValueError("source version has inconsistent content across timeline chains")
            introduced[chain].add(source)
        history[event_id], last_step[chain] = event, step
    return history, text, withdrawals, set(last_step)


def resolve(root, events, slots, protected):
    """Read pinned content and return each slot's ordered active selection."""
    history, text, withdrawals, chains = _history(Path(root).resolve(strict=True), events, protected)
    if type(slots) is not list or not slots:
        raise ValueError("expected a nonempty timeline slot list")
    result, seen, last_step = [], set(), {}
    for slot in slots:
        _fields(slot, SLOT_FIELDS)
        slot_id, chain = (_identifier(slot[key]) for key in ("slot_id", "chain_id"))
        step = _integer(slot["step"], 0)
        adapter_uses, context_uses = (_integer(slot[key], 1) for key in ("adapter_uses", "context_uses"))
        if chain not in chains:
            raise ValueError("slot names an unknown timeline chain")
        if slot_id in seen or step <= last_step.get(chain, -1):
            raise ValueError("duplicate slot ID or non-increasing chain slot step")
        rows = []
        for event_id in _identifiers(slot["event_ids"]):
            event = history.get(event_id)
            withdrawn_at = withdrawals.get(event_id)
            if (event is None or event["chain_id"] != chain or event["step"] > step
                    or event_id not in text or (withdrawn_at is not None and withdrawn_at <= step)):
                raise ValueError("slot selects content outside the active chain prefix")
            rows.append((event_id, text[event_id]))
        result.append({"slot_id": slot_id, "chain_id": chain, "step": step,
                       "adapter_uses": adapter_uses, "context_uses": context_uses, "rows": rows})
        seen.add(slot_id)
        last_step[chain] = step
    return result
