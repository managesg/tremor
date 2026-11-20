# Wave 1 adversarial verification

2026-11-19, Opus 5.5 (independent verifier). Base: local commit `74b0494` plus uncommitted Wave 1 work.
Scope: W1-01, -02, -03, -04, -05, -06, -07, -08, -09, -11. Out of scope and not reviewed: `runner.py`
(W1-10) and `prereg/*.md` (W1-12), which appeared during the review. No repo file was edited except this one.
Probes and mutants ran on copies under the session scratchpad.

## Verdict: NOT ACCEPTED

- 2 modules FAIL: `train/power.py` and `train/t7_edit.py`.
- `manifest.py` passes its own row but carries the highest-impact footgun (path-dependent hash).
- All other modules PASS or PASS-WITH-NOTES.
- The suite is green and stable. Seven mutants survive, which shows real test gaps.

## 1. Repeated test runs and flakiness

Command: `PYTHONPATH=src python3 -I -W ignore -m unittest discover -s tests`, 20 times.

| Run | Result |
|---|---|
| First loop | 20/20 OK. Runs 1-3 ran 46 tests and runs 4-20 ran 51, because `runner.py` and `test_runner.py` landed at 19:03:20 mid-loop. The tree was still changing. |
| Second loop on a frozen tree | 20/20 `Ran 51 tests ... OK`. The sha256 of every file under `src tests train` was identical before and after (`TREE-STABLE`). |

**Diagnosis of the earlier `test_stats.test_bootstrap_cluster_and_seed` failure: most likely a stale or partial file. This cannot be proven after the fact.**

Evidence against real nondeterminism:
- `paired_bootstrap` uses `random.Random(seed)` over `sorted(groups)` and makes no time call.
- Output was identical under `PYTHONHASHSEED` 0, 1 and 12345: `(0.333, -1.0, 1.0)`.
- The test's assertions still pass with an unseeded RNG (the "ignore seed" mutant survived), so RNG state cannot make it fail.

Evidence for a mid-write window: `stats.py` was written at 19:01:48 and `test_stats.py` at 19:01:58. Other builders kept rewriting files until 19:03:20, as the 46→51 count change shows.

**Side finding:** the seeded-determinism check is too weak to catch a missing seed. See fix 9.

## 2. Per-module verdicts

Acceptance command per module: `discover -p test_<m>.py`. Every module passes it: manifest 2, stats 4, ledger 12, hazard 4, tokens 4, memlint 7, traps 4, sqlseq 3, t7_pure 5 and coupling 1 tests OK.

Hygiene checks:
- Stdlib only: grep of the imports found nothing beyond the stdlib.
- No network or GPU: no `urllib`, `socket`, `http`, `requests`, `torch` or `cuda`. `subprocess` is used only for local `git`.
- Prints: the only one is `tokens.__main__`, which prints the probe and carries no content.
- No stray artifacts: `git status --untracked-files=all` shows only the listed files.

| Module | Verdict | Evidence |
|---|---|---|
| manifest (W1-01) | PASS-WITH-NOTES | Stable hash, a one-byte edit changes it, and missing values are `None` (all tested). **Path-dependent:** `tree_hash` hashes the path string as given. Identical trees at two locations give different hashes (`False`), and `src` vs its absolute path differ (`False`). `check_prereg` inherits this, so a freeze on the host fails in a container mounted elsewhere, or under a different invocation. The `versions` field has only the Python version. The "drop filename from hash" mutant survived, so renames are untested. |
| stats (W1-02) | PASS-WITH-NOTES | Holm matched a brute-force reference with 0 mismatches over 2000 random cases (ties and boundary values included). Hand case `[0.04,0.01,0.03,0.005]` gives `[F,T,F,T]`, which is correct. Cluster resampling is real: resample sizes are `{2,6,10}` for clusters of 5 and 1 rows, where a by-row resample would always give 6. The row-resample mutant was KILLED. Gaps: the `>`→`>=` boundary mutant and the unseeded-RNG mutant both SURVIVED. Mixed-type cluster keys raise `TypeError` from `sorted`. Empty rows return `(0,0,0)` because the metric is called on `[]`. |
| ledger (W1-03) | PASS-WITH-NOTES | **Separation holds:** across 30 random poisoned test halves the train rows were identical (1 distinct) and the chosen tau did not change. Three leak mutants were KILLED: tau picked on test, sweep on all events, split by event. The exposure fix is still in place and tested: the "exposure on decay = real gap" mutant was KILLED. The grow_decay tail is consistent, because a decay sweep runs at every event including the last, so the tail never exceeds tau (probe: promote_repeated 98.0, grow_decay 14.0, `dead_rules_at_end` 0). Notes: (a) `_tau_row` returns `0.0` for a zero denominator (`{'exposure_saving': 0.0, 'extra_prompts': 0.0}` on empty or no-promotion input), so null is recorded as 0. (b) The ratios carry no numerator or denominator, which breaks the PRINCIPLES units rule. (c) Interleaved sessions: when session A spans days 0-50, it goes to train while test session C starts on day 2 (`max train t 50.0, min test t 2.0`). Sessions are disjoint but not split by time. (d) The shortcut comment says ties "break by name"; they actually break by input order. |
| hazard (W1-04) | PASS-WITH-NOTES | The MLE and Vuong LLR are correct; the seeded alpha lands within ±10% and exponential data favours the exponential (tested). Degenerate inputs are handled without crashing: `[]`, `[3.0]` and `[2,2,2]` all return `alpha=None`. However, they return `llr 0.0, p 1.0` instead of `None`. Two gaps give a fit with p 0.94 (fine, but n=2). `gaps()` counts denied events as uses (`[1.0, 2.0]`). The "one-sided p" mutant SURVIVED. |
| tokens (W1-05) | PASS-WITH-NOTES | **No leak on real data:** ran on `~/.claude/projects` (33 files, 1226 assistant messages, 33 sessions), printing counts only. All 67 output strings are key-shaped (`[A-Za-z0-9_.]`), with 0 containing a space and a max length of 40. The canary test is real: a mutant adding `json.dumps(content)` was KILLED. Defects: (a) `_num` turns a missing or non-int usage field into `0`. Probe: missing cache fields give `0 0`, so null is recorded as 0, a §4.2 target. (b) A tool_use streamed in 3 records with the same `tool_use` id counts 3 reads. The test fixture enshrines the double count (`reads == 4`). |
| memlint (W1-06) | PASS-WITH-NOTES | Path traversal is blocked for `../x`, absolute paths, a symlink to `/etc/hostname`, `a/../../etc` and a sibling-prefix dir `<root>-evil`: all return `source_outside_root`. Defects: (a) a NUL byte in `source` crashes `lint` with `ValueError` (embedded null byte). (b) A non-UTF-8 file crashes `lint_dir` with `UnicodeDecodeError`. (c) The secret regex misses `ghp_…`, `xoxb-…`, `aws_secret_access_key=…` and `token=…`; the last is in W0-1's own grep list. (d) Any 7-40 hex string (`0000000`) passes as a commit; this is declared as a shortcut. The sibling-prefix mutant (dropping `os.sep`) SURVIVED, so it is untested even though the code is right. |
| traps (W1-07) | PASS | Byte-identical per seed, seeds differ, and the wrong-note follower hits the canary twice with re-entry (tested). The seed mutant was KILLED. Note: `trap.json`, which holds the canary and the fix value, sits beside `repo/`. The runner must not expose `out/` to the agent. |
| sqlseq (W1-08) | PASS-WITH-NOTES | Byte-identical, 40 questions, the oracle scores 1.0 and stateless scores below 0.5 on every family (tested). The vocabulary-leak branch of `check_split` is never exercised: its mutant SURVIVED. DB bytes depend on the SQLite library version (same-host only). |
| power (W1-09) | **FAIL** | (a) `idle_fraction` is power ≤ baseline×1.1 weighted by seconds, while WORKPLAN §6 defines it as samples with `utilization.gpu`=0 over samples in the job window. Utilization is not parsed at all. (b) The default baseline is the job's own minimum, so a constant 100 W fully busy job reports `idle_fraction 1.0`. (c) There are no baseline-subtracted joules, though §6 asks for gross and net. (d) The §6 sampler output (`noheader,nounits`) makes `parse_csv` crash with a bare `StopIteration`. (e) Identical timestamps give `idle_fraction 0.0`, which should be None. Units are right: watts × seconds = J (trapezoid, where §6 says rectangle; state it). The `<`/`<=` mutant SURVIVED. |
| t7_arms (W1-09) | PASS-WITH-NOTES | Truncation accuracy at 2k and 8k, seeded sampling and the torn-line JSONL are tested. **Resume keys on `id` only:** probe running arm B on an out file that already holds arm 0 made 0 calls, so a whole arm is skipped silently. There is no shortcut comment. |
| t7_edit (W1-09) | **FAIL** | The base-checksum "verification" is tautological. It compares a list it deep-copies and never mutates against itself, so it is always equal. The "drop post-check" mutant SURVIVED. Neither `apply_column_edit(w, spec)` nor `runner.py`/`t7_arms.py` (grep: no `sha256`/`expected`) takes the recorded base sha256, so §7's "a sha256 mismatch aborts T7" is not implemented. A ragged base raises a bare `IndexError` after validation. |
| coupling (W1-11) | PASS-WITH-NOTES | Commits after the cutoff are ignored (tested, and the mutant was KILLED). Merge commits contribute no pairs; their parents' commits do (probe: `{('c','e'):1, ('a','b'):1}`). This is reasonable but undocumented. An empty repo raises `CalledProcessError`. A non-ASCII path comes back C-quoted (`'"sp ace/\\303\\274.txt"'`), so names will not match real files. |

`shortcut:` comments exist in stats, manifest, hazard, memlint, coupling and ledger. They are missing where known limits exist: power (baseline), tokens (one file = one session, tool counting) and t7_arms (resume key).

## 3. Mutation summary

Mutants ran on copies in the scratchpad, never in the repo.

- **KILLED (13):** stats row-resample; ledger ×4 (tau on test, sweep on all, split by event, exposure-on-decay); hazard alpha; coupling cutoff; tokens ×3 (unsalted, no dedupe, content leak); memlint no bound; t7_edit mutate base; traps seed.
- **SURVIVED (8):** Holm `>=`; stats unseeded RNG; manifest drop filename; hazard one-sided p; memlint `startswith` without sep; t7_edit drop post-check (the check is dead code); power `<`; sqlseq vocab check.

## 4. Fix list, ranked by severity

1. **power.py (FAIL).** Parse `utilization.gpu`. Define `idle_fraction` = samples with util 0 / samples in the window, as in §6. Take `baseline_w` from the separate 60 s pre-job record, never the job minimum. Return gross and baseline-subtracted joules. Accept the §6 `noheader,nounits` format and raise `ValueError` on a bad header. Return `None` instead of 0.0 when seconds = 0. Add tests for a constant busy job and the §6 format.
2. **t7_edit.py (FAIL).** Take `expected_base_sha256` and raise before editing on mismatch, comparing against the recorded download manifest. Delete or keep the dead post-check, but do not call it verification. Validate ragged rows. Add a mismatch test.
3. **manifest.tree_hash path dependence.** Hash each file's path relative to its input root, not the given string, so `check_prereg` is location- and invocation-independent. Add tests: same tree at two locations gives equal hashes, and a rename gives a different hash. Add tool versions, or state that only Python is recorded.
4. **t7_arms.run resume.** Key done records on `(id, arm, cap)` or refuse a file whose records name another arm or cap. Add a test.
5. **tokens.py null as 0 and double counting.** Return `None` for an absent usage field and keep 0 only for a reported 0. Count tool_use by unique `id`. Fix the fixture that enshrines `reads == 4`.
6. **ledger.py.** `_tau_row` should return `None` for zero denominators and include numerators and denominators (exposure days, prompts) per PRINCIPLES. Either cut sessions by time or record that interleaved sessions put train events after the test start. Correct the tie-break comment.
7. **coupling.py.** Use `git -c core.quotePath=false log -z` (or parse NUL-separated output). Document that merges are skipped. Give a clear error, or `{}`, for an empty repo.
8. **memlint.py.** Treat a NUL byte as `source_dangling`. Open files with `errors="replace"`, or count `unparseable`, instead of crashing. Add `ghp_`/`github_pat_`, `xox[abpr]-`, `aws_secret_access_key` and `token=` patterns.
9. **Test gaps (surviving mutants).** Holm boundary (p equal to alpha/(m-k)); a seeded-determinism test that compares two seeds over a continuous metric; a rename in manifest; a two-sided p in hazard; a sibling-prefix escape in memlint; the sqlseq vocabulary branch; the power idle boundary.
10. **Low.**
    - hazard: return `llr`/`p` as `None` when degenerate, and exclude denied events from `gaps`.
    - Tests leak `tempfile.mkdtemp` dirs (`test_traps`, `test_sqlseq`); use `TemporaryDirectory`.
    - Move `trap.json` outside the agent-visible tree, or document it for the runner.
    - Add the missing `shortcut:` comments.

## 5. Not checked

- `runner.py` (W1-10) and `prereg/` (W1-12), both out of scope.
- Real `nvidia-smi` output on this box (no process was run).
- `sqlseq` byte identity across SQLite versions.
- Whether real Claude Code transcripts actually repeat `tool_use` blocks across streamed records. The double count is shown on a fixture only.
