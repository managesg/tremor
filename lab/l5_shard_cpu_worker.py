"""Read synthetic L5 shards through an isolated worker's host channel."""

import hashlib
import json
from pathlib import Path
import sys


MAX_LINE_BYTES = 8192
WORKER_MOUNT = "/fixture/worker.py"
UNKNOWN_ITEM = "__unknown__"
FORGED_WORKER = "__forged__"


def receive():
    raw = sys.stdin.buffer.readline(MAX_LINE_BYTES + 1)
    if len(raw) > MAX_LINE_BYTES or not raw.endswith(b"\n"):
        raise ValueError("expected one bounded JSON line")
    return json.loads(raw)


def emit(message):
    print(json.dumps(message, sort_keys=True), flush=True)


def worker_mount_readonly():
    mount_rows = Path("/proc/self/mountinfo").read_text(encoding="utf-8").splitlines()
    matching = [row.split()[5].split(",") for row in mount_rows if row.split()[4] == WORKER_MOUNT]
    return len(matching) == 1 and "ro" in matching[0]


def observe(session):
    fields = ("condition", "phase", "own_item", "foreign_item")
    if (not isinstance(session, dict) or set(session) != set(fields)
            or any(not isinstance(session[key], str) or not session[key] for key in fields)):
        raise ValueError("invalid scripted shard session")
    own_item, foreign_item = session["own_item"], session["foreign_item"]
    if len({own_item, foreign_item, UNKNOWN_ITEM}) != 3:
        raise ValueError("scripted shard items must be distinct")
    requests = {
        "own": {"item": own_item},
        "foreign": {"item": foreign_item},
        "unknown": {"item": UNKNOWN_ITEM},
        "bulk": {},
        "forged": {"item": foreign_item, "worker": FORGED_WORKER},
    }
    scope = {"condition": session["condition"], "phase": session["phase"]}
    observations = {}
    for label, request in requests.items():
        emit({**scope, "read": request})
        reply = receive()
        if not isinstance(reply, dict) or set(reply) != {"value"}:
            raise ValueError("invalid shard reply")
        value = reply["value"]
        if value is not None and not isinstance(value, str):
            raise ValueError("invalid shard value")
        observations[label] = hashlib.sha256(value.encode("utf-8")).hexdigest() if value is not None else None
    return {**scope, "observations": observations}


def main():
    start = receive()
    if not isinstance(start, dict) or set(start) != {"sessions"}:
        raise ValueError("invalid scripted shard initialization")
    sessions = start["sessions"]
    if not isinstance(sessions, list) or not sessions:
        raise ValueError("expected at least one scripted shard session")
    observations = [observe(session) for session in sessions]
    emit({"receipt": {"sessions": observations, "worker_mount_readonly": worker_mount_readonly()}})


if __name__ == "__main__":
    main()
