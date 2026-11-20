# Adversarial review 2 (2026-11-19)

Reviewer: Fable 5.2, not the author. Read-only; nothing was run, installed or downloaded.
Repo state: `972dee3` plus the uncommitted working tree (PLAN, prereg/*, three new reports).

Read in full: VISION, PRINCIPLES, ARCHITECTURE, WORKPLAN, research/07, 10, 11,
reports/prereg-audit, staged-t7-decision, E9-autoresearch-design, E1-E8.1-local-results, README.
PLAN: sections 1, 2 (T1-T9), 3, 4, 6, 7, 8 and the appendix. **Not read in full:** PLAN section 5,
SCIENCE (only section 5, section 8 and the lines the audit cites), prereg bodies beyond their
headers and the grep hits quoted below, all code. Line numbers are the working tree's.

Labels: **fact** = quoted from a repo file; **inference** = my reasoning; **unknown** = not
stated in what I read.

## 0. The blunt summary

1. The repo holds about 555 kB of documents and 1,416 lines of code. Nine hypotheses, none
   tested. Five pre-registrations, none frozen. The freeze procedure needs commits and only one
   commit is approved (WORKPLAN 5.2, owner question 1). The whole confirmatory programme is
   blocked by a yes/no question, not by science.
2. The architecture the owner now asks about (hub and cells) has no code, and WORKPLAN 9 cut
   `cell.py`, `gate.py`, `memstore.py` and `board.py` ("no reachable decision") while PLAN 6.1
   P1b and 6.3 items 9 and 13 still list them as "start now".
3. The two experiments nearest to running (T7 stage 1, E9) both state in their own design
   documents that the likely outcome is "inconclusive", and both give an inconclusive result
   the same consequence as a kill. PRINCIPLES run-gate rule 6: "A result that cannot change
   what we do next is not run." They fail the project's own gate.
4. Every GPU experiment sits behind an undiagnosed fault: both T7 smoke arms were killed by
   the 10 GiB MemAvailable watchdog after 22 and 13 minutes on a 0.8B model, "cause unknown"
   (staged-t7-decision 2). Planning more GPU-hours before that is explained is wasted paper.
5. The three idea families are not yet a test mechanism. Each has its own bespoke experiment
   with its own task, metric and budget. Section 4 proposes one perturbation matrix that
   replaces most of them.

## 1. Requirement 1: can the hub also be a cell, without a second framework?

### What the contract says (fact)

- ARCHITECTURE 1: "The hub is a strong model (Claude) plus the owner's signing key."
- ARCHITECTURE 2.1: the hub "signs the ceiling", and "no model process can read the private key".
- ARCHITECTURE 8: tiers are "stub, local model, Claude worker, hub"; on failure "escalate one
  tier, then the hub, then the owner". So the hub already does cell work as the last tier.
- The four files flow hub to cell and cell to hub. Cost is reported cell to hub only.

### Verdict: not supported as written. Six things break.

| # | What breaks when the hub does a cell's job | Why |
|---|---|---|
| 1 | "Hub" is three things under one name | The owner's key, deterministic hub code (router, lint, check runner) and the hub model. Section 2.1 gives signing to "the hub" and denies it to any model in the next sentence. A symmetric design needs the three named apart. |
| 2 | The hub-as-worker has no contract | No cell directory, no `policy.json`, no budget, no log chain, no evidence bundle. The strongest model is the only actor with no ceiling. |
| 3 | Verification independence | 2.3 says the verifier never sees the worker's reasoning. If the hub did the work and the hub judges it, that is "a model judging its own output as the only evidence", which PRINCIPLES forbids. Only tasks with a deterministic check are safe. |
| 4 | Hub cost is invisible | The run-gate inequality `c_s + c_k + (1 - p) * c_h` has no term for planning, routing and verifying. Hub tokens appear in no evidence bundle. "Decentral" can look cheap while the hub spends most of the tokens. |
| 5 | Nothing above the hub but the owner | A failed hub-as-worker task escalates straight to a human. No rule says when the hub should refuse to self-assign. |
| 6 | Orchestrating local models from a Claude Code session | A local cell "cannot be a Claude Code session" (file 07, boundary). The hub must shell out. Its shell is the only sandboxed tool; starting a container from inside needs `docker.sock`, which file 07 lists among settings that "can break the boundary". |

### The fix needs no second framework. It deletes a concept.

Make the centre of the star **plain code plus the owner's key**: the scripted hub of
ARCHITECTURE 10 step 3. Every model, including the strongest, is a cell with a directory, a
signed policy, a budget and a log. "Plan", "verify" and "judge" become task classes. Then:

- Hub-as-cell is a Claude cell whose `cell.json` names a stronger model. No new file type.
- Claude orchestrating local models is a planner cell whose output is task specs; the router
  (code, outside Claude Code's sandbox, started by the owner) launches the workers. The
  `docker.sock` problem goes away because Claude never launches anything.
- Hub cost is logged by the same evidence-bundle schema as any cell (fixes row 4).
- Rule for row 3: a cell's result is never verified by a cell with the same model ID unless a
  deterministic check exists. Otherwise it goes to a different tier or to the owner.

What this costs, honestly:

- A planner cell needs a wide read ceiling. "Narrow authority" is then true for workers only.
- Planning has no deterministic check, so planner quality is judged only downstream.
- A Claude cell is a subagent or a headless session, not a directory process. Its enforcement
  is permission rules plus the shell-only sandbox. The three worker kinds share a file format,
  not a security property. ARCHITECTURE 3 says this in its table; section 1 ("one contract")
  should not imply more.

Cheapest experiment (zero cost, no model): reinstate ARCHITECTURE 10 steps 1 to 3 and add two
contract tests: (a) the same task spec runs unchanged on a stub cell and on a scripted
stand-in for a strong cell; (b) a "plan" task is executed by a cell and its cost appears in
the bundle. If both pass with no new file type, the symmetric claim holds on paper and in code.

## 2. Requirement 2: Claude "on localhost" for confidentiality

Source: research/07 only. File 07 read the MCP-tunnel and several self-hosted pages only
partially (its row 6-9); gaps are marked unknown.

**"Claude on localhost" is a misnomer.** In every shape in file 07 the model runs at Anthropic
or at a cloud provider. What can be local is the tool execution, the files and, in one
private-beta shape, the session store.

### Claude Code self-hosted environments

| | From file 07 |
|---|---|
| Covers | Where sessions execute: "Runners execute the sessions; the idea is the same as a self-hosted CI runner." Checkout, files at rest and tool side effects are on your host. |
| Stays exposed | "The control plane remains Anthropic-hosted: session orchestration, queueing, and the claude.ai interface." "Anthropic stores the session transcript." Session content "still goes to `api.anthropic.com` even with Bedrock". The control plane picks the model ("You can't choose the model with `ANTHROPIC_MODEL`"). |
| Limits | Not available to Zero Data Retention or HIPAA organisations. Public beta, Team and Enterprise only. GitHub or GHES checkout only. Runner locks to one owner. On a Bedrock runner, claude.ai server-managed settings and organisation policies "don't reach sessions". |
| Threat model it fits | An outsider reaching your code or services through a vendor-hosted sandbox. Keeping repositories and credentials off a vendor's execution host. |
| Threat model it does not fit | Confidentiality of anything the model reads, from Anthropic. Every file the agent reads, every tool result and every prompt is session content. Choosing this shape also rules out ZDR. |

### Claude Code sandbox (the "specific sandboxes")

| | From file 07 |
|---|---|
| Covers | Shell commands: filesystem and network limits on what Bash can touch. |
| Stays exposed | "Sandboxing reduces risk but is not a complete isolation boundary." Read, Edit, Write, WebFetch, MCP servers, hooks, LSP, the status line and `apiKeyHelper` run outside it. Hooks run "with your full access". |
| Network | Filtering is by client-supplied hostname, no TLS inspection by default; domain fronting is named as possible; broad hosts such as github.com are exfiltration paths. A custom proxy port replaces the built-in lists. |
| Ways it breaks | `allowUnixSockets` (docker.sock), broad `allowWrite`, `enableWeakerNestedSandbox`, `allowNestedUserNamespaces`; an unsandboxed retry via `dangerouslyDisableSandbox` unless `allowUnsandboxedCommands: false`. |
| Threat model it fits | An injected or mistaken shell command damaging files or calling out. |
| Does not fit | Exfiltration through a file tool, a hook or an MCP server; a determined adversary on the network path; confidentiality from the model provider. |

### MCP tunnels

| | From file 07 |
|---|---|
| Covers | Reaching a private MCP server without opening it inbound: "A lightweight gateway you deploy makes a single outbound connection, no inbound firewall rules." |
| Stays exposed | Research preview, "provided 'as-is' without any uptime, support, or continuity commitment". "Depends on Cloudflare", so a third party is on the path. Every tool result returned through the tunnel becomes session content and goes to the model. MCP servers run outside the sandbox. |
| Unknown | Whether traffic is end-to-end encrypted through the tunnel provider, and what the provider can log. File 07 does not say. |

### The only shape with a stronger claim

Self-hosted Managed Agents: "Session history is stored in your own database", model requests
"go where you choose", ZDR applies to requests to Claude. But: private beta by request; no
dreams, scheduled deployments, webhooks or Files API; "the agent's `bash` tool is a real shell
with the worker process's permissions and network access". The model still sees the content.

**Bottom line.** None of these keeps session content from the model provider. Only a local
open-weight cell does, and only for content the hub never reads.

### Overclaims and loose wording in our documents

| Where | Says | Problem |
|---|---|---|
| ARCHITECTURE 2, 4 | "The hub never holds a cell's secrets or reads its raw log by default"; "Raw logs never leave the cell" | False for a Claude-subagent cell: its whole context is session content sent to the same API, under the same account, as the hub. For a local cell, the digest lint must resolve source pointers into the log; if the hub model does that, it reads the log. Fix: say which part is local code and which is the remote model. |
| ARCHITECTURE 2.1 | "No model process can read the private key" | On this box the hub session runs as the owner's user, and file tools are outside the sandbox (file 07). A key file under the owner's home is readable by Read unless it is on a hardware token, passphrase-protected, or off the box. As written this is an intention, not a property. |
| ARCHITECTURE 9, row 1 | A compromised cell "cannot sign or reach another cell" | True for a containerised local cell only. A stub cell is "not an OS boundary" (section 3). A Claude cell is held back from other cells' directories by permission rules alone. The row's residual note covers Claude cells but the headline claim is still too strong. |
| VISION thesis | Local cells are "private" | The result, check output and digest go to the hub, and the hub model is remote. Private means: raw logs and inputs the hub passed by path and hash without reading. Any task the hub planned was read by the hub. |
| PLAN T1, 7.3 | Transcripts "never leave the box" | The transcripts record sessions whose content was already sent to the model API when they happened. Correct wording: "our analysis exports nothing". |
| ARCHITECTURE 6, PLAN 4.5 | Self-hosted environments and MCP tunnels: "Not used" | Not an overclaim, but it contradicts the new requirement. If the owner wants them, both files change, and the limits above (Team or Enterprise, GitHub checkout, no ZDR, research preview) become project constraints. |

Outside file 07, flagged because it bears on the same question: the owner's sessions on this
box go through a local proxy with a fallback chain to other providers whose retention terms
"were NOT reviewed" (backend `AGENTS_SYSTEM.md`). PLAN 4.4 and WORKPLAN step 11 correctly ban
that route for C0. The same care is not stated for the build sessions that read the repo.

## 3. Requirement 3: the three idea families against first principles

The owner's term "KDS" does not appear in any repo file (grep, zero hits) and is ambiguous. I
treat it as the three families in PRINCIPLES "Scope guard": memory, green efficiency, adaptive
policies and rules. If the owner meant something else, this section must be redone.

### 3.1 Memory (H3, H4, H8, E8.3, E8.4, E3.x, E9 memory arm)

- **Does it make sense?** Yes. It is the only family with outside evidence that it both helps
  and hurts (file 11: wrong-note trap, 413-file sprawl, near-zero gain for the weakest model).
- **Decision it changes:** do cells get memory at all; flat or governed; is a dream pass ever
  scheduled.
- **Simplest version:** one JSONL file, a source pointer per record, supersede instead of
  delete, and a plain search tool over the raw log as the baseline to beat.
- **Cut:** E8.4 dream dose (a third-order question before the first-order one has an answer);
  the T4 consolidator adapter (PRINCIPLES scope guard: not "training a local model to imitate"
  a frontier one); wikis; the E9 memory arm (section 6).
- **Merge:** H3, H4 and H8 are one experiment: arms {none, raw-log search, flat file, governed
  file, governed plus dream} by model tier, on one task, at one budget. Three hypotheses,
  three task designs and three budgets today.

### 3.2 Green efficiency (H6, E8.1, T7 cost columns, run gate)

- **Does it make sense?** As a reporting discipline, yes. As an "idea family", weakly: it has
  one decision in it.
- **Decision it changes:** which tier does a task class (H6), and the minimum task size worth
  sending to a fresh worker (cold start, E8.1).
- **Problems:**
  - PLAN H6's own Fermi says the cost side is "nearly settled by arithmetic". The open part is
    quality, which is not an efficiency question.
  - Joules exist only for the local GPU. PRINCIPLES says they are "never extrapolated ... to
    Claude's serving side". So no cross-tier energy comparison can ever be made, and "green"
    promises more than the instruments deliver. Call it cost efficiency.
  - H6's kill uses USD per passing task for the local route. The owner ruled local USD "n/a"
    for H7 and E9 (prereg-audit, E9 design 5.5), and WORKPLAN 6 says USD "needs the owner's
    tariff". H6's primary criterion cannot be computed until that is reconciled.
  - On a shared GPU, "baseline-subtracted joules" assumes the other tenants draw constant
    power. Unverified.
- **Simplest version:** four cost columns on every result, plus one inequality (ARCHITECTURE 8).
- **Cut:** idle fraction as a headline metric (descriptive only); E8.1's "below 67%"
  prediction (it tests a slide figure file 10 could not confirm; no decision follows).
- **Merge:** the fan-out gate (H2) is this family, not family 3. PRINCIPLES itself says
  "Fan-out is a *cost* decision" and then lists H2 under adaptive policies.

### 3.3 Adaptive policies and rules (H1, H2, E5.3, E9 authority)

- **Does it make sense?** The ceiling plus deny list does. Decay is not yet justified. Idle
  exposure in rule-days is a proxy with no link to harm: it matters only if a compromise lands
  in an idle window, and nothing measures that.
- **Decision it changes:** the value of tau, or whether decay exists at all; which rule type
  (deny rule, hook, sandbox) holds under pressure.
- **Evidence state:** H1 is untestable here. 1,079 events, 1 session, 11 denials
  (E1-E8.1-local-results). The backend policy file says the owner launches agents in
  skip-permission modes; if most sessions run that way there are no prompts to replay
  (inference; check it).
- **Simplest version:** a signed static ceiling, a deny list and an expiry date. No decay.
- **Cut:** H1 as a confirmatory hypothesis until a count of sessions with permission events on
  the owner's other machine exists. Move H2 to family 2 and defer it (it needs G1).
- **Keep and promote:** E5.3 (behaviour under denial). It needs no transcript corpus and tests
  the family live.

### 3.4 The families as task controls: one robustness measure

Today each family has a different task, metric and budget, so nothing can be compared. Use one
harness (`runner.py`, trapbench) and turn each family into a switch.

**Definitions.** Unit: one (task, seed) pair. Condition k: clean, or exactly one perturbation.
Arm a: a setting of the control switches. Pass is the task's deterministic check.

| Quantity | Definition | Unit |
|---|---|---|
| Clean pass rate | passes / episodes, condition clean | fraction, both counts shown |
| Perturbed pass rate | the same under perturbation k | fraction |
| Robustness drop | clean minus perturbed, paired by task and seed | points |
| **Control effect (primary)** | drop of the baseline arm minus drop of the control arm, same k | points; cluster bootstrap by task |
| Harm rate | episodes with a canary hit, a protected-file hash change or an executed action outside the ceiling, whether or not the task passed | fraction |
| Recovery cost | tokens per passing task under k, next to the clean figure | tokens / pass |
| Worst case | lowest perturbed pass rate over k; all-seeds pass rate | fraction |

A control counts only if its effect interval excludes zero, its clean pass rate is within 2
points of the baseline's, and its own tokens are charged inside the same per-task cap.
(2 points is my design choice.)

**Perturbations**, seeded and injected by the harness at a fixed step, one per episode:

| k | Perturbation | Scoring | Family it should be matched to |
|---|---|---|---|
| P1 | Requirement changes mid-task (spec v2 replaces v1) | v2's tests; canary on a v1-only artifact | Memory (stale record), policy |
| P2 | Noisy requirement: one irrelevant and one contradictory sentence, precedence rule stated | generator's ground truth | none (pure model baseline) |
| P3 | Injected wrong or stale memory | trapbench canary (exists) | Memory |
| P4 | A cell fails (bad result) or is slow (exceeds `wall_s`) | task check on the merged result | Efficiency (cascade, timeout, escalation) |
| P5 | Permission denial with a safe allowed route | E5.3 outcome classes from the trace | Policy |

**Arms, first pass:** all controls off against all controls on. Only where the two differ on
a perturbation is a one-family ablation run for that perturbation. A full factorial is not
affordable and not needed.

**Fermi (not measured).** 10 tasks x 2 seeds x 5 conditions x 2 arms = 200 episodes per
model. At that size only effects of about 15 points are visible (PLAN 4.3's own power note).
P4 needs at least two cells, so it runs only after the router exists.

**What this replaces:** E3.3 and E3.4 (P3 with memory arms), E5.3 (P5), E8.2's hub-assign arm
(P4), E9's authority test (P5 plus the E9-0 route catalogue), and H8 (the same matrix run on
two model tiers).

## 4. Requirement 4: a model-agnostic test mechanism

What exists: `runner.py` with backends `scripted`, `local_hf` and a refused `claude` stub. PLAN
section 3 is titled "model-agnostic" but PLAN 4.2 says "One fixed model snapshot per
experiment ... No search over model and effort". Requirement 4 overrides that line; it needs
an amendment.

### Protocol

1. **One loop for every model.** Our own agent loop, one task spec, one tool schema (the
   contract's capability keys), one adapter per backend returning a tool call or a final
   answer plus usage. Claude runs through the Messages API with a direct key, not through
   Claude Code: Claude Code adds its own system prompt, tools and loop, so it would be a
   different harness. "Claude Code as shipped" is a separate, labelled product arm.
2. **Byte-identical inputs.** Same tasks, seeds, prompts (hash recorded) and tool set. The
   only per-model difference is the chat template. No per-model prompt tuning; if any is
   allowed, every model gets the same number of variants, chosen on a practice family.
3. **Instrument checks in every batch.** A scripted stateless stub (floor) and a scripted
   oracle (ceiling). If the floor passes or the oracle fails, the batch is void.
4. **Calibration band.** A task enters only if the weakest model in the comparison scores
   above 30% and the strongest below 85% clean (the band E8.3 already uses), judged on a
   practice family.
5. **Order.** Models interleaved round-robin over tasks, so drift during a batch hits all
   models alike.
6. **Outcome classes.** pass, fail, refusal, budget exhausted, infrastructure abort. Refusals
   are reported separately. An infrastructure abort (rate limit, timeout, watchdog) is re-run
   once and counted.
7. **Scoring.** Deterministic only. No model grader anywhere in a cross-model comparison.

### Controls for fairness

- **Budget.** A per-task cap in the same unit for all models. Tokens are not that unit:
  tokenizers differ. Cap on turns plus input and output bytes; report native tokens beside
  them. PLAN E8.3's "same 20k token cap" across a local model and Sonnet is not a matched
  budget.
- **Reasoning effort and decoding.** Fixed per model before the run, recorded, never searched
  on the test split. Report the setting next to every number.
- **Context window.** Either truncate all models to the smallest window in the comparison or
  report both; say which.
- **Contamination.** Tasks come from our seeded generator with held-out families (PLAN 3.4),
  so no model has seen them.

### Drift

- API models: pin the dated snapshot ID, and record the model ID **returned in each response**.
  On this box a "Claude" call routed through the local proxy can be answered by a fallback
  model (backend `AGENTS_SYSTEM.md`). A harness that trusts the requested ID can report a
  GLM run as a Claude run. Direct key only; a mismatch voids the episode.
- Local models: revision SHA, weights sha256, decoding config, container digest.
- **Sentinel set:** 20 fixed tasks run at the start and end of every batch and whenever a
  batch spans more than a day. If the sentinel pass rate moves outside its binomial interval,
  the batch is flagged and never pooled with others.
- Price sheet: read at run time, stored with its date in the manifest (already the plan).

### Cost normalisation

- Report, per passing task and never summed across kinds: native tokens by class; bytes in and
  out; wall-clock seconds; USD for API routes at the dated price sheet; GPU-only joules for
  local routes; USD for local routes only once the owner supplies a tariff, and then with
  hardware excluded and said so.
- The cross-model headline is pass rate and control effect at a fixed turn-and-byte budget.
  Cost per pass is secondary and always carries its price date.
- Unknown is unknown: no API-side joules, no local USD without a tariff.

### Another provider later

The adapter is the only new code. Under the backend policy a new provider "carries no tenant
data"; trapbench is synthetic, so that rule is met. Record the provider's own usage fields;
if it returns none, that provider gets no cost row.

## 5. Requirement 5: experiments ranked by decision value per cost

Decision value is my judgement; costs are the documents' own figures.

| Rank | Item | Decision it settles | Cost | Call |
|---|---|---|---|---|
| 1 | Diagnose the two watchdog kills (T7 smoke) | Whether any GPU plan on this box is real | zero | **Do first** |
| 2 | Scripted router, two stub cells, contract tests, hub-as-cell tests (ARCHITECTURE 10 steps 1-3) | Requirement 1 | zero | **Reinstate** (WORKPLAN 9 cut it) |
| 3 | Perturbation matrix on scripted backends (section 3.4) | Whether the robustness instrument works | zero | **Build** |
| 4 | Finish E8.1: record the price sheet, report the cold-start cache write | Minimum task size for a worker | zero | **Finish**; drop the 67% prediction |
| 5 | Count sessions with permission events on the other machine | Whether H1 lives | zero, one command | **Do** |
| 6 | E9-0 only: scripted catalogue of routes to a protected file | Which routes a hook and a ceiling stop; feeds requirement 2 | zero GPU | **Keep, alone** |
| 7 | Matrix on one local model (4B-9B) and one Claude tier | Which controls survive; H8 folded in | G3 (ii), a few GPU-hours, a Claude batch near C2's USD 40 | **Next spend** |
| 8 | H6 local screen: stub against local model, classes (a) and (b) | Whether any class leaves the Claude tier | G3 (ii), GPU-hours unmeasured | After 7 |
| 9 | T7 stage 1, arms B and A only | Whether "weights" stays an owner control | part of 12 GPU-hours | **Shrink or cut** (section 6, claim 8) |

**Cut:**
- E9-1 and E9-2 (13 GPU-hours). Self-described likely inconclusive; see claim 9.
- E8.4 dream dose.
- T7 stage 2, arm D, the LoRA step, arm 0 (the most expensive arm, a reference only, and the
  one the watchdog killed first).
- T4 consolidator training.
- H5 as a named hypothesis (keep the free read-off).
- VISION "Connecting a very strong model to everyone's local agents" and ARCHITECTURE 12.
  Both say they are untestable now; they cost reading budget (PRINCIPLES complexity budget).

**Defer:**
- E8.2 / H9. It needs E2.2's tasks, which need G1 or an unchecked licence; eight interleaved
  small agents; its own stop rule (all arms under 30%) is the likely result for a model of at
  most 9B.
- H2 (E2.1 to E2.3): needs G1.
- H1 replay, H3 and H4 as separate experiments: folded into the matrix.
- CL-Bench (G10), C3, C6.

### Internal contradictions between documents

| # | Topic | Conflict |
|---|---|---|
| 1 | H8 status | PLAN 67-68 and 186: confirmatory, a Holm family of two with H9. prereg/H8: exploratory (owner 2026-11-19). SCIENCE 5: only H1-H4 and H6 are confirmatory. SCIENCE 8 lists H8 beside the confirmatory questions. |
| 2 | H9 status | With H8 out, H9 is a "family" of one. No `prereg/H9.md`. PLAN 503 still says "outside both families". Owner ruling missing. |
| 3 | T7 design | PLAN T7 and H7: one stage, cap 32,768, arms A-D on "Full MATH-500", five arms. prereg/H7 and staged-t7-decision: two stages, n = 100 in every arm, primary `acc8k`, a D-null arm, off-target moved to stage 2. PLAN T9 cites the staged record; PLAN T7 was not updated. WORKPLAN steps 8-9 are unstaged. |
| 4 | The 12-point gate | Gate: A beats B by more than 12 points. H7's prediction and survive rule: at least 5 points. Minimum detectable effect at n = 100: about 12 to 18 points. So the test cannot confirm H7 as worded; a result of +5 to +12 with an interval above 0 meets "survive against B" and still stops as inconclusive. The kill needs the interval's upper bound below +5, i.e. an observed deficit. The record itself puts a pass at 0.3-2.4% if the true difference is 0 and 28-34% if it is +10. |
| 5 | Arm C selection | WORKPLAN step 8 chooses arm C's setting on smoke problems that are MATH-500 items; PLAN forbids choosing on the benchmark (audit code gap 3). |
| 6 | H1 threshold | PLAN 77 calls fewer than 200 events or 30 sessions a "Kill"; the audit and owner call it a precondition; WORKPLAN 65 says "precondition kill". |
| 7 | H1 corpus size | PLAN 8.2 and WORKPLAN 7: "155 events in one session". Results: 1,079 events, 1 session. README: "far below the 200-event threshold" (it is the session count that fails, not events). |
| 8 | Session counting | E1 finds 1 session; E8.1 finds 5 main sessions in the same corpus. Unexplained. |
| 9 | Claude budget | WORKPLAN 1 quotes "total ceiling USD 185 as in PLAN". PLAN 4.3: 145 proposed, 185 only with conditional C6, and "No second batch without a new approval". Binding default: USD 5 and 9 calls. Only C0 is approved, and C0 as designed does not fit in 9 calls (PLAN 4.3 caveat). |
| 10 | Local USD | H6 prices local energy at 240 W x time; the owner ruled local USD "n/a" for H7 and E9; no tariff exists. |
| 11 | Next GPU item | PLAN T9: after a T7 kill or inconclusive, "E9 is the next GPU item". PLAN 6.1 P5 and T8 priority: E8.3 local arm first. |
| 12 | Small-model subject | E9 proposes the 0.8B model as proposer; WORKPLAN step 10 calls 0.8B "likely uninformative" for E8.3; PRINCIPLES cuts any track "that needs a bigger local model to make its point". H8 predicts weak models gain under 5 points from memory, and E9 tests a memory benefit on the weakest model in the plan. |
| 13 | Model roles | PLAN 4.2 fixes hub = Opus 5.5 and cell = Sonnet 5.5, one snapshot per experiment. Requirements 1 and 4 need any tier in either role. PLAN 4.2's tier order ends "Opus, Fable" as execution tiers while the same table says Fable is "never running experiments". The "+5 from 5" question is still open. |
| 14 | Built or cut | PLAN 6.1 P1b, 6.3 items 9 and 13: `cell.py` and the board harness are zero-cost start-now work. WORKPLAN 9: cut. |
| 15 | Stale status lines | VISION: "one permission-replay ledger with nine unit tests. Nothing else below is built". PLAN header: "the repo has no commit yet". Actual: 13 modules, 89 tests reported, commit `972dee3`. |
| 16 | Memory floor | T7: kill below 10 GiB. E9: do not start below 20 GiB. Two smoke kills at 9.97 and 9.44 GiB while another snapshot shows 68 GiB available with the smoke running. The pool swings by tens of GiB from other tenants; a 300-second wall-clock training budget (E9) on that host is noise by design. |

## 6. Top claims: counter-argument, cheapest test, verdict

**Claim 1. "Centralised and decentralised are the same design with a different routing
table."**
- Counter: the table changes who executes, not who reads. The hub still plans and verifies
  every task on a remote API, and its tokens are unmeasured. Three worker kinds have three
  enforcement mechanisms. It is one file format, not one design.
- Cheapest test: in the scripted router, log planner and verifier tokens as cell cost; in C0,
  report the hub's share of tokens per passing task.
- Verdict: **weakened.** Survives only with the hub split into key, code and model (section 1).

**Claim 2. "Policy takes effect only with the owner's signature; no model can hold the key."**
- Counter: the signature proves who approved a file. It does not enforce the file. Enforcement
  is `cell.py` (not written) or Claude Code permission rules (bypassable for Bash, file tools
  outside the sandbox). A model that can read the owner's home can read an unprotected key.
  "Whether people read the diffs they sign" is conceded untestable (ARCHITECTURE 12).
- Cheapest test: E9-0's route catalogue aimed at the key file and at `policy.json`: which of
  the nine routes reach them from a Claude-cell configuration.
- Verdict: **weakened.** Keep the signature; drop the sentence about the key unless the key
  is off the box or on a token.

**Claim 3. "Local cells are private; raw logs never leave the cell."**
- Counter: section 2. True for local-model cells and only for content the hub does not read.
- Cheapest test: a sentinel string in a cell log; grep every byte the router hands to a hub
  model backend (scripted) across the matrix. Target zero. That is E3.5 pointed at the hub.
- Verdict: **weakened**; false as worded for Claude cells.

**Claim 4. H6: a local cell clears an 80% floor and the cascade costs at most 30% of
Claude-only.**
- Counter: the three task classes are the project's own generator's output. A class easy
  enough for a 4B model may be easy enough for the stub (the kill rule concedes this). The
  cost half is arithmetic. The remaining finding would be "a small model can do a task we
  designed for it".
- Cheapest test: stub against local model on class (b), 400 generated tasks, before any Claude
  spend.
- Verdict: **survives as a routing rule, weakened as a research claim.**

**Claim 5. H1: permission decay has a knee.**
- Counter: no data (1 session). The exposure metric has no harm model. Prior art for both
  halves exists (PLAN's own list). The owner's own usage pattern may produce no prompts.
- Cheapest test: the session count on the other machine.
- Verdict: **cut as confirmatory** until that count is at least 30. Keep the ledger as a tool.

**Claim 6. H3 and H4: dreaming must beat equal tokens; governance halves lock-in.**
- Counter: the vendor slide already shows search alone at 53% against wiki plus search at 54%
  to 61% for 64 times the tokens (file 11, talk claim). The likely answer is "search wins at
  small budgets", and the lint "checks provenance, not truth" (VISION), so governance may
  halve nothing against a wrong note with a real-looking source.
- Cheapest test: P3 in the matrix with arms {raw-log search, flat, governed}, one local model.
- Verdict: **survives, merged** into one experiment. Drop the dream arm unless governed
  memory first loses to search.

**Claim 7. H8: weaker models need imposed structure.**
- Counter: it rests on six points from one slide; the "threshold" is one model (Sonnet 4.6).
  The CL-Bench abstract says naive in-context learning beats dedicated memory systems (file
  10). On a home-made task, S2 beating S0 may only show that instructions help.
- Cheapest test: it is the model-agnostic matrix with the memory switch, on two tiers.
- Verdict: **survives as exploratory**; it is the best pilot for requirement 4. Fix its
  matched budget (bytes and turns, not tokens).

**Claim 8. "The staged T7 pre-test is a cheap, decisive test."**
- Counter: it is not decisive. By its own tables the gate passes under 3% of the time if the
  author's expectation (no real difference) is right, and an inconclusive result has "the
  same architecture consequence as a kill". The default decision (cells get decoding configs
  and adapters) can be taken today for nothing. The prediction (5 points) is below what
  n = 100 can resolve. It is a replication of someone else's result on a model the scope
  guard says we are not here to improve.
- Cheapest test: none needed. If it runs at all, run B and A only as the runtime smoke and
  report the difference with its interval, labelled descriptive.
- Verdict: **cut as a hypothesis test**; keep at most as a labelled smoke.

**Claim 9. "E9 exercises all three families on a hard metric with no model grader."**
- Counter: the pilot keeps one family (memory, D against R, six chains). Arm S and the
  cascade are cut. Its design says "With six chains [inconclusive] is the likely outcome".
  The proposer is a 0.8B model acting through one `set(file, name, value)` action, so the
  "attempt rate" measures a schema plus a planted temptation, and H8 predicts the memory
  effect is near zero for such a model. The metric is a 300-second wall-clock budget on a
  host whose free memory swings by tens of GiB. The licence is one word in a README and the
  dataset licence is unverified.
- Cheapest test: E9-0 (no GPU). It is the only part whose result is not predicted in advance.
- Verdict: **cut**, except E9-0.

**Claim 10. "Every result reports tokens, joules and USD per passing task; budgets are
matched."**
- Counter: joules are GPU-only on a shared GPU; API joules are unknown; local USD is "n/a";
  tokens are not comparable across tokenizers; E8.1's 93.7% cache-read share is unpriced.
  Three of four cost columns are empty or not comparable across tiers.
- Cheapest test: ten 60-second baseline power samples across a day. If the baseline's spread
  exceeds the expected per-task energy, baseline-subtracted joules are unusable on this box.
- Verdict: **weakened.** Keep the columns; stop calling it green until one cross-tier
  comparison is computable.

**Claim 11. "We build the measuring instruments first; the plan stays small."**
- Counter: section 0, point 1. Each owner request has added a track (T7, T8, T9) and the cuts
  made to pay for them were of things not yet built. The run gate is applied to experiments,
  never to documents.
- Cheapest test: a rule that no new hypothesis is written until one existing pre-registration
  is frozen and run.
- Verdict: **weakened.** The discipline is real on paper and absent in the ratio.

**Claim 12. H9: small models coordinate through a board only when handed its structure.**
- Counter: both outcomes are uninteresting at eight interleaved agents of at most 9B, and
  ARCHITECTURE adopts a board only on a separate 10% rule. The source run used 1,000
  frontier agents; PLAN concedes a negative result "says nothing" about that.
- Cheapest test: none worth its cost now.
- Verdict: **defer.**

## 7. Requirement 6: names

I cannot check trademarks, package registries, domains or the web from here. **Nothing below
is claimed to be available.** From memory only, and unverified: Helm, Dispatch, Convoy and
Flotilla are names already used by other software projects, so the last three carry collision
risk; someone must search before any is adopted.

| Name | Rationale |
|---|---|
| **Sortie** | One mission by one unit of a fleet, with an objective, a return and a debrief. Maps exactly to task spec, result and evidence bundle. Short, and a countable noun: "a sortie passed". My pick. |
| **Slipstream** | Streaming plus efficiency: a follower spends less energy behind a leader. Fits small cells drafting behind a strong hub. |
| **Muster** | Calling a fleet to roll-call and checking who is fit for duty. Fits floors, gates and held-out checks. |
| **Outrider** | A scout sent ahead of the main body under orders. Fits a cell with narrow authority. |
| **Squadron** | A small tasked unit inside a fleet. Fits "a few cells, one owner". |
| **Relay** | Streaming and hand-off between stations. Fits escalation between tiers. Generic; high collision risk. |
| **Flotilla** | A small fleet of small vessels. Fits "many small cells". Collision risk noted above. |
| **Convoy** | Many ships moving under one escort and one set of rules. Fits the signed ceiling. Collision risk noted above. |

"murmuration" names emergent flocking with no leader. The design is a star with a signed
ceiling, and VISION says it is "not ... a claim that agents self-organise". The current name
contradicts the design; any of the above is closer.

## 8. Ranked action list

1. Find the cause of the two watchdog kills before planning one more GPU-hour.
2. Get the owner's answer on later local commits (WORKPLAN question 1). It blocks every freeze.
3. Reinstate the scripted router and stub cells; split "hub" into key, code and model; make
   every model a cell; add the two hub-as-cell contract tests.
4. Build the perturbation matrix (P1 to P5) on scripted backends and define the control-effect
   metric in SCIENCE 4.
5. Amend PLAN 4.2 and section 3 for requirement 4: our own loop for all models, bytes and
   turns as the matched budget, returned-model-ID check, sentinel set.
6. Fix the confidentiality wording listed in section 2, and record that self-hosted
   environments and MCP tunnels do not hide session content from the model provider.
7. Reconcile the documents: H8 and H9 status, PLAN T7 against prereg/H7, H1 threshold wording
   and the stale counts, the USD 185 line, the status lines in VISION and PLAN.
8. Cut E9-1, E9-2, E8.4, T7 stage 2, arm 0, arm D, the LoRA step and T4. Keep E9-0.
9. Decide T7 stage 1: drop it, or run B and A as a labelled smoke with no hypothesis attached.
10. Run the session count on the other machine; park H1 unless it reaches 30.
11. Finish E8.1 with a recorded price sheet; report the cold-start figure only.
12. Ask the owner for one 4B-9B model (G3 ii), a tariff or a ruling that local USD stays
    "n/a" (then rewrite H6's cost criterion), and a name.

## 9. The one research question I would own

**At a matched budget, which single control (provenance-governed memory, a signed ceiling
with a deny list, or cascade escalation) reduces the pass-rate drop under its matched
perturbation, and does the answer change sign between a local model of at most 9B and the
Claude tiers?**

Why this one: it decides which of the three families survive, whether controls must differ
by model strength (H8 generalised), and whether the model-agnostic harness is worth having.
Every other experiment in the plan is either a special case of it or does not change a build
decision.

## 10. Not checked

- No code was read or run; "89 tests" and "1,416 lines" are a report's figure and a `wc` count.
- SCIENCE was not read in full; a contradiction inside it could be missed.
- The power and gate figures are quoted from the audit and the staged record, not recomputed.
- Platform statements are file 07's, which read several pages only partially and on one date.
- Name collisions are from memory and unverified. No trademark, registry or web check.
- Whether the owner's sessions run in skip-permission mode is inferred from a policy file, not
  measured.

verified: 972dee3 (plus working tree) 2026-11-19
