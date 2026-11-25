# TREMOR protocol readiness for R2 through R4

This is the internal drafting index for the eight portfolio preregistrations. Each line below
identifies the proposed primary contrast and the evidence needed to turn it into an executable
protocol. Numerical targets are design proposals. Freeze status and execution authorization are
recorded separately for each batch.

Use the proposal for exact predictions and the complete arm lists. Use the portfolio and live
checklist for sequencing and resource limits. EP-1 is a separate instrument and the initial
measurement for L5. [Proposal §5](../../PROPOSAL-RESIDENCY-V3.md#5-research-lines) ·
[Portfolio workplan](../../WORKPLAN-RESIDENCY-V3.md) · [Live checklist](../../WORKPLAN-CURRENT.md) ·
[EP-1 draft](../../../prereg/EP1.md)

## Primary contrasts and freeze inputs

| Line | Proposed primary contrast and endpoint | Matched comparators to retain | Artifacts and inputs still needed for freeze | GPU-hours / hosted stop |
| --- | --- | --- | --- | ---: |
| L1 · Verification | B. Compare susceptibility-guided and uniform verification on relative reduction in undetected false completions. Proposal target 25%, with a 10% interval boundary. The held-out fluctuation–response model is secondary. | Uniform checking, check where reruns disagree, equal-token retries, activity and mean-only predictors, and the pilot-fitted predictor. Charge measurement and checking to each arm. | Held-out condition IDs by tier and task, reruns and dose schedule, false-completion truth, tuning split, pilot variance and a predeclared rate denominator when the comparators approach the floor. | 8 / USD 24 |
| L2 · Memory error spread | C. Check whether R-targeted verification matches full-verification adoption within the proposed 3-point margin using at most half the checks, while outperforming random verification and cheap rankings. | Full and random verification, warning, origin binding, and ordering by out-degree, recency, or retrieval frequency. Use a fixed benign planted note and a trigger-only control. | Eligible parent–offspring events and an audited first-generation R calculation. Specify verification-share grid, adoption denominator, search rule for the minimum successful dose, and precision for the equivalence and ranking contrasts. The unplanted variant still needs a separate ruling and protocol. | 6 / USD 15 |
| L3 · Monitor ensembles | C. In the approved toy setting, compare the loss of catch rate under the registered selection-pressure condition. The proposal expects rotation to halve the ensemble loss and beat conservative aggregation. B, held-out catch-rate gain over top-k at 5% false-positive rate, is the specified fallback primary if the selection arm is declined. | Equal monitor calls for fixed and rotating views, conservative aggregation, one random view per decision, top-k, random k, and the registered selection rules. | Bind primary before running. Pin view definitions and call budget, blinded failure and clean pools, threshold-fit split, joint miss tables and paired discordance. Keep the toy setting defensive and within D1. | 4 / USD 24 |
| L4 · Memory consolidation | C. Test whether verified replay keeps false notes under 5% at the two strongest measured settings, uses at most 1.5 times the tokens under the defined cost contrast, and beats equal-token search in tokens per passing task. | Equal-token search or retries, plain and placebo consolidation, evaluator-gated write without replay, raw history, and no memory. Train the adapter as a separate local arm E. | Day and night trace chains, old and new stores with source IDs, measured compression ratios, scorer results, paired cost records, and calibration of the ladder and token-ratio reference. Freeze adapter data, controls, and checkpoint lineage separately. | 12 / USD 40, plus adapter below |
| L5 · Coordination | B. Test the carrier trade-off across authored and held-out norms, including whether context cuts held-out violations by at least 10 points and loses at least half its gain under registered disruptions. Track blocked legitimate work and cost alongside violations. | Context, memory, environment, code and neutral controls. For evaporating claims retain rank partition, lease timeout, coordinator assignment and disjoint scheduling. Keep frozen EP-1 contrasts separate. | Define N1 and held-out N2, checked predicate and permissible violations, comparably priced carrier scopes, disruption placement, matched rounds and common event schema. The L5/L7 topology extension has its own visibility and allocation checks. | 3 / USD 29 |
| L6 · Permissions | Primary. Evidence-based leases reduce unused grant exposure by the proposed 30% against both tuned fixed promotion/decay and time-boxed grants, at equal or lower blocked legitimate work and with no additional benign-rule violations. Proposal interval boundary 10%. | Tuned fixed rule, time-boxed grant, per-scope bound without pooling, static allow list and always ask. Tune on separate task sets. | Benign permission fixtures, independently labeled legitimate actions, exposure denominator, calibrated evidence bounds, scope pooling policy, grant change and revocation trace, and paired intervals for utility and violations. | 2 / USD 6 |
| L7 · Team scaling | B. At 16 local agents, compare active share and distinct passing work at equal tokens. Proposal targets at least 50% active for coupling-sized blocks against below 30% for a flat team, and more passing work than parallel smaller teams with selection. The 32-versus-4 correlation contrast is secondary. | Flat team, hub, random blocks of equal size, declared-scope blocks, and parallel smaller teams with hidden independent selection. Charge selection and coordination. | Seeded team layouts, task dependency graph, kept-result selector and cost, definition of active share, paired outcome variance and a minimum advantage margin. Record pairing, correlation spread and actual resource use at each approved local size. | 8 / USD 12 |
| L8 · Activation readouts | B. Compare text ensemble plus activation readout with text-only at 5% false-positive rate. Proposed gain at least 5 points, joint error correlation at most 0.3, and an upper-bound kill threshold of 2 points when the probe has no standalone advantage. | Text only, follow-up question and self-report, word-frequency control, random direction, mass-mean and logistic probes, and the planned multi-layer/token comparator. Use held-out labeled failures and aligned threshold fitting. | Verify local hook access, layer/token IDs, snapshot and preprocessing, probe training split, hidden labels, paired misses and threshold/normalization sensitivity. Prediction D additionally needs the frozen local L4-E lineage below. | 6 / USD 3 |

Source for the endpoints, comparator lists and proposed effect bounds is the corresponding line
in [Proposal §5](../../PROPOSAL-RESIDENCY-V3.md#5-research-lines). Resource columns are batch
ceilings in [Portfolio R4](../../WORKPLAN-RESIDENCY-V3.md) and
[Live checklist Phase 8](../../WORKPLAN-CURRENT.md#phase-8-tremor-programme-under-the-owner-budget-usd-170-api-70-gpu-h-addendum-7-2026-11-20).
Calibration and first local slices share 7.5 GPU-hours. The line total is 49 GPU-hours. With
those slices and up to 13.5 GPU-hours for L4-E, the program ceiling is 70 GPU-hours. Reconcile
actual usage before scheduling. The program's hosted limits are separate from Spark hours.

## Readiness evidence shared across lines

1. **R1 controls.** Supply the per-line scripted check and expected result, a replayable board
   trace, a scorer agreement receipt, a gate review, and one deliberately failing control.
   Preserve prior stores with provenance. Scripted outcomes validate the instrument.
2. **R2 calibration.** Record Spark memory and throughput evidence, and local hook status.
   Using the approved pilot, report variance or discordance and the intracluster correlation.
   Use task sets or chains as the unit, with at least three reruns per task set averaged first.
   Use the proposal's cluster-bootstrap plan and design effect. Specify support, kill and
   inconclusive intervals in advance. Estimate achievable precision at the actual cap and mark
   unreachable outcomes prospectively. Apply Holm correction to the registered secondaries.
   For proposed 5% false-positive readouts, preserve separate clean-threshold and failure pools
   and the proposal's minima of 400 clean and 200 failure episodes.
3. **Per-batch freeze artifact.** Record the protocol and code/tree/config hashes, model snapshot,
   task-family revision, seed map, train/pilot/held-out splits, scorer IDs, primary and secondary
   contrasts, economic and statistical stopping rules, expected and maximum resources, and
   exact approval and review evidence. A run record includes the manifest, replayable evidence,
   adjudication, resource ledger, and passage or stop reason.
4. **Open interpretation checks.** For L2-E, the proposal's initial support text uses a lower
   bound above 1% and the later accuracy note uses above 5%. Resolve this before any approved
   L2-E protocol is frozen. For L4-C, bind the token reference and the joint decision across
   the two strongest settings. For L5-B and L7-B, freeze the respective equivalence and
   meaningful advantage margins. Select L3-C or its stated fallback before seeing outcomes.

## L4-E checkpoint dependency and coordination extension

- **L4-E → L8-D.** The local adapter design has a recorded D3 scope and a separate execution
  gate. Before L8-D, record the immutable base revision and adapter configuration, training
  provenance and resource receipt, the matched context control, and digests for the precise
  before/after checkpoints. Bind the calibration and held-out prompt manifests and exact
  activation hook/normalization protocol. L4-E's draft predicts at least a 10-point improvement
  over context on the sibling norm and at least twice as many nights to correct the planted
  wrong fact. The L8-D manifest must cite the L4-E receipt and
  checkpoint digests before collecting held-out reads. Compare the resulting direction with a
  random-direction control on held-out prompts. L8-B has its own prerequisites.
  [Approval record](../ep-approvals.md#addendum-9-2026-11-20-1805-utc-overnight-directive) ·
  [Proposal L8](../../PROPOSAL-RESIDENCY-V3.md#line-8-activation-readouts-as-one-more-check-on-a-team) ·
  [Checkpoint and split preflight](L4-L8-adapter-lineage.md) · [Scripted L8-B readout](L8-activation-scripted.md)
- **L5/L7 topology.** First preserve the verified deduplicated independent union on the same
  tasks and cost ledger. For an authority contrast, hold evidence visibility fixed across fixed
  lead, rotating lead/helper, and peer policies. Measure evidence access in a separate matched
  contrast within the same authority mode. Preregister disruption against a no-disruption
  control, score work independently, and charge the same prices for coordination and
  verification. Scope and budget frontier-advisor escalation as its own contrast. The scripted
  evidence is available and the live allocation and protocol are open.
  [Topology design](../../WORKPLAN-SWARM-AND-VISUALS.md#new-hypothesis-leadership-can-move-with-the-work) ·
  [Scripted evidence](Topology-scripted-evidence.md)
