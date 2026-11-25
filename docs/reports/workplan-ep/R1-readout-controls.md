# Scripted L1, L3, and L7 readout controls

These fixtures exercise the existing readout functions with known values. The outcome rows are synthetic. No local model, GPU workload, network call, or live research batch ran.

| Line | Scripted null and positive control | Hand-checkable expected result |
| --- | --- | --- |
| L1 · Variance and dose | Cross task-set counts `0,1,1,1,2` or `0,0,1,2,2` with a flat or increasing response at doses 0, 1, 2, 3. All count and response families have pooled mean 0.5. | Count sample variance is 0.5 or 1, with binomial reference `2 × 0.5 × 0.5 = 0.5`. Overdispersion is 1 or 2. Within-set sample variance averages 0.3 or 0.1, respectively. The flat response has linear slope 0, and `1/8,3/8,5/8,7/8` has slope 1/4. All nonconstant-dose bootstrap samples stay on their exact lines. |
| L3 · Joint misses | With four labeled failures, monitor pair `1100 / 1010` is pairwise independent, while `1100 / 1100` copies an error pattern. Each individual monitor misses 2/4 in both cases. | Joint misses go from 1/4 to 1/2. Phi goes from 0 to 1 and the two-monitor Kish diagnostic from 2 to 1. |
| L7 · Team-size correlation | Enumerate all 64 six-bit inputs. Each source computes parity on one nonzero bit mask. Compare distinct sources at both sizes with four sources shared among a team of 32. Every source errs on 32/64 task sets. Two distinct masks give each pair of parity values exactly 16 times. | Distinct sources give mean pairwise correlation 0 at both sizes. With four repeated sources at size 32, 112 of 496 unordered pairs have correlation 1 and the rest have 0. The 32-minus-4 contrast is 7/31 and the Kish diagnostic stays at 4 despite growth from 4 to 32 members. |

The original L1 dose check exercises a probability-scale linear slope. The proposal's later redesign specifies a continuous adoption-count slope and a nested comparison, with final variables and cluster-resampling rules still to be frozen. The original four-failure L3 matrix checks joint misses. The extension below tests the false-positive threshold separately. The L7 shared-source cells deliberately violate exchangeability, so the Kish value is reported as a diagnostic alongside correlation range [0, 1]. The fixtures do not test whether allocating checks or changing team layout improves model behavior.

## Reproduce from Murmuration

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m lab.r1_readout_controls
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest -v lab.tests.test_r1_readout_controls
```

The three tests passed. The saved `runs/r1-readouts-scripted/trace.json` has SHA-256 `a4e20e1c7a36438d07ca986435267fc8e09253e0fc43e4eb5b8479af522934c5`.

[Fixture runner](../../../lab/r1_readout_controls.py) · [Focused tests](../../../lab/tests/test_r1_readout_controls.py) · [Portfolio contrasts and freeze inputs](R2-R4-protocol-readiness.md)

## L1 budgeted verification allocation control

`lab/l1_verification_allocation.py` commits an allocation before the
grader receives the completion truth. The positive and null oracle
variants reuse the same plan digests. The two measured rankers each
charge forty calibration reruns and four checks under a 56-unit
incremental budget. Uniform checking buys fourteen checks without
calibration. Majority voting reserves 56 retry attempts across 28
claims. The original proposal is common to all fixture arms.

The calibration fixture gives both strata pooled mean 0.5.
The overdispersed counts select the variable stratum. Within-unit
disagreement selects the other stratum, so the two rankers demonstrably
place checks differently. The grading receipt distinguishes undetected
false completion, negative return on legitimate work, missing checker
receipt, and unresolved retry voting.

| Fixture | Overdispersion | Uniform | Disagreement | Majority retry |
| --- | ---: | ---: | ---: | ---: |
| Planted false, undetected | 1 | 1 | 4 | 0 |
| Null, undetected | 0 | 0 | 0 | 0 |

The retry arm had one unresolved vote in both cases. Its zero observed
undetected cases do not make that unresolved outcome a verified
completion. Relative reduction against uniform was zero for the
positive fixture and undefined for the null baseline.

Report `runs/l1-verification-allocation.ylm7v1/report.json`, SHA-256
`030861581f1d7ef5dd690ce9b0c210a252701b5ef9e46adbf91434bc37b1c108`.
The report reproduced byte for byte and the original readout trace
kept its digest. This verifies ranking and accounting on public fixtures.
The extension below adds proportional allocation and several comparators.
Independent held-out calibration, uncertainty and native execution remain open.

### Additional L1 allocation baselines

The extended public runner adds five baselines to the instrument. Random
uses seed 17. Length and team size rank by the respective observed feature.
The pilot predictor fits a two-feature linear model on eight separate
synthetic observations. The proportional arm divides checks across strata
using measured scores and available claims. The predictor and proportional
arm each charge 40 measurement units before applying four checks. The
other three buy 14 checks. All five consume the same 56-unit allocation.

| Fixture result | Random | Length | Team size | Pilot predictor | Proportional |
| --- | ---: | ---: | ---: | ---: | ---: |
| Positive, undetected false completions | 3 | 3 | 2 | 4 | 1 |
| Null, undetected false completions | 0 | 0 | 0 | 0 | 0 |
| Missing checker result in each scenario | 0 | 1 | 0 | 0 | 1 |

All five plans keep identical digests across the positive and null grading
variants. These outcomes verify implementation behavior on the public
fixture. Independent held-out calibration, uncertainty and native
execution remain open. The original four-arm report still replays byte
for byte.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m lab.l1_allocation_baselines
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:lab:tests python3 -m unittest -v lab.tests.test_l1_allocation_baselines lab.tests.test_l1_verification_allocation
```

Retained report `runs/l1-baselines-pilot4-preflight.qvMLCj/l1.json`, SHA-256
`68e0b12bed0eb9c90dda197e5fb62986eaa903adf890a0faefdaabf26a0317c6`.

## L3 matched two-view monitor control

This fixture uses four disjoint labeled inventories. The first has four
failure cases for selecting views, the second has 20 clean cases for
fitting each cutoff, and the assessment has 20 separate clean cases and
four separate failures. Both policies pay 12 for the shared selection
inventory, 40 for cutoff fitting, 40 for clean assessment and 8 for
failure assessment. All charges are scripted monitor calls.

| Fixture | Top two by individual catch | Joint-miss pair | Paired failure outcomes |
| --- | --- | --- | --- |
| Complementary views | A and B catch 2/4 | A and C catch 3/4 | 2 both, 1 selected only, 0 top only, 1 neither |
| Copied-view null | A and B catch 2/4 | A and B catch 2/4 | 2 both, 0 selected only, 0 top only, 2 neither |

Each fitted cutoff flagged 1/20 held-out clean rows. A separate
label-swap test kept the plans and cutoffs pinned. It raised the selected
arm's held-out false-positive rate to 2/20 and the runner withheld the
matched-rate contrast. Cases with shared IDs or missing or nonbinary view
flags fail explicitly. The very small counting fixtures are used to
verify arithmetic and data separation. The scientific primary remains
to be selected and the real assessment pools remain to be frozen.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m lab.l3_equal_budget_monitors
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:lab:tests python3 -m unittest -v lab.tests.test_l3_equal_budget_monitors lab.tests.test_r1_readout_controls
```

Retained report `runs/l3-equal-budget.zPRtkw/report.json`, SHA-256
`aae899c22cc3c04b4432e73ccecd8dae324af542239efc21ef4c5d8e854396bd`.
The plan and assessment each pin complete split rows. Reordering input
rows preserves the canonical pins. Reassigning values to case IDs
changes the pins even if aggregate counts stay the same.

## L1 count-scale model rehearsal

The later L1 redesign specifies a count-scale susceptibility and a
nested regression. The opening of the proposal still describes a
binary logit slope. Before the scientific freeze, the protocol needs
one estimand, the exact outcome and predictor roles, dose and count
units, the nuisance variables, and the tier/task grouping for clustered
resampling. The verification-allocation endpoint remains primary.

The development check uses orthogonal synthetic factors and a generic
response. The added predictor comes from each row's count-versus-dose
slope. The reduced columns are an intercept and three independent
nuisance factors. Expected residual sums of squares are 40 and 8 for a
planted additional effect, and 8 and 8 under the null. The corresponding
partial R² and F statistics are 4/5 and 12, and 0 and 0. If the added
column is already in the reduced span, the comparison is undefined.
These are exact arithmetic expectations. The fixture does not choose
the real outcome or a scientific decision rule.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m lab.l1_nested_model_control
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:lab:tests python3 -m unittest -v lab.tests.test_l1_nested_model_control
```

Retained report `runs/l1-nested-model.syI2Zm/report.json`, SHA-256
`7655e7536f66c5320fe734fca453d8553bf4c826438c8a2736e234820b3fc111`.
The exact fixture reproduced the positive and null results above.
Rank deficiency, a saturated fit and a zero residual each return an
explicit reason when the F statistic is unavailable.
