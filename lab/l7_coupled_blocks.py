"""Scripted L7 grouping and one charged round of cross-block summaries."""

import json
import random
import re
import subprocess

from lab import l7_parallel_selection as selection, topology
from murmuration.coupling import coupling

ROSTER = ("a", "b", "c", "d", "e", "f")
CALIBRATION_PAIRS = {("a", "b"): 5, ("c", "d"): 4, ("e", "f"): 3, ("b", "c"): 1}
MODES = ("coupled", "random", "scope")


def digest(value):
    return selection._digest(value)


def calibration_from_git(repo, cutoff, files, *, expected_counts_sha256, max_files=50):
    """Read a pinned complete calibration history and project co-change onto the roster."""
    if not isinstance(cutoff, str) or re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", cutoff) is None:
        raise ValueError("calibration cutoff must be a full immutable commit ID")
    if type(max_files) is not int or max_files < 2 or not files:
        raise ValueError("invalid co-change calibration plan")
    git = ["git", "-C", str(repo)]
    result = subprocess.run([*git, "rev-parse", "--verify", cutoff + "^{commit}"],
                            check=True, capture_output=True, text=True, timeout=10)
    shallow = subprocess.run([*git, "rev-parse", "--is-shallow-repository"],
                             check=True, capture_output=True, text=True, timeout=10)
    if result.stdout.strip() != cutoff or shallow.stdout.strip() != "false":
        raise ValueError("calibration requires the exact commit in a complete history")
    counts = coupling(str(repo), cutoff, max_files=max_files)
    if digest([[left, right, counts[left, right]] for left, right in sorted(counts)]) != expected_counts_sha256:
        raise ValueError("co-change counts differ from the independently pinned calibration export")
    projected = {}
    for (left, right), weight in counts.items():
        a, b = files.get(left), files.get(right)
        if a is not None and b is not None and a != b:
            key = tuple(sorted((a, b)))
            projected[key] = projected.get(key, 0) + weight
    return projected


def partition(roster, pairs, *, block_size=2):
    """Fill fixed-size blocks greedily using positive calibration weights and stable ties."""
    if (type(block_size) is not int or block_size < 1 or not roster or len(roster) % block_size
            or any(not isinstance(worker, str) or not worker for worker in roster) or len(set(roster)) != len(roster)):
        raise ValueError("invalid coupling roster or block size")
    canonical = {}
    for pair, weight in pairs.items():
        if (type(pair) is not tuple or len(pair) != 2 or pair[0] == pair[1]
                or any(member not in roster for member in pair) or type(weight) is not int or weight < 0):
            raise ValueError("invalid calibration pair or co-change weight")
        key = tuple(sorted(pair))
        if key in canonical:
            raise ValueError("ambiguous duplicate coupling pair")
        canonical[key] = weight
    remaining, groups = list(roster), []
    while remaining:
        group = [remaining.pop(0)]
        while len(group) < block_size:
            next_member = max(remaining, key=lambda member: sum(
                canonical.get(tuple(sorted((member, prior))), 0) for prior in group
            ))
            group.append(next_member)
            remaining.remove(next_member)
        groups.append(tuple(group))
    return tuple(groups)


def integrate(summaries, expected_pins, task, *, read_round, task_id="join", observation=7):
    """Admit only earlier independently pinned summaries, then verify the upper work."""
    def blocked(reason):
        return {"verified": False, "task": task_id, "reason": reason}

    if type(read_round) is not int or read_round < 0 or type(observation) is not int:
        return blocked("invalid_upper_request")
    sources, seen = {}, set()
    for summary in summaries:
        if type(summary) is not dict or summary.keys() != {"group", "committed_round", "items"}:
            return blocked("invalid_summary")
        group, round_id, items = (summary[key] for key in ("group", "committed_round", "items"))
        if (not isinstance(group, str) or group in seen or group not in expected_pins
                or type(round_id) is not int or not 0 <= round_id < read_round or type(items) is not list):
            return blocked("untrusted_or_uncommitted_summary")
        seen.add(group)
        local = set()
        for item in items:
            if (type(item) is not dict or item.keys() != {"task", "answer", "proof_sha256"}
                    or not isinstance(item["task"], str) or item["task"] in local or type(item["answer"]) is not int
                    or not isinstance(item["proof_sha256"], str) or re.fullmatch(r"[0-9a-f]{64}", item["proof_sha256"]) is None):
                return blocked("invalid_summary_item")
            local.add(item["task"])
            if item["task"] in task.requires:
                if item["task"] in sources:
                    return blocked("ambiguous_prerequisite")
                sources[item["task"]] = (group, item["answer"], item["proof_sha256"])
        if expected_pins[group] != digest(summary):
            return blocked("untrusted_or_uncommitted_summary")
    if any(name not in sources for name in task.requires):
        return blocked("missing_committed_prerequisite")
    answer = observation + sum(sources[name][1] for name in task.requires)
    return {"verified": answer == task.expected, "task": task_id,
            "reason": "accepted" if answer == task.expected else "wrong_answer", "answer": answer,
            "inputs": [{"task": name, "group": sources[name][0], "proof_sha256": sources[name][2]}
                       for name in task.requires]}


def _summary(group_id, report):
    trace = report["trace"]
    trace_sha = digest(trace)
    outputs = {}
    for row in trace:
        if row["kind"] == "verify" and row["accepted"]:
            work = trace[row["submission"]]
            outputs.setdefault(work["task"], {"task": work["task"], "answer": work["answer"],
                                              "proof_sha256": digest([group_id, trace_sha, work, row])})
    return {"group": group_id, "committed_round": trace[-1]["round"], "items": list(outputs.values())}


def run(groups, *, budget=80, withheld=None):
    if (len(groups) == 0 or any(len(group) != 2 for group in groups)
            or len([worker for group in groups for worker in group]) != len(ROSTER)
            or set(worker for group in groups for worker in group) != set(ROSTER)):
        raise ValueError("blocks must partition the same six worker slots into pairs")
    labels = [f"block-{index}" for index in range(len(groups))]
    if withheld is not None and withheld not in labels:
        raise ValueError("unknown withheld block")
    upper_reserve = len(groups) * 3 + 3  # publish, check, read per block, then work, check, terminal
    if type(budget) is not int or budget - upper_reserve < len(groups):
        raise ValueError("aggregate cap must fund local terminal and summary charges before work")
    base, remainder = divmod(budget - upper_reserve, len(groups))

    tasks = {"left": topology.Task(2), "right": topology.Task(3),
             "left_local": topology.Task(5, ("left",)), "right_local": topology.Task(7, ("right",))}
    observations = {"a": {"left": 2}, "b": {"left_local": 3}, "c": {"right": 3},
                    "d": {"right_local": 4}, "e": {}, "f": {}}
    candidates, summaries = {}, {}
    for position, (group, members) in enumerate(zip(labels, groups, strict=True)):
        fixture = topology.Fixture("l7_public_block", tasks, {worker: observations[worker] for worker in members})
        cap = base + int(position < remainder)
        report = topology.run(fixture, "peers", budget=cap, evidence_access="shared", workers=members)
        candidates[group] = report
        summaries[group] = _summary(group, report)
    pins = {group: digest(summary) for group, summary in summaries.items()}
    read_round = topology.ROUNDS + 1
    upper = integrate([summary for group, summary in summaries.items() if group != withheld], pins,
                      topology.Task(12, ("left", "right")), read_round=read_round)
    performed = "answer" in upper
    transfers = [
        {"group": group, "summary_sha256": pins[group], "committed_round": summaries[group]["committed_round"],
         "read_round": read_round, "read_status": "withheld" if group == withheld else "delivered"}
        for group in labels
    ]
    charge = {"budget": budget, "local": sum(row["spent"] for row in candidates.values()),
              "publish": len(groups), "summary_review": len(groups), "summary_read": len(groups),
              "upper_work": int(performed), "upper_review": int(performed), "terminal": 1}
    charge["spent"] = sum(value for key, value in charge.items() if key != "budget")
    charge["unused"] = budget - charge["spent"]
    if charge["unused"] < 0:
        raise ValueError("group trace or upper cost exceeded the planned cap")
    lower = {item["task"] for summary in summaries.values() for item in summary["items"]}
    return {"groups": groups, "withheld": withheld, "candidates": candidates, "summaries": summaries,
            "summary_pins": pins, "summary_transfers": transfers, "integration": upper, "accounting": charge,
            "verified_task_count": len(lower) + upper["verified"]}


def demo():
    random_order = list(ROSTER)
    random.Random(0).shuffle(random_order)
    orders = {"coupled": partition(ROSTER, CALIBRATION_PAIRS),
              "random": tuple(tuple(random_order[index:index + 2]) for index in range(0, len(ROSTER), 2)),
              "scope": (("a", "c"), ("b", "d"), ("e", "f"))}
    calibration = [[left, right, weight] for (left, right), weight in sorted(CALIBRATION_PAIRS.items())]
    return {"scientific_result": False, "calibration_scope": "predeclared_public_fixture_counts",
            "calibration_sha256": digest(calibration), "calibration_pairs": calibration,
            "arms": {name: run(orders[name]) for name in MODES}, "withheld": run(orders["coupled"], withheld="block-1")}


if __name__ == "__main__":
    print(json.dumps(demo(), sort_keys=True, indent=2))
