# L4-B recovery observation and censoring

L4-B compares recovery time just below the fitted (R=1) boundary
with recovery time two settings lower. The proposal predicts at least
a twofold ratio. It separately proposes support when the lower
interval bound exceeds 1.5 and a kill when the upper bound is below
1.25. It calls for a time-to-event analysis with right-censoring and a
ratio of restricted means. The existing recovery helper gives a time
or `None`, so its output cannot distinguish missing follow-up from a
completed observation interval. [Proposal](../../PROPOSAL-RESIDENCY-V3.md#line-4-dreaming-as-error-correcting-consolidation)

## Development observation record

Two independent pins bind the candidate design and the observed
chain inventory. The design declares elapsed nights from a frozen
shock, horizon, consecutive confirmation rule, and exact scorer pin.
The observation records one chain terminal and the predicate for
each available night. Omitted nights and explicit unknowns remain
visible. The candidate uses the confirmation night as the event and
also reports the onset of the confirming streak.

| Disposition | Required evidence |
| --- | --- |
| Confirmed recovery | First complete qualifying streak with known follow-up through confirmation. |
| Right-censored | Full known follow-up through the planned horizon and no confirmed event. A streak still too short to confirm is reported separately. |
| Incomplete follow-up | A completed-run declaration with missing or unknown observation nights. A later observed streak cannot establish the first event across an earlier gap. |
| Operational truncation | A stop before a reliable first event. The observed prefix stays visible without a scientific censor time. |

A confirmed event in the known prefix keeps its observed time even if
the operation later stops. The verifier checks the pinned record and
classification. Native observation accuracy and scorer independence
remain outside this receipt.

## Decisions before native assessment

The L4 author should bind the boundary fit and selected settings
before opening recovery outcomes. Freeze shock time and delivery
evidence, baseline and tolerance, required hold or correction
evidence, and whether the event clock uses onset or confirmation.
Define the common restriction horizon and observation cadence,
including whether follow-up can confirm an onset at the horizon.
Specify censoring, interval-censoring, stop and missingness handling,
and the assumption needed to use the observed follow-up distribution.
Record the matched chain inventory, cluster bootstrap and ratio
behavior if the comparison has no positive restricted mean or
insufficient follow-up. Independently review the resulting estimator,
capacity and approved pilot before opening the assessment.

The retained L4 memory control has four scripted chains and one
withdrawal of a planted note. It records no correction event and no
qualified L4-B recovery follow-up. The reference value was available
to the verifier as an input. It was never emitted as a correction.
The prototype therefore does not calculate a restricted mean or a
scientific ratio for that archive.
[Archived source provenance](L4-E-public-content-parity.md)

## Reproduce the retained checks

```bash
BUNDLE=runs/l4b-recovery-observation.63yNsN
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:lab python3 -m lab.l4b_recovery historical \
    runs/l4-memory-scripted/trace.json \
    --archive-sha256 067a0918fb97fd24bd86a8227952aeaf0a8a878c538038c485fcee39c9fbbe6d
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:lab python3 -m lab.l4b_recovery verify \
    "$BUNDLE/design.json" "$BUNDLE/observations.json" \
    --design-sha256 6ca332d610637cce86b1771be1f76f33504c9971c2e9db0ff62c35e8a308fdb6 \
    --observations-sha256 c1ff34a3bda694f6be77de801a7eace4efcb33b4eef492aea65bbd3dbb7b8dab
```

Both reports replayed byte for byte. The historical report has SHA-256
`11b4cc576fd71e9fc268a38e5c300ee336761777c6eec0b61c87869b7bf7887e`.
The synthetic four-disposition report has SHA-256
`55c12d803d27e1638c1ef363372e6a4d50ab13f1f2724c01627cddf1b3f9f1ed`.
