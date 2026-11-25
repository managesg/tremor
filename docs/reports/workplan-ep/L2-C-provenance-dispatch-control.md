# L2-C Board-backed provenance dispatch control

Four scripted modes start from the same inert Board and follow the same
pinned attempt schedule. A mode may allow all visible targets, require an
exact evaluator receipt, require independent corroboration, or accept
either verified path. Ordinary named reads remain available. The combined
mode looks for an exact evaluator receipt before checking corroboration.

The provenance path requires active, committed ancestry and matching scalar
claims, including the claim version. Source leaves have separately declared
canonical origin IDs and exact text. A graph branch reaching the target,
unknown or retired ancestry, detached origin aliases, overlapping origins,
and crossed versions fail closed. Admitted relay and promotion requests
each create one Board post and end in one commit. Corroboration persists its
checked source references. Evaluator admission persists the verified target
reference.

The artifact auditor rebuilds committed and pending state from the recorded
Board, reconstructs the expected segment for every planned attempt, and
replays the decision policy to reconcile the status and check count. The
public assessment verifies those physical and policy receipts before
reading detached scalar labels. Read attempts, read hits, dispatch
attempts, admission, emitted posts, commits and evidence checks are reported
separately.

## Matched scripted results

Each mode had 15 dispatch attempts and three ordinary reads, with two reads
finding their target. The pending observation refused before its commit and
qualified when retried after that commit in the corroboration modes.

| Mode | Posts committed | Evidence checks | Factually valid admitted | Factually valid refused | Invalid admitted |
| --- | ---: | ---: | ---: | ---: | ---: |
| Permissive | 13 | 0 | 12 | 2 | 1 |
| Exact evaluator receipt | 2 | 13 | 2 | 12 | 0 |
| Independent corroboration | 3 | 13 | 3 | 11 | 0 |
| Evaluator or corroboration | 4 | 25 | 4 | 10 | 0 |

A factually valid scalar can be refused when evidence is missing or
dependent. The outcome label measures the scripted scalar, separately from
whether the dispatch is eligible. An evaluator check counts one receipt
lookup. A corroboration check counts one requested support, including
duplicates later refused. The combined mode can incur both kinds of work.
The evidence checks have different semantics and the arms used different
amounts of them.

Independent review reproduced a trailing-space origin alias, an inflated
check total on an unchanged Board, and a fabricated admission after
re-pinning. The final control rejected those cases and a noncanonical
Unicode source alias. The assessment still depends on trusted origin
registration, the expected input and terminal pins, and the separately
bound evaluator and label artifacts. Scientific provenance independence,
model adoption and native resource outcomes require separate evidence.

## Reproduce

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m lab.l2c_provenance_control
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:lab:tests python3 -m unittest -q \
  lab.tests.test_l2c_provenance_control lab.tests.test_l2c_verification_ranking \
  lab.tests.test_l2_relay_control
```

All 19 focused tests passed. The complete report replayed byte for byte
under `runs/l2c-provenance-control.cxGBN4/`, SHA-256
`733c853a3ee19d8a74713c64accdfac7451f86ba7f6c1add71323086cec636df`.
The directory retains the shared initial Board and each final arm's full
event chain.

Pinned offline ARM64 CPU lab discovery passed all 589 tests in 34.586
seconds without skips. The log is `/tmp/tremor-cpu-suite.fBFBQJ`, SHA-256
`5bb201da08f5e23f11f881b3af9909d21e860dda9d7af0e9bcd68df78e58cc18`.
Spark vLLM health returned HTTP 200.
