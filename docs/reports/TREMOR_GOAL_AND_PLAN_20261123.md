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

## Data transfer status

Source: `/home/adelmar/SeaBridgeAI-data/_manifests/SPARK_DATA_MAP_20261122.md`.

The data map lists no TREMOR data, and no TREMOR step depends on AWS or PC data. All TREMOR evidence, archives and run packets were produced on the Spark and live under `/home/adelmar/SeaBridgeAI/murmuration/runs` and the repository. Each data step is therefore neither DONE-BY-TRANSFER nor WAITING-ON-TRANSFER. It is either already local or waits on a named admission:

- **M1, M3 X42 and R3 L5, M10:** local on the Spark, sha-verified in the packets above. Nothing needs to be collected again.
- **M8 SmolLM3 weights and backing storage:** waiting on the storage operator's admission, not on the transfer.
- **AWS:** none needed. The only AWS reference in `docs/reports/workplan-ep/` is the M2 hold in `Pilot4-pricing-verification-gates.md`. This lane never connects to AWS.

## Next action

**WAITING.** No row can run without an owner decision. The first reply should answer the ordered X42 request in `coordinator-outbox/overnight-20261121.md`:

1. Source owners decide whether to adopt the BtUauk grader fix.
2. PC then launches the bench reviewer on the final cut, or delegates that launch to this lane.

Limits are unchanged: no push or PR, no deletion, no paid calls, no AWS access, no secrets printed, one session per lane.
