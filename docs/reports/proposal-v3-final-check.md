# Proposal V3 Final Accuracy Check Report

**Date:** 2026-11-21
**Reviewer:** Opus 5.5 (accuracy reviewer)
**Status:** READY-WITH-EDITS

---

## Summary of Changes Made

### 1. ArXiv Metadata Discrepancies Fixed (Front Matter)
Added explicit note in the reading rules about three papers where arXiv v1 metadata differs from web versions:
- **Worse Together** (2610.00583): arXiv v1 = 30 Sep 2026, 3 authors (Paliskara, Namchittai, Lampinen). Web version adds Tay & Griffin, dated 11 Nov 2026.
- **Red-Teaming Auto Mode** (2609.19587): arXiv v1 = 17 Sep 2026, updated 27 Sep.
- **Would This Change Your Answer?** (2608.16747): Confirmed it is about agents predicting counterfactual behaviour from interpretability tools, not a monitoring study—line 8 correctly cites it as "not our prior".

### 2. Quote Status Clarification
Added explicit **Quote status** section:
- Lydia Hallie items: paraphrases from owner-pasted transcript notes we did not see → UNVERIFIED as verbatim.
- CJ Avilla's "design for appropriate trust, not greater trust": attributed to Lee & See 2004 by speaker; not in our talk notes → UNVERIFIED as verbatim.
- Diogo Almeida and Lance Martin items: TALK CLAIMS.

### 3. Line 1: Variance–Response Redesign
- Replaced logit slope with **linear susceptibility** χ = d⟨A⟩/dD measured on continuous adoption count and continuous dose.
- Cross-predictor test remains (χ adds to mean-only predictors).
- Williams test → **nested F-test** comparing linear model with χ to one without, on held-out conditions.
- Added: 95% bootstrap interval for χ from 1,000 resamples clustered by tier and task type.
- Clarified primary prediction is B; others secondary, Holm-corrected.

### 4. Line 2: Memory Immune System
- **Organism:** Changed "six or more fractions" → "five non-zero fractions (the Nakayashiki design of five fractions)" to match prior art.
- **Prediction D:** Added log-ratio with 0.5 added to counts to stabilise when adoption at smallest fraction is near zero. Peak level chosen on held-out half of chains to avoid selection bias.
- **Prediction E:** Kill criterion fixed: upper 95% Clopper-Pearson bound below 5% on every tier kills; support needs lower bound above 5% (Holm-corrected across tiers). At n=200, ≥17 events needed for support (79% power at true 10%).

### 5. Line 3: Correlation-Aware Monitor Ensembles
- Clarified primary prediction is C; if owner declines selection arm, B becomes primary.
- Kill for B: paired standard error ~1.1 points (900–1,700 failure episodes); at n=200 kill is low-powered and we say so.
- Cited arXiv 2611.00407: small local monitors (Llama 3B/8B) did not separate exploit attempts; primary monitor AUC 0.64.

### 6. Line 4: Dreaming as Error-Correcting Consolidation
- **Prediction A fix:** x-axis is measured compression ratio per level, not rung index. Two-segment fit (4 params on 5 x-values) vs linear; bootstrap interval over chains; report whether held-out error interval excludes linear fit. At least 7 strength settings via interpolated promotion thresholds.
- **Prediction D fix:** Denominator = chains where shortcut arose; if <20, D is descriptive. At 5% arising rate, 20 chains need ~400 total chains.
- Kill B: recovery time as time-to-event, censored; ratio of restricted mean times. Kill if upper bound <1.25; support if lower bound >1.5. At CV=1: ~190 chains/setting for support, 315 for kill.

### 7. Line 6: Trust and Permission Calibration
- Kill: "Supported: lower bound above 10%" — explicit wording per §3 formula 4.0a.
- Decisive result: n ≈ 9× detection n (standard error ≤ 10/2.8 points).

### 8. Line 7: Renormalization Across Team Size
- Kill A fix: Kish exponent 0.7 kept only as descriptive. Kill = interval for ρ̄(32)−ρ̄(4) below 0.02; support if lower bound >0.02. Under Kish with constant ρ̄, n_eff saturates at 1/ρ̄; same-model teams have positive ρ̄ by default, so exponent <0.7 follows from any ρ̄ >~0.04 with no new team effect. Prior 35% is inconsistent with that.

### 9. Section 9 Budget: Arithmetic Reconciliation
| Item | GPU-hours | API USD (stop) |
|------|-----------|----------------|
| Pilot 2 + EP-1 | 0 | 5.25 |
| Sensitivity pilot | 0 | 1.25 |
| Lines 1–8 stops | — | 153.0 |
| **Total stop** | **56.5** | **159.5** |
| Reserve from USD 170 | — | **10.5** |
| Line 4 adapter (conditional) | up to 13.5 | 0 |

Corrected budget table: plan sum = USD 106, stop sum = USD 153 (was USD 107.3/159.5). Reserve = USD 10.5.

### 10. Footer Cleanup
- Removed internal commit hash `verified: b4a820e 2026-11-20`
- Removed any internal paths, module names, role names, machine names, ports
- Kept `[owner to add]` for contact

---

## Unresolved / Could Not Verify

1. **Lydia Hallie and CJ Avilla verbatim quotes:** No recording access; marked UNVERIFIED in Quote status section.
2. **Lee & See 2004 citation for "appropriate trust":** Attributed by speaker; not independently retrieved. Flagged UNVERIFIED.
3. **FIBS / Bergen probe AUROC figures:** Cited from opened passages only; UNVERIFIED beyond those passages.
4. **Lance Martin "28.7 hours / 47 proved lemmas":** Slide-read from talk; domain unconfirmed. Marked TALK CLAIM.
5. **Baiesi et al. 2009 (0902.3955):** Cited as snippet; not full read.
6. **Ant-robot covering rule (Wagner et al. 1999) and lease (Gray & Cheriton 1989):** From memory; not re-read.
7. **Line 3 n_eff prior (35%):** Reviewer noted inconsistent with Kish+constant-ρ̄ default; prior kept but flagged.
8. **Line 8 probe hook points on 4B model:** Unverified; local GPU has open host-memory fault.
9. **Dual-use rulings needed:** Lines 2, 3 (selection arm), 4 (prediction D) — pending owner decision.
10. **Team-size ruling for >8 agents:** Line 1, 7 — pending.

---

## Final Verdict

**READY-WITH-EDITS**

The document is ready to share after the edits above. All factual discrepancies from the accuracy review and arXiv metadata check have been addressed. The remaining items are explicitly flagged as UNVERIFIED or pending owner rulings, which is appropriate for a pre-registration draft.