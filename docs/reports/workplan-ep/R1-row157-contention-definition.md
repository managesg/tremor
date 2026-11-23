# R1 row 157: contention definition (frozen)

**Author:** the TREMOR lane, Spark chat `claude_bb451a1d_cd2f_4c9f_8c91_ccb964f9bd06`, as the X42 row-157 preregistration author. PC designated this role in message `msg_9cc549080e56`.
**Status:** frozen at the local commit that adds this file, before any further bench result is viewed. Any change is a new file with a new hash, and a reason.
**Reviewer:** the Local Coordinator Assistant, for leakage from known results.

## Policy text being defined

`docs/WORKPLAN-RESIDENCY-V3.md`, R1: "Episode design v2: four or more rounds, staggered reads, contention above 1, round 1 scored apart."

This document defines "contention above 1" and fixes the related terms it depends on. It adds no other number. The only numbers in it, 1 and 4, come from the policy text.

## Definitions

1. **Round.** One step of the episode in which every active agent may read the board and take at most one claim or work action. An episode has R rounds, numbered 1 to R, with R ≥ 4.
2. **Open task at round r.** A task that, at the start of round r, is neither finished nor held by a live claim.
3. **Active agent at round r.** An agent that is allowed to act in round r: not stopped, removed or crashed.
4. **Design contention.** κ_r = A_r / T_r for round r, where A_r is the number of active agents and T_r the number of open tasks at the start of round r. It is defined only when T_r ≥ 1. If T_r = 0 the round has no open work, κ_r is undefined (not 0 and not infinity), and the round is left out of the contention condition.
5. **Contention above 1.** An episode design satisfies the condition when κ_r > 1, that is A_r > T_r, for every round r in 1..R with T_r ≥ 1. It is a property of the episode generator, fixed before the episode runs, and it must hold in round 1. By pigeonhole, A_r > T_r means that if every active agent claims, at least two agents claim the same task. Contention is therefore possible by construction in each such round, not merely allowed.
6. **Episode-level contention.** κ_min = min over rounds with T_r ≥ 1 of κ_r. The design condition is κ_min > 1. If no round has an open task, κ_min is undefined and the episode is not eligible.
7. **Measured claim contention** (a readout, not the design condition). For round r, c_r = (claim actions in round r) / (distinct tasks claimed in round r). It is undefined when no task is claimed. It describes what agents did, and it is reported next to κ but never substituted for it.
8. **Round 1 scored apart.** Every outcome and readout is reported for round 1 separately from rounds 2..R. Round-1 values are never pooled into the rounds 2..R estimates.
9. **Staggered reads** are named in the policy row but not defined here. Their definition stays with the row-157 author in a separate frozen document. Nothing in this definition depends on them.

## What this rules out

A design with more open tasks than active agents in round 1 does not satisfy "contention above 1", whatever happens in later rounds. A design whose replenishment lets open tasks reach or exceed the active agents in any later round does not satisfy it either.

## Leakage disclosure

Before writing this, the author had seen the following. The reviewer should judge whether any of it shaped the definition.

- **The e972484a bench verdict** (`runs/x42-r1-bench-verdict.uPqmQ9/VERDICT.md`, row 157). It said "contention above 1" was never defined, and that the v2 episode had 2 claimants on one task in round 1 only, with 4 agents for 6 tasks over the episode (0.67).
- **Proposal line 603.** It reports that in the instrument pilot, in round 1 of every episode, all four agents herded.
- **The proposal's budget table.** It lists a sensitivity pilot over "rounds, contention, team size".

No other R1 bench result, run output or N2 material was read for this purpose. The definition follows the policy wording ("above 1") and the standard pigeonhole reading of agents against open tasks. It was not tuned to make any existing episode pass or fail.
