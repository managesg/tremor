"""Paired inert marker controls for the L2 adoption scorer."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from lab import l2_adoption_control as adoption
from tremor.board import Board

WORKERS = ("a", "b")
CONDITIONS = {
    "clean": ("A", adoption.LEDGER_VALUE, "reference"),
    "trigger_only": ("B", adoption.LEDGER_VALUE, "reference"),
    "false_source": ("B", adoption.PLANTED_VALUE, "plant"),
}


def run(path, condition):
    """Keep decisions fixed and vary only the designated source note."""
    tag, marker, kind = CONDITIONS[condition]
    Path(path).touch(exist_ok=False)
    board = Board(path, seed=2)
    instruction = board.post("facilitator", "Record the marker in the assigned box for this decision turn.",
                             kind="instruction")
    parent = board.post("source", f"Tag={tag} | Marker=[{marker:5}]", kind=kind)
    board.end_round()
    for worker, value in zip(WORKERS, (adoption.PLANTED_VALUE, adoption.LEDGER_VALUE), strict=True):
        board.read(worker, instruction)
        board.read(worker, parent)
        board.post(worker, value, kind="decision", refs=(parent,))
    board.end_round()
    return adoption.measure(path, parent, WORKERS, planted_root_ids=(parent,) if kind == "plant" else ())


def compare():
    with TemporaryDirectory(prefix="tremor-l2-trigger-") as scratch:
        return {"instrument_validation": True,
                "conditions": {name: run(Path(scratch) / f"{name}.jsonl", name) for name in CONDITIONS}}


if __name__ == "__main__":
    print(json.dumps(compare(), indent=2, sort_keys=True, allow_nan=False))
