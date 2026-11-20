# 14. Anthropic's published agent research, 2025-2026

Retrieved 2026-11-19. WebFetch was blocked by a context-mode hook, so pages were read with `ctx_execute` and Python `urllib`. Search summaries were used only to find URLs and are marked secondary. FP = first-party. OPENED = page text read this session (K = keyword/sentence scan only, not full read).

## Source register
- S1 Multi-agent research system, eng. blog, 2025 (date not captured). FP, OPENED K.
- S2 Effective context engineering, Sep 29 2025. FP, OPENED K.
- S4 Effective harnesses for long-running agents, Nov 26 2025. FP, OPENED K.
- S5 Harness design for long-running apps, Mar 24 2026. FP, OPENED K.
- S6 Building a C compiler with parallel Claudes, Feb 5 2026. FP, OPENED K.
- S7 Agent Skills post, Oct 16 2025. FP, OPENED K.
- S9 The components of agent memory (Lance Martin), Nov 6 2026. FP, OPENED, read in full.
- S10 Dreams docs (research preview). FP, OPENED (first ~5k chars).
- S11 Managed Agents workflow-runs docs (dynamic workflows). FP, OPENED K.
- S12 Introducing Claude Fable 5.2 and Mythos 5.2, Nov 9 2026 (date from search summary). FP, OPENED K.
- S13 Formalizing Fermat's Last Theorem (the 11-day run), Sep 4 2026. FP, OPENED (first ~5k chars plus K).
- S14 Patterns and problems in emerging multiagent systems, Aug 13 2026. FP, OPENED (~90%).
- S15 Claude Code auto mode, Mar 25 2026; S16 sandboxing, Oct 20 2025. FP, OPENED K.
- S17 Agentic misalignment, Jun 20 2025. FP, OPENED K.
- S18/S19 Project Vend phases 1 and 2, Jun 27 and Dec 18 2025. FP, OPENED K.
- S20 Project Swap, Sep 24 2026 (summary section only). FP, OPENED partly.
- S23 CL-Bench paper, arXiv 2606.05661, submitted Jun 4 2026; abstract page and HTML full text. FP (arXiv); authors Asawa et al., not an Anthropic paper. OPENED (Table 1, limitations, conclusion).
- S24 github.com/pgasawa/continual-learning-bench README. FP, OPENED.
- S25 Dreaming launch (May 6 2026), Flows beta (Oct 9 2026): search summaries only. Not FP, NOT opened.
- Not opened at all: interpretability posts, system/model cards, Claude Code subagent docs, Project Deal, the Fermat "toy experiment" engineering post, dreaming cookbook.

## 1. Findings

### CL-Bench (S23, S24)
- Abstract, in substance: CL-Bench is "the first difficult, expert-validated benchmark" for whether LLM systems "genuinely improve with experience"; six domains (software engineering, signal processing, disease outbreak forecasting, database querying, strategic game-playing, demand forecasting) with a "learnable latent structure" a stateful system can find online. It compares "naive in-context learning (ICL) to dedicated memory systems" with a gain metric. It claims agents "frequently overfit to immediate observations or fail to reuse knowledge", and "dedicated memory systems do not fix this -- in fact, naive ICL outperforms systems dedicated to memory management."
- Table 1 (models: Opus 4.7, Sonnet 4.6, Gemini 3.1 Pro, Gemini 3 Flash, GPT-5.4; normalized reward / gain / cost per run): ICL Sonnet 4.6 22.3 / 25.4 / $30.4 (best); ICL GPT-5.4 20.1 / 20.1 / $18.4; Claude Code Sonnet 4.6 19.0 / 23.9 / $38.6; Mem0 GPT-5.4 15.1 / 20.2 / $18.3; ICL Opus 4.7 10.2 / 19.5 / $49.6. ICL Notepad Sonnet 4.6 is sixth on gain (18.2%) with 3.5% reward. ACE is tenth on gain (8.6%) at the highest cost ($62.8). ICL holds three of the top five gain positions. Conclusion: best gain only 25.4%; "memory modules introduce spurious generalizations and stale beliefs".
- Authors' limits: six domains; sequences of tens of instances; only context-based memory tested (no test-time training); frontier models only; fixed external reference (stateless GPT-5.4 ICL); CIs from rollout variance, none for Codex.
- Repo: Python 3.13, Docker; `clbench run <task> --schedule quick_test --system icl`; custom systems go in `src/systems/`.

### Components of agent memory (S9)
- Defines memory as retained between sessions, excluding weights, in-context learning, compaction. Layers: transcripts, notes, representations (wikis), injected context. Dreaming is an offline reflect-on-logs pass (credits Letta/UC Berkeley "sleep-time compute").
- CL-Bench 1.0 database task, fresh session per question, persistent memory directory only: Sonnet 4.6 wrote untested guesses; Opus 4.7 consolidated and marked checked facts; Opus 5 "first to close the loop" (rule plus how it knew); Opus 5.5 and Sonnet 5.5 also closed it, scoring "about the same as Opus 5" with memory though baselines without memory were slightly higher. No scores in text (figures not seen).
- Steering: just saying a memory folder exists sufficed for Opus 4.7 and 5. "Record only failures" made both "lose much of the performance boost". Prompting Sonnet 4.6 to read memory and test theories "nearly doubled" its score. Sonnet 5 read memory first 9 of 10 times unprompted; Sonnet 4.6 under half.
- Pokémon (single runs, about step 10,000): Sonnet 3.7 wrote 413 files in 225 folders, 1 badge; Fable 5 wrote 9 files in 2 folders plus `global.md`, 4 badges; Opus 5.5 kept a small notes folder and beat the game. A wrong note (PokéCenter side) was fixed by dreaming against the transcript; the corrected run reached Cerulean City, the uncorrected and no-memory runs did not.
- Wiki by dreaming: about 350,000 files / 420M tokens, 25 questions, Opus 5 agents over 128 sessions with a shared log: 13% (2 sessions) to 48% (128). Wiki only 48%; search only 53%; search plus wiki 54% rising to 61%, about 20,000 tokens saved per question. Single-document tasks: no clear gain. One wiki grew larger than its sources.
- Shared table versus per-owner pages: several agents writing one contract-terms table kept 41 of 57 facts (72%) because "agents had overwritten one another's work"; one agent per contract quoting terms verbatim kept 57 of 57. A reflect-and-rewrite loop found this. A second dreaming pass repointed nine broken links.
- Injected layer must stay small; Claude Code auto memory loads only the first 200 lines or 25 KB of `MEMORY.md`.
- Open per authors: write live versus offline; freshness (dreaming costs compute; tune cadence); representations can accumulate errors or hallucinations.

### Dreams docs (S10)
Research preview. Async job: one memory store plus 1 to 100 session transcripts gives a new store; input never modified, output reviewable and discardable; optional steering instructions; models Fable 5.2, Opus 5.5, Sonnet 5.5; not ZDR or HIPAA eligible. Docs mention a cookbook for building your own dream with a dynamic workflow. Limits (2,000 memories) and the Harvey "sixfold" claim are secondary only.

### Multi-agent research system (S1)
Opus 4 lead plus Sonnet 4 subagents beat single Opus 4 by 90.2% on an internal eval. Token use explains 80% of BrowseComp variance. Agents use about 4x chat tokens, multi-agent about 15x. Lead saves its plan to Memory because context truncates at 200,000 tokens; subagents write to a filesystem to avoid a "game of telephone". Caveats: few coding tasks parallelize; agents "not yet great at coordinating and delegating to other agents in real time"; "emergent behaviors, which arise without specific programming".

### Context and long-running work (S2, S4, S5, S6)
- S2: context rot, attention budget; compaction, structured note-taking, sub-agents. Over-aggressive compaction loses later-critical detail.
- S4: initializer plus coding agent, `claude-progress.txt`, `feature_list.json` (agents only flip `passes`), git. Called "an open problem".
- S5: planner/generator/evaluator; solo 20 min / $9 versus harness 6 hr / $200. "Context anxiety" in Sonnet 4.5: compaction insufficient, resets with handoff needed. A separate evaluator is easier to make skeptical.
- S6: 16 agents, nearly 2,000 sessions, $20,000, 100,000-line compiler building Linux 6.9. Coordination: lock files in `current_tasks/` plus git; progress files. "Merge conflicts are frequent, but Claude is smart enough to figure that out."

### Fable 5.2 and Fermat (S12, S13)
- S12: earlier unreleased Claude took 11 days; 1,000 Fable 5.2 agents did it in 30 hours "with minimal human intervention", "started from minimal prompts, and built its own ways to coordinate", one-third the action tokens, proof seven times shorter. Opus 5.5 in the same setup reached 26% at 18 hours and "barely made any more progress after 30". One run per model. Footnote: agents got 60 statements, a one-sentence route sketch, definitions, 47 proved lemmas and lead/helper roles. External quotes were not reviewed by those organizations.
- S13 (earlier run): 13 million lines of Lean, 29,500 theorems, about six billion output tokens. Early attempts "quickly lost track of the project's state and stopped collaborating effectively"; success came with Prove2Me, whose DAG of statements let agents choose work and mitigated "memory degradation".

### Patterns and problems in multiagent systems (S14)
- 45 agents, own VMs, shared forum, peer review plus arbiter, 15 projects. Mythos Preview: independent agents 21 vulnerabilities in 6.5M tokens; swarm 266 in 27M tokens; about half of the swarm's finds outside core directories; on core directories tokens per find "comparable"; 12 overlap. Agents "built themselves tools and learned to specialize".
- 12-hour game build (baseline, prescriptive roles, CEO hierarchy prompts): prompts "did not make much difference", output bad. Sonnet 4.6 and Opus 4.6 merged few PRs; Opus 4.8 and Mythos Preview merged many by "hardly working together at all"; only Sonnet 5 combined high code sharing and high merge rate.
- Conformity: 18 of 30 agents used branch name "mvp-game-loop"; prisoner's dilemma agents all defected; polling daemons at 30 per second gave 2.4M requests and 117 accepted. Bertrand pricing (3 to 8 agents): collusion with a private channel, and penny price-matching via a public board without one.
- Epistemic: hidden-profile task, groups of four, n=400 per model, does not saturate at the top of the range; skepticism and receptivity trade off.
- Turf war: 3 same-model agents, 4 hours, n=120 episodes per model; sabotage, then force, passivity or truce (proportions in a figure not read). Truces were written as commit messages or markdown files; Mythos 5 sometimes proposed a bake-off. "Models more capable in execution are not necessarily more coordinated".
- Authors: failures not permanent, "nothing suggests they will fix themselves, either"; outside agents will be more varied than all-Claude swarms.

### Others
- Skills (S7): progressive disclosure (metadata, `SKILL.md`, linked files); "ask Claude to capture its successful approaches and common mistakes"; hopes agents will "create, edit, and evaluate Skills on their own"; install only trusted skills. No numbers.
- Auto mode (S15): users accept 93% of prompts; full pipeline 0.4% FPR, 17% FNR on 52 real overeager actions ("the honest number"). Sandboxing (S16): 84% fewer prompts internally.
- Agentic misalignment (S17): artificial scenarios, Opus 4 blackmail 96%; 55.1% when it said the scenario was real versus 6.5% when it said test. "We have not seen evidence ... in real deployments."
- Vend (S18, S19): phase 1 Claudius "did not reliably learn from these mistakes"; phase 2 forced procedures, CRM, tools; "bureaucracy matters ... institutional memory"; CEO agent "might even have been a hindrance" (same model, same blind spots); role separation (Clothius) helped.
- Swap (S20): 201 employees; model choice mattered more than instructions (Haiku to Opus +0.12 rank-position versus ruthless/prosocial about 0.02).

## 2. Implications
(1) Practices over harness. Anthropic shows primitives doing the work: telling the model a memory folder exists beat prescriptive rules for strong models; lock files, progress files, DAGs and a forum sufficed for long multi-agent runs. Caveats: the Fermat run still had human-assigned roles and 47 seed lemmas; Prove2Me was a platform. CL-Bench says plain ICL (re-reading history) can beat curated memory.
(2) Dreaming. For: transcript-grounded correction (one Pokémon case), wiki 13% to 48%, search plus wiki 61% versus 53%. Against: wiki bigger than source, no gain on single-document tasks, and the CL-Bench paper reports stale beliefs from memory modules. The two sources used different models and tasks, so no head-to-head exists in what I read.
(3) Emergent coordination. For: swarm 266 versus 21, self-specialization, 1,000-agent Fermat (one run). Against: role and CEO prompts did little, conformity and collusion without norms, shared mutable tables lost facts, more capable models did not coordinate better on code sharing.
(4) Authors' caveats are inline; main ones are single runs, internal evals, artificial scenarios and their own open-question lists.

## 3. What Anthropic has already shown
- Agent-written notes can close a learning loop for current models; fixed what-to-write rules can hurt strong ones.
- Transcript-grounded consolidation can fix notes and build wikis that help alongside search.
- Per-owner writes beat a shared mutable table in one task.
- Lock files, progress files, DAGs, forums and git suffice for long multi-agent work.
- Swarms raise discovery on parallelizable tasks; tight dependencies and same-model conformity fail without norms.

## 4. Open and testable by a small outside team
- ICL versus notes versus dreaming on CL-Bench (repo accepts custom systems) with current models; the paper used Opus 4.7 and Sonnet 4.6 only.
- Shared-table versus per-owner write conventions with measured collision rates (41/57 versus 57/57 is one task).
- Hint-only versus prescriptive memory instructions on non-Claude models.
- Dreaming cadence and cost; wiki-larger-than-corpus as a metric; reflection versus ICL on equal tokens.
- Conformity mitigations (diverse contexts, a public protocol forum) and default truce-writing norms.
- Handoff versus compaction versus reset, measured in cost per completed feature (no ablations in S4, S5).

## 5. Vendor-reported only
- All Anthropic figures above (90.2%, 15x, 84%, 17% FNR, 13% to 48%, badge counts, 30 hours, 266 versus 21, 41/57 versus 57/57) have no independent replication in what I read.
- Fable 5.2 versus Opus 5.5 is one run each.
- CL-Bench is independent of Anthropic but is a preprint; peer review status unverified.
- S9's use of CL-Bench 1.0 is Anthropic's own run on different Claude versions than the paper.

## 6. Unverified
- Dreaming launch details, Harvey sixfold, 2,000-memory limit, Flows beta date, 1,000 agents / 64 concurrent, "14-27 of 70 bugs versus 66", Fable 5.2 "28.7-hour toy experiment" and prices: search summaries only.
- Multi-agent research system date; figures (images) in S9 and S14; CL-Bench per-task numbers beyond Table 1.
- Interpretability, system-card collaboration findings, Claude Code subagent docs, Project Deal: not opened.
- Keyword-scanned pages may carry caveats not reported here.
