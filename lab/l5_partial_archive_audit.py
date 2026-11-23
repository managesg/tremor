"""Check a pinned stopped archive and compare its prefix with the current instrument."""

import argparse
import json
from pathlib import Path
import signal
from tempfile import TemporaryDirectory

from lab import adapter_lineage, l5_matrix_partial as partial


def audit(bundle, *, index_sha256):
    """Report current byte agreement without claiming historical source identity."""
    root = Path(bundle).resolve(strict=True)
    index = adapter_lineage._json(adapter_lineage._path(root, {"path": "index.json"}), index_sha256)
    plan = adapter_lineage._json(adapter_lineage._path(root, {"path": partial.PLAN}), index.get("plan_sha256"))
    stop = adapter_lineage._json(adapter_lineage._path(root, {"path": partial.STOP}), index.get("stop_sha256"))
    current = partial._plan(plan.get("seed"))
    pin_keys = {"instrument_sha256", "cutoff_instrument_sha256"}
    if set(plan) != set(current) or any(plan[key] != current[key] for key in current.keys() - pin_keys):
        raise ValueError("archived interruption differs from the current scripted fixture settings")
    for key in pin_keys:
        adapter_lineage._digest(plan[key], 64)
    if (set(stop) != {"stage", "pid", "returncode", "plan_sha256", "arm_id", "ordinal"}
            or type(stop["pid"]) is not int or stop["pid"] <= 0
            or type(stop["returncode"]) is not int or stop["returncode"] != -signal.SIGKILL
            or stop["stage"] != "pre_dispatch" or stop["plan_sha256"] != index["plan_sha256"]
            or stop["arm_id"] != plan["arm_id"] or type(stop["ordinal"]) is not int
            or stop["ordinal"] != plan["ordinal"]):
        raise ValueError("archived host stop does not bind the planned pre-dispatch boundary")
    archived = partial._inventory(root)
    if set(index) != {"plan_sha256", "stop_sha256", "files"} or archived != index["files"]:
        raise ValueError("archived files do not match the independently pinned index")

    def halt():
        raise partial._Cutoff

    with TemporaryDirectory(prefix="tremor-l5-prefix-audit-") as folder:
        replay = Path(folder)
        try:
            partial._produce(replay / "matrix", current, halt)
        except partial._Cutoff:
            pass
        else:
            raise ValueError("current replay failed to reach the planned stop boundary")
        observed = partial._inventory(replay)
    changed = sorted(key for key in archived.keys() | observed.keys() if archived.get(key) != observed.get(key))
    return {
        "evidence": "scripted_l5_stopped_archive_current_source_comparison",
        "index_sha256": index_sha256,
        "archived_files": len(archived),
        "replayed_files": len(observed),
        "file_differences": changed,
        "current_prefix_matches_archive": not changed,
        "instrument_sha256_matches": plan["instrument_sha256"] == current["instrument_sha256"],
        "cutoff_instrument_sha256_matches": plan["cutoff_instrument_sha256"] == current["cutoff_instrument_sha256"],
        "full_historical_verification_performed": False,
        "phase_scores": None,
        "authorizes_execution": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--index-sha256", required=True)
    args = parser.parse_args()
    try:
        result = audit(**vars(args))
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.exit(2, f"{error}\n")
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
