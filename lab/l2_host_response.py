"""Host-side capture and replay of raw responses for an L2 scripted arm."""

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re

from lab import l2_generation_audit, r3_l2_host_verify
from tremor.board import read_log

USAGE = ("input_tokens", "output_tokens", "generation_ns", "reached_output_limit")


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _sha(data):
    return hashlib.sha256(data).hexdigest()


@contextmanager
def capture(path, generate):
    """Give the fixture a callback that retains generator returns on the host."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        sequence = 0

        def record(row):
            stream.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())

        def observed(prompt, *, max_input_tokens, max_output_tokens):
            nonlocal sequence
            identity = {"attempt": sequence, "prompt_sha256": _sha(prompt.encode())}
            sequence += 1
            limits = {"max_input_tokens": max_input_tokens, "max_output_tokens": max_output_tokens}
            record({"event": "request", **identity, **limits})
            try:
                output = generate(prompt, **limits)
            except Exception as error:
                record({"event": "failed", **identity, "error_type": type(error).__name__})
                raise
            record({"event": "returned", **identity, "text": output.text,
                    **{key: getattr(output, key) for key in USAGE}})
            return output

        yield observed


def _json_object(text):
    def unique(pairs):
        result = dict(pairs)
        _require(len(result) == len(pairs), "duplicate JSON member")
        return result

    try:
        value = json.loads(text, object_pairs_hook=unique)
    except (ValueError, RecursionError):
        return None
    return value if type(value) is dict else None


def _valid_usage(receipt, limits):
    return (type(receipt["text"]) is str
            and type(receipt["input_tokens"]) is int
            and 0 < receipt["input_tokens"] <= limits["max_input_tokens"]
            and type(receipt["output_tokens"]) is int
            and 0 < receipt["output_tokens"] <= limits["max_output_tokens"]
            and type(receipt["generation_ns"]) is int and receipt["generation_ns"] >= 0
            and receipt["reached_output_limit"] is (receipt["output_tokens"] == limits["max_output_tokens"]))


def _verified_returns(host, journal):
    """Bind independent observations to the exact scheduled prompt and usage."""
    limits = {key: journal[0][key] for key in ("max_input_tokens", "max_output_tokens")}
    attempts = [entry for entry in journal if entry["event"] == "start"]
    terminals = {(entry["worker"], entry["stage"]): entry for entry in journal
                 if entry["event"] in ("completed", "failed")}
    index = 0
    for ordinal, attempt in enumerate(attempts):
        identity = {"attempt": ordinal, "prompt_sha256": attempt["prompt_sha256"]}
        terminal = terminals.get((attempt["worker"], attempt["stage"]))
        if index == len(host) and terminal is None:
            # The process can stop after journaling a start and before invoking the generator.
            break
        _require(index < len(host) and host[index] == {"event": "request", **identity, **limits},
                 "host request does not match scheduled prompt and caps")
        index += 1
        if terminal is None:
            if index < len(host):
                receipt = host[index]
                index += 1
                _require(all(receipt[key] == value for key, value in identity.items())
                         and receipt["event"] in ("returned", "failed"), "unexpected open-attempt observation")
                if receipt["event"] == "returned" and _valid_usage(receipt, limits):
                    yield None, receipt
            break
        _require(index < len(host), "generation terminal lacks a host response")
        receipt = host[index]
        index += 1
        _require(all(receipt[key] == value for key, value in identity.items()), "host response belongs to another attempt")
        if terminal["event"] == "failed":
            if receipt["event"] == "returned":
                _require(terminal["error_type"] == "ValueError" and not _valid_usage(receipt, limits),
                         "valid host return cannot be credited as a validator rejection")
            else:
                _require(receipt == {"event": "failed", **identity, "error_type": terminal["error_type"]},
                         "host failure differs from the generation journal")
            continue
        _require(receipt["event"] == "returned" and type(receipt["text"]) is str
                 and _sha(receipt["text"].encode()) == terminal["reply_sha256"]
                 and all(type(receipt[key]) is type(terminal[key]) and receipt[key] == terminal[key] for key in USAGE),
                 "host response bytes or usage differ from the generation journal")
        proposal = _json_object(receipt["text"])
        _require((proposal is not None) is terminal["json_object"], "raw response parses differently")
        yield terminal, None if terminal["held_at_limit"] else proposal
    _require(index == len(host), "unmatched host response evidence")


def replay(board, journal, responses, *, board_head, journal_sha256, responses_sha256):
    """Recompute matched-warning-arm adoption from host-observed responses."""
    _require(all(type(pin) is str and re.fullmatch(r"[0-9a-f]{64}", pin)
                 for pin in (board_head, journal_sha256, responses_sha256)), "all three external pins are required")
    raw = Path(responses).read_bytes()
    _require(_sha(raw) == responses_sha256, "external host response digest mismatch")
    meter = l2_generation_audit.audit(board, journal, expected_journal_sha256=journal_sha256,
                                      expected_board_head=board_head,
                                      renderer=l2_generation_audit.render_scripted_prompt)
    _require(meter["condition"] in ("warning", "neutral"), "response replay expects a matched warning arm")
    rows = [json.loads(line) for line in Path(journal).read_bytes().splitlines()]
    host = [json.loads(line) for line in raw.splitlines()]
    decisions, requested = [], set()
    host_only_return = None
    for turn, proposal in _verified_returns(host, rows):
        if turn is None:
            host_only_return = {key: proposal[key] for key in USAGE}
            continue
        worker, source = turn["worker"], turn["observed_source_id"]
        if turn["stage"] == "initial" and proposal == {"action": "verify"} and "reference_sha256" in rows[0]:
            requested.add(worker)
        if (proposal is not None and set(proposal) == {"value", "source_id"}
                and proposal["source_id"] == source and type(proposal["value"]) is str
                and re.fullmatch(r"[a-z]{1,16}", proposal["value"])):
            decisions.append((worker, source, proposal["value"]))

    received = {row["worker"] for row in rows if row["event"] == "reference_read"}
    _require(received <= requested, "Board reference read lacks an observed verification request")
    stats = {**meter, "response_sha256": responses_sha256, "replayed_decisions": len(decisions),
             "host_only_return_usage": host_only_return}
    if meter["status"] != "completed":
        return {**stats, "exposures": None, "adoptions": None}
    _require(received == requested, "observed verification request lacks a Board reference read")
    trace = read_log(board)
    recorded = [(event["agent"], event["data"]["refs"], event["data"]["text"])
                for event in trace if event["type"] == "post" and event["data"]["kind"] == "decision"]
    _require(recorded == [(worker, [source], value) for worker, source, value in decisions],
             "Board decisions differ from independently parsed host responses")
    parent, = [event["data"]["id"] for event in trace if event["type"] == "post" and event["round"] == 0
               and event["data"]["kind"] == "plant" and event["data"]["text"] == "Marker: blue"]
    exposed = {event["agent"] for event in trace if event["type"] == "read" and event["round"] == 1
               and event["data"] == {"item": parent, "n": 1}}
    adoptions = sum(worker in exposed and source == parent and value == "blue" for worker, source, value in decisions)
    return {**stats, "exposures": len(exposed), "adoptions": adoptions}


def verify_archive(export, *, schedule, archive_id, observed_pins, response_pins, frozen_governance=None):
    """Verify every scripted export arm against its separate host-owned response file."""
    export = Path(export).absolute()
    _require(set(response_pins) == set(observed_pins), "host response pins must cover every scheduled arm")
    custody = {}
    for key, (response, digest) in response_pins.items():
        path = Path(response).absolute()
        _require(path.resolve(strict=True) == path and path.is_file() and path.stat().st_nlink == 1
                 and not path.is_relative_to(export), "host response files must be outside the export")
        custody[key] = path, digest
    _require(len({path for path, _ in custody.values()}) == len(custody), "response file reused across arms")
    verified = r3_l2_host_verify.verify(export, schedule=schedule, archive_id=archive_id,
                                        observed_pins=observed_pins, frozen_governance=frozen_governance,
                                        renderer=l2_generation_audit.render_scripted_prompt)
    for receipt in verified["arms"]:
        identity = receipt["identity"]
        response, digest = custody[identity["block_id"], identity["arm_position"]]
        receipt["raw_replay"] = replay(export / receipt["board"], export / receipt["journal"], response,
                                       board_head=receipt["board_head"], journal_sha256=receipt["journal_sha256"],
                                       responses_sha256=digest)
    evidence = ("scripted_host_response_governed_verified" if frozen_governance is not None
                else "scripted_host_response_verified")
    return {**verified, "evidence": evidence}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("board", type=Path)
    parser.add_argument("journal", type=Path)
    parser.add_argument("responses", type=Path)
    parser.add_argument("--board-head", required=True)
    parser.add_argument("--journal-sha256", required=True)
    parser.add_argument("--responses-sha256", required=True)
    args = parser.parse_args()
    try:
        result = replay(args.board, args.journal, args.responses, board_head=args.board_head,
                        journal_sha256=args.journal_sha256, responses_sha256=args.responses_sha256)
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
