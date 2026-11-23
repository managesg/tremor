"""Verify technical smoke metrics from exact, independently pinned CUDA receipts."""

import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re

from lab import r3_resource_audit as guard
from lab import smollm3_smoke_admission as admission
from lab import smollm3_smoke_container as container
from lab import smollm3_smoke_worker as worker


EXPECTED = {
    "evidence": "local_public_prompt_smoke_worker",
    "plan_sha256": admission.WORKER_PLAN_SHA256,
    "manifest_sha256": admission.MODEL_MANIFEST_SHA256,
    "prompt_sha256": worker.PROMPT_SHA256,
    "input_ids_sha256": worker.INPUT_IDS_SHA256,
    "device": "cuda:0",
    "cuda_allocator_fraction": Decimal("0.2"),
    "input_tokens": worker.INPUT_TOKENS,
    "authorizes_execution": False,
    "scientific_acceptance": False,
}
METRICS = {
    "output_tokens", "cap_reached", "load_ns", "generation_ns",
    "peak_cuda_allocated_bytes", "peak_cuda_reserved_bytes",
}


def _invalid_constant(value):
    raise ValueError(f"nonfinite worker metric: {value}")


def _read_worker(raw):
    if not raw.endswith(b"\n"):
        raise ValueError("worker capture ends with an incomplete record")
    lines = [line for line in raw.splitlines() if line.lstrip().startswith(b"{")]
    if len(lines) != 1:
        raise ValueError("worker capture must contain exactly one JSON object record")
    return json.loads(lines[0], parse_float=Decimal, parse_constant=_invalid_constant,
                      object_pairs_hook=guard._unique_object)


def verify(host_capture, *, snapshot, worker_mount, host_capture_sha256, worker_log_sha256, admission_id):
    """Validate the successful exact CUDA worker evidence without settling usage."""
    if type(admission_id) is not str or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", admission_id):
        raise ValueError("expected the exact independently identified smoke admission ID")
    host = Path(host_capture)
    outcome, terminal, decision, _, created = guard._read_host_capture(
        host, host_capture_sha256, exact_container=True, admission_id=admission_id,
        include_created=True,
    )
    reason, _ = guard._guard_measurement(admission_id, outcome, terminal, decision, True)
    if reason != "completed":
        raise ValueError(f"cannot verify a successful CUDA worker: {reason}")

    inspect_pin = created.get("prestart_inspect_sha256")
    if not isinstance(inspect_pin, str) or not re.fullmatch(r"[0-9a-f]{64}", inspect_pin):
        raise ValueError("host capture lacks a valid pre-start container inspection pin")
    try:
        inspect_raw = guard._private_capture_bytes(host.with_name("prestart-inspect.json"), 16 * 1024)
    except FileNotFoundError as error:
        raise ValueError("missing pre-start container inspection") from error
    if hashlib.sha256(inspect_raw).hexdigest() != inspect_pin:
        raise ValueError("pre-start container inspection digest differs from the pinned host capture")
    view = json.loads(inspect_raw, object_pairs_hook=guard._unique_object)
    container.verify_created(
        view, identity=created["container_id"], attempt=created["container"],
        snapshot=snapshot, worker=worker_mount, plan_sha256=admission.WORKER_PLAN_SHA256,
    )

    export = terminal["worker_output"]
    raw = guard._private_capture_bytes(host.with_name("worker.log"), guard.WORKER_LOG_LIMIT)
    if (not export or export["bytes"] != len(raw)
            or hashlib.sha256(raw).hexdigest() != export["sha256"]
            or export["sha256"] != worker_log_sha256):
        raise ValueError("worker log does not match the terminal and independent pins")
    result = _read_worker(raw)
    if result.keys() != EXPECTED.keys() | METRICS or any(
        type(result[key]) is not type(value) or result[key] != value for key, value in EXPECTED.items()
    ):
        raise ValueError("worker record differs from the pinned CUDA smoke contract")
    output = result["output_tokens"]
    if (type(output) is not int or not 0 < output <= worker.MAX_OUTPUT_TOKENS
            or result["cap_reached"] is not (output == worker.MAX_OUTPUT_TOKENS)):
        raise ValueError("worker output token count or cap status is invalid")
    load, generation = result["load_ns"], result["generation_ns"]
    if (any(type(value) is not int or value <= 0 for value in (load, generation))
            or load + generation > guard._number(terminal["observed_wall_seconds"], "observed_wall_seconds") * 10**9):
        raise ValueError("worker timings are invalid or exceed the host wall interval")
    allocated, reserved = result["peak_cuda_allocated_bytes"], result["peak_cuda_reserved_bytes"]
    if type(allocated) is not int or type(reserved) is not int or not 0 < allocated <= reserved:
        raise ValueError("worker CUDA peaks are invalid")
    return {
        **result,
        "cuda_allocator_fraction": float(result["cuda_allocator_fraction"]),
        "evidence": "verified_smollm3_cuda_smoke_metrics",
        "admission_id": admission_id,
        "host_capture_sha256": host_capture_sha256,
        "prestart_inspect_sha256": inspect_pin,
        "worker_log_sha256": worker_log_sha256,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("host_capture", type=Path)
    parser.add_argument("snapshot", type=Path, help="reviewed snapshot mount source")
    parser.add_argument("worker_mount", type=Path, help="reviewed worker mount source")
    parser.add_argument("--host-capture-sha256", required=True)
    parser.add_argument("--worker-log-sha256", required=True)
    parser.add_argument("--admission-id", required=True)
    try:
        result = verify(**vars(parser.parse_args(argv)))
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
