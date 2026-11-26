# R5 GPU readiness, 2026-11-26

Source proof, read-only live check on seabridge-spark at 2026-11-26T04:12:52Z, not a quiet-host window and not an admission.

Command: `python3 -B lab/r5_gpu_readiness.py` (gate 73,400,320 KiB, other GPU processes not allowed, model `data/hf/Qwen3.5-4B`). The check ran no GPU process, loaded no model, wrote nothing, and made no network or API call. Weights were sha256-hashed by chunked read (about 17 s).

Reading: the check returned `ok: false` for one reason, two other processes on the GPU (the resident llama-server and the gnome-remote-desktop daemon). MemAvailable (80,755,704 KiB, about 77.0 GiB) is above the gate and the 10 GiB host stop. All 14 manifest files match and the revision matches the plan. GB10 has unified memory, so `nvidia-smi` reports memory total and used as `[N/A]`. The load average is recorded only; no quiet-host claim is made. A B0/B1 launch still needs the owner's admission and a fresh reading at execution.

Tests: `PYTHONPATH=src:lab:tests:. python3 -B -m unittest lab.tests.test_r5_gpu_readiness` runs 21 tests, all pass. A mutation run on a copy under `/tmp/claude-1000` killed 18 of 18 mutants.

## Output

```json
{
 "ok": false,
 "failures": [
  "gpu: 2 other process(es) on the GPU"
 ],
 "gpu": {
  "gpus": [
   {
    "name": "NVIDIA GB10",
    "memory_total": "[N/A]",
    "memory_used": "[N/A]",
    "utilization": "20 %"
   }
  ],
  "other_processes": [
   {
    "pid": "435838",
    "process_name": "/home/adelmar/.cache/huggingface/seabridge-inkling-2-mini/runtime-b12588/llama-server",
    "used_memory": "27521 MiB"
   },
   {
    "pid": "1960504",
    "process_name": "/usr/libexec/gnome-remote-desktop-daemon",
    "used_memory": "279 MiB"
   }
  ],
  "error": null
 },
 "memory": {
  "mem_available_kib": 80755704,
  "gate_kib": 73400320,
  "host_stop_kib": 10485760
 },
 "weights": {
  "revision_expected": "851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a",
  "revision_found": "851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a",
  "files_checked": 14,
  "mismatches": [],
  "missing": [],
  "error": null
 },
 "writes": {
  "model_dir_changed": false,
  "paths_written_by_check": []
 },
 "loadavg": [
  "2.43",
  "1.92",
  "2.41"
 ],
 "quiet_host_claimed": false
}
```
