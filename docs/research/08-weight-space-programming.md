# 08 - Weight-Space Programming (WSP): what is real, what is prior art, whether to replicate

Date of research: 2026-11-19. Public web only. No paywall bypass.
Reading method: "urllib" = python urllib via ctx_execute, full text read. "search" = WebSearch result summary only, page NOT opened (treat as lead, not evidence).

## 1. Sources and OPENED status

| Source | OPENED | How |
|---|---|---|
| rikiyat.github.io/blog/weight-space-programming/ (primary) | yes, full | urllib, HTML stripped, read in full |
| github.com/RikiyaT/lm_understand-logs (README, LICENSE, exp8 README) | yes | urllib raw files |
| arXiv 2611.20953 (Kundu, Claude replication) | abstract only | urllib |
| arXiv 2611.21449 (Goworek et al., replicate+extend) | abstract only | urllib |
| brainwagon.org skeptical post (2026-11-08) | yes, full | urllib |
| akmaier.substack.com (Maier) | teaser only (paywalled; not bypassed) | urllib |
| dev.to/shaam_ai post | first part | urllib |
| github.com/andsalazar/model-training | landing page only | urllib |
| Honnibal rebuttal, HN thread, The Register, HF model card, X post, Simon Willison, Toledo eval, DSC Medium piece, Moonshots ep 308 | NO | search summaries only |
| arXiv 2512.24601 (RLM), 2511.16665 (TLT) | abstract yes | urllib |
| ROME 2202.05262, MEMIT 2210.07229, Task Vectors 2212.04089, RepE 2310.01405, ActAdd 2308.10248, Abliteration 2406.11717, Tracr 2301.05062 | abstract yes | urllib |

## 2. Owner's pasted summary, claim by claim

| Claim | Verdict | Evidence |
|---|---|---|
| Authors Takehi, Teoh, Zhang, Khattab (MIT CSAIL) | CONFIRMED | byline lists all four, all "MIT CSAIL" |
| Release Nov 2, 2026 | CONFIRMED | "Published November 2, 2026" |
| GPT-6 Astra read/edited raw weights of Qwen3.5-0.8B, no backprop | PARTLY. Edit is real; "raw weights" is misleading | Qwen run used "a Python kernel over the weights" plus 10/25/50 forward-pass tool; "Again, no training or gradient information is allowed." Raw-weights-as-text, no-tools only applied to the tiny networks (Exp 1,2,4,5) |
| 0.016% of weights, 64 columns across two layers | CONFIRMED (wording: 64 per layer) | "subtracted that direction from 64 output columns in each (131,072 weights)" of MLPs in layers 15 and 19; "0.016%" |
| MATH-500 7.9% -> 48.1% | CONFIRMED | table: Base 7.9, Edited 50 passes 48.1 |
| "up to 6x" math | CONFIRMED arithmetically (48.1/7.9 = 6.1); it is the authors' own tweet wording per search | page: GSM8K 13.8->67.1 |
| "tripled" instruction following | CONFIRMED | "raising IFEval by 3x" (21.0 -> 62.3) |
| Diagnosed repetitive reasoning loops | CONFIRMED | "Astra identifies an issue ... causing reasoning loops that Qwen's own model card warns about"; 85/96 practice answers hit the 32,768 limit |
| Code and logs public | CONFIRMED (logs + harness scripts; not a method library) | github.com/RikiyaT/lm_understand-logs; edited model on Hugging Face (link on page, not opened) |
| Featured on Moonshots ep. 308 | UNVERIFIED | search only: ep. 308 dated Nov 4 titled "...AIs Editing AI Brains"; no transcript opened; not on the blog page |

Missing from the owner's summary: the page itself says the 10- and 25-pass edits barely worked (12.3% and 14.1% MATH-500), the Gemma 3 270M follow-up failed (6.8 -> 7.7 at best), and the sycophancy-from-weights test failed.

## 3. Method (from the page and exp8 README)

- Editor: `gpt-6-astra` via Codex CLI (`codex exec`), reasoning effort `max` for Exp 8; Codex's own tools switched off, every action through a custom harness.
- Serialisation: tiny nets (17k to 172k weights) pasted as text. Larger (Go 1.48M, Qwen 0.8B): persistent CPU Python kernel; `load tensor`, compute with numpy/torch, `save_edit(name, tensor)`; max 300 code runs; no running the model inside the kernel.
- Forward-pass tool: budget 10/25/50. One pass = generate answers to up to 512 practice problems (paired original vs edited allowed) or a teacher-forced read of up to 1,024 texts (log-probs, hidden states, MLP activations, attention).
- Data given: 7,469 GSM8K-train and 7,275 MATH-train problems plus 714 AIME answers; never the benchmarks.
- Forbidden: backward passes, optimizers, fitting weights to a loss; edits to final norm, embeddings/output layer, or whole-tensor scaling were refused by `save_edit`.
- What was edited (50-pass run): "subtracts the loop direction from the 64 output columns per layer of the MLPs of layers 15 and 19 that write it most." (dev.to describes it as rank-1 on `down_proj`; second hand.)
- Validation inside the run: paired generations on practice problems. Final evaluation outside, never shown to Astra: vLLM, bf16, thinking on, T 0.6, top-p 0.95, top-k 20, presence penalty 1.5, max 32,768 tokens, math-verify grading.
- Written-from-scratch tasks: MinAtar (3 games, 600-32-32-6 tanh, one reply, no rollouts), 9x9 Go (243->512x6->82, 1,480,274 weights, 0/10/25/50 forward passes).
- Process stats for p50c: 158 turns, 80 Python runs, 4 conversations, 20.3 h wall-clock (incl. 4.7 h outage). 10-pass: 74 turns, 11.6 h. 25-pass: 86 turns, 8.5 h.

## 4. Models, benchmarks, baselines, trials

- Models: PPO MLPs (500-32-32-5; 679-128...-16), DDPM MLP (23,824 w), char-LM 7.16M, Gemma 3 270M (it), Qwen3.5-0.8B.
- Benchmarks (Qwen): MATH-500, GSM8K, AMC23, Minerva, OlympiadBench, GPQA Diamond, MMLU-Pro (1,000 fixed), IFEval. 50-pass table in README: AMC23 0.5->23.4, Minerva 1.5->25.4, OlympiadBench 1.3->21.8, MMLU-Pro 40.3->45.5, GPQA 22.7 (note) ->36.6.
- Baselines: PPO at 100M/500M steps for games (the authors defend these as "price in experience"). **No** fine-tuning, LoRA, steering, or decoding baseline for Qwen in the post. The page says nothing comparing to them.
- Trials: **n = 1 editing run per budget** (three runs p10c/p25c/p50c). Eval averages 4 samples/problem on MATH-500, 2 on GSM8K/IFEval, 1 on MMLU-Pro. The three runs used *different* edits (30 matrices layers 8-22; one attention head zeroed; two MLPs), so the "10/25/50" rows are three different one-shot discoveries, not a smooth budget curve (my inference from the README table).
- Exp 3: two attempts per model. Exp 7: four weights-only attempts failed; three pairs succeeded only after adding an attention tool.

## 5. Failure modes, limits, safety, cost, licence

- Authors' own limits: "capabilities are exciting but still limited, specifically due to inefficiencies in context length and harnesses"; Gemma: "Editing weights could remove an obstacle that hid an ability, but it could not add an ability the model lacked"; Exp 7 failed on weights alone; "WSP is not a method"; no comparison with interpretability researchers.
- Safety: **no dedicated safety section** on the page. It lists "auditing without evaluation (e.g. backdoors)" as an opportunity and "recursive self-improvement" as a direction. The DSC Medium title mentions risks (Microsoft "Lazarus") but I did not open it.
- Compute and cost: **not stated** (no dollar figure, no token count seen). Only wall-clock and turn counts above. GPT-6 Astra at `max` effort is a paid frontier API; evaluation used vLLM (GPU, hardware not stated in what I read).
- Licence: logs/data/networks CC BY 4.0; authors' scripts (`*.py`, `*.sh`) MIT; MinAtar source quoted in prompts GPL-3.0; third-party benchmark text under its own licence. Repo: github.com/RikiyaT/lm_understand-logs (1 commit, ~1.3k stars at fetch).

## 6. Independent critiques and replications, with reliability

1. **Kundu, arXiv 2611.20953** (single author, preprint, not peer reviewed; used Claude Opus 5.5, 10 "pre-registered" experiments, controls, hand-audited cells). Qwen MATH-500 6.7 -> 51.4/55.2/58.1 at 10/25/50 passes; mechanism differed (final norm scale + "Wait" logit), norm alone only 20.9-22.1%; sycophancy identified 6/6 from weights (contradicts original); Gemma no gain. Reliability: medium; transparent, but self-reported and one model family. Supports: the loop fix is reachable by other frontier models and by different routes.
2. **Goworek et al., arXiv 2611.21449** (4 authors, 3-day sprint, abstract only read). Breakout networks 514/550/307 vs 517 reproduce; the networks are "compiled programs" (decompiled to Python matching actions); digit classifier 50% vs 82% simple baseline; reading = mostly input layer; poisoned-model detection 10/10, 7/10, 23/32 but never the trigger. Reliability: medium-high on direction, abstract only.
3. **Brainwagon (2026-11-08)**, co-written with Claude Code, secondary synthesis. Reports (second hand) independent re-run of edited model 51.0% on full MATH-500; community steering-vector version 8 -> 36 correct on 96 problems vs 10 for a random direction; HN comment claiming thinking-off base gets 52% (unverified, flagged by the author). Reliability: good as a map, not primary.
4. **Honnibal rebuttal** (via search summary only): reading-from-raw-weights was only on 17k-172k-weight nets; every real-LM result used Python plus forward passes. Consistent with the authors' own page.
5. **andsalazar repo**: README text via search, "mostly negative results"; found cheaper open-weight models mostly could not do the reading. 0 stars, unreviewed. Low-medium.
6. **Maier substack**: paywalled; teaser only. Claim (via search): Astra designs a program then compiles it to weights; not evidence it understands trained weights. Not verified by me.
7. dev.to shaam_ai: aggregator; verdict "editing holds, reading fails". Low.
8. Search summaries also quote a Toledo non-thinking baseline (43.95%) and a "repetition penalty recovers 54%" draft. NOT opened; do not cite as fact.

Net: the released Qwen edit reproduces (about 51% on MATH-500 per two independent reports I could only read second hand/abstract). The gain is predominantly loop repair, not new maths ability (authors' Gemma result and critics agree). The "6x" is relative to a thinking-mode baseline that 93% truncates.

## 7. Related items the owner mentioned

- **Recursive Language Models** (arXiv 2512.24601, Zhang, Kraska, Khattab; v1 31 Dec 2025, v2 28 Jan 2026, v3 11 May 2026; opened). It is an **inference-time** paradigm: the long prompt lives in an external environment (Python REPL), and the LLM programmatically examines, decomposes and recursively calls itself over snippets; handles inputs "two orders of magnitude beyond model context windows"; plus a small post-trained RLM-Qwen3-8B (+28.3% over base). It is **not** teacher/student/judge self-training; the owner's description is wrong. Code: github.com/alexzhang13/rlm (search only). Link to WSP: same group (Zhang, Khattab); same "LLM acts through a REPL" harness idea, applied to weights.
- **Taming the Long-Tail (TLT)** (arXiv 2511.16665, Hu et al., ASPLOS '26; opened abstract). Systems paper: speculative decoding with an adaptive draft model trained on idle GPUs during long-tail rollouts of reasoning RL, >1.7x end-to-end RL training speedup, lossless. Posted Nov 2025, not Feb 2026; unrelated to weight editing.

## 8. New vs prior art

- ROME 2202.05262 / MEMIT 2210.07229: rank-one and batched weight edits of mid-layer MLPs, designed by humans via causal tracing. WSP-Qwen is the same family of edit, found by an LLM agent.
- Task vectors 2212.04089: weight-space arithmetic from fine-tuned deltas (needs training).
- RepE 2310.01405 / ActAdd 2308.10248: activation steering, inference-time, no training. A "subtract the loop direction" edit is the weight-baked version of this.
- Abliteration 2406.11717: erasing one direction from weights removes refusal; closest precedent for the Qwen edit.
- Tracr 2301.05062: compile programs into transformer weights; precedent for "write networks from scratch".
- Genuinely new (supported by evidence): a general frontier LLM, off the shelf, autonomously runs the probe-find-direction-edit-measure loop in a sandbox. Not new: the edit type, the compile-a-program idea, the reading of small nets' input layers.

## 9. (1) Minimal local replication on the Spark

Question to test: can a model that is not Astra find and apply a loop-fixing weight edit on Qwen3.5-0.8B, and does it beat trivial baselines?

- Model: Qwen3.5-0.8B (public, fits trivially). Eval: MATH-500 and IFEval subset via vLLM on the Spark, bf16, same sampling as exp8, 32k token cap, fixed seeds, `math-verify` grader taken from the released repo (`code/mathqa.py`, `code/evaluate.py`).
- Arm A (control, cheapest, do first): load the released edited checkpoint, rerun eval. Expect near 48-51% per reports. Arm B: base with thinking off. Arm C: base with repetition penalty / loop-break decoding. Arm D: difference-of-means loop direction ablation on layers 15/19 (a script, no LLM). Arm E: local agent (Claude via harness or a local open model) given the exp8 harness and 50 passes, 3 seeds. Arm F: untouched base with random direction ablation of same size.
- Tooling: the authors' harness scripts (MIT) plus a `save_edit` guard; edits written to a copy, base weights kept read-only and hashed.
- Cost/time ESTIMATE (not measured): A-D a few Spark-hours of vLLM generation plus under a day of setup; Arm E is the expensive one: authors' 50-pass runs took 8-20 h wall-clock each with generation passes up to ~30 min, plus paid frontier-model tokens I cannot price.
- Safety/rollback: edit only a copy; never touch a served production weight; checksum before and after; no tenant data; log everything.
- Deterministic eval: fixed seeds, fixed practice-problem subsets, N samples per problem as in the post, report CIs.
- Decision under first principles / simple / cheap: **do Arms A-D only (cheap, deterministic, a day); skip Arm E unless A-D show the edit adds value beyond decoding fixes.** Reason: the edit is a loop fix; if repetition penalty or thinking-off matches it, the weight-surgery story adds nothing for us. A full agent replay is a research project with no direct payoff for a hub-and-cells architecture. This is a recommendation, not a measured result.

## 10. (2) Frontier "weight surgeon" in a hub-and-cells architecture

Fit: the hub (strong model) inspects a small cell model's failure logs, finds a low-dimensional cause (loops, a refusal-like direction, a format habit), and ships a small patch: direction ablation or a LoRA merge into the cell. Fits because the edit is tiny, auditable (a diff of 131k numbers), reversible (keep base hash), and needs only a CPU kernel plus a forward-pass budget.

Where it does not fit: adding knowledge or skills. The authors' own Gemma result says edits remove obstacles, not add abilities. For that, distillation or LoRA fine-tuning (conventional) stays.

Falsified if any of: (a) repetition penalty, thinking-off or a steering vector matches the edit at equal or lower cost; (b) three seeds of the hub-agent produce edits that vary wildly (the p10/p25/p50 runs already did) or fail on a second small model that also loops; (c) edits degrade off-target tasks (MMLU-Pro, GPQA) by more than noise; (d) cost of hub tokens per patch exceeds a one-off LoRA fine-tune cost; (e) the edit fails to transfer to a quantised or different-sampling deployment.

## 11. (3) Uncertainties

- Cost, API effort/tokens, and GPU hardware of the original: not found.
- Whether Astra, as opposed to any capable agent, was essential: Kundu says Claude reproduced the gain by a different mechanism; I read only the abstract.
- Qwen's "93% hit token limit" baseline and the T=0.6 vs recommended T=1.0 mismatch are second-hand (brainwagon); I did not read the Qwen model card.
- Independent 51.0% figure, 52% thinking-off, 43.95% Toledo, repetition-penalty 54% are second-hand or unopened; treat as leads.
- Moonshots ep. 308 content, the Honnibal post, the HF card, the Register article and the Maier article body not opened.
- All of this is days old, non-peer-reviewed blog/preprint material; one editing run per budget, one editor model in the original.

## 12. Update 2026-11-24: self-rewriting paper, the post's addendum, and a local test

Added at the owner's request ("add this to research and testing", 2026-11-24).

### 12.1 "Language Models Can Rewrite Their Own Weights"

**Source:** Fan, He, Yang, Mao, Zhu, Cheng, Liang, Shen, Li, Guo and Liu (UIUC), arXiv 2611.21885. v1 is dated 16 Nov 2026 and v2 18 Nov 2026. A research subagent read the full text of v2 (HTML). The owner's summary came from a YouTube video, which was not opened. The paper cites the MIT post as its closest work and takes up the post's "self-editing" future work. The two author lists do not overlap.

| Claim in the video | Primary text |
|---|---|
| Qwen3.5 27B edits its own weights in a sandbox with no gradients, optimizer or internet | CONFIRMED. Loaders, subprocesses and network are also refused. Each session gets 20 forward passes and 200 code runs. |
| 3,000 practice math problems | CONFIRMED (DeepScaleR, with benchmark overlap removed) |
| Compares hidden states of finished and truncated answers | CONFIRMED |
| Layer-8 rank-one update gives +6.6 points | DIFFERENT, conflated. The layer-8 rank-one edit (first protocol) gave 57.2% to 58.3%, **+1.1 points, p = 0.038**, on 490 held-out problems with 8 seeds each. The +6.6 points (57.2% to about 63.8%) is **one session out of 8** in a second protocol. That edit raised the time-step bias of all 48 linear-attention layers by 0.5, so it is not rank-one. Another session gave +4.0 with a layer-63 projection. 5 of the 8 sessions withdrew. |
| Self-repair: values about 1,400x normal, clipped | CONFIRMED. The largest value is 1,397x the median, against at most 162x elsewhere. The rule clips weights above 15x the median in 20 matrices. |
| Six image benchmarks recover from 7% to 70% using only text probes | CONFIRMED: 7.3% to 70.2%, against a base of 84.3%, on 100 items per benchmark, one answer each. On held-out text problems the repair recovered only 0.0% to 33.0%, against a base of 58.5%. |
| Works at 27B, not 9B | CONFIRMED: the 2B model makes no edit, and the 4B and 9B models damage themselves. This rests on one session per smaller size. |
| No code released | No repo or release statement found. arXiv licence only. |

**Baselines:** none of the three that note 08 uses to judge the MIT result, namely a steering vector, a decoding fix (thinking off, repetition penalty) or a random-direction control. The only controls are the base model, the damaged copy and ablations of the repair parts.

**Read for TREMOR:**
- The headline gain is a best-of-8 session. The pre-specified rank-one edit is marginal.
- The repair result is real but easy for a model to find. A matrix with a 1,397x outlier is a large, obvious target, so it says little about diagnosing subtle faults.
- It falls under the same kill rule as H7: a decoding or steering rival at matched cost must be beaten first.
- No independent critique found. A literature issue (openinterpretability #4798) restates the abstract.

**Local test:** not possible without GPU admission. A 27B model in bf16 also exceeds the T7 envelope. It stays documentary.

### 12.2 The post's 12 Nov addendum

The post added "Response to Comments" on 12 Nov:
- WSP is "a concept, not a method".
- Gradients are allowed when the programmer decides the edit.
- The baselines test narrow claims rather than ranking methods.
- No comparison with interpretability researchers is claimed.

The local log clone, `data/lm_understand-logs` at `4d09ba6` (2026-10-29), predates the addendum. Refetching it is a network action and is not needed for Exp 1, so it was not done.

### 12.3 Local test: WSP-R1

**WSP-R1** is a blind cross-model replication of the post's Exp 1, where a model names the game from the raw weights of a 17,253-parameter PPO policy with no tools.
- **Design:** the released prompts are read by Claude Opus 5.5, against within-tensor shuffled controls.
- **Preregistration:** `prereg/WSP-R1-exp1-blind-read.md`, with script `lab/wsp_exp1_blind.py`, both frozen at `5367f53` before any call.
- **Cost:** no GPU, no install and no fetch. 8 subagent calls under the rule 8 default ceiling.
- **Result:** recorded below when graded.
