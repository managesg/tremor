"""Capture exact FAKE transport digests and replay the B4 reservation archive."""

import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit
from unittest.mock import patch

from lab import ep1_b4_full_reservation as fixture
from tremor import backend_claude, ep1

CASE_NAMES = ("full-schedule", "no-room-for-rerun")
ARTIFACTS = ("wire.json", "price-sheet.json", "ledger/canary.jsonl", "ledger/ep1.jsonl", "ep1/schedule.json",
             "ep1/episodes.jsonl", "ep1/final.json")


def _require(condition, detail):
    if not condition:
        raise ValueError(detail)


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _json(data):
    def unique(pairs):
        value = dict(pairs)
        _require(len(value) == len(pairs), "duplicate archive JSON member")
        return value
    return json.loads(data, object_pairs_hook=unique)


def _wire_batch(entries, requests, batch, input_bound):
    while entries and entries[0]["kind"] == "batch_open":
        entries = entries[1:]
    _require(entries and entries[-1]["kind"] == "batch_stop" and entries[-1]["batch"] == batch,
             "missing ledger terminal batch event")
    _require(len(entries) == 2 * len(requests) + 1, "wire attempt and ledger terminal counts differ")
    charges, unknown, ids = [], [], []
    pending = None
    price = Decimal(0)
    for reserve, terminal, request in zip(entries[:-1:2], entries[1:-1:2], requests, strict=True):
        call = reserve["id"]
        _require(reserve["kind"] == "reserve" and terminal["id"] == call and call not in ids
                 and reserve["batch"] == request["batch"] == batch
                 and reserve["input_tokens_ub"] == request["bytes"] == input_bound
                 and reserve["max_tokens"] == fixture.OUTPUT_TOKENS,
                 "wire attempt differs from its unique reservation")
        digest = request["sha256"]
        _require(isinstance(digest, str) and len(digest) == 64 and all(c in "0123456789abcdef" for c in digest),
                 "wire request must carry a SHA-256 digest")
        if call.endswith("#r1"):
            _require(pending == (call[:-3], digest), "transport retry changed parent request bytes or identity")
        else:
            _require(pending is None, "transport retry missing from episode sequence")
        ids.append(call)
        pending = None
        if request["status"] == 200:
            usage = terminal["usage"]
            _require(terminal["kind"] == "charge" and terminal["request_sha256"] == digest
                     and terminal["request_bytes"] == input_bound and terminal["requested_model"] == reserve["model"]
                     and usage == request["usage"] == {"input_tokens": input_bound,
                                                       "output_tokens": fixture.OUTPUT_TOKENS,
                                                       "cache_read_input_tokens": 0,
                                                       "cache_creation_input_tokens": 0},
                     "charged usage or request digest differs from FAKE wire receipt")
            charges.append(call)
            price += Decimal(str(terminal["usd"]))
        else:
            _require(request["status"] == 503 and request["usage"] is None and terminal["kind"] == "unbilled_unknown"
                     and terminal["error"].startswith("HTTP 503 "), "unexpected FAKE outage or terminal receipt")
            unknown.append(call)
            price += Decimal(str(reserve["worst_usd"]))
            if not call.endswith("#r1"):
                pending = call, digest
    _require(pending is None, "unmatched first transport failure")
    return {"calls": ids, "charged": charges, "unmetered": unknown, "usd": price,
            "stop": entries[-1]["reason"]}


def _episode_meter(row, calls, charged):
    groups = list(dict.fromkeys(call.removesuffix("#r1") for call in calls))
    known = len(charged.intersection(calls))
    _require(groups == [turn["call_id"] for turn in row["turns"]], "ledger call identities differ from ordered turns")
    _require(row["calls"] == len(groups) and row["tokens"]["input"] == known * fixture.INPUT_BYTES
             and row["tokens"]["output"] == known * fixture.OUTPUT_TOKENS,
             "episode call or token summary differs from its ledger receipts")
    if row["ended"] == "complete":
        scorers = row["scorers"]
        _require(known == ep1.CALLS_PER_EPISODE and row["valid"] is True and row["void"] is None
                 and row["Y"] == scorers["alloc"]["Y"] == scorers["alloc2"]["Y"] == 0.25
                 and scorers["disagreement"] is None and scorers["third"]["status"] == "OK",
                 "invalid completed FAKE cell or three-scorer verdict")


def _case(content, name):
    wire, schedule, final = (_json(content[path]) for path in ("wire.json", "ep1/schedule.json", "ep1/final.json"))
    by_batch = {}
    for ordinal, request in enumerate(wire):
        _require(request["sequence"] == ordinal and request["batch"] in ("canary", "ep1"),
                 "unexpected wire attempt order")
        by_batch.setdefault(request["batch"], []).append(request)
    _require(list(by_batch) == ["canary", "ep1"] and wire[1:] == by_batch["ep1"], "unexpected nested batch order")
    outages = {i for i, request in enumerate(by_batch["ep1"], 1) if request["status"] != 200}
    _require(outages == (fixture.TRANSPORT_FAILURES if name == "full-schedule" else fixture.NO_ROOM_FAILURES),
             "wire failure sequence differs from the fixture")
    canary = _wire_batch([_json(line) for line in content["ledger/canary.jsonl"].splitlines()],
                         by_batch["canary"], "canary", 90_000)
    observed = _wire_batch([_json(line) for line in content["ledger/ep1.jsonl"].splitlines()],
                           by_batch["ep1"], "ep1", fixture.INPUT_BYTES)
    _require(canary["calls"] == canary["charged"] == ["canary:0"] and canary["stop"] == "complete",
             "nested canary failed to settle once")
    _require(schedule["dry_run"] is True and schedule["stamp"] == final["stamp"] == ep1.FAKE
             and schedule["schedule_seed"] == 0 and schedule["plan"] == ep1.plan("ep1", 0)
             and sorted(block["set"] for block in schedule["plan"]) == list(range(20))
             and all(sorted(block["order"]) == sorted(ep1.BASE_CONDS) for block in schedule["plan"]),
             "unexpected FAKE arm schedule")
    cells = [(block["set"], cond) for block in schedule["plan"] for cond in block["order"]]
    episodes = [_json(line) for line in content["ep1/episodes.jsonl"].splitlines()]
    episode_order = list(dict.fromkeys(call.split(":")[0] for call in observed["calls"]))
    _require(episode_order == [row["episode_id"] for row in episodes], "ledger attempts are not in episode order")
    charged, count_by_episode = set(observed["charged"]), {}
    for call in observed["calls"]:
        count_by_episode.setdefault(call.split(":")[0], []).append(call)
    position, aborts, reruns, pending = 0, 0, 0, False
    for row in episodes:
        _require(position < len(cells) and row["stamp"] == ep1.FAKE and row["evidence"] == "fake"
                 and row["seed"] == row["set"]
                 and (row["set"], row["cond"]) == cells[position]
                 and row["attempt"] == int(pending) and row["id_tag"] == ("r1" if pending else ""),
                 "episode schedule, seed or retry identity changed")
        _episode_meter(row, count_by_episode[row["episode_id"]], charged)
        reruns += pending
        pending = row["ended"] == "infrastructure_abort"
        if pending:
            aborts += 1
        else:
            _require(row["ended"] == "complete", "unexpected FAKE episode termination")
            position += 1
    reason, detail, expected_requests, expected_aborts, expected_reruns = (
        ("inconclusive", None, 496, 2, 2) if name == "full-schedule"
        else ("stopped:cap", "no_rerun_calls_left", 36, 1, 0)
    )
    calls = len(observed["calls"])
    tokens = fixture.CANARY_TOKENS + calls * (fixture.INPUT_BYTES + fixture.OUTPUT_TOKENS)
    total_usd = canary["usd"] + observed["usd"]
    ledger = final["ledger"]
    _require((final["reason"], final["detail"], observed["stop"]) == (reason, detail, reason)
             and (calls, aborts, reruns) == (expected_requests, expected_aborts, expected_reruns)
             and final["aborts"] == aborts and final["episodes"] == len(episodes)
             and ledger["calls"] == calls + 1 and ledger["tokens"] == tokens
             and ledger["price_sheet_sha256"] == _sha(content["price-sheet.json"])
             and ledger["caps"] == {"calls": 500, "tokens": 1_250_000, "usd": 5.0, "parent": None}
             and ledger["remaining"]["calls"] == 500 - ledger["calls"]
             and ledger["remaining"]["tokens"] == 1_250_000 - tokens
             and abs(Decimal(str(ledger["usd"])) - total_usd) < Decimal("0.000000000001"),
             "FAKE case terminal did not reconcile")
    if name == "full-schedule":
        _require(position == len(cells) and not pending, "full FAKE schedule did not complete")
    else:
        remaining = ledger["caps"]["calls"] - ledger["calls"]
        required = (len(cells) - position) * ep1.CALLS_PER_EPISODE
        _require(pending and required == remaining + 1, "no-room fixture does not cross by exactly one request")
    return {"reason": reason, "detail": detail, "ep1_wire_attempts": calls, "charged_replies": len(charged),
            "unmetered_attempts": len(observed["unmetered"]), "nested_reserved_tokens": tokens,
            "episodes": len(episodes), "completed_cells": position, "reruns": reruns}


def audit(root, *, seal_sha256):
    root = Path(root)
    data = (root / "seal.json").read_bytes()
    _require(_sha(data) == seal_sha256, "external FAKE archive seal mismatch")
    seal = _json(data)
    _require(set(seal) == set(CASE_NAMES), "archive must contain both registered FAKE fixtures")
    result = {}
    for name in CASE_NAMES:
        content = {path: (root / name / path).read_bytes() for path in ARTIFACTS}
        _require({path: _sha(raw) for path, raw in content.items()} == seal[name], "sealed artifact digest mismatch")
        result[name] = _case(content, name)
    return {"evidence": "FAKE_wire_receipt_audit", "scientific_acceptance": False, "seal_sha256": seal_sha256,
            "cases": result}


def capture(root):
    root = Path(root)
    root.mkdir()
    original = backend_claude.ClaudeClient._post
    seal = {}
    for name, failures, calls, aborts in (
        ("full-schedule", fixture.TRANSPORT_FAILURES, 496, 2),
        ("no-room-for-rerun", fixture.NO_ROOM_FAILURES, 36, 1),
    ):
        wire = []

        def observe(client, body, timeout):
            _require(urlsplit(client.base_url).hostname == "127.0.0.1", "FAKE capture refuses non-loopback targets")
            status, response = original(client, body, timeout)
            wire.append({"sequence": len(wire), "batch": client.ledger.batch, "bytes": len(body),
                         "sha256": _sha(body), "status": status, "usage": response.get("usage") if status == 200 else None})
            return status, response

        with patch.object(backend_claude.ClaudeClient, "_post", observe):
            fixture.run_probe(root, name, failures, calls, aborts)
        with (root / name / "wire.json").open("x") as stream:
            json.dump(wire, stream, sort_keys=True)
        seal[name] = {path: _sha((root / name / path).read_bytes()) for path in ARTIFACTS}
    data = json.dumps(seal, sort_keys=True).encode()
    with (root / "seal.json").open("xb") as stream:
        stream.write(data)
    return audit(root, seal_sha256=_sha(data))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--capture", action="store_true")
    mode.add_argument("--seal-sha256")
    args = parser.parse_args()
    try:
        result = capture(args.directory) if args.capture else audit(args.directory, seal_sha256=args.seal_sha256)
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
