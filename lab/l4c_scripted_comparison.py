"""Matched development operations for verified replay, writes and search."""

from dataclasses import dataclass
from fractions import Fraction
import json

from murmuration import night

from lab.l4_adaptive_replay_control import replay_day
from lab.l4c_scripted_ledger import audit
from lab.l4c_scripted_scoring import score
from lab.l4c_scripted_verify import plan_pin, verify


ARMS = ("replay", "write_only", "search")


@dataclass(frozen=True)
class Task:
    id: str
    source: str
    candidates: tuple[str, ...]


@dataclass(frozen=True)
class Day:
    revisions: tuple[tuple[str, int, str], ...]
    arrivals: tuple[tuple[str, str, str], ...]
    tasks: tuple[Task, ...]


def _check_plan(days, cap):
    if type(cap) is not int or cap < 0 or not days:
        raise ValueError("nonnegative development cap and at least one day required")
    note_ids, task_ids, versions = set(), set(), {}
    for plan in days:
        revised = set()
        for source, version, _ in plan.revisions:
            if source in revised or type(version) is not int or version != versions.get(source, 0) + 1:
                raise ValueError("source revisions must advance in unique boundary order")
            versions[source] = version
            revised.add(source)
        for note, _, _ in plan.arrivals:
            if note in note_ids:
                raise ValueError("duplicate note opportunity")
            note_ids.add(note)
        for task in plan.tasks:
            if task.id in task_ids:
                raise ValueError("duplicate task opportunity")
            task_ids.add(task.id)


def _actor_day(*, arm, day, plan, store, active, versions, cap):
    operations = []
    gate_status = "search_without_memory"
    if arm != "search":
        arrivals = []
        for note, text, source in plan.arrivals:
            arrivals = night.add_note(arrivals, note, text, "scripted-worker", day, (source,),
                                      authored_source_version=versions.get(source))
        candidates = [*store, *arrivals] if arm == "replay" else arrivals
        rewrite = arm == "replay"
        # Reserve the maximum whole-gate cost. No partially checked night is accepted.
        required = len(candidates) * (1 + rewrite)
        if required <= cap:
            result = replay_day(candidates, day=day, source_prefix=active, strength=int(rewrite), seed=17 + day)
            for kind in ("source_check", "rewrite_check"):
                for row in result[f"{kind}s"]:
                    operations.append({"kind": kind, "subject": row["note_id"], "outcome": row["disposition"]})
            store = result["store"] if rewrite else [*store, *result["store"]]
            gate_status = "completed"
        else:
            gate_status = "budget_withheld"

    submissions = dict.fromkeys(task.id for task in plan.tasks)
    for task in plan.tasks:
        if gate_status == "budget_withheld":
            break
        if arm == "search":
            for source in task.candidates:
                if len(operations) >= cap:
                    break
                answer = active.get(source)
                operations.append({"kind": "search_read", "subject": f"{task.id}/{source}",
                                   "outcome": "missing" if answer is None else "returned"})
                if answer is not None:
                    submissions[task.id] = answer
                    break
        elif len(operations) < cap:
            answer = next((note["text"] for note in reversed(store) if note["sources"] == [task.source]), None)
            operations.append({"kind": "memory_lookup", "subject": task.id,
                               "outcome": "missing" if answer is None else "returned"})
            submissions[task.id] = answer
    return {"day": day, "arm": arm, "operations": operations, "spent": len(operations),
            "unused": cap - len(operations), "gate_status": gate_status,
            "resident": store, "submissions": submissions}


def execute(days, *, cap):
    """Execute and retain actor traces before any evaluator truth is available."""
    days = tuple(days)
    _check_plan(days, cap)
    active, versions, records, history = {}, {}, [], []
    stores = {arm: [] for arm in ARMS}
    for day, plan in enumerate(days, 1):
        history.append({"day": day, "revisions": list(plan.revisions)})
        for source, version, text in plan.revisions:
            active[source], versions[source] = text, version
        for arm in ARMS:
            row = _actor_day(arm=arm, day=day, plan=plan, store=stores[arm], active=active, versions=versions, cap=cap)
            stores[arm] = row["resident"]
            records.append(row)
    return {"records": records, "raw_source_revisions": history, "plan_sha256": plan_pin(days, cap=cap)}


def _ratio(numerator, denominator):
    if not denominator:
        return None
    exact = Fraction(numerator, denominator)
    return {"numerator": exact.numerator, "denominator": exact.denominator}


def evaluate(execution, days, *, truth_by_day, cap):
    """Grade settled receipts using detached close-day truth and verify accounting."""
    days = tuple(days)
    verify(execution, days, cap=cap)
    records = execution["records"]
    meter_fields = ("day", "arm", "operations", "spent", "unused")
    meter = audit(({field: row[field] for field in meter_fields} for row in records), cap=cap)
    if meter["days"] != len(days) or len(truth_by_day) != len(days):
        raise ValueError("assessment windows differ from execution schedule")
    scored = []
    for row in records:
        index = row["day"] - 1
        result = score(tasks=[(task.id, task.source) for task in days[index].tasks], submissions=row["submissions"],
                       resident=row["resident"], truth=truth_by_day[index])
        resident, task = result["resident_counts"], result["task_counts"]
        scored.append({"day": row["day"], "arm": row["arm"], **result,
                       "false_share": (_ratio(resident["false"], len(row["resident"]))
                                       if not resident["unknown_truth"] else None),
                       "units_per_pass": _ratio(row["spent"], task["passed"]) if not task["unknown_truth"] else None})
    totals = {}
    for arm in ARMS:
        spent = sum(row["spent"] for row in records if row["arm"] == arm)
        passed = sum(row["task_counts"]["passed"] for row in scored if row["arm"] == arm)
        unknown = sum(row["task_counts"]["unknown_truth"] for row in scored if row["arm"] == arm)
        totals[arm] = {"spent": spent, "passed": passed, "unknown_truth": unknown,
                       "units_per_pass": _ratio(spent, passed) if not unknown else None}
    return {"meter": meter, "scored": scored, "totals": totals}


def fixture(*, revise):
    after = "valve was open" if revise else "valve was shut"
    return (
        Day((("valve", 1, "valve was shut"), ("flow", 1, "flow was steady"), ("state", 1, "state was ready")),
            (("valve-note", "valve was shut", "valve"), ("flow-note", "flow was steady", "flow"),
             ("bad-note", "state was missing", "state")),
            (Task("day1-valve", "valve", ("not-available", "valve")), Task("day1-flow", "flow", ("flow",)))),
        Day((("valve", 2, after),) if revise else (), (),
            (Task("day2-valve", "valve", ("not-available", "valve")), Task("day2-flow", "flow", ("flow",)))),
    ), ({"valve": "valve was shut", "flow": "flow was steady", "state": "state was ready"},
        {"valve": after, "flow": "flow was steady", "state": "state was ready"})


def demo():
    cap = 8
    cases = {}
    for revise in (True, False):
        days, truth = fixture(revise=revise)
        execution = execute(days, cap=cap)
        cases["source_revised" if revise else "unchanged_source"] = {
            "execution": execution, "assessment": evaluate(execution, days, truth_by_day=truth, cap=cap),
        }
    return {"scope": "scripted_development", "scientific_result": False,
            "development_units_per_day_cap": cap, "cases": cases}


if __name__ == "__main__":
    print(json.dumps(demo(), indent=2, sort_keys=True, allow_nan=False))
