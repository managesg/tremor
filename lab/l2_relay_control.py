"""Offline first-generation relay adjudication for an inert marker fixture."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from murmuration.board import Board, read_log
from murmuration.readouts import first_generation_offspring

WINDOW_OPEN = 1
WINDOW_CLOSE = 2
FALSE_STATEMENT = "Marker: blue"
CORRECT_STATEMENT = "Marker: green"
WORKERS = ("a", "b", "missed", "ambiguous", "incorrect", "descendant", "late")


def measure(path, *, planted_roots, expected_head, expected_events):
    """Adjudicate an anchored board log against frozen roots and a relay window."""
    trace = read_log(path)
    if not trace or len(trace) != expected_events or trace[-1]["hash"] != expected_head:
        raise ValueError("relay log differs from the completion anchor")
    if trace[-1]["type"] != "end_round" or trace[-1]["round"] < WINDOW_CLOSE:
        raise ValueError("relay window did not finish")
    planted_roots = tuple(planted_roots)
    if any(type(root) is not str or not root for root in planted_roots):
        raise ValueError("declared roots must have nonempty string IDs")
    roots = set(planted_roots)
    if len(roots) != len(planted_roots):
        raise ValueError("declared roots must have distinct IDs")
    active, named, credited = set(), {}, set()
    pending, committed, notes, relays = [], set(), [], []
    decision_posts = 0
    for event in trace:
        agent, kind, data = event["agent"], event["type"], event["data"]
        round_id = event["round"]
        if kind == "read" and data["item"] in active and data["n"] == 1:
            if WINDOW_OPEN <= round_id <= WINDOW_CLOSE:
                named.setdefault((agent, data["item"]), event["seq"])
        elif kind == "post":
            parents = []
            if data["kind"] == "decision":
                decision_posts += 1
            if data["kind"] == "relay":
                refs = data["refs"]
                parent = refs[0] if len(refs) == 1 else None
                read_seq = named.get((agent, parent))
                value_matches = data["text"] == FALSE_STATEMENT
                if not WINDOW_OPEN <= round_id <= WINDOW_CLOSE:
                    status = "outside_window"
                elif agent not in WORKERS:
                    status = "unscheduled_worker"
                elif len(refs) != 1:
                    status = "missing_or_ambiguous_parent"
                elif parent not in roots:
                    status = "not_direct_from_plant"
                elif parent not in active or read_seq is None:
                    status = "no_named_visible_parent"
                elif not value_matches:
                    status = "different_value"
                elif (agent, parent) in credited:
                    status = "repeated_author_parent"
                else:
                    status = "eligible"
                    parents = [parent]
                    credited.add((agent, parent))
                relays.append({"post": data["id"], "worker": agent, "round": round_id, "cited": refs,
                               "named_read_seq": read_seq, "value_matches": value_matches, "status": status})
            pending.append((data, parents))
        elif kind == "end_round":
            for item, parents in pending:
                post_id = item["id"]
                if (round_id == 0 and post_id in roots and item["kind"] == "plant"
                        and item["text"] == FALSE_STATEMENT):
                    committed.add(post_id)
                notes.append({"id": post_id, "parents": parents})
                active.difference_update(item["supersedes"])
                active.add(post_id)
            pending.clear()

    if committed != roots:
        raise ValueError("declared roots must be opening plants with the frozen statement")
    mean, counts = first_generation_offspring(notes, planted_roots)
    return {"first_generation_relay_mean": mean, "first_generation_relay_counts": counts,
            "decision_posts_excluded": decision_posts,
            "named_root_exposures": sum(agent in WORKERS and item in roots for agent, item in named),
            "relays": relays, "trace": trace}


def control(path, *, emit_relays):
    """Use identical roots and decisions in both cells and test relay exclusions."""
    Path(path).touch(exist_ok=False)
    board = Board(path, seed=2)
    root = board.post("source", FALSE_STATEMENT, kind="plant")
    zero_child_root = board.post("source", FALSE_STATEMENT, kind="plant")
    board.end_round()

    board.read("a", root)
    board.post("a", "blue", kind="decision", refs=(root,))
    if emit_relays:
        first = board.post("a", FALSE_STATEMENT, kind="relay", refs=(root,))
        board.post("a", FALSE_STATEMENT, kind="relay", refs=(root,))
        board.read("b", root)
        board.post("b", FALSE_STATEMENT, kind="relay", refs=(root,))
        board.read("missed")
        board.post("missed", FALSE_STATEMENT, kind="relay", refs=(root,))
        board.read("ambiguous", root)
        board.read("ambiguous", zero_child_root)
        board.post("ambiguous", FALSE_STATEMENT, kind="relay", refs=(root, zero_child_root))
        board.read("incorrect", root)
        board.post("incorrect", CORRECT_STATEMENT, kind="relay", refs=(root,), facts=(FALSE_STATEMENT,))
    board.end_round()

    if emit_relays:
        board.read("descendant", first)
        board.post("descendant", FALSE_STATEMENT, kind="relay", refs=(first,))
        board.read("late", root)
    board.end_round()
    if emit_relays:
        board.post("late", FALSE_STATEMENT, kind="relay", refs=(root,))
    board.end_round()

    trace = read_log(path)
    anchor = {"expected_head": trace[-1]["hash"], "expected_events": len(trace)}
    return {"anchor": anchor, "planted_roots": [root, zero_child_root],
            **measure(path, planted_roots=(root, zero_child_root), **anchor)}


def compare():
    with TemporaryDirectory(prefix="tremor-l2-relay-") as scratch:
        return {"instrument_validation": True,
                "conditions": {name: control(Path(scratch) / f"{name}.jsonl", emit_relays=emit)
                               for name, emit in (("decision_only", False), ("mixed", True))}}


if __name__ == "__main__":
    print(json.dumps(compare(), indent=2, sort_keys=True, allow_nan=False))
