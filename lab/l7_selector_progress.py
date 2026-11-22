"""Join public L7 review progress and selector charges to a pinned replay."""

import argparse
import json
from pathlib import Path

from lab.replication_inventory import _hex, _metadata, _object, _require


SCHEMA = "tremor.l7_public_selector_progress.v1"


def _review_progress(reviews, expected, teams):
    _require(type(reviews) is list and len(reviews) <= len(expected), "invalid candidate review prefix")
    charges = []
    for captured, row in zip(reviews, expected):
        _object(captured, ("candidate_id", "artifact_sha256", "verified_tasks", "charge"), "candidate review")
        identity = row["candidate_id"]
        _require(captured["candidate_id"] == identity
                 and captured["artifact_sha256"] == _hex(teams[identity]["artifact_sha256"], 64)
                 and captured["verified_tasks"] == row["verified_tasks"],
                 "candidate review differs from pinned artifact or score")
        charge = captured["charge"]
        _require(charge is None or type(charge) is int and charge == 1, "invalid public review charge")
        charges.append(charge)
    return {"completed_reviews": len(reviews), "scheduled_reviews": len(expected),
            "known_review_cost": sum(value for value in charges if value is not None),
            "review_charges_unavailable": charges.count(None),
            "complete_review_cost": len(reviews) if len(reviews) == len(expected) and None not in charges else None}


def _terminal(capture, expected, fully_reviewed):
    if capture is None:
        return {"terminal": "unavailable", "started": None, "selection_charge": None,
                "selected": None, "utility": None, "utility_unavailable_reason": "missing_selector_observation"}
    _object(capture, ("started", "terminal", "charge", "selected"), "selector progress")
    started, state, charge = (capture[field] for field in ("started", "terminal", "charge"))
    _require(type(started) is bool and (charge is None or type(charge) is int and charge in (0, 1)),
             "invalid selector start or charge")
    _require(not started or fully_reviewed, "selector started before candidate reviews finished")
    chosen = None
    utility = None
    if state == "completed":
        _require(started and charge == 1, "completed selector requires a start and charged selection")
        chosen = expected["selected"]
        utility = expected["utility"]
    elif state == "cancelled_before_start":
        _require(not started and charge == 0, "pre-start cancellation must have zero selection charge")
    elif state == "terminal_unavailable":
        _require(started, "unavailable selector terminal requires an observed start")
    else:
        _require(state == "interrupted_after_start" and started, "invalid interrupted selector terminal")
    _require(capture["selected"] == chosen, "selector terminal differs from verified selection availability")
    return {"terminal": state, "started": started, "selection_charge": charge, "selected": chosen, "utility": utility,
            "utility_unavailable_reason": None if state == "completed" else state}


def verify(replay, witness, *, replay_sha256, witness_sha256):
    """Verify the scripted evidence join without asserting native completion."""
    baseline = _metadata(Path(replay), replay_sha256)
    _require(baseline.get("scientific_result") is False and baseline.get("status") == "completed"
             and type(baseline.get("reviewed")) is list and baseline["reviewed"],
             "a completed public score replay is required")
    expected = baseline["reviewed"]
    for row in expected:
        tasks = row["verified_tasks"]
        _require(type(tasks) is list and all(type(task) is str and task.strip() for task in tasks)
                 and len(tasks) == len(set(tasks)), "verified tasks must be distinct nonempty strings")
    identities = [row["candidate_id"] for row in expected]
    _require(len(identities) == len(set(identities)) and identities == baseline["candidate_order"]
             and baseline["selected"] == max(expected, key=lambda row: len(row["verified_tasks"]))
             and type(baseline["utility"]) is int and baseline["utility"] == len(baseline["selected"]["verified_tasks"]),
             "completed replay score, order or choice differs")
    document = _object(_metadata(Path(witness), witness_sha256),
                       ("schema", "plan_sha256", "replay_sha256", "reviews", "selector"), "selector progress witness")
    _require(document["schema"] == SCHEMA and document["replay_sha256"] == replay_sha256
             and document["plan_sha256"] == _hex(baseline["plan_sha256"], 64),
             "selector witness belongs to a different replay or plan")
    progress = _review_progress(document["reviews"], expected, baseline["teams"])
    terminal = _terminal(document["selector"], baseline, progress["completed_reviews"] == len(expected))
    return {"evidence": "public_scripted_selector_progress", "replay_sha256": replay_sha256,
            "witness_sha256": witness_sha256, **progress, **terminal,
            "native_execution_verified": False, "scientific_acceptance": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("replay", "witness"):
        parser.add_argument(name, type=Path)
        parser.add_argument(f"--{name}-sha256", required=True)
    try:
        result = verify(**vars(parser.parse_args()))
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
