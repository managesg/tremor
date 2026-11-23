"""Verify the retained R3-L2 evidence and inventory the missing launch inputs."""

import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path

from lab import adapter_lineage, r3_l2_relay_partial, r3_l2_relay_replay, r3_resource_audit, spark_calibration_guard

SCHEMA = "r3_l2_admission_inventory_v1"
BATCH = "R3-L2"
CALIBRATION = "runs/spark-calibration"
STOPS = "runs/r3-exact-relay-stop.OYdK97"
ARTIFACTS = {
    "protocol_draft": "docs/reports/workplan-ep/R3-L2-protocol-draft.md",
    "reference_custody": "docs/reports/workplan-ep/L2-reference-custody.md",
    "calibration_guard": "lab/spark_calibration_guard.py",
    "scripted_batch_runner": "lab/r3_l2_batch.py",
    "standalone_model_adapter": "lab/spark_decision.py",
    "model_snapshot_manifest": "data/hf/Qwen3.5-4B/MANIFEST.sha256.json",
    "calibration_admission": f"{CALIBRATION}/r2-admission.json",
    "resource_ledger": f"{CALIBRATION}/resource-ledger.jsonl",
    "calibration_log": f"{CALIBRATION}/r2-calibration.log",
    "l2_host_terminal": "runs/l2-host-response-scripted.lHgVm3/host/terminal-raw-verified.json",
    "cpu_completion": f"{STOPS}/completed.report.json",
    "cpu_memory_floor": f"{STOPS}/memory_floor.report.json",
    "cpu_wall_limit": f"{STOPS}/wall_limit.report.json",
}
LAUNCH_INPUTS = {
    "frozen_protocol": "L2 protocol author: exact estimands, opportunity windows, censoring, floor and stop rules",
    "protected_cohort_custody": "Independent custodian: reviewed cohort, reference truth, controls and split digests",
    "schedule_and_scorers": "L2 protocol author and reviewer: frozen seed, order, scorer and Board digests",
    "native_runner": "Coordinator-designated runner owner: exact executable, argv, code, image and config digests",
    "mount_and_capture_review": "Independent verifier: model and limits, read-only inputs, raw host custody, lock and cleanup",
    "resource_reservation": "Admission reviewer: exact short-job reservation, both balances and unresolved-attempt disposition",
    "operator_authorization": "Owner and independent reviewer: one-use exact-batch authorization, UTC window and both signatures",
}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _artifact(root, reference, expected_path):
    _require(type(reference) is dict and reference.keys() == {"path", "sha256"}
             and reference["path"] == expected_path, "unexpected admission artifact path or fields")
    adapter_lineage._artifact(root, reference)


def _check_calibration(root, artifacts):
    ledger_ref = artifacts["resource_ledger"]
    ledger = (root / ledger_ref["path"]).read_bytes()
    _require(hashlib.sha256(ledger).hexdigest() == ledger_ref["sha256"], "resource ledger changed during evidence readback")
    guard_log = root / artifacts["calibration_log"]["path"]
    records = [json.loads(line, parse_float=Decimal, object_pairs_hook=adapter_lineage._unique_members)
               for line in ledger.splitlines()]
    _require(len(records) == 2 and all(row["batch"] == spark_calibration_guard.BATCH for row in records),
             "resource evidence must contain only the historical R2 settlement")
    admission_ref = artifacts["calibration_admission"]
    admission = adapter_lineage._json(root / admission_ref["path"], admission_ref["sha256"])
    _require(admission["batch"] == records[0]["batch"] and admission["admission_id"] == records[0]["admission_id"]
             and Decimal(str(admission["reserved_gpu_hours"])) == records[0]["reserved_gpu_hours"],
             "historical R2 admission does not match its reservation")
    outcome, terminal, decision, digest = r3_resource_audit._read_guard_log(guard_log)
    _require(outcome is not None and terminal is not None
             and digest == artifacts["calibration_log"]["sha256"] == records[1]["run_log_sha256"],
             "historical calibration receipt and log do not bind")
    accounting = r3_resource_audit.audit(records, outcome=outcome, terminal=terminal, decision=decision)
    _require(accounting["status"] == "verified_settlement", "historical R2 accounting did not settle")
    ref = artifacts["model_snapshot_manifest"]
    model = adapter_lineage._json(root / ref["path"], ref["sha256"])
    revision = adapter_lineage._digest(model["revision"], 40)
    return {
        "scope": "historical_R2_only", "model_revision": revision, "model_weights_rehashed": False,
        "charged_gpu_hours": str(accounting["actual_charged_gpu_hours"]),
        "program_balance_gpu_hours_after_r2": str(accounting["available_program_gpu_hours"]),
        "shared_balance_gpu_hours_after_r2": str(accounting["available_r2_r3_gpu_hours"]),
    }


def _checked_stop(root, artifacts, role, scenario):
    ref = artifacts[role]
    report = adapter_lineage._json(root / ref["path"], ref["sha256"])
    _require(report["evidence"] == "scripted_cpu_guard_parent_tape" and report["stop"] == scenario
             and type(report["gpu_jobs"]) is int and report["gpu_jobs"] == 0
             and report["isolated_cpu"] is True and report["container_removed"] is True and report["child_reaped"] is True,
             "unexpected CPU stop evidence class or terminal state")
    directory = Path(ref["path"]).parent / scenario
    identity = adapter_lineage._digest(report["container_id"], 64)
    pins = report["artifacts"]
    image = report["isolation"]["image"]
    _require(report["isolation"]["network"] == "none" and image == spark_calibration_guard.IMAGE,
             "CPU evidence is outside the pinned isolation envelope")
    receipts = {}
    for name, key in (("guard-stop.json", "watchdog_stop_sha256"), ("container-exit.json", "container_exit_sha256"),
                      ("container-cleanup.json", "container_cleanup_sha256")):
        reference = {"path": str(directory / name), "sha256": report[key]}
        path = adapter_lineage._path(root, reference)
        record = receipts[name] = adapter_lineage._json(path, report[key])
        _require((record["container_id"], record["image"], record["manifest_sha256"])
                 == (identity, image, pins["manifest_sha256"]), "CPU stop receipts do not bind the same plan and ID")
    stop, terminal, cleanup = (receipts[key] for key in ("guard-stop.json", "container-exit.json", "container-cleanup.json"))
    _require(stop["stop"] == scenario and stop["scripted_trigger_reached"] is True and stop["attempts_observed"] == 2
             and terminal["status"] == "exited" and terminal["exit_code"] == 137 and terminal["oom_killed"] is False
             and cleanup["absent_after_removal"] is True and cleanup["removal_acknowledged"] is True
             and cleanup["forced"] is False, "CPU watchdog, exit or cleanup receipt differs from the expected stop")
    board = root / directory / "export/board.jsonl"
    export = r3_l2_relay_partial.verify(board, manifest_path=root / directory / "plan.json",
                                        host_response_path=root / directory / "host.jsonl", **pins)
    expected_unknown = int(scenario == "memory_floor")
    _require(export == report["export"] and export["status"] == "incomplete_prefix"
             and export["open_opportunity"] == 1 and export["readout"] is None
             and export["unknown_attempts"] == expected_unknown
             and (export["host_only_usage"] is None) == bool(expected_unknown),
             "CPU stop export differs from the independently replayed usage prefix")
    return {"container_id": identity, "exit": terminal["exit_code"], "unknown_attempts": expected_unknown,
            "host_only_usage_retained": export["host_only_usage"] is not None}


def _check_cpu_evidence(root, artifacts):
    ref = artifacts["l2_host_terminal"]
    terminal = adapter_lineage._json(root / ref["path"], ref["sha256"])
    _require(terminal["evidence"] == "scripted_host_response_verified" and terminal["status"] == "completed"
             and len(terminal["arms"]) == 2
             and {row["condition"] for row in terminal["arms"]} == {"warning", "neutral"},
             "host terminal is not the paired scripted L2 receipt")
    memory = _checked_stop(root, artifacts, "cpu_memory_floor", "memory_floor")
    wall = _checked_stop(root, artifacts, "cpu_wall_limit", "wall_limit")
    ref = artifacts["cpu_completion"]
    completed = adapter_lineage._json(root / ref["path"], ref["sha256"])
    identity = adapter_lineage._digest(completed["container_id"], 64)
    _require(len({identity, memory["container_id"], wall["container_id"]}) == 3,
             "CPU receipts reuse a container identity")
    _require(completed["evidence"] == "scripted_cpu_guard_parent_tape" and completed["stop"] == "completed"
             and completed["isolated_cpu"] is True and completed["container_removed"] is True
             and completed["gpu_jobs"] == 0 and completed["isolation"]["image"] == spark_calibration_guard.IMAGE,
             "unexpected CPU completion evidence")
    directory = Path(ref["path"]).parent / "completed"
    pins = completed["artifacts"]
    adapter_lineage._artifact(root, {"path": str(directory / "plan.json"), "sha256": pins["manifest_sha256"]})
    relay = r3_l2_relay_replay.verify(root / directory / "export/board.jsonl", render=json.dumps,
                                      board_sha256=pins["board_sha256"], generation_sha256=pins["generation_sha256"],
                                      host_response_path=root / directory / "host.jsonl",
                                      host_response_sha256=pins["host_response_sha256"])
    relay["readout"].pop("trace")
    _require(relay == completed["export"] and relay["status"] == "complete"
             and relay["host_responses_verified"] is True, "CPU completion differs from its replay")
    return {"scripted_host_arms": len(terminal["arms"]), "memory_floor": memory, "wall_limit": wall,
            "scripted_completion_relay_mean": relay["readout"]["first_generation_relay_mean"]}


def verify(repository, manifest, *, manifest_sha256):
    """Verify a fixed offline inventory without implementing or admitting a native run."""
    root = Path(repository).resolve(strict=True)
    document = adapter_lineage._json(Path(manifest), manifest_sha256)
    _require(document.keys() == {"schema", "batch", "artifacts", "launch_inputs"}
             and document["schema"] == SCHEMA and document["batch"] == BATCH,
             "R3-L2 evidence inventory has unexpected scope or fields")
    inputs = document["launch_inputs"]
    _require(type(inputs) is dict and inputs.keys() == LAUNCH_INPUTS.keys()
             and all(value is None for value in inputs.values()), "offline inventory cannot accept launch inputs")
    artifacts = document["artifacts"]
    _require(type(artifacts) is dict and artifacts.keys() == ARTIFACTS.keys(), "incomplete R3-L2 evidence roles")
    for key, expected_path in ARTIFACTS.items():
        _artifact(root, artifacts[key], expected_path)
    return {
        "batch": BATCH, "status": "awaiting_inputs", "authorizes_execution": False, "native_entrypoint": None,
        "manifest_sha256": manifest_sha256, "artifacts": artifacts, "missing_inputs": LAUNCH_INPUTS,
        "historical_calibration": _check_calibration(root, artifacts), "cpu_evidence": _check_cpu_evidence(root, artifacts),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--manifest-sha256", required=True)
    args = parser.parse_args()
    try:
        result = verify(args.repository, args.manifest, manifest_sha256=args.manifest_sha256)
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.exit(2, f"{error}\n")
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
