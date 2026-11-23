"""Exercise the L2 board-to-generation-to-adoption path on the fixture inputs."""

import hashlib
import json
import os
from pathlib import Path
import re
from time import monotonic_ns

from lab import l2_adoption_control


def _unique_object(pairs):
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError("duplicate keys in decision")
    return result


def _check_usage(output, input_cap, output_cap):
    if (type(output.input_tokens) is not int or not 0 < output.input_tokens <= input_cap
            or type(output.output_tokens) is not int or not 0 < output.output_tokens <= output_cap
            or type(output.generation_ns) is not int or output.generation_ns < 0):
        raise ValueError("generation usage outside the declared caps or duration")
    if output.reached_output_limit is not (output.output_tokens == output_cap) or not isinstance(output.text, str):
        raise ValueError("generation return has inconsistent limit metadata or text")


def validate_identity(identity):
    if (type(identity) is not dict or set(identity) != {"archive_id", "schedule_sha256", "block_id", "arm_position"}
            or type(identity["archive_id"]) is not str
            or re.fullmatch(r"[0-9a-f]{32}", identity["archive_id"]) is None
            or type(identity["schedule_sha256"]) is not str
            or re.fullmatch(r"[0-9a-f]{64}", identity["schedule_sha256"]) is None
            or type(identity["block_id"]) is not str or not identity["block_id"]
            or identity["block_id"] != identity["block_id"].strip()
            or type(identity["arm_position"]) is not int or identity["arm_position"] < 0):
        raise ValueError("invalid generation receipt identity")


def run(path, condition, *, generate, render, max_input_tokens, max_output_tokens, accept_at_limit,
        reference_text=None, identity=None):
    """The renderer sees the worker's observed inputs. The scorer is separate."""
    if condition not in l2_adoption_control.CONDITIONS:
        raise ValueError("unknown fixture condition")
    if type(accept_at_limit) is not bool:
        raise ValueError("an explicit output-limit scoring rule is required")
    if any(type(limit) is not int or limit < 1 for limit in (max_input_tokens, max_output_tokens)):
        raise ValueError("input and output token limits must be positive integers")
    if reference_text is not None and (not isinstance(reference_text, str) or not reference_text.strip()):
        raise ValueError("reference text must identify a nonempty source")
    if identity is not None:
        validate_identity(identity)
    turns = []
    verification_durations = []
    journal_path = Path(path).with_suffix(".generation.jsonl")

    def record(journal, row):
        journal.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
        journal.flush()
        os.fsync(journal.fileno())

    with journal_path.open("x", encoding="utf-8") as journal:
        header = {"event": "arm_start", "condition": condition, "accept_at_limit": accept_at_limit,
                  "max_input_tokens": max_input_tokens, "max_output_tokens": max_output_tokens}
        if reference_text is not None:
            header["reference_sha256"] = hashlib.sha256(reference_text.encode()).hexdigest()
        if identity is not None:
            header["identity"] = identity
        record(journal, header)

        def ask(observation, prompt, stage):
            turn = {**observation, "stage": stage, "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest()}
            record(journal, {"event": "start", **turn})
            try:
                output = generate(prompt, max_input_tokens=max_input_tokens, max_output_tokens=max_output_tokens)
                _check_usage(output, max_input_tokens, max_output_tokens)
            except Exception as error:
                record(journal, {"event": "failed", **turn, "error_type": type(error).__name__, "usage": None})
                raise
            try:
                proposal = json.loads(output.text, object_pairs_hook=_unique_object)
            except (ValueError, RecursionError):
                proposal = None
            held_at_limit = output.reached_output_limit and not accept_at_limit
            turn.update(reply_sha256=hashlib.sha256(output.text.encode()).hexdigest(),
                        input_tokens=output.input_tokens, output_tokens=output.output_tokens,
                        generation_ns=output.generation_ns, reached_output_limit=output.reached_output_limit,
                        held_at_limit=held_at_limit, json_object=isinstance(proposal, dict))
            record(journal, {"event": "completed", **turn})
            turns.append(turn)
            return proposal if isinstance(proposal, dict) and not held_at_limit else None

        def decide(worker, instruction, source_id, source_text, read_reference=None):
            observed = (worker, instruction, source_id, source_text)
            observation = {"worker": worker, "observed_source_id": source_id,
                           "observed_instruction_sha256": hashlib.sha256(instruction.encode()).hexdigest(),
                           "observed_source_sha256": hashlib.sha256(source_text.encode()).hexdigest()}
            if read_reference is None:
                return ask(observation, render(*observed), "initial")
            proposal = ask(observation, render(*observed, verification=None), "initial")
            if proposal != {"action": "verify"}:
                return proposal
            start_ns = monotonic_ns()
            verified = read_reference()
            elapsed = monotonic_ns() - start_ns
            if verified is None:
                return None
            verification_durations.append(elapsed)
            record(journal, {"event": "reference_read", "worker": worker, "reference_id": verified["id"],
                             "reference_read_ns": elapsed,
                             "reference_sha256": hashlib.sha256(verified["text"].encode()).hexdigest()})
            return ask(observation, render(*observed, verification=verified), "after_verification")

        readout = l2_adoption_control.run(path, condition, decide=decide, reference_text=reference_text)
        record(journal, {"event": "arm_complete", "board_head": readout["trace"][-1]["hash"]})

    return {"generation_turns": turns, "verification_reads": len(verification_durations),
            "verification_read_ns": sum(verification_durations),
            "input_tokens": sum(turn["input_tokens"] for turn in turns),
            "output_tokens": sum(turn["output_tokens"] for turn in turns), "readout": readout}
