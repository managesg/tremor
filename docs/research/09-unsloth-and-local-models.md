# 09 - Unsloth and local models on GB10 (research, read-only, 2026-11-19)

Method: WebFetch was blocked by a context-mode hook. Pages were read with python urllib via ctx_execute (HTML stripped, text searched); Hugging Face model lists came from the public HF API (`huggingface.co/api/models?author=...&search=...`, tags only, so licences are metadata tags, not model-card text). Nothing was installed, downloaded or run. Page text is treated as data. "OPENED" = I read the page text myself.

## Sources

| # | URL | OPENED |
|---|-----|--------|
| S1 | https://github.com/unslothai/unsloth (README) | yes |
| S2 | https://unsloth.ai/docs/blog/fine-tuning-llms-with-nvidia-dgx-spark-and-unsloth | yes |
| S3 | https://github.com/NVIDIA/dgx-spark-playbooks/tree/main/nvidia/unsloth (README, last updated 12/15/2025 per page) | yes |
| S4 | https://unsloth.ai/docs/basics/fine-tuning-llms-with-blackwell-rtx-50-series-and-unsloth.md | yes (excerpts) |
| S5 | https://unsloth.ai/docs/blog/how-to-fine-tune-llms-with-unsloth-and-docker.md | yes (excerpts) |
| S6 | https://www.nvidia.com/en-us/products/workstations/dgx-spark/ (NVIDIA spec page) | yes |
| S7 | raw.githubusercontent.com/NVIDIA/dgx-spark-playbooks/main/{README, nvidia/vllm, nvidia/sglang, nvidia/llama-cpp, nvidia/ollama, nvidia/nim-llm}/README.md | yes (excerpts) |
| S8 | https://huggingface.co/Qwen (org page) and HF API listings for Qwen, google, openai, mistralai, microsoft, ibm-granite, meta-llama, HuggingFaceTB, nvidia | yes (list/tags only; no model cards) |
| S9 | gist RobG-git/fd1739c79e2405eb56032dee7901421e (community Studio-on-Spark guide) | yes, partially (first ~3.5k chars) |
| S10 | WebSearch summary of NVIDIA developer forum threads on GB10 power (forums.developer.nvidia.com ... "dgx-spark-power-clarification", "dear-nvidia-nvidia-smi-is-broken-on-the-dgx-spark"; parca-agent PR 3247) | NO (search snippets only, not opened) |
| S11 | https://developer.nvidia.com/blog/train-an-llm-on-an-nvidia-blackwell-desktop-with-unsloth-and-scale-it/ | NO (search snippet only) |

## 1. Unsloth

**Licence (S1, opened).** README: "Apache-2.0, AGPL-3.0 licenses found"; "Unsloth uses a dual-licensing model of Apache 2.0 and AGPL-3.0. The core Unsloth package remains licensed under Apache 2.0, while certain optional components, such as the Unsloth Studio UI are licensed under ... AGPL-3.0." Repo has `studio/` and `unsloth/` directories. I did not open the per-directory LICENSE/COPYING files, so the exact file-level split is UNVERIFIED. No "Unsloth Pro" licence text was seen on the page. For us: use the core library (`pip install unsloth`, Apache-2.0); do not embed Studio/Desktop code in a distributed product without a licence check.

**What it does (S1).** Fine-tuning and RL: LoRA, QLoRA, full fine-tuning, pretraining, GRPO, GSPO, DPO, FP8; export to GGUF, NVFP4, FP8. Also a desktop app / Studio web UI (the repo now leads with these). Claims: "2x faster with 70% less VRAM with no accuracy loss"; per-notebook table gives 1.5x/60%, 2x/70%, gpt-oss GRPO 2x/80%. How measured: the README does not state method or baseline in the text I read. Treat as vendor claims, unverified; NVIDIA's playbook repeats "2x" as "claims" (S3).

**Model families (S1, S3).** README names Qwen3.8, Qwen3.5, GLM-5.3-Flash, Kimi K3, DeepSeek-V4, MiniMax-H3, Gemma 4, gpt-oss, FLUX/Qwen-Image diffusion, TTS/embedding. NVIDIA's playbook names LLaMA, Mistral, Qwen, DeepSeek. Phi not seen on the pages read; likely supported but UNVERIFIED.

**DGX Spark / GB10 / Blackwell / ARM64.**
- Official Unsloth guide exists (S2): Docker or venv; says all Unsloth notebooks work on Spark; gpt-oss-120b QLoRA 4-bit about 68 GB unified memory; gpt-oss-20b RL (2048 game) 1,000 steps in about 4 hours. Page footer says "Last updated 11 months ago", so the pinned versions below are old.
- Spark Dockerfile in S2: base `nvcr.io/nvidia/pytorch:25.09-py3`, CUDA 13.0 env, builds triton from a pinned commit and xformers from source with `TORCH_CUDA_ARCH_LIST="12.1"`, then `pip install unsloth unsloth_zoo bitsandbytes==0.48.0 transformers==4.56.2 trl==0.22.2`. Run flags: `--gpus=all --net=host --ipc=host --ulimit memlock=-1 --ulimit stack=67108864`.
- NVIDIA playbook (S3): base `nvcr.io/nvidia/pytorch:25.11-py3`; inside it `pip install transformers peft hf_transfer "datasets==4.3.0" "trl==0.26.1"` then `pip install --no-deps unsloth unsloth_zoo bitsandbytes` (no-deps so the container's torch/CUDA are not overwritten). Prereq `nvcc --version` = 13.0. Listed risks: Triton mismatches, CUDA toolkit config, OOM needing smaller batch. Rollback: pip uninstall. Our host matches (CUDA 13.0, Blackwell).
- Generic Blackwell page (S4): "compatible with every NVIDIA GPU from 2018+ including the DGX Spark"; pip or uv install; xformers may need building from source (uses arch 12.0 there; Spark guide uses 12.1). It also says DGX Spark users should follow the DGX guide, not the generic image (S5).
- Unsloth Desktop has a Linux ARM64 .deb (S1). Studio on GB10 in a container works per one community gist (S9, unofficial; its title says transformers patches are needed for aarch64 GB10 inference, details not read).
- NOT verified: that PyPI `torch` aarch64 wheels with cu130 install cleanly under uv on this host (no torch is installed here). This is the main reason to prefer the NVIDIA PyTorch container over a bare uv venv.

## 2. Models (<= 32B). IDs below were seen in HF API listings or the Qwen org page (S8). Licence = HF tag; read the model card before relying on it.

**Qwen (org https://huggingface.co/Qwen).** Qwen3.5 exists: `Qwen/Qwen3.5-0.8B`, `Qwen/Qwen3.5-2B`, `Qwen/Qwen3.5-4B`, `Qwen/Qwen3.5-9B`, `Qwen/Qwen3.5-27B`, `Qwen/Qwen3.5-35B-A3B` (35B total, so just over the 32B line; 3B active), plus `-Base`, `-FP8`, `-GPTQ-Int4` variants for some; larger `Qwen3.5-122B-A10B`, `Qwen3.5-397B-A17B`. Also `Qwen/Qwen3.6-27B`, `Qwen/Qwen3.6-35B-A3B`, and (org page) `Qwen/Qwen3.8-27B`. Coder: `Qwen/Qwen3-Coder-30B-A3B-Instruct`, `Qwen/Qwen3-Coder-Next` (size not checked). Small: `Qwen/Qwen3-4B`, `Qwen/Qwen3-4B-Instruct-2507`. Guard/classifier: `Qwen/Qwen3Guard-Gen-0.6B|4B|8B`. All tagged apache-2.0 (no attribution/commercial limit in the tag; Apache-2.0 still requires licence notice retention). Qwen3.5 base models exist for fine-tuning.

**Google Gemma 4 (org https://huggingface.co/google):** `google/gemma-4-E2B-it`, `gemma-4-E4B-it`, `gemma-4-12B-it`, `gemma-4-26B-A4B-it`, `gemma-4-31B-it` (apache-2.0 tag). Note Gemma 3 (`google/gemma-3-4b-it`) carries tag `gemma`, i.e. the custom Gemma terms with use restrictions; Gemma 4 appears to have moved to Apache-2.0 (tag only, card not read).

**OpenAI gpt-oss (org https://huggingface.co/openai):** `openai/gpt-oss-20b`, `openai/gpt-oss-120b`, `openai/gpt-oss-safeguard-20b` (apache-2.0; safeguard variant is a policy-classifier model, relevant to the permission classifier).

**Mistral (org https://huggingface.co/mistralai):** `Ministral-3-3B-Instruct-2512`-family (3B/8B/14B, Instruct/Reasoning/Base, apache-2.0; exact non-GGUF 3B ID: `mistralai/Ministral-3-3B-Instruct-2512-BF16`), `mistralai/Devstral-Small-2-24B-Instruct-2512` (apache-2.0, coder). `Devstral-2-123B` is tagged "other" and is too big anyway. Old `Ministral-8B-Instruct-2410` is "other" (research licence): avoid.

**Others:** `microsoft/phi-4` (14B, MIT), `microsoft/Phi-4-mini-instruct` (MIT); `ibm-granite/granite-4.2-3b`, `granite-4.2-8b`, `granite-4.2-30b` (apache-2.0); `HuggingFaceTB/SmolLM3-3B` (apache-2.0); `meta-llama/Llama-3.2-3B-Instruct`, `Llama-3.1-8B-Instruct` (Llama community licences: attribution/naming and large-MAU terms, not read, UNVERIFIED details). NVIDIA Nemotron 3.5 models (e.g. `nvidia/NVIDIA-Nemotron-3.5-Bolt-E4B-4GB`, `...Lightning-30B-A3B-BF16`) are tagged "other" (NVIDIA licence, not read): check terms.

**Recommendations (judgement, not benchmarked by me; no benchmark pages opened):**
- (a) Tool-using subject agent: `Qwen/Qwen3.5-9B` or `Qwen/Qwen3.6-27B`/`Qwen3.5-27B` for headroom; MoE `Qwen3.6-35B-A3B` decodes fastest on bandwidth-limited Spark (NVIDIA's vLLM and llama.cpp playbooks both use it as the featured example, S7). Alternatives: `gpt-oss-20b`, `gemma-4-26B-A4B-it`. For many cheap "little agents": 2-4B (`Qwen3.5-2B/4B`, `gemma-4-E4B-it`, `Ministral-3-3B`) are plausible for narrow, scripted tool use with constrained output; expect weak long-horizon planning. Verify with our own eval, not model-card claims.
- (b) Log-to-memory consolidator: summarisation/extraction, long input: `Qwen3.5-9B` or `granite-4.2-8b`; fine-tune target via Unsloth (base `Qwen3.5-4B-Base` / `9B-Base` exist).
- (c) Permission/need classifier: small fine-tuned 0.8-4B (`Qwen3.5-0.8B/2B/4B`) with constrained decoding is the cheapest fit; `Qwen3Guard-Gen-*` and `gpt-oss-safeguard-20b` are ready-made safety classifiers but are trained for content-safety policy, not our permission semantics: use as baselines only.

**How to verify IDs:** open https://huggingface.co/Qwen, /google, /openai, /mistralai, /microsoft, /ibm-granite, /HuggingFaceTB, /meta-llama (gated, needs acceptance), /nvidia; or run `curl 'https://huggingface.co/api/models?author=Qwen&search=Qwen3.5&expand[]=tags'`. Read the model card's licence block (the tag can be generic "other"). Unsloth also publishes its own quantised mirrors under `unsloth/` (not enumerated here).

## 3. Inference serving on GB10

Spec (S6, opened): GB10 Grace Blackwell, 20-core Arm (10 Cortex-X925 + 10 Cortex-A725), up to 1 PFLOP FP4 (footnote: theoretical, with sparsity), 128 GB LPDDR5x coherent unified memory, 256-bit interface, **273 GB/s** bandwidth, GB10 TDP 140 W, PSU 240 W, ConnectX-7 200 Gbps.

Decode is bandwidth-bound: upper bound tokens/s ~ 273 GB/s / bytes of weights read per token (my arithmetic, not a measurement; real is lower). Examples: 9B dense at 4-bit (~4.5 GB) ceiling ~60 tok/s; 27B dense at 8-bit (~27 GB) ~10 tok/s; 35B-A3B MoE at 4-bit (~1.5-2 GB active) ceiling well above 100 tok/s. Dense 27-32B at BF16 (~54-64 GB) is ~4-5 tok/s: poor. Prefill and training are compute-bound and fare better. Batching (vLLM) amortises weight reads across concurrent agents, which suits many parallel little agents.

All NVIDIA playbook pages below were opened (S7); statuses are from those pages only:
- **vLLM**: NVIDIA container `nvcr.io/nvidia/vllm:26.05-py3` (tag seen; `LATEST_VLLM_VERSION=26.05.post1-py3`); page states prereqs "ARM64 processor and Blackwell", CUDA 13.0, Python 3.12; also a source-build path for ARM64; `vllm/vllm-openai:gemma4-cu130` for Gemma-4-based models. Page lists an agent-ready recipe `nvidia/Qwen3.6-35B-A3B-NVFP4`. Updated 06/12/2026.
- **llama.cpp**: build from source with CUDA for GB10; serves GGUF via OpenAI-compatible `llama-server`; example Qwen3.6-35B-A3B with MTP; updated 06/03/2026. Lowest-friction single-user option, no Python stack.
- **SGLang**: container `lmsysorg/sglang:latest-cu130`; updated 04/28/2026.
- **Ollama**: NVIDIA playbook exists but last updated 10/12/2025 (stale); fine for convenience, slower to track new models.
- **NVIDIA NIM**: playbook uses `nvcr.io/nim/meta/llama-3.1-8b-instruct-dgx-spark`; a Qwen3-32B Spark NIM is mentioned. Needs NGC login/API key; NIM licence terms not read (UNVERIFIED for commercial use).

## 4. Energy / power measurement during training

Not opened (S10 snippets only), so treat as leads:
- `nvidia-smi --query-gpu=power.draw,utilization.gpu,clocks.gr --format=csv -l 1` reportedly works on GB10 for GPU power; memory fields and power limit show "Not Supported" (unified memory). NVML sample-buffer APIs reportedly empty on GB10; `nvmlDeviceGetPowerUsage` instantaneous works.
- NVIDIA staff on forums reportedly say the displayed wattage is GPU only, not whole system; whole-system needs a wall meter or smart plug. Spec page (S6) gives only TDP 140 W (SoC) / 240 W PSU, no measured idle/peak.
- Forum threads report anomalous low readings (~5-14 W under load) on some units: cross-check one run against a wall meter.
- Method: sample at 1 Hz to CSV alongside the training log; energy = sum(W x dt); report J per step and per token; record clocks and temps (`/sys/class/thermal/thermal_zone*/temp`). Separate GPU-only from wall figures.

## 5. Minimal, reversible install route (commands NOT executed)

Recommend the NVIDIA PyTorch container, not a uv venv, because no torch is installed and aarch64+cu130 wheels are unverified. Everything lives in docker; rollback = remove container/image and the cache dir.

```bash
# one-time: pull base (estimate ~20-25 GB image; NOT measured)
docker pull nvcr.io/nvidia/pytorch:25.11-py3
mkdir -p ~/SeaBridgeAI/murmuration/.cache/hf ~/SeaBridgeAI/murmuration/runs
docker run --gpus all --ipc=host --ulimit memlock=-1 --ulimit stack=67108864 -it --rm \
  -v ~/SeaBridgeAI/murmuration:/work -v ~/SeaBridgeAI/murmuration/.cache/hf:/root/.cache/huggingface \
  -w /work nvcr.io/nvidia/pytorch:25.11-py3 bash
# inside (per NVIDIA playbook S3):
pip install transformers peft hf_transfer "datasets==4.3.0" "trl==0.26.1"
pip install --no-deps unsloth unsloth_zoo bitsandbytes
python /work/test_unsloth.py   # fetched from the playbook repo; tiny smoke test
```
Estimated downloads (my estimates, parameter count x bytes): Qwen3.5-0.8B BF16 ~1.6 GB, 4B ~8 GB, 9B ~18 GB, 27B ~54 GB; add HF cache for datasets. Expect first run to need the NVIDIA-playbook versions (the 25.11 container plus pinned trl/datasets) because newer Unsloth may require newer transformers; re-check with `pip check`. Alternative if the playbook fails: Unsloth's own Spark Dockerfile (S2; builds triton/xformers from source, longer, older pins). A uv venv in the repo is possible only after `uv pip install torch --index-url <aarch64 cu130 index>` is confirmed; I did not confirm that index exists.

For serving, run llama.cpp or the vLLM container separately (docker), bound to 127.0.0.1; one at a time, because training and serving share the same ~73 GB free unified memory.

## 6. Risks and unverified

- Unified memory is shared with the OS and other jobs; ~73 GB free caps full fine-tuning (use LoRA/QLoRA; 27B+ QLoRA is tight beside a serving process).
- Unsloth Spark guide pins are about 11 months old; NVIDIA playbook (Dec 2025) is newer; real version compatibility unverified on this host.
- "2x faster / 70% less VRAM" are vendor claims with no method read; benchmark ourselves with fixed seed/steps.
- Licence file-level split (Apache vs AGPL) not read; HF licence tags are metadata only; Llama/Gemma-3/NVIDIA "other" terms unread.
- Model quality for tool use, consolidation and classification not benchmarked by me; no leaderboard pages opened. Qwen3.5-0.8B existence confirmed by HF API listing only (card not opened).
- Spark decode figures are my arithmetic from the 273 GB/s spec; no measured tok/s source was opened.
- Power section rests on unopened forum snippets.
- Not checked: Phi support in Unsloth, PyPI aarch64 torch wheels, SGLang/vLLM behaviour with Qwen3.5 small models, NIM licence.
