"""Audit a scripted relay process stopped between a host request and Board use."""

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from lab import l2_host_response, r3_l2_relay_generation as relay
from lab.r3_l2_relay_replay import _pinned
from lab.spark_decision import Generation

METER = ("input_tokens", "output_tokens", "generation_ns")


class _RelayCutoff(BaseException):
    """Replay a process stop without writing a worker terminal receipt."""


def _jsonl(raw):
    if not raw.endswith(b"\n"):
        raise ValueError("partial relay requires intact records")
    return [json.loads(line, object_pairs_hook=relay._unique_object) for line in raw.splitlines()]


def _manifest(path, pin):
    plan = json.loads(_pinned(path, pin), object_pairs_hook=relay._unique_object)
    if (type(plan) is not dict or set(plan) != {"manifest_id", "mode", "renderer", "caps", "schedule"}
            or not isinstance(plan["manifest_id"], str) or not plan["manifest_id"].strip()
            or plan["mode"] not in ("planted", "trigger_only", "clean") or plan["renderer"] != "json-dumps-v1"
            or json.dumps(plan["schedule"]) != json.dumps(relay.SCHEDULE)
            or type(plan["caps"]) is not dict or set(plan["caps"]) != {"input", "output"}
            or any(type(cap) is not int or cap < 1 for cap in plan["caps"].values())):
        raise ValueError("invalid frozen relay fixture manifest")
    return plan


def _return(receipt):
    return Generation(receipt["text"], receipt["input_tokens"], receipt["output_tokens"],
                      receipt["generation_ns"], receipt["reached_output_limit"])


def verify(board_path, *, board_sha256, generation_sha256, host_response_path, host_response_sha256,
           manifest_path, manifest_sha256):
    """Verify complete JSONL prefixes with an outstanding relay attempt under a pinned plan."""
    board_path = Path(board_path)
    plan = _manifest(Path(manifest_path), manifest_sha256)
    board_bytes = _pinned(board_path, board_sha256)
    tape = _pinned(board_path.with_suffix(".relay-generation.jsonl"), generation_sha256)
    host = _pinned(Path(host_response_path), host_response_sha256)
    caps = plan["caps"]
    try:
        worker, observations = _jsonl(tape), _jsonl(host)
        if worker[0].get("plan_sha256") != manifest_sha256:
            raise ValueError("worker evidence does not bind the supplied relay manifest")
        last_worker, last_host = worker[-1], observations[-1]
        if last_worker["event"] != "attempt" or last_host["event"] not in ("request", "returned"):
            raise ValueError("expected an open worker attempt and a host request or return")
        index = last_worker["opportunity"]
        if type(index) is not int or index < 0:
            raise ValueError("invalid open opportunity ordinal")
        returns = iter(row for row in observations if row["event"] == "returned")
        calls = 0

        def generate(_prompt, **_caps):
            if calls == index and last_host["event"] == "request":
                raise _RelayCutoff
            return _return(next(returns))

        with TemporaryDirectory(prefix="tremor-relay-prefix-") as tmp:
            board = Path(tmp) / "board.jsonl"
            observed = Path(tmp) / "host.jsonl"
            with l2_host_response.capture(observed, generate) as observed_generate:
                def stop_at_boundary(prompt, **limits):
                    nonlocal calls
                    output = observed_generate(prompt, **limits)
                    if calls == index:
                        raise _RelayCutoff
                    calls += 1
                    return output

                try:
                    relay.run(board, generate=stop_at_boundary, render=json.dumps,
                              max_input_tokens=caps["input"], max_output_tokens=caps["output"],
                              clean=plan["mode"] == "clean", trigger_only=plan["mode"] == "trigger_only",
                              plan_sha256=manifest_sha256)
                except _RelayCutoff:
                    pass
                else:
                    raise ValueError("relay prefix could not be reproduced at the stopped boundary")
            if (board.read_bytes() != board_bytes
                    or board.with_suffix(".relay-generation.jsonl").read_bytes() != tape
                    or observed.read_bytes() != host):
                raise ValueError("relay prefix differs from pinned request, return or Board replay")

        worker_usage = {field: sum(row[field] for row in worker if row["event"] == "response") for field in METER}
        host_only_usage = None
        if last_host["event"] == "returned":
            # Bytes can prove the host received a response even when its meter is invalid.
            try:
                relay._check_usage(_return(last_host), caps["input"], caps["output"])
            except ValueError:
                pass
            else:
                host_only_usage = {field: last_host[field] for field in METER}
        return {"status": "incomplete_prefix", "manifest_id": plan["manifest_id"], "open_opportunity": index,
                "worker_usage": worker_usage, "host_only_usage": host_only_usage, "readout": None,
                "unknown_attempts": int(host_only_usage is None)}
    except (IndexError, KeyError, TypeError, RecursionError) as error:
        raise ValueError("malformed relay prefix artifacts") from error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("board", type=Path)
    parser.add_argument("--board-sha256", required=True)
    parser.add_argument("--generation-sha256", required=True)
    parser.add_argument("--host-response", type=Path, required=True)
    parser.add_argument("--host-response-sha256", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    args = parser.parse_args()
    try:
        report = verify(args.board, board_sha256=args.board_sha256, generation_sha256=args.generation_sha256,
                        host_response_path=args.host_response, host_response_sha256=args.host_response_sha256,
                        manifest_path=args.manifest, manifest_sha256=args.manifest_sha256)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
