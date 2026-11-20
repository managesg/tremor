# Bench extensions R1 (night loop and readouts)

Scope: row 13, items "night loop" and "readouts" of Phase R1. Stdlib only, CPU, USD 0, synthetic data only.
No result in this note comes from a model run. Files: `src/murmuration/night.py`, `src/murmuration/readouts.py`,
`tests/test_night.py`, `tests/test_readouts.py`. It reuses no existing module; `consolidate.py` (dream arms A-E)
is a different, bytes-budgeted object and was left alone.

## night.py
- `add_note`: day-episode write. Note = id, text, author, episode, sources (evidence ids), parents (note ids).
- `consolidate(store, s, night, verifier, mode, rewrite, seed)`: each note is chosen with probability s;
  a chosen note is rewritten (callback, default identity) into `n<night>-<id>` with `parents=[old id]`.
  Returns a NEW store; input untouched, so the old store is the undo. Mode `direct`: rewrite replaces the
  original; with a verifier, a failing original is dropped and a failing rewrite is blocked (original kept).
  Mode `gated`: rewrite is written only if the verifier passes it; originals are never dropped.
- `placebo`: reads the same tokens, changes no content. `false_share`, `lineage` (provenance walk), `tokens`
  (whitespace words; shortcut, not a tokenizer). Deterministic via `random.Random(seed)`.
- `false` on a note is scripted ground truth for benches; passes may only use the verifier callback.

## readouts.py (formulas are standard statistics, not our results)
- Overdispersion: k task sets x n reruns, pooled p, `var_ddof1(counts) / (n p (1-p))`; 1 under independent
  Bernoulli reruns (binomial), above 1 when task sets differ (McCullagh and Nelder, GLMs, ch. 4). This is the
  mechanical-link control for line 1: reruns of one task set should not look more dispersed than a binomial.
- `rerun_variance`: mean within-set sample variance of reruns.
- `dose_slope`: OLS slope with percentile pair-bootstrap interval (Efron and Tibshirani 1993).
- `reproduction_number`: adopters are planted notes plus all provenance descendants; R_hat =
  (adopters - roots) / adopters = pooled mean offspring, which equals R in expectation for a subcritical
  Galton-Watson forest (Harris 1963).
- `pairwise_miss`: joint-miss matrix, pairwise phi correlation (pairs with a constant monitor skipped), mean
  rho_bar and its min/max spread, and Kish `n_eff = n / (1 + (n-1) rho_bar)` (Kish, Survey Sampling, 1965),
  the design-effect form used in PROPOSAL section 3.
- `recovery_time`: steps after the shock until the series is within tol of baseline for `hold` points.

## What each scripted control proves
- overdispersion: iid coins give 1 (+-0.1); a planted half-always/half-never split gives exactly n.
- dose_slope: zero-slope noise gives an interval containing 0; planted 0.3 recovered within 0.08, interval
  excludes 0 and covers 0.3; no dose spread raises.
- R: no adoption gives (0, 1); planted Poisson(0.7) forest of 3000 trees recovers 0.70 within 0.03.
- n_eff: independent monitors give rho near 0 and n_eff near n; identical monitors give 1; a shared-cause
  mixture with hand-derived rho = 0.36 is recovered within 0.03.
- recovery: no shock effect gives 0; a hand-built curve gives 3; never recovers gives None; hold works.
- night: s=0 leaves the store equal; s=1 links every note to its source; fraction chosen tracks s and is
  seed-deterministic; an imperfect rewriter DOES grow the false share (control that the harm exists); with a
  perfect verifier the false share never grows over 5 nights in both modes; gated blocks bad writes and keeps
  originals; placebo equals the store, copies it, and charges the same tokens as a real pass.

Stub check, done by script on scratch copies: each public function replaced by `return None`; every function
is caught by at least one test after adding an absolute token assertion (`tokens` first survived because two
`None` values compared equal).

## Limits
- Synthetic scripts show the code recovers planted truth; they say nothing about language models.
- Bootstrap null interval is a 95% interval: a null test seed can fail by chance about 5% of the time; seeds
  are fixed.
- Kish assumes exchangeable monitors; it describes variance of an average, not ensemble catch rate.
- R_hat is only unbiased in aggregate over many forests; one small tree is noisy. Tokens are words.
- Not built here: episode design v2, scripted nulls per line, line techniques (`sgv` ... `blocks`), carriers,
  the response-to-fluctuation ratio, cascade depth. Readouts are in `readouts.py`, not `susceptibility.py`.
