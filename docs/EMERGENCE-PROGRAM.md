# Emergence program: practice versus enforcement

2026-11-19. Author: Fable 5.2 (planner). Status: **proposal. Nothing here is approved, built or
run.** Repo is still `murmuration` (rename pending). This file re-centres `docs/PROPOSAL.md`; it
does not delete it. Decisions for the owner: `docs/reports/emergence-decision-memo.md`.

Reading rule: every outside number is a **lead**. Most papers were read as abstracts only (notes
15, 16, 17). Vendor figures are single runs with no independent replication (note 14). Costs are
estimates unless marked measured.

## 1. Why the proposal changes

The owner's goal: improve agent performance and collaboration, test new concepts such as
dreaming, and make models **less reliant on the harness and more on practices they can adopt**,
so that positive emergent results appear. `PROPOSAL.md` answered a narrower question (handoff
record against raw-log search) and cut dreaming, the shared board and most complex-systems tests.
Those cuts were right about cost and wrong about the centre: they removed what the goal names.

The new research notes make one cheap, falsifiable test possible:

- Practices matter, and in both directions. Anthropic reports that telling a model a memory folder
  exists was enough for strong models; a "record only failures" rule made them lose much of the
  gain; a prompt to read memory and test theories "nearly doubled" a weaker model's score (note 14,
  post read in full). Role and CEO prompts "did not make much difference" in a 12-hour build
  (note 14, about 90% read).
- Conventions decide outcomes. Several agents writing one table kept 41 of 57 facts; one agent per
  page kept 57 of 57. 18 of 30 agents chose the same branch name (note 14).
- **Nobody we could find compares a norm given as an instruction with the same norm enforced in
  code, on the same task** (note 16, abstract-level search of 31 sources). That is the gap. A
  shallow search is not proof of novelty.

What we must not overclaim:

- The 1,000-agent Fermat run was not a no-harness result. Agents had lead and helper roles, 60
  target statements, a route sketch, 47 proved lemmas, Lean as a verifier and a full safety
  harness; the post calls it a "toy experiment" (notes 10, 14). Across the talks the harness was
  removed for coordination and memory and kept for blast radius (note 13).
- The swarm's 266 vulnerabilities against 21 used 27M tokens against 6.5M (note 14): about 9.9
  against 3.2 per million tokens (our arithmetic). Threefold, not thirteenfold; not budget-matched.
- The wiki curve's x-axis is dreaming **sessions** (2 to 128) at a nominal 1M-token budget each,
  "not measured spend". Tokens actually spent are unknown.
- Multi-agent is not free: returns diminish once a single agent passes about 45% (a regression
  coefficient, not a sharp line); errors amplify 17.2x in independent teams against 4.4x with a
  central check; at most nine agents were tested (note 15, full text opened).
- CL-Bench's paper says plain in-context learning beats dedicated memory systems; ACE is tenth on
  gain at the highest cost (note 14, Table 1 opened).

## 2. Thesis and the one headline question

**Thesis.** A harness does two jobs. Containment (sandbox, leases, signed ceiling) stays in code.
Coordination and memory discipline (claims, ownership, checking, hygiene, consolidation) may need
only a short written practice, if the model is capable enough. If so, the practice is portable to
any harness and the code can go. If not, we learn which rules must stay in code, for which models.

**Headline question.** For each named collaboration practice, does giving it to the models as a
short playbook produce the same team outcome as enforcing it in code, at the same budget; how does
that depend on model capability; and which practices produce positive emergence and which produce
negative emergence?

### 2.1 The seven practices

| ID | Practice | Playbook line (card text, shortened) | Enforcement in code | Primary measure | Negative effect to watch |
|---|---|---|---|---|---|
| A | Claim before work | Claim one unclaimed task before starting; release it when done or stuck | Router rejects a second claim; claims expire | Duplicate-work rate; claim collisions | Claims never released |
| B | One writer per page | Write only pages you own; quote sources verbatim | Router refuses writes to another owner's page | Fact-retention rate | Bottleneck on one owner |
| C | Unique names | Name branches and files with your agent ID and task ID | Router assigns the name | Name-collision rate | Herding on one name |
| D | Write, then read, before acting | Post your intent, re-read the board, then act | Router blocks the action until the fresh board is read | Useful-read fraction; duplicate work | Ritual reads that change nothing |
| E | Verify before done | Not done until the check passes; a different agent verifies | Router runs the check; same-model verification refused | Error pass-through with injected faults | Verifier shares the author's blind spot |
| F | Memory hygiene | Every note links its source; supersede, never rewrite; facts expire | Lint rejects notes without a source; code applies expiry | Poison adoption; stale-fact reuse; sprawl | Rewrite collapse; over-deletion |
| G | Consolidate ("dream") | At session end re-read the log, re-check each note, append corrections | Scripted re-verify pass run by the router | Section 4 | Entrenched errors; cost |

A handoff record (the old headline) is practice F applied at an agent boundary. It stays, as one
row.

### 2.2 The harness-dependence index

Let `Y` be a team outcome where higher is better, measured per team episode: for example the
fraction of work slots that produced a distinct passing task (unit: passing tasks / slots, both
counts shown). Four arms give `Y_none`, `Y_play`, `Y_code`, `Y_both`.

- **Playbook-to-enforcement ratio** `R = Y_play / Y_code` (dimensionless; numerator and
  denominator reported). Simple, but misleading when `Y_none` is already high.
- **Harness-dependence index** `HDI = (Y_code - Y_play) / (Y_code - Y_none)`. 0 means the playbook
  alone recovers everything enforcement gives. 1 means the playbook does nothing. Below 0 means the
  playbook beats enforcement. Above 1 means the playbook hurts.
- `HDI` is defined only when the 95% interval of `Y_code - Y_none` excludes 0. Otherwise the
  practice is not needed at this capability, or does not help; `Y_none` says which.
- Residual harness value: `Y_both - Y_play`. Cost: tokens and USD per passing task, each arm.
- Intervals: paired cluster bootstrap over task sets, 10,000 resamples, percentile.

**Capability prediction, written before any data** (from slide-read memory scores and
Anthropic's steering notes, so a lead). Three regimes: below a threshold the model does not adopt
the card (`HDI` near 1); in a middle band the card works (`HDI` near 0); above it the model
follows the practice unprompted (`Y_none` near `Y_code`) and a prescriptive card may hurt. The
prediction fails if `HDI` is flat across tiers.

### 2.3 Emergence, defined so it can come out wrong

**Emergence gain** `EG = Y_team - Y_nominal`, where the nominal group is the same number of agents
with the same total budget and no shared medium, results pooled and de-duplicated. Positive
emergence is `EG` with an interval above 0. Everything else is description.

Order parameters, all computed from logs, no model judge (definitions from note 16 section 8 and
`SCIENCE.md` 1.5; they are our proposals, not validated measures):

- Work-distribution entropy (bits / log N): equal split or monopoly. High with duplicates is waste.
- Specialisation index (0 to 1): role differentiation. Needs a fixed task taxonomy.
- Read:write ratio (reads / writes) and useful-read fraction (new-row reads / reads):
  coordination or polling.
- Claim-collision rate (collisions / claims) and duplicate-work rate (duplicates / completions).
- Convergence time (turns until a fraction f agree): convention formation. f is a free choice.
- Information-cascade length (hops of one fact): herding and poison spread.
- Fact-retention rate (facts kept / facts planted): loss on shared writes or consolidation.
- Memory sprawl (files, characters, characters per used fact, dead-weight fraction).
- Poison-adoption fraction and correction half-life (tasks to halve it): lock-in.
- Error correlation rho (pairwise failure covariance): effective number of independent agents.

Positive emergence means higher team pass rate, lower collision and loss, lower cost per pass.
Negative emergence means lock-in, herding, collusion or sprawl. Both are measured in every run.

## 3. Arms, budgets and how the architecture carries them

**Arms.** `none` / `playbook` / `code` / `both`. One practice varied at a time.

- The `none` arm carries a **neutral card of the same byte length**, so a playbook effect cannot
  be a prompt-length effect.
- Budgets are matched per team episode in turns plus input and output bytes; card text, board
  reads, rejected actions and any offline pass are charged inside the cap. Native tokens are
  reported beside it.
- Scoring is deterministic: task checks, canaries, counts from the log. No model grader.
- Every batch includes a scripted floor that must fail and a scripted oracle that must pass.
- Team size 4, never above 8 in this program (the scaling paper tested at most nine).
- Stressors from `PROPOSAL.md` are kept as conditions, not as the headline: P3 planted wrong
  memory, P4 a cell fails, P1 a requirement changes mid-task (the lock-in probe).

**A practice card is one file.** `practices/<id>.md`: an ID, a version, the card text (at most
600 bytes), the name of its enforcement check, and its measures. The run manifest records its
sha256. Swapping a card is editing a file; an arm is a pair (card or neutral card, enforcer on or
off). Seven cards are under 5,000 bytes, far below the size caps of agent instruction files
(32 KiB and 25 KB in notes 15 and 14).

**No new framework.** The design in `ARCHITECTURE.md` already has the two places a practice can
live:

- *Instruction:* the router appends the card to the cell's `prompt.md` at dispatch. The prompt
  hash changes and is logged.
- *Enforcement:* the router already checks every action against the cell's policy when the action
  executes (`router.py`, default deny). A claim lock, a page-ownership check or a lint is one more
  predicate at that same boundary.

What is missing is small: a shared board (one SQLite file behind one logging function; `PLAN.md`
5.1 named it `board.py` and `WORKPLAN.md` 9 cut it), a turn loop for a team of cells, and the
order-parameter counters. The star stays: cells reach the board only through the router.

## 4. Dreaming as one practice, on a compute-matched ladder

Dreaming is practice G. It gets the same treatment: playbook, code, both, and a baseline that
ignores it. Design from note 17.

**Seven arms**, same task stream, seeds and model:

| Arm | What | Role |
|---|---|---|
| A | No memory | Floor |
| B | Raw-log memory: the full history in context when it fits the cap, else retrieval | **First baseline.** CL-Bench's finding is that this may win |
| C | The dream's token budget spent on extra retrieval or retries | Equal-token control |
| D | Placebo dream: same tokens, notes from shuffled or other-task transcripts | Controls for "any extra text" |
| E | Scripted re-verify: replay stored claims against the environment, withdraw failures; no model | The cheap control; the code-enforced form of G |
| F | Model dream | The playbook form of G |
| G | Model dream followed by scripted verify | Both |

**Five rungs**, in cost order. Do not advance until the previous rung has a pre-registered primary
contrast and a measured spread; stop the ladder if rung 3 fails.

| Rung | Question | Kill |
|---|---|---|
| 1 | Does scripted re-verify (E) cut repeated errors against raw log (B) and placebo (D)? | Interval includes 0 and its upper bound is below the smallest effect of interest |
| 2 | Poisoned memory: correction half-life and false-correction rate, including a "confident poison" | Poison-hit rate not below B, or true notes deleted above a preset tolerance |
| 3 | **Core:** does F beat C at equal total tokens (online plus offline), and D? | F not better than C by the minimum detectable effect |
| 4 | Dreamer and solver crossed: local or API dreamer, local or API solver | API-dreamer gain below the detectable effect, or dearer per point than arm C |
| 5 | Shared memory: transfer between agents against contamination and lock-in after a mid-stream change | No transfer gain over private memory, or contamination exceeds it |

Measures: task accuracy; tokens per correct answer, with dream cost amortised over H future tasks
and the break-even H reported; fact retention before and after each pass; sprawl. Leakage guard:
dream only over training episodes, evaluate on held-out instances, plant canary strings in gold
answers and search memory for them.

Honest prior: E and B are likely hard to beat at small budgets. That is why E runs first.

## 5. Complex-systems concepts as testable claims

A concept enters only with a quantity, a cheapest test and a baseline that ignores it. Status
words: BUILT, PLANNED (in this proposal), DEFERRED.

| Concept | Quantity | Cheapest test | Status | Where the analogy breaks |
|---|---|---|---|---|
| Stigmergy: a shared board | `EG`; useful-read fraction; duplicate work; idle-turn fraction | Team of 4 on the board, practices A and D, four arms; single-agent polling null | Board PLANNED. **Proposed reinstatement** (was H9 and E8.2, cut) | A table row is exact and global, not a decaying local trace; agents read prose, so this may be ordinary messaging through a file |
| Near-decomposability: coupling | Co-change coupling against file overlap; `EG` by coupling tercile | On public git history, no model; then split tasks by coupling in the team runs | Counter BUILT and verified. Gate test **proposed reinstatement** (needs a clone gate) | Co-change records habits, not dependencies |
| Polycentric local rules | `HDI` per practice; harm rate under a signed ceiling | The four-arm design itself: rules agents hold against rules imposed | Lease check BUILT, unverified. Cards PLANNED | Ostrom's users write their own rules and have a stake; ours are handed down and agents have none. A later arm lets the team write its card |
| Requisite variety | Distinct situations against distinct responses; unhandled-case rate | Count board states a card does not cover; replay at two key granularities | Ledger BUILT; corpus too small. Card coverage PLANNED | Counting treats all cases as equal; a few are catastrophic |
| Lock-in and path dependence | Poison-adoption fraction; correction half-life; convention flip rate | Planted wrong note and a seeded deviating convention, with and without a "challenge what fails a test" card | Trap benchmark and lint BUILT and verified. Probe PLANNED. **Proposed reinstatement** (was H4) | One small store has weak increasing returns; same-model agents are correlated by construction |
| Diminishing returns; value of computation | Marginal pass rate per token; break-even H | Cost per pass in every arm; dose curve only after ladder rung 3 passes | Cost columns BUILT. Dose curve DEFERRED | Our budgets are tiny next to a 128-session curve |

**Reinstated as proposals, pending the owner's ruling:** the shared board harness; the
prompted-only memory arm that `PLAN.md` T8 cut (it is the playbook arm); scripted re-verify and
the model dream arms (was H3); shared-memory lock-in (was H4); the capability threshold (was H8),
now in the headline. **Still cut:** dream dose until rung 3 passes, criticality, scaling laws,
debate, personas, topology sweeps, cache sharing, weight edits, anything at 1,000 agents. Error
correlation is a free read-off, not a test.

## 6. Test staging, stated honestly

**Scripted agents cannot adopt an instruction.** They obey or ignore by construction. They can
only validate instruments. Adoption needs real models. Three rungs.

**Rung 0: scripted, no cost.** Scripted agents with a set compliance probability q in {0, 0.5, 1}.
The pipeline must return `HDI` near 1 for q = 0 and near 0 for q = 1, no duplicate work executed
under enforcement, a failing floor and a passing oracle. A scripted consolidation comparison (rewrite
against delta-append on a lookup table) checks the fact-retention counter. **No rung 0 number is
a finding**: it restates what we coded.

**Rung 1: a small Claude tier through the API.** Named batch **EP-1**.

- Design: practices A and C in one allocation micro-task. 4 agents, a board with 6 open tasks, 2
  rounds (claim and name; then act on the updated board). Outcome: distinct passing tasks / 4 work
  slots. Under `code` a rejected agent can lose its slot, so enforcement is not free. 15 task
  sets, each run under all four arms.
- Calls: 4 agents x 2 rounds x 4 arms x 15 task sets = 480, plus 20 for a returned-model-ID check
  and one re-run of infrastructure aborts. **500 calls.**
- Caps per call: 2,000 input tokens, 300 output tokens; at most 1.15M tokens in total.
- Model: Haiku 5.5, direct key, returned model ID checked on every response.
- **Proposed ceiling: USD 5 and 500 calls.** The policy default is USD 5 and 9 calls per named
  batch. We ask to keep the USD default and change only the call count: one team episode is 8
  calls, so 9 calls cannot hold one episode per arm. Estimate, not a quote: at the Sonnet 5.5
  prices note 10 read (USD 2 and USD 10 per million input and output tokens) the full cap costs
  USD 3.50; the Haiku price row was unreadable, so the Sonnet price stands in as an assumed upper
  bound. The runner stops at USD 5 of recorded spend or 500 calls, whichever comes first; missing
  usage fields stop the batch.
- Before EP-1, a 9-call smoke inside the unchanged default checks the adapter, usage fields and
  model ID. It decides nothing else.
- A second tier (Sonnet 5.5, batch EP-2, same ceiling) is a separate approval. Only then can the
  capability question be read, and only as exploratory.

**Rung 2: a local open-weight model.** Only after the host-memory leak (S0 in `PROPOSAL.md`) is
isolated and gate G3 (ii) approves one 4B to 9B model. Until then nothing in this program needs
the GPU. The dreaming ladder's first rungs can run on either backend, each as its own batch.

**What EP-1 can show.** It is a toy allocation game with real models. It can show whether a card
changes collective behaviour and whether enforcement adds anything. It says nothing about real
coding work; that needs the trap benchmark tasks at the next step.

**Power.** From note 17: the minimum detectable effect at 80% power is about
`2.8 x sd_d / sqrt(n)`, where `sd_d` is the standard deviation of paired differences. n = 10 gives
0.89 sd_d; n = 15 gives 0.72 (our arithmetic); n = 20 gives 0.63; n = 40 gives 0.44. `sd_d` is
measured, not guessed. EP-1 therefore detects only large effects: about 20 points if `sd_d` is
near 0.25 (an assumption). Not detectable at this size: `playbook` against `both`, small `HDI`
differences between practices, and the tier interaction.

**Kill criteria and "inconclusive"** (smallest effect of interest: 20 points; a design choice the
owner may change before the freeze):

| Result | Reading | Action |
|---|---|---|
| Floor passes, oracle fails, model ID mismatch, or duplicate work executed under `code` | Instrument void | Fix; no claim |
| `Y_none` already within 10 points of `Y_code` | No problem at this tier | Drop this practice for this tier; try the next once |
| `Y_play - Y_none` interval above 0 and at least 20 points | Card adopted; report `HDI` with its interval | Carry the card to real tasks |
| `Y_code - Y_none` clear, `Y_play - Y_none` interval wholly below 20 points | Harness needed here | Keep the rule in code for this tier. A result, not a failure |
| Interval of `Y_play - Y_none` contains both 0 and 20 | **Inconclusive** | One predeclared doubling of n under a new approval, then report "not shown" |
| Any harm: canary hit, protected-file change, action outside the lease | Harm | Stop the batch |

**Program-level kill.** If, for the first three practices on two tiers, every `HDI` interval lies
above 0.8, the "less harness" thesis is rejected for those tiers: we ship enforcement and stop
writing cards. If `Y_none` matches `Y_code` everywhere, there is nothing to improve and the
program stops.

## 7. How this improves models, not only harnesses

1. **A portable practice library.** Each card is plain text any model in any harness can read. It
   ships with its evidence row: tier, `HDI`, interval, n, date, task. A card with no row is a
   hypothesis.
2. **Honest scope.** A card changes behaviour in context, not weights. "Improves the model" here
   means: the same model does better with less harness code.
3. **Later, optional, deferred: distillation.** Trajectories from teams that followed a practice
   and passed deterministic checks could train a small adapter for a local model. One test: does
   the practice now appear in the `none` arm without the card? This needs training gates, the leak
   fixed, and an owner ruling, because the scope guard and the recommended cut of consolidator
   training both stand against it. No frontier-model ambition: one practice, one local model.
4. **Feeding the Claude Code ecosystem.** A surviving card becomes a candidate skill, `AGENTS.md`
   line or subagent convention. A card that fails (`HDI` near 1) becomes a candidate hook or
   tool-level check. Each is a hypothesis with its evidence status, valid only for the tier and
   task tested.

## 8. Prior art and what could be new

Prior art, all of it: skills and instruction files; playbook-style context methods (ACE);
reflection and skill libraries; lock files, progress files and task graphs for long multi-agent
runs; blackboard systems and claim protocols; vendor dreaming and sleep-time compute; governed
shared memory; failure taxonomies that argue for structural fixes over prompts; one peer-reviewed
toy-game result that a one-line instruction changes collective structure (note 16).

Possibly new, stated modestly: (1) a head-to-head, budget-matched comparison of one norm as
instruction against the same norm in code, with an index and intervals; (2) that comparison across
capability tiers; (3) a scripted re-verify control for dreaming next to an equal-token control;
(4) open cards and instruments. "Not found in an abstract-level search" is not novelty.

## 9. Work plan

Sizes are relative. Agent build tokens run on a subscription: USD unknown, not zero. One
GPU-hour is at most 0.86 MJ at the 240 W supply rating.

| Stage | Content | Size | Model roles | Cost (estimates) | Needs |
|---|---|---|---|---|---|
| E0 | Owner rulings; verify the existing `cell.py`, `router.py`, `perturb.py` | S | Opus verifies | About 0.2M tokens; 0 GPU | Memo decisions |
| E1 | Build `practice.py` (load, hash, attach card; enforcement predicates), `board.py`, `team.py` (turn loop), `orders.py` (order parameters, `HDI`, `EG`), scripted adopters; tests; rung 0 | M | Sonnet builds; Opus verifies; Haiku or a script formats cards | About 0.8M tokens; 0 GPU; USD 0 | Reinstatement ruling |
| E2 | Pre-registration `prereg/EP1.md` frozen; Claude adapter in `runner.py`; 9-call smoke | S | Fable writes the pre-registration; Sonnet builds; Opus checks | About 0.3M tokens; at most USD 5 | Commit ruling; G7 default |
| E3 | EP-1 | S | Cells under test: Haiku 5.5 | At most 1.15M tokens, USD 5, 500 calls | EP-1 approval |
| E4 | EP-2, second tier; practices B and E on trap benchmark tasks | M | Fable reads results; Sonnet builds | One batch each, same ceiling proposed | Separate approvals |
| E5 | Dream ladder: scripted check, then rungs 1 and 2 | M | Sonnet builds `consolidate.py`; Opus verifies | Local: cap 8 GPU-hours, at most 6.9 MJ, USD n/a; or one API batch | S0 fixed and G3 (ii), or a batch approval |
| E6 | Ladder rung 3; rungs 4 and 5 only if it passes | L | as above | To be sized from rung 1 spread | Separate approvals |
| E7 | Card library with evidence rows; write-up | S | Sonnet drafts; Haiku chores; Opus claims check | About 0.3M tokens | G8 |

**Build next:** `practice.py`, `board.py`, `team.py`, `orders.py`, the Claude backend of
`runner.py`, `consolidate.py`, `prereg/EP1.md`, seven card files.
**Keep from `PROPOSAL.md`:** S0 to S5, the cross-model protocol, the confidentiality section, the
lease.
**Cut or demote:** the handoff-against-search matrix as headline (S7 becomes practice F, with no
separate store); T7 beyond the running smoke; E9-1 and E9-2; dream dose; every hypothesis number
not mapped in section 5.

Document debt is real: this file adds about 4,000 words to a repo with under 1,300 lines of code.
If the owner approves the re-centring, `PROPOSAL.md` sections 2, 4 and 5 are marked superseded,
and no further planning document is written before EP-1 is frozen and run.

## 10. Risks

| Risk | Why it matters here | Guard, and its limit |
|---|---|---|
| Collusion | Agents colluded on prices through a public board (note 14); collusion can outlast its incentive (note 16, abstract) | No competitive payoffs in our tasks; injected faults and a count of verifier pass-through; no same-model verification without a deterministic check. Limit: adversarial incentives are not tested |
| Lock-in and herding | A card can spread a bad convention as fast as a good one | A seeded deviating convention and a planted stale note in every practice; correction half-life reported. Limit: small stores, short horizons |
| Memory poisoning | One wrong note can reach every session | Source links, supersede, scripted re-verify; the benchmark holds no working attack. Limit: lint checks that a source exists, not that it is true |
| Measurement artefacts | Prompt length; interleaved turns are not concurrency; enforcement makes collisions zero by construction; a toy game is not work | Neutral card of equal length; one shared stale snapshot per round; arms compared on team outcome and cost, not on the enforced quantity; real tasks at E4 |
| Leakage | A card or a dream can carry answers | Cards checked against task text; canaries; held-out instances. Limit: generator templates can be learned |
| Judge dependence | Vendor memory results use model graders | Deterministic scoring only, which limits us to checkable tasks |
| Correlated errors | Same-family agents fail together | Report rho; independence rule. Limit: one model family at rung 1 |
| Wrong model answering | The local proxy can answer a "Claude" call with another provider | Direct key; returned model ID; a mismatch voids the episode |
| Spend | A team run multiplies calls | Hard call and USD stops; no second batch without approval; a ceiling is never raised to fix a failing run |

Not checked: no code or test was run; the leak and smoke status are as relayed; Haiku 5.5 pricing
was not readable; note 14 keyword-scanned several pages; notes 15 to 17 read most papers as
abstracts.

verified: 972dee3 (plus working tree) 2026-11-19
