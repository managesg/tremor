"""Rescore opening and post-disruption work in an audited scripted L5 matrix."""

import argparse
import json
from pathlib import Path

from lab import l5_matrix_audit, l5_matrix_partial
from tremor.board import read_log
from tremor.trapbench import alloc, alloc2


def _score(actions, taskset):
    score = alloc2.second_scorer_gate(actions, taskset, alloc.score) if actions else None
    if score is not None and not score["valid"]:
        raise ValueError("phase scorers did not agree on valid work")
    return score


def verify(directory, *, summary_sha256):
    """Bind phase readbacks to the scripted work order and closed Board rounds."""
    directory = Path(directory)
    audited = l5_matrix_audit.audit(directory, summary_sha256=summary_sha256)
    summary = l5_matrix_audit._pinned_json(directory / "summary.json", summary_sha256)
    plan = l5_matrix_audit._pinned_json(directory / "plan.json", summary["plan_sha256"])
    opening = 2 if plan["contended"] else 1
    phase_rounds = {"pre": opening, "post": opening + 2}
    arms = []
    for row in summary["rows"]:
        trace = read_log(directory / row["arm_id"] / "board.jsonl")
        commits = {event["round"]: event["hash"] for event in trace if event["type"] == "end_round"}
        if trace[-1]["hash"] != row["board_head"] or any(r not in commits for r in phase_rounds.values()):
            raise ValueError("phase readback requires the pinned Board and both phase commits")
        attempts = [entry for entry in row["dispatch"] if entry["action"]["type"] == "work"]
        phases = {phase: [] for phase in phase_rounds}
        # Admitted work has no independent Board event in the legacy archive.
        # The scripted runner emits its first oracle job before the intervention.
        oracle = alloc.oracle_log(row["taskset"])
        for index, (dispatch, work, job) in enumerate(zip(attempts, row["work"], oracle, strict=True)):
            phase = "pre" if index == 0 else "post"
            if dispatch["phase"] != phase or dispatch["round"] != phase_rounds[phase]:
                raise ValueError("work phase does not match its committed Board round")
            if type(dispatch["action"]["answer"]) is not int or type(work["action"]["answer"]) is not int:
                raise ValueError("scripted work answers must be exact integers")
            if {key: value for key, value in work["action"].items() if key != "rejected"} != job:
                raise ValueError("work order differs from the scripted oracle")
            phases[phase].append(work["action"])
        if len(phases["pre"]) != 1 or len(phases["post"]) != row["taskset"]["n_agents"] - 1:
            raise ValueError("work counts differ from the expected opening and post phases")
        results = {
            phase: {"round": round_, "commit_head": commits[round_], "work_attempts": len(phases[phase]),
                    "score": _score(phases[phase], row["taskset"])}
            for phase, round_ in phase_rounds.items()
        }
        arms.append({
            "arm_id": row["arm_id"],
            "block_id": row["block_id"],
            "condition": row["condition"],
            "opening_work": results["pre"],
            "physical_round_one_score": results["pre"]["score"] if opening == 1 else None,
            "post_work": results["post"],
            "terminal_score": row["score"],
        })
    return {**audited, "evidence": "scripted_l5_phase_score_readback", "authorizes_execution": False,
            "scientific_n2_frozen": False, "phase_scores": arms}


def verify_partial(directory, *, index_sha256):
    """Keep matrix-level scoring unavailable on the verified stopped prefix."""
    verified = l5_matrix_partial.verify(directory, index_sha256=index_sha256)
    return {**verified, "evidence": "scripted_l5_phase_score_readback", "authorizes_execution": False,
            "phase_scores": None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    pins = parser.add_mutually_exclusive_group(required=True)
    pins.add_argument("--summary-sha256")
    pins.add_argument("--index-sha256")
    args = parser.parse_args()
    try:
        report = (verify_partial(args.directory, index_sha256=args.index_sha256) if args.index_sha256 is not None
                  else verify(args.directory, summary_sha256=args.summary_sha256))
    except (IndexError, KeyError, OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(report, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
