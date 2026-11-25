# L4 measured loaded payload, retained episodes, and source support

The audit measures the UTF-8 text payloads loaded before and after one
consolidation boundary. It reports the exact fraction `after / before` and
keeps raw-episode retention separate, by count and by payload bytes. An empty
before payload leaves the fraction undefined. A nonempty before payload with
an empty after payload gives zero.

The paired snapshot binds note payloads, source/version history, and raw
episode identities to an externally supplied canonical SHA-256. A retained
episode must match its complete before record. A rewritten note must name
parents from the before snapshot, and its cited support must come from those
parents. The audit counts distinct source episode IDs whose source versions
are current in the supplied inventory at the cutoff. It also reports which
of those episodes remain available after pruning, and which cited episodes
are stale. Repeated observations of one source version must agree on the
source payload. Identifiers must use Unicode NFC.

## Observed development and archived counts

| Input | Loaded before and after | Loaded retained fraction | Raw retention |
| --- | --- | --- | --- |
| Pinned two-episode fixture | 40 → 12 bytes | 3/10 | 2 of 2 episodes, 24 of 24 bytes |
| Historical planted verified replay, night one | 26 → 12 bytes | 6/13 | Unknown |

Both source episodes in the new fixture were available at the cutoff and
retained afterward. In an independent pruning check, retaining zero, one, or
both episodes changed the available-after list while leaving the earlier
support count fixed. The other eleven archived nights had equal before and
after loaded payload bytes. The old trace replayed byte for byte at its
original SHA-256, including unchanged historical store and source history.
Its format leaves raw retention and promotion support unknown.

UTF-8 text bytes exclude serialization overhead and model tokens. Distinct
episode IDs measure recorded support. Independent corroboration and semantic
entailment require their own review and measurement. The scientific
compression index and strongest settings still need a tokenizer, rendering
policy, held-out chain custody and an approved measurement protocol.

## Reproduce

```bash
artifact=runs/l4-measured-compression.C7Csn1
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m lab.l4_measured_compression \
  --pair "$artifact/paired-snapshot.json" \
  --expected-sha256 15e0c789f2a16180345b7b38552ac6b340d416bdbbcadfca86fe243ae3a0d214
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m lab.l4_measured_compression \
  --archive runs/l4-memory-scripted/trace.json \
  --expected-sha256 067a0918fb97fd24bd86a8227952aeaf0a8a878c538038c485fcee39c9fbbe6d
```

The paired and historical reports reproduced byte for byte. Paired report
SHA-256 `73397910a7d3b18c08c958522ad9ed48815ef123707c5b6995c71d9b39ac16fc`.
Historical report SHA-256
`c83c0c1200e1e467c3c4f6a5a546b43833d351c23128e1ac50b21b48c40bd603`.

The focused compression, legacy replay and L4-C checks passed all 18 tests.
Pinned offline ARM64 CPU lab discovery passed all 559 tests in 37.664
seconds without skips. Its log is `/tmp/tremor-cpu-suite.IxtdEM`, SHA-256
`1fad6dc26f99a573817cdd06b01678826d2ed121ad6dc17fe0284d3d2fd828a5`.
Spark vLLM health returned HTTP 200.
