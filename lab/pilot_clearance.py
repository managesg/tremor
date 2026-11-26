"""Replay a Pilot 3 or Pilot 4 clearance (select with --batch) from saved local records."""
import argparse
import hashlib
import json
import math
from pathlib import Path

from murmuration import ep1
from murmuration.trapbench import alloc

CORE = ("none", "play", "code")
ORDERS = ("shared", "per_agent")
USAGE_KEYS = {
    "input": "input_tokens",
    "output": "output_tokens",
    "cache_creation": "cache_creation_input_tokens",
    "cache_read": "cache_read_input_tokens",
}
OUTPUT_CEILING = 150


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _read(path, *, lines=False):
    raw = path.read_bytes()
    data = [json.loads(line) for line in raw.splitlines()] if lines else json.loads(raw)
    return data, hashlib.sha256(raw).hexdigest()


def _usage(turns):
    usage = {key: 0 for key in USAGE_KEYS}
    for turn in turns:
        for key, wire in USAGE_KEYS.items():
            value = turn["usage"][wire]
            _require(type(value) is int and value >= 0, f"invalid {wire}: {turn['call_id']}")
            usage[key] += value
    return usage


def _label(batch):
    return "Pilot " + batch[5:]


def _validate_episodes(schedule, rows, batch="pilot3"):
    plan = ep1.plan(batch, 0)
    _require(
        schedule["kind"] == batch and schedule["dry_run"] is False
        and type(schedule["schedule_seed"]) is int and schedule["schedule_seed"] == 0
        and schedule["plan"] == plan,
        f"saved schedule differs from the {_label(batch)} design",
    )
    expected = [(block["set"], block["task_order"], cond) for block in plan for cond in block["order"]]
    _require([(r["set"], r["task_order"], r["cond"]) for r in rows] == expected,
             "episode records do not match the complete scheduled cells in order")
    _require(len({r["episode_id"] for r in rows}) == len(rows), "duplicate episode ID")
    turns = []
    for row in rows:
        episode = row["episode_id"]
        _require(
            row["kind"] == row["batch"] == batch and row["schedule_seed"] == 0
            and row["ended"] == "complete" and row["valid"] is True and row["void"] is None
            and row["attempt"] == 0 and row["calls"] == 8,
            f"incomplete or unexpected {_label(batch)} episode: {episode}",
        )
        taskset = alloc.gen(row["set"], "train")
        digest = hashlib.sha256(alloc.dumps(taskset).encode()).hexdigest()
        _require(row["taskset_sha256"] == digest, f"wrong training task set: {episode}")
        score = alloc.score(row["log"], taskset)
        _require(score["valid"] and score == row["scores"] and score["Y"] == row["Y"],
                 f"saved score disagrees with the action log: {episode}")
        episode_turns = row["turns"]
        expected_turns = {(r, f"a{a}") for r in range(2) for a in range(4)}
        _require(len(episode_turns) == 8
                 and {(t["round"], t["agent"]) for t in episode_turns} == expected_turns,
                 f"incomplete turn records: {episode}")
        for turn in episode_turns:
            expected_id = f"{episode}:r{turn['round']}:{turn['agent']}"
            _require(turn["call_id"] == expected_id and turn["retries"] == 0
                     and isinstance(turn["block_types"], list)
                     and bool(turn["block_types"])
                     and all(isinstance(block, str) for block in turn["block_types"])
                     and isinstance(turn["reply"], str)
                     and isinstance(turn["stop_reason"], str),
                     f"incomplete or unexpected call record: {expected_id}")
        malformed = sum(t["status"] == "malformed" for t in episode_turns)
        _require(row["malformed"] == malformed, f"malformed count mismatch: {episode}")
        _require(row["tokens"] == _usage(episode_turns), f"episode usage mismatch: {episode}")
        turns.extend(episode_turns)
    _require(len({t["call_id"] for t in turns}) == len(turns), "duplicate call ID")
    return turns


def _reconcile(final, ledger, rows, turns, batch="pilot3"):
    _require(all(line["batch"] == batch for line in ledger), "unexpected ledger batch")
    _require(len(ledger) == 2 * len(turns) + 2, "incomplete or unexpected ledger length")
    _require(ledger[0]["kind"] == "batch_open" and ledger[-1]["kind"] == "batch_stop"
             and ledger[-1]["reason"] == "complete", f"ledger lacks completed {_label(batch)} bookends")
    for turn, offset in zip(turns, range(1, len(ledger) - 1, 2), strict=True):
        reserve, charge = ledger[offset:offset + 2]
        call_id = turn["call_id"]
        _require(reserve["kind"] == "reserve" and charge["kind"] == "charge"
                 and reserve["id"] == charge["id"] == call_id
                 and charge["usage"] == turn["usage"] and charge["usd"] == turn["usd"]
                 and charge["stop_reason"] == turn["stop_reason"]
                 and charge["returned_model"] == turn["returned_model"] == ep1.MODEL
                 and charge["response_sha256"] == hashlib.sha256(turn["reply"].encode()).hexdigest()
                 and charge["void"] is None and charge["usage_invalid"] is None,
                 f"ledger disagrees with recorded call: {call_id}")
    summary = final["ledger"]
    usage = _usage(turns)
    usd = math.fsum(t["usd"] for t in turns)
    _require(
        final["kind"] == summary["batch"] == batch and final["reason"] == summary["stop_reason"] == "complete"
        and final["aborts"] == 0 and final["episodes"] == len(rows)
        and final["voids"] == dict.fromkeys(ep1.BASE_CONDS + tuple(ep1.PILOT_CARDS), 0)
        and summary["calls"] == len(turns) and summary["tokens"] == sum(usage.values())
        and summary["tokens_by_class"] == {**usage, "unmetered_worst": 0}
        and math.isclose(summary["usd"], usd, abs_tol=1e-12, rel_tol=0),
        "saved batch summary disagrees with local records",
    )
    return {"calls": len(turns), "tokens": sum(usage.values()), "usd": f"{usd:.7f}",
            "transport_aborts": 0, "voided_episodes": 0,
            "reservations": len(turns), "charges": len(turns)}


def _usage_readout(rows):
    turns = [turn for row in rows for turn in row["turns"]]
    over = [t for t in turns if t["usage"]["output_tokens"] > OUTPUT_CEILING]
    admitted = wrong = 0
    for row in rows:
        expected = {task["id"]: task["expect"] for task in alloc.gen(row["set"], "train")["tasks"]}
        work = [e for e in row["log"]
                if e["action"] == "work" and not e.get("rejected") and e["task"] in expected]
        admitted += len(work)
        wrong += sum(type(e.get("answer")) is not int or e["answer"] != expected[e["task"]] for e in work)
    usage = _usage(turns)
    return {
        "episodes": len(rows), "calls": len(turns), "tokens_by_class": usage, "tokens": sum(usage.values()),
        "usd": f"{math.fsum(turn['usd'] for turn in turns):.7f}",
        "http_400_in_trace": sum("HTTP 400" in str(t.get("reason")) for t in turns),
        "non_text_replies": sum(any(b != "text" for b in t["block_types"]) for t in turns),
        "end_turn": sum(t["stop_reason"] == "end_turn" for t in turns),
        "stop_max_tokens": sum(t["stop_reason"] == "max_tokens" for t in turns),
        "max_output_tokens": max(t["usage"]["output_tokens"] for t in turns),
        "over_150": len(over),
        "over_150_by_round": {str(r): sum(t["round"] == r for t in over) for r in range(2)},
        "malformed": sum(row["malformed"] for row in rows),
        "admitted_work": admitted,
        "wrong_admitted_work": wrong,
    }


def audit(directory: Path, ledger_path: Path, batch="pilot3"):
    """Return the replay, or raise when the batch's (default Pilot 3) evidence is missing or inconsistent."""
    schedule, schedule_sha = _read(directory / "schedule.json")
    rows, episodes_sha = _read(directory / "episodes.jsonl", lines=True)
    final, final_sha = _read(directory / "final.json")
    ledger, ledger_sha = _read(ledger_path, lines=True)
    turns = _validate_episodes(schedule, rows, batch)
    local_ledger = _reconcile(final, ledger, rows, turns, batch)

    core_rows = [row for row in rows if row["cond"] in CORE]
    all_rows = _usage_readout(rows)
    core = _usage_readout(core_rows)
    conditions = {
        cond: _usage_readout([row for row in rows if row["cond"] == cond])
        for cond in CORE + tuple(ep1.PILOT_CARDS)
    }
    orders = {
        order: {
            "all_conditions": _usage_readout([row for row in rows if row["task_order"] == order]),
            "core": _usage_readout([row for row in core_rows if row["task_order"] == order]),
        }
        for order in ORDERS
    }
    gate = ep1.order_gate(schedule, rows)
    code_duplicates = sum(order["duplicates"]["code"] for order in gate["orders"].values())
    criteria = {
        "1_request_shape": "pass" if all_rows["http_400_in_trace"] == all_rows["non_text_replies"] == 0 else "fail",
        "2_no_truncation": "pass" if all_rows["stop_max_tokens"] == 0 and core["over_150"] == 0 else "fail",
        "3_reply_format": "pass" if core["malformed"] <= 7
            and all(conditions[cond]["malformed"] <= 4 for cond in CORE) else "fail",
        "4_arithmetic": "pass" if core["wrong_admitted_work"] <= 3 else "fail",
        "5_usable_order": "pass" if gate["picked"] and code_duplicates == 0 else "fail",
        "6_scripted_bracket": "unavailable",
        "7_console_and_manual_review": "unavailable",
    }
    return {
        "batch": batch,
        "clearance": "failed" if "fail" in criteria.values() else "incomplete",
        "source_sha256": {"schedule": schedule_sha, "episodes": episodes_sha, "final": final_sha, "ledger": ledger_sha},
        "readouts": {"all_conditions": all_rows, "core": core, "per_order": orders, "per_condition": conditions},
        "local_ledger": local_ledger,
        "criteria": criteria,
        "criterion_scope": {
            "wording": "§13.16b names the three EP-1 conditions and also refers to the whole batch. Both scopes are shown.",
            "1": "Whole-batch check using locally retained responses and reconciled attempt records.",
            "2": "Zero max_tokens stops over the whole batch; the 150-token maximum over the three core conditions (144 calls, EP-1 13.16b, D8-c). Whole-batch overages are also reported.",
            "3": "The predeclared denominators are 144 core replies and 48 replies per core condition.",
            "4": "The predeclared maximum of 72 admitted work events corresponds to the three core conditions.",
            "per_order": "Descriptive summaries with the original 150-token ceiling shown. No split clearance thresholds.",
        },
        "order_rule": gate,
        "unavailable_evidence": {
            "scripted_bracket": "The Pilot 3 batch files carry no linked three-arm floor/oracle receipt.",
            "console_ledger_equality": "Local ledger reconciles with all retained attempt records. Console evidence is unavailable.",
            "manual_episode_review": "No linked complete signed per-episode reading record was supplied.",
            "independent_regate": "No independent re-gate receipt is part of this batch record.",
        },
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("ledger", type=Path)
    parser.add_argument("--batch", default="pilot3", choices=("pilot3", "pilot4"))
    args = parser.parse_args(argv)
    try:
        result = audit(args.directory, args.ledger, args.batch)
    except (OSError, KeyError, TypeError, ValueError) as error:
        parser.exit(2, f"{_label(args.batch)} evidence unavailable or inconsistent: {error}\n")
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
