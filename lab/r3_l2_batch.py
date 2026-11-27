"""Replay a pinned L2 development batch on CPU and retain its board and meter evidence."""

import argparse
import hashlib
import json
import os
from pathlib import Path

from lab import l2_generation_audit, r3_l2_generation, r3_schedule
from lab.l2_reference_custody import verify_reference
from lab.spark_decision import Generation
from tremor.manifest import config_hash


def _unique(pairs):
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError("duplicate field in L2 batch manifest")
    return result


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _append(stream, record):
    stream.write(json.dumps(record, sort_keys=True, allow_nan=False) + "\n")
    stream.flush()
    os.fsync(stream.fileno())


def _readback(board, journal):
    if not journal.is_file():
        return None
    try:
        return l2_generation_audit.audit(board, journal, expected_journal_sha256=_digest(journal), renderer=l2_generation_audit.render_scripted_prompt)
    except (KeyError, OSError, TypeError, ValueError):
        return None


def run(bundle, batch_path, output, *, batch_sha256, generate):
    """Execute only the paired development fixture; retain each attempted arm."""
    raw = Path(batch_path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != batch_sha256:
        raise ValueError("batch manifest digest mismatch")
    batch = json.loads(raw, object_pairs_hook=_unique)
    if type(batch) is not dict or batch.get("purpose") != "scripted_l2_warning":
        raise ValueError("batch must declare the scripted L2 warning fixture")
    schedule = r3_schedule.plan(batch["conditions"], batch["blocks"], seed=batch["seed"])
    if set(schedule["conditions"]) != {"warning", "neutral"}:
        raise ValueError("each L2 block needs warning and neutral")
    limits = batch["limits"]
    if (limits.keys() != {"max_input_tokens", "max_output_tokens", "accept_at_limit"}
            or type(limits["accept_at_limit"]) is not bool
            or any(type(limits[k]) is not int or limits[k] < 1 for k in ("max_input_tokens", "max_output_tokens"))):
        raise ValueError("invalid L2 generation limits")
    # Verify every planned block before creating output or asking for a decision.
    references = {}
    for block in batch["blocks"]:
        references[block["block_id"]] = verify_reference(bundle, block["case_id"], **batch["custody"])

    output = Path(output)
    output.mkdir(exist_ok=False)
    attempted, comparisons = [], []
    status = "completed"
    with (output / "batch.jsonl").open("x", encoding="utf-8") as journal:
        _append(journal, {"event": "start", "purpose": batch["purpose"], "batch_sha256": batch_sha256,
                          "schedule": schedule, "schedule_sha256": config_hash(schedule)})
        for block in schedule["blocks"]:
            block_id = block["block_id"]
            verified = references[block_id]
            paired = {}
            for condition in block["order"]:
                arm = f"arm-{len(attempted)}"
                board = output / f"{arm}.jsonl"
                meter = board.with_suffix(".generation.jsonl")
                identity = {"arm": arm, "block_id": block_id, "condition": condition,
                            "reference_sha256": verified.sha256}
                _append(journal, {"event": "arm_start", **identity})
                try:
                    result = r3_l2_generation.run(board, condition, generate=generate, render=l2_generation_audit.render_scripted_prompt,
                                                  reference_text=verified.text, **limits)
                    receipt = l2_generation_audit.audit(board, meter, expected_journal_sha256=_digest(meter),
                                                        expected_board_head=result["readout"]["trace"][-1]["hash"],
                                                        renderer=l2_generation_audit.render_scripted_prompt)
                    if (receipt["status"] != "completed" or receipt["condition"] != condition
                            or receipt["input_tokens_known"] != result["input_tokens"]
                            or receipt["output_tokens_known"] != result["output_tokens"]):
                        raise ValueError("arm meter reconciliation failed")
                    readout = result["readout"]
                    row = {"event": "arm_complete", **identity, "meter": receipt,
                           "exposures": readout["exposure_denominator"], "adoptions": readout["adoption_count"],
                           "adoption_rate": readout["adoption_rate"]}
                except Exception as error:
                    status = "failed"
                    row = {"event": "arm_failed", **identity, "error_type": type(error).__name__,
                           "meter": _readback(board, meter)}
                attempted.append(row)
                _append(journal, row)
                if status == "failed":
                    break
                paired[condition] = row["adoption_rate"]
            if status == "failed":
                break
            if all(value is not None for value in paired.values()):
                comparisons.append({"block_id": block_id, "warning_minus_neutral": paired["warning"] - paired["neutral"]})
        result = {"event": "finish", "status": status, "scored_pairs": comparisons,
                  "attempted_arms": len(attempted), "planned_arms": 2 * len(schedule["blocks"]),
                  "evidence_type": "scripted_development"}
        _append(journal, result)
    return {**result, "arms": attempted}


def _scripted_generate(prompt, *, max_input_tokens, max_output_tokens):
    # There is deliberately no loader or GPU entry point on the replay CLI.
    view = json.loads(prompt)
    if view["worker"] == "a" and view["verification"] is None:
        answer = {"action": "verify"}
    else:
        value = view["observed"].split()[-1] if view["verification"] is None else view["verification"]["text"].split()[-1]
        answer = {"value": value, "source_id": view["source"]}
    return Generation(json.dumps(answer), 1, 1, 0, max_output_tokens == 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("batch", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--batch-sha256", required=True)
    args = parser.parse_args()
    try:
        result = run(args.bundle, args.batch, args.output, batch_sha256=args.batch_sha256, generate=_scripted_generate)
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, sort_keys=True, indent=2))
    return int(result["status"] != "completed")


if __name__ == "__main__":
    raise SystemExit(main())
