# L2 paper-ledger reference custody

A synthetic probe supplied a paper ledger that said `blue` while the independent
adoption scorer still treated `green` as correct. The generation bridge carried
and recorded the supplied ledger bytes. The contradiction mattered at the
fixture boundary, where the runner supplied `reference_text`.

The offline custody check verifies one reviewed case ID against two separately
pinned files. The reference manifest maps the case to an exact source path and
SHA-256. The evaluator inventory maps the same case to its expected marker.
The check reads the referenced file once and compares the exact bytes with
`Paper ledger marker: <marker>` in the current fixture format. It also checks
that the pinned marker agrees with the existing adoption scorer. A contradictory
source fails even if its own digest and the manifest digest were refreshed.
Missing cases or files, a digest mismatch, a duplicate JSON key, or an indirect
file path also cause refusal.

| Record | Synthetic example |
| --- | --- |
| Reference manifest | `{"references":{"pair-01":{"path":"paper-ledger.txt","sha256":"<source digest>"}}}` |
| Independent evaluator inventory | `{"markers":{"pair-01":"green"}}` |
| Exact source file | `Paper ledger marker: green` with no trailing newline |

The trusted caller supplies the manifest and truth inventory digests from
their respective review records. It should use `VerifiedReference.text` for
both matched arms, so downstream code can pass the verified bytes without
reopening the file. The check is scoped to the existing scripted scorer and
record format. A live task-family scorer, trusted freeze records, a read-only
bundle, and wiring the check before the guarded worker are still pending.
This offline check makes no admission or scientific claim. [Generation and reference path](R3-local-decision-path.md) · [CPU adoption evidence](L2-adoption-scripted.md)

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests python3 -m unittest -v \
    lab.tests.test_l2_reference_custody lab.tests.test_r3_l2_generation \
    lab.tests.test_l2_adoption_control
```
