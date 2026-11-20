# G1b fixes: the EP-1 model loop after the REJECT

2026-11-20. Opus 5.5, implementer. A different Opus verifies. Answers `G1b.md` defects G1b-1 to G1b-8 and the
brief's items 1 to 6. Nothing was committed or pushed.

> **Instrument validation only.** Every number here comes from scripted responders, the loopback fake server or a
> loopback raw socket. None of it is evidence about a model. No key, no `.env*`, no provider call, no GPU.

**Subject.** HEAD `36bab4b` plus uncommitted work.
- Changed: `src/murmuration/team_claude.py`, `prompts/ep1/system.md`, `prompts/ep1/turn.md`, `src/murmuration/router.py`
  (one read-only function, `stops`), `tests/test_team_claude.py`, `tests/test_router.py`.
- Not changed: `team.py`, `enforce.py`, and every frozen file (`backend_claude.py`, `spend.py`, `board.py`, and the rest).

## What the loop does now

1. **A reply is one JSON array of actions.** A bare object counts as a list of one.
   - Round 1 accepts one `claim`, or `pass`.
   - Round 2 accepts `claim`, `work` and `release`, each optional and at most once, in that order; or `pass` alone.
   - The parser stays strict:
     - nothing before or after the value, and no second value;
     - no BOM and no comments;
     - duplicate keys, `NaN` and `Infinity` are refused;
     - every element is a flat object, so the depth is one array of scalars; 600 bytes at most;
     - only the allowed types and fields;
     - each task id must be in the set shown to that agent: exact match, ASCII, at most 32 characters.
   - Reasons: `pass_not_alone`, `empty_list`, `duplicate_type`, `out_of_order`, `unknown_task`, `multiple_values`,
     and the earlier ones.
2. **Execution.** Each round, every agent reads, then is called, in call order. Then the replies run through
   `router.act` in the board's seeded order (item 6), each reply's actions in their own order.
   - **A refused action is lost and counts as one refusal of that agent (D3).** Its later actions are still sent and
     buy no extra call.
   - Under `code`, sending the later actions frees nothing: a refused claimer's `work` is `work_without_claim`.
3. **A `release` of the task claimed in the same reply runs after that round's `end_round`.**
   - The board accepts a release only for a committed claim, so this is required. Without it, card-A holders ("release
     when done") would collect board-error refusals that agents with the neutral twin do not.
   - It still goes through `router.act`, in seeded order. It is refused if the agent lost the board's draw, which can
     happen under `none`.
4. **Stops are read after every action.** `router.stops(handle)` is a read-only query: no act, no log line.
   - Without it, a stop reached by an agent's last action was invisible: `act` reports a stop only on the next action.

## Defects and their fixes

| G1b | Fix | Regression tests (`tests/test_team_claude.py` unless named) |
|---|---|---|
| 1 one action per reply | Ordered list per prereg 6; deferred same-reply release | `RoundActionTests.*`, `ParseAndMalformedTests.test_valid_actions_and_round_rules`, `test_parser_cases` |
| 1 false-done by construction | An honest work then release now executes; the rate is measured | `RoundActionTests.test_false_done_is_measured_not_built_in`: 0, 0.25 and 1.0 in every arm |
| 2 unknown ids, crash, side channel | Ids must be on the board; a `PromptTooLarge` becomes a record | `TaskIdTests.*`, `CapsAndSealTests.test_oversize_prompt_is_refused_before_any_call_and_the_record_is_kept` |
| 3 `batch` signature | `ClaudeClient.call` now takes `batch`, and the loop passes it | `FakeServerScheduleTests.test_real_client_signature_through_the_loop_with_a_batched_ledger` |
| 4 escaping `HTTPException` | Caught in the loop: `infrastructure_abort`, worst case added | `HttpRobustnessTests.test_transport_failures_are_infrastructure_aborts_and_rerunnable` |
| 5 a 200 with no model | Void, not re-runnable | `HttpRobustnessTests.test_a_200_without_or_with_another_model_is_a_void_not_a_rerun` |
| 5 `stop_reason` | Any value other than `end_turn` is malformed | `HttpRobustnessTests.test_truncated_or_declined_replies_are_malformed` |
| 6 claim order | Seeded execution order | `SeededOrderTests.*` |
| 7 label spoof | Strict `_is_real`; `model` taken from the responses | `LabelTests.*`, `LabelFromResponseTests.*` |
| 8 stop clauses unreachable | Reachable; see the next section | `RefusalStopTests.*`, `test_router.ActTests.test_stops_reports_a_stop_reached_by_the_last_action_without_acting` |
| 8 re-runs reuse ids | Refused before any request unless a new `id_tag` is given | `FakeServerScheduleTests.test_a_rerun_needs_a_new_id_tag` |
| 8 no `orders` | `orders` is in the record | via `RoundActionTests` |
| 8 template hash re-read | Hashed from the bytes used | `CapsAndSealTests.test_template_hashes_are_the_files_and_the_record_carries_them` |
| M08 gold leak survived | Every prompt of 15 heldout sets x 4 arms x 3 scripts is scanned for every `expect` | `GoldLeakTests.test_no_prompt_of_a_full_schedule_holds_a_gold_answer` |

**More detail on some rows:**
- **G1b-2.** `TaskIdTests` covers emoji, `\x01`, `é`, prose and over-long ids. Each is `unknown_task`, never reaches the
  board, and never appears raw or escaped in any other prompt. The record is never lost.
- **G1b-3.**
  - The real `ClaudeClient` runs against the fake server with the `ep1` batched ledger: 8 calls, `Y = 1`.
  - `batch_report` counts 8 calls.
- **G1b-4.** The client still catches only `OSError` and `ValueError`.
  - A cut-short body (`IncompleteRead`) or a bad status line (`BadStatusLine`) leaves its reserve open.
  - The loop adds `ledger.worst_case` to `usd_unbilled`. The test checks it equals the ledger's `spent_usd`.
  - **How it is caught.** `test_egress` forbids importing `http.client` outside `backend_claude.py`. So the loop
    catches `Exception`, matches `http.client.HTTPException` by its class hierarchy (module and name), and re-raises
    anything else.
- **G1b-6.** In the board's seeded order, for each claimed task the claimant drawn by `Board.end_round` goes first.
  Tests:
  - for seeds 0 to 14, `none` and `code` give the same winner, and the winner is not always `a0`;
  - with 3 shuffled call orders, 4 arms and 3 scripts, every outcome is identical.
- **G1b-7.**
  - `_is_real` requires `type(client) is ClaudeClient`, no instance-level `call`, a constructed `_key` and the real host.
  - The record's `model` is the model the responses named, or `None` if they disagree. The request is kept as
    `requested_model`.
  - The real-label test patches only `_post`, with `PILOT_LEDGER_DIR` patched to a temp dir.
- **Template hashes.** `template_sha256` is now hashed from the template bytes actually loaded.
- **M08.** The scan matches the number with digit-bounded matching. Heldout sums are 100 or more, so they never
  equal an operand.

**Proof against the old code.** The new `test_team_claude.py` was run on a scratch copy of the pre-fix tree:
**20 of 44 tests fail** (8 FAIL, 12 ERROR).
- Every regression test above fails on the old code, except two.
- `GoldLeakTests` passes on the old code, because the old code does not leak. It exists to kill the M08 mutation;
  see the mutation table.
- `test_real_client_signature...` fails on the old code because of the old record shape. Against the real old
  behaviour (HEAD `backend_claude.py`, with no `batch` parameter, plus the new loop) it fails with
  `TypeError: ClaudeClient.call() got an unexpected keyword argument 'batch'`.

**Mutations on the new code: 17 of 17 RED.** Each mutation was applied to a scratch copy and judged by
`test_team_claude`. The script is in the session scratchpad, `g1bfix/scripts/mutate.py`.

| Mutation | Result |
|---|---|
| M08: gold answers in the system text | RED |
| No stop query | RED |
| A refusal ends the turn | RED |
| Execution in call order | RED |
| No deferral of a same-reply release | RED |
| No id check | RED |
| No `HTTPException` catch | RED |
| A 200 with no model left re-runnable | RED |
| `stop_reason` ignored | RED |
| The old `_is_real` | RED |
| `model` label taken from the request | RED |
| No re-run check | RED |
| No unbilled worst case on an escaped exception | RED |
| `PromptTooLarge` raised instead of recorded | RED |
| Action order unchecked | RED |
| Duplicate types unchecked | RED |
| No void on a missing model | RED |

## HTTP outcomes (item 4)

Every case returns a record. None is accepted as a reply (`log == []`). The ledger keeps every attempt without
usage at its reserved worst case, and `usd_unbilled` equals the ledger spend in the test.

| Case | Client behaviour | `ended` | Re-runnable |
|---|---|---|---|
| 200 cut short (`IncompleteRead`) | escapes the client, caught in the loop | `infrastructure_abort` | yes, with a new `id_tag` |
| bad status line (`BadStatusLine`) | escapes the client, caught in the loop | `infrastructure_abort` | yes, with a new `id_tag` |
| connection reset, closed without a reply | `OSError`, one retry | `infrastructure_abort` | yes, with a new `id_tag` |
| timeout | `OSError`, one retry | `infrastructure_abort` | yes, with a new `id_tag` |
| 429, 529, 500 twice | one retry | `infrastructure_abort` | yes, with a new `id_tag` |
| 400 | no retry | `infrastructure_abort` | yes, with a new `id_tag` (see owner decision 2) |
| 429, then 200 | retry succeeds; 9 ledger calls | plays on | n/a |
| 200 with no or empty `model` | `RuntimeError("... HTTP 200 ...")` | `void` | no; batch stop |
| 200 with another `model` | client void | `void` | no; batch stop |
| `stop_reason` `max_tokens` / `refusal` / other | reply received | the turn is malformed (`truncated`, `declined`, `bad_stop_reason`) | n/a |
| request over the input cap | not sent | `prompt_too_large`, with `abort_reason` | no: a harness fault |

- **Re-runs.** `run_episode_model` refuses with `ValueError`, before any request, when the client's ledger directory
  already holds a reserve for that episode id. A re-run must pass a new `caps["id_tag"]`: up to 16 characters of
  `[A-Za-z0-9_-]`. The record carries `episode_id`, `id_tag`, `rerunnable` and `batch`.
- **Mapping a 200 with no model to void keys on the frozen client's message `failed: HTTP 200`.** The fake-server test
  pins it. If `backend_claude.py` changes that message, the test goes red.

## Refusal stops (item 6, D3, prereg 12)

Each refused action counts, so:
- **3 consecutive (per agent) is reachable in EP-1.** A round-2 reply of claim, work and release on a task another
  agent holds gives 3 refusals, and that agent stops. The release is the third: a board error.
  - Test: `ended = complete`, `stopped_agents = ["a0"]`, `Y = 0.75`.
- **20 total is unreachable with 4 agents.** At most 3 refusals in round 1 and 3 per agent in round 2: 3 + 12 = 15.
  - The test reaches 14, still `complete`.
  - With 6 agents (5 herd losers each refused 1 + 3) it fires: `ended = episode_stopped`, 20 refusals, 5 agents
    stopped, one holder playing honestly.
- **The episode stop is reachable with 4 agents another way:** every agent stopped, if all four send three refused
  steps in round 2.

## Prereg clarifications needed (exact text for `prereg/EP1.md`, owner to apply before the freeze)

1. **Section 6, the "Reply format" line.**
   - Replace: "Reply format: one JSON object. Anything else is a logged no-op and the turn is lost."
   - With: "Reply format: one JSON array of actions in the round's order; a bare object counts as a list of one.
     Every task id must be one shown on the task list. Anything else is a logged no-op and the turn is lost."
2. **Section 6, after "Round 2 accepts, in this order and each optional: ...", add:** "or `pass` alone. The actions
   of a reply are sent to the router in their order. A refused action is lost and counts as one refusal; the later
   actions are still sent, and no extra call is bought. A `release` of the task claimed in the same reply is
   executed after the round's claims are resolved."
3. **Section 6, the "Claims in one round are resolved at its end in the board's seeded order" line, add:** "Under every
   arm the replies of a round are executed in that order. For each task claimed in the round, the claimant that the
   board's seeded draw picks executes first. Under `code` and `both`, the claim lock therefore refuses exactly the
   agents the board would resolve against."
4. **Section 6, "Budget matching".**
   - Replace "a refusal costs the turn and buys no extra call".
   - With "a refused action is lost and buys no extra call".
5. **Section 12, "refusal loop".**
   - Replace "an episode ended by 3 consecutive or 20 total refusals".
   - With "an episode ended because every agent was stopped (3 consecutive refusals each) or the team reached 20
     refusals; with 4 agents and 2 rounds the total is at most 15, so only the first can end an EP-1 episode".
6. **Section 13.4.** Strike the "Open defect" sentence. D3 settled it, and `test_team_claude.RefusalStopTests` proves
   both stops through the model loop.
7. **Section 13.3, add:** "a task id not on the board (`unknown_task`), a `stop_reason` other than `end_turn`
   (`truncated` or `declined`), and an out-of-order or duplicate action type".
8. **Section 12, "Instrument void", add:** "a 200 response that names no model".

## Owner decisions still open (not settled by code)

1. **Section 6 against section 12 on transport failures.**
   - Section 6 calls an infrastructure abort re-runnable.
   - Section 12 stops the batch on 429 or 5xx after the retry, and on any `unbilled_unknown` ledger line. Every failed
     attempt writes such a line, including a retried 429 that then succeeds.
   - The loop records `rerunnable: true` and leaves the stop to the batch driver.
   - The owner must say which wins, and whether a lone `unbilled_unknown` from a successful retry stops the batch.
2. **Whether a 400 is re-runnable.** A request error, such as `temperature` not accepted, will repeat on every re-run.
   The loop calls it `infrastructure_abort`.

## Not done, still required before the freeze (from G1b "Must be done")

- **The batch driver, item 10.** None of it exists yet:
  - seeded arm order;
  - one `ep1` ledger;
  - batch stops on void, malformed thresholds and the first-set check;
  - `id_tag` per re-run.
- **The analysis entry point and the paired-t function, item 12.**
- **A re-run of the G1b gate at a fixed SHA, item 14.**
- **The template hashes changed** (`system.md`, `turn.md`) and must be recorded in the config hash.
- **G0-2R.** No spend file was touched. `backend_claude.py` is unchanged; `HTTPException` is handled in
  `team_claude.py`.
- **Known and left alone:**
  - `system.md` still says "a team of four" (harmless for EP-1);
  - the status line keeps the `A:` predicate prefix (a G1b-8 note);
  - retries have no backoff.
