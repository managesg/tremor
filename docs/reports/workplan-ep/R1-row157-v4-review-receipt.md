# R1 row 157: receipt for the v4 independent review cited in the pin

**Why:** the 83e4870 bench re-check (`runs/x42-bench-recheck-83e4870.4P3pJg/VERDICT.md`, sha256 `48834c15…`) raised finding F1. The pin file cites an "independent review" of v4 runs, but no receipt for that review existed. This file records the review as it was reported to the lane.

## The review

- **Reviewer:** a fresh-context Opus subagent, briefed with `interrogate`, on host seabridge-spark.
- **Scope:** read-only; it ran on a scratch `git archive HEAD` plus the four uncommitted v4 files.
- **Timing:** after the staggered-reads definition (`5c64406`) and before the v4 commit (`4408ef4`) and the pin (`83e4870`).
- **Reported file hashes:** `r1_read_schedule.py` `a8831fe9…`, `r1_episode_v4.py` `28aaddd5…`, and the two test files `cb3c597e…` and `956fddf2…`.
- **Docstring fix after the review:** before committing, the lane corrected one docstring line in `r1_episode_v4.py` (where reads are recorded). That changed its sha256 to the committed `6bca8a4d…`. No code changed.

## Verdict: ACCEPT, no verified defect

1. **`lags()` and `staggered()`:**
   - `lags()` uses only roster inputs, and `staggered()` follows definition 3.
   - Lags of 0, r+1 and `True` are rejected; the rule lag ≤ r follows from definition 2.
   - A one-round plan is vacuously true, and the docstring says so.
2. **Reads against the board:** in the `late_error` run, all 16 reads have seen round = r − lag, and each commit hash equals the `end_round` hash in `board.jsonl`. Claims and items equal a replay of the log cut at that commit. There were 0 mismatches, from the reviewer's own script. Reads at different lags differ: in round 4, a0 sees 5 claims and a1 sees 4.
3. **Contention:** the table equals v3's and `satisfies()` holds. `board.jsonl`, scores and contention resolution are identical between v3 and v4 in both cases.
4. **Pins:** deterministic, and they change with the seed, rule, generator sha and any single lag.
5. **Limits:**
   - Agents never act on their views.
   - Read content is claims only.
   - The chained `delivery.jsonl` read log is replaced by `reads.json`, pinned by hash.

   All three are recorded in `R1-row157-staggered-reads-pin.md`.
6. **Tests:** 26 tests passed.

## What seeing the run could and could not influence

The review ran v4 before the pin was frozen. The 83e4870 re-check changed only the lag rule and reran both cases. Board, scores and contention came out identical, so a run outcome gave no leverage over the pinned schedule. The pin stands, as the re-check concluded.
