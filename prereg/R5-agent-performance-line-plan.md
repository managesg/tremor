# R5 plan: agent performance line (can a team's success be forecast, and is its self-report accurate)

**PLAN, revision 4. Not frozen; no run, spend or admission authority.** 2026-11-25, HEAD `f09f47b`. Every number has a repo source or says "from pilot".

Keys: P `docs/PROPOSAL-RESIDENCY-V3.md`; in `docs/reports/tremor/`: AR `ADMISSION_RECORD_20261125.md`, ADM `OWNER_DECISION_protected_admissions_M3R3_M4_M9.md`, DL `DECISION_LOG.md`; SR `docs/reports/workplan-ep/Spark-readiness.md`; EP `prereg/EP1.md`; L2/L3/L4 `prereg/R2-L*-C-protocol.md`; M7 `prereg/M7-grover-protocol-draft.md`.

## 1. Gap

Every existing line tests an **allocation rule** against a baseline (P:11-14, P:81-86). None tests whether a team's **task performance can be predicted out of sample**, or whether what a team reports about itself is accurate.

- "Nothing here depends on capability" (P:1020-1021).
- Primary endpoints elsewhere: L2-C adoption share (L2:30-32); L3-C catch-rate loss ratio (L3:31-33); L4-C false-note share and token ratios (L4:36-38); L7 error correlation and share acting (P:738-744); M7 regime tests (M7:32-33, M7:44-46); EP-1 one card contrast, one tier (EP:118-125).
- No calibration readout exists (`src/murmuration/readouts.py:17-128`); `src`, `lab` and `prereg` contain no Brier, ECE or stated confidence.
- Falsifier 2 (P:994-996) has no test linking a statistic to later success.

## 2. Hypotheses

Rules from P: n is task sets, three or more reruns each, cluster bootstrap, **one primary contrast** (P:178-179); a variance needs 10 reruns (P:286-288); SE at most min(K, E − K)/2.8 with the design effect (P:180-188); "not significant" is inconclusive (P:59-62). **E, K, n: from the B1 pilot by that rule; ICC needs a further source.**

**Primary: H2.** Reason: it is the gap itself; it needs no new reply field and no L3-C or L4-C run; floor and ceiling are checked in B0. **Secondary, Holm, family size 3: H1, H3, H5.** The size stays 3 if one is not run. Each is reported alone.

**H2 (primary). Small teams forecast larger ones.**
- Estimand: held-out log score of the pass-count distribution at n = 8 (the Claude cap, P:759), predicted from (q, c) fitted at n in {2, 4}. Pass count X = the number of **agents** in an episode whose own submitted work passes the oracle (one 0/1 row per agent); it is not EP-1's Y, which counts work slots (EP:118-119).
- Model: with probability c all agents fail together, otherwise each fails independently with probability q; P(all fail) = c + (1 − c)·q^n, the `all_miss` of `nulls.correlated_monitors(n, q, c)` (`nulls.py:134-147`, needs n ≥ 2; n = 1 uses the closed form 1 − q for a pass).
- Arms: forecast with fitted c; forecast with c = 0. No confidence field in these runs.
- Null: independent agents, X ~ Binomial(n, 1 − q) (`nulls.scripted_adopters`); overdispersion 1 (`readouts.overdispersion`).
- Primary endpoint: paired difference in log score on held-out seeds and task sets.
- Supported: 95% interval above 0 and coverage not rejected: exact two-sided binomial test of the count of held-out task-set means inside their 95% predictive interval, against 0.95. Killed: interval below 0.
- Uninformative: floor or ceiling (P:1009-1010); overdispersion interval contains 1 at every n; under 10 reruns.

**H1 (secondary; a forecasting extension of line 7).** Line 7 owns ρ̄ and share acting (P:738-744); EP-1 owns Y under a card. R5 adds only: does the sign of EG(4) forecast that of EG(8)? EG(n) = Y_team(n) − Y_nominal(n) (`stats.emergence_gain`, `stats.nominal_group`), equal tokens.
- Null: EG = 0; team and nominal labels permuted within task set.
- Supported: both intervals on the same side of 0. Killed: on opposite sides.
- Uninformative: token match fails; floor or ceiling.

**H3 (secondary). Team confidence outruns team accuracy.**
- Estimand: G = mean stated confidence − pass rate per episode; ΔG = G_team(4) − G_solo.
- Arms: solo; team of 4; team of 4 with the neutral card (P:155); **team of 4 with no confidence field**.
- Null: each episode's (confidence, pass) **pair** is permuted together across arms within task set; both terms of G are then exchangeable, so E[ΔG] = 0.
- Behaviour check: pass rate with against without the field. If its interval excludes 0, H3 holds only for teams asked for confidence.
- Supported: interval above 0. Killed: interval below 0. Secondary readout: Brier score.
- Uninformative: unparseable or constant confidences (share from B1); floor or ceiling.

**H5 (secondary). Best-of-N buys fewer than N independent draws.**
- Selection rule: the candidate with the fewest view flags, first wins ties (new; not the pressured `l3c_harness.best_of_n`). **When no candidate is clean, candidate 0 is returned and reported as flagged** (DL:217).
- Per task t: a candidate fails with probability f_t; a failing one looks clean with probability a_t; passing candidates get no false flags. One draw is not clean with probability u_t = f_t(1 − a_t), estimated on a calibration split.
- Endpoint: S = mean over tasks and over N in {2, 4, 8, 16} (16 from P:460) of [observed P(no clean among N) − u_t^N].
- Sign: assume an episode's N draws are exchangeable, independent given a hidden state θ, with not-clean probability u(θ) and mean u_t. Then P(no clean) = E[u(θ)^N] ≥ (E[u(θ)])^N = u_t^N (Jensen; x^N is convex). Non-negative association only raises it, at every N, so no signs mix. S > 0 reads as "fewer than N independent draws".
- Conditions of the argument (Opus review): u_t is estimated on episodes kept apart from the scored ones, with the same spread of hidden states; the hidden-state distribution is the same for every N; plugging the estimate into u_t^N biases S downward (Jensen again), so S is conservative and B1's K must allow for that bias.
- What breaks it: negatively dependent draws (candidates made deliberately different, a shared budget, a small pool sampled without replacement) or order effects (draws not exchangeable). The protocol checks the rate by draw position.
- Supported: 95% interval above 0. Killed: upper bound below K (K from B1 by the SE rule).
- Description only: the failure rate of the selected output given a clean candidate, and D = gap_t(N) − gap0_t(N), where gap = P(selected is reported clean and fails the oracle) (P:163) and gap0_t(N) = [1 − u_t^N] · f_t·a_t / ((1 − f_t) + f_t·a_t). D mixes a downward and an upward (convexity) effect and carries no claim.
- Uninformative: every u_t is 0 or 1; u_t^N negligible at every grid N; 400 clean and 200 failure episodes not reached (P:189-190). Boundary: P:980.

**H4 is not registered here.** "Night t false share predicts day t+1 pass rate" is secondary analysis of L4-C data. **Request to the L4-C author:** register it in the L4-C freeze before L4-C runs (section 16 lock is open, AR:11; L4:359-372), with its null (false share permuted across nights within chain). Otherwise R5 does not analyse it. This line takes no second reading of seen data.

## 3. Design

**Reused.** `team.run_episode` (scripted), `stats`, `analysis.error_correlation`, `readouts`, `monsel.ensemble_catch`, `l3c_harness` (pool checks, `bootstrap_ratio`), `spend.Ledger`, the gate, the skeleton.

**New.** `lab/r5_perf_harness.py`: arm-by-size loop over `run_episode`; common-cause fit and log score; `calibration_gap`, `brier`, pair permutation; the H5 no-clean rate and gap. No model backend is written: `run_episode` refuses one (`src/murmuration/team.py:226-227`) and M3 R3-L2 already owes the native launcher (AR:9).

**Stage A, offline (no spend).** Scripted agents with planted q, c, confidence bias and per-task f, a. Each estimator recovers its planted value; each null its closed form.

**Stage B, local GPU.** Read-only check 2026-11-25: one NVIDIA GB10, unified memory, 121 GiB host, 80 GiB available, a resident llama-server at 27.5 GiB. Fits: Qwen3.5-4B at `data/hf/Qwen3.5-4B` with `MANIFEST.sha256.json`, revision `851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a` (SR:119), peak 8.543 GiB (SR:137); Qwen3.5-0.8B on disk. Not available: SmolLM3-3B (DL:259). Launch gate: a fresh `MemAvailable` of at least 70 GiB (DL:15).

- **Cost per call, upper bound:** 300 output tokens (EP:985) ÷ 9.07 tokens/s (SR:133) = 33.08 s. Calls per episode: 2 per agent (8 for 4 agents, EP:987; `team.py:221` defaults).
- **B0, cost and floor/ceiling probe only.** One task set × 1 rerun at n in {2, 4, 8}: (4 + 8 + 16) = 28 calls × 33.08 s = 926.13 s, + 71.094 s load (SR:132) = 997.2 s = **0.277 GPU-hour**. **B0 gives no SD and no ICC and does not set H2's n.** It gives the measured cost per call and the floor/ceiling reading at n = 8.
- **B1, variance pilot, a separate request.** One task set × 10 reruns (P:287) at n in {2, 4, 8}: 280 calls × 33.08 s = 9,261.3 s, + 71.094 s = 9,332.4 s = **2.592 GPU-hours** (28% of 9.4). Conditions: B0 shows neither floor nor ceiling at n = 8, and the measured cost per call replaces 33.08 s. B1 gives the rerun SD of the log-score difference. **It cannot give ICC** (one task set); ICC needs the approved variance pilot (unreleased, AR:11) or a further request.
- **Requests, not taken.** Each is to be named in the resource owner's placement request against the residual, 9.4 after SmolLM3's 0.1 (ADM:30), which L4-E, Grover and the controller also claim (ADM:248), after the ledger is reconciled (ADM:22). Each reservation is also the wall-time stop (prompt time unmeasured); unused time is released at settlement (SR:139).
- **Main run (B2):** sized from B1 only, n from the SE rule × measured cost; a third request. If it does not fit, the rest is inconclusive (P:960-963).
- **Pilot data are excluded** from every confirmatory analysis: the B0 and B1 task set and seeds are named in the protocol and never enter B2, whose sets and seeds are sealed before B0.

**Stage C, hosted: none proposed.** The USD 10 paid cap is shared by M2, M7 and D8 (AR:3) and is a code constant (`spend.py:48`); no source allocates any here.

## 4. Work plan

| Phase | Work | Owner | Acceptance |
|---|---|---|---|
| 0 | Plan re-reviewed | independent Opus; line author decides | verdict in DL |
| 1 | Harness, tests, planted-value recovery, mutants | Sonnet; independent Opus | every targeted mutant killed (DL:275) |
| 2 | `prereg/R5-protocol.md`, L2-C layout | Opus drafts; independent Opus | no OPEN method item |
| 3 | Seal held-out seeds, task sets, confidence wording | **custodian named by the owner** (not author, not runner) | path, sha256, custodian in the record |
| 4 | B0 probe, then B1 pilot: each with placement, freeze, admission | Sonnet runs; Opus verifies | `admit` passes; ledger settled |
| 5 | Numbers from B1; B2 freeze, admission, run | same | fixed n, no interim look (DL:238) |
| 6 | Report per hypothesis | Opus | independent reconstruction from traces |

Tests (run at `f09f47b`: 161 lab, 158 package, OK):
```
PYTHONPATH=src:. python3 -m unittest lab.tests.test_l3c_harness lab.tests.test_l4c_harness lab.tests.test_tremor_admission_gate lab.tests.test_tremor_freeze_skeleton
PYTHONPATH=src python3 -m unittest tests.test_nulls tests.test_spend tests.test_readouts tests.test_stats
PYTHONPATH=src:. python3 -m unittest lab.tests.test_r5_perf_harness   # new
```
Admission path, per GPU batch, in this order:
```
python3 -m lab.tremor_freeze_skeleton prereg/R5-protocol.md --batch <id> --out <freeze> --input <path>...
# author and custodian fill every empty field; the owner's admission record is written
python3 -m lab.tremor_admission_gate check <freeze> <admission> --now <utc> --hosted-cap 0 --gpu-cap <placed> --max-window-hours <h> --owner-words "<exact>"
python3 -m lab.tremor_admission_gate admit <freeze> <admission> --now <utc> --hosted-cap 0 --gpu-cap <placed> --max-window-hours <h> --owner-words "<exact>"
```
No GPU process starts before `admit` succeeds. The pinned commit is at or after `c0daf55` (DL:242).

**Expiry and fallback.** Stage B depends on three things with no date: the R3-L2 launcher, a named custodian, and (for H5) the L3-C pool. This plan's Stage B expires 14 days after Phase 0 acceptance (the author's choice; the owner may replace it). On expiry the line reports "INSTRUMENTED, not piloted" (P:45-46), makes no claim, and releases any reservation.

## 5. Risks and what is unproven

- **Nothing is evidenced** (P:47).
- Pilot leakage: excluded in writing (section 3); unproven until the custodian seals B2's inputs first.
- A confidence field can change behaviour: see the no-confidence arm; H2 runs without it.
- Undated dependencies (launcher, L3-C, L4-C, custodian): see expiry.
- Floor or ceiling on a 4B model with integer-sum tasks (P:1020): checked in B0; may end the line there.
- No correction across hypotheses: no combined claim is made.
- GPU bounds assume 300 tokens per call at the slower rate of two short single-stream prompts (SR:146-148).
- The residual is oversubscribed (ADM:248); B1 alone is 28% of it and may not be placed.
- H5 sits near the monitor-selection rule; the owner confirms D1 covers it (P:980).
- Unverified: the gate on a real R5 record.
