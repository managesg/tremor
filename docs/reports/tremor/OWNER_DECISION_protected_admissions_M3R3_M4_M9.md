# Owner decision packet: protected admissions M3 R3, M4, M5, M6, M8, M9

Prepared 2026-11-23 on `seabridge-spark` from the murmuration checkout at HEAD `4442b97` (working tree dirty). Read-only: no git write, network, GPU, container or protected run was done to produce this packet. Nothing here is an admission, reservation or approval. Alejandro approves spend and launch; reviewers named below supply the evidence.

Source paths are under `docs/reports/workplan-ep/` unless they start with `runs/`, `lab/` or `docs/`. Citations are `file:line`. Abbreviations: **CB** = `Coordinator-blockers-20261122.md`; **FS** = `R3-first-slices-admission.md`; **INV** = `R3-L2-admission-inventory.md`; **L5D** = `R3-L5-protocol-draft.md`; **RR** = `R2-R4-protocol-readiness.md`; **SAR** = `Spark-allocation-rephase.md`; **SR** = `Spark-readiness.md`; **SM** = `SmolLM3-native-smoke-packet.md`; **SMO** = `runs/smollm3-native-owner.vt3Sj1/OWNER.md`; **CCD** = `Combined-controller-design.md`.

## Summary table

| Item | Decision needed | Decider | Ready now | Recommendation |
|---|---|---|---|---|
| M3 R3-L2 | One-use batch admission and about 3 GPU-hours reservation for the L2 warning and memory slice on local Qwen3.5-4B | Alejandro with the admission reviewer; protocol author, evaluator custodian and runner owner supply the freeze | No | Not yet: no frozen protocol, protected cohort, or native launch entry point |
| M3 R3-L5 | One-use batch admission and about 4 GPU-hours for the L5 carrier slice (N1/N2, teams of 4 and 8) | Alejandro with the admission reviewer; L5 author and independent custodian supply the freeze | No | Not yet: N2 not sealed; the 4 vs 3 GPU-hour figures disagree; no native launcher |
| M4 L1, L6 | Freeze the protocol (estimand, denominators, splits) | Line authors and custodians, independent reviewer | No | Approve the freeze once the listed fields arrive; this is a preregistration, not a GPU launch |
| M4 L2, L3, L4 | Freeze plus three scope rulings (L2 unplanted variant and L2-E 1% vs 5%; L3 primary C vs B; L4-D outside D1) | Owner for the scope rulings; authors for the freeze | No | Approve the rulings now; freeze after the authors deliver |
| M4 L5, L7, L8 | Freeze N1/N2, hub and participation definitions, and the causal token and readouts | Line authors, custodians, reviewers; L8-D also waits on M5 | No | Approve after L5 matches the M3 L5 freeze; L8-D not yet |
| M4 R2 sensitivity pilot | A separate named release | Owner | No: no scope, hours or cost in the repo | Not yet: needs a written scope and price first |
| M5 L4-E, L8-D | Price and admit the smallest valid paired adapter tranche; later the L8-D freeze | Trainer, protocol author, independent reviewer, resource owner; Alejandro for the spend | No | Not yet: no actual schedule, no price, and the 13.5-hour ceiling exceeds the 9.5-hour residual |
| M6 | Freeze the authority and access contrast and admit a protected native run | Author, custodian, resource reviewer; Alejandro for the spend | No | Not yet: allocation unplaced; no host transport or cost receipts |
| M8 | Reserve 0.1 GPU-hour in `spark-replication` and issue a one-use admission for the SmolLM3 smoke | Spark resource owner, admission issuer, storage operator; Alejandro for the spend | No: current memory, writable backing, no live placement | Approve after the preconditions below; the smallest, best-prepared request |
| M9 | Select eligible components and admit the combined-controller comparison | Integration author, task custodian, claims reviewer; Alejandro for the spend | No | Not yet: no supported components, no allocation, EP-1 is still a draft |

Ledger context used throughout: R2 charged 0.023123 GPU-hours; the shared R2/R3 balance is 7.476877 and the program balance 65.976877 with the provisional 4.0-hour T7 hold (`Spark-readiness.md:139-141`; `FS:9`). These are balances at that settlement, not a current reservation (`SAR:4-7`; `INV:17-21`). Every request below needs the ledger reconciled again immediately before it is admitted.

## Cross-cutting preconditions and flags

1. **No batch has a native launch entry point except the SmolLM3 smoke.** The only guarded launcher for Qwen3.5-4B is `python3 -m lab.spark_calibration_guard --approved-launch --receipt "$R2_ADMISSION_RECEIPT"` (`SR:95`). Its admission schema fixes `batch` to `spark-r2-qwen35-4b-throughput` and `reserved_gpu_hours` to 0.1 (`SR:82-88`), so it cannot admit R3 or M4 batches. `INV:2-5` says so for L2.
2. **Source tree state.** `lab/smollm3_smoke_launch.py`, `lab/smollm3_smoke_admission.py` and `lab/topology_matched_traversal.py` are untracked in the checkout (checked with `git ls-files`). The git status also shows many untracked `l2c_*`, `l4_*`, `l4a_*` and `l5a_*` modules. A per-line "tree hash" freeze (`RR:48-52`) must pin a committed or closure-archived tree, not this working tree.
3. **Host memory.** SMO:20-22 recorded 57,100,444 KiB `MemAvailable` against the stock 73,400,320 KiB (70 GiB) pre-start check. The stock smoke gate would refuse today. I did not re-read live memory; the admission reviewer must.
4. **Hours mismatch for L5.** The L5 first slice plans about 4 GPU-hours (`FS:12`; `L5D:3`), but the L5 line ceiling is 3 (`RR:22`). Resolve before any L5 reservation.
5. **9.5-hour residual.** After the R2/R3 share (7.476877) and L1-L8 ceilings (49.0), 9.5 GPU-hours remain. The L4-E adapter alone is up to 13.5. Grover, the second family and the combined controller are "Unplaced" (`SAR:9-17`). A 0.1-hour SmolLM3 placement would leave 9.4 (`SAR:55-56`).
6. **Roles that make decisions.** Safety rules reserve gated approvals to Alejandro in the current session. Reviewers only supply evidence. A one-use approval is bound to an exact batch and UTC window (`INV:31`).
7. **Rollback for any GPU batch** is not a data revert. It is: stop (watchdog or manual), exact-ID container removal, hold the reservation until cleanup and billing evidence are in, then settle or cancel with a pinned receipt. Do not re-admit until reconciled (`FS:34`; `CB:83-85`).

---

## 1. M3 R3-L2 (warning vs neutral, memory spread R, local Qwen3.5-4B)

**Decision needed.** Authorize one native L2 batch: freeze, reserve about 3 GPU-hours (`FS:12`), and issue a one-use admission. Nothing is dispatched until all seven pending inputs at `INV:23-31` are met. Decision owners: Alejandro (authorization), admission reviewer (reservation), L2 protocol author (freeze), independent evaluator custodian (cohort), local Coordinator to designate one runner owner, independent verifier (mount and capture review).

**Command once admitted.** Missing. `INV:3-5` states there is no exact reviewed R3-L2 launch entry point; the Qwen loader is a standalone adapter and the L2 batch CLI is scripted. What exists, all CPU-only:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:lab python3 -m lab.r3_l2_admission_inventory . runs/r3-l2-admission-inventory.BHtWxt/manifest.json --manifest-sha256 cab23d5c5de9b5ed04f5b97f29162913b39464f498bec1089695118aebeaac30` (`INV:39-44`). It verifies the inventory and refuses crossed batches.
- `python3 -m lab.r3_l2_batch BUNDLE BATCH OUTPUT --batch-sha256 SHA` (`lab/r3_l2_batch.py:125-130`). It is a scripted CPU replay.
- `python3 -m lab.r3_schedule INVENTORY.json` and `python3 -m lab.r3_replay INVENTORY.json` (`FS:47,67`).

**Resource reservation.** About 3 GPU-hours inclusive of all charged wall time from Docker start through confirmed cleanup (`FS:12`, `FS:34`), drawn from the shared 7.476877 balance. That is a planning value, not a reservation (`FS:12`). The shared first slices are capped at 7.5 GPU-hours, with L5 shrunk first at the stop (`CB:68-72`). Memory: the R2 run sampled a minimum of 58.348 GiB available and a 8.543 GiB peak CUDA reservation, from two short prompts only (`FS:10-11`). Runtime: no figure for a sustained run exists; calibration throughput gives no estimate of matched sets per hour (`FS:35`). The 10 GiB host watchdog and the existing vLLM service stay in place (`INV:33`).

**Protected inputs and custody.** Frozen task and reference truth, controls, and disjoint splits held by an independent evaluator custodian with read-only custody receipts (`INV:26`). Pinned: Qwen3.5-4B revision `851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a`, manifest SHA-256 `9b70e85c464f8dddbe1c6094832f51043a85fa7dcdf281e0cb81aa0d2d4d6ea6` (`FS:14`). Host-owned raw replies and usage; worker never sees reference text (`INV:29`; `R3-governed-cpu-readiness.md:5-10`).

**Stop conditions.** Host watchdog memory floor (10 GiB), wall-limit deadline fixed at launch, and the protocol's stop rules (not yet frozen) (`FS:92-110`; `INV:23`). A stop withholds R and keeps the arm's unknown usage (`INV:17-21`). Any missing, stale, incompatible or unsettled admission is a refusal; uncertain stop or cleanup holds the reservation (`INV:33-35`).

**Rollback.** See cross-cutting item 7. CPU receipts show the guard stops a real child and writes the stop receipt before signalling (`FS:88-110`).

**Tests before and after.**
- Before: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:lab:tests python3 -m unittest -q lab.tests.test_r3_cpu_guard_replay lab.tests.test_spark_calibration_guard lab.tests.test_r3_resource_audit lab.tests.test_r3_l2_batch` (`FS:119-123`), the inventory CLI above, `lab.tests.test_r3_schedule` (`FS:48`), and a scripted rehearsal of the actual proposed runner, watcher and accounting (`FS:35`).
- After: per-result Opus claims check (R3 requires it, `CB:31`), settled resource receipt (`FS:84`), and `lab.r3_resource_audit` reconciliation.

**Risks.** No exact launch entry point. The scripted control counts first-generation relays only (`FS:20`). Unplanted-note variant is out of scope without its own ruling (`FS:23`). The shared Spark device and historical host-memory loss are unresolved (`FS:11`). Overlapping runner ownership across lane handoffs (`INV:35-36`).

**Recommendation: not yet.** Approve after: frozen protocol, protected cohort receipts, schedule and scorer pins, a single designated runner with a reviewed native entry point, mount and capture review, and a reconciled reservation.

---

## 2. M3 R3-L5 (norm carriers N1/N2, teams of 4 and 8) and the CPU scorer-canary

**Decision needed.** Same shape as L2 for about 4 GPU-hours (`FS:12`; `L5D:3`), plus a separate freeze of the CPU scorer-canary case study (`CB:31`). Deciders: Alejandro; L5 author and independent custodian (seal N2); runner owner; admission reviewer.

**Command once admitted.** Missing for native execution (`L5D:41-42`, `L5D:74-76`: runner owner needs an independently reviewed native implementation). CPU commands that exist: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m lab.l5_matrix EVIDENCE_DIR --seed 86 --contended --full-cycle`, then `python3 -m lab.l5_matrix_audit runs/l5-matrix-full-cycle.BKB6kj/evidence --summary-sha256 40787e0f89a7bcf2b09da54eb48317fe386faf55b147457f69ed3ff83565b79e` (`L5D:108-114`). The delivery audit is in `L5D:217-227`. Both are scripted.

**Resource reservation.** About 4 GPU-hours planned (`FS:12`; `L5D:3`) against a line ceiling of 3 (`RR:22`); reconcile first. With L2 at about 3, 0.476877 of 7.476877 remains (`FS:12`). If room is short, L5 shrinks first and a failed plain-coordination floor means stop and report (`CB:68-72`). Memory and runtime: no figure for eight-worker readiness or run count; the short calibration does not establish either (`L5D:42`).

**Protected inputs and custody.** Sealed N2 (labels, case generator or task inventory, seed split, rubric, verified predicate) held by an independent custodian; no N2 information to carriers, the code enforcer or workers, with leak audit across retrieval, prompts, caches and logs (`L5D:22`). Preregistration author and custodian owe the protected N2 rule and case commitment (`CB:30`). Authored N1 separately.

**Stop conditions.** Disruption missed or interrupted yields no effect inference (`L5D:23`). Frozen stop and void procedures for scorer disagreement (`L5D:31`). The plain-coordination floor failing is stop and report (`FS:83`).

**Rollback.** Cross-cutting item 7; each run keeps scheduled, completed, stopped and censored records (`L5D:41`).

**Tests before and after.**
- Before: `lab.l5_matrix` plus audit above, `lab.l5_matrix_delivery_replay` and `_audit` (`L5D:217-227`), `lab.l5_shard_cpu_replay` (`L5D:183-186`), `lab.l5_shared_work_control` (`L5D:145`), and the prefix audit evidence (`R3-governed-cpu-readiness.md:39-62`). Replay known pass, known violation, blocked legitimate action and disruption placement with the native runner on scripted inputs (`FS:21`).
- After: R3 claims check per result, settled resource receipt.

**Risks.** The code carrier and norm evaluator may share an implementation, so verify both against an independent control set (`L5D:21`). Real environment isolation and contention are only scripted (`L5D:72-73`). The 4 vs 3 GPU-hour mismatch above. Eight-worker fixtures must not silently inherit four-slot defaults (`L5D:17`).

**Recommendation: not yet.** Approve after N2 is sealed by the custodian, a native runner is reviewed, the hours figure is reconciled, and the L2 outcome is known if L5 is to be shrunk against it.

---

## 3. M4 L1-L8 (freeze gates, grouped)

**Decision needed (all groups).** Freeze each line's protocol with a tree hash and measured variance and clustering, or record prospectively reachable outcomes (`CB:32`). Securing protected inputs, exact admission and independent outcome and cost reviews follow. A freeze is a preregistration. It does not by itself authorize any GPU run; each batch needs its own admission (`RR:48-52`).

**Command once admitted.** Missing for every line. `RR` names no native launch entry. Related CPU checks exist for L8: `PYTHONDONTWRITEBYTECODE=1 python3 -m lab.adapter_lineage BUNDLE PLAN.json --plan-sha256 "$L8_D_FROZEN_PLAN_SHA256"` with optional `--safetensors-max-bytes "$REVIEWED_CHECKPOINT_LIMIT"` (`L4-L8-adapter-lineage.md:27-28`, `:46-48`).

**Resource reservation (line batch ceilings, `RR:18-25`).**

| Line | GPU-hours | Hosted USD |
|---|---:|---:|
| L1 | 8 | 24 |
| L2 | 6 | 15 |
| L3 | 4 | 24 |
| L4 | 12, plus adapter | 40 |
| L5 | 3 | 29 |
| L6 | 2 | 6 |
| L7 | 8 | 12 |
| L8 | 6 | 3 |
| Total | 49 | |

Calibration and first slices share 7.5; with up to 13.5 for L4-E the program ceiling is 70 (`RR:31-33`). Hosted limits are separate from Spark hours (`RR:33`). Memory and runtime per line: no figure in the repo. Per-line minima: 400 clean and 200 failure episodes for 5% false-positive readouts (`RR:46-47`).

**Group A, L1 and L6: simple freezes.**
- L1: estimand, opportunity denominator, zero and missing-pair rules, tuning and holdout split, cluster precision (`CB:42-43`).
- L6: benign permission and legitimacy labels, exposure denominator, calibrated evidence bounds, paired decisions (`CB:56`).
- Recommendation: approve each freeze when its listed fields arrive.

**Group B, L2, L3, L4: need owner scope rulings first.**
- L2: unplanted variant needs its own ruling (`CB:44-46`). Open interpretation: L2-E support text says a lower bound above 1%, the later accuracy note above 5% (`RR:53-55`). Resolve before freezing.
- L3: choose the approved primary C or the prespecified fallback B before seeing outcomes (`CB:47-49`; `RR:20,57`).
- L4: an L4-D setting outside D1 needs a separate scope ruling; bind the token reference and joint decision across the two strongest settings (`CB:50-52`; `RR:55-56`).
- Recommendation: owner can rule on the three items now; each freeze follows once authors deliver.

**Group C, L5, L7, L8.**
- L5: seal N1/N2 and private verdicts, carrier delivery, prices, matched disruptions (`CB:53-54`). Must equal the M3 L5 freeze.
- L7: hub and participation definitions, seeded layouts, work selector, variance and meaningful gain, equal realized tokens (`CB:57-58`; margins `RR:56-57`).
- L8: causal decision token, raw capture, blind calibration and holdout splits, feature fitting, matched operating point; L8-D also needs settled L4-E lineage (`CB:59-61`).
- Recommendation: L5 and L7 approve after fields arrive; L8-B approve after hook procedure review; L8-D not yet (blocked on M5).

**R2 sensitivity pilot.** `CB:32` calls for a separate named release. The repo gives no scope, GPU-hours, USD or window for it; those are preconditions. Recommendation: not yet.

**Protected inputs and custody.** Held-out condition IDs, false-completion truth, blinded failure and clean pools, hidden labels and probe splits, kept by line custodians independent of the author (`RR:18-25`). The per-batch freeze artifact lists the code, tree and config hashes, snapshot, splits, scorer IDs, stopping rules, resources and approvals (`RR:48-52`).

**Stop conditions.** Economic and statistical stopping rules are frozen per batch (`RR:50`). Support, kill and inconclusive intervals are set in advance; unreachable outcomes are marked prospectively (`RR:43-45`).

**Rollback.** A freeze before any run is reversible by supersession. After admission, cross-cutting item 7.

**Tests before and after.** Before: per-line scripted checks with one deliberately failing control and a scorer agreement receipt (`RR:37-39`); `lab.tests.test_adapter_lineage` (`L4-L8-adapter-lineage.md:29`); pilot variance and intracluster correlation with at least three reruns per task set (`RR:41-43`). After: independent claims review and settled resource receipt (`RR:51-52`).

**Risks.** The working tree has many untracked line modules, so tree hashes must come from a committed tree. Variance data comes from an approved pilot not yet released. Holm correction for registered secondaries (`RR:45`).

---

## 4. M5 (L4-E adapter and L8-D)

**Decision needed.** (a) Ask the L4-E author to supply the prospective training visit and matched context schedule, rendered inputs, protected source custody and a separately reviewed objective and trainer config (`runs/l4e-prospective-trainer.QIXxzB/coordinator-packet.md`, last paragraph). (b) The resource reviewer prices the smallest protocol-valid tranche, including evaluation and checkpoint emission. (c) Alejandro admits it. L8-D freeze follows a settled L4-E receipt. Deciders: trainer, protocol author, independent reviewer, L8-D author and custodian (`CB:33`).

**Command once admitted.** Native trainer missing. The only run is a CPU verification, which refuses configs that try to authorize training: `bash runs/l4e-prospective-trainer.QIXxzB/verify.sh`. It runs `python3 -B -m lab.l4e_timeline ...` and `python3 -B -m lab.l4e_prospective_trainer fixture/timeline --plan fixture/trainer-plan.json 97e82a76... ` against the pinned receipt. Note `lab.l4e_prospective_trainer` exists only inside the run's `source/` closure, not under `lab/`. For L8-D: `python3 -m lab.adapter_lineage ...` and `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m lab.l8_loader_receipt runs/l8-loader-scripted.cDdneC runs/l8-loader-scripted.cDdneC/l8.json --plan-sha256 2154e775... --max-bytes 2048` (`L4-L8-adapter-lineage.md:82-85`, synthetic fixture only).

**Resource reservation.** L4-E: up to 13.5 GPU-hours (`RR:32`; `SAR:13`); SAR recommends reviewing a shorter first tranche, no figure given. The shared residual is 9.5 and must also cover Grover, the second family and the controller (`SAR:16-19`, `SAR:55-56`), so the full ceiling cannot be placed. Memory, runtime and tranche size: not in the repo; preconditions.

**Protected inputs and custody.** Immutable base revision and adapter config, training provenance, the matched context control, and before/after checkpoint digests (`RR:61-65`). Held-out probe split and sample, family and content-digest disjointness (`L4-L8-adapter-lineage.md:15-19`). The trainer packet's compared arms differ in visit counts by design; no equal-compute claim follows (coordinator-packet).

**Stop conditions.** None frozen. L8-D holds when the before and after checkpoint bytes are identical (`L4-L8-adapter-lineage.md:23-25`).

**Rollback.** Cross-cutting item 7. A checkpoint is a new artifact; discard it, do not overwrite.

**Tests before and after.** Before: `bash runs/l4e-prospective-trainer.QIXxzB/verify.sh`; `lab.tests.test_adapter_lineage` (19 tests, `L4-L8-adapter-lineage.md:55`). After: independent training and settlement receipt, loader byte receipt, and the L8-D preflight against the settled L4-E digest (`L4-L8-adapter-lineage.md:3-6`, `:87-94`).

**Risks.** Tied-parameter loaders can mutate a module before the state check fails; a loader that reuses instances needs a rollback path (`L4-L8-adapter-lineage.md:96-101`). Unvalidated hook procedure. The 13.5 vs 9.5 gap. L8-D positive claims need independently established consolidation.

**Recommendation: not yet.** Approve now only the non-GPU request that the author and reviewer deliver the schedule and a priced smallest tranche. Admission after that.

---

## 5. M6 (coordination, topology)

**Decision needed.** Freeze the authority and access contrasts, exact intervention and matching control, stopping rules, observed delivery, eligible held-out tasks, independent verification and measured caps and costs (`CB:34`); then admit a protected native run. Deciders: author, custodian, resource reviewer; Alejandro for the spend.

**Command once admitted.** Native runner missing. The execution runner must attach per-attempt tokens and measured costs and the public case has no independent host transport (`runs/topology-two-round-joined.FRL4cn/owner-packet.md`, last paragraph). CPU: `bash runs/topology-two-round-joined.FRL4cn/verify.sh` (unittest `test_join`, `make_fixture.py`, `replay.py` against pinned plan, capture, assessment and catalog), and from the pinned closure `python3 -B -m lab.topology_matched_traversal` after `sha256sum -c source.sha256` (`Topology-matched-traversal.md:45-49`).

**Resource reservation.** No M6-specific GPU-hours exist in the repo. The related line ceilings are L5 at 3 and L7 at 8 (`RR:22,24`), and the L5/L7 topology extension has its own allocation checks (`RR:73-79`). The second-family, Grover and controller rows are unplaced (`SAR:14`). Fixture "units" (28 per cell) are scripted and are not tokens or cost (`owner-packet.md`; `Topology-matched-traversal.md:143-144`). Precondition: a resource-owner allocation and cap.

**Protected inputs and custody.** Held-out tasks, scorer and sample custody with independent assessment (`owner-packet.md`; `Topology-matched-traversal.md:35-36`, `:99-100`). A direct authority contrast needs a separately frozen common delivery schedule (`Topology-matched-traversal.md:73-76`).

**Stop conditions.** Not frozen. Scripted rules to preserve: a stop after one acknowledgment with a missing receipt withholds every own-access comparison against that baseline (`owner-packet.md`).

**Rollback.** Cross-cutting item 7.

**Tests before and after.** Before: the two verify commands above and the 9 and 11 test suites cited at `Topology-matched-traversal.md:51`, `:95`. After: independent scoring, observed host receipts, realized cost reconciliation.

**Risks.** All current counts (432 arms, 121 arms with more verified tasks) come from engineered public fixtures and are no estimate for a model (`Topology-matched-traversal.md:29`, `:118-119`). Equal-ceiling is primary; the equal-realized-cost slice is only descriptive (`:141-143`). `lab/topology_matched_traversal.py` is untracked.

**Recommendation: not yet.** Approve after the contrast is frozen, caps are priced, an allocation exists, and a host transport is reviewed.

---

## 6. M8 (SmolLM3-3B native smoke, 0.1 GPU-hour)

**Decision needed.** Route one public, local SmolLM3 CUDA load-and-generate smoke through Spark admission (`SMO:3-6`): one deterministic prompt of 73 input tokens, thinking disabled, 2-token output cap. Required from named owners (`SMO:9-14`):
- Spark storage operator and independent runner reviewer: canonical model and worker paths, and evidence the backing bytes stay fixed through cleanup.
- Spark resource owner: reconcile the program ledger, keep the 4.0-hour T7 hold, record the scoped 0.1 GPU-hour `spark-replication` reservation, and confirm a window meeting the reviewed envelope (or a reviewed fitting one).
- Local Coding Agent Coordinator and independent admission reviewer: route the issuer's one-use record and keep its exact SHA-256 separate from the admission file.
- Spark operator: run the launcher as `adelmar` (UID 1000) under the shared guard lock.

Alejandro is the approver for the spend and the launch. The L1-L3 replication freeze is a separate later decision (`SMO:3-7`; `CB:36`).

**Command once admitted.** Exists, in a detached reviewed bundle. Stock argv from the argparse in `runs/replication-smollm3-staging.out5A0/native-launch-reviewed.tl0ZlD/lab/smollm3_smoke_launch.py` (lines 185-194):

```
python3 -m lab.smollm3_smoke_launch RECEIPT RESERVATION SNAPSHOT WORKER WORKER_MANIFEST OUTPUT \
    --admission-sha256 <issuer-held-sha256> --approved-launch
```

`OUTPUT` is created with mode 0700 and the launcher refuses without `--approved-launch`. Notes: (1) `lab/smollm3_smoke_launch.py` in the checkout is untracked but byte-identical to that bundle copy (checked with `diff -q`; I did not diff the later `native-launch-cancellation-final.v022iV` closure that SM:174-177 names as final). (2) The detached patch `runs/m8-smoke-bound-opening.xlu84i` makes the launch also require `--opening-balance LEDGER R2_GUARD PLACEMENT PLACEMENT_SHA256` (`runs/m8-smoke-bound-opening.xlu84i/OWNER.md`); it is not adopted, so the final argv depends on which source the owner adopts. Working directory and `PYTHONPATH` for the launch are not stated in the packets; the operator must confirm. The metric verifier takes `guard.jsonl`, the reviewed snapshot path and worker mount path positionally plus `--host-capture-sha256`, `--worker-log-sha256` and `--admission-id` (`SM:142-144`). The `cancel` receipt is verified by `replay_cancellation.py` (`SM:168-184`).

**Resource reservation.** 0.1 GPU-hour placed in `spark-replication` from the 9.5 residual, leaving 9.4 (`SAR:55-56`; `Portfolio-evidence-and-resource-reconciliation-20261121.md:259`), program 65.876877 if the historical ledger stands (`SAR:61-62`). Proposed envelope: 70 GiB pre-start host headroom, 300-second outer deadline, 0.1 GPU-hour reserve, leaving up to 60 seconds after the deadline before the reserve is exceeded (`SM:43-46`). Memory evidence: 6,167,546,549-byte staged model; `MemAvailable` 57,100,444 KiB against the 73,400,320 KiB check at the 2026-11-22 00:33:35 UTC readback (`SMO:17-22`). Runtime evidence: two staged-file integrity passes took 7.444 and 4.601 seconds; create, inspect and cleanup time were not measured (`SMO:24-26`). The CPU receipt is single-thread; CUDA compatibility is unmeasured (`SM:26-32`). The final pre-attachment check needs 300 seconds still available (`SMO:23-24`).

**Protected inputs and custody.** The smoke uses public inputs only; the protected L1-L3 cohort is not touched. Pinned digests (`SMO:30-38`): model manifest `6ff79f0d...9d7f`, worker closure `e2146b3a...24b6`, CUDA plan `514d0dec...26dc8`, stock source manifest `c8164f59...a450a05c`, create recipe `27a220e9...3a43`. The model and worker directories are mode 0775 on writable ext4; a Docker read-only bind does not stop a host writer, so the storage owner must provide custody evidence for the actual paths (`SMO:11`, `SMO:28-34`; `SM:126-129`).

**Stop conditions.** 10 GiB host memory stop and the physical guard lock (`SM:39-42`); 300-second outer deadline; pre-attachment input drift stops the launch before attach (`SM:159-166`); any uncertain terminal fact keeps the hold (`SMO:48-52`).

**Rollback.** The mock chain shows the reservation held until an exact settlement or a verified `cancel` returns the unused reserve at zero charge (`SM:159-184`). A real launch follows item 7: exact-ID container removal, attachment reaping, durable capture, then settlement. A missing or uncertain terminal fact keeps the hold (`SMO:48-52`).

**Tests before and after.**
- Before: `bash runs/m8-smoke-bound-opening.xlu84i/verify.sh` (75 tests) and `verify-combined.sh <new-absolute-scratch>` (78 tests) (`runs/m8-smoke-bound-opening.xlu84i/OWNER.md`); `sha256sum -c source.sha256` in the operator bundle and `python3 -B replay.py` (`SM:134-137`); `python3 -B replay_cancellation.py` (`SM:182`); `lab.tests.test_spark_calibration_guard`.
- After: exact pre-start inspection, host capture and worker-output pins; verified CUDA load and generation result; watchdog and exact-ID cleanup; independent settlement or cancellation (`SMO:48-52`).

**Risks.** The stock memory gate fails at the last observed memory. CUDA create and attach are unverified outside mocks (`SM:66-68`). Opening verification is an R2-only cut and does not certify later ledger activity (`runs/m8-smoke-bound-opening.xlu84i/OWNER.md`). The retained opening and recipe joins used synthetic admission inputs (`SMO:44-47`). The reserve overshoots by at most 60 seconds on cleanup. It is a technical smoke only and carries no replication claim.

**Recommendation: approve after** these preconditions: (1) fresh memory reading at or above the 70 GiB check, or a reviewed fitting envelope; (2) storage custody evidence for the model and worker paths; (3) the resource owner writes the `spark-replication` placement and confirms the current ledger head; (4) the owner adopts one launcher source (with or without `--opening-balance`) and commits it; (5) issuer's one-use admission with a fresh UTC window. It is small, bounded and the only item with a reviewed launcher.

---

## 7. M9 (combined controller vs plain team)

**Decision needed.** Select eligible components, comparator, safeguards, protected task families and matched caps; then admit a combined-vs-plain run with independent witnesses recording dispatch, observed charges and outcomes (`CB:37`). Deciders: integration author, task custodian, claims reviewer; Alejandro for the spend.

**Command once admitted.** Native missing. Only CPU validators exist: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest -q lab.tests.test_controller_pair_audit lab.tests.test_controller_selection` (`CCD:105`, and `CCD:72` for the selection tests), `lab/controller_selection.py` and `lab/controller_pair_audit.py`. The selection validator returns `validation=structure_and_pins_only` and `scientific_acceptance=false` (`CCD:62-64`).

**Resource reservation.** None established. "No controller run, sample size or incremental allocation is established" (`CCD:5`). The 70 GPU-hour program ceiling is already fully allocated by current planning rows, and the combined comparison needs a recorded placement before any incremental commitment (`CCD:40`; `SAR:14`). The 9.5-hour residual is shared with the adapter, Grover and replication (`SAR:16-19`). Memory and runtime: none in the repo; preconditions. Hosted USD also needs placement (`CCD:40`).

**Protected inputs and custody.** Integrated evaluation sets sealed by task family, lineage and seed until both arms freeze; a continual-learning benchmark and a unit-test-scored family held out; hidden scoring kept from workers, monitors and advisors; scorer identities and agreement receipts bound before runs (`CCD:34-36`). Any second-family claim needs its own predeclared mapping and independent holdout (`CCD:35`).

**Stop conditions.** Not frozen (`CCD:45`, `CCD:47`). Scripted audit policy: a cap breach or unresolved usage allows only charged cleanup, and later attempts in that arm are refused; a stopped arm gives a missing paired effect (`CCD:93-97`).

**Rollback.** Cross-cutting item 7. If no component qualifies, record that the trial lacks an eligible controller and the lines continue on their own protocols (`CCD:22`).

**Tests before and after.** Before: the two unittest modules above; the scripted pair audit reproduces `runs/controller-pair-scripted.Jc3FeF/audit.json` (SHA-256 `ccd7f345...b999`, `CCD:99-103`); the selection validator result `runs/controller-selection-scripted.8Jf9Zf/validation.json` (`CCD:67-68`). After: independent claims review, realized resource parity and the registered estimator (`CCD:75-78`).

**Risks.** EP-1 is still a draft and Pilot 3 failed the 150-output-token criterion at a maximum of 263 (`CCD:5`). Components qualify only from supported frozen results of M3 to M8, none of which exist (`CCD:9`). Unplaced hours. Shared-device contention.

**Recommendation: not yet.** Approve after at least one component has a supported frozen result, the plain baseline and caps are frozen, and the resource owner records a placement.

---

## Ordering suggestion

1. M8 is the only item with a reviewed launcher, and its preconditions are administrative.
2. M4 Group B scope rulings and Group A freezes cost nothing and unblock the rest.
3. M3 R3 L2 and L5 follow once a native runner is designated and custody exists; reconcile the L5 hours first.
4. M5, M6 and M9 wait on allocation: the 9.5-hour residual cannot cover the 13.5-hour L4-E ceiling plus the three unplaced rows.

Unchecked here: live host memory and ledger state, whether the `v022iV` closure matches the checkout launcher, the per-line freeze docs under `prereg/` and `docs/reports/workplan-ep/Execution-plan-20261123.md`, and the lab sources of items other than the ones diffed or grepped.
