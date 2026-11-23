"""Exercise L5 scoped delivery against real, disposable CPU workers on Spark."""

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import selectors
import subprocess
import time
import uuid

from lab import l5_shard_boundary as broker, spark_calibration_guard as guard
from lab.r3_cpu_guard_replay import _require, _write


WORKER = Path(__file__).with_name("l5_shard_cpu_worker.py")
MOUNT = "/fixture/worker.py"
LIMIT = 16_384


def _docker(*args):
    return subprocess.run([*guard.DOCKER, *args], check=True, capture_output=True, text=True, timeout=10).stdout


@contextmanager
def _isolated_worker(worker_path):
    _require(worker_path.resolve() == worker_path and not any(c in str(worker_path) for c in ",\r\n"),
             "worker mount source must be canonical")
    user = f"{os.geteuid()}:{os.getegid()}"
    identity = _docker(
        "create", "--name", f"tremor-l5-shard-{uuid.uuid4().hex}", "--interactive",
        "--pull=never", "--runtime", "runc", "--network", "none", "--read-only", "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges", "--user", user, "--memory", "128m", "--memory-swap", "128m",
        "--cpus", "1", "--pids-limit", "24", "--shm-size", "16m", "--log-driver", "none",
        "--mount", f"type=bind,source={worker_path},target={MOUNT},readonly",
        "--entrypoint", "timeout", guard.IMAGE, "--kill-after=1s", "8s", "python", "-I", "-B", MOUNT,
    ).removesuffix("\n")
    _require(guard.CONTAINER_ID.fullmatch(identity), "expected a full disposable CPU container ID")
    finished = False
    try:
        fmt = "{{json .Id}}\n{{json .Image}}\n{{json .Mounts}}\n{{json .HostConfig}}\n{{json .Config.User}}"
        observed = _docker("inspect", "--type", "container", "--format", fmt, identity)
        actual_id, image, mounts, limits, actual_user = map(json.loads, observed.splitlines())
        _require(actual_id == identity and image == guard.IMAGE and actual_user == user
                 and len(mounts) == 1 and mounts[0]["Source"] == str(worker_path)
                 and mounts[0]["Destination"] == MOUNT and mounts[0]["Type"] == "bind"
                 and mounts[0]["RW"] is False and limits["NetworkMode"] == "none"
                 and limits["Runtime"] == "runc" and limits["ReadonlyRootfs"] is True
                 and limits["Privileged"] is False and not limits["DeviceRequests"] and not limits["Devices"]
                 and limits["CapDrop"] == ["ALL"] and "no-new-privileges" in limits["SecurityOpt"]
                 and limits["Memory"] == limits["MemorySwap"] == 128 * 1024**2
                 and limits["NanoCpus"] == 10**9 and limits["PidsLimit"] == 24
                 and limits["ShmSize"] == 16 * 1024**2 and limits["LogConfig"]["Type"] == "none"
                 and limits["AutoRemove"] is False and limits["RestartPolicy"]["Name"] in ("", "no"),
                 "L5 CPU worker boundary differs from approved isolation")
        yield identity, {"image": image, "network": "none", "mounts": {MOUNT: "ro"},
                         "memory_bytes": limits["Memory"], "cpu_limit": 1, "pids_limit": limits["PidsLimit"]}
        finished = True
    finally:
        flags = [] if finished else ["--force"]
        removed = _docker("rm", *flags, identity)
        _require(removed.removesuffix("\n") == identity, "Docker did not remove the exact L5 fixture ID")
        _require(not _docker("ps", "-aq", "--no-trunc", "--filter", f"id={identity}"),
                 "L5 fixture container still appears after removal")


def _receive(stream, deadline):
    buffer = bytearray()
    with selectors.DefaultSelector() as selector:
        selector.register(stream, selectors.EVENT_READ)
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not selector.select(remaining):
                raise TimeoutError("L5 CPU worker transcript timed out")
            chunk = os.read(stream.fileno(), LIMIT + 1)
            if not chunk:
                _require(not buffer, "L5 worker left a partial transcript record")
                return
            buffer.extend(chunk)
            while b"\n" in buffer:
                raw, _, tail = buffer.partition(b"\n")
                _require(len(raw) <= LIMIT, "L5 worker exceeded transcript record limit")
                buffer[:] = tail
                yield json.loads(raw)
            _require(len(buffer) <= LIMIT, "L5 worker exceeded transcript record limit")


def _send(stream, value):
    data = json.dumps(value, separators=(",", ":"), sort_keys=True).encode() + b"\n"
    _require(len(data) <= LIMIT, "L5 host exceeded transcript record limit")
    _require(stream.write(data) == len(data), "incomplete L5 host transcript write")
    stream.flush()


def _sessions(inventory, worker, condition):
    foreign = next(candidate for candidate in inventory.workers if candidate != worker)
    return [
        {"condition": condition, "phase": phase, "own_item": inventory.item_ids[worker, phase],
         "foreign_item": inventory.item_ids[foreign, phase]}
        for phase in broker.PHASES
    ]


def _exercise(inventory, worker, sessions, child):
    _send(child.stdin, {"sessions": sessions})
    messages = _receive(child.stdout, time.monotonic() + 9)
    receipts = []
    for session in sessions:
        condition, phase = session["condition"], session["phase"]
        own, foreign = session["own_item"], session["foreign_item"]
        requests = {
            "own": {"item": own}, "foreign": {"item": foreign}, "unknown": {"item": "__unknown__"},
            "bulk": {}, "forged": {"item": foreign, "worker": "__forged__"},
        }
        expected_guide = condition.startswith("environment:") and (
            condition == "environment:clean" or phase == "pre" or inventory.target != worker
        )
        observations = {}
        for name, request in requests.items():
            expected_request = {"condition": condition, "phase": phase, "read": request}
            _require(next(messages, None) == expected_request, "L5 worker request departed from planned transcript")
            reply = broker.dispatch(inventory, worker, condition, phase, request)
            expected_items = [{"item": own, "canary": inventory.canaries[worker, phase]}] if (
                name == "own" and expected_guide
            ) else []
            _require(reply == {"items": expected_items}, "L5 response differs from scoped delivery")
            value = reply["items"][0]["canary"] if reply["items"] else None
            _send(child.stdin, {"value": value})
            observations[name] = hashlib.sha256(value.encode()).hexdigest() if value is not None else None
        receipts.append({"condition": condition, "phase": phase, "observations": observations})
    worker_receipt = {"sessions": receipts, "worker_mount_readonly": True}
    _require(next(messages, None) == {"receipt": worker_receipt}, "L5 worker did not witness the scoped transcript")
    child.stdin.close()
    _require(next(messages, None) is None and child.wait(timeout=2) == 0,
             "L5 isolated worker did not finish normally")
    return worker_receipt


def run(output):
    root = Path(output).absolute()
    _require(os.geteuid() != 0 and root.resolve() == root,
             "L5 shard fixture requires an unprivileged caller and canonical output")
    root.mkdir(mode=0o700)
    worker_path = root / "worker.py"
    worker_pin = _write(worker_path, WORKER.read_bytes())
    rows = []
    for size in (4, 8):
        for condition in broker.CONDITIONS:
            inventory = broker.fixture(size)
            for worker in inventory.workers:
                sessions = _sessions(inventory, worker, condition)
                _require(guard.available_kib() > guard.FLOOR_KIB, "Spark memory floor blocks CPU shard replay")
                with _isolated_worker(worker_path) as (identity, isolation):
                    command = [*guard.DOCKER, "start", "--attach", "--interactive", identity]
                    with subprocess.Popen(
                        command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0,
                    ) as child:
                        try:
                            receipt = _exercise(inventory, worker, sessions, child)
                        finally:
                            guard._reap_attachment(child)
                rows.append({"team_size": size, "condition": condition, "worker": worker, "container_id": identity,
                             "removed": True, "isolation": isolation, "worker_receipt": receipt})
    _require(len({row["container_id"] for row in rows}) == len(rows), "duplicate L5 fixture container ID")
    report = {"evidence": "scripted_cpu_environment_shards", "scientific_result": False, "gpu_jobs": 0,
              "worker_sha256": worker_pin, "rows": rows}
    _write(root / "report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.output), sort_keys=True))


if __name__ == "__main__":
    main()
