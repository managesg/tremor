"""Join archived R1 host spot samples to the pinned CPU test-suite windows."""

import argparse
from datetime import datetime
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import re

from lab import adapter_lineage
from lab.r1_bench_receipts import SKIP, TEST_ID


SCHEMA = "r1_cpu_host_capture_v1"
STAMP = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$", re.MULTILINE)
INSPECT = re.compile(r"^([0-9a-f]{64})(?: (sha256:[0-9a-f]{64}))? runc none true "
                     r"(4294967296) (2000000000)(?: (256))? null \[\]$", re.MULTILINE)


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _pinned(root, name, pin, limit=512 * 1024):
    path = adapter_lineage._path(root, {"path": name})
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    _require(len(raw) <= limit, f"oversized R1 artifact: {name}")
    adapter_lineage._match(path, sha256(raw).hexdigest(), pin)
    return raw


def _samples(raw):
    """Parse archived sample records, using the vmstat delta row only."""
    text = raw.decode()
    stamps = list(STAMP.finditer(text))
    _require(stamps and stamps[0].start() == 0, "host capture has no timestamped samples")
    records = []
    for index, stamp in enumerate(stamps):
        end = stamps[index + 1].start() if index + 1 < len(stamps) else len(text)
        body = text[stamp.end():end]
        load = re.search(r"load average: ([0-9]+\.[0-9]+),", body)
        memory = re.search(r"^MemAvailable:\s+([0-9]+) kB$", body, re.MULTILINE)
        swap = re.search(r"^SwapFree:\s+([0-9]+) kB$", body, re.MULTILINE)
        _require(load and memory and swap, "host sample lacks load, memory or swap")
        sample = {
            "utc": stamp[0],
            "load_one_minute": load[1],
            "available_kib": int(memory[1]),
            "swap_free_kib": int(swap[1]),
            "vmstat_interval": None,
        }
        container = re.search(r"^([a-zA-Z0-9_.-]+) Up .+$", body, re.MULTILINE)
        if container:
            sample["observed_container_name"] = container[1]
        if "procs ---" in body:
            lines = body.strip().splitlines()
            start = next(i for i, line in enumerate(lines) if line.split()[:2] == ["r", "b"])
            keys = lines[start].split()
            baseline, delta = (lines[start + i].split() for i in (1, 2))
            _require(len(baseline) == len(delta) == len(keys), "incomplete vmstat baseline or delta")
            fields = dict(zip(keys, map(int, delta), strict=True))
            sample["vmstat_interval"] = {name: fields[key] for name, key in (
                ("idle_percent", "id"), ("io_wait_percent", "wa"), ("swap_in", "si"), ("swap_out", "so")
            )}
        records.append(sample)
    return records


def _joined_run(root, index, run, files, command_samples):
    number = run["run"]
    prefix = f"retry-1/full-current-{number}"
    ends = _samples(_pinned(root, prefix + ".host", files[prefix + ".host"]))
    middle_raw = _pinned(root, prefix + ".mid", files[prefix + ".mid"])
    mid = _samples(middle_raw)
    _require(len(ends) == 2 and len(mid) == 1, "R1 run needs two bounds and one direct inspection sample")
    begin, end = (datetime.fromisoformat(row["utc"]) for row in ends)
    interiors = [row for row in command_samples if begin < datetime.fromisoformat(row["utc"]) < end]
    _require(len(interiors) == 1 and begin < datetime.fromisoformat(mid[0]["utc"]) < end,
             "R1 host sample falls outside its exact run window")
    _require(interiors[0].get("observed_container_name") == f"{index['container_prefix']}-{number}",
             "host observation names a different suite container")
    seen = INSPECT.findall(middle_raw.decode())
    _require(len(seen) == 1, "missing exact CPU-only runtime inspection")
    container_id, image, memory, cpus, pids = seen[0]
    _require(not image or image == index["image"], "inspection reports a different image")

    raw = _pinned(root, prefix + ".log", run["sha256"]).decode()
    _require(_pinned(root, prefix + ".exit", files[prefix + ".exit"]).strip() == b"0", "R1 run did not exit zero")
    match = re.findall(r"^Ran ([0-9]+) tests in ([0-9]+\.[0-9]+)s$", raw, re.MULTILINE)
    identities = TEST_ID.findall(raw)
    _require(match == [(str(run["tests"]), run["seconds"])] and len(identities) == len(set(identities)) == run["tests"]
             and raw.splitlines()[-1:] == ["OK (skipped=1)"]
             and [line for line in raw.splitlines() if " ... skipped " in line] == [SKIP]
             and run["skips"] == 1, "R1 test output differs from the pinned suite receipt")
    wall = int((end - begin).total_seconds())
    _require(Decimal(run["seconds"]) <= wall, "test duration exceeds recorded host bounds")
    return {
        "run": number, "wall_seconds": wall, "test_seconds": run["seconds"], "tests": run["tests"],
        "samples": sorted([*ends, *mid, *interiors], key=lambda row: row["utc"]),
        "runtime": {"container_id": container_id, "image": image or None, "memory_bytes": int(memory),
                    "nano_cpus": int(cpus), "pids_limit": int(pids) if pids else None,
                    "network": "none", "read_only_root": True, "gpu_requested": False},
    }, identities


def verify(bundle, capture_index, *, capture_sha256):
    """Verify spot evidence. Quiet-host and bench acceptance remain independent decisions."""
    root = Path(bundle).resolve(strict=True)
    index = adapter_lineage._json(Path(capture_index), capture_sha256)
    _require(set(index) == {"schema", "suite_sha256", "image", "container_prefix", "files"} and index["schema"] == SCHEMA,
             "unknown R1 capture index")
    _require(re.fullmatch(r"sha256:[0-9a-f]{64}", index["image"]), "missing expected image")
    _require(re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*", index["container_prefix"]), "invalid suite container prefix")
    suite_raw = _pinned(root, "verified-full-suite.json", index["suite_sha256"])
    suite = adapter_lineage._strict_object(suite_raw, Path("verified-full-suite.json"))
    _pinned(root, "source.sha256", suite["candidate_sha256"])
    numbers = [run["run"] for run in suite["runs"]]
    _require(all(type(number) is int for number in numbers) and numbers == [1, 2, 3],
             "expected the three serial R1 runs")
    files = index["files"]
    common = "retry-1/host-samples.log"
    names = {f"retry-1/full-current-{number}.{suffix}" for number in numbers for suffix in ("host", "mid", "exit")}
    _require(type(files) is dict and files.keys() == names | {common}, "incomplete host capture index")
    command_samples = _samples(_pinned(root, common, files[common]))
    _require(len(command_samples) == 3, "expected the three independent host samples")
    rows, test_orders = [], set()
    for run in suite["runs"]:
        row, identities = _joined_run(root, index, run, files, command_samples)
        rows.append(row)
        test_orders.add(sha256("\n".join(identities).encode()).hexdigest())
    _require(test_orders == {suite["run_order_sha256"]}, "serial runs disagree on the pinned test inventory")
    _require(len({row["runtime"]["container_id"] for row in rows}) == len(rows)
             and all(left["samples"][-1]["utc"] <= right["samples"][0]["utc"]
                     for left, right in zip(rows, rows[1:])), "R1 runs overlap or reuse a container")
    return {
        "evidence": "r1_archived_cpu_host_spot_samples",
        "capture_sha256": capture_sha256,
        "suite_sha256": index["suite_sha256"],
        "candidate_sha256": suite["candidate_sha256"],
        "quiet_host_qualified": None,
        "continuous_host_observation": False,
        "independent_bench_accepted": None,
        "runs": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("capture_index", type=Path)
    parser.add_argument("--capture-sha256", required=True)
    args = parser.parse_args()
    try:
        report = verify(**vars(args))
    except (IndexError, KeyError, OSError, StopIteration, TypeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(report, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
