"""Scripted L7 comparator: select one isolated small-team result under one budget."""

import hashlib
import json

from lab import topology

REVIEW_COST = 1
SELECTION_COST = 1


def _bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _digest(value):
    return hashlib.sha256(_bytes(value)).hexdigest()


def _check_plan(fixture, subteams, team_caps, budget, assessment_truth, candidate_rosters):
    if (len(subteams) < 2 or set(subteams) != set(team_caps)
            or any(not isinstance(candidate, str) or not candidate.strip() for candidate in subteams)):
        raise ValueError("declare at least two distinct candidate IDs and matching budget shares")
    if any(type(cap) is not int or cap < topology.UNIT_COST["merge"] for cap in team_caps.values()):
        raise ValueError("each subteam must have a budget covering its terminal merge")
    selection_reserve = len(subteams) * REVIEW_COST + SELECTION_COST
    if type(budget) is not int or sum(team_caps.values()) + selection_reserve > budget:
        raise ValueError("aggregate budget cannot cover fixed shares and selection")
    if candidate_rosters is not None:
        if set(candidate_rosters) != set(subteams) or any(
            not isinstance(roster, (list, tuple)) or not roster or
            any(type(member) is not str or not member or member in ("verifier", "scripted_advisor")
                for member in roster)
            for roster in candidate_rosters.values()
        ):
            raise ValueError("candidate rosters must match the planned subteams")
        members = [member for roster in candidate_rosters.values() for member in roster]
        if len(members) != len(set(members)) or set(members) != set(fixture.observations):
            raise ValueError("candidate rosters must partition the global fixture")
    for candidate, observations in subteams.items():
        roster = topology.WORKERS if candidate_rosters is None else candidate_rosters[candidate]
        if (not roster or set(observations) != set(roster)
                or any(not isinstance(values, dict) or not set(values) <= set(fixture.tasks)
                       or any(type(answer) is not int for answer in values.values())
                       for values in observations.values())):
            raise ValueError("each subteam needs private observations from the common fixture universe")
        if candidate_rosters is not None and any(
            list(observations[worker].items()) != list(fixture.observations[worker].items()) for worker in roster
        ):
            raise ValueError("subteam observations differ from the common fixture inputs")
    if (set(assessment_truth) != set(fixture.tasks)
            or any(type(value) is not int for value in assessment_truth.values())):
        raise ValueError("selection needs a complete arithmetic reference for the task universe")
    return selection_reserve


def _seal(trace):
    """Project checked work into an isolated artifact without names, raw logs, or costs."""
    accepted = {}
    for row in trace:
        if row["kind"] != "verify" or not row["accepted"]:
            continue
        work = trace[row["submission"]]
        accepted[row["event"]] = {"task": work["task"], "answer": work["answer"],
                                  "inputs": [accepted[index]["task"] for index in work["inputs"]]}
    return list(accepted.values())


def _review(artifact, dependencies, assessment_truth):
    passed = set()
    for item in artifact:
        name = item["task"]
        if (item["answer"] == assessment_truth[name] and item["inputs"] == list(dependencies[name])
                and passed.issuperset(item["inputs"])):
            passed.add(name)
    return sorted(passed)


def run(fixture, subteams, *, team_caps, budget, assessment_truth=None, cancel_selection=False,
        candidate_rosters=None):
    """Give every subteam a fixed cap and keep the highest-scoring individual artifact."""
    if type(cancel_selection) is not bool:
        raise ValueError("cancel_selection must be a Boolean")
    reference = ({name: task.expected for name, task in fixture.tasks.items()}
                 if assessment_truth is None else dict(assessment_truth))
    selection_reserve = _check_plan(fixture, subteams, team_caps, budget, reference, candidate_rosters)
    order = list(subteams)
    dependencies = {name: task.requires for name, task in fixture.tasks.items()}
    plan = {"fixture": fixture.name, "candidate_order": order, "budget": budget, "caps": team_caps,
                        "work_tasks": [(name, task.expected, task.requires) for name, task in fixture.tasks.items()],
                        "subteam_inputs": {candidate: _digest({worker: list(values.items())
                                                               for worker, values in subteams[candidate].items()})
                                           for candidate in order},
                        "assessment_sha256": _digest(reference)}
    if candidate_rosters is not None:
        plan["candidate_rosters"] = {candidate: list(members) for candidate, members in candidate_rosters.items()}
    plan_pin = _digest(plan)
    teams, sealed = {}, {}
    for candidate in order:
        # Give each team only its own observations and the public work-path checks.
        local = topology.Fixture(fixture.name, fixture.tasks, subteams[candidate])
        roster = None if candidate_rosters is None else candidate_rosters[candidate]
        result = topology.run(local, "peers", budget=team_caps[candidate], evidence_access="shared", workers=roster)
        trace = result["trace"]
        spent = sum(row["cost"] for row in trace)
        if spent != result["spent"] or not 0 <= spent <= team_caps[candidate] or trace[-1]["kind"] != "merge":
            raise ValueError("subteam receipt does not reconcile to its fixed cap")
        artifact = _seal(trace)
        sealed[candidate] = artifact
        teams[candidate] = {"cap": team_caps[candidate], "spent": spent, "unused": team_caps[candidate] - spent,
                            "trace_sha256": _digest(trace), "trace": trace,
                            "artifact_sha256": _digest(artifact), "artifact": artifact}

    # All artifacts are sealed before selection sees the separate scoring reference.
    reviewed = [{"candidate_id": name, "verified_tasks": _review(sealed[name], dependencies, reference)}
                for name in order]
    selected = None if cancel_selection else max(reviewed, key=lambda row: len(row["verified_tasks"]))
    team_spent = sum(row["spent"] for row in teams.values())
    verification_spent = REVIEW_COST * len(teams)
    selection_spent = 0 if cancel_selection else SELECTION_COST
    spent = team_spent + verification_spent + selection_spent
    return {
        **({"candidate_rosters": plan["candidate_rosters"]} if candidate_rosters is not None else {}),
        "scientific_result": False,
        "status": "incomplete_selection" if cancel_selection else "completed",
        "fixture": fixture.name,
        "candidate_order": order,
        "plan_sha256": plan_pin,
        "assessment_sha256": _digest(reference),
        "teams": teams,
        "reviewed": reviewed,
        "diagnostic_union": sorted({task for row in reviewed for task in row["verified_tasks"]}),
        "selected": selected,
        "selection_receipt": None if selected is None else {
            "plan_sha256": plan_pin, "reviewed_order_sha256": _digest(reviewed),
            "selected_artifact_sha256": teams[selected["candidate_id"]]["artifact_sha256"],
        },
        "utility": None if selected is None else len(selected["verified_tasks"]),
        "accounting": {"budget": budget, "allocated": sum(team_caps.values()) + selection_reserve,
                       "selection_reserved": selection_reserve, "team_spent": team_spent,
                       "verification_spent": verification_spent, "selection_spent": selection_spent,
                       "spent": spent, "unused": budget - spent},
    }


def audit(fixture, subteams, report, *, team_caps, budget, assessment_truth=None, report_sha256=None,
          candidate_rosters=None):
    """Verify an archived receipt against the separately supplied selection plan."""
    if report_sha256 is not None and report_sha256 != _digest(report):
        raise ValueError("parallel selection report digest mismatch")
    if report.get("status") not in ("completed", "incomplete_selection"):
        raise ValueError("unknown parallel selection terminal state")
    expected = run(fixture, subteams, team_caps=team_caps, budget=budget, assessment_truth=assessment_truth,
                   cancel_selection=report["status"] == "incomplete_selection", candidate_rosters=candidate_rosters)
    if _bytes(report) != _bytes(expected):
        raise ValueError("parallel selection report differs from the pinned plan replay")
    return expected


def demo():
    def observations(a=None, b=None):
        return {"a": a or {}, "b": b or {}, "c": {}}

    complementary, redundant, _ = topology.FIXTURES
    fixture_cells = {
        "complementary": (complementary, {"slot-a": observations({"left": 2}, {"join": 7}),
                                         "slot-b": observations({"right": 3})}, False),
        "redundant": (redundant, {"slot-a": observations({"common": 5}),
                                 "slot-b": observations({"common": 5})}, False),
        "completed_zero": (complementary, {"slot-a": observations(), "slot-b": observations()}, False),
        "cancelled": (complementary, {"slot-a": observations({"left": 2}),
                                     "slot-b": observations({"right": 3})}, True),
    }
    report = {}
    for name, (fixture, subteams, cancel) in fixture_cells.items():
        shares = {candidate: 14 for candidate in subteams}
        cell = run(fixture, subteams, team_caps=shares, budget=32, cancel_selection=cancel)
        report[name] = audit(fixture, subteams, cell, team_caps=shares, budget=32, report_sha256=_digest(cell))
    return report


if __name__ == "__main__":
    print(json.dumps(demo(), sort_keys=True, indent=2, allow_nan=False))
