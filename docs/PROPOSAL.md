# Sortie: project proposal

2026-11-19. Author: Fable 5.2 (planner). Status: **proposal; nothing here is approved by being
written.** Repo is still named `murmuration` (rename: `docs/reports/rename-plan.md`).
A sortie is one mission by one unit of a fleet: an objective, a return, a debrief. Here: task
spec, result, evidence bundle. The name is **unchecked**: "sortie" is a common English and French
word and other software very likely uses it (from memory, unverified; no registry, domain or
trademark search was done).

Assumption, stated: the owner asked for a project "based on all the feedback". I read that as
adopting the cuts recommended by adversarial review 2 and the GPT consult. Every cut below is
reversible and **awaits the owner's explicit ruling**. Sources: `docs/reports/` and `docs/*.md`.
Every cost is an **estimate** unless marked measured.

**Amended 2026-11-20, Opus 5.5, after the GPT and Cursor/Grok reviews**
(`docs/reports/review-integration.md`). "Verified" and "built" here mean the code passed a gate,
not that anything is known about models: evidence status uses `ALIGNMENT-INTEGRATION.md` 1
(INSTRUMENTED / PILOTED / EVIDENCED / NOT STARTED / OUT OF SCOPE), and nothing is PILOTED or
EVIDENCED. Joules are a raw local field, never a headline. "Lease" throughout is a design: no lease
object exists in the code (`ARCHITECTURE.md` 9a), so "out-of-lease action" is not yet computable. The GPT review would cut broad perturbation sweeps, which section 2's
matrix is; that disagreement is for the owner (`WORKPLAN-ALIGN.md` 8a). T7 and H1 wording updated.

## 1. Thesis, and what Sortie is not

When work crosses an agent boundary (a subagent returns, a session ends, a cell fails), state is
lost or goes stale. Sortie tests one mechanism for that: a **handoff** that is versioned, linked
to its source and revocable, against the simpler thing, search over the raw log, at the same
budget. The system around it is deliberately small: plain router code, the owner's key, and
models that are all "cells" under the same contract. If the simple baseline ties, we ship the
simple baseline.

Not: a frontier-lab model, pretraining, or a local model trained to imitate one; a framework,
bus or simulator; a claim that agents self-organise; a privacy product; a "green" claim for
hosted models (their energy is not observable to us).

## 2. The one research question

**At a matched per-task budget, do versioned, provenance-linked, revocable handoffs lose less
pass rate under perturbation than equally funded raw-log retrieval or free-form notes, and does
the answer differ between a local model (at most 9B parameters) and a Claude tier?**

- Unit: one (task, seed) pair. Pass: the task's deterministic check. No model grader.
- Conditions: clean, plus exactly one of P1 requirement changes mid-task; P2 noisy requirement
  (model-only baseline); P3 injected wrong or stale memory; P4 a cell fails or is slow; P5
  permission denial with a safe allowed route.
- Primary metric, **control effect**: `CE(a,k) = D(base,k) - D(a,k)` in percentage points, where
  `D` is clean pass rate minus perturbed pass rate, paired by task and seed; 95% cluster bootstrap
  by task. Beside it: harm rate (fraction of episodes with a canary hit, protected-file change or
  out-of-lease action), recovery cost (tokens per pass), worst case over k.
- Budget: the same cap per task for every arm, in turns plus input and output bytes; native
  tokens reported beside it. Memory reads, note-writing and any offline consolidation are charged
  inside the cap.

**Ship rule** (margins are design choices; the owner may change them before the freeze):

| Outcome on P1, P3 and P4 | Decision |
|---|---|
| CE interval excludes 0, point estimate at least 10 points, clean pass rate within 2 points of retrieval, harm rate not higher | Handoffs become the default; build the store |
| Interval inside ±10 points, or retrieval better | Ship retrieval; delete the handoff store |
| Anything else | "Not shown". Retrieval stays the default. One predeclared expansion (24 held-out tasks x 3 repetitions), then stop |

Honest power: at the first-pass size only effects of about 15 points are visible.

## 3. Architecture in plain terms

- **Owner key.** Signs each policy. A signature shows who approved a file; it enforces nothing.
  Keeping the key from every model holds only if it is off the box, on a token or
  passphrase-protected.
- **Router code.** Deterministic, started by the owner. Reads task specs, launches cells, runs
  checks, writes cost lines. Never calls a model to route.
- **Every model is a cell,** the strongest included: a folder with a prompt, a policy, a budget
  and an append-only hash-chained log. Three kinds (plain code, local open-weight model, Claude)
  share a file format, **not** a security property.
- **Planner cell.** Claude orchestrating local models is a planner cell that writes task specs.
  It never launches a process. Claude can equally be a worker or verifier cell.
- **Capability lease.** A task-scoped, expiring list of allowed actions, checked **at the tool
  boundary when the action executes**; default deny, deny wins. No decay rule, no learned rules.
- **Evidence bundle.** Result, check output, cost (tokens by class, seconds, joules or null, USD
  or null), model ID, lease hash, log range. Missing is null, never 0.
- **Independence rule.** A result is not verified by a cell with the same model ID unless a
  deterministic check exists.
- **Matched budgets.** Child budgets are reserved before dispatch; planner and verifier tokens
  are cell cost, so "decentral" cannot look cheap while the planner spends the tokens.

## 4. The three idea families, as controls

| Family | Simplest version kept | Baseline it must beat | Cut (reversible, ruling pending) |
|---|---|---|---|
| Memory | One JSONL file; each record has a source pointer, a version and a supersede or revoke link | Raw-log search, same cap | E8.4 dream dose, dreaming arms, T4 consolidator training, wikis, E9 memory arms; H3, H4 and H8 merged into the matrix (H8 exploratory, owner 2026-11-19) |
| Cost efficiency ("green" only where joules are measured) | Four cost columns on every result, one routing inequality, static cheapest-qualified tier | Fixed strongest-tier policy | Idle fraction as a headline, E8.1's 67% prediction, predictive routing; H2 and H9 deferred |
| Adaptive policies | Signed static ceiling, deny list, expiry, task-scoped lease | Prose rule; name-based deny rule | Permission decay and H1 as confirmatory, learned rules, coupling heuristics |

Also cut: T7 as a hypothesis test, E9-1 and E9-2, H5 as a named hypothesis, the "one strong hub
for everyone's cells" sections (VISION, ARCHITECTURE 12).

## 5. Minimal experiment program

Ordered by decision value per cost. One GPU-hour is at most 0.86 MJ at the 240 W supply rating
(upper bound; measured GPU idle is 5 W over one 29 s sample). Local USD is "n/a" until the owner
gives a tariff. Agent build tokens run on a subscription: USD unknown, not zero.

| ID | What; decision it settles | Built / to build | Cost (estimates) | Kill or stop |
|---|---|---|---|---|
| S0 | Isolate the host-memory leak (about 22 MB per step, not visible to torch). Settles whether any local-GPU item is real | Watchdog, memlog, power sampler exist. Sample and pad diagnostics showed no leak | At most 1 GPU-hour (0.86 MJ) inside the approved G9 cap; USD 0 | Two further bounded diagnostics fail: park every local-GPU item; scripted and hosted work continues |
| S1 | Router and cell contract; "every model is a cell" holds in code | `cell.py`, `router.py`, 11 tests: uncommitted, **unverified**. To build: policy signature check | 0 GPU; about 0.4M agent tokens | A new file type is needed: the symmetric claim is dropped |
| S2 | Matrix instrument on scripted backends | `perturb.py` (7 tests, unverified), `runner.py`, trapbench. To build: floor stub and oracle per batch | 0 GPU; about 0.4M agent tokens | Floor passes or oracle fails: instrument void, fix before any model run |
| S3 | E8.1 finished: cold-start cache write per subagent, priced | `tokens.py` verified. To do: record the dated price sheet | 0 | No price sheet readable: USD stays null, report tokens only |
| S4 | H1 lives or stays parked | `ledger.py`, `hazard.py` verified | One salted command on the other machine | Fewer than 30 sessions with permission events: H1 stays parked (30 is a recruitment target, not a validated sample size) |
| S5 | E9-0 only: scripted catalogue of nine routes to a protected file, plus the canary test (section 7) | To build | 0 GPU; about 0.4M agent tokens | None; a coverage table is the result |
| S6 | Handoff store, raw-log search arm, notes arm | `memlint.py` verified. Store and arms to build | 0 GPU; about 0.6M agent tokens | Cannot be charged inside one cap: redesign before S7 |
| S7 | **Headline run.** 10 tasks x 2 seeds x 6 conditions x 2 arms (retrieval, handoff) = 240 episodes per model; notes and no-memory arms only where those two differ | Needs S0-S2, S6, a frozen pre-registration | Per model at most 9.1M tokens (cap 30,000 in + 8,000 out per episode, calibrated on a pilot). Local: cap 8 GPU-hours, at most 6.9 MJ, USD n/a. Claude: ceiling USD 40 proposed, energy n/a | Section 2 ship rule |
| S8 | Cross-model blocks: a second open-weight family, later GPT | Adapter per backend to build | Same caps per block; each its own approval | Sentinel drift: block reported alone |
| S9 | H6 local screen (stub against local model) | After S7 | Unmeasured | Local model ties the stub: class stays on Claude |

Built and verified (Opus, three passes, accepted with notes): manifest, stats, ledger, hazard,
tokens, memlint, coupling, trapbench, runner, CLI; 85 tests ran green 20 times. The tree now
holds 110 test functions (counted, not re-run here); the newer ones are unverified.

Parked or cut:
- **T7:** parked; proposed cut (GPT review, 2026-11-20). Labelled runtime smokes of arms 0, B
  and A ran (`docs/reports/T7-smoke.md`): 0/20, 8/20 and 1/20 at an 8,192-token cap with most
  generations cut and different decoding per arm. Configuration results, not an edit effect.
  Stage 2, arm D and the LoRA step are cut.
- **E9:** only the scripted stage E9-0 (as S5). E9-1 and E9-2 (13 GPU-hours) are cut.
- **H1:** parked until 30 sessions exist (S4); not a headline even then.
- **E8.1:** finish with a price sheet (S3).

## 6. Cross-model protocol

1. **One loop for every model:** our own agent loop, one task spec, one tool schema, one adapter
   per backend. "Claude Code as shipped" is a separate, labelled product arm.
2. **Blocks.** Block by model and by task. Freeze commit, task text, hidden tests, tool schemas
   and mechanism settings. Pilot on a practice family; conclusions only from held-out families.
3. **Caps.** Per task and arm: turns plus input and output bytes, and wall seconds. Calibrate on
   the pilot, then freeze. Timeouts and rejected patches count as failures.
4. **Instrument checks per batch.** A scripted floor and a scripted oracle; if the floor passes
   or the oracle fails, the batch is void. Tasks enter only if the weakest model scores above
   30% and the strongest below 85% clean.
5. **Drift.** Models interleaved, arm order rotated. A 20-task sentinel set runs at the start
   and end of every batch; a move outside its binomial interval makes the batch a separate block.
6. **Returned-model-ID check.** Direct key only. The local proxy on this box can answer a
   "Claude" request with another provider's model, so the ID returned in each response is
   compared with the requested one; a mismatch voids the episode. Local models: revision SHA,
   weights sha256, quantisation, runtime, container digest.
7. **Costs, never summed across kinds:** native tokens, bytes, seconds, USD at a dated price
   sheet. Joules: whole-GPU sampled power for local runs; **hosted energy is "n/a"**.
8. **Local open-weight models** run through the existing container; Unsloth (the owner's named
   tool) needs gate G2b first. **GPT later:** synthetic tasks only, its own approval.

## 7. Confidentiality, stated accurately

**No Claude shape keeps session content from the model provider.** Every prompt, every file a
Claude cell reads and every tool result is sent to the provider.

| Shape | What it does give | What it does not |
|---|---|---|
| Self-hosted environments | Execution, checkout and files at rest on your host | Transcript and control plane stay at Anthropic; not available with Zero Data Retention |
| Claude Code sandbox | Limits on what shell commands touch | File tools, hooks and MCP servers run outside it |
| MCP tunnels (research preview) | A private server reached without an inbound port | Every tool result returned becomes session content; a third party is on the path; end-to-end encryption unknown |
| Local open-weight cell | Its raw log and inputs passed by path and hash stay local | Anything a Claude planner or verifier reads |

Source: `research/07`, which read several pages only in part. Neither self-hosted environments
nor tunnels are used today; adopting them is an owner decision.

**Canary test plan** (scripted first, zero cost): plant unique synthetic strings in a local
cell's log, in a file passed by hash, in a tool result and in a placeholder credential. Search
for them in every byte the router hands to any model backend, in adapter request bodies, in
subprocess egress (container with no network), in logs and in `runs/`. Target for the first two
on a local-only route: 0 hits. Hits on any Claude route are expected and reported as "reaches
the provider". Also test: lease revocation takes effect on the next action; a lost tunnel fails
closed (only if tunnels are adopted).

## 8. Model roles and routing

| Work | Model | Never |
|---|---|---|
| Research, discovery, plan, pre-registrations | Fable 5.2 | bulk, running experiments |
| Orchestration and verification | Opus 5.5, fresh context | verifying its own work without a deterministic check |
| Coding | Sonnet 5.5; Opus 5.5 after two failures, or for security and refactors | commit, push, install |
| Paper drafting from frozen results | Sonnet 5.5 | typing a number from memory |
| Bulk chores | a script, else Haiku 5.5 | judging |
| Cells under test | scripted, local open-weight, Claude tiers, later GPT | carrying tenant data |

Routing: computed answer, then stub code, then local model, then Haiku, Sonnet, Opus. The
cheapest tier whose held-out pass rate clears the class floor does the job; escalate one tier on
a failed check; no unchanged retries. Open: the owner's "+5 from 5" is still not understood.

## 9. Honest status

- **Verified:** the Wave 1 instruments above. **Unverified:** `cell.py`, `router.py`,
  `perturb.py`, the T7 generation scripts, every doc edit made today. (2026-11-20: cell, router
  and the EP-1 rung 0 have since passed gates, but the model-facing layer was rejected once and its
  fix is not re-verified, and the instrument pilot has not run.)
- **No hypothesis has been tested. No pre-registration is frozen.**
- **Failed or blocked:** the permissions corpus is too small (1,079 events, 11 denials, but 1
  session; 30 is a recruitment target). The T7 smoke was killed repeatedly by the host-memory
  watchdog; the leak's cause is not isolated. Smokes of arms 0, B and A later completed (0/20,
  8/20, 1/20 at an 8,192 cap, most runs cut): configuration results under a cap, not an effect
  estimate (updated 2026-11-20).
- **Measured once, exploratory:** in 42 local sessions cache reads were 93.7% of tokens
  (unpriced; one user, one machine).
- **Prior art:** orchestrator and workers, cascades, signed policy, governed memory with
  provenance, dreaming and consolidation all exist or ship. **Possible small contributions:** an
  equal-budget test of handoffs against retrieval under seeded perturbations, and open
  instruments. "Not found in a shallow search" is not novelty.
- **Document debt:** about 59,000 words of docs against about 1,800 lines of code. Rule
  proposed: no new hypothesis until one pre-registration is frozen and run.

## 10. One page for the Claude Code team (gate G8; not sent)

**Problem.** State crossing an agent boundary is lost or stale. **We bring** open stdlib
instruments and a pre-registered test the team can run on data we never see. **We do not have**
any result.

| Ask | Hypothesis | Evidence today |
|---|---|---|
| A handoff record for subagent and session boundaries: versioned, source-linked, revocable | It loses fewer points than equal-budget retrieval under changed or stale state | None. Instrument drafted on scripted backends, unverified |
| Per-cell cost in the result: planner, verifier and worker tokens by class, and the model ID that answered | Planning and cache reads dominate cost per passing task; cold start sets a minimum task size | One corpus: 93.7% of tokens were cache reads, unpriced |
| Task-scoped, expiring capability leases checked when a tool executes | They block routes that prose and name-based deny rules miss, at a small prompt cost | None. Route catalogue (S5) not built. H1's decay idea is parked for lack of data |

**How to check us:** commands, seeds, tree hashes, pre-registration files.

## 11. Approvals and gates

| Gate | Exact scope | Cap | Status | Blocks |
|---|---|---|---|---|
| Rulings on the cuts (sections 4, 5) | Each cut, yes or no | none | **Pending** | Doc clean-up |
| Later local commits | `murmuration` only, no push | none | **Open** (owner question 1) | Every freeze; the rename |
| Rename to Sortie | `rename-plan.md`, only with no job running | none | Name decided; execution pending | nothing |
| G9 | T7 inference, in-process | 12 GPU-hours; stop below 10 GiB MemAvailable | Approved | S0, T7 smoke |
| G3 (ii) | One open-weight model, 4B-9B, ID and licence confirmed first | about 8-18 GB disk | **Not approved** | S7 local, S9 |
| G5 for S7 | Local headline run | 8 GPU-hours proposed | **Ask** | S7 local |
| G7 | Claude batch for S7, direct key with usage fields | USD 40 proposed; binding default USD 5 and 9 calls | **Ask** | S7 Claude |
| G2b, G6 | Unsloth packages; training | n/a | Not requested | S8 via Unsloth |
| GPT block | Synthetic tasks, one adapter | to set | Not requested | S8 GPT |
| Signing key | Created and held by the owner | n/a | Open | Signed leases |
| G8 | Licence, any push, pitch, publication | n/a | **Blocked** | Section 10 |
| Never | Shared endpoints, other repos, deletion, tenant data in any prompt | n/a | n/a | n/a |

## 12. Timeline, in sessions

No dates until throughput is measured.

| Session | Content | Needs |
|---|---|---|
| 1 | S0 diagnosis; Opus verifies S1 and S2 code; S3; S4 | nothing new |
| 2 | Rename (no job running); commit; S5; S6 | commit ruling |
| 3 | Full scripted matrix with floor and oracle; caps calibrated; headline pre-registration frozen | commit ruling |
| 4 | Local pilot on the practice family; calibration band | G3 (ii), S0 resolved |
| 5 | S7 local | G5 |
| 6 | S7 Claude block | G7 |
| 7 | S8 blocks; S9 | separate approvals |
| 8 | Paper draft (Sonnet, Haiku), claims check (Opus), pitch | G8 |

Not checked: no test or code was run; the leak figure and smoke history are as relayed by the
parent; the documents were being edited while read.

verified: 972dee3 (plus working tree) 2026-11-19; amendments verified: 36bab4b (plus working tree) 2026-11-20
