# murmuration: the plan

Date: 2026-11-19. Status: plan. Committed at `972dee3`: the Wave 1 tools (14 Python files under
`src/`); 89 passing tests is the figure in `docs/reports/E1-E8.1-local-results.md`, not re-run
for this edit. Run so far: E1 and E8.1 on the local corpus, pre-freeze and exploratory (same
report), and two T7 smoke arms killed by the 10 GiB memory watchdog, cause unknown
(`docs/reports/staged-t7-decision.md`). No hypothesis has been tested; no pre-registration is
frozen. Companions: `docs/SCIENCE.md` (concept-to-experiment map, formulas, pre-registration
template) and `docs/ARCHITECTURE.md` (hub-and-cells design; not built).

Governing rules: `docs/PRINCIPLES.md` (five-step filter: question, delete, simplify, accelerate,
automate; units on every quantity; matched budgets; value-of-computation run gate). Every
experiment below must also report tokens, joules and USD per passing task and idle-compute
fraction; an experiment whose Fermi estimate shows the effect is invisible at the planned n is not
run. Where PRINCIPLES.md and this file disagree, PRINCIPLES.md wins.

Verification pass (2026-11-19): files `research/05a` and `05b` opened the primary vendor sources
and 11 papers. Corrections are in `SCIENCE.md` 7.2a and override any figure in this file. Net
effects on the plan: H1's decay premise is an analogy (Anderson-Schooler covers words/emails, not
permissions); H3's equal-total-token control is stricter than the sleep-time-compute paper's;
H4's novelty is only a coding-specific deterministic test and linter; deny rules are not an
absolute guarantee (Bash bypasses); do not cite 97% (interference) or 72% (cache saving).

Amendment (2026-11-19, owner requirements; research files 07, 08, 09): the tool must work both
centralised and decentralised (hub and cells, `ARCHITECTURE.md`); the local-model plan is no
longer Qwen-only and Unsloth is authorised in principle for training (each install and download
is still its own gate, 6.2); hypotheses H6 and H7 and Track T7 are added; T6, E3.2 and Claude
batch C3 are cut or deferred to keep the plan small (section 2). Sci-Hub is not used; sources are
open pages only. Facts from files 07-09 carry the status given in `SCIENCE.md` 7.2a.

Amendment 2 (2026-11-19, owner requests after the AI Engineer Code Summit talks; research files
10 and 11): hypotheses H8 and H9 and Track T8 (a small test program for the ideas in Lance
Martin's and Diogo Almeida's talks) are added; H3 gains a raw-log search control and loses the
re-summarise control; the model role table in 4.2 is extended; Claude batch C6 is added as
conditional. What was cut to pay for this is listed in T8. Plain-language summary:
`docs/VISION.md`. All talk figures are talk claims (`SCIENCE.md` 1.5).

Amendment 3 (2026-11-19, adversarial review 2, `docs/reports/adversarial-review-2.md`, and the
owner's decisions relayed that day): the hub is split into owner key, router code and models,
and every model is a cell (`ARCHITECTURE.md` 1-2); confidentiality wording is narrowed
(`ARCHITECTURE.md` 6a); the three idea families become task controls under one robustness
measure (T10, `SCIENCE.md` 4a); a cross-model protocol is added (4.6) and 4.2 is amended. Owner
decisions and the review's recommended cuts are in 6.4. No cut is applied until the owner rules.
Change list: `docs/reports/doc-reconciliation.md`.

Reading rule for this file: every number that is not a design choice of ours is a **lead**, not a
fact. The first four research files rest mostly on search snippets. Talk figures are cited as "per the
talk, owner-validated": the owner confirmed they match Anthropic's material, but they are talk
claims, not peer-reviewed results.

---

## 1. Thesis and hypotheses

### 1.1 Thesis

Coding-agent harnesses already contain three adaptive loops: authority (what the agent may do),
division of labour (when work is split across agents), and memory (what survives a session, and
who else reads it). Each loop today is tuned by taste. Complex-systems and organizational science
offer quantities that can be **measured on real traces** and that predict when each loop helps or
hurts. murmuration builds the measuring instruments, states falsifiable predictions before the
data is seen, and reports the result whichever way it goes.

What this project is not: a simulator. The earlier NK-landscape simulator with invented cost
constants is retired. Its conclusions were true by construction. Theory is used here only where
it gives a number we can check on real or independently grounded data.

Organisation (added 2026-11-19, amended by Amendment 3): the three loops run in one shape, a
hub and cells (`ARCHITECTURE.md`). The hub is router code plus the owner's key. Every model is a
cell: a strong-model planner cell writes task specs and proposes policy that the owner signs, a
verifier cell judges where no deterministic check exists, and worker cells with narrow
authority, local memory and optionally a local model do the work. Central and decentral differ
in who executes, set by the routing table; a Claude planner still reads what it plans. Whether
any work can move to a cell is itself a hypothesis (H6), not an assumption.

### 1.2 Hypotheses

Five are confirmatory (H1-H4 and H6, Holm-corrected as one family). H1 is pending: its
precondition is not met on the local corpus (below). H5 is exploratory. H7 is a single
pre-test of a published result, reported with intervals, outside the family (staged; T7). H8 is
**exploratory** (owner 2026-11-19; `prereg/H8.md`), outside every Holm family. **H9's status
awaits the owner's ruling**: with H8 out, the former family of two would be a family of one (a
single test at 0.05); there is no `prereg/H9.md`; the adversarial review recommends deferring
H9 (it needs E2.2's tasks, which need G1). The robustness matrix (T10) is exploratory.

**H1. Authority decay has a knee (permissions).**
- Concept: usage-based decay (Anderson and Schooler / ACT-R base-level activation) applied to
  least privilege (Saltzer and Schroeder).
- Prediction: the chance that an idle capability is used again falls with idle time faster than a
  memoryless process would predict. If so, some decay window tau exists where `grow_decay` cuts
  idle exposure by at least 30% against `promote_repeated` while adding at most 10% more prompts,
  on sessions held out from the tau choice.
- Precondition (not a kill of the hypothesis): at least 200 real permission events and at
  least 30 sessions. Below it, H1 is untestable on that corpus, not refuted (owner 2026-11-19:
  H1 stays pending). The local corpus holds 1,079 events in 1 session (11 denials): the session
  count fails (`docs/reports/E1-E8.1-local-results.md`). Next: a salted session count on the
  owner's other machine.
- Kill: denials not reliably detectable; no tau in {1, 3, 7, 14, 30} days meets the 30%/10% bar on held-out sessions; or the
  reuse hazard is flat, in which case decay only trades exposure for prompts one for one.
- Prior art: decay on idle exists (Android auto-reset, AWS unused-access analysis); grow on need
  exists (NVIDIA OpenShell Policy Advisor, JIT access). Per CJ Avilla's talk, owner-validated, the
  grow/shrink session policy with a two-week unused rule is already described. Our claim is only
  the measurement on coding-agent traces. A combined, risk-tiered rule was not found in my search.

**H2. Coupling predicts when fan-out pays (orchestration).**
- Concept: near-decomposability (Simon); coordination as dependency management (Malone and
  Crowston).
- Prediction: (a) on public git history, co-change coupling between two concurrent changes
  predicts integration failure better than file overlap alone (AUC gain of at least 0.05);
  (b) at **matched total tokens**, fan-out gain over a single agent is negative in the top
  coupling tercile and non-negative in the bottom one; (c) a gate using that score matches the
  better of always-fan-out and never-fan-out on pass rate while spending at most 80% of
  always-fan-out's tokens.
- Kill: coupling adds nothing over overlap (CI on the AUC gain includes 0); or at matched tokens
  fan-out never wins in any tercile, in which case the correct gate is "never" and we say so.
- Prior art: Kim et al. (scaling agent systems), Li et al. (sub-agent concurrency), NP-Bench /
  Nerveplane (scope partition), Claim Plane, CooperBench. Gating on decomposability is published.
  A git-co-change gate evaluated at matched tokens was not found in my search.

**H3. A dream pass must beat the same tokens spent elsewhere (memory).**
- Concept: complementary learning systems (fast episodic store, slow structured store, offline
  replay). Used as a design frame only. Neuroscience is not evidence that the agent job works.
- Prediction: on a benchmark with planted wrong and stale memory, a consolidation pass that reads
  raw logs beats **both** equal-token controls (extra retries; a search tool over the raw
  logs with no dream pass) by at least 10 percentage points of task pass rate, and removes at least 70% of planted
  wrong notes while keeping at least 95% of true ones.
- Kill: the CI of dream gain against the better control includes 0. Then reflection has not
  justified its compute, which is the question Lance Martin's talk leaves open (per the talk,
  owner-validated: "task-specific evals needed to show reflection justifies its compute").
- Control changed 2026-11-19: per Lance Martin's slide (talk claim, slide-only), search over the
  corpus without any wiki scored 53% and wiki plus search 54% to 61%. Plain search is therefore
  the hardest control and replaces "re-summarise memory without the logs".
- Prior art: Anthropic Dreaming (Managed Agents), Claude Code auto memory, claude-diary, Letta
  sleep-time compute, Reflexion. Consolidation is not new. A compute-matched evaluation on coding
  sessions was not found in my search, and one research file's search summary said the same.

**H4. Ungoverned shared memory locks in early errors (shared memory).**
- Concept: increasing returns and lock-in (Arthur); commons governance (Ostrom).
- Prediction: in a store written by several agents, a planted wrong convention gains retrieval
  share over time under a flat shared file. Provenance lint plus supersede-not-delete plus
  re-verify-on-use cuts the lock-in rate by at least half while losing at most 5% of true-note
  utility.
- Kill: lock-in rate under the flat file is already below 10% (no problem to solve), or governance
  does not halve it, or it costs more than 5% utility.
- Prior art: Governed Collaborative Memory (arXiv 2605.04264), Governed Shared Memory
  (2606.24535), Collaborative Memory (2505.18279), Zep/Graphiti supersession, MINJA and
  AgentPoison on the attack side. Governance designs exist. Our contribution would be a
  deterministic, coding-specific test and a linter, nothing more.

**H5 (exploratory). Clones are not an ensemble.**
- Concept: diversity prediction theorem (Page; Krogh and Vedelsby).
- Prediction: pass@k of k same-prompt attempts is predicted by per-task failure probabilities
  alone (`1 - mean(q_t^k)`); varied prompts or models lower failure correlation.
- Read off for free from T2 runs. No confirmatory claim. Prior art is dense (five 2026 preprints
  listed in research file 01).

**H6. A small local cell clears the floor on some task class, and the cascade is cheaper
(routing).**
- Concept: model cascade (FrugalGPT, abstract only); value of computation (Russell and Wefald,
  citation only); polycentric organisation as the frame (interpretation).
- Task classes, fixed before any run: (a) session log to memory records, (b) memory lint and
  pointer repair, (c) a narrow scripted edit under tests. All on trapbench, deterministic checks.
- Prediction: on at least one class, a local cell (model of at most the 9B class, on this box)
  clears an **absolute floor of 80% pass rate** on held-out tasks (95% CI lower bound at or
  above 0.80, 400 generated tasks per class), and the cell-first cascade (cell, check, escalate
  on failure) costs at most **30%** of the Claude-only USD per passing task. Local energy is
  priced at the 240 W power-supply rating x wall time x the owner's tariff (an upper bound from
  the spec page), not at the GPU-only reading. Hardware cost is excluded and that is stated in
  the result. **Not computable yet:** no tariff exists, and the owner ruled local USD "n/a" for
  H7 and E9. Until the owner supplies a tariff, or rules that local USD stays "n/a" (then this
  cost criterion is rewritten before any freeze), H6's 30% bar cannot be evaluated.
- Why an absolute floor and not "as good as Claude": a 5-point non-inferiority claim against
  Claude would need several hundred Claude episodes per class, which the budget in 4.3 does not
  buy. Local tasks are cheap, so the floor is tested locally; the small Claude batches supply
  only the cost of the Claude-only route and a descriptive ceiling.
- Fermi, done before running: 240 W for an hour is 0.24 kWh, far below an hour of API work, so
  the cost side is nearly settled by arithmetic (cascade cost is about `(1 - p)` of hub cost).
  The part that can fail is quality: the floor, and whether the check lets wrong results pass.
- Kill: no class clears the floor; or the no-model stub cell is within 5 points of the local
  model on a class (then that class routes to the stub and the model is cut from it); or the
  deterministic check accepts wrong results in more than 5% of hand-audited passes; or the
  30% bar is missed once escalations are charged.
- Prior art: cascades and routers are published (FrugalGPT and successors). Tier escalation is
  already the owner's working rule. Our claim is only the measurement on coding-agent memory
  tasks with a signed-policy cell. 80%, 30% and 5 points are our design choices, not literature
  values.

**H7. A hub-supplied weight change beats a decoding-only fix at matched cost (weight surgery).**
- Concept: model editing (ROME, MEMIT, task vectors, activation steering, abliteration;
  abstracts opened in file 08) and the MIT "weight-space programming" post of 2 Nov 2026.
- Prediction: on Qwen3.5-0.8B, the released direction edit (or, in a second step, a LoRA
  adapter) beats the best decoding-only fix (thinking off, or a repetition penalty) by at least
  5 points on MATH-500 under the same per-problem token cap (the matched budget), with no
  off-target loss above 2 points on an IFEval and MMLU-Pro subset. Tokens and joules per correct
  answer are reported for every arm. Operational design (cap 8,192, n = 100, two stages, the
  12-point stage-1 gate): `prereg/H7.md`, summarised in T7.
- Kill: any decoding-only arm is within 5 points of the edit (paired CI) under the same cap;
  or the edit loses more than 2 points off-target against the same decoding-only arm. Then
  "the hub edits cell weights" is dropped from the architecture and cells get decoding configs
  and, where trained, adapters.
- Prior-art warnings (file 08): the edit type is not new (abliteration is the closest
  precedent). The original has one editing run per budget, no LoRA, steering or decoding
  baseline, and 8 to 20 hours of wall-clock per run; the 10- and 25-pass edits barely worked;
  the Gemma 3 270M follow-up did not improve; the authors say edits remove an obstacle and do
  not add an ability. The 6x is measured against a thinking-mode baseline that mostly hits the
  token limit. Unopened second-hand reports put thinking-off and repetition-penalty baselines
  near the edit; they are leads, not facts, and they are why this test is cheap and first.
  My expectation is that H7 is killed. That is a useful result.

**H8 (exploratory, owner 2026-11-19). A weaker model needs imposed memory structure to benefit
from memory (memory).** Matched budget amended 2026-11-19: across a local model and Sonnet the
cap is turns plus input and output bytes per question, with native tokens reported beside it
(4.6); "same token cap" below means that cap. Review 2 suggests running H8 as the T10 matrix
with the memory switch on two tiers (a recommendation, not applied).
- Concept: none borrowed from complexity science. It is a reading of one talk chart
  (`SCIENCE.md` 1.5, note 6): on CL-Bench's database task the gain from a memory store was near
  zero for the weakest model shown and closed about half the headroom for the other five. That
  looks like a threshold. Interpretation of six points; talk claim.
- Prediction, on a CL-Bench-style task from our own generator (E8.3), same token cap per
  question in every arm: for a local model of at most the 9B class, a bare memory directory
  with no instruction (S0) gains less than 5 points over stateless, and a structured memory
  (S2: when-to-read and when-to-write instruction, record schema, lint on write, size cap)
  gains at least 10 points over S0. For Sonnet 5.5, S0 already gains at least 10 points over
  stateless and S2 adds less over S0 than it does for the local model (interaction above 0).
- Kill: the local S2-minus-S0 interval includes 0 (structure does not rescue a weak model:
  small cells then get no memory of their own, and memory arrives in the task spec from the
  planner cell); or local S0 already gains 10 points or more (no threshold at this size: the lint and
  cap are dropped for cells, which is simpler); or the interaction interval includes 0 (then
  "inversely related to model strength" is not shown and structure is kept or dropped on its
  main effect alone).
- Secondary, descriptive: memory size in characters and files per 100 sessions; duplicate
  records; wrong-note follow rate.
- Prior art: CL-Bench (arXiv 2606.05661; its abstract says naive in-context learning beats
  dedicated memory systems, per file 10); Anthropic's memory post advises telling the model
  what memory is for, not how (per file 10). Structured agent memory is dense prior art. Our
  claim is only the model-strength interaction at equal tokens. 5 and 10 points are our design
  choices.

**H9 (status awaiting the owner's ruling; review recommends defer). Small local models
coordinate through a shared board only when handed its structure (orchestration).**
- Concept: stigmergy (coordination through a shared environment). Speculative for
  language-model agents; the observation is Lance Martin's 1,000-agent run, where agents
  created their own tables (talk claim, unreproduced, frontier model).
- Prediction, with a lead and seven helpers on one local model of at most the 9B class
  (E8.2), matched total tokens per task: (i) from a blank database, an agent-created table that
  another agent later reads appears in fewer than half of runs; (ii) with the five-table schema
  given, the duplicate-work rate is at most half of the blank-database arm's and the pass rate
  is at least 10 points higher.
- Kill: the blank-database arm forms a used table in at least half of runs and the
  given-schema arm's pass-rate advantage has an interval that includes 0. Then self-organised
  tables do not need a frontier model at this scale, and we say so.
- Separate decision rule (not part of H9): a hub-hosted board enters `ARCHITECTURE.md` only if
  the given-schema arm beats hub assignment (the current star) by at least 10% in tokens per
  passing task at matched tokens. Otherwise the star stays as it is.
- Limits stated up front: eight agents, not 1,000; turns are interleaved on one GPU, so there
  is no true concurrency; a negative result says nothing about frontier models at scale.
- Prior art: blackboard systems and shared-scratchpad agents are old and dense; Claim Plane and
  NP-Bench (file 02) cover claims and scope partition. Not found in my search: the
  blank-versus-given-schema comparison on small local models. Half, 10 points and 10% are our
  design choices.

---

## 2. Tracks

Common rules for every track:
- Deterministic scoring first: tests pass, canary files, string and path matches. No model is the
  sole judge. A model grader may be added only after it passes the grader-sanity checks from
  Lance Martin's talk: repeat gradings agree, binary or pairwise format, and a human has read at
  least 20 examples first.
- Paired designs: every arm sees the same tasks and seeds.
- Statistics: effect size with a 95% bootstrap CI resampled by task or session, never by row.
  Minimum effect is written down before the main run. Code hash and config hash are frozen before
  the main run and printed in every output.
- Pilot data never enters a confirmatory analysis.

**Cut or deferred after the five-step filter (2026-11-19).** Adding H6, H7 and T7 must not grow
the plan, so these go:
- **T6 integration demonstrator: deleted.** The minimum viable hub-and-cells in
  `ARCHITECTURE.md` section 10 is the integration, with tests, and replaces it.
- **E3.2 compression loss: deleted.** No decision in this plan depends on its result.
- **E2.3 / Claude batch C3 (USD 150, the largest spend): deferred** until E2.1 passes and E2.2
  shows an effect on the local model. Not requested now.
- **E1.4 many contributors: deferred** to after G8; it cannot run before publication anyway.
- **T4 consolidator training: conditional.** Runs only if H3 survives on a base model and the
  base local model misses the H6 floor on class (a). RECOMMENDED CUT, awaiting owner ruling (6.4).
- **T7 Arm E (a frontier agent re-discovering the edit): not planned.** File 08 estimates 8 to
  20 hours of wall-clock per run plus unpriced frontier tokens, and no decision here needs it.
- `synth.py` (illustration only) is a deletion candidate at the next code change.
- **E3.3 arm B2 (re-summarise memory without logs): replaced** by B3, search over the raw logs
  (2026-11-19). Same number of arms. Further cuts made when T8 was added are listed in T8.

### T1. Permissions (built; needs one fix)

- Question: does grow-on-need, decay-on-idle beat "promote repeated requests" (the answer the
  owner received in the Q&A) on prompts and standing exposure? How often do agents over-request
  or block themselves?
- Design: replay of real transcripts through the four policies already in `ledger.py`.
- **E1.0 metric fix (do first).** The exposure metric is inconsistent between policies:
  `promote_repeated` counts only idle time at the end of the stream, while `grow_decay` adds tau
  at every decay. A key used on days 0-3 and again on day 40 scores 1 idle day under
  `promote_repeated` and 15 under `grow_decay`, although `grow_decay` held it for less time.
  Replace with one definition for all policies: idle rule-days summed over every gap while the
  rule stands (formula in SCIENCE.md). Add a test with exactly that example.
- E1.1 tau sweep on real traces, tau chosen on the first 70% of sessions by time, judged on the
  last 30%.
- E1.2 reuse-hazard fit: distribution of gaps between uses of a capability; power law against
  exponential by likelihood ratio.
- E1.3 allowlist mining hold-out: build an allowlist from the early window, measure false-deny
  and excess-grant on the late window (the AWS-style baseline).
- E1.4 many contributors: others run `murmuration report --salt` and share the JSON.
- Data: local Claude Code transcripts (salted aggregates only; our analysis exports nothing).
  The sessions they record already sent their content to the model API when they ran.
- Corpus so far: 1,079 events, 1 session, 11 denials; E8.1 counts 42 sessions with usage
  fields (5 main, 37 subagent) in the same corpus. Why E1 finds 1 session and E8.1 finds 5
  main sessions is unexplained; resolve before any H1 or E8.1 claim.
  Public agent trajectories do not record permission prompts as far as I know, so no public
  dataset substitutes. That is a real limit.
- Baselines that ship: static allowlist, promote-repeated, always-ask. The auto-mode classifier
  cannot be replayed offline; E5.3 covers it live.
- Metrics: prompts per 100 calls, idle exposure rule-days, thrash rate, grant-use ratio,
  after-denial classes.
- GPU: none. Models: none. Cost: zero.

### T2. Orchestration and fan-out gating

- Question: can a cheap score computed before the run decide whether to fan out?
- E2.1 (no model): on public repositories, take pairs of pull requests that were open at the same
  time. Predict integration failure (textual conflict from `git merge-tree`; where the repo's
  tests run offline, also "tests pass alone, fail merged") from (a) file overlap and (b) co-change
  coupling computed only from history **before** both PRs opened. Split by repository.
- E2.2 (local model as subject, many seeds): tasks stratified by coupling tercile; arms: single
  agent, always fan-out (lead plus k workers in separate worktrees), gated. Total tokens matched
  per task.
- E2.3 (Claude confirmation, small n): same arms on a subset. See section 4. Deferred (above).
- E2.4 (exploratory, free): failure correlation and pass@k from the E2.2 attempts.
- Datasets: public repos under permissive licences (verify each licence before cloning; clone is a
  download gate). Task candidates: CooperBench and the benchmark from Li et al., if public and
  their licences allow; otherwise paired-feature tasks derived from E2.1's PR pairs. Do not
  assume availability; verify first.
- Baselines that ship: single agent (the default), always fan-out, "the model decides when to
  spawn" (what Claude Code does today).
- Metrics: pass rate by tests on the merged tip, total tokens, token multiple, conflict count.
- Seeds: 5 per task per arm on the local model; 2 on Claude.
- Minimum effects: stated in H2.
- GPU: needed for E2.2 serving only. E2.1 is CPU.

### T3. Memory, shared memory, dreaming

- Question: does consolidation earn its tokens, and does governance stop shared memory from
  spreading errors?
- **trapbench** (built in this repo, self-authored, no licence issue): a generator of small toy
  repositories with tests, a sequence of sessions, and planted memory conditions: correct note,
  wrong note (the Pokemon-style trap from Lance Martin's talk), stale note (true in session 2,
  false after a change in session 5), and no note. Following a wrong note leaves a canary (a
  specific command run or file touched), so scoring is deterministic.
- E3.1 (no model): memory linter over existing memory directories; report provenance coverage
  and pointer validity. Counts only.
- E3.2 compression loss: **deleted** (see the cut list above).
- E3.3 compute-matched dream (H3). Arms with the same token budget B per cycle:
  A = dream pass over raw logs, writing a new store plus a diff; B1 = B extra tokens of retries;
  B3 = a search tool over the raw logs with no dream pass, B tokens of search and reading
  (replaces B2, re-summarise memory without logs); C = nothing. Dream tokens are charged to
  arm A.
- E3.4 shared-memory lock-in (H4): three or more agent sessions write one store. Arms: flat shared
  file; governed store (lint, supersede, re-verify-on-use); private-only memory.
- E3.5 leak test: two scopes, 50 sentinel strings, count cross-scope retrievals. Target zero.
- Models: a local model for volume; Claude for a confirmation subset.
- Baselines that ship: flat memory file loaded in full; a dedupe-and-prune pass (what third-party
  descriptions say Auto Dream does; unverified); diary-then-reflect.
- Metrics: pass rate, wrong-note follow rate, memory-correction half-life, true-note retention,
  tokens.
- Seeds: 5 per scenario per arm on the local model; 2 or 3 on Claude. At least 40 scenarios.
- GPU: needed for the local-model arms. E3.1 is CPU.

### T4. Local model adaptation and cell routing

See section 3. One trained artifact at most (a consolidator, conditional), one tabular model
that does not need a GPU, and the H6 routing measurement:
- E4.1 (H6): the three task classes of H6, each run on three tiers: no-model stub cell, local
  model cell, Claude worker. The cascade is computed from the same episodes (no extra runs).
  Held-out tasks only; the floor is fixed in the pre-registration. Order by cost: stub and
  local model first; a class where the local model does not beat the stub by 5 points gets no
  Claude run. The Claude reference for class (a) is batch C4, already planned; classes (b) and
  (c) need a small new batch C5 (section 4.3), requested only if they pass that screen. 20
  hand-audited passes per class for the false-accept rate.

### T5. Claude-side tests

See section 4. Confirmation runs for E3.3 and E3.4 plus the live denial experiment E5.3. E2.3
is deferred.

### T6. Integration (deleted)

Replaced by the minimum viable hub-and-cells in `ARCHITECTURE.md` section 10: a stub cell, a
scripted router and contract tests with no model and no GPU. It is a demonstration, not a
hypothesis test.

### T7. Weight surgery vs LoRA vs decoding fix

- Question: does a small weight edit shipped by the hub do anything a decoding setting does not?
  The decision it changes: whether "weights" stays in the owner's edit controls as more than
  adapters and decoding configs.
- Subject: Qwen3.5-0.8B at the revision named in `prereg/H7.md`. Arm A is rebuilt locally from
  the authors' diff and checked against the model card's tensor hashes (G3i, G9 reviews).
- **Staged pre-test, inference only (gate G9; owner 2026-11-19).** The operational design is in
  `prereg/H7.md` (sections 6, 7, 10, 12) and `docs/reports/staged-t7-decision.md`; this summary
  defers to them and does not restate caps or sampling. It replaces the earlier one-stage design
  here (32,768 cap, arms A-D on the full MATH-500, five arms at once).
  - Same 100 seeded MATH-500 problems in every arm; primary metric `acc8k` (8,192-token cap).
  - **Stage 1:** arms B (thinking off), then A (edit), then 0 (reference, thinking on). The gate
    uses B and A only.
  - **Stage-1 gate (owner decision 2026-11-19):** stage 2 runs only if `acc8k(A) - acc8k(B)` is
    more than 12 points and its 95% interval lies above 0. Kill at stage 1 if the interval's
    upper bound is below +5. Otherwise inconclusive, stop.
  - **Stage 2:** arms C (repetition penalty, chosen on `math_train.jsonl` practice problems
    only), D and D-null, and the off-target checks.
  - **Stated limit (review 2, row 4):** at n = 100 the minimum detectable effect is about 12 to
    18 points, while H7's survive margin is 5. The test cannot confirm H7 as worded: a result
    of +5 to +12 with an interval above 0 stops as inconclusive, and a kill needs an observed
    deficit. Per the staged record, the gate passes in about 0.3-2.4% of runs if the true
    difference is 0 and 28-34% if it is +10. An inconclusive result has the same architecture
    consequence as a kill.
  - **Open alternative (review 2 action 9, not applied):** drop T7, or run B and A only as a
    labelled smoke with the difference and interval reported as descriptive. The owner's
    12-point gate decision stands unless the owner rules otherwise.
  - **Blocker:** both smoke arms were killed by the 10 GiB MemAvailable watchdog (arm 0 after
    about 22 minutes at 9.97 GiB, arm B after about 13 minutes at 9.44 GiB), cause unknown.
    No further T7 GPU time is planned until the cause is found (review 2 action 1).
- Kill criteria: those of H7, as operationalised in `prereg/H7.md` 12. Also: if arm D does not
  beat D-null, the script is dropped (this does not kill arm A).
- **RECOMMENDED CUT, awaiting owner ruling (6.4):** stage 2, arm 0, arm D (with D-null) and the
  LoRA step below. Until the owner rules, they keep their current status: stage 2 and arm D
  conditional on the gate; arm 0 scheduled last in stage 1; LoRA conditional on survival.
- **Optional second step, only if H7 survives the pre-test:** a LoRA adapter trained with
  Unsloth on the public GSM8K-train and MATH-train problems the post used, compared with the
  edit and the best decoding arm under the same cap, with training energy charged to the LoRA
  arm. Needs G2b, G6 and its own pre-registration. One configuration, three seeds.
- Fermi (estimate, not measured): file 08 estimates a few GPU-hours for the arms plus under a
  day of setup; the 12 GPU-hour cap of G9 binds. Stage 2 is projected only after a smoke arm
  completes.
- Rollback and safety: edits are written to a copy; base weights are read-only and hashed
  before and after; no shared endpoint is touched; public benchmark data only.
- GPU: inference only for the pre-test. Models: one 0.8B model and its edited copy.

### T8. Test program for the Code Summit ideas (added 2026-11-19)

- Question: which of the things Lance Martin and Diogo Almeida showed or asked can we test with
  what exists here, and which decision does each test change?
- Rule: real artifacts only. No replay or simulation built on Lance's published numbers: that
  would be a simulator with constants we did not measure, which `PRINCIPLES.md` forbids. Data
  are the owner's local transcripts (counts only), our own generated toy repositories and
  databases, and public repositories under G1.
- Every experiment reports pass rate with a 95% interval, tokens, joules (GPU-only sampled power
  x time, labelled so) and USD per passing task, and idle fraction. Thresholds are our design
  choices, not literature values.

**Priority order** (cheapest instrument first; a kill cancels what depends on it):

| # | Test | Owner's item | Needs | Cost |
|---|---|---|---|---|
| 1 | E1.0 to E1.3, permission grow and decay replay (T1, unchanged) | (f) | nothing | 0 |
| 2 | E8.1 token-class and read:write ledger on our own sessions | (e), (a) | owner's yes to read usage fields | 0 |
| 3 | E8.3 memory structure against model strength, local arm (H8) | (c) | G2a, G3 (ii), G5 | electricity; cap 8 GPU-hours |
| 4 | E8.2 shared board with local cells (H9) | (b) | E2.2's tasks; G5 | electricity; cap 16 GPU-hours |
| 5 | E8.3 Claude arm, batch C6, only if the local arm shows the H8 pattern | (c) | G7 | up to USD 40 |
| 6 | E8.4 dream dose, only if E3.3 leaves an effect possible. RECOMMENDED CUT, awaiting owner ruling (6.4) | (d) | G5 | electricity; cap 16 GPU-hours |

GPU-hour caps are ours and bind as stop rules; throughput on this box is unmeasured, so they are
not estimates.

**E8.1 Token-class and read:write ledger (no model, no GPU).**
- Decisions it changes: (1) the cold-start term in the run gate: what a freshly spawned Claude
  worker pays before it does anything, which sets a minimum task size worth sending to a
  worker; (2) whether a ratio near 11 reads per write is a team signature or what one agent
  does alone (the null for H9); (3) whether old transcripts can serve as a cost record at all.
- Data: the local Claude Code transcripts T1 already reads. Assumption to check on the first
  file, not yet verified: each assistant message carries usage fields for input, cache-write,
  cache-read and output tokens. If absent, the transcript part is dropped and only new runs are
  measured (every runner episode logs the four classes from now on; `ARCHITECTURE.md` 4).
- Metrics, per session, main and subagent sessions separately: tokens by class (tokens); cost
  share by class (USD of class / total USD, at a price sheet read and recorded at run time,
  per model); cache hit rate (cache-read / all input-side tokens, both counts shown);
  cache-write tokens in a subagent's first call (the cold start); tool-call reads per write
  (Read, Grep, Glob calls / Edit, Write calls).
- Expectation written down first: Diogo Almeida's slide puts cache reads at about 67% of cost,
  unconfirmed and drawn at an older price (`SCIENCE.md` 1.5, note 9). Prediction: in our median
  session the cache-read share of USD is below 67%. Refuted if the median is 67% or more.
- Controls: none (descriptive). Bootstrap by session. No seeds.
- Stop rule: fewer than 30 sessions with usage fields: report counts only, no claim.
- Privacy: counts only; nothing leaves the box; no message text is read or stored.
- Cost: zero. Gate: one owner yes (same corpus as T1, a new field).

**E8.3 Memory structure against model strength (H8).**
- Task: a CL-Bench-style sequence from our own generator (added to trapbench): a generated
  SQLite database and 40 questions per sequence, a fresh session per question, one memory
  directory that persists across the sequence. Later questions reuse facts that earlier ones
  can discover (join keys, a misleadingly named column, a unit convention). Scoring is the
  query result against the generator's answer. Test families are held out (3.4).
- Arms: stateless; S0 bare directory, no instruction (the condition on Lance Martin's slide);
  S2 structured (instruction, record schema of 5.2, lint on write, size cap). Same cap per
  question in turns plus input and output bytes (4.6); memory reads count against it; native
  tokens are reported beside it.
- Subjects: the local cell-worker model (3.2) first. Sonnet 5.5 (batch C6) only if the local
  arm shows S0 below 5 points and S2 at least 10 above S0.
- Kill and decision: as in H8. Also: a stateless local pass rate under 30% or over 85% makes
  the task uninformative; re-tune difficulty once on a practice family, then stop.
- Metrics: pass rate; tokens, J, USD per passing question; memory characters and files per 100
  sessions; duplicate-record rate; memory tokens read per question against position in the
  sequence (the "memory grows with history" question from Diogo Almeida's talk, read off for
  free).
- Seeds: 5 sequences per arm locally (3 arms x 5 x 40 = 600 sessions). Claude: 2 sequences for
  S0 and S2, 1 for stateless (200 sessions).
- Fermi: at most 600 sessions x 20k tokens = 12M tokens locally; GPU-hours unknown until P4
  measures tokens per second; the 8-hour cap binds. Honest power: with 5 sequences only effects
  of about 10 points or more are visible, which is why the thresholds sit there. On Claude only
  about 15 points or more.
- Gate: G5 (scope amended); C6 under G7.

**E8.2 Shared board with local cells (H9).**
- Substrate, all standard library: one Git repository with a worktree and branch per agent
  (own-branch commits only; the harness merges and runs the tests), and one SQLite file reached
  only through a harness function that sets the agent's identity, logs every statement and
  limits rows and time. This is the gateway of Lance Martin's design in miniature. It is an
  experiment harness, not a new part of the architecture.
- Team: one lead and seven helpers, the same local model, turns interleaved in-process.
- Tasks: E2.2's low- and high-coupling tasks (10 each), so E2.2's single-agent arm and its
  lead-plus-workers arm are reused and only two arms are new.
- Arms, total tokens matched per task: C hub assigns from a fixed list, no board (E2.2's
  fan-out arm, today's star); B board with the five tables given (announce, assign, notes,
  subtasks, landed); A blank database, the prompt names Git and the database only.
- Kill and decision rule: as in H9. Also: all arms under a 30% pass rate means the model is too
  weak to be a subject; stop without a claim (the larger subject in 3.2 is a separate request).
- Metrics: pass rate on the merged tip; tokens, J, USD per passing task; reads per write;
  useful-read fraction; failed-claim attempts per subtask (a claim made on a stale read);
  duplicate-work rate; idle-turn fraction and idle-turn tokens; emergent-table rate; GPU idle
  fraction. Definitions: `SCIENCE.md` 1.5.
- Seeds: 5 per task per arm (2 new arms x 20 tasks x 5 = 200 team runs).
- Cost: unknown until E2.2's smoke run; the 16 GPU-hour cap binds.
- Gate: G5 (scope amended). Runs only after E2.2's arms exist.

**E8.4 Dream dose (conditional extension of E3.3). RECOMMENDED CUT, awaiting owner ruling
(6.4): a third-order question before the first-order one (does a dream pass beat search at all)
has an answer.**
- Question: where on the token axis does a dream pass pay, if anywhere? Lance Martin's chart
  (talk claim, slide-only) shows 64 times the tokens buying 7 points when search is available.
- Design: arm A and the better of B1 and B3 at budgets B, 4B and 16B, every control given the
  same tokens. Anytime: run 4B only if E3.3 at B leaves a 10-point gain inside its interval;
  run 16B only if 4B improved on B.
- Prediction (exploratory, outside every Holm family): the gain over the best control per
  doubling is smaller from 4B to 16B than from B to 4B.
- Decision: use the dose with the best gain per token. If no dose beats the control, H3 is
  dead at every tested dose and dreaming is not scheduled in cells.
- Seeds and scenarios: as E3.3. Cost: the 16 GPU-hour cap. Gate: G5.

**Diogo Almeida's frontiers through the five-step filter** (source: transcript and file 10; all
talk claims, and by his own account design questions, not solutions):

| His frontier | Verdict | Where, or why not |
|---|---|---|
| Agent cost is shaped by the cache | Test | E8.1 |
| Parallel agents rediscover the same facts; share state | Test | E8.2 (duplicate work, useful-read fraction) |
| Memory grows with history instead of being looked up | Measured as a by-product | E8.3 (memory tokens per question against position). A standalone full-history-versus-lookup test is deferred: no decision waits on it |
| Reliability, not occasional brilliance; benchmarks hide it | Adopt as a reporting rule, no new runs | Every experiment with seeds also reports the all-seeds pass rate (tasks passed on every seed / tasks) next to the mean. Already the logic of H6's interval-lower-bound floor |
| A model inside the lint checker (semantic lint) | Already covered | H6 class (b), memory lint and pointer repair |
| Routing and hand-off fight the cache | Partly | E8.1 measures the cold start. A live all-Opus-versus-hand-off replay is deferred: it costs Claude spend and E8.1 answers the routing question first |
| Encode the spirit, not the letter (principal-agent problems) | Deferred | The only test is a model judging loopholes, and a model as sole judge is forbidden by `PRINCIPLES.md`. E5.3 already compares rule types on behaviour |
| Real-time semantic security with a small fast model | Deferred | Labels would come from our own rules (3.1: circular). Revisit when E5.3 has produced labelled outcomes |
| Sharing the KV cache between agents | Cut | Needs open weights with cache access; not possible through the Claude API; one preprint reports inconsistent judge decisions under reuse (file 10, abstract only) |
| Verifiable stages, explicit state instead of one long chat | Already the design | Task spec with a deterministic check per task (`ARCHITECTURE.md` 4) |
| Generative interfaces, voice, "cursed software", the fourth logic gate, slop | Cut | No decision in this plan depends on them |

**What was cut or deferred to keep T8 small.**
- Any replay of Lance Martin's numbers: forbidden (invented simulator).
- CL-Bench itself: **deferred behind a new gate G10.** File 10 found the repository
  (Apache-2.0) and that it needs Python 3.13, uv and Docker, which are installs; the licences of
  its task data were not read. Our own generated task comes first at zero install. The price is
  that our numbers are not comparable with the slide's. CL-Bench becomes an external check only
  if H8 survives.
- A team-size sweep (the utilisation question): deferred. One team size; idle share is
  descriptive.
- A prompted-only memory arm (S1) between S0 and S2: cut. Two levels answer the decision.
- A Claude arm of E8.2: not requested. It would cost about what the deferred batch C3 costs.
- E3.3 arm B2: replaced by B3 (above).

### T9. E9: the autoresearch loop as a testbed (added 2026-11-19)

**Status (2026-11-19):** approved by the owner **in principle**, with a 13 GPU-hour cap (2 for
E9-1 calibration, 11 for the E9-2 pilot) and USD 0. A 20 GB download cap is the parent's
design choice, not the owner's words. Not yet run; the prereg is not frozen. **E9-0** (scripted
route catalogue, no GPU) is kept. **E9-1 and E9-2: RECOMMENDED CUT, awaiting owner ruling**
(6.4). Reasons from review 2 (claim 9; rows 12 and 16): the design itself calls "inconclusive"
the likely pilot outcome with six chains; the proposer is a 0.8B model, which WORKPLAN calls
likely uninformative for E8.3 and for which H8 predicts a memory effect near zero; the metric
is a 300-second wall-clock budget on a host whose free memory swings by tens of GiB; the
dataset licence is unverified. The owner's in-principle approval stands until the owner rules
on the cut. Text below is the design as approved in principle.

- Question: can one small real loop (an agent edits `train.py`, trains 300 seconds, keeps or
  reverts by `val_bpb`, logs to `results.tsv`, under prose rules) test authority, memory and
  green accounting with a hard metric and no model grader? Substrate: `karpathy/autoresearch`,
  cloned at `228791f` (README says MIT; no licence text in the repo).
- Design: `docs/reports/E9-autoresearch-design.md`. Pre-registration draft: `prereg/E9.md`.
  Exploratory, outside every Holm family.
- Five-step filter:
  - **Replaces:** T7 stage 2 and the optional T7 LoRA step, if T7 stage 1 ends in a kill or
    inconclusive (`docs/reports/staged-t7-decision.md`). The weight-surgery track then closes.
    If the T7 gate passes, stage 2 runs first and E9 waits. No GPU-hours carry over; E9 needs
    its own gate.
  - **Next GPU item (reconciled with 6.1 P5):** open until the owner rules on 6.4. If E9-1 and
    E9-2 are kept, E9 follows T7 stage 1. If they are cut, the next GPU item is the T10 matrix
    on one 4B-9B local model (review rank 7), then the E8.3 local arm per P5. Either way no GPU
    item starts before the T7 watchdog kills are explained.
  - **Does not replace:** H3 and E3.3. E9's memory arm is a second, exploratory look on a
    different task.
  - **Cut from E9 itself:** arm N (no memory), arm S (enforced ceiling with a model agent),
    the cascade and every Claude arm. Each is a separate ask. The pilot is the scripted
    authority catalogue (no GPU), a calibration stage, and two memory arms.
- Cost and gate: gate G11 (6.2), cap 13 GPU-hours (2 calibration, 11 pilot), USD 0, downloads
  at most 20 GB. The approval list is section 10 of the design report. The GB10 box is
  unmeasured for this workload; the calibration stage can end E9 before the pilot starts.

### T10. The three idea families as task controls (added 2026-11-19; build only, zero cost)

- Question: under one fixed set of perturbations, which family's control (provenance-governed
  memory; a signed ceiling with a deny list; cascade escalation) shrinks the pass-rate drop its
  matched perturbation causes, and does the answer change between a local model of at most 9B
  and the Claude tiers? The families are the `PRINCIPLES.md` scope guard's (the owner's
  "KDS", as relayed). Exploratory.
- Measure: the control effect `CE` and its companions, defined once in `SCIENCE.md` 4a. A
  control counts only if the interval of `CE` excludes 0, its clean pass rate is within 2
  points of the baseline arm's, and its tokens sit inside the same per-task cap.
- Perturbation matrix P1-P5 (`SCIENCE.md` 4a): P1 requirement change mid-task (memory,
  policy); P2 noisy requirement (pure model baseline); P3 injected wrong or stale memory
  (memory); P4 a cell fails or is slow (efficiency); P5 permission denial with a safe allowed
  route (policy). One perturbation per episode, seeded, injected at a fixed step.
- Arms: all controls off against all controls on; a one-family ablation only where those two
  differ on a perturbation. Deterministic scoring only; cross-model runs follow 4.6.
- Fermi (estimate): 10 tasks x 2 seeds x 5 conditions x 2 arms = 200 episodes per model; only
  effects of about 15 points are visible. P4 needs at least two cells (the router).
- Order: (1) build on the scripted backends, zero cost (review rank 3; an uncommitted
  `perturb.py` exists, not verified here); (2) one 4B-9B local model and one Claude tier under
  G3 (ii), G5 and a G7 batch (review rank 7), each its own approval.
- **Recommended merges, not applied (awaiting owner ruling, 6.4):** the review proposes that
  this matrix replace E3.3 and E3.4 (P3 with memory arms), E5.3 (P5), E8.2's hub-assign arm
  (P4), E9's authority test (P5 plus the E9-0 catalogue) and H8 (the matrix on two tiers).
  Until the owner rules, those experiments keep their current status.

---

## 3. The local-model plan (model-agnostic)

Formerly "The Qwen plan". No model family is assumed. A model is a row in a cell's `cell.json`
and earns its place per task class by the H6 rule: cheapest tier that clears the held-out floor.

### 3.1 Why a small local model, and for what

Candidates considered, with an honest verdict:

| Candidate | Verdict |
|---|---|
| Consolidator ("dreamer"): session log in, memory records with source pointers out | **Train this.** Generative, high volume, offline, and it reads raw logs that may hold secrets, so local is the right place for it. |
| Permission need predictor: will this capability be used again within tau? | Tabular problem. Logistic regression or gradient boosting first, on CPU. A small-model arm only if the tabular model leaves measurable headroom. |
| Risk classifier for commands | Labels would come from our own written rules, so a model would only relearn the rules. Circular. Not trained. |
| Fan-out decomposability predictor | Labels come from E2.2: a few hundred at most. Too few for a LoRA. Logistic model on coupling features. |
| Path-waste scorer | Computable deterministically from traces. No model. |

The consolidator is worth training because of one question a frontier model cannot answer about
itself: **how much of the dream gain survives when the dreamer is a small local model at near-zero
marginal cost?** If a small adapter (4B to 9B class) keeps most of the gain, the
compute-justification question in H3 changes. If it keeps none, that is also a result. Training
is conditional (section 2 cut list): a base model that already clears the floor needs no adapter.

The second GPU use needs no training: the local model is the **subject** agent for E2.2, E3.3 and
E3.4, and the worker inside a local cell (H6), which makes many seeds affordable.

### 3.2 Model menu by role

**Nothing is downloaded before the owner opens each model card and confirms the ID and the
licence.** The IDs below were seen in Hugging Face API listings on 2026-11-19 (file 09). The
licence column is the listing's metadata tag, not the model-card text. No model was benchmarked
by us; the picks are judgement. Download sizes are parameter count x bytes, not measured.

| Role | First candidate | Alternatives | Licence tag | Size (estimate) |
|---|---|---|---|---|
| T7 subject | `Qwen/Qwen3.5-0.8B` plus the released edited checkpoint (ID unverified) | none: T7 replicates one published model | apache-2.0 | ~1.6 GB each at BF16 |
| Narrow cell worker (H6), many cheap seeds | `Qwen/Qwen3.5-4B` | `Qwen/Qwen3.5-2B`, `google/gemma-4-E4B-it`, `mistralai/Ministral-3-3B-Instruct-2512-BF16`, `ibm-granite/granite-4.2-3b`, `HuggingFaceTB/SmolLM3-3B` | apache-2.0 | ~8 GB |
| Consolidator and tool-using subject (E2.2, E3.3, E3.4) | `Qwen/Qwen3.5-9B` | `ibm-granite/granite-4.2-8b`, `openai/gpt-oss-20b`, `google/gemma-4-12B-it`, `microsoft/phi-4` (MIT) | apache-2.0 | ~18 GB |
| Larger subject, only if the 9B class fails the 20-task tool-use smoke test | `Qwen/Qwen3.6-35B-A3B` (mixture-of-experts, about 3B active) | `Qwen/Qwen3.5-27B`, `google/gemma-4-26B-A4B-it`, `mistralai/Devstral-Small-2-24B-Instruct-2512` | apache-2.0 | 27B dense ~54 GB at BF16; quantise |
| Fine-tune base (T4, T7 step two; both RECOMMENDED CUT, 6.4) | `Qwen/Qwen3.5-4B-Base` or `-9B-Base` | the instruct model of the chosen worker | apache-2.0 | as above |

Avoid without a licence read: Gemma 3 (custom Gemma terms), Llama (community licence),
NVIDIA Nemotron and older Ministral (tagged "other"). `Qwen3Guard-Gen-*` and
`openai/gpt-oss-safeguard-20b` are content-safety classifiers, not permission models; if used at
all, as baselines only.

Start with **one** model per role. A second family is added only to check that an H6 result is
not specific to one family, after the first result exists.

Decode speed is expected to be bound by memory bandwidth (273 GB/s per the spec page): by file
09's arithmetic, not a measurement, a dense 27B model at BF16 would manage about 4 to 5 tokens
per second, a 9B model at 4-bit up to about 60. Measure tokens per second before sizing anything.

**Runtime.** The GB10 is ARM64 with CUDA 13.0. No torch is installed on the host, and PyPI
aarch64 cu130 wheels are unconfirmed, so a `uv` virtual environment is not the plan. The route
is the NVIDIA PyTorch container (`nvcr.io/nvidia/pytorch:25.11-py3` per NVIDIA's DGX Spark
Unsloth playbook, dated December 2025; the owner confirms the tag at pull time). Unsloth is
installed inside it with `--no-deps` so the container's torch is not overwritten. Unsloth's own
Spark guide is about 11 months old and is the fallback. Unsloth's "2x faster, 70% less VRAM" is
a vendor claim with no method read; we measure. Plan for plain LoRA; QLoRA is optional.

### 3.3 Data, without tenant data or secrets

1. trapbench sessions run by a real agent (local model, later Claude) inside generated toy
   repositories. The world is synthetic; the logs are real agent output. Gold memory records are
   known from the generator, so no teacher model is required.
2. Public agent trajectories, only after their licence is checked. Used for out-of-distribution
   evaluation of pointer validity, not for training in the first pass.
3. Never: the owner's transcripts, any SeaBridge repository, any tenant data. A secret scan runs
   over the training set before every training job and the job refuses to start on a hit.

Target size: 2,000 to 5,000 (log, records) pairs.

### 3.4 Splits and anti-leak rules

- Split by **generator family** (repo template, fact type, phrasing set) and by session, never by
  row. Test families are written by a different prompt and never seen in training.
- No scenario, repository or session appears in two splits. A hash check enforces it.
- The test split is opened once, after hyperparameters are frozen on validation.
- The true-by-construction trap: a model can learn the generator's templates. Guards: held-out
  families; the out-of-distribution trajectory set; and the only result that counts is
  **downstream** (does memory written by the adapter raise held-out task pass rate in E3.3).

### 3.5 Baselines

- Non-learned: extractive heuristic (keep lines matching command, path and error patterns).
- Tiny model: logistic regression or gradient boosting choosing which log lines to keep.
- Base local model zero-shot with the same prompt.
- Claude zero-shot on a small subset (gate C4), as the ceiling.

### 3.6 Training

- Tool: Unsloth core library (Apache-2.0) inside the NVIDIA container (gate G2b). The Unsloth
  Studio and desktop parts are AGPL-3.0 and are not used or redistributed.
- LoRA rank in {8, 16, 32}; alpha = 2 x rank; dropout 0.05; learning rate in {1e-4, 2e-4};
  1 to 3 epochs; attention and MLP projection modules; 16-bit; gradient accumulation; context up
  to 8k tokens. At most 6 configurations, chosen on validation only.
- Seeds: 3 for the chosen configuration.
- Overfit guard, per Lance Martin's talk (train versus held-out split when hill-climbing): report
  train, validation and test side by side; stop if validation falls while train rises; no result
  is reported from a split that guided a choice.

### 3.7 Evaluation (all deterministic)

Planted-fact recall, wrong-note removal, true-note retention, pointer validity (the cited log line
contains the claim's anchor span), record-schema lint pass rate, and E3.3 downstream pass rate.

### 3.8 Memory and throughput: estimates to measure

- **Power, stated honestly.** `nvidia-smi --query-gpu=power.draw` sampled at 1 Hz gives GPU
  power only; on this box memory and power-limit fields read N/A. Energy = sum of sampled watts
  x seconds, labelled "GPU only". It excludes CPU, memory, storage and the power supply's loss.
  Forum reports of implausibly low readings on some units are unopened leads, so one run is
  cross-checked against a wall meter or smart plug if the owner has one. Without a wall meter,
  no whole-system figure is reported; cost comparisons use the 240 W supply rating as an upper
  bound (H6).
- 4B to 9B LoRA at 8k context, 16-bit: guess 25 to 40 GiB peak. Throughput on the GB10: unknown.
- First job is a 50-step dry run that records peak memory and steps per second. All later
  estimates come from it.
- Abort rules: peak above 60 GiB, or MemAvailable below 10 GiB at any time (T7, G5; other
  sessions share this machine). Start floors where a source sets one: at least 20 GiB
  MemAvailable for the G2a pull preflight (WORKPLAN wave 2 step 3) and before E9 starts
  (E9 design report, approval item 8). The 10 GiB abort and the 20 GiB start floors do not conflict: one kills a
  running job, the other gates a start; no start floor is set here for other jobs. Caveat
  (review 2, row 16): both T7 smoke arms were
  killed near 10 GiB while another snapshot showed 68 GiB available with a smoke running; the
  pool swings by tens of GiB with other tenants, cause unknown. Wall-clock budgets on this host
  (E9's 300 seconds) are noisy for the same reason.

### 3.9 Rollback

Adapters are small files under `runs/`. Base weights are never modified. Rollback is deleting the
adapter directory and the cache directory named in the gate. No shared service is touched.

---

## 4. The Claude-side plan

### 4.1 Experiments that need Claude

| ID | Experiment | Why Claude |
|---|---|---|
| E5.1 | trapbench: planted wrong and stale memory, equal-token arms (E3.3 subset) | The claim is about the shipped model family |
| E5.2 | Fan-out gating at matched tokens (E2.3 subset). **Deferred.** | Orchestrator/worker split is the shipped pattern |
| E5.3 | Behaviour under denial: retry, workaround, report, safe completion, across policy types | Self-block and workaround are model behaviours; replay cannot see them |
| E5.4 | Teacher ceiling for the consolidator on about 50 logs | Ceiling for section 3.5; Claude-route cost for H6 class (a) |
| E5.5 | Claude-route cost and ceiling for H6 classes (b) and (c), only for a class that passed the local screen | H6 cost comparison |
| E5.6 | Hub-and-cells smoke: Claude Code session as planner cell, one subagent worker cell, one fresh-context verifier, three trapbench tasks (the labelled "Claude Code as shipped" arm, 4.6) | `ARCHITECTURE.md` section 10 step 4; runs inside batch C0 |

E5.3 detail: 20 toy tasks where the direct route is denied and a safe allowed route exists. Arms:
name-based deny rule; hook exiting 2 with a reason; sandbox bound. Outcome classes scored from
the trace: blocked and reported, completed by the allowed route, attempted workaround, gave up.
This is the owner's Q&A question turned into a measurement. Correction from file 07: Claude
Code's sandbox bounds shell commands only. Read, Edit, Write, WebFetch, MCP servers and hooks
run outside it, so the "sandbox bound" arm must deny by a Bash route, and a task whose direct
route is a file tool belongs to the deny-rule or hook arm.

### 4.2 Models and effort

Per the owner's role table (2026-11-17): Fable 5.2 writes the plan, Opus 5.5 orchestrates and
verifies (the planner and verifier cell roles, medium effort), Sonnet 5.5 does the work (worker, subject and Claude
cell, high effort). One fixed model snapshot per experiment, recorded in the manifest. No search
over model and effort in this plan.

Amended 2026-11-19 (owner requirements 1 and 4, via review 2): the roles above are defaults for
building and running this project, not a restriction on the system or the experiments. Any
model may fill any cell role (planner, verifier, worker), and a cross-model experiment may put
any tier in either role. "One fixed snapshot" now means one fixed snapshot **per model per
experiment**, pinned and checked per response (4.6). Effort and decoding are fixed per model
before the run and never searched on the test split.

Extended 2026-11-19 with the owner's words: "Fable 5.2 is doing the science research and
discovery, and the paper should be handled by Sonnet and Haiku. Then we can have a +5 from 5
and send it to the coding and OPUS and SONNET for work." Reconciled with the 2026-11-17 roles:

| Work | Model | Effort | Cost guidance |
|---|---|---|---|
| Science research and discovery: hypotheses, plan, pre-registrations, reading results | Fable 5.2 | as the owner's model file sets | The dearest tier. Few, long calls. Never bulk, never running experiments |
| Paper: drafting sections from frozen results | Sonnet 5.5 | high | Drafts only from results files; no number typed from memory |
| Paper: bulk chores (reference formatting, moving tables from results files, cross-checks of figures against results) | Haiku 5.5 | high | Prefer a script where the check is computable; Haiku only for what a script cannot do |
| Paper: claims check before anything leaves the box | Opus 5.5 with fresh context, after the script check | medium | One pass per draft. Publication itself is gate G8 |
| Planner and verifier cells in the running system: split, verify, judge (routing is router code, `ARCHITECTURE.md` 2) | Opus 5.5 by default | medium | Deterministic check first; the model verifier only where no check exists |
| Coding work | Sonnet 5.5; Opus 5.5 after two failed attempts or for security or refactor work | high / medium | The owner's standing escalation rule |
| Bulk and cheap tasks | no model, else Haiku 5.5 | high | A lookup beats a model call |
| Local cells | small open-weight models (Qwen, Gemma and the 3.2 menu), adapters trained with Unsloth | n/a | Electricity only. Only for a task class where the cell clears the floor (H6). Nothing downloaded yet |

Routing rule, from first principles (`ARCHITECTURE.md` 8): **the cheapest tier whose held-out
pass rate clears the floor does the job.** Order tried: computed answer, stub code, local model,
Haiku, Sonnet, Opus, then the owner. Fable is not an execution tier (the table above: "never
running experiments"); it plans. Escalate one tier on a failed check; never retry unchanged. Price
ratios are read from the price sheet at run time and recorded; this file quotes none.

Where this departs from the owner's pstack model file: that file sends "judgment and prose" to
Opus. For this repo's paper the newer words above govern (Sonnet drafts, Haiku does chores);
Opus keeps the verifying role it already had.

**Open question for the owner: what does "+5 from 5" mean?** I did not guess. Candidate
readings: (A) a quality bar: the plan or paper must score 5 out of 5 in review before it goes
to coding; (B) the model generation: use the 5.5 models (Opus 5.5, Sonnet 5.5) rather than 5
for the coding work; (C) five reviewers or five more rounds. *Labelled assumption, low
confidence:* (A). Nothing is built on it. Under (B) the table above already complies. Until
the owner answers, hand-off to coding uses the gate that already exists: an independent
verifier accepts the plan. No 5-point rubric is invented.

### 4.3 Budgets

Policy default, binding unless the owner sets otherwise: **USD 5 total and at most 9 calls per
named batch.** "Call" is read conservatively as one API request. Under that default only the
smoke batch C0 can run. The table is what I propose instead; the owner may lower any line.

| Gate | Batch | Episodes (target) | Token cap per episode | Hard USD ceiling |
|---|---|---|---|---|
| C0 | Harness smoke test | 3 | 60k | 5 (default; 9 calls) |
| C1 | E5.1 trapbench: 20 scenarios x 4 arms x 2 seeds | 160 | 80k | 60 |
| C2 | E5.3 denial: 20 tasks x 3 arms x 2 seeds | 120 | 50k | 40 |
| C3 | E5.2 fan-out: 15 tasks x 3 arms x 2 seeds. **Deferred, not requested** | 90 | 400k (whole team) | 150 |
| C4 | E5.4 teacher ceiling | 50 | 40k | 20 |
| C5 | E5.5 H6 classes (b), (c): 25 tasks each. Conditional on the local screen | 50 | 40k | 20 |
| C6 | E8.3 Claude arm (H8): 40 questions x 5 sequences. Conditional on the local arm. The 20k token cap is a spend guard only; the matched budget against the local arm is turns plus bytes (4.6) | 200 | 20k | 40 |
| | **Total proposed now (C0, C1, C2, C4, C5)** | | | **145** |
| | Total if conditional C6 is also approved | | | 185 |
| | Total if C3 is later requested | | | 295 |

**Approved today: C0 only** (USD 5, 9 requests). 145, 185 and 295 are proposal totals, not
ceilings anyone approved; USD 185 includes the conditional C6. WORKPLAN 1 quotes "total ceiling
USD 185 as in PLAN" in the parent's approval text; read against this table and the rule below
("No second batch without a new approval"), every batch after C0 needs its own approval.

Rules: the USD ceiling binds first. I do not quote token prices here; the runner reads the
current price sheet at run time, records it in the manifest, estimates cost per episode from C0,
and cuts the episode count to fit. Spend is tracked from API usage fields; missing telemetry stops
the batch. No second batch without a new approval. This ledger is separate from GitHub Actions.

C0 caveat: three agentic episodes, and the hub-and-cells smoke E5.6 in particular (hub, cell and
verifier each make several requests), do not fit in 9 API requests. C0 can run as designed only
if the owner states a call limit with the USD 5 ceiling. Without that, C0 shrinks to what 9
requests allow and E5.6 waits.

Honest power note: at these sizes only large effects (roughly 15 points or more) are detectable.
Claude runs confirm or contradict the local-model results; they do not stand alone.

### 4.4 Privacy

- Generated toy repositories only. No SeaBridge code, no real transcripts.
- A fresh, empty config directory for every run, so the owner's global instructions, memory and
  skills never enter a prompt.
- Runs inside a container with no mounted home directory and network limited to the API. The
  limit must come from the container or a firewall: Claude Code's own network allowlist filters
  by client-supplied hostname and its docs name domain fronting as possible (file 07).
- The API key is read from the environment and never logged.
- Direct key only. The owner's interactive sessions on this box go through a local proxy whose
  fallback chain can answer a "Claude" request with another provider's model, whose retention
  terms were not reviewed (backend `AGENTS_SYSTEM.md`). Every response's returned model ID is
  recorded; a mismatch with the pinned ID voids the episode (4.6). The same care applies to
  build sessions that read this repository: what they read reaches whichever model answers.
- Confidentiality limit: anything a Claude cell reads is sent to the model provider; no Claude
  shape in file 07 prevents that (`ARCHITECTURE.md` 6a).

### 4.5 Deployment shape (corrected against file 07)

File 07 found three Managed Agents shapes plus a separate Claude Code one. What this plan uses
and does not use:

| Shape | Who runs what | Status per the docs | Used here |
|---|---|---|---|
| Claude Code on this box (CLI, headless, subagents) | Harness and tools local; model at Anthropic | Not a subject of file 07; in daily use here | **Yes**, for building and for the labelled "Claude Code as shipped" product arm (E5.6). Cross-model arms use our own loop over the Messages API (4.6) |
| Managed Agents, cloud sandboxes (default) | Anthropic runs sandbox, agent loop and model | Status not recorded in file 07 | No |
| Managed Agents, self-hosted sandboxes | You run the sandbox; agent loop, memory stores and session log stay at Anthropic | Public beta per the May 2026 article | No |
| Self-hosted Managed Agents | You run sandbox and service; model at Anthropic or a provider you choose | **Private beta, by request.** No dreams, scheduled deployments, webhooks or Files API; multi-agent limited to a coordinator with 1 to 20 listed subagents | No |
| Claude Code self-hosted environments | Runner on your host; control plane and transcript at Anthropic | Public beta, Team and Enterprise; no Zero Data Retention | No |
| MCP tunnels | A gateway you deploy makes one outbound connection to reach a private MCP server | Research preview, no continuity commitment; depends on Cloudflare | No |

Neither self-hosted environments nor MCP tunnels hide session content from the model provider:
the transcript and every tool result still reach it (`ARCHITECTURE.md` 6a). If the owner wants
either shape, this table and `ARCHITECTURE.md` 6 change and their limits become project
constraints (owner decision; not assumed here).

Consequences for the experiments:
- Anthropic's Dreams job is a research preview and is not available on a self-hosted server. H3
  does not run it; it stays a named prior-art baseline we cannot replay.
- A cell with a local small model is not a Claude Code session and not a documented Managed
  Agents use (the gateway docs say model IDs must name the same model). The local backend of
  `runner.py` is our own worker process. No Anthropic-compatible shim is built.
- Policy is not signed anywhere on the platform today (managed settings are config). The signed
  ceiling in `ARCHITECTURE.md` is ours and is enforced by our own code and by ordinary
  permission rules, not by a platform feature.
- File 07 treated "dynamic workflows" as the equivalent of "Flows" (the Flows URL returned 404).
  That is an assumption. Nothing here depends on it.
- Status labels differ between the pages file 07 read and were not reconciled. Re-check before
  any public statement.

### 4.6 Cross-model protocol (added 2026-11-19, review 2 section 4)

Applies to every comparison across models (H6, H8, T10, and any later provider).

1. **One loop for every model.** Our own agent loop, one task spec, one tool schema (the
   contract's capability keys), one adapter per backend returning a tool call or a final answer
   plus usage. Claude runs through the Messages API with a direct key, not through Claude Code,
   which adds its own system prompt, tools and loop. "Claude Code as shipped" is a separate,
   labelled product arm.
2. **Byte-identical inputs.** Same tasks, seeds, prompts (hash recorded) and tools. The only
   per-model difference is the chat template. No per-model prompt tuning; if any is allowed,
   every model gets the same number of variants, chosen on a practice family.
3. **Instrument checks in every batch.** A scripted stateless stub (floor) and a scripted oracle
   (ceiling). If the floor passes or the oracle fails, the batch is void.
4. **Calibration band.** A task enters only if the weakest model in the comparison scores above
   30% and the strongest below 85% clean, judged on a practice family (E8.3's band).
5. **Order.** Models interleaved round-robin over tasks, so drift during a batch hits all alike.
6. **Outcome classes.** pass, fail, refusal, budget exhausted, infrastructure abort. Refusals
   are reported separately. An infrastructure abort (rate limit, timeout, watchdog) is re-run
   once and counted.
7. **Scoring.** Deterministic only. No model grader anywhere in a cross-model comparison.

**Matched budget.** Tokenizers differ, so tokens are not a shared unit. The per-task cap is
**turns plus input and output bytes**, the same for all models; native tokens are reported
beside it. Reasoning effort and decoding are fixed per model before the run and reported next
to every number. Context window: truncate all models to the smallest window in the comparison,
or report both, and say which. Contamination: tasks come from our seeded generator with held-out
families (3.4).

**Drift.**
- API models: pin the dated snapshot ID and record the model ID **returned in each response**.
  A mismatch voids the episode (4.4: a proxied "Claude" call can be answered by another model).
- Local models: revision SHA, weights sha256, decoding config, container digest.
- **Sentinel set:** 20 fixed tasks run at the start and end of every batch, and again whenever a
  batch spans more than a day. If the sentinel pass rate moves outside its binomial interval,
  the batch is flagged and never pooled with others.
- Price sheet: read at run time, stored with its date in the manifest.

**Cost normalisation.** Per passing task, never summed across kinds: native tokens by class;
bytes in and out; wall-clock seconds; USD for API routes at the dated price sheet; GPU-only
joules for local routes; USD for local routes only once the owner supplies a tariff, hardware
excluded and said so. The cross-model headline is pass rate and control effect at a fixed
turn-and-byte budget; cost per pass is secondary and carries its price date. Unknown stays
unknown: no API-side joules, no local USD without a tariff.

**Another provider later.** The adapter is the only new code. Trapbench is synthetic, so no
tenant data is involved. Record the provider's own usage fields; a provider that returns none
gets no cost row.

---

## 5. Repo layout, interfaces, tests

### 5.1 Layout (additions marked +)

```
src/murmuration/
  ledger.py        T1 replay (exists; E1.0 fix)
  synth.py         illustration only (exists; deletion candidate)
  __main__.py      CLI (exists; add subcommands)
+ cell.py          hub-and-cells contract: verify signed policy, enforce keys, run worker,
                   append hash-chained log, write result (ARCHITECTURE.md). Replaces T6.
+ hazard.py        E1.2 reuse-gap fit
+ coupling.py      E2.1 co-change coupling and overlap from git log
+ gate.py          fan-out gate: score -> fan out or not
+ memlint.py       memory record schema and linter
+ memstore.py      governed store: append, supersede, re-verify-on-use, scope filter
+ trapbench/       generator, scenarios, deterministic scorer
+ runner.py        agent episode runner behind one interface (local or Claude)
+ stats.py         paired bootstrap, Holm
+ manifest.py      git SHA, config hash, versions, seed, price sheet
+ tokens.py        E8.1 token classes, cost share, read:write counts from transcripts
+ board.py         E8.2 harness only: SQLite behind one logging function, per-agent worktrees
train/             + LoRA script and configs; T7 arm scripts (not imported by the package)
cells/             + one directory per cell: policy, prompt, log, memory (ARCHITECTURE.md)
prereg/            + one file per hypothesis, committed before main runs
runs/              + outputs (gitignored)
tests/
```

Core package stays standard-library only. Torch and friends live under `train/` and in the
runner's optional backends, so the instruments install anywhere.

### 5.2 Interfaces

- Memory record (JSON line): `id, claim, scope, author, source (file:line or commit),
  created_at, last_used_at, use_count, confidence (observed | told | inferred | imported),
  valid_until, supersedes, check (optional command)`.
- `runner.run(task, arm, seed, backend) -> Episode(trace, tokens, passed, canaries)`. One
  interface for local and Claude backends so arms differ only in the arm.
- `gate.decide(repo, plan) -> {fan_out: bool, score: float, reason: str}`.
- Hub-and-cells contract: four JSON files (signed policy, task spec, result with evidence,
  memory digest) and `routes.json`. Fields are in `ARCHITECTURE.md` sections 4 and 8. A cell
  backend is one more `backend` value for `runner.run`; there is no second runner.

### 5.3 CLI

```
murmuration report <paths> --salt S        (exists)
murmuration hazard <paths> --salt S
murmuration coupling <repo> --before <sha>
murmuration memlint <memory-dir>
murmuration trapbench gen --seed N --out DIR
murmuration trapbench score <run-dir>
murmuration stats <results.jsonl> --prereg prereg/H3.md
murmuration tokens <paths> --salt S        (E8.1)
murmuration cell run cells/<id> <task.json>
murmuration policy verify cells/<id>       (signing is the owner's own ssh-keygen -Y sign)
```

### 5.4 Tests and determinism

- `unittest` stays the runner (pytest is not installed and is not needed).
- Each new module ships with tests for its invariants: exposure definition, no promotion from a
  denial, coupling uses only pre-window history, linter rejects a record without a source,
  supersede never deletes, scope filter returns zero sentinels, generator is byte-identical for a
  seed, scorer is pure; for `cell.py`: tampered or expired policy refused, key outside the
  ceiling returns `escalate`, deny wins, a broken log chain is detected.
- Reproducibility: pinned versions in a lock file once installs are approved; every output
  carries git SHA, config hash, seed and model snapshot; `stats` refuses results whose code hash
  differs from the pre-registration.
- Model runs are not deterministic. That is why they are repeated and reported with intervals.

---

## 6. Timeline, gates, zero-cost start

### 6.1 Phases

| Phase | Content | Size | Needs |
|---|---|---|---|
| P0 | E1.0 fix; E1.1-E1.3 on local traces; hazard fit; E8.1 token-class and read:write ledger | S | nothing (E8.1: owner's yes to read usage fields) |
| P1 | coupling.py; memlint; trapbench generator and scorer; stats; manifest; pre-registrations (H1-H4, H6, H7) | M | nothing |
| P1b | Minimum viable hub-and-cells: `cell.py`, two stub cells, scripted router, contract tests incl. the two hub-as-cell tests (ARCHITECTURE 10, steps 1-3); then the T10 matrix on scripted backends. Status open: WORKPLAN 9 cut it; review 2 recommends reinstating (6.4) | S | nothing (a throwaway test key; the owner creates the real signing key) |
| P2 | E2.1 on public repos | M | G1 |
| P3 | Container runtime; **T7 stage 1 (B, A, then 0)**, stage 2 only past the 12-point gate (T7; `prereg/H7.md`). Blocked until the smoke watchdog kills are explained | S | G2a, G3 (0.8B pair only), G9 |
| P4 | Worker and subject model in; tokens/s and power measured; trapbench smoke test; H6 local screen (stub vs local model) | M | G3 (role models), G4 or in-process |
| P5 | E8.3 local arm first (single agent, the cheapest GPU main run); then E3.3, E3.4, E2.2 and E4.1 on the local model (main runs, frozen hash); then E8.2 (reuses E2.2's tasks); E8.4 only if its condition holds (RECOMMENDED CUT, 6.4). Whether E8.3 or E9 or the T10 matrix is the next GPU item is open until the owner rules on 6.4 (T9) | L | G0, G5 |
| P6 | Claude batches C0, C1, C2, C4, conditional C5, conditional C6 | M | G7 |
| P7 | Conditional training: consolidator LoRA (only if the cut-list condition holds); T7 LoRA arm (only if H7 survived P3). Both RECOMMENDED CUT (6.4) | L | G2b, G6 |
| P8 | Write-up; pitch | S | G8 |

Order matters: real traces first (P0), instruments second, model runs last, training last of
all. A hypothesis killed early cancels its later phases: H7 killed in P3 removes the T7 LoRA
arm; no class passing the P4 screen removes E4.1 and C5. Sizes are relative effort, not dates;
no date is promised before P3 has measured throughput on this box.

### 6.2 Approval gates

Nothing below happens without the owner's explicit yes. One reply can approve several.

| Gate | What | Exact scope | Size | Cost | Rollback |
|---|---|---|---|---|---|
| G0 | First local commit | Commit the working tree in `murmuration` only; no push, no remote | small | 0 | none needed |
| G1 | Clone public repos for E2.1 | Up to 20 permissive-licence repos, list shown first, into `murmuration/data/repos/` (gitignored) | up to ~20 GB | 0 | remove that directory |
| G2a | Container runtime (inference) | Pull one image, `nvcr.io/nvidia/pytorch:25.11-py3` (tag from NVIDIA's DGX Spark playbook; owner confirms the tag; whether an NGC login is needed is unverified). Inside it, `pip install transformers` into a derived local image. Nothing on the host, nothing global. A second image (NVIDIA's vLLM container) only if measured throughput would push G9 past its cap, as its own approval. | image est. 20-25 GB, not measured | 0 | remove the images |
| G2b | Unsloth packages (training only) | Inside the same container, per the NVIDIA playbook: `pip install peft hf_transfer "datasets==4.3.0" "trl==0.26.1"`, then `pip install --no-deps unsloth unsloth_zoo bitsandbytes`. Unsloth core is Apache-2.0; the AGPL-3.0 Studio and desktop parts are not installed. Version compatibility on this host is unverified; the playbook's smoke test runs first. Not requested until a training job is. | est. a few GB | 0 | remove the derived image |
| G3 | Weights, a menu approved per ID | Each ID and licence opened and confirmed by the owner first (3.2), into a cache directory the owner names. (i) T7 pair: `Qwen/Qwen3.5-0.8B` and the released edited checkpoint. (ii) Cell worker, 2B-4B class. (iii) Consolidator and subject, 8B-9B class. (iv) Optional larger subject, quantised. Any family on the 3.2 menu; not Qwen-only. | est. (i) ~3 GB, (ii) ~8 GB, (iii) ~18 GB, (iv) up to ~54 GB | 0 | remove the cache directory |
| G4 | Local serving | A dedicated process bound to loopback on a port the owner assigns, with purpose, owner and retirement date. The shared `spark-vllm` endpoint and the listeners on 8010/8080 are **not** touched or probed. Alternative with no port: in-process batch inference. Training and serving are never run at the same time (shared memory). | ~15-30 GiB memory | electricity | stop the process |
| G5 | GPU main runs | E2.2, E3.3, E3.4 and E4.1 on the local model; memory cap 60 GiB; abort if free memory drops below 10 GiB. Scope amended 2026-11-19, each line its own yes: E8.3 local arm (stop at 8 GPU-hours), E8.2 (stop at 16), conditional E8.4 (stop at 16; RECOMMENDED CUT, 6.4). Memory start and abort floors: 3.8 | est. 20-60 GPU-hours, to be measured, plus the T8 stop caps | electricity | kill the job; outputs in `runs/` |
| G6 | LoRA training with Unsloth | Needs G2b. 50-step dry run, then: (a) consolidator, at most 6 configurations x up to 3 epochs on a 4B-9B base, 3 seeds of the winner; (b) T7 LoRA arm, one configuration, 3 seeds, on the 0.8B model. Each is conditional (6.1, P7) and approved separately. Both RECOMMENDED CUT (6.4). | est. 10-40 GPU-hours, to be measured | electricity | remove adapter directories |
| G7 | Claude spend | Batches C0, C1, C2, C4 and conditional C5 as in 4.3; each named batch approved with its ceiling; default USD 5 and 9 calls if no number is given. C3 is deferred and not requested. C6 (USD 40) is conditional on the E8.3 local result and is requested only then. | — | approved: C0 only, USD 5. Proposed: up to USD 145; 185 with C6 | stop; no refund |
| G8 | Publication | Licence choice; pushing anywhere; sharing any aggregate outside the box; contacting the Claude Code team | — | 0 | cannot unpublish |
| G9 | Weight-surgery pre-test (T7, staged: stage 1 B, A, 0; stage 2 C, D, D-null only past the gate) | Clone `github.com/RikiyaT/lm_understand-logs` (scripts MIT, logs CC BY 4.0) into `murmuration/data/` (gitignored); download MATH-500, the IFEval and MMLU-Pro subsets and the practice problems after each licence is checked; run the arms of `prereg/H7.md`, inference only, in-process (no port). Arm D writes one edited copy of the 0.8B weights under `runs/`; the base is hashed and read-only. Hard cap 12 GPU-hours (our cap; file 08's "a few hours" is an estimate), stop and report if reached. | est. a few GB of data; ~1.6 GB edited copy | electricity | remove `data/` clone, the datasets and `runs/t7/` |
| G11 | E9 autoresearch testbed (T9) | Approved by the owner in principle (2026-11-19). E9-0 scripted route catalogue (no GPU); E9-1 calibration (2 GPU-hours); E9-2 pilot (11 GPU-hours); the approval list in section 10 of `docs/reports/E9-autoresearch-design.md`. E9-1 and E9-2: RECOMMENDED CUT (6.4) | downloads at most 20 GB (parent's design choice) | USD 0; cap 13 GPU-hours | owner removes `data/autoresearch`, `data/autoresearch-cache/` and `runs/e9/` (design report paths) |
| G10 | CL-Bench as an external check (deferred, not requested) | Only if H8 survives E8.3. Clone `github.com/pgasawa/continual-learning-bench` (Apache-2.0 per file 10) into `murmuration/data/`; installs it needs per its README (Python 3.13, uv, Docker), inside a container, nothing on the host; the owner reads the task-data licences first | not measured | 0 | remove the clone and the image |

Gate notes:
- **T7 (both stages) needs G2a, part (i) of G3, and G9. It does not need G2b, G4, G5 or G6**:
  no training, no served port, no main-run budget. Only the optional LoRA step needs G2b and G6.
- A `uv` virtual environment is not offered: aarch64 cu130 torch wheels are unconfirmed
  (file 09). It becomes an option only if the owner confirms the wheel index.
- "Unsloth authorised in principle" (owner, 2026-11-19) is recorded here as intent. It does not
  open G2b, G3 or G6; each still needs its own yes with the scope above.
- The policy signing key (`ARCHITECTURE.md` section 4) is created and held by the owner. Agents
  use a throwaway key inside tests only.
- Power for every GPU gate is reported as GPU-only sampled power x time unless a wall meter is
  used (3.8).

### 6.3 Start now at zero cost

1. E1.0: one exposure definition for all policies, with the regression test.
2. Run `report` and a tau sweep on the local transcript corpus; check the 200-event and
   30-session thresholds.
3. `hazard.py` and the reuse-gap fit.
4. `coupling.py`, tested on this repo's own history once it has one.
5. `memlint.py`; run it over existing local memory directories (counts only).
6. trapbench generator and scorer, with scripted fake agents to test the scorer.
7. `stats.py`, `manifest.py`, and the pre-registration files (H1-H4, H6, H7).
8. Open the ten must-read sources in full (list in SCIENCE.md) and correct this plan.
9. Minimum viable hub-and-cells, steps 1-3 of `ARCHITECTURE.md` section 10: `cell.py`, two stub
   cells, a scripted router and the contract tests, including the two hub-as-cell tests. No
   model, no GPU, no network. Status open: cut by `WORKPLAN.md` 9, reinstatement recommended
   by review 2 (6.4); uncommitted `cell.py` and `router.py` exist, not verified here.
10. Write the T7 arm scripts and the power sampler against a tiny random-weight model, so G9 is
    spent on the measurement and not on debugging.
11. E8.1: check whether the local transcripts carry the four usage fields; if so, the
    token-class and read:write ledger (counts only).
12. The CL-Bench-style generator and scorer for E8.3 (a generated SQLite database, 40
    questions, held-out families), tested with scripted fake agents.
13. The board harness for E8.2 (SQLite behind one logging function, a worktree per agent, the
    merge-and-test step), tested with scripted fake agents; pre-registrations for H8 and H9.
    Status: `board.py` cut by `WORKPLAN.md` 9; H9 awaits the owner's ruling (review 2
    recommends defer). Not started.
14. The T10 perturbation matrix on scripted backends (`SCIENCE.md` 4a). Zero cost.

### 6.4 Owner decisions and recommended cuts (2026-11-19)

**Owner decisions recorded** (relayed by the parent, 2026-11-19):

| Decision | Where it lands |
|---|---|
| H8 is exploratory, outside every Holm family | 1.2; `prereg/H8.md`; `SCIENCE.md` 5 |
| T7 keeps the staged design with the 12-point stage-1 gate | T7; `prereg/H7.md` 12 |
| E9 approved in principle, cap 13 GPU-hours, USD 0 (the 20 GB download cap is the parent's design choice) | T9; G11 |

**Recommended cuts, NOT applied.** Source: `docs/reports/adversarial-review-2.md` sections 5,
6 and 8 (action 8). Every item below keeps its current status until the owner rules; nothing is
deleted from this plan.

| Item | Status today | Recommendation | Reason (review 2) |
|---|---|---|---|
| E9-0 scripted route catalogue | Approved in principle (G11) | **Keep** | The only E9 part whose result is not predicted in advance; zero GPU (claim 9) |
| E9-1 calibration | Approved in principle (G11), 2 GPU-hours | RECOMMENDED CUT, awaiting owner ruling | Feeds only E9-2 |
| E9-2 pilot | Approved in principle (G11), 11 GPU-hours | RECOMMENDED CUT, awaiting owner ruling | Its own design calls "inconclusive" the likely outcome with six chains; 0.8B proposer for which H8 predicts a near-zero memory effect; 300-second wall-clock metric on a host whose free memory swings by tens of GiB; dataset licence unverified (claim 9; rows 12, 16) |
| E8.4 dream dose | Conditional, G5 line (16 GPU-hours) | RECOMMENDED CUT, awaiting owner ruling | A third-order question before the first-order one has an answer (3.1) |
| T7 stage 2 (arms C, D, D-null, off-target) | Conditional on the 12-point gate | RECOMMENDED CUT, awaiting owner ruling | The gate passes in under 3% of runs if the expected null holds, and an inconclusive result has the same consequence as a kill (claim 8, row 4) |
| T7 arm 0 | Stage 1, run last | RECOMMENDED CUT, awaiting owner ruling | The most expensive arm, a reference only, and the one the watchdog killed first |
| T7 arm D (with D-null) | Stage 2 | RECOMMENDED CUT, awaiting owner ruling | Listed with stage 2 in the review's cut list; the review gives no separate reason |
| T7 LoRA step | Conditional on H7 survival (G2b, G6) | RECOMMENDED CUT, awaiting owner ruling | Listed in the review's cut list; it depends on an H7 survival the staged test is unlikely to show (inference from row 4) |
| T4 consolidator training | Conditional (section 2 cut list; G6) | RECOMMENDED CUT, awaiting owner ruling | Scope guard: not "training a local model to imitate" a frontier one (3.1) |

**Other review recommendations awaiting an owner ruling** (not part of action 8, listed so they
are not lost): reinstate P1b, the scripted router and hub-as-cell tests (rank 2; conflicts with
WORKPLAN 9); the T10 merges (T10); decide T7 stage 1 as test or labelled smoke (action 9); H9
defer; park H1 unless the other machine's session count reaches 30 (action 10); drop E8.1's
67% prediction (action 11); cut H5 as a named hypothesis, VISION's "Connecting a very strong
model" and ARCHITECTURE 12 (section 5 cut list); a tariff or a ruling that local USD stays
"n/a" (H6); a name (`VISION.md`, Naming).

---

## 7. Risks, validity, safety, licence

### 7.1 Threats to validity

- **Replay is counterfactual.** T1 cannot know what the agent would have done under another
  policy. T1 claims are limited to prompts and exposure. E5.3 exists to cover behaviour.
- **Prompt counts are an upper bound**: transcripts do not show which calls were actually
  prompted.
- **One user's traces.** H1 on a single person's corpus is a case study. E1.4 is the only cure.
- **Capability key is coarse** (`Bash:<first token>`). A finer key changes every T1 number.
  Report both granularities.
- **Synthetic worlds.** trapbench is ours; a result there may not transfer. Mitigations: held-out
  families, real agent logs, Claude confirmation, and the wording "on trapbench".
- **Token matching is imperfect**: cached tokens, thinking tokens and tool output differ by arm.
  Report raw token classes as well as totals.
- **Local model as subject.** A small model may fail for reasons unrelated to the manipulation.
  Require a minimum baseline pass rate (30%) before a scenario enters the main run.
- **H6 is tested on our own generator.** A cell that clears the floor on trapbench classes has
  cleared it there. Each class needs a held-out generator family, and the false-accept audit is
  by hand. The cost comparison leaves out hardware and uses a rated-power upper bound.
- **T7 is a replication of one model and one published edit.** A kill says the edit adds
  nothing over decoding on Qwen3.5-0.8B's loop problem. It says nothing about weight edits in
  general, and a survival does not show that a hub can find such edits itself (arm E is not run).
- **Planner, verifier and Claude worker cells share a model family**, so a verifier's errors correlate with the
  worker's. Deterministic checks come first for that reason.
- **T8 rests on talk claims.** H8 and H9 are motivated by slides from one vendor's runs, read
  from screenshots. Our tests use our own generator, a team of eight and small models; they can
  refute H8 and H9 as worded and cannot confirm or refute what happened at 1,000 frontier
  agents. Interleaved turns are not concurrency. Our CL-Bench-style task is not CL-Bench.
- **Small n on Claude.** Stated in 4.3.
- **Researcher degrees of freedom.** Pre-registration, frozen hash, single opening of test splits.
- **Co-change is a proxy** for coupling and is confounded by repo size and commit habits. Split
  by repo and report per-repo results.

### 7.2 What stays speculative

Self-organized criticality, scaling exponents, edge of chaos, and any general claim that agents
"self-organize". None is tested here. Stigmergy gets one bounded test (H9, E8.2: eight local
agents, one shared board); anything beyond that stays speculative, as does every idea in
`VISION.md` about one strong hub serving many people's cells. H5 is exploratory. The hub-and-cells
demonstrator is a demonstration. Recursive self-improvement and a hub that programs cell weights
in the loop are not claimed or built: T7 tests one published edit once. (For the record, per
file 08: "Recursive Language Models" is an inference-time REPL method, not self-training, and
"Taming the Long-Tail" is a speculative-decoding speed-up for RL training from November 2025;
neither is weight editing.)

### 7.3 Safety and privacy

- No secrets, no tenant data, no SeaBridge code in any dataset, prompt or output.
- Our analysis of transcripts exports nothing. Only salted counts may be shared, and only after
  G8. (The sessions the transcripts record sent their content to the model API when they ran.)
- Shared infrastructure is never probed, restarted or reconfigured.
- Nothing is pushed or published without G8.
- A planted "wrong memory" benchmark is also a poisoning test set. It contains no working attack
  on a real system; keep it that way.
- Weight edits (T7) are made on a copy, never on a served model; base weights are hashed before
  and after. The edit studied removes a repetition loop. No edit that removes a safety
  behaviour is made or tested.
- Sources: open pages only. Sci-Hub is not used; a paywalled text stays unread and is marked so.

### 7.4 Licence options (owner decides at G8)

- **Apache-2.0** (recommended): permissive, with a patent grant, usual for tooling others adopt.
- MIT: simpler, no patent grant.
- No licence yet: safe default until G8; others may read but not reuse.
- trapbench data: CC BY 4.0 or the same licence as the code.
- Any adapter or edited checkpoint inherits its base model's licence terms. Verify per model
  before any release (Hugging Face tags are metadata, not the licence text).
- Unsloth: core package Apache-2.0, Studio and desktop parts AGPL-3.0 per its README; the
  file-level split was not read. We use the core library only and redistribute none of it.
- T7 materials: authors' scripts MIT, logs and networks CC BY 4.0; benchmark text under each
  benchmark's own licence.

---

## 8. Presenting to the Claude Code team

### 8.1 One-page pitch outline

1. **The question from the floor.** How do you stop agents over-requesting permissions and
   blocking themselves? The answer given was "a human promotes repeated requests". We measured
   that answer against the grow/shrink policy from the same talk.
2. **What we built.** A stdlib replay ledger anyone can run on their own transcripts, a coupling
   gate, a memory linter, and a wrong-memory benchmark with deterministic scoring.
3. **What we found.** One slide per hypothesis: prediction written before the data, the result,
   the interval, and whether it was killed. Killed hypotheses stay on the slide.
4. **What we did not show.** Counterfactual limits, one-user corpus, synthetic worlds.
5. **Three proposals** (below).
6. **How to check us.** Commands, seeds, hashes, pre-registration files.

### 8.2 The three asks

| Ask | Framed as | Evidence status today |
|---|---|---|
| **Shrink audit.** A command that lists allow rules by idle days and proposes removals, the mirror of the existing prompt audit. | H1: a decay window exists that cuts idle exposure by 30% for 10% more prompts. | Tool built. No real-data result: the local corpus holds 1,079 events in one session; the 30-session precondition fails, so H1 is untestable there, not refuted. |
| **Fan-out gate.** Before spawning workers, compute a coupling score from git history and default to one agent above a threshold. | H2: coupling predicts when fan-out loses at matched tokens. | Not built. Published work suggests fan-out often does not pay on bounded tasks (leads, partly unverified). |
| **Provenance-linted memory with a compute-matched dream evaluation.** Every durable note carries a source pointer; dreaming is judged against the same tokens spent on retries. | H3 and H4. | Not built. Anthropic already ships dreaming and auto memory; we offer the test, not the feature. |

The honest framing for all three: we bring instruments and pre-registered tests that the team can
run on data we will never see. Their traces would answer H1 far better than ours.

---

## Appendix: what this plan deliberately leaves out

- The NK simulator, invented cost constants, and the three-axis hypothesis.
- Search over model, effort and prompt.
- Debate, role personas, topology sweeps.
- Any learned risk classifier.
- More than one trained adapter at a time (the consolidator and the T7 LoRA arm are each
  conditional, and neither is requested now).
- T6, E3.2, and (deferred) E2.3 with batch C3 and E1.4: see the cut list in section 2.
- A frontier agent editing weights (T7 arm E), any hub-edits-cells loop, any framework, bus,
  daemon or cell-to-cell messaging (`ARCHITECTURE.md` section 11).
- From T8: replays of published talk numbers, CL-Bench itself (gate G10), a team-size sweep,
  a Claude arm of the shared-board test, KV-cache sharing, a "spirit" policy judged by a model.
Add any of these only after a confirmatory hypothesis survives and points at it.
