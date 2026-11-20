# G3(i) evidence: model and dataset metadata (no downloads of weights or data)

Fetched 2026-11-19 by python urllib from the public HF API (`?blobs=true` for sizes) and `raw/main` files. Nothing pulled, nothing installed. Owner asks (cache directory, licence confirmation) are NOT done here.

## 1. Base model: `Qwen/Qwen3.5-0.8B` (OPENED yes: API JSON, LICENSE, card header)

| Field | Value |
|---|---|
| revision sha | `2fc06364715b967f1860aea9cf38778875588b17` (same as the revision named in `apply_edit.py` and the edit README) |
| lastModified | 2026-03-02T11:26:58.000Z |
| gated / private | `False` / `False` |
| licence tag | `license:apache-2.0`; cardData `license: apache-2.0`, `license_link: https://huggingface.co/Qwen/Qwen3.5-0.8B/blob/main/LICENSE` (the top-level API `license` field is null; the tag carries it) |
| LICENSE file | 11,544 B, 202 lines, first lines "Apache License / Version 2.0, January 2004" |
| library / pipeline | transformers / image-text-to-text (full multimodal release) |
| downloads | 2,676,111 |

Files and sizes (bytes):

| File | Size |
|---|---|
| model.safetensors-00001-of-00001.safetensors | 1,746,942,600 |
| tokenizer.json | 12,807,982 |
| vocab.json | 6,722,759 |
| merges.txt | 3,353,259 |
| README.md | 61,705 |
| model.safetensors.index.json | 50,900 |
| tokenizer_config.json | 16,709 |
| LICENSE | 11,544 |
| chat_template.jinja | 7,755 |
| config.json | 2,907 |
| .gitattributes | 1,570 |
| preprocessor_config.json | 390 |
| video_preprocessor_config.json | 385 |
| **Total** | **1,769,980,465 B (1.77 GB, 1.65 GiB)** |

## 2. Edited checkpoint: `RikiyaT/Qwen3.5-0.8B-weight-space-programming` (OPENED yes: API JSON, README raw, LICENSE)

Where the ID comes from: the blog post (https://rikiyat.github.io/blog/weight-space-programming/), section "Logs", link text "Hugging Face". The cloned repo `lm_understand-logs` does not name it (see G9-repo-review.md). The model card itself links back to the repo and to the blog, so the pair is consistent.
The ID exists: yes, public.

| Field | Value |
|---|---|
| revision sha | `d1671a178705bcab7644806d23c535517f35723b` |
| createdAt / lastModified | 2026-11-02T22:12:58.000Z / 2026-11-02T22:13:54.000Z |
| gated / private | `False` / `False` |
| licence tag | `license:apache-2.0`; cardData `license: apache-2.0`, `base_model: Qwen/Qwen3.5-0.8B` |
| LICENSE file | 11,544 B, 202 lines, "Apache License / Version 2.0, January 2004" (same size as the base) |
| downloads | 5,836 |
| tags | ml-intern, weight-space-programming, base_model:finetune:Qwen/Qwen3.5-0.8B |

Files and sizes (bytes):

| File | Size |
|---|---|
| model.safetensors-00001-of-00001.safetensors | 1,746,943,032 |
| eval/samples_edited_math500.jsonl | 7,818,699 |
| tokenizer.json | 12,807,982 |
| vocab.json | 6,722,759 |
| merges.txt | 3,353,259 |
| eval/samples_base_math500.jsonl | 1,626,439 |
| model.safetensors.index.json | 50,900 |
| eval/scores_edited_math500.json | 48,899 |
| tokenizer_config.json | 16,709 |
| README.md | 4,876 |
| chat_template.jinja | 7,755 |
| config.json | 2,907 |
| eval/scores_base_math500.json | 2,794 |
| LICENSE, .gitattributes, preprocessor_config.json, video_preprocessor_config.json | 11,544 / 1,570 / 390 / 385 |
| **Total** | **1,779,420,899 B (1.78 GB)** |

Weights file is 432 bytes larger than the base file (1,746,943,032 vs 1,746,942,600), consistent with a re-serialized safetensors header, not a different tensor set (inference; the hash check below settles it).

Model card facts (README raw, quoted):
- "Only these two tensors differ from `Qwen/Qwen3.5-0.8B` @ `2fc06364715b967f1860aea9cf38778875588b17`": `model.language_model.layers.15.mlp.down_proj.weight` sha256 `82e2d733ea64feaeb4af93a1e065641d3df98b494a8b7576ef2f52e90fe2ee53`; `model.language_model.layers.19.mlp.down_proj.weight` sha256 `8ef3c61bc36af113ad58e89dbb0a4a14dcba5a45cb750c15ab515c82ddd12eb2` (sha256 of the raw bfloat16 bytes). After download, our manifest must reproduce these; they should also equal `edited_sha256` in `exp8_math/runs/p50c/edit/manifest.json` (not yet compared; do it in the download step).
- Built "by akhaliq with ML Intern on Hugging Face Jobs, 2026-11-02: the edit was rebuilt and hash-verified on CPU" using `exp8_math/code/apply_edit.py`. The rebuild was done by a third party (akhaliq), but the repo sits under the post author's account `RikiyaT`, and the blog links it.
- "One substitution: the post evaluated a text-only export of the model, and this checkpoint is the full multimodal release. The language-model tensors are identical (hash-verified), and text prompts do not use the vision tower."
- Independent re-run (model card claim, not reproduced by us): MATH-500 51.0%, 31.6% hit the token limit; base 25-problem smoke test 5.0%, 95% hit the limit; vLLM 0.33.0 / transformers 5.20.2 / math-verify 0.9.0, 51 min on an H200.
- Licence line (card header): `license: apache-2.0`; "Base model: Qwen/Qwen3.5-0.8B, Apache 2.0".

Licence status: Apache-2.0 for both IDs, tags and LICENSE text agree. Not blocking. Owner confirmation still needed (WORKPLAN G3(i) item 2).

Sizing for the download decision: both models = 3.55 GB; base only = 1.77 GB. The edited weights can be rebuilt bit-exact from the base with `apply_edit.py`, so the 1.78 GB edited download is optional (the HF copy is a cross-check, and arm A would be run from the rebuilt file).

## 3. Datasets (OPENED yes: HF API JSON, cards, file sizes, row counts)

| Dataset (HF id) | Revision sha | Licence | Gated | Size | Rows | Source URL |
|---|---|---|---|---|---|---|
| `HuggingFaceH4/MATH-500` | `6e4ed1a2a79af7d8630a6b768ec859cb5af4d3be` | none on the HF card (cardData has no `license`, no licence tag) | False | `test.jsonl` 446,564 B | 500 (counted) | https://huggingface.co/datasets/HuggingFaceH4/MATH-500 ; card says it is 500 problems "from the MATH benchmark that OpenAI created in their _Let's Verify Step by Step_ paper", source https://github.com/openai/prm800k |
| `google/IFEval` | `966cd89545d6b6acfd7638bc708b98261ca58e84` | `apache-2.0` (tag and cardData) | False | `ifeval_input_data.jsonl` 207,111 B | 541 (counted) | https://huggingface.co/datasets/google/IFEval |
| `TIGER-Lab/MMLU-Pro` | `b189ec765aa7ed75c8acfea42df31fdae71f97be` | `mit` (tag and cardData) | False | `data/test-00000-of-00001.parquet` 4,144,185 B; validation 42,857 B | test 12,032; validation 70 (API splits) | https://huggingface.co/datasets/TIGER-Lab/MMLU-Pro |
| `openai/gsm8k` (practice and reference only) | `740312add88f781978c0658806c59bc2815b9866` | `mit` | False | main train 2,306,545 B, test 419,088 B | main train 7,473, test 1,319 | https://huggingface.co/datasets/openai/gsm8k |

IFEval and MMLU-Pro dataset IDs are my choice of the canonical ones; the cloned repo does not name them (it names only the MATH-500, GSM8K, AIME, AMC, Minerva and Olympiad IDs). The repo's MMLU-Pro subset is "a fixed random 1,000 of 12,032" and the ids are in the per-problem files (`mmlupro_<n>`, 1000 ids), consistent with the 12,032 total. The IFEval ids in the repo number 541, matching `google/IFEval`.

MATH-500 licence analysis: unlabelled on HF. Upstream sources: `openai/prm800k` LICENSE first lines "MIT License / Copyright (c) 2023 OpenAI" (OPENED yes); `hendrycks/math` LICENSE "MIT License / Copyright (c) 2021 Dan Hendrycks" (OPENED yes). The `DigitalLearningGmbH/MATH-lighteval` mirror of MATH is tagged `mit`. The inference is MIT upstream; the HF card for the 500 subset states no licence. Status: UNCLEAR on the artifact itself, MIT upstream. Low risk for local evaluation (no redistribution); owner should confirm if we ever publish problems.

### IFEval checker needs extra packages: YES
The authors' IFEval checkers are not in `lm_understand-logs` (their README: IFEval's official checkers "Not included"; `evaluate.py` imports a private `weightenv.lmo.tasks.ifevalg`). The official code is `google-research/google-research/instruction_following_eval` (repo LICENSE: "Apache License, Version 2.0", OPENED yes). Its `requirements.txt` (OPENED yes) lists exactly: `absl`, `langdetect`, `nltk`, `immutabledict`; `instructions.py` imports `absl`, `langdetect` and the sibling `instructions_util` (nltk). nltk also needs tokenizer data downloaded at first use (not verified here; standard behaviour). Per WORKPLAN Wave 2 item 7 ("Stop if a licence is unclear or the IFEval checker needs packages") this is a stop and an owner ask: a code fetch from GitHub plus four pip packages and nltk data.

## 4. Summary of what is NOT verified

- No weights hashed; the two tensor hashes from the model card are quoted, not recomputed.
- `edited_sha256` in our local manifest was not compared to the model card hashes.
- vLLM, math-verify, numpy availability inside `nvcr.io/nvidia/pytorch:25.11-py3` was not checked (no docker run).
- Model-card eval numbers (51.0%) and the post's 48.1% are claims by third parties and the authors; none reproduced.
- Licence texts were read at the licence line and file header only, not legally reviewed.
