# L2-C ranked Board dispatch with once-per-target screening

The two Board prefixes are separate. An externally pinned one-to-one
mapping joins each calibration rank to a visible held-out target and its
exact scalar version. The runner replays the calibration rankings against
their closure anchor, checks the held-out prefix and its complete dispatch
tape, and verifies the mapped claim bytes before selecting any checks.

Each chosen target gets one scripted evaluator start and settlement.
Matched, mismatched and unavailable results each occupy one check. An
independent replay checks the ledger against the pinned evaluator
reference. The dispatcher reuses the settled status for both a relay and
a promotion attempt per target. Unchecked and matched visible targets
remain eligible for those actions. Mismatches and unavailable results
refuse. Ordinary named reads remain available, including reads of the
original mismatched scalar.

The same four reads and eight dispatches run in every arm. The physical
audit verifies the presence or absence of each expected Board post and the
closure that follows it. Each cached lookup is accounted separately from
the initial evaluator checks. Detached factual labels are applied after
dispatch. The runner validates their envelope and scope before opening
the output Board, and neither the evaluator settlement nor dispatch
uses their values. Reversing labels leaves the ledger, decisions and Board
bytes identical.

| Arm | Evaluator checks | Cached lookups | Committed posts | Invalid dispatches admitted | Factually valid attempts refused |
| --- | ---: | ---: | ---: | ---: | ---: |
| Direct relay count | 1 | 2 | 6 | 0 | 0 |
| Out-degree | 1 | 2 | 6 | 2 | 2 |
| Named retrievals | 1 | 2 | 8 | 2 | 0 |
| Recency | 1 | 2 | 8 | 2 | 0 |
| Seeded random | 1 | 2 | 8 | 2 | 0 |
| Zero verification | 0 | 0 | 8 | 2 | 0 |
| Full verification | 4 | 8 | 4 | 0 | 2 |

In this fixture, direct-relay ranking checks the mismatched target and
blocks two later writes from that one settlement. Out-degree selects the
target whose evaluator is unavailable. That check is charged and the
target's two otherwise factually valid dispatches are refused. Full
verification blocks both categories. These counts describe a development
screening policy. Scientific model adoption, the equivalence margin,
actual monetary or token cost, and real evaluation custody remain separate
requirements.

Review reproduced the crossed-label retry issue. The final runner
rejects the crossed envelope before creating the arm file, and the valid
retry succeeds at that same destination. Re-pinned claim-version changes,
duplicate mapped targets, forged ledger statuses and forged cached
lookup counts were also exercised.

## Reproduce

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m lab.l2c_ranked_dispatch
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:lab:tests python3 -m unittest -q \
  lab.tests.test_l2c_ranked_dispatch lab.tests.test_l2c_provenance_control \
  lab.tests.test_l2c_verification_ranking
```

All 22 focused tests passed. The full report reproduced byte for byte at
`runs/l2c-ranked-board-dispatch.3pOPx0/report.json`, SHA-256
`0019b51ae2c2475814a2d2682a7eb1a66c544b9f441de68cf41ab3e55e7332c5`.
The directory retains both initial Boards, each arm's event chain, the
bridge and evaluator reference, the detached label tape and each ledger.

The pinned offline ARM64 CPU lab suite passed all 596 tests in 35.146
seconds without skips. The log is `/tmp/tremor-cpu-suite.Zssl5w`, SHA-256
`b92db049b22307782fc48fed7ba9515cc6d2c94ce47c2922f0b9af12bce66745`.
Spark vLLM health returned HTTP 200.
