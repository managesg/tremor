# Spark GPU readiness for R5/R6 (read-only host inspection)

Docs only. No run, admission, freeze, approval or spend authority. Collected 2026-11-27T06:02Z (host clock 01:01 local) on the Spark, local read-only commands. **No request of any kind was sent to 100.91.57.48:8011** (no curl, no socket, no health check). `nvidia-smi` and `ps` were read; no file was hashed. Keys: R5 `prereg/R5-agent-performance-line-plan.md`; PL `prereg/R6-pvsnp-research-line-plan.md`; draft `prereg/R6-protocol-draft.md`; FP `docs/reports/tremor/R6_FREEZE_PACKET.md`; DL `docs/reports/tremor/DECISION_LOG.md`; ST `~/.agents/agent-manager/pilot-lanes/outbox/tremor-coordinator-status.md`.

## 1. Host facts

| Fact | Value | Command |
|---|---|---|
| GPU | NVIDIA GB10, driver 580.178.04, CUDA 13.0 | `nvidia-smi` |
| GPU memory column | "Not Supported" (unified memory); util 15%, 37C, 5W | `nvidia-smi` |
| Compute process | pid 435838 `.../runtime-b12588/llama-server`, 27521 MiB | `nvidia-smi` |
| Other GPU processes | graphics only: gnome-shell 190 + 16 MiB, gnome-remote-desktop-daemon 279 MiB (C+G), Xwayland 9, Xorg 43 | `nvidia-smi` |
| RAM | total 121 GiB, used 41, free 8, buff/cache 73, available 80; swap 15 total, 15 used | `free -g` |
| MemAvailable | 84,059,668 kB (about 80.2 GiB) | `grep MemAvailable /proc/meminfo` |
| Uptime / load | up 10 days 11:05, 9 users, load 2.22 / 2.17 / 2.34 | `uptime` |
| CPUs | 20 | `nproc` |
| Disk (`/`, holds /home) | 3.7T size, 1.8T used, 1.8T avail, 51% | `df -h /home` |
| Model dir | `/home/adelmar/.cache/huggingface/seabridge-inkling-2-mini/` | `ls -la` |
| Q8 GGUF | `Inkling-2-Mini-UD-Q8_K_XL.gguf`, 22,867,451,616 bytes, mtime Nov 23 01:45 | `ls -la` |
| mmproj | `mmproj-F16.gguf`, 639,348,160 bytes | `ls -la` |
| llama-server exe | 67,624 bytes, mtime Nov 20 18:03 (a launcher stub; real code sits in runtime-b12588) | `ls -la` |
| Local Qwen | `data/hf/Qwen3.5-0.8B`, `data/hf/Qwen3.5-4B` present | `ls data/hf` |
| SmolLM3-3B | not available (R5:65, DL:259) | cited, not re-checked |

Process line (`ps -eo pid,etime,args | grep -i llama`), no secrets in it: pid 435838, elapsed 3-23:07:44, `--model .../Inkling-2-Mini-UD-Q8_K_XL.gguf --mmproj .../mmproj-F16.gguf --alias Inkling-2-Mini --host 100.91.57.48 --port 8011 --ctx-size 131072 --parallel 1 --n-gpu-layers all --jinja --no-webui`.

Observations, not conclusions: swap is full (15 of 15 GiB) while 80 GiB is available; the host shows GPU util 15% with the single shared slot, so something is generating or recently generated (cannot attribute without contacting the service). The R5 launch gate asks for MemAvailable of at least 70 GiB (R5:65, DL:15); `lab/r5_gpu_readiness.py:11` and PL:256 / draft:156 use a 10 GiB host stop. The two thresholds differ; this report does not choose one.

## 2. What the R5/R6 lines need on the GPU

| Item | Stated need | Source |
|---|---|---|
| R5 B0 (Qwen) | 28 calls x 33.08 s + 71.094 s load = 997.2 s = 0.277 GPU-h | R5:67-68 |
| R5 B1 (Qwen) | 280 calls x 33.08 s + 71.094 s = 9,332.4 s = 2.592 GPU-h (28% of the 9.4 residual) | R5:69 |
| R5 B2 main run | sized from B1 only; no number | R5:71 |
| R5 residual | 9.4 GPU-h after SmolLM3's 0.1; also claimed by L4-E, Grover, controller; oversubscribed | R5:70, R5:114 |
| R6 P0 | 12 calls, strictly serial; inputs about 200 / 1,000 / 2,000 tokens x output cap 64 / 300 x 2 same-seed repeats; bound min(15 min, 12 x 300 s) = 0.25 GPU-h; placement OPEN | PL:277-282, draft:136-139, draft:151 |
| R6 B0' | 28 calls x T; GPU-h OPEN until T measured | PL:286, draft:152 |
| R6 B1' | 280 calls x T; OPEN | PL:287, draft:153 |
| R6 secondary arms and main | OPEN, sized from B1' | draft:154 |
| R6 wall caps | P0 15 min; others OPEN (R6-O11) | draft:155 |
| R6 tokens per call | P0 output cap 64 and 300; the 300-token cap for later batches is OPEN until P0 (whether output goes to reasoning first is unknown) | PL:262, PL:277 |
| R6 hosted USD | 0 | draft:149-150 |
| R6 residual draw | whether calls to the resident service draw on the 9.4 GPU-h is OPEN (PC placement); until then wall time counts | PL:263, draft:157 |
| R6 per-call stops | 300 s timeout, 2 errors in total, skip spike (2 busy or over 60 s) | draft:139 |

The R5 Qwen figures (33.08 s, 0.277, 2.592) are void for R6 (PL:253-255). Seconds per call, generation tokens per second, queue wait and seed behaviour on Inkling are unmeasured (PL:247). The plan's own prose for the slot: other lanes' prompts above 100k tokens, and a cached prompt of about 33.7k tokens that any P0 call evicts (two minutes to re-evaluate at 275 to 283 tokens/s), reported by the coordinator, not measured by TREMOR (PL:267).

## 3. What exists offline and what is missing

Exists (files present at HEAD `4ee10cf`):
- `lab/r5_gpu_readiness.py` (read-only check; tests `lab/tests/test_r5_gpu_readiness.py`).
- `lab/r6_inkling_client.py` (stdlib client, P0_STOPS at `:24`; `lab/tests/test_r6_inkling_client.py`) and `lab/r6_p0_probe.py` (12-call driver, identity snapshot, `BATCH = "r6-p0"`; `lab/tests/test_r6_p0_probe.py`). ST records 103 OK for the two P0 suites at f788499. Not re-run here.
- `lab/tremor_admission_gate.py`, `lab/tremor_freeze_skeleton.py` and their tests; `lab/r6_holm.py`, `lab/r6_scorecard.py`, `lab/r6_predicates.py`, `lab/r6_pvsnp_tasks.py`, `lab/r6_stage_a.py`, `lab/r5_perf_harness.py`.
- FP section 1: skeleton run gives 5 computed fields and 14 MISSING per batch.

Missing before a first P0, B0' or B1' run (FP section 2; draft:121-132):
1. **Freeze record** per batch: 14 empty fields (`reserved_gpu_hours`, `hosted_usd_plan`, `hosted_usd_stop`, `protected_inputs`, `approval_review_evidence`, `config_hash`, `contrasts`, `d1_basis`, `expected_and_max_resources`, `inherited_pins`, `model_snapshot`, `scorer_ids`, `stopping_rules`, `task_family_revision`). The draft must first become `prereg/R6-protocol.md` (R6-O1, FP:58); the skeleton values are throwaway until then.
2. **Admission record** (owner): window, `reserved_gpu_hours`, owner words, freeze sha; `admit` is one-use and runs last (draft:132, FP:128).
3. **PC placement**: GPU-hours and wall caps (R6-O10, R6-O11), the residual-draw decision, and the named Spark service owner (R6-O11).
4. **Written notice** before and after to the PC coordinator (OmniRoute fallback hop), the Spark service owner, and direct users of :8011 (draft:127, FP:120).
5. **Quiet window**: Spark hop out of OmniRoute routing; the owner agrees it with PC (draft:128).
6. **Custodian (R6-O2)**: not named by the owner (ST). Needed to seal protected inputs, including the pilot pool, before P0 (D2, FP:81-91); no sealed path exists.
7. **Code**: F1 generator, F4 checker and, per draft:132, the P0 driver were "not committed" in the draft's 2026-11-26 status; the P0 driver now exists in `lab/` (ST: 103 OK), but the F1/F4 generators and checkers are not shown as built (FP:72, `task_family_revision`). Confirm before freeze.
8. `model_snapshot` gaps: no mmproj hash or inode in DL:311 (FP:71). The sha256 of the Q8 GGUF recorded in DL:311 is a local identity, not upstream verification (PL:245).
9. B0' and B1' also wait on P0's T (PL:316), the dial (R6-O17) and the output cap and timeout (R6-O22).
10. R5 Stage B (Qwen) additionally needs the R3-L2 launcher and a custodian (R5:103); its 14-day expiry is the author's choice.

## 4. Is the llama-server on this host the one the plans name?

Observed here: pid 435838, `Inkling-2-Mini-UD-Q8_K_XL.gguf`, `--ctx-size 131072 --parallel 1`, alias `Inkling-2-Mini`, `--host 100.91.57.48 --port 8011`, started 3-23:07 ago. The plans name the same: pid 435838, same model file, same context, slots and endpoint (PL:243; draft:158; DL:311 start time Mon Nov 23 01:54:13 2026). The same pid, path and arguments match as text.

**Match on pid, path and arguments: yes. Identity of the bytes and the running binary: UNVERIFIED in this report.** The recorded hashes (GGUF sha256 `dfb04bf3...`, exe sha256 `cc26daf1...`, DL:311) were not recomputed and `/proc/<pid>/exe` and `maps` were not read here. Whether the server answers as `Inkling-2-Mini` with 131072 context and one slot is UNVERIFIED without contacting it, and is not to be tested outside P0 (PL:276 does it read-only inside the admitted batch). The elapsed time (3 days 23 h at 06:02Z) agrees with a start near 2026-11-23 01:54 local to within the clock offset; not a proof.

## 5. Checklist for PC

- [ ] Say whether calls to the resident Inkling service draw on the 9.4 GPU-h residual (draft:157) and place GPU-hours: P0 at or above 0.25 (draft:151), B0'/B1' after T.
- [ ] Place the wall caps (R6-O11) and name the Spark service owner.
- [ ] Choose the host-memory stop (10 GiB in PL:256 / `lab/r5_gpu_readiness.py:11` versus 70 GiB in R5:65); today MemAvailable is about 80 GiB with swap full.
- [ ] Send written notice before and after to the OmniRoute hop owner, the service owner and direct users of :8011.
- [ ] Agree a quiet window with the owner: Spark hop out of OmniRoute routing for the window.
- [ ] Ask the owner to name the R6 custodian (R6-O2); custodian seals the pilot pool and main inputs before P0.
- [ ] Do not let anyone start P0, B0' or B1' before `check` then `admit` pass for that batch; `admit` is one-use.
- [ ] Re-read pid, start time, exe hash and GGUF inode (read-only, as the file owner) immediately before the freeze; stop on any mismatch (draft:135).

Not checked: the resident server's behaviour or health, sha256 of any file, the test suites at this HEAD, whether F1 and F4 generators are built.
