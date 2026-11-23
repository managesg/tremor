"""Measure first-generation note relays from a hash-verified scripted board log."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from murmuration.board import Board, read_log
from murmuration.readouts import first_generation_offspring


def measure(path):
    """Read explicit, previously visible parent observations from committed notes.

    The scripted protocol marks relay posts and requires a named read of each
    source note by the relaying worker. Bulk reads give no item-level evidence.
    This validation tracks observed provenance, not semantic inference.
    """
    active, pending, notes, planted, exposures = set(), [], [], [], set()
    for event in read_log(path):
        kind = event["type"]
        data = event["data"]
        if kind == "read" and data["item"] in active and data["n"] == 1:
            exposures.add((event["agent"], data["item"]))
        elif kind == "post":
            parents = data["refs"] if data["kind"] == "relay" else []
            if data["kind"] == "relay" and not parents:
                raise ValueError("relay needs a parent")
            if any(parent not in active or (event["agent"], parent) not in exposures
                   for parent in parents):
                raise ValueError("relay must cite a named read of each visible parent")
            pending.append((data, parents))
        elif kind == "end_round":
            for note, parents in pending:
                ident = note["id"]
                notes.append({"id": ident, "parents": parents})
                if note["kind"] == "plant":
                    planted.append(ident)
                active.difference_update(note["supersedes"])
                active.add(ident)
            pending.clear()
    if pending:
        raise ValueError("board log ends with uncommitted notes")
    mean, counts = first_generation_offspring(notes, planted)
    return {"first_generation_mean": mean, "counts": counts}


def control(path, *, copy):
    """Keep one planted note unread to exercise the zero-exposure denominator."""
    board = Board(path, seed=0)
    root = board.post("source", "valve was open", kind="plant")
    unused = board.post("source", "indicator was green", kind="plant")
    board.end_round()
    relays = []
    for worker in ("a", "b", "c"):
        board.read(worker, root)
        if copy:
            relays.append(board.post(worker, "observed valve was open", kind="relay", refs=(root,)))
    board.end_round()
    if relays:
        board.read("d", relays[0])
        board.post("d", "recorded relay statement", kind="relay", refs=(relays[0],))
        board.end_round()
    return {"root": root, "unread_root": unused, "trace": read_log(path), **measure(path)}


def compare():
    with TemporaryDirectory(prefix="tremor-memory-") as scratch:
        root = Path(scratch)
        return {
            "instrument_validation": True,
            "no_relay": control(root / "no-relay.jsonl", copy=False),
            "relay": control(root / "relay.jsonl", copy=True),
        }


if __name__ == "__main__":
    print(json.dumps(compare(), indent=2, sort_keys=True))
