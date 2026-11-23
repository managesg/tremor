"""Guard one independently admitted local SmolLM3 smoke. No ledger writes."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import pwd
import signal
import stat
import subprocess
import time
import uuid

from lab import smollm3_smoke_admission as admission
from lab import smollm3_smoke_container as container
from lab import smollm3_smoke_preflight as preflight
from lab import spark_calibration_guard as spark


def _sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_record(stream, record):
    line = json.dumps(record, sort_keys=True, allow_nan=False) + "\n"
    stream.write(line)
    stream.flush()
    os.fsync(stream.fileno())
    return hashlib.sha256(line.encode("ascii")).hexdigest()


def _claim(identifier, admission_sha256, attempt):
    directory = Path(pwd.getpwuid(os.geteuid()).pw_dir) / ".tremor-smollm3-claims"
    directory.mkdir(mode=0o700, exist_ok=True)
    info = directory.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077:
        raise ValueError("smoke claims require the private owner directory")
    _sync_directory(directory.parent)
    with spark._private_file(directory / f"{identifier}.json", "x") as marker:
        _write_record(marker, {"admission_sha256": admission_sha256, "attempt": attempt})
    _sync_directory(directory)


def _headroom():
    if spark.available_kib() < spark.ADMISSION_KIB:
        raise RuntimeError("available memory is below the reviewed Spark headroom")


def _execute(receipt, admission_sha256, inputs, snapshot, worker, host_log, worker_log, inspect_log,
             *, recheck_inputs):
    identifier = inputs["admission_id"]
    attempt = f"tremor-r2-{uuid.uuid4().hex}"
    plan_sha = inputs["worker_plan_sha256"]
    argv = container.create_command(attempt, snapshot, worker, plan_sha)
    common = {"admission_id": identifier, "container": attempt}
    identity = child = started = None
    attachment = "not_started"
    owned = removed = False
    sequence = 0

    def emit(event, **fields):
        nonlocal sequence
        record = {**common, **fields}
        if event != "start":
            record["container_id"] = identity
        _write_record(host_log, {"version": 2, "sequence": sequence, "event": event, "record": record})
        sequence += 1

    _claim(identifier, admission_sha256, attempt)
    emit("start", worker_log_limit=spark.WORKER_LOG_LIMIT)
    spark._append_attempt(spark.ADMISSION_JOURNAL, "pending", identifier, attempt)
    try:
        created = subprocess.run(argv, check=True, stdout=subprocess.PIPE, text=True, timeout=30)
        candidate = created.stdout.removesuffix("\n")
        if not spark.CONTAINER_ID.fullmatch(candidate):
            raise RuntimeError("Docker did not return one full container ID")
        identity = candidate
        inspect_sha256 = None
        try:
            inspected = subprocess.run(container.inspect_command(identity), check=True,
                                       stdout=subprocess.PIPE, text=True, timeout=10)
            view = json.loads(inspected.stdout)
            container.verify_created(view, identity=identity, attempt=attempt, snapshot=snapshot,
                                     worker=worker, plan_sha256=plan_sha)
            owned = True
            inspect_sha256 = _write_record(inspect_log, view)
        finally:
            emit("created", prestart_inspect_sha256=inspect_sha256)

        if recheck_inputs() != inputs:
            raise ValueError("pre-start inputs differ from preflight")
        current = admission.verify(receipt, admission_sha256=admission_sha256, now=datetime.now(timezone.utc))
        if current["admission_id"] != identifier:
            raise ValueError("pre-start admission differs from preflight")
        _headroom()
        attachment = "unconfirmed"
        started = time.monotonic()
        attach = ["/usr/bin/prlimit", f"--fsize={spark.WORKER_LOG_LIMIT}:{spark.WORKER_LOG_LIMIT}",
                  "--", *spark.DOCKER, "start", "--attach", identity]
        child = subprocess.Popen(attach, stdout=worker_log, stderr=subprocess.STDOUT, close_fds=True)

        def kill():
            subprocess.run([*spark.DOCKER, "kill", identity], check=True, timeout=10,
                           stdout=subprocess.DEVNULL)

        def record_stop(reason, minimum):
            emit("decision", watchdog_decision=reason, sample_kib=minimum, attachment_pid=child.pid)

        stop, minimum = spark.watch(child, kill, spark.available_kib, time.monotonic, time.sleep,
                                    deadline=started + current["outer_wall_seconds"], on_stop=record_stop)
        child.wait(timeout=10)
        attachment = "reaped"
        emit("outcome", stop=stop, min_memavailable_kib=minimum, attachment_pid=child.pid)
        if stop != "completed":
            raise RuntimeError(f"smoke did not complete: {stop}")
    finally:
        try:
            if owned:
                removal = subprocess.run([*spark.DOCKER, "rm", "--force", identity], capture_output=True,
                                         text=True, timeout=10)
                removed = removal.returncode == 0 and removal.stdout.removesuffix("\n") == identity
        finally:
            try:
                if child is not None and attachment != "reaped":
                    spark._reap_attachment(child)
                    attachment = "reaped"
            finally:
                output = None
                if attachment != "unconfirmed":
                    worker_log.flush()
                    os.fsync(worker_log.fileno())
                    size = os.fstat(worker_log.fileno()).st_size
                    worker_log.seek(0)
                    output = {"bytes": size, "sha256": hashlib.file_digest(worker_log, "sha256").hexdigest(),
                              "limit_reached": size >= spark.WORKER_LOG_LIMIT}
                clean = removed and attachment != "unconfirmed"
                emit("terminal", cleanup_confirmed=clean, container_cleanup_confirmed=removed,
                     attachment_status=attachment, attachment_pid=child.pid if child is not None else None,
                     attachment_returncode=child.returncode if attachment == "reaped" else None,
                     observed_wall_seconds=time.monotonic() - started if started is not None else 0,
                     worker_output=output)
                if clean:
                    spark._append_attempt(spark.ADMISSION_JOURNAL, "removed", identifier, attempt, identity)
    if not clean:
        raise RuntimeError("exact cleanup was not confirmed")


def launch(receipt, reservation, snapshot, worker, worker_manifest, output, *, admission_sha256, opening_balance):
    """Start only after verifying an external admission, reserve and reviewed mounts."""
    if opening_balance is None:
        raise ValueError("launch requires an independent opening balance")
    output = Path(output).absolute()
    if (output.parent.resolve(strict=True) != output.parent
            or any(output.is_relative_to(Path(path).resolve(strict=True)) for path in (snapshot, worker))):
        raise ValueError("capture must have a real parent outside the worker mounts")

    def recheck_inputs():
        return preflight.verify(receipt, reservation, snapshot, worker, worker_manifest,
                                admission_sha256=admission_sha256, now=datetime.now(timezone.utc),
                                opening_balance=opening_balance)

    with spark.host_lock():
        spark.ensure_no_unresolved_attempt(spark.ADMISSION_JOURNAL)
        spark.ensure_no_running_calibration(include_stopped=True)
        inputs = recheck_inputs()
        _headroom()
        admission.verify(receipt, admission_sha256=admission_sha256, now=datetime.now(timezone.utc))
        output.mkdir(mode=0o700)
        previous = signal.signal(signal.SIGTERM, spark.interrupt)
        try:
            with (spark._private_file(output / "guard.jsonl", "x") as host_log,
                  spark._private_file(output / "worker.log", "x+b") as worker_log,
                  spark._private_file(output / "prestart-inspect.json", "x") as inspect_log):
                _sync_directory(output)
                _sync_directory(output.parent)
                _execute(receipt, admission_sha256, inputs, snapshot, worker, host_log, worker_log,
                         inspect_log, recheck_inputs=recheck_inputs)
        finally:
            signal.signal(signal.SIGTERM, previous)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("receipt", "reservation", "snapshot", "worker", "worker_manifest", "output"):
        parser.add_argument(field, type=Path)
    parser.add_argument("--admission-sha256", required=True)
    parser.add_argument("--opening-balance", nargs=4, required=True,
                        metavar=("LEDGER", "R2_GUARD", "PLACEMENT", "PLACEMENT_SHA256"))
    parser.add_argument("--approved-launch", action="store_true")
    args = vars(parser.parse_args())
    if not args.pop("approved_launch"):
        parser.error("launch requires the exact reviewed admission and --approved-launch")
    launch(**args)


if __name__ == "__main__":
    main()
