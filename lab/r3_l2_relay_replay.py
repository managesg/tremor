"""Replay a pinned scripted relay board and generation tape without model calls."""

import argparse
from contextlib import nullcontext
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from tempfile import TemporaryDirectory

from lab import l2_host_response, r3_l2_relay_generation as relay
from lab.spark_decision import Generation

FIXTURE_BYTE_LIMIT = 1024 * 1024


def _artifact_bytes(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > FIXTURE_BYTE_LIMIT:
            raise ValueError(f"invalid relay artifact: {path.name}")
        raw = stream.read(FIXTURE_BYTE_LIMIT + 1)
    if len(raw) != info.st_size:
        raise ValueError(f"relay artifact size changed while reading: {path.name}")
    return raw


def _pinned(path, digest):
    if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        raise ValueError("expected SHA-256 pin for each relay artifact")
    raw = _artifact_bytes(path)
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError(f"relay artifact digest mismatch: {path.name}")
    return raw


def verify(board_path, *, board_sha256, generation_sha256, render,
           host_response_path=None, host_response_sha256=None):
    """Match every archived event to a deterministic replay using a trusted renderer."""
    board_path = Path(board_path)
    board_bytes = _pinned(board_path, board_sha256)
    tape = _pinned(board_path.with_suffix(".relay-generation.jsonl"), generation_sha256)
    if (host_response_path is None) != (host_response_sha256 is None):
        raise ValueError("host response verification needs its path and independent SHA-256 pin")
    host = _pinned(Path(host_response_path), host_response_sha256) if host_response_path is not None else None
    if not callable(render) or not tape.endswith(b"\n"):
        raise ValueError("relay renderer and complete JSONL records are required")
    try:
        records = [json.loads(line, object_pairs_hook=relay._unique_object) for line in tape.splitlines()]
        header = records[0]
        if type(header["planted_roots"]) is not list or header["event"] != "start":
            raise ValueError("missing relay start receipt")
        caps = header["caps"]
        if host is None:
            responses = iter(row for row in records[1:] if row["event"] in ("response", "incomplete"))
        else:
            observations = [json.loads(line, object_pairs_hook=relay._unique_object) for line in host.splitlines()]
            responses = iter(row for row in observations if row["event"] in ("returned", "failed"))

        def generate(_prompt, **_caps):
            row = next(responses)
            if row["event"] in ("incomplete", "failed"):
                failure = row.get("failure" if host is None else "error_type")
                if not isinstance(failure, str) or not failure.isidentifier() or len(failure) > 128:
                    raise ValueError("invalid recorded generation failure")
                raise type(failure, (Exception,), {})()
            return Generation(row["raw" if host is None else "text"], row["input_tokens"], row["output_tokens"],
                              row["generation_ns"], row["reached_output_limit"])

        with TemporaryDirectory(prefix="tremor-relay-replay-") as folder:
            replayed = Path(folder) / "board.jsonl"
            observed = Path(folder) / "host.jsonl"
            capture = l2_host_response.capture(observed, generate) if host is not None else nullcontext(generate)
            mode = ({"trigger_only": True} if header.get("trigger_only") is True
                    else {"clean": not header["planted_roots"]})
            with capture as source:
                report = relay.run(replayed, generate=source, render=render,
                                   max_input_tokens=caps["input"], max_output_tokens=caps["output"],
                                   plan_sha256=header.get("plan_sha256"), **mode)
            if host is not None and observed.read_bytes() != host:
                raise ValueError("host request or return differs from pinned response replay")
            if replayed.with_suffix(".relay-generation.jsonl").read_bytes() != tape:
                raise ValueError("generation tape differs from independent request, usage or terminal replay")
            if replayed.read_bytes() != board_bytes:
                raise ValueError("board differs from replay of the recorded generation")
    except (IndexError, KeyError, TypeError, RecursionError) as error:
        raise ValueError("malformed relay capture") from error
    if host is not None:
        report["host_responses_verified"] = True
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("board", type=Path)
    parser.add_argument("--board-sha256", required=True)
    parser.add_argument("--generation-sha256", required=True)
    parser.add_argument("--host-response", type=Path)
    parser.add_argument("--host-response-sha256")
    args = parser.parse_args()
    try:
        report = verify(args.board, board_sha256=args.board_sha256, generation_sha256=args.generation_sha256,
                        render=json.dumps, host_response_path=args.host_response,
                        host_response_sha256=args.host_response_sha256)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    if report["readout"] is not None:
        report["readout"].pop("trace")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
