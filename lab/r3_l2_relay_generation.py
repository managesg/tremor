"""CPU development harness for the independent, inert L2 direct-relay cohort."""

import hashlib
import json
import os
from pathlib import Path
import re

from lab import l2_relay_control as relay, l2_trigger_control
from lab.r3_l2_generation import _check_usage, _unique_object
from tremor.board import Board, read_log


SCHEDULE = (
    (("a", True), ("b", True), ("missed", False), ("incorrect", True)),
    (("a", True), ("late", True)),
)
COMPLETED_STATUS = {"planted": "complete", "clean": "no_planted_roots", "trigger_only": "trigger_only"}
_TRIGGER_TAG, _TRIGGER_MARKER, _ = l2_trigger_control.CONDITIONS["trigger_only"]
TRIGGER_ONLY_STATEMENT = f"Tag={_TRIGGER_TAG} | Marker=[{_TRIGGER_MARKER:5}]"


def _proposal(raw, named_source):
    try:
        value = json.loads(raw, object_pairs_hook=_unique_object)
    except (ValueError, RecursionError):
        return "malformed", None
    if value == {"kind": "abstain"}:
        return "abstained", None
    if (type(value) is not dict or value.keys() != {"kind", "parent_id", "text"}
            or value["kind"] not in ("relay", "decision")
            or not isinstance(value["parent_id"], str)
            or not isinstance(value["text"], str) or not value["text"].strip()):
        return "malformed", None
    if value["parent_id"] != named_source:
        return "unobserved_parent", None
    return "posted", value


def run(path, *, generate, render, max_input_tokens, max_output_tokens, clean=False, trigger_only=False,
        plan_sha256=None):
    """Record one scripted relay window and meter before independently scoring its board."""
    if any(type(limit) is not int or limit < 1 for limit in (max_input_tokens, max_output_tokens)):
        raise ValueError("input and output token limits must be positive integers")
    if type(clean) is not bool:
        raise ValueError("clean must be a Boolean")
    if type(trigger_only) is not bool:
        raise ValueError("trigger_only must be a Boolean")
    if clean and trigger_only:
        raise ValueError("clean and trigger-only fixture modes are mutually exclusive")
    if plan_sha256 is not None and (not isinstance(plan_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", plan_sha256)):
        raise ValueError("invalid relay plan digest")
    path = Path(path)
    tape = path.with_suffix(".relay-generation.jsonl")
    if path == tape:
        raise ValueError("board and generation evidence paths must be distinct")
    with tape.open("x", encoding="utf-8") as journal:
        def record(event, **fields):
            journal.write(json.dumps({"event": event, **fields}, sort_keys=True, allow_nan=False) + "\n")
            journal.flush()
            os.fsync(journal.fileno())

        path.touch(exist_ok=False)
        board = Board(path, seed=2)
        text = relay.CORRECT_STATEMENT if clean else relay.FALSE_STATEMENT
        if trigger_only:
            text = TRIGGER_ONLY_STATEMENT
        has_plants = not (clean or trigger_only)
        items = tuple(board.post("source", text, kind="plant" if has_plants else "note") for _ in range(2))
        roots = items if has_plants else ()
        board.end_round()
        header = {"planted_roots": roots, "scheduled_opportunities": sum(map(len, SCHEDULE)),
                  "caps": {"input": max_input_tokens, "output": max_output_tokens}}
        if trigger_only:
            header["trigger_only"] = True
        if plan_sha256 is not None:
            header["plan_sha256"] = plan_sha256
        record("start", **header)

        usage = {"input_tokens": 0, "output_tokens": 0, "generation_ns": 0, "unknown_attempts": 0}
        truncations = 0
        opportunity = 0
        for slots in SCHEDULE:
            for worker, named in slots:
                source = items[0] if named else None
                observed = board.read(worker, source)
                visible = [observed] if named else observed
                objects = [{"id": item["id"], "text": item["text"]} for item in visible]
                with path.open("rb") as persisted:
                    os.fsync(persisted.fileno())
                read = read_log(path)[-1]
                context = {"worker": worker, "round": board.round, "opportunity": opportunity,
                           "source_id": source, "visible": objects}
                prompt = render(context)
                attempt = {**context, "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                           "read_seq": read["seq"], "read_head": read["hash"]}
                record("attempt", **attempt)
                try:
                    output = generate(prompt, max_input_tokens=max_input_tokens, max_output_tokens=max_output_tokens)
                    _check_usage(output, max_input_tokens, max_output_tokens)
                except Exception as exc:
                    usage["unknown_attempts"] += 1
                    record("incomplete", opportunity=opportunity, failure=type(exc).__name__, usage=usage)
                    return {"status": "incomplete_generation", "usage": usage, "readout": None, "anchor": None}
                for field in ("input_tokens", "output_tokens", "generation_ns"):
                    usage[field] += getattr(output, field)
                if output.reached_output_limit:
                    truncations += 1
                    disposition, proposal = "output_limit", None
                else:
                    disposition, proposal = _proposal(output.text, source)
                record("response", opportunity=opportunity, disposition=disposition, raw=output.text,
                       input_tokens=output.input_tokens, output_tokens=output.output_tokens,
                       generation_ns=output.generation_ns, reached_output_limit=output.reached_output_limit)
                if proposal is not None:
                    board.post(worker, proposal["text"], kind=proposal["kind"], refs=(source,))
                opportunity += 1
            board.end_round()

        with path.open("rb") as persisted:
            os.fsync(persisted.fileno())
        trace = read_log(path)
        anchor = {"expected_head": trace[-1]["hash"], "expected_events": len(trace)}
        if truncations:
            record("incomplete", **anchor, output_limit_replies=truncations, usage=usage)
            return {"status": "output_limit", "usage": usage, "readout": None, "anchor": None}
        readout = relay.measure(path, planted_roots=roots, **anchor) if roots else None
        record("complete", **anchor, usage=usage)
        status = "complete" if roots else "no_planted_roots"
        return {"status": "trigger_only" if trigger_only else status, "usage": usage,
                "readout": readout, "anchor": anchor}
