"""Reconcile terminal states and paired scripted charges across the Grover cap grid."""

import argparse
import json
from pathlib import Path

from lab import topology
from . import cap_frontier, release_audit, topology_audit, topology_transfer


def _checked_report(raw, reference_pin=None):
    audit = topology_audit.audit(raw, expected_sha256=reference_pin)
    cases = {}
    for case in json.loads(raw)["cases"]:
        identity = (case["regime"], case["development_seed"])
        cases[identity] = {
            (arm["mode"], arm["evidence_access"]): {
                "verified_stage_union": arm["verified_stage_union"],
                "cap": arm["budget"],
                "spent_scripted_units": arm["spent"],
                "unused_scripted_units": arm["unused"],
                "budget_stopped": arm["budget_stopped"],
                "stopped_on_event": next(
                    (event["attempted"] for event in arm["trace"] if event["kind"] == "budget_stop"), None
                ),
            } for arm in case["arms"]
        }
    return audit["sha256"], cases


def _checked_arms(cap, reference_pin=None):
    trace = topology_transfer.compare(budget=cap)
    raw = (json.dumps(trace, indent=2, sort_keys=True) + "\n").encode()
    digest, cases = _checked_report(raw, reference_pin)
    if any(type(arm["cap"]) is not int or arm["cap"] != cap for arms in cases.values() for arm in arms.values()):
        raise ValueError(f"verified trace has a different cap from {cap}")
    return digest, cases


def _difference(treatment, control):
    stages = len(treatment["verified_stage_union"]) - len(control["verified_stage_union"])
    return {
        "achieved_stage_difference": stages,
        "completed_pair_stage_difference": (
            None if treatment["budget_stopped"] or control["budget_stopped"] else stages
        ),
        "spent_scripted_unit_difference": treatment["spent_scripted_units"] - control["spent_scripted_units"],
    }


def summarize(reference_sha256=cap_frontier.REFERENCE_SHA256):
    """Keep the terminal outcome and resource use separate from stage credit."""
    full_cap = topology.BUDGET
    reference_pin, reference = _checked_arms(full_cap, reference_sha256)
    if reference.keys() != set(topology_transfer.DEVELOPMENT_CASES):
        raise ValueError("incorrect reference case roster")
    rows = []
    same_union_stopped = same_union_different_spend = 0
    for cap in range(1, full_cap + 1):
        pin, cases = (reference_pin, reference) if cap == full_cap else _checked_arms(cap)
        if cases.keys() != reference.keys():
            raise ValueError("cap changed the reference case roster")
        summaries = []
        for (regime, seed), arms in cases.items():
            full = reference[regime, seed]
            records = []
            for (mode, access), arm in arms.items():
                reference_arm = full[mode, access]
                same_union = arm["verified_stage_union"] == reference_arm["verified_stage_union"]
                same_union_stopped += same_union and arm["budget_stopped"]
                same_union_different_spend += same_union and (
                    arm["spent_scripted_units"] != reference_arm["spent_scripted_units"]
                )
                records.append({
                    "mode": mode, "access": access, **arm,
                    "same_stage_union_as_full_cap": same_union,
                    "against_independent_at_same_access": _difference(arm, arms["independent", access]),
                })
            summaries.append({"regime": regime, "seed": seed, "arms": records})
        rows.append({"cap": cap, "trace_sha256": pin, "cases": summaries})
    return {
        "evidence": "scripted_public_cpu_paired_frontier",
        "reference_sha256": reference_pin,
        "audited_arm_cap_views": sum(len(arms) for arms in reference.values()) * len(rows),
        "same_union_as_full_cap_but_budget_stopped": same_union_stopped,
        "same_union_as_full_cap_but_different_spend": same_union_different_spend,
        "caps": rows,
        "scientific_acceptance": False,
    }


def verify_pair(*, treatment, control, regime, seed, treatment_arm, control_arm):
    """Compare public arms from two independently pinned archives at an equal ceiling."""
    selectors = {"treatment": tuple(treatment_arm), "control": tuple(control_arm)}
    if selectors["treatment"] == selectors["control"]:
        raise ValueError("select two distinct comparison arms")
    arms = {}
    for role, (path, pin) in (("treatment", treatment), ("control", control)):
        raw = release_audit._pinned(Path(path), pin, release_audit.TRACE_LIMIT)
        _, cases = _checked_report(raw, pin)
        mode, access = selectors[role]
        arms[role] = {"trace_sha256": pin, "mode": mode, "access": access,
                      **cases[regime, seed][mode, access]}
    if arms["treatment"]["cap"] != arms["control"]["cap"]:
        raise ValueError("paired arms have different resource caps")
    return {
        "evidence": "scripted_public_cpu_paired_trace",
        "regime": regime,
        "seed": seed,
        **arms,
        "comparison": _difference(arms["treatment"], arms["control"]),
        "scientific_acceptance": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    sweep = commands.add_parser("sweep")
    sweep.add_argument("--reference-sha256", default=cap_frontier.REFERENCE_SHA256)
    pair = commands.add_parser("pair")
    pair.add_argument("--regime", required=True)
    pair.add_argument("--seed", type=int, required=True)
    for role in ("treatment", "control"):
        pair.add_argument(f"--{role}", nargs=2, metavar=("PATH", "SHA256"), required=True)
        pair.add_argument(f"--{role}-arm", nargs=2, metavar=("MODE", "ACCESS"), required=True)
    inputs = vars(parser.parse_args())
    operation = summarize if inputs.pop("command") == "sweep" else verify_pair
    try:
        result = operation(**inputs)
    except (OSError, KeyError, ValueError, TypeError, IndexError) as error:
        parser.exit(2, f"Grover paired frontier failed: {error}\n")
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
