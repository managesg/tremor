"""Index evidence for the R3-L5 first slice without authorizing a run."""

import argparse
import hashlib
import json
from pathlib import Path
import re


BATCH = "R3-L5"
ROOT = Path(__file__).resolve().parents[1]
SHA256 = re.compile(r"[0-9a-f]{64}")
REVIEW_ROLES = {
    "frozen_protocol": "L5 protocol author",
    "protected_n2_custody": "Independent N2 custodian",
    "schedule_and_independent_scorer": "Protocol author and independent scorer reviewer",
    "native_runner": "Coordinator-designated runner owner",
    "mount_and_capture_review": "Independent verifier",
    "resource_reservation": "Resource and admission reviewer",
    "operator_authorization": "Owner and independent admission reviewer",
}
PUBLIC_EVIDENCE = {
    "completed_delivery_matrix": (
        "runs/l5-matrix-delivery.s2y3ZN/replay/audit.json",
        "41b9545ca69e459265418244e0d8fd559abbf3efe94a2520ca118db7bc640470",
        ("status", "arms", "work_attempts", "delivery_witnesses", "complete_cycles"),
    ),
    "condition_bound_interruption": (
        "runs/r3-l5-detached-bound-prefix.MAUvaX/result.json",
        "5c48c2db4142fea45de9cf1108eedf3745d13489b003047e313e1ca1b9f2d9ce",
        ("scope", "run_id", "wire_event_counts", "unstarted", "comparison"),
    ),
    "child_stop_observation": (
        "runs/l5-condition-current.Pjhcxc/live-barrier-report.json",
        "bb08da07b09e6a45cad6aef122dfb46fe055f0d1225cc8051eb7d32b9bf6cd3c",
        ("status", "evidence", "completed_arms", "open_attempts", "comparison"),
    ),
}


def _digest(value):
    return isinstance(value, str) and SHA256.fullmatch(value) is not None


def _read_pinned(path, expected):
    if not _digest(expected):
        raise ValueError(f"invalid SHA-256 for {path}")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError(f"SHA-256 mismatch for {path}")
    return json.loads(raw)


def _review_references(index):
    if index is None:
        return None, {}
    if not isinstance(index, dict) or set(index) != {"batch", "plan_sha256", "references"}:
        raise ValueError("review index must contain batch, plan_sha256, and references")
    plan = index["plan_sha256"]
    references = index["references"]
    if index["batch"] != BATCH or not _digest(plan) or not isinstance(references, dict):
        raise ValueError("review index must identify the exact R3-L5 plan")
    if references.keys() - REVIEW_ROLES.keys():
        raise ValueError("unknown review role")
    for role, reference in references.items():
        if (
            not isinstance(reference, dict)
            or set(reference) != {"plan_sha256", "reference_sha256"}
            or reference["plan_sha256"] != plan
            or not _digest(reference["reference_sha256"])
        ):
            raise ValueError(f"{role} must reference the same plan and an exact SHA-256")
    return plan, references


def inventory(root, index=None):
    plan, references = _review_references(index)
    public = {}
    for name, (relative, digest, fields) in PUBLIC_EVIDENCE.items():
        receipt = _read_pinned(root / relative, digest)
        public[name] = {"path": relative, "sha256": digest, **{key: receipt[key] for key in fields}}
    return {
        "batch": BATCH,
        "plan_sha256": plan,
        "public_development_evidence": public,
        "review_references": {
            role: {
                "owner_role": owner,
                "reference_sha256": references.get(role, {}).get("reference_sha256"),
                "disposition": "reference_supplied" if role in references else "missing",
            }
            for role, owner in REVIEW_ROLES.items()
        },
        "missing_references": sorted(REVIEW_ROLES.keys() - references.keys()),
        "independent_review_verified": False,
        "protected_custody_verified": False,
        "authorizes_execution": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="root of the retained public artifacts")
    parser.add_argument("--review-index", type=Path, help="public metadata with opaque review digests")
    parser.add_argument("--review-index-sha256", help="independently supplied digest of the review index")
    args = parser.parse_args()
    if (args.review_index is None) != (args.review_index_sha256 is None):
        parser.error("--review-index and --review-index-sha256 must be supplied together")
    try:
        index = _read_pinned(args.review_index, args.review_index_sha256) if args.review_index else None
        report = inventory(args.root, index)
    except (OSError, KeyError, ValueError) as error:
        parser.exit(2, f"{error}\n")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
