# TREMOR Spark evidence and resource reconciliation

November 21, 2026 UTC · **1 of 10 milestones accepted.** This internal
checkpoint records which acceptance criteria the available evidence
supports and what the assigned owners still need to supply. The
[execution plan](Execution-plan-20261123.md) retains the full scope and
Monday morning checkpoint.

## Acceptance register

| Milestone | Evidence and disposition | Owner and remaining acceptance |
| --- | --- | --- |
| 1. Spark R2 calibration | **Accepted.** The native Qwen run used 83.242 seconds through confirmed cleanup. The GPU ledger settled 0.023123 hours. | The operator retains the accepted run and receipt. Later workloads have separate admission. [Settlement](Spark-readiness.md#calibration-result-and-settlement) |
| 2. Pilot 4 and EP-1 | **Blocked.** Pilot 3 selected shared order and reached 263 output tokens against a ceiling of 150. The exact Pilot 4 proposal replay matches the archive. The installed CLI refuses the new batch before execution. | Preregistration author records wording, scoring scope, duplicate credit, and order disposition. Spend and driver reviewers clear the exact revision. Operator records all seven separately gated Pilot 4 checks. Author freezes EP-1 before its separately admitted 60 episodes and reviewed analysis. [Gates](Pilot4-pricing-verification-gates.md) |
| 3. CPU benchmark and R3 | **In progress.** Three ordered 783-case R1 receipts match the pinned source. The optional Torch branch passed separately. Public mutation audit detected twelve variants. L2/L5 CPU interruption and custody rehearsals retain missing outcomes. L2 native inventory still lacks its entry point. | Local Coordinator routes quiet-host qualification, required module reviews and the formal bench verdict. Runner owners and custodians provide exact candidate, frozen inputs and capture, then admission and measured cleanup and settlement. [R1 audit](R1-evidence-review-20261121.md) · [R3 inventory](R3-L2-admission-inventory.md) |
| 4. L1–L8 portfolio | **In progress.** Each line has a reproducible public instrument check. The latest controls check measurement, missingness, cost or receipt integrity. | Line authors freeze scope, matched design and decisions. Custodians supply protected inputs and labels. Reviewers verify admitted outcomes or registered stops, uncertainty and actual costs. [Eight-line plan](R2-R4-protocol-readiness.md) |
| 5. L4-E to L8-D | **In progress.** The Qwen base and synthetic projection switch have measured CPU hook evidence. The runtime join verifies synthetic receipt bindings. | Trainer and reviewer settle the actual before/after checkpoints against the context control. L8-D author freezes the held-out probe afterward and the custodian verifies actual loading and capture. [Lineage](L4-L8-adapter-lineage.md) |
| 6. Coordination | **In progress.** Matched public traversal covers 54 blocks and 432 arms. Realized reads differed in 72 of 108 groups even with matched planned traversal. | Author and custodian freeze authority by access, common tasks and independent union. Outcome and resource reviewers verify protected matched results and realized costs. [Traversal](Topology-matched-traversal.md) |
| 7. Grover transfer | **Blocked.** Independent rational replay agreed with the public CLI and transfer scorer over 76 cases and 344 points. | After EP-1, author freezes the protected design, custodian and reviewer establish independent inventory and scorer custody, and the operator runs the admitted matched transfer with settlement. [Custody](Grover-holdout-custody-checklist.md) |
| 8. Second-family replication | **In progress.** SmolLM3 loaded and ran the public CPU probe. The CUDA launch and settlement chain has mock evidence. The exact weight-copy check and matched schedule checks pass offline. | Family and loader reviewer clears the designated model. Resource and admission reviewers record the exact reserve and launch pin. Custodian and author freeze disjoint tuning and paired protected L1–L3 transfer and recalibration against the common reference. [Smoke](SmolLM3-native-smoke-packet.md) · [Matched design](Second-model-replication-design.md) |
| 9. Combined controller | **In progress.** Scripted replay has one complete pair with delta 1/6 and a stopped pair with unavailable delta. Failed-only worker arms are refused as complete. | Integration author and claims reviewer freeze supported components, safeguards and baseline. Verify admitted held-out pairs and complete cost and settlement evidence. [Design](Combined-controller-design.md) |
| 10. Internal research report | **In progress.** The current checkpoint aligns reproducible evidence and local resource accounts with the acceptance register. | Claims reviewer reproduces eligible outcomes and their uncertainty. Resource owner reconciles provider and GPU records, supports the final cost attribution, and resolves or explicitly retains the historical T7 hold. |

## Resource readback

| Account | Current retained evidence | Reconciliation |
| --- | --- | --- |
| R2 native GPU | 0.100000 hours reserved, 0.023123 charged, 0.076877 released | No outstanding hold on this admission. The historical receipt reproduced byte for byte. |
| T7 historical GPU | 2.371010 generation hours from three retained traces. The reported completed-container subtotal is 8,655 seconds. | Full attempted work remains estimated, including failed and diagnostic intervals. Retain the provisional 4.0-hour program hold. |
| Program planning balance | 65.976877 GPU-hours after the settled R2 charge and provisional T7 hold. The R2/R3 share retains 7.476877 and the L1–L8 nominal ceilings total 49. | The residual is 9.5 hours shared by additional work. The proposed 0.1-hour SmolLM3 placement would leave 9.4 hours there. It has no binding reservation. |
| Hosted API | Four local ledger files contain 417 unique reservations and 417 charges. Reported gross local spend is USD 0.0413027. | The stored decimal sum is USD 0.041302700000000000620 because charge rows retain floating-point digits. Provider Console total remains unknown. Pilot 4 has no local ledger or run directory. |

[GPU settlement and placement](Spark-allocation-rephase.md) · [T7 source](../T7-smoke.md) · [API pricing and current gates](Pilot4-pricing-verification-gates.md)

## Reproduction

From the Murmuration root, verify the 21 exact receipt paths, including a
public replay from each line, with the following command.

```bash
sha256sum -c runs/portfolio-reconciliation.BNttQL/evidence.sha256
```

The manifest SHA-256 is
`b556f26b79998aa82d5129e89542543caa2d48dda699e214718346869761bc3d`.
The R2 replay, exact local API recount and verification log are in
`runs/portfolio-reconciliation.BNttQL`. Individual line checkpoints in
the execution plan record implementation, targeted tests, and source
identities. The repeated public outcomes do not resolve the open
scientific rows in this register.
