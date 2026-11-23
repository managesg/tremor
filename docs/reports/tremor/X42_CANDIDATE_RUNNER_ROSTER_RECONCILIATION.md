# X42 candidate, runner and roster reconciliation

Requested by the Assistant at the 20 UTC checkpoint (`msg_3c7c734027a2`), before any quiet-window request.

## The candidate of record is `83e4870`

| Item | Value | Evidence |
| --- | --- | --- |
| Candidate commit | `83e48700923fb80bd03c05a58f97b4ca9c6973cf` | bench re-check `runs/x42-bench-recheck-83e4870.4P3pJg/VERDICT.md` (sha256 `48834c15…`), row 157 ACCEPT |
| Tree | `572155d04e9c45e1a1980256dab9934246b8fa89` (586 files) | dry preflight `runs/x42-quiet-host-dry-preflight.ObtNW8` |
| Runner target | `commit=` and `tree=` equal the two values above | `OWNER_DECISION_X42_quiet_host_window.md`, lines 55–56, commit `9a3897d` |
| Roster | package 869 IDs (sha256 `b5125b45…`), lab 878 IDs (sha256 `9575847a…`) | dry preflight, collected in the pinned image, no tests run |
| Suites | package 869 OK, lab 878 OK, exit 0 | `runs/container-suite-83e4870.h77kHM` |

Candidate, runner and roster all name the same commit and tree. They agree.

## Commits after the candidate are not in it

`git log 83e4870..HEAD` shows five commits: `e74fcdc`, `5ddd339`, `a833e17`, `9a3897d` and `2c3e914`. All are docs except one test file in `2c3e914`, `lab/tests/test_r1_staggered_pin_literal.py`, which pins the v4 pin values literally (a re-check minor note). A run of HEAD would therefore collect 879 lab tests, not 878.

**Decision:** the quiet-host window runs the exact candidate `83e4870`, with its roster pinned at 878. The literal test is not part of the window. It does not change any code under review, since v4 and its pins are byte-identical. If PC prefers to include it, the candidate moves to `2c3e914` or later, and these must be redone before W1:

1. full suites in the pinned image;
2. a fresh dry preflight and roster;
3. the runner's `commit=` and `tree=`;
4. a bench note confirming the diff is test and docs only.

No window may run with a roster that does not match its source tree. The runner checks the tree id before it starts.
