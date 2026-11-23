# TREMOR goal and work plan

Recorded November 23, 2026 (UTC), by the one TREMOR chat in the Spark `seabridge_development` lane, Orca session `claude_bb451a1d_cd2f_4c9f_8c91_ccb964f9bd06`. Repository `/home/adelmar/SeaBridgeAI/murmuration`, branch `master`, HEAD `d897860`. **Acceptance: 1/10.** M10 offline evidence is accepted at local scope, but M10 is not counted as accepted.

## Goal, verbatim

The goal registry's text starts with the stray character `l`, which is kept here unchanged.

```text
l Complete all ten TREMOR research milestones on Spark by Wednesday morning, November 25, 2026, following docs/reports/workplan-ep/Execution-plan-20261123.md. MET when every milestone has independent acceptance, applicable backend and frontend checks have recorded commands and results, resource use is reconciled, and verified local commits and a Local Coordinator handoff exist. The earlier lane stop was lifted by the November 21 owner directive. For a blocked row, record ONE blocker line with its owner, evidence and next action, continue independent work, and report WAITING only when no executable row remains. At the Wednesday morning checkpoint, report every unmet criterion.
```

## Work plan

Paths are relative to the repository root.

- [x] **M1 DONE · Spark calibration.** The guarded Qwen R2 run, exact teardown and 0.023123 GPU-hour settlement are accepted. Evidence: `docs/reports/workplan-ep/Spark-readiness.md#calibration-result-and-settlement`.
- [ ] **M2 BLOCKED · Pilot 4 and EP-1.** Offline retry and B4 reply custody were exercised. Pilot 3 criterion 2 still fails, with 263 output tokens against a 150 ceiling. Evidence: `runs/pilot4-full-retry.ZwWZHE/OWNER_PACKET.md` and `runs/m2-enabled-response-custody.cHx1kP/OWNER.md`.
  - **Blocker owners:** Alejandro, the preregistration author, and the spend and driver reviewers.
  - **Needed:** D8 hold release; wording, scoring and order decisions; pricing and driver clearance; named release. After that, seven Pilot 4 checks, the EP-1 freeze and 60 admitted episodes.
  - Gate register: `docs/reports/workplan-ep/Pilot4-pricing-verification-gates.md`.
- [ ] **M3 OPEN, partly blocked · CPU benchmark and R3.** All 351 files and modes match the X42 nominated cut. The source manifest hash is `e972484a4db7c24f75058bf904c273545a4a4684a6dcc370caed2de44b1726de`; the binding target is `1c7b3af9433d17528ed093aaeacab1fb3d919af6265dbe46482455dc530dd7f4`. Zero of the three archived host windows are eligible. The R3 L5 CPU interruption receipt is verified. Evidence: `runs/tremor-chat-intake.f0VZwV/OWNER.md` and `runs/r3-l5-real-cpu-interruption.VMBB6X/verified.json`.
  - **X42 blocker owners:**
    - Source owners decide whether to adopt the BtUauk grader fix (`runs/r1-execution-consistency.BtUauk/OWNER.md`).
    - PC 7ce2c340 then launches the designated bench reviewer, or delegates the launch to this lane.
    - The N2 custodian supplies the sealed commitment.
    - The Assistant reviews the host evidence.
  - **X42 Gate R1 bench verdict: REJECT** on e972484a (`runs/x42-r1-bench-verdict.uPqmQ9/VERDICT.md`, EVIDENCE `a770a1dd…`). The reviewer was a fresh-context Opus subagent briefed with interrogate, launched under the owner's chat authorization. Rows 159 (no `susceptibility.py`), 162 (missing L4 and L6 nulls) and 165 (no technique modules) are REJECT. Rows 155, 157, 167 (custody-gated) and 169 are INCOMPLETE. Row 158 is ACCEPT with a caveat.
  - **Defect D1 fixed:** local commit `899ffeb`. Undefined Kish values now return None. Lab 384 OK and package 776 OK on a clean archive (`runs/commit-suite-d1fix.5AglpS`, EVIDENCE `1a17ed73…`).
  - **Next for M3 R1:** build the missing row-159, 162 and 165 deliverables, then get a fresh PC nomination and a bench re-review. Owner: this lane for the build. The preregistration author owns definitions such as "contention above 1".
  - **R3 L2/L5 blocker owners:** the runner owner, custodian, admission reviewer and Alejandro. Register: `docs/reports/workplan-ep/R3-L2-admission-inventory.md`.
- [ ] **M4 BLOCKED on protocol freezes · L1–L8.** Offline L7 rotation and L8-D lineage groundwork exist. Evidence: `runs/m4-l7-combined-rotation.X5jf6W/OWNER.md`.
  - **Blocker owners:** the line authors, custodians and reviewers. Alejandro owns the R2 sensitivity release.
  - Register: `docs/reports/workplan-ep/R2-R4-protocol-readiness.md`.
- [ ] **M5 BLOCKED · L4-E to L8-D.** The Qwen loader and hook receipt exist. Evidence: `docs/reports/workplan-ep/Qwen-base-cpu-hook-receipt.md`.
  - **Blocker owners:** the trainer, protocol author and L8-D custodian.
  - Packet: `runs/l4e-prospective-trainer.QIXxzB/coordinator-packet.md`.
- [ ] **M6 BLOCKED · Coordination.** Public matched-traversal controls exist. Evidence: `docs/reports/workplan-ep/Topology-matched-traversal.md`.
  - **Blocker owners:** the author, custodian and resource reviewer.
  - Packet: `runs/topology-two-round-joined.FRL4cn/owner-packet.md`.
- [ ] **M7 BLOCKED · Grover and quantum simulator.** Release and fallback replay exist. Evidence: `docs/reports/workplan-ep/Grover-topology-scripted.md`.
  - **Blocker owners:** EP-1 (see M2), the Grover authors, the custodian and scorer, and the resource reviewer.
  - Packet: `runs/grover-statistical-envelope.6Cln7i/OWNER.md`.
- [ ] **M8 BLOCKED · SmolLM3 second family.** The V3 reserve-to-settlement binding is done offline. Evidence: `runs/m8-worker-runtime-binding.DV7iql/OWNER.md`.
  - **Blocker owners:** the storage operator, admission issuer and resource owner. They provide backing storage, the memory and runtime window, a 0.1 GPU-hour reservation and one-use admission.
  - Packet: `runs/smollm3-native-owner.vt3Sj1/OWNER.md`.
- [ ] **M9 BLOCKED · Combined controller.** Scripted controller coverage exists. Evidence: `runs/controller-cluster-join.iJZn9z/OWNER.md`.
  - **Blocker owners:** the integration author, task custodian, claims reviewer and witnesses.
- [ ] **M10 PARTLY ACCEPTED · Report, resources and release.** The Assistant accepted the offline release and reader evidence at local scope (`msg_805f62c63b42`, relayed by PC).
  - **Accepted files:** `runs/tremor-chat-intake.f0VZwV`, with `OWNER.md` prefix 3d744345, `EVIDENCE.sha256` prefix 6590b891 and `FRONTEND.sha256` prefix 6800c876.
  - **Recorded:** in `docs/reports/workplan-ep/Execution-plan-20261123.md`, local commit `d897860`.
  - **Blocker owners:**
    - The release owner and Alejandro own release adoption and G8 sharing.
    - The claims reviewer and resource owner own the provider Console totals and T7 accounting. The provisional 4.0 GPU-hour T7 hold stays until it is backed by evidence.
- [ ] **Goal registry BLOCKED.** The chat goal is null and the registry reports `paused`. **Blocker owners:** PC 7ce2c340 and the Assistant `codex_c125641a`.
- [ ] **Cross-cutting, OPEN, this chat.**
  - Keep the evidence boundaries and one-writer ownership.
  - Commit only verified local work.
  - Reread this plan hourly.
  - Report every unmet criterion at the Wednesday morning checkpoint.
  - The integrated test receipt is in `runs/wednesday-current-integrated.kzSQSv`: cut `9a611c0`, 372 lab and 767 package tests passed, one Torch-dependent skip.
  - **Exact HEAD check, November 23:** `runs/head-suite-6f18ea1.PJJClT` (EVIDENCE.sha256 `dbbbd04c…`; minimal closure of 21 untracked lab files in `needed-untracked.txt`), run on a clean `git archive` of `6f18ea1`. The package suite passed: 772 tests, exit 0, one Torch skip. The first lab run omitted `lab` from `PYTHONPATH`, which was a harness error. The corrected run (`lab-pathfix.log`) had 364 tests and 9 import errors, exit 1. **Correction:** `lab/quantum` and `lab/autoresearch` are committed. The earlier claim that they lie outside the repository is withdrawn.
  - **Closure proof:** `runs/head-closure-proof.7Ggnqw` (EVIDENCE.sha256 `259a7cb4…`). HEAD plus 21 untracked lab files (`needed-untracked.sha256`) plus the working-tree `src/murmuration/readouts.py` and `lab/topology.py` (`extra-tracked.sha256`) passes the full lab suite: 384 tests, OK, two skips. The package suite on the same combined cut is recorded in that packet.
  - **RESOLVED, self-contained cut committed:** local commit `9e491f6` adds exactly the 23 custody paths (`runs/x42-lab-custody-successor.NNql13`), on the owner's authorization in chat. On a clean archive, the lab suite passed 384 tests and the package suite 772 tests, both exit 0 (`runs/commit-suite-9e491f6.lTbkAc`, EVIDENCE `41ee7ff7…`). An independent fresh-context verifier returned CONFIRMED. **Assistant ACCEPTED** at exact source and test-receipt scope (relayed message `msg_0b2174027a4a`; PC has `msg_1c5f35207b37`). Lean and MATH500 remain declared test fixtures. The lab-cut source blocker is closed.

## Data transfer status

Source: `/home/adelmar/SeaBridgeAI-data/_manifests/SPARK_DATA_MAP_20261122.md`.

The data map lists no TREMOR data, and no TREMOR step depends on AWS or PC data. All TREMOR evidence, archives and run packets were produced on the Spark and live under `/home/adelmar/SeaBridgeAI/murmuration/runs` and the repository. Each data step is therefore neither DONE-BY-TRANSFER nor WAITING-ON-TRANSFER. It is either already local or waits on a named admission:

- **M1, M3 X42 and R3 L5, M10:** local on the Spark, sha-verified in the packets above. Nothing needs to be collected again.
- **M8 SmolLM3 weights and backing storage:** waiting on the storage operator's admission, not on the transfer.
- **AWS:** none needed. The only AWS reference in `docs/reports/workplan-ep/` is the M2 hold in `Pilot4-pricing-verification-gates.md`. This lane never connects to AWS.

## Next action

**ACTIVE, Table A row X42 (`PC_ALL_BLOCKERS_WORKPLAN_V2_20261122-2d2173c9.md`, rows 232–242).** Source-only R1 build-out after the Gate R1 bench REJECT:

- [x] D1 Kish guard, `899ffeb`.
- [x] Row 165 `evapclaim` (L5), `bf304de`: 4 focused tests pass; full suites on that commit are running (`runs/commit-suite-evapclaim.wXXQ8w`).
- [x] Row 165 `lease` (L6), `4464b7e`: 4 focused tests pass. The bound and the pooling groups are caller-supplied; no method or threshold is invented.
- [x] Row 165 `sgv` (L1), `44e19cc`: 4 focused tests pass. It uses the proposal's 10-rerun minimum.
- [x] Row 165 `quarantine` (L2), `604fa25`: 4 focused tests pass. R comes from `readouts.reproduction_number`.
- [x] Row 165 `monsel` (L3) `fb9fb62`, `vreplay` (L4) `7d28822`, `blocks` (L7) `b264d8f`. Full suites on `b264d8f`: lab 384 OK (2 skips), package 804 OK (1 skip), both exit 0 (`runs/commit-suite-row165.fymZzN`).
- [x] Row 159 `susceptibility.py` `da38c43`. The worker draft was reviewed by this chat. Its ports match the lab originals in 0/500 differential cases each (`runs/r1-row159-port-check.wu8GlM`, EVIDENCE `94734818…`). This chat fixed the worker's wrong hand value (slope 2/5) and removed the test's dependency on an uncommitted lab file.
- [x] Row 162 `nulls.py` `00619ed`: exact enumerated nulls for L1, L2 (all generations), L4, L6 and L7, each checked against a closed form (11 tests). The L3 and L5 controls remain in untracked lab files.
- [x] Full suites on `00619ed`: lab and package OK, exit 0 (`runs/commit-suite-r1build.5wKvBH`).
- [x] **Independent verifier on `00619ed`** (fresh-context Opus, briefed with interrogate, host check `seabridge-spark`). ACCEPT: `evapclaim`, `quarantine`, `monsel`, `lease`, `susceptibility`. REJECT: `vreplay` (truncated readings), `blocks` (ZeroDivisionError; not proportional), `nulls` (`recovery_nights` hangs at tol 0; `immune` has no effect). Also flagged: `sgv` used raw variance instead of overdispersion; a parent counted as independent support in `quarantine`; lab files cited but not committed.
- [x] **All findings fixed** in `de56a29`, with a test for each.
- [x] **Ten lab files committed** in `7f1de86`: the row-159 port originals, the L3 and L5 null controls, the L6 lease fixture, and their tests. All were created by the `01a1fa3a` lineage (`runs/r1-lab-controls-custody.Bxz1nK/CUSTODY.md`). Lab suite: 406 tests OK.
- [x] **Row 155 receipt:** fresh-context body read of all ten modules at `00619ed` (`runs/r1-row155-body-review.ipRvT9/REVIEW.md`). The row's `poison` path is wrong: the module is `trapbench/poison.py`. Eight defects were demonstrated in the core modules: orders, ledger `deny_keys`, monitor, enforce, coupling git-option injection, perturb `passed` coercion, and consolidate arm E. They are recorded and not yet fixed.
- [x] **Row-155 core-module defects fixed**: `30bb01c` (coupling git-option injection, ledger `deny_keys`), `33b2ca2` (perturb), `52cbce1` (monitor, enforce, consolidate, orders). Each test fails before its fix and passes after. Full suites on `52cbce1`: lab 406, package 835, exit 0.
- [x] **Re-verifier on `52cbce1`**: 15 of 17 fixes CONFIRMED and no assertion weakened. It found two problems, fixed in `a5b85c0`: `sgv` could not rank pass/fail work (it now uses per-unit binomial overdispersion over item counts), and `quarantine` accepted a sibling as support (lineages must now be disjoint).
- [x] **Row 169 per-module verification** (`runs/r1-row169-module-verification.BBKCr0/RECEIPTS.md`): fresh-context Opus, one verifier per module, at `a5b85c0`. `susceptibility` ACCEPT. Seven REJECTs on boundary or mechanism gaps, all fixed in `08659a3` with tests. The `nulls` verdict is being rerun on `08659a3` after a session restart.
- [x] **Second verification round at `08659a3`:** six of the seven fixed modules ACCEPTED; `blocks` REJECTED (strings, duplicates). `nulls` REJECTED on timing near keep = 1 and input checks, with every enumeration correct. All fixed in `6e33ad2` with failing-first tests, and an exact L3 correlated-monitors null added. Full suites on `6e33ad2`: lab 406, package 846, exit 0. Receipts: `runs/r1-row169-module-verification.BBKCr0/RECEIPTS.md`.
- [x] **Third independent pass at `6e33ad2`:** `sgv` and `evapclaim` ACCEPT; `blocks` and `nulls` REJECT (a `recovery_nights` regression, float tie-breaks, unchecked agent inputs). All fixed in `7b4ea36`, each module with a test that fails on `6e33ad2`. Full suites: lab 406, package 847, exit 0.
- [x] **Diff review of `7b4ea36`:** REJECT on `nulls.recovery_nights` (hang on 30000-digit fractions; division by zero at keep = 1 - 1/10^400). Fixed in `9203700` with an exact binary-lifting search. Full suites: lab 406, package 849, exit 0 (`runs/commit-suite-rn.46Lyu0`).
- [x] **Independent review of `9203700`:** REJECT on refusal speed only (answers exact, 40,036 brute-force matches; huge x and tol took 23 s to refuse). Fixed in `cf9572e` (x and tol count against the guard; worst case 0.93 s). Full suites: lab 406, package 850, exit 0 (`runs/commit-suite-rn2.xfJTDa`).
- [x] **Row 157 contention definition frozen:** `docs/reports/workplan-ep/R1-row157-contention-definition.md`, sha256 `b9db8f83…`, commit `8a16e88`. Sent to the Assistant for leakage review.
- [x] **Delegated decisions (owner 08:00Z):** rebuild on e972484a; adopt the L5 grader fix (`1f45463`); N2 by an independent sealed author with the commitment `6def4efc…` held by the Assistant; row-157 addendum pinning scheduled counts (`5cabfe7`).
- [x] **Candidate `d918428`** = the e972484a archive plus the R1 build. Receipt: `runs/x42-rebuild-lineage-receipt.fPcr5u`. Independent Opus review: ACCEPT. Suites: package 869 OK; lab 832 ran with 10 environmental errors (numpy, torch, pilot3 data). **Nominated to PC** for the bench re-review. Superseded: `6e33ad2`, `7b4ea36`, `9203700`, `cf9572e`.
- [x] **Row 157 built:** episode v3 with scheduled κ 4/3, 4/3, 4/3, 2 (`ea24c1f`, review ACCEPT); pin frozen before the reveal (`1d333f7`, pin `6fa1d9e5…`); realized readouts ρ_r and c_r (`8de57ef`, review findings fixed). Addendum accepted at source scope.
- [x] **Candidate `e11df9d` replaces `d918428`:** diff review ACCEPT (only new lab files and docs). Pinned-container suites: package 869 OK, lab 860 OK, exit 0 (`runs/container-suite-e11df9d.hZjTis`). Nomination update sent to PC (`msg_c6c4c6ebfb69`); packet `docs/reports/tremor/X42_BENCH_REREVIEW_PACKET_e11df9d.md`.
- [x] **Owner-decision packets** (`docs/reports/tremor/`): D8, protected admissions, M10, quiet-host window, each independently reviewed and fixed (`e11df9d`, `52d4899`).
- [ ] **Waiting:** PC forwards `e11df9d` to the bench reviewer; Alejandro decides the packets.
- [ ] **Next:** PC nominates the cut, the bench reviewer re-reviews it (the row-169 `interrogate` pass), and this lane fixes any finding. Rows 157 and 167 stay held with their owners.
- [ ] **Row 157:** the preregistration-author role is named in Table A rows 238 and 242, but no person or session is designated. The contention definition stays held until PC designates one.
- [ ] Rows 155 and 169: module-body review and per-module verification receipts.
- [ ] Then: PC fresh nomination of the new cut, and bench re-review.

Routed, not done by this lane:
- Row 157 "contention above 1": preregistration author.
- Row 167 sealed N2: custodian.
- Grader-fix adoption: source owners.
- Host windows: PC and the Assistant.
- D8 and spend: Alejandro.

The seven row-165 workers ran on a Windows read-only host (`C:\Users\adelm\.omniroute\cxa`) and could not reach the Spark repository. Their claims stay unaccepted.

Limits are unchanged: no push or PR, no deletion, no paid calls, no AWS access, no secrets printed, one session per lane.
