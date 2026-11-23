"""Bind a SmolLM3 admission and reserve to the exact local worker and model files."""

from datetime import datetime
from decimal import Decimal
import hashlib
from pathlib import Path

from lab import replication_inventory
from lab import smollm3_opening_balance as opening
from lab import smollm3_smoke_admission as admission
from lab import smollm3_smoke_settlement as settlement


MODEL = "HuggingFaceTB/SmolLM3-3B"
REVISION = "a07cc9a04f16550a088caea529712d1d335b0ac1"
WORKER_MANIFEST_SHA256 = "e2146b3a2b3c652572ffb9e6d6d07d05def2c0489aeb50ac541e7e97688724b6"
WORKER_FILES = {
    "candidate-cuda-plan.json", "lab/smollm3_smoke_worker.py", "lab/spark_causal_decision.py",
    "lab/spark_decision.py",
}


def _real_directory(path):
    path = Path(path).absolute()
    if path.resolve(strict=True) != path or not path.is_dir():
        raise ValueError("expected an exact local directory with no links")
    return path


def _verify_worker(worker, manifest_path):
    root = _real_directory(worker)
    path = Path(manifest_path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("expected a regular worker manifest")
    with path.open("rb") as stream:
        raw = stream.read(4097)
    if hashlib.sha256(raw).hexdigest() != WORKER_MANIFEST_SHA256:
        raise ValueError("worker manifest differs from the reviewed closure")
    records = [line.split("  ", 1) for line in raw.decode("ascii").splitlines()]
    pins = {file: digest for digest, file in records}
    if len(records) != len(WORKER_FILES) or pins.keys() != WORKER_FILES:
        raise ValueError("unexpected worker file inventory")
    actual = set()
    for entry in root.rglob("*"):
        relative = entry.relative_to(root).as_posix()
        if entry.is_symlink():
            raise ValueError("unexpected link in worker tree")
        if not entry.is_dir():
            actual.add(relative)
            if relative not in pins or not entry.is_file():
                raise ValueError("unexpected worker input")
            with entry.open("rb") as stream:
                if hashlib.file_digest(stream, "sha256").hexdigest() != pins[relative]:
                    raise ValueError("worker file differs from its exact pin")
        elif relative != "lab":
            raise ValueError("unexpected directory in worker tree")
    if actual != pins.keys() or pins["candidate-cuda-plan.json"] != admission.WORKER_PLAN_SHA256:
        raise ValueError("worker tree does not contain the exact CUDA plan and closure")


def verify(receipt, reservation, snapshot, worker, worker_manifest, *, admission_sha256, now: datetime, opening_balance=None):
    """Review the pinned local handoff. This operation never starts a container."""
    accepted = admission.verify(receipt, admission_sha256=admission_sha256, now=now)
    reserve = settlement.verify(reservation, reservation_sha256=accepted["reservation_sha256"])
    if (reserve["admission_id"] != accepted["admission_id"]
            or reserve["held_gpu_hours"] != Decimal(str(accepted["reserved_gpu_hours"]))):
        raise ValueError("replication reserve does not bind the admission ID and amount")
    if opening_balance is not None:
        opening.verify_for_launch(
            *opening_balance, receipt=receipt, admission_pin=admission_sha256,
            reservation=reservation, reservation_pin=accepted["reservation_sha256"], now=now,
        )
    _verify_worker(worker, worker_manifest)
    directory = _real_directory(snapshot)
    pin = accepted["model_manifest_sha256"]
    normalized = replication_inventory._normalized(directory.parent, {
        "root": directory.name, "manifest_sha256": pin, "repo": MODEL, "revision": REVISION,
    })
    inventory = replication_inventory._snapshot(*normalized, "smollm3_public_smoke_candidate", pin)
    report = {
        "evidence": "smollm3_exact_local_input_preflight",
        "admission_id": accepted["admission_id"],
        "worker_plan_sha256": accepted["worker_plan_sha256"],
        "worker_manifest_sha256": WORKER_MANIFEST_SHA256,
        "reservation_sha256": reserve["reservation_sha256"],
        "model_manifest_sha256": pin,
        "snapshot_bytes": inventory["bytes"],
        "starts_container": False,
    }
    if opening_balance is not None:
        report["opening_placement_sha256"] = opening_balance[-1]
    return report
