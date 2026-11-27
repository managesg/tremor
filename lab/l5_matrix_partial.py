"""Verify a public L5 matrix interrupted at a recorded pre-dispatch barrier."""

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import select
import signal
import subprocess
import sys
from tempfile import TemporaryDirectory

from lab import l5_grader_custody as custody, l5_matrix, l5_matrix_custody
from lab.r3_cpu_guard_replay import _sha, _write
from lab.r3_l2_relay_replay import _artifact_bytes, _pinned
from tremor.board import read_log

ARM = "arm-01"
ORDINAL = 1
PLAN = "fixture-plan.json"
STOP = "host-stop.json"
TAPE = l5_matrix_custody.TAPE


class _Cutoff(BaseException):
    """Reproduce the exact stop during verification without a model or signal."""


def _plan(seed):
    custody._require(type(seed) is int and seed >= 0, "partial fixture seed must be a nonnegative integer")
    return {"seed": seed, "fixture": "scripted_l5_before_dispatch", "contended": True, "full_cycle": False,
            "arm_id": ARM, "ordinal": ORDINAL, "instrument_sha256": l5_matrix_custody._instrument_digest(),
            "cutoff_instrument_sha256": _sha(Path(__file__).read_bytes())}


def _produce(matrix, plan, at_barrier):
    @contextmanager
    def observe_arm(path, identity, _taskset):
        ordinal = 0
        with (path / TAPE).open("x", encoding="utf-8") as tape:
            def record(row):
                tape.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
                tape.flush()
                os.fsync(tape.fileno())

            def observe(phase, board_path, action, before):
                nonlocal ordinal
                with board_path.open("rb") as persisted:
                    os.fsync(persisted.fileno())
                trace = read_log(board_path)
                attempt = {"ordinal": ordinal, "phase": phase, "round": before["round"],
                           "board_head": trace[-1]["hash"], "board_events": len(trace),
                           "action_sha256": custody.digest(action)}
                record({"event": "attempt", **attempt})
                if identity["arm_id"] == ARM and ordinal == ORDINAL:
                    at_barrier()
                    raise AssertionError("the stop barrier unexpectedly released the worker")
                ordinal += 1

                def complete(status, reason):
                    record({"event": "result", "ordinal": attempt["ordinal"], "dispatch": status,
                            "reason": reason, "attempt_sha256": custody.digest(attempt)})
                return complete
            yield observe
    l5_matrix.run(matrix, seed=plan["seed"], contended=plan["contended"],
                  full_cycle=plan["full_cycle"], observe_arm=observe_arm)


def _inventory(root):
    entries = {}
    matrix = root / "matrix"
    custody._require(matrix.is_dir() and not matrix.is_symlink(), "missing or linked partial matrix directory")
    for path in matrix.rglob("*"):
        custody._require(not path.is_symlink(), "unexpected link in the partial matrix")
        if not path.is_dir():
            entries[path.relative_to(root).as_posix()] = _sha(_artifact_bytes(path))
            custody._require(len(entries) <= 64, "too many files in the partial matrix")
    return entries


def _load_plan(root, pin):
    plan = json.loads(_pinned(root / PLAN, pin))
    custody._require(plan == _plan(plan["seed"]), "partial matrix plan differs from its fixture")
    return plan


def _worker(root, pin):
    plan = _load_plan(root, pin)

    def hold():
        print("pre_dispatch", flush=True)
        signal.pause()

    _produce(root / "matrix", plan, hold)


def run(root, *, seed=17):
    """Stop one actual CPU child while its second arm waits before dispatch."""
    root = Path(root).absolute()
    root.mkdir(mode=0o700)
    plan_pin = _write(root / PLAN, _plan(seed))
    with (root / "worker.stderr").open("xb") as errors:
        with subprocess.Popen([sys.executable, "-B", "-m", "lab.l5_matrix_partial", str(root), "--worker", plan_pin],
                              stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=errors) as child:
            try:
                custody._require(select.select([child.stdout], [], [], 8)[0] and
                                 os.read(child.stdout.fileno(), 64) == b"pre_dispatch\n" and child.poll() is None,
                                 "scripted CPU child did not reach its pre-dispatch barrier")
            finally:
                if child.poll() is None:
                    child.kill()
                child.wait(timeout=2)
    custody._require(child.returncode == -signal.SIGKILL, "scripted CPU child did not stop with SIGKILL")
    stop_pin = _write(root / STOP, {"stage": "pre_dispatch", "pid": child.pid, "returncode": child.returncode,
                                   "plan_sha256": plan_pin, "arm_id": ARM, "ordinal": ORDINAL})
    return _write(root / "index.json", {"plan_sha256": plan_pin, "stop_sha256": stop_pin, "files": _inventory(root)})


def verify(root, *, index_sha256):
    """Bind retained CPU artifacts to a known planned interruption and exact replay."""
    root = Path(root)
    index = json.loads(_pinned(root / "index.json", index_sha256))
    custody._require(custody._fields(index, "plan_sha256 stop_sha256 files"), "invalid partial matrix index")
    plan = _load_plan(root, index["plan_sha256"])
    stop = json.loads(_pinned(root / STOP, index["stop_sha256"]))
    custody._require(custody._fields(stop, "stage pid returncode plan_sha256 arm_id ordinal")
                     and stop["stage"] == "pre_dispatch" and type(stop["pid"]) is int and stop["pid"] > 0
                     and stop["returncode"] == -signal.SIGKILL and stop["plan_sha256"] == index["plan_sha256"]
                     and stop["arm_id"] == ARM and type(stop["ordinal"]) is int and stop["ordinal"] == ORDINAL,
                     "host stop differs from the pinned interruption")
    actual_files = _inventory(root)
    custody._require(actual_files == index["files"], "partial matrix files differ from the supplied index")

    def halt():
        raise _Cutoff

    with TemporaryDirectory(prefix="tremor-matrix-prefix-") as folder:
        directory = Path(folder)
        try:
            _produce(directory / "matrix", plan, halt)
        except _Cutoff:
            pass
        else:
            raise ValueError("matrix replay did not reach the stop barrier")
        custody._require(actual_files == _inventory(directory), "partial matrix differs from exact stopped replay")
        schedule = json.loads((directory / "matrix" / "plan.json").read_bytes())["schedule"]
        planned = sum(len(block["order"]) for block in schedule["blocks"])
        started = len({name.split("/")[1] for name in actual_files if name.endswith("/intent.json")})
        completed = sum(name.endswith("/result.json") for name in actual_files)
        events = [json.loads(line)["event"] for name in actual_files if name.endswith("/" + TAPE)
                  for line in _artifact_bytes(directory / name).splitlines()]
    return {"status": "incomplete", "planned_arms": planned, "started_arms": started, "completed_arms": completed,
            "unstarted_arms": planned - started, "returned_attempts": events.count("result"),
            "open_attempts": events.count("attempt") - events.count("result"), "comparison": None,
            "scientific_n2_frozen": False, "child_returncode": stop["returncode"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--worker", help=argparse.SUPPRESS)
    parser.add_argument("--index-sha256")
    args = parser.parse_args()
    try:
        if args.worker:
            _worker(args.output, args.worker)
            return
        result = (verify(args.output, index_sha256=args.index_sha256) if args.index_sha256
                  else {"index_sha256": run(args.output, seed=args.seed)})
    except (IndexError, KeyError, TypeError, OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
