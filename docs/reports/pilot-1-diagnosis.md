# Pilot 1 diagnosis (instrument pilot, Haiku 5.5, 2026-11-20)

Read-only diagnosis of the run that stopped `stopped:void_model`, detail `malformed_states_check`.
It covers 11 episodes, 88 calls and USD 0.0115. No code was changed. No call was made.
Evidence: `runs/ep1-live/pilot/*`, `runs/spend/pilot.jsonl`, `src/murmuration/{team_claude,backend_claude,router,board,team,ep1}.py`, `prereg/EP1.md`.

## Summary

| # | Finding | Instrument defect? | EP-1 risk |
|---|---------|--------------------|-----------|
| 1 | Output tokens go to hidden adaptive-thinking blocks. Haiku 5.5 thinks by default, and the 300-token cap is shared between thinking and the JSON. | Yes. A wrong assumption ("no thinking parameter" taken to mean no thinking) plus missing observability. | Lost turns at rates that depend on the card. The cost and token budgets are not at risk. |
| 2 | `board_error:ValueError` is the board refusing the release from a claim loser. | No. The behaviour is designed and documented in the prereg. | It does not change Y or `valid`. Only the per-arm refusal counts and the stop counters are affected. |
| 3 | Smaller issues: herding in round 1, the pilot conditions recorded with `arm = "play"`, and a complete JSON reply lost to `max_tokens`. | Partly. | See section 3. |

## 1. Truncation: where the output tokens go

### Evidence

- **The trace hides nothing.** `backend_claude.py:170` keeps only the `type == "text"` blocks and joins them. `:175` hashes that text into `response_sha256`, and `team_claude.py:369` stores `str(text)[:1200]` as `turn["reply"]`. The longest reply is 143 characters, so nothing was cut. For all 88 of 88 calls, `sha256(turn.reply)` equals the ledger's `response_sha256`. The trace shows every text token that came back, so there is no hidden prose before or after the JSON array.
- **Output tokens are far larger than the visible text.** Round-1 replies are about 32 characters (`[{"type":"claim","item":"t0t0"}]`, roughly 12 to 15 tokens), but the median output is 88 to 110 tokens in `none`, `code`, `keyword_stuffed` and `states_check`. In round 1 the ratio is 2.75 to 3.2 output tokens per visible character, about ten times what JSON text costs. That ratio was grouped by `arm`, which folds `states_check` and `keyword_stuffed` into `play`. The one low point is `play` (card A) in round 1, with a median of 21 tokens, about the size of the JSON alone. Card A is a direct procedure ("claim one unclaimed task ... pick a different task"), and in this condition there was almost no hidden reasoning. That is a correlation; it is not shown to be the cause.
- **The truncated replies run out mid-JSON after 54 to 142 characters**, at `trace:37,46,47,107,109`. The other 250 or so of the 300 tokens were already spent before the text block.
- **Mechanism.** Claude Haiku 5.5 runs adaptive thinking when the request omits `thinking`, with effort `medium` by default. The thinking display defaults to `"omitted"`, so the response holds `thinking` blocks with empty text, and those tokens are billed as `output_tokens` and count toward `max_tokens`. The request body at `team_claude.py:308-310` and `backend_claude.py:132` sends no `thinking` field and no `output_config`. `prereg/EP1.md:308` says "No tools, no cache control, no thinking parameter", which assumed that leaving the parameter out meant no thinking. The canary used a trivial prompt and returned 4 output tokens, so it could not show this.
- **What could not be confirmed directly.** No content-block type is recorded anywhere, in the ledger or in the turns. The thinking explanation is therefore an inference, though nothing else fits: the sha equality rules out any missing text.
- Trace line 107 ends `...}]\n\n` with a complete, valid array, followed by `max_tokens`. After the array, the model went on to more text or another block, and the harness rightly refused the reply because it did not end on `end_turn` (`team_claude.py:370`).

### Root cause

The prompt does not cause this, and nothing in it asks for prose. The cause is a 300-token cap that thinking and the JSON share, combined with default-on thinking that nobody measured. A cap of 300 is ample for the JSON alone; round-2 JSON is about 45 to 50 tokens.

### Dependence on the arm

| cond (card) | calls | truncated | round-2 output, median / p90 | round-1 output, median |
|---|---|---|---|---|
| states_check | 24 | **4** (all in round 2) | **293.5** / 300 | 109.5 |
| keyword_stuffed | 16 | 0 | 255.5 / 283 | 126 |
| none (neutral twin) | 16 | 0 | 247.5 / 269 | 97.5 |
| code (twin + enforcer) | 16 | 1 | 217.5 / 269 | 88 |
| play (card A) | 16 | 0 | 203.5 / 221 | **21** |

The input size is flat, with medians of 455 to 471 tokens. The strongest evidence that the card matters is the output distribution, not the count of truncations: `play` uses 21 tokens in round 1 against 97.5 for `none`, and `states_check` has a round-2 median of 293.5, at the cap. On the counts alone, the one-sided hypergeometric p for 4 or more of the 5 truncations falling in `states_check` is about 0.015 over round-2 calls (12 of 44). That condition was picked after looking, however, and with a Bonferroni correction across the 5 conditions p is about 0.08. **The counts are suggestive, not beyond chance.** The `states_check` card spells out the scoring rules, which plausibly invites more reasoning. Card length is not the driver, since the byte lengths are matched within 20 (1,896 to 2,024 card-bytes per episode).

### Effect on EP-1 validity

- A truncated reply costs the turn, and in round 2 that is the agent's only work slot, so Y can only go down. Thinking depth plainly depends on the card: in round 1, `play` used 21 tokens against 97.5 for `none`. **The missingness is therefore correlated with the arm, and this confounds the `play` against `none`/`code` contrast.** On these numbers the bias favours `play`, which thinks less and truncates less.
- The pilot rate in the EP-1 arms is 1 of 48 calls (about 2%), well under the EP-1 stop rules (more than 48 of 480 overall, or 15% per arm, `prereg:690`). EP-1 would probably not stop, but it would carry an arm-dependent loss of 1 to 5% of round-2 turns that the plan never anticipated. Round-2 thinking sits within about 30 to 80 tokens of the cap, so the margin is thin.
- Cost and tokens are not at risk. A call uses about 465 tokens in and 168 out, or about 633 in total, at about USD 0.00013. Over 500 calls that is roughly 317k tokens and USD 0.07, against caps of 1,250,000 tokens and USD 5.

### Minimal fix options (both re-gated per `prereg` section 16 item 875)

- **A. Turn thinking off:** add `"thinking": {"type": "disabled"}` to the body in `team_claude.py:308` and to the payload in `backend_claude.py:132`. Haiku 5.5 accepts it at effort `high` or below, and the default is `medium`.
  - Expected result: no hidden tokens, so the output should be about 15 to 50 tokens. This is a prediction, not yet shown.
  - Two risks: (a) with thinking off, the model may move its reasoning into visible text, which the strict parser rejects as `extra_text` or `not_json`, possibly at different rates per arm; (b) every sum was correct with thinking on, and without it arithmetic errors could start to move Y, which should measure coordination rather than arithmetic.
  - Budgets: the 300 cap, the 2,000-byte bound (about 30 more bytes, within the 524 bytes of headroom) and every budget stay as they are; token use falls.
  - Costs: it is a prereg change, and it needs a test that the body carries the field. A one-call canary only proves that the field does not return a 400. Fix A therefore needs a small re-pilot: about 40 calls is about USD 0.005, and the full 120 is about USD 0.016.
- **B. Keep thinking and raise `max_tokens`** to about 1,000. The pilot cannot show that 1,000 is enough, because the round-2 outputs are censored at 300. Fix B needs the same re-pilot.
  - The 300 is hard-coded twice: `spend.PER_CALL_OUTPUT_TOKENS` (`spend.py:48`, checked in `reserve`) and `team_claude.CAPS`.
  - The batch token cap is checked against the **reserved worst case** (input bytes + `max_tokens`, `spend.py:~479`), not against actual use. With the prereg's 2,000-byte input bound, the worst case is 3,000 tokens per call. `episode_tokens` must therefore rise from 18,400 to 24,000 (8 × 3,000), and the `ep1` cap from 1,250,000 to 1,500,000 (500 × 3,000). The `pilot` cap rises in step, to 150 × 3,000 = 450,000.
  - Worst-case USD is 500 × (2,000 × 0.1 + 1,000 × 0.5) / 1e6, about USD 0.35, still far below USD 5.
  - This keeps the model's default behaviour, but the depth of thinking can still differ by arm, now without losing turns.
- **Either way:** the `pilot` batch is now stopped, and settle refuses while a stop is recorded. A re-pilot therefore needs owner approval and a new or reopened batch.
- **Either way, add cheap observability:** record the list of content-block types and the count of thinking blocks per call in the ledger or the turn. Without it, this diagnosis cannot be confirmed from the logs.

## 2. `board_error:ValueError`

### Exact path

In `none`, `play` and the pilot cards (enforcer off), several agents claim the same task in round 2. Each reply is `claim, work, release`.

1. `team_claude.py:290-292` defers the release of a task claimed in the same reply until after `router.end_round`.
2. `Board.end_round` (`board.py:141+`) resolves the claim to one seeded winner.
3. The losers' deferred releases run at `team_claude.py:250-253` → `send` → `team.submit` (`team.py:134`) → `router.act`. The enforcer admits the action because it is off.
4. Then `_execute` → `board.release`, and `board.py:137-138` raises `ValueError(f"{agent} does not hold {item}")`.
5. `router.py:274-277` catches it, returns `refused, board_error:ValueError`, and counts one refusal for that agent (`enf.refusals.record`, consecutive = prior + 1).

In `code` (trace:60, `ep1-code-t1-s1` a1), the enforcer refuses the loser's claim (`A:duplicate_claim`), so `claimed` stays `None`. The release is then sent at once rather than deferred, the enforcer admits it, and the board raises the same error.

### Instrument bug?

No. The router comment at `router.py:274` names this exact case, and `prereg/EP1.md:318-320` says "`none` and `play` have no enforcer denials by construction, only board-error refusals of a release."

### Effect

- **Y, `valid` and the scored log are unchanged.** The release reaches the board only after the work event. `team.submit` logs only claim and work events into `ep.log` (`team.py:146`), and the scores match a recount: for example `ep1-none-t0-s0` has distinct 2, duplicates 2, Y 0.5.
- **What changes:** the refused release appears in `trace` with `executed: false` (`team.py:142`), it adds to `refused` and `refusals`, and it charges `spent.refused` bytes. `orders.false_done_rate` was 0.0 in every episode.
- **Can it differ across arms?**
  - The reason label does. In `none` and `play`, a claim loser shows `board_error` refusals. In `code`, the same behaviour shows up as `A:*` refusals plus `board_error` only when the release was sent.
  - So the raw "refusal rate per arm" (`prereg:517`) mixes enforcer denials with board errors. Report the two separately.
  - Stops: in `code` the board error is counted as a consecutive refusal, and it was the third one that stopped `a1` in `ep1-code-t1-s1`. Each read resets the consecutive count, so with 2 rounds a stop can only come after an agent's final action and cannot cost a call or change Y.
  - The 20-refusal episode stop is out of reach, since at most 4 × 4 = 16 refusals fit in an episode.
- **Optional fix (no budget effect):** split the reason into a typed label such as `board_error:release_unheld` and report board errors apart from enforcer denials. This changes reporting only.

## 3. Other observations from the 11 traces

- **Round-1 herding:** in every episode, all four agents claim task 0, and in round 2 the losers all claim the next task id, so the collisions repeat. The cause is that all four prompts are identical apart from the agent id, the committed board is empty, and the task list is sorted. As a result, Y takes only the values 0.5 and 0.75, and every arm scores the same on a given set (t0: all 0.5). This is not a code defect, but it is a sensitivity defect, and with the variance this low EP-1 may be unable to separate the arms. Nudging the agents toward different tasks would breach the "no advice" design, so it needs an owner decision. Report it; do not patch it.
- **Labelling:** the pilot conditions run with `arm = "play"`, so the episode ids look like `ep1sc-play-*` and `ep1kw-play-*`. In `final.json`, `voids` is keyed only by `code`, `none` and `play`, so `states_check` and `keyword_stuffed` are folded into `play`. Any per-arm summary built on `arm` rather than `cond` merges them. This is a minor reporting defect that does not touch EP-1, which has 3 conds equal to 3 arms.
- **Valid JSON lost to `max_tokens`:** trace:107 is the only case. The handling is correct under the rules, but it is evidence that the cap, not the format, drives the malformed count.
- The stop itself is correct: in `ep1.py:381-384`, per = 3 sets × 8 = 24 calls, and the threshold is 24 × 15 // 100 = 3. `states_check` reached 4.
- `ep1-none-t1-s1`: a0 and a1 both named their result `sum_t1t1`, giving name_collisions 1. Scored per rule; not a defect.

Not checked: the actual content-block types, which no log holds; whether Haiku 5.5 accepts `thinking: disabled` together with an explicit temperature of 1.0 (that needs a paid canary); and whether card A causes the drop in thinking, which is a correlation only.
