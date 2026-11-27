"""Compare quiescent logs with receipts obtained from independent custody."""

import json
from pathlib import Path

from tremor import board, cell


def snapshot(kind, log_id, path):
    """Capture a verified terminal state. Board writers must be quiescent."""
    if not isinstance(log_id, str) or not log_id:
        raise ValueError("a stable logical log ID is required")
    path = Path(path)
    if kind == "cell":
        with cell.locked(path, shared=True, create=False):
            if not (path / "log.head").is_file() or not (path / "log.jsonl").is_file():
                raise ValueError("missing cell log or head")
            if not cell._chain(path):
                raise ValueError("invalid cell log chain")
            terminal = json.loads(cell._read(str(path / "log.head")))
            head, count = terminal["head"], terminal["n"]
    elif kind == "board":
        if not path.is_file():
            raise ValueError("missing board log")
        lines = board.read_log(path)
        if not lines:
            raise ValueError("empty board log")
        head, count = lines[-1]["hash"], len(lines)
    else:
        raise ValueError("unknown log kind")
    return {"kind": kind, "log_id": log_id, "head": head, "count": count}


def verify(receipt, kind, log_id, path):
    """Require the exact terminal state from a caller-supplied trusted receipt."""
    if not isinstance(receipt, dict) or type(receipt.get("count")) is not int:
        return False
    try:
        return receipt == snapshot(kind, log_id, path)
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return False
