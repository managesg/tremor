"""Offline structural preflight for a frozen L8-B probe evidence bundle."""

import argparse
from itertools import combinations
import json
from pathlib import Path
from unicodedata import normalize

from lab import adapter_lineage
from lab import l8_matched_probe_controls as probe


SCHEMA = "l8_probe_lineage_v1"
SPLITS = ("training", "threshold_fit_clean", "heldout_clean", "heldout_failure")


def _fields(value, expected):
    if type(value) is not dict or value.keys() != set(expected.split()):
        raise ValueError("unexpected probe lineage fields")


def _identifier(value):
    if type(value) is not str or not value or value != value.strip() or value != normalize("NFC", value):
        raise ValueError("probe lineage IDs must be nonempty and canonical")
    return value


def _reference(reference):
    _fields(reference, "path sha256")
    if type(reference["path"]) is not str or not reference["path"]:
        raise ValueError("expected a probe artifact path")
    adapter_lineage._digest(reference["sha256"], 64)
    return reference


def _pinned_artifact_json(root, reference):
    reference = _reference(reference)
    return adapter_lineage._json(adapter_lineage._path(root, reference), reference["sha256"])


def _split(root, record, seen_ids):
    _fields(record, "samples probe_rows")
    samples = record["samples"]
    if type(samples) is not list or not samples:
        raise ValueError("probe lineage split must declare samples")
    ids, families, contents = set(), set(), set()
    for sample in samples:
        _fields(sample, "sample_id family_id content")
        identifier = _identifier(sample["sample_id"])
        family = _identifier(sample["family_id"])
        if identifier in seen_ids:
            raise ValueError("probe lineage sample IDs must be globally unique")
        reference = _reference(sample["content"])
        adapter_lineage._artifact(root, reference)
        seen_ids.add(identifier)
        ids.add(identifier)
        families.add(family)
        contents.add(reference["sha256"])

    document = _pinned_artifact_json(root, record["probe_rows"])
    _fields(document, "rows")
    rows = document["rows"]
    if type(rows) is not list or any(type(row) is not dict or "id" not in row for row in rows):
        raise ValueError("expected probe row objects with sample IDs")
    row_ids = [_identifier(row["id"]) for row in rows]
    if len(row_ids) != len(ids) or set(row_ids) != ids:
        raise ValueError("probe row IDs differ from the declared sample inventory")
    return rows, families, contents


def _check_disjoint(splits):
    training, threshold = (splits[name][1:] for name in SPLITS[:2])
    clean, failure = (splits[name][1:] for name in SPLITS[2:])
    holdout = tuple(left | right for left, right in zip(clean, failure, strict=True))
    for left, right in combinations((training, threshold, holdout), 2):
        if left[0] & right[0]:
            raise ValueError("probe family overlaps training, threshold fit or holdout")
        if left[1] & right[1]:
            raise ValueError("probe content overlaps training, threshold fit or holdout")


def verify(bundle, manifest_path, *, manifest_sha256, plan_sha256, report_sha256):
    """Verify exact artifacts, declared partitions, and replay of the matched probe report."""
    root = Path(bundle).resolve(strict=True)
    manifest = adapter_lineage._json(Path(manifest_path), manifest_sha256)
    _fields(manifest, "schema probe_plan heldout_report splits")
    if manifest["schema"] != SCHEMA:
        raise ValueError("unknown probe lineage schema")
    _fields(manifest["splits"], " ".join(SPLITS))

    plan = _pinned_artifact_json(root, manifest["probe_plan"])
    if probe.digest(plan) != adapter_lineage._digest(plan_sha256, 64):
        raise ValueError("probe plan differs from its independent digest")
    report_ref = _reference(manifest["heldout_report"])
    if report_ref["sha256"] != adapter_lineage._digest(report_sha256, 64):
        raise ValueError("held-out report differs from its independent digest")
    report = _pinned_artifact_json(root, report_ref)

    seen_ids = set()
    splits = {name: _split(root, manifest["splits"][name], seen_ids) for name in SPLITS}
    _check_disjoint(splits)
    training, threshold, clean, failure = (splits[name][0] for name in SPLITS)
    fitted = probe.fit(training, threshold, seed=plan["seed"], vocabulary=plan["vocabulary"])
    if probe.digest(fitted) != plan_sha256:
        raise ValueError("probe plan differs from the normalized fit rows")
    measured = probe.evaluate(fitted, clean, failure, plan_sha256=plan_sha256)
    if probe.digest(measured) != probe.digest(report):
        raise ValueError("held-out report differs from the normalized probe row replay")

    return {
        "status": "verified_offline", "scientific_result": False, "custody_verified": False,
        "manifest_sha256": manifest_sha256, "probe_plan_sha256": plan_sha256, "heldout_report_sha256": report_sha256,
        "fit_split_sha256": fitted["fit_split_sha256"], "heldout_split_sha256": measured["heldout_split_sha256"],
        "splits": {
            name: {"sample_count": len(rows), "family_count": len(families), "content_count": len(contents),
                   "sample_ids_sha256": probe.digest(sorted(row["id"] for row in rows))}
            for name, (rows, families, contents) in splits.items()
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--plan-sha256", required=True, help="canonical digest from the matched probe plan")
    parser.add_argument("--report-sha256", required=True, help="SHA-256 of the independently retained report file")
    args = parser.parse_args()
    try:
        result = verify(args.bundle, args.manifest, manifest_sha256=args.manifest_sha256,
                        plan_sha256=args.plan_sha256, report_sha256=args.report_sha256)
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
