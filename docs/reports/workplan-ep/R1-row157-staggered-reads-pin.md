# R1 row 157: pinned staggered reads and contention for episode v4 (frozen before the reveal)

**Applies:** the frozen staggered-reads definition (`R1-row157-staggered-reads-definition.md`, sha256 `eddd1e5e…`, commit `5c64406`), plus the contention definition, addendum and pin (`8a16e88`, `5cabfe7`, `1d333f7`).
**Written** before any bench outcome on v4 was viewed. Both pins below were recomputed from a clean `git archive 4408ef4`, not from working files.

## Pinned generator

| Item | Value |
| --- | --- |
| Generator | `lab/r1_episode_v4.py`, commit `4408ef4`, sha256 `6bca8a4deb45397fc13d02377cecc1c951fc36284dbea10e0d98be0b69eac0f4` |
| Read-schedule module | `lab/r1_read_schedule.py`, sha256 `a8831fe957705c61cc979cb423522ae2b14cd798dd2b011875d2e64c1f094f5d` |
| Seed | 17 |
| Rounds | R = 4 |
| Roster | a0–a3 |

## Scheduled lags

ℓ = 1 + ((roster index + r) mod 2) from round 2 on. Round 1 is lag 1 for every agent, because only the setup commit exists before it.

| Round | a0 | a1 | a2 | a3 |
| --- | --- | --- | --- | --- |
| 1 | 1 | 1 | 1 | 1 |
| 2 | 1 | 2 | 1 | 2 |
| 3 | 2 | 1 | 2 | 1 |
| 4 | 1 | 2 | 1 | 2 |

Every round r ≥ 2 has two distinct lags, so definition 3 is met. Scheduled contention is v3's, unchanged: κ = 4/3, 4/3, 4/3, 2.

## Pins (`plan.json` at 4408ef4, seed 17)

- `scheduled_reads.pin_sha256` = `8a11207d7f1a2cc843e5dedfbf7092ffa118641808239d93eb8460d17c71a028`
- `scheduled_contention.pin_sha256` = `5600a4ee2c359c000376260245fab0b8c85f4650f542feef6f85ccafe09ca1e4`. It differs from v3's `6fa1d9e5…` only because its metadata names v4. The counts are identical.
- Both pins carry `generator_sha256` = `6bca8a4d…`, so any edit to v4 changes them.

## Stated limits (from the independent review)

- **Reads are recorded, not acted on.** In this scripted fixture every claim and work action comes from the plan. The reads meet definitions 1–5 as a scheduled design property, but no agent acts on its lagged view. A finding that staggered views change behaviour needs non-scripted agents.
- **Read content is claims only.** The board records init, claim and end_round events. Work results are not board events, so each read's `items` is empty.
- **Reads are pinned by hash, not chained.** They live in `reads.json`, pinned through `summary.reads_sha256`. Each read records the commit hash it saw, and the review checked all 16 against `board.jsonl` with no mismatch.
