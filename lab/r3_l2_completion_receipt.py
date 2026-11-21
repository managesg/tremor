"""Cross-check the scripted R3-L2 completion summary and host terminal."""

import argparse
import json
from pathlib import Path

from lab import adapter_lineage, r3_l2_relay_partial, r3_l2_relay_replay, spark_calibration_guard


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


def verify_bound(bundle, *, completion_sha256, terminal_sha256, plan_sha256):
    """Bind both receipts to a separately pinned plan and replay the CPU result."""
    root = Path(bundle).resolve(strict=True)
    receipt = verify(root, completion_sha256=completion_sha256, terminal_sha256=terminal_sha256)
    if receipt["manifest_sha256"] != plan_sha256:
        raise ValueError("completion receipts do not bind the independently pinned plan")
    plan = r3_l2_relay_partial._manifest(root / "completed/plan.json", plan_sha256)
    terminal = adapter_lineage._json(root / "completed/guard-terminal.json", terminal_sha256)
    pins = terminal["artifacts"]
    board = adapter_lineage._path(root, {"path": "completed/export/board.jsonl"})
    tape_path = adapter_lineage._path(root, {"path": "completed/export/board.relay-generation.jsonl"})
    host_path = adapter_lineage._path(root, {"path": "completed/host.jsonl"})
    tape = r3_l2_relay_replay._pinned(tape_path, pins.get("generation_sha256"))
    start = next(iter(r3_l2_relay_partial._jsonl(tape)), None)
    if not isinstance(start, dict) or start.get("event") != "start":
        raise ValueError("relay tape lacks a start record")
    mode = "trigger_only" if start.get("trigger_only") is True else ("planted" if start.get("planted_roots") else "clean")
    if (start.get("plan_sha256") != plan_sha256 or start.get("caps") != plan["caps"]
            or mode != plan["mode"] or start.get("scheduled_opportunities") != sum(map(len, plan["schedule"]))):
        raise ValueError("relay start does not bind the reviewed plan, limits and mode")
    replay = r3_l2_relay_replay.verify(
        board, board_sha256=pins.get("board_sha256"), generation_sha256=pins.get("generation_sha256"),
        render=json.dumps, host_response_path=host_path,
        host_response_sha256=pins.get("host_response_sha256"),
    )
    if replay["status"] != "complete" or replay["host_responses_verified"] is not True:
        raise ValueError("expected completed relay with independently recorded host responses")
    replay["readout"].pop("trace")
    if replay != terminal.get("export"):
        raise ValueError("host receipt differs from the completed relay replay")
    return {**receipt, "plan_id": plan["manifest_id"], "cpu_export_replayed": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--completion-sha256", required=True)
    parser.add_argument("--terminal-sha256", required=True)
    parser.add_argument("--plan-sha256", help="independent plan pin for exact CPU replay")
    args = parser.parse_args()
    try:
        pins = {"completion_sha256": args.completion_sha256, "terminal_sha256": args.terminal_sha256}
        receipt = (verify_bound(args.bundle, plan_sha256=args.plan_sha256, **pins)
                   if args.plan_sha256 is not None else verify(args.bundle, **pins))
    except (OSError, ValueError) as error:
        parser.exit(2, f"{error}\n")
    print(json.dumps(receipt, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
