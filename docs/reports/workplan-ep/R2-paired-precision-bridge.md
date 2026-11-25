# R2 exact paired-variance precision bridge

The bridge starts from the pinned schedule and raw observations and
rebuilds the paired receipt. The separately pinned design binds the
schedule, cohort, outcome units, additive contrast, arm direction,
scorer and rerun envelope. An optional capacity receipt must bind the
same design and rerun count. The bridge passes the rational variance
of eligible cluster means directly to the prospective planner.

The prospective projection requires a complete eligible cohort under
this bridge. Unrecorded mates or excluded clusters keep the projection
unavailable. Fewer than two eligible clusters, zero variance, or
unspecified effect thresholds also withhold results that need those
inputs. Without capacity, a positive-variance design can calculate a
required count while projected SE and target reachability stay unknown.
The bridge does not establish external custody, observed SE, scientific
decision reachability, or authorization.

An exact synthetic boundary used cluster means of zero and 1/10,
giving a sample variance of 1/200. Its target SE was 1/20, so the
required count is exactly two clusters. Routing the same example
through an upward-rounded decimal SD would give a count of three.
The previous calculator's existing results and errors stayed identical
in 1,148 regression cases.

The retained historical L2 archive contains only two paired reruns of
one case and no eligible cluster. Its pinned preview uses
neutral-minus-warning solely to match the archived additive schema.
The actual prospective L2 estimator still needs author approval.
The historical preview has no approved additive thresholds, capacity,
or precision result. L1-B's relative reduction requires a separate
registered denominator and zero-baseline rule.

```bash
PAIRED=runs/r2-paired-l2-historical.ulNWCc
PREVIEW=runs/r2-paired-precision-l2.OkkOId
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:lab python3 -m lab.r2_paired_precision \
  "$PREVIEW/design.json" "$PAIRED/schedule.json" "$PAIRED/observations.json" \
  --design-sha256 52ce67f583baac0cd485ad7f953f83f161b3146cfcd6023b6cda1e6779effe30 \
  --schedule-sha256 a4c16fab774cbcd4d6ed5d88dcbc1ff7a5469b7a7196c92f57d39b097b4df3b1 \
  --observations-sha256 208e043aea7b0dc8685ef740a35346b1e21ee55e10d1334bb49b1ef4c9ade6c7
```

Historical report `runs/r2-paired-precision-l2.OkkOId/report.json`
replayed byte for byte, SHA-256
`b1416b2db06dc7483f400e90f7ae22447988129fe6b225c5a74bf7f6ea44a1eb`.
Synthetic exact-boundary report
`runs/r2-paired-precision-control.chPYMl/report.json`, SHA-256
`ffcf3a1ae25fc8b960068a7a3db21aa59d2ec7848ac03ca95c0076f2b523d844`.
[Paired receipt](R2-paired-cluster-receipt.md) · [Precision intake](R2-prospective-precision.md)
