"""R5 stage B0/B1 GPU readiness: read-only checks, no GPU process, no model load, no writes."""

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HOST_STOP_KIB = 10 * 1024 * 1024  # 10 GiB host stop (M8_RUNNER_REVIEW_AND_STORAGE_REQUESTS.md)
PLAN = Path("prereg/R5-agent-performance-line-plan.md")
GPU_QUERY = ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,utilization.gpu", "--format=csv,noheader"]
APP_QUERY = ["nvidia-smi", "--query-compute-apps=pid,process_name,used_memory", "--format=csv,noheader"]


def run_nvidia_smi(argv):
    return subprocess.run(argv, capture_output=True, text=True, timeout=20, shell=False, check=False)


def _csv(text):
    return [[c.strip() for c in line.split(",")] for line in text.splitlines() if line.strip()]


def _gpu(runner):
    out = {"gpus": [], "other_processes": [], "error": None}
    try:
        gpu, apps = runner(GPU_QUERY), runner(APP_QUERY)
    except (OSError, subprocess.SubprocessError) as exc:
        out["error"] = f"nvidia-smi unavailable: {type(exc).__name__}: {exc}"
        return out
    if gpu.returncode != 0 or apps.returncode != 0:
        out["error"] = f"nvidia-smi exit {gpu.returncode}/{apps.returncode}: {(gpu.stderr + apps.stderr).strip()[:200]}"
        return out
    out["gpus"] = [dict(zip(("name", "memory_total", "memory_used", "utilization"), r)) for r in _csv(gpu.stdout)]
    out["other_processes"] = [dict(zip(("pid", "process_name", "used_memory"), r)) for r in _csv(apps.stdout)]
    return out


def _meminfo(path):
    for line in Path(path).read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1])
    raise ValueError("MemAvailable missing")


def _expected_revision(repo_root):
    text = (Path(repo_root) / PLAN).read_text()
    m = re.search(r"data/hf/Qwen3\.5-4B`[^\n]*?revision `([0-9a-f]{40})`", text)
    return m.group(1) if m else None


def _verify_weights(model_dir, expected_revision, chunk):
    model_dir = Path(model_dir)
    res = {"revision_expected": expected_revision, "revision_found": None, "files_checked": 0,
           "mismatches": [], "missing": [], "error": None}
    try:
        manifest = json.loads((model_dir / "MANIFEST.sha256.json").read_text())
        res["revision_found"] = manifest["revision"]
        entries = manifest["files"]
    except (OSError, ValueError, KeyError) as exc:
        res["error"] = f"manifest unreadable: {type(exc).__name__}: {exc}"
        return res
    for e in entries:
        p = model_dir / e["path"]
        if not p.is_file():
            res["missing"].append(e["path"])
            continue
        h, size = hashlib.sha256(), 0
        with open(p, "rb") as f:
            while block := f.read(chunk):
                h.update(block)
                size += len(block)
        res["files_checked"] += 1
        if h.hexdigest() != e["sha256"] or size != e["bytes"]:
            res["mismatches"].append(e["path"])
    return res


def _listing(model_dir):
    return sorted((str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in Path(model_dir).rglob("*"))


def check(repo_root, model_dir, min_mem_available_kib, other_gpu_processes_allowed, *,
          runner=run_nvidia_smi, meminfo_path="/proc/meminfo", loadavg_path="/proc/loadavg", chunk=1 << 20):
    before = _listing(model_dir) if Path(model_dir).is_dir() else None
    failures = []
    gpu = _gpu(runner)
    if gpu["error"]:
        failures.append("gpu: " + gpu["error"])
    elif not gpu["gpus"]:
        failures.append("gpu: no GPU reported")
    if gpu["other_processes"] and not other_gpu_processes_allowed:
        failures.append(f"gpu: {len(gpu['other_processes'])} other process(es) on the GPU")
    avail = _meminfo(meminfo_path)
    mem = {"mem_available_kib": avail, "gate_kib": min_mem_available_kib, "host_stop_kib": HOST_STOP_KIB}
    if avail < min_mem_available_kib:
        failures.append(f"memory: MemAvailable {avail} KiB below gate {min_mem_available_kib} KiB")
    if avail < HOST_STOP_KIB:
        failures.append(f"memory: MemAvailable {avail} KiB below the 10 GiB host stop")
    weights = _verify_weights(model_dir, _expected_revision(repo_root), chunk)
    if weights["error"]:
        failures.append("weights: " + weights["error"])
    if weights["missing"]:
        failures.append(f"weights: missing {weights['missing']}")
    if weights["mismatches"]:
        failures.append(f"weights: sha256/size mismatch {weights['mismatches']}")
    if weights["revision_expected"] is None or weights["revision_found"] != weights["revision_expected"]:
        failures.append(f"weights: revision {weights['revision_found']} != expected {weights['revision_expected']}")
    after = _listing(model_dir) if Path(model_dir).is_dir() else None
    wrote = before != after
    if wrote:
        failures.append("writes: the model directory changed during the check")
    return {"ok": not failures, "failures": failures, "gpu": gpu, "memory": mem, "weights": weights,
            "writes": {"model_dir_changed": wrote, "paths_written_by_check": []},
            "loadavg": Path(loadavg_path).read_text().split()[:3],
            "quiet_host_claimed": False}


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    # shortcut: gate figure fixed to the R5 plan's 70 GiB, edit if the plan changes.
    print(json.dumps(check(root, root / "data/hf/Qwen3.5-4B", 73_400_320, False), indent=1))
