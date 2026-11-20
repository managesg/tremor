# QGrid, Lean and auto-research: assessment and order

2026-11-20, revised after QGrid was found. Author: Fable 5.2 (planner). A proposal on paper.
Nothing was built, installed, run or spent. Read from the murmuration tree at 36bab4b plus
uncommitted work, and from a read-only shallow clone of QGrid at `data/qgrid` (gitignored).

The owner asked: "Should we use the Quantum Simulator and Lean from out Qgrid project to test the
findings too? Implement it altogether with auto research."

**Handling rule for QGrid.** It is a hackathon project with several contributors and no licence
file. Internal use only: this document copies no code or text from it and names no person. We
call it in place from `data/qgrid`; we do not vendor it. Before any run, the owner should confirm
that the other contributors agree to this use.

## 1. Verdicts (recorded 2026-11-20)

Two independent adversarial reviews (`docs/reports/gpt-adversarial-review.md`,
`docs/reports/cursor-adversarial-review.md`) and my own earlier view agree: sequence and cut.
**Nothing in this document is scheduled before EP-1 is reported.** Sections 4 to 8 are kept as
the design that would apply if an item returns.

| Item | Verdict | Condition for return |
|---|---|---|
| Second task family from QGrid | **DEFERRED** | After EP-1 is reported. Only as a **frozen tiny export** (a hashed table and its inputs), never a live link to a repository that keeps changing |
| Python mirror of the Lean checker | **CUT as a scorer** | None. A mirror that accepts what real Lean rejects is the "accept if present" bug again |
| Quantum stage | **CUT from every scored loop** and from every claim in a paper or abstract | None. Classical baselines at most |
| Auto-research over cards (`ar1`) | **DEFERRED, possibly dropped** | All six preconditions of section 7.0 |
| `lab/` auto-research scaffold | **Kept as an unrun artefact** | Not run, not cited as a result |
| QGrid history as an observed setting | Deferred, optional | After EP-1 is reported; counts only |
| Lemma-proving Lean family (my first draft) | **CUT** | None |
| "Implement it altogether" | **No** | One step at a time, each behind its own gate |

## 2. What QGrid is (read, not run)

- **A four-stage pipeline** behind fixed interfaces and five JSON contracts: grid snapshot, plan
  proposal, physics check, certificate. A stage that is missing falls back to a fixture and is
  labelled `FIXTURE`; the project rule is never to present a fixture stage as a measured result.
- **A feedback loop.** A blocked certificate yields a constraint that is passed to the next
  proposal round, up to a round limit.
- **The plan space is small and discrete:** 630 plans per site by default (how the load is split
  over 4 candidate substations, plus three levers). It can be enumerated.
- **The physics check** is a power-flow run with a one-line-out test, built on `pandapower`.
- **The Lean part** is Lean 4, toolchain pinned to v4.35.0, **no Mathlib and no other package**,
  about 580 lines in three files. It compiles to a checker program that reads evidence and
  returns a verdict over 11 encoded rules, tagged hard or negotiable. The theorems are about the
  checker itself (the verdict is sound and complete for the encoded rules, deterministic, and
  names the first failing rule). The status board says 6 theorems; an audit file lists 11 for an
  axiom check. They are not proofs about any one plan.
- **A Python mirror** of the Lean checker decides when Lean is not installed, and says so in the
  certificate. A parity test compares mirror and Lean, and it is skipped when Lean is absent.
- **The quantum part** is a Grover-style search run on a classical simulator (PsiQDK), with a
  numpy fallback and two classical baselines (random and heuristic). The record names the engine
  that actually ran.
- **Process:** three lanes with folder ownership, contract changes only after a posted notice, a
  status board, and one adversarial review with 10 findings, part fixed at the snapshot I read.
- **Tests:** about 50 test functions.

**On this machine:** `aarch64` Linux, 2.6 TB free; no Lean (I checked the path); no PsiQDK and no
`pandapower` (parent's check). So today nothing in QGrid beyond the mirror could run here.
Whether Lean 4.35.0, `pandapower` and PsiQDK install and work on ARM64, and their sizes, are
**unverified**. Every install is an owner gate.

## 3. First-principles check

The five-step filter of `PRINCIPLES.md`: the QGrid family answers a real question (does the
result hold under real coupling and a real verifier?), so it survives step 1, simplified to
cached snapshots and one precomputed table. Auto-research answers "is card wording worth
tuning?" and comes last, because automation is step 5. The quantum stage changes no decision of
ours and is deleted at step 2.

- **Units.** Every outcome is a count over a stated denominator; cost is tokens and USD from the
  ledger.
- **Matched budgets.** Every arm and every control chain gets the same calls and caps.
- **Deterministic scoring.** Sealed code scores from logs. No model grades anything.
- **No invented simulators.** We write no quantum simulator and no power-flow solver.

## 4. QGrid as a task family (DEFERRED)

A moving owner repository would itself become the confound. If this family returns, it is built
from a frozen tiny export: the verdict table below, its inputs and their hashes, made once.

### 4.1 The task

A task is one site, one cached snapshot and one requested load. An agent submits a plan as an
index or a contract-shaped object. **Acceptance is deterministic:** the plan matches the
contract, the physics check passes, and the certificate is green. Amber is counted separately,
never as a pass.

Because there are only 630 plans, the harness computes the verdict of every plan once, offline,
and seals the table. Scoring is then a lookup, the oracle and the random floor are exact, and no
physics or Lean runs during a paid episode. `Y` = distinct tasks with an accepted plan / work
slots, as in EP-1.

Why it is a better family than lemma proving:

- **Agents submit data, not Lean.** No untrusted code runs, and no model can type `sorry`.
- **Real coupling.** Sites share substation and transformer capacity, so one agent's accepted
  plan can make another's fail.
- **The capability floor can be measured before spending:** the share of the 630 plans that pass
  is the random floor. The 30% to 85% window for the model is then checked by a small paid pilot.

### 4.2 Can it host our practices?

| Practice | Fit | How it is measured |
|---|---|---|
| A, claim before work | Good | Tasks are sites; shared capacity is the contested resource. Duplicate work = two agents planning the same site; collisions = two accepted plans that cannot both hold |
| B, write only to pages you own | Good | QGrid's own lanes and contract notices are this practice. Each agent owns one site page of quoted snapshot facts; the read-off is how many facts survive unchanged |
| E, not done until the check passes; someone else verifies | **Best** | A plan reported as accepted that the sealed table says fails is an error passed through. QGrid's `FIXTURE` rule is the same idea |
| Poisoned note | Good | The feedback loop already carries constraints from one round to the next. A planted wrong constraint or a wrong capacity figure is a poison whose truth can be replayed against the snapshot |

Each practice still needs its card, its neutral twin and its router predicate. Only E and the
poisoned note are worth building first; A is already tested by EP-1.

### 4.3 Risks specific to this family

- **Dependencies.** The physics table needs `pandapower`; the certificate needs real Lean. Both
  unverified on ARM64.
- **Determinism of the physics check** across versions and machines: unverified.
- **Time to enumerate** 630 plans with the one-line-out test, per task: unknown.
- **Few tasks.** Few cached sites; train and held-out may differ only by load and scenario.
- **Prompt size** under a new per-call cap: unknown.
- **Licence and consent** (handling rule above).

## 5. Verifier gaming and verifier error

The agent cannot touch the checker, so the classic routes move from the agent to the build:

| Route | Where it could enter | Guard |
|---|---|---|
| `sorry`, a new `axiom`, `native_decide`, `unsafe` | The Lean sources, if edited | Seal `lean/` by hash; run QGrid's axiom audit once at build and record its output; any change voids the table |
| Extra imports or packages | The Lean manifest | It lists no packages today; seal it |
| **Mirror against real Lean** | The mirror decides when Lean is absent | **The mirror is cut as a scorer.** Only the real Lean checker, built from the pinned toolchain, gives a verdict. No pinned toolchain, or a mirror-only row: the verdict is **INVALID**, not pass and not fail, and the task is excluded |
| Two verifiers disagree | Physics check and Lean checker both exist | **Pre-registered: the counted verdict is the Lean checker's verdict on evidence that includes the physics result.** A failed or missing physics result is a fail or INVALID, never a pass. Nothing else counts |
| **Mis-encoded rules** | The theorems prove the verdict matches the encoded rules, not that the rules match the grid or the utility | Claim only "passes the encoded rules". Say so in every report |
| Unverified evidence builder | Python turns plan and physics into the evidence Lean sees | It is outside the proofs. Seal it; treat it as part of the scorer |
| Fixture presented as measured | A missing stage falls back silently to a fixture | The table build fails if any stage is labelled `FIXTURE` |
| Plans fitted to the rules | An agent finds plans that satisfy the letter of the rules | That is the task. It limits what a green plan means, not our measurement |

**Canaries that must score zero**, frozen as fixtures before any table is sealed. Each is a
doctored copy of the checker or its inputs, and each must fail the build or be marked INVALID:

- `sorry`; `admit`;
- an extra axiom, or `native_decide`;
- a weakened statement;
- a lemma that assumes the goal;
- an unsealed or extra import;
- an edit to a theorem instead of to its proof;
- a mirror-only verdict; a missing or unpinned toolchain; a `FIXTURE` stage.

One canary that scores above zero voids the table.

## 6. QGrid itself as an observed multi-agent setting

QGrid was built by lanes working in parallel under written rules: folder ownership, contract
notices, a status board, honesty labels and an adversarial review. That is a small real instance
of practices B and E.

**Proposal: a read-only observational note, zero API cost.** The local clone is shallow (one
commit), so it needs one read of the public history and of pull-request and issue metadata, with
the owner's go-ahead. (A file `docs/reports/qgrid-coordination-history.md` appeared while I
wrote this; I have not read it.)

Aggregate counts only, lanes numbered, no names, no quotes: the share of pull requests that touch
one lane's folders only; contract changes preceded by a notice; review findings opened and closed
and the time to fix; stages labelled `FIXTURE` over time; reverts soon after a merge.

It can say whether the written rules were followed in one real project. It cannot say anything
causal or general: one team, one day, an unknown mix of people and agents, no control. Its only
use is to choose which practice to test. If the first three counts cannot be computed, stop.

## 7. Auto-research over practice cards (`ar1`) (DEFERRED)

### 7.0 Why deferred, and the preconditions

It is a Goodhart engine aimed at our known weakness: a card that leaks the scorer's check. Every
keep is a look at the score. It returns only when all six hold:

1. EP-1 is reported.
2. The scorer is frozen.
3. Two sealed held-out families exist, made by a **different generator**, absent from the
   repository and from every prompt, and scored once after the search is frozen.
4. A human-written card sits in the same results table.
5. An edit cap is pre-registered (how many edits, and how large).
6. One held-out score is named in advance that can kill the card.

Precondition 3 is not met by anything we have: the allocation family's held-out set comes from
the same generator. The `lab/` scaffold stays as an unrun artefact. The USD 3.00 for `ar1` stays
allocated and unopened. Sections 7.1 to 7.7 describe the design and its arithmetic, not a plan.

### 7.1 Design

Karpathy's pattern (`docs/research/17`, `docs/reports/E9-autoresearch-design.md`): one editable
file, a fixed budget per experiment, keep or revert by a deterministic metric, a results log;
plus a train and held-out split, as in Lance Martin's skill hill-climbing.

- **The one editable file** is a *copy* of card A in a scratch area, within 600 bytes, with its
  neutral twin regenerated. Nothing under `practices/` changes.
- **Code location:** `lab/`, outside the hashed `src/`, `practices/` and `tests/`, so it cannot
  invalidate the EP-1 freeze.
- **Metric:** the sealed `Y` on train task sets with a real model.
- **One iteration:** a proposer call writes a candidate; candidate and current card run on the
  same 20 train sets, paired: 2 x 20 x 8 = 320 calls, plus the proposer call.
- **Keep or revert:** keep only if the 95% paired interval of `Y_candidate - Y_current` lies
  above 0. Plain git in a scratch worktree whose path the owner approves.
- **Held-out guard:** scored once, at the end; the only source of a claim.
- **Sealing and leak check:** `seal.py` covers scorer, task sets, templates and the loop.
  `practice.leak_check` must match operands and task ids as well as answers, and the card ban
  list of the EP-1 prereg applies to every candidate.
- **Log:** one JSONL line per iteration: card hashes, both scores, interval, kept or reverted,
  tokens, USD.

### 7.2 Controls, matched in calls

- **Random-edit chain:** the same number of iterations, with random edits of the same size and no
  model proposing.
- **Reverted baseline (A/A):** the candidate is the current card, byte for byte. A keep here is a
  false keep.

### 7.3 Budget inside USD 3.00

The USD 10 is shared: EP-1 USD 5, `ar1` USD 3.00, USD 2 unallocated. `ar1` cannot open until
EP-1 has settled as `complete` or `inconclusive`.

Per call, from EP-1's reserved worst case (USD 0.275 per 500 calls): USD 0.00055. Likely about
USD 0.00008 (G0-2R's "about USD 0.04" for 480 calls).

| Item | Calls | Reserved | Likely |
|---|---|---|---|
| One iteration | 321 | USD 0.177 | about USD 0.028 |
| Iterations USD 3.00 holds at full reservation | | **16** (17 would need USD 3.001) | |
| Held-out at the end: 3 cards x 20 sets x 8 | 480 | USD 0.264 | about USD 0.04 |
| **Proposed run: 15 iterations (6 proposer, 6 random-edit, 3 A/A) plus held-out** | 5,295 | **USD 2.91** | about USD 0.46 |

Six proposer iterations are a test of the loop, not a search. Unverified until the canary: the
Haiku 5.5 price, and so every USD figure. The proposer call's size is my estimate. `ar1` would
also need its own caps in the spend code, a spend review and a pre-registration.

### 7.4 Kill criteria

- Do not open if EP-1 shows `Y_none` within 10 points of `Y_code`: no room for a card.
- Any keep in the A/A iterations, or no keep in 6 proposer iterations: stop.
- The pre-named held-out score not met, or not above the random-edit chain: the card is dropped.
- Any spend stop, seal break or leak-check hit stops the chain.

### 7.5 Risks

- **The card may smuggle the answer** or the task's structure. The leak check catches literal
  answers; only a held-out family from another generator catches the rest.
- **Winner's curse.** Six looks at noise keep something by luck about one time in seven.
- **Tuned to one model.** A card tuned on Haiku 5.5 is a card for Haiku 5.5.

### 7.6 Allocation family or QGrid family?

Allocation is ready and its cost is known (1,386 bytes a request), but its held-out set is a
different number range from the same generator, so a run would test the loop and nothing about
cards. QGrid would differ more in kind, but is not built and its cost is unknown. Neither meets
precondition 3. Neither runs now.

### 7.7 Boundary

Scripted adopters react to a card's id and enforcer, not to its text. Every claim about wording
needs a real model.

## 8. Order

**Now: nothing is built.** EP-1's gates come first (G1b re-gate, batch driver, analysis entry
point, freeze, the owner's "confirm", canary, EP-1). Then EP-1 is **reported**. Nothing below
starts before that, and each row is a new owner ask.

| Step | What | Files and size | Tests | Gates | Cost | Decision it changes |
|---|---|---|---|---|---|---|
| 0 | EP-1, run and reported | As planned | As planned | As planned | Sub-cap USD 5, expected about 0.3 | Whether card A helps; whether anything below is worth doing |
| 1 | **First step after EP-1, if the family returns: a frozen tiny QGrid export** (the sealed verdict table) | `lab/qgrid_table.py`, about 80 lines, run once; output: one hashed table | QGrid's own tests with real Lean, the axiom audit, the zero-score canaries of section 5; table hash stable over two builds | **Owner approves installs** in a separate environment: `pandapower`, elan with Lean 4.35.0. Contributors' consent | **USD 0 API.** Sizes, ARM64 support and build time unverified | Whether QGrid can be a family at all, and its random floor |
| 2 | QGrid observational note (optional) | A one-off script in `lab/`, about 60 lines; output is a table of counts | Counts reproduce on a second run | Owner's go-ahead for the public read | USD 0 | Which practice to test first |
| 3 | QGrid family, practice E, 3 arms, on the frozen export | `lab/qgrid_family.py`, about 120 lines; card, twin, predicate; prompts | Rung-0 style scripted table; a G1b-style gate; pilot | New owner ask; new caps; freeze | Unknown until prompt size is measured | Whether the EP-1 reading holds under real coupling |
| 4 | `ar1` | The existing `lab/` scaffold, unrun | Fake-server chain; A/A on scripted responders | All six preconditions of 7.0; spend review; pre-registration | At most USD 3.00 | Whether card wording is worth tuning |

A second family is a later replication, not a covariate of EP-1.

## 9. What I recommend cutting, although the owner said "implement it altogether"

- **The quantum stage, from every scored loop and every claim.** It is a classical simulation
  over a space small enough to enumerate; it can show no advantage and changes none of our
  decisions. PsiQDK is not installed.
- **The Python mirror as a scorer.**
- **The lemma-proving Lean family** from my first draft.
- **Mathlib.** QGrid does not use it.
- **Live grid data and any live link to QGrid.** A frozen export only.
- **Auto-research, for now** (deferred behind section 7.0), and on prompts or code for good.
- **Any second practice, paid tier or domain family before EP-1 is reported.**
- **A tier comparison.** Sonnet 5.5 costs twenty times Haiku; it does not fit the ceiling.
- **Practices A and B on QGrid** in the first pass. E and the poisoned note first.
- **Any causal reading of QGrid's history.**
- **Doing these together.**

## 10. Not checked

- No QGrid code or test was run. Facts in section 2 are from reading one snapshot of the files.
- ARM64 support, sizes and build times of Lean 4.35.0, `pandapower` and PsiQDK.
- The share of plans that pass, and the time to enumerate them.
- Every USD figure: arithmetic on the price sheet and G0-2R, unconfirmed until the canary.
- QGrid's full history, issues and pull requests: not read (shallow clone).
- The train and held-out detail of the skill hill-climbing reference: taken from the brief.

verified: murmuration 36bab4b (plus working tree) 2026-11-20; QGrid shallow clone read 2026-11-20
