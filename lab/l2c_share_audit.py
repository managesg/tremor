"""Independent count reconciliation for the inert L2-C verification-share fixture."""


_CONDITIONS = ("unavailable", "restored")
_STATUSES = ("matched", "mismatch", "unavailable")
ORDERINGS = ("direct_relays", "outdegree", "retrievals", "recency", "random")
_COUNTERS = (
    "checks", "cached_lookups", "reads", "read_hits", "attempts", "committed",
    "invalid_admitted", "invalid_refused", "valid_admitted", "valid_refused",
)
_ROW_FIELDS = {"condition", "arm", "selected", "settlements", *_COUNTERS}
_OBJECTIVES = ("checks", "invalid_admitted", "valid_refused")


def _identifier(value):
    return type(value) is str and bool(value) and value == value.strip()


def _nonnegative(value):
    return type(value) is int and value >= 0


def _target_inventory(orders):
    if type(orders) is not dict or orders.keys() != set(ORDERINGS):
        raise ValueError("the complete five-arm ranking inventory is required")
    inventory = None
    for arm, order in orders.items():
        if (not _identifier(arm) or type(order) not in (list, tuple) or not order
                or any(not _identifier(target) for target in order) or len(set(order)) != len(order)):
            raise ValueError("each arm needs distinct ordered target IDs")
        if inventory is None:
            inventory = set(order)
        if set(order) != inventory:
            raise ValueError("each arm must rank the same target inventory")
    return inventory


def _account(row, target_count):
    settlements = row["settlements"]
    if (type(settlements) is not dict or settlements.keys() != set(_STATUSES)
            or any(not _nonnegative(count) for count in settlements.values())
            or sum(settlements.values()) != row["checks"]):
        raise ValueError("settlements must reconcile every purchased check")
    reads, attempts = row["reads"], row["attempts"]
    admitted = row["invalid_admitted"] + row["valid_admitted"]
    refused = row["invalid_refused"] + row["valid_refused"]
    expected_refusals = 2 * (settlements["mismatch"] + settlements["unavailable"])
    if (reads != target_count or row["read_hits"] != reads or attempts != 2 * target_count
            or row["cached_lookups"] != 2 * row["checks"] or row["committed"] != admitted
            or admitted + refused != attempts or refused != expected_refusals):
        raise ValueError("dispatch counters do not reconcile the matched fixture")
    return row["read_hits"], row["invalid_admitted"] + row["invalid_refused"]


def _increments(grid, orders, condition):
    by_target = {}
    for arm, order in orders.items():
        prior = grid[condition, arm, 0]
        for checks, target in enumerate(order, 1):
            current = grid[condition, arm, checks]
            delta = tuple(current["settlements"][status] - prior["settlements"][status]
                          for status in _STATUSES)
            invalid = current["invalid_refused"] - prior["invalid_refused"]
            valid = current["valid_refused"] - prior["valid_refused"]
            if (sorted(delta) != [0, 0, 1] or min(invalid, valid) < 0
                    or invalid + valid != 2 * (1 - delta[0])):
                raise ValueError("each added target must settle once with its exact dispatch effect")
            value = (*delta, invalid, valid)
            if by_target.setdefault(target, value) != value:
                raise ValueError("target settlement or dispatch effect differs across ranking arms")
            prior = current
    return by_target


def _frontier(rows):
    def dominates(candidate, point):
        return candidate != point and all(left <= right for left, right in zip(candidate, point, strict=True))

    objectives = [tuple(row[field] for field in _OBJECTIVES) for row in rows]
    return [{"arm": row["arm"], **{field: row[field] for field in _OBJECTIVES}}
            for row, point in zip(rows, objectives, strict=True)
            if not any(dominates(candidate, point) for candidate in objectives)]


def audit(rows, *, orders, restored_target, statuses, invalid_uses):
    """Validate the exact two-condition prefix grid and report descriptive tradeoffs."""
    inventory = _target_inventory(orders)
    if not _identifier(restored_target) or restored_target not in inventory:
        raise ValueError("restored target must belong to the shared ranking inventory")
    if (type(statuses) is not dict or statuses.keys() != set(_CONDITIONS)
            or any(type(mapping) is not dict or mapping.keys() != inventory
                   or any(value not in _STATUSES for value in mapping.values()) for mapping in statuses.values())
            or type(invalid_uses) is not dict or invalid_uses.keys() != inventory
            or any(not _nonnegative(count) or count > 2 for count in invalid_uses.values())):
        raise ValueError("reference and label counts must cover the exact target inventory")
    target_count = len(inventory)
    if type(rows) is not list:
        raise ValueError("share grid rows must be an ordered list")
    grid, denominators = {}, set()
    for row in rows:
        if (type(row) is not dict or row.keys() != _ROW_FIELDS
                or not _identifier(row["arm"]) or row["arm"] not in orders
                or row["condition"] not in _CONDITIONS
                or any(not _nonnegative(row[field]) for field in _COUNTERS)):
            raise ValueError("invalid share grid row")
        condition, arm, checks = row["condition"], row["arm"], row["checks"]
        key = condition, arm, checks
        if checks > target_count or key in grid or row["selected"] != list(orders[arm][:checks]):
            raise ValueError("grid needs exactly one row for each locked selection prefix")
        denominators.add(_account(row, target_count))
        grid[key] = row
    if (len(grid) != len(_CONDITIONS) * len(orders) * (target_count + 1)
            or denominators != {(target_count, sum(invalid_uses.values()))}):
        raise ValueError("share grid is incomplete or its matched denominators differ")

    unavailable, restored = (_increments(grid, orders, condition) for condition in _CONDITIONS)
    for condition, observed in (("unavailable", unavailable), ("restored", restored)):
        for target, status in statuses[condition].items():
            refusals = (0, 0) if status == "matched" else (invalid_uses[target], 2 - invalid_uses[target])
            expected = (*(int(choice == status) for choice in _STATUSES), *refusals)
            if observed[target] != expected:
                raise ValueError("grid target effect differs from the evaluator status or label counts")
    for target in inventory:
        if target == restored_target:
            if unavailable[target] != (0, 0, 1, 0, 2) or restored[target] != (1, 0, 0, 0, 0):
                raise ValueError("restoration must settle the unavailable target and restore its two valid sends")
        elif unavailable[target] != restored[target]:
            raise ValueError("restoration changed a different target's settlement or dispatch effect")
    affected = sum(restored_target in row["selected"] for row in rows if row["condition"] == "restored")
    return {
        "target_count": target_count,
        "row_count": len(rows),
        "affected_cells": affected,
        "nondominated": {
            condition: _frontier([grid[condition, arm, checks] for arm in sorted(orders)
                                  for checks in range(target_count + 1)])
            for condition in _CONDITIONS
        },
    }
