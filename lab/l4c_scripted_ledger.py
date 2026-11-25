"""Independently recount the operation units in scripted L4-C arm records."""

from collections.abc import Mapping


ARMS = ("replay", "write_only", "search")
ALLOWED_KINDS = {
    "replay": {"source_check", "rewrite_check", "memory_lookup"},
    "write_only": {"source_check", "memory_lookup"},
    "search": {"search_read"},
}
ROW_FIELDS = {"day", "arm", "operations", "spent", "unused"}
OPERATION_FIELDS = {"kind", "subject", "outcome"}


def audit(records, *, cap):
    """Check the ordered arm records against one per-night operation cap."""
    if type(cap) is not int or cap < 0:
        raise ValueError("operation cap must be a nonnegative integer")

    day = 0
    rows = total = 0
    for row in records:
        if not isinstance(row, Mapping) or row.keys() != ROW_FIELDS:
            raise ValueError("unexpected scripted ledger row fields")
        recorded_day = row["day"]
        if type(recorded_day) is not int or recorded_day < 1:
            raise ValueError("ledger day must be a positive integer")
        arm_index = rows % len(ARMS)
        expected_arm = ARMS[arm_index]
        if row["arm"] != expected_arm:
            raise ValueError("scripted ledger arms must appear in the declared order")
        if arm_index == 0:
            if recorded_day <= day:
                raise ValueError("scripted ledger days must be strictly increasing")
            day = recorded_day
        elif recorded_day != day:
            raise ValueError("scripted ledger day is missing a planned arm")

        operations = row["operations"]
        if not isinstance(operations, list):
            raise ValueError("ledger operations must be an ordered list")
        for operation in operations:
            if not isinstance(operation, Mapping) or operation.keys() != OPERATION_FIELDS:
                raise ValueError("unexpected scripted ledger operation fields")
            kind = operation["kind"]
            if type(kind) is not str or kind not in ALLOWED_KINDS[expected_arm]:
                raise ValueError("operation kind is incompatible with the ledger arm")
            if any(type(operation[field]) is not str or not operation[field] for field in ("subject", "outcome")):
                raise ValueError("operation subject and outcome must be nonempty strings")

        spent = len(operations)
        if spent > cap:
            raise ValueError("recorded operations exceed the common cap")
        if (type(row["spent"]) is not int or type(row["unused"]) is not int
                or (row["spent"], row["unused"]) != (spent, cap - spent)):
            raise ValueError("claimed spent or unused units do not match the operation ledger")
        total += spent
        rows += 1

    if rows % len(ARMS):
        raise ValueError("scripted ledger ends with an incomplete night")
    return {"days": rows // len(ARMS), "rows": rows, "total_operations": total}
