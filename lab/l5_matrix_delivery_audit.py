"""Independently join isolated CPU delivery receipts to an archived L5 matrix."""

import argparse
import hashlib
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory

from lab import l5_matrix, l5_matrix_audit as matrix


HEX_DIGEST = re.compile(r"[0-9a-f]{64}")
IDENTITY_FIELDS = ("block_id", "condition", "arm_id")
DENIED_READS = ("foreign", "unknown", "bulk", "forged")
GUIDE = "claim before work"
TAPE = "delivery-attempts.jsonl"
TAPE_LIMIT = 256 * 1024
EVENT_FIELDS = {"attempt": {"frame"}, "created": {"container_id"},
                "ack": {"container_id", "worker_receipt"}, "cleanup": {"container_id"}, "stop": {"stage"}}
STOPS_AFTER = {"attempt": {"preflight", "create"}, "created": {"attach", "reap", "cleanup"},
               "ack": {"reap", "cleanup"}, "cleanup": {"exchange"}}


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _main_prefixes(arm, row, workers, work):
    trace = matrix._trace(arm / "board.jsonl", row["board_head"], row["board_event_count"])
    commits = [event for event in trace if event["type"] == "end_round"]
    matrix._require([event["round"] for event in commits] == list(range(5)),
                    "delivery evidence requires the contended three-phase Board path")
    pre, post, settled = commits[1:4]
    target = row["perturbed_task"]
    claims = matrix._claim_history(trace)
    holder = claims[2].get(target)
    matrix._require(holder == workers[1] and claims[3].get(target) == (None if row["disrupted"] else holder),
                    "delivery boundary did not preserve the expected opening and intervention states")

    recovery_expected = row["carrier"] == "environment" and row["disrupted"]
    pending = trace[post["seq"] + 1:settled["seq"]]
    if recovery_expected:
        matrix._require(len(pending) == 1 and pending[0]["round"] == 3
                        and pending[0]["type"] == "claim" and pending[0]["agent"] == holder
                        and pending[0]["data"] == {"item": target} and claims[4].get(target) == holder,
                        "isolated guide did not lead into the committed recovery claim")
    else:
        matrix._require(not pending and claims[4].get(target) == claims[3].get(target),
                        "clean or neutral arm changed the claim during the recovery window")

    matrix._require([(event["phase"], event["round"]) for event in work]
                    == [("pre", 2), *([("post", 4)] * (len(workers) - 1))],
                    "work did not occur in the opening and post-recovery windows")
    target_work = [event for event in work if event["action"]["task"] == target]
    expected_status = "violation_executed" if row["carrier"] == "neutral" and row["disrupted"] else "admitted"
    matrix._require(len(target_work) == 1 and target_work[0]["phase"] == "post"
                    and target_work[0]["round"] == 4 and target_work[0]["action"]["agent"] == holder
                    and target_work[0]["status"] == expected_status,
                    "target work was not observed after the recovery boundary")

    prefixes = {("pre", worker): pre for worker in workers}
    target_position = workers.index(holder)
    for index, worker in enumerate(workers):
        prefixes["post", worker] = pending[0] if recovery_expected and index > target_position else post
    return prefixes


def _delivery_trace(arm, row, workers):
    raw = (arm / "delivery.jsonl").read_bytes().splitlines(keepends=True)
    receipt = row["delivery_board"]
    trace = matrix._trace(arm / "delivery.jsonl", receipt["head"], receipt["event_count"])
    matrix._require(len(raw) == len(trace) and all(line.endswith(b"\n") for line in raw),
                    "named read log does not contain complete raw records")
    count = len(workers)
    expected_types = ["init", *(["post"] * count), "end_round", *(["read"] * count),
                      "end_round", *(["read"] * count)]
    matrix._require([event["type"] for event in trace] == expected_types,
                    "environment delivery log changed its pre/post visibility windows")
    opened = trace[1:count + 1]
    posts = {event["data"]["id"]: event for event in opened}
    matrix._require(len(posts) == count and all(event["data"]["refs"] == [worker]
                    and not event["data"]["supersedes"] for event, worker in zip(opened, workers, strict=True)),
                    "environment intervention changed the committed guide inventory")
    return raw, trace, posts


def _frames(directory, summary):
    for row in summary["rows"]:
        if row["carrier"] not in ("environment", "neutral"):
            continue
        arm = directory / row["arm_id"]
        work = [event for event in row["dispatch"] if event["action"]["type"] == "work"]
        workers = [event["action"]["agent"] for event in work]
        matrix._require(len(workers) == len(set(workers)) == row["taskset"]["n_agents"],
                        "delivery roster differs from the matched work roster")
        expected_order = [(phase, worker) for phase in ("pre", "post") for worker in workers]
        matrix._require(expected_order == [(entry["phase"], entry["worker"]) for entry in row["exposure"]],
                        "unexpected archived worker or phase delivery order")
        prefixes = _main_prefixes(arm, row, workers, work)
        environment = row["carrier"] == "environment"
        if environment:
            raw, delivery, posts = _delivery_trace(arm, row, workers)
        for exposure in row["exposure"]:
            worker, phase = exposure["worker"], exposure["phase"]
            prefix = prefixes[phase, worker]
            frame = {name: row[name] for name in IDENTITY_FIELDS}
            frame.update(worker=worker, phase=phase, item=None, delivery_read_seq=None, delivery_read_sha256=None,
                         board_head=prefix["hash"], board_event_count=prefix["seq"] + 1, guide_sha256=None)
            matrix._require(exposure["guide_consumed"] is environment, "archived delivery changed guide consumption")
            if environment:
                seq, item = exposure["read_event_seq"], exposure["item"]
                event, post = delivery[seq], posts[item]
                matrix._require(post["round"] == 0 and post["data"]["text"] == GUIDE
                                and event["round"] == (1 if phase == "pre" else 2),
                                "named read did not deliver the retained guide at the prescribed phase")
                frame.update(item=item, delivery_read_seq=seq, delivery_read_sha256=_sha(raw[seq]),
                             guide_sha256=_sha(post["data"]["text"].encode()))
            yield frame


def _verify_receipt(row, frame, containers):
    matrix._require(isinstance(row, dict) and set(row) == {"frame", "worker_receipt", "container_id", "removed"},
                    "invalid isolated receipt row")
    witnessed = row["frame"]
    matrix._require(isinstance(witnessed, dict) and type(witnessed.get("board_event_count")) is int
                    and (frame["delivery_read_seq"] is None or type(witnessed.get("delivery_read_seq")) is int)
                    and witnessed == frame, "isolated receipt does not bind the archived delivery frame")
    identity = row["container_id"]
    matrix._require(isinstance(identity, str) and HEX_DIGEST.fullmatch(identity) and identity not in containers
                    and row["removed"] is True, "isolated receipt has missing, repeated or unremoved container")
    containers.add(identity)
    _verify_ack(row["worker_receipt"], frame)


def _verify_ack(receipt, frame):
    observations = dict.fromkeys(DENIED_READS)
    observations["own"] = frame["guide_sha256"]
    matrix._require(isinstance(receipt, dict) and receipt.get("worker_mount_readonly") is True
                    and receipt == {"sessions": [{"condition": frame["condition"], "phase": frame["phase"],
                                                  "observations": observations}], "worker_mount_readonly": True},
                    "isolated worker's returned shard observations are incomplete or inconsistent")


def _replay_frames(directory, plan_sha256):
    plan = matrix._pinned_json(directory / "plan.json", plan_sha256)
    matrix._require(plan["contended"] is True, "expected the contended public delivery plan")
    frames = []

    def observe(frame, _guide):
        arm = replay / frame["arm_id"]
        board = (arm / "board.jsonl").read_bytes()
        delivery = (arm / "delivery.jsonl").read_bytes() if frame["delivery_read_seq"] is not None else None
        frames.append((frame, board, delivery))
        return frame["guide_sha256"]

    with TemporaryDirectory(prefix="tremor-l5-delivery-prefix-") as scratch:
        replay = Path(scratch) / "matrix"
        l5_matrix.run(replay, seed=plan["schedule"]["seed"], contended=True, verify_delivery=observe)
        matrix._require(_sha((replay / "plan.json").read_bytes()) == plan_sha256,
                        "delivery plan does not reproduce the exact public fixture")
    return frames


def _verify_frame(directory, frame, expected, board, delivery):
    matrix._require(type(frame) is dict and type(frame.get("board_event_count")) is int
                    and (expected["delivery_read_seq"] is None or type(frame.get("delivery_read_seq")) is int)
                    and frame == expected, "delivery attempt differs from the exact scripted frame")
    arm = directory / frame["arm_id"]
    identity = {key: frame[key] for key in IDENTITY_FIELDS}
    matrix._require(json.loads((arm / "intent.json").read_bytes()) == identity,
                    "delivery attempt differs from the archived arm intent")
    with (arm / "board.jsonl").open("rb") as stream:
        matrix._require(stream.read(len(board)) == board,
                        "delivery attempt does not bind the retained Board prefix")
    if delivery is not None:
        with (arm / "delivery.jsonl").open("rb") as stream:
            matrix._require(stream.read(len(delivery)) == delivery,
                            "delivery attempt does not bind the retained named read")


def _unique_keys(pairs):
    result = dict(pairs)
    matrix._require(len(result) == len(pairs), "duplicate delivery tape JSON member")
    return result


def verify_prefix(directory, *, plan_sha256, tape, tape_sha256):
    """Reconcile public attempts and monotonic time from intent through confirmed cleanup."""
    directory = Path(directory)
    with Path(tape).open("rb") as stream:
        raw = stream.read(TAPE_LIMIT + 1)
    matrix._require(0 < len(raw) <= TAPE_LIMIT and _sha(raw) == tape_sha256,
                    "invalid or unpinned delivery attempt tape")
    prefix, _, tail = raw.rpartition(b"\n")
    matrix._require(prefix or tail, "empty delivery attempt tape")
    frames = _replay_frames(directory, plan_sha256)
    attempts = []
    identities = set()
    previous_clock, previous = 0, None
    for line in prefix.splitlines():
        row = json.loads(line, object_pairs_hook=_unique_keys)
        matrix._require(type(row) is dict, "expected a delivery event object")
        event, timestamp = row.get("event"), row.get("monotonic_ns")
        matrix._require(type(event) is str and event in EVENT_FIELDS
                        and row.keys() == EVENT_FIELDS[event] | {"event", "ordinal", "monotonic_ns"}
                        and type(row["ordinal"]) is int and type(timestamp) is int and timestamp >= previous_clock,
                        "invalid delivery event fields, ordinal or monotonic time")
        if event == "attempt":
            ordinal = len(attempts)
            matrix._require(row["ordinal"] == ordinal < len(frames) and (
                previous is None or (previous == "cleanup" and current["acknowledgment_observed"])),
                "delivery attempt is out of schedule or follows unfinished delivery")
            frame, board, delivery = frames[ordinal]
            _verify_frame(directory, row["frame"], frame, board, delivery)
            current = {key: frame[key] for key in (*IDENTITY_FIELDS, "worker", "phase")}
            current.update(ordinal=ordinal, container_id=None, acknowledgment_observed=False,
                           cleanup_confirmed=None, transport_wall_ns=None)
            attempts.append(current)
            start_clock = timestamp
        else:
            matrix._require(attempts and row["ordinal"] == current["ordinal"] and previous != "stop",
                            "delivery event is outside its active attempt")
            if event == "created":
                identity = row["container_id"]
                matrix._require(previous == "attempt" and isinstance(identity, str)
                                and HEX_DIGEST.fullmatch(identity) and identity not in identities,
                                "invalid or reused delivery container identity")
                identities.add(identity)
                current["container_id"] = identity
            elif event in ("ack", "cleanup"):
                allowed = ("created",) if event == "ack" else ("created", "ack")
                matrix._require(previous in allowed and row["container_id"] == current["container_id"],
                                "delivery acknowledgment or cleanup is out of order or has wrong container ID")
                if event == "ack":
                    _verify_ack(row["worker_receipt"], frame)
                    current["acknowledgment_observed"] = True
                else:
                    matrix._require(timestamp > start_clock, "delivery cleanup gives no elapsed interval")
                    current["cleanup_confirmed"] = True
                    current["transport_wall_ns"] = timestamp - start_clock
            else:
                matrix._require(type(row["stage"]) is str and row["stage"] in STOPS_AFTER[previous]
                                and (previous != "cleanup" or not current["acknowledgment_observed"]),
                                "delivery stop stage contradicts the observed events")
        current["observed_stage"] = row["stage"] if event == "stop" else event
        previous_clock, previous = timestamp, event
    uncertainty = sum(attempt["transport_wall_ns"] is None for attempt in attempts)
    complete = not tail and len(attempts) == len(frames) and previous == "cleanup" and current["acknowledgment_observed"]
    return {"evidence": "scripted_cpu_delivery_prefix", "plan_sha256": plan_sha256, "tape_sha256": tape_sha256,
            "status": "all_deliveries_observed" if complete else "incomplete",
            "planned_attempts": len(frames), "observed_attempts": attempts, "unknown_transport_wall_attempts": uncertainty,
            "unparsed_tail_bytes": len(tail),
            "transport_wall_ns": None if uncertainty or tail else sum(attempt["transport_wall_ns"] for attempt in attempts),
            "comparison": None, "authorizes_execution": False, "scientific_result": False}


def verify(directory, *, summary_sha256, sidecar, sidecar_sha256):
    directory, sidecar = Path(directory), Path(sidecar)
    ordinary = matrix.audit(directory, summary_sha256=summary_sha256)
    matrix._require((ordinary["arms"], ordinary["work_attempts"], ordinary["named_reads"]) == (20, 120, 96),
                    "delivery evidence requires a complete one-block-per-size matrix")
    summary = matrix._pinned_json(directory / "summary.json", summary_sha256)
    plan = matrix._pinned_json(directory / "plan.json", summary["plan_sha256"])
    matrix._require(plan.get("contended") is True, "delivery evidence requires the contended matrix")
    data = matrix._pinned_json(sidecar, sidecar_sha256)
    matrix._require(isinstance(data, dict) and set(data) == {"evidence", "summary_sha256", "worker_sha256", "rows"}
                    and data["evidence"] == "scripted_cpu_matrix_delivery" and data["summary_sha256"] == summary_sha256,
                    "delivery sidecar does not attest the externally pinned matrix")
    worker = sidecar.parent / "worker.py"
    matrix._require(isinstance(data["worker_sha256"], str) and HEX_DIGEST.fullmatch(data["worker_sha256"])
                    and not worker.is_symlink() and _sha(worker.read_bytes()) == data["worker_sha256"],
                    "saved worker script does not match the sidecar pin")
    frames = list(_frames(directory, summary))
    matrix._require(isinstance(data["rows"], list) and len(data["rows"]) == len(frames) == 96,
                    "delivery sidecar has missing or unexpected witness rows")
    containers = set()
    for row, frame in zip(data["rows"], frames, strict=True):
        _verify_receipt(row, frame, containers)
    return {**ordinary, "delivery_witnesses": len(frames), "worker_sha256": data["worker_sha256"],
            "sidecar_sha256": sidecar_sha256}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("matrix", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--summary-sha256")
    mode.add_argument("--plan-sha256")
    parser.add_argument("--sidecar", type=Path)
    parser.add_argument("--sidecar-sha256")
    parser.add_argument("--tape", type=Path)
    parser.add_argument("--tape-sha256")
    args = parser.parse_args()
    try:
        if args.plan_sha256 is not None:
            if args.tape is None or args.tape_sha256 is None or args.sidecar or args.sidecar_sha256:
                parser.error("--plan-sha256 requires --tape and --tape-sha256")
            report = verify_prefix(args.matrix, plan_sha256=args.plan_sha256, tape=args.tape,
                                   tape_sha256=args.tape_sha256)
        else:
            if args.sidecar is None or args.sidecar_sha256 is None or args.tape or args.tape_sha256:
                parser.error("--summary-sha256 requires --sidecar and --sidecar-sha256")
            report = verify(args.matrix, summary_sha256=args.summary_sha256, sidecar=args.sidecar,
                            sidecar_sha256=args.sidecar_sha256)
    except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
        parser.exit(2, f"{error}\n")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
