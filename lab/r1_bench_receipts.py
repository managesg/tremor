"""Verify retained R1 CPU bench receipts and identify current source drift."""

import argparse
import hashlib
import json
import re
from pathlib import Path
from stat import S_IMODE

from lab import adapter_lineage

EXPECTED_TESTS = 783
EXPECTED_FILES = 329
SKIP = "test_local_hf_fails_cleanly (test_runner.RunnerTests.test_local_hf_fails_cleanly) ... skipped 'torch present'"
TEST_ID = re.compile(r"^(\S+ \([\w.]+\))(?= \.\.\.|$)", re.MULTILINE)


TEST_STATUS = re.compile(
    r"(?:^| \.\.\. )(ok|FAIL|ERROR|expected failure|unexpected success|skipped '[^\n]*')$", re.MULTILINE,
)


def _passing_test_ids(log, expected_count):
    """Require one passing status per test, including unittest's continuation format."""
    labels = list(TEST_ID.finditer(log))
    identities = [label[1] for label in labels]
    if len(identities) != expected_count or len(set(identities)) != expected_count:
        raise ValueError("suite does not list the expected distinct test identities")
    skip_label, skip_status = SKIP.split(" ... ", 1)
    if skip_label not in identities:
        raise ValueError("suite omits the allowed skip")
    for index, label in enumerate(labels):
        end = labels[index + 1].start() if index + 1 < len(labels) else len(log)
        statuses = TEST_STATUS.findall(log, label.end(), end)
        expected = skip_status if label[1] == skip_label else "ok"
        if statuses != [expected]:
            raise ValueError(f"suite test has a missing or nonpassing status: {label[1]}")
    return identities


def _digest_path(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _verify_logs(bundle, log_sha256):
    if len(log_sha256) != 3 or len(set(log_sha256)) != 3:
        raise ValueError("exactly three distinct run log pins are required")
    verified = []
    expected_ids = None
    for index, digest in enumerate(log_sha256, 1):
        log = adapter_lineage._path(bundle, {"path": f"full-{index}.log"})
        raw = log.read_bytes()
        adapter_lineage._match(log, hashlib.sha256(raw).hexdigest(), digest)
        status = adapter_lineage._path(bundle, {"path": f"full-{index}.exit"})
        log_text = raw.decode("utf-8")
        lines = log_text.splitlines()
        summaries = [line for line in lines if line.startswith("Ran ")]
        match = re.fullmatch(rf"Ran {EXPECTED_TESTS} tests in ([0-9]+\.[0-9]+)s", summaries[0]) if len(summaries) == 1 else None
        skips = [line for line in lines if re.search(r" \.\.\. skipped ", line)]
        if status.read_text().strip() != "0" or lines[-1:] != ["OK (skipped=1)"] or not match or skips != [SKIP]:
            raise ValueError(f"bench run {index} does not have the expected passing receipt")
        identities = _passing_test_ids(log_text, EXPECTED_TESTS)
        if expected_ids is not None and identities != expected_ids:
            raise ValueError(f"bench run {index} used a different ordered test inventory")
        expected_ids = identities
        verified.append({"run": index, "tests": EXPECTED_TESTS, "skip": SKIP, "seconds": match[1], "sha256": digest})
    return verified, hashlib.sha256("\n".join(expected_ids).encode()).hexdigest()


def verify(bundle, checkout, *, inventory_sha256, log_sha256):
    """Check exact archived bytes and modes and report comparable checkout paths."""
    bundle = Path(bundle).resolve(strict=True)
    checkout = Path(checkout).resolve(strict=True)
    source = (bundle / "source").resolve(strict=True)
    if source != bundle / "source":
        raise ValueError("archived source must be inside the receipt bundle")
    inventory = adapter_lineage._path(bundle, {"path": "source.sha256"})
    raw = inventory.read_bytes()
    adapter_lineage._match(inventory, hashlib.sha256(raw).hexdigest(), inventory_sha256)
    paths = set()
    changed = []
    for line in raw.decode("utf-8").splitlines():
        digest, permissions, name = line.split(" ", 2)
        if name in paths or Path(name).as_posix() != name or not re.fullmatch(r"[0-7]{3,4}", permissions):
            raise ValueError("invalid or repeated bench inventory record")
        paths.add(name)
        expected = adapter_lineage._digest(digest, 64), int(permissions, 8)
        archived = adapter_lineage._path(source, {"path": name})
        if (_digest_path(archived), S_IMODE(archived.stat().st_mode)) != expected:
            raise ValueError(f"archived bench source differs from the pinned inventory: {name}")
        try:
            current = adapter_lineage._path(checkout, {"path": name})
        except (OSError, ValueError):
            changed.append({"path": name, "status": "missing_or_not_regular"})
            continue
        if (_digest_path(current), S_IMODE(current.stat().st_mode)) != expected:
            changed.append({"path": name, "status": "bytes_or_mode_changed"})
    if len(paths) != EXPECTED_FILES:
        raise ValueError("unexpected archived bench file count")

    runs, test_ids_digest = _verify_logs(bundle, log_sha256)
    return {
        "evidence": "historical_pinned_cpu_bench_receipts",
        "inventory_sha256": inventory_sha256,
        "archived_inventory_files": len(paths),
        "matching_checkout_inventory_files": len(paths) - len(changed),
        "checkout_inventory_drift": changed,
        "ordered_test_ids_sha256": test_ids_digest,
        "runs": runs,
        "quiet_host_qualified": None,
        "independent_module_reviews_accepted": None,
        "bench_accepted": None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("checkout", type=Path)
    parser.add_argument("--inventory-sha256", required=True)
    parser.add_argument("--log-sha256", required=True, nargs=3)
    args = parser.parse_args()
    try:
        report = verify(**vars(args))
    except (OSError, ValueError) as error:
        parser.exit(2, f"{error}\n")
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
