"""Read defensive ranking features from a pinned predecision Board prefix."""

import random

from lab import l2_relay_control as relay


def features(path, *, candidates, expected_head, expected_events):
    """Count observed activity for every active opening candidate at the cutoff."""
    candidates = tuple(candidates)
    if (not candidates or any(type(item) is not str or not item for item in candidates)
            or len(set(candidates)) != len(candidates)):
        raise ValueError("candidate IDs must form a nonempty unique inventory")
    if type(expected_events) is not int or expected_events < 1 or type(expected_head) is not str:
        raise ValueError("an exact predecision head and event count are required")
    measured = relay.measure(path, planted_roots=candidates, expected_head=expected_head,
                             expected_events=expected_events)
    trace = measured["trace"]
    if type(trace[-1]["round"]) is not int or trace[-1]["round"] != relay.WINDOW_CLOSE:
        raise ValueError("predecision Board must end at the round-two commit")

    roots = set(candidates)
    counts = measured["first_generation_relay_counts"]
    opening, active, pending = {}, set(), []
    retrievals = dict.fromkeys(candidates, 0)
    children = {candidate: set() for candidate in candidates}
    for event in trace:
        kind, data = event["type"], event["data"]
        if kind == "post":
            cited = roots.intersection(data["refs"], active)
            pending.append((event, cited))
        elif kind == "end_round":
            for post, cited in pending:
                item = post["data"]
                item_id = item["id"]
                if post["round"] == 0 and item["kind"] == "plant" and item["text"] == relay.FALSE_STATEMENT:
                    opening[item_id] = (post["round"], post["seq"])
                for candidate in cited:
                    children[candidate].add(item_id)
                active.difference_update(item["supersedes"])
                active.add(item_id)
            pending.clear()
        elif kind == "read":
            item, returned = data["item"], data["n"]
            if type(returned) is not int:
                raise ValueError("invalid Board read receipt")
            if item in roots and item in active and returned == 1:
                retrievals[item] += 1

    if roots != active.intersection(opening):
        raise ValueError("candidate inventory must match all active opening marker roots")
    return {
        candidate: {"direct_relays": counts[candidate], "outdegree": len(children[candidate]),
                    "retrievals": retrievals[candidate], "posted_round": opening[candidate][0],
                    "posted_seq": opening[candidate][1]}
        for candidate in candidates
    }


def rank_arms(observed, *, check_budget, seed):
    """Choose targets from validated feature rows with stable ID tie breaks."""
    ordered = sorted(observed)
    arms = {}
    for metric in ("direct_relays", "outdegree", "retrievals"):
        arms[metric] = sorted(ordered, key=lambda candidate: -observed[candidate][metric])[:check_budget]
    arms["recency"] = sorted(ordered, key=lambda candidate: (-observed[candidate]["posted_round"],
                                                              -observed[candidate]["posted_seq"]))[:check_budget]
    arms["random"] = random.Random(seed).sample(ordered, check_budget)
    arms["none"], arms["full"] = [], ordered
    return arms
