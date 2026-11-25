"""Defensive quarantine decisions for committed inert scalar observations."""

import re
from unicodedata import normalize


_POST_ID = re.compile(r"p(?:0|[1-9][0-9]*)")


def _receipt(reason, checks):
    return {"admitted": reason == "admitted", "reason": reason, "checks": checks}


def _lineage(items, origins, start, claim, *, forbidden=None):
    seen, visiting, terminal = set(), set(), set()
    positions, edges = {}, []
    stack = [(start, False)]
    while stack:
        item_id, closing = stack.pop()
        if closing:
            visiting.remove(item_id)
            seen.add(item_id)
            continue
        if item_id == forbidden or item_id in visiting:
            return None, "ancestry_circular"
        if item_id in seen:
            continue
        if item_id not in items:
            return None, "ancestry_unavailable"
        item = items[item_id]
        refs, round_id = item.get("refs"), item.get("round")
        if (item.get("id") != item_id or _POST_ID.fullmatch(item_id) is None
                or type(round_id) is not int or round_id < 0
                or type(refs) not in (list, tuple)
                or any(type(parent) is not str or not parent for parent in refs)
                or len(set(refs)) != len(refs)):
            return None, "ancestry_invalid"
        if item.get("text") != claim:
            return None, "claim_mismatch"
        positions[item_id] = (round_id, int(item_id[1:]))
        if not refs:
            leaf = origins.get(item_id)
            if (item.get("kind") != "observation" or type(leaf) is not dict
                    or leaf.keys() != {"origin", "text"} or leaf["text"] != claim
                    or type(leaf["origin"]) is not str or not leaf["origin"]
                    or leaf["origin"] != leaf["origin"].strip()
                    or leaf["origin"] != normalize("NFC", leaf["origin"])):
                return None, "ancestry_invalid"
            terminal.add(leaf["origin"])
        elif item_id in origins or item.get("kind") == "observation":
            return None, "ancestry_invalid"
        visiting.add(item_id)
        stack.append((item_id, True))
        for parent in reversed(refs):
            edges.append((parent, item_id))
            stack.append((parent, False))

    if any(positions[parent][0] >= positions[child][0] or positions[parent][1] >= positions[child][1]
           for parent, child in edges):
        return None, "ancestry_invalid"
    return terminal, None


def decide(items, origins, verified, *, mode, operation, target, support):
    """Decide whether an inert committed claim may be relayed or promoted."""
    if mode not in ("permissive", "verified", "corroborated") or operation not in ("relay", "promotion"):
        raise ValueError("unknown quarantine mode or operation")
    if (type(target) is not str or not target or type(support) not in (list, tuple)
            or any(type(item) is not str or not item for item in support)):
        raise ValueError("target and support must contain Board item IDs")
    if target not in items:
        return _receipt("target_unavailable", 0)
    claim = items[target].get("text")
    if type(claim) is not str:
        raise ValueError("target must carry exact scalar text")
    if mode == "permissive":
        return _receipt("admitted", 0)
    if mode == "verified":
        if target not in verified:
            return _receipt("verification_missing", 1)
        return _receipt("admitted" if verified[target] == claim else "verification_mismatch", 1)
    if not support:
        return _receipt("support_missing", 0)

    target_origins, target_error = _lineage(items, origins, target, claim)
    supporting = [_lineage(items, origins, item, claim, forbidden=target) for item in support]
    checks = len(supporting)
    if len(set(support)) != checks:
        return _receipt("support_duplicate", checks)
    if target_error:
        return _receipt(target_error, checks)
    used = set(target_origins)
    for source_origins, error in supporting:
        if error:
            return _receipt(error, checks)
        if used.intersection(source_origins):
            return _receipt("origin_overlap", checks)
        used.update(source_origins)
    return _receipt("admitted", checks)
