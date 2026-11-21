"""Describe Pilot 3 replies after reconciling each saved text with its charge."""

import argparse
import json
from pathlib import Path

from lab import pilot_clearance, pilot_reply_diagnostics


def audit(directory: Path, ledger_path: Path):
    """Check the complete historic batch and report descriptive reply diagnostics."""
    schedule, schedule_sha = pilot_clearance._read(directory / "schedule.json")
    rows, episodes_sha = pilot_clearance._read(directory / "episodes.jsonl", lines=True)
    final, final_sha = pilot_clearance._read(directory / "final.json")
    ledger, ledger_sha = pilot_clearance._read(ledger_path, lines=True)
    turns = pilot_clearance._validate_episodes(schedule, rows)
    reconciliation = pilot_clearance._reconcile(final, ledger, rows, turns)
    pilot_clearance._require(
        all(set(turn["block_types"]) == {"text"} for turn in turns),
        "non-text provider blocks cannot establish a complete text-only reply",
    )
    records = ({**turn, "cond": episode["cond"]}
               for episode in rows for turn in episode["turns"])
    return {
        "batch": "pilot3",
        "evidence": "locally_reconciled_historical_reply_diagnostics",
        "response_sha256_matches": reconciliation["charges"],
        "source_sha256": {"schedule": schedule_sha, "episodes": episodes_sha, "final": final_sha,
                          "ledger": ledger_sha},
        "diagnostics": pilot_reply_diagnostics.describe(records),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("ledger", type=Path)
    args = parser.parse_args(argv)
    try:
        result = audit(args.directory, args.ledger)
    except (OSError, KeyError, TypeError, ValueError) as error:
        parser.exit(2, f"Pilot 3 reply provenance unavailable or inconsistent: {error}\n")
    print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
