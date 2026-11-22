# TREMOR coordinator blockers

November 22, 2026 UTC. **1 of 10 milestones accepted.** The current
checkpoint is Wednesday morning, November 25. R2 calibration is accepted. Pilot 4 and Grover
transfer remain blocked. The seven other milestones have completed local
work and outstanding acceptance dependencies.

## Resolved locally

The lane's November 22 one-shot publication timer was stopped under the
current publication hold. Systemd confirmed no next trigger and no
previous trigger. The publication service is inactive. The staged release
remains clean at a99cddd. The timer unit is still enabled and persistent,
so a user-manager restart or manual activation can rearm it. A durable
configuration change needs the owner's named approval and the release
owner's disposition. [Timer evidence](../../../runs/publication-hold-confirmed.HiOLje/evidence.sha256)

Local evidence ready for review includes three full CPU suites on the
corrected R1 source, the reproduced three-file R1 checkout repair, the full
offline Pilot 4 retry boundary, matched public coordination controls, and
the verified preliminary findings. These results are already in the lane
outbox.

## Current blockers and owners

| Scope | Owner and action required |
| --- | --- |
| Coordinator delivery · X44 | **Local Coordinator Manager** acknowledged TREMOR Table A through Spark outbox line 3111 at 13:38 UTC. New packets use the established outbox. [Table A readback](../../../coordinator-outbox/pc-ack-table-a-tremor-20261122-successor-1338Z-through-3111.md) |
| M2 · Pilot 4 and EP-1 | **Owner, preregistration author, spend and driver reviewers** record the current named release, freeze wording and scoring/order rules, and clear the exact driver and pricing coverage. After all seven Pilot 4 checks, the author can freeze EP-1 and route the separately admitted 60-episode experiment. [Gates](Pilot4-pricing-verification-gates.md) · [Offline retry boundary](../../../runs/pilot4-full-retry.ZwWZHE/OWNER_PACKET.md) |
| M3 · R1 benchmark and checkout | **Coordinator** nominated the exact corrected source under X42 for source review. **Local Coordinator Assistant**, designated independent host reviewer, records a reasoned disposition for each of three windows. The separate bench reviewer has yet to start. **Source owners** review outstanding grader and readout findings on the exact nominated bytes. **Preregistration author and independent custodian** must deliver the protected N2 rule and case commitment. The designated reviewers owe fresh module verdicts and the independent bench verdict. [X42 source nomination](../../../coordinator-outbox/pc-x42-r1-source-nomination-1341Z.md) · [Pinned reviewer intake](../../../runs/r1-source-nomination-readback.Lgn6EH/OWNER.md) · [X42 reviewer designation](../../../coordinator-outbox/pc-x42-r1-reviewer-designation-1355Z.md) · [Grader consistency evidence](../../../runs/r1-execution-consistency.BtUauk/OWNER.md) · [CPU series](R1-corrected-candidate-suite-series-20261122.md) · [Checkout repair](../../../runs/r1-tracked-entry-audit.VQ72kG/OWNER.md) |
| M3 · R3 L2 and L5 | **Runner owner, protected-data custodian, resource/admission reviewer and owner** freeze cohorts, schedule, scorers and native runner, verify independent capture and mount custody, and record an exact reservation and one-use admission. Separately, freeze and review the CPU scorer-canary case study. R3 requires the per-result Opus claims check. [L2 inventory](R3-L2-admission-inventory.md) · [L5 protocol](R3-L5-protocol-draft.md) |
| M4 · L1–L8 | **Line authors, custodians and independent reviewers** need the eight protocol decisions below and a separate named release for the R2 sensitivity pilot. Freeze each line with a tree hash and measured variance and clustering, or record the prospectively reachable outcomes. Secure protected inputs, exact admission, and independent outcome and cost reviews. [Eight-line protocol readiness](R2-R4-protocol-readiness.md) |
| M5 · L4-E and L8-D | **Trainer, protocol author and independent reviewer** freeze actual adapter and context-control schedules and settle the paired before/after checkpoints. **L8-D author and custodian** then freeze the held-out probe and verify observed installation and hook capture. [Lineage](L4-L8-adapter-lineage.md) · [Trainer packet](../../../runs/l4e-prospective-trainer.QIXxzB/coordinator-packet.md) |
| M6 · Coordination | **Author, custodian and resource reviewer** freeze authority and access contrasts, exact intervention and matching control, stopping rules, observed delivery, eligible held-out tasks, independent verification and measured caps/costs. [Coordination packet](../../../runs/topology-two-round-joined.FRL4cn/owner-packet.md) |
| M7 · Grover transfer | **EP-1 author, Grover author and independent custodian/scorer** complete the EP-1 prerequisite, then freeze protected structural splits, primary estimand, stopped-pair policy, defensible sample plan, and measured resource admission. [Grover custody](Grover-holdout-custody-checklist.md) · [Estimand packet](../../../runs/grover-statistical-envelope.6Cln7i/OWNER.md) |
| M8 · Second-family replication | **Storage operator, admission issuer and resource owner** provide fixed backing paths, a reviewed memory/runtime window, the scoped 0.1 GPU-hour reservation and one-use approval for the exact SmolLM3 smoke. **Author and independent custodian** next freeze the protected L1–L3 unchanged-transfer and recalibration comparison against the common reference. The recorded memory sample was below the stock threshold. [Operator packet](../../../runs/smollm3-native-owner.vt3Sj1/OWNER.md) · [Pairing design](Second-model-replication-design.md) |
| M9 · Combined controller | **Integration author, task custodian and claims reviewer** select eligible components, comparator, safeguards, protected task families and matched caps. Independent witnesses must record dispatch, observed charges and outcomes. Public SQLite and scripted checks have been verified. [Controller design](Combined-controller-design.md) |
| M10 · Final report and staged release | **Claims reviewer and resource owner** reproduce accepted native outcomes, uncertainty and costs, documenting unknown billing and disposition of the provisional T7 hold. **Release owner and proposal reviewer** separately route the pre-share source/quote review, D6 Console reconciliation, and G8 owner-only sharing. D6 belongs to publication. Pilot 4 has its own Console criterion. [Findings](Portfolio-evidence-and-resource-reconciliation-20261121.md) · [Spark allocation](Spark-allocation-rephase.md) |

### M4 decisions to route in parallel

- **L1 verification:** Freeze estimand, opportunity denominator, zero and
  missing-pair rules, tuning/holdout split and cluster precision.
- **L2 memory spread:** Freeze eligible transmission, adoption denominator,
  dose grid, censoring and equivalence/ranking precision. An unplanted
  variant needs its own scope ruling.
- **L3 monitors:** Choose the approved primary or pre-specified fallback,
  then freeze clean/failure pools, view definitions, equal call budget and
  threshold-fitting split.
- **L4 consolidation:** Freeze matched day/night stores, source-version
  grading, cost and compression denominators, and joint decision rule.
  An L4-D setting outside D1 needs a separate scope ruling.
- **L5 carriers:** Seal N1/N2 and private verdicts, carrier delivery, prices,
  matched disruptions, opportunities and common event evidence.
- **L6 permissions:** Freeze benign permission and legitimacy labels,
  exposure denominator, calibrated evidence bounds and paired decisions.
- **L7 scaling:** Freeze hub and participation definitions, seeded layouts,
  work selector, variance and meaningful gain, and equal realized tokens.
- **L8 readouts:** Freeze the causal decision token, raw capture, blind
  calibration and holdout splits, feature fitting and matched operating
  point. L8-D also depends on settled L4-E lineage.

## Future risks to monitor

- **Deadline and shared Spark capacity.** One device and reserved serving
  capacity constrain serial wall time. Budget ceilings do not estimate
  durations. Obtain measured runtimes and cleanup windows before placing
  approved tranches. Do not spend the same residual twice. The existing
  R3 protocol caps the shared first slices at 7.5 GPU-hours, specifies
  shrinking the L5 slice first at that stop, and requires a stop and report
  if the local 4B work hits the plain-coordination floor. Retain the
  10 GiB watchdog and short-run envelope if memory risk remains unbounded.
- **Candidate or price drift.** Source, policy, filesystem identity, or
  date changes can invalidate pinned review evidence or pricing windows.
  Qualify the exact run at launch. A rejected R1 window may need one
  replacement on the same nominated source. A changed candidate needs
  qualification against its own exact source.
- **Hosted cap and Console mismatch.** Before any paid work that needs
  more than the current code or per-file ceiling, the owner and spend
  reviewer must resolve the allocation mismatch through the existing
  gated code and Console process. Record the applicable cap. The offline
  Pilot 4 replay grants no spending authority.
- **Interruption, uncertain cleanup and missing costs.** Preserve pending
  holds, missing outcomes and unknown usage until exact cleanup and billing
  evidence arrives. Reconcile before subsequent admission.
- **Insufficient matched support.** Contention, attrition, label leakage
  and unequal realized costs can invalidate a contrast. Make the handling
  of unknowns, cluster size, stop outcomes and uncertainty prospective.
- **Reviewer availability and scope changes.** Assign distinct reviewers
  and custodians early. A changed release scope needs an independent
  claims review and new publication authorization. The inactive but
  enabled one-shot timer needs a durable hold if a user-manager restart is
  possible.
