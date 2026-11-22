# EP-1 design notes (companion to `prereg/EP1.md`)

2026-11-20, revised the same day after the owner's approval. Author: Fable 5.2 (planner). Draft
only; nothing run, nothing frozen, `code_tree_hash:` blank. Read from the tree at 36bab4b plus
uncommitted work. I did not run the test suite or any code, and I did not read `.env*`.

**Gate status.** G1b (the model loop) returned REJECT for the freeze (`workplan-ep/G1b.md`).
Fixes are reported in `workplan-ep/G1b-fixes.md` and are not yet verified by a different
reviewer. The freeze waits for a G1b re-gate at a fixed SHA and for the spend re-verification
(G0-2R2). The canary call and the instrument pilot now run before the freeze (section 4).

**Third revision, 2026-11-20.** Added: the three-scorer rule and the primary-outcome decision
(1b), the resolved transport rules, the analysis module, the canary suite, the card check, the
approved pilot, the batch driver, and the new freeze order.

**Fourth revision, 2026-11-20.** Added section 2d: the card A limit, the scorer input rule, the
three-scorer result, void-on-invalid, the closed stop reasons, the structured contrasts, the
`Y` ban-list limit and the hash scope. Sections 1b, 1c, 1d and 4 are corrected to match. Still
nothing run by me: every count is from the named report or from reading the source.

**Fifth revision, 2026-11-20.** The re-gate G1b-R returned REJECT (`workplan-ep/G1b-R.md`, R-1 to
R-7). Added section 2e: the pre-freeze changes that answer it. Rows 18, 22, 24 and 26 of
section 1 and the corrections in section 3 are updated to match. The freeze and the canary now
wait for a further re-gate at a fixed SHA. Nothing is frozen, so these are pre-freeze changes,
not deviations.

## 1. Design choices, and why

| # | Choice | Why | Cheapest alternative |
|---|---|---|---|
| 1 | One primary contrast, `Y_play - Y_none`; the three raw contrasts are reported first, the other two labelled exploratory | The brief allows no hypothesis beyond practice A. No Holm and no p-value code | Add a second primary: then Holm over two and a bootstrap p-value must be built |
| 2 | Directional hypothesis, two-sided reading | The template wants a direction; the novelty check says the direction for a weak tier is open | None |
| 3 | **No "adopted" verdict.** Each contrast is "resolved" (both intervals exclude 0) or "not resolved: inconclusive", plus "smaller than 20 points" when `hi` < 0.20. HDI is interpreted only when the code gain is resolved | Owner-delegated resolution. A "resolved and at least 20" rule fires at most about half the time for a true 20-point effect | The old four-row verdict table |
| 4 | Percentile bootstrap kept, with a paired t interval (df 19, t 2.093) as a guard; disagreement reads "inconclusive" | 20 clusters are at the bootstrap's warning line, not past it. A t interval is one small function | Drop the guard: saves one function, loses the check |
| 5 | Held-out range, seeds 0 to 19, for EP-1; train range for everything before the freeze | Keeps examples and rehearsal numbers out of the paid task sets | Train range for both: weaker leakage guard |
| 6 | One work slot per agent, in round 2; round 1 is `claim` or `pass` | Matches EP ("claim and name; then act") and keeps `Y` at 4 slots | Allow work in round 1: then a slot definition is needed |
| 7 | **Ordered round actions:** a round-2 reply is a list of up to three actions, `claim` then `work` then `release`, each at most once, or `pass` alone | G1b-1: with one action per reply, card A's own instructions could not be carried out, which biased `Y_play - Y_none` toward the null and capped `Y_code` at the round-1 winners | One action per reply: then `release`, the false-done read-off and card A version 1 all have to go |
| 8 | A refused action is lost; later actions of the reply are still sent; no extra call | Keeps 8 calls per episode in every arm | End the turn at the first refusal: fewer refusals counted, same `Y` |
| 9 | A `release` sent with its claim runs after the round resolves | The board accepts a release only for a committed claim; without this, card-A holders would collect refusals that neutral-twin agents do not | Refuse it: an arm-specific penalty for following the card |
| 10 | Seeded execution order: the claimant the board's draw picks goes first, in every arm | G1b-6: under `code` the winner was always `a0`; the prereg's "seeded order" was false | Fixed call order with honest wording: position confounds per-agent read-offs |
| 11 | **Refusal stop per agent** (D3): 3 consecutive refusals stop that agent; the episode ends only when every agent is stopped or the team reaches 20 | A team-wide counter stopped a herding `code` episode at `Y = 0`. That would bias one arm by the stop rule | Team-wide stop: rejected in `workplan-ep/D3-decision.md` |
| 12 | A rejected claim reaches the agent in the next round's prompt, never in the same turn | One call per agent per round. The novelty check asked for this to be fixed in advance | Same-turn retry: breaks the 8-call match |
| 13 | The status line is in every arm | Same prompt shape; only the content differs under enforcement | Status only under `code`: a prompt-shape confound |
| 14 | Naming rule not shown | Name collisions are a read-off of natural herding (WORKPLAN-ALIGN 2.2) | Show the rule: then it measures instruction following |
| 15 | Task ids must be on the board; a `stop_reason` other than `end_turn` is malformed | G1b-2 and G1b-5: invented ids crashed the episode and opened a 32-character channel between agents; truncated and declined replies were scored as play | None |
| 16 | Temperature 1.0, explicit | At 0, 20 near-identical sets give one draw repeated. The client default is 0.0 | Temperature 0: a deterministic probe, not a sample |
| 17 | Run order by task set, seeded arm order inside a set | A cap stop leaves complete paired sets | By arm: a stop could leave an arm missing |
| 18 | A set counts when all 3 arms have a valid `Y`; an episode with every agent stopped is valid and keeps its scored `Y` (2e, item 5); under 12 valid sets per arm, "incomplete: not shown", HDI included | 12 keeps the detectable effect near 20 points at `sd_d` 0.25. Dropping stopped episodes would censor `code` only | No floor: a 5-set table would invite reading |
| 19 | The 20 spare calls: 1 canary, 19 for at most 2 infrastructure re-runs (each with a new `id_tag`), never behavioural | An episode is 8 calls; retries also count | Zero re-runs: one timeout costs a set |
| 20 | Malformed thresholds: void above 10% overall (48 of 480) or 15% in an arm (24 of 160); stop above 6 of the first 24 | Above it the batch measures the reply format. The first-set share (one in four) is unchanged from the 4-arm draft | One overall threshold only |
| 21 | WITHDRAWN (ruling 1 on 2e): no number of all-stopped episodes stops the batch. Was: the third episode ended by the refusal stop stops the batch | With 4 agents the team total is at most 15, so only "every agent stopped" can end an episode | Stop on the first |
| 22 | A returned-model mismatch, or a 200 naming no model, voids the episode and stops the batch. Two checks: the loop on the canonical model key with any client, the real client on the exact id (2e, item 2) | G1b-5: a nameless 200 was quietly re-runnable. G1b-R R-2: the loop itself passed a wrong id from a scripted client | Void and continue |
| 23 | 10th percentile reported beside the mean (second lowest of 20) | Novelty-check section 6 item 6 | Mean only |
| 24 | Per-call input cap stated as 2,000 request **bytes** | G0-2R: tokens never exceeded bytes; no tokenizer needed. Largest EP-1 request 1,476 bytes (G1b-R R-7.1; 1,386 was seeds 0 to 14 only), 524 under the bound | A bytes-per-token factor: not justified without the tokenizer |
| 25 | **Primary outcome kept as `distinct_passing / 4 slots`; its precondition (one accepted work event per agent) is checked by every scorer; an invalid log is void** | Lean proved the bound false for arbitrary logs (1b). The loop already admits one work per agent, so no number changes | `/ 6 tasks`, or count one work per agent: see 1b |
| 26 | Three scorers (`alloc`, `alloc2`, Lean `formal/alloc_score`); any disagreement voids the episode and stops the batch; Lean `INVALID` (missing, unpinned, build or axiom-audit failure) stops the batch; Lean `REJECTED` voids the episode, never re-run (2e, item 1) | One scorer was a single point of failure. A missing prover must not read as a pass | Two Python scorers only: no kernel-checked properties |
| 27 | HDI margin: the `Y_code - Y_none` interval entirely above 0 and the point estimate at least 10 points; otherwise "not interpretable" with a reason code | A ratio with a denominator near 0 is noise. 10 is half the smallest effect of interest | Report HDI always: unreadable when the code gain is small |
| 28 | Pilot schedule: 5 arms x 3 train-range sets x 8 calls = 120 of the 150 calls | The most whole sets that fit, with 30 calls for retries and re-runs | 3 arms x 5 sets: no room for EP-1's own arms beside the leakage cards |
| 29 | An oversized prompt is an aborted record with its reason, never re-run | G1b-2: it used to crash and lose the record. It is a harness fault, not a transport failure | Raise: the record is lost |
| 30 | Two owner "confirm" words: before the canary (covers the canary and the pilot) and before EP-1 | The pilot now sits between the canary and the freeze; the frozen hashes exist only at the second | One word: it would approve EP-1 before its hashes exist |

## 1b. The primary outcome after the Lean finding (decided 2026-11-20)

**The finding.** `formal/alloc_score` proves `distinct_gt_slots_possible`: a log exists with
`slots < distinct_passing`. Its counterexample has one slot and two passing work events (`a0` on
`t0`, `a1` on `t1`), so `Y` = 2. `distinct_le_slots_one_work_per_agent` and `Y_in_unit` hold only
with at most one accepted work event per agent. With 6 tasks and 4 slots, six passing work
events would give `Y` = 1.5.

**Can EP-1 reach that?** Not through the loop as I read it. `team_claude.ROUND_ORDER` lets round
1 send only `claim`, and round 2 at most one `work`. So an agent has one work action per
episode, and a team at most four. The parent's note says an agent "can claim, work and release
in round 2 as well"; that is one work, in round 2, not a second one. I read the parser and did
not run it. The re-gate must show, with a test, that a round-1 `work` and a second `work` are
both refused.

**Decision: option C.** Keep `Y = distinct_passing / 4 slots`. Make the precondition a checked
field. A log that breaks it is an instrument void.

| Option | Verdict | Reason |
|---|---|---|
| A: divide by 6 tasks | Rejected | `Y` could not pass 4/6 with one work per agent; the 20-point effect, the ceiling and the rung-0 expectations would all need recomputing by enumeration |
| B: count one passing work per agent | Rejected | Same number as C on every log the loop can make; needs a "which event counts" rule; scores a broken log instead of flagging it |
| C: keep `/ 4`, check, void | Chosen | Nothing in the prereg's arithmetic changes; a harness fault becomes a void, not a higher score |

**Does it penalise "pick a different task"?** No. An agent that loses round 1 and claims another
task in round 2 does its one piece of work there, and it counts.

**MDE and reading table.** Unchanged: on every valid log the score is the same function. This
assumes the rung-0 scripts give each agent one work event. Rung 0 is re-run after the scorer
change; I did not run it.

**New fields, same in all three scorers.** `extra_work_events` (accepted work on a task in the
set beyond the first by the same agent, in log order); `valid` (`extra_work_events` is 0 and
accepted known-task work events are at most `slots`); `Y` is null when not `valid`.

**Two rules settled by the parent under the owner's delegation.**

1. False-done counts only executed releases on tasks in the task set. A refused release never
   happened; an unknown-task release is a logged no-op.
2. Answers are JSON integers only. `30.0` is not `30`.

**Exact changes needed.**

| File | Change |
|---|---|
| `src/murmuration/trapbench/alloc.py` | Add `extra_work_events`, `valid`; `Y` null when not valid. A passing answer must be an `int` and not a `bool` (today `e.get("answer") == expect[...]` accepts `30.0`) |
| `src/murmuration/trapbench/alloc2.py` | The same fields and null `Y`. Count a done release only if executed and on a task in the set (today it counts refused and unknown-task releases). `compare` covers the new fields |
| `formal/alloc_score/` | The same fields; `valid_iff`; `distinct_le_slots` and `Y_in_unit` with `valid = true` as the hypothesis; `distinct_gt_slots_possible` kept, plus a theorem that its log is not valid |
| `tests/test_alloc.py`, `test_alloc2.py`, `test_formal_alloc.py` | Invalid-log cases (five work events; two by one agent), the float answer, refused and unknown-task releases. Differential tests with no tolerated category for these |
| `src/murmuration/analysis.py`, the driver | Treat `valid` false or a null `Y` as a void, never as 0 |

**Closed after this decision (2d, item 2).** `alloc2` used to read work events written with
`type`; `alloc` ignored them. The orchestrator ruled: scorer input is the episode action log
only, and an event without a string `action` is malformed. All three scorers now implement it.

## 1c. The three scorers: what is and is not shown

- **Shown, on seeded logs** (`docs/reports/scorer-differential.md`; I did not run the tests):
  `alloc`, `alloc2` and the Lean scorer agree on 10,000 seeded logs on every shared field and
  on `valid`: 0 disagreements in each of the three pairs, with no category tolerated. The
  history is in 2d, item 3.
- Lean: 66 theorems. The report gives 66 `#print axioms` lines after a clean build; I count 66
  `theorem` lines in the tree (`Basic.lean` 13, `Json.lean` 2, `Theorems.lean` 51). It was 52 at
  the time of the finding in 1b and 64 after the option C alignment. Axioms `propext`,
  `Quot.sound`, `Classical.choice` only, as reported. Lean 4.35.0, core only, at
  `data/tools/lean`; archive sha256
  matched the release digest (`docs/WORKPLAN-CURRENT.md`, phase 1b; `ep-approvals.md`,
  addendum 3). `formal_alloc` returns `INVALID` for a missing Lean, a toolchain other than
  `leanprover/lean4:v4.35.0`, a refused static scan or a failed build.
- Not shown: that the Lean definitions equal the Python scorers. Differential tests on seeded
  logs support it; they do not prove it.

## 1d. Canary suite, card check, analysis module, driver

| Item | File | State as read |
|---|---|---|
| Canary suite | `tests/test_canaries.py` | 18 bad-input rows that must score zero or be refused, 3 must-pass controls. The brief said 17: the table has 18 `refuse` rows; fix the stated count at the re-gate |
| Card check | `src/murmuration/cardcheck.py`, `tests/test_cardcheck.py` | Word ban on the card body (`BANNED`), plus a non-author review file recording the card's sha256. The review file now exists (2d, item 1). Paraphrase stays a stated limit |
| Ban list | `cardcheck.BANNED` | `score`, `scored`, `pass`, `correct`, `slot`, `point`, `grade` are now listed. `Y` is not, on purpose (2d, item 6) |
| Analysis | `src/murmuration/analysis.py`, `stats.hdi`, `stats.paired_t`, `tests/test_analysis.py` | Three raw contrasts first, as structured records (2d, item 5); HDI margin rule with reason codes `code_worse_than_none`, `code_gain_unresolved`, `no rows`; n = task sets; refuses scripted or `FAKE` records on a model table. Both earlier gaps are closed: the default is 10,000 resamples and the paired t function exists |
| Batch driver | `src/murmuration/ep1.py` | Built, not gated. I read its scoring gate, void path and stop mapping, not the whole file. Steps `dry-run`, `canary`, `pilot`, `run`, `analyse`; the CLI refuses without an explicit owner-confirm flag |
| Pilot cards | `practices/pilot/states_the_check.md`, `keyword_stuffed.md` | Marked pilot-only; must fail the word ban; inside the hashed `practices/` |

## 2. Owner decisions: recorded 2026-11-20

Source: `docs/reports/ep-approvals.md`, addendum. Owner's words: "Go ahead with all your
recommendations I approve them."

| # | Decision | Where it lands in the prereg |
|---|---|---|
| 1 | Acknowledgement: a direct key has no provider-enforced cap; the USD 10 ceiling rests on our ledger | Section 15 |
| 2 | 3 arms x 20 task sets; `both` dropped | Sections 5, 6, 8, 10, 11, 12 |
| 3 | Smallest effect 20 points; "inconclusive" legitimate; doubling n is a new ask | Sections 9, 10 |
| 4 | Canary: Haiku only, padded to 90,000 bytes, worst case about USD 0.018, a canary-only exception inside EP-1's caps | Section 13 |
| 5 | Key read in-process by the parent at launch; never printed or given to a builder | Section 4 |
| 6 | Freeze commit may include verified uncommitted files; `train/` excluded from the hash; local only | Section 15, freeze steps 9 and 10 |

**What 3 x 20 buys and costs.** 3 x 20 x 8 = 480 calls, plus 20 spare, the same as before. The
minimum detectable effect is `2.8 x sd_d / sqrt(20)` = 0.63 `sd_d`: about 16 points at `sd_d`
0.25 (was about 18), about 22 at 0.35. 20 clusters sit at the bootstrap's warning line. Lost:
`Y_both - Y_play`, which was not detectable anyway.

## 2b. Conflicts resolved 2026-11-20 (owner delegated: "resolve conflicts and go ahead")

| # | Resolution | Where |
|---|---|---|
| 1 | EP-1 token cap 1,250,000, so 480 calls plus the 90,300-token canary fit at full reservation (1,194,300; 1,238,000 with every spare call). USD 5 and 500 calls unchanged. `spend.BATCH_SPECS` now says 1,250,000; the changed file awaits re-verification (G0-2R2) | Prereg 10, 13.12 |
| 2 | The USD 10 is shared: EP-1 USD 5 (expected to settle near 0.3); auto-research batch `ar1` USD 3.00, opened only after EP-1 settles `complete` or `inconclusive`; USD 2 unallocated, of which USD 0.50 later went to the pilot with the owner's approval; USD 1.50 untouched without a new ask | Prereg 15 |
| 3 | No "adopted" verdict; three raw contrasts with task-block intervals first; HDI only when the code gain is resolved | Prereg 1, 10, 11, 12, 16 |
| 4 | Gate tests must cover heldout seeds 0 to 19 | Prereg 5, 13.13 |
| 5 | Transport rules, resolved: a 429, a 5xx or a transport failure is an infrastructure abort, re-run once with a new `id_tag`; the third transport abort in the batch stops the batch; an HTTP 400 stops the batch at once (an instrument bug). Sections 6 and 12 now say the same | Prereg 6, 12 |
| 6 | Auto-research and new-family code live under `lab/`, outside the hashed paths: `src/`, `practices/`, `tests/` and the `formal/alloc_score/` sources (not `.lake/`) | Prereg 15 |
| 7 | Primary outcome: option C (1b). False-done counts executed releases on known tasks only. Answers are JSON integers only | Prereg 7, 7a, 8, 12, 13.3 |

**Power, said exactly.** For a true 20-point effect the point estimate is at or above 20 only
about half the time, at any n. The interval clears 0 in about 9 runs of 10 at `sd_d` 0.25 and
about 7 of 10 at 0.35 (normal approximation; my arithmetic, not run). It never clears 20.

## 2c. Changes from the two adversarial reviews (2026-11-20)

Sources: `docs/reports/cursor-adversarial-review.md` and `docs/reports/gpt-adversarial-review.md`.
Both are advice from models that read a brief, not evidence. I read the first in full; Opus is
integrating both into the other documents.

| Change in `prereg/EP1.md` | Section |
|---|---|
| The prior-art concession is the first sentence of a new abstract | Top |
| The `play` card must not state the scorer's predicate: a frozen ban list, one test, checked by a non-author; cards frozen before any score | 6, 13.15 |
| Tokens, not bytes: fixed card slot, mean input tokens per arm, a 3% gap flagged | 6 |
| The "states the check" card and the keyword-stuffed no-norm card belong to the instrument pilot, not to EP-1's three arms | 6, 13.16 |
| No truncation by the harness; card hash per call; truncated replies per arm | 6 |
| Retries and denials matched across arms and reported per arm | 6, 8 |
| HDI not reported unless `Y_code - Y_none` is resolved positive and at least 10 points; otherwise "inconclusive" | 11 |
| n is task sets, never agent-turns; pairwise error correlation across agents | 8 |
| Scripted and model results kept apart by a check in the analysis code, with a test | 11 |
| Prerequisites: the instrument-pilot design and a human baseline of about ten manual task sets | 13.16, 13.17 |

**A finding of mine while applying the ban.** Card A version 1 passes the word list as I read it,
but it says "pick a different task". That is the scorer's distinctness in other words. A word
list cannot rule on it. The non-author checker must, before the freeze. If the sentence goes, the
card is version 2 and the neutral twin is regenerated.

**The USD 10 allocation stays as resolved** (2b row 2): EP-1 USD 5, `ar1` USD 3.00, USD 2
unallocated. `ar1` is now deferred (see the proposal); its USD 3.00 stays allocated and unopened.

**Instrument pilot: approved** (`ep-approvals.md`, addendum 2; owner's words: "Yes you got my
approval"). This replaces the earlier USD 0.25 proposal.

- Batch `pilot` in `spend.BATCH_SPECS`: **USD 0.50, 150 calls, 345,000 tokens** (150 x 2,300),
  a sibling of `ep1`. From the USD 2 reserve; USD 1.50 stays unallocated.
- Reserved worst case: 150 x USD 0.00055 = USD 0.0825.
- **Opens only after the canary completes:** `spend.py` refuses the `pilot` batch until `canary`
  has settled `complete`.
- Arms: EP-1's three plus the two pilot-only leakage cards in `practices/pilot/`, enforcer off.
  5 x 3 train-range sets x 8 calls = 120 calls (design choice 28).
- Traces hand-checked. Excluded from every confirmatory estimate. With 3 sets it can show only
  a gross fault or leak.
- **It runs before the freeze.** That makes it a look at model behaviour on EP-1's arms before
  the prereg is fixed. The guard: any pilot-driven change is re-gated, and the prereg diff
  (pre-pilot against frozen) ships with the result, also when it is empty.
- The canary sub-cap is one call. A pilot-driven change to `spend.py` or `backend_claude.py`
  leaves the canary's check stale; a second canary is an owner decision.

**Human baseline.** About ten train-range task sets played by a person through the same prompts
and parser. USD 0. Who plays, and when, is an owner decision. If it is not played before the
freeze, the prereg and the result say so.

## 2d. Rulings and results recorded in the fourth revision (2026-11-20)

Each item names its source. I ran nothing; "read" means read in the tree.

**1. Card A: approved, with a limit on two read-offs.**

- Source: `docs/reports/card-A-review.md`. Reviewer: Opus 5.5, a model, independent of the card's
  author. Verdict: APPROVE with the stated paraphrase limit. The owner may override it.
- Card version 1 is kept: 337 bytes on disk, body 237 bytes, sha256 `9875048b...` (the full
  digest is in the review and in prereg section 6).
- The limit. V1 in code enforces the card's sentences 1 and 3. "Claim only one at a time." and
  the release sentence have no counterpart in code. By the round rules they cannot move `Y`.
  They can move the false-done rate and the release refusals.
- What the prereg now fixes: those two per-arm read-offs are reported with the asymmetry stated
  beside them, and a `play` difference on them is not read as card against code (prereg 6, 8,
  14).
- Why the optional 166-byte version 2 (an exact V1 match) was not adopted: the reviewer marked
  it optional; it would need a new card version, a new review, a new neutral twin and a new
  byte figure; and without the release sentence the `play` arm would give the false-done
  read-off almost nothing to count. Cheapest alternative, still open to the owner: adopt
  version 2 before the freeze and drop the asymmetry sentence.

**2. Scorer input rule (orchestrator, owner-delegated, fail closed).**

- Scorer input is the episode action log only. An event without a string `action` is malformed
  and makes the log invalid, so the episode is void. This covers `type`-keyed events and
  board-shaped events.
- Evidence the loop never writes such an event: `team.py` line 148 appends entries keyed by
  `action`; for practices A and C `team._score` passes only that log to `alloc.score`, and the
  board log lines are not scorer input.
- Why fail closed: reading two shapes meant two readings, and that produced the disagreements
  in item 3. Rejecting the second shape costs nothing on logs the loop writes.

**3. Three scorers agree.** Source: `docs/reports/scorer-differential.md`.

| Stage | Pair | Disagreements |
|---|---|---|
| Before the unknown-task fix, 2,000 logs | `alloc` vs `alloc2` | 341 |
| Before option C and the two rules, 5,000 logs | Lean vs `alloc2` / Lean vs `alloc` | 2,283 / 1,081 |
| Input rule in `alloc2` only, 10,000 logs | `alloc` vs `alloc2` / Lean vs `alloc2` | 3,903 / 4,599 |
| Input rule in all three, 10,000 logs | each of the three pairs | 0 |

- Final: 0 disagreements in each pair on 10,000 seeded logs, every shared field and `valid`,
  nothing tolerated. 2,396 of those logs are valid.
- Lean: 66 kernel-checked theorems (1c), axioms `propext`, `Quot.sound`, `Classical.choice`
  only. They include `no_action_not_valid` and the bounds under `valid` (`valid_bounds`,
  `distinct_le_slots_of_valid`, `Y_in_unit_of_valid`).
- Still not shown: equality of the Lean definitions and the Python scorers (1c).

**4. Void on an invalid log, everywhere; a closed set of stop reasons.**

- `team.py`, `team_claude.py` and `ep1.py` all give `Y` = `None` and `status`
  `void:invalid_log` for an invalid log (read; the tests are named in prereg section 12).
- `ep1` refuses an analysis when a record marked invalid still has a numeric `Y`.
- Void counts per arm go into `final.json` (`voids`).
- `Ledger.stop_batch` accepts eight reasons only (`spend.STOP_WHY`): `cap`, `transport`,
  `http400`, `void_model`, `scorer_disagreement`, `refusal_loop`, `owner`, `crash`. Only
  `complete` and `inconclusive` settle a batch.
- Limit: an invalid log is recorded as `stopped:void_model`; the exact cause is in `detail`.
  (Superseded: the set now has nine values and an invalid log stops as `stopped:invalid_log`;
  see "Section 2e: resolved".)
- A correction this brought to prereg section 12: the driver stops the batch on a scorer
  disagreement, as well as voiding the episode.

**5. Structured contrasts.**

- `analysis.summarise` returns, per contrast, `point`, `ci_boot`, `ci_t` and `resolved`
  (`positive`, `negative` or `unresolved`). Resolved means both intervals exclude 0 on the
  same side.
- With one task set there is no paired t (`stats.paired_t` needs 2 pairs), and the rule then
  uses the bootstrap alone. EP-1 has 20 sets and shows nothing under 12, so it cannot get
  there. (G1b-R R-6 found the 12-set floor missing from the code; see 2e, item 6.)

**6. `Y` is not on the card ban list.** Matching is by token prefix, so `Y` would ban "you" and
"your", which card A uses. A single letter cannot state the scorer's predicate. Stated as a
limit in prereg sections 6 and 14. Cheapest alternative: exact-match entries in `cardcheck`,
which is a code change for no gain.

**7. Freeze hash scope, unchanged and restated.** `src/`, `practices/`, `tests/` and the
`formal/alloc_score/` sources (not `.lake/`). `lab/` is outside. `code_tree_hash:` stays blank
until the freeze commit.

## 2e. Pre-freeze changes after the re-gate G1b-R (2026-11-20)

Source of every defect and number: `docs/reports/workplan-ep/G1b-R.md` (REJECT; Opus 5.5, fresh
context; scripted responders and loopback only, so nothing here is evidence about a model).
Source of every fix: the orchestrator's fix report, which I received as a summary and did not
check against the code. Nothing is frozen and `code_tree_hash:` is blank, so each item is a
pre-freeze change to the prereg, not a deviation.

| # | Date | Defect | What the prereg now says | Decided by | Prereg sections |
|---|---|---|---|---|---|
| 1 | 2026-11-20 | R-1: Lean `INVALID` or `REJECTED` never voided an episode | `INVALID` stops the batch, before any call or at the first episode where it appears. `REJECTED` voids that episode, never re-run. Any field disagreement with the Python scorers voids and stops | Orchestrator | 7, 12, 13.18 |
| 2 | 2026-11-20 | R-2: the loop did not compare the returned model | The loop compares the canonical model key (`cell.model_key`) on every call and voids on a mismatch or a missing id, whatever the client. The real client also checks the exact id | Fix report | 12, 13.1 |
| 3 | 2026-11-20 | R-3: the floor bracket accepted any floor below 1 | Each arm must score exactly 0.25 (floor) and exactly 1.0 (oracle), else void | Fix report | 6, 12, 13.6 |
| 4 | 2026-11-20 | R-4: a cut-short canary reply escaped with no record | A cut-short, refused, malformed or failed canary reply writes `canary.json`, charges the ledger and stops with a reason | Fix report | 12, 13 |
| 5 | 2026-11-20 | R-5: a stopped episode was done for the driver, censored by the analysis | **Section 10 changed (intention-to-treat).** An episode with every agent stopped is included with its scored `Y` and counted per arm (`all_agents_stopped`). No task set is dropped because of stops | Orchestrator | 8, 10, 11, 12, 14 |
| 6 | 2026-11-20 | R-6: three analysis rules were not in the code | Under 12 valid task sets per arm: "incomplete: not shown", HDI hidden too. The "<20-point smallest effect" label when `hi` < 0.20. "exploratory" on every secondary read-off | Fix report | 8, 10, 11 |
| 7 | 2026-11-20 | R-7.1: the largest request was understated | 1,476 bytes, not 1,386. The fake-harness dry-run result is recorded | G1b-R; fix report | 6, 13.2, 13.8, 15 |

**Item 1, why the two Lean outcomes differ.** `INVALID` says the scorer cannot run at all
(G1b-R: "a missing Lean voids all 60"), so continuing would spend calls on episodes that can
never be scored three times. `REJECTED` is about one episode's input; the other episodes can
still be scored. Cheapest alternative: treat both as a batch stop, which is simpler and loses
only the rest of the batch on a single rejected input.

**Item 2, the stated gap.** Case and date variants of the same model pass the loop check by
design, because they share the canonical key; G1b-R's examples are `CLAUDE-HAIKU-5-5` and
`claude-haiku-5-5-20261101`. Only the real client catches those. A fake or scripted client
that returns a variant therefore passes; that affects instrument runs only, never a paid call.

**Item 5, why intention-to-treat.** The refusal stop can silence an agent under `code` only.
G1b-R's `steal` probe: 20 of 20 `code` episodes ended `episode_stopped` with `Y` = 0.0 while
`none` and `play` scored 1.0. Dropping those sets removes the worst `code` outcomes and would
favour `code`. Prereg section 12 already said such an episode "is scored from its log and
flagged"; section 10 said the opposite and is the one that changed. Cheapest alternative:
censor and report the count, which keeps the bias and only discloses it.

**Item 7, the headroom recheck.**

- Bound: 2,000 request bytes per call. Largest request: 1,476 bytes (heldout seed 19, a
  two-digit seed id, random script; 1,920 prompts over seeds 0 to 19, 4 scripts, 3 arms).
- Headroom: 2,000 - 1,476 = 524 bytes, 26.2% of the bound. The bound stays.
- 1,386 was the maximum on seeds 0 to 14; the difference is 90 bytes.
- Reservations use the 2,000-byte bound, so no cap or reserved worst case changes (USD 0.275
  for 500 calls stands).
- Realistic spend at the sheet's prices: 480 x (1,476 x 0.10 + 300 x 0.50) / 1,000,000 =
  USD 0.143 at most (was USD 0.139 from 1,386; my arithmetic).

**The fake-harness dry run, as reported.** Canary complete; pilot complete; `ep1` ended
`inconclusive` over 60 episodes and 481 calls (480 plus the canary); stamp `FAKE`; verdict
`GREEN`. Instrument validation only, not at a fixed SHA. G1b-R's run before the fixes gave the
same counts (answer 6: pilot 15 episodes and 120 calls, bracket 0.25 and 1.0, Lean `OK` on 60
of 60, and no stop fired because the fake responder plays the floor).

**Left for the next re-gate or the orchestrator (not settled here).**

- R-7.2: G0-2R2 must re-hash `backend_claude.py` as well as `spend.py`.
- R-7.3: the card review is pinned to `alloc.py` at `91b4d8...`; the tree has `07ae29d8...`.
  The reviewer re-confirms against the current scorer.
- M13: the driver's `unbilled_unknown` stop has no test; test it or remove it.
- RESOLVED (ruling 1, end of this file): the batch stop at the third episode with every agent
  stopped (design choice 21) is removed, in `ep1.py` and in the prereg.
- RESOLVED (ruling 2): a valid task set is one where all 3 arms are non-void;
  `analysis.summarise` counts that way.
- RESOLVED in the prereg and in the code (ruling 3): the `hi` < 0.20 label uses the bootstrap
  interval alone; the kill read-off uses `hi_below_soi_both` (read in `analysis.py` 2026-11-20,
  not run).

## 3. Still open

**Owner actions**

1. **Console workspace spend limit** of USD 10 or less. Strongly recommended, set only by the
   owner, pending. Record the value and the owner's words.
2. **The one word "confirm", twice:** after the dry run and immediately before the canary
   (covers the canary and the pilot), and again after `prereg-check`, immediately before EP-1.
   Each time after the parent shows the exact numbers. Recorded verbatim.
3. **QGrid** (the Lean and quantum question): found, read-only clone under `data/qgrid`
   (gitignored, no licence file, internal use only). See `docs/LEAN-AUTORESEARCH-PROPOSAL.md`.
   It does not block EP-1.

**Design decisions from G1b-fixes: now settled** (owner-approved defaults, 2b row 5)

- **A. Transport failures.** A 429 or 5xx after the one retry, or a transport failure (timeout,
  reset, no response, cut-short body), ends the episode as `infrastructure_abort`. It is re-run
  once with a new `id_tag`. The third transport abort in the batch, or an abort with no re-run
  calls left, stops the batch. A lone `unbilled_unknown` line from a retry that then succeeded
  does not stop the batch; its worst case stays counted.
- **B. HTTP 400.** Stops the batch at once, never re-run: an instrument bug. A request error
  (for example an explicit temperature the model refuses) repeats on every call.
- **C. Sections 6 and 12 of the prereg no longer disagree.** Section 6 used to call every
  infrastructure abort re-runnable while section 12 stopped the batch on a 429 or 5xx. Both now
  carry rule A; section 12 governs if they ever differ.
- **D. Code against these rules.** `G1b-fixes.md` says the loop marks a 400 as
  `infrastructure_abort` with `rerunnable: true` and leaves the stop to the batch driver. The
  driver must stop on a 400 and count aborts; that is part of its gate.

**Refusal stops, said plainly** (`G1b-fixes.md`, "Refusal stops")

- Each refused action counts once.
- The 3-consecutive per-agent stop is reachable in EP-1: `claim`, `work`, `release` on a task
  another agent holds.
- The 20-total stop is not reachable with 4 agents: at most 3 + 12 = 15. A test shows it with 6
  agents. An EP-1 episode can end early only when every agent is stopped.

**Corrections to earlier statements**

- "Code hard stop USD 9.00 absolute across all ledgers" was wrong. USD 9.00 is the default
  ceiling of one ledger file. USD 10 is the hard cap across the pinned directory.
- "USD 0.18 for the full cap" used the sheet's 0.10 input price. The code reserves at 0.20, so
  the reserved worst case is USD 0.275. Realistic spend is at most USD 0.143 for 480 calls
  (USD 0.139 used the 1,386-byte maximum; see 2e, item 7).
- "The largest EP-1 request is 1,386 bytes" was the maximum on seeds 0 to 14. On seeds 0 to 19
  it is 1,476 bytes (G1b-R R-7.1).
- "A task set enters the analysis only if all its arms completed" is withdrawn (2e, item 5).
- "The refusal stop fires on a round-1 herd" was true of the team-wide counter. D3 replaced it.
- "`team_claude.py` is absent" is out of date: it exists, uncommitted, and is under re-gate.

**Token cap (resolved, 2b row 1).** At the old 1,150,000 only 460 EP-1 calls fitted beside the
canary at full reservation. The cap is 1,250,000 before the freeze. `spend.BATCH_SPECS` now
carries 1,250,000 (and the `ar1` and `pilot` batches); the changed file awaits re-verification
(G0-2R2). After the freeze no cap is raised.

## 4. Freeze procedure, in order (updated 2026-11-20)

**State on 2026-11-20:** step 1 was run once as G1b-R and returned REJECT. Step 1 is repeated at
a fixed SHA (commit first) after the fixes of 2e; nothing after it has run on real calls.

Stop at the first step that fails. The order in one line: model-loop re-gate (G1b re-gate) and
spend re-verification (G0-2R2) -> dry run on the fake server -> owner "confirm" -> canary
(Console cost equals the ledger) -> pilot -> any pilot-driven fix with re-gate and prereg diff
-> human baseline (or its absence stated) -> commit -> `code_tree_hash` -> `prereg-check` ->
owner "confirm" -> EP-1.

**Before step 1 (zero cost, already under way).** Owner decisions recorded verbatim in
`ep-approvals.md` and folded into `prereg/EP1.md`. Novelty re-run gate recorded. Now in the
tree (2d): the batch driver, the paired t function, the scorer changes of 1b and the input rule
in all three scorers, the card review file. Still to confirm at the re-gate: `router.seal`
passing the agent list (D3 limits). Opus checks every number in the prereg against its source.

1. **G1b re-gate** by a different Opus at a fixed SHA, on 3 arms and heldout seeds 0 to 19:
   floor, oracle, gold-leak scan, largest request re-measured, one work per agent proven, the
   three-scorer gate, the canary suite green. Must return ACCEPT. **G0-2R2** in the same pass:
   the final `spend.py` (canary 90,000, `ep1` 1,250,000, `ar1`, `pilot`) re-hashed and
   re-verified. Gate G1 notes closed; full suite green.
2. **Dry run on the fake server** (the driver's `dry-run`; this is B4): the whole schedule at
   worst-case usage, the canary and the pilot included; every stop fires; the analysis table is
   stamped `FAKE`. Zero cost.
3. **Owner "confirm" (first).** The parent reads the key in-process, shows the numbers (USD 10
   ceiling on our ledger only; EP-1 USD 5 and 500 calls; canary USD 0.05 and one call; pilot
   USD 0.50 and 150 calls; the model ID; whether the Console limit is set) and waits for the one
   word. Recorded verbatim. The driver refuses without the owner-confirm flag.
4. **Canary:** one padded Haiku call. Console tokens and cost equal the ledger line, or
   everything stops. Refetch the price sheet first if it is older than 3 days (the current one
   is refused after 2026-11-22).
5. **Pilot:** opens only after the canary settled `complete`. 5 arms x 3 train-range sets.
   Traces hand-checked and the reading recorded. Excluded from every estimate.
6. **Any pilot-driven fix.** Code or card changes go back through step 1 (re-gate) and step 2.
   The prereg diff against its pre-pilot text is saved, to be shipped with the result. A change
   to `spend.py` or `backend_claude.py` makes the canary stale: owner decision.
7. **Human baseline** played and stamped `human`, or its absence written into the prereg
   (section 14) and carried into the result.
8. **Fill the open fields** of `prereg/EP1.md`: task-set hash (20 sets), template hashes, the
   analysis file's sha256, price sheet sha256.
9. **Commit.** `git status --short --ignored` on the hashed paths shows nothing but
   `__pycache__` and `.lake/`. First local commit (code and the prereg with `code_tree_hash:`
   blank). It may include verified uncommitted files. Never `--no-verify`. No push.
10. **`code_tree_hash`.** Computed over `src/`, `practices/`, `tests/` and the
    `formal/alloc_score/` sources (`.lean` files, `lakefile.toml`, `lake-manifest.json`,
    `lean-toolchain`; not `.lake/`). `train/` is excluded; `lab/` is outside. Written into
    `code_tree_hash:`; the prereg's sha256 and the config hash go into
    `docs/reports/prereg-freezes.md`; second local commit.
11. **`python -m murmuration prereg-check`** passes.
12. **Owner "confirm" (second).** The parent shows the frozen hashes and the caps and waits for
    the one word. Recorded verbatim.
13. **EP-1**, one process. Any code change after step 9 restarts from step 1.

Not checked: no code or test was run, so every count from a test (the differential zeros, the
17 mutations, the canary rows passing) is as reported or as read in the source; `.env*` was not
read; the Lean project was not built by me; the papers in the novelty check were not opened by
me; whether the API accepts an explicit temperature for `claude-haiku-5-5`; whether `prompts/`
is inside the tree hash today (step 9 assumes it must be); whether `prereg-check` can hash a
file subset of `formal/alloc_score/` (it takes paths; excluding `.lake/` may need a change);
the G1b fixes themselves, which I read as a report only; `ep1.py` beyond its scoring gate, void
path and stop mapping; whether the fixes of 2e are in the code as the prereg now states them
(G1b-R found that an `INVALID` Lean verdict did not void; the fix is reported only, and the
fix report reached me as a summary).

verified: 36bab4b (plus working tree) 2026-11-20

## Orchestrator rulings on section 2e (2026-11-20, owner-delegated)
1. The batch stop at the third all-stopped episode is REMOVED. All-stopped episodes occur only in the `code`
   arm, so an arm-driven batch stop would truncate the run asymmetrically and could leave the last task block
   unbalanced; it buys no protection (each episode is capped at 8 calls; the per-agent refusal stop inside an
   episode stays). All-stopped episodes are included (intention-to-treat) and counted per arm. Code change:
   ep1.py (next fix round), with a test that heavy refusal never stops the batch and never unbalances a block.
2. A valid task set is one where all three arms are non-void (the analysis is paired across arms).
3. The 'smaller than the 20-point smallest effect of interest' label uses the PRIMARY interval (cluster
   bootstrap, 95%): it applies when that interval's upper bound is below 0.20.

## Section 2e: resolved (2026-11-20)

The three items 2e left open are settled by the rulings above. Prereg changes 8 to 12 in its
"Pre-freeze changes" table carry them; `code_tree_hash:` stays blank. I read `ep1.py`,
`spend.py` and `analysis.py`; I ran nothing.

| Ruling | In the code | In the prereg |
|---|---|---|
| 1: no batch stop for all-stopped episodes | Yes: `ep1._after`; tests `test_all_stopped_episodes_never_stop_the_batch`, `test_heavy_refusal_in_the_code_arm_never_stops_the_batch_or_unbalances_a_block` | Section 12, changes 8 to 10 |
| 2: valid task set = all 3 arms non-void | Yes: `analysis.summarise` | Section 10, change 11 |
| 3: the <20-point label uses the bootstrap upper bound | Yes (read 2026-11-20, not run): `analysis._contrast` sets `smaller_than_effect_of_interest` from the bootstrap `hi`; the kill takes `hi_below_soi_both` (both intervals) | Section 11, change 12 |

Also folded in with ruling 1's fix round: an invalid log stops as `stopped:invalid_log`
(`void_model` keeps the model-identity voids and the malformed-reply stops); `spend.STOP_WHY`
has nine values; `Ledger.settle` refuses while a stop is recorded on the batch, a child or a
dependency, and the same rule gates `pilot` and `ar1`.

**Open, for the next fix round (not guessed here):**

- DONE in the code (read, not run; the tests are for the re-gate to run): `analysis.py` applies
  the label on the bootstrap interval alone (ruling 3), and the kill read-off takes `fires` from
  the separate flag `hi_below_soi_both`.
- `refusal_loop` is still in `spend.STOP_WHY` and nothing writes it. Removing it is a `spend.py`
  change that needs re-verification (G0-2R2); the prereg states it as unused.

verified: 36bab4b (plus working tree) 2026-11-20

## After pilot 1 (2026-11-20): four decisions and the implementer's list

Pilot 1 ran on real Haiku 5.5 and stopped on the malformed rule (11 episodes, 88 calls, USD
0.0115). Sources: `docs/reports/pilot-1-diagnosis.md`, `runs/ep1-live/pilot/pilot_trace.txt`.
The prereg carries these as pre-freeze changes 13 to 17; `code_tree_hash:` stays blank. I read
the diagnosis, the trace and the code named below. I ran nothing and made no call.

### 1. Truncation: thinking is turned off; `max_tokens` stays 300

- **Decision.** Every request sends `"thinking": {"type": "disabled"}`. No cap or budget moves.
- **Checked in the Claude API documentation, 2026-11-20.** Haiku 5.5 thinks when the field is
  absent and accepts `disabled` at effort `high` or below; its default effort is `medium`. The
  quoted lines are in the prereg, section 6. The diagnosis said the same; it is now read from
  the source. Not shown on a real call yet.
- **Why not `max_tokens` 1,000.** It keeps thinking whose depth follows the card, so the arms
  would still differ in something no one pre-registered. It rests on outputs pilot 1 saw only
  cut at 300. It moves the `ep1` token cap to 1,500,000, tokens per episode to 24,000 and the
  per-call output cap to 1,000. Off does none of this.
- **Risks carried into pilot 2:** visible reasoning that the parser rejects, and wrong sums.
- **Fallback** if the API returns a 400: `max_tokens` 1,000 with those three caps. That is an
  owner decision.
- **Side finding.** The documentation says Haiku 5.5 returns a 400 for any non-default
  temperature, and for any temperature at all from API version 2026-10-21. The explicit 1.0
  works today because it is the default and the pinned version is older. Keep the pin.

### 2. Herding: both the phenomenon and an instrument fault; task order is drawn per agent

- **What the trace shows.** All four agents claim the first listed task in round 1 of all 11
  episodes; the three losers all claim the second. `Y` is 0.5 or 0.75 and equal across the
  conditions of a set.
- **Reading.** Under `none` this is the herd the practice is for. Under `play` and `code` it is
  a fault of the instrument: the four prompts are identical and the board is empty, so neither
  the card nor the lock gives an agent a reason to pick differently from its neighbour. The
  design could not show 20 points whatever the truth.
- **Decision.** Each agent sees the 6 tasks in its own seeded order, the same in every arm of a
  task set. It adds no text and no advice.
- **It favours no arm** because the seed has no arm in it and every contrast is paired within a
  set. It lifts `Y` in all three arms; the room above `Y_none` may shrink, which works against
  finding a gain, and pilot 2 screens for that on `none` alone (mean `Y_none` 0.30 to 0.80).
- **Was open for the owner or orchestrator; resolved 2026-11-20 by measuring both** (section
  "Pilot 2 runs both task orders" below). The decision above is no longer EP-1's order; it is
  one of two candidates. The alternative was to keep the sorted list and state in advance that
  EP-1 can then show only "no difference".
- **Not done:** I did not model how `Y_none` will land. The 0.28 chance of four distinct first
  picks assumes every agent takes the first task it sees; real agents may not.

### 3. Refusal labels differ by arm: a note is enough

Confirmed. The loser's release is refused as `board_error` under `none` and `play`, and as
`A:*` plus sometimes `board_error` under `code`. It reaches the board after the work event, so
`Y` and `valid` do not move, and a stop it triggers comes after the agent's last action. The
prereg now says the refusal read-off is given in two rows and the sum is not compared.

### 4. Pilot 2

| Item | Value |
|---|---|
| Batch | `pilot2`, sibling of `ep1`, opens after the canary settled `complete` |
| Caps | USD 0.25, 260 calls, 598,000 tokens (260 x 2,300); worst case reserved USD 0.143 |
| Source | The unallocated USD 1.50; USD 1.25 stays. **Approved by the owner 2026-11-20** ("You got my approval"; `ep-approvals.md`, addendum 6) |
| Size | 5 conditions x 6 train sets (seeds 0 to 5) x 8 = 240 calls, 30 episodes; 3 sets per task order |
| Stops | The driver's own (400, transport, malformed above 24 of 240 or 7 of 48 per condition, caps) plus: any `thinking` block in a response |
| Clears EP-1 | All seven criteria in the prereg, section 13 item 16b; criterion 5 is now "at least one order usable" |

### Implementer's list (I changed no code)

| File | Where | Change |
|---|---|---|
| `src/murmuration/team_claude.py` | `CAPS` (line 36) | add `"thinking": {"type": "disabled"}`; `output_tokens` stays 300 |
| `src/murmuration/team_claude.py` | body, lines 308 to 310 | add `"thinking": self.caps["thinking"]` to the hashed body |
| `src/murmuration/backend_claude.py` | payload, line 132 | add `"thinking": {"type": "disabled"}`; keep only `text` blocks as now, and record the list of content-block types per call |
| `src/murmuration/ep1.py` | size probe, line 405 | add the same `thinking` field so the byte probe measures the real body |
| `src/murmuration/team_claude.py` | `prompt`, line 206 | list tasks in `random.Random(f"ep1:view:{ts['split']}:{ts['seed']}:{agent}").sample(tasks, len(tasks))` order; no arm in the seed |
| `src/murmuration/spend.py` | `BATCH_SPECS` | add `"pilot2": {"usd": 0.25, "calls": 260, "tokens": 598_000, "parent": None, "requires_settled": CANARY, "settled_reasons": ("complete",)}` |
| `src/murmuration/spend.py` | `PER_CALL_OUTPUT_TOKENS`, `ep1` tokens, `pilot` | no change: 300, 1,250,000, 345,000 |
| `src/murmuration/ep1.py` | `KINDS`, `DEFAULT_SETS`, `SPLIT` | add kind `pilot2`: 6 sets, split `train`, the 5 pilot conditions |
| `src/murmuration/ep1.py` | after each call | stop the batch if a response holds a `thinking` block |
| `src/murmuration/ep1.py` | pilot report | key per-condition summaries on `cond`, not `arm` (the two pilot cards were folded into `play`) |
| `src/murmuration/analysis.py` | refusal read-off | two rows per arm: `A:*` denials and `board_error:*` |
| tests | | the field is in both request builders; the order is equal across arms and differs across agents; `pilot2` caps; the thinking-block stop |

`spend.py` and `backend_claude.py` change, so G0-2R2 must cover them again, and the canary no
longer covers the changed request; pilot 2's first call stands in for that (prereg, item 16b).

verified: 36bab4b (plus working tree) 2026-11-20

## Pilot 2 runs both task orders (2026-11-20, owner approved)

Owner, verbatim: "You got my approval". This answered the ask "confirm both orders and pilot 2"
(`ep-approvals.md`, addendum 6). Prereg: pre-freeze change 18; section 13, item 16b.

- **The herding disagreement is resolved by measuring both.** S2 (as the orchestrator names it; I
  did not reread it for this edit) keeps the shared list, because the herd is the phenomenon the
  practice is for. My change 14 drew the order per agent, because under one list no arm could
  differ in pilot 1. Neither side had data with thinking off. Pilot 2 now runs both, and neither
  position is adopted in advance.
- **Design.** Factor `order`: `shared` or `per_agent`. In pilot 2 only, the 6 task sets split 3
  and 3 by a seeded assignment with no arm in it. All conditions of a set share its order, so
  contrasts are within an order. No call is added and no cap moves (240 scheduled, 260 calls,
  USD 0.25, 598,000 tokens). EP-1 and the canary stay on `shared` until the rule picks.
- **The rule that picks EP-1's order (design decision, not a confirmatory test).** An order is
  usable when, on its 3 sets: (a) mean `Y_none` is 0.30 to 0.80; (b) at least 2 executed
  duplicate work events under `none` (0 under `code` by construction); (c) `Y_code` differs from
  `Y_none` in at least one set. One usable: EP-1 uses it. Both: `shared`. Neither: EP-1 is not
  cleared and the table goes to the owner. The owner may overrule before the freeze.
- **Why these three.** (a) is the old room screen. (b) asks whether the failure the practice
  targets happens at all in that order. (c) is the pilot 1 fault stated as a test: if the
  enforced rule cannot move `Y`, the card has no room either. The `play` arm stays out of the
  rule so that the choice is not made on the primary contrast.
- **Why `shared` wins a tie.** It is built, gated and covered by the canary, and it keeps the
  natural herd. The tie is not broken by the size of a pilot difference, which at 3 sets is
  noise.
- **Into the freeze.** The chosen order becomes one fixed value in the prereg, section 6, with
  the pilot table for both orders, as a dated pre-freeze change. `per_agent` means a change of
  EP-1's default in the code and a re-gate; `shared` means none. This sits in step "any
  pilot-driven fix with re-gate and prereg diff" of section 4, before the commit and the hash.
- **Power.** 3 `none` episodes per order: mean `Y` in steps of 1/12; 20 points is 2.4 slots of
  12. The orders run on different task sets. The rule can pick the wrong order and can call a
  workable order unusable. It catches a gross fault only. No pilot 2 number is a finding.
- **Implementer's list, row 5, is superseded.** The per-agent order is a switch
  (`team_claude.CAPS["task_order"]`, default `shared`), not the only order. Still needed: the
  seeded 3 and 3 assignment for kind `pilot2`, the per-order table in the pilot report, and a
  test that the assignment is the same for every condition of a set.
- **Not checked.** I ran nothing. I read the switch in `team_claude.py` (working tree) and did
  not see the set-to-order assignment in the code. Thresholds (b) and (c) are my design
  choices; no simulation says how often they misfire. Whether `analysis` reports executed
  duplicate work per order today, I did not check.

verified: 36bab4b (plus working tree) 2026-11-20

## 2f. Pilot 2 malformed-reply fix (pre-freeze change 19)

**Stop reason (reconciled against the retained archive):** 23 of 88 calls were recorded as malformed (26.1%), comprising 22 `not_json` and one `oversize`. Each retained malformed reply had leading text before a final JSON array. All 88 replies ended with `end_turn` and the recorded content blocks were text. The strict parser rejected leading text outside the JSON array. See `runs/m10-early-pilot-provenance.l7RSWZ/report.json` for the aggregate replay.

**Arm distribution (exploratory, n=11 episodes):** `states_check` 10, `play` 6, `keyword_stuffed` 3, `none` 3, `code` 1. Prose differs by card (`states_check` most), but the fix is arm-neutral: it changes the parser, not the prompt.

**Considered and rejected:**
- **Assistant prefill (`[`):** Haiku 5.5 returns HTTP 400 on any prefill even with `thinking: disabled`. Official docs do not qualify this by thinking mode; the restriction applies to the model family. Not viable.
- **Prompt line "JSON array only":** Would not eliminate the model's visible reasoning (it is not instruction-following failure; the model architecture outputs it). Adds words that favour no arm but does not solve the problem.
- **Raise `max_tokens`:** 300 is a hard cap on total output; prose + JSON often exceeds it. Raising to 1,000 moves three caps and needs owner re-approval (section 1 item 13).

**Chosen fix (pre-registered, arm-neutral):** Accept the **last top-level JSON array** in the reply. Prose before it is ignored and logged as `extra_text_bytes`; anything after it is `extra_text` and malformed. `max_reply_bytes` (600) still counts the whole reply. No threshold changes (10% overall, 15% per arm); the fix reduces the malformed numerator.

**Implementation:** `team_claude.parse` → find last `raw_decode` yielding a list; verify trailing is only whitespace; return that list. `extra_text_bytes` recorded per turn for audit.

**Pilot 2 order observations (exploratory only):** `per_agent` showed 0 duplicates in 3 `none` episodes (pilot 1 had 2); `shared` showed 1. Per-arm counts too small (n=1 per cell) to infer. The change-18 order rule **cannot be evaluated from pilot 2** — it stopped after 88 calls (11 episodes) under a 260-call cap, before completing the planned task sets. Pilot 3 must show: 6 task sets per order (3 `none` episodes each), room/duplicate/instrument-gap pass/fail per the rule in 13.16b.

**Pilot 3 specification (same both-orders design):**
- New batch `pilot3` sibling of `ep1` in `spend.BATCH_SPECS` (not inside `ep1`).
- Caps: USD 0.25, 260 calls, 598,000 tokens from unallocated USD 1.25 (addendum 7).
- Per-call caps unchanged: 2,000 bytes in, `max_tokens` 300, `thinking` disabled.
- 5 arms × 6 train sets × 8 calls = 240 calls + 20 retry buffer.
- Same 7 clearance criteria as pilot 2.
- Owner approval required before run.
