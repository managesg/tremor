"""Replay retained public L1 dispatch with separately pinned fixture labels."""

import argparse
import json
from pathlib import Path

from lab import adapter_lineage, l1_dispatch_replay, l1_dispatch_scoring, l1_verification_allocation as allocation


COHORT = "public-l1-development-positive-v1"
REFERENCE_SHA256 = "030861581f1d7ef5dd690ce9b0c210a252701b5ef9e46adbf91434bc37b1c108"
LABEL_SCHEMA = "l1_public_claim_labels_v1"


def reference_labels(reference):
    """Read the fixture's recorded legitimacy labels, with no checker results."""
    document = adapter_lineage._json(Path(reference), REFERENCE_SHA256)
    positive = document["positive"]["arms"]
    claims, _ = allocation.development_inputs()
    identifier_order = [claim.identifier for claim in claims]
    rows = None
    for arm in positive.values():
        observed = [(row["claim_id"], row["legitimate"]) for row in arm["metrics"]["outcomes"]]
        if [identifier for identifier, _ in observed] != identifier_order or any(
            type(legitimate) is not bool for _, legitimate in observed
        ):
            raise ValueError("fixture label inventory differs from the public claims")
        if rows is not None and rows != observed:
            raise ValueError("fixture arms bind different legitimacy labels")
        rows = observed
    if not rows:
        raise ValueError("fixture contains no label inventory")
    source = f"public-l1-positive-reference-{REFERENCE_SHA256}"
    return {"schema": LABEL_SCHEMA, "cohort": COHORT,
            "claim_inventory_sha256": allocation.digest(allocation._claim_inventory(claims)),
            "labels": [{"claim_id": identifier, "case_id": f"l1-public-{identifier}", "source_id": source,
                        "legitimate": legitimate} for identifier, legitimate in rows]}


def replay(bundle, reference, labels, *, pins_sha256, labels_sha256):
    root = Path(bundle)
    pinned_labels = adapter_lineage._json(Path(labels), labels_sha256)
    if pinned_labels != reference_labels(reference):
        raise ValueError("independent fixture labels differ from the pinned historical reference")
    dispatch = l1_dispatch_replay.replay(root, pins_sha256=pins_sha256)
    pins = adapter_lineage._json(root / "pins.json", pins_sha256)
    claims, _ = allocation.development_inputs()
    reports = {}
    for name, prior_report in dispatch["reports"].items():
        directory = root / name
        plan = adapter_lineage._json(directory / "plan.json", pins[name]["plan_file_sha256"])
        reports[name] = l1_dispatch_scoring.score(
            plan, claims, directory / "journal.jsonl", labels,
            plan_sha256=prior_report["plan_sha256"], journal_sha256=prior_report["journal_sha256"],
            labels_sha256=labels_sha256, expected_cohort=COHORT,
        )
    return {"scope": "scripted_cpu_dispatch_label_replay", "scientific_result": False,
            "original_labels_reference_sha256": REFERENCE_SHA256, "dispatch_pins_sha256": pins_sha256,
            "labels_sha256": labels_sha256, "reports": reports}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("reference", type=Path)
    parser.add_argument("labels", type=Path)
    parser.add_argument("--pins-sha256", required=True)
    parser.add_argument("--labels-sha256", required=True)
    args = parser.parse_args()
    try:
        result = replay(args.bundle, args.reference, args.labels, pins_sha256=args.pins_sha256,
                        labels_sha256=args.labels_sha256)
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.exit(2, f"{error}\n")
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
