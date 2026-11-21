"""Audit pinned EP-1 fake floor/oracle receipts without running a model."""

import argparse
import hashlib
import json
from pathlib import Path

from lab import adapter_lineage as files
from murmuration import ep1
from murmuration.trapbench import alloc, alloc2

ARTIFACTS = ("schedule.json", "episodes.jsonl", "final.json")
FAKE_STAMP = "FAKE: loopback fake server; not evidence about any model"


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _read(root, name, pin):
    path = files._path(root, {"path": name})
    raw = path.read_bytes()
    files._match(path, hashlib.sha256(raw).hexdigest(), pin)
    if name.endswith(".jsonl"):
        _require(raw.endswith(b"\n"), "episode receipt has an incomplete JSONL record")
        return [files._strict_object(line, path) for line in raw.splitlines()]
    return files._strict_object(raw, path)


def _audit_control(root, pins, expected_y, seed):
    schedule, rows, final = (_read(root, name, pins[name]) for name in ARTIFACTS)
    plan = ep1.plan("ep1", seed, n_sets=1)
    _require(schedule["kind"] == "ep1" and schedule["dry_run"] is True
             and type(schedule["schedule_seed"]) is int and schedule["schedule_seed"] == seed
             and schedule["plan"] == plan, "bracket schedule differs from the fixed fake EP-1 plan")
    block = plan[0]
    _require(len(block["order"]) == len(ep1.BASE_CONDS) and set(block["order"]) == set(ep1.BASE_CONDS)
             and [row["cond"] for row in rows] == block["order"],
             "bracket must contain each scheduled arm in order")
    _require(final["kind"] == "ep1" and final["stamp"] == FAKE_STAMP and final["episodes"] == len(rows)
             and final["aborts"] == 0 and final["voids"] == dict.fromkeys(ep1.BASE_CONDS, 0)
             and final["ledger"]["batch"] == "ep1" and final["ledger"]["stop_reason"] == "complete",
             "bracket must have a complete, zero-void fake terminal record")
    taskset = alloc.gen(block["set"], block["split"])
    taskset_sha256 = hashlib.sha256(alloc.dumps(taskset).encode()).hexdigest()
    episode_ids = set()
    arms = {}
    for row in rows:
        name = row["cond"]
        identifier = row["episode_id"]
        _require(isinstance(identifier, str) and bool(identifier) and identifier not in episode_ids,
                 "bracket must have distinct nonempty episode IDs within each control")
        episode_ids.add(identifier)
        _require(row["kind"] == row["batch"] == "ep1" and row["arm"] == name and row["stamp"] == FAKE_STAMP
                 and row["instrument_validation"] is True and row["evidence"] == "fake"
                 and row["schedule_seed"] == seed and row["set"] == block["set"]
                 and row["taskset_sha256"] == taskset_sha256 and row["attempt"] == 0
                 and row["ended"] == "complete" and row["valid"] is True and row["void"] is None,
                 f"incomplete or nonfake bracket episode: {name}")
        score = alloc.score(row["log"], taskset)
        second = alloc2.score(row["log"], taskset)
        _require(score["valid"] and second["valid"] and score == row["scores"] == row["scorers"]["alloc"]
                 and second == row["scorers"]["alloc2"] and row["scorers"]["disagreement"] is None
                 and type(row["Y"]) in (float, int) and score["Y"] == second["Y"] == row["Y"] == expected_y,
                 f"bracket scored result differs from the expected control: {name}")
        arms[name] = {"Y": score["Y"], "taskset_sha256": taskset_sha256, "episode_id": identifier}
    return {"pins": pins, "arms": arms}


def audit(bundle, *, floor_pins, oracle_pins, seed=0):
    """Verify synthetic historical control receipts with externally supplied pins."""
    _require(type(seed) is int, "schedule seed must be an integer")
    root = Path(bundle).resolve(strict=True)
    result = {}
    for role, pins, expected in (("floor", floor_pins, ep1.FLOOR_Y), ("oracle", oracle_pins, ep1.ORACLE_Y)):
        _require(set(pins) == set(ARTIFACTS), f"expected complete external pins for {role}")
        directory = root / role / "ep1"
        _require(directory.is_dir() and directory.resolve(strict=True) == directory,
                 f"unsafe control path for {role}")
        result[role] = _audit_control(directory, pins, expected, seed)
    return {"evidence": "historical_fake_bracket", "authorizes_execution": False,
            "pilot4_clearance": None, "schedule_seed": seed, "controls": result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--floor-sha256", required=True, nargs=3, metavar=("SCHEDULE", "EPISODES", "FINAL"))
    parser.add_argument("--oracle-sha256", required=True, nargs=3, metavar=("SCHEDULE", "EPISODES", "FINAL"))
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    try:
        report = audit(args.bundle, floor_pins=dict(zip(ARTIFACTS, args.floor_sha256, strict=True)),
                       oracle_pins=dict(zip(ARTIFACTS, args.oracle_sha256, strict=True)), seed=args.seed)
    except (OSError, KeyError, TypeError, ValueError) as error:
        parser.exit(2, f"fake bracket unavailable or inconsistent: {error}\n")
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
