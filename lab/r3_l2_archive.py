"""Archive scripted L2 fixture blocks with verified custody and generation receipts."""

import hashlib
import json
import os
from pathlib import Path
import stat
from uuid import uuid4

from lab import l2_adoption_control, l2_generation_audit, l2_reference_custody, r3_l2_generation, r3_schedule


def run(out, conditions, blocks, *, seed, bundle, manifest, manifest_sha256, truth_inventory, truth_sha256,
        render, generate, max_input_tokens, max_output_tokens, accept_at_limit):
    """Run matched fixture arms. Each block supplies block_id, stratum, and case_id.

    The injected callbacks are trusted offline code. A successful index covers
    every planned arm. Failed runs retain their partial board and journal files
    without a completed index.
    """
    schedule = r3_schedule.plan(conditions, blocks, seed=seed)
    if any(condition not in l2_adoption_control.CONDITIONS for condition in conditions):
        raise ValueError("unknown L2 fixture condition")
    if any(type(cap) is not int or cap < 1 for cap in (max_input_tokens, max_output_tokens)):
        raise ValueError("input and output token caps must be positive integers")
    if type(accept_at_limit) is not bool:
        raise ValueError("an explicit output-limit scoring rule is required")
    if not callable(render) or not callable(generate):
        raise ValueError("offline render and generate callbacks are required")

    out = Path(out).absolute()
    parent = out.parent
    if parent.resolve(strict=True) != parent or not parent.is_dir():
        raise ValueError("archive parent must be an existing directory without symlinks")
    case_ids = {block["block_id"]: block["case_id"] for block in blocks}
    references = {
        block_id: l2_reference_custody.verify_reference(
            bundle, case_id, manifest=manifest, manifest_sha256=manifest_sha256,
            truth_inventory=truth_inventory, truth_sha256=truth_sha256,
        )
        for block_id, case_id in case_ids.items()
    }
    out.mkdir(mode=0o700)
    if stat.S_IMODE(out.stat().st_mode) != 0o700 or out.stat().st_uid != os.geteuid():
        raise ValueError("archive directory must be private and owned by the current user")
    schedule_digest = hashlib.sha256(json.dumps(schedule, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    archive_id = uuid4().hex
    index = {
        "evidence": "scripted_fixture",
        "archive_id": archive_id,
        "schedule": schedule,
        "schedule_sha256": schedule_digest,
        "custody": {"manifest_sha256": manifest_sha256, "truth_sha256": truth_sha256},
        "limits": {"max_input_tokens": max_input_tokens, "max_output_tokens": max_output_tokens,
                   "accept_at_limit": accept_at_limit},
        "arms": [],
    }
    for block_position, block in enumerate(schedule["blocks"]):
        block_id = block["block_id"]
        reference = references[block_id]
        for arm_position, condition in enumerate(block["order"]):
            board = out / f"block-{block_position:04d}-arm-{arm_position:02d}.jsonl"
            journal = board.with_suffix(".generation.jsonl")
            identity = {"archive_id": archive_id, "schedule_sha256": schedule_digest,
                        "block_id": block_id, "arm_position": arm_position}
            result = r3_l2_generation.run(
                board, condition, generate=generate, render=render,
                max_input_tokens=max_input_tokens, max_output_tokens=max_output_tokens,
                accept_at_limit=accept_at_limit, reference_text=reference.text, identity=identity,
            )
            receipt = l2_generation_audit.audit(
                board, journal, expected_board_head=result["readout"]["trace"][-1]["hash"], renderer=render,
                expected_identity=identity,
            )
            if (receipt["status"] != "completed" or receipt["condition"] != condition
                    or receipt["input_tokens_known"] != result["input_tokens"]
                    or receipt["output_tokens_known"] != result["output_tokens"]
                    or receipt["reference_reads"] != result["verification_reads"]):
                raise ValueError("generation receipt differs from the completed arm")
            index["arms"].append({
                "block_id": block_id, "arm_position": arm_position, "case_id": case_ids[block_id],
                "reference_sha256": reference.sha256, "board": board.name, "journal": journal.name,
                "readout": {k: v for k, v in result["readout"].items() if k != "trace"},
                **receipt,
            })
    index_path = out / "index.json"
    staged_index = out / ".index.pending"
    with staged_index.open("x", encoding="utf-8") as stream:
        json.dump(index, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    # Publish without replacing a destination or removing retained scratch files.
    os.link(staged_index, index_path)
    directory_fd = os.open(out, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    return {"index_path": index_path, "index": index}
