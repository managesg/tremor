# Gate G1b-R: re-gate of the EP-1 model loop and the EP-1 driver (independent adversarial verification)

2026-11-20. Opus 5.5, fresh context, not the author of this code. Read-only on the repo except this file.
- No provider call, no key, no `.env*`.
- `train/`, `runs/` and `data/` untouched; the Lean toolchain was used read-only through a symlink.
- `CUDA_VISIBLE_DEVICES=''` and `python3 -B` everywhere.
- Every run, probe and mutation ran on a copy in the session scratchpad (`.../scratchpad/g1br/`). The copy's
  `spend.PILOT_LEDGER_DIR` resolves inside the copy. The real `runs/spend` does not exist before or after.
- Network: 127.0.0.1 only (the fake server and a raw-socket server).

> **Instrument validation only.** Every number below comes from scripted responders, the loopback fake server or a
> raw loopback socket. None of it is evidence about a model.

**Subject.** HEAD `36bab4b` plus uncommitted work. I snapshotted it at the start; the sha256 list of `src`, `tests`,
`prompts`, `practices`, `prereg` and `formal/alloc_score` is in the scratchpad (`tree.sha`).
- At the end the live tree differed from the snapshot in one file only: `prereg/EP1.md`, which another session is
  still editing.
- Every code, test, prompt and card file was identical. The verdict binds to that code; there is still no fixed SHA.

## Verdict

**REJECT. The freeze may not proceed. The canary may not proceed either:**
- prereg section 13 orders the canary after this re-gate's ACCEPT and after G0-2R2;
- the canary path has its own crash (R-4).

The G1b defects 1 to 8 are fixed in the loop and hold under my probes. The ordered actions, the unknown-id
rejection, the HTTP handling, the seeded order and the label are all sound.

The REJECT comes from the driver and from two places where code and prereg disagree:
- the scorer gate does not void on Lean `INVALID` (R-1);
- the loop does not check the returned model itself (R-2).

## Defects, ranked

### R-1 (blocks the freeze). Lean `INVALID` or `REJECTED` never voids an episode

What the prereg requires:
- section 7: "An episode without three agreeing verdicts does not enter the analysis";
- section 12: "or the Lean scorer returns `INVALID`. That episode is void".

What the code does:
- `ep1._score_gate` records `third.status = INVALID` (or `REJECTED`) but sets no `disagreement`. Only an `OK` Lean
  result that differs is compared.
- Nothing reads `third` again: not `_Run._valid`, not `_after`, not `analysis.summarise`. The episode is valid, is not
  re-run and enters the analysis with its `Y`.
- The module docstring says so plainly ("the third scorer is optional and never blocks a run").

The suite encodes the opposite of the prereg:
- `test_ep1.Base` patches `_lean` to return `INVALID` for every test (lines 26 and 76);
- `test_full_dry_run_within_all_caps_through_the_cli` then asserts 60 `complete` episodes and `inconclusive`;
- `test_every_record_carries_what_analysis_needs...` asserts `third.status == "INVALID"` on a counted record.

**Fix.**
- In `_score_gate`, any `third` status other than `OK` voids the episode, through the same path as a disagreement.
- `Base` gets an `OK` stub (or the real Lean); one test asserts that `INVALID` and `REJECTED` void and stop the batch.
- Settle in the prereg whether a Lean `INVALID` on one episode stops the batch or only voids the episode. A missing
  Lean voids all 60.

With the real Lean (built in the copy in about 20 s), the CLI dry run had `third = OK` on 60 of 60 episodes. So the
fix costs nothing when Lean is present.

### R-2 (blocks the freeze). The loop does not compare the returned model with the requested one

The brief asks whether the loop itself, not the client, voids a mismatched model. It does not.
- `team_claude.ask` voids only when `returned_model` is missing or empty, or when the client set `rec["void"]`.
- Probe `p1_model.py`: a scripted client returned each of `claude-sonnet-5-5`, `claude-haiku-5-5-20261101`,
  `CLAUDE-HAIKU-5-5` and `" claude-haiku-5-5"`.
  - Each gave `ended = complete`, `void = None`, `Y = 1.0`.
  - The record's `model` was the wrong id.
- One call of 8 returning `claude-opus-5-5` also gave `complete`. The `model` was `None`, but there was no void.
- `analysis._check` tests only that `model` is truthy, so a single wrong id reaches a model table.
- A list-valued `returned_model` from a scripted client raises `TypeError` out of `run_episode_model`, with no record.

What still protects the real path:
- the real `ClaudeClient` voids a mismatch (`sheet.accepts`), including a non-string model;
- `test_ep1.test_returned_model_mismatch_voids_and_stops` passes;
- my raw-socket probe with a list-valued model gave `void` and `stopped:void_model`.

**Fix (one line).** Void when `rec.get("returned_model") != self.caps["model"]` (or `not sheet.accepts`). Add a
scripted-client test. Optionally make `analysis._check` require `model == requested_model`.

### R-3 (fix before the freeze). The floor bracket accepts any floor below 1

- Prereg section 12 voids if "the scripted floor scores above 1/4".
- `ep1._bracket` sets `floor_fails` when every floor `Y` is below 1.
- `test_floor_fails_and_oracle_passes_through_the_driver` asserts only `y < 1`.
- Mutation M12 (the floor responder sends a1 to task 1, so floor `Y = 0.5`): see the mutation table.

**Fix.** `floor_fails` requires every `Y == 0.25`, and the test asserts it.

### R-4 (fix before the canary). The canary path does not catch `HTTPException`

`_canary` catches `RuntimeError`, `EpisodeVoided`, `EpisodeCapExceeded` and `SpendError`. My raw-socket probe cut the
canary's 200 response short, and `http.client.IncompleteRead` escaped `run_batch`. As a result:
- no `canary.json` is written;
- no `stop_batch` is recorded;
- the `canary:0` reserve stays open at its worst case.

The loop handles the same exception (G1b-4), so this is the one path the fix missed. A cut-short paid canary would
crash the process and leave the batch unsettled. The ledger refuses a reused id, so there is no double charge.

**Fix.** Catch it as the loop does (`team_claude._http_exception`): reason `transport`, the batch stopped, the record
written. Add a test.

### R-5 (owner decision before the freeze). An `episode_stopped` cell is done for the driver but censored by the analysis

- The driver counts `ended = episode_stopped` as a valid, finished cell (`_valid`): it is not re-run.
- `analysis.summarise` keeps only `ended == "complete"`. So the whole task set leaves every contrast.
- Probe `steal` (round 2, every agent claims, works and releases a neighbour's held task), 20 seeds:
  - `code`: `episode_stopped`, `Y = 0.0` in 20 of 20;
  - `none` and `play`: `Y = 1.0`.
- So the arm-caused worst outcome is dropped, not scored. This is informative censoring in favour of `code`.
- At most 2 such sets can be lost, because the third such episode stops the batch.

Prereg section 12 says the episode "is scored from its log and flagged", and section 10 says a set enters only "if
all its arms completed". The owner must pick one reading, and the code must match it.

### R-6 (fix before the freeze, in `analysis.py`, whose sha256 is frozen). Prereg sections 10 and 11 rules not implemented

- "With fewer than 12 complete sets every contrast reads 'incomplete: not shown'": not present.
- The label "Smaller than the 20-point effect of interest" when `hi < 0.20`: not present. Neither is the kill read-off
  of section 12 (`hi < 0.20` in both intervals).
- The "exploratory" label on the two secondary contrasts: not present.
- `analysis.resolve` falls back to the bootstrap alone when the paired t is missing (one set). The prereg requires
  both intervals; with the 12-set floor this only matters if that floor is absent.

### R-7 (record text, before the freeze)

1. **Largest request.** Prereg sections 6 and 13.2 say 1,386 bytes (seeds 0 to 14).
   - On heldout seeds 0 to 19, the largest I measured is **1,476 bytes**: seed 19, a two-digit seed id, with a random
     script. Every seed-19 prompt was above 1,460 bytes.
   - It is still under the 2,000-byte cap. Section 13.13 requires the re-measured number.
2. **`backend_claude.py` is modified** (the `batch` parameter and its mismatch check, 6 lines against HEAD).
   - G1b-fixes says "`backend_claude.py` is unchanged" in one place and "`ClaudeClient.call` now takes `batch`" in
     another.
   - So G0-2R2 must re-hash `backend_claude.py`, not only `spend.py`.
3. **The card review is pinned to an older scorer.** `docs/reports/card-A-review.md` records `alloc.py` at `91b4d8...`;
   the tree has `07ae29d8...`.
   - `check_card` checks only the card sha256, which matches (`9875048b...`), so the gate passes nominally.
   - The reviewer should re-confirm against the current scorer.
   - Non-authorship itself is not machine-checked: any file holding the sha passes.

## Notes (no action required for the freeze unless the owner wants it)

- **Other 4xx codes.** 401, 403, 404 and 413 become re-runnable `infrastructure_abort`s, not the HTTP-400 instrument
  stop. That is bounded by the 3-abort stop.
- **Leniency in the parser.** A trailing NBSP is stripped and accepted (`str.strip`). A `release` without `done` is
  accepted (`done` is optional).
- **Code-arm status lines** carry `refused: A:duplicate_claim:<id>`. The word "duplicate" is a banned card word. This
  is part of the `code` treatment (known since G1b-8), and no gold appears with it.
- **The system text says "one work slot" and "Correct answers count".** Both are banned card words. They are shared by
  every arm, and the distinctness predicate is not stated.
- **Stop labels.** A malformed-threshold stop is written with the ledger's `void_model` `why`, and `prompt_too_large`
  maps to `crash`. Both are correct as stops; the labels are coarse.

## Answers to the brief

### (1) Parsing, round rules, one accepted work per agent

**Parser probe** (`p2_parse.py`, 46 inputs). Every hostile input was refused with a reason:
- smuggling:
  - prose or a code fence: `extra_text` / `not_json`;
  - two arrays: `multiple_values`;
  - zero-width trailing: `extra_text`;
  - BOM: `not_json`;
- duplicates and order:
  - two `work`s: `duplicate_type`;
  - `work, claim`: `out_of_order`;
  - `pass` plus anything: `pass_not_alone`;
  - a duplicate (also escaped) key: `not_json`;
- values:
  - `NaN`: `not_json`;
  - `1e2`, `true`, a 33-character name: `bad_field`;
- shape and size:
  - nesting 300 deep, a JSON string or `null`: `not_object`;
  - over 600 bytes: `oversize`;
- identity and ids:
  - an `agent` field: `agent_field`;
  - an unknown, upper-case, padded or Unicode look-alike id: `unknown_task`;
  - an extra key: `extra_key`;
- round 1:
  - `work` or `release`: `type_not_allowed_in_round`;
  - two claims: `duplicate_type`.

**Round-1 loser path** (`p6_rounds.py`, 20 heldout sets, all 3 arms):
- `honest` (herd on t0; losers claim a free task, work it and release it in one reply): `Y = 1.0`, complete in every
  arm.
- `clash` (two losers claim the same free task): `Y = 0.5` in every arm. Under `code` the drawn loser gets
  `duplicate_claim`, `work_without_claim` and a board-error release: 3 refusals, so it is stopped (D3).
- `steal` under `code`: all four agents stopped, `episode_stopped`, 12 refusals. This matches prereg section 6, which
  says the 20-total stop is unreachable.

**One accepted work per agent: no path found.**
- The parser admits at most one `work` per reply, and only in round 2. The harness sets `agent`.
- The deferred step carries only releases.
- Across every probe episode, `extra_work_events` was 0.

Crafted invalid logs against the three scorers (`p5_scorers.py`, real Lean 4.35.0):
- two works by one agent, five agents, `agent` null twice, the same task twice, `type` instead of `action`, and
  `rejected: 0` each gave `valid = false`, `Y = None`;
- all three scorers agreed on all 15 logs, with no disagreement;
- the driver stops on `void_invalid_log`.

### (2) Model identity

Not enforced by the loop: see R-2. A missing or empty model voids: `""`, `None` and `0` gave `void`, "response names
no model".

### (3) HTTP and transport

Raw-socket and fake-server probes through `run_batch` (`p3_http.py`, `p7_headroom.py`):

| Case | Result |
|---|---|
| 200 cut short; bad status line; connection closed twice | `infrastructure_abort`, re-run once under `r1`, batch completes |
| 3 cut-short episodes | `stopped:transport` (`transport_aborts`) after the third |
| a 200 with a list-valued model | `void`, `stopped:void_model` |
| a 200 with no `stop_reason` | malformed `bad_stop_reason`, turn lost |
| `max_tokens` 3 times on 1 set | malformed `truncated`; `malformed_overall` stop (more than 2 of 24) |
| 400 / 429 / 5xx / model mismatch / no model | covered by `test_ep1` (`http_400` at once, never re-run; and so on); passes |
| full 20-set schedule with two episodes aborting on their 8th call | 499 calls including the canary, 60 cells complete, `inconclusive`, 922,532 tokens; no `cap` or `no_rerun_calls_left` stop |

- In every probe, no ledger id was charged or reserved twice.
- Aborted attempts stay as open reserves at their worst case.
- **Exception:** the canary path (R-4).

### (4) Driver

- **Arm order.** Seeded per task block from `Random(f"ep1:order:{s}")`, and recorded in `schedule.json` and in each
  record's `block_order`. Mutation M11 tests that it is shuffled.
- **Pairing.** The same `alloc.gen(s, split)` and board seed `s` in every arm, with `taskset_id` and
  `taskset_sha256`.
- **Three-scorer gate.** An `alloc2` or Lean disagreement voids the episode and stops the batch.
  - Lean `INVALID` or `REJECTED` does not void: **R-1**.
- **Void-on-invalid:** stops the batch.
- **Card check gate.** `_preflight` refuses without a review recording the card sha256, and checks the twin's byte
  match; see R-7.3.
- **Floor and oracle bracket:** present; its floor condition is too weak (R-3).
- **"Resolved".** Read from the structured `summary["contrasts"][...]["resolved"]`, never from the rendered text.

### (5) Prompts

Probe `p4_prompts.py`: 1,920 prompts, heldout 0 to 19, 4 scripts, 3 arms.
- With the same replies, `none` and `code` are byte-identical.
- `play` equals `none` once the card is swapped for the twin. Card and twin are 237 bytes each.
- All prompts are ASCII.
- **No gold.** No task's `expect` appears in any prompt, apart from operands.
- **No predicate words** (`expect`, `distinct`, `valid`, `unique`, `collision`, the name rule). The one exception is
  "duplicate" in the `code` status lines (see Notes).
- The largest body is 1,476 bytes (R-7.1).

### (6) Dry run

`PYTHONPATH=src python3 -B -m murmuration ep1 dry-run --out-dir <scratch>`, run in the copy with the real Lean. It took
24 s and exited 0.
- **Verdict `GREEN`.** Stamp: `FAKE: loopback fake server; not evidence about any model`. The `ep1` report is also
  stamped FAKE.
- **Canary:** complete.
- **Pilot:** 15 episodes, 120 calls, complete.
- **`ep1`:** 60 episodes, all `complete`, 481 calls including the canary, 892,470 tokens, USD 0.147 (fake prices);
  reason `inconclusive`.
- **Bracket:** floor `Y = [0.25, 0.25, 0.25]`, oracle `[1, 1, 1]`.
- **Lean:** `OK` on 60 of 60.
- **No stop fired in the dry run.** The fake responder plays the floor. Every stop listed under (3) fired only in my
  probes and in the unit tests.

### (7) Suite and mutations

**Full suite**, 10 runs on the snapshot copy: `PYTHONPATH=src python3 -B -m unittest discover -s tests`, 5 at a time.
- **10 of 10 OK: 673 tests each, 2 skipped, 425 to 461 s.**
- The skips have nothing to do with EP-1: `test_t7_gen` needs torch, and `test_t7_samples` has no data.
- The Lean tests ran; none was skipped.
- `train/*.py` was copied (read only) into the copy so that the `t7` tests could import it. A first serial run without
  it had 3 import errors and nothing else.
- The real `runs/spend` did not exist before or after.

**Mutations.** Each was applied to a copy and judged by `tests.test_team_claude` plus `tests.test_ep1`. M00 is the
unmodified baseline.

| # | Mutation (one safety line) | Result |
|---|---|---|
| M00 | baseline, no change | GREEN |
| M01 | a missing model is not voided in the loop | RED |
| M02 | duplicate action types allowed | RED |
| M03 | unknown task ids admitted (only the regex is checked) | RED |
| M04 | `stop_reason` `max_tokens` accepted | RED |
| M05 | execution in call order, not seeded order | RED |
| M06 | `HTTPException` re-raised from the loop | RED |
| M07 | the HTTP-400 stop removed (400 becomes a re-run) | RED |
| M08 | the third transport abort no longer stops (`>= 4`) | RED |
| M09 | an `alloc2` disagreement ignored | RED |
| M10 | the card preflight skipped | RED |
| M11 | arm order not shuffled | RED |
| M12 | **floor responder scores 0.5 (a1 works task 1)** | **GREEN: survives** (R-3) |
| M13 | **the driver's `unbilled_unknown` stop removed** | **GREEN: survives** |
| M14 | the invalid-log stop removed | RED |
| M15 | a re-run reuses the original `id_tag` | RED |

**13 of 15 RED.**
- **M12** proves R-3.
- **M13 has no test.** The stop is close to unreachable, because a failure without a successful retry ends as an abort,
  which returns before the check. It still needs one test, or should be removed as dead code.

## Must be done before the freeze

1. **R-1:** a Lean `INVALID` or `REJECTED` voids the episode. Change the `test_ep1` stub, and add the void test.
2. **R-2:** the loop voids a returned model other than `caps["model"]`. Add a scripted-client test.
3. **R-3:** the floor bracket requires `Y == 0.25` (kills M12). Add a test for the `unbilled_unknown` stop, or delete
   it (M13).
4. **R-4:** the canary catches `HTTPException`. Add a test. This is required **before the canary**.
5. **R-5:** the owner settles `episode_stopped` (scored or censored); the driver and the analysis then agree.
6. **R-6:** the 12-set rule, the `hi < 0.20` label and kill read-off, and the exploratory labels in `analysis.py`.
7. **R-7:**
   - put 1,476 bytes in the prereg;
   - G0-2R2 covers `backend_claude.py`;
   - the card review is re-confirmed against the current `alloc.py`.
8. Re-run this gate at a **fixed SHA** (commit first), then G0-2R2, then the canary.

Scratchpad artefacts:
- probe scripts: `.../scratchpad/g1br/probes/`;
- outputs: `p2.out`, `p3.out`, `p5.out`, `p7.out`, `dry1.out`, `mut.out`, `suite_*.log`.
