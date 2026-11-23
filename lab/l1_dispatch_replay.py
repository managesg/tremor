"""Record and replay public CPU dispatch against pinned L1 allocation plans."""

import argparse
import hashlib
import json
import os
from pathlib import Path

from lab import adapter_lineage, l1_dispatch_audit, l1_verification_allocation as allocation


SCENARIOS = {
    "stopped_checks": ("uniform", 16),
    "completed_retries": ("majority_retry", 4),
    "completed_measured_checks": ("overdispersion", 48),
}


class ScriptedFailure(Exception):
    """The fixture returned no result and no measurement."""


class ScriptedStop(Exception):
    """The fixture left the requested action open."""


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _write(path, value):
    raw = (json.dumps(value, sort_keys=True, allow_nan=False) + "\n").encode()
    with path.open("xb") as stream:
        stream.write(raw)
    return _sha(raw)


def _perform(scenario, attempt):
    index, units = attempt["attempt_index"], attempt["units"]
    if scenario == "stopped_checks":
        if index == 1:
            raise ScriptedFailure()
        if index == 2:
            raise ScriptedStop()
        return False, units - 1
    if scenario == "completed_measured_checks":
        return index == 0, units - index
    return index % 2 == 0, units


def _dispatch(path, plan, plan_pin, claims, perform):
    attempts = l1_dispatch_audit.attempts(plan, claims, plan_sha256=plan_pin)
    with path.open("x", encoding="utf-8") as tape:
        seq = 0

        def record(event, **fields):
            nonlocal seq
            tape.write(json.dumps({"seq": seq, "event": event, **fields}, sort_keys=True, allow_nan=False) + "\n")
            tape.flush()
            os.fsync(tape.fileno())
            seq += 1

        record("plan", plan_sha256=plan_pin)
        for attempt in attempts:
            index = attempt["attempt_index"]
            identity = {"attempt_index": index,
                        "attempt_sha256": allocation.digest({"plan_sha256": plan_pin, "attempt": attempt})}
            record("start", **identity)
            try:
                result, used_units = perform(attempt)
            except ScriptedFailure:
                record("failure", **identity, reason="scripted_failure", used_units=None)
            except ScriptedStop:
                record("terminal", status="stopped", reason="operator_limit")
                break
            else:
                record("answer", **identity, result=result, used_units=used_units)
        else:
            record("terminal", status="completed", reason=None)
    return _sha(path.read_bytes())


def replay(bundle, *, pins_sha256):
    root = Path(bundle)
    pins = adapter_lineage._json(root / "pins.json", pins_sha256)
    if pins.keys() != SCENARIOS.keys():
        raise ValueError("unexpected dispatch replay inventory")
    claims, calibration = allocation.development_inputs()
    reports = {}
    for scenario, (mode, budget) in SCENARIOS.items():
        receipt = pins[scenario]
        if type(receipt) is not dict or receipt.keys() != {"plan_sha256", "plan_file_sha256", "journal_sha256"}:
            raise ValueError("invalid dispatch replay pins")
        directory = root / scenario
        plan = adapter_lineage._json(directory / "plan.json", receipt["plan_file_sha256"])
        original = allocation.make_plan(claims, calibration, mode=mode, budget=budget)
        if allocation.digest(original) != receipt["plan_sha256"]:
            raise ValueError("dispatch artifact does not match the public allocation planner")
        reports[scenario] = l1_dispatch_audit.audit(
            plan, claims, directory / "journal.jsonl",
            plan_sha256=receipt["plan_sha256"], journal_sha256=receipt["journal_sha256"],
        )
    return {"scientific_result": False, "scope": "scripted_cpu_dispatch", "pins_sha256": pins_sha256, "reports": reports}


def run(output):
    root = Path(output)
    root.mkdir()
    pins = {}
    claims, calibration = allocation.development_inputs()
    for scenario, (mode, budget) in SCENARIOS.items():
        directory = root / scenario
        directory.mkdir()
        plan = allocation.make_plan(claims, calibration, mode=mode, budget=budget)
        plan_pin = allocation.digest(plan)
        plan_file_pin = _write(directory / "plan.json", plan)
        journal_pin = _dispatch(directory / "journal.jsonl", plan, plan_pin, claims,
                                lambda attempt: _perform(scenario, attempt))
        pins[scenario] = {"plan_sha256": plan_pin, "plan_file_sha256": plan_file_pin, "journal_sha256": journal_pin}
    return replay(root, pins_sha256=_write(root / "pins.json", pins))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="mode", required=True)
    record = commands.add_parser("run")
    record.add_argument("output", type=Path)
    verify = commands.add_parser("replay")
    verify.add_argument("bundle", type=Path)
    verify.add_argument("--pins-sha256", required=True)
    args = parser.parse_args()
    try:
        result = run(args.output) if args.mode == "run" else replay(args.bundle, pins_sha256=args.pins_sha256)
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.exit(2, f"{error}\n")
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
