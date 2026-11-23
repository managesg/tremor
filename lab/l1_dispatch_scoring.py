"""Join verified scripted L1 dispatch records to an independent public label file."""

from pathlib import Path
from unicodedata import normalize

from lab import adapter_lineage, l1_dispatch_audit


CATEGORIES = ("selected_resolved", "selected_unresolved", "unallocated")
ATTEMPT_FIELDS = ("attempt_index", "action", "ordinal", "status", "result")


def _fields(record, fields):
    if type(record) is not dict or record.keys() != set(fields.split()):
        raise ValueError("unexpected public claim label fields")


def _identifier(value):
    if type(value) is not str or not value or value != value.strip() or value != normalize("NFC", value):
        raise ValueError("public label IDs must be nonempty and canonical")
    return value


def _labels(path, pin, cohort, inventory_pin, claims):
    document = adapter_lineage._json(Path(path), pin)
    _fields(document, "schema cohort claim_inventory_sha256 labels")
    if document["schema"] != "l1_public_claim_labels_v1":
        raise ValueError("unknown public claim label schema")
    if _identifier(document["cohort"]) != _identifier(cohort):
        raise ValueError("public label cohort differs from the expected cohort")
    if document["claim_inventory_sha256"] != inventory_pin:
        raise ValueError("public labels do not bind the planned claim inventory")
    rows = document["labels"]
    if type(rows) is not list or len(rows) != len(claims):
        raise ValueError("public labels need exact claim coverage")
    by_claim, cases = {}, set()
    for row in rows:
        _fields(row, "claim_id case_id source_id legitimate")
        claim_id, case_id = row["claim_id"], _identifier(row["case_id"])
        if type(claim_id) is not str or not claim_id:
            raise ValueError("invalid public claim identifier")
        _identifier(row["source_id"])
        if claim_id in by_claim or case_id in cases:
            raise ValueError("public label claim and case IDs must be unique")
        if type(row["legitimate"]) is not bool:
            raise ValueError("public label legitimacy must be Boolean")
        by_claim[claim_id] = row
        cases.add(case_id)
    if set(by_claim) != {claim.identifier for claim in claims}:
        raise ValueError("public labels need exact claim coverage")
    return by_claim


def _decision(claim, attempts):
    if not attempts:
        return "unallocated", claim.claimed_complete
    if any(attempt["status"] != "answered" for attempt in attempts):
        return "selected_unresolved", None
    votes = [attempt["result"] for attempt in attempts]
    if attempts[0]["action"] == "check":
        return "selected_resolved", votes[0]
    votes.append(claim.claimed_complete)
    return "selected_resolved", sum(votes) * 2 > len(votes)


def score(plan, claims, journal, labels, *, plan_sha256, journal_sha256, labels_sha256, expected_cohort):
    """Score only settled responses, preserving planned-but-unanswered claim decisions."""
    claims = tuple(claims)
    dispatch = l1_dispatch_audit.audit(plan, claims, journal, plan_sha256=plan_sha256, journal_sha256=journal_sha256)
    inventory_pin = plan["claim_inventory_sha256"]
    by_claim = _labels(labels, labels_sha256, expected_cohort, inventory_pin, claims)

    attempts_by_claim = {claim.identifier: [] for claim in claims}
    for attempt in dispatch["attempts"]:
        attempts_by_claim[attempt["claim_id"]].append({field: attempt[field] for field in ATTEMPT_FIELDS})
    counts = {category: dict.fromkeys(("claims", "known_false_completions", "legitimate_rejections",
                                       "unknown_legitimate", "unknown_illegitimate"), 0)
              for category in CATEGORIES}
    results = []
    for claim in claims:
        attempts = attempts_by_claim[claim.identifier]
        category, completion = _decision(claim, attempts)
        row = by_claim[claim.identifier]
        legitimate = row["legitimate"]
        tally = counts[category]
        tally["claims"] += 1
        tally["known_false_completions"] += completion is True and not legitimate
        tally["legitimate_rejections"] += completion is False and legitimate
        tally["unknown_legitimate"] += completion is None and legitimate
        tally["unknown_illegitimate"] += completion is None and not legitimate
        results.append({**row, "category": category, "completion": completion, "attempts": attempts})
    return {
        "status": "scored_public_dispatch", "dispatch_status": dispatch["status"], "dispatch_reason": dispatch["reason"],
        "cohort": expected_cohort, "plan_sha256": plan_sha256, "journal_sha256": journal_sha256,
        "labels_sha256": labels_sha256, "claim_inventory_sha256": inventory_pin,
        "counts": counts, "claims": results, "scientific_rate": None,
    }
