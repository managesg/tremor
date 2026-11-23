"""Replay an R3 matched schedule with the CPU-only L2 or L5 fixtures."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from time import monotonic_ns

from murmuration.manifest import config_hash
from lab import l2_adoption_control, l5_carrier_fixture, r3_schedule


def _fixture_conditions(line):
    if line == "L2":
        return {name: (name,) for name in l2_adoption_control.CONDITIONS}
    if line == "L5":
        return {f"{carrier}:{state}": (carrier, disrupted)
                for carrier in l5_carrier_fixture.CARRIERS
                for state, disrupted in (("clean", False), ("disrupted", True))}
    raise ValueError("scripted replay supports L2 or L5")


def _utc():
    return datetime.now(timezone.utc).isoformat()


def _run_arm(line, path, args):
    if line == "L2":
        result = l2_adoption_control.run(path, *args)
        keys = ("exposure_denominator", "scored_decisions", "adoption_count", "adoption_rate",
                "first_generation_counts", "eligible_without_scored_decision")
        return {"board_head": result["trace"][-1]["hash"], **{key: result[key] for key in keys}}
    result = l5_carrier_fixture.run(path, *args)
    keys = ("board_head", "carrier_reads", "carrier_bytes_read", "pre_replacement", "post_replacement")
    return {"distinct_passing": result["score"]["distinct_passing"], **{key: result[key] for key in keys}}


def replay(inventory, *, stop_after=None):
    """Return the observed arm prefix and structural block completion."""
    line = inventory["line"]
    fixtures = _fixture_conditions(line)
    schedule = r3_schedule.plan(inventory["conditions"], inventory["blocks"], seed=inventory["seed"])
    if set(schedule["conditions"]) - fixtures.keys():
        raise ValueError(f"condition absent from the {line} scripted fixture")
    total = len(schedule["conditions"]) * len(schedule["blocks"])
    if stop_after is not None and (type(stop_after) is not int or not 0 <= stop_after <= total):
        raise ValueError("stop_after must be an arm count within the schedule")
    limit = total if stop_after is None else stop_after

    begun_utc, start_ns = _utc(), monotonic_ns()
    blocks, observed = [], []
    failure = None
    with TemporaryDirectory(prefix="tremor-r3-replay-") as scratch:
        for block in schedule["blocks"]:
            rows = []
            for condition in block["order"]:
                if failure is not None or len(observed) == limit:
                    break
                arm_start_utc, arm_start_ns = _utc(), monotonic_ns()
                # The board path is constructed from the event index, not from labels.
                path = Path(scratch) / f"arm-{len(observed)}.jsonl"
                arm = {"block_id": block["block_id"], "condition": condition}
                try:
                    readout = _run_arm(line, path, fixtures[condition])
                except Exception as error:  # fixture errors are retained, and later arms are never attempted
                    failure = {**arm, "error_type": type(error).__name__, "start_utc": arm_start_utc,
                               "finish_utc": _utc(), "start_offset_ns": arm_start_ns - start_ns,
                               "finish_offset_ns": monotonic_ns() - start_ns}
                    break
                row = {**arm, "readout": readout}
                observed.append(row)
                rows.append({**row, "start_utc": arm_start_utc, "finish_utc": _utc(),
                             "start_offset_ns": arm_start_ns - start_ns, "finish_offset_ns": monotonic_ns() - start_ns})
            if failure is not None and failure["block_id"] == block["block_id"]:
                status = "failed"
            else:
                status = "complete" if len(rows) == len(block["order"]) else "partial" if rows else "unstarted"
            blocks.append({**block, "status": status, "observed": rows, "missing": block["order"][len(rows):]})
    # Reaching this point confirms the CPU scratch directory was cleaned up.
    return {"mode": "scripted_cpu", "line": line, "schedule_sha256": config_hash(schedule),
            "readouts_sha256": config_hash(observed), "schedule": schedule, "blocks": blocks,
            "complete_blocks": [row["block_id"] for row in blocks if row["status"] == "complete"],
            "attempted_arms": len(observed) + (failure is not None), "scored_arms": len(observed), "planned_arms": total,
            "stop": "fixture_error" if failure else "completed" if len(observed) == total else "scripted_stop",
            "failed_arm": failure,
            "start_utc": begun_utc, "cleanup_utc": _utc(), "observed_wall_ns": monotonic_ns() - start_ns,
            "cleanup_confirmed": True, "gpu_hours": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inventory", type=Path)
    parser.add_argument("--stop-after", type=int, help="simulate a stop after this many fixture arms")
    args = parser.parse_args()
    try:
        output = replay(json.loads(args.inventory.read_bytes()), stop_after=args.stop_after)
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(output, indent=2, sort_keys=True))
    return int(output["stop"] != "completed")


if __name__ == "__main__":
    raise SystemExit(main())
