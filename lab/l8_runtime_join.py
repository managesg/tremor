"""Check pinned stage and sample bindings in an L8-D runtime capture."""

import argparse
import json
from pathlib import Path
import re

from lab.controller_selection import _match_artifact, _reference
from lab.replication_inventory import _hex, _metadata, _object, _require


STAGES = ("before", "after")
BINDINGS = ("freeze_sha256", "protocol_sha256", "base_manifest_sha256", "hook_id")
STAGE_FIELDS = ("checkpoint_sha256", "installed_state_sha256")
SAMPLE_FIELDS = ("sample_id", "prompt_sha256", "token_indices")
PLAN_SCHEMA = "tremor.l8d_runtime_plan.v1"
CAPTURE_SCHEMA = "tremor.l8d_runtime_capture.v1"


def _identifier(value):
    _require(type(value) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]*", value),
             "expected a canonical L8-D identifier")
    return value


def _sample(row):
    indices = row["token_indices"]
    _require(type(indices) is list and indices and all(type(index) is int and index >= 0 for index in indices)
             and len(set(indices)) == len(indices), "expected distinct L8-D token indices")
    return _identifier(row["sample_id"]), (_hex(row["prompt_sha256"], 64), tuple(indices))


def verify(bundle, plan_path, capture_path, *, plan_sha256, capture_sha256):
    """Verify the declared join and raw bytes without decoding activation values."""
    root = Path(bundle).resolve(strict=True)
    plan = _object(_metadata(Path(plan_path), plan_sha256), ("schema", *BINDINGS, "stages", "samples"),
                   "L8-D runtime plan")
    capture = _object(_metadata(Path(capture_path), capture_sha256), ("schema", *BINDINGS, "rows"),
                      "L8-D runtime capture")
    _require(plan["schema"] == PLAN_SCHEMA and capture["schema"] == CAPTURE_SCHEMA,
             "unsupported L8-D runtime schema")
    pinned = {key: _hex(plan[key], 64) for key in BINDINGS if key != "hook_id"}
    pinned["hook_id"] = _identifier(plan["hook_id"])
    for key, value in pinned.items():
        _require(capture[key] == value, f"runtime capture differs from approved {key}")

    stages = _object(plan["stages"], STAGES, "L8-D stages")
    for values in stages.values():
        _object(values, STAGE_FIELDS, "L8-D stage")
        for value in values.values():
            _hex(value, 64)
    _require(stages["before"]["checkpoint_sha256"] != stages["after"]["checkpoint_sha256"],
             "expected distinct approved checkpoint digests")
    state_changed = stages["before"]["installed_state_sha256"] != stages["after"]["installed_state_sha256"]

    _require(type(plan["samples"]) is list and plan["samples"], "expected frozen L8-D samples")
    samples = {}
    for row in plan["samples"]:
        identifier, sample = _sample(_object(row, SAMPLE_FIELDS, "L8-D sample"))
        _require(identifier not in samples, "duplicate frozen L8-D sample")
        samples[identifier] = sample

    _require(type(capture["rows"]) is list, "expected L8-D activation rows")
    expected = {(identifier, stage) for identifier in samples for stage in STAGES}
    seen, raw_files = set(), set()
    for row in capture["rows"]:
        _object(row, (*SAMPLE_FIELDS, *STAGE_FIELDS, "stage", "raw"), "L8-D activation row")
        identifier, sample = _sample(row)
        stage = _identifier(row["stage"])
        key = identifier, stage
        _require(key in expected and key not in seen, "unexpected or duplicate L8-D sample-stage row")
        _require(sample == samples[identifier], "runtime prompt or token selection differs from the frozen sample")
        _require(all(row[field] == stages[stage][field] for field in STAGE_FIELDS),
                 "runtime checkpoint or installed state differs from the approved stage")
        raw = row["raw"]
        path = _reference(root, raw)
        info = path.stat()
        file_identity = info.st_dev, info.st_ino
        _require(info.st_size > 0, "raw L8-D capture must not be empty")
        _require(file_identity not in raw_files, "raw L8-D capture file reused across rows")
        _match_artifact(root, raw)
        raw_files.add(file_identity)
        seen.add(key)
    _require(seen == expected, "runtime capture does not cover every frozen sample and stage")
    return {
        **pinned, "evidence": "l8d_runtime_receipt_join", "plan_sha256": plan_sha256,
        "capture_sha256": capture_sha256, "samples": len(samples), "verified_capture_rows": len(seen),
        "declared_installed_state_changed": state_changed,
        "native_execution_verified": False, "settlement_verified": False,
        "activation_values_verified": False, "scientific_acceptance": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("bundle", "plan_path", "capture_path"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--capture-sha256", required=True)
    try:
        result = verify(**vars(parser.parse_args()))
    except (OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
