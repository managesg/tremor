"""External watchdog and accounting for one explicitly approved R2 calibration container."""

import argparse
import fcntl
import hashlib
import json
import math
import os
import pwd
import re
import signal
import stat
import subprocess
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

FLOOR_KIB = 10 * 2**20
ADMISSION_KIB = (60 + 10) * 2**20
WALL_SECONDS = 300
IMAGE = "sha256:c74c8710f2bc017b5de956853c50d896af4aa49b751bb87cbebf69e5206befb7"
BATCH = "spark-r2-qwen35-4b-throughput"
LOCK_PATH = Path("/run/lock/tremor-r2-spark.lock")
ADMISSION_JOURNAL = Path(pwd.getpwuid(os.geteuid()).pw_dir) / ".tremor-spark-admission.jsonl"
DOCKER = ["docker", "--host", "unix:///var/run/docker.sock"]
WORKER_LOG_LIMIT = 4 * 1024 * 1024
CONTAINER_ID = re.compile(r"[0-9a-f]{64}")
ATTEMPT_LABEL = "ai.seabridge.tremor.attempt"


def verify_receipt(receipt, now):
    identifier = receipt.get("admission_id")
    if not isinstance(identifier, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", identifier):
        raise ValueError("invalid R2 admission ID")
    if receipt.get("batch") != BATCH or receipt.get("reserved_gpu_hours") != 0.1:
        raise ValueError("R2 receipt must reserve 0.1 GPU-hour for this calibration")
    balance = receipt.get("available_r2_r3_gpu_hours")
    if type(balance) not in (int, float) or not math.isfinite(balance) or not 0.1 <= balance <= 7.5:
        raise ValueError("R2/R3 ledger must show at least 0.1 GPU-hour available")
    for field in ("review_reference", "authorization_reference", "ledger_reference"):
        if not isinstance(receipt.get(field), str) or not receipt[field].strip():
            raise ValueError(f"missing {field} in R2 admission receipt")
    issued = datetime.fromisoformat(receipt.get("issued_utc", ""))
    if issued.utcoffset() != timedelta(0) or not timedelta(0) <= now - issued <= timedelta(hours=1):
        raise ValueError("R2 admission receipt must be issued in UTC in the last hour")
    return identifier


def claim_receipt(root, identifier, receipt, container):
    claims = root / "runs/spark-calibration/admissions"
    claims.mkdir(parents=True, exist_ok=True)
    with (claims / f"{identifier}.json").open("x", encoding="utf-8") as output:
        json.dump({"receipt": receipt, "container": container}, output, sort_keys=True)


def interrupt(signum, _frame):
    raise SystemExit(128 + signum)


@contextmanager
def host_lock(path=None):
    fd = os.open(path if path is not None else LOCK_PATH, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit("another Spark R2 calibration guard holds the host lock") from None
        yield
    finally:
        os.close(fd)


def ensure_no_running_calibration(*, include_stopped=False):
    found = subprocess.run(
        [*DOCKER, "ps", "-aq" if include_stopped else "-q", "--filter", "name=^/tremor-r2-"],
        check=True, capture_output=True, text=True, timeout=10,
    )
    if found.stdout.strip():
        if include_stopped:
            raise SystemExit("Spark admission refused: an earlier calibration container still exists")
        raise SystemExit("Spark R2 admission refused: an earlier calibration container is still active")


def _journal_file(path, flags):
    fd = os.open(path, flags | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                or info.st_nlink != 1 or info.st_mode & 0o077):
            raise ValueError("Spark admission journal must be a private host-owned regular file")
        return os.fdopen(fd, "rb" if flags == os.O_RDONLY else "ab")
    except BaseException:
        os.close(fd)
        raise


def _pending_attempt(path):
    try:
        journal = _journal_file(path, os.O_RDONLY)
    except FileNotFoundError:
        return None
    pending = None
    with journal:
        while line := journal.readline(1024):
            if not line.endswith(b"\n"):
                raise ValueError("incomplete Spark admission journal record")
            record = json.loads(line)
            if type(record) is not list or len(record) != 4:
                raise ValueError("invalid Spark admission journal record")
            event, admission, name, identity = record
            if not (isinstance(admission, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,80}", admission)
                    and isinstance(name, str) and re.fullmatch(r"tremor-r2-[0-9a-f]{32}", name)):
                raise ValueError("invalid Spark admission journal identity")
            if event == "pending" and pending is None and identity is None:
                pending = admission, name
            elif (event == "removed" and pending == (admission, name)
                  and isinstance(identity, str) and CONTAINER_ID.fullmatch(identity)):
                pending = None
            else:
                raise ValueError("invalid Spark admission journal transition")
    return pending


def ensure_no_unresolved_attempt(path):
    if pending := _pending_attempt(path):
        raise SystemExit(f"Spark admission refused: unresolved create or cleanup for {pending[0]} ({pending[1]})")


def diagnose_admission(path):
    pending = _pending_attempt(path)
    if pending is None:
        return {"journal": "no_pending_attempt"}
    admission, name = pending
    result = {"journal": "pending", "admission_id": admission, "attempt": name, "admission_blocked": True}
    listed = subprocess.run(
        [*DOCKER, "ps", "-aq", "--no-trunc", "--filter", f"label={ATTEMPT_LABEL}={name}"],
        check=True, capture_output=True, text=True, timeout=10,
    ).stdout.splitlines()
    if not listed:
        return {**result, "observation": "no_match_at_query_time"}
    if len(listed) != 1 or not CONTAINER_ID.fullmatch(listed[0]):
        raise ValueError("ambiguous or noncanonical Docker IDs for pending attempt")
    identity = listed[0]
    view = ('{"id":{{json .Id}},"name":{{json .Name}},"attempt":{{json (index .Config.Labels "' + ATTEMPT_LABEL
            + '")}},"state":{{json .State.Status}}}')
    inspected = json.loads(subprocess.run(
        [*DOCKER, "inspect", "--type", "container", "--format", view, identity],
        check=True, capture_output=True, text=True, timeout=10,
    ).stdout)
    if (type(inspected) is not dict or inspected.keys() != {"id", "name", "attempt", "state"}
            or inspected["id"] != identity or inspected["attempt"] != name
            or not isinstance(inspected["name"], str) or not inspected["name"].startswith("/")
            or not isinstance(inspected["state"], str) or not re.fullmatch(r"[a-z]+", inspected["state"])):
        raise ValueError("container inspection does not corroborate pending attempt")
    return {**result, "observation": "matching_object", "container_id": identity,
            "container_state": inspected["state"], "name_matches": inspected["name"] == f"/{name}"}


def _append_attempt(path, event, admission, name, identity=None):
    with _journal_file(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND) as journal:
        journal.write((json.dumps([event, admission, name, identity]) + "\n").encode("ascii"))
        journal.flush()
        os.fsync(journal.fileno())
    parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(parent)
    finally:
        os.close(parent)


def cleanup(name):
    removed = subprocess.run([*DOCKER, "rm", "--force", name], capture_output=True, timeout=10)
    if removed.returncode == 0:
        return True
    found = subprocess.run(
        [*DOCKER, "ps", "-aq", "--filter", f"name=^/{name}$"], check=True,
        capture_output=True, timeout=10,
    )
    if found.stdout.strip():
        removed.check_returncode()
    return False


def available_kib():
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1])
    raise RuntimeError("MemAvailable is unavailable")


def watch(child, kill, free_kib, monotonic, pause, *, deadline=None, on_stop=None):
    if deadline is None:
        deadline = monotonic() + WALL_SECONDS
    minimum = None
    while True:
        status = child.poll()
        sampled = free_kib()
        minimum = sampled if minimum is None else min(minimum, sampled)
        observed = monotonic()
        reason = None
        if sampled <= FLOOR_KIB:
            reason = "memory_floor"
        elif observed >= deadline:
            # A child first observed exited after the deadline has no timely completion witness.
            reason = "wall_limit"
        elif status is not None:
            return "completed" if status == 0 else "child_error", minimum
        if reason:
            if on_stop is not None:
                on_stop(reason, minimum)
            if status is None:
                kill()
            return reason, minimum
        pause(min(1, deadline - observed))


def _reap_attachment(child):
    try:
        child.wait(timeout=2)
    except subprocess.TimeoutExpired:
        # This handle is the guard's own attach client, not the container.
        child.kill()
        child.wait(timeout=2)


def _private_file(path, mode):
    return open(path, mode, opener=lambda name, flags: os.open(name, flags | os.O_NOFOLLOW, 0o600))


def _capture_calibration(identifier, receipt, directory, *, exact_container=False, admission_journal=None):
    directory = directory.absolute()
    model = (Path(__file__).resolve().parent.parent / "data/hf/Qwen3.5-4B").resolve()
    if directory.parent.resolve(strict=True) != directory.parent or directory.is_relative_to(model):
        raise ValueError("host capture must have a real parent outside the worker model mount")
    directory.mkdir(mode=0o700)
    with _private_file(directory / "guard.jsonl", "x") as host, _private_file(directory / "worker.log", "x+b") as worker:
        _run_calibration(identifier, receipt, host_log=host, worker_log=worker, exact_container=exact_container,
                         admission_journal=admission_journal)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approved-launch", action="store_true",
                        help="launch after the R2 batch reservation and independent review")
    parser.add_argument("--receipt", type=Path, help="JSON for the single-use R2 batch admission")
    parser.add_argument("--capture-directory", type=Path, help="fresh private directory for separate host and worker evidence")
    parser.add_argument("--require-container-identity", action="store_true",
                        help="require the full Docker ID before starting or removing the container")
    parser.add_argument("--diagnose-admission", action="store_true", help="report pending state using read-only Docker queries")
    args = parser.parse_args()
    if args.diagnose_admission:
        if args.approved_launch or args.receipt is not None or args.capture_directory is not None or args.require_container_identity:
            parser.error("--diagnose-admission cannot be combined with launch options")
        try:
            with host_lock():
                report = diagnose_admission(ADMISSION_JOURNAL)
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            parser.exit(1, f"Spark admission observation unavailable ({type(exc).__name__})\n")
        print(json.dumps(report, sort_keys=True))
        return
    if not args.approved_launch:
        parser.error("GPU launch requires --approved-launch after the R2 gate")
    if args.receipt is None:
        parser.error("GPU launch requires a structured R2 batch admission receipt")
    if args.require_container_identity and args.capture_directory is None:
        parser.error("exact container identity requires --capture-directory")
    try:
        receipt = json.loads(args.receipt.read_text())
        identifier = verify_receipt(receipt, datetime.now(timezone.utc))
    except (AttributeError, OSError, TypeError, ValueError) as exc:
        parser.error(str(exc))
    with host_lock():
        ensure_no_unresolved_attempt(ADMISSION_JOURNAL)
        if args.require_container_identity:
            ensure_no_running_calibration(include_stopped=True)
        else:
            ensure_no_running_calibration()
        if args.capture_directory is None:
            _run_calibration(identifier, receipt)
        else:
            _capture_calibration(identifier, receipt, args.capture_directory,
                                 exact_container=args.require_container_identity,
                                 admission_journal=ADMISSION_JOURNAL if args.require_container_identity else None)


def _run_calibration(identifier, receipt, *, host_log=None, worker_log=None, exact_container=False,
                     admission_journal=None):
    if available_kib() < ADMISSION_KIB:
        raise SystemExit("R2 admission requires at least 70 GiB MemAvailable")
    root = Path(__file__).resolve().parent.parent
    name = f"tremor-r2-{uuid.uuid4().hex}"
    if (host_log is None) != (worker_log is None):
        raise ValueError("host and worker evidence streams must be supplied together")
    if exact_container and host_log is None:
        raise ValueError("exact container identity requires host and worker capture")
    if admission_journal is not None and not exact_container:
        raise ValueError("admission journaling requires exact container capture")
    sequence = 0

    def emit(event, record):
        nonlocal sequence
        if exact_container and event != "start":
            record = {**record, "container_id": container_id}
        if host_log is None:
            print(json.dumps(record, sort_keys=True), flush=True)
        else:
            row = {"version": 2 if exact_container else 1, "sequence": sequence, "event": event, "record": record}
            host_log.write(json.dumps(row, sort_keys=True) + "\n")
            host_log.flush()
            os.fsync(host_log.fileno())
            sequence += 1

    if host_log is not None:
        emit("start", {"admission_id": identifier, "container": name, "worker_log_limit": WORKER_LOG_LIMIT})
    create_options = ["--log-driver=none"] if worker_log is not None else []
    if admission_journal is not None:
        create_options.extend(["--label", f"{ATTEMPT_LABEL}={name}"])
    command = [
        *DOCKER, "create", *create_options, "--pull=never", "--name", name, "--gpus", "all", "--memory", "60g",
        "--memory-swap", "60g",
        "--network", "none", "--mount", f"type=bind,source={root / 'data/hf/Qwen3.5-4B'},target=/model,readonly",
        "--mount", f"type=bind,source={root / 'lab/spark_calibration.py'},target=/worker.py,readonly",
        "-e", "HF_HUB_OFFLINE=1", "-e", "TRANSFORMERS_OFFLINE=1",
        "-e", "PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True",
        "--entrypoint", "timeout", IMAGE, "--kill-after=5s", "285s", "python", "-B", "/worker.py",
    ]
    started = None
    previous_signal = signal.signal(signal.SIGTERM, interrupt)
    create_attempted = False
    create_finished = False
    container_id = None
    child = None
    attachment_pid = None
    attachment_status = "not_started"
    try:
        claim_receipt(root, identifier, receipt, name)
        if admission_journal is not None:
            _append_attempt(admission_journal, "pending", identifier, name)
        create_attempted = True
        if exact_container:
            created = subprocess.run(command, check=True, stdout=subprocess.PIPE, text=True, timeout=30)
            candidate = created.stdout.removesuffix("\n")
            if not CONTAINER_ID.fullmatch(candidate):
                raise RuntimeError("Docker create did not return exactly one full container ID")
            container_id = candidate
            emit("created", {"admission_id": identifier, "container": name})
        else:
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, timeout=30)
        create_finished = True
        if available_kib() < ADMISSION_KIB:
            raise RuntimeError("host MemAvailable fell below the 70 GiB admission headroom")
        started = time.monotonic()
        attachment_status = "unconfirmed"
        target = container_id if exact_container else name
        attach = [*DOCKER, "start", "--attach", target]
        if worker_log is None:
            child = subprocess.Popen(attach)
        else:
            bounded = ["/usr/bin/prlimit", f"--fsize={WORKER_LOG_LIMIT}:{WORKER_LOG_LIMIT}", "--", *attach]
            child = subprocess.Popen(bounded, stdout=worker_log, stderr=subprocess.STDOUT, close_fds=True)
        attachment_pid = child.pid if type(child.pid) is int else None

        def record_stop(reason, minimum):
            emit("decision", {"watchdog_decision": reason, "sample_kib": minimum,
                              "container": name, "admission_id": identifier, "attachment_pid": attachment_pid})

        stop, minimum = watch(
            child,
            lambda: subprocess.run([*DOCKER, "kill", target], check=True, timeout=10,
                                   stdout=subprocess.DEVNULL),
            available_kib, time.monotonic, time.sleep,
            deadline=started + WALL_SECONDS,
            on_stop=record_stop,
        )
        child.wait(timeout=10)
        attachment_status = "reaped"
        emit("outcome", {"stop": stop, "min_memavailable_kib": minimum, "container": name,
                         "admission_id": identifier, "attachment_pid": attachment_pid})
        if stop != "completed":
            raise SystemExit(1)
    finally:
        cleaned_up = False
        try:
            if exact_container and container_id is not None:
                removed = subprocess.run([*DOCKER, "rm", "--force", container_id], capture_output=True,
                                         text=True, timeout=10)
                cleaned_up = removed.returncode == 0 and removed.stdout.removesuffix("\n") == container_id
            elif create_attempted and not exact_container:
                removed = cleanup(name)
                cleaned_up = removed or create_finished
        finally:
            try:
                if child is not None and attachment_status != "reaped":
                    _reap_attachment(child)
                    attachment_status = "reaped"
            finally:
                signal.signal(signal.SIGTERM, previous_signal)
                if create_attempted:
                    attach_rc = child.returncode if attachment_status == "reaped" else None
                    terminal = {
                        "observed_wall_seconds": (time.monotonic() - started if started is not None else 0),
                        "cleanup_confirmed": cleaned_up and attachment_status != "unconfirmed",
                        "container_cleanup_confirmed": cleaned_up,
                        "attachment_status": attachment_status,
                        "attachment_pid": attachment_pid,
                        "attachment_returncode": attach_rc if type(attach_rc) is int else None,
                        "container": name,
                        "admission_id": identifier,
                    }
                    if worker_log is not None:
                        terminal["worker_output"] = None
                        if attachment_status != "unconfirmed":
                            os.fsync(worker_log.fileno())
                            size = os.fstat(worker_log.fileno()).st_size
                            worker_log.seek(0)
                            terminal["worker_output"] = {
                                "bytes": size, "sha256": hashlib.file_digest(worker_log, "sha256").hexdigest(),
                                "limit_reached": size >= WORKER_LOG_LIMIT,
                            }
                    emit("terminal", terminal)
                    if admission_journal is not None and terminal["cleanup_confirmed"]:
                        _append_attempt(admission_journal, "removed", identifier, name, container_id)


if __name__ == "__main__":
    main()
