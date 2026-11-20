# 13. Four talks through the emergence lens

Date: 2026-11-19. Lens: build something that improves agent performance and collaboration, tests "dreaming", and lets models lean on practices and primitives (from complex systems) instead of a heavy harness, so that positive emergence shows up.

## Source status and transcript quality

Everything below is a TALK CLAIM unless tagged `[verified-by-10]`, meaning research/10 read the primary page (multi-agent post, memory post, CL-Bench repo and abstract). I verified nothing independently; the arithmetic is mine and so labelled.

| Source | What I read | Quality problems |
|---|---|---|
| Lance Martin, 03:48:31-04:06:48 (YouTube `y9JtCCZP2MQ`) | Raw transcript in full (source clock). Figures from slides come only from note 11 (assistant-read, OCR risk). | ASR: "math slash theorem" (Fermat), "CLAW" (Claude), "multi-aging", "Lean ... is a harness" (context says ProofToMe), "Lagrange tunnel" (slides: Langlands-Tunnell), "Sonic 3.7", "Cloud 3 7", "FABL2". Timestamps below are 45 s bucket starts (~). |
| Diogo Almeida, 05:06:58-05:29:53 (`ZZ19zhYnDKY`) | Raw transcript in full, plus notes 10 and 11. | Profanity elided ("what the is going on"); product name "Jev/Jeb/jeike" unstable; "o of nan" = O(N), "login" = log N (inference); "GPT9", "GPT7 to9" numerics unreliable. He is a vendor (TypeSafe AI) with unproven product claims. |
| CJ Avilla (trust talk, Otter.ai) | Raw transcript in full. | NO timestamps; speaker labels unreliable; "Speaker 1" is presumed CJ. Opening cut mid-talk; tail leaks the next talk. "cloud managed agents" = Claude Managed Agents, "OpenShift" = OpenShell, "Lee and c2 1004" = Lee & See 2004, "Otel" = OTel. Q&A garbled; the owner asks one question. Cited by section. |
| Lydia Hallie | Only note 12, written from an owner-pasted transcript. I did not see the raw text. | No timestamps; recording flagged as a technical-failure re-record; two YouTube IDs, correct one unresolved. Quotes below are note paraphrases, not verbatim. |

## (a) Statements for "less harness, more practices and primitives"

**Lance**
- ~03:51:45: "They can connect to two different things, a Git and a SQL database. That's it." Same bucket: "Those are the core primitives that we give this team."
- ~03:52:06: prompt = "one lead agent, 999 helper agents. It gives them awareness of Git and the database and the problem statement." "That's really it."
- ~03:52:32: "agents now are sufficiently advanced that they can actually build primitives that they need to solve hard problems."
- ~03:54:00: "agents can solve very long horizon problems without much scaffolding."
- ~03:55:31: "agents are getting increasingly good at orchestrating themselves ... using these simple primitives."
- Contrast: Sept run = a dozen agents + ProofToMe + researcher support; Fable 5.2 run = none of those.
- Memory: ~03:58:00 the CL-Bench setup gives "no specific memory prompting": the directory is available, "Use memory if you want." Stronger models then know "when to write" and "when to read" on their own. Note 10 relays the blog line "tell Claude what memory is for, but not how" `[verified-by-10]`.
- Salience is delegated to the model: ~04:00:17 "better models have much better instincts for salience and what to write to memory."

**Diogo**
- 05:19:53 (blue LED analogy): "adding a new primitive that composes together with a old primitive."
- 05:20:38: AI as a fourth semantic logic gate, "program with common sense".
- 05:22:09: engineering by decomposition, verifiable stages, "state management instead of assuming everything is global state within a KV cache".

**Lydia** (note 12): CLAUDE.md should hold only what the model cannot see from code; emphatic rules can give "more tool calls and worse results".

**CJ**: the closest thing to a primitive is the policy lattice (base, per-session, human-signed ceiling). It is a feedback controller, not prompt text.

## (b) Emergent phenomena (observed or claimed)

Lance, all from the 1,000-agent run (about 30 h; the blog says 28.7 h `[verified-by-10]`):
1. **Self-built coordination tables.** The lead created them about 5 min in. ~03:52:26: "We didn't tell them to [build] these tables." Five tables: announce, assign, notes, subtasks, landed. `[verified-by-10]` for the five names. Read/write roles per table are slide-derived.
2. **Stigmergy-like traffic** (note 11 slide numbers). Hour 5.3: 12,929 writes, 147,425 reads, read:write 11.4. My arithmetic: Notes carry 73% of all writes (9,502 of 12,929); Notes+Subtasks carry 96% of writes and 69% of reads (note 11 says ~71%, I get 68.7%). Announce is near-broadcast: 19 writes, 23,787 reads.
3. **Reallocation.** ~03:54:20: "the lead and the agents themselves kind of reallocate themselves and kind of reassign themselves to different parts of the problem."
4. **Self-made abstractions.** A task tree for one hard statement; at hour 22.6, 946 of 1,079 shown tasks done (of 2,418 written).
5. **Convergence.** Proved statements by time (slides): 0 at 0.2 h, 13 at 1.2 h, 18 at 1.9 h, 34 at 4.8 h, of 60. Idle helpers: 125 of 999 at 1.2 h and 209 at 4.8 h (12.5% to 20.9%, my arithmetic). The lead issued a coordinated "Total freeze of origin/main".
6. **Memory sprawl vs tight memory.** Pokemon: Sonnet 3.7, 413 files / 977,930 chars; Fable 5, 10 files / 43,406 chars (22.5x, my arithmetic). Note 10, from the blog text, says nine files, so file count differs by source. Same prompt, different self-organised memory.
7. **Wiki structure growing with dreaming compute.** 103 pages / 766 links after 2 sessions; 222 pages / 12,893 links after 128. Links per page go from 7.4 to 58 (my arithmetic): link density grows far faster than page count.

Diogo and CJ: none observed. Diogo predicts unpredictability (05:21:24, internet analogy); CJ cites Zucker's 1840-1920 emergence of institutional trust as analogy.

Lydia: sessions orchestrating sessions; 2,500 to 30,000+ changes a day (May to September). Volume, not emergence.

Caveat: items 1-5 come from ONE run with ONE lead, on a task with a machine-checkable oracle (Lean). The lead is a designated hub, so this is hierarchy plus emergent shared state, not a flat swarm. "Emergent" here means unprompted table design and allocation, not decentralised self-organisation.

## (c) Dreaming, consolidation, reflection (numbers)

- Framing: agents write memory "myopically ... greedily within a session" (~03:56:30); memory must be globally coherent and non-redundant. Hippocampus-replay analogy (~03:57:04). Dreaming = reflect over transcripts and notes and "re-represent them" (~04:01:48); outputs are wikis, injected context, corrected notes.
- CL-Bench (40 database questions, fresh session each, memory dir vs none; slide numbers via note 11): Opus 5.5 0.838 vs 0.655; Sonnet 5.5 0.833 vs 0.644; Opus 5 0.828 vs 0.564; Opus 4.7 0.700 vs 0.383; Sonnet 5 0.610 vs 0.306; Sonnet 4.6 0.364 vs 0.330. Gains (my arithmetic): +0.03, +0.19, +0.26, +0.32, +0.30, +0.18, so a threshold effect, not a smooth capability gradient.
- Poison rescue: wrong landmark note trapped the agent; raw memory regressed; memory+dreaming escaped to Cerulean at action ~1,935. Single run window, no variance shown.
- Wiki compute curve (Stainless corpus, 25 questions): search alone 53%; wiki alone 13% at 2M dreaming tokens, 48% at 128M; wiki+search 54% to 61%. Per doubling of tokens (6 doublings): about +5.8 points wiki alone, +1.2 wiki+search (my arithmetic). Opus 5 built the wikis.
- Gap-filling: placeholder pages filled, index created.
- No dreaming numbers from the other three. CJ's analogue is offline review of thousands of sessions against a policy, feeding back into the ceiling.
- Counter-evidence in research/10: the CL-Bench abstract says "naive ICL outperforms systems dedicated to memory management" `[verified-by-10]`.

## (d) Admitted limits, failures, open problems

- Lance: the Sept dozen-agent team "didn't work very effectively" without ProofToMe (~03:50:20). Weak models "don't reliably know when to write" or read memory (~03:57:53). A wrong memory persisted and trapped the agent until dreaming. Sonnet 3.7 memory was "indiscriminate". The event page flags the ~30 h result as unreproduced; the blog calls it a "toy experiment"; 47 proved lemmas were given as input `[verified-by-10]`. Not stated: variance, cost, repeat runs.
- Lydia (note 12): the same prompt gives different small decisions with the human out of the loop (the auth-migration example). 1 in 10 dangerous commands still got through auto mode. Deny rules apply only through the documented decision order. The sandbox excludes hooks, MCP and Claude's own file tools.
- Diogo: no finished architecture. Memory is "the most vague of my directions". Routing and subagents are an unresolved flip-flop. His reliability and "Jev" claims are not demonstrated in the talk. Self-admitted: "we have like a lot of work to do."
- CJ: "supervision is not going to scale." Over-trust is acknowledged, with no probability given ("Ooh, that's a juicy one"). Her answer to the owner's question (agents over-request, or block themselves) was a human promotes or denies; no automated fix. Inference hooks do not exist yet in Managed Agents; she suggests tool policy "always ask" plus your own classifier. Regulated PR-review mandates "will likely have to change". The institutions-fail Q&A was answered with "very little time".

## (e) Where a harness stayed essential, and why

- Lance: per-agent sandbox, no keys, no network, gateway as "the only link out" (Claude API, Git, SQL). Gateway sets agent identity and logs every push and query. Fail-closed real-time classifier on every tool call. Offline review of all runs every 10 min. Own-branch pushes plus merge job, size and time limits on SQL. ~03:51:36: "Most of this is directed on safety and security." Reason: 1,000 agents executing code. The task also had a hard oracle (Lean).
- Lydia: deny rules before the classifier; "if Claude gets it wrong once, can I take it back?"; sandbox for dependency code reading .env/SSH keys; hooks with exit code 2; CI as the shared check.
- CJ: vaulted keys injected at egress; MCP tunnels; self-hosted sandboxes; auto mode instead of click-to-allow ("asking users to click allow doesn't work"); OTel alerts; interrupt, revoke, signed ceiling cut to zero network. Reason: hidden-instruction PDF, secret exfil via an allowed domain, workaround after error.
- Diogo: real-time semantic security is "not fast, cheap, and reliable enough" (05:25:09); he does not argue against sandboxes.
- Pattern: harness removed on COORDINATION and MEMORY, kept on BLAST-RADIUS.

## (f) Cheap tests that follow (all can run on Sonnet-tier agents against a local task with a deterministic oracle)

1. **Primitives ablation.** N=8-20 agents, 30 small failing-test tasks, three arms: (A) Git+SQLite and a Lance-style one-paragraph prompt; (B) same plus a prescribed schema; (C) no shared store. Log CREATE TABLE events, time to first table, tables per run, read:write ratio, write Gini by agent, idle fraction, tests passed, tokens.
2. **Poison-and-dream.** Seed a memory dir with one wrong fact, run a dreaming pass (re-read transcripts, rewrite notes). Arms: no dreaming; dreaming; equal-token extra search or retry. Deterministic check: fixed question set, wrong-answer rate, whether the poisoned string survives.
3. **Memory tightness vs model tier.** Run the same CL-Bench-style task on a small local model and a Claude model. Track files and characters per session and score. Tests note 11's H8 (weaker model needs more structure).
4. **Wiki link density.** Dreaming at 2x, 4x, 8x budgets; record links per page, orphans, placeholders, accuracy.
5. **Grow/shrink permission replay (zero model cost).** Replay existing Claude Code permission logs through CJ's rule: base, ceiling, promote after K repeats, shrink after D idle days. Measure standing-grant-hours, prompts avoided, denials. Addresses note 12's "no decay" issue.
6. **Shared state vs rediscovery.** 3 parallel agents on one repo, with and without a shared notes table; count duplicate file reads (Diogo's 05:23:46 question).
7. **Variance spread.** Same prompt x50; report decision spread, not the mean (Lydia's drift, Diogo's "Einstein 95% / Mr. Bean 5%").

## (g) Contradictions and tensions between talks

1. **Lance vs Diogo on shared state and routing.** Diogo asks why agents "can't share state" and says routing and subagents fight the KV cache. Lance shows shared state working, but through SQL and Git, not the cache. This is consistent if the answer is "shared state lives outside the context window."
2. **Trust in background work.** Diogo: you "should not trust LMs at all" for run-in-the-background cognitive work. Lance and Lydia run hours-to-30 h autonomy. Reconciliation: Lance's run has a perfect oracle plus heavy monitoring; Lydia insists on verification points. Autonomy tracks verifiability, which is also Diogo's own prescription.
3. **"Without much scaffolding" vs the scaffolding listed.** The slide shows sandboxes, gateway, two monitors, merge job, plus given lemmas. Lance's own sentence is "a lot of structure in terms of safety and monitoring". "Less harness" is true for coordination only.
4. **Hierarchy.** Lance: one lead, 999 helpers. Lydia: one orchestrator plus doer threads. Neither shows decentralised self-organisation.
5. **Static vs adaptive controls.** CJ shrinks unused grants (GitHub unused two weeks); Lydia's rules and CLAUDE.md are static (note 12 issue 4). CJ's rule is the only decay mechanism in the four talks.
6. **Rules vs spirit.** Diogo wants "spirit over letter"; Lydia and CJ rely on letter rules because only rules are guarantees (classifier miss rate 17%, note 12). Fable 5 Pokemon file count also differs: slide 10 vs blog 9.

## Table: practices and primitives the talks suggest

| Practice or primitive | What it replaces in a harness | How to measure emergence or benefit deterministically | Risk |
|---|---|---|---|
| Two-store substrate (Git+SQL), agents author the schema | Orchestration platform, task-graph tool (ProofToMe) | Test-suite pass rate, DDL events, time-to-first-table, read:write, write Gini vs prescribed-schema arm | Lean-style oracle may be doing the work; one lead = hub, not emergence |
| Lead + helper roles from a one-paragraph prompt | Role/persona config, hand-written routing | Task completion, idle fraction over time, allocation entropy per statement | Hierarchy mistaken for self-organisation; idle fraction 13-21% waste |
| Stigmergic shared tables (notes/subtasks/landed) | Message passing, agent-to-agent protocol | Reads per write, duplicate-work rate, claim collisions | Notes become a 70%-of-writes bottleneck; poisoned notes spread |
| Memory directory, model decides when and what to write | Memory-schema and write-rule prompting | Files and chars per session, score vs no-memory, by model tier | Weak or local models sprawl; gain is threshold-shaped |
| Dreaming pass (reflect, repair, re-represent) | Manual memory curation, hard TTL or caps | Poisoned-fact survival, wrong-answer rate, equal-token search control, links per page | Dreaming can entrench errors; compute per point of gain unproven |
| Grow/shrink permission lattice (base, session, signed ceiling) | Static allow lists, per-call click-to-approve | Replay: standing-grant-hours, prompts avoided, denials | Promotion becomes rubber stamp; shrink can block progress |
| Offline review of all runs against a written policy | Human PR/log supervision | Flag precision/recall on seeded bad runs | Reviewer model shares blind spots with the agent |
| Verification points as pass/fail hooks (exit code 2) | Prompt pleading in CLAUDE.md | Fraction of runs where hook triggers rework; decision-drift spread over 50 reruns | Only helps where an oracle exists |
| Sandbox + gateway + fail-closed classifier (kept) | Nothing: this is the part that cannot be removed | Escape-attempt corpus, p95 classifier latency, false-block rate | Cost and latency; deny rules bypassable (research/05a) |

Not checked: raw Lydia transcript; slide numbers against the recording; anything in the primary blogs beyond what research/10 reports.
