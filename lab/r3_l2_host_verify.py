"""Verify a quiescent scripted L2 export against a plan and pins held by the host."""

import hashlib
import json
from pathlib import Path
import re

from lab import l2_adoption_control, l2_generation_audit
from lab.r3_l2_generation import validate_identity


def verify(export, *, schedule, archive_id, observed_pins, renderer, frozen_governance=None):
    """Return a host terminal record after auditing every scheduled arm.

    The host supplies its own schedule, archive ID, renderer, and observed pins
    from outside the export. Pins map (block_id, arm_position) to the SHA-256
    digests of the complete board and journal files. The export must be held
    exclusively by the host after worker exit for the duration of verification.
    Governed evidence also requires exact per-arm reference digests, token caps
    and output-limit scoring rules from the independent freeze, never the export.
    This checks scripted receipts and prompt replay. Reply digests alone cannot
    reconstruct generated decisions or establish native-model provenance.
    """
    if not callable(renderer):
        raise ValueError("host renderer is required")
    conditions = schedule["conditions"]
    blocks = schedule["blocks"]
    if (not isinstance(conditions, list) or len(conditions) < 2
            or any(arm not in l2_adoption_control.CONDITIONS for arm in conditions)
            or len(set(conditions)) != len(conditions) or not isinstance(blocks, list) or not blocks):
        raise ValueError("host schedule requires a nonempty predetermined arm inventory")
    schedule_sha256 = hashlib.sha256(
        json.dumps(schedule, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()
    expected = {}
    block_ids = set()
    for block_position, block in enumerate(blocks):
        block_id = block["block_id"]
        order = block["order"]
        if not isinstance(order, list) or sorted(order) != sorted(conditions):
            raise ValueError("host block order does not match the scheduled conditions")
        for arm_position, condition in enumerate(order):
            identity = {"archive_id": archive_id, "schedule_sha256": schedule_sha256,
                        "block_id": block_id, "arm_position": arm_position}
            validate_identity(identity)
            stem = f"block-{block_position:04d}-arm-{arm_position:02d}"
            expected[block_id, arm_position] = (identity, condition, f"{stem}.jsonl", f"{stem}.generation.jsonl")
        if block_id in block_ids:
            raise ValueError("host schedule contains a duplicate block ID")
        block_ids.add(block_id)

    if set(observed_pins) != set(expected):
        raise ValueError("trusted pins must cover exactly the scheduled arms")
    if frozen_governance is not None and (
        type(frozen_governance) is not dict or set(frozen_governance) != set(expected)
        or any(type(terms) is not dict for terms in frozen_governance.values())
    ):
        raise ValueError("frozen governance must cover exactly the scheduled arms")
    for pins in observed_pins.values():
        if (not isinstance(pins, dict) or set(pins) != {"board_sha256", "journal_sha256"}
                or any(type(pin) is not str or re.fullmatch(r"[0-9a-f]{64}", pin) is None for pin in pins.values())):
            raise ValueError("trusted board and journal SHA-256 pins are required")

    root = Path(export).absolute()
    if root.resolve(strict=True) != root or not root.is_dir():
        raise ValueError("export must be a directory without symlinks")
    files = {entry.name: entry for entry in root.iterdir()}
    expected_names = {name for _, _, board, journal in expected.values() for name in (board, journal)}
    if set(files) != expected_names:
        raise ValueError("export files differ from the planned boards and journals")
    if any(entry.is_symlink() or not entry.is_file() for entry in files.values()):
        raise ValueError("export entries must be regular files without symlinks")
    if any(entry.stat().st_nlink != 1 for entry in files.values()):
        raise ValueError("export entries must have exactly one hard link")

    receipts = []
    for key, (identity, condition, board, journal) in expected.items():
        pins = observed_pins[key]
        if hashlib.sha256(files[board].read_bytes()).hexdigest() != pins["board_sha256"]:
            raise ValueError("board file digest mismatch")
        receipt = l2_generation_audit.audit(
            files[board], files[journal], expected_journal_sha256=pins["journal_sha256"],
            expected_identity=identity, renderer=renderer,
            expected_governance=frozen_governance[key] if frozen_governance is not None else None,
        )
        if receipt["status"] != "completed" or receipt["condition"] != condition:
            raise ValueError("export arm does not match its planned terminal receipt")
        receipts.append({"board": board, "journal": journal, "board_sha256": pins["board_sha256"], **receipt})

    if frozen_governance is not None:
        terms_by_block = {}
        for receipt in receipts:
            block_id = receipt["identity"]["block_id"]
            if terms_by_block.setdefault(block_id, receipt["governance"]) != receipt["governance"]:
                raise ValueError("frozen governance differs across a matched block")
    evidence = "scripted_host_governed_verified" if frozen_governance is not None else "scripted_host_verified"
    return {"evidence": evidence, "status": "completed", "archive_id": archive_id,
            "schedule_sha256": schedule_sha256, "arms": receipts}
