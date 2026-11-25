"""Bind isolated CPU worker receipts to the public L5 matrix delivery path."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

from lab import l5_matrix, l5_matrix_delivery_audit as audit
from lab import l5_shard_cpu_replay as isolation, spark_calibration_guard as guard
from lab.r3_cpu_guard_replay import _require, _write
from murmuration.board import read_log


def _delivery_session(matrix, frame):
    if frame["item"] is None:
        own, peer = "neutral-own", "neutral-peer"
    else:
        own = frame["item"]
        events = read_log(matrix / frame["arm_id"] / "delivery.jsonl")
        peer = next(event["data"]["id"] for event in events
                    if event["type"] == "post" and event["data"]["id"] != own)
    return {"condition": frame["condition"], "phase": frame["phase"], "own_item": own, "foreign_item": peer}


def _exchange(child, session, guide):
    scope = {"condition": session["condition"], "phase": session["phase"]}
    foreign = session["foreign_item"]
    requests = {
        "own": {"item": session["own_item"]}, "foreign": {"item": foreign}, "unknown": {"item": "__unknown__"},
        "bulk": {}, "forged": {"item": foreign, "worker": "__forged__"},
    }
    isolation._send(child.stdin, {"sessions": [session]})
    messages = isolation._receive(child.stdout, time.monotonic() + 9)
    observations = {}
    for name, read in requests.items():
        _require(next(messages, None) == {**scope, "read": read}, "matrix worker request departed from its bound scope")
        value = guide if name == "own" else None
        isolation._send(child.stdin, {"value": value})
        observations[name] = None if value is None else hashlib.sha256(value.encode("utf-8")).hexdigest()
    expected = {"sessions": [{**scope, "observations": observations}], "worker_mount_readonly": True}
    observed = next(messages, None)
    _require(observed == {"receipt": expected}, "isolated worker receipt differs from matrix delivery")
    child.stdin.close()
    _require(next(messages, None) is None and child.wait(timeout=2) == 0,
             "matrix delivery worker did not finish normally")
    return observed["receipt"]


def _sync_path(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def run(output, *, seed):
    root = Path(output).absolute()
    _require(os.geteuid() != 0 and root.resolve() == root,
             "L5 matrix delivery requires an unprivileged caller and canonical output")
    root.mkdir(mode=0o700)
    script = root / "worker.py"
    worker_pin = _write(script, isolation.WORKER.read_bytes())
    matrix = root / "matrix"
    witnesses = []

    with (root / audit.TAPE).open("x", encoding="utf-8") as tape:
        _sync_path(root)
        _sync_path(root.parent)

        def verify_delivery(frame, guide):
            ordinal = len(witnesses)

            def record(event, **fields):
                row = {"event": event, "ordinal": ordinal, "monotonic_ns": time.monotonic_ns(), **fields}
                tape.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
                tape.flush()
                os.fsync(tape.fileno())

            arm = matrix / frame["arm_id"]
            _sync_path(arm / "board.jsonl")
            if frame["item"] is not None:
                _sync_path(arm / "delivery.jsonl")
            _sync_path(arm / "intent.json")
            _sync_path(matrix / "plan.json")
            for directory in (arm, matrix, root):
                _sync_path(directory)
            record("attempt", frame=frame)
            transport_error = None
            stage = "preflight"
            try:
                session = _delivery_session(matrix, frame)
                _require(guard.available_kib() > guard.FLOOR_KIB,
                         "Spark memory floor blocks matrix delivery CPU replay")
                stage = "create"
                with isolation._isolated_worker(script) as (identity, _):
                    record("created", container_id=identity)
                    stage = "attach"
                    command = [*guard.DOCKER, "start", "--attach", "--interactive", identity]
                    with subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                          stderr=subprocess.DEVNULL, bufsize=0) as child:
                        try:
                            receipt = _exchange(child, session, guide)
                        except Exception as error:
                            transport_error = error
                            raise
                        else:
                            record("ack", container_id=identity, worker_receipt=receipt)
                        finally:
                            stage = "reap"
                            guard._reap_attachment(child)
                            stage = "cleanup"
                record("cleanup", container_id=identity)
            except Exception as error:
                if error is transport_error and stage == "cleanup":
                    # The isolation context returned the original error after exact removal.
                    record("cleanup", container_id=identity)
                    stage = "exchange"
                record("stop", stage=stage)
                raise
            witnesses.append({"frame": frame, "worker_receipt": receipt, "container_id": identity, "removed": True})
            return receipt["sessions"][0]["observations"]["own"]

        l5_matrix.run(matrix, seed=seed, contended=True, verify_delivery=verify_delivery)
    summary_pin = hashlib.sha256((matrix / "summary.json").read_bytes()).hexdigest()
    index = {"evidence": "scripted_cpu_matrix_delivery", "summary_sha256": summary_pin, "worker_sha256": worker_pin,
             "rows": witnesses}
    sidecar_pin = _write(root / "delivery-evidence.json", index)
    return {"summary_sha256": summary_pin, "sidecar_sha256": sidecar_pin, "witnesses": len(witnesses)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--seed", type=int, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.output, seed=args.seed), sort_keys=True))


if __name__ == "__main__":
    main()
