# L4-C comparison with versioned sources and detached scoring

The two-night development fixture compares verified replay, evaluator-gated
writes, and search on the same ordered arrivals, task opportunities, and active
source versions. Each arm receives eight abstract operation units per night.
The producer records each source check, rewrite check, memory lookup, and
search attempt where applicable. A failed retrieval consumes one unit. A
memory gate checks its maximum whole-gate cost before starting. Unused
allowance stays visible. Version-one source bytes remain in the raw history
when version two takes effect.

After execution, a separate verifier reconstructs every expected operation,
submission and resident memory state from the supplied plan. The plan digest binds the full task inventory and candidate order, including unused candidates. A separate
ledger recounts charges and cap balances. A terminal scorer compares responses
and resident claims against detached close-night labels. Replacing a label
changes the scored result and preserves the execution bytes. The assay
distinguishes wrong answers, unanswered work and missing labels.

## Observed development results

Both memory arms rejected the unsupported new note on night one. After the
valve source changed on night two, verified replay withdrew the old note
without a replacement and left that query unanswered. Evaluator-gated write
retained the old note and returned the stale answer. Search retrieved the
current source. When the source stayed unchanged, all three arms tied on
four passing tasks.

| Case | Arm | Two-night units used | Passing tasks | Units per pass | Night-two false resident notes |
| --- | --- | ---: | ---: | ---: | --- |
| Source revision | Replay | 12 | 3 | 4 | 0 of 1 |
| Source revision | Evaluator-gated write | 7 | 3 | 7/3 | 1 of 2 |
| Source revision | Search | 6 | 4 | 3/2 | Empty resident store |
| Unchanged source | Replay | 13 | 4 | 13/4 | 0 of 2 |
| Unchanged source | Evaluator-gated write | 7 | 4 | 7/4 | 0 of 2 |
| Unchanged source | Search | 6 | 4 | 3/2 | Empty resident store |

A one-unit cap leaves only the first unsuccessful search in each night.
Total spend remains two while cost per passing task is undefined. No resident
notes leaves the false-share denominator undefined. A submitted answer with
a missing label withholds cost per pass, and a resident note with missing
truth withholds false share.

The same caps permit different realized operation counts. Scientific token
parity, trusted plan and label custody, the reference for the 1.5× cost
rule, and native measurements at the two strongest observed compression
settings remain separate gates.

## Checks and reproduction

The initial meter accepted a deleted receipt when its totals were recomputed.
The integrated verifier rejects the deletion, a fabricated favorable submission,
a changed source schedule, and mutated resident provenance. Changing an unused candidate now also breaks the archived plan pin. Independent review
also checked both revision cases at caps zero through twelve, including JSON
round-trip parity of all 26 executions.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m lab.l4c_scripted_comparison
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:lab:tests python3 -m unittest -v \
  lab.tests.test_l4c_scripted_comparison lab.tests.test_l4_adaptive_replay_control \
  lab.tests.test_memory_replay
```

All 22 focused tests passed. The CLI report reproduced byte for byte at
`runs/l4c-matched-comparison.X0NdTG/report.json`, SHA-256
`8db703232273f5179b65fb0fed97d506bb92490a444b72a85516df6f24d4cbfb`.

The pinned offline ARM64 CPU lab discovery passed 552 tests in 34.656
seconds with no skips. Its log is `/tmp/tremor-cpu-suite.qpl9ov`, SHA-256
`9218462e9787232e336f4540cce89e30549bfd85dd97a88dc60144b4e50f4217`.
Spark vLLM health returned HTTP 200.
