"""Development-only L3-B comparison on scripted binary monitor flags."""

from collections import Counter
from fractions import Fraction
import hashlib
from itertools import combinations
import json


TARGET_FPR = Fraction(1, 20)
ARMS = ("top", "selected")


def digest(value):
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def _ratio(value):
    return {"numerator": value.numerator, "denominator": value.denominator}


def _split(rows, *, failure, known_ids, view_ids=None):
    rows = list(rows)
    if not rows:
        raise ValueError("monitor split must be nonempty")
    ids = set()
    for row in rows:
        if type(row) is not dict or row.keys() != {"id", "failure", "views"}:
            raise ValueError("invalid monitor row fields")
        identifier, label, views = row["id"], row["failure"], row["views"]
        if (type(identifier) is not str or not identifier.strip()
                or identifier in ids or identifier in known_ids):
            raise ValueError("monitor split IDs must be unique and disjoint")
        if label is not failure:
            raise ValueError("monitor split label mismatch")
        if (type(views) is not dict or len(views) < 2
                or any(type(view) is not str or not view.strip() for view in views)
                or any(type(bit) is not int or bit not in (0, 1) for bit in views.values())):
            raise ValueError("expected named binary monitor views")
        current_views = sorted(views)
        if view_ids is None:
            view_ids = current_views
        if current_views != view_ids:
            raise ValueError("monitor views must form a rectangular inventory")
        ids.add(identifier)
    known_ids.update(ids)
    return sorted(rows, key=lambda row: row["id"]), view_ids


def _scores(rows, pair):
    return [sum(row["views"][view] for view in pair) for row in rows]


def fit(calibration_failure, threshold_fit_clean):
    """Select pairs on failures and fit their cutoffs on a separate clean split."""
    known_ids = set()
    failures, views = _split(calibration_failure, failure=True, known_ids=known_ids)
    clean, _ = _split(threshold_fit_clean, failure=False, known_ids=known_ids, view_ids=views)
    catches = {view: sum(row["views"][view] for row in failures) for view in views}
    ranked = sorted(views, key=lambda view: (-catches[view], view))
    joint = {pair: _scores(failures, pair).count(0) for pair in combinations(views, 2)}

    anchor = ranked[0]
    anchored_pairs = [(anchor, other) for other in views if other != anchor]
    selected = min(anchored_pairs, key=lambda pair: (joint[tuple(sorted(pair))], pair[1]))
    allow = int(len(clean) * TARGET_FPR)
    arms = {}
    for name, pair in zip(ARMS, (ranked[:2], selected), strict=True):
        scores = _scores(clean, pair)
        cutoff = sorted(scores, reverse=True)[allow]
        arms[name] = {
            "pair": list(pair), "calibration_joint_misses": joint[tuple(sorted(pair))],
            "cutoff": cutoff, "threshold_fit_false_positives": sum(score > cutoff for score in scores),
        }
    return {
        "target_false_positive_rate": _ratio(TARGET_FPR), "view_ids": views,
        "calibration_failure_ids": [row["id"] for row in failures],
        "threshold_fit_clean_ids": [row["id"] for row in clean],
        "fit_split_sha256": {"calibration_failure": digest(failures), "threshold_fit_clean": digest(clean)},
        "calibration_individual_catches": catches,
        "calibration_joint_misses": [{"pair": list(pair), "misses": count} for pair, count in joint.items()],
        "arms": arms,
    }


def _paired_flags(top, selected):
    counts = Counter(zip(top, selected, strict=True))
    return {"both": counts[True, True], "selected_only": counts[False, True],
            "top_only": counts[True, False], "neither": counts[False, False]}


def evaluate(plan, heldout_clean, heldout_failure, *, plan_sha256):
    """Score a pinned fit without using held-out rows to change pairs or cutoffs."""
    if digest(plan) != plan_sha256:
        raise ValueError("monitor plan digest mismatch")
    calibration_count = len(plan["calibration_failure_ids"])
    fit_clean_count = len(plan["threshold_fit_clean_ids"])
    known_ids = set(plan["calibration_failure_ids"]) | set(plan["threshold_fit_clean_ids"])
    views = plan["view_ids"]
    clean, _ = _split(heldout_clean, failure=False, known_ids=known_ids, view_ids=views)
    failures, _ = _split(heldout_failure, failure=True, known_ids=known_ids, view_ids=views)
    arms, clean_flags, failure_flags = {}, {}, {}
    matched = True
    for name in ARMS:
        point = plan["arms"][name]
        pair, cutoff = point["pair"], point["cutoff"]
        clean_flags[name] = [score > cutoff for score in _scores(clean, pair)]
        failure_flags[name] = [score > cutoff for score in _scores(failures, pair)]
        false_positives, catches = sum(clean_flags[name]), sum(failure_flags[name])
        fit_rate = Fraction(point["threshold_fit_false_positives"], fit_clean_count)
        false_positive_rate = Fraction(false_positives, len(clean))
        matched &= fit_rate == false_positive_rate == TARGET_FPR
        # Give each policy the full shared calibration charge and its own two-view costs.
        calls = {"calibration_failure": len(views) * calibration_count, "threshold_fit_clean": len(pair) * fit_clean_count,
                 "heldout_clean": len(pair) * len(clean), "heldout_failure": len(pair) * len(failures)}
        arms[name] = {
            **point, "threshold_fit_false_positive_rate": _ratio(fit_rate),
            "heldout_false_positives": false_positives, "heldout_false_positive_rate": _ratio(false_positive_rate),
            "heldout_catches": catches, "heldout_catch_rate": _ratio(Fraction(catches, len(failures))),
            "call_counts": {**calls, "total": sum(calls.values())},
        }
    paired = _paired_flags(failure_flags["top"], failure_flags["selected"])
    gain = Fraction(paired["selected_only"] - paired["top_only"], len(failures))
    return {
        "plan_sha256": plan_sha256, "fit": plan, "arms": arms,
        "heldout_clean_count": len(clean), "heldout_failure_count": len(failures),
        "heldout_split_sha256": {"clean": digest(clean), "failure": digest(failures)},
        "heldout_target_matched": matched, "heldout_catch_gain": _ratio(gain) if matched else None,
        "paired_clean_flags": _paired_flags(clean_flags["top"], clean_flags["selected"]),
        "paired_failure_flags": paired,
    }


def _fixture_rows(label, flags, *, failure):
    return [{"id": f"{label}-{index:02d}", "failure": failure, "views": dict(zip("ABC", bits, strict=True))}
            for index, bits in enumerate(flags)]


def demo():
    """Replay a complementary pair and a copied-view null at the same call charge."""
    cases = {}
    for name, flags in (("positive", ((1, 1, 1), (1, 1, 0), (0, 0, 1), (0, 0, 0))),
                        ("null", ((1, 1, 1), (1, 1, 1), (0, 0, 0), (0, 0, 0)))):
        clean = [(1, 1, 1)] + [(0, 0, 0)] * 19
        plan = fit(_fixture_rows(f"{name}-cal-fail", flags, failure=True),
                   _fixture_rows(f"{name}-fit-clean", clean, failure=False))
        cases[name] = evaluate(plan, _fixture_rows(f"{name}-hold-clean", clean, failure=False),
                               _fixture_rows(f"{name}-hold-fail", flags, failure=True), plan_sha256=digest(plan))
    return {"scientific_result": False, "scope": "L3_B_fallback_development", "cases": cases}


if __name__ == "__main__":
    print(json.dumps(demo(), sort_keys=True, indent=2, allow_nan=False))
