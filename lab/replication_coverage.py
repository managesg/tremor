"""Report outcome and resource coverage for matched replication schedules."""

import argparse
import json
from pathlib import Path

from lab import replication_pairing as pairing
from lab.replication_inventory import _hex, _metadata, _object, _require


SCHEMA = "replication_pair_coverage_v1"
LIMIT_SCHEMA = "replication_pair_limits_v1"
CUMULATIVE_LIMIT_SCHEMA = "replication_cumulative_limits_v1"
EXECUTION_SCHEMA = "replication_execution_observation_v1"
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


def _cumulative_scope(limits, allowed, receipts):
    _require(type(limits) is dict and limits.keys() <= set(allowed), "invalid cumulative resource limits")
    report = {}
    for resource, cap in limits.items():
        _require(type(cap) is int and cap >= 0, "invalid cumulative resource limit")
        known = sum(row[resource]["known_subtotal"] for row in receipts)
        unavailable = sum(row[resource]["unavailable_records"] for row in receipts)
        if known > cap:
            status = "exceeded"
        elif unavailable:
            status = "unavailable"
        else:
            status = "within_limit"
        report[resource] = {"limit": cap, "known_subtotal": known, "unavailable_records": unavailable,
                            "complete_total": None if unavailable else known, "status": status}
    return report


def _cumulative_limits(witness, line, pins, totals):
    """Sum supplied assignment receipts. Shared work and charges need separate attribution."""
    document = _metadata(Path(witness[0]), witness[1])
    _object(document, ("schema", "line", "schedule_pins", "line_limits", "role_limits"), "cumulative limits")
    _require(document["schema"] == CUMULATIVE_LIMIT_SCHEMA and document["line"] == line
             and document["schedule_pins"] == pins, "cumulative limits refer to different pairing evidence")
    by_role = _object(document["role_limits"], totals.keys(), "cumulative limit roles")
    line_receipts = [usage for role in totals.values() for usage in role.values()]
    line_limits = _cumulative_scope(document["line_limits"], ("calls", "gpu_wall_ns"), line_receipts)
    role_limits = {role: _cumulative_scope(limits, RESOURCES, list(totals[role].values()))
                   for role, limits in by_role.items()}
    _require(line_limits or any(role_limits.values()), "expected at least one cumulative resource limit")
    return {"limits_sha256": witness[1], "line": line_limits, "by_role": role_limits}


def _execution_observation(witness, paired, coverage_pin, rows, roles):
    bindings = paired.get("scheduled_snapshot_binding")
    _require(bindings is not None, "execution observation requires snapshot-bound schedules")
    document = _metadata(Path(witness[0]), witness[1])
    _object(document, ("schema", "line", "schedule_pins", "coverage_sha256", "executions"), "execution observation")
    _require(document["schema"] == EXECUTION_SCHEMA and document["line"] == paired["line"]
             and document["schedule_pins"] == paired["manifest_sha256"]
             and document["coverage_sha256"] == coverage_pin, "execution observation refers to different coverage")
    _require(type(document["executions"]) is list, "invalid execution observations")
    seen, attempts, captures = set(), set(), set()
    counts = {role: {arm: {"observed": 0, "stopped": 0, "void": 0}
                     for arm in ARMS} for role in roles}
    for event in document["executions"]:
        _object(event, ("task_id", "replicate_id", "role", "arm", "state", "attempt_id",
                        "observer_capture_sha256", "snapshot"), "execution row")
        key = tuple(pairing._identifier(event[field]) for field in ("task_id", "replicate_id"))
        role, arm, state = (pairing._identifier(event[field]) for field in ("role", "arm", "state"))
        _require(key in rows and role in bindings and arm in ARMS, "execution row has no scheduled arm")
        attempt = pairing._identifier(event["attempt_id"])
        capture = _hex(event["observer_capture_sha256"], 64)
        assignment = key, role, arm
        _require(assignment not in seen and attempt not in attempts and capture not in captures,
                 "execution observation reuses an assignment, attempt or capture")
        _require(state != "unavailable" and state == rows[key][role][arm]["state"],
                 "execution state differs from coverage or has no terminal")
        _require(event["snapshot"] == bindings[role], "observed checkpoint differs from scheduled snapshot")
        seen.add(assignment)
        attempts.add(attempt)
        captures.add(capture)
        counts[role][arm][state] += 1

    missing = dict.fromkeys(("stopped", "void", "unavailable"), 0)
    for key, records in rows.items():
        for role, arms in records.items():
            for arm, record in arms.items():
                if (key, role, arm) not in seen:
                    state = record["state"]
                    _require(state != "observed", "an observed arm is missing its execution observation")
                    missing[state] += 1
    return {"evidence": "matched_independently_pinned_observer_declarations",
            "observation_sha256": witness[1], "matched_terminal_rows": len(seen), "by_role_and_arm": counts,
            "without_terminal_observation_by_state": missing, "native_execution_verified": False}


def verify(*, line, splits, unchanged, recalibrated, coverage, reference=None, limits=None, cumulative_limits=None,
           inventory=None, execution_observation=None):
    """Verify exact joins and report coverage without selecting a scientific estimand."""
    paired = pairing.verify(line=line, splits=splits, unchanged=unchanged, recalibrated=recalibrated,
                            reference=reference, inventory=inventory)
    pins = paired["manifest_sha256"]
    declared = _metadata(Path(coverage[0]), coverage[1])
    _object(declared, ("schema", "line", "schedule_pins", "rows"), "replication coverage witness")
    _require(declared["schema"] == SCHEMA and declared["line"] == line and declared["schedule_pins"] == pins,
             "coverage refers to different pairing evidence")
    inventory = _metadata(Path(splits[0]), splits[1])
    task_splits = pairing._splits(inventory)
    group_by_task = {row["task_id"]: row["group_id"] for row in inventory["members"]}
    schedule = pairing._schedule(_metadata(Path(unchanged[0]), unchanged[1]), role="unchanged",
                                 line=line, task_splits=task_splits,
                                 snapshot=paired.get("scheduled_snapshot_binding", {}).get("unchanged"))
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
    if cumulative_limits is not None:
        report["cumulative_limits"] = _cumulative_limits(cumulative_limits, line, pins, totals)
    if execution_observation is not None:
        report["execution_observation"] = _execution_observation(execution_observation, paired, coverage[1], rows,
                                                                roles)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--line", choices=pairing.LINES, required=True)
    for name in ("splits", "unchanged", "recalibrated", "coverage", "reference"):
        parser.add_argument(f"--{name}", nargs=2, metavar=("PATH", "SHA256"), required=name != "reference")
    parser.add_argument("--limits", nargs=2, metavar=("PATH", "SHA256"),
                        help="independently pinned per-assignment limits shared by both arms of each role and block")
    parser.add_argument("--cumulative-limits", nargs=2, metavar=("PATH", "SHA256"),
                        help="independently pinned limits on total declared usage by line and role")
    parser.add_argument("--inventory", nargs=2, metavar=("PATH", "SHA256"),
                        help="independently pinned structural inventory for snapshot-bound schedules")
    parser.add_argument("--execution-observation", nargs=2, metavar=("PATH", "SHA256"),
                        help="independently pinned execution observations for covered arms")
    try:
        result = verify(**vars(parser.parse_args()))
    except (OSError, ValueError, TypeError, KeyError) as error:
        parser.error(str(error))
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
