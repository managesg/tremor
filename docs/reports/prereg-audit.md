# Pre-registration audit: H1, H7, H8, E8.1 (2026-11-19)

Auditor: Opus 5.5 (verifier role). Repo state: `972dee3` plus an uncommitted working tree,
including the untracked `train/t7_*.py`. Every `code_tree_hash:` line is still blank: the parent
freezes after the T7 smoke. No commits were made, nothing was run beyond read-only checks, and
nothing was installed.

Sources checked:
- `docs/PLAN.md` 1.2, T1, T7, T8 (E8.1, E8.3), 4.3, 6.1-6.3
- `docs/SCIENCE.md` 1.4, 1.5, 4, 5, 6
- `docs/research/08-weight-space-programming.md`
- `docs/reports/G9-repo-review.md`, `G3i-evidence.md`, `E1-E8.1-local-results.md`
- `docs/WORKPLAN.md`
- `train/t7_*.py`, `src/murmuration/{stats,manifest,__main__}.py`
- `data/lm_understand-logs/exp8_math/code/profiles.py`

Owner decisions applied (2026-11-19):
- (a) H8 is exploratory.
- (b) H1 gets a pre-freeze observation and stays unfrozen.
- (c) E8.1 gets the exploratory observation.
- (d) H7 is made executable: arms 0, A-D, the D null, off-target checks, an 8k truncation
  primary, n = 100, matched cost, and the freeze procedure.

## 1. What changed, per file

### prereg/H1.md
- Added a "Pre-freeze observation" block (source: E1-E8.1-local-results):
  - 1,079 events in 1 session, so the precondition of at least 200 events and at least 30
    sessions (PLAN line 77) is not met;
  - the hazard fit is not interpretable, and no value from it is cited;
  - H1 stays unfrozen pending a multi-session corpus.
- Unit of analysis: a session means a main session id, because subagent events carry their
  parent's id.
- Holm needs a p-value, but `stats.paired_bootstrap` returns only (point, lo, hi). The draft
  says "bootstrap p-value" with no code behind it. The rule is now stated (one-sided share of
  resamples at or below 0) and flagged as a code change.
- Numbers checked against PLAN 70-83 and 271-278, all found:
  - 200 events / 30 sessions;
  - tau in {1, 3, 7, 14, 30};
  - 30% / 10%;
  - the 70/30 split by time;
  - the E1.0 example (1 idle day against 15);
  - 9 held-out sessions at n = 30 (arithmetic).
- 10,000 resamples and the 0.05 family level are SCIENCE 5.

### prereg/H7.md (rewritten)

| Draft said | Problem | Now |
|---|---|---|
| Cap 32,768 for every arm | Owner chose the 8k truncation rule. Arm B's published `nothink35` cap is 8,192 (G9 4), so the draft conflicted with its own arm B | Primary `acc8k`: finished, within 8,192 tokens, and graded correct. Generation caps per arm are listed in section 6 |
| n = 500 for A-D | Owner set 100 | 100 seeded problems in every arm (`t7_samples.main_ids`, seed 20261119) |
| No power statement | Required | Normal-approximation table. At n = 100: half-width about ±9-12 points; MDE about 12-18 points; at a true difference of 0, kill 1 fires 12-20% and the outcome is inconclusive about 80%. The authors' 7.9 -> 48.1 is edit against arm 0 (about 40 points, detected with near certainty), not edit against decoding. Discordance of 20-40% is labelled an assumption |
| Kill 1 "within 5 points (paired CI)", no executable form; no third outcome | Ambiguous, and at n = 100 neither rule is likely to fire | Survive / kill (CI upper bound below +5 against B or C) / inconclusive ("not shown"; same architecture consequence as a kill) |
| Arm C "repetition penalty or loop-break", chosen on "20 practice problems in the smoke" | `think35` already has presence penalty 1.5 (D3). `t7_samples.smoke_ids` are MATH-500 problems, which PLAN forbids for choosing C | C = `think35` plus `repetition_penalty` r in {1.05 (repo `lfm25` profile), 1.1, 1.2 (design choices)}, chosen on 20 seeded `math_train.jsonl` practice problems; ties go to the smaller r |
| Arm D underspecified | The loop-token definition is open (D3) and the null is undefined | Column rule and size (64 x 1,024 x 2 = 131,072, matching p50c per G9 2). The null uses a seeded random u with the same rule. The loop definition stays on the must-decide list |
| Edited checkpoint "ID unverified, from README" | G9: the README has no ID; the edit is a bit-exact diff | Arm A is rebuilt from the p50c diff on base `2fc0636...`, with card hashes matched (`t7_rebuild.py`) |
| USD via 240 W x tariff | Owner: n/a for local runs | USD n/a, not 0. Tokens, joules (GPU-only, gross and baseline-subtracted), GPU-hours and idle fraction are reported |
| Off-target sizes "to fix"; IFEval assumed | IFEval needs unapproved packages (G9 6) | MMLU-Pro 200 and IFEval 100 proposed (design choice). Kill 2 rests on MMLU-Pro alone if IFEval is dropped. Its chance of firing by chance (about 30% per comparison) is stated |
| "Arm 0 near 7.9%" | Not quantified | Our 95% interval is about ±5 points (n = 100, 1 sample, against the post's 4 x 500) |
| Second-hand leads (52, 43.95, 54, 51.0, 36/96 vs 10) | Not always labelled | All labelled "second-hand leads, not facts" (08 section 6) |

- Added "Pre-freeze observation" (16a). `runs/t7-smoke/probe100.jsonl` generated arm 0 on
  all 100 main problems at cap 192, before any freeze (checked against `t7_samples.main_ids`:
  100 of 100). None finished and none was correct, so no accuracy signal was observed.

### prereg/H8.md
- Marked **exploratory**, outside every Holm family. Section 11 no longer uses Holm or a
  p-value. The kills are relabelled as exploratory decision rules.
- Status changed from "speculative" to "interpretation", matching PLAN line 190.
- Generator path corrected to `src/murmuration/trapbench/sqlseq.py`.
- The 20k cap traces to PLAN 4.3 C6, "Token cap per episode". Using it for the local arm is a
  design choice.
- Other numbers were checked against PLAN 186-209, 450-473 and 744, and all match:
  - 5 and 10 points;
  - 600 and 200 sessions;
  - 8 GPU-hours and USD 40;
  - the 30% and 85% bounds;
  - 10 and 15 points as the visible effects.

### prereg/E8.1.md
- n corrected from 30 (25 subagent, 5 main) to 42 (37 subagent, 5 main), per the
  pre-freeze run.
- Added the observation:
  - token shares cache_read 93.7%, cache_write 5.3%, output 1.1%, input about 0.002%
    (recomputed from the four token counts; total 75,224,020);
  - these are token shares, not cost shares;
  - no price sheet was recorded, so USD is null and the primary is not computed.
- The exploratory rationale was rewritten. "Exactly at the floor" is no longer true. The new
  reasons are the owner's decision, a main stratum of 5, and the token shares having been seen
  before the freeze.
- Our reads-per-write ratio is labelled a proxy: it counts tool calls, while the talk's 11.4
  counts database reads (SCIENCE 1.5, note 1).
- The 67% is SCIENCE 1.5, note 9.

## 2. Lines other documents must change (not edited here)

Line numbers are as of this audit, in the working tree.

| File:line | Now says | Change to |
|---|---|---|
| PLAN.md:67-68 | "H8 and H9 (added with T8) form a second, separate family of two, Holm-corrected, tested first on a local model." | "H8 is exploratory (owner 2026-11-19). H9 ..." plus the owner's ruling on H9 (see note) |
| PLAN.md:186 | "**H8. A weaker model needs imposed memory structure to benefit from memory (memory).**" | "**H8 (exploratory). ...**", matching the H5 label at line 130 |
| PLAN.md:503 | "Prediction (exploratory, outside both families)" | "outside every Holm family" if H9 is no longer a family of two |
| SCIENCE.md:650-652 | "Five confirmatory hypotheses (H1-H4, H6) ... Everything else is labelled exploratory" | Already consistent with H8 exploratory. It contradicts PLAN 67 for **H9**: add H9's status once the owner rules |
| SCIENCE.md:937-939 | Summary lists H8 beside the confirmatory questions | Add "(exploratory)" after "(H8)" |
| PLAN.md:374-375 | "same per-problem token cap (32,768, the published setting)" | "primary at 8,192 by truncation (finished and correct within 8,192); generation caps per prereg/H7 section 6" |
| PLAN.md:380-384 | Arm 0 "100-problem subset only"; A, B, C, D "Full MATH-500" | All arms: the same 100 seeded problems (`t7_samples`, seed 20261119). Add the row "D-null: random direction, same rule" |
| PLAN.md:383 | C "repetition penalty or loop-break decoding (one setting, chosen on practice problems ...)" | "`think35` (presence 1.5) plus `repetition_penalty` r, chosen on 20 seeded `math_train` practice problems" |
| PLAN.md:386 | "Off-target: an IFEval and an MMLU-Pro subset for arms A, B, C." | "... for arms A, B, C, D and D-null; IFEval only if its checker packages are approved" |
| PLAN.md:394-397 | "...small (about 5 points) for edit-vs-decoding, which is why A-D use all 500 problems and arm 0 does not." | "n = 100 for every arm (owner 2026-11-19); at n = 100 the edit-vs-decoding contrast resolves only about ±10 points (power table in prereg/H7 section 10)" |
| PLAN.md:913 (G9 row) | "run the five arms" | "run arms 0, A-D and D-null" |
| WORKPLAN.md:84 | "20 practice problems, arms 0 and B: tokens/s, watts, peak memory; choose arm C's setting here." | "Timing on `smoke_ids` (MATH-500, timing only); arm C's r chosen on 20 seeded `math_train.jsonl` practice problems" |
| WORKPLAN.md:87 | "Freeze H7; run arm 0 (100 seeded problems), A-D, D's random null, off-target for A-C" | "... arms 0, A-D and D-null on the same 100 seeded problems; off-target for A-D and D-null" |

Note on H9: with H8 removed, the "family of two" becomes H9 alone. Holm over one test is no
correction. The owner must say whether H9 stays confirmatory, tested uncorrected at 0.05, or
becomes exploratory like H8. No prereg/H9.md exists yet.

H1 and E8.1 lines:

| File:line | Now says | Change to |
|---|---|---|
| PLAN.md:77 | "Kill: fewer than 200 real permission events or fewer than 30 sessions; ..." | "Precondition, not a kill: below 200 events or 30 sessions in the corpus named at the freeze, H1 is untestable on that corpus and stays pending (owner 2026-11-19)" |
| WORKPLAN.md:65 | "Fewer than 200 events or 30 sessions: report the H1 precondition kill and stop." | "... report the precondition not met (H1 untestable on this corpus, pending a multi-session corpus) and stop." |
| PLAN.md:442-444 | E8.1 "Prediction ... Refuted if the median is 67% or more." | Add "(exploratory, owner 2026-11-19)" |

H7 design choices made by the auditor, not in PLAN:
- the operational form of kill 1 (the CI upper bound below +5);
- the inconclusive outcome, with the same architecture consequence as a kill;
- the arm C grid and tie rule;
- arm D's column rule and null;
- the off-target sizes.

The owner may overrule any of these before the freeze. Kill 2's chance of firing by chance
across its four comparisons is about 50-75% at the proposed sizes (prereg/H7 section 12).

## 3. Code gaps the parent must close before freezing H7 (not edited: outside scope)

1. `train/t7_arms.py` `accuracy_at_cap` counts `correct and tokens <= cap`. A generation cut
   at exactly the cap with a mid-thought `\boxed{}` scores correct. Add `r["finished"]`, and add
   a test fixture for a cut generation.
2. `t7_gen.py` covers arms 0 and B only. Arms A, C, D, D-null and the off-target graders
   still need code, and so does the repetition-penalty processor.
3. `t7_samples.smoke_ids` are MATH-500. They may be used for timing only. Arm C's selection set
   must be practice problems.
4. `stats.paired_bootstrap` returns no p-value. This matters for H1's Holm entry, not for
   H7 or H8.

## 4. Must decide before the H7 freeze (also in prereg/H7.md section 18)

1. Arm C's r: run the {1.05, 1.1, 1.2} grid on the practice set and write the winner in.
2. Arm D: the loop and non-loop token definition (D3), the direction data, and the D-null seed.
3. Generation cap for A, C, D and D-null (32,768 or 8,192), from the smoke projection against
   12 GPU-hours. If it does not fit even at 8,192, ask the owner; n is never shrunk.
4. Off-target: MMLU-Pro size and seed; IFEval approved or dropped.
5. The probe100 exposure: accept and record it, or redraw `MAIN_SEED`.
6. Owner confirmations: the MATH-500 licence reading (the HF card has none; upstream is MIT)
   and G3 (i).
7. Commit approval. The procedure is:
   1. commit, with `git status --porcelain src train prereg` empty;
   2. compute the hash with `python3 -m murmuration manifest --tree src train --root .`;
   3. write it on the hash line;
   4. run `python3 -m murmuration prereg-check prereg/H7.md --tree src train --root .`;
   5. record it in `docs/reports/prereg-freezes.md`;
   6. commit.

## 5. Not checked

- The power figures are normal approximations under an assumed 20-40% discordance. They were
  not simulated, and they are not measured.
- The second-hand leads in file 08 were not opened.
- The licence texts were not re-read beyond G3i.

verified: 972dee3 (plus working tree) 2026-11-19
