# R1 L5 grader fix: decision ADOPT

**Decided by:** the TREMOR lane as L5 grader source owner (PC designation `msg_9cc549080e56`), under the owner's delegated authority for the night of 2026-11-23.
**Applies to:** the next X42 candidate, which is built on the nominated e972484a bytes.

## The fix

`runs/r1-execution-consistency.BtUauk/owner.patch` (sha256 `16a1262ef94ad0f8b1b3f656ea8e8703f2130af6596f386df930031191f5b143`) changes `lab/l5_grader_custody.py` and `lab/tests/test_l5_grader_custody.py`.

**Defect:** the original grader counts an executed norm violation even when the action log records the action as rejected.

**Patch:** the action's `rejected` flag must be a Boolean that agrees with a recognised dispatch status before any execution classification is computed.

## Evidence

An independent read-only evaluation (fresh-context Opus, briefed with `interrogate`, host `seabridge-spark`) worked from scratch copies of the run folders, so the repository was untouched:

1. **verify.sh:** `bash runs/r1-execution-consistency.BtUauk/verify.sh` exited 0. It checked the archive, manifest and evidence hashes, confirmed the patch equals the diff of the candidate files, saw the red run fail as expected ("ValueError not raised"), saw the green run pass (9 tests OK), and matched both the original and the candidate report to `report.json`. All six normalised public cases were preserved.
2. **Fail-before, pass-after:** the patched test file against the original grader exits 1 with 4 failures (the main regression plus three subtests). Against the patched grader it exits 0 with 9 tests OK. The 7 existing tests pass on both.
3. **Line review:**
   - The only deleted line, `executed = row["n1_dispatch"] in team.EXECUTED`, comes back as `executed = status in team.EXECUTED`.
   - Every existing `_require` call and test is kept, and one `_require` is added.
   - Unknown statuses cannot come from a legitimate run: `router.act` and `enforce.py` produce exactly `admitted | refused | violation_executed`, and the fixture writes a Boolean `rejected`.
4. **Archive lab suite, without and with the patch:**

   | | Tests | Errors | Skipped |
   |---|---|---|---|
   | Without | 554 | 10 | 9 |
   | With | 556 | 10 | 9 |

   The only change in per-test results is the two new passing tests. The 10 errors are environmental and identical in both runs: numpy and torch are absent, and `runs/ep1-live/pilot3/episodes.jsonl` is not in the manifest.

## Decision

ADOPT. The patch fixes the false-execution defect, weakens no check, leaves every recorded public case unchanged, and refuses only inputs that no legitimate producer emits.

## Known limit

The check proves that the two records agree. It is not independent evidence of where they came from: a producer that changes both together would pass. Protected N2, host qualification and the formal bench verdict are separate gates.
