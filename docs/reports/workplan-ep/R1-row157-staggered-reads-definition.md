# R1 row 157: staggered reads definition (frozen)

**Author:** the TREMOR lane as the row-157 preregistration author (PC designation `msg_9cc549080e56`).
**Fills:** item 9 of the frozen definition (`R1-row157-contention-definition.md`, sha256 `b9db8f83…`), which left staggered reads to a separate frozen document. Items 1–8 and the addendum (`5cabfe7`) are unchanged.
**Frozen** at the local commit that adds this file. Any change goes in a new file with a new hash and a reason.

## Policy text

"Episode design v2: four or more rounds, staggered reads, contention above 1, round 1 scored apart."

## Definitions

1. **Board read.** An agent reads the shared work board: the claims, posts and work results committed so far. Reading a fixed fixture marker or any other value that never changes during the episode is not a board read.
2. **View age.** The Board commits actions only at the end of each round. When agent a reads in round r, it sees the board as committed at the end of round r − ℓ_a(r), with lag ℓ_a(r) ≥ 1. A lag of 1 means the latest commit.
3. **Staggered reads.** A design has staggered reads when, in every round r ≥ 2 in which at least two agents are scheduled active, the scheduled lags of those agents take at least two distinct values. So in every such round, some agents act on an older view of the board than others. Round 1 is exempt because only the setup commit exists before it; it is still scored apart (definition 8).
4. **Scheduled and pinned.** The lags ℓ_a(r) are produced by the episode generator from its seed and fixed rule before the run. They are committed with a sha256 before any bench outcome is revealed, in the same way as the contention pin (addendum rule 2). The realized view each agent actually received is a separate readout, never a substitute for the schedule.
5. **Read evidence.** For each read, the run records which committed board round the agent saw. A reviewer can then check, from the run's own files, that each agent's view matched its scheduled lag.

## What this rules out

- A design where every active agent reads the same latest commit in some round r ≥ 2.
- A design whose only per-round read is a fixed marker.
- A design whose lags are chosen during or after the run.

## Leakage disclosure

The author has read the e11df9d bench verdict (`runs/x42-bench-rereview-e11df9d/VERDICT.md`, sha256 `031ac207…`, relayed in `msg_2e797d28c96f`). It reported that staggered reads had no frozen definition and that v3 has one named reader of a setup marker per round. That finding is the reason this file exists. The verdict gave no numeric or outcome result for staggered reads, so none could be tuned to. The definition follows the policy wording and the Board's commit-at-round-end model, and it was written without running any candidate design against it.
