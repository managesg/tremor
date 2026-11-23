# R1 row 157: contention addendum (frozen)

**Supplements:** `docs/reports/workplan-ep/R1-row157-contention-definition.md` (sha256 `b9db8f838448d11e681809bbc4a56f018d743a295f91cc19364dc06ea33cc5f8`, commit `8a16e88`). That file is not changed.
**Why:** the Assistant's independent source review (relay `msg_8a5dcfc2ff4c`) accepts the prospective contention ratio only if the counts it uses are pinned before the reveal and kept apart from rounds changed by claims. This addendum pins that. It was written before any further bench result was viewed.

## Scheduled counts, pinned before the reveal

1. **Scheduled counts.** For each episode and each round r, the design contention κ_r uses the scheduled number of eligible agents Â_r and the scheduled number of open tasks T̂_r. Both are produced by the episode generator from its seed and its fixed rules before the episode runs. They are not counted from the run.
2. **Generator rule pinned.** Before the reveal of any bench outcome, the generator rule (or the explicit per-round table of Â_r and T̂_r) is committed with a sha256, together with the generator source revision and seeds. A design satisfies "contention above 1" only if, for every round with T̂_r ≥ 1, Â_r > T̂_r under that pinned rule. An episode generated from an unpinned or later-changed rule is not eligible.
3. **Eligibility of agents and tasks.** An agent is scheduled eligible in round r if the generator's roster has it active in r, before any crash, stop or removal that happens during the run. A task is scheduled open in round r if, under the generator's rule, it has been released by round r and its scheduled completion has not happened. Realized claims and completions are not used.

## Realized counts are a separate readout

4. **Realized counts.** The realized active agents A_r and realized open tasks T_r, counted from the board at the start of round r, are reported as a separate readout, ρ_r = A_r / T_r (undefined when T_r = 0). They depend on what agents claimed and finished in earlier rounds. They never replace κ_r in the eligibility condition, and they are reported next to κ_r so readers can see the difference.
5. **Measured claim contention** c_r (definition 7 of the frozen file) is unchanged and stays a readout.
6. **Round 1.** Rule 8 of the frozen file is unchanged. In round 1, Â_1 and T̂_1 are fixed by the generator, and κ_1 > 1 must hold. Round-1 readouts are reported apart from rounds 2..R.

## Leakage disclosure

Since the frozen definition, the author has seen no new bench outcome. The only new input is the Assistant's review note above, which concerns method, not results.
