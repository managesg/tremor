# Spark GPU allocation decision

Keep the 4.0 GPU-hour T7 hold in the budget until the resource owner records a
disposition. The retained calibration ledger has settled 0.023123 GPU-hours
inside R2/R3. Its remaining program balance is 65.976877 GPU-hours, of which
7.476877 is the remaining R2/R3 allocation. These are the balances at that
settlement. A new admission needs current balances and charges.

| Planned work | Remaining nominal GPU-hours | Treatment in the draft |
| --- | ---: | --- |
| R2/R3 calibration and first local slices | 7.476877 | Retain the remaining shared allocation. |
| L1–L8 line work | 49.0 | Retain the eight individual ceilings. |
| L4-E adapter | Up to 13.5 | Review a shorter initial tranche and defer the rest of this ceiling. |
| Grover transfer, second-family replication, and combined controller | Unplaced | Record separate incremental allocations or reviewed attribution to existing rows. |

The first two rows leave **9.5 GPU-hours** of capacity. That amount is shared
by the adapter and any incremental work from the last row. A 9.5-hour adapter
reservation by itself leaves zero for those three milestones. It would be
premature to adopt 9.5 hours as an adapter run cap or to interpret an unplaced
row as having zero cost.

## Proposed sequence

1. Continue preparing the already allocated R3 first slices. Before launch,
   reconcile the current shared and program balances and clear the exact
   protocol, custody, runner, and admission gates.
2. Ask the adapter owner and independent protocol reviewer to price the smallest
   valid paired tranche, including checkpoint save and verification. The
   trained pair and comparable context control must meet the existing
   scientific checks before the L8-D freeze.
3. Ask the Grover, replication, and controller owners to identify incremental
   charges and any eligible jointly produced traces. Credit a shared trace
   only where both protocols prospectively permit its use, and charge the
   underlying job once. Place all incremental costs explicitly before
   approving any adapter reservation.
4. If these minima exceed the 9.5-hour envelope, defer the unfunded tranches.
   The resource owner can reconcile the missing T7 terminal records or
   rephase other ceilings via the owning protocol reviewers. Keep each
   milestone in the acceptance register during deferral.

The observed ledger balance and arithmetic establish an envelope. The
adapter duration, overlap eligibility, and feasibility of the full program
remain decisions for the named reviewers, with independent scientific and
resource checks. This draft changes no allocations and authorizes no jobs.

[Settlement](Spark-readiness.md#calibration-result-and-settlement) ·
[Nominal phase allocations](../../WORKPLAN-RESIDENCY-V3.md#phase-r4-line-runs-under-the-owner-budget-stops-from-docsworkplan-currentmd-phase-8) ·
[T7 estimates](../T7-smoke.md) ·
[Adapter and activation handoff](L4-L8-adapter-lineage.md)
