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

## First proposed replication placement

Under the owner's November 21 delegation, the lane selected the public
SmolLM3 technical smoke as the first proposed incremental replication
charge. Place 0.1 GPU-hour in `spark-replication` from the 9.5 GPU-hour
shared residual. This would leave 9.4 GPU-hours there for the adapter,
Grover, controller, and further replication work. The R2/R3 and L1–L8
amounts and provisional T7 hold stay in the accounting.

The retained settlement replay verified a historical program balance of
65.976877 GPU-hours. A 0.1 GPU-hour hold against that balance would yield
65.876877 GPU-hours. That is a proposal based on the historical ledger,
and no reservation was written. The resource owner must reconcile
current balances and record the placement. The independent admission
reviewer must provide the exact one-use pin for the reviewed bundle.

The exact smoke launcher refused its existing memory check in the
November 21 sample. Host `MemAvailable` was 57,997,260 KiB against the
existing 73,400,320 KiB requirement. The resource and runner reviewers
can use a suitable window or review a revised bounded envelope. Spark
service ownership and the existing guard remain in place.

The replay evidence is
`runs/smollm3-placement-review.oqs7DV/historical-audit.json`,
SHA-256 `643ea2e89a5561ea4583648d4a519b5555d4827321c9345e59e49b6359c47154`.
[Exact smoke bundle and receipt requirements](SmolLM3-native-smoke-packet.md)

## Deadline and device time

At the November 22 00:18:56 UTC checkpoint, Spark reported one NVIDIA
GB10. The Monday 09:00 UTC deadline left 117,664 seconds, or 32.684444
hours at full serial utilization. This is a physical-device upper bound
for newly started serial experiment work. Host availability, service
contention, ordered dependencies, and cleanup can reduce usable time.

The 49 GPU-hours across L1–L8 and the historical 65.976877 GPU-hours of
remaining program balance are resource ceilings. Both exceed the
checkpoint's remaining serial wall time if used in full. Actual native
durations and deadline feasibility remain unknown. A reviewer can
prioritize a truly admissible tranche only after checking its measured
runtime and cleanup bound, prerequisite order, and separately assigned
capacity. Shared traces require prospective approval from each receiving
protocol, with one resource charge for the underlying job. Preserve
each milestone's registered comparisons and acceptance criteria.

Reproduce the timestamp, device count, line ceiling sum, and historical
ledger arithmetic from the repository root.

```bash
sha256sum -c runs/spark-deadline-envelope.gTLzpr/evidence.sha256
python3 -B runs/spark-deadline-envelope.gTLzpr/replay.py | cmp - runs/spark-deadline-envelope.gTLzpr/report.json
```

### SmolLM3 preflight lead time

One back-to-back offline pair ran the stock file validation against the
actual staged 6,167,546,549-byte model and pinned worker. The first pass
took 7.444 seconds and the second took 4.601 seconds, for 12.045 seconds
total. Both returned identical receipts. Linux reported approximately
2.82 GB and 0.12 GB of storage-layer reads respectively, so cache state
differed. The timing uses one process at nice level 10, unchanged caches,
and a fixed historical fixture timestamp. This single pair is a
scheduling observation, with no estimate of a worst-case duration.

The actual launcher also creates and inspects the container before its
final validation. Include those operations and confirm that the reviewed
admission still has the required 300-second window at the final recheck.
The measurement establishes the integrity-check lead time only. Current
admission, protected staging, CUDA duration, and cleanup remain open.

Verify the retained measurements and exact source references with
`sha256sum -c runs/smollm3-two-pass-leadin.vAJvJ9/evidence.sha256`.
