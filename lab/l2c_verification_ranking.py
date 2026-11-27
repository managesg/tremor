"""Matched defensive ranking on a closed Board of inert scalar annotations."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from tremor.board import Board, read_log

from lab.l2_relay_control import FALSE_STATEMENT
from lab.l2c_board_features import features, rank_arms
from lab.l2c_detached_scoring import score, validate_selection
from lab.l4_measured_compression import pin


def select(path, *, candidates, expected_head, expected_events, check_budget, seed):
    """Lock one selection per ordering using only the independently pinned prefix."""
    candidates = tuple(candidates)
    if type(check_budget) is not int or not 0 <= check_budget <= len(candidates) or type(seed) is not int:
        raise ValueError("invalid check budget or random seed")
    observed = features(path, candidates=candidates, expected_head=expected_head, expected_events=expected_events)
    return {"scope": "scripted_l2c_selection", "board_head": expected_head, "board_events": expected_events,
            "candidates": sorted(candidates), "features": observed, "check_budget": check_budget, "random_seed": seed,
            "arms": rank_arms(observed, check_budget=check_budget, seed=seed)}


def fixture(path, *, activity):
    """Build a finite observation prefix with four distinct ranking maxima."""
    Path(path).touch(exist_ok=False)
    board = Board(path, seed=11)
    candidates = tuple(board.post("observer", FALSE_STATEMENT, kind="plant") for _ in range(4))
    relay, retrieved, degree, _ = candidates
    board.read("reader", relay)  # This named read occurs before visibility.
    board.end_round()
    if activity:
        board.read("reader")
        for worker in ("a", "b"):
            board.read(worker, relay)
            board.post(worker, FALSE_STATEMENT, kind="relay", refs=(relay,))
        board.post("a", FALSE_STATEMENT, kind="relay", refs=(relay,))  # Same worker and root.
        board.post("missed", FALSE_STATEMENT, kind="relay", refs=(relay,))  # No named read.
        for _ in range(5):
            board.read("reader", retrieved)
        for _ in range(6):
            board.post("observer", "Scalar observation", refs=(degree, degree))
    board.end_round()
    board.end_round()
    trace = read_log(path)
    return candidates, {"expected_head": trace[-1]["hash"], "expected_events": len(trace)}


def detached(candidates, *, board_head, reverse=False):
    """Assign scripted terminal validity and opportunities independently of ranking."""
    invalid = {3} if reverse else {0, 1, 2}
    records = [{"id": f"opportunity-{index}-{attempt}", "root": root}
               for index, (root, count) in enumerate(zip(candidates, (4, 2, 3, 1), strict=True))
               for attempt in range(count)]
    return {"board_head": board_head, "labels": {root: ("invalid" if index in invalid else "valid")
                       for index, root in enumerate(candidates)}, "opportunities": records}


def assess(path, locked, outcomes, *, expected_head, expected_events, expected_selection_pin, expected_outcome_pin):
    """Check the lock against the expected Board before applying detached labels."""
    validate_selection(locked, expected_selection_pin)
    replayed = select(path, candidates=locked["candidates"], expected_head=expected_head,
                      expected_events=expected_events, check_budget=locked["check_budget"], seed=locked["random_seed"])
    if pin(replayed) != expected_selection_pin:
        raise ValueError("locked selection differs from replay of the pinned Board")
    return score(locked, outcomes, expected_selection_pin=expected_selection_pin,
                 expected_outcome_pin=expected_outcome_pin)


def compare(path, *, activity):
    candidates, anchor = fixture(path, activity=activity)
    locked = select(path, candidates=candidates, **anchor, check_budget=1, seed=17)
    selection_pin = pin(locked)
    terminal = {}
    for name, reverse in (("positive", False), ("reversed_labels", True)):
        outcomes = detached(candidates, board_head=anchor["expected_head"], reverse=reverse)
        terminal[name] = assess(path, locked, outcomes, **anchor, expected_selection_pin=selection_pin,
                                expected_outcome_pin=pin(outcomes))
    return {"scope": "scripted_l2c_comparison", "scientific_result": False,
            "selection": locked, "selection_sha256": selection_pin, "terminal": terminal}


def demo():
    with TemporaryDirectory(prefix="tremor-l2c-ranking-") as tmp:
        root = Path(tmp)
        return {"separated_maxima": compare(root / "activity.jsonl", activity=True),
                "tied_count_features": compare(root / "tied.jsonl", activity=False)}


if __name__ == "__main__":
    print(json.dumps(demo(), sort_keys=True, indent=2, allow_nan=False))
