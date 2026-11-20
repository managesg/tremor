# 02 - Multi-agent coordination: LLM-agent evidence and organizational science

Date: 2026-11-19. Method: public web search plus fetching abstracts or pages.
Verified key: **Y** = I opened the page and read the quoted text. **N (search)** = URL and claim seen only in search-result text, not opened. Figures are quoted from the cited source only. Several 2026 papers are preprints (not peer reviewed unless stated).

---

## A. Practitioner write-ups and platform docs

### A1. Anthropic multi-agent research system
**Source:** Anthropic Engineering, "How we built our multi-agent research system". https://www.anthropic.com/engineering/multi-agent-research-system (verified: Y)
**Reliability:** Medium. Vendor, internal eval, not peer reviewed.
**Status:** established as a practitioner report; the causal claims are interpretation.
**Plain-language concept:** A lead agent plans and spawns parallel subagents with separate context windows. Reported: Opus 4 lead plus Sonnet 4 subagents beat single-agent Opus 4 by 90.2% on their internal research eval; agents use about 4x chat tokens, multi-agent about 15x; token usage alone explained 80% of BrowseComp variance. They say most coding tasks have fewer truly parallelizable parts than research.
**Coding-agent analogy:** Fan-out is a way to buy more token capacity and context, not "smarter teamwork".
**Where the analogy fails:** Research subagents read; coding subagents write to shared state, so merge cost appears.
**Concrete experiment:** On N fixed tasks, run 1 agent vs lead+k workers at matched total tokens; record pass rate and tokens per pass. If the multi-agent gain vanishes at matched tokens, fan-out is a budget effect only.

### A2. Anthropic "Building effective agents"
**Source:** Anthropic, Dec 19 2024. https://www.anthropic.com/engineering/building-effective-agents (verified: Y)
**Reliability:** Medium (vendor guidance).
**Status:** interpretation.
**Plain-language concept:** Find the simplest solution and add complexity only when needed. Orchestrator-workers fits tasks where subtasks cannot be predicted in advance (the page gives coding as an example).
**Coding-agent analogy:** Default to one agent; add an orchestrator only when decomposition is unknowable up front.
**Where the analogy fails:** It gives no quantitative threshold for when to switch.
**Concrete experiment:** Log how often a planned decomposition changes mid-run; use that rate as the switch signal between a fixed pipeline and an orchestrator.

### A3. Claude Code subagents, agent teams, worktrees
**Source:** https://code.claude.com/docs/en/sub-agents and https://code.claude.com/docs/en/agent-teams (both opened: Y); https://code.claude.com/docs/en/common-workflows (search result only, N). Depth and concurrency limits (3 and 20) come from the SDK subagents page, seen in search text only (N).
**Reliability:** High for what the product does; no efficacy data.
**Status:** established (documentation).
**Plain-language concept:** Subagents report back to a main orchestrator and do not talk to each other. Agent teams (experimental, off by default) add direct messaging and a shared task list, at higher token cost. Worktrees give each session its own checkout.
**Coding-agent analogy:** Subagents = hub-and-spoke; teams = a shared blackboard (task list) plus messages.
**Where the analogy fails:** Worktrees isolate files, not meaning; interface drift still merges cleanly but breaks (see D2).
**Concrete experiment:** Same 6 tasks with subagents vs agent-team mode; count duplicated edits (same hunk by 2 agents) and tokens.

### A4. Claude Managed Agents multiagent orchestration
**Source:** https://platform.claude.com/docs/en/managed-agents/multiagent-orchestration (search result only; verified: N)
**Reliability:** Low-medium until the page is read directly.
**Status:** established as product description (unverified details).
**Plain-language concept:** Per search text: multiagent block with advisor, subagents and workflows; delegation one level deep; agents in a session share sandbox and filesystem but have separate thread histories; dynamic workflows let Claude write an orchestration program.
**Coding-agent analogy:** "Orchestration as code" moves coordination from model judgment to deterministic scripts.
**Where the analogy fails:** Shared filesystem means shared-state races remain.
**Concrete experiment:** Replace an LLM orchestrator's merge-ordering decisions with a deterministic script on the same tasks; compare clean-merge rate.

---

## B. Multi-agent failure and scaling science

### B1. MAST: why multi-agent LLM systems fail
**Source:** Cemri et al., "Why Do Multi-Agent LLM Systems Fail?" arXiv:2503.13657. https://arxiv.org/abs/2503.13657 (verified: Y)
**Reliability:** Medium-high (large annotated set, kappa reported; preprint).
**Status:** established as taxonomy.
**Plain-language concept:** 1600+ annotated traces over 7 frameworks; 14 failure modes in 3 clusters: system design, inter-agent misalignment, task verification (taxonomy built from 150 traces, kappa = 0.88). Gains from MAS on popular benchmarks are often minimal.
**Coding-agent analogy:** A checklist for post-mortems of orchestrated runs.
**Where the analogy fails:** Traces come from generic frameworks, not git-based coding fleets.
**Concrete experiment:** Tag 50 of your own failed runs with the 14 modes; see whether verification failures dominate.

### B2. Towards a science of scaling agent systems
**Source:** Kim et al., arXiv:2512.08296. https://arxiv.org/abs/2512.08296 (verified: Y)
**Reliability:** Medium-high (controlled, 260 configs; R^2 only 0.373 cross-validated).
**Status:** established for the tested benchmarks; extrapolation is interpretation.
**Plain-language concept:** Across 5 architectures and 6 benchmarks, relative change vs single agent ranged from +80.8% (decomposable finance) to -70.0% (sequential planning). Coordination gives diminishing returns above a single-agent baseline threshold; tool-heavy tasks pay overhead; no centralized verification means more error propagation. Predicts best architecture for 87% of held-out configs. (Error amplification 4.4x vs 17.2x and "45%" threshold: search snippet only, N.)
**Coding-agent analogy:** Parallelize only decomposable work; keep sequential work on one agent; add a central verifier.
**Where the analogy fails:** Benchmarks are not repo-scale edits.
**Concrete experiment:** Label 30 tasks decomposable/sequential by dependency graph; test whether fan-out win/loss follows the label.

### B3. CooperBench
**Source:** Khatua et al., "CooperBench: Why Coding Agents Cannot be Your Teammates Yet", arXiv:2601.13295. https://arxiv.org/html/2601.13295 (search result only; verified: N)
**Reliability:** Medium (not opened; figures differ between sources).
**Status:** interpretation pending verification.
**Plain-language concept:** Per search text, two agents implementing separate features in one codebase succeed about 30% less than doing both alone ("curse of coordination"); failures attributed to communication, broken commitments, wrong expectations. An author post says 50%; unresolved.
**Coding-agent analogy:** Pairwise parallel feature work is the hard case.
**Where the analogy fails:** Chat-only coordination; a shared spec/contract file might change it.
**Concrete experiment:** Replicate on 20 pairs with and without a machine-checkable contract file both agents must update.

### B4. Sub-agent concurrency in long-horizon coding
**Source:** Li et al., arXiv:2610.10263. https://arxiv.org/abs/2610.10263 (verified: Y)
**Reliability:** Medium (354 tasks, 2124 executions, Codex/Claude Code/Kimi Code; preprint).
**Status:** established for tested agents.
**Plain-language concept:** Dynamic concurrency did not consistently raise success: resolution effects ranged from -11.9 to +2.3 percentage points, token use 1.41x to 3.31x. Gains appeared on long-horizon benchmarks (LoopsBench), none on bounded SWE-bench Verified tasks. Catalogues 13 concurrency failure modes.
**Coding-agent analogy:** Parallel fan-out pays only on long, large tasks.
**Where the analogy fails:** The agent decides when to spawn; forced fan-out may differ.
**Concrete experiment:** Gate fan-out on estimated task size (files touched); measure pass rate and token multiple vs always-on.

---

## C. Parallel coding agents: conflicts and duplicate work

### C1. Merge-conflict field data
**Source:** AgenticFlict, arXiv:2604.03551. https://arxiv.org/abs/2604.03551 (verified: Y)
**Reliability:** Medium-high for rate; preprint, textual conflicts only.
**Status:** established.
**Plain-language concept:** 142K+ agent PRs, 107K+ processed by merge simulation, 27.67% conflict rate, 336K+ conflict regions. (Same-agent vs cross-agent pair rates of 19.8% / 41.7% appear only in a GitHub issue summary: UNVERIFIED.)
**Coding-agent analogy:** Roughly one in four agent PRs conflicts with base.
**Where the analogy fails:** Public-repo PRs, not coordinated in-house fleets.
**Concrete experiment:** Dry-run `git merge-tree` of all open agent branches nightly; log conflict rate per file/dir.

### C2. Semantic conflicts that merge cleanly
**Source:** "Passes Alone, Fails Together", arXiv:2609.25396. https://arxiv.org/abs/2609.25396 (verified: Y)
**Reliability:** Medium (workshop paper; authors state constructed rates do not estimate real frequency).
**Status:** established on benchmark; real-world frequency unknown.
**Plain-language concept:** Of 834 runs on 417 mined Django pairs, one showed interference; on constructed tasks, interference in 97% of runs; a message describing the concurrent change recovered 82%.
**Coding-agent analogy:** Notify peers of interface changes.
**Where the analogy fails:** Real merged PRs rarely collide semantically.
**Concrete experiment:** Run each branch's tests alone and on the merged tip; count tests failing only after merge.

### C3. Up-front scope partitioning
**Source:** NP-Bench / Nerveplane, arXiv:2610.07261. https://arxiv.org/abs/2610.07261 (verified: Y)
**Reliability:** Low-medium (small scenarios: 9; tool authors evaluate own planner).
**Status:** speculative-to-interpretation.
**Plain-language concept:** Declare scopes, partition into disjoint ones, order merges producer-to-consumer. Reported clean integration 1/9 to 9/9 and conflicts 13 to 0.
**Coding-agent analogy:** Scheduling, not warning.
**Where the analogy fails:** Needs accurate scope declarations.
**Concrete experiment:** Compare declared file scope to actual diff paths over 100 runs; measure overlap precision.

### C4. Observation-driven coordination with CRDTs
**Source:** CodeCRDT, arXiv:2510.18893. https://arxiv.org/abs/2510.18893 (verified: Y)
**Reliability:** Medium-low (6 tasks x 50 runs).
**Status:** established small-scale.
**Plain-language concept:** 600 trials: up to 21.1% speedup on some tasks, up to 39.4% slowdown on others, 100% convergence, semantic conflict 5-10%.
**Coding-agent analogy:** Conflict-free text merge does not mean correct code.
**Where the analogy fails:** Non-git substrate.
**Concrete experiment:** Add a post-merge test gate and count semantic failures per merge.

### C5. Claim-before-write admission
**Source:** "Claim Plane", arXiv:2608.00947 and 2607.21909. https://arxiv.org/pdf/2608.00947 (search result only; verified: N)
**Reliability:** Low until read.
**Status:** speculative.
**Plain-language concept:** Deterministic pre-write admission of change intents for parallel agents; title mentions "reliability gains and limits of selective concurrency".
**Coding-agent analogy:** Lock files by declared intent.
**Where the analogy fails:** Unknown from snippet.
**Concrete experiment:** Implement advisory path-claim file; count blocked-duplicate edits.

---

## D. Framework and role literature

### D1. MetaGPT, ChatDev, CAMEL, AgentVerse, AutoGen
**Source:** arXiv:2308.00352 (MetaGPT), 2307.07924 (ChatDev), 2303.17760 (CAMEL), 2308.10848 (AgentVerse), 2308.08155 (AutoGen); all at https://arxiv.org/abs/<id> (verified: Y, abstracts)
**Reliability:** Medium for design ideas; benchmarks are early and weak.
**Status:** interpretation.
**Plain-language concept:** MetaGPT encodes SOPs as assembly-line roles so agents verify intermediate artifacts. ChatDev chat chains with "communicative dehallucination". CAMEL role-playing with inception prompts. AgentVerse dynamically adjusts group composition. AutoGen programmable conversation patterns.
**Coding-agent analogy:** Role = scoped prompt plus artifact contract.
**Where the analogy fails:** MAST and Agentless show role pipelines often add failure surface.
**Concrete experiment:** Ablate each role (remove "reviewer") over 30 tasks; keep a role only if it changes pass rate.

### D2. Magentic-One
**Source:** arXiv:2411.04468. https://arxiv.org/abs/2411.04468 (verified: Y)
**Reliability:** Medium.
**Status:** established.
**Plain-language concept:** Orchestrator plans, tracks progress, re-plans; statistically competitive on GAIA, AssistantBench, WebArena; agents can be added/removed without change.
**Coding-agent analogy:** Progress ledger plus re-plan loop.
**Where the analogy fails:** Web tasks, not shared-repo writing.
**Concrete experiment:** Add an explicit "ledger" file the orchestrator updates; measure stalled-run rate.

### D3. SWE-agent, Agentless, OpenHands
**Source:** arXiv:2405.15793, 2407.01489, 2407.16741; https://arxiv.org/abs/<id> (verified: Y)
**Reliability:** Medium (2024-era numbers).
**Status:** established for their time.
**Plain-language concept:** SWE-agent: interface design (ACI) matters, 12.5% pass@1 on SWE-bench. Agentless: simple localize-repair-validate got 32.00% on SWE-bench Lite at $0.70. OpenHands: platform with multi-agent coordination.
**Coding-agent analogy:** Tool and pipeline design can beat agent count.
**Where the analogy fails:** Numbers outdated for current models.
**Concrete experiment:** Compare your orchestrated run to a fixed localize-edit-test script on the same tasks, cost per pass.

### D4. Debate and ensembles
**Source:** Du et al. arXiv:2305.14325; "Stop Overvaluing Multi-Agent Debate" arXiv:2502.08788; Self-MoA arXiv:2502.00674; https://arxiv.org/abs/<id> (verified: Y)
**Reliability:** Medium-high for the negative results (9 benchmarks, 4 models).
**Status:** established, contested.
**Plain-language concept:** Debate improved reasoning in 2023; a 2025 systematic study found MAD often fails to beat Chain-of-Thought and Self-Consistency despite more compute, and model heterogeneity helps. Self-MoA (one best model) beat mixing models by 6.6% on AlpacaEval 2.0 and 3.8% on average.
**Coding-agent analogy:** Diversity helps only if quality does not drop; sampling-then-selecting by tests is the cheap ensemble.
**Where the analogy fails:** Code has an executable oracle (tests); text tasks don't.
**Concrete experiment:** k independent attempts + test-based selection vs k-agent debate at equal tokens.

### D5. Role specialization vs generalists
**Source:** "Code in Harmony" (https://openreview.net/pdf?id=URUMBfrHFy), MapCoder-Lite arXiv:2509.17489, ECER 2026 comparison (all search results only; verified: N)
**Reliability:** Low-medium.
**Status:** interpretation.
**Plain-language concept:** Per search text: roles help when a feedback/verification loop exists (coder+tester); fixed pipelines lost to a single agent on bug-fix; general models were more robust across roles than code-specialized ones.
**Coding-agent analogy:** Specialize on verification, not on persona.
**Where the analogy fails:** Not read.
**Concrete experiment:** Compare coder+tester vs coder-only at equal tokens.

---

## E. Shared state, stigmergy, self-organization

### E1. Blackboard architectures
**Source:** Han and Zhang arXiv:2507.01701 (Y, https://arxiv.org/abs/2507.01701); Salemi et al. arXiv:2510.01285 (search result, N, https://arxiv.org/abs/2510.01285)
**Reliability:** Medium-low (reasoning/QA benchmarks).
**Status:** interpretation.
**Plain-language concept:** Agents read/write a common blackboard; next actor chosen from its content until consensus. Claimed best average performance with fewer tokens. A data-science variant reports 13-57% relative gains (snippet only).
**Coding-agent analogy:** A shared task/state file the repo owns.
**Where the analogy fails:** Still needs a control agent to pick who acts.
**Concrete experiment:** Replace message passing with a single append-only state file; compare tokens and duplicates.

### E2. Stigmergy and pressure fields
**Source:** arXiv:2601.08129 (pressure fields), 2512.10166 (collective memory); https://arxiv.org/abs/<id> (verified: Y)
**Reliability:** Medium-low (toy tasks).
**Status:** speculative for coding.
**Plain-language concept:** Agents act on a shared artifact guided by quality-signal gradients with temporal decay; meeting scheduling: 48.5% vs 12.6% conversation vs 1.5% hierarchical over 1,350 trials; decay off cost 10 points. Traces without agent memory failed completely in a grid world.
**Coding-agent analogy:** Failing tests/lint as pheromone; decay avoids lock-in.
**Where the analogy fails:** Scheduling is not code; traces need agents able to interpret them.
**Concrete experiment:** Failing-test count as a work-priority signal with decay on claimed items; compare with an assigned queue.

### E3. Self-organizing agent teams
**Source:** Dochkina arXiv:2603.28990 (verified: Y, https://arxiv.org/abs/2603.28990); also SelfOrg arXiv:2510.00685, TheBotCompany arXiv:2603.25928 (search result only, N).
**Reliability:** Medium-low (single-author preprint, simulated tasks).
**Status:** interpretation.
**Plain-language concept:** 25,000 tasks, 8 models, 4-256 agents: minimal structure (fixed ordering) outperformed centralized by 14% (p<0.001); strong models self-organized, weak models needed structure; 5,006 unique roles from 8 agents.
**Coding-agent analogy:** Give strong agents a shared ledger and ordering, not fixed personas.
**Where the analogy fails:** Task type is not code.
**Concrete experiment:** Fixed-role vs self-claimed task board over 40 tasks, equal tokens.

### E4. Multi-developer / diverse agent pools
**Source:** arXiv:2610.20518 "The Wealth of Agents". https://arxiv.org/abs/2610.20518 (verified: Y)
**Reliability:** Low-medium.
**Status:** speculative.
**Plain-language concept:** On GAIA, specialist agents each at or below 35% reached 70% combined.
**Coding-agent analogy:** Route by specialty.
**Where the analogy fails:** Routing quality unknown for code.
**Concrete experiment:** Log per-agent pass rate by task class; route to the best class, compare with round-robin.

---

## F. Organizational science

### F1. Brooks's law
**Source:** Brooks, The Mythical Man-Month (1975); secondary: https://en.wikipedia.org/wiki/Brooks%27s_law (verified: Y for the quote "Adding manpower to a late software project makes it later"; book itself UNVERIFIED).
**Reliability:** High as folk law, weak quantitative evidence.
**Status:** established (qualitative).
**Plain-language concept:** More people add training and communication overhead.
**Coding-agent analogy:** Adding agents mid-run adds onboarding (context) and n(n-1)/2 channels.
**Where the analogy fails:** Agents onboard in seconds from files; overhead is tokens and merge, not training.
**Concrete experiment:** Add a worker at minute T of a task; measure completion-time change vs not adding.

### F2. Conway's law
**Source:** Conway, "How Do Committees Invent?" (1968); summary page http://www.melconway.com/Home/Conways_Law.html (verified: Y).
**Reliability:** High (widely corroborated).
**Status:** established.
**Plain-language concept:** System design copies the organization's communication structure.
**Coding-agent analogy:** Agent boundaries produce module boundaries; one agent per module yields module seams.
**Where the analogy fails:** Agents share a repo view; "communication" is files.
**Concrete experiment:** Compare module coupling in code produced by 3 per-module agents vs 1 agent.

### F3. Malone and Crowston coordination theory
**Source:** ACM Computing Surveys 26(1), 87-119, 1994, DOI 10.1145/174666.174668. https://crowston.syr.edu/sites/default/files/acmcs94.pdf (search result only; verified: N)
**Reliability:** High (classic).
**Status:** established.
**Plain-language concept:** Coordination is managing dependencies: shared resources, producer/consumer, simultaneity, task/subtask.
**Coding-agent analogy:** Classify task dependencies, then pick the mechanism (lock, ordering, handoff).
**Where the analogy fails:** Predates LLM nondeterminism.
**Concrete experiment:** Annotate each merge conflict as one of the four dependency types; map to mitigation.

### F4. Galison trading zones
**Source:** Galison, Image and Logic (1997); https://projects.iq.harvard.edu/files/andrewhsmith/files/galison_trading_withthe_enemy.pdf (search result only; verified: N).
**Reliability:** Medium-high.
**Status:** established (history of science), analogy is interpretation.
**Plain-language concept:** Groups coordinate local exchange without agreeing on global meaning.
**Coding-agent analogy:** Agents with different tools/prompts need only a shared interface schema, not shared understanding.
**Where the analogy fails:** Models share training; "incommensurability" is weaker.
**Concrete experiment:** Minimal handoff schema (files, contract, test) vs free-text handoff; compare rework.

### F5. Wegner transactive memory
**Source:** Wegner (1987), chapter in Theories of Group Behavior; Wegner (1995), Social Cognition 13(3) (search result, https://en.wikipedia.org/wiki/Transactive_memory; verified: N).
**Reliability:** Medium-high.
**Status:** established.
**Plain-language concept:** A group knows more because members know who knows what. Directory/allocation/retrieval terms appear to come from the 1995 paper (secondary source).
**Coding-agent analogy:** A who-owns-what index for agents.
**Where the analogy fails:** Agents lose memory between sessions unless written down.
**Concrete experiment:** Add an ownership index; measure time to find the right owner/file.

### F6. Hutchins distributed cognition
**Source:** Hutchins, Cognition in the Wild (MIT Press, 1995). https://mitpress.mit.edu/9780262581462/cognition-in-the-wild/ (search result only; verified: N).
**Reliability:** High.
**Status:** established.
**Plain-language concept:** Cognition lives in people plus artifacts (charts, instruments).
**Coding-agent analogy:** Tests, ledgers, and CI are the shared cognitive artifacts.
**Where the analogy fails:** Navigation crews are trained together over years.
**Concrete experiment:** Remove the shared ledger from one arm; measure repeated work.

### F7. Edmondson psychological safety
**Source:** Administrative Science Quarterly 44(2), 350-383, 1999, DOI 10.2307/2666999. https://dash.harvard.edu/entities/publication/13a7b031-0fdd-45ec-a7e0-2b80e2bc679f (search result only; verified: N).
**Reliability:** High (51 teams).
**Status:** established for humans.
**Plain-language concept:** Teams where speaking up is safe learn more.
**Coding-agent analogy:** Agents must be able to report "blocked/uncertain" without penalty; sycophantic agreement is the failure.
**Where the analogy fails:** Agents do not fear social cost; failure is training-induced agreeableness.
**Concrete experiment:** Reward-free "I'm blocked" channel; count escalations vs silent wrong completions.

### F8. Weick sensemaking
**Source:** Weick, ASQ 38, 628-652, 1993, DOI 10.2307/2393339. https://www.cs.unibo.it/~ruffino/Letture%20TDPC/K.%20Weick%20-%20The%20collapse%20of%20sensemaking.pdf (search result only; verified: N).
**Reliability:** Medium (single case).
**Status:** interpretation.
**Plain-language concept:** Organizations unravel when role structure and sensemaking collapse together.
**Coding-agent analogy:** When the plan and the agent roles both go stale, runs drift.
**Where the analogy fails:** Life-or-death stakes absent.
**Concrete experiment:** Detect stale plan (diff vs plan) and force a re-plan; compare drift.

### F9. Nonaka SECI
**Source:** Organization Science 5(1), 14-37, 1994, DOI 10.1287/orsc.5.1.14. https://www.lamsade.dauphine.fr/~giard/Organization_Science_Nonaka94.pdf (search result only; verified: N).
**Reliability:** Medium (influential, hard to test).
**Status:** interpretation.
**Plain-language concept:** Knowledge converts between tacit and explicit via socialization, externalization, combination, internalization.
**Coding-agent analogy:** Session learnings externalized into docs/tests, combined, internalized into next prompts.
**Where the analogy fails:** Model weights do not update from sessions.
**Concrete experiment:** Compare runs with and without an externalized lessons file; measure repeat-mistake rate.

---

## Final sections

### (1) Ranked top-8 ideas for orchestration/collaboration
1. Gate fan-out by decomposability and estimated size (B2, B4); default to single agent.
2. Declare scopes up front and partition work; order merges producer-to-consumer (C3, F3).
3. Post-merge verification gate: run tests alone and combined (C2).
4. Machine-checkable contract/interface file with change notices to peers (C2, B3, F4).
5. Central verifier as the only error damper (B2: no central verification propagates errors).
6. Shared ledger/blackboard file with who-owns-what and failing-test signals (E1, E2, F5, F6).
7. Sampling plus test-based selection instead of debate (D4).
8. Ablate every role; keep roles that tie to a verification loop (D1, D5).

### (2) Prior-art warnings
- Parallel scope partition (Nerveplane/NP-Bench), claim-plane admission, and CodeCRDT already exist; do not claim novelty.
- Blackboard, stigmergy, and self-organizing agent teams are published; positioning must be about the coding repo substrate and evidence.
- Many 2026 results are preprints by tool authors on their own benchmarks.
- MAST and the scaling study already provide failure/threshold vocabulary; reuse it.

### (3) What I could not verify
- Search-result-only sources (marked N): CooperBench numbers, Managed Agents docs, Claim Plane, role-specialization papers, SelfOrg, TheBotCompany, the 4.4x/17.2x/45% figures in the scaling study, all F3-F9 URLs.
- The 19.8%/41.7% same- vs cross-agent conflict rates (GitHub-issue summary only).
- Primary books (Brooks, Galison, Hutchins, Wegner 1987/1995) not opened.
- I did not open full texts of MetaGPT/ChatDev/AutoGen to extract benchmark numbers.
- The Anthropic Claude Code depth (3) and concurrency (20) limits come from search text only.
