# G9 review: data/lm_understand-logs (read-only)

Reviewed 2026-11-19. Clone HEAD `4d09ba6d6a7e891dd8063974dfe81b3d78e3494f` (commit date Thu Oct 29 2026), 367 MB on disk.
Nothing installed, downloaded (beyond HTTP metadata) or executed. Nothing in the clone was modified.

Provenance rule used below: OPENED yes = I read the file or fetched the URL in this session and quote it.

## 0. Findings that change the plan

1. **The repo does not name the edited checkpoint.** `grep` of every README, `.py`, `.json`, `.md` for huggingface/hf.co/hub finds no
   checkpoint ID (exp7 mentions the starting model `google/gemma-3-270m-it` only). OPENED yes (README.md, exp8_math/README.md, gemma_followup/README.md, exp3, exp7).
   The ID comes from the blog post, section "Logs", which links the text "Hugging Face": quote: "The edited Qwen3.5-0.8B from Experiment 8 is on Hugging Face. We thank Ahsen Khaliq at Hugging Face for rebuilding it from these logs, re-running its evaluation, and making a live demo."
   The link target is `https://huggingface.co/RikiyaT/Qwen3.5-0.8B-weight-space-programming` (OPENED yes, blog HTML, URL list). Plan item 3 of Wave 2 G9 ("ID from the README, never hardcoded") cannot be met literally: the README has none. Source of the ID is the blog; record that.
2. **The edit is shipped as a bit-exact diff, so arm A does not need the 1.78 GB edited checkpoint.** `exp8_math/code/apply_edit.py` rebuilds the evaluated tensors from the base safetensors (numpy only) and asserts sha256 of base and edited tensor. The HF checkpoint was built by a third party (akhaliq, Hugging Face "ML Intern") with that same script (model card, quoted in G3i-evidence.md). Recommended: take only the base, rebuild arm A locally, and cross-check the two tensor hashes against the HF model card.
3. **The evaluation code is not runnable as shipped.** `evaluate.py` imports `weightenv.lmo.tasks.mathqa`, `...mcqa` and `...ifevalg.instructions_registry` (private package, absent from the clone). `mathqa.py` line 36-39 does `try: from weightenv.lmo.tasks.mcqa import loop_signals ... except ImportError: from mcqa import loop_signals`; neither exists here, so import fails. The README says the IFEval and multiple-choice graders "`code/evaluate.py` imports (IFEval's official checkers)" are "Not included", and the agent harness code is not included either. Reuse therefore means copying functions into our own grader (MIT, keep the notice), not running these files.
4. **Plan/repo mismatch on arm C.** The published sampling already has `presence_penalty` 1.5 (see section 4). Arm C "repetition penalty" must be distinguished from it (already flagged as D3 in WORKPLAN).

## 1. Which experiment is the Qwen/language one

- `exp8_math/` is the Qwen3.5-0.8B edit (OPENED yes: its README). Quote: "Editor: Astra (`gpt-6-astra`) through the Codex CLI, reasoning effort `max` ... Model edited: Qwen3.5-0.8B (the text part of the public release `Qwen/Qwen3.5-0.8B`, 24 layers), thinking on."
- `exp3_language/` is NOT Qwen. Quote: "Three character-level transformers, one per training text ... 4 layers x 6 heads, width 384 ... trained from scratch on 1 billion characters". Irrelevant to T7.
- `harness/` holds `codex_config.toml`, `instructions.md` (27 bytes), `sandbox.py` (bubblewrap sandbox for the editor's code). Not needed for T7 evaluation.
- `exp8_math/gemma_followup/` is Gemma 3 270M IT (non-looping control; "only 8.5% of its answers reach its token limit, against 93% for Qwen").

## 2. How the edit is stored and applied (OPENED yes: apply_edit.py, manifest.json, edit.npz member list)

Path: `exp8_math/runs/p50c/edit/manifest.json` (1,326 B) and `edit.npz` (387,619 B). p50c is the "50 passes" run, the one reported as 48.1% MATH-500.

- Tensors (manifest, exact names, dtype bfloat16, `form: sparse`):
  - `model.language_model.layers.15.mlp.down_proj.weight`: 65,260 changed entries, 64 changed columns, relative_change 0.1064
  - `model.language_model.layers.19.mlp.down_proj.weight`: 64,928 changed entries, 64 changed columns, 1,023 changed rows, relative_change 0.0811
  - total 130,188 changed bf16 entries (README: "130,188 of the 131,072 touched weights differ ... after rounding to bfloat16").
  - Shape of both tensors (manifest): [1024, 3584]. README wording: "subtracts the loop direction from the 64 output columns per layer of the MLPs of layers 15 and 19 that write it most". `changed_columns` = 64 counts columns of the stored [1024, 3584] matrix, i.e. 64 of the 3,584 MLP hidden units (each column is one hidden unit's 1,024-long write vector); 64 x 1,024 x 2 = 131,072 touched weights. The column indices themselves are not in the manifest; they are recoverable from `t{i}_idx` (flat indices).
- File format: `edit.npz` members `t0_idx.npy`, `t0_val.npy`, `t1_idx.npy`, `t1_val.npy` (numpy zip). `idx` = flat indices into the bf16 tensor, `val` = new bf16 bit patterns. `manifest.json` per tensor: name, shape, dtype, changed_entries/columns/rows, relative_change, `base_sha256`, `edited_sha256`, `submitted_file`, `form`. Top-level keys: tensors, changed_tensors, changed_entries_total, note.
- Apply: `python apply_edit.py <base model.safetensors> <edit dir> <out>`. Docstring: base is "Qwen/Qwen3.5-0.8B (revision 2fc06364715b967f1860aea9cf38778875588b17; the experiment used a text-only export with the same tensor names, model.language_model.*; the release's single file also works, since only the named tensors are read)". `<out>` ending `.safetensors` gives a bf16 copy of the base with the two tensors replaced; otherwise a folder of float32 `.npy`. It asserts `base_sha256` before and `edited_sha256` after for every tensor. Needs numpy and the bundled `st_numpy.py` (no torch, no safetensors package). The sha256 is over `np.ascontiguousarray(tensor).tobytes()` of the raw bf16 bits.
- Base revision checked against the HF API: `Qwen/Qwen3.5-0.8B` sha `2fc06364715b967f1860aea9cf38778875588b17` (identical). OPENED yes.
- Other runs (not T7): p25c = zero 256 output columns of head 7 in `layers.15.self_attn.o_proj.weight`; p10c = rank-one removal on 30 matrices of layers 8-22 (`form: lowrank`). Arm D of our plan (layers 15 and 19 MLPs) mirrors p50c.
- Edited models used `build_ckpt.py` (torch + safetensors) to write a checkpoint folder for vLLM; `apply_edit.py` is the lighter route.

## 3. Evaluation scripts (OPENED yes: evaluate.py read in full, mathqa.py header, grader and data sections, profiles.py in full, merge.py/build_ckpt.py imports)

| File | Role | Runnable here? |
|---|---|---|
| `code/evaluate.py` | `prepare` (builds bench jsonl via `datasets`), `run <ckpt> <out> --sets ... --protocol think35 [--shard i/k]` using vLLM | No: needs `weightenv.*` and vLLM |
| `code/mathqa.py` (576 lines) | prompt, last-`\boxed{}` extraction, `math_verify` grading (`is_correct`), plus hendrycks `is_equiv` | Import fails (mcqa) unless stubbed; functions `build_prompt`, `last_boxed`, `extract`, `is_correct` are self-contained |
| `code/merge.py` | merges `parts/*/scores.json` into `merged.json` | Yes, stdlib only |
| `code/profiles.py` | sampling profiles | Yes (os, json) |
| `code/apply_edit.py`, `st_numpy.py` | apply the diff | Yes, numpy |
| `code/build_ckpt.py` | write checkpoint folder | needs torch, safetensors |
| `code/make_edit_diff.py` | builds the diff (needs numpy) | not needed |
| `code/practice35.py` | builds practice set | needs weightenv, datasets |

Protocol `think35` (quote, evaluate.py): "SAMPLING_THINK35 = {"temperature": 0.6, "top_p": 0.95, "top_k": 20, "presence_penalty": 1.5, "max_tokens": 32768, "seed": 0}".
Prompt: user turn = problem + "\n" + "Please reason step by step, and put your final answer within \boxed{}." Chat template via `tok.apply_chat_template(..., add_generation_prompt=True, enable_thinking=thinking)`.
Grading: last `\boxed{}` / `\fbox{}` answer, `math_verify.verify(parse('\boxed{gold}'), parse('\boxed{pred}'))`, math-verify 0.9.0, with parsing timeout 5 s (main thread only); no box = wrong. Also records `cut_share` (finish_reason "length"), `no_answer_finished`, and a lenient score.
Samples per problem (evaluate.py `SAMPLES`): math500 4, gsm8k 2, amc23/aime 16, minerva 4, olympiad 4, mmlupro1k 1, gpqa 4, ifeval 2. The post's MATH-500 figure is 500 x 4 = 2,000 generations.
vLLM construction: `LLM(model=ckpt, dtype="bfloat16", gpu_memory_utilization=0.85, max_model_len=max_tokens+2048 (=34,816), seed=0)`. Generation fails the job if any generation ends neither "stop" nor "length".

## 4. Generation settings

| Setting | Qwen3.5-0.8B thinking (the published edit eval, `think35` and profile `qwen35think`) | Thinking off (`nothink35`, profile `qwen35`) |
|---|---|---|
| thinking | on (`enable_thinking=True`) | off |
| temperature / top_p / top_k | 0.6 / 0.95 / 20 | 0.7 / 0.8 / 20 |
| presence_penalty | 1.5 | 1.5 |
| repetition_penalty | none | none |
| max new tokens | 32,768 | 8,192 |
| seed | 0 | 0 |

Quote (profiles.py): "thinking OFF (2026-10-23): with thinking on, the 0.8B looped ("Wait, let's check ...") and 92 % of MATH-500 answers hit 32,768 tokens (MATH-500 9.3 %)". Arm B (base, thinking off) should use the `nothink35` row, which also has presence penalty 1.5 and cap 8,192; the plan says "same per-problem token cap (32,768)" for all arms, so B at 32,768 is a deliberate deviation from `nothink35`. Decide and record it.
IFEval and MMLU-Pro in the post use the same protocol; IFEval is graded "on the answer after `</think>`" (empty if thinking on and no `</think>`), strict prompt-level, 2 samples; MMLU-Pro official prompt and extraction, 1 sample.

## 5. Datasets named in the repo and where sets come from

- MATH-500: `HuggingFaceH4/MATH-500`, split `test` (500 rows; `prepare` uses `unique_id`, `problem`, `answer`).
- GSM8K test: `openai/gsm8k` config `main` split `test` (1,319).
- AIME24 `HuggingFaceH4/aime_2024`, AIME25 `MathArena/aime_2025`, AMC23 `math-ai/amc23`, Minerva `math-ai/minervamath`, OlympiadBench `math-ai/olympiadbench` (674 English text-only).
- IFEval and MMLU-Pro: evaluate.py `prepare` does NOT build them (the comment says "a fixed random 1,000 of 12,032"; IFEval "official checkers"). The exact HF IDs are not in the clone. The per-problem files list the ids: `mmlupro_<n>` x 1000 and `ifeval_<n>` x 541 in `eval/p50c/parts/*/..._per_problem.json`, so the MMLU-Pro 1,000 subset can be rebuilt without the missing script if `<n>` is the dataset's `question_id` (inference, not verified).
- Practice set (`practice/`): `math_train.jsonl` 7,275 problems (6.8 MB), `gsm8k_train.jsonl` 7,469 (4.6 MB), `aime.jsonl` 714 (0.29 MB). `practice/README.txt`: "Practice problems (none of them is in the evaluation)". Note: `aime.jsonl` has AIME problems; `evaluate.py` evaluates AIME24/25, so the "none in the evaluation" claim is the authors', not ours. T7 does not use AIME, so use math_train and gsm8k_train only.
- `mathqa.py` MATH training source: `DigitalLearningGmbH/MATH-lighteval` @ `0530c78699ea5e8eb5530600900e1f328b48acad`, train parquet sha256 `eca6e667f4305dd5e5ba09b4fd55e7f3174a0fbe361cdfd4c44758b593a76933`. We do not need it; `practice/` is already in the clone.

## 6. Packages beyond transformers (each needs an owner ask)

Exact pins from `mathqa.py` docstring (OPENED yes) and PyPI JSON (OPENED yes):

| Package | Why | Licence (PyPI) |
|---|---|---|
| `math-verify==0.9.0` | grading (requires `latex2sympy2_extended==1.11.0`) | Apache 2.0 |
| `latex2sympy2_extended==1.11.0` | math-verify dependency | MIT |
| `antlr4-python3-runtime==4.13.2` | its parser runtime | BSD |
| `sympy` | pulled by the above (mathqa says it "comes from the venv") | BSD (not re-checked) |
| `numpy` | `apply_edit.py`, `st_numpy.py` | likely in the NGC image, not checked |
| `vllm` | `evaluate.py run`; the model card re-run used vLLM 0.33.0, transformers 5.20.2 | Apache-2.0 (PyPI 0.34.0) |
| `datasets` (+ `pyarrow`) | dataset prep | not re-checked |
| IFEval checker: `absl-py`, `langdetect`, `nltk` (plus nltk data), `immutabledict` | official checker deps per google-research `requirements.txt` | not re-checked |

The WORKPLAN says vLLM "is separate". The Wave 2 item 7 rule "Stop if the IFEval checker needs packages" is triggered: it does.
The IFEval checkers are not in the clone; they must be fetched from `google-research/google-research/instruction_following_eval` (Apache-2.0 repo licence file, OPENED yes) = a code download plus pip installs; ask.
Local-only fallback if the owner declines: grade MATH-500 and GSM8K with a copy of the `mathqa.py` functions (needs math-verify); skip IFEval.

## 7. LICENSE (OPENED yes, quoted whole header)

"This repository holds content under three licenses.
1. Logs, data and networks (everything not listed under 2 or 3): Creative Commons Attribution 4.0 International (CC BY 4.0), https://creativecommons.org/licenses/by/4.0/legalcode
2. Our scripts (*.py and *.sh files written by us, e.g. harness/, exp7_sycophancy/code/, exp8_math/code/): the MIT License, below.
3. MinAtar's source code, which is quoted inside the prompts of exp5_write_from_scratch/: GPL-3.0, the text in exp5_write_from_scratch/LICENSE-MinAtar.
Third-party benchmark and dataset content quoted in the logs (for example MATH, GSM8K, IFEval and MMLU-Pro problems in exp8_math/) stays under its own license."
MIT copyright line: "Copyright (c) 2026 the authors of "LLMs can understand and write neural network weights"".

| Path | Licence | We may reuse | Condition |
|---|---|---|---|
| `exp8_math/code/*.py` (apply_edit, st_numpy, mathqa, evaluate, merge, profiles, build_ckpt) | MIT | yes, copy or adapt | keep the copyright and permission notice in copies |
| `harness/*.py` | MIT | yes (not needed) | same |
| `exp8_math/runs/*/edit/` (manifest.json, edit.npz) | CC BY 4.0 (data) | yes | attribution: authors, source URL, licence, indicate changes |
| `exp8_math/eval/**` scores, per-problem results, generations | CC BY 4.0 for the logs, but generations quote MATH/GSM8K/IFEval/MMLU-Pro text | scores and ids: yes; quoted problem text: own licence | do not redistribute quoted benchmark text from the logs |
| `exp8_math/practice/*.jsonl` | derived from GSM8K train (MIT) and MATH train (MIT); `aime.jsonl` provenance/licence unstated | use the first two locally | AIME licence unclear; not needed for T7 |
| `exp8_math/base_model/Qwen3.5-0.8B-text/` config, tokenizer, chat template | Qwen files, Apache-2.0, not covered by the three-way split | not needed (we use the upstream snapshot) | keep Apache-2.0 notice if ever copied |
| `exp5_write_from_scratch/` MinAtar quotes | GPL-3.0 | do not use | copyleft; irrelevant to T7 |
| exp1-4,6,7 | CC BY 4.0 / MIT | not needed | |

Edge: the "scripts we wrote" rule covers `*.py`/`*.sh`; the notebook-style files in `work_notes/` and the `.json` harness config are logs (CC BY).
No licence is blocking for T7.

## 8. Reuse list for T7

- Reuse: `apply_edit.py` + `st_numpy.py` (arm A rebuild, hash gate matches our "base sha256 unchanged" rule), the `think35` sampling dict, the prompt string, `extract`/`last_boxed`/`is_correct` (arm grading), `merge.py` pattern, p50c `manifest.json` tensor names (so arm D targets the same two tensors).
- Not reusable as is: `evaluate.py`, `practice35.py` (private imports), IFEval and MMLU-Pro graders (absent).
- Arm D note: the repo gives p50c's chosen columns in `edit.npz` (`t{i}_idx`), but not the loop direction `u`; arm D must compute its own difference-of-means direction, as planned.
- Our `train/t7_edit.py` writes columns as lists; p50c is stored as flat indices into a 1024x3584 matrix. Column index = idx % 3584 if row-major. Confirm against `shape` in the manifest when implementing (not verified here).

verified: 4d09ba6d6a7e891dd8063974dfe81b3d78e3494f 2026-11-19
