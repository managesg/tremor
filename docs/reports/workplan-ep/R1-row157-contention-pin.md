# R1 row 157: pinned scheduled contention (frozen before the reveal)

**Applies:** the frozen definition (`R1-row157-contention-definition.md`, sha256 `b9db8f83…`, commit `8a16e88`) and addendum (`R1-row157-contention-addendum.md`, sha256 `f6ae2b43…`, commit `5cabfe7`). Addendum rule 2 requires the generator rule, source revision and seeds to be committed with a sha256 before any bench outcome is revealed. This file does that.
**Written before** any further bench result was viewed. No bench outcome has been viewed since the definition was frozen.

## Pinned generator

| Item | Value |
| --- | --- |
| Generator | `lab/r1_episode_v3.py`, committed in `ea24c1f` |
| Generator sha256 | `edfe7750f721aa3695ea194c0ab72e1510955ab31b2673d300b4e21b0185d236` |
| Schedule module | `lab/r1_contention_schedule.py`, sha256 `c3245774ed647403c574a12657d0bcacd4bb1c362345569c5fc80076b3901359` |
| Rule | `fixed-roster-staggered-release-v3` |
| Seed | 17 (the generator default) |
| Rounds | R = 4 |

## Scheduled counts, computed from generator inputs only

| Round | Scheduled agents Â_r | Scheduled open tasks T̂_r | κ_r |
| --- | --- | --- | --- |
| 1 | 4 | 3 | 4/3 |
| 2 | 4 | 3 | 4/3 |
| 3 | 4 | 3 | 4/3 |
| 4 | 4 | 2 | 2 |

κ_r > 1 holds in every round with an open task, including round 1, so the design satisfies "contention above 1". For contrast, the v2 generator gives κ = 2/3, 4/5, 1 and 4/3, which fails in rounds 1 to 3.

**Pin.** The canonical-JSON sha256 of this table plus its metadata (generator path, generator sha256, seed and rule) is the value `run()` writes to `plan.json` under `scheduled_contention.pin_sha256`. It must equal the value the bench reviewer recomputes from commit `ea24c1f`. Any edit to the generator changes it. The value at `ea24c1f`, seed 17, is recorded at the bottom of this file.

## Readouts kept separate (addendum rule 4)

Realized ρ_r and measured claim contention c_r are readouts. v3 does not yet report them, which is a known gap. They never enter the eligibility condition.

## Pin value

`6fa1d9e56fad0a74829e6f9de4a9f70b73118165c696e044923b0efffd69f588` (scheduled_contention.pin_sha256 at ea24c1f, seed 17; its generator_sha256 field reads `edfe7750f721aa3695ea194c0ab72e1510955ab31b2673d300b4e21b0185d236`).
