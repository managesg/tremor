# Staged T7: decision record (2026-11-19)

Author: Fable 5.2 (planner). Owner: "go ahead with your recommendation" (2026-11-19). This
approves the staged design as a plan. It does not approve a run, a freeze or a commit.
Changed file: `prereg/H7.md` (sections 6, 10, 12, 15, 17, 18 and the header note). The
`code_tree_hash:` line is untouched and still blank.

## 1. The change

T7 now runs in two stages.

| Stage | Arms | Runs when |
|---|---|---|
| 1 | B (thinking off), A (released edit), 0 (base, reference), in that order | after the stage-1 freeze |
| 2 | C (repetition penalty), D (scripted direction edit), D-null, off-target checks | only if the stage-1 gate passes |

Stage 1 is read once, when arms B and A are complete on all 100 problems. Three outcomes:

1. **Kill.** The upper bound of the 95% interval of `acc8k(A) - acc8k(B)` is below +5 points.
   This is the existing kill 1. H7 is killed and stage 2 does not run.
2. **Gate passes.** A beats B by more than 12 points (at least 13 of 100 problems) and the 95%
   interval lies above 0. Stage 2 runs inside what is left of the 12 GPU-hours.
3. **Inconclusive.** Anything else. Stop. Reported as "not shown". This is a legitimate result.

## 2. Why

- **Resolution.** The audit (`docs/reports/prereg-audit.md`) shows n = 100 resolves an
  edit-against-decoding difference only to about ±10 points. The authors' 7.9% to 48.1% is the
  edit against the base model, not against a decoding fix. The critics' reading is that most of
  it is a loop fix, which thinking-off also provides. The second-hand leads put the edit and
  the decoding arms within a few points of each other.
- **Memory.** Both smoke arms were killed by the watchdog: arm 0 at MemAvailable 9.97 GiB after
  about 22 minutes, arm B at 9.44 GiB after about 13 minutes. The cause is unknown. The host
  and its unified memory are shared with other sessions. Six arms means six chances of this.
- **Cap.** 12 GPU-hours covers everything. Arms C and D also need code that does not exist yet
  (the audit's code gap 2) and a practice-set grid run.
- **Nothing decision-relevant is lost.** H7 survives only by beating both B and C. If A does
  not clearly beat B, no stage-2 result can make H7 survive. A kill and an inconclusive result
  have the same architecture consequence (`prereg/H7.md` section 12).

## 3. The gate number

Derivation, from the audit's power figures (normal approximation, not simulated):

- Interval half-width at n = 100 is 1.96 x sqrt(d / n), where d is the share of problems on
  which exactly one arm is right. The audit assumes d between 20% and 40%. That gives 8.8 to
  12.4 points.
- The margin is 12 points, the upper end. **Design choice.** It is fixed before any data and
  does not depend on the discordance we observe. The interval condition is kept beside it in
  case the real discordance is above 40%.

Chance that A beats B by at least 13 problems, same approximation, d from 20% to 40%:

| True A - B | P(gate passes) |
|---|---|
| 0 | 0.3-2.4% |
| +5 | 5-12% |
| +10 | 28-34% |
| +15 | 66-72% |
| +20 | 89-97% |

Plain reading: stage 2 will most likely not run. A true advantage of 10 points would be
missed about two times in three. That is the price of n = 100, and it was already the price
before staging.

The owner may replace the gate before the freeze. The obvious alternative is "the survive
condition against B" (interval above 0 and a point estimate of at least +5). It is looser: at
low discordance it lets through differences of about 9 to 12 points.

## 4. What stays unchanged

- n = 100 per arm, the same seeded problems, one sample each. n is never shrunk to fit the cap.
- The primary metric `acc8k` (finished, within 8,192 tokens, graded correct).
- Survive, kill 1 and kill 2 as written, and the inconclusive outcome and its consequence.
- The 12 GPU-hour cap, now for both stages together. USD 0.
- Arm definitions, sampling profiles, grader, seeds, the arm A rebuild and its hash checks.
- The 10 GiB MemAvailable floor. It is not lowered.
- H7 stays a single pre-test outside every Holm family.

## 5. What staging changes besides the gate

- Run order in stage 1 is B, A, 0. The gate needs only B and A, so a stop during the expensive
  arm 0 leaves the decision intact. The 7.9% check may then be partial.
- Off-target checks move to stage 2. Kill 2 only qualifies a survival, so it is not needed
  before the gate passes.
- Arms C and D may never run. Then we learn nothing about the repetition-penalty arm or the
  scripted direction. PLAN's separate rule for arm D ("drop the script if it does not beat its
  null") is simply not exercised.
- The gate is stricter than the survive condition against B. An observed difference between
  +5 and +12 with an interval above 0 stops as inconclusive.
- Two freeze entries instead of one, if stage 2 runs.

## 6. Still to decide before the stage-1 freeze

From the audit's pre-freeze list (its section 4) and code gaps (its section 3), re-sorted for
staging. Full text: `prereg/H7.md` section 18.

Needed for stage 1:
1. The `finished` condition in `accuracy_at_cap`, with a test for a generation cut at the cap
   (code gap 1). Without it the primary metric is not what the file says.
2. Arm A generation code (code gap 2, the arm A part only).
3. Arm A's generation cap: 32,768 if the stage-1 projection fits, else 8,192. The primary is
   the same either way.
4. The probe100 exposure: accept and record, or redraw `MAIN_SEED`.
5. Owner confirmations: the MATH-500 licence reading and G3 (i).
6. Memory aborts: one smoke arm completes without a watchdog kill, or the cause is found.
   New item; not in the audit.
7. Commit approval for the freeze commits.
8. The owner confirms or replaces the gate (section 3).

Written down before the stage-1 freeze, run only if the gate passes (so that no stage-2
choice is made after seeing stage-1 results):
9. Arm C: the practice-set seed, the grid {1.05, 1.1, 1.2} and the tie rule. The grid run and
   the chosen r come later.
10. Arm D: the loop and non-loop token definition, the practice problems used, the D-null seed.
11. Off-target: MMLU-Pro size and seed; IFEval approved or dropped.

Other documents to align (not edited here): the PLAN and WORKPLAN lines listed in the audit's
section 2, plus PLAN T7 and WORKPLAN step 87 for the staging itself.

## 7. Not checked

- The gate probabilities are a normal approximation under an assumed discordance. They were
  not simulated.
- The smoke logs were not read by the planner; the watchdog figures are as reported by the
  parent.
- Whether stage 2 fits the remaining cap cannot be projected until a smoke arm completes.

verified: 972dee3 (plus working tree) 2026-11-19
