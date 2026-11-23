"""Generate matched condition orders for a declared R3 block inventory."""

import argparse
from collections import Counter, defaultdict
from itertools import zip_longest
import json
from pathlib import Path
import random


def _labels(values, name):
    if any(type(value) is not str or not value or value != value.strip() for value in values):
        raise ValueError(f"{name} must be nonempty strings without surrounding whitespace")


def _orders(conditions, rng):
    n = len(conditions)
    labels = rng.sample(conditions, n)
    base = [0] + [(i + 1) // 2 if i % 2 else n - i // 2 for i in range(1, n)]
    shifts = rng.sample(range(n), n)
    forward = [tuple(labels[(i + shift) % n] for i in base) for shift in shifts]
    return forward + [row[::-1] for row in forward] if n % 2 else forward


def plan(conditions, blocks, *, seed):
    """Return the run order and within-stratum position and neighbor counts."""
    if type(seed) is not int:
        raise ValueError("seed must be an integer")
    if not isinstance(conditions, list) or len(conditions) < 2:
        raise ValueError("at least two conditions are required")
    _labels(conditions, "conditions")
    if len(conditions) != len(set(conditions)):
        raise ValueError("conditions must be distinct")
    if not isinstance(blocks, list) or not blocks:
        raise ValueError("at least one block is required")

    inventory = defaultdict(list)
    seen = set()
    for block in blocks:
        block_id, stratum = block["block_id"], block["stratum"]
        _labels((block_id, stratum), "block IDs and strata")
        if block_id in seen:
            raise ValueError(f"duplicate block ID: {block_id}")
        seen.add(block_id)
        inventory[stratum].append(block_id)

    rng = random.Random(seed)
    conditions = sorted(conditions)
    scheduled_by_stratum, audits = [], {}
    for stratum, members in sorted(inventory.items()):
        orders = _orders(conditions, rng)
        position = {condition: [0] * len(conditions) for condition in conditions}
        neighbors = Counter()
        scheduled = []
        for i, block_id in enumerate(rng.sample(sorted(members), len(members))):
            order = orders[i % len(orders)]
            scheduled.append({"block_id": block_id, "stratum": stratum, "order": list(order)})
            for index, condition in enumerate(order):
                position[condition][index] += 1
            neighbors.update(zip(order, order[1:]))
        complete, remainder = divmod(len(members), len(orders))
        audits[stratum] = {"positions": position,
                           "adjacent": {a: {b: neighbors[a, b] for b in conditions if a != b} for a in conditions},
                           "complete_cycles": complete, "remainder_blocks": remainder, "cycle_size": len(orders)}
        scheduled_by_stratum.append(scheduled)
    scheduled = []
    for wave in zip_longest(*scheduled_by_stratum):
        active = [block for block in wave if block is not None]
        rng.shuffle(active)
        scheduled.extend(active)
    return {"seed": seed, "conditions": conditions, "blocks": scheduled, "strata": audits}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inventory", type=Path)
    args = parser.parse_args()
    try:
        inventory = json.loads(args.inventory.read_bytes())
        result = plan(inventory["conditions"], inventory["blocks"], seed=inventory["seed"])
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
