# Pre-registration protocol: R2 L4-C, verified replay at the two strongest consolidation settings

## 1. Status

**DRAFT. Not frozen. No run, spend or experiment authority.** This file is a documentary draft
written offline on 2026-11-24. Nothing here admits a batch, reserves GPU-hours or approves spend.
A freeze needs the items in section 14 closed and the record in section 15.

Scope is bound by `prereg/R2-L2-L3-L4-scope.md` (SC): L4-D is excluded; L4-C is primary; L4-B and
L4-E are retained; L4-E keeps its separate adapter and lineage dependency (SC:26-27), which the
admissions packet tracks as M5 (ADM:17). Section 16 binds the joint decision across the two
strongest settings, which the readiness register lists as an open check (RR:55-56).

Source key. Every number below carries one of these citations. Where the repo gives no number the
text says OPEN and section 14 names the decision and its owner.

| Key | File | State when read |
|---|---|---|
| SC | `prereg/R2-L2-L3-L4-scope.md` | committed (`d4b1f91`); sha256 `9008847b…` |
| RR | `docs/reports/workplan-ep/R2-R4-protocol-readiness.md` | **untracked**; sha256 `1352e8941da7e699f81153461a46ba1cf717fb41aa55260ebf771e49087b5db6` |
| P | `docs/PROPOSAL-RESIDENCY-V3.md` | committed text at HEAD `1dabf53` (`git show HEAD:`). The working tree has uncommitted edits, one of them at P:585-586; line numbers here are the committed ones |
| W | `docs/WORKPLAN-RESIDENCY-V3.md` | committed; working tree identical |
| AP | `docs/reports/ep-approvals.md` | working tree, with uncommitted edits; D1 at AP:166, D3 at AP:168 |
| ADM | `docs/reports/tremor/OWNER_DECISION_protected_admissions_M3R3_M4_M9.md` | as read |
| DL | `docs/reports/tremor/DECISION_LOG.md` | committed; "parked owner-yes items decided under OD4" at DL:193-207 |
| LC | `docs/reports/workplan-ep/L4-C-matched-scripted-comparison.md` | **untracked**; sha256 `f24b66b8155e28ff47bcf43bee2a2298036edaac5d900dde832154f1023adf19` |
| LA | `docs/reports/workplan-ep/L4-adaptive-replay-scripted.md` | **untracked**; sha256 `f907e6361f0e65b08301390bdf1dc212861b49eafbc02d1fbc6b74b07729697b` |
| LM | `docs/reports/workplan-ep/L4-measured-compression.md` | **untracked**; sha256 `6950dcd0e42c52b1c7510a9b18c87751a58bcd707bca01879e3ded5f5a1c8fd3` |
| LB | `docs/reports/workplan-ep/L4-B-recovery-observation-contract.md` | **untracked** |
| LL | `docs/reports/workplan-ep/L4-L8-adapter-lineage.md` | **untracked** |
| code | `src/murmuration/{vreplay,nulls,susceptibility,readouts}.py` | committed at HEAD `1dabf53`; working tree identical for these four files |
| lab | `lab/l4c_scripted_{comparison,scoring,ledger,verify}.py`, `lab/l4_adaptive_replay_policy.py`, `lab/l4_measured_compression.py` | **untracked** development fixtures |

## 2. Hypothesis and the single primary endpoint

**Hypothesis (prediction C, primary).** Verified replay keeps the false share below 0.05 at the two
strongest settings, at no more than 1.5 times the tokens, and beats equal-token search in tokens
per passing task (P:536-538; RR:21; W:50-51).

**Single primary endpoint.** The share of false notes in the always-loaded layer under verified
replay (P:530-531, P:536), read at each of the two strongest settings. It is the first conjunct of
one primary contrast (P:179).

**The primary is a conjunction, decided by an intersection-union test.** Every conjunct must hold,
each at the stated level with no multiplicity adjustment, and each is reported separately
(DL:205). The conjuncts are:

| ID | Conjunct | Source |
|---|---|---|
| C1a, C1b | False share below 0.05 at the strongest and at the second-strongest setting | P:536-537; RR:21 |
| C2 | Verified replay uses no more than 1.5 times the tokens of the reference | P:537; RR:21 |
| C3 | Verified replay beats equal-token search in tokens per passing task | P:537-538; RR:21 |

The reference in C2 is OPEN (L4-O1). Whether C2 and C3 are read once or at each setting is OPEN
(L4-O3). The DL row names L2-C and L3-C; its application to L4-C here follows the same owner
delegation and needs its own DL entry before the freeze (L4-O18).

**Secondaries.** L4-B and L4-E are retained (SC:27) and are secondary, Holm-corrected
(P:236-237; RR:45). Each needs its own protocol; this file freezes neither. L4-B: recovery time
just below the boundary is at least twice its value two settings lower (P:533-535), killed if the
ratio's upper bound is below 1.25 and supported if its lower bound is above 1.5 (P:564). L4-E: the
adapter transfers at least 10 points better than context and a planted wrong fact takes at least
twice as many nights to correct (P:540-542; RR:65-67). L4-D is out of scope (SC:26). Prediction A
is not retained by SC:27; its status in this batch is OPEN (L4-O4).

## 3. Arms and matched comparators

All arms are compared at equal total budget, and the cost of measuring a statistic is charged to
the arm that uses it (P:193-194; P:517-518).

| Arm | Source |
|---|---|
| Verified replay with adaptive strength (technique) | P:513-517; `vreplay.py:1-7` |
| The same tokens spent on search or retries (reference for C3) | P:518; RR:21 |
| Evaluator-gated write with no consolidation (reference for the second kill) | P:519-520; RR:21; W:44 |
| Plain model dream | P:518; RR:21 |
| Placebo dream: notes from shuffled transcripts | P:518-519; RR:21 |
| Raw history in context with no store | P:520; RR:21; W:44 |
| No memory | P:520; RR:21 |

Excluded: the learned consolidator (Auto-Dreamer), because it needs training (P:520-522). The
adapter arm E is a separate local arm (RR:21) under its own gate (AP:168; W:219).

The scripted fixture covers three of these arms only: `ARMS = ("replay", "write_only", "search")`
(`lab/l4c_scripted_comparison.py:15`). A native harness for all seven is OPEN (L4-O9).

## 4. Data and planted inputs

Benign planted notes only, under D1 (AP:166; W:214). The arising-shortcut setting is not run
(SC:26).

- **Night loop.** Each day the team works from the current store; each night a consolidation pass
  reads the day's log and the old store and writes a new store; the old store is kept, so every
  night is an auditable diff (P:169-171; W:158).
- **Consolidation ladder.** No dream; extractive merge; abstractive with raw log kept; abstractive
  with raw log dropped and promotion after two supporting episodes; the same after one. Interpolated
  promotion thresholds give at least seven settings (P:524-527). The x-axis is the measured
  compression ratio, not the rung number (P:527-528).
- **Measured compression.** The development audit reports the exact fraction `after / before` of
  loaded UTF-8 payload bytes and keeps raw-episode retention separate (LM:3-7). It excludes model
  tokens; the scientific compression index still needs a tokenizer, a rendering policy, held-out
  chain custody and an approved measurement protocol (LM:34-38). OPEN (L4-O5).
- **Daily error rate.** Prediction A fixes one (P:530); the proposal gives no value. OPEN (L4-O6).
- **Nights per chain.** Prediction A reads after six nights (P:531). Prediction C states no
  horizon. Draft default: C inherits six nights. OPEN (L4-O6).
- **Inputs to freeze.** Day and night trace chains, old and new stores with source IDs, measured
  compression ratios, scorer results, paired cost records, and calibration of the ladder and the
  token-ratio reference (RR:21).
- **Sealing.** Close-night truth labels are detached from execution and supplied only after
  dispatch (LC:14-16; `lab/l4c_scripted_scoring.py:10-11`). A custodian independent of the author
  holds labels and held-out chains (ADM:128).
- No tenant or private data enters any test (P:987-988).

## 5. Splits and blinding

- **Unit.** n is chains, never agent turns; each is rerun at least three times and averaged first
  (P:178-179; RR:42).
- **Calibration chains** measure the compression ratio of every setting and fix the two strongest
  settings (section 16). **Assessment chains** are disjoint from them and carry the outcomes.
  Chain, family, source, episode and note identities must not overlap between the two; the L4-A
  fixture already rejects such overlaps and is the model. Split IDs and the seed map are OPEN
  (L4-O7); RR:49 requires them in the freeze artifact.
- **Blinding.** Consolidation passes and agents never see the oracle (P:166-167). The scripted
  re-check in verified replay reads the environment, not the truth labels (P:513-514). The custodian
  keeps assessment labels sealed until section 16 is locked and the analysis code is frozen.
- **Truth.** Three scorers; any disagreement voids a run (P:165-166).

## 6. Primary metric and computation

1. **Technique per night** (`vreplay.py`): `gate(claims, check)` keeps only claims whose scripted
   re-check returns True, and a crashing check keeps nothing (`:35-47`); `replay_batch(retained,
   new)` puts every retained raw episode before the new ones (`:50-52`); `next_strength(rung, last,
   now)` lowers the rung by one when recovery time or R rose and never raises it (`:55-64`);
   `retain(note_ids, uses, capacity)` keeps the most-used notes, ties by note id (`:67-82`).
2. **Controller readings.** Recovery time and R each night (P:516) come from
   `susceptibility.recovery_time` and `susceptibility.reproduction_number`
   (`susceptibility.py:12-14`; `readouts.py:128-135`, `:55-71`). A missing reading is passed as
   None and leaves the rung unchanged (`vreplay.py:13`).
3. **False share (C1).** False resident notes divided by resident notes, per chain and setting, at
   the close of the last night, with a note false when its text differs from the close-night truth
   for its source (`lab/l4c_scripted_scoring.py:58-61`; `lab/l4c_scripted_comparison.py:139`). An
   empty store or a note with missing truth leaves the share undefined, not zero (LC:38-41).
4. **Token ratio (C2).** Total tokens of the verified-replay arm divided by total tokens of the
   reference arm, on the same chains. Reference and token meter: OPEN (L4-O1, L4-O2).
5. **Tokens per passing task (C3).** Tokens spent divided by tasks passed, per arm; undefined when
   no task passes or a submitted answer has no label (LC:37-41;
   `lab/l4c_scripted_comparison.py:116-120`, `:141`).
6. Reruns are averaged within chain first (P:178-179).

Gaps. The fixture counts abstract operation units, eight per night per arm (LC:5), and whitespace
words (LA:51-53), not model tokens; scientific token parity and the reference for the 1.5 times
rule are named there as separate gates (LC:43-46). `vreplay` has no token meter, no false-share
function and no harness around the night loop. These need code and tests before a freeze (L4-O9).

## 7. Minimum effect and margin

- C1: false share below 0.05 (P:536; RR:21).
- C2: at most 1.5 times the tokens (P:537; RR:21).
- C3: fewer tokens per passing task than equal-token search (P:537-538). No minimum advantage is
  given. OPEN (L4-O8).
- Kill bounds: "ties" with search and "matches" the gated write (P:566-567) carry no numeric
  margin. OPEN (L4-O8).
- Context for C1: prediction A expects the false share to exceed 0.25 at the stronger settings
  (P:531).

Thresholds are proposals; the pre-registration fixes them after the variance pilot (P:231).

## 8. Sample size, power and stopping

- **Rule.** n is set so the standard error of the primary contrast is at most min(K, E − K)/2.8,
  which gives 80% power to support at E and to kill at zero (P:181-183; W:182-185). Raw counts are
  divided by the design effect 1 + (m − 1)·ICC from the pilot (P:186-188).
- **n is OPEN (L4-O10).** K is not given for any conjunct (section 7), and no variance pilot is
  released (ADM:136). Under an intersection-union test the conjunct with the least power bounds the
  power of the whole; n must be computed for each conjunct and the largest taken.
- **Reachability.** The budget buys a first test, not a decisive kill; a decisive result needs
  about 6 to 11 times the detect-only n (P:962-965; W:221-223). The freeze must state, for each
  conjunct, which outcomes this batch can reach; an out-of-reach kill is reported as inconclusive
  (P:964-965; RR:44-45).
- **Economic stop.** The text arms end at 12 GPU-hours or USD 40 hosted, whichever comes first,
  and report what they have (RR:21; P:584; P:938-939).
- **Statistical stop.** OPEN (L4-O11). RR:50 requires it. Draft default: fixed n, no interim look
  at arm outcomes.
- **Two-failure pivot.** A line whose pilot shows a floor or ceiling twice is closed with that
  result (W:228).

## 9. Analysis plan

1. Average reruns within chain, then the cluster bootstrap over chains (P:179; RR:43).
2. **Manipulation check.** The plain model dream against the placebo dream at each of the two
   settings (P:560-561), and the plain dream's false share against prediction A's 0.25 (P:531). If
   no unprotected arm has a false share at or above 0.05, C1 is trivially true and is reported as
   not informative. Whether that blocks "supported" is OPEN (L4-O12).
3. **Primary.** The 95% interval (P:184-185) of each conjunct, computed separately: C1a and C1b
   against 0.05; C2 against 1.5; C3 as the paired contrast with equal-token search. Combined by the
   rule in section 16.
4. **Kill contrasts** (P:566-567): verified replay against equal-token search in tokens per
   passing task; verified replay against the evaluator-gated write.
5. **Secondaries, Holm-corrected** (P:236-237; RR:45): the remaining arms of section 3, L4-B and
   L4-E under their own protocols.
6. **Null comparison.** `nulls.iterated_map(x0, keep, add, nights)` gives the exact false share
   after each night under the linear map x' = keep·x + add (`nulls.py:82-91`, `:14-16`).
   `nulls.recovery_nights(x0, keep, tol)` gives the first night a planted share with no new errors
   is at or below tol, None if it never is, and refuses answers too large to settle exactly
   (`nulls.py:94-131`). The observed false share and the controller's recovery readings are
   reported next to that null; the rule for fitting keep, add and tol is OPEN (L4-O13). If scripted
   agents reproduce the curve, the result is a property of the loop and is reported as such
   (P:172-174).
7. Report, per arm and setting: the measured compression ratio, the nightly rung sequence of the
   controller, unused budget, and every undefined denominator with its reason.

## 10. Decision rule and kill criteria

By where the 95% interval falls (P:184-185):

- **Supported:** every conjunct of section 2 holds under the rule of section 16 (DL:205).
- **Killed** (P:566-567), either one of:
  - equal-token search ties or wins;
  - the evaluator-gated write matches verified replay, so replay adds nothing.
- **Line-level kill:** the model dream is indistinguishable from the placebo dream at every
  setting (P:560-561).
- **Inconclusive:** otherwise, including any outcome marked unreachable at freeze (P:964-965).

The proposal's kill list for C does not cover a false share whose interval lies above 0.05. This
draft reports that case as "not supported, C1 refuted at setting s". Whether it is also a kill is
OPEN (L4-O8).

## 11. Pre-run sanity checks

1. The scripted L4-C comparison replays byte for byte against its recorded report digest
   `8db70323…` and its 22 focused tests pass (LC:63-65).
2. The integrated verifier rejects a deleted receipt, a fabricated favourable submission, a changed
   source schedule and mutated resident provenance (LC:50-52).
3. Replacing a truth label changes the score and leaves the execution bytes unchanged (LC:15-16).
4. One deliberately failing control fails, and a scorer agreement receipt exists (RR:37-38).
5. `nulls.iterated_map` and `nulls.recovery_nights` match their hand-derived closed forms in the
   module tests (`nulls.py:3-4`).
6. `vreplay.gate` drops a claim whose check raises (`vreplay.py:41-44`), and `next_strength`
   leaves the rung unchanged on a None reading (`vreplay.py:13`, `:63`).
7. The compression audit reproduces its paired and historical reports (LM:52-55).
8. Spark memory and throughput evidence and the pilot's variance and ICC are on record
   (RR:40-41).
9. The spend ledger carries this batch's caps in code (P:941-942).

## 12. Threats to validity

- **Equal caps are not equal tokens.** The same caps permit different realized operation counts
  (LC:43).
- **Stale-note trade.** In the fixture, verified replay withdrew a stale note and left the query
  unanswered, while search retrieved the current source (LC:21-25). A low false share can be bought
  with unanswered work, which only C3 exposes.
- **An empty store has no false share** (LC:38-39). An arm that keeps nothing must not pass C1.
- **Adaptive strength moves the setting.** The controller lowers the rung (`vreplay.py:11-13`), so
  a chain started at a strong setting may not stay there (section 16).
- **R reading.** `reproduction_number` returns the descendant share, which is below 1 by
  construction, and returns 0.0 when nothing is planted (`readouts.py:55-71`); the fixture uses a
  first-generation meter instead (LA:22).
- **Recovery reading.** `recovery_time` returns a time or None, so it cannot tell missing follow-up
  from a completed observation interval (LB:8-9).
- **Compression in bytes, cost in tokens.** UTF-8 bytes exclude serialization overhead and model
  tokens (LM:34).
- **Six nights are not a time series** (P:552).
- **Hard promotion rules** can give a sudden switch with hysteresis (P:556-557), so the two
  strongest settings may lie on either side of a jump.
- **Power:** the stops are far below the decisive-kill n (W:222-223).

## 13. Resource and budget limits

| Limit | Value | Source |
|---|---|---|
| GPU-hours, text arms batch ceiling | 12 | RR:21; P:584; W:214 |
| Hosted stop | USD 40 | RR:21; P:584; W:214 |
| Hosted plan | USD 33 | P:584; W:214 |
| Adapter arm E, outside this batch | up to 13.5 GPU-hours | P:584-585; AP:168; W:219 |
| Programme ceiling | 70 GPU-hours | RR:32 |

Reconcile actual usage before scheduling; hosted limits are separate from Spark hours (RR:32-33).
Memory and runtime per line: no figure in the repo (ADM:107). Only the owner changes a cap
(P:942). Unknown cost is never counted as zero (P:168). The 12 GPU-hours and USD 40 cover all L4
text arms (W:214); the split between C, B and any A work is OPEN (L4-O14).

## 14. OPEN items blocking a freeze

| ID | Decision still needed | Owner |
|---|---|---|
| L4-O1 | The token reference for C2: which arm's tokens the 1.5 times bound is measured against. Candidates in the proposal's baseline list (P:517-520): plain model dream, evaluator-gated write, no memory, equal-token search. The baselines are stated "at equal total tokens" (P:517-518), which a 1.5 times allowance against any of them contradicts | Line author proposes; owner approves at freeze |
| L4-O2 | The token meter: tokenizer, rendering policy, which calls count (day work, consolidation pass, scripted re-checks, controller readings), and the charge for measurement (P:193-194; LM:36-38) | Line author; independent reviewer |
| L4-O3 | Whether C2 and C3 are read once across both settings or at each setting (section 16, step 5) | Line author proposes; owner approves at freeze |
| L4-O4 | Status of prediction A in this batch. SC:27 does not retain it, yet B's boundary (P:535) and C's manipulation check use the ladder sweep | Owner |
| L4-O5 | The compression index: tokens or bytes, orientation (`after / before`, LM:4, means a smaller value is stronger), tie rule, and the calibration protocol that ranks settings (RR:21; LM:36-38) | Line author; custodian holds the calibration chains |
| L4-O6 | Daily error rate, nights per chain, store size, and the planted note inventory | Line author |
| L4-O7 | Calibration and assessment split IDs; seed map | Custodian |
| L4-O8 | Margins: minimum advantage for C3; numeric meaning of "ties" and "matches" in the two kills and the measure on which the gated write "matches"; whether C1 refuted is a kill; whether a kill at one setting suffices | Line author proposes; owner approves at freeze |
| L4-O9 | Native harness and tests: night loop around `vreplay`, all seven arms, token meter, false-share and cost-per-pass functions. New code moves the candidate tree hash | Line author; independent reviewer |
| L4-O10 | n per conjunct, pilot variance and ICC, reachable outcomes at the cap. Needs the approved pilot, which is not released (ADM:136) | Owner releases the pilot; line author computes; reviewer checks |
| L4-O11 | Statistical stopping rule | Line author; owner approves |
| L4-O12 | Whether a failed manipulation check blocks "supported" | Line author proposes; owner approves at freeze |
| L4-O13 | Fitting rule for keep, add and tol in the `nulls` comparison | Line author |
| L4-O14 | Split of the 12 GPU-hours and USD 40 between C, B and A work | Owner |
| L4-O15 | Controller rule: `vreplay.next_strength` lowers when either reading rose (`vreplay.py:63-64`); the fixture lowers only when both rose (LA:12-14; `lab/l4_adaptive_replay_policy.py:132`). Also which R the controller reads (section 12) | Line author; independent reviewer |
| L4-O16 | Model tiers and snapshots, task-family revision, team size | Owner (tiers and spend); line author |
| L4-O17 | RR, LC, LA, LM and the `lab/l4*` modules are untracked. A freeze must pin a committed or closure-archived tree (ADM:27). No native launch entry point exists (ADM:26, ADM:91) | Owner approves the commit; integration owner makes it; line author builds the launcher |
| L4-O18 | A DL entry that applies the intersection-union rule to L4-C by name (DL:205 names L2-C and L3-C), and the section 16 lock line | Orchestrator under OD4; owner for the lock |
| L4-O19 | Independent review of this protocol (SC:39) | Independent reviewer |

## 15. What the freeze record must contain

Per RR:48-52 and SC:35-39:

1. **Protocol sha256** of this file at the frozen commit.
2. **Code tree hash at the candidate.** The git tree of HEAD `1dabf53` read today is
   `3a9a1dc57b138aab80ab46c0e878fe06a1984387`; the record must recompute it and must name the final
   candidate once L4-O9 or L4-O17 moves it. Also the config hash.
3. **Protected inputs**, each with path, sha256 and custodian: day and night trace chains, old and
   new stores with source IDs, measured compression ratios per setting, the ladder calibration,
   close-night truth labels, paired cost records, split IDs, seed map (RR:21).
4. **The two-setting lock** of section 16, with its timestamp and message id, and the bound token
   reference (L4-O1).
5. Model snapshot, task-family revision, scorer IDs, primary and secondary contrasts, economic and
   statistical stopping rules, expected and maximum resources (RR:48-50).
6. **The admission:** a one-use approval by the owner, bound to the exact batch and UTC window
   (ADM:31; SC:38), with the resource limits of section 13.
7. Approval and review evidence, quoted exactly (RR:50-51), including the independent review
   (SC:39).
8. The D1 basis (AP:166) and the scope record that excludes L4-D (SC:26).
9. For L4-E only, in its own record: the settled receipt and before and after checkpoint digests
   that L8-D must cite (RR:61-69; LL:3-6).

A freeze is a pre-registration. It does not authorise a GPU run; each batch needs its own admission
(ADM:89).

## 16. The joint decision across the two strongest settings

RR:55-56 asks for this binding. The rule is the intersection-union test of DL:205: no conjunct may
be passed on behalf of another, and no setting on behalf of the other.

1. **Which settings.** The two settings with the strongest measured compression among the ladder
   settings run (P:527-528; RR:21; LC:44-46), ranked on the calibration chains only (section 5).
   Rung index does not decide the ranking. This is an interpretation: the proposal says "strongest" (P:536)
   and the register "strongest measured" (RR:21); P:527-528 is a rule about the fits' x-axis, applied here
   by analogy. Index, orientation, tie rule and confirmation of this reading: L4-O5.
2. **Lock before outcomes.** The custodian records the two setting IDs with their measured ratios,
   a message id and a UTC time before any assessment label is opened and before any false share
   from a model-generated assessment chain exists. Scripted fixtures (LC, LA) are instrument
   checks, not outcomes. After the lock the pair does not change; a setting that later fails to run
   is reported as missing, not replaced.
3. **What "at a setting" means under adaptive strength.** The controller can lower the rung during
   a chain (`vreplay.py:11-13`). Draft default: a chain belongs to the setting it starts at, the
   false share is read on that chain whatever rung it ends at, and the nightly rung sequence is
   reported. Confirming or replacing this default is part of L4-O15.
4. **C1 at both settings.** C1a and C1b are tested separately, each by its own 95% interval
   against 0.05 (P:184-185; P:536). No pooling, no averaging across the two settings, no choosing
   the better one.
5. **C2 and C3.** Draft default: each is tested at each of the two settings, giving six conjuncts,
   which is the strictest reading of P:536-538. Reading them once on the pooled pair is the
   alternative. OPEN (L4-O3).
6. **Undefined is not passed.** A conjunct whose value is undefined (empty store, no passing task,
   missing label; LC:37-41) does not hold. Missing is not zero.
7. **Outcome.**

| Conjuncts | Result for prediction C |
|---|---|
| All hold at both settings | Supported |
| Any one fails or is undefined, and no kill criterion of section 10 is met | Not supported; reported as inconclusive, with the failing conjunct and setting named |
| A kill criterion of section 10 is met | Killed. Whether one setting suffices: L4-O8 |

8. **Reporting.** Every conjunct is reported at every setting with its estimate, interval and
   denominator, whatever the joint result (DL:205).
9. **Not locked means not frozen.** A freeze record without the lock of step 2 and the bound token
   reference (L4-O1) is invalid, and no L4 admission can cite it.

## Decisions since drafting (2026-11-24, line author under OD4; the freeze confirms or replaces them)

Source: `docs/reports/tremor/DECISION_LOG.md`, "L4 strength-lowering rule" (`f33164d`).
- **Rule for lowering strength (L4-O15):** one rung down when either recovery time or R rises. This matches the accepted `vreplay` module (`vreplay.py:63`). `lab/l4_adaptive_replay_policy.py` now follows it (`1b30daf`).
- **Conjunction rule:** the joint decision across the two settings requires every conjunct (an intersection-union test, each reported).
- **Still OPEN:** every other item in section 14, including the token reference (L4-O1), the token meter (L4-O2) and the freeze record.
