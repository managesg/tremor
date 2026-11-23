"""Check pinned prospective precision inputs without admitting a research run."""

import argparse
import hashlib
import json
from pathlib import Path
from unicodedata import normalize

from lab import adapter_lineage, r2_precision_math


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _fields(record, expected):
    _require(type(record) is dict and record.keys() == set(expected.split()), "unexpected precision input fields")


def _id(value):
    _require(type(value) is str and bool(value) and value == value.strip() and value == normalize("NFC", value),
             "precision IDs and units must be nonblank and canonical")
    return value


def _int(value, minimum):
    _require(type(value) is int and value >= minimum, "invalid precision cluster count or rerun count")
    return value


def _reference(root, reference):
    _fields(reference, "path sha256")
    _require(type(reference["path"]) is str and bool(reference["path"]), "invalid precision artifact path")
    return adapter_lineage._path(root, reference)


def _document(root, reference):
    return adapter_lineage._json(_reference(root, reference), reference["sha256"])


def _pilot(root, reference, design_pin):
    if reference is None:
        return None, None
    record = _document(root, reference)
    _fields(record, "schema design_sha256 method sd icc reruns_per_cluster clusters")
    _require(record["schema"] == "r2_precision_variance_v1" and record["design_sha256"] == design_pin,
             "variance receipt differs from the pinned precision design")
    reruns = _int(record["reruns_per_cluster"], 3)
    _require(type(record["clusters"]) is list, "variance receipt needs an enumerated pilot cluster inventory")
    seen, eligible = set(), 0
    for cluster in record["clusters"]:
        _fields(cluster, "id status reruns")
        identifier = _id(cluster["id"])
        count = _int(cluster["reruns"], 0)
        _require(identifier not in seen and cluster["status"] in ("eligible", "censored"),
                 "duplicate or unsupported pilot cluster")
        seen.add(identifier)
        if cluster["status"] == "eligible":
            _require(count == reruns, "eligible pilot cluster does not have its planned matched reruns")
            eligible += 1
    _require(eligible >= 2, "variance receipt needs at least two eligible independent cluster IDs")
    return {key: record[key] for key in ("method", "sd", "icc", "reruns_per_cluster")}, {
        "eligible_clusters": eligible, "censored_clusters": len(seen) - eligible,
    }


def _capacity(root, reference, design_pin):
    if reference is None:
        return None
    record = _document(root, reference)
    _fields(record, "schema design_sha256 max_clusters reruns_per_cluster")
    _require(record["schema"] == "r2_precision_capacity_v1" and record["design_sha256"] == design_pin,
             "capacity receipt differs from the pinned precision design")
    return {"max_clusters": _int(record["max_clusters"], 0),
            "reruns_per_cluster": _int(record["reruns_per_cluster"], 3)}


def verify(bundle, manifest, *, manifest_sha256):
    root = Path(bundle).resolve(strict=True)
    packet = adapter_lineage._json(Path(manifest), manifest_sha256)
    _fields(packet, "schema proposal design pilot capacity")
    _require(packet["schema"] == "r2_precision_preflight_v1", "unexpected precision preflight schema")
    proposal_path = _reference(root, packet["proposal"])
    proposal_pin = hashlib.sha256(proposal_path.read_bytes()).hexdigest()
    adapter_lineage._match(proposal_path, proposal_pin, packet["proposal"]["sha256"])
    design = _document(root, packet["design"])
    _fields(design, "schema line unit expected_effect kill_boundary")
    _require(design["schema"] == "r2_precision_design_v1", "unexpected precision design schema")
    line, units = _id(design["line"]), _id(design["unit"])
    design_pin = packet["design"]["sha256"]
    pilot, coverage = _pilot(root, packet["pilot"], design_pin)
    capacity = _capacity(root, packet["capacity"], design_pin)
    planning = r2_precision_math.calculate(expected_effect=design["expected_effect"],
                                            kill_boundary=design["kill_boundary"], pilot=pilot, capacity=capacity)
    return {
        "line": line, "unit": units, "manifest_sha256": manifest_sha256, "proposal_sha256": proposal_pin,
        "design_sha256": design_pin, "pilot_sha256": packet["pilot"]["sha256"] if pilot is not None else None,
        "capacity_sha256": packet["capacity"]["sha256"] if capacity is not None else None,
        "pilot_coverage": coverage, "capacity": capacity, "planning": planning, "observed_standard_error": None,
        "scientific_decision_reachability": None,
        "authorizes_execution": False, "scientific_result": False, "custody_authenticity_verified": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--manifest-sha256", required=True)
    args = parser.parse_args()
    try:
        report = verify(args.bundle, args.manifest, manifest_sha256=args.manifest_sha256)
    except (KeyError, OSError, TypeError, ValueError, OverflowError) as error:
        parser.exit(2, f"{error}\n")
    print(json.dumps(report, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
