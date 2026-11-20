# R1 Bench Gate Verdict: ACCEPT

## Verification Summary

**All five verification criteria satisfied:**

1. **Formulas correct and correctly sourced** — Hand-derived on small examples:
   - Overdispersion (var/(n·p·(1-p))): matches code; p∈{0,1}→1.0 shortcut correct
   - Dose-response slope: OLS + percentile bootstrap CI; planted test recovers ~0.3
   - Reproduction number R: (adopters−roots)/adopters; simple 2-node case gives 0.5
   - Pairwise-miss phi correlation + Kish n_eff = m/(1+(m−1)ρ): independent→m, identical→1, planted ρ≈0.36→n_eff≈1.73
   - Recovery time: first t≥shock with |x−baseline|≤tol for `hold` consecutive steps; null→0, basic→3, hold=2→3, never→None

2. **Scripted controls prove claims** — All 15 tests pass:
   - Null value on no-signal logs ✓
   - Planted ground truth recovered within tolerance ✓
   - Night loop with perfect verifier never increases false-note share ✓
   - s=0 leaves store unchanged ✓
   - Placebo changes nothing, charges tokens ✓
   - Old store kept on gated bad write ✓
   - Provenance links correct (new note parents = [old id]) ✓
   - Deterministic under seed ✓

3. **Tests not weakened; catch stubbed bodies** — Mutant analysis:
   - Stubbed overdispersion (returns 0) fails: het expects ~5.0
   - Stubbed n_eff fails: expects 4 and 1
   - Stubbed dose_slope fails: planted expects 0.3
   - Stubbed reproduction_number fails: planted expects 0.7
   - Stubbed recovery_time fails: planted expects 3
   - Stubbed pairwise_miss fails: expects ρ=0/0.36, n_eff=4/1.73

4. **No invented results** — Synthetic data only in tests; report limits stated honestly (confidence intervals, no p-values, no financing predictions)

5. **stdlib only, no other-module edits** — Imports: `random`, `statistics`, `math`, `itertools`, `copy`; no external deps; no changes to existing modules

## Test Results
- `tests/test_night.py`: 8 tests, 0.007s, **OK**
- `tests/test_readouts.py`: 7 tests, 0.233s, **OK**
- Full suite (764 tests): 291s, **OK (skipped=1)**

## Risk Notes
- Kish formula assumes exchangeable monitors; report notes this
- Recovery time uses absolute tolerance; relative mode not implemented
- No network/GPU/API dependencies — fully offline