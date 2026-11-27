"""Exercise the Spark watchdog against an isolated scripted L2 CPU child."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from lab import l2_generation_audit, r3_l2_batch, spark_calibration_guard as guard
from tremor.board import read_log

SCENARIOS = ("completed", "memory_floor", "wall_limit")


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _write(path, value):
    data = value if isinstance(value, bytes) else json.dumps(value, sort_keys=True).encode()
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return _sha(data)


def _fixture(inputs):
    inputs.mkdir()
    source = _write(inputs / "paper.txt", b"Paper ledger marker: green")
    references = _write(inputs / "references.json", {"references": {"case": {"path": "paper.txt", "sha256": source}}})
    truth = _write(inputs / "truth.json", {"markers": {"case": "green"}})
    return _write(inputs / "batch.json", {
        "purpose": "scripted_l2_warning", "conditions": ["warning", "neutral"], "seed": 17,
        "blocks": [{"block_id": "cpu-pair", "case_id": "case", "stratum": "fixture"}],
        "limits": {"max_input_tokens": 60, "max_output_tokens": 12, "accept_at_limit": False},
        "custody": {"manifest": "references.json", "manifest_sha256": references,
                    "truth_inventory": "truth.json", "truth_sha256": truth},
    })


def _worker(root, scenario, pin):
    attempts = 0

    def generate(prompt, **caps):
        nonlocal attempts
        attempts += 1
        if scenario != "completed" and attempts == 5:
            _write(root / "pending.json", {"generation_attempt": attempts})
            time.sleep(15)
            raise RuntimeError("the fixture watchdog did not stop its child")
        return r3_l2_batch._scripted_generate(prompt, **caps)

    inputs = root / "inputs"
    result = r3_l2_batch.run(inputs, inputs / "batch.json", root / "export", batch_sha256=pin, generate=generate)
    return 0 if result["status"] == "completed" else 1


def _recover(export, scenario, batch_pin):
    rows = [json.loads(line) for line in (export / "batch.jsonl").read_bytes().splitlines()]
    _require(rows[0]["event"] == "start" and rows[0]["batch_sha256"] == batch_pin, "batch receipt identity mismatch")
    expected = ["start", "arm_start", "arm_complete", "arm_start"]
    if scenario == "completed":
        expected.extend(("arm_complete", "finish"))
    _require([row["event"] for row in rows] == expected, "unexpected exported arm sequence")
    order = rows[0]["schedule"]["blocks"][0]["order"]
    receipts = []
    for index, condition in enumerate(order):
        board = export / f"arm-{index}.jsonl"
        generation = board.with_suffix(".generation.jsonl")
        trace = read_log(board)
        meter = l2_generation_audit.audit(
            board, generation, expected_board_head=trace[-1]["hash"],
            expected_journal_sha256=_sha(generation.read_bytes()), renderer=l2_generation_audit.render_scripted_prompt,
        )
        _require(meter["condition"] == condition, "exported arm is out of schedule order")
        anticipated = ("completed", 3, 0) if index == 0 or scenario == "completed" else ("incomplete", 1, 1)
        _require((meter["status"], meter["completed_generations"], meter["unknown_usage_attempts"]) == anticipated,
                 "partial export did not retain its completed and unknown attempts")
        if meter["status"] == "completed":
            completed = rows[2 + index * 2]
            _require(completed["condition"] == condition and completed["meter"] == meter,
                     "complete arm differed from its batch settlement")
        receipts.append(meter)
    completed_pairs = len(rows[-1]["scored_pairs"]) if scenario == "completed" else 0
    _require(completed_pairs == int(scenario == "completed"), "unexpected eligible paired result")
    return {"batch_sha256": _sha((export / "batch.jsonl").read_bytes()), "completed_pairs": completed_pairs,
            "arms": receipts}


def run(root, scenario):
    """Start and reap one CPU-only child and audit its quiescent export."""
    _require(scenario in SCENARIOS, "unknown CPU watchdog fixture")
    root = Path(root).absolute()
    root.mkdir()
    pin = _fixture(root / "inputs")
    pending = root / "pending.json"
    started_utc = datetime.now(timezone.utc)
    start = time.monotonic()
    stop_path = root / "guard-stop.json"

    def clock():
        elapsed = time.monotonic() - start
        if elapsed > 8:
            raise TimeoutError("CPU fixture exceeded its real observation window")
        return guard.WALL_SECONDS + elapsed if scenario == "wall_limit" and pending.is_file() else elapsed

    def free_kib():
        if scenario == "memory_floor" and pending.is_file():
            return guard.FLOOR_KIB
        return guard.available_kib()

    with (root / "worker.stderr").open("xb") as stderr:
        child = subprocess.Popen([sys.executable, "-B", "-m", "lab.r3_cpu_guard_replay", str(root), scenario,
                                  "--worker-batch-sha256", pin], stdin=subprocess.DEVNULL,
                                 stdout=subprocess.DEVNULL, stderr=stderr)
        try:
            stop, minimum = guard.watch(
                child, child.kill, free_kib, clock, lambda seconds: time.sleep(min(0.02, seconds)),
                deadline=guard.WALL_SECONDS,
                on_stop=lambda reason, sample: _write(stop_path, {"pid": child.pid, "stop": reason, "sample": sample}),
            )
        finally:
            if child.poll() is None:
                child.kill()
            child.wait(timeout=2)
    try:
        os.waitpid(child.pid, os.WNOHANG)
    except ChildProcessError:
        reaped = True
    else:
        raise ValueError("fixture child was not reaped")
    _require(stop == scenario and child.returncode == (0 if scenario == "completed" else -signal.SIGKILL),
             "unexpected guard stop or worker exit")
    _require(stop_path.is_file() == (scenario != "completed"), "missing or unexpected pre-termination receipt")
    stopped_utc = datetime.now(timezone.utc)
    duration = time.monotonic() - start
    report = {
        "evidence": "scripted_cpu_guard", "stop": stop, "pid": child.pid, "child_returncode": child.returncode,
        "child_reaped": reaped, "minimum_sample_kib": minimum, "injected_limit": None if stop == "completed" else stop,
        "started_utc": started_utc.isoformat(), "reaped_utc": stopped_utc.isoformat(), "observed_cpu_wall_seconds": duration,
        "gpu_jobs": 0, "export": _recover(root / "export", scenario, pin),
    }
    _write(root / "guard-terminal.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("scenario", choices=SCENARIOS)
    parser.add_argument("--worker-batch-sha256", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker_batch_sha256:
        return _worker(args.output, args.scenario, args.worker_batch_sha256)
    print(json.dumps(run(args.output, args.scenario), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
