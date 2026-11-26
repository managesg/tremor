# Pre-registration protocol: R6, agent performance on the P vs NP task suite

## 1. Status

**DRAFT (phase R4 of the R6 plan). Not frozen. No run, spend, admission or GPU authority.** Written offline on 2026-11-26 at HEAD `9a015ea` by the coordinator (Opus 5.5). No network, model call, GPU process or key was used. A freeze needs every item in section 13 closed and the record in section 14. At the freeze this file is renamed `prereg/R6-protocol.md`, the name the plan's freeze command uses (R6-O1).

**Method choices** are the line author's under the owner approval of 2026-11-26 ("Yes approve it all and tell them to make decisions on my behalf", DL:303), each citing its rule (section 12). **No number is invented:** sizes, K, seeds, GPU-hours and wall-time caps are OPEN with method and holder (section 13); every number shown is carried from a cited source. Revised 2026-11-26 after an independent review (ACCEPT as a draft, not freezable).

Keys: PL `prereg/R6-pvsnp-research-line-plan.md` (rev. 2, ACCEPT, DL:295); R5 `prereg/R5-agent-performance-line-plan.md` (DL:293); DL `docs/reports/tremor/DECISION_LOG.md`; L3 `prereg/R2-L3-C-protocol.md`; H `lab/r5_perf_harness.py` at `d0c67d7` (DL:299); T `lab/r6_pvsnp_tasks.py` and `lab/r6_m1_enum.py` (`9a015ea`); SC `lab/r6_scorecard.py` (`fa03232`, `28610e1`); PR `lab/r6_predicates.py` (`caf0643`, `5108519`); G `lab/tremor_admission_gate.py`, `lab/tremor_freeze_skeleton.py` (DL:279); CL `lab/r6_inkling_client.py` (**untracked, unreviewed**); AP `docs/reports/ep-approvals.md` (AP-D1 at AP:166).

## 2. Purpose and scope

R6 measures how well agents and teams do checkable work on the P vs NP task suite (R6-TS, PL Part II.1), and whether small teams forecast larger ones: the R5 hypotheses on R6-TS, plus a Red Team arm and a Definition Audit arm. **Every claim is about agents on these tasks, never about P vs NP**; small n says nothing asymptotic. R6-TS data do not enter R5's analysis unless the R5 author registers that before any run (PL:217). **Out of scope:** hosted calls (PL 6.5), Lean kernel checks (a Safety rule 2 install), unbounded-n lemmas (PL:142), milestones M2 to M5 beyond the scorecard.

## 3. Estimands and hypotheses

**Primary: H2. Small teams forecast the pass-count distribution at n = 8** (R5:22-29; PL:211).
- Unit: one agent's work on one task in one episode; row `{"n","task","rerun","agent","pass"}`, `pass` = the F1 to F6 oracle's verdict only.
- Model: with probability c all agents fail together, otherwise each fails independently with probability q (`H.pmf`, `H.fit_common_cause`).
- Estimand: held-out log score at n = 8 of the pass-count distribution from (q, c) fitted at n ∈ {2, 4}, fitted c against c = 0, paired on held-out seeds and task sets (`H.h2_primary`).
- **One pooled primary:** one (q, c) over all task sets, family a stratum of the draw; per-family results **descriptive only** (D9).

**Holm secondaries, family size 4: H1, H3, H5, RT** (decision D8). The size stays 4 if a member is not run. Each is reported alone.
- **H1.** Does the sign of EG(4) forecast the sign of EG(8)? EG(n) = Y_team(n) − Y_nominal(n), at equal tokens (R5:31-34; `H.h1_primary`). This is a separate instantiation on R6-TS; R5's own H1 stays with R5 (PL:215), and neither test reads the other's data.
- **H3.** Team confidence outruns team accuracy. ΔG = G_team(4) − G_solo, where G = mean stated confidence − oracle pass rate per episode (R5:36-42; `H.h3_primary`, `H.behaviour_check`, `H.brier`).
- **H5.** Best-of-N buys fewer than N independent draws. S = mean over tasks and N ∈ {2, 4, 8, 16} of [observed P(no clean among N) − u_t^N] (R5:44-53; `H.select_clean`, `H.h5_primary`, `H.draw_position_check`).
- **RT.** A Red Team role lowers the share of false lemmas still accepted (PL:219-225), section 4.

**Descriptive, no test: Definition Audit (DA)** (PL:227-229). Precision and recall for "defective", the true-negative rate on faithful pairs, and exact-span location accuracy.

**Gate report, no test.** G1 to G6 failure rates per gate, arm and team size, on answers that carry a scorecard (PL:233-235).

## 4. Arms

| Arm | Hypothesis | Content | Source |
|---|---|---|---|
| Team n ∈ {2, 4} (fit), n = 8 (held out), no confidence field | H2 | runner rows (below) | R5:23-25 |
| Team n = 4 and n = 8 against nominal groups of the same size, equal tokens | H1 | `H.nominal_rows`, `H.team_rows` | R5:31 |
| Solo; team of 4; team of 4 with the neutral card; team of 4 with no confidence field | H3 | confidence pair permutation | R5:38-39 |
| Best of N ∈ {2, 4, 8, 16}, chosen by imperfect views only: syntax validator, spot check on a sealed eighth of assignments, a second agent's flag | H5 | never the oracle | PL:213; R5:45 |
| F5 proposer, then a second agent in the **Red Team** role ("refute this") or the **control solver** role, same calls and tokens | RT | one override rule for both | PL:221-222 |
| F6 auditor, a different agent from the statement author | DA | planted labels | PL:229 |

**Override rule (both RT arms).** The proposer's label stands unless the second agent supplies a counterexample that the PR checker verifies. The arms differ by role, never by decision rule (PL:222; D6). **One proposer pass per lemma is shared by both arms**, so the pairing removes proposer variance and only the second agent's role differs (D14).

**Model.** Every arm uses Inkling-2-Mini (section 11). `team.run_episode` refuses a model backend (`src/murmuration/team.py:226-227`), and `H.agent_passes` accepts only integer answers. So the R6 runner (**not built**, R6-O7) writes H2-layout rows directly, one task per episode, with `pass` from the F-oracle, and bypasses `H.run_arms`. The analysis functions consume those rows unchanged.

## 5. Task suite, ground truth and scoring

| Family | Agent output | Ground truth and checker | State at `9a015ea` |
|---|---|---|---|
| F1 SAT, #SAT, 3-CNF n ≤ 20 | witness or model count | satisfying set as a 2^n-bit integer, popcount (PL:194) | **not built** |
| F2 circuit size, n ≤ 4 | circuit, claimed size, optional "minimum" | evaluate on all inputs; M1 table (`T.min_circuit_size`, `circuit_open`) | M1 table built; **submitted-circuit evaluator not built** |
| F3 MCSP-type (truth table, s) | yes with a circuit, or no | M1 table | **not built** |
| F4 resolution refutation of a small unsat CNF | refutation | step checker; exact minimum width | **not built** |
| F5 executable lemma, planted true or false at a sealed rate | true, or false with a counterexample | exhaustive run in `PR.check_lemma` under `PR.parse` whitelist and step limit | sandbox built; **lemma generator not built** |
| F6 informal/formal pair, faithful pairs at a sealed rate | faithful, or defect and span | planted label; exact span match | **not built** |

**M1 ground truth.** W1 (dynamic programming) and W2 (enumeration) agree on all 65,536 four-input functions (`9a015ea`; `lab/tests/test_r6_m1_agreement.py`); the constant convention and partial independence are at PL:151. Tasks in `circuit_open(n)` have only a lower bound and are **excluded from F2 and F3** (D10).

**Predicates.** No agent-submitted Python runs outside `PR.parse` and `PR.check_lemma` (PL:144). Circuit-size lemmas wait until the M1 tables are registered in the PR registry (PL:142). That registry is empty at `5108519`.

**Scorecard.** `SC.validate`, `SC.gates` and `SC.score` compute G1 to G6 as PL E defines them; G3 is partly judgment (sealed pattern plus reviewer flag). Inputs: the PL E rubric weights (D18), and the sealed `briefing_keywords` and `overclaim_patterns` (R6-O3). **A gate failure never changes `pass`**; it zeroes only the rubric total (PL:235, PL:406).

## 6. Endpoints and decision rules

Conventions, from D1 to D7 (section 12):
- All intervals are two-sided 95%; the Holm family-wise alpha is 0.05 (lane decision D15, matching the 95% wording of R5:28 and L3:213; 0.05 appears in neither).
- **Kill wins** over support (L3:251; D3).
- A conjunction is an **intersection-union test**: every clause must hold, each is reported separately, and no adjustment is made (DL:205, DL:236; D4).
- **Holm:** a new fixed four-member step-down over {H1, H3, H5, RT} in `lab/r6_holm.py` (to be built, R6-O7); a member not run counts as p = 1. `H.holm_family` is **not** used: it hard-codes {H1, H3, H5} and raises on RT (H:828-837), and the pin is not edited.
- **p per member:** H1 `p_holm` = max(p_EG4, p_EG8), two-sided permutation p's, when both signs agree, else 1 (`H.h1_primary`); H3 one-sided `p_up` (`H.h3_primary`); H5 one-sided `p_up`, within-task permutation (`H.h5_primary`); RT one-sided exact within-lemma permutation, which for paired 0/1 outcomes is the exact binomial on discordant lemmas (exact McNemar), toward treatment < control.
- **The claim** = Holm rejection at 0.05 **and** the unadjusted 95% interval on the supported side; no adjusted interval. A kill reads the unadjusted interval as a stop only (L3:211-213).

| H | Endpoint | Supported | Killed | Uninformative |
|---|---|---|---|---|
| H2 | paired log-score difference (fitted c minus c = 0) at n = 8 on held-out seeds and task sets | interval above 0 **and** coverage not rejected: exact Poisson-binomial test (`H.coverage_p`) of held-out task means inside their predictive interval (IUT) | interval below 0 | floor or ceiling at n = 8 (`H.floor_ceiling_reading`); overdispersion interval contains 1 at every n; fewer than 10 reruns (R5:29) |
| H1 | EG(4) and EG(8) intervals | both on the same side of 0 (IUT, both clauses) | opposite sides | token match fails; floor or ceiling (R5:34) |
| H3 | ΔG | interval above 0; if the behaviour check's interval excludes 0, the claim is limited to teams asked for confidence | interval below 0 | parseable confidences below the SE-rule n; constant confidences; floor or ceiling (R5:42; D16) |
| H5 | S | interval above 0 | upper bound below K | every u_t is 0 or 1; max u_t^N below the SE target at every N (D16); 400 clean and 200 failure episodes not reached (R5:53) |
| RT | share of false lemmas still accepted, treatment minus control, paired by lemma; null: arm labels permuted within lemma | interval below 0 | interval above 0 | false lemmas the proposer accepts are fewer than the SE-rule n (this defines "nearly every", PL:225; D16) |
| DA | precision, recall, true-negative rate, span accuracy | rates with exact binomial (Clopper-Pearson) intervals (D5) | none | none |

RT also reports verified-refutation recall on false lemmas and the rate of unverified counterexamples on true ones (each a G2 failure, PL:224).

## 7. Denominators

- **H2:** agent rows at each n in held-out task sets and seeds; unparseable output is `pass = 0`, counted (D11).
- **H1:** token-matched episodes; the rest excluded and counted.
- **H3:** episodes with a parseable confidence; unparseable share per arm reported.
- **H5:** scored tasks; u_t from the calibration split only (R5:49).
- **RT:** planted-false F5 lemmas; planted-true ones for the unverified-counterexample rate.
- **DA:** defective pairs (recall, span), faithful pairs (true-negative rate), flagged pairs (precision).
- **Gates:** scorecard-carrying answers per gate, arm and team size; `na` excluded and counted.
- **Never counted:** P0, B0′, B1′ rows (D2).

## 8. Sample size and stopping rule

- **Rule.** For each hypothesis, choose n so that the standard error of the effect is at most min(K, E − K)/2.8, using the design effect 1 + (m − 1)·ICC (R5:18; L3:176-181). E, K, n and reruns come **from B1′ only**. B1′ cannot give ICC because it uses one task set (PL:285), so ICC needs a further source or the design effect is bounded conservatively at the freeze (R6-O12).
- **Fixed n, one analysis, no interim look** at any arm outcome (DL:238; D1).
- **Economic stop.** A batch stops at its placed GPU-hours or wall-time cap, whichever is first, and reports what it has (R6-O10, R6-O11). Outcomes the placed size cannot reach are declared at the freeze and reported inconclusive (L3:187-190). **Any hypothesis below its registered n is inconclusive and descriptive only.** Arms run **interleaved by task or lemma**, so a cap cannot cut one arm alone.
- **Line stop.** On a hard rule or Safety gate, or at the Inkling-stage expiry, **2026-12-10T04:50Z**: R0 acceptance (commit `9fc1eba`, 2026-11-26T04:50Z) plus 14 days, the planner's choice (PL:330). Then report "INSTRUMENTED, not piloted" and release any reservation.
- **Two-failure pivot.** A floor or ceiling at n = 8 in B0′ blocks B1′ (DL:303). The dial may be reset once and B0′ repeated under a new admission; a second floor or ceiling closes the line (L3:195-196).

## 9. Stages

| Stage | Content | Gives | State |
|---|---|---|---|
| A, offline | Scripted agents with planted values through H at `d0c67d7` (PL:313) | planted values recovered; nulls match closed forms; a planted gate failure leaves `pass` unchanged | **Not evidenced on R6-TS** (section 15) |
| P0 | Probe of the resident slot (section 10) | T, slowest generation rate, output cap, seed behaviour | YES in principle (DL:303); not admitted |
| B0′ | One task set × 1 rerun at n ∈ {2, 4, 8}: 28 calls × T (PL:284; R5:68) | cost per call, floor/ceiling at n = 8 | R5's B0 request, decided YES (DL:303), applied to R6-TS; its 0.277 GPU-h was a Qwen figure and is void until T is measured |
| B1′ | One task set × 10 reruns: 280 calls × T (PL:285) | rerun SD of the H2 log-score difference; confidence parse share | R5's B1 request, decided YES conditional on no floor or ceiling at n = 8 (DL:303), applied to R6-TS; its 2.592 GPU-h is void until T is measured |
| Main | Sized from B1′ only (section 8) | confirmatory analysis | separate request |

B0′ and B1′ size H2 only; the H1, H3, H5, RT and DA arms are sized from B1′ and requested separately, and an unplaced request leaves that hypothesis inconclusive (PL:286). "One task set" is one task from one family that the line author names, so the 28 and 280 call counts reserved at DL:303 hold. Other families' dials stay OPEN until their own probe (R6-O4, R6-O17).

## 10. P0 probe design and admission prerequisites

**Why P0 is not harmless** (PL:265): any call evicts another lane's cached prompt (about 33.7k tokens), and an idle check races with other clients.

**Prerequisites. All are required, in this order.**
1. This protocol frozen, with a freeze record for batch `r6-p0` and `admit` passed by G (section 14).
2. Written notice **before** and **after** the window, to: the PC coordinator, who runs the OmniRoute fallback hop; the Spark service owner; and every known direct user of `:8011`. A routing window does not stop direct clients.
3. A quiet window. It means taking the Spark hop out of OmniRoute routing, which AGENTS.md reserves to the owner. So the **owner** agrees it with the PC coordinator.
4. The service owner is named in the PC placement.
5. Identity, read-only on the Spark **before the freeze** (D12; R6-O9), so `model_snapshot` holds it at `admit` (no request to the service): Q8_K_XL and mmproj sha256, runtime build, server pid and start time, sha256 of `/proc/<pid>/exe`, inode of the GGUF mapped in `/proc/<pid>/maps`.
6. The F1 generator is built and reviewed (R6-O5), because P0's prompts are F1 whatever the pilot family.

**Steps** (PL:274-276):
- Read-only: record the server's reported model, context and slot count, and confirm the endpoint names against the resident build. Re-check the pid, start time, exe hash and GGUF inode against the freeze. **Any mismatch stops P0 before the first call.**
- Twelve generation calls, strictly one in flight. Inputs of about 200, 1,000 and 2,000 tokens, × output cap 64 and 300, × 2 same-seed repeats. Synthetic F1 prompts only, from the sealed pilot pool.
- Per call: client wall time; server prompt and generation token counts and times; queue wait (wall minus server times); finish reason; reasoning-token share; whether repeats match.

**Stops, whichever comes first:** 12 calls; 15 minutes wall; **2 errors in total** (D13); a **skip spike** (two calls that find the slot busy or wait over 60 s); 300 s per-call timeout. No retry loop. The 60 s and 300 s are the planner's choices (PL:278).

**P0 gives** T (worst wall time per call, queue included), the slowest generation rate, the output cap and seedability; **no pass rate, variance or ICC** (PL:280).

**Client.** CL encodes `max_consecutive_errors: 2`; this protocol registers 2 errors **in total**. No request is sent until CL is aligned, reviewed, committed and stub-tested (R6-O8).

## 11. Resource and budget limits

| Limit | Value | Source or holder |
|---|---|---|
| Hosted plan | USD 0 | PL 6.5; every gate call uses `--hosted-cap 0` |
| Hosted stop | USD 0 | PL 6.5 |
| GPU-hours, P0 | bound min(15 min, 12 × 300 s) = 0.25; placement OPEN | PL:278; PC placement (R6-O10) |
| GPU-hours, B0′ | OPEN: 28 × T | PC placement, after P0 (R6-O10) |
| GPU-hours, B1′ | OPEN: 280 × T | PC placement, after B0′ (R6-O10) |
| GPU-hours, secondary arms and main | OPEN | line author computes from B1′; PC placement |
| Wall-time cap per batch | P0: 15 minutes (PL:278); others OPEN | PC placement (R6-O11) |
| Host memory stop | 10 GiB MemAvailable before each batch | PL:256 |
| Residual draw | whether calls to a resident service draw on the residual 9.4 GPU-h; until decided, wall time counts (PL:261) | PC placement |

**Model** (PL:241; DL:295; not re-read here): `Inkling-2-Mini-UD-Q8_K_XL.gguf` with `mmproj-F16.gguf`, alias `Inkling-2-Mini`, on `100.91.57.48:8011`, `--ctx-size 131072 --parallel 1`; one shared slot that is also the last-resort OmniRoute fallback hop for other lanes. **Reuse only:** never restart, copy or reconfigure it. Unknown cost is never zero.

## 12. Method decisions (line author under the owner approval of 2026-11-26, DL:303)

The freeze confirms or replaces each decision. The independent reviewer checks each one (R6-O20).

| ID | Decision | Rule applied |
|---|---|---|
| D1 | Fixed n per hypothesis, one analysis, no interim look | DL:238; PL:317 |
| D2 | Pilot data (P0, B0′, B1′ task sets, seeds and rows) are excluded from every confirmatory analysis. The main-run sets, seeds, planted labels and keyword lists are sealed before P0 | R5:72; PL:287 |
| D3 | Kill wins: if a kill and "supported" both apply, the result is not supported | L3:251 |
| D4 | Intersection-union for every conjunction (H2 interval and coverage; H1 both intervals) | DL:205; DL:236 |
| D5 | Exact tests and bounds: the H2 coverage test (exact Poisson-binomial, `H.coverage_p`); DA and gate rates by Clopper-Pearson. Floor/ceiling keeps the pinned point rule (`H.floor_ceiling_reading`: rate ≤ edge or ≥ 1 − edge) | R5:28; H at `d0c67d7` |
| D6 | The same override rule in both RT arms | PL:222 |
| D7 | Holm across the secondary family; the kill reads the unadjusted interval as a stop only | L3:211-213; R5:20 |
| D8 | **Deviation from PL:214-217:** H1 is instantiated on R6-TS, separately from R5's H1 (PL:215). The Holm family is {H1, H3, H5, RT}, size 4, fixed if one is not run, in `lab/r6_holm.py`. **This changes the decision rule:** the first step's threshold moves from alpha/3 to alpha/4, so an RT result that passes under PL:217 can fail here. To be recorded in DL | coordinator brief; H |
| D9 | **Deviation from PL:211 ("per family"):** one pooled H2 primary; per-family results are descriptive, since six per-family primaries would be hidden multiplicity. To be recorded in DL | one primary contrast (R5:18) |
| D10 | Tasks in `circuit_open(n)` are excluded from F2 and F3 | the pass must be decidable (PL:190) |
| D11 | A row without parseable output counts as `pass = 0` and is counted | the oracle decides pass (PL:211) |
| D12 | Identity taken before the P0 freeze, re-checked at P0 step 1; mismatch stops P0 | `model_snapshot` needed at `admit` (PL:243, PL:274); a file hash alone does not tie the running process to it |
| D13 | The P0 error stop counts 2 errors in total, not consecutive | PL:278 says "2 errors"; total is the stricter reading |
| D14 | One proposer pass per lemma, shared by both RT arms | the pairing isolates role (PL:222) |
| D15 | Intervals are two-sided 95%; Holm alpha is 0.05 (lane decision matching the 95% intervals; 0.05 is not written in the cited sources) | R5:28; L3:213 |
| D16 | (a) `edge` = 0: floor/ceiling = every row fails or every row passes, the only case that leaves (q, c) unidentified. (b) H3 uninformative if parseable confidences < its SE-rule n. (c) H5 "negligible": max u_t^N < min(K, E − K)/2.8. (d) RT "nearly every": accepted false lemmas < the RT SE-rule n | tied to the SE rule (R5:18) or identifiability; no new constant |
| D17 | B = 10,000 resamples and 10,000 permutations; no exclusion cap (no endpoint is a ratio); seeds sha256 of `tag:seed:task` | EP1.md:692; H1.md:128; L3:202 |
| D18 | PL E weights by default; an owner override is optional and does not block | PL E |

## 13. OPEN items blocking a freeze

"Person": only a named person or a role outside this line closes it.

| ID | Decision still needed, and the method to set it | Holder | Person |
|---|---|---|---|
| R6-O1 | Rename to `prereg/R6-protocol.md` and commit locally at or after `9a015ea` (and so after `c0daf55`, DL:242) | line author | no |
| R6-O2 | Name the custodian (not the author, not a runner) | owner (Alejandro) | **yes** |
| R6-O3 | Seal the main-run task sets, seeds and seed map, the F5 false rate, the F6 faithful rate, the F6 defect spans, the H5 spot-check eighth, the H3 confidence wording, the neutral card, the RT and control role texts, `briefing_keywords` and `overclaim_patterns`. Path, sha256 and custodian for each | custodian | **yes** |
| R6-O4 | Pilot task: the line author names the family; the custodian draws it from a pool disjoint from the main pool and seals it before P0 | line author; custodian | **yes** |
| R6-O5 | Build the F1, F3, F4, F5 and F6 generators and checkers and the F2 submitted-circuit evaluator. Each needs an independent review with every targeted mutant killed (DL:275) | line author (Sonnet worker); independent Opus reviewer | no |
| R6-O6 | Run R6 Stage A on the R6-TS checkers through H at `d0c67d7`. Acceptance is the PL:313 criteria | line author; reviewer | no |
| R6-O7 | R4 work list. Episode runner writing H2-layout rows with the oracle pass (team, nominal, best-of-N, RT, DA), interleaved by task or lemma. Also code absent at the pin: `lab/r6_holm.py` (fixed four-member Holm, section 6), the RT paired difference with its exact within-lemma test and bootstrap interval, and Clopper-Pearson intervals. Stub-tested, mutants killed, reviewed | line author; reviewer | no |
| R6-O8 | CL: align the error stop to the total count (D13), review it, commit it, and run `test_r6_inkling_client` against a stub only. Also extend `lab/r5_gpu_readiness.py` to allow the resident process and hash a GGUF (PL:255) | client author; reviewer | no |
| R6-O9 | Identity of D12 (file hashes, pid, start time, exe hash, GGUF inode), read-only on the Spark before the P0 freeze. An upstream hash is a separate gated network step | line author on the Spark | no |
| R6-O10 | GPU-hours per batch: P0 ≤ 0.25; B0′ = 28 × T; B1′ = 280 × T; secondary arms and the main run from B1′. Also whether the resident service draws on the residual | PC placement (DL:303) | **yes** |
| R6-O11 | Quiet window (the Spark hop taken out of OmniRoute routing); before and after notice to the PC coordinator, the Spark service owner and direct `:8011` users; wall-time caps for B0′ onward; service owner named | owner (routing); PC coordinator; PC placement | **yes** |
| R6-O12 | E, K, n and reruns per hypothesis by the SE rule from B1′; the ICC source or a conservative design-effect bound; reachable outcomes at the placed size | line author computes; reviewer checks | no |
| R6-O13 to O16 | **CLOSED** by D15 to D18 (line author; freeze confirms) | — | no |
| R6-O17 | Difficulty dial (n, size bound, clause ratio): from B0′ for the pilot family; from each other family's own probe, requested separately | line author; PC placement | no |
| R6-O18 | M2 meter k, c, s, if any scorecard fills `meter` (PL:154) | line author | no |
| R6-O19 | The owner confirms that AP-D1 (AP:166) covers H5, which sits near the monitor-selection rule (R5 section 5) | owner | **yes** |
| R6-O20 | Independent review of this protocol, including D8 to D18, and DL entries recording the D8 and D9 deviations | independent Opus reviewer; line author writes DL | no |
| R6-O21 | Admission records for each batch: owner words, UTC window, max window hours, batch id | owner | **yes** |
| R6-O22 | Output cap and per-call timeout for B0′ and later, from P0 | line author | no |
| R6-O23 | Register any PR circuit-size functions only after M1 is accepted (PL:142); otherwise F5 excludes circuit-size lemmas | line author; reviewer | no |
| R6-O24 | `rt_min_accepted`: the minimum number of false lemmas the proposer must accept for the Red Team contrast to be informative (required config key of `lab/r6_stage_a.py`); set by the pilot's SE rule (R5 plan:217) from B1′, frozen before the main run | line author (delegated, protocol line 7) | no |

## 14. What the freeze record must contain

Created by `python3 -m lab.tremor_freeze_skeleton prereg/R6-protocol.md --batch <id> --out <freeze> --input <path>...`; G refuses it until every key is filled. One record per batch (`r6-p0`, `r6-b0`, `r6-b1`, main).

1. **Protocol sha256** of this file at the frozen commit (`protocol_sha256`, computed by the skeleton from `git cat-file`; `protocol_path`, `batch`).
2. **Code tree hash** at the pinned commit (`commit`, `tree`, computed). Also the config hash (`config_hash`): sha256 of the frozen run config (arms, sizes, caps, CL stops, output cap, rubric weights).
3. **Protected inputs** (`protected_inputs`), each with path, sha256 and custodian: every item of R6-O3 and R6-O4. Paths must be under the repo and contain no symlinks (G:153-165).
4. **Model snapshot** (`model_snapshot`): the D12 identity (Q8_K_XL and mmproj sha256, runtime build, pid, start time, exe sha256, GGUF inode), the alias, the server arguments and the endpoint, plus the note "local identity, not upstream verified". Also `task_family_revision` (the generator and checker commits for F1 to F6 and the M1 table commit `9a015ea`); `scorer_ids` (SC commit and function names, PR commit, F1 to F6 checker names); `contrasts` (H2 primary, the Holm family {H1, H3, H5, RT}, DA descriptive); `stopping_rules` (section 8 and the P0 stops); and `expected_and_max_resources` (calls, T, GPU-hours, wall cap).
5. **Resource limits** (`reserved_gpu_hours`, `hosted_usd_plan` = 0, `hosted_usd_stop` = 0) from section 11.
6. **Approval and review evidence** (`approval_review_evidence`), quoted exactly: DL:303; the independent review of this protocol; the reviews of SC, PR, T, CL, `lab/r6_holm.py` and the F1 to F6 checkers; the custodian's attestation that the main-run inputs were sealed and unread before P0; and, for `r6-p0` only, the notice message ids (before and after), the owner's agreed quiet window and the named service owner.
7. **D1 basis** (`d1_basis`): AP-D1 (AP:166) and the owner's confirmation for H5 (R6-O19).
8. **Inherited pins** (`inherited_pins`; the skeleton finds this item by the words "inherited from the M3", the label the other protocols use): H `d0c67d7`, T `9a015ea`, SC `fa03232` and `28610e1`, PR `caf0643` and `5108519`, the G floor `c0daf55`.
9. **The admission** (G `_ADMISSION_KEYS`): `batch`, `one_use` true, `used` false, `valid_from_utc`, `valid_until_utc`, the limits, `owner_words` and `freeze_record_sha256`. It passes `check` and then `admit` with `--hosted-cap 0 --gpu-cap <placed> --max-window-hours <h>`.

A freeze authorises no run; no request reaches the service before that batch's `admit` succeeds (PL:298).

## 15. What is unverified

- **Briefing claims** (PL:12): no step depends on any 2025 to 2026 item.
- **Stage A "done by scripted agents"** (coordinator brief): H's `d0c67d7` tests cover R5 recovery only; the R6-TS checkers do not exist (section 5). A **briefing claim, unverified**.
- **Q8 identity:** not computed; `SHA256SUMS` has no Q8_K_XL entry (PL:243).
- **Live server values** (PL:241, not re-read); the 33.7k cached prompt (server log); endpoint names; seed behaviour; reasoning-token use.
- **B0 0.277 and B1 2.592 GPU-h:** Qwen figures (R5:68-69), void for Inkling.
- **G on a real R6 record**; the readiness extension; CL; the recalled cross-checks (`T.crosscheck_report`, not re-run here).

## 16. Risks

- **Shared slot:** no quiet window means no Inkling stage; P0 evicts another lane's cache even inside one, and an unknown direct client can still arrive (the skip-spike stop catches it).
- **Ceiling:** handled by the dial and the two-failure pivot, or the line closes.
- **Pooled H2:** family heterogeneity can inflate c and overdispersion; per-family readouts show it without a claim.
- **H1 cost:** nominal and token-matched arms at n = 8; unplaced means inconclusive, family still size 4, and the alpha/4 first step costs power for RT (D8).
- **Unbuilt pieces** move the code tree; the freeze pins the final commit.
- **Determinism:** unseeded reruns cannot be replayed.
- **Memorization:** sealed random seeds are the control.
- **Keyword lists** catch wording, not meaning.
- **Identity:** a local hash misses a bad download.
- **Expiry** may come first.
