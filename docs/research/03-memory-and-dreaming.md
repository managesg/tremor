# 03 - Memory, dreaming, correction, shared memory for agents

Date: 2026-11-19. Method: web searches only. "Verified Y" below means the URL appeared in search results and the search summary matched the citation. NO page was opened in full, so details such as numbers come from search summaries (some secondary). "UNVERIFIED (from memory)" marks anything not seen. Papers dated after my training (2026 arXiv IDs, Anthropic Nov 2026 post) were seen only via search snippets; treat as leads.

Experiment convention: "control" = compute-matched control (same tokens/LLM calls spent on a no-memory retry or random/neutral rewrite).

---

## A. Cognitive and RL foundations

### 1. Complementary Learning Systems (1995)
**Source:** McClelland, McNaughton, O'Reilly (1995), Psychological Review 102(3):419-457. https://stanford.edu/~jlmcc/papers/McCMcNaughtonOReilly95.pdf. Verified Y.
**Reliability:** High (foundational, heavily cited); model-based theory, not direct proof for LLMs.
**Status:** established (for brains); interpretation (for agents).
**Plain-language concept:** Learn fast and specifically in one store (hippocampus), learn slowly and structurally in another (neocortex); replay the fast store into the slow one, interleaved, to avoid overwriting old knowledge.
**Coding-agent analogy:** Session log/episodes = fast store; curated CLAUDE.md/wiki/skills = slow store; a consolidation job = replay.
**Where the analogy fails:** The slow store here is editable text, not weights; no catastrophic interference mechanism, so the "must interleave" argument does not directly apply. Text can be rewritten in one shot (and corrupted in one shot).
**Concrete experiment:** Same 50 recorded sessions; (a) consolidate in one batch, (b) interleaved small batches with old rules retained, (c) no consolidation. Metric: pass rate on held-out tasks that need old rules vs new rules. Control: same token spend on summarising without rule extraction.

### 2. CLS updated
**Source:** Kumaran, Hassabis, McClelland (2016), "What Learning Systems do Intelligent Agents Need? Complementary Learning Systems Theory Updated", Trends Cogn Sci 20(7):512-534. https://pubmed.ncbi.nlm.nih.gov/27315762/. Verified Y.
**Reliability:** High.
**Status:** established (theory); interpretation for LLM agents.
**Plain-language concept:** Replay is goal-weighted (not uniform), hippocampal traces can support some generalisation, and cortex can learn fast when new info fits existing structure.
**Coding-agent analogy:** Replay should prioritise sessions tied to goals/failures; new facts that fit an existing schema can be filed directly.
**Where the analogy fails:** Brain replay has no analogue of "an LLM wrote the memory, possibly wrongly".
**Concrete experiment:** Replay selection A/B on a fixed session set: uniform vs failure-and-goal-weighted selection into the same distillation prompt, same token budget. Metric: downstream task pass rate; control: random selection with equal tokens.

### 3. Sleep and consolidation evidence
**Source:** Rasch & Born (2013), "About Sleep's Role in Memory", Physiological Reviews 93(2):681-766. https://pubmed.ncbi.nlm.nih.gov/23589831/. Verified Y.
**Reliability:** High review; mechanisms still debated.
**Status:** established (sleep benefits memory, active system consolidation); the exact mechanism is contested.
**Plain-language concept:** Sleep, especially slow-wave sleep, actively reorganises memories, not just protects them.
**Coding-agent analogy:** Offline passes between sessions are legitimate, but only if they change something measurable.
**Where the analogy fails:** "Dreaming" is a metaphor; LLM offline passes have no evidence base in this review. Do not cite neuroscience as evidence the agent job works.
**Concrete experiment:** None needed beyond experiments 1/2; use the metaphor only for naming.

### 4. Bartlett schemas, reconstructive memory
**Source:** Bartlett (1932), Remembering. Seen only via secondary summaries (e.g. https://en.wikipedia.org/wiki/Frederic_Bartlett). Verified N for primary; secondary Y.
**Reliability:** Medium (classic, detail partly replicated, later work disputes how much distortion is typical).
**Status:** established (reconstruction) / interpretation (analogy).
**Plain-language concept:** Remembering rebuilds from fragments plus expectations, so recalls drift toward the schema.
**Coding-agent analogy:** Summaries of summaries drift toward the agent's prior; consolidated notes can "regularise" a surprising fact into a usual one.
**Where the analogy fails:** Drift here is measurable against the raw log, which humans lack.
**Concrete experiment:** Chain-summarise 20 sessions 1, 2, 3 times; count facts (from a seeded list of 30 unusual facts) retained exactly. Control: same chain with extractive (verbatim-quote) compression. Deterministic string match.

### 5. Ebbinghaus forgetting and ACT-R decay
**Source:** Murre & Dros (2015), PLOS ONE 10(7):e0120644, https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0120644; Anderson & Schooler (1991), Psychological Science 2:396-408, seen via https://www.ai.rug.nl/~niels/publications/taatgenLebiereAnderson.pdf. Verified Y (replication and secondary; Anderson & Schooler primary not opened).
**Reliability:** High for replication; ACT-R d=0.5 is a convention, not a law.
**Status:** established (power-law usage/recency); interpretation (as agent TTL).
**Plain-language concept:** Odds an item is needed again fall as a power of time since use, and rise with use count (B = ln sum t^-d).
**Coding-agent analogy:** Rank notes by recency+frequency of actual retrieval-and-use, not creation time; expire unused ones.
**Where the analogy fails:** Code facts can be wrong without age (a path renames overnight); decay handles relevance, not truth.
**Concrete experiment:** Replay 200 past retrieval events; compare ranking by (a) recency only, (b) ACT-R base-level with d in {0.3,0.5,0.7}, (c) random. Metric: fraction of retrieved notes later actually used. Deterministic, no LLM.

### 6. Dyna
**Source:** Sutton (1991), "Dyna, an integrated architecture for learning, planning, and reacting", SIGART Bulletin 2(4):160-163. https://dl.acm.org/doi/10.1145/122344.122377. Verified Y.
**Reliability:** High.
**Status:** established (RL).
**Plain-language concept:** Learn a model from real experience, then spend idle compute updating the policy using simulated experience from that model.
**Coding-agent analogy:** Offline "dream" = replay or imagined variations of past tasks to refine playbooks. Sutton's paper notes learned models can be wrong.
**Where the analogy fails:** Agent has no cheap simulator; imagined experience from an LLM is itself unverified.
**Concrete experiment:** Dyna-style: for failed tasks, generate K variations in a sandbox with executable tests (real verifier), distil rules only from passing/failing runs. Control: same K runs without distillation (pure retries).

### 7. Dreamer / world models
**Source:** Hafner et al., "Dream to Control", ICLR 2020, arXiv:1912.01603. https://arxiv.org/abs/1912.01603. Verified Y.
**Reliability:** High in RL control; small relevance to text agents.
**Status:** established (RL); speculative as an analogy.
**Plain-language concept:** Train the policy inside a learned latent world model ("imagination").
**Coding-agent analogy:** A repo/test-based "world model" of the codebase to rehearse changes.
**Where the analogy fails:** No learned dynamics model for codebases; the real environment (tests) is cheap and exact, so imagination adds little.
**Concrete experiment:** Skip; use real sandbox replay (card 6) instead.

### 8. Experience replay
**Source:** Schaul et al., "Prioritized Experience Replay", ICLR 2016, arXiv:1511.05952. https://arxiv.org/abs/1511.05952. Verified Y. (Search summary: beat uniform replay on 41 of 49 Atari games.)
**Reliability:** High within Atari/DQN.
**Status:** established (RL).
**Plain-language concept:** Replay surprising transitions more often.
**Coding-agent analogy:** Prioritise sessions with high surprise (test failures, user corrections) for consolidation.
**Where the analogy fails:** No gradient; "TD error" proxy must be invented (e.g. user correction count).
**Concrete experiment:** Same as card 2, with priority = number of user corrections.

---

## B. LLM agent memory systems

### 9. Generative Agents
**Source:** Park et al., UIST 2023, arXiv:2304.03442. https://arxiv.org/pdf/2304.03442. Verified Y.
**Reliability:** Medium (sandbox demo, 25 agents, human-rated believability, not task success).
**Status:** established (as design); interpretation (that reflection helps tasks).
**Plain-language concept:** Memory stream, retrieval by recency+importance+relevance, periodic reflections that synthesise higher-level notes.
**Coding-agent analogy:** Session log + scored retrieval + diary/reflect (claude-diary says it takes inspiration from this).
**Where the analogy fails:** Evaluated on believability, not correctness. Retrieval weights are hand-set.
**Concrete experiment:** Retrieval scoring ablation (recency / importance / relevance / all) on a fixed Q&A set over your own session logs, exact-match answers.

### 10. Reflexion
**Source:** Shinn et al., NeurIPS 2023, arXiv:2303.11366. https://arxiv.org/abs/2303.11366. Verified Y.
**Reliability:** Medium. Reported +22% AlfWorld, +20% HotPotQA, +11% HumanEval; search summaries say WebShop gain was small and that independent work finds reflection can hurt.
**Status:** established (works in some tasks); contested generally.
**Plain-language concept:** After a failure, write a verbal lesson and put it in the next attempt's context.
**Coding-agent analogy:** Post-failure note ("tests failed because X; next time Y").
**Where the analogy fails:** Needs an external pass/fail signal; the lesson can be wrong and then persists.
**Concrete experiment:** On 100 repo tasks with tests: (a) retry blind, (b) retry with test output only, (c) retry with LLM reflection. Equal retry count. Metric: pass@2. Control (a)+(b) isolate the reflection text.

### 11. Voyager
**Source:** Wang et al., arXiv:2305.16291. https://arxiv.org/abs/2305.16291. Verified Y.
**Reliability:** Medium (Minecraft; ablation shows skill library matters).
**Status:** established in domain.
**Plain-language concept:** Store verified executable code as reusable skills; retrieve by embedding.
**Coding-agent analogy:** Skills/scripts promoted only after they pass; procedural memory beats prose memory.
**Where the analogy fails:** Skills drift as APIs change; Minecraft APIs are stable.
**Concrete experiment:** Promote a script into the skill library only after N passes; measure tool-call count on repeated tasks vs a prose-only note. Deterministic.

### 12. MemGPT / Letta
**Source:** Packer et al., arXiv:2310.08560. https://arxiv.org/abs/2310.08560. Verified Y. Letta docs on shared blocks and sleeptime agents seen at https://docs.letta.com/v1-sdk/memory/shared-memory (Verified Y, snippet only).
**Reliability:** Medium (paper evals are small; product docs are vendor).
**Status:** established (design).
**Plain-language concept:** OS-style tiers: small in-context "core" blocks edited by the agent via tools; larger external archive.
**Coding-agent analogy:** Always-loaded index (MEMORY.md) plus on-demand topic files. Letta advises one owner agent for heavy edits to shared blocks, others append.
**Where the analogy fails:** Agent-edited core memory can overwrite itself badly.
**Concrete experiment:** Replay a conflict log: two writers editing the same block, count lost updates under (a) last-write-wins, (b) owner+append-only.

### 13. Sleep-time compute
**Source:** Lin et al. (Letta/Berkeley), arXiv:2504.13171. https://arxiv.org/abs/2504.13171. Verified Y.
**Reliability:** Medium. Reported: ~5x less test-time compute for same accuracy, up to +13%/+18% with more sleep compute, 2.5x lower per-query cost when amortised; at highest test-time budgets the baseline caught up slightly; gain grows with query predictability.
**Status:** established on synthetic stateful tasks; interpretation for coding agents.
**Plain-language concept:** Pre-compute inferences about a context offline so queries are cheaper.
**Coding-agent analogy:** Offline pass that pre-answers likely questions about a repo (architecture notes).
**Where the analogy fails:** Needs predictable queries; repos change.
**Concrete experiment:** Compute-matched: offline budget B tokens spent on pre-analysis vs the same B tokens added to test-time thinking on the same tasks. Metric: pass rate and total tokens.

### 14. A-MEM
**Source:** Xu et al., arXiv:2502.12110. https://arxiv.org/abs/2502.12110. Verified Y (via alphaxiv/arxiv results).
**Reliability:** Medium-low (benchmark gains on LoCoMo-type tasks; critiques note embedder dependence and silent rewriting of memories).
**Status:** interpretation.
**Plain-language concept:** Zettelkasten notes with tags and links; new notes can update old notes.
**Coding-agent analogy:** Linked wiki pages that get edited on new evidence.
**Where the analogy fails:** Silent edits destroy provenance; no audit trail.
**Concrete experiment:** Same notes with (a) in-place update, (b) supersede-with-link (old kept). Seeded wrong update; measure time-to-detect and recoverability.

### 15. Mem0
**Source:** Chhikara et al., arXiv:2504.19413. https://arxiv.org/pdf/2504.19413. Verified Y (numbers via a Medium review, not the paper).
**Reliability:** Low-medium (vendor paper; reported latency/token savings vs full context, comparison to Zep contested by others).
**Status:** interpretation.
**Plain-language concept:** Extract, consolidate (add/update/delete/noop), retrieve salient facts.
**Coding-agent analogy:** Fact-extraction after each session.
**Where the analogy fails:** Chat-preference facts differ from code facts that need file/commit anchors.
**Concrete experiment:** ADD/UPDATE/DELETE/NOOP decisions on 100 seeded contradictory facts; exact-match against a gold final state.

### 16. Zep / Graphiti
**Source:** Rasmussen et al., arXiv:2501.13956. https://arxiv.org/abs/2501.13956. Verified Y.
**Reliability:** Medium-low (vendor; DMR benchmark criticised; 94.8% vs MemGPT 93.4% per search).
**Status:** interpretation; bi-temporal design is sound.
**Plain-language concept:** Temporal knowledge graph; contradicted facts get an invalid_at timestamp, not deleted; tracks event time and ingestion time.
**Coding-agent analogy:** Facts about a repo with valid-from/valid-to and source commit.
**Where the analogy fails:** Heavy LLM extraction cost; a git log already is a bi-temporal store.
**Concrete experiment:** Compare "facts with valid_to + commit anchor" vs flat notes on 50 questions whose answers changed across commits (knowledge-update class of LongMemEval).

### 17. Anthropic memory tool, context editing, context engineering
**Source:** https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool ; https://platform.claude.com/docs/en/build-with-claude/context-editing ; https://www.anthropic.com/research/effective-context-engineering-for-ai-agents (search showed this and an engineering URL; the engineering URL was not itself in results). Verified Y (snippets).
**Reliability:** Vendor docs; accurate on API; performance claims (+39% memory+context editing, +29% editing alone) are the vendor's own blog numbers, seen via secondary summary.
**Status:** established (API); interpretation (benefit).
**Plain-language concept:** Client-side file directory (view/create/str_replace/insert/delete/rename) that persists; context editing clears old tool results; compaction summarises; just-in-time retrieval over pre-loading.
**Coding-agent analogy:** Directly the current file-based memory.
**Where the analogy fails:** The client implements storage, so provenance, ACLs and TTL are your job; the tool has none.
**Concrete experiment:** Long task with clearing on/off and memory on/off (2x2), same token cap; measure completion.

### 18. Anthropic "components of agent memory" and dreaming
**Source:** https://www.anthropic.com/research/components-of-agent-memory (Lance Martin, 2026-11-06 per search summary; details beyond title from secondary posts, e.g. https://the-decoder.com/anthropic-says-the-key-to-agent-memory-is-knowing-what-to-forget-not-how-much-to-store/); product: https://claude.com/resources/articles/new-in-claude-managed-agents (Dreaming, research preview, announced 2026-05-06). Verified Y (snippets; primary not opened).
**Reliability:** Vendor research, own benchmarks; numbers below are secondary.
**Status:** interpretation / vendor claim.
**Plain-language concept:** A separate job re-reads memory plus raw transcripts, fixes wrong notes, builds linked wiki pages, keeps the always-loaded layer short. Reported: Pokemon test 413 files vs 10 files; wiki quality 13% to 48% as dreaming scaled 2 to 128 sessions; a dream reads 1-100 sessions and writes a NEW store, original untouched; "tell it what memory is for, not how to use it."
**Coding-agent analogy:** The "dream" pass this project wants.
**Where the analogy fails:** Output is graded on vendor criteria; cost and delay acknowledged by the vendor; no independent replication seen.
**Concrete experiment:** Dream pass vs equal-token "re-summarise with no transcripts" control vs no pass, on a seeded-wrong-note set (inject 10 false notes, 10 stale notes); metric = false notes removed, true notes preserved, downstream pass rate.

### 19. Claude Code auto memory and auto dream
**Source:** https://code.claude.com/docs/en/memory (official, Verified Y snippet): CLAUDE.md plus auto memory in ~/.claude/projects/<project>/memory/, MEMORY.md first 200 lines or 25KB loaded. Auto Dream: third-party descriptions only (https://claudefa.st/blog/guide/mechanics/auto-dream, https://www.mindstudio.ai/blog/what-is-claude-code-autodream-memory-consolidation); sources disagree on backups and say some details come from leaked code. Auto Dream official documentation: NOT found.
**Reliability:** Official for memory; low for Auto Dream details.
**Status:** established (auto memory); speculative (Auto Dream internals).
**Plain-language concept:** Background sub-agent dedupes, converts relative dates to absolute, prunes stale entries on a timer/session count.
**Coding-agent analogy:** The local baseline to beat.
**Where the analogy fails:** Per-user local; no shared/team semantics.
**Concrete experiment:** Snapshot memory dir, run the pass, diff; count dropped facts vs gold list.

### 20. claude-diary
**Source:** https://github.com/rlancemartin/claude-diary and https://rlancemartin.github.io/2025/12/01/claude_diary/. Verified Y (snippets).
**Reliability:** Practitioner repo, no benchmark.
**Status:** interpretation.
**Plain-language concept:** /diary writes per-session entries (decisions, preferences, PR feedback); /reflect reads entries and proposes CLAUDE.md edits, kept manual so a human reviews them.
**Coding-agent analogy:** Append-only logs plus human-gated promotion.
**Where the analogy fails:** Single user; no conflict handling.
**Concrete experiment:** Count how many proposed rules a reviewer accepts per 20 entries, and re-violation rate of accepted vs rejected rules.

---

## C. Poisoning, correction, belief revision

### 21. AgentPoison
**Source:** Chen et al., arXiv:2407.12784. https://arxiv.org/pdf/2407.12784. Verified Y.
**Reliability:** Medium-high (peer-style, public code); setting is RAG/memory retrieval agents.
**Status:** established (attack feasibility).
**Plain-language concept:** A few optimised poisoned entries plus a trigger in the query hijack retrieval; search summary reports success at very low poison rates.
**Coding-agent analogy:** A memory note from an untrusted web page or PR comment steers later sessions.
**Where the analogy fails:** Needs a trigger crafted against the retriever; plain-text file memory read in full is a different surface (prompt injection).
**Concrete experiment:** Insert 1-3 poisoned notes in a 200-note store; measure how often the agent follows them under (a) no provenance, (b) provenance-tagged untrusted notes quarantined.

### 22. MINJA
**Source:** Dong et al., arXiv:2503.03704. https://arxiv.org/abs/2503.03704. Verified Y.
**Reliability:** Medium (follow-up 2601.05504 says original used idealised settings).
**Status:** established (feasibility); degree contested.
**Plain-language concept:** Attacker writes to memory via ordinary queries only; reported >95% injection success, >70% attack success; filters like Llama Guard ineffective. Recommends isolation, authentication, memory management.
**Coding-agent analogy:** Any user or tool output that the agent later summarises into memory is a write channel.
**Where the analogy fails:** Depends on memory being auto-written from user-controlled text.
**Concrete experiment:** Red-team: attacker-controlled issue text; count promotions to durable memory under (a) auto-write, (b) human-gated promotion.

### 23. AGM belief revision
**Source:** Alchourron, Gardenfors, Makinson (1985), J Symbolic Logic 50:510-530; overview https://plato.stanford.edu/entries/logic-belief-revision/. Verified Y (SEP; primary not opened).
**Reliability:** High as logic; known weaknesses for iterated revision.
**Status:** established (formal theory); interpretation for agents.
**Plain-language concept:** Expansion, contraction, revision with minimal change and an entrenchment ordering that says what to give up first.
**Coding-agent analogy:** When a new observation contradicts a note, drop the least-entrenched belief (lowest confidence/oldest/least-sourced), keep the rest.
**Where the analogy fails:** AGM assumes logically closed sets and consistent input; notes are loose prose.
**Concrete experiment:** 40 seeded contradictions; rule-based revision (source rank, then recency) vs LLM-judged; metric = final-state accuracy against gold, deterministic.

### 24. Wrong or misleading memory
**Source:** Anthropic components post (card 18, secondary) reports a faulty note trapping an agent and a dream fixing it; "Honest Lying: Understanding Memory Confabulation in Reflexive Agents", https://arxiv.org/html/2605.29463v1 (search snippet only).
**Reliability:** Low-medium (snippets).
**Status:** interpretation.
**Plain-language concept:** A confident but wrong lesson gets retrieved forever and can be worse than none.
**Coding-agent analogy:** "Always run X before Y" noted from one fluke.
**Where the analogy fails:** n/a.
**Concrete experiment:** Seed 10 wrong rules; measure harm vs no-memory baseline, then whether a re-verify-on-use step (run the cheap check the note claims) removes them.

---

## D. Collective memory theory and shared memory

### 25. Transactive memory
**Source:** Wegner (1987), "Transactive Memory: A Contemporary Analysis of the Group Mind", in Theories of Group Behavior, Springer, https://link.springer.com/chapter/10.1007/978-1-4612-4634-3_9. Verified Y.
**Reliability:** High, widely cited and empirically studied.
**Status:** established (human groups).
**Plain-language concept:** Groups hold knowledge by knowing who knows what, as much as by knowing the facts.
**Coding-agent analogy:** A directory of "which agent/person/doc owns which area" beats copying everything everywhere.
**Where the analogy fails:** Agents do not build trust over time unless forced to.
**Concrete experiment:** Routing test: questions answered via an owner-directory pointer vs full-shared-store retrieval; measure accuracy and tokens.

### 26. Organizational memory
**Source:** Walsh & Ungson (1991), Academy of Management Review 16(1):57-91. Seen via https://journals.sagepub.com/doi/10.1177/1350507609341091 (citation study). Verified Y (secondary).
**Reliability:** High as a framework; mostly conceptual.
**Status:** established (framework).
**Plain-language concept:** Five storage bins: individuals, culture, transformation (procedures), structure, ecology; memory is used or misused in decisions.
**Coding-agent analogy:** Individuals = per-user notes; culture = CLAUDE.md conventions; transformation = scripts/CI; structure = repo layout; ecology = tooling.
**Where the analogy fails:** Descriptive, not predictive.
**Concrete experiment:** Classify 100 existing notes into the five bins; check which bin has the most stale or contradicted items.

### 27. Governed shared memory research
**Source:** Collaborative Memory, arXiv:2505.18279 https://arxiv.org/abs/2505.18279; Governed Shared Memory, arXiv:2606.24535 https://arxiv.org/abs/2606.24535; MAP-Graph 2608.10509; Portable Agent Memory 2605.11032 (all Verified Y, snippets only).
**Reliability:** Low-medium (recent, mostly self-evaluated, little independent replication).
**Status:** interpretation / early.
**Plain-language concept:** Private vs shared tiers; read and write policies per user; named failure modes: unauthorised leakage, stale propagation, contradiction persistence, provenance collapse; provenance chains; temporal supersession.
**Coding-agent analogy:** Team memory over a company repo, where clients' data must not cross.
**Where the analogy fails:** Their benchmarks are custom.
**Concrete experiment:** Leak test with 2 tenants and 50 seeded sentinel strings; count cross-tenant retrievals (target 0) under per-note ACL filter at retrieval vs at write.

### 28. Knowledge graphs / wikis as agent memory
**Source:** Zep (card 16), A-Mem (card 14), Anthropic dreaming wiki result (card 18, secondary); Letta forum https://forum.letta.com/t/sleeptime-agents-for-memory-consolidation-best-practices-guide/154 (snippet). Verified Y.
**Reliability:** Low-medium.
**Status:** interpretation.
**Plain-language concept:** Structure (links, entities, validity) helps multi-hop and update questions; flat vectors lose them.
**Coding-agent analogy:** Linked markdown wiki with backlinks.
**Where the analogy fails:** Maintenance cost; link rot.
**Concrete experiment:** Same facts as flat file vs linked wiki; multi-hop questions; count tool calls and correct answers.

### 29. Append-only session logs
**Source:** No dedicated study seen. Zep's non-deleting invalid_at (card 16) and Anthropic "dream writes new store, original untouched" (card 18) are the nearest evidence. UNVERIFIED (from memory) as general principle (event sourcing).
**Reliability:** Engineering practice.
**Status:** interpretation.
**Plain-language concept:** Raw log is immutable truth; memory is a derived, rebuildable view.
**Coding-agent analogy:** transcripts as ground truth for dream correction.
**Where the analogy fails:** Logs contain secrets and untrusted text; retention policy needed.
**Concrete experiment:** Delete derived memory, rebuild from log; compare to old on 50 questions (rebuildability test).

---

## E. Evaluation and payoff

### 30. Benchmarks
**Source:** LoCoMo, Maharana et al. ACL 2024, arXiv:2402.17753 https://arxiv.org/pdf/2402.17753; LongMemEval, Wu et al. ICLR 2025, arXiv:2410.10813 https://arxiv.org/abs/2410.10813. Verified Y. Audit paper arXiv:2609.38021 "Auditing Long-Term Memory Evaluation" (snippet only).
**Reliability:** Medium. LongMemEval: 500 questions, five abilities incl. knowledge updates and abstention, S about 115k tokens; commercial assistants dropped about 30%. LoCoMo public subset is 10 conversations; judge variance reported.
**Status:** established (as benchmarks); neither measures coding-agent memory.
**Plain-language concept:** Question-answer tests over long chat histories.
**Coding-agent analogy:** Build a repo-specific set: seeded facts, changed facts, abstain cases.
**Where the analogy fails:** Chat recall is not task success.
**Concrete experiment:** 60-question deterministic set from your own session logs (exact match), including 15 "answer changed" and 10 "should say unknown".

### 31. Does reflection pay for its compute?
**Source:** Reflexion paper (card 10); "Self-Reflection in LLM Agents: Effects on Problem-Solving Performance", arXiv:2405.06682 https://arxiv.org/pdf/2405.06682; "Honest Lying" 2605.29463; "Decomposing Self-Reflection", https://aclanthology.org/2026.realm-1.21/; "When Does Memory Help Multi-Trajectory Inference", arXiv:2605.28224. Verified Y (snippets).
**Reliability:** Mixed; I did not open them.
**Status:** contested.
**Plain-language concept:** Gains often vanish against retry baselines, sometimes reflection hurts; search summary found no strictly compute-matched study. Letta sleep-time paper (card 13) is the closest compute-matched evidence and shows gains only on predictable queries.
**Coding-agent analogy:** Spending tokens on a nightly pass may equal spending them on one more retry.
**Where the analogy fails:** Memory's value is across sessions; one-shot ablations understate it.
**Concrete experiment:** Three arms with equal token budget over 4 weeks of tasks: (A) dream pass, (B) extra retries or longer thinking, (C) nothing. Metric: pass rate, tokens, human corrections per session. This is the master control.

---

## F. Safe sharing design (synthesis, speculative unless noted)

### 32. Memory record schema for sharing
**Source:** Synthesis of cards 16, 18, 27 and ACT-R (card 5); not an existing standard. Status: speculative.
**Plain-language concept:** Each note carries: claim, scope (repo/team/tenant), author (agent/person), source pointer (log line, commit, URL), created_at, last_used_at, use_count, confidence class (observed-by-tool / told-by-user / inferred / imported), valid_until or TTL, supersedes id, ACL.
**Coding-agent analogy:** Git blame for beliefs.
**Where it fails:** Authoring overhead; agents fill fields sloppily.
**Concrete experiment:** Linter that rejects notes lacking source pointer or scope; measure the fraction of unlinted legacy notes failing, and later error rate by confidence class.
Rules: inferred and imported notes are advisory until verified by a tool run; user-told notes outrank inferred; contradiction creates a supersede link, never deletion; shared promotion needs a gate (human or deterministic check); tenant data never crosses scope; TTL by class (volatile facts like paths short, conventions long).

---

# Closing sections

## (1) Ranked top-8 ideas
1. Provenance plus confidence-class on every note, with a deterministic linter (card 32). Cheapest, blocks most poisoning and drift.
2. Raw append-only logs as ground truth; memory is a rebuildable derived view; dream writes a NEW store and a diff, never edits in place (cards 18, 29).
3. Re-verify-on-use: a note that makes a checkable claim (path, command, version) carries a cheap check; failed check demotes it (cards 5, 24).
4. Compute-matched dream experiment (A dream / B retries / C none) as the gate for any dreaming budget (card 31).
5. Supersede-not-delete with valid_from/valid_to and source commit, plus rule-based belief revision (source rank then recency) before LLM judgement (cards 16, 23).
6. Human-gated promotion from personal to shared memory, with per-note scope/ACL enforced at retrieval and sentinel leak tests (cards 22, 27).
7. Transactive directory: shared store holds "who/what owns X" pointers and verified facts, not copies of everything (card 25).
8. Procedural memory first: promote only tested scripts/skills, since executable memory is checkable (card 11).

## (2) Prior-art warnings
- Anthropic already ships Claude Code auto memory (official) and Managed Agents Dreaming (research preview, announced May 2026); Auto Dream in Claude Code is documented only by third parties. Letta ships sleeptime agents and shared blocks. Zep/Graphiti covers bi-temporal graph memory. claude-diary covers diary/reflect. Do not claim novelty on consolidation, supersession or sleep-time compute.
- Unclaimed or thinly covered: compute-matched evaluation of consolidation on coding sessions, cross-person provenance/TTL policy for shared coding memory, deterministic linting of memory.
- Vendor benchmarks (Mem0, Zep, Anthropic) disagree and are self-reported; do not import their numbers.
- "Dreaming" and "sleep" are metaphors; neuroscience supports offline consolidation in brains, not LLM text rewriting.

## (3) What I could not verify
- No page was opened in full; every figure comes from search summaries, several secondary (Mem0 latency numbers via Medium; Anthropic Pokemon and wiki 13%->48% via Decoder/DEV posts; Anthropic +39%/+29% via a summary).
- Primary Bartlett (1932), Ebbinghaus (1885), Anderson & Schooler (1991), AGM (1985) not opened.
- The anthropic.com/engineering context-engineering URL itself was not in the results (only a research-page copy); cite the research URL.
- Auto Dream internals (leaked-code claims, backups) unverified; no official doc found.
- Date-future arXiv IDs (2605-2610 series) seen only as snippets; their claims are unreviewed.
- No compute-matched reflection study was found; the search summary stated this too.
- LoCoMo/LongMemEval numbers for specific memory systems not checked.
