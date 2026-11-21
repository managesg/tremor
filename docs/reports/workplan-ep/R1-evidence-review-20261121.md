# R1 evidence review on Spark

The independent technical review examined the exact retained 351-file
candidate and its three serial suites. The source manifest SHA-256 is
`73c4f429748e3c90b065095d46c799c8c5bce0cd5fe83ade22da2c55f2141ef6`.
All listed hashes and modes matched. Each suite exited zero with 783
identical ordered test identities and the same Torch-dependent skip,
`test_runner.RunnerTests.test_local_hf_fails_cleanly`. The archive's
`verified-full-suite.json` reproduced byte for byte at
`539030c1f1024f41d76417d17f65fc63ac6536fd3427826ca33d288130270f86`.

The retained host samples support low observed contention. Twelve
samples showed 71.254–71.775 GiB available memory and one-minute load
between 1.21 and 3.05. Five sampled CPU intervals were 90–95% idle
with zero I/O wait. Each test container had a two-CPU limit, 4 GiB RAM,
no network and no attached GPU devices. The record covers sampled
intervals. Formal quiet-host qualification remains unset.

## Astra adversarial findings

The scripted episode and L5 matrix construct action answers using
`alloc.oracle_log`, which copies exact answers from the task fixture.
This tests the scoring path. It leaves participant isolation from
hidden references unverified. The public L5 grader also reconstructs
`alloc.gen(0)` and requires reference equality with that public example.
It cannot accept a distinct held-out N2 reference in that mode. The
dispatch census explicitly records `scientific_n2_frozen=false`.

The proposal still requires protected N2 and independent verifier-mutant
evidence, fresh per-module Opus review, an adversarial verifier ACCEPT,
and quiet-host qualification. The archived acceptance fields remain
unset. The Astra review supplies an independent technical finding.

## Night-loop archive isolation

A rewrite callback changed the archived input note's text and nested
provenance. The post-callback read charge fell from three words to one.
A consumer could also mutate provenance through the placebo output.

Local commit `154e280` isolates mutable store data at write, replay and
verifier boundaries. It measures input tokens before callbacks. The
regression reproduced the original three-word read charge and preserved
source links after a mutating callback and after consumer edits. Twenty-eight
focused tests passed. The existing memory and adaptive replay bytes
remained identical. Local evidence is under
`runs/r1-night-store-isolation.Ldw3Rp`.

[Phase R1 workplan](../../WORKPLAN-RESIDENCY-V3.md#phase-r1-build-the-bench-extensions-cpu-only-usd-0) · [R1 source review and run history](R1-current-snapshot.md)

## Full-suite regression check for the night-loop patch

A separate 351-file candidate overlays only the two night-loop paths on
the archived candidate. Its source manifest is
`ee8237e5f288cb4f8d1a08453589d5e921cec2443f084d53b31519515a66689e`.
An isolated Spark CPU container ran the full repository suite in 231.597
seconds. Exit code was zero with 785 tests and the same single skip.
The original 783 identities retained their order, and the two additional
identities are the new night-loop regressions. The read-only runtime had
no attached GPU devices. All source hashes and modes matched after exit,
and vLLM retained its running engine process.

The suite and verification receipt are under
`runs/r1-night-patched-suite.ut50XT`. Receipt SHA-256
`b5e7f40cda8775760eb058d748cf1b9f01e3a6cd5b3abe606f7c82157372394a`.
This is one full-suite regression pass on the patched candidate. The three
earlier complete runs apply to the original candidate.

## L5 scripted phase evidence

The separate [phase auditor](../../../lab/l5_matrix_phase_scores.py)
now binds work order to the exact public scripted oracle sequence.
Previously, swapping both phase and round labels in a repinned work
record could move work into the opening score. A second reproduced
mutation could replace integer answers with equal-valued floats and
change opening scores. The auditor checks both answer records for exact
integer type and requires the ordinal's expected phase and committed
round.

The 200-arm replay remained byte-identical at
`ec1a489a3a359878d3bca342aaffe1de68dd3b3b913177bc81f1cb4d5155ff9b`.
Fifteen focused tests passed from the pinned closure
`runs/r1-night-store-isolation.Ldw3Rp/phase-source-final`.
Its manifest digest is
`5dc170a703fe0d7fdcaea8870f20c323dd1d0fb5f056ee62a9ba25073dd5aaa2`.
Stopped runs still leave phase scores unavailable. Legacy Board records
omit admitted work events, so the check establishes deterministic
scripted chronology. Protected N2 needs its own authenticated evidence.

## Independent public scorer mutation check

The retained R1 candidate and the current checkout have identical
`alloc.py` and `alloc2.py` bytes. An independent reviewer compiled twelve
behavioral mutations of `alloc.score`, one at a time, in memory. The
public arithmetic corpus detected all twelve and matched all fourteen
cases with the unmodified scorer. Clean and reordered work both scored
1.0. The audit stores each mutation and its expected and observed
outputs. It runs with the tracked scorer and corpus files.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python3 -B -m lab.r1_independent_verifier_mutation_audit
```

The result reproduced byte for byte from a clean source closure.
Result SHA-256
`fdfd02889d437f2d1c71a26457561ab1dfcf580c2a9dbffc07a74cb2bed950dc`.
The one case skipped in the archived suites ran separately from the
same pinned source on Spark without Torch and passed. The historical
suite summaries retain their original skip counts. Protected N2
verification, per-module review, and quiet-host disposition remain open.
