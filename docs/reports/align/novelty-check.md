# Novelty check (G0-3)

2026-11-19. Reader: Opus 5.5. Input: `docs/reports/align/novelty-fetch.md` (Haiku's verbatim
excerpts, HTML versions, fetched today), `docs/EMERGENCE-PROGRAM.md` ("EP"),
`docs/ALIGNMENT-INTEGRATION.md` ("AI doc"), `docs/PROPOSAL-SHARE.md`, `docs/WORKPLAN-ALIGN.md`,
notes 16 and 21. I opened no paper, repo or figure myself. Everything below is excerpt-level: an
arm that is not in the excerpts may still exist in the full text, the figures or the code. Quotes
are at most 25 words and name the excerpt section as Haiku labelled it. No provider call, no edit
outside this file.

## Verdict in one paragraph

No excerpt shows an arm that gives one norm as an instruction and the same norm enforced in code,
at a matched budget, in the same environment and tier. But the papers already do most of what our
framing implied was new. They compare prompt-level team interventions with structural ones in real
Claude teams across several capability tiers, with about 30 runs per cell. They measure
coordination outcomes, not only ethics. And *Worse Together* tests a code guard (block an order
until messages are read) that is our practice D enforcer. Its closest pair, a lead that **holds the
only tools** against a lead that **only advises**, compares structural authority with advisory
authority on the same role. Results for that pair were not extracted, so it is "closest,
unresolved", not a match. What survives is narrow: the same rule as card and as router predicate,
with no extra agent, at a matched byte budget, scored deterministically, for coordination and
memory practices that these papers do not test (claims, unique names, memory hygiene,
consolidation).

## 1. Arms per paper, and whether any is a same-norm instruction/code pair

Legend for "form": **I** = instruction (prompt text), **S** = structure or role (an agent, a
channel, a document), **C** = enforced in code or by tool permission, **?** = not stated in the
excerpts.

### 1.1 *Aligning AI Teams*, arXiv 2611.17820

Environments: sepsis-triage classifier build; consulting proposal generation. Models: Mythos
Preview, Opus 4.7, Opus 4.6, Opus 4.1, Sonnet 4.6. About 30 runs per (model, config) cell
("We run each (model, config) cell ∼30 times (median)", Section 4.1 Metrics).

| Arm | Form | Evidence (excerpt section) |
|---|---|---|
| Single-agent default | none | "one coder agent receiving the task with no extra framing" (4.1, reference band) |
| Safety-prompted single agent | I | "adds two sentences to the system prompt emphasizing that the agent is responsible for the safety" (4.1, reference band) |
| Multi-agent baseline: PM plus 8 coders, hub-and-spoke, shared workspace, no DMs | S | "a fixed team of one project-manager (PM) agent and eight coder agents, all running on the same model" (4.1, baseline) |
| Group chat | S | "A shared messaging channel that all nine agents can post to and read from" (4.1, interventions) |
| Review, three topologies (1:1 reviewers, distributed, PM-centralised) | S, and C? | "Each subtask is gated on reviewer approval ... the coder iterates until approved before marking the subtask finished" (4.1, interventions) |
| Designated safety lead | I (to the PM) plus a role | "the PM is instructed to task one of the eight coders as the project's end-to-end safety authority" (4.1, safety responsibility) |
| Distributed responsibility | I | "every coder is told they are personally responsible for system-level safety" (4.1, safety responsibility) |
| Coordinator-published safety specification | S (a document) | "having a coordinator agent publish a safety specifications document" (Abstract) |
| Compound intervention | ? | "Only the compound intervention reliably brings agent teams into the single-agent reference band" (4.1, findings 1 and 2). Its parts are not in the excerpts |

Same-norm pair: **none found.** The review gate is the only candidate for code enforcement. The
paper excerpt does not say how the gate is implemented; magelab's README says its framework
enforces review ("cannot be marked succeeded without approval", magelab features). That the paper's
review arm used this gate is **my inference**. Even so, no arm gives the review rule as text only.
The responsibility arms are instructions with no code counterpart. Budget matching: "not found"
(fetch, section 1). The 1:1 review topology adds 8 agents, so its compute differs by construction.

### 1.2 *AI Organizations Are More Effective but Less Aligned*, arXiv 2604.10290

Environments: AI consultancy (10 scenarios per note 21), AI software team (2 tasks); 15 and 50
rollouts. Models in the excerpts: Opus 4.1, Opus 4.5.

| Arm | Form | Evidence |
|---|---|---|
| Single agent | none | "multi-agent 'AI organizations' are simultaneously more effective ... but less aligned, than individual AI agents" (Abstract) |
| Consultancy organisation: managers, specialists, interns, email | S | "Agents communicate with each other by sending emails at every turn" (3.1) |
| Software team: PM plus coders, ticketing system, Claude Agent SDK | S | "All agents interact with each other through a ticketing system" (3.2) |
| Model swap Opus 4.1 to Opus 4.5 | tier | "the single-vs-organization gaps are visibly smaller for Opus 4.5" (5.2, cut off) |
| Structure and size sweeps (flat, hierarchical, hub-and-spoke, random) | S | Note 21 line 18, blog-level. **Not in this fetch** |

Same-norm pair: **none found** ("whether any arm enforces a norm in code (no statement found)",
fetch section 2). Budget matching: not found. Headline numbers are in Figures 1, 2 and 5, not read.

### 1.3 *Worse Together*, arXiv 2610.00583 and blog (MAMUBench)

Environments: API key (shared token budget, `labctl` MCP tool), clinic (calendar), personal
assistant (group order or booking), merge queue (not among the 74 scenarios). Models in excerpts:
Opus 5, Sonnet 5 (note 21 adds GPT-5.6-sol, blog-level). Some arms ran five episodes.

| Arm | Form | Evidence |
|---|---|---|
| Coordinator (one agent serves all users) | S | "a coordinator, where one agent serves all users" (Section 3) |
| Silent team | S | "each user has a separate agent but agents cannot communicate" (Section 3) |
| Peer-to-peer team | S | "each user has a separate agent and agents can communicate" (Section 3) |
| Solo control (API key, merge queue) | none | "Where meaningful (API key and merge queue), we also include a solo control" (Section 3) |
| Team lead, **lead-only** | C (tool ownership) | "The lead either holds the only tools that change jobs (lead-only) or only advises (advisory)" (Section 6, Mitigations) |
| Team lead, **advisory** | I | same quote |
| Merge queue: lead without guidance; team + lead + cut line | S, I (stated priorities) | "A team lead without guidance lowers it to 38% and 44%; ... team + lead + cut line reaches 95% and 96%" (Appendix B.2) |
| Blocking an order until messages are read | C | "blocking agents from placing an order until they had read their messages rescued more failed group orders than simply rerunning them" (blog tl;dr) |

Same-norm pair: **closest, unresolved.** Lead-only against advisory varies one thing, whether the
lead's authority is enforced by tools or offered as advice, with the same extra agent in the same
environment. That is a structure-against-instruction pair on one norm (lead authority). Three gaps
keep it from matching our design: (a) the excerpt does not say whether followers are told to obey
the advisory lead, so the instructed norm may differ; (b) its numbers were not extracted; (c) budget
matching is not stated, and the lead is "an extra agent with no jobs" (Section 6, Mitigations).
Label check: Haiku files this quote under Section 6 Personal Assistant, but "tools that change jobs"
reads like the API key environment of Section 4. Possibly mislabelled; check in the full text.

The read-before-order guard is compared with **reruns**, not with an instruction arm such as "read
your messages before ordering". No instruction-only version was found.

### 1.4 magelab README (released with 2611.17820)

A framework, not an arm. It already enforces one norm in code: review approval before success. It
tracks per-agent USD ("Cost tracking is automatic — the database and dashboard both report per-agent
and total USD spend", README cost). That makes post-hoc cost comparison possible, but no per-arm cap
beyond `max_turns` and `org_timeout_seconds` was found. "Structured task management" may include
task assignment or claims; the README excerpt does not say.

## 2. Our claims: keep, soften, remove

| Claim (where) | Status | Why |
|---|---|---|
| "Nobody we could find compares a norm given as an instruction with the same norm enforced in code, on the same task" (EP 1, bullet 3) | **Remove** | Too strong. WT's lead-only/advisory pair is close; 2611 compares prompt and structural interventions on one task |
| "a head-to-head, budget-matched comparison of one norm as instruction against the same norm in code, with an index and intervals" (EP 8, item 1) | **Soften** | Survives only as "same rule, no extra agent, matched byte budget"; still excerpt-level |
| "that comparison across capability tiers" (EP 8, item 2) | **Remove as novelty** | 2611 ran five Claude models; WT ran Opus 5 and Sonnet 5; 2604 compared Opus 4.1 with 4.5. Tier sweeps are standard. Keep tier as a design axis only |
| Scripted re-verify control for dreaming (EP 8, item 3) | **Keep** | None of these papers tests memory or consolidation. Still only an abstract-level search (note 16) |
| "open cards and instruments" (EP 8, item 4) | **Soften** | magelab and MAMUBench are open. Ours differs only in cost (a few USD) and deterministic scoring |
| "The cited work measures ethics and safety outcomes" (AI doc 9, item 2) | **Wrong; correct** | WT scores coordination: "the peer-to-peer team reaches 30% of the optimum for Opus 5 ... against 64% ... for their coordinators" (Section 4, Results), scored "mechanically from environment logs" (Section 8) |
| "I found no opened paper that compares a prompt-only norm against the same norm enforced in code" (note 16, lines 99 and 166) | **Outdated** | Same reason as row 1. A note is a dated record; add a pointer to this file rather than rewriting it |
| PROPOSAL-SHARE.md | **Nothing to soften** | Its headline is handoffs against search (lines 20 to 23); it makes no instruction-against-enforcement claim |

### 2.1 Replacement wording for `EMERGENCE-PROGRAM.md`

Section 1, replace the third bullet ("**Nobody we could find ...** not proof of novelty.") with:

> - Team interventions have been compared before, in real Claude teams across several tiers:
>   prompt-level responsibility against a designated lead and a published spec (*Aligning AI
>   Teams*, 2611.17820), and a lead that holds the only tools against one that only advises, plus
>   a read-before-order guard (*Worse Together*, 2610.00583). In the excerpts we read, no arm gives
>   the **same rule** both as text and as code with no extra agent at a matched budget, and none
>   tests claims, naming or memory hygiene. That is the remaining gap. It rests on excerpts, not
>   on the full papers or their code (`docs/reports/align/novelty-check.md`).

Section 8, replace the "Possibly new" paragraph with:

> Closest prior work: *Aligning AI Teams* (prompt against structural safety interventions, five
> Claude models), *AI Organizations* (2604.10290; teams against single agents), and *Worse
> Together* (formations, a tool-holding against an advisory lead, a read-before-order guard;
> MAMUBench). Tier sweeps and open team testbeds are therefore not new. Possibly new, stated
> modestly and at excerpt level: (1) one rule given as a card and as a router predicate, with an
> equal-length neutral card, no extra agent and one byte budget charged to every arm, reported as
> an index with intervals; (2) applied to coordination and memory practices these papers do not
> test (claims, unique names, hygiene, consolidation); (3) a scripted re-verify control for
> dreaming next to an equal-token control; (4) instruments that run for a few US dollars with
> deterministic scoring. "Not found in the excerpts we read" is not novelty.

Section 2.1 table, practice D row: add "Enforcer replicates the *Worse Together* read-before-order
guard". Cards S and L (WORKPLAN-ALIGN section 3): add "Replication of the *Aligning AI Teams* spec
and safety-lead arms, transposed to the hold task".

### 2.2 `PROPOSAL-SHARE.md`

No change needed now. If it is re-centred on the practice program, replace the "Prior art"
sentence at lines 302 to 304 with:

> **Prior art.** Orchestrators, model cascades, signed policy, governed memory with provenance,
> consolidation and multi-agent team testbeds all exist; Anthropic Fellows work already compares
> prompt-level and structural team interventions across Claude tiers (*Aligning AI Teams*,
> *Worse Together*). Our possible contribution is narrow: the same rule as text and as code at
> one budget, for claims and memory practices, with open few-dollar instruments.

### 2.3 `ALIGNMENT-INTEGRATION.md` section 9 (outside the brief, for whoever edits it)

Item 2's last sentence becomes: "*Worse Together* also scores coordination (share of optimum,
fulfilment) mechanically from logs; our difference is the practices tested, not the outcome type."
The section's "Until that is checked (G0-3)" sentence becomes: "G0-3 checked the excerpts and the
magelab README, not the code; no same-norm pair was found."

## 3. Is EP-1 a replication?

Keep three cases apart:

- **EP-1, practice A (claim before work): not a replication.** No excerpt arm tests claims or
  claim locks. Describe it as "an extension of the intervention-comparison design of *Aligning AI
  Teams* and *Worse Together* to a coordination practice". This is conditional: magelab's
  "structured task management" and the two unopened `safety-research` repos could contain a claim
  mechanism.
- **Cards S and L: replications.** They transpose 2611's spec and designated-lead arms to a toy hold
  task. Report them as replication attempts. The scripted S/L difference is arithmetic (AI doc 4).
- **Practice D's enforcer: a replication of WT's guard.** D's playbook arm is the new half, since WT
  compared the guard with reruns, not with an instruction.

The WORKPLAN-ALIGN trigger ("If such an arm exists, EP-1 is described as a replication") does not
fire on the excerpts. It must be re-run if the repos show a same-norm arm.

## 4. Reuse, and what this pass cannot verify

**Reusable now, as ideas and citations (no code copied):**

- WT's delivery finding as a design rule: "DMs are delivered as user messages, so an agent can
  commit before a message is in its context" (Section 6, Results).
- WT's mechanical scoring from logs and its share-of-optimum metric. Our `Y` per slot is the same
  kind.
- 2611's mean plus 10th-percentile reporting and about 30 runs per cell as a sizing reference.
- magelab's pattern of a code-enforced review gate and per-agent cost accounting.
- 2611's limitation as a caveat we share: "we study only Anthropic's Claude family" (Caveats).

**Not reusable without more work:**

- **Code from any repo.** No licence was found for magelab ("License text: not found in the
  README"), MAMUBench, `aligning-ai-teams` or `misalignment-in-ai-organizations`. Treat all as
  all-rights-reserved until a LICENSE file is read.
- **magelab as our runtime.** It is a framework on the Claude Agent SDK. EP section 3 says "No new
  framework", and our arms live in `router.py`. Adopting it would be a design change for the owner.
- **MAMUBench runs.** "about 3.4 billion tokens" per pass of the 74 scenarios (Section 8),
  about 46M per scenario on average (my arithmetic), against EP-1's 1.15M cap. At most, scenario and
  scoring definitions could be ported, after a licence check, to scripted rung 0.

**Cannot verify from excerpts (exact locations):**

- 2604.10290: all headline numbers (Figures 1, 2, 5); Appendices D and E; Limitations and Future
  work body; the structure-sweep claim (note 21, blog-level).
- 2611.17820: Appendix A.2 cost-effectiveness (Figure 6 only); Appendix C; per-cell numbers beyond
  the quoted deltas; parts of the compound intervention; how the review gate is implemented.
- 2610.00583: the read-before-order guard's numbers. The AI doc's "73% and 62%" and "47% to 67%"
  come from an earlier blog read and are **not** in this fetch. Lead-only against advisory results;
  Appendices A.3 and C.3; the 25-scenario results table; the instruction text, if any, followers
  receive under the advisory lead.
- Repos: `safety-research/aligning-ai-teams` and `safety-research/misalignment-in-ai-organizations`
  unopened; magelab README only; MAMUBench README only. Licences unknown for all four.
- PDFs not opened; HTML only (2604's HTML is marked experimental).

## 5. Questions for the authors

1. *Worse Together*: in the advisory-lead arm, are followers told to follow the lead? What were
   lead-only against advisory results per environment and model, and how many tokens per arm?
2. *Worse Together*: was the read-before-order guard ever compared with an instruction-only version
   ("read your messages before ordering") at the same budget?
3. *Aligning AI Teams*: is the review gate enforced in code (magelab `review_required`) or by
   prompt? Was any review arm run as instruction only?
4. *Aligning AI Teams*: which parts make up the compound intervention? What tokens or USD per cell
   (Figure 6, Appendix A.2), and does it change the ranking at matched cost?
5. *Aligning AI Teams*: the DoR annotator is "given the run's final outcome ... up front" (Appendix
   A.3). Was a blind annotation run, and how far do labels move?
6. Did any of the three projects test task claims, ownership locks or naming conventions, in code or
   as text? Are they in magelab's task management?
7. Licences for magelab, MAMUBench and both `safety-research` repos.
8. Why the capability trend differs: the sepsis gap grows with capability (Sonnet 4.6 about −1 pp,
   Mythos −59 pp) but the consulting gap does not. Is that task headroom or model behaviour?
9. *AI Organizations*: were any norms enforced through the ticketing system rather than prompted?

## 6. Consequences for the EP-1 pre-registration (`prereg/EP1.md`, practice A only)

1. **Novelty paragraph:** use the EP section 8 wording above; call EP-1 an extension, not a
   replication; record "prior-art status: excerpt-level, repos unopened, verified 2026-11-19".
2. **No extra agent in the code arm, stated.** Claim rejection is a router predicate, charged inside
   the same byte cap. This is the one design feature the papers' lead and reviewer arms lack.
3. **When a rejection reaches the agent, stated.** WT shows an agent can commit before a message is
   in its context. Pre-register whether a rejected claim is returned in the same turn or shown in the
   next snapshot, and score both lost slots and re-claims.
4. **One tier, no tier claim.** EP-1 runs Haiku 5.5 only. 2611's sepsis drops were smallest on its
   weakest model (Sonnet 4.6 about −1 pp), but WT's weaker model coordinated worse (12% against 30% of
   optimum). The direction for a weak tier on coordination is open; pre-register it as two-sided.
5. **No model annotator.** Keep deterministic scoring from the log and say so. 2611's DoR labels came
   from a model that saw the outcome.
6. **Report `Y` with a constraint read-off** (false-done rate, name collisions), as WORKPLAN-ALIGN
   B3 already says, and add the 10th percentile beside the mean, as 2611 does.
7. **Re-run gate:** if the repos (question 6) show a claim-lock arm with a text twin, the novelty
   paragraph flips to "replication on coordination practices" before the freeze, per WORKPLAN-ALIGN
   section 6.
8. **n = 15 is small next to 2611's ~30 per cell.** The existing power statement (about 20 points
   detectable) stands. No change in calls or cost.

Not done: no paper, repo or figure was opened by me; the classification of the review gate and of
the WT lead arms rests on excerpts and one README.

verified: excerpts in docs/reports/align/novelty-fetch.md, read 2026-11-19 (no commit)
