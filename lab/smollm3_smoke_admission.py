"""Validate a separately pinned SmolLM3 Spark smoke admission offline."""

from datetime import datetime, timedelta
from decimal import Decimal
from hashlib import sha256
import json
import os
import re
from stat import S_ISREG


SCHEMA = "tremor.smollm3_smoke_admission.v1"
BATCH = "spark-smollm3-3b-technical-smoke"
ALLOCATION = "spark-replication"
WORKER_PLAN_SHA256 = "514d0decfdf849432ad7893cb9b465af62d5fce8acdab4ee849a80d195326dc8"
MODEL_MANIFEST_SHA256 = "6ff79f0d818a19b9e36f64c7bae12558d099889eae5b368038133a4906df9d7f"
RESERVED_GPU_HOURS = Decimal("0.1")
OUTER_WALL_SECONDS = 300

_MAX_RECEIPT_BYTES = 16384
_SHA256 = re.compile(r"[a-f0-9]{64}")
_IDENTIFIER = re.compile(r"[A-Za-z0-9_-]{1,80}")
_UTC = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|\+00:00)")
_FIELDS = {
    "schema", "admission_id", "batch", "valid_from_utc", "valid_until_utc",
    "worker_plan_sha256", "model_manifest_sha256", "allocation",
    "reservation_sha256", "review_reference", "authorization_reference",
    "reserved_gpu_hours", "outer_wall_seconds",
}


def _unique(pairs):
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError("duplicate smoke admission field")
    return result


def _reject_constant(value):
    raise ValueError(f"nonfinite smoke admission number: {value}")


def _timestamp(value):
    if type(value) is not str or _UTC.fullmatch(value) is None:
        raise ValueError("smoke admission timestamps must be explicit ISO 8601 UTC")
    try:
        return datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError("invalid smoke admission UTC timestamp") from error


def verify(path, *, admission_sha256, now):
    """Verify a receipt's bounds and identity. The launcher consumes its ID.

    The caller supplies the independently obtained receipt digest, checks the
    referenced reservation and review, and owns any journal or GPU operation.
    """
    if type(admission_sha256) is not str or _SHA256.fullmatch(admission_sha256) is None:
        raise ValueError("expected lowercase SHA-256 for the smoke admission")
    if not isinstance(now, datetime) or now.utcoffset() != timedelta(0):
        raise ValueError("admission validation requires the current UTC time")

    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        if not S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError("smoke admission must be a regular file")
        raw = stream.read(_MAX_RECEIPT_BYTES + 1)
    if len(raw) > _MAX_RECEIPT_BYTES or sha256(raw).hexdigest() != admission_sha256:
        raise ValueError("smoke admission digest mismatch or oversized receipt")
    receipt = json.loads(raw, object_pairs_hook=_unique, parse_float=Decimal, parse_constant=_reject_constant)
    if type(receipt) is not dict or set(receipt) != _FIELDS or receipt["schema"] != SCHEMA:
        raise ValueError("unexpected smoke admission schema")
    identifier = receipt["admission_id"]
    if type(identifier) is not str or _IDENTIFIER.fullmatch(identifier) is None:
        raise ValueError("invalid one-use smoke admission ID")
    if receipt["batch"] != BATCH or receipt["allocation"] != ALLOCATION:
        raise ValueError("expected the SmolLM3 smoke batch and replication allocation")
    if (receipt["worker_plan_sha256"] != WORKER_PLAN_SHA256
            or receipt["model_manifest_sha256"] != MODEL_MANIFEST_SHA256):
        raise ValueError("smoke admission pins a different worker plan or model manifest")
    reservation = receipt["reservation_sha256"]
    if type(reservation) is not str or _SHA256.fullmatch(reservation) is None:
        raise ValueError("expected a pinned replication reservation")
    for field in ("review_reference", "authorization_reference"):
        reference = receipt[field]
        if type(reference) is not str or not reference.strip() or not reference.isprintable():
            raise ValueError(f"expected a nonempty {field}")
    if (type(receipt["reserved_gpu_hours"]) is not Decimal or receipt["reserved_gpu_hours"] != RESERVED_GPU_HOURS
            or type(receipt["outer_wall_seconds"]) is not int or receipt["outer_wall_seconds"] != OUTER_WALL_SECONDS):
        raise ValueError("smoke admission differs from the reviewed resource envelope")

    start = _timestamp(receipt["valid_from_utc"])
    end = _timestamp(receipt["valid_until_utc"])
    if not start <= now < end or end - now < timedelta(seconds=OUTER_WALL_SECONDS):
        raise ValueError("current UTC window does not cover the smoke deadline")
    return {**receipt, "reserved_gpu_hours": float(RESERVED_GPU_HOURS)}
