# Pre-registration: EP-1 Practice A (claim before work) as a card against the same rule in code

**Abstract.** Comparing soft practices with structural ones in agent teams is not new: two 2026
papers already do it in real teams (section 3), and this study extends their design to one
coordination rule on a toy task. It measures, with four Haiku 5.5 agents, 20 task sets and a
matched budget, how the share of distinct passing work changes when a claim-before-work rule is
given as a card, enforced in code, or absent. It reports three raw contrasts with intervals and
no verdict; a null and "inconclusive" are allowed results. No model has been run.

Status: DRAFT. Not frozen. Nothing in this file has been run. No EP-1 episode may run until the
freeze is recorded in `docs/reports/prereg-freezes.md` (WORKPLAN-EP section 5) and the gate in
section 13 has passed. Two paid steps come before the freeze, each under its own owner approval
and sub-cap and neither producing EP-1 data: the one-call canary and the instrument pilot
(section 13). Open design choices and owner decisions: `docs/reports/ep1-design-notes.md`.

Date: 2026-11-20 (draft)      Author: Fable 5.2 (draft); number check by Opus 5.5 pending
Code git SHA (frozen):
code_tree_hash:
Config hash:
Model snapshot(s): `claude-haiku-5-5`, direct key, no alias (the price sheet's `aliases` is empty)
Seeds: task sets `alloc.gen(s, "heldout")`, s = 0 to 19; board seed = s, the same in every arm;
arm order per set from `random.Random(f"ep1:order:{s}")`; bootstrap seed 0.

Source of every number: `docs/EMERGENCE-PROGRAM.md` ("EP") sections 2.2 and 6,
`docs/WORKPLAN-EP.md` sections 1, 5, 6, 7, `docs/WORKPLAN-ALIGN.md` sections 2 and 5,
`docs/reports/price-sheet-notes.md`, `docs/reports/ep-approvals.md`, unless the line says
"design choice" (mine, with the reason in the design notes).

## Pre-freeze state (2026-11-20, read from the tree at 36bab4b plus uncommitted work)

- **Owner decisions applied.** The six recommendations were approved on 2026-11-20
  (`docs/reports/ep-approvals.md`, addendum): 3 arms x 20 task sets; a 20-point smallest effect
  with "inconclusive" a legitimate result; a Haiku-only padded canary; the key read in-process by
  the parent; the freeze commit scope; and the acknowledgement text. This draft carries them.
- **The model loop is built but not accepted.** `team_claude.py`, `prompts/ep1/` and their tests
  exist, uncommitted. Gate G1b returned **REJECT for the freeze** (`workplan-ep/G1b.md`, eight
  defects). Fixes are reported in `workplan-ep/G1b-fixes.md` and are not yet verified by a
  different reviewer. **The freeze waits for a G1b re-gate at a fixed SHA.** The round rules in
  section 6 are written to the fixed loop; if the re-gate changes them, this file changes first.
- **The re-gate G1b-R returned REJECT** (`workplan-ep/G1b-R.md`, defects R-1 to R-7; the G1b
  defects 1 to 8 held as fixed). Fixes for R-1 to R-7 are reported by the orchestrator and are
  not verified by a different reviewer. This file now states the rules those fixes implement
  ("Pre-freeze changes" below). **The freeze and the canary wait for a further re-gate at a
  fixed SHA** (commit first), then G0-2R2, which must cover `backend_claude.py` as well as
  `spend.py` (G1b-R, R-7.2).
- **Built, uncommitted, not yet gated; read by me in part** (the scoring gate, the void path and
  the stop mapping): the batch driver `src/murmuration/ep1.py` (dry-run,
  canary, pilot, run, analyse; seeded arm order, one `ep1` ledger, batch stops, an `id_tag` per
  re-run; its CLI refuses without an explicit owner-confirm flag).
- **Built, uncommitted, not yet gated:** the analysis module `src/murmuration/analysis.py` with the
  HDI margin rule in `stats.hdi` (section 11); the canary suite `tests/test_canaries.py` and the
  card check `src/murmuration/cardcheck.py` (section 13); the second scorer
  `trapbench/alloc2.py`; the Lean scorer `formal/alloc_score/` with its wrapper
  `src/murmuration/formal_alloc.py` (section 7); the two pilot-only cards under
  `practices/pilot/`. **No longer absent:** the paired t function (`stats.paired_t`) and the
  recorded non-author review of card A (`docs/reports/card-A-review.md`, section 6). The
  three-scorer result is recorded in `docs/reports/scorer-differential.md` (section 7). I read
  these in the tree; I ran nothing.
- **Spend code:** batch sub-caps and the token meter exist (`spend.BATCH_SPECS`) and were
  ACCEPTED-WITH-NOTES (`workplan-ep/G0-2R.md`). `spend.py` has changed since (the `ep1` token cap
  of 1,250,000, the `ar1` batch, the `pilot` batch); the changed file awaits re-verification
  (G0-2R2). Any change to a spend file needs a re-hash.
- **Rung 0:** ACCEPT-WITH-NOTES; the prereg may be drafted, not frozen (`workplan-ep/G1.md`). Its
  D3 finding is settled by `workplan-ep/D3-decision.md` (section 6). `rung0.py`, `team.py` and
  `adopters.py` are uncommitted.
- Lessons carried from H1 (`prereg/H1.md`): (1) H1 was drafted before its precondition was
  checked and turned out untestable; here the precondition is the built and verified backend, and
  it is checked before the freeze. (2) A look at real data before the freeze is a deviation; so
  no heldout task set and no EP-1 episode is run before the freeze, and canary data never enters
  the analysis. There is one declared look: the owner-approved instrument pilot (section 13), on
  train-range sets, whose every consequence for this file is shipped as a diff with the result
  (section 14 names the risk). (3) H1's analysis needed code that did not exist; the code this analysis
  needs is listed in section 11. (4) Untestable is not refuted: a void batch is not a null.

### Pre-freeze changes (not deviations: nothing is frozen, `code_tree_hash:` is blank)

All dated 2026-11-20, after G1b-R. Source of each: `workplan-ep/G1b-R.md` (the defect named) and
the orchestrator's decision or fix report. I ran nothing; the next re-gate checks the code
against these lines.

| # | Change | Source | Sections |
|---|---|---|---|
| 1 | Lean outcomes split: `INVALID` stops the batch (before any call, or at the first episode where it appears); `REJECTED` voids that episode, never re-run; a field disagreement with the Python scorers voids the episode and stops the batch | R-1; orchestrator decision | 7, 12, 13.18 |
| 2 | Model identity: the loop compares the canonical model key (`cell.model_key`) on every call and voids on a mismatch or a missing id, whatever the client; the real client also checks the exact returned id | R-2 | 12, 13.1 |
| 3 | Dry-run bracket: in each arm the floor must score exactly 0.25 and the oracle exactly 1.0, else void | R-3 | 6, 12, 13.6 |
| 4 | Canary: a cut-short, refused, malformed or failed reply writes `canary.json`, charges the ledger and stops with a reason | R-4 | 12, 13 |
| 5 | **Section 10 changed (intention-to-treat):** an episode in which every agent was stopped by the refusal rule is included with its scored `Y` and counted per arm (`all_agents_stopped`); no task set is dropped because of stops | R-5; orchestrator decision | 8, 10, 11, 12, 14 |
| 6 | Analysis rules stated as built: fewer than 12 valid task sets per arm reads "incomplete: not shown", HDI included; the "smaller than the 20-point smallest effect" label; "exploratory" on every secondary read-off | R-6 | 8, 10, 11 |
| 7 | Record corrections: the largest EP-1 request is 1,476 bytes, not 1,386; the fake-harness dry-run result | R-7.1; G1b-R answer (6); fix report | 6, 13, 15 |
| 8 | **Batch stop at the third all-stopped episode removed.** An episode with every agent stopped never stops the batch, however many there are; it is scored, included and counted per arm. Read in `ep1._after` and its two tests | Orchestrator ruling 1 on design notes 2e (owner-delegated) | 12 |
| 9 | An invalid log stops the batch as `stopped:invalid_log`, no longer `stopped:void_model`; the closed stop set has nine values, not eight; `void_model` keeps the model-identity voids and the malformed-reply stops; `refusal_loop` stays in the set, never written by the driver. Read in `spend.STOP_WHY`, `ep1._WHY` | Ruling 1 fix round | 12, 14 |
| 10 | Settle rule stated: `Ledger.settle` refuses while a stop is recorded on the batch, a child (the canary) or a dependency; the same rule gates `pilot` (after the canary) and `ar1` (after `ep1`). Read in `spend.settle`, `_check_batch`, `_stops_in_scope` | Ruling 1 fix round | 12, 15 |
| 11 | A valid task set is one where all three arms are non-void. Wording only: section 10 already said so and `analysis.summarise` counts that way | Orchestrator ruling 2 | 10 |
| 12 | The "smaller than the 20-point effect of interest" label applies when the upper bound of the primary interval (cluster bootstrap, 95%) is below 0.20. The kill rule (section 12, both intervals) is unchanged. **Open: `analysis.py` still uses both intervals for the label and derives the kill read-off from the same flag; a code change is needed before the freeze** | Orchestrator ruling 3 | 11 |

Changes 8 to 12 are also dated 2026-11-20 and were made after the orchestrator's rulings; I read
`ep1.py`, `spend.py` and `analysis.py` for them and ran nothing.

## 1. Hypothesis

With four Haiku 5.5 agents on the six-task allocation board, giving practice A as a card raises
the share of work slots that produce a distinct passing task by at least 20 points over an
equal-length neutral card (`Y_play - Y_none >= 0.20`).

The prediction is directional; the reading is two-sided and carries no "adopted" verdict: the
raw contrasts and their intervals are reported (section 11). The direction for a weak
tier on coordination is open (novelty-check section 6, item 4). No other hypothesis is tested.
No tier claim is made: one model, one tier.

## 2. Concept and status

Polycentric local rules: a coordination rule held by the agents as text against the same rule
imposed at the router (EP sections 2 and 5). Status: interpretation. The analogy is weak where
EP says it is: the card is handed down, and the agents have no stake.

## 3. Prior art checked

`docs/reports/align/novelty-check.md` (G0-3, Opus 5.5, 2026-11-19): *Aligning AI Teams* (arXiv
2611.17820), *AI Organizations Are More Effective but Less Aligned* (2604.10290), *Worse
Together* (2610.00583, MAMUBench) and the `magelab` README, all as excerpts.

- **EP-1 is not a replication.** It extends the intervention-comparison design of *Aligning AI
  Teams* and *Worse Together* to a coordination practice. No excerpt arm tests task claims or a
  claim lock.
- What the `code` arm adds to those designs: **no extra agent.** The claim rule is one router
  predicate (`enforce.claim_before_work`), charged inside the same call and token caps. The
  papers' lead and reviewer arms add an agent.
- **When a rejected claim reaches the agent** is fixed here (section 6), because *Worse Together*
  reports that an agent can commit before a message is in its context.
- **No model annotator.** Every score is a count from the log (`alloc.score`, `orders.compute`).
- The wording we will use (novelty-check 2.1 and 3): EP-1 is "an extension of the
  intervention-comparison design of *Aligning AI Teams* and *Worse Together* to a coordination
  practice". Possibly new, stated modestly and at excerpt level: one rule given as a card and as
  a router predicate, with an equal-length neutral card, no extra agent and one byte budget
  charged to every arm. "Not found in the excerpts we read" is not novelty. Tier sweeps and open
  team testbeds are not new and are not claimed.
- The "not a replication" reading is conditional: magelab's "structured task management" and the
  two unopened `safety-research` repos could contain a claim mechanism.
- Prior-art status: excerpt-level; papers' PDFs, figures and all four repos unopened; verified
  2026-11-19. Re-run gate: if a repo shows a claim-lock arm with a text twin, this section changes
  to "replication on coordination practices" before the freeze (WORKPLAN-ALIGN section 6).

## 4. Data

- Source: `trapbench/alloc.py`, generated by our code. Each task set has 6 tasks of the form
  `sum a b` with one integer answer. Licence: ours. Nothing is downloaded.
- **Privacy: synthetic tasks only.** Prompts hold the fixed instructions, the card or its neutral
  twin, and the board view. No tenant data, no personal data, no repository content, no file from
  outside `practices/` and the generator. **Key (owner decision 5):** the parent reads the one
  key variable in-process at launch. It is never printed, never logged, never written to disk and
  never given to a builder or a subagent. The exact read site is fixed at the G1b re-gate.
- Excluded: the canary call; every instrument-pilot record; human-baseline records; any episode
  voided under section 12; rung-0 records (they carry `instrument_validation: true` and are not
  evidence about models).
- Unit of analysis: the task set. One team episode per arm per task set.

## 5. Splits

No training happens, so the split guards against leakage only. EP-1 uses the `heldout` range
(operands 50 to 99), seeds 0 to 19. Everything before the freeze (tests, prompt examples, the
fake-server dry run B4, the instrument pilot, the human baseline) uses the `train` range
(operands 10 to 49). The two ranges are
disjoint by construction. Hash of the 20 serialised task sets (`alloc.dumps`): recorded at freeze.
Gate tests so far scanned heldout seeds 0 to 14 only; seeds 15 to 19 need the same floor, oracle
and gold-leak checks at the re-gate.

## 6. Arms and baselines

| Arm | Card in the prompt | Enforcer | Role |
|---|---|---|---|
| `none` | neutral twin of card A, same byte length | off | Baseline; what ships today |
| `play` | card A (`practices/A.md`, version 1) | off | The practice as text |
| `code` | neutral twin | on (`claim_before_work`, V1) | The practice in code |

**What 3 arms x 20 task sets x 8 calls = 480, plus 20 spare, means.** One episode is 4 agents x
2 rounds = 8 calls. Each of the 20 task sets is run once under each of the 3 arms: 60 episodes,
480 calls, 80 work slots per arm. The 500-call cap leaves 20: 1 is the canary, and the other 19
may be used only to re-run, from its first call and with the same seeds and a new `id_tag`, an
episode that an infrastructure failure aborted (HTTP 429 or 5xx after the one retry, or a
transport failure: no response, timeout, reset, cut-short body; section 12). An aborted episode
is re-run once, never twice. That allows at most 2 re-runs (16 calls); a third transport abort
in the batch stops the batch. An HTTP 400 is not an infrastructure abort: it is an instrument
bug, it stops the batch at once and is never re-run. Every HTTP attempt counts as a call, so
each retry also comes out of the 19. No episode is re-run for a behavioural reason (malformed
reply, refusal, low score). Section 12 states the same rule; if the two ever differ, section 12
governs.

**The `both` arm is dropped (owner decision 2, 2026-11-20).** It answered no confirmatory
question, and `Y_both - Y_play` was not detectable at this size (EP section 6). Dropping it buys
20 clusters at the same 480 calls and the same caps. The loop still accepts `both`; EP-1 does
not schedule it, and nothing about it is reported.

**The card must not state what the scorer checks.** If the `play` card restated the scorer's
predicate, the arm would measure instruction-following on a visible answer key, not a practice.

- **Scorer-word ban, machine-checked, before EP-1 starts.** `cardcheck.check_card`
  (`src/murmuration/cardcheck.py`, tests in `tests/test_cardcheck.py`) checks the card body
  against `cardcheck.BANNED`, the scorer's predicate words and phrases (token match, prefixes
  included; a drift test compares the list with the scorer's own vocabulary). The list is frozen
  with the card. An earlier draft of this section listed `score`, `scored`, `pass`, `correct`,
  `slot`, `point`, `grade` and `Y`. The first seven are now in `BANNED` (read in
  `cardcheck.py`).
- **`Y` is not on the ban list: a stated limit.** Matching is by token prefix, so the entry `Y`
  would hit every token that starts with "y", and card A says "you" and "your"; the list would
  ban the card. A single letter also cannot state the scorer's predicate. So the symbol `Y` is
  not machine-checked; the non-author review covers it.
- **A recorded non-author review, also required.** For a `play` card, `check_card` returns `ok`
  only when a review file exists, written by someone other than the card's author, that records
  the sha256 of the exact card bytes. Without it EP-1 does not start (`ep1._preflight` refuses).
  Cards are frozen before any score exists.
- **The review exists: APPROVE with the stated paraphrase limit** (`docs/reports/card-A-review.md`,
  2026-11-20). The reviewer is an independent Opus 5.5 model reviewer, not a person; the owner
  may override it. Card A version 1 is kept: 337 bytes on disk, body 237 bytes, whole-file
  sha256 `9875048b79b8585397b44f3c89fddae8cd733dfc318fee99be7d3912f06b3e25`. The review found
  no banned word and no answer-key leak. It was made against `alloc.py` at sha256
  `91b4d893...`; the scorer has changed since (`07ae29d8...`, `scorer-differential.md`), and the
  card bytes have not.
- **Card A says more than the code arm enforces (pre-registered reading).** V1
  (`enforce.claim_before_work`) enforces two things: no claim on a task another agent holds, and
  no work without the agent's own claim. Those are the card's sentences 1 and 3. Two sentences
  have no counterpart in code: "Claim only one at a time." and "Release your claim when the task
  is done or when you are stuck, so others can take it." So `play` against `code` compares "the
  rule plus two etiquette lines" with "the rule".
  - **They cannot move `Y`** (the review's argument, from the round rules above, not a
    measurement). Every arm already allows at most one claim per round. A release cannot hand a
    task to another agent before the single work slot in round 2.
  - **They can move two read-offs:** the false-done rate, and the board-error refusals of a
    release (a release of a claim the agent did not win). Only the `play` arm is told to
    release.
  - **Rule, fixed now.** Those two per-arm read-offs are reported with this asymmetry stated
    beside them. A difference between `play` and the other two arms on either one is read as a
    possible effect of the release sentence, not of claim-before-work, and no contrast on them
    is interpreted as a card-against-code result. The three `Y` contrasts are read as before.
  - **Version 2 was not adopted.** The review offered an optional 166-byte card that matches V1
    exactly. It was optional, not required. Adopting it would mean a new card version, a new
    review, a regenerated neutral twin and a new 237-byte figure. Release also stays part of the
    practice as the claim board uses it, and the false-done read-off needs releases. The owner
    may still choose version 2 before the freeze; that changes this section first.
- **Paraphrase is a stated limit.** A word list cannot catch a paraphrase. Card A version 1 says
  "pick a different task", which is close in meaning to the scorer's distinctness without using
  a listed word; it passes any word list. The non-author reviewer rules on it; a changed card is
  a new card version (section 14). The review lowers this risk; it does not remove it.
- **Tokens, not bytes.** Card and twin are equal in bytes, which does not make them equal in
  tokens. The card sits in one fixed slot of the prompt in every arm. Mean input tokens per arm
  are reported from `usage`; a gap between `play` and `none` above 3% of mean input tokens is
  stated in the headline as a budget mismatch.
- **Leakage controls are not EP-1 arms.** A card that states the check
  (`practices/pilot/states_the_check.md`) and a keyword-stuffed card that states no norm
  (`practices/pilot/keyword_stuffed.md`) belong to the instrument pilot (section 13): separate,
  small, and excluded from every EP-1 estimate. Both are marked pilot-only in their headers and
  must fail the word ban (`test_cardcheck.test_pilot_cards_fail_the_word_list`). EP-1 has three
  arms.

**Fixed for every arm (design choices marked):**

- Team: 4 agents `a0` to `a3`, all `claude-haiku-5-5`; 6 tasks; 4 work slots; 2 rounds.
- One stale snapshot per round: all four agents see the board as committed at the start of the
  round. Claims in one round are resolved at its end in the board's seeded order. Under every
  arm the replies of a round are executed in that order. For each task claimed in the round, the
  claimant that the board's seeded draw picks executes first. Under `code` the claim lock
  therefore refuses exactly the agents the board would resolve against.
- **Ordered round actions.** Round 1 accepts one `claim`, or `pass`. Round 2 accepts, in this
  order and each optional and at most once: one `claim`, one `work` (task, integer answer, a name
  for the result), one `release` (with a `done` flag); or `pass` alone. An agent has one work
  slot, in round 2. (Design choice.)
- The actions of a reply are sent to the router in their order. A refused action is lost and
  counts as one refusal of that agent; the later actions are still sent, and no extra call is
  bought. A `release` of the task claimed in the same reply is executed after the round's claims
  are resolved (the board accepts a release only for a committed claim).
- The naming rule `{agent}-{task}` is **not shown**; the agent picks the name. Name collisions
  are a read-off of natural herding (WORKPLAN-ALIGN 2.2).
- Reply format: one JSON array of actions in the round's order; a bare object counts as a list
  of one. Every task id must be one shown on the task list. A reply whose `stop_reason` is not
  `end_turn` is malformed. Anything else is a logged no-op and the turn is lost.
- **Refusal stop, per agent (D3 decision).** Each refused action counts once. 3 consecutive
  refusals by the same agent stop that agent for the rest of the episode; later actions from it
  are answered `agent_stopped` and are not new refusals. A counter is reset only by that agent's
  own admitted action. The episode ends only if every agent is stopped or the team reaches 20
  refusals.
  - **The 3-consecutive stop is reachable in EP-1.** A round-2 reply of `claim`, `work` and
    `release` on a task another agent holds is three refusals, and that agent stops.
  - **The 20-total stop is not reachable in EP-1.** With 4 agents and 2 rounds the team total is
    at most 15 (3 in round 1, 3 per agent in round 2: 3 + 12). So only "every agent stopped" can
    end an EP-1 episode. The 20-total clause stays in the code and is proven with 6 agents in a
    test (`test_team_claude.RefusalStopTests`), not in EP-1.
  - A herd in round 1 (three refused once each) leaves round 2 playable.
  - Enforcer refusals occur only under `code`. A board-error refusal (a `release` of a claim the
    agent did not win) can occur in any arm, at most once per agent, so it cannot stop an agent
    outside `code`.
- **A rejected claim reaches the agent in the next round, never in the same turn.** There is one
  call per agent per round, so a refusal in round 1 appears in that agent's round-2 prompt twice:
  in the board view (the claims map names the holder) and in a one-line status of its own last
  action (`accepted`, `refused: <reason>`, or `no-op`). The status line is present in every arm.
  Without enforcement the router admits a colliding claim and the loss shows only in the claims
  map. A refusal in round 2 is never seen by the agent: the slot is lost. (Design choice.)
- Under `code`, a `work` without the agent's own claim is refused. A round-1 loser can send
  `claim` then `work` in one round-2 reply; if two losers claim the same free task, the one the
  seeded draw resolves against is refused, and its `work` is then refused too
  (`work_without_claim`). Enforcement is therefore not free.
- Caps per call: **2,000 request bytes** of input, a strict upper bound on input tokens (G0-2R:
  tokens never exceeded bytes in any probe), and `max_tokens` = 300. A request over the bound is
  not sent: the episode ends as an aborted record (`prompt_too_large`, with its `abort_reason`),
  is kept, and is never re-run (a harness fault, not an infrastructure failure). A reported `usage` above 2,000 input tokens voids the episode. Prompt text is ASCII,
  asserted. **The largest EP-1 request measured is 1,476 bytes** (heldout seed 19, a two-digit
  seed id, with a random script; G1b-R R-7.1, probe of 1,920 prompts over heldout seeds 0 to 19,
  4 scripts and 3 arms). An earlier draft said 1,386 bytes; that was the maximum on seeds 0 to
  14 only. **Headroom rechecked:** 2,000 - 1,476 = 524 bytes, 26.2% of the bound, so the bound
  holds on every scheduled seed and is not changed. No tools, no cache control, no thinking
  parameter.
- Temperature 1.0, sent explicitly (design choice: at 0 the 20 task sets would be near-copies of
  one draw). `ClaudeClient.call` defaults to 0.0 and must be overridden. Whether
  `claude-haiku-5-5` accepts an explicit temperature is unchecked until the canary.
- Budget matching: every arm has the same 8 calls and the same caps; a refused action is lost and
  buys no extra call. Card and neutral twin have equal byte length (237 bytes each), not equal
  token count; native tokens are reported per arm.
- **Retries and denials are matched across arms.** The same retry rule applies in every arm; a
  retry repeats a failed transport attempt and never gives an agent a second try at a reply. A
  denial (a router refusal) buys no extra call in any arm. Retries, denials and agents stopped
  are reported per arm; `none` and `play` have no enforcer denials by construction, only
  board-error refusals of a release.
- **No truncation by the harness, and truncation logged per arm.** An oversize prompt is refused,
  never cut, so a card at the tail cannot silently vanish. Every call record carries the hash of
  the card or twin bytes actually sent. Replies cut at `max_tokens` are counted per arm.
- Run order: by task set; within a set the 3 arms run in the seeded order. A cap stop then leaves
  whole sets, not whole arms. One process.
- Scripted floor (all four work task 0) and scripted oracle (four distinct tasks), sent through
  the same model-loop path with a scripted responder, bracket the batch. In each of the 3 arms
  the floor must score exactly `Y` = 0.25 and the oracle exactly `Y` = 1.0; any other value in
  any arm is an instrument void (section 12).

## 7. Primary metric (one)

`Y = distinct_passing / slots` per team episode, from `alloc.score` on the episode log: the
number of distinct tasks with an accepted, correct `work` event, over 4 slots (one per agent).
Both counts are reported. The primary quantity is the mean paired difference `Y_play - Y_none`
over task sets, in points (1 point = 0.01).

**The definition is kept, and its precondition is now checked (decided 2026-11-20, before the
freeze; design choice, reason in section 7a).** `Y` is a share of slots only when each agent has
at most one accepted work event. The Lean scorer proved that without this the bound fails
(section 7a). So every scorer checks it on every log:

- `extra_work_events`: accepted work events on a task in the set beyond the first by the same
  agent, in log order. New field.
- `valid`: true when every event is well formed (the input rule below), `extra_work_events` is
  0 and the number of accepted work events on tasks in the set is at most `slots`. New field.
- `Y` is `distinct_passing / slots` when `valid`, and null otherwise. **An invalid log is an
  instrument void (section 12). It is never capped, clipped or partly counted.**
- On every valid log all other fields are unchanged, so `Y` is in [0, 1], in quarters, exactly
  as before.

The EP-1 loop cannot produce an invalid log: round 1 accepts only `claim` or `pass`, and round 2
accepts at most one `work` (`team_claude.ROUND_ORDER`; a second is `duplicate_type`, a round-1
`work` is `type_not_allowed_in_round`). I read this in the code; the re-gate proves it with a
test. An agent that picks a different task in round 2 still does its one piece of work on that
task, so the rule does not penalise what card A asks for.

**The scorer input rule (orchestrator ruling under the owner's delegation, 2026-11-20; fail
closed).** Scorer input is the episode action log only.

- Every event is an object with a string `action`. An event without a string `action` is
  malformed. That covers an event with no `action`, an event keyed by `type`, and a board-shaped
  event such as `{"type":"release","data":{...}}`.
- An event is also malformed when it is not an object, when `agent`, `task` or `name` is present
  and neither a string nor null, or when `rejected` is present and neither a bool nor null.
- One malformed event makes the log invalid: `valid` false, `Y` null, the episode void. Nothing
  is repaired and nothing is skipped.
- A release is read from the top-level `task` and `done` only.
- **Evidence that the loop writes only this shape** (read in the code, not run): `team.py`
  appends its log entries with the key `action` (line 148: `agent`, `action`, `task`, `answer`,
  `name`, `rejected`). For practices A and C, `team._score` passes only that log to
  `alloc.score`; the board log lines are read for other practices and are never scorer input
  for A and C. So the rule rejects nothing the loop writes, and a `type`-keyed event in a
  scored log means a harness fault.
- The ruling closes the question an earlier draft left open (work events written with `type`).
  All three scorers implement it: `alloc.well_formed`, `alloc2._malformed`, and the Lean
  definition `wellFormedEvent` (`scorer-differential.md`, "Ruling applied to alloc and Lean").

**Two scoring rules settled under the owner's delegation (2026-11-20):**

1. **False-done counts only executed releases on tasks in the task set.** A refused release
   never happened. A release on an unknown task id is a logged no-op. Neither is a done release.
2. **Answers are JSON integers only.** `30.0` is not `30`, in line with the no-repair parsing
   rule of section 13.3. A work event with a non-integer answer is not passing.

**Three scorers; a disagreement voids the episode.** Every episode log is scored three times,
from the log alone:

| Scorer | What it is | State |
|---|---|---|
| `trapbench/alloc.py` | The primary Python scorer; `Y` is its number | Built; aligned to option C and the input rule; uncommitted; not gated |
| `trapbench/alloc2.py` | An independent Python scorer, written from this file and the log format, not from `alloc.py` | Built; aligned; uncommitted; not gated |
| `formal/alloc_score/` | The same scorer as Lean 4 definitions, compiled to an executable, with theorems checked by the Lean kernel and an axiom audit; called through `formal_alloc.py` | Built; aligned; uncommitted; not gated |

- **Rule.** If any two scorers differ on a shared field of an episode, that episode is void
  **and the batch stops** (section 12). It is not averaged, not adjudicated and not re-scored by
  hand.
- **The Lean scorer has three outcomes (orchestrator decision, 2026-11-20, after G1b-R R-1).**

| Lean outcome | Meaning | Consequence |
|---|---|---|
| `OK` | A verdict | Compared field by field with the Python scorers. Any difference voids the episode and stops the batch (`stopped:scorer_disagreement`) |
| `INVALID` | The scorer itself is unusable: Lean absent, toolchain not exactly `leanprover/lean4:v4.35.0`, a failed build or a failed axiom audit (the static scan refusing the sources reads the same, as before) | **Stops the batch**: before any call when the preflight finds it, otherwise at the first episode where it appears. No episode is scored by two scorers only |
| `REJECTED` | The scorer ran and rejected this episode's input | **Voids that episode.** It is never re-run. The batch continues |

- `INVALID` and `REJECTED` are never agreement. An episode without three agreeing verdicts does
  not enter the analysis. A skipped Lean test is not a pass.
- G1b-R found that the driver recorded `INVALID` or `REJECTED` and counted the episode anyway
  (R-1). The fix is reported, not verified by me; the next re-gate tests each row of the table.
- **Toolchain.** Lean 4.35.0, core only, no Mathlib, installed inside the repo at
  `data/tools/lean` (gitignored); the archive's sha256 matched the release digest
  (`docs/WORKPLAN-CURRENT.md`, phase 1b; owner approval in `ep-approvals.md`, addendum 3).
- **Differential result (instrument validation, no model).** Source for every number in this
  bullet: `docs/reports/scorer-differential.md`. I did not run the tests; the re-gate reruns
  them at the frozen SHA.
  - **Final state: 0 disagreements in each of the three pairs** (Lean vs `alloc`, `alloc` vs
    `alloc2`, Lean vs `alloc2`) on 10,000 seeded logs (`tests/test_formal_alloc.py`, `rand_case`,
    seed `formal_alloc:differential:v2`). Every shared field is compared, `valid` included, on
    the full logs with no category removed or tolerated. 2,396 of the 10,000 logs are valid.
  - **History, kept because each number was a real defect or a real open rule:**

| Stage | Pair | Disagreements |
|---|---|---|
| Before the unknown-task fix | `alloc` vs `alloc2`, 2,000 logs | 341 |
| Before option C and the two rules, 5,000 logs | Lean vs `alloc2` | 2,283 |
| | Lean vs `alloc` | 1,081 |
| After the input rule reached `alloc2` only, 10,000 logs | `alloc` vs `alloc2` | 3,903 |
| | Lean vs `alloc2` | 4,599 |
| | Lean vs `alloc` | 0 |
| After the input rule reached all three, 10,000 logs | each of the three pairs | 0 |

  - The same report gives the full suite as 669 tests OK and 1 skipped (a test that needs
    torch), for the tree at run time, while another session was editing other files.
  - Agreement on seeded logs is evidence, not proof, that the three implement one definition
    (section 14).

## 7a. Formal verification findings

Source: `formal/alloc_score/` (Lean 4.35.0, core only), read as source; I did not build it.
**Count: 66 theorems.** `scorer-differential.md` reports a clean `lake build`, 66
`#print axioms` lines and an audit that shows only the axioms `propext`, `Quot.sound` and
`Classical.choice`. My own count of `theorem` lines in the tree is also 66 (`Basic.lean` 13,
`Json.lean` 2, `Theorems.lean` 51), and `Axioms.lean` has 66 `#print axioms` lines. The count
was 52 when the finding below was made and 64 after the option C alignment. Theorem names are
as in `AllocScore/Theorems.lean`. The scorer is not gated; these are findings about our
instrument, not about any model.

| Theorem | What it says |
|---|---|
| `distinct_gt_slots_possible` | A log exists with `slots < distinct_passing`. **`distinct_passing <= slots` and `Y` in [0, 1] are false for arbitrary logs** |
| `distinct_le_slots_one_work_per_agent`, `Y_in_unit` | Both hold when each agent has at most one accepted work event |
| `distinct_le_work` | `distinct_passing` never exceeds the number of accepted work events |
| `surviving_le_distinct` | `surviving_passing <= distinct_passing`, always |
| `score_insert_unknown`, `unknown_insert_count` | An unknown-task event changes no field except `unknown_task_events` |
| `clobber_last_writer`, `clobber_at_most_one`, `clobber_passing` | Per name, the survivor is the last accepted work event in log order |
| `score_deterministic`, `score_ext_taskset`, `score_swap` | Same input, same score; adjacent events on different tasks with different names can be swapped |
| `swap_same_name_can_change`, `swap_same_task_can_change` | Counterexamples: order matters for a shared name or a shared task |
| `score_valid_iff` (`validWith_iff`) | `valid` is true exactly when no event is malformed, the agents of accepted known-task work are pairwise different, and there are at most `slots` such events |
| `distinct_le_slots_of_valid`, `Y_in_unit_of_valid`, `valid_bounds` | **On a valid log:** `surviving_passing <= distinct_passing <= slots`, the denominator is positive, and `Y` is in [0, 1] |
| `no_action_not_valid`, `malformed_not_valid` | A log that holds an event with no action, or any malformed event, is not valid |
| `distinct_gt_slots_log_not_valid`, `two_work_one_agent_not_valid` | The counterexample log, and two accepted work events by one agent, are not valid |

`score_insert_unknown` now holds for a well-formed inserted event only, because a malformed
event voids the log.

- **The counterexample.** One slot, two accepted passing work events, by `a0` on `t0` and by `a1`
  on `t1`: `distinct_passing` = 2, `slots` = 1, `Y` = 2. With EP-1's 6 tasks and 4 slots, a log
  with six passing work events would give `Y` = 6 / 4 = 1.5.
- **What it means for EP-1.** Sections 7 and 10 of earlier drafts treated `Y <= 1` as a property
  of the scorer. It is a property of the loop (one work action per agent). The scorer did not
  check it. A harness fault that admitted extra work would have raised `Y` silently.
- **Options considered.**

| Option | Verdict | Reason |
|---|---|---|
| A: `Y = distinct_passing / 6 tasks` | Rejected | With one work per agent `Y` could not exceed 4/6, the 20-point effect and the ceiling would change scale, and every rung-0 expectation (computed over 4) would need recomputing by enumeration |
| B: count at most one passing work per agent | Rejected | Equal to the kept definition on every log the loop can produce, but it needs a "which event counts" rule and it scores a broken log instead of flagging it |
| C: keep `/ 4 slots`, check the precondition, void an invalid log | **Chosen** | No number in this file changes; the bound becomes a checked fact per episode; a broken harness is a void, not a higher score |

- **MDE, ceiling and reading table: re-derived, unchanged.** On every valid log the score is the
  same function as before. So `Y` is still in quarters, the rung-0 expectations (0.7766, 0.9892,
  floor 0.25) still apply, and sections 9 to 11 stand. This rests on the rung-0 scripts giving
  each agent one work event; rung 0 is re-run after the scorer change to confirm it (not run by
  me).
- **Changes that were needed so the three scorers implement one definition.** All are reported
  done in `scorer-differential.md`, together with the input rule of section 7; the table is kept
  as the record of what changed:

| Scorer | Change |
|---|---|
| `trapbench/alloc.py` | Add `extra_work_events` and `valid`; `Y` null when not valid. Accept an answer only when it is an `int` and not a `bool` (today `30.0 == 30` passes) |
| `trapbench/alloc2.py` | The same two fields and the null `Y`. Count a done release only when it was executed and its task is in the set (today it counts refused and unknown-task releases). `compare` treats `valid` and `extra_work_events` as shared fields |
| `formal/alloc_score/` | The same two fields; a `valid_iff` theorem; `distinct_le_slots` and `Y_in_unit` restated with `valid = true` as the hypothesis; `distinct_gt_slots_possible` kept, with a theorem that its log is not valid |
| Tests | `test_alloc`, `test_alloc2`, `test_formal_alloc`: one invalid-log case each (five work events, and two by one agent), the float-answer case, the refused and unknown-task release cases; the differential tests rerun with zero tolerated categories for these |

## 8. Secondary metrics (all exploratory, each with numerator and denominator)

- **Every read-off in this section is printed with the label "exploratory"** (section 11),
  the two contrasts on the next line included.
- `Y_code - Y_none`, `Y_code - Y_play`, with intervals.
- **Episodes in which every agent was stopped** (`all_agents_stopped`), counted per arm. They
  stay in every estimate with their scored `Y` (section 10).
- `HDI = (Y_code - Y_play) / (Y_code - Y_none)` from `stats.hdi`; undefined handling in section 11.
- Mean and 10th percentile of `Y` per arm (nearest rank: the second lowest of 20 values).
- **Named read-offs:** name collisions (`name_collisions`) and `surviving_passing / slots`;
  **false-done rate** (done releases with no earlier passing work event by the same agent on that
  item / done releases; `None` when there is no done release). Only an executed release on a
  task in the task set is a done release (section 7).
- **Read with the card asymmetry (section 6).** The false-done rate and the board-error release
  refusals are reported per arm with one sentence beside them: only card A tells the agent to
  release, and the code arm has no release rule. A `play` difference on either is not a
  card-against-code result.
- **Void episodes per arm**, with the reason of each (section 12).
- Claim-collision rate (collisions / claims; `None` with no claims), executed duplicate work,
  slots lost to a refusal, re-claims in round 2, agents stopped by the per-agent refusal stop,
  work-distribution entropy.
- Malformed-reply rate, refusal rate, retries and truncated replies per arm.
- **Pairwise error correlation across agents**, per arm: for each of the 6 agent pairs, the
  correlation over the 20 task sets of "this agent's slot produced no distinct passing work";
  the mean of the 6 is reported, or "undefined" when an indicator is constant. Four copies of
  one model are expected to fail together.
- **n is always the number of task sets (20), never agent-turns or calls.**
- Cost per arm: tokens by class, USD, USD per distinct passing task.

## 9. Minimum effect of interest

20 points (EP section 6; approved by the owner on 2026-11-20, decision 3). One slot in five is
the smallest gain that would justify carrying a card to real tasks. Below it the card is not
worth a prompt line that every agent pays for on every turn.

## 10. Sample size, power and stopping rule

- n = 20 task sets, fixed. No extension after looking (SCIENCE section 5).
- **Power, stated plainly.** Minimum detectable effect at 80% power is about
  `2.8 x sd_d / sqrt(n)` (EP section 6). At n = 20 that is 0.63 `sd_d`: about 16 points if `sd_d`
  is 0.25 (an assumption), about 22 points if it is 0.35. `sd_d` is unknown until the run.
- **What a true 20-point effect would look like here.** Its point estimate lands at 20 or above
  only about half the time, at any n. So a rule of the form "resolved and at least 20 points"
  would fire at most about half the time for an effect that is exactly at the bar; that is why
  section 11 has no such verdict. The interval clears 0 in about 9 runs of 10 if `sd_d` is 0.25
  and about 7 of 10 if it is 0.35 (normal approximation with the t critical value; my
  arithmetic, not run). The interval never clears 20 for a true 20-point effect.
- 20 clusters sit at the line (roughly 20) where `stats.paired_bootstrap` warns that a plain
  percentile interval needs a correction. At the line is not past it: the interval may still be
  too narrow. Section 11 keeps the guard.
- **Ceiling.** If agents under `none` picked tasks uniformly at random, the scripted model gives
  `Y_none` = 0.7766 and `Y_code` = 0.9892 (`rung0-expected-v2.md`; instrument arithmetic, not a
  prediction about models). The largest possible gain would then be 21 points, at the edge of
  what is detectable. A 20-point effect is realistic only if the agents herd under `none` (the
  fully herded floor is 0.25).
- **No emergence gain.** EP-1 has no nominal group (no arm without the shared board), so `EG` is
  not measured and nothing here is a claim about emergence.
- **"Inconclusive" is a legitimate outcome** (owner decision 3) and is reported as such. Doubling
  n needs a new owner ask, a new named batch and a new freeze (WORKPLAN-EP section 1). It is not
  automatic.
- Stop: the first of 60 completed episodes (3 arms x 20 sets); USD 5 of recorded spend; 500
  calls; **1,250,000 tokens**; any section 12 stop. The token cap was set to 1,250,000 before the
  freeze (owner-delegated resolution, 2026-11-20) so that the schedule fits at full reservation
  with the canary inside: 480 x 2,300 + 90,300 = 1,194,300, and with all 499 non-canary calls
  used, 499 x 2,300 + 90,300 = 1,238,000. USD 5 and 500 calls are unchanged. After the freeze a
  cap is never raised to finish.
- The batch ends with one reason: `complete` (60 episodes) or `inconclusive` (complete, primary
  contrast not resolved), which settle it, or `stopped:<why>` with `<why>` from the closed set
  in section 12, which does not.
- **CHANGED before the freeze (orchestrator decision, 2026-11-20; intention-to-treat; G1b-R
  R-5).** An episode in which every agent was stopped by the refusal rule (`episode_stopped`) is
  **included** in the analysis with the `Y` scored from its log, and such episodes are counted
  per arm (`all_agents_stopped`). **No task set is ever dropped because of stops.**
  - Why: the refusal rule can stop an agent under `code` only (section 6), so dropping stopped
    episodes censors the arms unequally and would favour `code`. G1b-R's `steal` probe shows it:
    20 of 20 `code` episodes stopped with `Y` = 0.0 while `none` and `play` scored 1.0, and the
    earlier rule removed exactly those sets (instrument probe, not evidence about a model).
  - The earlier text ("a task set enters the analysis only if all its arms completed") is
    withdrawn. It disagreed with section 12, which already said such an episode "is scored from
    its log and flagged".
- **A valid task set.** An episode gives an arm a valid `Y` when it ended `complete` or
  `episode_stopped`, has a non-null `Y` and carries no void. A task set enters the analysis when
  all 3 arms have a valid `Y`, that is, all three are non-void (orchestrator ruling 2: the
  analysis is paired across arms; `analysis.summarise` builds its rows this way). A set is left out only for an instrument reason: a void episode
  (section 12), an infrastructure abort whose re-run also failed, or a batch stop before the
  set finished. Sets left out are counted with their reasons.
- **With fewer than 12 valid task sets per arm, every contrast and the HDI read "incomplete: not
  shown"** and no number is printed for them (design choice: 12 of 20).

## 11. Analysis

Entry point: `analysis.summarise` and `analysis.render` in `src/murmuration/analysis.py` (tests:
`tests/test_analysis.py`), called by the batch driver's `analyse` step. The file's sha256 is
recorded at freeze. It exists, uncommitted and not yet gated. The two gaps an earlier draft
named are closed in the tree I read: `summarise` defaults to 10,000 resamples, and the paired t
interval is built (`stats.paired_t`, called by `summarise`).

- **The analysis returns structured contrasts, not only text.** `summarise` returns, for each of
  the three contrasts, one record: `name`, `point`, `ci_boot` (the bootstrap interval), `ci_t`
  (the paired t interval) and `resolved`, which is `positive`, `negative` or `unresolved`.
  `analysis.resolve` is the one rule: `positive` or `negative` only when both intervals exclude
  0 on the same side. `render` prints from these records.
- **With one valid task set there is no paired t.** `stats.paired_t` needs at least 2 pairs;
  `summarise` then leaves `ci_t` empty and `resolve` falls back to the bootstrap alone. EP-1
  cannot reach this case: it has 20 sets, and under 12 valid sets per arm no contrast is shown
  (section 10). The fallback exists for small scripted checks and is never an EP-1 reading.
- **The 12-set floor is in the analysis code** (G1b-R R-6 found it missing; the fix is
  reported, not verified by me). With fewer than 12 valid task sets per arm, each of the three
  contrasts and the HDI print "incomplete: not shown" and no number.
- **Which episodes count.** A `Y` is used when the episode ended `complete` or
  `episode_stopped`, the `Y` is not null and the record has no void (section 10). The number of
  `all_agents_stopped` episodes is printed per arm beside the contrasts.

- Paired arms on the same task set and seeds. Resampling unit: the task set.
- Cluster bootstrap: `stats.paired_bootstrap`, 10,000 resamples, 95% percentile, seed 0.
- Few-cluster guard (design choice; chosen over building a bias-corrected interval first): the
  paired t interval on the 20 per-set differences (df = 19, t = 2.093) is reported beside the
  bootstrap interval. A contrast is "resolved" only if both intervals exclude 0 on the same
  side. The function is built (`stats.paired_t`; `test_analysis.test_defaults_and_paired_t`)
  and is gated with the module.
- **No "adopted" verdict (owner-delegated resolution, 2026-11-20).** The output leads with the
  three raw contrasts, each with its point estimate `d` and its task-block interval `lo`, `hi`
  (resampling unit: the task set), bootstrap and t side by side:

| Contrast | What it is |
|---|---|
| `Y_play - Y_none` | The card. The pre-specified primary contrast (section 1) |
| `Y_code - Y_none` | The code gain |
| `Y_code - Y_play` | What enforcement adds over the card |

- Each contrast gets one of three plain labels, and no other:

| Interval | Label |
|---|---|
| `lo` > 0, or `hi` < 0, in both intervals | **Resolved** (positive or negative), with `d` and the interval |
| otherwise | **Not resolved: inconclusive** |
| in addition, `hi` < 0.20 in the primary interval (cluster bootstrap, 95%) | "Smaller than the 20-point effect of interest" (the "<20-point smallest effect" label; a null on size, SCIENCE section 5). Orchestrator ruling 3: the bootstrap upper bound alone decides this label. **Code not yet matching:** `analysis._contrast` requires `hi` < 0.20 in both intervals, and the kill read-off (section 12) reuses that flag; the label must follow this row and the kill rule must stay on both intervals before the freeze |
| fewer than 12 valid task sets per arm | **"incomplete: not shown"**, in place of every row above; no `d`, no interval |

- No row says the card is adopted, and no row says an effect "is 20 points". Showing that an
  effect is at least 20 points would need `lo` >= 0.20, which this n cannot give for a true
  20-point effect.
- **Correction:** none. One contrast is primary; the other two are reported first with it but
  carry the label "exploratory". EP-1 is a family of one, outside the H1-H4, H6 family of SCIENCE
  section 5. No p-value is computed.
- **HDI margin rule (`stats.hdi`).** HDI is reported only when the task-block interval of
  `Y_code - Y_none` is entirely above 0 **and** its point estimate is at least 10 points (the
  10 is a design choice: half the smallest effect of interest). Otherwise the output prints
  "not interpretable", the reason code, and no number:

| Reason code | When |
|---|---|
| `code_worse_than_none` | the interval is entirely below 0 |
| `code_gain_unresolved` | the interval includes 0, or the point estimate is under 10 points |
| `no rows` | no valid task set |

- Below the 12-set floor the HDI line reads "incomplete: not shown", before the margin rule is
  applied. HDI always carries the label "exploratory".

- When the rule is met, `stats.hdi` uses the same resampling; values below 0 or above 1 are
  reported, never clipped; resamples whose denominator is within 1e-9 of zero are dropped and
  counted. Test: `test_analysis.test_margin_rule`, `test_near_zero_denominator`.
- **n is the number of task sets**, in every table and interval, never agent-turns or calls
  (`test_analysis.test_counts_task_sets_not_turns`).
- **Scripted and model results never share a table or figure, and the code checks it.**
  `analysis` raises `AnalysisRefused` for a model table when a record has
  `instrument_validation: true`, a `FAKE` label, a `scripted:` run id, an `evidence` field other
  than `model`, no run id or no returned model id. Scripted output is stamped `FAKE`. Tests:
  `test_analysis.test_refusals`, `test_scripted_never_reaches_model_table_even_relabelled`.
- **Pilot records are not EP-1 records.** They carry the `pilot` batch id and are never passed
  to the confirmatory table.
- Descriptive decision rule (not a test): if the point estimate of `Y_code - Y_none` is under 10
  points, the practice is "not needed on this task at this tier"; `Y_none` says whether the
  agents already split the work.
- **Every secondary read-off is printed with the label "exploratory":** the two secondary
  contrasts, the HDI, and every number of section 8. Only `Y_play - Y_none` is printed without
  it (G1b-R R-6 found the label missing; the fix is reported, not verified by me).

## 12. Kill, void and stop conditions

**Instrument void (no claim; fix; new freeze):**

- **the bracket:** in any arm the scripted floor scores anything other than exactly 0.25 (1/4),
  or the scripted oracle anything other than exactly 1.0 (4/4). An earlier draft said "above
  1/4"; the code accepted any floor below 1 (G1b-R R-3, mutation M12, a floor of 0.5 passing);
- a duplicate claim or an unclaimed `work` executes under `code`;
- **model identity, two checks.** (a) The loop compares the canonical model key
  (`cell.model_key`) of the returned id with the requested one on every call, with every client
  (real, fake or scripted), and voids on a mismatch or a missing id. (b) The real client also
  requires the exact returned id `claude-haiku-5-5`. Case and date variants of the same model
  (G1b-R's `CLAUDE-HAIKU-5-5`, `claude-haiku-5-5-20261101`) share the canonical key, so they
  pass (a) by design and are caught by (b). A 200 response that names no model is void under
  (a);
- `code_tree_hash` mismatch, or a sealed file (scorer, prereg, task sets) changes during the run;
- malformed replies above 10% of calls overall (more than 48 of 480) or above 15% in any arm
  (more than 24 of 160) (design choice: above this the batch measures the reply format);
- **not a void, and not a batch stop (orchestrator ruling 1, 2026-11-20):** an episode ended by
  the refusal stop (`episode_stopped`: every agent stopped), however many there are. Each is
  scored, included and counted per arm (section 10). The earlier stop at the third such
  episode is removed: such episodes occur only under `code`, so the stop would have cut the
  run short because of one arm and could leave a task block with fewer than 3 arms. Tests (read,
  not run by me): `test_ep1.test_all_stopped_episodes_never_stop_the_batch`,
  `test_heavy_refusal_in_the_code_arm_never_stops_the_batch_or_unbalances_a_block`;
- **scorer disagreement:** any two of the three scorers of section 7 differ on a shared field.
  That episode is void and the batch stops (`ep1._after`, `stopped:scorer_disagreement`);
- **Lean `INVALID`** (toolchain missing or unpinned, a build failure or an axiom-audit failure):
  the batch stops, before any call if the preflight finds it, otherwise at the first episode
  where it appears;
- **Lean `REJECTED`** (the input was rejected): that episode is void and is never re-run; the
  batch continues. Its task set has no valid `Y` in that arm and is left out, counted with its
  reason (section 10). The count of such episodes is reported;
- **an invalid log:** any scorer reports `valid` false (a malformed event, which includes any
  event without a string `action`; an agent with more than one accepted work event; or more
  accepted work events than slots; section 7). The loop cannot produce one, so one such episode
  means the harness is broken: the batch is void and stops with `stopped:invalid_log`.

**Void on an invalid log, at every level (read in the code; tests named; not run by me):**

| Level | What happens | Test |
|---|---|---|
| `team.py` (rung 0) | `Y` is `None`, `valid` false, `status` `void:invalid_log` | `test_team.test_a_second_accepted_work_event_by_one_agent_is_void_with_no_y` |
| `team_claude.py` (model loop) | The same, and `void` = `invalid_log` | `test_team_claude`, the test of the same name |
| `ep1.py` (driver) | `Y` set to `None`; the record is logged and excluded; the batch stops with `stopped:invalid_log` | `test_ep1.test_an_invalid_log_is_void_logged_excluded_and_stops_the_batch` |
| `ep1.py` before any analysis | A record marked invalid or void that still carries a numeric `Y` raises `AnalysisRefused` | `test_ep1.test_analysis_never_sees_a_numeric_y_for_an_invalid_log` |

- `analysis.summarise` uses a `Y` only when it is not null, the episode ended `complete` or
  `episode_stopped` (section 10; changed after G1b-R R-5) and the record has no `void`. A void
  is never a 0. A stopped episode's `Y` is its scored value, which may be 0.
- **Void counts per arm** are written to the batch's `final.json` (`voids`) and reported.

**The public ledger stop has a closed reason set.** A batch that does not settle is recorded
through `Ledger.stop_batch` as `stopped:<why>`. `<why>` must be one of nine values
(`spend.STOP_WHY`): `cap`, `transport`, `http400`, `void_model`, `invalid_log`,
`scorer_disagreement`, `refusal_loop`, `owner`, `crash`. Any other value is refused. Only
`complete` and `inconclusive` settle a batch (`spend.SETTLED_REASONS`); a stop never settles,
and it keeps the `pilot` and `ar1` batches refused. The driver maps each cause to one of these
(`ep1._why`), and a cause it does not know becomes `crash`. The driver never writes
`refusal_loop`: no refusal count stops the batch (ruling 1); the value stays in the set unused.

- **A stop blocks every later settle (read in `spend.py`).** `Ledger.settle` refuses while a
  stop is recorded on the batch itself, on a child batch (the canary, for `ep1`) or on a batch
  it depends on. The same rule gates opening: `pilot` opens only after the canary settled
  `complete` with no stop recorded on it, and `ar1` only after `ep1` settled with no stop on
  `ep1` or the canary.
- **Stated limit: the reason is coarse.** An invalid log now has its own value,
  `stopped:invalid_log`. `stopped:void_model` still covers a returned-model mismatch, a 200
  with no model and the malformed-reply stops. The exact cause is in the `detail` field of
  `final.json` and in the episode record, and the report gives it.

**Stop the batch at once (halt, report to the owner, raise nothing):**

- any cap in section 10; a ledger `overspent` line, or an `unbilled_unknown` line other than the
  retry case below; missing or invalid `usage`; `cache_creation_input_tokens` other than 0; recorded spend above the reserved worst
  case; the price sheet older than 3 days;
- canary failure: wrong model, missing usage, or Console cost or tokens not equal to the ledger;
  also a canary reply that is cut short, refused, malformed or failed. In each case
  `canary.json` is written, the ledger is charged, and the batch stops with a reason from the
  closed set below (G1b-R R-4: a cut-short reply used to escape with no record, no stop and
  the reserve left open);
- a returned-model mismatch or a 200 with no model, under either identity check above (the
  episode is void, never re-run, and the batch stops);
- more than 6 malformed replies in the first complete task set (24 calls) (design choice: the
  same one-in-four share as before, now over 3 arms; a broken format is caught after about
  USD 0.01, before it consumes the batch);
- **not a batch stop (ruling 1): a refusal loop.** An episode ends early when every agent was
  stopped (3 consecutive refusals each) or the team reached 20 refusals; with 4 agents and 2
  rounds the total is at most 15, so only the first can end an EP-1 episode. The episode is
  scored from its log, flagged `all_agents_stopped` and **included in the analysis with that
  `Y`** (section 10); it is not re-run. No number of such episodes stops the batch;
- any harm: a canary string in an output, a protected-file change, an action outside the lease;
- a second process on the ledger;
- **transport failures (resolved; owner-delegated defaults, 2026-11-20).** An HTTP 429 or 5xx
  after the one reserved retry, or a transport failure (timeout, reset, no response, cut-short
  body), ends the episode as `infrastructure_abort`. It does not stop the batch. The episode is
  re-run once, from its first call, with the same seeds and a new `id_tag`. The third transport
  abort in the batch stops the batch (a re-run that aborts counts as an abort), as does an
  abort with no re-run calls left. An HTTP 400 stops the batch at once and is never re-run: it
  is an instrument bug, and the same request would fail again. A lone `unbilled_unknown` line
  from a retry that then succeeded does not stop the batch; its worst case stays counted as
  spend. Section 6 says the same;
- a request over the input bound (`prompt_too_large`): kept as an aborted record with its
  reason, never re-run, and reported as a harness fault.

**Kill for the idea, on this task and tier:** `Y_play - Y_none` with `hi` < 0.20 in both
intervals. Then the card is dropped here, and if `Y_code - Y_none` is resolved positive the rule
stays in code. A result, not a failure.

## 13. Sanity checks and the gate before the freeze

**Gate status, 2026-11-20: G1b REJECT; re-gate G1b-R REJECT (R-1 to R-7); fixes reported, not
re-gated; no fixed SHA yet; spend file and `backend_claude.py` changed, not re-verified
(G0-2R2). The freeze waits for both, then the canary and the pilot.**
The re-gate is run by a different Opus at a fixed SHA, on 20 heldout sets and 3 arms. All of the
following must exist, be verified by Opus under WORKPLAN-EP section 4, and be inside the frozen
tree:

1. **Adapter** (`team_claude.py`, B2): model required with no default; the key read in-process by
   the parent at launch (section 4); proxy and base-URL variables do not change the destination;
   the `model` label taken from the responses, and only an unmodified `ClaudeClient` on the real
   host is labelled `model` (G1b-7). The loop voids a call whose canonical model key differs
   from the requested one or whose id is missing, with any client; the real client checks the
   exact id (section 12). A scripted-client test proves the loop check.
2. **Prompt format:** system text, card or neutral twin, status line, board view. Byte-identical
   across arms except the card slot. The largest request is measured: 1,476 bytes on heldout
   seeds 0 to 19 (G1b-R R-7.1; 1,386 was seeds 0 to 14 only), 524 bytes under the 2,000-byte
   bound. It is measured again at the frozen SHA. The templates' sha256, hashed from
   the bytes used, go in the config hash; they changed with the G1b fixes.
3. **Action parsing:** strict JSON; tests for prose around the JSON, two `work` actions, another
   agent's ID, a non-integer answer, an empty reply, a task id not on the board (`unknown_task`),
   a `stop_reason` other than `end_turn` (`truncated` or `declined`), and an out-of-order or
   duplicate action type. Each is a logged no-op that costs the turn. Nothing is repaired: an
   answer of `30.0` is not the integer `30`, in the parser and in all three scorers. No
   model-written text reaches another agent's prompt (G1b-2).
4. **Sealed board in a model loop:** the model sees only the view replayed from the verified log;
   actions pass only through `router.act`; one stale snapshot per round; seeded execution order;
   the status line carries the router's result. The per-agent refusal stop (D3) is proven through
   the model loop (`test_team_claude.RefusalStopTests`): a round-1 herd leaves round 2 playable;
   the 3-consecutive stop fires with 4 agents; the 20-total stop cannot fire with 4 agents (at
   most 15) and is shown with 6. `router.seal` must pass the agent list to the enforcer (D3
   limits).
5. **Caps:** `max_tokens` 300; input above 2,000 request bytes not sent; call 501 refused; USD 5,
   1,250,000 tokens and the canary's USD 0.05 as nested batch sub-caps (`spend.BATCH_SPECS`); USD 9
   per ledger file and USD 10 across the pinned directory (section 15); an absolute ledger path;
   temperature override. A re-run needs a new `id_tag`.
6. **Floor and oracle** through the model-loop path: exactly 0.25 and exactly 1.0 in each arm,
   from the log alone; any other value is void, and a test asserts the equality (G1b-R R-3).
7. **Analysis module** (`src/murmuration/analysis.py`, `tests/test_analysis.py`) and the paired t
   function, run on fake data: three raw contrasts first with task-block intervals, the HDI
   margin rule with its reason codes, n as task sets, and the refusal of scripted or `FAKE`
   records on a model table (section 11). The module and the t function are built; the
   structured contrast records (`point`, `ci_boot`, `ci_t`, `resolved`) are part of the gate.
8. **B4:** the whole schedule against the fake server at worst-case usage; every stop fires; the
   table is stamped `FAKE`.
   - **Fake-harness dry run, as reported (instrument validation only, no model, not at a fixed
     SHA):** canary complete; pilot complete; `ep1` ended `inconclusive` over 60 episodes and
     481 calls (480 plus the canary); stamp `FAKE`; verdict `GREEN`. Source: the orchestrator's
     fix report. G1b-R's own run before the fixes gave the same counts, with the pilot at 15
     episodes and 120 calls, a bracket of 0.25 and 1.0 in all 3 arms and Lean `OK` on 60 of 60
     (G1b-R, answer 6).
   - No stop fired in that dry run; the stops are shown by unit tests and probes (G1b-R). It is
     rerun at the frozen SHA.
9. Rung-0 report accepted (gate G1); full suite green; spend files re-hashed if touched.
10. Token accounting balances: per call, ledger usage equals the response `usage`; the batch
    total equals the sum.
11. **Batch driver** (`src/murmuration/ep1.py`, being built): five steps, `dry-run`, `canary`,
    `pilot`, `run`, `analyse`. Seeded arm order within a set, one `ep1` batched ledger, the batch
    stops of section 12, an `id_tag` per re-run. **Its CLI refuses every paid step without an
    explicit owner-confirm flag**; a test proves the refusal. `dry-run` uses the fake server only.
12. **The token meter with the canary inside.** The `ep1` token cap is 1,250,000 (section 10).
    `spend.BATCH_SPECS` now carries 1,250,000 and the `pilot` batch; the changed spend file is
    re-hashed and re-verified (G0-2R2) before any paid call. B4 must show the whole schedule plus 16 re-run
    calls passing at full reservation with the canary charged at its worst case
    (1,231,100 tokens; my arithmetic, not run).
13. **Gate coverage: heldout seeds 0 to 19, all 3 arms.** Floor, oracle, gold-leak scan, largest
    request and seeded-order tests. Coverage of seeds 0 to 14 only does not pass the gate.
14. **G1b re-gate ACCEPT** recorded at the SHA that is frozen.
15. **The card check** (`src/murmuration/cardcheck.py`, section 6): card A passes the scorer-word
    ban **and** a non-author review file records the card's sha256, before EP-1 starts. The
    review file exists (`docs/reports/card-A-review.md`, sha256 `9875048b...`, APPROVE with the
    stated paraphrase limit; section 6). The re-gate confirms that `check_card` returns `ok`
    with it.
16. **Instrument pilot, run and read before the freeze** (owner-approved 2026-11-20:
    `ep-approvals.md`, addendum 2, "Yes you got my approval").
    - **Caps:** USD 0.50 and 150 calls, taken from the USD 2 reserve; 345,000 tokens (150 x
      2,300). Batch `pilot` in `spend.BATCH_SPECS`, a sibling of `ep1`, not inside it. Reserved
      worst case 150 x USD 0.00055 = USD 0.0825. Haiku 5.5 only, the same per-call caps as EP-1.
    - **It opens only after the canary has completed.** `spend.py` refuses to open `pilot` until
      the `canary` batch has settled `complete`.
    - **Arms:** EP-1's three (`none`, `play`, `code`) plus two pilot-only leakage cards, both
      with the enforcer off: `practices/pilot/states_the_check.md` and
      `practices/pilot/keyword_stuffed.md`. Byte-matched to card A within
      `cardcheck.TOLERANCE_BYTES` = 20; tokens reported per arm.
    - **Schedule:** 5 arms x 3 train-range task sets x 8 calls = 120 calls, leaving 30 for
      retries and re-runs (design choice: the most whole sets that fit under 150; fixed in the
      driver before the first "confirm"). Train-range sets only; no heldout set.
    - **Traces are hand-checked:** every pilot episode's prompts, replies and log are read by a
      person or the verifying model against the scores, and the reading is recorded.
    - **Excluded from every confirmatory estimate.** With 3 sets it can show only a gross fault
      or a gross leak; it is a check on the instrument, not an estimate.
    - **Any pilot-driven change is re-gated**, and the diff of this file against its pre-pilot
      text is shipped with the EP-1 result, whether or not anything changed.
17. **Human baseline, about ten manual task sets, or its absence stated.** A person plays the
    agents' seats through the same prompts and parser on train-range sets. Zero API cost. Stamped
    `human`, never in an estimate. It shows whether the game measures coordination or plain
    inability to play it. If it has not been played by the freeze, this file says so in section
    14 and the result carries the same sentence.
18. **Three scorers** (section 7): `alloc`, `alloc2` and the Lean `formal/alloc_score` agree on
    the seeded differential logs with no tolerated category; the two rules of section 7, the
    input rule and the `valid` check are in all three; the Lean axiom audit shows only the
    standard axioms; a missing or unpinned Lean reads `INVALID` (`tests/test_formal_alloc.py`,
    `Invalid`). In the driver, `INVALID` stops the batch and `REJECTED` voids the episode
    (section 7), each with a test; the driver tests run with an `OK` Lean result, not an
    `INVALID` stub (G1b-R R-1). Reported met in `scorer-differential.md` (0 disagreements in each pair on
    10,000 logs; 66 theorems); the re-gate reruns it at the frozen SHA.
19. **Canary suite** (`tests/test_canaries.py`): deliberately bad inputs that must score zero or
    be refused by the real code paths, plus 3 must-pass controls so the suite cannot go green by
    refusing everything. The table in the tree I read has 18 bad-input rows and 3 controls (the
    work plan said 17; the count is fixed at the re-gate). No model, no key, loopback only.

**The canary call (owner decision 4).** Not the canary suite of item 19: this is the one paid
price check. After the dry run and the first "confirm", before the pilot and before the freeze:
one Haiku 5.5 call, no Sonnet call. It is padded to at most 90,000 request bytes so that a tenfold price error shows in
the Console. This is a named, canary-only exception to the 2,000-byte per-call cap
(`canary_input_tokens_max` = 90,000 in `BATCH_SPECS`); no other call may use it. Worst case about
USD 0.018 (90,000 x USD 0.20 per million, the price the code reserves at), under its USD 0.05
sub-cap, and counted inside EP-1's USD 5, 500 calls and 1,250,000 tokens. 90,000 bytes stays under
the sheet's 100,000-token long-context threshold. The sheet's Haiku 5.5 input price, USD 0.10 per
million, is ten times below Haiku 4.5; the Console cost and token counts must equal the ledger
line, or the program stops. A canary reply that is cut short, refused, malformed or failed also
stops the program: `canary.json` is written, the ledger is charged and the stop carries a reason
(section 12; a test is required before the canary, G1b-R R-4). Canary data never enters the
analysis. The price sheet (fetched
2026-11-19, refused after 2026-11-22) is refetched if it is older than 3 days at canary time.
The canary sub-cap is one call. If a later change touches `spend.py` or `backend_claude.py`, the
canary no longer covers the changed code; a second canary is an owner decision, not a re-run.

**The "confirm" step, twice.** (1) After the dry run on the fake server and immediately before
the canary, the parent shows the owner the exact numbers (USD 10 ceiling resting on our ledger
only, USD 5 and 500 calls for EP-1, USD 0.05 and one call for the canary, USD 0.50 and 150 calls
for the pilot, the model ID) and waits for the one word "confirm". It covers the canary and the
pilot. (2) After the freeze and `prereg-check`, immediately before EP-1, the parent shows the
frozen hashes and the same caps and waits for "confirm" again. Each word is recorded verbatim in
`ep-approvals.md`. Without it, no paid call; the driver's CLI refuses without the owner-confirm
flag.

**Order before EP-1.** Model-loop re-gate (G1b re-gate) and spend re-verification (G0-2R2); dry
run on the fake server; owner "confirm"; canary (Console cost equals the ledger); pilot; any
pilot-driven fix, with re-gate and prereg diff; human baseline, or its absence stated; commit;
`code_tree_hash`; `prereg-check`; owner "confirm"; EP-1. The steps are in the design notes,
section 4.

## 14. Known threats to validity

- A toy game with two-digit sums. It says nothing about real coding work.
- One model, one tier, one family, one prompt wording. No tier claim, no claim about diversity.
- The common prompt describes the `claim` action in every arm, so `none` is "board and claim
  tool, no norm", not "no coordination". This can raise `Y_none`.
- Enforcement feedback (the `refused` status) is part of the `code` treatment, not separable. The
  status shows the router reason with the predicate prefix (`refused: A:duplicate_claim:<item>`),
  which leaks the label "A", not the answer.
- A release sent with its claim is executed after the round resolves. This is a harness
  convenience that a real board would not give.
- The per-agent refusal stop can silence an agent under `code` only. It is reported per arm.
  An episode with every agent stopped keeps its scored `Y` in the analysis (section 10), so the
  stop can lower `Y_code` but cannot remove a `code` episode.
- Equal bytes are not equal tokens; the neutral twin is filler words, not prose.
- The ban list stops listed words, not paraphrase. Card A's "pick a different task" is near the
  scorer's distinctness; a non-author review lowers the risk and does not remove it. How much of
  any card effect is answer-key leakage is the instrument pilot's question; with 3 task sets the
  pilot can show only a gross leak.
- The card reviewer is a model (Opus 5.5), independent of the card's author; it is not a human
  review, and the owner may override it.
- Card A has two sentences with no counterpart in the code arm (one claim at a time; release).
  They cannot move `Y` but can move the false-done rate and the release refusals; those two
  read-offs are read with that asymmetry (section 6).
- The symbol `Y` is not on the ban list, because prefix matching would ban "you" (section 6).
- The scorers reject any event without a string `action`. That the loop writes only such events
  is read from the code and covered by tests, not proven.
- A ledger stop reason is one of nine coarse values; `void_model` covers the model-identity
  voids and the malformed-reply stops, and the exact cause is in the batch's `detail`
  (section 12).
- **The pilot is a look at real model behaviour before the freeze**, on EP-1's own three arms.
  It uses train-range sets and is excluded from every estimate, but it can still steer choices
  made in this file. The guard is disclosure: every change after the pilot is re-gated and the
  prereg diff is shipped with the result.
- `Y <= 1` rests on the loop admitting one work action per agent, checked per episode by the
  `valid` field, not on the scorer's arithmetic (section 7a).
- The Lean scorer proves properties of its own definitions. That those definitions match the
  Python scorers is shown by differential tests on seeded logs, not by proof.
- No human baseline exists yet; without it a low `Y` may be inability, not poor coordination.
- A stale snapshot per round is not concurrency. Agents are called in sequence.
- Enforcement removes executed duplicates by construction; arms are compared on `Y` and cost.
- 20 clusters, discrete outcomes in quarters, a percentile interval that may be too narrow.
- No `both` arm: nothing is learned about a card on top of enforcement.
- Temperature 1.0: one draw per cell; run-to-run spread within a task set is not measured.
- Same-model agents fail together; rho is reported, not tested.
- Prior art was read as excerpts only (section 3).

## 15. Budget and cost accounting

- **How the USD 10 is shared (owner-delegated resolution, 2026-11-20).** EP-1 sub-cap USD 5
  (expected to settle near USD 0.3). Auto-research batch `ar1`: USD 3.00; it cannot open until
  EP-1 has settled with a stop reason of `complete` or `inconclusive` and no stop is recorded on
  EP-1 or its canary (section 12), and it is now deferred
  behind further preconditions (`docs/LEAN-AUTORESEARCH-PROPOSAL.md`). USD 2 was left as an
  unallocated reserve, untouched without a new owner ask. **Instrument pilot: USD 0.50 and 150
  calls, taken from that reserve with the owner's approval** (`ep-approvals.md`, addendum 2); USD 1.50 stays
  unallocated. The sum is 5 + 3 + 0.50 + 1.50 = USD 10.
- Caps: EP-1 stops at USD 5 or 500 calls or 1,250,000 tokens. **USD 9.00 is the default ceiling of
  one ledger file. USD 10 is the hard cap across every `*.jsonl` in the pinned ledger directory**
  (`spend.HARD_CAP_USD`); no argument raises it. Owner ceiling USD 10 (`ep-approvals.md`,
  item 1). GPU-hours: 0. (An earlier draft said "USD 9.00 absolute across all ledgers"; that was
  wrong.)
- The per-call input bound is in request bytes, and the bound is valid: tokens never exceeded
  bytes in G0-2R's probes. The largest EP-1 request is 1,476 bytes (G1b-R R-7.1), 524 bytes
  under the 2,000-byte bound; the bound and every reservation below are unchanged.
- **Reserved worst case:** 500 x (2,000 x 0.20 + 300 x 0.50) / 1,000,000 = USD 0.275. The code
  reserves input at USD 0.20 per million, twice the sheet's 0.10. (An earlier draft said
  USD 0.18, at 0.10.) Realistic spend from the 1,476-byte maximum, at the sheet's prices and
  with tokens at most bytes: 480 x (1,476 x 0.10 + 300 x 0.50) / 1,000,000 = at most USD 0.143
  for 480 calls (USD 0.139 with the earlier 1,386; my arithmetic), likely about USD 0.04
  (G0-2R). Canary worst case: about USD 0.018, inside the same caps.
- If the true prices were ten times the sheet's, 500 calls would bill at most USD 1.75, under the
  USD 5 cap, and the canary would stop the program first.
- **The ceiling is soft.** A direct API key has no provider-enforced spend cap; the USD 10
  ceiling rests only on our own ledger. The owner approved this acknowledgement on 2026-11-20
  and restates it with the one word "confirm" immediately before the canary (section 13). A
  Console workspace spend limit of USD 10 or less is strongly recommended and is an **owner
  action, pending**; the parent does not set it.
- Approval gate: `docs/reports/ep-approvals.md`. Still open: the G1b re-gate; the spend
  re-verification (G0-2R2); the gate of the batch driver, the analysis module and the three
  scorers (all built, none gated); both "confirm" words; the canary; the pilot; this freeze; a price sheet
  within 3 days; the Console limit (owner).
- **Freeze commit scope (owner decision 6):** the local freeze commit may include verified but
  uncommitted files. `train/` is excluded from the tree hash. Local only; no push.
- **What the tree hash covers.** `src/`, `practices/` (with `practices/pilot/`), `tests/`, and
  the sources of the Lean scorer under `formal/alloc_score/`: its `.lean` files,
  `lakefile.toml`, `lake-manifest.json` and `lean-toolchain`. The build directory
  `formal/alloc_score/.lake/` is not hashed. The Lean toolchain itself sits under `data/tools/`
  (gitignored) and is pinned by version, not by this hash. `lab/` is outside the hash.
  `code_tree_hash:` at the top stays blank until the freeze commit.
- **Later work stays outside the hash.** Auto-research code and any new task-family code live
  under `lab/`, outside the hashed paths, so building them cannot invalidate the EP-1 freeze.
  Auto-research edits a *copy* of a card in a scratch area, never a file under `practices/`. Any
  change inside the hashed paths between the freeze and the end of EP-1 is a `code_tree_hash`
  mismatch and a void.
- Reported per arm and in total: tokens by class (input, output, cache read, cache write; the
  last two must be 0); USD from the ledger (usage x sheet), retried attempts included; USD per
  distinct passing task with both counts.
- Energy (J): not reported for hosted calls. Provider-side energy is unknown, not zero.
- Build and verification tokens run on a subscription: USD unknown, not zero.

## 16. What would change our mind

- For the card: `Y_play - Y_none` resolved positive in both intervals. How large it is stays an
  estimate with an interval, not a verdict.
- Against the card on this task and tier: `hi` < 0.20 while `Y_code - Y_none` is resolved.
- Against the practice mattering at all here: `Y_none` within 10 points of `Y_code`.
- Against the instrument: any void in section 12. A void changes our mind about the harness, not
  about the practice.
- One batch on one tier does not license a general claim. A second tier, a real task, or another
  group's run that misses the bar would overturn a positive reading.

## 17. Deviations (filled in afterwards, never deleted)
