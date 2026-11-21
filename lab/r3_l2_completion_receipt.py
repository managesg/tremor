"""Cross-check the scripted R3-L2 completion summary and host terminal."""

import argparse
import json
from pathlib import Path

from lab import adapter_lineage, spark_calibration_guard


def verify(bundle, *, completion_sha256, terminal_sha256):
    """Cross-check two CPU receipts. Replay and plan custody are separate."""
    root = Path(bundle).resolve(strict=True)
    completion_path = adapter_lineage._path(root, {"path": "completed.report.json"})
    terminal_path = adapter_lineage._path(root, {"path": "completed/guard-terminal.json"})
    completion = adapter_lineage._json(completion_path, completion_sha256)
    terminal = adapter_lineage._json(terminal_path, terminal_sha256)
    for receipt in (completion, terminal):
        if (
            receipt.get("evidence") != "scripted_cpu_guard_parent_tape"
            or receipt.get("stop") != "completed"
            or type(receipt.get("gpu_jobs")) is not int
            or receipt["gpu_jobs"] != 0
            or receipt.get("isolated_cpu") is not True
            or receipt.get("container_removed") is not True
            or receipt.get("child_reaped") is not True
            or type(receipt.get("child_returncode")) is not int
            or receipt["child_returncode"] != 0
            or "watchdog_stop_sha256" not in receipt
            or receipt["watchdog_stop_sha256"] is not None
            or "injected_limit" not in receipt
            or receipt["injected_limit"] is not None
        ):
            raise ValueError("expected normal, reaped CPU completion without a watchdog stop")

        identity = adapter_lineage._digest(receipt.get("container_id"), 64)
        isolation = receipt.get("isolation")
        if (
            not isinstance(isolation, dict)
            or isolation.get("container_id") != identity
            or isolation.get("image") != spark_calibration_guard.IMAGE
            or isolation.get("network") != "none"
            or isolation.get("capabilities_dropped") != ["ALL"]
            or type(isolation.get("cpu_limit")) is not int
            or isolation["cpu_limit"] != 1
            or isolation.get("memory_bytes") != 128 * 1024 * 1024
            or isolation.get("mounts") != {
                "/export": "rw", "/fixture/lab": "ro", "/fixture/src": "ro", "/plan.json": "ro",
            }
        ):
            raise ValueError("completion does not bind the expected container and isolation envelope")

    if completion != terminal:
        raise ValueError("completion summary differs from the host terminal")
    artifacts = terminal.get("artifacts")
    if not isinstance(artifacts, dict):
        raise ValueError("completed CPU terminal must contain artifact pins")
    return {
        "evidence": "scripted_cpu_completion_receipts",
        "authorizes_execution": False,
        "container_id": terminal["container_id"],
        "manifest_sha256": adapter_lineage._digest(artifacts.get("manifest_sha256"), 64),
        "completion_sha256": completion_sha256,
        "terminal_sha256": terminal_sha256,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--completion-sha256", required=True)
    parser.add_argument("--terminal-sha256", required=True)
    args = parser.parse_args()
    try:
        receipt = verify(args.bundle, completion_sha256=args.completion_sha256, terminal_sha256=args.terminal_sha256)
    except (OSError, ValueError) as error:
        parser.exit(2, f"{error}\n")
    print(json.dumps(receipt, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
