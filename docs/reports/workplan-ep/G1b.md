# Gate G1b (model-facing loop, B2): independent adversarial verification

2026-11-20. Opus 5.5, fresh context. Read-only on the repo except this file. No provider call, no key, no `.env*`,
`train/`, `runs/` or `data/` touched. Every mutation ran on a temporary copy in the session scratchpad. All tests and
probes ran with `CUDA_VISIBLE_DEVICES=''` and `python3 -B`. Network use: 127.0.0.1 only (fake server and a raw socket).

> **Instrument validation only.** Every number below comes from scripted responders or the loopback fake server.
> None of it is evidence about a model.

**Subject.** HEAD `36bab4b` plus the uncommitted `team_claude.py`, `prompts/ep1/{system,turn}.md`,
`tests/test_team_claude.py` and the modified `backend_claude.py`, `spend.py`, `router.py`, `enforce.py`.

## Verdict

**REJECT for the freeze. The loop's mechanics are mostly sound, but EP-1 must not be frozen on it as built.**

- The deciding defect is **G1b-1**. The loop accepts exactly one action per reply, but `prereg/EP1.md` section 6
  allows `claim`, then `work`, then `release` in round 2. This changes what every arm measures. It biases the
  confirmatory `Y_play - Y_none` against the hypothesis, because card A's own instructions cannot be carried out.
- Four more defects can crash an episode or mislabel it without leaving a record (G1b-2 to G1b-5).

What holds, verified by probe:
- the strict JSON parser, apart from the gaps listed below;
- the harness-set `agent`;
- the stale snapshot per round;
- card versus neutral twin as the only prompt difference;
- the usage void and the returned-model void;
- retry accounting in the ledger;
- floor and oracle in every arm on 30 task sets.

## Defects, ranked

### G1b-1 (blocks the freeze). One action per reply does not match the round rules in prereg section 6

The prereg says round 2 accepts, in order and each optional, one `claim`, one `work` and one `release`. It also says
"a round-1 loser can send `claim` then `work` in round 2". The code (`ROUND_TYPES`, `parse`) and `ALLOWED_TEXT[1]`
allow exactly one action per reply. Measured with scripted responders on set `h50`:

| Scripted behaviour | none | play | code | both |
|---|---|---|---|---|
| Round 1: all four claim t0. Round 2: each works its own task (`loser_works`) | 1.00 | 1.00 | **0.25** | **0.25** |
| Round 1: all four claim t0. Round 2: losers re-claim a free task, as card A says (`loser_reclaims`) | 0.25 | 0.25 | 0.25 | 0.25 |
| Round 1: oracle claims. Round 2: `release done` (card A's last sentence) | 0.00 | | | |

What this does to each measure:
- **`code` and `both`.** Only a round-1 claim winner can ever score. The "enforcement is not free" path in the prereg,
  where a loser claims and then works, cannot be taken. So `Y_code <= distinct round-1 winners / 4` by construction.
- **`play`.** Card A says to pick a different task if one is held, to claim before working, and to release when done.
  A card-following round-1 loser spends its only round-2 action on `claim` and loses its slot. A card-following
  winner that releases instead of working loses its slot. A `none` agent with the neutral twin just works. **The
  format penalises adherence to the card, so `Y_play - Y_none` (the one confirmatory comparison) is biased toward
  the null.**
- **False-done rate.** Work and release can never both happen for one agent, so every done release is false-done
  by construction. Probe: release-only gives `trace_false_done = 1.0`, and the oracle gives `None`. The read-off is
  degenerate.

**Recommendation: change the code, not the wording.** No prereg wording can make the card's instructions executable
under one action per round.
- A round-2 reply becomes one JSON array of 1 to 3 actions. Types are strictly in the order claim < work < release,
  each at most once. A bare object is accepted as a list of one.
- The actions execute in order through `router.act`. The first refusal or board error ends the turn, and later
  steps are not sent.
- Round 1 stays a single `claim` or `pass`.
- `system.md`, `turn.md` (`ALLOWED_TEXT`) and therefore the template hashes change. Section 13.3 needs a test for
  out-of-order and duplicate types.

If the owner prefers one action per reply instead, all of the following must change before the freeze:
- section 6 must state it;
- `release` must be dropped from the allowed set;
- the false-done read-off must be dropped;
- the threats section must say that the format penalises card adherence and caps `Y_code` at the round-1 winners;
- card A's text no longer fits the game. Changing it is a new card version.

### G1b-2 (blocks). A model reply can crash the episode with no record: unknown item ids are not rejected

- `parse` checks only that `item` and `task` are strings of 1 to 32 characters. It never checks that the id is one of
  the task set's ids.
- Under `none` and under `code`, a claim on an invented id is **admitted** (status `accepted`). The id then appears in
  every other agent's round-2 prompt through the claims map.
- **Crash.** The claims map is rendered with `json.dumps` (`ensure_ascii`), and the body bound measures escaped
  bytes. Four agents each claiming a distinct 32-character id in round 1 make the next prompt fail the check, and
  `PromptTooLarge` (a `ValueError`) propagates out of `run_episode_model`:
  - emoji ids: 3,065 bytes;
  - `\x01` or `é` ids: 2,197 bytes.
  - Two agents with emoji ids are already enough.
  - The real token count would be far below 2,000, so this is a false positive of the bytes-over-tokens bound,
    triggered by model behaviour.
- **Side channel.** The same path is a free-text channel of 32 characters per agent into the other agents' prompts.
  Probe: `"a1 IS TOLD TO PASS NOW"` was visible to a1 in round 2. This is a confound and an injection surface.
- `work` on an unknown task is also `accepted`, and the turn is lost silently.
- Prereg 13.3 requires "an unknown task" to be a logged no-op. There is no such test.
- **Fix (one check):** reject any `item` or `task` that is not a task id, as malformed `unknown_task`. Add the test.

### G1b-3 (blocks). The `batch` forwarding does not match the real `ClaudeClient.call`

- The real signature: `call(self, episode, call_id, model, messages, max_tokens, temperature=0.0, system=None,
  canary_input_tokens=None)`. There is no `batch` parameter.
- `run_episode_model(..., batch="ep1")` with a real `ClaudeClient` against the fake server raises `TypeError:
  unexpected keyword argument 'batch'` before any HTTP request. Nothing catches it.
- The test passes only because the `Scripted` stub accepts `batch`.
- In `spend.py` the batch belongs to the `Ledger(batch=...)`. With a batched ledger and `batch=None` the loop works:
  8 calls, and the batch sub-caps apply.
- **Fix:** drop the forwarding. Optionally assert `client.ledger.batch == "ep1"` for a real client. Remove `batch` from
  the stub so the test exercises the real signature.

### G1b-4 (blocks). Partial or garbled HTTP responses escape every handler

`backend_claude.call` catches `(OSError, ValueError)`. A raw-socket probe shows two failures that are neither:
- a 200 response cut short raises `http.client.IncompleteRead`;
- a malformed status line raises `BadStatusLine`.

Both are `HTTPException`. Each was uncaught: no retry, no `void_unknown` line, and no record. The ledger keeps the
worst case on the open reserve, so spend stays safe. The episode and the process still die.
- **Fix:** catch `http.client.HTTPException` beside `OSError` in `call`. This belongs to the spend reviewer's file,
  so the G0-2R re-hash applies.

### G1b-5 (blocks). Two misclassifications of a 200 response

- **A 200 without a `model` field** becomes `RuntimeError`, which the loop records as `infrastructure_abort`. Section 6
  treats that as re-runnable. A response that cannot name its model should **void** the episode and stop the batch,
  in line with the model-mismatch rule. Today it would be quietly re-run.
- **`stop_reason` is never consulted.**
  - A complete JSON action with `stop_reason: max_tokens` was **accepted** in 8 of 8 turns (`Y = 1.0`).
  - The same with `stop_reason: refusal` was also accepted. It was counted in `model_refusals` but scored as play.
  - Prereg 13.3 requires "a declined request" to be a logged no-op, and a truncated reply must be malformed.
  - **Fix:** any `stop_reason` other than `end_turn` makes the reply malformed (`truncated` or `declined`). Add the
    tests.

### G1b-6 (fix before freeze). The board seed does not order claims under enforcement

- The prereg says that if two agents claim the same free task, "the second in seeded order is refused".
- The probe disagrees. On set h0, `floor` across board seeds 0 to 14:
  - the round-1 winner varies under `none` (a0, a1, a2, a3);
  - it is **always a0** under `code`.
- The claim lock refuses in call order, and the call order is fixed at a0 to a3 in both rounds.
- Agents are exchangeable copies of one model, so `Y` has no bias in expectation. Still, the prereg text is false
  for `code` and `both`, and position confounds per-agent read-offs.
- **Fix:** either shuffle the call order per round from the board seed, or change the wording to "call order, fixed
  a0 to a3; first come under the lock".

### G1b-7 (fix before freeze). The `model` label can be spoofed

- `_is_real` checks `isinstance(client, bc.ClaudeClient)` plus `base_url`.
- A `ClaudeClient` subclass that overrides `call` with a script, and sets `base_url = "https://api.anthropic.com"`
  without `__init__`, gets `instrument_validation: false, evidence: "model"`. Probe: `Sub()` returns `model`. The
  test's own `RealStub` relies on this.
- A plain duck-typed object with the same `base_url` is correctly labelled `fake`.
- **Fix:** require `type(client) is bc.ClaudeClient`, unmodified `call`, and a constructed instance (`_key` set). Then
  reach the real-label branch in the test some other way (for example, monkeypatch `_post`).

### G1b-8 (notes)

- **The refusal stop cannot fire in EP-1.** Each agent has 2 turns, and each turn begins with an admitted `read`, which
  resets that agent's run. 3 consecutive refusals are impossible, and the team maximum is 8 refusals against the 20
  cap. Prereg 12 ("three or more episodes ended by the refusal stop") and the "open defect" in 13.4 are dead text.
  Say so in the prereg, backed by one test.
- **Infrastructure re-runs need a new `id_tag`.** A re-run with the same seeds reuses the call ids, and the ledger
  refuses it: `spend_stop:SpendError`, probe B. The batch driver must pass `id_tag` (for example `-rr1`) and record
  it.
- **Cache creation.** A batched ledger stops on `cache_creation_input_tokens > 0` (probe: `spend_stop:BatchStopped`
  after 1 call). `test_team_claude` line 311 runs an unbatched ledger that accepts 160 cache-creation tokens. That is
  correct for an unbatched ledger, but the EP-1 driver must always be batched.
- **The record carries no `orders` read-offs and no board log** (only `board_head` and `board_events`).
  `orders.compute(lines, trace)` cannot be rerun from the JSONL for the executed claim-collision rate. Put `orders`
  in the record, as `team.run_episode` does.
- **The record's `template_sha256` is re-read from disk at the end of the episode**, not taken from the bytes used.
  Hash the `tpl` bytes that were loaded. The per-turn `prompt_sha256` is correct.
- **The status line shows the router reason with the predicate prefix:** `refused: A:duplicate_claim:<item>`. This
  is part of the code treatment (threats, section 14). It leaks the label "A", not the gold.
- **Hard-coded team size.** `system.md` says "a team of four", but `run_episode_model` accepts other `n_agents`. That
  is harmless for EP-1.
- **Retries are immediate,** with no backoff and no `Retry-After`.

## Answers to the brief, item by item

### (1) Parsing

The table lists probes run directly against `parse`, unless the row says otherwise.

| Input | Result |
|---|---|
| JSON + trailing prose | `extra_text` |
| Two objects | `multiple_actions` |
| A list | `multiple_actions` / `not_object` |
| Duplicate keys, including `{"type":"pass","type":"claim"}` | `not_json` (the `_pairs` hook) |
| Escaped key `{"type":"pass"}` alone | valid. It *is* `type`; correct |
| BOM prefix | `not_json` (`strip` keeps U+FEFF) |
| `NaN` / `Infinity` | `not_json` |
| Nesting 300 deep | `not_json` (`RecursionError` caught) |
| `answer` above 10^6, a float or a bool | `bad_field` |
| Comments, code fences | `not_json` |
| A reply over 600 bytes | `oversize` |
| A reply naming any agent | `agent_field` (malformed, never `identity_spoof`) |
| Unknown action type | `bad_type` |
| `work` or `release` in round 1 | `type_not_allowed_in_round` |
| A claim on an id not on the board | **accepted** (G1b-2) |
| `stop_reason` `max_tokens` or `refusal` with valid JSON | **accepted** (G1b-5) |
| `pass` | no-op, status `no-op`, not counted as malformed |
| `release` without work | admitted, scores nothing, counted false-done |

One-action deviation: see G1b-1. Code change recommended.

### (2) Prompt

- **Card is the only difference.** On 15 train plus 15 heldout sets, oracle in both rounds:
  - `none` equals `code` and `play` equals `both`, byte for byte;
  - `none` and `play` differ only by the card (237 bytes against 237 bytes).
- **No gold.** `expect` and the naming rule are never in the text.
- **Board view.** Only the committed claims map is shown; posts are not. Same-round claims are hidden.
- **Hashes.** Template hashes are in every record (see the note in G1b-8), with a per-turn `prompt_sha256`.
- **Worst-case size, round 2, 4 agents, 6 tasks, a 40-character refusal status:**
  - real ids: request body **1,396 bytes**, prompt text 1,196 bytes (UTF-8);
  - adversarial 32-character ASCII ids: 1,500 bytes body, 1,300 bytes text;
  - non-ASCII ids: up to 3,065 bytes body. Only reachable through G1b-2.
- **Caps.** The per-call cap is 2,000 tokens; `spend.PER_CALL_INPUT_TOKENS` is 2,000, applied to the body *bytes*.
  The bytes-versus-tokens question is left to G0-2R.

### (3) Labels and the real path

**Labels.**
- A scripted responder and the fake server are stamped `instrument_validation: true, evidence: "fake"`, with the
  `FAKE` label.
- A real `ClaudeClient` on api.anthropic.com gives `evidence: "model"`. This branch is reached only through a stub
  (see G1b-7).

**Voids.**
- A returned-model mismatch voids the episode, both through the stub and through the real client against the fake
  server.
- A missing model gives `infrastructure_abort`, not a void (G1b-5).

**What a real run does that no test exercises:**
- the `https` host check and the pilot ledger directory;
- real headers: `x-api-key` and `anthropic-version: 2023-06-01`; urllib's default User-Agent;
- TLS;
- whether `claude-haiku-5-5` accepts an explicit `temperature` (unchecked; a 400 would become `infrastructure_abort`
  on every call);
- multiple text blocks, which are concatenated;
- the 120 s per-request timeout, cut down to the episode's remaining 600 s.

**Errors and accounting:**

| Case | Behaviour |
|---|---|
| 429 or 529 | One immediate retry, which counts as a second ledger call (reserve `#r1`). The probe 429 then OK gives 9 ledger calls for 8 loop calls. |
| Two failures | `infrastructure_abort`. Prereg 12 says the batch stops; prereg 6 calls it re-runnable. Settle which wins. |
| Failed attempts | Their worst case stays in `unbilled_usd`. |
| 400 | No retry. `infrastructure_abort`. |
| Partial body or bad status line | Uncaught (G1b-4). |

There is no idempotency key. A retry after a timeout may be billed twice; the ledger counts both at the worst case.

### (4) Floor and oracle through the full loop

- `alloc` has a single task family (`sum a b`). I ran both splits, seeds 0 to 14, all 4 arms, with the board seed
  equal to the set seed: **floor 0.25 and oracle 1.00 in all 240 episodes**. All ended `complete` with 8 calls and 0
  malformed replies. No violation executed under `code` or `both`.
- **Pairing.** The `taskset_sha256` is the same across arms in every set. A cluster id is available as
  `taskset_sha256` together with `seed`, but there is no explicit set index, and the episode id appears only inside
  each `call_id`.
- **Independence across arms.** There is no API seed, so each arm draws its own model sample: independent within a
  set, given the shared board seed.
- **Arm order.** The seeded arm order and the batch driver do not exist yet.

### (5) Suite and mutations

**Full suite.** I ran `PYTHONPATH=src python3 -B -m unittest discover -s tests` 10 times on the live tree:
- **10 of 10 OK**, 1 skipped, 136 to 162 s per run;
- the first 8 runs had 482 tests and the last 2 had 486. Another session was adding tests while I ran, so the tree
  is not a fixed SHA. Re-run the suite at the freeze SHA.

**Mutations.** Each was applied to a temp copy of `src`, `tests`, `prompts` and `practices`, and judged by
`test_team_claude` plus `test_team`. The baseline copy is GREEN.

| # | Mutation | Result |
|---|---|---|
| M01 | A reply carrying `agent` is accepted | RED |
| M02 | Trailing text is accepted | RED |
| M03 | Duplicate keys are accepted | RED |
| M04 | The round rule is off (`work` allowed in round 1) | RED |
| M05 | Every client is labelled real (`evidence: "model"`) | RED |
| M06 | The usage-over-cap void is off | RED |
| M07 | The pre-send prompt-size check is off | RED |
| M08 | **The gold answers are appended to the system text** | **GREEN: survives** |
| M09 | The status line always reads `accepted` | RED |
| M10 | The temperature is not forwarded (the client default 0.0 is used) | RED |
| M11 | The per-episode call cap is off | RED |
| M12 | A returned-model void is ignored | RED |
| M13 | The `none` and `code` arms get the real card | RED (13 failures) |
| M14 | A malformed reply is not counted as malformed | RED |
| M15 | The round-2 snapshot is empty | RED |
| M16 | `NaN` and `Infinity` are accepted | RED |

**15 of 16 RED.**

M08 survives because the only gold-leak test checks for the literal word `expect`. Add a test that no task's
`expect` value appears in the system text or the turn text, unless it is one of that task's operands.

## Must be done before the EP-1 pre-registration may be frozen

1. Fix G1b-1 (code: ordered round-2 list), then update the templates, their hashes and the parser tests. If the owner
   picks one action per reply instead, make every prereg change listed under G1b-1.
2. Fix G1b-2: reject unknown task ids, with a test.
3. Fix G1b-3: remove the `batch` forwarding. Test against the real `ClaudeClient.call` signature, through the fake
   server and a batched ledger.
4. Fix G1b-4: catch `HTTPException`. G0-2R then re-hashes `backend_claude.py`.
5. Fix G1b-5: a missing model voids the episode; `stop_reason` other than `end_turn` is malformed. Add tests for
   truncated and declined replies.
6. Settle G1b-6, in code or in the prereg wording. Fix G1b-7, with a stricter `_is_real`.
7. Settle the conflict between section 6 and section 12 on 429 and 5xx after the retry: re-run or stop.
8. Mark the refusal-stop clauses as unreachable, with one test.
9. Put `orders.compute` output in the record. Fix the false-done definition once G1b-1 lands.
10. Build the batch driver:
    - seeded arm order;
    - one batched `ep1` ledger;
    - a fresh `id_tag` per re-run;
    - a batch stop on a model mismatch, a missing model, 429 or 5xx after the retry, the malformed thresholds, and the
      first-set check.
11. Run the 4 x 15 worst-case schedule against the fake server (B4). The existing test runs 3 x 20.
12. Build the analysis entry point and the paired-t function.
13. Add a gold-leak test that kills M08.
14. Re-run this gate on the changed loop, at a fixed SHA.

## Artefacts (scratchpad, not in the repo)

`/tmp/claude-1000/-home-adelmar-SeaBridgeAI-manageesg-backend/6d6e3057-52a5-4529-b1fd-fc0a5bee49e3/scratchpad/g1b/`:
- `probe.py` to `probe5.py` and their outputs;
- `mutate.py` and `mut_out.txt`;
- `suite_*.log` and `suite_summary.txt`.
