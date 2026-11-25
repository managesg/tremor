# L2-C matched verification share on Board dispatch

Five complete rankings are frozen once. The direct-relay, out-degree,
named-retrieval, recency and seeded random comparators each select a prefix
of their own fixed order at zero through four checks. The random arm uses
one full seeded permutation. The two reference conditions keep the same
Boards, target bindings, opportunity identities and factual labels. They
differ only in the availability of the evaluator reference for one target.

Each of the 50 cells ran four successful ordinary reads and eight scheduled
dispatch attempts. A cell received one evaluator check per selected target
and two cached lookups per selected target. The audit reconciles the full
five-arm grid and checks status and factual category against an independently
reconstructed expected target inventory. Physical receipts, terminal Board
heads, short and full selection orders, and settled check costs remain
available for every cell.

## Exact scripted point comparisons

The table counts how many targets each order first had to check for its
invalid-admission count to match its four-check reference. These are
point comparisons at the five observed integer shares, including zero.

| Ranking | First matching check count, unavailable | First matching check count, restored |
| --- | ---: | ---: |
| Direct relays | 1 | 1 |
| Out-degree | 2 | 2 |
| Named retrievals | 2 | 2 |
| Recency | 4 | 4 |
| Seeded random order | 4 | 4 |

With one unavailable reference, all four checks block the two invalid
dispatches and also withhold two factually valid attempts. Both effects are
visible. Restoring the reference reinstates those two valid attempts
in exactly 13 paired cells. The other 12 pairs have byte-identical Board
histories. The locked order, purchased checks, cached lookups and invalid
admission counts stay identical in every pair.

Uniform selection over all finite permutations has an exact expectation
under these validated target increments. At one check its expected invalid
admission count is 3/2 in both conditions. Its expected valid refusal count
is 1/2 with the reference unavailable and zero when restored. The seeded
random path and the finite expectation are reported separately. There is
no estimated native adoption curve or scientific equivalence decision.
Independent reference custody, measured model behavior, confidence and
dose rules, and native admission remain open.

Independent review reproduced coherent aggregate relabeling of mismatches,
redistribution across factual labels, erased read hits and incomplete arm
coverage. The final audit rejects those cases against the separate input
and label inventories. The previous single-budget artifact also replayed
byte for byte.

## Reproduce

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m lab.l2c_share_response
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:lab:tests python3 -m unittest -q \
  lab.tests.test_l2c_share_response lab.tests.test_l2c_ranked_dispatch \
  lab.tests.test_l2c_provenance_control
```

All 20 focused tests passed. The report and 50 separate Board and receipt
pairs are retained under `runs/l2c-share-response.Pz0iQz/`. The report
reproduced byte for byte, SHA-256
`515aede07ac27efac27d6cc2b3cbebe00188603f45531955c8a2734cb8864fdd`.

Pinned offline ARM64 CPU lab discovery passed all 602 tests in 35.243
seconds without skips. Its log is `/tmp/tremor-cpu-suite.nbIGyW`, SHA-256
`31f93201e2bddaeff1cb69dcdb37c5c46a6a583458e4d99578412ffd8ee91ce3`.
Spark vLLM health returned HTTP 200.
