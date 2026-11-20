# Wave 1 final acceptance check

2026-11-19, Opus 5.5 (independent adversarial verifier). Base: local commit `74b0494` plus uncommitted work.
Claims are bound to a frozen copy of `src tests train fixtures` with combined sha256 `8b200f8b75dc7d35...`.
The live tree had the same hash before the 20x loop and again just before this report was written.
No repo file was edited except this one. Mutants, probes and old-behaviour restorations ran on copies in the
session scratchpad. Real-transcript probes printed counts only.

## Verdict: ACCEPTED-WITH-NOTES for a second local commit; NOT yet ready for an H1 or E8.1 FREEZE

- Every prior FAIL is fixed. 31 of 33 old-behaviour restorations fail at least one test.
- One fix is untested: the runner's `tokens_method` label. Restoring the old behaviour passes the suite.
  The other survivor (CO3) is an equivalent mutant.
- Freezing needs the procedural preconditions in section 6. One of them is a wrong-provenance record from
  the `manifest --root` gap.

## 1. Prior FAIL and open items: old behaviour restored, test must fail

Harness: copy the frozen tree, apply one exact-once text patch that restores the old behaviour, then run
`python3 -B -m unittest discover -s tests -p <module test>`.

| Item | Old behaviour restored | Result | Killing test |
|---|---|---|---|
| manifest MF1 | hash the absolute path | KILLED | `test_check_prereg_passes_elsewhere_fails_on_edit` |
| manifest MF2 | relpath per input root (prior root-collapse regression) | KILLED | `test_move_changes_hash_same_content_other_checkout_does_not` |
| manifest MF3 | drop the filename from the hash | KILLED | same |
| manifest MF4 | dedupe identical bytes | KILLED | `test_identical_bytes_at_distinct_paths_not_deduped` |
| runner RU1 | delete the `tokens_method` field | **SURVIVED** | none. No test asserts the label. |
| ledger LE1/LE2 | zero denominator gives `0.0` | KILLED ×2 | `test_zero_denominators_are_none_and_never_meet_bar` |
| coupling CO1 | empty repo raises | KILLED | `test_empty_repo_returns_empty` |
| coupling CO2 | `quotePath` left on | KILLED | `test_non_ascii_path_is_not_quoted` |
| coupling CO3 | drop `--no-merges` | survived (equivalent) | Without `-m`, `git log --name-only` lists no files for a merge, so the flag changes nothing. |
| memlint ML1-ML5 | NUL crash; non-UTF-8 crash; old 3-pattern secret regex; `startswith` without sep; no root bound | KILLED ×5 | `test_nul_…`, `test_non_utf8_…`, `test_more_secret_shapes`, `test_sibling_prefix_escape`, `test_dangling_and_escape` |
| power PW1-PW4 | idle from power ≤ min×1.1; baseline = minimum; idle when `u<5`; zero seconds gives 0.0 | KILLED ×4 | `test_idle_is_utilization_not_power`, `test_baseline_is_mean_not_minimum`, `test_idle_means_utilization_exactly_zero` |
| t7_edit TE1 | expected sha ignored | KILLED | `test_edit` |
| t7_arms TA1/TA2 | resume keyed on id only; on (id, arm, cap) | KILLED ×2 | `test_resume_key_includes_arm_cap_seed` |
| tokens TK1-TK4 | missing gives 0; no tool_use dedupe; key ignores `id`; missing cache_hit denominator gives 0 | KILLED ×4 | `test_missing_usage_is_none_not_zero`, `test_repeated_tool_use_id_counted_once`, `test_distinct_tool_use_ids_in_one_message_both_count` |
| hazard HZ1-HZ4 | degenerate gives `llr 0.0, p 1.0` (two paths); denied counted as a use; one-sided p | KILLED ×4 | `test_degenerate`, `test_denied_events_are_not_uses`, `test_p_is_two_sided_vuong` |
| stats ST1/ST2 | Holm `>=`; unseeded RNG | KILLED ×2 | `test_holm_boundary_is_inclusive_reject`, `test_bootstrap_seed_is_honoured` |
| sqlseq SQ1 | vocabulary check off | KILLED | `test_shared_vocabulary_is_rejected` |

All 7 prior survivors are now killed: S3, S5, H1, ML1, Q1, P5 and P6, plus T3 as TK3.

### Adversarial `tree_hash` probes

Each probe used synthetic `src/` and `train/` trees.

| Case | Result |
|---|---|
| The same tree at another checkout location | equal |
| Two files swap contents | changes |
| A file moves from `src/` to `train/` | changes |
| A file symlink is added | changes |
| An empty dir is added | **unchanged**: empty dirs are invisible, as in git |
| A regular file is replaced by a symlink to identical bytes | **unchanged** |
| Code under a symlinked dir is edited | **unchanged**: `os.walk` does not follow it. This is a false-pass vector. |
| A dangling symlink | `FileNotFoundError`, which fails closed |
| `tree_hash([src])` against `tree_hash([src], root=repo)` | differ: the default root depends on the path set |
| `tree_hash(['.'])` | includes `.git`, `runs/` and `.salt`, so it changes when run outputs change |

The repo has 0 symlinks today.

## 2. Flakiness

20 runs of `PYTHONPATH=src python3 -B -W ignore -m unittest discover -s tests` on the frozen copy:
20/20 `Ran 85 tests … OK` (2.54-3.28 s). The tree hash was identical before and after. No flakiness.

## 3. CLI and real-data privacy

- `--help` exits 0 for the top level and all 13 subcommands: report, synth, sweep, allowlist, hazard,
  tokens, memlint, coupling, manifest, trap-gen, seq-gen, run, power-parse.
- The corpus is `~/.claude/projects`, 41 JSONL files. Sentinel words chosen from this verifier's own
  prompt ("adversarial", "verifier", "flakiness", "sentinel", "acceptance", "freeze", "ponytail") occur in
  7-41 source files each. Salted runs of report, sweep, hazard, tokens probe, tokens ledger and allowlist
  all exited 0 with empty stderr:
  - 0 sentinel hits.
  - 0 leaves with a space, `/` or `=`.
  - The salt does not appear in the output, and neither does the home path.
  - The largest output is the tokens ledger: 738 leaves, max length 22.
- **Unsalted output leaks command content.** `allowlist` without `--salt` emits raw `Bash:<first token>`
  keys. Of its 15 keys, 2 are environment assignments (`UPPERCASE=value`, values up to 113 characters, with
  `/`). They matched no secret pattern, but this is transcript text, which contradicts the README's "never
  transcript or message content". Unsalted `report`, `sweep` and `hazard` emit no keys and are clean.

### `manifest --root` gap

`--root` reaches only `git_sha` and never `tree_hash`. The tree hash root is the common parent of the
`--tree` paths, the same default `check_prereg` uses. So `--root` cannot make `check_prereg` pass falsely.

It can, however, write a **wrong-provenance record**. Probe: the cwd was a copy of `src` and `train` with
a one-byte edit, and the command was `manifest --root <repo> --tree src train`. The record paired the repo's
HEAD sha (equal to the repo: True) with the edited copy's tree hash (equal to the repo's: False; equal to
the copy's: True).

Further gaps:
- Without `--root`, `git_sha` comes from the cwd. It is None outside a repo.
- `git_sha` does not flag a dirty tree.
- `runner.run`'s manifest has no `tree_hash`, and its `git_sha` also reads the cwd.

## 4. Repo audit

- 55 tracked plus untracked files. The secret-pattern grep hits only the memlint regex, test shapes built at
  runtime, and a pattern name quoted in a report. None is a real credential.
- The only absolute out-of-repo path is `docs/WORKPLAN.md:10`. It is the owner's quoted approval, which names
  another repo's home path, and it is already committed in `74b0494`. For the owner to decide; not a blocker.
- The largest file is `docs/PLAN.md` at 77 KB. There are no binaries.
- `.gitignore` covers `runs/`, `data/`, `results/`, `.salt`, `*.jsonl` and `__pycache__`, each checked
  with `git check-ignore`. `data/`, `runs/` and `results/` do not exist. The only ignored files present are
  `__pycache__` dirs.

## 5. Per-module verdicts

| Module | Verdict | Open notes |
|---|---|---|
| manifest | ACCEPTED-WITH-NOTES | Symlinked dirs are not hashed. A symlink is indistinguishable from a file. Untracked or ignored files inside the paths are hashed. `versions` records Python and platform only. |
| runner | ACCEPTED-WITH-NOTES | The label is untested (RU1) and hard-coded for every backend. No `fsync` before `os.replace`. No `tree_hash`. `git_sha` from cwd. A rerun overwrites its record. `mkdtemp` leaks in its test. |
| ledger | ACCEPTED-WITH-NOTES | Interleaved sessions: train events can fall after the test start (by design, split by first event). |
| coupling | ACCEPTED-WITH-NOTES | A newline in a path comes back C-quoted (1 of 2 names matched a real file). This is not documented. |
| memlint | ACCEPTED-WITH-NOTES | **Secrets in JSON keys are missed.** `{"token": V}` and `{"aws_secret_access_key": V}` lint clean, while `"token: V"` inside a value is flagged: the closing quote sits between the key and the colon. `api_key` and `password` are not covered. An unhashable `id` or `supersedes` raises `TypeError`. |
| power | ACCEPTED-WITH-NOTES | Duplicate `_ts`. The time-weighted idle deviation is stated only in `UNITS`; WORKPLAN §6 is unchanged. |
| t7_edit | ACCEPTED-WITH-NOTES | `checksum` ignores shape (`[[1,2,3,4]]` and `[[1,2],[3,4]]` hash equal). No caller passes the manifest sha. The empty base is now fine. |
| t7_arms | ACCEPTED | — |
| tokens | ACCEPTED | — |
| hazard | ACCEPTED | — |
| stats | ACCEPTED-WITH-NOTES | `check_prereg` is called only by tests. Empty rows and mixed cluster keys were not re-probed. |
| sqlseq, traps | ACCEPTED-WITH-NOTES | `mkdtemp` leaks in tests. `trap.json` sits beside `repo/`. |
| CLI | ACCEPTED-WITH-NOTES | The `--root` provenance gap. Unsalted `allowlist` leaks command tokens. |
| prereg | not re-reviewed | Files are unchanged since the re-verification (mtimes 19:04-19:05). The H8 confirmatory/exploratory conflict is still open. The H1 and E8.1 numbers were checked for presence in PLAN only, never in context. |

## 6. Ranked residual defects

**Before any H1 or E8.1 FREEZE**
1. Commit first, and freeze from the repo root with exactly `--root . --tree src train`. Record that path list
   in the prereg. This avoids the wrong-provenance record and the stale `git_sha`.
2. Make `tree_hash` refuse symlinks, or record a zero-symlink check in the freeze record.
3. Run protocol: call `stats.check_prereg(frozen, ["src", "train"])` before each run. Nothing calls it today.
4. Unsalted `allowlist` output: require `--salt` (as `tokens ledger` does), or drop raw keys. H1 uses it.
5. Check the H1 and E8.1 prereg numbers in context. Decide H8 confirmatory against exploratory.
6. Runner, before any run reports its tokens: assert `tokens_method` in `test_runner`, set it per backend, and add
   `tree_hash` plus the repo root to its manifest.

**Acceptable for the commit; fix before the module is used**
7. memlint JSON-key secrets and the `TypeError` on an unhashable value. Needed before H4.
8. t7_edit shape-blind checksum, and wiring the manifest sha. Needed before T7.
9. Low: runner `fsync`, the duplicate `_ts`, WORKPLAN §6 time-weighting, the coupling newline note, and the
   `mkdtemp` leaks in test_runner, test_sqlseq and test_traps.

## 7. Second local commit: proposed staging, by path

The second commit stages:
- **Modified files:** `README.md`, `src/murmuration/__main__.py`, `src/murmuration/ledger.py`,
  `tests/test_ledger.py`.
- **Reports:** `docs/reports/wave1-verification.md`, `docs/reports/wave1-reverification.md`,
  `docs/reports/wave1-acceptance.md`.
- **Pre-registrations:** `prereg/E8.1.md`, `prereg/H1.md`, `prereg/H7.md`, `prereg/H8.md`.
- **Source:** `src/murmuration/coupling.py`, `src/murmuration/hazard.py`, `src/murmuration/manifest.py`,
  `src/murmuration/memlint.py`, `src/murmuration/runner.py`, `src/murmuration/stats.py`,
  `src/murmuration/tokens.py`, `src/murmuration/trapbench/__init__.py`, `src/murmuration/trapbench/sqlseq.py`,
  `src/murmuration/trapbench/traps.py`.
- **Tests:** `tests/test_cli.py`, `tests/test_coupling.py`, `tests/test_hazard.py`, `tests/test_manifest.py`,
  `tests/test_memlint.py`, `tests/test_runner.py`, `tests/test_sqlseq.py`, `tests/test_stats.py`,
  `tests/test_t7_pure.py`, `tests/test_tokens.py`, `tests/test_traps.py`.
- **Training scripts:** `train/power.py`, `train/t7_arms.py`, `train/t7_edit.py`.

Leave out, or stage only if the orchestrator owns it: `docs/PRINCIPLES.md`. Another session edited it (the
owner's scope guard), and this verifier did not review it.

Nothing under `data/`, `runs/` or `results/` exists. No `__pycache__` and no `*.jsonl` file is in the list.

## 8. Not checked

- Real `nvidia-smi` output.
- `sqlseq` byte identity across SQLite versions.
- The prereg contents beyond their mtimes.
- `docs/PRINCIPLES.md`.
