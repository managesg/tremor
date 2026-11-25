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
- [ ] **M2 BLOCKED · Pilot 4 and EP-1.** Offline retry and B4 reply custody were exercised. Pilot 3 criterion 2 still fails, with 263 output tokens against a 150 ceiling. Evidence: `runs/pilot4-full-retry.ZwWZHE/OWNER_PACKET.md` and `runs/m2-enabled-response-custody.cHx1kP/OWNER.md`. BLOCKED: paid/live provider calls + D8 price-sheet refetch, Alejandro; docs/reports/tremor/OWNER_DECISION_M2_M7_D8_Pilot4_EP1.md:1
  - **Blocker owners:** Alejandro, the preregistration author, and the spend and driver reviewers.
  - **Needed:** D8 hold release; wording, scoring and order decisions; pricing and driver clearance; named release. After that, seven Pilot 4 checks, the EP-1 freeze and 60 admitted episodes.
  - Gate register: `docs/reports/workplan-ep/Pilot4-pricing-verification-gates.md`.
- [ ] **M3 OPEN, partly blocked · CPU benchmark and R3.** All 351 files and modes match the X42 nominated cut. The source manifest hash is `e972484a4db7c24f75058bf904c273545a4a4684a6dcc370caed2de44b1726de`; the binding target is `1c7b3af9433d17528ed093aaeacab1fb3d919af6265dbe46482455dc530dd7f4`. Zero of the three archived host windows are eligible. The R3 L5 CPU interruption receipt is verified. Evidence: `runs/tremor-chat-intake.f0VZwV/OWNER.md` and `runs/r3-l5-real-cpu-interruption.VMBB6X/verified.json`. BLOCKED: row 167 custodian/L5 admission and quiet-host windows (PC, Alejandro); docs/reports/tremor/X42_ROW167_L5_CUSTODY_REQUIREMENTS.md:1, docs/reports/tremor/OWNER_DECISION_X42_quiet_host_window.md:1
  - **X42 blocker owners:**
    - Source owners decide whether to adopt the BtUauk grader fix (`runs/r1-execution-consistency.BtUauk/OWNER.md`).
    - PC 7ce2c340 then launches the designated bench reviewer, or delegates the launch to this lane.
    - The N2 custodian supplies the sealed commitment.
    - The Assistant reviews the host evidence.
  - **X42 Gate R1 bench verdict: REJECT** on e972484a (`runs/x42-r1-bench-verdict.uPqmQ9/VERDICT.md`, EVIDENCE `a770a1dd…`). The reviewer was a fresh-context Opus subagent briefed with interrogate, launched under the owner's chat authorization. Rows 159 (no `susceptibility.py`), 162 (missing L4 and L6 nulls) and 165 (no technique modules) are REJECT. Rows 155, 157, 167 (custody-gated) and 169 are INCOMPLETE. Row 158 is ACCEPT with a caveat.
  - **Defect D1 fixed:** local commit `899ffeb`. Undefined Kish values now return None. Lab 384 OK and package 776 OK on a clean archive (`runs/commit-suite-d1fix.5AglpS`, EVIDENCE `1a17ed73…`).
  - **Next for M3 R1:** build the missing row-159, 162 and 165 deliverables, then get a fresh PC nomination and a bench re-review. Owner: this lane for the build. The preregistration author owns definitions such as "contention above 1".
  - **R3 L2/L5 blocker owners:** the runner owner, custodian, admission reviewer and Alejandro. Register: `docs/reports/workplan-ep/R3-L2-admission-inventory.md`.
- [ ] **M4 BLOCKED on protocol freezes · L1–L8.** Offline L7 rotation and L8-D lineage groundwork exist. Evidence: `runs/m4-l7-combined-rotation.X5jf6W/OWNER.md`. BLOCKED: freeze admission, Alejandro (offline L2-C/L3-C/L4-C drafts done); docs/reports/workplan-ep/R2-R4-protocol-readiness.md:1
  - **Blocker owners:** the line authors, custodians and reviewers. Alejandro owns the R2 sensitivity release.
  - Register: `docs/reports/workplan-ep/R2-R4-protocol-readiness.md`.
- [ ] **M5 BLOCKED · L4-E to L8-D.** The Qwen loader and hook receipt exist. Evidence: `docs/reports/workplan-ep/Qwen-base-cpu-hook-receipt.md`. BLOCKED: protected run admission, Alejandro; docs/reports/tremor/OWNER_DECISION_protected_admissions_M3R3_M4_M9.md:1
  - **Blocker owners:** the trainer, protocol author and L8-D custodian.
  - Packet: `runs/l4e-prospective-trainer.QIXxzB/coordinator-packet.md`.
- [ ] **M6 BLOCKED · Coordination.** Public matched-traversal controls exist. Evidence: `docs/reports/workplan-ep/Topology-matched-traversal.md`. BLOCKED: protected run admission, Alejandro; docs/reports/tremor/OWNER_DECISION_protected_admissions_M3R3_M4_M9.md:1
  - **Blocker owners:** the author, custodian and resource reviewer.
  - Packet: `runs/topology-two-round-joined.FRL4cn/owner-packet.md`.
- [ ] **M7 BLOCKED · Grover and quantum simulator.** Release and fallback replay exist. Evidence: `docs/reports/workplan-ep/Grover-topology-scripted.md`. BLOCKED: EP-1 paid calls, Alejandro; docs/reports/tremor/OWNER_DECISION_M2_M7_D8_Pilot4_EP1.md:1
  - **Blocker owners:** EP-1 (see M2), the Grover authors, the custodian and scorer, and the resource reviewer.
  - Packet: `runs/grover-statistical-envelope.6Cln7i/OWNER.md`.
- [ ] **M8 BLOCKED · SmolLM3 second family.** The V3 reserve-to-settlement binding is done offline. Evidence: `runs/m8-worker-runtime-binding.DV7iql/OWNER.md`. BLOCKED: storage paths, runner reviewer, 0.1 GPU-h reservation (Spark operator, PC); docs/reports/tremor/OWNER_DECISION_M4_L2_L3_L4_and_M8_prereqs.md:1
  - **Blocker owners:** the storage operator, admission issuer and resource owner. They provide backing storage, the memory and runtime window, a 0.1 GPU-hour reservation and one-use admission.
  - Packet: `runs/smollm3-native-owner.vt3Sj1/OWNER.md`.
- [ ] **M9 BLOCKED · Combined controller.** Scripted controller coverage exists. Evidence: `runs/controller-cluster-join.iJZn9z/OWNER.md`. BLOCKED: protected run admission, Alejandro; docs/reports/tremor/OWNER_DECISION_protected_admissions_M3R3_M4_M9.md:1
  - **Blocker owners:** the integration author, task custodian, claims reviewer and witnesses.
- [ ] **M10 PARTLY ACCEPTED · Report, resources and release.** The Assistant accepted the offline release and reader evidence at local scope (`msg_805f62c63b42`, relayed by PC). BLOCKED: Console totals, T7 settlement, timer executor (PC); docs/reports/tremor/OWNER_DECISION_M10_release_and_T7.md:1
  - **Accepted files:** `runs/tremor-chat-intake.f0VZwV`, with `OWNER.md` prefix 3d744345, `EVIDENCE.sha256` prefix 6590b891 and `FRONTEND.sha256` prefix 6800c876.
  - **Recorded:** in `docs/reports/workplan-ep/Execution-plan-20261123.md`, local commit `d897860`.
  - **Blocker owners:**
    - The release owner and Alejandro own release adoption and G8 sharing.
    - The claims reviewer and resource owner own the provider Console totals and T7 accounting. The provisional 4.0 GPU-hour T7 hold stays until it is backed by evidence.
- [x] **Goal registry CLOSED 2026-11-25.** Owner cleared the /goal and PC removed the goal and loop hooks everywhere, so no goal registry remains to wait on (Assistant relay, sup:9f33b3f027c3a347). The Assistant is now `claude_683b11af` (`codex_c125641a` retired).
- [ ] **Cross-cutting, OPEN, this chat.** Standing duties; stays open per Assistant (sup:9f33b3f027c3a347). Checkpoint report: docs/reports/TREMOR_CHECKPOINT_20261125.md.
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

## Hourly checklist (2026-11-25, Assistant instruction; refresh at least hourly)

Repo `/home/adelmar/SeaBridgeAI/murmuration` master, HEAD `f791802`, local only. Acceptance 1/10 (M1). Candidate `f62cfe1`. Status key: DONE, IN PROGRESS, BLOCKED (owner), NOT STARTED. Milestone rows are lines 18-49 of this file.

| Item (file:line) | Acceptance | Status |
|---|---|---|
| M3 Gate R1 rows 155-165, 169 (this file:22) | independent bench ACCEPT at `f62cfe1` (`runs/x42-bench-recheck-f62cfe1.CgLSTo/VERDICT.md`) | DONE |
| M3 row 167 (this file:22; `X42_ROW167_L5_CUSTODY_REQUIREMENTS.md`) | custody binding, L5 admission, reveal review | BLOCKED: owner:custody-X42-row-167 (owner decides custody; the Assistant holds none), then Alejandro |
| M3 three quiet-machine windows (this file:22; packet `f80a26c`) | three ELIGIBLE windows on `f62cfe1`, roster 912/929 | BLOCKED: PC (freeze, host reviewer, operator, D2); the lane's yes is recorded (`628f9b4`) |
| M4 L2-C, L3-C, L4-C DRAFT protocols (this file:32) | each cites sources or marks OPEN; independent review ACCEPT | DONE (`462da48`, `625ab34`) |
| M4 L3-C harness (this file:32) | reuses monsel; mutants killed; review | DONE (`1dabf53`) |
| M4 readiness register tracked (this file:32) | file committed, sha256 `1352e894` unchanged | DONE (`f791802`) |
| M4 L4-O15: align `lab/l4_adaptive_replay_policy.py` to "either reading rises" (this file:32) | test fails on current code, passes after; clean-archive lab suite OK | DONE (committed after `c0daf55`; lab 1010 tests, same 10 host errors) |
| M4 commit lab and docs cited by the three drafts that are still untracked (this file:32) | every cited path is tracked; sha256 unchanged | DONE (`c0daf55`, 40 files) |
| M4 advisory test gaps in quarantine and sgv (this file:32) | tests only, in the next candidate after the windows | PATCH READY, not applied: `runs/advisory-gaps-patch.zlCV0b/advisory-gaps.patch` (sha256 `19032089…`, 4 new tests, applies clean to `ba0a910`, three mutants killed). Apply only after the windows, because it moves the tree. |
| M4 full freezes L2-L4 (this file:32) | OPEN items closed, freeze record with protocol sha and tree hash | BLOCKED: line authors, custodian, Alejandro admission |
| M2, M7 (this file:18, :41) | D8 refetch, Pilot 4, EP-1 | BLOCKED: Alejandro (paid calls) |
| M5, M6, M9 (this file:35, :38, :47) | admitted native runs | BLOCKED: Alejandro; preconditions unmet |
| M8 (this file:44) | runner reviewer accepts closure `a6a7875`; memory, storage paths; 0.1 GPU-h reservation | BLOCKED: runner reviewer, Spark operator, PC binding |
| M10 (this file:49) | Console totals, T7, timer executor | BLOCKED: PC |
| WSP-R1 (`prereg/WSP-R1-exp1-blind-read.md`; prereg `5367f53`, result `5938fed`) | real 4/4, shuffled 1/4 recorded; spend reconciled | DONE; spend: tokens measured by the Assistant (8 calls: input 62, output 39,791, cache create 983,957, cache read 1,841,140; file not readable on this host), cost not computed, unknown not zero; BLOCKED on a billing ledger |

## Blockers and next items (refreshed 2026-11-24 about 14 UTC, owner request via PC msg_caa7882ac737)

Acceptance: 1/10 (M1). Candidate of record `f62cfe1` (tree `cdaee764…`). All commits are local; nothing is pushed.

**Dropped as stale:**
- Row 169's single-reviewer question: decided (`88b19c1`), and row 169 is ACCEPT at `f62cfe1`.
- Quiet-window nomination: PC nominated `f62cfe1` with roster 912 `caf3dc41` and 929 `d5082bb1` (msg_c37cd18b6654).
- M2/M7 packet truncation: restored in `50fb635`.
- M8 `replication_inventory` gap: Decision 4 ACCEPT (`54cc69e`).
- M4 scope: frozen in `d4b1f91`.

**Open gates (one line each):**

| Gate or dependency | Owner | Evidence | Smallest action |
|---|---|---|---|
| X42 quiet-machine windows W1-W3 | Alejandro + PC (named yes; carried in the morning owner batch) | `OWNER_DECISION_X42_quiet_host_window.md` (`f80a26c`), dry preflight `3a16b006` | yes for the three windows, then PC binds the freeze, operator and host reviewer |
| X42 row 167 (N2 custody, L5, reveal) | owner:custody-X42-row-167 (owner), then Alejandro | `X42_ROW167_L5_CUSTODY_REQUIREMENTS.md`, commitment `6def4efc` | owner's custody decision, then the one-use L5 admission |
| M2/M7: D8 price sheet lapsed 2026-11-24 00:00 UTC | Alejandro (named yes: network refetch + spend) | `OWNER_DECISION_M2_M7_D8_Pilot4_EP1.md` (`50fb635`) P4 | yes to refetch, then a continuity review and window instants |
| M8 SmolLM3 smoke | runner reviewer; Spark operator (memory at execution, storage paths); Alejandro or PC (0.1 GPU-h yes) | `DECISION_LOG.md` Decisions 1-4 (`54cc69e`) | runner reviewer accepts the closure at `a6a7875`; operator names and freezes the paths |
| M3 R3, M5, M6, M9 run admissions | Alejandro | `OWNER_DECISION_protected_admissions_M3R3_M4_M9.md` | named one-use admissions |
| M4 L2-L4 full protocols | this lane (offline drafting), then Alejandro (admission) | `prereg/R2-L2-L3-L4-scope.md` (`9008847b`) | freeze each full protocol and tree hash |
| M10 remainder | PC | `OWNER_DECISION_M10_release_and_T7.md` | Console totals, T7 settlement, timer executor |
| WSP-R1 spend reconciliation | Assistant | `prereg/WSP-R1-exp1-blind-read.md` (`5938fed`) | record the actual cost; unknown until then |

**OD4 decisions (2026-11-24):** see `DECISION_LOG.md`, "parked owner-yes items decided under OD4". The X42 windows and the M8 0.1 GPU-h reservation are now decided yes by this lane and wait only on **PC binding** (and, for M8, the runner reviewer and Spark operator). L5, M3 R3-L2, M5, M6 and M9 are not admitted until their preconditions exist. The D8 refetch waits for a paid-call yes (Safety gate). M4 rulings: L3 = C, the conjunction rule, and R = first generation.

**Next real items for this lane (offline):**
- Carried-forward advisory gaps for the next candidate (quarantine: missing parent and unknown id; sgv: bool budget and redundant dict check). Not cut unless a new candidate is needed.
- M4 protocol drafting for L2-C and L3-C under the frozen scope.
- Otherwise: `sup3 next`.

## Current workplan (2026-11-23, 20 UTC)

Acceptance: 1/10 (M1). Repository HEAD is recorded in each checkpoint. All commits are local; nothing is pushed.

### M3 R1 / X42 Gate R1
- [x] **Candidate of record: `83e4870`** (tree `572155d0…`), the e972484a archive plus the R1 build, episode v4 and frozen pins. Pinned-container suites: package 869 OK, lab 878 OK. Candidate, runner and roster agree (`docs/reports/tremor/X42_CANDIDATE_RUNNER_ROSTER_RECONCILIATION.md`).
- [x] **Bench verdicts:**
  - e11df9d: rows 155, 158, 159, 162, 165 and 169 ACCEPT.
  - 83e4870: row 157 ACCEPT (episode design only).
- [x] **Row 157: ACCEPTED** on bench re-check at `83e4870` (`runs/x42-bench-recheck-83e4870.4P3pJg/VERDICT.md`, sha256 `48834c15…`), for the episode design only. Behaviour is not established, because the agents are scripted.
- [ ] **Row 167:** INCOMPLETE. Custody binding (custodian), L5 admission (Alejandro), then the reveal review. Requirements: `docs/reports/tremor/X42_ROW167_L5_CUSTODY_REQUIREMENTS.md`. BLOCKED: owner:custody-X42-row-167, custody of sealed material is the owner's decision (the Assistant is not the custodian), then L5 admission (Alejandro); docs/reports/tremor/X42_ROW167_L5_CUSTODY_REQUIREMENTS.md:1
- [ ] **Three quiet-machine runs:** packet `OWNER_DECISION_X42_quiet_host_window.md` (`9a3897d`). The dry preflight passes. Needs PC's window after the integration freeze, with the packet predicates confirmed. BLOCKED: PC window and host reviewer; docs/reports/tremor/OWNER_DECISION_X42_quiet_host_window.md:1
- [x] **Row 169: ACCEPTED at `f62cfe1`** (decided under owner delegation 2026-11-24T05:35Z, `88b19c1`: per-module Opus verdicts on the exact candidate bytes plus the bench interrogate pass). The per-module round found real defects in five modules (sgv, quarantine, monsel, vreplay, lease), fixed over five rounds. All nine are ACCEPT at `f62cfe1`, and the bench re-check `runs/x42-bench-recheck-f62cfe1.CgLSTo/VERDICT.md` (`6ada3cf4…`) confirms rows 155, 157, 158, 159, 162, 165 and 169 ACCEPT, with row 167 INCOMPLETE. **New candidate of record: `f62cfe1`** (tree `cdaee764…`, 623 files). Container suites: package 912 OK, lab 929 OK. The dry preflight passes, with roster 912 `caf3dc41…` and 929 `d5082bb1…`. `83e4870` is superseded. The quiet-window packet is re-targeted and needs a fresh nomination and yes from PC.

### Other milestones (owner-decision packets in `docs/reports/tremor/`)
- [ ] **M2 and M7, D8:** conditional ceilings (Pilot 4 USD 0.25, EP-1 USD 5.00). No Pilot 4 launcher exists yet. **The pinned price sheet lapses at 2026-11-24 00:00 UTC** (`spend.py:45,186-188`; checked 21:56 UTC). A fresh window needs a named refetch, the new digest, a continuity review against the `ep1` parent ledger, a checked window and a re-run of D8-e (D8 packet, P4 lapse status). M7's protocol and allocation are open. BLOCKED: paid-call yes for D8 refetch (Alejandro); docs/reports/tremor/OWNER_DECISION_M2_M7_D8_Pilot4_EP1.md:1
- [x] **M4 L2/L3/L4 scope APPROVED and frozen (documentary):** owner decision `msg_e96a060964d0`; `prereg/R2-L2-L3-L4-scope.md` (sha256 `9008847b…`) and the register `docs/reports/prereg-freezes.md` (`d4b1f91`). No run authority. Basis: recommended options drafted with one-line yeses (`docs/reports/tremor/OWNER_DECISION_M4_L2_L3_L4_and_M8_prereqs.md`):
  - L2: planted notes only under D1; the arising form and prediction E are out of this freeze. If E is ever approved, it uses the 5% bound.
  - L3: primary C under the D1 toy-monitor conditions; B is the fallback if C is declined before any outcome.
  - L4-D: the arising-shortcut setting is out of this freeze.

  A yes also ratifies D1 for those lines, because D1 was the orchestrator's disclosed decision (`ep-approvals.md:163-166`). Owner: Alejandro.
- [ ] **M8 SmolLM3 smoke:** five preconditions in the sources (three operator prerequisites, plus ledger placement and the one-use admission, which the yes covers): BLOCKED: operator storage paths, runner reviewer, 0.1 GPU-h yes; this file:116
  - memory: the last readback was 54.46 GiB against the 70 GiB gate, or a separately reviewed envelope;
  - storage custody: the canonical paths are not yet named;
  - one adopted launcher: the patched `--opening-balance` source would need re-pinning.

  Owners: resource owner, storage operator, runner reviewer; Alejandro for the 0.1 GPU-hour spend.
- [ ] **M3 R3, M5, M6, M9:** not admissible today (protected-admissions packet). BLOCKED: named one-use admissions (Alejandro); docs/reports/tremor/OWNER_DECISION_protected_admissions_M3R3_M4_M9.md:1
- [x] **M10 local release adoption** (`a833e17`).
- [ ] **M10 remainder:** Console totals, T7 settlement, timer disposition (named executor). BLOCKED: Console totals, T7, timer executor (PC); docs/reports/tremor/OWNER_DECISION_M10_release_and_T7.md:1

### Limits
No push, PR, spend, install, deletion, quiet-host run, paid call or N2 access without the applicable exact admission.
