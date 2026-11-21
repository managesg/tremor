"""Replay the pinned R1 development episode and its Board and scoring receipts."""

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from lab import adapter_lineage, r1_episode_v2


ARTIFACTS = ("plan.json", "dispatch.json", "board.jsonl", "delivery.jsonl")


def verify(bundle, *, summary_sha256):
    """Verify closed scores and retain nulls at controlled stop boundaries."""
    root = Path(bundle).resolve(strict=True)
    summary_path = adapter_lineage._path(root, {"path": "summary.json"})
    summary = adapter_lineage._json(summary_path, summary_sha256)
    plan_path = adapter_lineage._path(root, {"path": "plan.json"})
    plan = adapter_lineage._json(plan_path, summary.get("plan_sha256"))
    with TemporaryDirectory(prefix="tremor-r1-episode-audit-") as directory:
        output = Path(directory) / "replay"
        expected = r1_episode_v2.run(
            output, case=plan.get("case"), seed=plan.get("seed"),
            stop_after_round=plan.get("controlled_stop_after_round"),
        )
        if summary != expected:
            raise ValueError("pinned summary differs from the replayed episode and scores")
        for name in ARTIFACTS:
            archive = adapter_lineage._path(root, {"path": name})
            if archive.read_bytes() != (output / name).read_bytes():
                raise ValueError(f"archived {name} differs from replay")
    prefix = summary["first_round_score"]
    final = summary["final_score"]
    return {
        "evidence": "pinned_scripted_r1_episode_replay",
        "summary_sha256": summary_sha256,
        "case": summary["case"],
        "status": summary["status"],
        "committed_measured_rounds": summary["committed_measured_rounds"],
        "first_round_distinct_passing": None if prefix is None else prefix["distinct_passing"],
        "final_distinct_passing": None if final is None else final["distinct_passing"],
        "scientific_result": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--summary-sha256", required=True)
    args = parser.parse_args()
    try:
        result = verify(**vars(args))
    except (OSError, ValueError) as error:
        parser.exit(2, f"{error}\n")
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
