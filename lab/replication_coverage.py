"""Report outcome and resource coverage for matched replication schedules."""

import argparse
import json
from pathlib import Path

from lab import replication_pairing as pairing
from lab.replication_inventory import _metadata, _object, _require


SCHEMA = "replication_pair_coverage_v1"
LIMIT_SCHEMA = "replication_pair_limits_v1"
ARMS = ("technique", "comparator")
STATES = ("observed", "stopped", "void", "unavailable")
RESOURCES = ("calls", "input_tokens", "output_tokens", "gpu_wall_ns")


def _components(schedule, group_by_task):
    """Keep clusters connected by any common block, custody group or exact task input."""
    parents = {key: key for key in schedule}

    def root(key):
        while parents[key] != key:
            parents[key] = parents[parents[key]]
            key = parents[key]
        return key

    first = {}
    for key, (block, task_input, *_) in sorted(schedule.items()):
        task = key[0]
        for identity in (("block", block), ("group", group_by_task[task]), ("task_input", task_input)):
            representative = root(first.setdefault(identity, key))
            parents[root(key)] = representative
    groups = {}
    for key in sorted(schedule):
        groups.setdefault(root(key), []).append(key)
    return sorted(groups.values())


def _tally(totals, usage):
    _object(usage, RESOURCES, "declared usage")
    for resource, value in usage.items():
        _require(value is None or type(value) is int and value >= 0, "usage must be nonnegative or unavailable")
        tally = totals[resource]
        if value is None:
            tally["unavailable_records"] += 1
        else:
            tally["known_subtotal"] += value


def _coverage(rows, schedule, roles):
    result = {}
    totals = {
        role: {arm: {dimension: {"known_subtotal": 0, "unavailable_records": 0} for dimension in RESOURCES}
               for arm in ARMS}
        for role in roles
    }
    _require(type(rows) is list, "invalid coverage rows")
    for row in rows:
        _object(row, ("task_id", "replicate_id", "roles"), "coverage row")
        key = tuple(pairing._identifier(row[field]) for field in ("task_id", "replicate_id"))
        _require(key in schedule and key not in result, "extra or repeated coverage assignment")
        role_receipts = _object(row["roles"], roles, "coverage roles")
        for role, arms in role_receipts.items():
            _object(arms, ARMS, "within-role coverage arms")
            for arm, record in arms.items():
                _object(record, ("state", "usage"), "arm receipt")
                _require(record["state"] in STATES, "invalid observed outcome state")
                _tally(totals[role][arm], record["usage"])
        result[key] = role_receipts
    _require(result.keys() == schedule.keys(), "coverage must retain every matched assignment")
    for arms in totals.values():
        for usage in arms.values():
            for tally in usage.values():
                tally["complete_total"] = None if tally["unavailable_records"] else tally["known_subtotal"]
    return result, totals


def _limits(witness, line, pins, roles, schedule):
    document = _metadata(Path(witness[0]), witness[1])
    _object(document, ("schema", "line", "schedule_pins", "per_assignment_limits"), "replication limits")
    _require(document["schema"] == LIMIT_SCHEMA and document["line"] == line and document["schedule_pins"] == pins,
             "limits refer to different pairing evidence")
    by_role = _object(document["per_assignment_limits"], roles, "limit roles")
    blocks = {entry[0] for entry in schedule.values()}
    for per_block in by_role.values():
        _object(per_block, blocks, "limit blocks")
        for limits in per_block.values():
            _require(type(limits) is dict and limits and limits.keys() <= set(RESOURCES), "invalid resource limits")
            _require(all(type(limit) is int and limit >= 0 for limit in limits.values()), "invalid resource limit")
    return by_role


def _limit_result(record, limits):
    usage = record["usage"]
    exceeded = sorted(name for name, cap in limits.items() if usage[name] is not None and usage[name] > cap)
    unavailable = sorted(name for name in limits if usage[name] is None)
    return {"exceeded": exceeded, "unavailable": unavailable,
            "eligible": record["state"] == "observed" and not exceeded and not unavailable}


def verify(*, line, splits, unchanged, recalibrated, coverage, reference=None, limits=None):
    """Verify exact joins and report coverage without selecting a scientific estimand."""
    paired = pairing.verify(line=line, splits=splits, unchanged=unchanged, recalibrated=recalibrated,
                            reference=reference)
    pins = paired["manifest_sha256"]
    declared = _metadata(Path(coverage[0]), coverage[1])
    _object(declared, ("schema", "line", "schedule_pins", "rows"), "replication coverage witness")
    _require(declared["schema"] == SCHEMA and declared["line"] == line and declared["schedule_pins"] == pins,
             "coverage refers to different pairing evidence")
    inventory = _metadata(Path(splits[0]), splits[1])
    task_splits = pairing._splits(inventory)
    group_by_task = {row["task_id"]: row["group_id"] for row in inventory["members"]}
    schedule = pairing._schedule(_metadata(Path(unchanged[0]), unchanged[1]), role="unchanged",
                                 line=line, task_splits=task_splits)
    roles = tuple(role for role in pins if role != "splits")
    rows, totals = _coverage(declared["rows"], schedule, roles)
    limits_by_role = _limits(limits, line, pins, roles, schedule) if limits is not None else None
    clusters = []
    for members in _components(schedule, group_by_task):
        complete = {
            role: sum(all(record["state"] == "observed" for record in rows[key][role].values()) for key in members)
            for role in roles
        }
        cluster = {
            "assignments": [{"task_id": task, "replicate_id": replicate, "receipts": rows[task, replicate]}
                            for task, replicate in members],
            "complete_pairs": complete,
            "all_declared_roles_observed": all(count == len(members) for count in complete.values()),
        }
        if limits_by_role is not None:
            eligible_pairs = dict.fromkeys(roles, 0)
            for key, assignment in zip(members, cluster["assignments"], strict=True):
                block = schedule[key][0]
                checks = {}
                for role, receipts in rows[key].items():
                    checks[role] = {arm: _limit_result(record, limits_by_role[role][block])
                                    for arm, record in receipts.items()}
                    eligible_pairs[role] += all(result["eligible"] for result in checks[role].values())
                assignment["per_assignment_limit_checks"] = checks
            cluster["observed_pairs_within_limits"] = eligible_pairs
        clusters.append(cluster)
    report = {
        "evidence": "declared_replication_coverage",
        "coverage_sha256": coverage[1],
        "pairing": paired,
        "linked_clusters": clusters,
        "declared_roles": roles,
        "clusters_with_all_declared_pairs_observed": sum(
            cluster["all_declared_roles_observed"] for cluster in clusters
        ),
        "usage_by_role_and_arm": totals,
        "scientific_acceptance": False,
    }
    if limits is not None:
        report["per_assignment_limits_sha256"] = limits[1]
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--line", choices=pairing.LINES, required=True)
    for name in ("splits", "unchanged", "recalibrated", "coverage", "reference"):
        parser.add_argument(f"--{name}", nargs=2, metavar=("PATH", "SHA256"), required=name != "reference")
    parser.add_argument("--limits", nargs=2, metavar=("PATH", "SHA256"),
                        help="independently pinned per-assignment limits shared by both arms of each role and block")
    try:
        result = verify(**vars(parser.parse_args()))
    except (OSError, ValueError, TypeError, KeyError) as error:
        parser.error(str(error))
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
