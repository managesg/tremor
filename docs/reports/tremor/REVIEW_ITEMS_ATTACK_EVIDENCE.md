# TREMOR review items: attack, test, mutation (fast path for the Assistant)

Lane: TREMOR. Refreshed 2026-11-26 at committed HEAD `9009eaf` in `/home/adelmar/SeaBridgeAI/murmuration`. Not committed.
Every command: `PYTHONPATH=src:tests:. python3 -B -m unittest <module>` from the repo root. No network, model, GPU or key.

Two columns per item:
- **lane** = the lane checkout. Note: during this run `lab/r6_inkling_client.py` and `lab/quantum/differential-report.md` showed as modified
  (uncommitted edits by someone else), so lane numbers for item 5 may include that edit; the archive column is exactly HEAD.
- **archive** = a fresh `git archive HEAD` extracted to a `mktemp` dir under `/tmp/claude-1000/mut` (nothing else copied; the price sheet
  `docs/reports/tremor/price-sheet-20261126.json` is tracked since 42a3d0e, so it is in the archive). The real, git-ignored `runs/spend`
  ledgers are absent there: tests that need them SKIP and are UNVERIFIED in the archive column (counts below).

Mutation method: copy the tree to a `mktemp` dir (lane: `lab`, `src`, `tests` copied, rest symlinked read-only; archive: the whole archive
copied), apply ONE `str.replace` (asserted to match exactly once), run the item's tests there with `PYTHONPATH` on the copy and `unittest -f`
(stops at the first failure, so "Ran N" of a caught mutation is partial). Script: `/tmp/claude-1000/mut/refresh.py`; raw output
`/tmp/claude-1000/mut/refresh.out`. `runs/spend` sha256 over its files before and after: `c9e7333d...` (identical).

Result key: lane / archive. All 15 mutation runs below were caught in BOTH copies. Survivors: none.

## 1. 623f83b admission gate (lab/tremor_admission_gate.py; later 05d7807 and 9009eaf touch it)
- Attacks: admission record copied to another path; second worktree re-admit; GIT_DIR redirect; owner-words substring; protocol hash from the working tree; hard-linked input (9009eaf).
- Tests: `test_copied_admission_cannot_admit_twice`, `test_other_worktree_shares_claims`, `test_git_dir_cannot_redirect_admit_or_claim_location`, `test_git_env_cannot_redirect_check`, `test_owner_words_exact_equality`, `test_protocol_working_tree_edit_is_ignored_commit_content_is_hashed`, `test_input_sha_refuses_hard_linked_file`.
- Command: `... unittest lab.tests.test_tremor_admission_gate`
- Result: lane `Ran 67 tests in 10.235s` OK / archive `Ran 67 tests in 15.553s` OK.
- Mutation 1: `_git`: `if not k.startswith("GIT_")}` -> `if True}`. CAUGHT both: `ERROR: test_git_dir_cannot_redirect_admit_or_claim_location`, `Ran 29`, `FAILED (errors=1)`.
- Mutation 2 (hard link): `st_nlink > 1` -> `st_nlink > 10**9`. CAUGHT both: `FAIL: test_input_sha_refuses_hard_linked_file`, `Ran 34`, `FAILED (failures=1)`.

## 2. e696b16 price-sheet successor path (src/murmuration/spend.py)
- Attack: a forged `sheet_continuity` line in another ledger file (before its batch_open, or branching from an old digest) must be corrupt, never followed.
- Command: `... unittest tests.test_spend tests.test_ep1`
- Result: lane `Ran 204 tests in 436.360s` OK / archive `Ran 204 tests in 319.118s` OK (no skips).
- Mutation: `Ledger._sum`: `if opens.get(b) != old:` -> `if False:`. CAUGHT both: `FAIL: test_branching_continuity_is_corrupt`, `Ran 68`, `FAILED (failures=1)`.

## 3. 33343d2 pre-reservation sheet refusals (src/murmuration/ep1.py, spend.py)
- Attack: a forgotten `--predecessor-price-sheet` flag must exit 2 with a reason and write nothing, so the batch is not stopped for good. The CLI cases are in the module below.
- Command: `... unittest lab.tests.test_ep1_continuity_cli` (also `tests.test_ep1`, item 2)
- Result: lane `Ran 11 tests in 5.919s` OK / archive `Ran 11 tests in 2.179s` `OK (skipped=7)`: the 7 real-ledger tests are UNVERIFIED in the archive; the synthetic-ledger variants ran.
- Mutation: `ep1.run_batch`: `ledger.check_sheet()  #` -> `pass  #`. CAUGHT lane: `FAIL: test_a2_a_forgotten_flag_does_not_stop_the_batch` (`Ran 1`); CAUGHT archive by the synthetic variant `FAIL: test_forgotten_flag_is_refused_up_front_and_does_not_stop_the_batch` (`Ran 9`, `FAILED (failures=1, skipped=7)`).

## 4. 05d7807 sealed inputs (lab/tremor_sealed_inputs.py)
- Attacks: a file planted in a sealed root (must be reported as `extra`, recursive, symlinks not followed); a parent directory swapped for a symlink (refused by seal, verify and the gate's input hash, also for a missing file); hard-linked file.
- Command: `... unittest lab.tests.test_tremor_sealed_inputs`
- Result: lane `Ran 61 tests in 0.352s` OK / archive `Ran 61 tests in 0.330s` OK.
- Mutation 1 (planted file): `verify`: `if rel not in listed and rel != manifest_path:` -> `if False:`. CAUGHT both: `FAIL: test_extra`, `Ran 12`, `FAILED (failures=1)`.
- Mutation 2 (parent swap): `_full`: `if os.path.islink(full) or os.path.realpath(full) != full:` -> `if False:`. CAUGHT both: `FAIL: test_missing_file_under_symlinked_parent_refused`, `Ran 29`, `FAILED (failures=1)`.

## 5. 9486e3c Inkling client and f788499 P0 driver (lab/r6_inkling_client.py, lab/r6_p0_probe.py)
- Attacks: loopback forms (`localhost`, non-IP, stub flag); userinfo in the URL; proxy env (client uses raw `http.client`, so urllib proxy env cannot apply; no mutation); slow-loris (hard wall deadline; not mutated); two clients one admission (the gate's `O_EXCL` claim); per-call token budget overrun; identity mismatch makes zero requests and never claims.
- Command: `... unittest lab.tests.test_r6_inkling_client lab.tests.test_r6_p0_probe`
- Result: lane `Ran 103 tests in 35.855s` OK / archive `Ran 103 tests in 35.552s` OK.
- Mutation A (userinfo): `if u.username or u.password or u.query or u.fragment:` -> `if u.query or u.fragment:`. CAUGHT both: `FAIL: test_bad_scheme_and_url_parts`, `Ran 24`.
- Mutation B (budget overrun): `if self._tokens + est_prompt + max_tokens > self._max_total:` -> `if False:`. CAUGHT both: `FAIL: test_token_precheck_uses_per_call_value`, `Ran 15`.
- Mutation C (identity): `r6_p0_probe`: `if not identity_matches(frozen, live):` -> `if False:`. CAUGHT both: `FAIL: test_mismatch_stops_before_claim_and_call`, `Ran 59`.
- Mutation D (two clients one admission): gate `os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW` -> without `os.O_EXCL`; run against gate + client + probe tests. CAUGHT both: `FAIL: test_copied_admission_cannot_admit_twice`, `Ran 20`, `FAILED (failures=1)`.

## 6. 42a3d0e run-data tests skip on a clean checkout, with synthetic-ledger variants
- Claim to check: on a checkout without the git-ignored `runs/spend` ledgers the run-data tests SKIP with a reason (never silently pass) and the synthetic variants still guard the behaviour.
- Command: `... unittest lab.tests.test_ep1_continuity_cli lab.tests.test_pilot4_rehearsal`
- Result: lane `Ran 14 tests in 25.619s` OK / archive `Ran 14 tests in 9.273s` `OK (skipped=8)`: 8 real-ledger tests UNVERIFIED in the archive.
- Mutation: same as item 3 (`ledger.check_sheet()  #` -> `pass  #`), run on the archive only to prove the synthetic path works without real ledgers. CAUGHT: `FAIL: test_forgotten_flag_is_refused_up_front_and_does_not_stop_the_batch`, `Ran 9`, `FAILED (failures=1, skipped=7)`. Lane: caught by `test_a2_a_forgotten_flag_does_not_stop_the_batch`.

## 7. caf0643 and 5108519 lemma sandbox (lab/r6_predicates.py)
- Attacks: dunder escape, huge range, shifts, step budgets (budget types validated in 5108519).
- Command: `... unittest lab.tests.test_r6_predicates`
- Result: lane `Ran 51 tests in 0.099s` OK / archive `Ran 51 tests in 0.099s` OK.
- Mutation: `_check`: final `_refuse("node type " + t.__name__)` -> `kids = []`. CAUGHT both: `FAIL: test_all_refused_at_parse (s='x.__class__.__mro__')`, `Ran 7`.

## 8. fa03232 and 28610e1 scorecard (lab/r6_scorecard.py)
- Attacks: reweighting (card weights must equal the frozen ones), empty keyword and pattern lists, sealed patterns that change under NFKC.
- Command: `... unittest lab.tests.test_r6_scorecard`
- Result: lane `Ran 44 tests in 0.071s` OK / archive `Ran 44 tests in 0.070s` OK.
- Mutation: `_check_lists`: `if _nfkc(p) != p:` -> `if False:`. CAUGHT both: `FAIL: test_unicode_cannot_hide_keywords_or_patterns`, `Ran 13`.

## 9. 8e828f1 Holm (lab/r6_holm.py)
- Attack: the H1 same-side bug (opposite-side EG4/EG8 intervals must kill; kill wins over a Holm rejection).
- Command: `... unittest lab.tests.test_r6_holm`
- Result: lane `Ran 15 tests in 0.017s` OK / archive `Ran 15 tests in 0.047s` OK.
- Mutation: `claim`: `killed = s == {"above", "below"}` -> `killed = False`. CAUGHT both: `FAIL: test_kill_wins`, `Ran 4`.

## 10. d0c67d7 R5 harness (lab/r5_perf_harness.py)
- Attack: the overdispersion check (a planted shared cause must be flagged at every n; an interval containing 1 at every n is a refusal reason).
- Command: `... unittest lab.tests.test_r5_perf_harness`
- Result: lane `Ran 65 tests in 75.229s` OK / archive `Ran 65 tests in 76.631s` OK.
- Mutation: `if all(lo <= 1 <= hi for lo, hi in ods.values()):` -> `if False:`. CAUGHT both: `FAIL: test_planted_shared_cause_is_flagged_at_every_size`, `Ran 28`.

## Summary
10 items, 15 mutations, 15 caught in both copies, 0 survivors. Unverified in the archive: 7 tests (item 3) and 8 tests (item 6) that need the real
`runs/spend` ledgers; they passed in the lane checkout. A mutation proves only that the named test guards that line, not every attack in the item.
Mutation and archive copies stay under `/tmp/claude-1000/mut` (not deleted).


Note added by the lane at commit time: the "modified by someone else during the run" remark about `lab/r6_inkling_client.py` refers to this lane's own worker resolving the Assistant's low survivor (after-loop deadline check, line ~285); the archive numbers are exactly the committed HEAD 9009eaf.
