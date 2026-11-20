# T7 smoke (2026-11-19): arms 0 and B, 20 problems, projection vs the 12 GPU-hour cap

Scope as approved: derived image, base model download, MATH-500 download, smoke of arms 0 and B only, projection, arm A dry rebuild.
The main T7 was NOT run. Verdict: **the projection exceeds the 12 GPU-hour cap. STOP; n was not shrunk.**

## 1. Image, model, data (what exists)

| Item | Value |
|---|---|
| Image | `murmuration-t7:1` = `train/Dockerfile`, `FROM nvcr.io/nvidia/pytorch:25.11-py3@sha256:417cbf33...a55dff21`, adds only `transformers==5.2.0 math-verify==0.9.0 latex2sympy2_extended==1.11.0 antlr4-python3-runtime==4.13.2` |
| Pip side effects (transitive, from `pip freeze` diff in `runs/t7-smoke/after.txt`) | click 8.3.0->8.5.1, hf-xet 1.2.0->1.8.0, huggingface_hub 1.1.2->1.33.0. torch and numpy unchanged. |
| Why transformers 5.2.0 | The card (`Qwen/Qwen3.5-0.8B` @ 2fc06364) says only "the latest transformers is required"; its `config.json` has `transformers_version 4.57.0.dev0` (export version, not a minimum). I probed GitHub tags: `models/qwen3_5/modeling_qwen3_5.py` is absent at v4.57.6, v5.0.0, v5.1.0 and present at v5.2.0 (PyPI 2026-02-16). 5.2.0 is therefore the first release containing the architecture. The model card's own re-run used 5.20.2. Limit: I checked that the module exists, not that every 5.2.0 code path matches 5.20.2. The image logs "fast path not available" (flash-linear-attention and causal-conv1d are not installed, not approved): the gated-delta-net layers run the slow torch fallback, which dominates cost below. |
| Base model | `data/hf/Qwen3.5-0.8B/`, revision 2fc06364715b967f1860aea9cf38778875588b17, `chmod -R a-w`, `MANIFEST.sha256.json`. The two LFS-tracked files (`model.safetensors-00001-of-00001.safetensors`, `tokenizer.json`) match the Hugging Face LFS sha256; the other files have no LFS hash (size checked only). Re-hashed at the end of the work: no file changed. Download tool: `train/fetch.py` (stdlib). |
| MATH-500 | `data/math500/test.jsonl`, `HuggingFaceH4/MATH-500` @ 6e4ed1a2, 446,564 B, 500 rows, sha256 `35dc41080a3680858b27fa7e0533d2d547825316fc5dafe5d316f4ccc5a06132` (in `test.jsonl.sha256`). Licence unstated on the card; owner accepted for this internal test. |
| Not downloaded | the edited checkpoint (arm A is rebuilt, section 3) |

## 2. Samples (by seed, `train/t7_samples.py`, tested in `tests/test_t7_samples.py`)

Main = `random.Random(20261119).sample(sorted(ids), 100)`. Smoke = `random.Random(20261120).sample(sorted(ids - main), 20)`: drawn from the complement, so disjoint by construction; the test asserts size, uniqueness, determinism and no overlap, also on the real file.

## 3. Arm A rebuild (dry apply, no checkpoint downloaded)

`train/t7_rebuild.py` (vendored MIT `apply_edit.py` and `st_numpy.py` in `train/vendor/` with the notice, unchanged; `mathqa_grade.py` is the authors' MIT excerpt for prompt, last-boxed extraction and math-verify). Ran in a container on the read-only base, wrote `runs/t7-smoke/armA/model.safetensors`:
- base file sha256 equals the download manifest before and after (base unchanged);
- per-tensor `base_sha256` asserted before and `edited_sha256` after by `apply_edit.py`: layers 15 and 19 `mlp.down_proj.weight`, 65,260 and 64,928 entries changed;
- exactly 2 of 488 tensors differ from the base; their sha256 equal the two hashes on the Hugging Face model card (82e2d733..., 8ef3c61b...). Rebuilt file sha256 `fd1e42ac...f737b553`.
- Note: `train/t7_edit.py`'s base check hashes float64 row lists (a different byte format). It was not used for the bf16 safetensors; the equivalent check (sha256 of raw bf16 bytes, from the manifest) is in `apply_edit.py` and `t7_rebuild.py`.

## 4. Smoke setup and settings

20 smoke problems, one batch (left padded, 520 prompt tokens), `transformers.generate`, bf16, `torch.manual_seed(0)`; sampling from G9 section 4: arm 0 = thinking on, T 0.6, top_p 0.95, top_k 20, presence_penalty 1.5; arm B = thinking off, T 0.7, top_p 0.8, top_k 20, presence_penalty 1.5. transformers has no presence penalty, so `train/t7_gen.py` applies penalty, temperature, top-k, top-p itself (vLLM order; tested in `tests/test_t7_gen.py`, container only). Deviations to record: (a) **cap 8192 for both arms**, not 32,768 (a 32,768 cap would be about 3 h for arm 0 alone at batch 20; arm B's published cap is 8192 anyway; 2k and 8k are read here directly, the 32k cost is projected below, not measured); (b) one shared RNG stream over the batch, not a seed per problem. Container: `--rm --gpus all --memory 60g --network none`, no ports, train/src/tests mounted read-only, `data/` rw with `data/hf` re-mounted read-only, `runs/` rw, run as the host uid. Power: host `nvidia-smi ... -lms 1000` for the whole run, energy integrated over the generation window with `train/power.py`; idle baseline from a separate 30 s record (mean 5.05 W; it includes the shared spark-vllm engine idling on the same GPU, whose idle load is about 12 percent utilisation, so `idle_fraction` (utilisation exactly 0) reads 0.0 even when my job is idle, and the net joules are an under-count if that engine is busy). Joules are GPU board power only. Per-problem JSONL: `runs/t7-smoke/arm0.jsonl`, `armB.jsonl`; power CSVs, `*.summary.json`; `train/t7_report.py` prints the table.

## 5. Smoke results (20 problems, cap 8192)

| | Arm 0 (thinking on) | Arm B (thinking off) |
|---|---|---|
| Accuracy, truncated at 2k / 8k | 0/20 = 0.00 / 0.00 | 5/20 = 0.25 / 8/20 = 0.40 |
| Finished before cap | 0 of 20 (all 20 cut at 8192, no box) | 12 of 20 (8 cut, no box) |
| Tokens: total / median / max | 163,840 / 8,192 / 8,192 | 92,406 / 4,236 / 8,192 |
| Generation wall time | 2,682.5 s | 2,993.4 s |
| tokens/s (non-pad tokens / wall) | 61.1 | 30.9 (padding wastes the slots of finished answers; slot rate is 54.7) |
| s per step, first 1k steps / last 1k | 0.273 / 0.412 | 0.322 / 0.417 |
| Mean GPU watts (generation window) | 7.07 | 6.80 |
| Joules GPU gross / net of 5.05 W | 18,972 / 5,420 | 20,341 / 5,222 |
| Joules per generated token (gross) | 0.116 | 0.220 |
| Idle fraction (util == 0) | 0.0 | 0.0 |
| Peak CUDA memory allocated | 5.16 GiB | 5.17 GiB |

### 5a. Arm A (released edit rebuilt from the authors' diff), added 2026-11-20 as a LABELLED RUNTIME SMOKE, no hypothesis attached

Same 20 problems, same settings as arm 0 (thinking on, T 0.6, top_p 0.95, top_k 20, presence 1.5), cap 8192, same 20 percent GPU memory limit and expandable segments, same container flags. Weights: `runs/t7-smoke/armA/` = the rebuilt `model.safetensors-00001-of-00001.safetensors` (re-run of `t7_rebuild.py` immediately before the run: base sha256 equal to the manifest before editing, per-tensor base and edited hashes asserted, exactly 2 of 488 tensors differ and match the model-card hashes, base unchanged after; rebuilt file sha256 fd1e42ac...f737b553) plus symlinks to the base's config, tokenizer and index. After the run the base files were re-hashed: no change. Idle baseline for this run: a fresh 30 s record, 4.90 W (arms 0 and B used their own earlier records, 5.05 W).

| | Arm A (edited, thinking on) | for comparison: arm 0 / arm B |
|---|---|---|
| Accuracy at 2k / 8k | 0/20 = 0.00 / 1/20 = 0.05 | 0.00 / 0.00 ; 0.25 / 0.40 |
| Finished before cap | 1 of 20 (2,263 tokens, correct); 19 cut at 8192, no box | 0 ; 12 |
| Tokens total | 157,911 | 163,840 ; 92,406 |
| Generation wall time / tokens per s | 2,859.8 s / 55.2 | 2,682.5 s / 61.1 ; 2,993.4 s / 30.9 |
| Mean GPU watts | 6.87 | 7.07 ; 6.80 |
| Joules gross / net | 19,653 / 5,637 | 18,972 / 5,420 ; 20,341 / 5,222 |
| Joules per generated token (gross) | 0.1245 | 0.116 ; 0.220 |
| Joules per passing problem, gross / net | 19,653 / 5,637 (1 passing problem) | n/a (0 passing) ; 2,543 / 653 (8 passing) |
| Peak CUDA memory | 5.16 GiB | 5.16 ; 5.17 |
| Idle fraction (util == 0) | 0.0 | 0.0 ; 0.0 |

Reading (n = 20, no claim): in this runtime smoke the edit did not stop the loop at 8k; 19 of 20 generations still ran to the cap, against the post's 31.6 percent cut at 32,768 tokens on MATH-500 (a different cap, sample size and engine). Joules per passing problem for A rests on one passing problem and is not a stable number.

n = 20 per arm: these are smoke numbers, not an effect estimate. Arm 0 at 8k scoring 0/20 agrees in direction with the post's 7.9 percent at 32,768 and its 92 percent hit rate; arm B finishing only 12 of 20 below 8k is a finding to note against the post's claim that thinking-off fixes the loop.
The run was GPU-light (about 7 W, 30 to 60 percent utilisation): it is bound by per-step Python and torch-fallback kernel overhead, not by arithmetic.

## 6. Projection of the main T7 versus the 12 GPU-hour cap: EXCEEDS, STOP

Measured per-step time: batch 20 rises from 0.273 s (start) to 0.412 s (step 8192), about 1.9e-5 s per step of length; batch 100 measured at 0.45 s per step at about 200 steps (probe, `probe100`), about 1.65 times batch 20. With HF `generate` a batch runs until its longest sequence ends, so any batch containing one looping answer runs the full cap (arm B above: 12 of 20 finished, yet the batch ran 8192 steps).
Extrapolation (linear in length, not measured beyond 8192; the cap-32,768 cost is an estimate): batch-100 mean step about 0.97 s over 32,768 steps = about 31,800 s = **about 8.8 GPU-hours for one arm**. The main T7 needs six such runs (0, A, B, C, D, D random null; with 100 problems each) = **about 53 GPU-hours, about 4.4 times the cap**, before the off-target IFEval and MMLU-Pro subsets for A to C. Even arm 0 alone (about 8.8 h) uses 73 percent of the cap. Energy at about 7 W GPU-only: about 1.3 MJ (0.37 kWh); electricity is not the constraint, wall time is.
Why this is not a "shrink n" case: the cost is per-step latency times length, and it barely depends on n up to 100. What would change it, each needing an owner decision: (1) flash-linear-attention and causal-conv1d (fast path, not approved), (2) vLLM (the authors' engine; continuous batching removes the straggler cost; not approved), (3) a lower token cap for the looping arms (changes the registered 32,768 cap), (4) a larger cap budget. I did none of these.

### 6a. GPU-hours consumed against the 12 GPU-hour G9 cap (wall-clock of containers with the GPU, one GPU)

| Item | Hours |
|---|---|
| Completed runs, container start to end (generation plus about 40 s load each): arm 0 2,722 s, arm B 3,033 s, arm A 2,900 s | 2.40 |
| Killed or abandoned attempts and diagnostics, estimated from log and CSV timestamps (the power CSVs of the killed runs were overwritten): arm 0 first attempt 22 min (measured), arm B first attempt about 13 min, second arm 0 attempt about 18 min, third about 3 min, the two timing probes about 3 min, leak diagnostics and microbenchmarks about 30 min | about 1.4 |
| **Total so far** | **about 3.8** (completed runs exact, the rest estimated within about 0.2) |
| **Remaining under the 12 h cap** | **about 8.2**, which is less than one full-length thinking arm at batch 100 (about 8.8 h, section 6) |

## 7. Arm C: repetition-penalty proposal (text only)

The published sampling already has `presence_penalty` 1.5, so C must be a different mechanism. Proposal: keep presence 1.5 and add a multiplicative `repetition_penalty` (transformers semantics, over prompt and output) from {1.05, 1.10, 1.15}, chosen on practice problems only (40 problems from the clone's `practice/math_train.jsonl`, never MATH-500), picking the smallest value that minimises the verbatim-loop rate (`loop_signals`) without lowering accuracy at 8k; default 1.10 if the practice run is not done. One value, fixed before any benchmark run, recorded in the prereg. Risk: a penalty over the prompt also discourages copying numbers from the problem; the practice run must report that.

## 8. Arm D: direction-script plan (text only)

1. Data: loop windows = the last 256 tokens of arm 0 answers flagged by `loop_signals` (verbatim_loop_end) on practice problems; control windows = tokens 256 to 512 of finished answers. Practice problems only.
2. Direction: residual-stream activations at the input of layers 15 and 19 `down_proj` output (1024-dim); `d = diff_of_means(loop, control)` (existing `t7_edit.diff_of_means`), unit norm.
3. Columns: of the 3,584 MLP hidden units per layer, pick the 64 whose write vector `W[:, j]` projects most on `d` (score `|W[:, j] . d|` times mean `|activation_j|` on the control windows), as the published edit touches 64 columns per layer.
4. Edit: new column = `W[:, j] - (W[:, j] . d) d`, computed in float32 and rounded to bf16, written to a copy under `runs/` as a column spec for `t7_edit.apply_column_edit`; base sha256 checked from the manifest first, base re-hashed after.
5. Null: a random unit direction (fixed seeds, 3 draws), the same column-selection rule and the same count, same norm of removed component. D is dropped if it does not beat the null (paired bootstrap on the same 100 problems), as the plan says.

## 9. Incidents and caveats (read these)

- **Host memory loss, cause not identified.** Three early attempts lost host memory (MemAvailable fell from 73 GiB to 9.97 and 9.44 GiB): the watchdog killed arm 0 (about 22 min in) and arm B (about 13 min in), and I killed a third arm 0 attempt at 27 GiB. My container's cgroup showed only about 1.8 GiB and torch's own counters stayed at 2 to 3 GiB; memory returned as soon as the container died. Microbenchmarks of my sampler, multinomial, the padded prompt and plain greedy generation did not reproduce it. After I added `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` and `torch.cuda.set_per_process_memory_fraction(0.2)` and per-256-step memory logging, arm 0 and arm B both completed with MemAvailable steady at 66 to 68 GiB. I do not know which change fixed it, or whether the cause was external; the 10 GiB hard stop never fired on the completed runs. Treat this as an open risk for the main run.
- A first set of killed attempts left `arm0.log`, `armB.log` and power CSVs that were overwritten by the completed runs; no result file from a killed run was used.
- The shared GPU also serves spark-vllm (about 28 GiB). Its activity during my runs is not separated from my joules.
- Not done: no vLLM, datasets, accelerate, peft, Unsloth or IFEval packages; no edited-checkpoint download; no main T7; no commit or push.

- Accuracy at a cap (`accuracy_at_cap`) counts a generation as correct if its last box matches and its token count is within the cap; a cut-off generation that already contained a correct box would be credited. In the smoke every correct answer had finished (B 8 of 8, A 1 of 1), so no credit came from a cut-off.
- All three arms share one RNG stream per batch (not one seed per problem), so per-problem outcomes are not independent draws; n = 20, 95 percent intervals are wide (for example 1/20 spans roughly 0 to 25 percent).
- Arm A was run after arms 0 and B, in a different GPU time slot shared with spark-vllm; the idle record that sets the net-joule baseline differs (4.90 W versus 5.05 W), so net joules across arms differ by that much per second.

## 10. Files written

`train/Dockerfile`, `train/fetch.py`, `train/t7_samples.py`, `train/t7_gen.py`, `train/t7_host.py`, `train/t7_rebuild.py`, `train/t7_report.py`, `train/vendor/` (MIT, notice in each file), `tests/test_t7_samples.py`, `tests/test_t7_gen.py`, this note; artifacts under `data/` (hf, math500, edits) and `runs/t7-smoke/`.
