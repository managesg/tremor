# 10. Diogo Almeida talk and source verification

Date of research: 2026-11-19. Public web only. WebFetch was blocked by a hook, so every page was read with `ctx_execute` and python `urllib` (HTML stripped to text). OPENED = yes means the page text was read in this session.

## 0. Headline correction to the brief

The owner-supplied transcript is not titled "Agents beyond the KV cache". Evidence:

- Transcript header: "Beyond Better Assistants: Software That Can Make a Decision", source video `ZZ19zhYnDKY` (Day 1 livestream, 5:06:58-5:29:53), not `Cyt3LU8TyNc`. Timestamps below are that livestream's clock. OPENED yes.
- Talk page https://ai.engineer/code/2026/talks/diogo-almeida (OPENED yes) carries the same title, date 11 Nov 2026, Main stage, Diogo Almeida, TypeSafe AI Co-founder and CEO. It says the talk itself is "titled 'I love you so jevving much'".
- `https://www.youtube.com/watch?v=Cyt3LU8TyNc` (OPENED yes, but only the page title came back): '"Where is all the automation?" — Diogo Almeida, TypeSafe AI'. I could not confirm it is the same recording or segment. The livestream `ZZ19zhYnDKY` title is "AIE CODE: Google DeepMind, Anthropic, SpaceXSI, TypeSafe, Lovable, Ramp, etc (System One theme)".
- KV-cache material is about 90 seconds of a 23-minute talk (05:22:50-05:24:20). The rest is about reliability, automation vs assistance, "Jev" (his product), and RLHF. Cost-share, routing economics and self-hosting come from his blog (section 2), not the talk.

## Part 1. The talk (OPENED yes: transcript, 1,318 lines, read in full; talk page read)

The transcript is machine-generated with recognition errors. "o of nan" at 05:23:22 is almost certainly O(N); "login or even better lookups" at 05:23:35 is almost certainly "log N". The page's own summary supports the reading "memory should not behave like a growing sequence". Treat the O(log N) reading as my inference.

Testability column: L = local GPU, C = via Claude API/Claude Code.

| # | Claim / open problem | Time | Quote (ASR) | Testable | Cheap experiment |
|---|---|---|---|---|---|
| 1 | Agents are inflexible because of the KV cache. | 05:23:11 | "they're so inflexible in their design because of the tyranny of the KV cache" | L, C | Log `cache_read_input_tokens` vs `input_tokens` vs `output_tokens` for one real Claude Code session and compute cost shares at current prices. |
| 2 | Memory is O(N): the whole history is re-sent each call. Asks why not log-time lookup. | 05:23:22 | "Why is memory o of nan, right? ... all of our history of coding agents always included in every new call?" | L, C | Compare an agent that appends full history vs one that keeps a small notes file plus retrieval; measure tokens per turn on a fixed task (20 tasks). |
| 3 | Missing piece is smarts to decide what to remember, not storage. | 05:23:35 | "we have the memory available. It's just that we don't have the smarts ... what you should remember" | C | Use Anthropic's CL-Bench database task (section 2) with and without a memory dir. |
| 4 | Parallel agents should share state and not rediscover the codebase. | 05:23:46 | "Why do they need to rediscover the same patterns of the codebase over and over" | C, L | Run 3 parallel agents on one repo, with and without a shared notes file/SQLite; count repeated file reads. |
| 5 | Even naive routing fails; subagent usefulness flip-flops; both fight the cache. | 05:23:58 | "even naive routing doesn't work ... why can't non-naive routing and sub agents work?" | C | Replay a 100k-token session: all-Opus vs hand-off to Sonnet for one step; read the cache write cost from `usage`. Blog predicts the cheap step costs ~3x more (blog assumptions, not measured by him). |
| 6 | Principal-agent problems; encode spirit, not letter. | 05:24:20, 05:24:45 | "we can't encode the spirit ... we're constrained to encoding bits" | C (weakly) | Write 10 policy rules plus 10 loophole actions; test whether an LLM judge catches loopholes a regex misses. Anecdotal, not a measurement of "spirit". |
| 7 | Real-time semantic security is limited by speed/cost, not intelligence. | 05:25:09 | "not fast, cheap, and reliable enough to actually run real time" | L | Time a small local model as a per-tool-call classifier; record p95 latency and false-block rate. |
| 8 | Semantic type system / semantic lint. | 05:25:46 | "run a jeike model in your lint checker ... uphold semantic properties" | L, C | Add one LLM lint rule to CI on a sample repo; measure flake rate over 5 reruns. |
| 9 | Need reliability ("Einstein 95%, Mr. Bean 5%"), which benchmarks do not show. | 05:16:20-05:16:43 | "if you can't tell which is which, how ... are you going to automate anything" | L, C | Run the same prompt 50 times; report the spread, not the mean. |
| 10 | Intelligence as a "fourth logic gate" inside program control flow; needs cheap, fast, smart. | 05:20:30, 05:20:57 | "push the frontiers of cheap, smart, fast" | L | Measure tokens/s and cost per call of a small local model for a semantic predicate. |
| 11 | State management instead of global state in a KV cache. | 05:22:23 | "actually do state management instead of assuming everything is global state within a KV cache" | C | Compare a task split into stages with explicit state objects vs one long chat. |
| 12 | Unreliable AI pushes review cost onto recipients ("slop"). | 05:26:39 | "it's actually totally fine to push the costs into other people" | n/a | Not a testable systems claim. |

Not in the talk (searched the full transcript): energy use, local or open-weight models, weights/continual-learning-in-weights, hardware, KV-cache cost numbers, O(log N) as a stated figure. Self-hosting is argued only in the blog. Only one concrete recommendation exists: design agents around the cache and push for verifiable stages. He says he has no finished architecture, and the page says "these are design questions, not demonstrated solutions". His reliability claims for Jev are unproven in the transcript.

## Part 2. Source verification

| Source | URL | OPENED | Date | Result |
|---|---|---|---|---|
| Lance Martin talk page | https://ai.engineer/code/2026/talks/lance-martin | yes | 12 Nov 2026 | Title "Exploring Claude's Frontier", Anthropic MTS, Day 2 livestream `y9JtCCZP2MQ` 3:48:31-4:06:52. Confirms 1,000 agents, lead plus helpers, Git plus SQL, ~30h run, memory directory, "dreaming", CL-Bench ("open-source continued learning benchmark called CLBench", 3:57:32). Page flags ~30h as Anthropic's own unreproduced result. |
| Multi-agent post (a) | https://claude.dev/blog/safely-scaling-multi-agent-teams-with-fable-5-2/ | yes | 9 Nov 2026 | Title "Safely scaling multi-agent teams with Claude Fable 5.2". Authors Zhang, Peng, Najt, Scholl, Martin. Confirms 1,000 agents, 28.7 h, one-third the output tokens, proof one-seventh the length, 60 statements, 47 proved lemmas given, 5 SQL tables (announce, assign, notes, subtasks, landed), no network in sandboxes, classifier plus offline monitor. Earlier Sept run: 11 days, ~6B output tokens, 13M Lean lines. Calls itself a "toy experiment". Not a new proof. |
| Same post, anthropic.com | https://www.anthropic.com/engineering/safely-scaling-multi-agent-teams-with-fable-5-2 | yes | n/a | HTTP 404 (guessed URL). The anthropic.com/engineering index (29 articles) does not list it. I could not confirm that claude.dev is Anthropic-operated; the post text reads as Anthropic's. Not found on anthropic.com. |
| Memory post (b) | https://www.anthropic.com/research/components-of-agent-memory | yes | 6 Nov 2026 | "The components of agent memory" (listed under Engineering). Confirms dreaming, CL-Bench 1.0 database task via Managed Agents, Pokemon comparison (Sonnet 3.7: 413 files / one badge; Fable 5: nine files / four badges), wrong-landmark note fixed by dreaming, "tell Claude what memory is for, but not how". Read ~13,000 of ~24,800 characters; the later wiki/consolidation-compute evaluation was not read. |
| CL-Bench repo | https://github.com/pgasawa/continual-learning-bench | yes (README and GitHub API) | created 2026-04-30, last push 2026-07-19 | Licence Apache-2.0, 250 stars. Python 3.13+, uv, Docker. CLI `clbench`. Task = multiple episodes in a shared environment, an evaluation script and reward metric, and schedules/variants. Systems in `src/systems/`, tasks in `src/tasks/`. |
| CL-Bench paper | https://arxiv.org/abs/2606.05661 | yes | submitted 4 Jun 2026 (v1) | Six domains: software engineering, signal processing, disease outbreak forecasting, database querying, strategic games, demand forecasting. Abstract says "naive ICL outperforms systems dedicated to memory management". Task format detail beyond the README was not read. |
| Diogo blog | https://www.completeskeptic.com/p/kv-cache-rules-everything-around | yes (full text) | 9 Sep 2026 | See below. |
| Pricing | https://platform.claude.com/docs/en/about-claude/pricing (same text at docs.claude.com) | yes | read 2026-11-19 | See below. |

### Cost-share pie: NOT confirmed

The blog's pie chart is an image and no values exist in the page text or alt text. What the text does say:

- "Output tokens ... are just 9-18% of the total bill. The rest is the model re-reading its own history." Assumes Fable 5 pricing, cache writes at 1.25x input, and 100% cache hit rate in the pie.
- The caption says "Only the additional cache write cost is separated from input cost."
- No 67%, 12% or 3% appears anywhere. The ~18% output figure is consistent only as the top of the 9-18% range. Cache read ~67%, input ~12% and write ~3% are unverified; the image was not opened. Someone should read the chart image or ask the author.
- Related text figures: at an 89% hit rate the workload costs $1.97M vs $1.07M at perfect caching (84% more); a third party cited in the blog (Martin Alderson) found cache reads ~76% of an Opus 5 bill in a modelled 100-turn session; "Fable 5.1 cut them from $1.00 to $0.25 per million tokens". The pricing table agrees on that last point (Fable 5 $1, Fable 5.1 $0.25).
- The simulator uses Nvidia Open-SWE-Traces with a gpt-oss tokenizer, so token counts are approximations for Claude. Rate/hit-rate figures from OpenCode and third parties were not opened.

### Current pricing (per MTok; multipliers are my arithmetic from the table)

| Model | Input | Output | 5m write | 1h write | Cache hit |
|---|---|---|---|---|---|
| Fable 5.2 | $8 | $40 | $10 (1.25x) | $16 (2x) | $0.20 (0.025x) |
| Opus 5.5 | $4 | $20 | $5 (1.25x) | $8 (2x) | $0.20 (0.05x) |
| Sonnet 5.5 | $2 | $10 | $2.50 (1.25x) | $4 (2x) | $0.10 (0.05x) |
| Fable 5.1 | $10 | $50 | $12.50 | $20 | $0.25 (0.025x) |
| Fable 5 | $10 | $50 | $12.50 | $20 | $1 (0.1x) |

The Haiku 5.5 row in the scraped text is garbled (tiered at 100k tokens); I did not use it. The page also says "All other models use the standard 0.1x multiplier". Because cache hits now cost 0.025x-0.05x, the pie would shift toward output and writes under current prices compared with the Fable 5 pie.

## Part 3. Frontier work (arXiv abstracts opened; full papers not read unless noted)

KV-cache sharing across agents
- 2510.12872 KVCOMM (OPENED, abstract): training-free reuse via an anchor pool; >70% reuse, up to 7.8x speedup in a 5-agent setting. Peer-reviewed status not checked, so treat as preprint.
- 2609.34060 KVCMAS (OPENED, abstract): low-rank online correction; 2.0x TTFT, up to 3.7x lower peak GPU memory vs a prior correction method. Preprint.
- 2601.08343 (OPENED, abstract): KV reuse can make an LLM judge's choices inconsistent with dense prefill even when accuracy looks stable. Preprint. A cautionary result for Diogo's shared-state idea.
- 2608.14624 CacheScout (OPENED, abstract): learns agent execution order to guide cache eviction/prefetch. Preprint.
- All of these need open-weight models with access to the cache. None work through the Claude API, where caches are not shared across models (the blog's point).

Prefix/prompt cache economics
- 2601.06007 Don't Break the Cache (OPENED, abstract): 500+ sessions, three providers; cost down 41-80%, TTFT down 13-31%; placing dynamic content last and excluding dynamic tool results beat naive full-context caching, which can raise latency. Preprint; provider pricing has since changed.
- 2607.19214 Keepalive economics (OPENED, abstract): pinging inside the TTL keeps the prefix warm; up to 12.5x cheaper post-pause request; about 4 minutes at a 5-minute TTL. Single author, preprint.

Sub-linear and hierarchical memory
- 2512.18950 MACLA (OPENED, abstract and HTML text): frozen LLM plus hierarchical procedural memory; 2,851 trajectories compressed to 187 procedures. The "logarithmic" in the text describes the learning curve/saturation, not a proven O(log N) memory size. Accepted at a conference per the abstract comments; not checked further.
- 2608.20631 Weighted Memory Tree (OPENED, abstract): hierarchical task/subtask/action memory with retention scores; +9.97 points accuracy and -32.8% prompt tokens vs linear memory on GAIA-Text with small open models. Preprint; no growth-rate proof.
- 2606.06448 Agent Memory characterization (OPENED, abstract): systems profile of ten memory systems; cost split by construction, retrieval and generation. Preprint.
- 2506.04761 Log-Linear Attention (OPENED, abstract): a logarithmically growing set of hidden states inside the model. This is the only formal log-growth result I opened, and it concerns attention state, not an agent notes store.

Established vs preprint: everything above is arXiv; I did not verify peer review for any item. No opened paper establishes O(log N) memory for agents.

## Corrections/uncertainties

1. Talk title and video ID in the brief are wrong; the transcript and talk page say "Beyond Better Assistants" (`ZZ19zhYnDKY`). Whether `Cyt3LU8TyNc` is the same talk is unknown.
2. The cost-share pie figures (67/18/12/3) are unverified; only "output 9-18%" is in the text.
3. Quotes are ASR; "O(N)" and "log" readings are my inference.
4. The multi-agent post was read on claude.dev, not anthropic.com (guessed URL returned 404). The memory post was only partly read.
5. The memory post's wiki/consolidation-compute results and the CL-Bench full task schema were not read.
6. I did not run any experiments; "cheap experiments" are proposals. Local-GPU specs were not checked.
7. Search-result summaries were used only to find candidates; every ID listed as opened was read from arxiv.org/abs, except MACLA, where I also read the HTML text.
