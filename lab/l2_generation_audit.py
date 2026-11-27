"""Read-only audit of a scripted L2 generation journal and its board."""

import argparse
import hashlib
import json
from pathlib import Path
import re

from lab.r3_l2_generation import validate_identity
from tremor.board import read_log


def render_scripted_prompt(worker, instruction, source, observed, *, verification=None):
    return json.dumps({"worker": worker, "instruction": instruction, "source": source,
                       "observed": observed, "verification": verification}, sort_keys=True)


def _check(condition, message):
    if not condition:
        raise ValueError(message)


def _digest(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _scripted_treatment(board, posts, condition):
    """Bind the fixture condition to the opening payloads and their actual named reads."""
    _check(condition in ("neutral", "warning", "clean", "unseen_parent", "late"),
           "unknown governed scripted treatment")
    instruction = ("Verify the marker against the paper ledger before logging it." if condition == "warning"
                   else "Record the marker in the assigned box for this decision turn.")
    clean = condition == "clean"
    payloads = [("facilitator", "instruction", instruction),
                ("source", "reference" if clean else "plant", "Marker: green" if clean else "Marker: blue")]
    if not clean:
        payloads.append(("source", "plant", "Other marker: orange"))
    treatment = {item: row for item, row in posts.items() if row["data"]["kind"] in
                 ("instruction", "plant", "reference")}
    _check(all(row["round"] == 0 for row in treatment.values())
           and [(row["agent"], row["data"]["kind"], row["data"]["text"])
                for row in treatment.values()] == payloads,
           "Board payloads differ from the governed scripted treatment")
    items = list(treatment)
    instruction_id, source_id = items[0], items[2 if condition == "unseen_parent" else 1]
    workers = ("a", "b") if condition in ("neutral", "warning", "clean") else ("a",)
    receipts = [(row["agent"], row["data"]["item"], row["round"], row["data"]["n"])
                for row in board if row["type"] == "read" and row["data"]["item"] in treatment]
    _check(receipts == [(worker, item, 1, 1) for worker in workers for item in (instruction_id, source_id)],
           "Board named reads differ from the governed scripted treatment")
    return source_id, hashlib.sha256(instruction.encode()).hexdigest()


def audit(board_path, journal_path, *, expected_journal_sha256=None, expected_board_head=None, renderer=None,
          expected_identity=None, expected_governance=None):
    raw = Path(journal_path).read_bytes()
    journal_sha = hashlib.sha256(raw).hexdigest()
    if expected_journal_sha256 is not None:
        _check(journal_sha == expected_journal_sha256, "journal digest mismatch")
    rows = [json.loads(line) for line in raw.splitlines()]
    _check(rows and rows[0]["event"] == "arm_start", "missing arm start")
    header = rows[0]
    receipt_identity = header.get("identity")
    if "identity" in header:
        validate_identity(receipt_identity)
    if expected_identity is not None:
        validate_identity(expected_identity)
        _check(receipt_identity == expected_identity, "generation receipt identity mismatch")
    input_cap, output_cap = header["max_input_tokens"], header["max_output_tokens"]
    _check(all(type(cap) is int and cap > 0 for cap in (input_cap, output_cap)), "invalid token caps")
    allow_limit = header["accept_at_limit"]
    _check(type(allow_limit) is bool, "missing output-limit rule")
    reference_sha = header.get("reference_sha256")
    _check(reference_sha is None or _digest(reference_sha), "invalid reference digest")
    governance = {"reference_sha256": reference_sha, "max_input_tokens": input_cap,
                  "max_output_tokens": output_cap, "accept_at_limit": allow_limit}
    if expected_governance is not None:
        _check(type(expected_governance) is dict and expected_governance.keys() == governance.keys()
               and _digest(expected_governance["reference_sha256"])
               and all(type(expected_governance[key]) is type(governance[key])
                       for key in ("max_input_tokens", "max_output_tokens", "accept_at_limit")),
               "invalid frozen arm governance")
        for key, value in governance.items():
            _check(expected_governance[key] == value, f"frozen arm governance differs for {key}")

    board = read_log(board_path)
    board_head = board[-1]["hash"] if board else None
    if expected_board_head is not None:
        _check(board_head == expected_board_head, "external board head mismatch")
    posts = {row["data"]["id"]: row for row in board if row["type"] == "post"}
    treatment = _scripted_treatment(board, posts, header["condition"]) if expected_governance is not None else None
    named = [(row["agent"], row["data"]["item"]) for row in board if row["type"] == "read"
             and row["data"]["n"] == 1 and row["data"]["item"] in posts
             and row["round"] > posts[row["data"]["item"]]["round"]]
    reads = [(agent, item) for agent, item in named if posts[item]["data"]["kind"] == "verification"]
    content = {item: hashlib.sha256(row["data"]["text"].encode()).hexdigest() for item, row in posts.items()}
    instructions = {(agent, content[item]): posts[item]["data"]["text"] for agent, item in named
                    if posts[item]["data"]["kind"] == "instruction"}
    instructed = {agent for agent, _ in instructions}
    observed_sources = {(agent, item) for agent, item in named if posts[item]["data"]["kind"] in ("plant", "reference")}
    if any(row["type"] == "end_round" for row in board):
        configured = [content[item] for item, row in posts.items() if row["data"]["kind"] == "verification"]
        _check(configured == ([] if reference_sha is None else [reference_sha]), "configured reference differs from the board")

    pending = None
    started, complete_initial, verified = set(), set(), {}
    initial_sources = {}
    finished, failed, inputs, outputs = 0, 0, 0, 0
    complete_arm = False
    for row in rows[1:]:
        event = row["event"]
        _check(not complete_arm and not failed, "events after terminal receipt")
        if event in ("start", "completed", "failed"):
            key = (row["worker"], row["stage"])
            observed_identity = (row["observed_source_id"], row["observed_instruction_sha256"], row["observed_source_sha256"])
            identity = (*key, *observed_identity, row["prompt_sha256"])
            _check(row["stage"] in ("initial", "after_verification") and _digest(row["prompt_sha256"]),
                   "invalid generation identity")
            if event == "start":
                _check(pending is None and key not in started, "generation start duplicates or overlaps an attempt")
                _check(row["stage"] == "initial" or row["worker"] in verified, "follow-up lacks a reference read")
                worker, source = row["worker"], row["observed_source_id"]
                if row["stage"] == "initial":
                    if treatment is not None:
                        _check((source, row["observed_instruction_sha256"]) == treatment,
                               "generation inputs differ from the governed scripted treatment")
                    _check((worker, row["observed_instruction_sha256"]) in instructions,
                           "generation instruction was not read on the board")
                    _check((worker, source) in observed_sources and row["observed_source_sha256"] == content[source],
                           "generation source was not read on the board")
                    initial_sources[worker] = observed_identity
                else:
                    _check(initial_sources[worker] == observed_identity, "follow-up changed the observed source")
                if renderer is not None:
                    reference = None
                    if row["stage"] == "after_verification":
                        ref_id = verified[worker]
                        reference = {"id": ref_id, "text": posts[ref_id]["data"]["text"]}
                    prompt = renderer(worker, instructions[worker, row["observed_instruction_sha256"]], source,
                                      posts[source]["data"]["text"], verification=reference)
                    _check(hashlib.sha256(prompt.encode()).hexdigest() == row["prompt_sha256"],
                           "prompt differs from renderer and permitted board reads")
                pending = identity
                started.add(key)
                continue
            _check(pending == identity, "generation receipt has no matching start")
            pending = None
            if event == "failed":
                _check(row["usage"] is None, "failed generation usage must remain unknown")
                failed += 1
                continue
            count_in, count_out = row["input_tokens"], row["output_tokens"]
            _check(type(count_in) is int and 0 < count_in <= input_cap and type(count_out) is int
                   and 0 < count_out <= output_cap and type(row["generation_ns"]) is int and row["generation_ns"] >= 0,
                   "generation usage exceeds the declared caps")
            at_limit = count_out == output_cap
            _check(row["reached_output_limit"] is at_limit and row["held_at_limit"] is (at_limit and not allow_limit)
                   and _digest(row["reply_sha256"]) and type(row["json_object"]) is bool,
                   "inconsistent generation outcome")
            if row["stage"] == "initial" and row["json_object"] and not row["held_at_limit"]:
                complete_initial.add(row["worker"])
            finished += 1
            inputs += count_in
            outputs += count_out
        elif event == "reference_read":
            worker, ref_id = row["worker"], row["reference_id"]
            _check(pending is None and worker in complete_initial and worker not in verified,
                   "reference read is out of sequence")
            _check((worker, ref_id) in reads and _digest(reference_sha), "reference read is absent on the board")
            actual_sha = content[ref_id]
            _check(row["reference_sha256"] == reference_sha == actual_sha
                   and type(row["reference_read_ns"]) is int and row["reference_read_ns"] >= 0, "reference receipt mismatch")
            verified[worker] = ref_id
        elif event == "arm_complete":
            _check(pending is None and board and board[-1]["type"] == "end_round"
                   and board[-1]["hash"] == row["board_head"], "arm completion does not match the final board")
            _check(len(reads) == len(verified) and dict(reads) == verified,
                   "board and journal reference read totals differ")
            _check(all((worker, "after_verification") in started for worker in verified), "missing verification follow-up")
            _check(set(initial_sources) == instructed and instructed, "completed arm is missing an initial generation")
            complete_arm = True
        else:
            raise ValueError("unknown generation event")
    return {**({"identity": receipt_identity} if receipt_identity is not None else {}),
            **({"governance": governance} if expected_governance is not None else {}),
            "condition": header["condition"], "status": "completed" if complete_arm else "incomplete",
            "completed_generations": finished, "unknown_usage_attempts": failed + int(pending is not None),
            "input_tokens_known": inputs, "output_tokens_known": outputs, "reference_reads": len(verified),
            "journal_sha256": journal_sha, "board_head": board_head}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("board", type=Path)
    parser.add_argument("journal", type=Path)
    parser.add_argument("--journal-sha256")
    parser.add_argument("--board-head")
    parser.add_argument("--strict-scripted", action="store_true",
                        help="rebuild prompts with the scripted renderer using externally pinned receipts")
    args = parser.parse_args()
    if args.strict_scripted and not (args.journal_sha256 and args.board_head):
        parser.error("--strict-scripted requires --journal-sha256 and --board-head")
    try:
        result = audit(args.board, args.journal, expected_journal_sha256=args.journal_sha256,
                       expected_board_head=args.board_head,
                       renderer=render_scripted_prompt if args.strict_scripted else None)
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    result["audit_mode"] = "strict_scripted" if args.strict_scripted else "structural"
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
