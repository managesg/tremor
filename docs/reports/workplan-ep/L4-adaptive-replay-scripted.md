# Scripted adaptive verified replay

The four-night control reuses the night loop in both arms. Every arriving or
retained note goes through an exact check against the current source prefix
before rewrite selection. A rewrite is checked separately against the same
source reference and retains its parent link. Source rejection removes the note
from the output. Rewrite rejection preserves an independently checked original.
The old store and every earlier night's record remain accessible.

## Decision and evidence

The reference arm uses fixture strength one. The adaptive arm starts there
and moves to zero only when both diagnostics increase in the latest two
comparable windows. The settings belong to this scripted fixture. The proposal's compression ladder remains uncalibrated.

The separately supplied clock specifies when each closed window may be used. The policy checks the two most recent eligible slots it consumes.
A window with availability on day three first becomes usable for the day-four
decision. Expected slot digests bind both dates, protocol, horizon, recovery
predicates, terminal state, relay endpoint, event count and nominated roots.
The retained Board log must match its completion anchor and contain the full
opening plant inventory. Recovery uses confirmed event time and is withheld
on an operational stop. Relay counts use the anchored first-generation meter.
A valid window with observed zero relays contributes zero. A missing mature
slot, missing relay receipt, no eligible roots or unconfirmed recovery is unknown.

The original review manufactured a rise by picking a low-count root in one
window and a high-count root in the next from the same anchored log. Requiring
the full opening-root inventory rejects that comparison. A separate test
relabels a future observation as an earlier eligible slot. Its digest now
fails the independently supplied slot pin.

## Observed results

The fixture saw confirmed recovery move from night zero to one and a
first-generation mean increase from zero to one on two roots. The adaptive
settings over four nights were `[1, 1, 1, 0]`. A declared alternative fourth-day
window held recovery and relay counts flat, producing `[1, 1, 1, 1]`.
The first three night records matched exactly. A future source change also
preserved those records and the fourth-day controller decision.

| Day-four accounting | Fixed | Adaptive |
| --- | ---: | ---: |
| Input note words | 15 | 15 |
| Source-admitted replay words | 12 | 12 |
| Original note checks | 5 | 5 |
| Words read for original checks | 15 | 15 |
| Proposed rewrite checks | 4 | 0 |
| Words read for rewrite checks | 12 | 0 |
| Contradictory notes dropped | 1 | 1 |

These are separate operation counts and whitespace word measurements.
Repeated views and reads can overlap. The counts supply no token-equivalence
or performance estimate. The fixture controls its observation clocks and
pins. Actual custody, the adaptive settings, measured compression,
evaluator-gated-write and search comparators, and native cost per passing task
remain open.

## Reproduce

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m lab.l4_adaptive_replay_policy
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:lab:tests python3 -m unittest -q \
  lab.tests.test_l4_adaptive_replay_control lab.tests.test_memory_replay \
  lab.tests.test_l4b_recovery lab.tests.test_l2_relay_control
```

All 28 focused tests passed. The report replayed byte for byte. The two
reports and the retained Board journals are in
`runs/l4-adaptive-replay.7cFtwz/`. Report SHA-256
`62413347a837c1fd532c74d54b68c04d19b1ee7604bc66f88e9ddc66d4eb9b6d`.
Alternative SHA-256
`b78d57a91fa322311e8a935731cf750423452877a6f9cef2cd0b8fda83e2efcb`.

The pinned offline ARM64 CPU lab discovery ran 544 tests in 33.725 seconds
with no skips. Its log is `/tmp/tremor-cpu-suite.8VI0HI`, SHA-256
`c35efdc1f94db9c6bd6e80f2e33bd2f11e05e84949aa574d9ede25f3678d1a43`.
An independent reviewer reran all 11 new focused tests and tried
reassigned roots, a moved slot, modified predicates, and crossed Board bytes.
The final implementation refused each case. Spark vLLM health returned HTTP 200.
