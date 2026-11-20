# Wave 1 re-verification

2026-11-19, Opus 5.5 (independent adversarial verifier). Base: local commit `74b0494` plus uncommitted work.
Every claim is bound to a frozen snapshot of `src tests train` with combined sha256 `470f1ec4996403a3...`.
The live tree had the same hash before and after the 20x loop. The W1-13 CLI builder was still writing
`__main__.py`, `README.md` and `tests/test_cli.py` when the snapshot was taken (19:12:53-19:12:56).
No repo file was edited except this one. Probes, mutants and old-behaviour reconstructions ran on copies in the
session scratchpad.

## Verdict: NOT ACCEPTED, but close

- The 5 prior top defects are **fixed**. Each new regression test **fails** against the old behaviour and
  **passes** now.
- Prior fix items 6-10 (ledger, coupling, memlint, hazard, stats test gaps, low items) are **not fixed**.
  Their files predate the prior report (mtimes 19:01-19:02, report 19:10), and the re-probes reproduce every
  finding. These are open items, not regressions.
- 2 modules FAIL, each on one item:
  - `manifest.py`: this round's fix introduced a regression. `tree_hash` collapses its roots, so on the real
    `src/`+`train/` layout a code move between roots leaves the freeze hash unchanged.
  - `runner.py`: the emitted token record does not say its counts are `len//4` estimates.
- Both are one-line fixes.

## 1. Prior top 5: old behaviour reconstructed, new tests shown to fail on it

`manifest`, `tokens`, `power`, `t7_edit` and `t7_arms` are not in `74b0494`, so `git show HEAD:` cannot supply
their old code. Old behaviour was restored in a temp copy by a one-defect patch that keeps the new interface, so a
failure is an assertion, not a `TypeError` on a changed signature. Harness: `scratchpad/mut.py`. It copies the
snapshot without `__pycache__`, asserts that the patch text matches exactly once, and runs
`python3 -B -m unittest discover -s tests -p <test>`.

| Prior defect | Old behaviour restored | Result on old | Failing test and assertion | Now |
|---|---|---|---|---|
| 1 power: idle from power ≤ job min ×1.1 | `if a[1] <= min(...)*1.1: idle += dtt` | KILLED | `test_idle_is_utilization_not_power`: `1.0 != 0.0`; `test_energy`: `0.333 != 0.0` | probe: constant 100 W, util 90 gives `idle_fraction 0.0` |
| 1 power: noheader format crashed | `if True:` (header required) | KILLED | `test_plan_sampler_format` ERROR; standalone the old path raises `StopIteration` | `parse_csv` of the §6 noheader text gives `[(…, 4.8, 4), (…, 5.0, 0)]` |
| 1 power: no net joules | `joules_gpu_net: None` | KILLED | `test_energy`, `test_baseline_watts` | net = gross − baseline_w × s; tested 1040 → 1000 J |
| 1 power: zero seconds gave 0.0 | `idle/secs if secs else 0.0` | KILLED | `0.0 is not None` | None |
| 2 t7_edit: tautological base check | `if False:` (ignore expected sha) | KILLED | `test_edit`: `ValueError not raised` | raises before editing on a mismatch |
| 2 t7_edit: ragged base gave bare IndexError | drop ragged check | KILLED | `IndexError: list assignment index out of range` | `ValueError("ragged base matrix")` |
| 3 manifest: path-dependent hash | `yield f, f` (hash path as given) | KILLED | `test_hash_location_and_spelling_independent`, `test_check_prereg_passes_elsewhere_fails_on_edit` | same tree at 2 locations and via `sub/..` and a relative path: equal |
| 3 manifest: rename untested (prior survivor) | `h.update(d)` (drop filename) | KILLED | `test_rename_and_one_byte_edit_change_hash` | — |
| 4 t7_arms: resume keyed on id only | `done = {(id, arm, cap, seed) …}` from caller | KILLED | `Lists differ: [] != [1, 2]` | arm B after arm 0 makes 2 calls |
| 4 t7_arms: seed ignored | key ignores the record's seed | KILLED | `[1, 2, 1] != [1, 2, 1, 1]` | — |
| 5 tokens: missing usage → 0 | `_num` returns 0 | KILLED | `test_missing_usage_is_none_not_zero` | missing is None and counted in `missing` |
| 5 tokens: tool_use per record | `if True:` (no dedupe) | KILLED | `(4, 1, 4.0) != (2, 1, 2.0)`, `3 != 1` | the fixture now enshrines `reads == 2` |

The only module with an old version in git is `ledger.py`. With `HEAD:src/murmuration/ledger.py`, the current
test file gives `Ran 12 … FAILED (errors=3)`, all on the new holdout tests. With `HEAD:tests/test_ledger.py`
against the current ledger it gives `Ran 9 … OK`. The original 9 tests are intact (the diff to them is +37/−0).

## 2. Flakiness: 20 runs each, snapshot and live tree

`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -B -W ignore -m unittest discover -s tests`

| Tree | Result | Tree hash before/after |
|---|---|---|
| snapshot | 20/20 `Ran 65 tests … OK` (2.20-2.65 s) | `470f1ec4996403a3` / same |
| live repo | 20/20 `Ran 65 tests … OK` (2.26-2.82 s) | `470f1ec4996403a3` / same |

No flakiness. Note that `python3 -I` ignores `PYTHONPATH`; the suite still works only because every test inserts
its own `sys.path`.

## 3. Per-module verdicts

| Module | Verdict | Evidence and open findings |
|---|---|---|
| power (W1-09) | **PASS-WITH-NOTES** (was FAIL) | All 5 prior sub-defects fixed (table above). (a) `idle_fraction` is time-weighted ("GPU-seconds"). WORKPLAN §6 counts samples. The two agree at a regular 1 s cadence but not with gaps: the probe `[(0,…,0),(10,…,50),(11,…,50)]` gives `0.909`, against 1/3 by sample count. Either state the deviation in §6 or count samples. (b) Mutant `u == 0`→`u < 5` SURVIVED: no test has a low non-zero utilization. (c) Mutant `baseline_watts` = record minimum SURVIVED: the test baseline is constant. (d) `_ts` is defined twice (dead duplicate). |
| t7_edit (W1-09) | **PASS-WITH-NOTES** (was FAIL) | The sha check is real and tested. (a) `checksum` ignores shape: `[[1,2,3,4]]` and `[[1,2],[3,4]]` hash equal (`True`), so a reshaped base passes. (b) An empty base raises a bare `IndexError`. (c) No caller passes the manifest sha yet (grep: only `t7_edit.py`); Wave 2 must wire `expected_base_sha256` from the download manifest. |
| t7_arms (W1-09) | **PASS** | Resume key `(id, arm, cap, seed)`; both mutants KILLED. A `shortcut:` comment covers old records. |
| tokens (W1-05) | **PASS-WITH-NOTES** | Both fixes proven. Real data (§5): no leak. 935 tool_use blocks have 935 unique ids, so real transcripts never repeat a tool_use; the old double count was fixture-only. (a) Mutant key `(message id, index)` SURVIVED. The test comment says "different message ids" but reuses `r1`, so `id`-based keying is not actually tested. (b) The `cache_hit` denominator uses `tot[k] or 0`, so a missing class silently shrinks it (it should be None when any denominator class is None). |
| manifest (W1-01) | **FAIL** (regression from this round's fix) | Path independence is fixed and tested. **New defect:** `_files` drops the root name and `tree_hash` stores items in a `set`. Synthetic probe with roots `src`, `train`: deleting `train/x.py` while an identical `src/x.py` exists does not change the hash (`changed: False`); moving `src/a.py` to `train/a.py` does not change it (`False`); `[A]` equals `[A, A]` (`True`). **On the real snapshot layout:** moving `train/t7_edit.py` to `src/t7_edit.py` leaves `tree_hash([src, train])` unchanged (`False`). With a copy in both roots, deleting the `src` copy also leaves it unchanged (`False`). So the WORKPLAN §5 freeze over `src/`+`train/` misses a code move. The old path-as-given hash did catch it. Fix: prefix each relpath with the root's basename (or root index) and hash a list. Bare files hash by basename (declared shortcut; `p/q.py` == `r/q.py`). `versions` still records only Python and platform, and this is not stated as a limit. |
| runner (W1-10) | **FAIL** (one criterion) | Good: `local_hf` with torch absent raises `RuntimeError: local_hf backend needs torch and transformers, not installed here: No module named 'torch'`, which is clean and tested. `claude` is a stub raising `NotImplementedError("claude backend is not approved yet")`. No network imports (grep for `urllib`, `socket`, `http`, `requests` and `anthropic` is empty). Cache classes are `None`. The JSONL write is temp + `os.replace`, which is atomic. **Defect:** the emitted record is `tokens: {'input': 144, 'output': 65, 'cache_read': None, 'cache_write': None}` with no estimate label (probe: `any estimate label in record: False`); only the `_scripted` docstring says `len//4`. A reader of `runs/` cannot tell estimates from model counts. Notes: (a) no `fsync` before `os.replace`, and a crash leaves a stale `.tmp`. (b) One record per `task__arm__seed__backend.jsonl`; a rerun silently overwrites it (probe: 1 file, 1 line after 2 runs). (c) The record's manifest has no `tree_hash`, and `git_sha` reads cwd (`root="."`), not the repo. (d) `test_jsonl_out` leaks a `mkdtemp` dir. |
| stats (W1-02) | PASS-WITH-NOTES (unchanged) | Required mutants: Holm→Bonferroni KILLED (`[T,T,F] != [T,T,T]`), Holm `break`→`continue` KILLED, row resampling KILLED. Still SURVIVED: Holm `>`→`>=`, unseeded RNG. Still: mixed cluster keys raise `TypeError`; empty rows return `(0, 0, 0)`. |
| ledger (W1-03) | PASS-WITH-NOTES (unchanged) | Required mutant "tau chosen on TEST" KILLED (`test_tau_chosen_on_train_only_poisoned_test_half`: `None != 1`). Not fixed: `_tau_row([])` still gives `exposure_saving 0.0, extra_prompts 0.0` (null as 0), and there are no numerators or denominators. The interleaved-session time split and the tie-break comment (line 159 still says "break by name") are unchanged. |
| hazard (W1-04) | PASS-WITH-NOTES (unchanged) | Degenerate inputs still give `llr 0.0, p 1.0`. `gaps` still has no denied-event filter. The one-sided-p mutant still SURVIVES. |
| memlint (W1-06) | PASS-WITH-NOTES (unchanged) | NUL in `source` still raises `ValueError`. A non-UTF-8 `.jsonl` still raises `UnicodeDecodeError` in `lint_dir`. `ghp_…`, `xoxb-…`, `aws_secret_access_key=…` and `token=…` all still lint clean (`[]`). The sibling-prefix mutant still SURVIVES. |
| coupling (W1-11) | PASS-WITH-NOTES (unchanged) | An empty repo still raises `CalledProcessError`. Not re-probed: quotePath, merges. The code is unchanged. |
| sqlseq (W1-08) | PASS-WITH-NOTES (unchanged) | The vocab-check mutant still SURVIVES. `test_sqlseq` still leaks `mkdtemp` dirs (lines 12, 32). |
| traps (W1-07) | PASS (unchanged) | `test_traps` line 28 still leaks a `mkdtemp`. `trap.json` still sits beside `repo/`, and the runner must not expose it. |
| prereg H1, H7, H8, E8.1 (W1-12) | **PASS-WITH-NOTES** | Each file has exactly one `code_tree_hash:` line, blank. All four say `Status: DRAFT. Not frozen.`; the only other "frozen" is the template's `Code git SHA (frozen):` label, left blank. All 17 sections are present. A scripted numeral check against PLAN, with small integers included and only section, task and gate references and list numbering filtered, found every number in PLAN except `10,000`, which is labelled "SCIENCE 5" in all four. (H7's `32,768` showed up as a regex split artefact; it is in PLAN.) H8 was hand-checked against PLAN lines 186-201 and 450-463 plus the C6 row (744): 5 and 10 points, 30%/85%, 8 GPU-h, USD 40, 200 sessions (5 sequences × 40) and 20k tokens all match. **H8 conflict:** PLAN line 67 makes H8/H9 a separate Holm family of two, while SCIENCE §5 (lines 650-652) says everything outside H1-H4 and H6 "is labelled exploratory in the output itself". H8 §11 states the conflict and leaves it open (correct), but still writes "Holm-corrected … 0.05 (design choice)". Notes: (a) H8 §8's heading lacks the template's "(exploratory)" label, and its secondaries drive kills 2 and 3, which are three uncorrected interval decisions beside one Holm-corrected primary. (b) A numeral being present in PLAN is not the same as being in the right context; only H8 was checked in context. |

## 4. Mutation summary (this pass)

24 mutants:
- **KILLED (17):** P1-P4, E1, E2, A1, A2, T1, T2, M1, M2, L1 (tau on test), S1 (Bonferroni), S2 (not step-down),
  S4 (row resampling).
- **SURVIVED (7):**
  - New code: P5 (baseline = minimum), P6 (`u<5`), T3 (tool key ignores `id`).
  - Prior survivors, still open: S3 (Holm `>=`), S5 (unseeded RNG), H1 (one-sided p), ML1 (startswith without
    sep), Q1 (sqlseq vocab check).

The 3 required mutations (tau train-only, Holm, cluster resampling) are all KILLED, so those tests are not
tautological.

## 5. Real-data check: `~/.claude/projects`, counts only

Script `scratchpad/realdata.py` used an in-process random salt, never printed. It walked every string leaf of
every output in process and printed only aggregates.

- `tokens.probe`: 37 files, 1388 assistant messages, 1388 with usage, 12 usage keys. 22 string leaves: 0 with a
  space, 0 with `/`, max length 40, 0 not key-shaped.
- `tokens.ledger`: 37 sessions (32 subagent). 666 string leaves: 0 with a space, 0 with `/`, max length 22.
  Salt in output: False. Raw sessionIds in output: 0 of 5. Missing usage fields: 0 in every class.
- `ledger.parse` → 934 events. `ledger.cli_report` has 76 leaves and `ledger.report` 52: 0 with a space, 0 with
  `/`, max length 21. Raw sessionIds in output: 0. Salt: False. Home path: False.

No content leak was found.

## 6. Ranked fix list

0. **manifest.tree_hash (FAIL):** see item 2. It blocks any freeze.
1. **runner (FAIL):** put the estimate label in the emitted record. Example: `tokens_source: "len//4 estimate"`, or
   per-class `{"value": n, "estimate": true}`. Assert it in `test_runner`. Add `fsync` before `os.replace`, record
   `tree_hash`, and pass the repo root to `manifest.build`.
2. **manifest.tree_hash:** key items by `(root basename or index, relpath)` and hash a list, not a set. Add tests
   for a delete with a cross-root duplicate and a move between roots. Do this before the first freeze.
3. **Prior items 6-8 still open:** ledger null-as-0 and units; coupling `-z`/quotePath and the empty repo;
   memlint NUL, non-UTF-8 and the secret patterns.
4. **t7_edit:** include the row and column counts in `checksum`; reject an empty base with `ValueError`.
5. **tokens:** set `cache_hit` to None when any denominator class is None; make `test_repeated_tool_use_id`
   really use different message ids.
6. **power:** count samples for `idle_fraction` per §6 (or record the time-weighted deviation in WORKPLAN §6);
   add a low-nonzero-utilization test and a varying-baseline test; delete the duplicate `_ts`.
7. **Prior item 9, still-surviving mutants:** S3, S5, H1, ML1, Q1.
8. **H8 prereg:** have Fable (D1) or the owner decide confirmatory against exploratory before the freeze. Label
   the secondaries, or put kills 2 and 3 under the correction.
9. **Low:** `mkdtemp` leaks in `test_runner`, `test_sqlseq` and `test_traps`; the missing `shortcut:` comment
   on power's time-weighting.

## 7. Not checked

- The W1-13 CLI (`__main__.py`, `test_cli.py`, README), still being written.
- The coupling quotePath and merge behaviour (unchanged code, not re-probed).
- Real `nvidia-smi` output (no process run).
- Prereg numbers in context for H1, H7 and E8.1 (presence-in-PLAN check only).
- `docs/PRINCIPLES.md` was modified at 19:18:08 during this review, by another session, not by this verifier.
  It was not reviewed.
