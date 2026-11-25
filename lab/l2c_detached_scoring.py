"""Score locked L2-C selections against detached, inert factual labels."""

from collections import Counter
from fractions import Fraction
import re
from unicodedata import normalize

from lab.l2c_board_features import rank_arms
from lab.l4_measured_compression import pin


ARM_NAMES = ("direct_relays", "outdegree", "retrievals", "recency", "random", "none", "full")
SELECTION_FIELDS = {"scope", "board_head", "board_events", "candidates", "features", "check_budget", "random_seed", "arms"}
FEATURE_FIELDS = {"direct_relays", "outdegree", "retrievals", "posted_round", "posted_seq"}


def _identifier(value):
    return (type(value) is str and bool(value) and value == value.strip()
            and value == normalize("NFC", value))


def _ratio(value):
    return {"numerator": value.numerator, "denominator": value.denominator}


def validate_selection(locked, expected_pin):
    if (type(locked) is not dict or locked.keys() != SELECTION_FIELDS or locked["scope"] != "scripted_l2c_selection"
            or pin(locked) != expected_pin):
        raise ValueError("locked selection differs from its expected pin or scope")
    candidates, budget, arms = (locked[field] for field in ("candidates", "check_budget", "arms"))
    head, events, seed = (locked[field] for field in ("board_head", "board_events", "random_seed"))
    if (type(head) is not str or re.fullmatch(r"[0-9a-f]{64}", head) is None
            or type(events) is not int or events < 1 or type(seed) is not int):
        raise ValueError("invalid Board head, event count or random seed")
    if (type(candidates) is not list or not candidates or any(not _identifier(item) for item in candidates)
            or len(set(candidates)) != len(candidates)):
        raise ValueError("locked selection requires distinct candidate IDs")
    roots = set(candidates)
    if type(budget) is not int or not 0 <= budget <= len(roots):
        raise ValueError("check budget is outside the candidate inventory")
    feature_rows = locked["features"]
    if type(feature_rows) is not dict or feature_rows.keys() != roots or any(
        type(row) is not dict or row.keys() != FEATURE_FIELDS
        or any(type(count) is not int or count < 0 for count in row.values())
        or row["posted_round"] != 0 or not 0 < row["posted_seq"] < events for row in feature_rows.values()
    ):
        raise ValueError("invalid predecision feature inventory")
    if type(arms) is not dict or arms.keys() != set(ARM_NAMES):
        raise ValueError("locked selection requires the exact comparator arms")
    for name, selected in arms.items():
        expected_checks = 0 if name == "none" else len(roots) if name == "full" else budget
        if (type(selected) is not list or len(selected) != expected_checks
                or any(not _identifier(item) or item not in roots for item in selected)
                or len(set(selected)) != len(selected)):
            raise ValueError(f"{name} selection does not match its check budget and candidate inventory")
    if arms != rank_arms(feature_rows, check_budget=budget, seed=seed):
        raise ValueError("locked arms differ from their ranked features")
    return roots, budget, arms


def _outcome_counts(outcomes, roots, expected_pin, board_head):
    if (type(outcomes) is not dict or outcomes.keys() != {"board_head", "labels", "opportunities"}
            or pin(outcomes) != expected_pin):
        raise ValueError("detached outcomes differ from their expected pin or schema")
    if outcomes["board_head"] != board_head:
        raise ValueError("detached outcomes belong to a different Board head")
    labels, opportunities = outcomes["labels"], outcomes["opportunities"]
    if (type(labels) is not dict or labels.keys() != roots
            or any(label not in ("valid", "invalid") for label in labels.values())):
        raise ValueError("detached labels require exact candidate coverage and valid/invalid values")
    if type(opportunities) is not list:
        raise ValueError("detached opportunities must be an ordered list")
    seen = set()
    invalid_counts = Counter()
    for row in opportunities:
        if (type(row) is not dict or row.keys() != {"id", "root"} or not _identifier(row["id"])
                or row["id"] in seen or not _identifier(row["root"]) or row["root"] not in roots):
            raise ValueError("detached opportunity must have a distinct ID and known root")
        seen.add(row["id"])
        if labels[row["root"]] == "invalid":
            invalid_counts[row["root"]] += 1
    return len(seen), invalid_counts


def score(locked, outcomes, *, expected_selection_pin, expected_outcome_pin):
    """Count scripted prevention over an identical opportunity inventory in every arm."""
    roots, budget, arms = validate_selection(locked, expected_selection_pin)
    opportunity_count, invalid_counts = _outcome_counts(outcomes, roots, expected_outcome_pin, locked["board_head"])
    invalid_total = sum(invalid_counts.values())
    valid_total = opportunity_count - invalid_total
    scored = {}
    for name in ARM_NAMES:
        selected = arms[name]
        prevented = sum(invalid_counts[root] for root in selected)
        remaining = invalid_total - prevented
        scored[name] = {
            "checks": len(selected),
            "opportunities": opportunity_count,
            "invalid_uses_remaining": remaining,
            "invalid_uses_prevented": prevented,
            "valid_uses_retained": valid_total,
            "invalid_use_rate": _ratio(Fraction(remaining, opportunity_count)) if opportunity_count else None,
        }

    expected_prevented = Fraction(invalid_total * budget, len(roots))
    return {
        "scope": "scripted_l2c_detached_scoring",
        "scientific_result": False,
        "selection_sha256": expected_selection_pin,
        "outcomes_sha256": expected_outcome_pin,
        "opportunities": opportunity_count,
        "invalid_opportunities": invalid_total,
        "valid_opportunities": valid_total,
        "arms": scored,
        "uniform_random_expectation": {
            "checks": budget,
            "invalid_uses_remaining": _ratio(invalid_total - expected_prevented),
            "invalid_uses_prevented": _ratio(expected_prevented),
        },
    }
