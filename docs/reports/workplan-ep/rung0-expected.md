# Rung 0: analytic expectations (A0-3)

2026-11-19, Opus 5.5. Written before A9 exists, so A9's table is checked against numbers fixed in advance. Every
number here is computed from a stated scripted model.

> **Instrument validation only.** Scripted adopters obey or ignore a card by construction. Nothing here, and nothing
> A9 measures, is evidence about models. Every rung-0 record carries `instrument_validation: true`, and C3 strikes any
> rung-0 number shown as model behaviour (EP section 6, WORKPLAN-EP section 7).

## 0. Baseline test count

- **Live working tree.** `PYTHONPATH=src python3 -m unittest discover -s tests` gave `Ran 186 tests ... OK
  (skipped=1)`, stable over 9 consecutive runs. The two runs before those gave 169 and 175 tests with failures, while
  Wave-A builders were writing new test files. Treat 186 as a moving baseline. Re-take it when Wave A lands.
- **Committed HEAD `972dee3`.** `git archive HEAD src tests` gave 79 tests, with 1 failure and 1 error. Both come from
  `train/` missing in that extracted copy (`ModuleNotFoundError: train`, `train/power.py` not found). They are not
  HEAD defects.

## 1. Common definitions and algebra

- `Y` is a team outcome where higher is better. `HDI = (Y_code - Y_play) / (Y_code - Y_none)` (EP 2.2).
- Arms:
  - `none`: neutral card, no enforcer.
  - `play`: practice card, no enforcer.
  - `code`: neutral card, enforcer on.
- A6 has the neutral card ignored by construction. So in `none` and `code`, every agent behaves as a non-adopter,
  whatever q is. **q acts only in `play`** (and `both`): each of the 4 agents adopts independently with probability q.
- **q = 0.** `play` and `none` behave identically, so `Y_play = Y_none` and `HDI = 1` whenever `Y_code != Y_none`. This
  checks arithmetic only. If A9 runs `none` and `play` with common random numbers per task set (the same seed), every
  set must give `HDI = 1` exactly, and any other value is a bug. With independent draws, see the bands in section 3.4.
- **Linear practices.** Suppose the outcome is a mean of independent per-agent contributions, and an enforced agent
  behaves like a full adopter. Then `Y_play(q) = Y_none + q (Y_code - Y_none)` and `HDI = 1 - q` exactly.
- **Team practices.** A, B, C, D and shared-memory G are non-linear in the number of adopters, so `HDI(0.5) != 0.5`.

## 2. The rung-0 allocation model (practices A and D)

These assumptions follow EP 6 and WORKPLAN-EP A2, A3, A6 and A7.

**Setup**

- 4 agents, 6 tasks, 2 rounds. Round 1 is the claim (and name) round; round 2 is the work round, one work slot per
  agent.
- The board snapshot is taken at the start of each round. Writes within a round are invisible until `end_round` (A2).
- Every executed work action passes its check, so `Y` depends only on allocation:
  `Y = distinct tasks worked / 4`, matching `alloc.score`'s `distinct_passing / slots`.

**Behaviour**

| Agent | Round 1 | Round 2 |
|---|---|---|
| Non-adopter | Makes no claim | Works on one task drawn uniformly from all 6, without reading the board |
| Adopter | Claims one task drawn uniformly from those unclaimed in its snapshot (all 6) | Reads the round-2 snapshot. If its claim won (first in seeded order), it works that task. If it lost, it claims and works a task drawn uniformly from those unclaimed in the round-2 snapshot. Losers draw from the same stale snapshot, so they can collide again |

**Code-arm semantics.** Y_code depends entirely on this, and A7 has not fixed it. Three readings of A7 ("refused; a
refusal costs the turn") are plausible, plus a sensitivity variant:

| Variant | What the router does | Consequence |
|---|---|---|
| **V1** | Enforces claim-before-work: every agent must claim in round 1. Duplicate claims are refused and cost the turn. A refused agent re-claims from the round-2 board, and duplicates among re-claimers are refused (slot lost) | The router does the board-reading for neutral-card agents, so `Y_code = Y_play(q=1)` |
| **V0** | Work is an implicit claim. Blind agents act only in round 2, and later duplicates are refused (slot lost) | A refused duplicate adds no distinct task, just as an executed duplicate does not. So `Y_code = Y_none` |
| **V-refuse** | Work without a prior claim is refused, and neutral agents never claim | `Y_code = 0` |
| **V2** (sensitivity) | As V1, but a refused claim retries at once against the router's fresh state | No turn is lost, so `Y_code = 1` |

### 2.1 Expected outcomes, exact

Exact enumeration with fractions; a Monte Carlo of 200k episodes agrees to 3 decimals.

| | q = 0 | q = 0.5 | q = 1 |
|---|---|---|---|
| `Y_none` | 671/864 = 0.7766 | same | same |
| `Y_play` | 671/864 = 0.7766 | 1140569/1382400 = 0.8251 | 85469/86400 = 0.9892 |
| `Y_code`, V1 | 85469/86400 = 0.9892 | same | same |
| `Y_code`, V0 | 671/864 | same | same |
| `Y_code`, V-refuse | 0 | same | same |
| `Y_code`, V2 | 1 | same | same |
| **HDI, V1** | **1** | **25215/32656 = 0.7721** | **0 exactly** |
| HDI, V0 | undefined (0/0) | undefined | undefined |
| HDI, V-refuse (negative denominator) | 1 | 0.8251 / 0.7766 = 1.0624 | 85469/67100 = 1.2737 |
| HDI, V2 | 1 | 241831/308800 = 0.7831 | 931/19300 = 0.0482 |

**Reading the table**

- Only V1 gives EP 6's "HDI near 0 at q = 1". Under V1 it is exactly 0, because the enforced arm suffers the same
  stale-snapshot collisions as adopters do. Refused duplicates and executed duplicates both add no distinct task.
- Under V2, enforcement has fresher information than the board, so **HDI(q = 1) = 0.048, not 0**, even with perfect
  adopters.
- Under V0, HDI is undefined at every q.
- Under V-refuse, the denominator is negative. EP's reading "HDI above 1 means the playbook hurts" then inverts: here
  the playbook is far better than enforcement.

**Decision needed (Fable consult trigger, WORKPLAN-EP section 3):** A6 and A7 must fix one code-arm semantics before
A9. V1 is the only one consistent with EP 6.

### 2.2 Collision rate at q = 1 (4 agents, 2 rounds, 6 tasks)

This uses the definition in `orders.py`: **colliding items** (items with 2 or more claimants in a round, from
`board.py` `resolved[].collision`) divided by claims, per episode.

Round 1:

- `P(no collision) = 6·5·4·3 / 6^4 = 5/18`, so `P(at least one) = 13/18 = 0.722`.
- `E[distinct claimed] = 6 (1 - (5/6)^4) = 671/216 = 3.106`.

Both rounds, per episode:

| Quantity | q = 0 | q = 0.5 | q = 1 |
|---|---|---|---|
| Claim-collision rate, mean of the per-episode ratio | **None** (no claims; not 0) | 847429/13608000 = 0.0623 (over the 15/16 of episodes with claims) | **142837/907200 = 0.1574** |
| Same, as a ratio of expectations | None | 0.1016 | 0.1705 |
| E[colliding items] | 0 | 8723/38400 = 0.2272 | 2003/2400 = 0.8346 |
| E[claims] | 0 | 7729/3456 = 2.236 | 1057/216 = 4.894 |
| Executed duplicate work, `play` | 193/216 = 0.894 | 241831/345600 = 0.700 | 931/21600 = 0.0431 |

Other arms:

- Executed duplicate work under `none` is 193/216 = 0.894 per episode, against 0 under `code` (V0, V1, V2: refused,
  never executed). The latter is an A9 instrument check.
- Under V1, refusals per episode equal E[colliding claimants beyond the first]. That is 20231/21600 = 0.937
  claims-beyond-first.

So at q = 1, with adopters acting on one stale snapshot:

- collisions are the norm, not the exception: 72% of episodes collide in round 1;
- about 4% of a slot per episode is wasted on executed duplicates;
- `Y_play` = 0.989, not 1.

### 2.3 Tie-break sensitivity (variant L)

If adopters take the **lowest-index** unclaimed task instead of a uniform draw, then at q = 1:

- round 1: all 4 claim t0;
- round 2: the 3 losers all take t1;
- so `Y_play = 1/2`, below `Y_none`. Collision rate = 2 colliding items / 7 claims = 2/7.

A9 must use uniform choice among unclaimed tasks, or state its tie-break.

### 2.4 Bands for A9 (`sets = 15`, code V1)

Monte Carlo, 1,000 replicates. Arms are drawn independently, which is conservative. Each replicate uses a percentile
cluster bootstrap with 1,000 resamples for the denominator.

| q | P(95% CI of `Y_code - Y_none` excludes 0) | HDI 2.5% / median / 97.5% |
|---|---|---|
| 0 | 0.997 | 0.53 / 1.00 / 1.78 |
| 0.5 | 0.993 | 0.35 / 0.75 / 1.43 |
| 1 | 0.998 | -0.20 / 0.00 / 0.17 |

The denominator is only 0.21, so single-set points are noisy. With common random numbers across arms, q = 0 and
q = 1 must give exactly 1 and 0. The q = 0.5 band above is the acceptance region.

## 3. Practice D (write, then read)

In this instrument, D reduces to A:

- "post intent" is the round-1 claim;
- "re-read" is the round-2 snapshot.

A re-read within the same turn sees nothing new, because writes are invisible until `end_round`. So D's
useful-read fraction for that read is 0 by construction, and `Y` and HDI equal section 2 under the same code
semantics. **The rung-0 instrument cannot separate D from A.** This is a Fable consult trigger.

## 4. Practices B (one writer per page) and C (unique names)

Both are last-writer-wins.

**B model**

- Each agent holds m facts per round; m cancels.
- A non-adopter rewrites the shared page from its stale snapshot, so of the k non-adopters only the last writer's
  facts survive the round.
- An adopter writes its own page.
- `Y` = fraction of facts retained.

Arms:

- `none`: `Y_none = 1/4`.
- `code`: refused writers retry on their own page in round 2, assuming the refusal names the page. So `Y_code = 1`,
  at a cost of one turn per refused writer.
- `play`: `Y_play = E[(4 - k + [k >= 1]) / 4]` with `k ~ Bin(4, 1 - q)`.

| q | `Y_play` | HDI | E[clobbered writes] |
|---|---|---|---|
| 0 | 1/4 | 1 | 3 |
| 0.5 | 47/64 = 0.7344 | 17/48 = 0.3542 | 17/16 |
| 1 | 1 | 0 | 0 |

**C:** **with the current `alloc.score`, names do not affect `distinct_passing`.** So `Y_code = Y_none`, and HDI is
undefined at every q. Only `name_collisions` moves:

- non-adopters herding on one name produce k - 1 collisions (expected 3, 17/16 and 0 at q = 0, 0.5, 1);
- the router-assigned name, and adopters' `{agent}-{task}` names, produce 0.

Under a **hypothetical** scoring in which same-named work clobbers to one survivor (allocation held perfect), C's
numbers equal B's table. That scoring is not built and not decided. EP-1 combines A and C (an existing consult item),
so C's HDI needs a scoring decision before EP-1.

## 5. Practice E (verify before done)

**Model**

- Each completed task carries an injected fault with probability f.
- A non-adopter marks it done unchecked.
- An adopter runs the deterministic check and withdraws faults.
- The enforced router runs the check.
- `Y` = 1 - fault pass-through.

Then `Y_none = 1 - f`, `Y_code = 1` and `Y_play = 1 - f(1 - q)`. **f cancels:** `HDI = 1 - q` for any f > 0, which gives
1, 0.5 and 0.

**Blocking caveat (A0-1 finding R3):** if the enforced arm uses the current `router.verify` with a different-model
verifier cell, its check is `bool(result)`. Every non-empty faulty result then passes, so `Y_code = Y_none` and HDI is
undefined. Fix A0-1 item 2 first.

## 6. Practice F (memory hygiene)

**Model:** unsourced poison notes. A non-adopter adopts the poison. An adopter rejects it, because the note has no
source link. The code lint rejects it. Adoption is per agent and independent, so the practice is linear:
`Y_none = 0`, `Y_code = 1`, `Y_play = q`, and `HDI = 1 - q` (1, 0.5, 0).

**Caveat:** a "confident poison" with a fabricated source passes both the adopter and the lint. For that item
`Y_code = Y_play = Y_none`, so HDI is undefined. Report it separately; do not pool it.

## 7. Practice G (consolidate)

`Y` = fraction of wrong notes withdrawn by session end. The scripted re-verify catches every planted wrong note.

- **Private memory:** linear. `Y_play = q` and `HDI = 1 - q` (1, 0.5, 0).
- **Shared memory:** one adopter cleans the store for everyone. `Y_play = 1 - (1 - q)^4`, which is 0, 15/16 and 1.
  `HDI = (1 - q)^4`, which is **1, 1/16 = 0.0625 and 0**.

A9 must state which memory layout it uses.

## 8. Summary for A9

| Practice | HDI q = 0 | HDI q = 0.5 | HDI q = 1 | Condition |
|---|---|---|---|---|
| A | 1 | 0.7721 | 0 | code V1 (V2: 0.7831 and 0.0482; V0: undefined) |
| B | 1 | 0.3542 | 0 | last-writer-wins, refusal retries on own page |
| C | undefined | undefined | undefined | current `alloc.score`; hypothetical clobber scoring gives B's row |
| D | = A | = A | = A | instrument cannot separate D from A |
| E | 1 | 0.5 | 0 | only after A0-1 R3 is fixed |
| F | 1 | 0.5 | 0 | unsourced poison; confident poison undefined |
| G | 1 | 0.5 (private) or 0.0625 (shared) | 0 | memory layout stated |

**Consult triggers raised:**

- the code-arm semantics for A (V0, V1, V-refuse or V2);
- C is undefined under the current scoring;
- D is not separable from A.

The exact computations are reproduced by `rung0.py` and `rung0b.py` (session scratchpad). The model above is complete
enough to re-derive every fraction without them.

verified: 972dee3 (plus working tree) 2026-11-19
