"""Exact bookkeeping for purchased checks in the public L2-C fixture."""

import re

from lab.l4_measured_compression import pin


_SHA256 = re.compile(r"[0-9a-f]{64}")


def _digest(value):
    return type(value) is str and _SHA256.fullmatch(value) is not None


def _identifier(value):
    return type(value) is str and bool(value) and value == value.strip()


def settle(selected, claims, reference, *, context_pin, expected_reference_pin):
    """Record a start and settled result for each purchased check in order."""
    if not _digest(context_pin) or not _digest(expected_reference_pin):
        raise ValueError("screening context and reference require exact SHA-256 pins")
    if type(claims) is not dict or any(
        not _identifier(target) or type(text) is not str for target, text in claims.items()
    ):
        raise ValueError("claims must map local target IDs to exact text")
    if (type(selected) is not list or any(not _identifier(target) or target not in claims for target in selected)
            or len(set(selected)) != len(selected)):
        raise ValueError("selection must be an ordered, unique subset of local targets")
    if (type(reference) is not dict or reference.keys() != claims.keys()
            or any(text is not None and type(text) is not str for text in reference.values())
            or pin(reference) != expected_reference_pin):
        raise ValueError("evaluator reference differs from the pinned target inventory")

    events = []
    for ordinal, target in enumerate(selected):
        claim, observed = claims[target], reference[target]
        identity = {"ordinal": ordinal, "target": target, "claim_sha256": pin(claim),
                    "context_sha256": context_pin}
        if observed is None:
            status = "unavailable"
        else:
            status = "matched" if claim == observed else "mismatch"
        events.extend((
            {**identity, "seq": 2 * ordinal, "event": "start"},
            {**identity, "seq": 2 * ordinal + 1, "event": "settle", "status": status, "used_checks": 1},
        ))
    return {
        "scope": "scripted_l2c_screening_ledger",
        "context_sha256": context_pin,
        "reference_sha256": expected_reference_pin,
        "claims_sha256": pin(claims),
        "selected": list(selected),
        "events": events,
        "checks": len(selected),
    }


def verify(ledger, selected, claims, reference, *, context_pin, expected_reference_pin, expected_ledger_pin):
    """Recover statuses only after a complete replay against independent pins."""
    expected = settle(selected, claims, reference, context_pin=context_pin,
                      expected_reference_pin=expected_reference_pin)
    if (type(ledger) is not dict or not _digest(expected_ledger_pin)
            or pin(expected) != expected_ledger_pin or pin(ledger) != expected_ledger_pin):
        raise ValueError("screening ledger differs from the independently pinned replay")
    return {event["target"]: event["status"] for event in expected["events"] if event["event"] == "settle"}
