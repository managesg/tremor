# Gate G1b-R2: the G1b re-gate plus the pilot-1 fix round (independent adversarial verification)

2026-11-20. Opus 5.5, verifier. I wrote none of this code. I read the repository and made no change to it except this
file. I made no provider call, used no key, read no `.env*` file and used no GPU (`CUDA_VISIBLE_DEVICES=''`). Every
experiment ran in a scratch copy of the tree:
`/tmp/claude-1000/-home-adelmar-SeaBridgeAI-manageesg-backend/6d6e3057-52a5-4529-b1fd-fc0a5bee49e3/scratchpad/g1br2`.

> **Instrument validation only.** Every number here comes from scripted clients, the loopback fake server
> (`tests/fakeclaude.py`) or a loopback raw socket. None of it is evidence about any model.

**Subject.** HEAD `b4a820e` plus the uncommitted working tree. sha256 prefixes of the files under test: `spend.py`
c7ec57de, `backend_claude.py` 1471467557, `team_claude.py` 1bb4ed66, `ep1.py` 412475a1, `analysis.py` c836f53b.
At the end, `src/`, `tests/` and `prereg/EP1.md` were byte-equal to the tested copy.

**Real ledger.** Unchanged before and after:
- `runs/spend/canary.jsonl` 45aaffae...;
- `runs/spend/pilot.jsonl` 38bd2f02...;
- the 7 files of `runs/ep1-live/`, combined hash aea4671e....

## Verdict

**ACCEPTED-WITH-NOTES.** The code closes G1b-R defects R-1 to R-6, and every pilot-1 safety claim I was asked to
refute holds. The suite is green, and all 20 mutants on the new safety lines were killed.

**May pilot 2 run? Not yet. It may run once these three conditions are met; none of them is a code defect:**
1. **Change 14 versus prereg 16b (N-1 below).** The owner, or the orchestrator, settles change 14, and prereg
   item 16b is made to match the build. As built, pilot 2 runs the old shared task order.
2. **Spend approval.** The owner gives a new ask and his "confirm" for the USD 0.25 `pilot2` batch (prereg 16, 16b).
3. **G0-2R2.** It re-hashes `spend.py` and `backend_claude.py`, since both changed.

## A. G1b-R defects, one probe each

| G1b-R | Probe (scratch copy) | Result |
|---|---|---|
| R-1 Lean `INVALID`/`REJECTED` | Full driver run with Lean stubbed to return `INVALID` or `REJECTED` on the 3rd scorer call, and with one Lean field changed. Also the CLI dry run with Lean absent. | `INVALID`: `stopped:scorer_disagreement`, detail `scorer_invalid`, at that episode. `REJECTED`: that episode is voided (`scorer_rejected`) and the batch goes on to `inconclusive`. A field disagreement voids the episode and stops the batch. With Lean absent, `ep1` stops before any episode (`scorer_invalid`) and only the canary is charged. **Closed.** |
| R-2 loop model check | A scripted client returns `claude-sonnet-5-5`, `claude-opus-5-5`, `claude-haiku-5-5-20261101`, `CLAUDE-HAIKU-5-5`, `" claude-haiku-5-5"`, a list, `None` and `""`. The real `ClaudeClient` runs through fakeclaude, with the wrong id on the episode calls only. | Scripted client: Sonnet, Opus, the list, `None` and `""` each void (no `TypeError`). The three canonical-key variants pass the loop, as prereg change 2 specifies. Real client: every variant gives `stopped:void_model`/`void_model_mismatch` after 1 episode call. For Sonnet the stop is `stopped:cap`/`Overspent` (the charge at Sonnet price crossed the reservation); it still stops after one call. **Closed.** |
| R-3 floor bracket | CLI dry run | `floor_Y` [0.25, 0.25, 0.25] and `oracle_Y` [1.0, 1.0, 1.0], checked against expected `{floor: 0.25, oracle: 1.0}`. The dry run is `GREEN`. **Closed.** |
| R-4 cut-short canary | A raw socket sends a 200 with `Content-Length: 900` and 13 bytes. | `stopped:transport`, `call_failed:IncompleteRead`, `canary.json` written, canary stop recorded, nothing escapes. **Closed.** |
| R-5 stopped episodes | `analysis.summarise` on the dry-run records with 6 episodes set to `episode_stopped` | Every arm keeps 20 episodes and 20 sets. `all_agents_stopped` = 2 per arm. No set is dropped (intention-to-treat). **Closed.** |
| R-6 analysis rules | `summarise` on 11 sets and on 12 sets | 11 sets: every contrast reads `incomplete: not shown` and the HDI is empty. 12 sets: labels are shown, `exploratory` is set on `code_none` and `code_play` and not on `play_none`, and `smaller_than_effect_of_interest` is computed. **Closed.** |
| R-7.1 largest request | Wire bodies of every call: heldout seeds 0 to 19 and train seeds 0 to 5, 5 conditions, 1,040 calls, my scripted replies | 1,476 bytes with the thinking field and 1,442 without. The prereg's estimate of about 1,510 with the field (1,476 + 34) stands as the upper reading under G1b-R's random script. Both are under the 2,000-byte cap. |

## B. Pilot-1 fix round: the claims I tried to refute

| Claim | Evidence | Holds? |
|---|---|---|
| Every request body carries `thinking: {type: disabled}` and `max_tokens` 300 | fakeclaude answers 400 to any body without the field. The CLI dry run (canary, 15 pilot, 30 `pilot2`, 60 `ep1` episodes, 841 requests) ends `GREEN` with no 400. My `pilot2` run against a copy of the real ledger: 240 of 240 bodies carry the field, and `max_tokens` = {300}. The canary body carries it too. | Yes |
| A missing field fails a test | Mutants M01 (client payload), M02 (team_claude hashed body), M03 (canary body) and M04 (`adaptive`) are each killed, by 2 to 79 failing tests | Yes |
| A thinking block voids and stops | fakeclaude returns a `thinking` block first, a `redacted_thinking` block first, or a `thinking` block last. Each gives `stopped:void_model`, detail `void_thinking_block`, after 1 request; the call is reserved and charged and the batch stop is written. A body stripped of the field (patched `json.dumps`) gives `stopped:http400` after 1 request. | Yes |
| Per-agent task order is OFF by default, and prompts are byte-identical to HEAD | All 1,040 prompts (sha256 of system + user) from HEAD's `src` and from the working tree match, under the same scripted client. An explicit `shared` equals the default. | Yes |
| ...and arm-independent when on | With `per_agent`: across 208 (set, agent, round) keys, 0 orders differ between arms. In 0 of 52 (set, round) pairs do all four agents share one order. The seed is the prereg's `ep1:view:{split}:{seed}:{agent}`. M16 (arm added to the seed) is killed. | Yes |
| `pilot2` USD 0.25 / 260 calls / 598,000 tokens | `spend.BATCH_SPECS`. M09, M10 and M11 are killed. | Yes |
| Opens only after a completed canary, and never after any canary stop | Real-ledger copy with no canary: refused at open, 0 requests. A `transport` stop appended after `complete`: refused at the first reserve (`BatchStopped`), 0 requests. M12, M13 and M20 are killed. | Yes (N-3) |
| A stopped pilot 1 does not block pilot 2 | Real-ledger copy (pilot stopped `void_model`): `pilot2` runs 30 episodes and 240 calls to `complete` | Yes |
| The `p2` prefix prevents id reuse with pilot 1 in the same real directory | Real-ledger copy: ids are `ep1p2-*` and `ep1p2sc/kw-*`, every attempt is 0, and there is no `events.jsonl`. Negative control (`ID_PREFIX={}`): no id is reused, because the directory-wide check in `team_claude` still refuses it. But 11 cells lose attempt 0 and write fake `interrupted` events. M14 is killed. | Yes (N-4) |
| Worst case across all batches is at most USD 10, including spend so far | Caps: `ep1` 5.00 (the canary included) + `pilot` 0.50 + `pilot2` 0.25 + `ar1` 3.00 = **8.75**. `HARD_CAP_USD` 10 binds program-wide. Charged so far: about USD 0.016. No charged ledger exists outside `runs/spend/`. | Yes |
| Spend refusals unchanged | The diff to `spend.py` is the one `pilot2` line plus its comment. `reserve` and `_check_batch` are untouched. | Yes |

**Tests.**
- Full discover (`PYTHONPATH=src python3 -B -I -W ignore -m unittest discover -s tests`): **724 tests, OK, 22 skipped,
  265.7 s.**
- Targeted run (`test_team_claude`, `test_ep1`, `test_spend`, `test_backend_claude`, `test_analysis`): 252 tests, OK.

**Fake dry run** (`python3 -m murmuration ep1 dry-run`, Lean toolchain copied into scratch): verdict `GREEN`.
- Canary `complete`; `pilot` `complete` with 15 episodes; `pilot2` `complete` with 30 episodes and `ep1p2` ids;
  `ep1` `inconclusive` with 60 episodes.
- The third scorer gave `OK` on every one of the 105 episodes.

**Mutants: 20 of 20 killed** (M01 to M20). They cover:
- the three thinking sites, the value of the field, the thinking-block void, `redacted_thinking`, the client's block
  types and the void label;
- the `pilot2` USD, call and token caps, `requires_settled`, `settled_reasons` and `parent`;
- the driver's canary gate, the `p2` prefix, the task-order default, the arm in the seed, the `caps.thinking` check
  and the 300-token output cap.

## C. Non-Haiku models

The Claude API reference (claude-api skill, models cached 2026-11-03) gives three rules:
- Haiku 5.5 accepts `disabled` at effort `high` or below, and its default is `medium`.
- Sonnet 5.5 and Opus 5.5 return a 400 for `disabled`.
- Sonnet 5.5 turns thinking off with `between_tools`.

So the implementer's statement is correct.

What uses another model:
- No configured batch does. Pilot, `pilot2`, the canary and `ep1` are Haiku (`team_claude.CAPS`, `ep1.MODEL`).
- `ar1` exists only as a cap in `BATCH_SPECS`. No code opens it, and no auto-research loop calls `ClaudeClient`.
- The one non-Haiku path is `runner._claude` (W1-10), whose default is `claude-sonnet-5-5`. It is unbatched, opt-in
  and outside EP-1. Because `ClaudeClient.call` now always sends `disabled`, that path would get a 400. It also sends
  `temperature` 0.0, which Sonnet 5.5 already rejects, so it was broken before this change.

**Not a blocker for pilot 2 or EP-1. It is a blocker for any future `ar1` or W1-10 run on Sonnet or Opus:** the
thinking field has to depend on the model before such a run.

## Notes

- **N-1 (gates pilot 2): change 14 is specified for pilot 2 but cannot reach it.**
  - Prereg 16b says pilot 2 "tests the changed instrument (changes 13 and 14)".
  - The driver passes only `caps={"id_tag": tag}`, and no CLI flag sets `task_order`. So `pilot2` runs `shared` (my
    real-ledger run recorded `task_order` = {`shared`}).
  - Criterion 5 (mean `Y_none` from 0.30 to 0.80) is then no screen: herded `Y` is 0.5 or 0.75, so it passes trivially.
  - Running pilot 2 as built and turning change 14 on later would need a third pilot, which needs a new owner ask
    under 16b.
  - **Before pilot 2, choose one:**
    - (a) The owner confirms change 14. Then the driver passes `task_order="per_agent"` for `pilot2` (and later `ep1`),
      with a test, and it is re-gated. It is one line plus a test.
    - (b) Change 14 is deferred. Then 16b is amended to "tests change 13 only", and criterion 5 is marked
      uninformative under the shared order.
- **N-2.** Change 14 is still recorded as "Not yet in the code". The code now holds the option, default off, so the
  prereg row should say "option built, off by default, awaits the owner".
- **N-3.** If the canary completed and a later stop was appended, `ep1._check_open` lets `pilot2` through and the
  ledger refuses it at the first reserve. That costs 0 requests, but it writes a `pilot2` stop `cap`, which kills
  `pilot2` permanently and under the wrong reason. Optional: make `_check_open` use the same rule as the ledger.
- **N-4.** Without the `p2` prefix, the directory-wide id check still prevents any reuse. The prefix avoids lost
  attempts and fake `interrupted` events. The test `test_pilot2_after_a_stopped_pilot_runs_with_its_own_episode_ids`
  pins this behaviour.
- **N-5.** The thinking-block scan sees the first 16 block types. A thinking block placed after 16 other blocks would
  pass unseen. This is unrealistic for 300-token replies.
- **N-6.** `CAPS["thinking"]` is the same dict object as `bc.THINKING_OFF`, so a caller that mutated it in place
  would change the module constant. The client sends `dict(THINKING_OFF)`, a copy, and `_check_caps` compares by value.
  Low risk.
- **N-7.** In the real-client run, a Sonnet id stops through `Overspent` (a cap), not through `void_model_mismatch`.
  It is still one call and a stop. Reports that count model voids should also read the cap stops.
- **N-8.** The block types are recorded per call (`turn.block_types`), as the diagnosis asked, so criterion 1 can be
  read from the logs.

**Not checked:**
- the real API's response to `disabled` with temperature 1.0 on Haiku 5.5 (the first paid call of pilot 2 tests it);
- the Console figures;
- the G0-2R2 hashes;
- the card-review re-pin (R-7.3);
- `docs/WORKPLAN-CURRENT.md` beyond the lines quoted;
- the analysis two-row refusal read-off was not probed (it is covered by `test_analysis`, which passed).

verified: b4a820e (plus working tree) 2026-11-20
