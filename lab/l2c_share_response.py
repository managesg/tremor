"""Exact scripted Board response across the full integer screening grid."""

from collections import Counter
from fractions import Fraction
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from murmuration.board import Board

from lab.l2c_ranked_dispatch import evaluate_arm, fixture
from lab.l2c_share_audit import ORDERINGS, audit
from lab.l2c_verification_ranking import select
from lab.l4_measured_compression import pin


SETTLEMENTS = ("matched", "mismatch", "unavailable")


def _write(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def _fraction(value):
    return {"numerator": value.numerator, "denominator": value.denominator}


def _describe(rows, count):
    descriptions = {}
    for condition in ("unavailable", "restored"):
        indexed = {(row["arm"], row["checks"]): row for row in rows if row["condition"] == condition}
        first, last = (indexed["direct_relays", checks] for checks in (0, count))
        full_invalid = last["invalid_admitted"]
        point_matches = {arm: next(checks for checks in range(count + 1)
                                   if indexed[arm, checks]["invalid_admitted"] == full_invalid) for arm in ORDERINGS}
        uniform = []
        for checks in range(count + 1):
            share = Fraction(checks, count)
            uniform.append({"checks": checks, "share": _fraction(share), **{
                metric: _fraction(first[metric] + share * (last[metric] - first[metric]))
                for metric in ("invalid_admitted", "valid_refused")
            }})
        descriptions[condition] = {"first_point_matching_full_invalid_admissions": point_matches,
                                    "uniform_permutation_expected_counts": uniform}
    return descriptions


def compare(root):
    rank, initial, original, plan, bridge, unavailable, truth = fixture(root)
    candidates = original["candidates"]
    selection = select(rank, candidates=candidates, expected_head=bridge["ranking_head"],
                       expected_events=bridge["ranking_events"], check_budget=len(candidates),
                       seed=original["random_seed"])
    route = {row["rank_id"]: row["target"] for row in bridge["targets"]}
    orders = {arm: [route[item] for item in selection["arms"][arm]] for arm in ORDERINGS}
    restored_target, = [target for target, value in unavailable.items() if value is None]
    restored_value = json.dumps({"subject": "heldout-2", "value": 7, "version": 1}, sort_keys=True)
    references = {"unavailable": unavailable, "restored": unavailable | {restored_target: restored_value}}
    items = Board(initial, seed=17).snapshot()["items"]
    statuses = {condition: {target: ("unavailable" if value is None else
                                     "matched" if value == items[target]["text"] else "mismatch")
                            for target, value in reference.items()} for condition, reference in references.items()}
    invalid_uses = dict.fromkeys(route.values(), 0)
    for step in plan["steps"]:
        if step["id"] in truth["values"] and not truth["values"][step["id"]]:
            invalid_uses[step["target"]] += 1
    case_inputs = {}
    rows, receipts = [], {}
    for condition, reference in references.items():
        binding = bridge | {"ranking_sha256": pin(selection), "reference_sha256": pin(reference)}
        bridge_pin = pin(binding)
        labels = truth | {"bridge_sha256": bridge_pin}
        labels_pin = pin(labels)
        case_inputs[condition] = {"bridge": binding, "bridge_sha256": bridge_pin,
                                  "reference": reference, "label_sha256": labels_pin}
        for arm in ORDERINGS:
            for checks in range(len(candidates) + 1):
                identity = f"{condition}-{arm}-{checks}"
                result = evaluate_arm(rank, initial, root / f"{identity}.jsonl", selection, plan, binding,
                                      reference, labels, arm=arm, expected_bridge_pin=bridge_pin,
                                      expected_truth_pin=labels_pin, check_count=checks)
                counts = result["dispatch"]["physical_counts"]
                settlements = Counter(result["settled"].values())
                rows.append({"condition": condition, "arm": arm, "checks": result["evaluator_checks"],
                             "selected": result["selected_targets"],
                             "settlements": {key: settlements[key] for key in SETTLEMENTS},
                             "cached_lookups": result["dispatch"]["cached_lookups"],
                             "reads": counts["reads"], "read_hits": counts["read_hits"],
                             "attempts": counts["dispatch_attempts"], "committed": counts["committed"],
                             **{key: result["assessment"][key] for key in (
                                 "invalid_admitted", "invalid_refused", "valid_admitted", "valid_refused",
                             )}})
                receipt_path = root / f"{identity}-receipt.json"
                _write(receipt_path, result)
                receipts[identity] = {"receipt_sha256": pin(result), **result["dispatch"]["terminal"]}
    audited = audit(rows, orders=orders, restored_target=restored_target, statuses=statuses, invalid_uses=invalid_uses)
    return {"scope": "scripted_l2c_integer_share_response", "scientific_result": False,
            "selection": selection, "orders": orders, "plan": plan, "factual_labels": truth["values"],
            "cases": case_inputs, "restored_target": restored_target, "rows": rows, "receipts": receipts,
            "expected_settlements": statuses, "invalid_opportunities_by_target": invalid_uses,
            "audit": audited, "descriptive": _describe(rows, len(candidates))}


def demo():
    with TemporaryDirectory(prefix="tremor-l2c-share-") as tmp:
        return compare(Path(tmp))


if __name__ == "__main__":
    print(json.dumps(demo(), sort_keys=True, indent=2, allow_nan=False))
