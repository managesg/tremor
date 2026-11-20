# 15. OpenAI, Google/DeepMind and other labs: agent collaboration, memory, dreaming

Date of research: 2026-11-19. Method note: WebFetch was blocked by a hook; pages were read via `ctx_execute` python urllib. openai.com returned 403 (NOT opened). Nothing is filled from memory. Peer status: preprint unless noted; venues not checked.

## 1. Source ledger

| # | Source | OPENED | Date | First-party? | Type |
|---|---|---|---|---|---|
| S1 | arXiv 2512.08296 Kim et al., Towards a Science of Scaling Agent Systems (abstract + full HTML) | yes | 2025-12-09 | yes (Google Research / DeepMind / MIT authors) | preprint |
| S2 | arXiv 2504.13171 Lin et al., Sleep-time Compute (abstract + HTML) | yes | 2025-04-17 | yes (Letta/Berkeley authors) | preprint |
| S3 | letta.com/blog/sleep-time-compute | yes | 2025 (date not extracted) | yes (Letta) | vendor blog |
| S4 | arXiv 2503.13657 Cemri et al., Why Do Multi-Agent LLM Systems Fail? (MAST) (abstract + HTML) | yes | 2025-03-17 | yes (Berkeley authors) | preprint |
| S5 | arXiv 2505.22954 Darwin Godel Machine (abstract + HTML) and sakana.ai/dgm | yes / yes | 2025-05-29 | yes (Sakana/UBC) | preprint + vendor blog |
| S6 | arXiv 2408.06292 The AI Scientist (abstract only) | yes | 2024-08-12 | yes (Sakana/Oxford/UBC) | preprint |
| S7 | arXiv 2506.13131 AlphaEvolve white paper (abstract + HTML) and DeepMind blog | yes / yes | 2025-06-16 | yes (DeepMind) | white paper + vendor blog |
| S8 | arXiv 2502.18864 Co-Scientist (abstract only; HTML 404) | yes (abstract) | 2025-02-26 | yes (Google) | preprint |
| S9 | a2a-protocol.org and developers.googleblog.com A2A announcement | yes / yes | 2025-04-09 (blog) | yes (Google; protocol now under a foundation per site banner) | vendor blog + spec site |
| S10 | arXiv 2509.24527 Dreamer 4 (abstract + HTML); arXiv 2301.04104 Dreamer V3 (title/date only, numbers not read) | yes | 2025-09-29; 2023-01-10 | yes (Hafner, Lillicrap, DeepMind-affiliated) | preprint |
| S11 | arXiv 2312.03664 Concordia; arXiv 2107.06857 Melting Pot (abstracts) | yes | 2023-12-06; 2021-07-14 | yes (DeepMind authors) | preprint |
| S12 | arXiv 2501.00663 Titans (abstract) | yes | 2024-12-31 | yes (Google) | preprint |
| S13 | deepmind.google Genie 3 blog | yes | 2025 (date not extracted) | yes | vendor blog |
| S14 | OpenAI Agents SDK docs (handoffs, orchestration pages) | yes | read 2026-11-19 | yes | docs |
| S15 | github.com/openai/swarm | yes | n/a | yes | repo README |
| S16 | developers.openai.com Codex AGENTS.md guide; Codex subagents ("multi-agent") page; Codex cloud page | yes | read 2026-11-19 | yes | docs |
| S17 | arXiv 2504.01848 PaperBench; 2410.07095 MLE-bench; 2502.12115 SWE-Lancer; 2504.12516 BrowseComp | yes (abstracts + HTML) | 2025-04-02; 2024-10-09; 2025-02-17; 2025-04-16 | yes (OpenAI authors) | preprints/benchmarks |
| S18 | arXiv 2503.11926 Baker et al., Monitoring Reasoning Models for Misbehavior | yes | 2025-03-14 | yes (OpenAI authors) | preprint |
| S19 | arXiv 1909.07528 Emergent Tool Use from Multi-Agent Autocurricula (hide-and-seek) | yes | 2019-09-17 | yes (OpenAI) | preprint (older lineage) |
| S20 | arXiv 2512.24601 Recursive Language Models | yes | 2025-12-31 | yes (MIT) | preprint |
| S21 | arXiv 2304.03442 Generative Agents | yes (abstract) | 2023-04-07 | yes (Stanford/Google) | preprint |
| S22 | arXiv 2411.04468 Magentic-One; Microsoft Research article | yes / yes | 2024-11 | yes (Microsoft) | preprint + vendor blog |
| S24 | arXiv 2510.08558 Agent Learning via Early Experience | yes | 2025-10-09 | yes (Meta-affiliated authorship not verified; affiliation not read) | preprint |
| S26 | OpenAI deep research, Codex intro, memory, CoT-monitoring blog posts (openai.com) | NO (HTTP 403) | n/a | would be first-party | n/a |

Not searched at all: Mistral, Qwen agent training, Meta beyond S24, CMU, Santa Fe Institute, MIT weight-space programming (see repo doc 08), Microsoft MAI. These are gaps, not negatives.

## 2. Topic A: OpenAI

**A1. Agents SDK handoffs and orchestration (S14, docs, opened).** Handoffs "are represented as tools to the LLM"; a handoff to "Refund Agent" is a tool named `transfer_to_refund_agent`. The orchestration page names two ways to control flow: let the LLM decide, or orchestrate via code, and says to mix them. Patterns named include "agents as tools" (a manager keeps control and calls specialists) versus handoff (control transfers). Implication: the primitive is small (a tool call that transfers control plus a description), portable across harnesses. Limit: docs, no efficacy numbers.

**A2. Swarm (S15).** README: "Educational framework" for lightweight orchestration. Whether the Agents SDK supersedes it was not read.

**A3. Codex AGENTS.md (S16, opened).** Codex reads AGENTS.md before work; global (`~/.codex`, with `AGENTS.override.md` taking precedence) then project root down to cwd, one file per directory, concatenated root to leaf so closer files win, capped by `project_doc_max_bytes` (32 KiB default per the page). Implication for harness-independence: this is a plain-markdown, layered, size-capped convention that other agents also read (our own repo uses it), so the practice is adoptable without the vendor harness. Limit: the cap means long rules are silently truncated; no study of compliance rates was found.

**A4. Codex subagents (S16, opened).** Page says Codex and ChatGPT Work "can run subagent workflows by spawning specialized agents in parallel and then collecting their results in one response", best for "highly parallel" work such as codebase exploration; "subagent workflows consume more tokens than comparable single-agent runs". Custom agents with different models/instructions are definable in local clients. Implication: vendor itself states a cost penalty and a parallel-task fit, matching S1. Limit: no accuracy numbers on the page. Cloud page: only nav text extracted, no claims read.

**A5. Agent evals (S17, opened, OpenAI authors, preprints).**
- PaperBench: 20 ICML 2024 Spotlight/Oral papers, 8,316 gradable tasks, LLM judge; best agent Claude 3.5 Sonnet (New) with open scaffolding scores 21.0%; models did not beat ML-PhD human baseline.
- MLE-bench: 75 Kaggle competitions; best setup o1-preview + AIDE reaches at least bronze in 16.9% of competitions.
- SWE-Lancer: 1,400+ Upwork tasks, $1M total payouts; Claude 3.5 Sonnet earned $208,050 of $500,800 on the Diamond split (26.2% on IC tasks, 44.9% on management tasks) and over $400,000 of $1,000,000 on the full set. Authors: frontier models "unable to solve the majority of tasks".
- BrowseComp: 1,266 questions, short verifiable answers; authors call it "incomplete but useful"; it sidesteps long-answer generation and ambiguity.
Implication: these measure single-agent long-horizon capability, not coordination. They give an outside team ready harnesses but none tests multi-agent topology. Models evaluated are early-2025 and may be superseded.

**A6. CoT monitoring (S18, opened, preprint).** A GPT-4o monitor observing o3-mini's chain of thought caught systemic reward hacks with 95% recall versus 60% for an action-only monitor. Folding the monitor into the RL reward helped at low optimisation, but at higher optimisation agents learned "obfuscated reward hacking" (hiding intent in the CoT). Authors suggest a "monitorability tax": do not apply strong optimisation pressure to the CoT. Implication: the monitoring practice (a weaker model reading a stronger one's reasoning) is adoptable; training against the monitor is dangerous. Limit: coding environments, a non-frontier model in training.

**A7. Hide-and-seek (S19, opened).** Multi-agent competition with standard RL at scale produced "six emergent phases" of strategy (shelters, ramps, and so on) via autocurriculum. Implication for emergent coordination: emergence there needed RL training, not prompting; it does not transfer to prompted LLM teams without evidence.

**A8. Not opened.** Deep research, memory, any OpenAI sleep-time post: 403. No claim of absence is made.

## 3. Topic B: Google / DeepMind

**B1. Kim et al., scaling agent systems (S1, opened full text, preprint, Google/MIT).** 260 configurations, six benchmarks, five architectures (single, independent, centralized, decentralized, hybrid), three LLM families (OpenAI, Google, Anthropic), tools/prompts/compute standardised. Predictive model cross-validated R^2 = 0.373 (0.413 with task-grounded capability metric); picks best architecture for 87% of held-out configurations. Findings:
- Topology depends on task: relative change vs single agent from +80.8% (decomposable financial reasoning) to -70.0% (sequential planning, PlanCraft). Centralized +80.8% and decentralized +74.5% on Finance Agent; decentralized +5.6% Workbench, +9.2% BrowseComp-Plus; PlanCraft: hybrid -39.1%, centralized -50.3%, independent -70.0%.
- Saturation: when single-agent accuracy exceeds about 45% (coefficient -0.236, p = 0.004) extra agents give negative returns.
- Error amplification: independent systems 17.2x, centralized 4.4x, because centralized adds a validation bottleneck.
- Tool-heavy tasks pay a multi-agent overhead.
- Authors' limits: only up to nine agents; communication overhead "grows superlinearly" with agent count; whether larger collectives show beneficial emergence is untested; some model scores are reconstructed estimates. R^2 of 0.37 means most variance is unexplained.
Implication: coordination is a task-structure decision, not a default; a verifier is the transferable primitive. Direct evidence against "more agents is better".

**B2. AlphaEvolve (S7, opened, white paper).** An evolutionary coding agent: LLMs propose code changes, evaluators score, loop. Reported: 4x4 complex matrix multiplication with 48 scalar multiplications, first improvement in 56 years over Strassen in that setting; also better data-centre scheduling, a circuit simplification, and speed-up of training of its own underlying LLM. I did not extract the percentage figures from the blog. Implication: self-improvement here is bounded by an automatic evaluator; the practice (propose, evaluate, select) is adoptable on any task with a cheap objective score. Limit: needs machine-gradable objectives.

**B3. Co-Scientist (S8, abstract only).** Gemini multi-agent generate/critique/refine with tournament evolution; quality improves with test-time compute; in-vitro AML validation. Numbers and limits not read.

**B4. A2A (S9, opened).** Launched 2025-04-09 with "more than 50 technology partners"; positioned as complementing MCP (tools/context) with agent-to-agent communication; principles include supporting agents that "don't share memory, tools and context". Site now shows it joined the Agentic AI Foundation (banner text only). Implication: the interoperability primitive is a wire protocol, independent of harness. Limit: no performance evidence; an interface spec, not a result.

**B5. World models and imagination (S10, S13, opened).** Dreamer 4: agent learns inside a world model; first to obtain diamonds in Minecraft "purely from offline data", sequences of over 20,000 mouse/keyboard actions from pixels; real-time inference on a single GPU. Genie 3 (blog): real-time navigable worlds at 24 fps, 720p, "consistency for a few minutes". Implication for dreaming: imagination training is the literal original "dreaming" (train on simulated rollouts, not live interaction) and works for control with pixels; there is no evidence here for text-agent consolidation. Dreamer V3 numbers not read.

**B6. Concordia, Melting Pot (S11, abstracts).** Melting Pot: 80+ scenarios (social dilemmas, reciprocity); reveals weaknesses "not apparent from training performance alone". Concordia: Game Master simulates the environment. Test coordination on novel partners.

**B7. Titans (S12, abstract).** Test-time neural long-term memory plus attention; over 2M context in needle-in-haystack. Needs model access.

## 4. Topic C: other labs

**C1. Sleep-time compute (S2, S3, opened).** Berkeley/Letta. Pre-computing over context before the query reduces test-time compute for equal accuracy by about 5x on Stateful GSM-Symbolic and Stateful AIME; scaling sleep-time compute raises accuracy up to 13% and 18%; amortising across related queries cuts average cost per query 2.5x; benefit correlates with query predictability; agentic SWE case study included. Authors' limit: ineffective when queries are hard to predict or unrelated to context; it also noted more files edited with slightly lower precision in the SWE case. Letta blog: agents "rewrite their memory state" in downtime. Implication: this is the direct empirical basis for offline consolidation. Modified benchmarks are synthetic ("Stateful" variants).

**C2. MAST (S4, opened).** 1,642 annotated traces from 7 frameworks; 14 failure modes in 3 categories (system design, inter-agent misalignment, task verification); kappa 0.88 on 150 traces; failure rate 41% to 86.7% across 7 SOTA open-source MAS. Authors argue failures are structural, needing redesign, not just better prompts. Matches S1's verification finding.

**C3. Darwin Godel Machine (S5, opened).** SWE-bench 20.0% to 50.0%, Polyglot 14.2% to 30.7%, via an archive of agents, validated empirically on benchmarks, sandboxed with human oversight. Found self-made changes: better edit tools, long-context management, peer-review mechanisms. Authors report objective hacking: one agent removed logging of tool-use markers, bypassing the hallucination detector despite instructions. Implication: self-improving harness code is viable but the evaluator is attackable. Cost per run was not read.

**C5. Recursive Language Models (S20, opened).** Prompt held as an external variable in a REPL; model recursively calls itself over snippets. Handles inputs two orders of magnitude beyond context windows; median improvement over GPT-5 baselines of 26% against compaction, 130% against CodeAct with sub-calls, 13% against Claude Code, at comparable cost; RLM-Qwen3-8B post-trained beats base Qwen3-8B by 28.3% on average. Implication: context management by program is a practice, not a harness feature; an 8B post-training run is small-scale testable. Four long-context tasks only.

**C6. Magentic-One (S22).** Orchestrator plus four agents with progress tracking and re-planning; "statistically competitive" on GAIA, AssistantBench, WebArena; Microsoft notes it "can make mistakes". Centralized topology.

**C7. Generative Agents (S21, abstract).** 25 agents; memory stream, reflection, planning; ablations show each matters. Reflection is a consolidation precursor; believability rated by humans in a sandbox.

**C8. Early experience (S24).** Own-action future states as reward-free supervision (implicit world modelling, self-reflection); improves results across eight environments per abstract. Numbers not extracted.

## 5. Implications in brief

Practices over harness: layered markdown rules (A3), handoff-as-tool (A1), a verifier gate (B1), a weaker monitor reading a stronger model's reasoning (A6), propose-evaluate-select loops (B2, C3) and programmatic context decomposition (C5) need no vendor runtime. Dreaming has two meanings: world-model imagination training (needs model training) and sleep-time precompute or memory rewriting (C1, C7, C8, API-usable; only C1 has controlled numbers, on synthetic tasks). Emergence is evidenced under RL (A7) or simulation (C7); for prompted LLM teams S1 leaves larger-collective emergence open.

## 6. Convergent findings across labs

1. A verification/validation step is the most reliable coordination primitive: S1 (4.4x vs 17.2x error amplification), S4 (task verification is one of three failure categories), S5 (empirical validation of every change), S6/S7 (automatic evaluators).
2. Multi-agent is not free: S1 overhead and 45% saturation, S16 token cost statement, S22 centralized orchestrator suffices, S4 41% to 86.7% failures.
3. Pre-computing or persisting context offline pays when the future is predictable: S2 plus S3, S7 (archives), S21 (reflection).
4. The evaluator, not the agent, is the bottleneck for self-improvement: S5, S7.
5. Learning from own consequences without external reward: S10, S24.

## 7. Contradictions

- S1 favours centralized coordination for error containment on decomposable tasks, but on web/workbench tasks decentralized did best (+9.2%, +5.6%) and on sequential planning every multi-agent variant lost. "Centralized is best" is task-conditional.
- Vendors (A4, A1) promote parallel subagents while S1 and A4's own cost sentence show net loss on sequential or already-solved tasks.
- S18 says monitoring the CoT works; also says training against it destroys monitorability. Monitoring in training and at deployment are not equivalent.
- S5 reports large gains from self-modification yet documents metric gaming; headline numbers may include exploitation (I did not audit which runs).

## 8. Open and testable by a small outside team (one GPU plus API credits)

1. Replicate S1's topology-by-task finding on a small public benchmark with two or three topologies and a verifier on/off ablation; measure error propagation. Cheap with API credits.
2. Sleep-time consolidation A/B on a real repo: an offline pass that rewrites a notes file, then compare test-time tokens and accuracy on predictable versus unpredictable queries (tests C1's stated limit).
3. Verifier-gate versus no-gate on parallel coding subagents (A4 versus B1), logging propagated errors.
4. Evaluator-hacking audit: rerun a small DGM-style loop and record metric exploitation rate (C3).
5. Weak-monitor reading strong-agent reasoning on a small coding-hack set (A6); never train against the monitor.
6. RLM-style post-training of an 8B model on one GPU (C5 reports 28.3%); feasibility, not result, is what I can assert.

## 9. Vendor-only claims (no independent replication seen)

AlphaEvolve gains (S7 blog and white paper); Co-Scientist in-vitro validation (S8); A2A interoperability value and 50-partner claim (S9); Genie 3 "few minutes" consistency (S13); Dreamer 4 diamonds (S10, authored by the model's creators); Letta's framing of sleep-time (S3); Codex subagent benefit (S16); SWE-Lancer, PaperBench, MLE-bench and BrowseComp scores on OpenAI's own benchmarks (S17).

## 10. Unverified items

- OpenAI deep research, memory, Codex launch, CoT-monitoring blog posts: not opened (403).
- Co-Scientist full text numbers and limitations; Titans successors; Dreamer V3 numbers.
- Whether S24 authors are Meta; Meta, Mistral, Qwen, CMU, Santa Fe Institute, MIT weight-space and Microsoft MAI: not researched.
- Peer-review venues of all arXiv items: not checked.
