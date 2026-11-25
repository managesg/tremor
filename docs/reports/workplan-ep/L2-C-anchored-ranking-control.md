# L2-C predecision verification ranking

The offline control locks the active opening candidates at the exact
round-two Board commit. Ranking uses the predecision head and event count.
The feature pass records direct eligible relay counts, committed child
out-degree, successful named lookup counts and posted order. Repeated
references within a child count once. Repeated successful named reads count
as separate lookups. A bulk read and a lookup before the root became visible
do not increase named retrievals. The direct count requires a committed
relay following a named read and credits each registered worker and root
pair once.

The four observed maxima differ by ordering. Each ranking and the seeded
random draw checks one candidate. Full verification checks all four.
Zero verification checks none. The scorer compares deterministic rankings
to the recorded feature rows and independently replays the selection from
the pinned Board before applying the detached scalar labels. The label
inventory binds to the Board head because local candidate IDs can repeat
on different Boards.

## Scripted outcomes

| Strategy | Selected | Checks | Invalid uses remaining, original labels | Invalid uses remaining, reversed labels |
| --- | --- | ---: | ---: | ---: |
| Eligible direct relays | p1 | 1 | 5 | 1 |
| Committed out-degree | p3 | 1 | 6 | 1 |
| Named retrievals | p2 | 1 | 7 | 1 |
| Recency | p4 | 1 | 9 | 0 |
| Seeded random | p4 | 1 | 9 | 0 |
| Zero verification | None | 0 | 9 | 1 |
| Full verification | All four | 4 | 0 | 0 |

The original labels create nine invalid and one valid opportunity across
the same ten scheduled uses. The exact uniform one-check expectation is
27/4 invalid uses remaining. The reversal leaves only p4 invalid and keeps
the Board and selection unchanged. Recency then prevents its one invalid
use, while the direct-relay ranking prevents zero. A separate quiet Board
has zero on all three count metrics and selects the first canonical ID for
those tied rankings.

The counts describe a scripted terminal oracle with perfect verification
at selected IDs. Model adoption, the scientific equivalence margin, comparative dose response, and actual dispatch quarantine still need separate evidence. The exact planned candidate inventory and assay labels are
development inputs. Native evidence and independent label custody remain
with the protocol owners.

## Verification

Independent review reproduced an incorrect ranking accepted after
re-pinning and a label join across Boards reusing local IDs. The final
assay rejects a ranked choice that disagrees with the features, a forged
feature inventory inconsistent with actual Board replay, and outcomes
bound to a different Board head. It refuses an appended pending suffix
under the original pin and a completed later round even under its new pin.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m lab.l2c_verification_ranking
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:lab:tests python3 -m unittest -v \
  lab.tests.test_l2c_verification_ranking lab.tests.test_l2_relay_control \
  lab.tests.test_r3_l2_relay_generation
```

All 16 focused tests passed. The full report reproduced byte for byte at
`runs/l2c-verification-ranking.MXAz6j/report.json`, SHA-256
`6cea982afea426a777b19884cae129d9f72a8a2a068166f822e37784d655c039`.
The folder retains the Board, closure anchor, selection and canonical
selection pin, plus both separately generated outcome tapes and scores.
The common canonical selection SHA-256 is
`b9d76ac882c177dfc6677ce324706903ff64e4eb5e1260be1c0de3e63ad7c77f`.

The pinned offline ARM64 CPU lab suite passed all 582 tests in 34.168
seconds without skips. Its log is `/tmp/tremor-cpu-suite.1wx3oQ`,
SHA-256 `a93feba6505f082a1fbed4864180e35f451eb52763d03ac412529359caf5479d`.
Spark vLLM health returned HTTP 200.
