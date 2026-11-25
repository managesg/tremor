"""Run the Spark watchdog and parent-owned relay capture against a scripted CPU child."""

import argparse
from contextlib import contextmanager, nullcontext
from dataclasses import asdict
import errno
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid

from lab import l2_host_response, r3_l2_relay_generation as fixture, r3_l2_relay_partial as partial
from lab import r3_l2_relay_replay as replay, spark_calibration_guard as guard
from lab.r3_cpu_guard_replay import _require, _sha, _write
from lab.spark_decision import Generation

SCENARIOS = ("completed", "memory_floor", "wall_limit")
CAPS = {"input": 20, "output": 16}
PIPE_LIMIT = 4096
CODE_ROOT = Path(__file__).resolve().parent.parent


class _HoldRequest(BaseException):
    """Leave only the parent's durable request receipt before the guarded stop."""


def _worker(board, plan_pin, plan=None, *, mode="planted"):
    if plan is not None:
        frozen = partial._manifest(plan, plan_pin)
        _require(frozen["caps"] == CAPS, "isolated worker plan differs")
        mode = frozen["mode"]
        try:
            fd = os.open(plan, os.O_WRONLY)
        except OSError as error:
            _require(error.errno in (errno.EROFS, errno.EACCES, errno.EPERM), "unexpected plan access error")
        else:
            os.close(fd)
            raise ValueError("isolated worker can open the plan for writes")
        _require(os.geteuid() != 0 and not Path("/var/run/docker.sock").exists(),
                 "worker must be unprivileged and have no Docker socket")

    def generate(prompt, **caps):
        print(json.dumps({"prompt": prompt, "caps": caps}), flush=True)
        reply = sys.stdin.buffer.readline(PIPE_LIMIT)
        if not reply.endswith(b"\n"):
            raise ValueError("missing or incomplete scripted parent response")
        return Generation(**json.loads(reply))

    report = fixture.run(board, generate=generate, render=json.dumps, max_input_tokens=CAPS["input"],
                         max_output_tokens=CAPS["output"], plan_sha256=plan_pin,
                         clean=mode == "clean", trigger_only=mode == "trigger_only")
    return 0 if report["status"] == fixture.COMPLETED_STATUS[mode] else 1


def _mounts(root, plan):
    return {
        "/fixture/lab": (CODE_ROOT / "lab", False),
        "/fixture/src": (CODE_ROOT / "src", False),
        "/plan.json": (plan, False),
        "/export": (root / "export", True),
    }


def _isolated_command(root, board, plan, plan_pin, *, exact_stop=False):
    _require(board == root / "export" / "board.jsonl", "unexpected isolated board path")
    mounts = []
    for dest, (source, writable) in _mounts(root, plan).items():
        _require(source.resolve() == source and not any(char in str(source) for char in ',\r\n'),
                 "isolated mount sources must use canonical, unambiguous paths")
        option = f"type=bind,source={source},target={dest}"
        mounts.extend(["--mount", option if writable else option + ",readonly"])
    return [
        *guard.DOCKER, "create", "--interactive", "--pull=never", "--runtime", "runc",
        "--network", "none", "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--user", f"{os.geteuid()}:{os.getegid()}", "--memory", "128m", "--memory-swap", "128m",
        "--cpus", "1", "--pids-limit", "24", "--shm-size", "16m", "--log-driver", "none", *mounts,
        "--workdir", "/fixture", "-e", "PYTHONPATH=/fixture:/fixture/src", "--entrypoint", "timeout", guard.IMAGE,
        "--kill-after=1s", "12s" if exact_stop else "7s",
        "python", "-B", "-m", "lab.r3_relay_cpu_guard", "/export/board.jsonl",
        "completed", "--worker-plan-sha256", plan_pin, "--worker-plan", "/plan.json",
    ]


def _kill_isolated(identity):
    _require(guard.CONTAINER_ID.fullmatch(identity), "CPU stop requires a full container ID")
    killed = subprocess.run([*guard.DOCKER, "kill", "--signal=KILL", identity],
                            check=True, capture_output=True, text=True, timeout=5)
    _require(killed.stdout.removesuffix("\n") == identity, "wrong CPU container stop acknowledgement")


def _isolated_state(identity):
    _require(guard.CONTAINER_ID.fullmatch(identity), "CPU state check requires a full container ID")
    fields = "{{json .Id}}\n{{json .State}}"
    observed = subprocess.run([*guard.DOCKER, "inspect", "--type", "container", "--format", fields, identity],
                              check=True, capture_output=True, text=True, timeout=5)
    container, state = (json.loads(line) for line in observed.stdout.splitlines())
    _require(container == identity and type(state) is dict, "CPU container state identity differs")
    return state


def _isolated_terminal(identity, expected_exit):
    state = _isolated_state(identity)
    _require(state.get("Status") == "exited" and state.get("Restarting") is False
             and state.get("Running") is False and state.get("OOMKilled") is False
             and type(state.get("ExitCode")) is int and state["ExitCode"] == expected_exit
             and state.get("Error") == "", "CPU container terminal state differs from the watchdog action")
    return {"container_id": identity, "status": state["Status"], "exit_code": state["ExitCode"],
            "oom_killed": state["OOMKilled"]}


@contextmanager
def _isolated_launch(root, board, plan, plan_pin, *, exact_stop=False):
    args = _isolated_command(root, board, plan, plan_pin, exact_stop=exact_stop)
    create_options = len(guard.DOCKER) + 1
    args[create_options:create_options] = ["--name", f"tremor-relay-cpu-{uuid.uuid4().hex}"]
    identity = subprocess.run(args, check=True, capture_output=True, text=True, timeout=8).stdout.removesuffix("\n")
    _require(guard.CONTAINER_ID.fullmatch(identity), "CPU Docker create did not return a full ID")
    terminal_verified = False
    try:
        fmt = "{{json .Id}}\n{{json .Image}}\n{{json .Mounts}}\n{{json .HostConfig}}\n{{json .Config.User}}"
        observed = subprocess.run([*guard.DOCKER, "inspect", "--type", "container", "--format", fmt, identity],
                                  check=True, capture_output=True, text=True, timeout=5)
        actual_id, image, mount_rows, settings, user = (json.loads(row) for row in observed.stdout.splitlines())
        mounts = {entry["Destination"]: (Path(entry["Source"]), entry["RW"]) for entry in mount_rows}
        _require(actual_id == identity and image == guard.IMAGE and len(mounts) == len(mount_rows)
                 and mounts == _mounts(root, plan) and all(row["Type"] == "bind" for row in mount_rows)
                 and settings["NetworkMode"] == "none" and settings["Runtime"] == "runc" and settings["ReadonlyRootfs"]
                 and settings["Privileged"] is False and not settings["DeviceRequests"] and not settings["Devices"]
                 and settings["CapDrop"] == ["ALL"] and "no-new-privileges" in settings["SecurityOpt"]
                 and settings["Memory"] == settings["MemorySwap"] == 128 * 1024 * 1024
                 and settings["NanoCpus"] == 10**9 and settings["PidsLimit"] == 24
                 and settings["ShmSize"] == 16 * 1024 * 1024 and settings["AutoRemove"] is False
                 and settings["RestartPolicy"]["Name"] in ("", "no")
                 and user == f"{os.geteuid()}:{os.getegid()}" and settings["LogConfig"]["Type"] == "none",
                 "CPU Docker isolation differs from the approved fixture")
        descriptor = {"container_id": identity, "image": image, "network": settings["NetworkMode"], "user": user,
                      "mounts": {dest: "rw" if rw else "ro" for dest, (_, rw) in mounts.items()},
                      "memory_bytes": settings["Memory"], "cpu_limit": 1, "capabilities_dropped": settings["CapDrop"]}
        if exact_stop:
            descriptor.update(pids_limit=settings["PidsLimit"], shm_bytes=settings["ShmSize"],
                              memory_swap_bytes=settings["MemorySwap"])
        yield [*guard.DOCKER, "start", "--attach", "--interactive", identity], descriptor
        terminal_verified = exact_stop
    finally:
        remove_flags = [] if terminal_verified else ["--force"]
        removed = subprocess.run([*guard.DOCKER, "rm", *remove_flags, identity], check=True, capture_output=True,
                                 text=True, timeout=5)
        _require(removed.stdout.removesuffix("\n") == identity, "wrong CPU container removal acknowledgement")
        remaining = subprocess.run([*guard.DOCKER, "ps", "-aq", "--no-trunc", "--filter", f"id={identity}"],
                                   check=True, capture_output=True, text=True, timeout=5)
        _require(not remaining.stdout, "CPU fixture container still exists")
        if terminal_verified:
            _write(root / "container-cleanup.json", {
                "container_id": identity, "image": image, "manifest_sha256": plan_pin,
                "removal_acknowledged": True, "absent_after_removal": True, "forced": False,
            })


def run(root, scenario, *, isolated=False, exact_container_stops=False, mode="planted"):
    """Start and reap one guarded child, then audit its export with a parent-owned tape."""
    _require(scenario in SCENARIOS, "unknown relay guard scenario")
    _require(mode in fixture.COMPLETED_STATUS, "unknown relay fixture mode")
    _require(not exact_container_stops or (isolated and scenario != "completed"),
             "exact container stops require isolated fault injection")
    root = Path(root).absolute()
    if isolated:
        _require(scenario == "completed" or exact_container_stops,
                 "isolated CPU fault injection requires explicit exact-container opt-in")
        _require(root.resolve() == root and all(not root.is_relative_to(CODE_ROOT / part) for part in ("lab", "src")),
                 "isolated export must be outside mounted code and use canonical paths")
        _require(os.geteuid() != 0, "isolated CPU fixture requires an unprivileged caller")
    root.mkdir(mode=0o700)
    if isolated:
        (root / "export").mkdir(mode=0o700)
    board = (root / "export" if isolated else root) / "board.jsonl"
    host = root / "host.jsonl"
    plan = root / "plan.json"
    stop_receipt = root / "guard-stop.json"
    container_exit_receipt = root / "container-exit.json"
    manifest_id = f"cpu-watchdog-{scenario}" if mode == "planted" else f"cpu-watchdog-{scenario}-{mode}"
    plan_pin = _write(plan, {"manifest_id": manifest_id, "mode": mode,
                             "renderer": "json-dumps-v1", "caps": CAPS, "schedule": fixture.SCHEDULE})
    start = time.monotonic()
    observed_attempt = 0
    stop_ready = False
    watchdog_sent_kill = False
    container_exit_pin = None
    buffer = b""

    def scripted(prompt, **_caps):
        if scenario == "memory_floor" and observed_attempt == 1:
            raise _HoldRequest
        request = json.loads(prompt)
        _require(request["opportunity"] == observed_attempt, "unexpected scripted request order")
        payload = {"kind": "abstain"}
        if observed_attempt in (0, 1):
            payload = {"kind": "relay", "parent_id": request["source_id"], "text": "Marker: blue"}
        return Generation(json.dumps(payload), 12, 8, 100, False)

    def clock():
        elapsed = time.monotonic() - start
        if elapsed >= 8:
            raise TimeoutError("relay CPU child exceeded its real observation window")
        return guard.WALL_SECONDS + elapsed if stop_ready and scenario == "wall_limit" else elapsed

    def memory():
        return guard.FLOOR_KIB if stop_ready and scenario == "memory_floor" else guard.available_kib()

    local = [sys.executable, "-B", "-m", "lab.r3_relay_cpu_guard", str(board), scenario,
             "--worker-plan-sha256", plan_pin, "--mode", mode]
    launch = (_isolated_launch(root, board, plan, plan_pin, exact_stop=exact_container_stops)
              if isolated else nullcontext((local, None)))
    with (root / "worker.stderr").open("xb") as stderr, l2_host_response.capture(host, scripted) as capture, launch as transport:
        command, isolation = transport
        with subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=stderr) as child:
            os.set_blocking(child.stdout.fileno(), False)

            def stop_record(reason, sample):
                record = {"pid": child.pid, "stop": reason, "sample": sample}
                if exact_container_stops:
                    record.update(container_id=isolation["container_id"], image=isolation["image"],
                                  manifest_sha256=plan_pin, scripted_trigger_reached=stop_ready,
                                  attempts_observed=observed_attempt)
                return record

            def record_stop(reason, sample):
                _write(stop_receipt, stop_record(reason, sample))
                if exact_container_stops:
                    directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
                    try:
                        os.fsync(directory)
                    finally:
                        os.close(directory)

            def stop_child():
                nonlocal watchdog_sent_kill
                if exact_container_stops:
                    _require(stop_receipt.is_file(), "watchdog decision must precede exact container stop")
                    identity = isolation["container_id"]
                    state = _isolated_state(identity)
                    _require(state.get("Status") == "running" and state.get("Running") is True
                             and state.get("Restarting") is False,
                             "CPU container stopped before the watchdog action")
                    _kill_isolated(identity)
                else:
                    child.kill()
                watchdog_sent_kill = True

            def observe(pause):
                nonlocal buffer, observed_attempt, stop_ready
                try:
                    buffer += os.read(child.stdout.fileno(), PIPE_LIMIT + 1)
                except BlockingIOError:
                    pass
                _require(len(buffer) <= PIPE_LIMIT, "CPU child exceeded transport record limit")
                if b"\n" in buffer:
                    raw, buffer = buffer.split(b"\n", 1)
                    message = json.loads(raw)
                    limits = {"max_input_tokens": CAPS["input"], "max_output_tokens": CAPS["output"]}
                    _require(type(message) is dict and message.keys() == {"prompt", "caps"}
                             and isinstance(message["prompt"], str) and message["caps"] == limits
                             and observed_attempt < sum(map(len, fixture.SCHEDULE)) and not stop_ready,
                             "invalid CPU child request")
                    try:
                        result = capture(message["prompt"], **limits)
                    except _HoldRequest:
                        stop_ready = True
                    else:
                        if scenario == "wall_limit" and observed_attempt == 1:
                            stop_ready = True
                        else:
                            child.stdin.write(json.dumps(asdict(result)).encode() + b"\n")
                            child.stdin.flush()
                    observed_attempt += 1
                time.sleep(min(0.02, pause))

            try:
                stop, minimum = guard.watch(
                    child, stop_child, memory, clock, observe, deadline=guard.WALL_SECONDS,
                    on_stop=record_stop,
                )
            finally:
                if exact_container_stops:
                    guard._reap_attachment(child)
                else:
                    if child.poll() is None:
                        child.kill()
                    child.wait(timeout=2)
            if exact_container_stops:
                _require(watchdog_sent_kill and stop_ready and stop == scenario,
                         "exact container stop did not reach the intended watchdog decision")
                terminal = _isolated_terminal(isolation["container_id"], 128 + signal.SIGKILL)
                container_exit_pin = _write(container_exit_receipt, {
                    **terminal, "attach_returncode": child.returncode,
                    "image": isolation["image"], "manifest_sha256": plan_pin,
                })
    try:
        os.waitpid(child.pid, os.WNOHANG)
    except ChildProcessError:
        reaped = True
    else:
        raise ValueError("relay CPU child was not reaped")
    _require(stop == scenario and (exact_container_stops
             or child.returncode == (0 if scenario == "completed" else -signal.SIGKILL)),
             "unexpected relay guard stop or child exit")
    _require(stop_receipt.is_file() == watchdog_sent_kill == (scenario != "completed"),
             "relay guard stop receipt differs from terminal")
    wall_seconds = time.monotonic() - start
    stop_pin = None
    if watchdog_sent_kill:
        raw = stop_receipt.read_bytes()
        _require(json.loads(raw) == stop_record(stop, minimum),
                 "relay watchdog receipt differs from reaped child")
        stop_pin = _sha(raw)

    pins = {"board_sha256": _sha(replay._artifact_bytes(board)),
            "generation_sha256": _sha(replay._artifact_bytes(board.with_suffix(".relay-generation.jsonl"))),
            "host_response_sha256": _sha(replay._artifact_bytes(host))}
    if isolated:
        _require({item.name for item in board.parent.iterdir()} == {"board.jsonl", "board.relay-generation.jsonl"}
                 and _sha(plan.read_bytes()) == plan_pin, "isolated export inventory or plan changed")
    if scenario == "completed":
        export = replay.verify(board, render=json.dumps, host_response_path=host, **pins)
        _require(export["status"] == fixture.COMPLETED_STATUS[mode],
                 "guarded fixture did not close the relay window")
        if export["readout"] is not None:
            export["readout"].pop("trace")
    else:
        export = partial.verify(board, manifest_path=plan, manifest_sha256=plan_pin, host_response_path=host, **pins)
    report = {"evidence": "scripted_cpu_guard_parent_tape", "stop": stop, "pid": child.pid,
              "child_returncode": child.returncode, "child_reaped": reaped, "minimum_sample_kib": minimum,
              "injected_limit": stop if watchdog_sent_kill else None, "observed_cpu_wall_seconds": wall_seconds,
              "watchdog_stop_sha256": stop_pin,
              "gpu_jobs": 0, "artifacts": {**pins, "manifest_sha256": plan_pin}, "export": export}
    if isolated:
        report.update(container_id=isolation["container_id"], container_removed=True, isolated_cpu=True,
                      isolation=isolation)
    if exact_container_stops:
        report["container_exit_sha256"] = container_exit_pin
        report["container_cleanup_sha256"] = _sha((root / "container-cleanup.json").read_bytes())
    _write(root / "guard-terminal.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("scenario", choices=SCENARIOS)
    parser.add_argument("--worker-plan-sha256", help=argparse.SUPPRESS)
    parser.add_argument("--worker-plan", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--mode", choices=fixture.COMPLETED_STATUS, default="planted")
    parser.add_argument("--isolated", action="store_true", help="use the pinned no-network CPU container")
    parser.add_argument("--exact-container-stops", action="store_true",
                        help="opt in to watchdog stops of the exact disposable CPU container")
    args = parser.parse_args()
    if args.worker_plan_sha256:
        return _worker(args.output, args.worker_plan_sha256, args.worker_plan, mode=args.mode)
    print(json.dumps(run(args.output, args.scenario, isolated=args.isolated,
                         exact_container_stops=args.exact_container_stops, mode=args.mode), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
