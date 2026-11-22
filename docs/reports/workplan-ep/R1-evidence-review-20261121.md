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

## Host window and candidate join

The exact run windows were 223, 224 and 216 seconds, with two
interior timestamps each. Across the 12 records, available memory
ranged from 71.254 to 71.775 GiB and one-minute load from 1.21 to
3.05. Five vmstat deltas show 90–95% idle and zero I/O wait. Two of
those deltas record swap-in. The recheck excludes the since-boot
vmstat row. One inspection lacks image and PID-limit fields, which
stay unavailable in the report.

Run `bash runs/r1-quiet-join-current.9LKPhZ/rehearse.sh` from the
checkout. It verifies the test identity and archived source manifest,
joins the pinned host records to the test windows, and rejects a
repinned inspection from another run. The host result SHA-256 is
`3739833c721631e79766deb387fa081229e3f0459681f5994501701102abdd90`.
These spot samples support a coordinator disposition. They leave
continuous host activity and formal quiet-host qualification unknown.

Independent worktree readback at `be73a3b` found 29 byte differences
against the three-pass archive and 27 against the later one-pass
patch. The 41 additional lab test modules belong to lab discovery.
The exact path evidence is in
`runs/r1-worktree-acceptance-review.Eq9fui/result.json`. The
coordinator and reviewers still need to nominate the exact candidate
and review the pinned module scope.

The inspection captured container IDs and timestamps. A separate
command captured container names and timestamps. A fresh test digest
with two inspection IDs exchanged still validates their time
windows. A future capture needs both ID and name in the same
inspection record to verify that pairing. The original pinned
samples retain their original IDs.

## Public Board work receipts

The direct projection of committed Board posts trusted the
embedded actor and read pointer. On a synthetic Board with no
read or claim, a fabricated receipt earned one passing task when
passed directly to the scorer.

The isolated adjudicator checks the pinned plan and Board chain,
the earlier same-worker read, committed source, held claim, and
exact observed operand before scoring. It rejected freshly
rehashed fabricated reads, crossed actors, absent claims, late
receipts, and answers that ignored a perturbed operand.

`bash runs/r1-board-work-audit.Aj13es/verify.sh` passed 14 tests.
First and final scores were 0 and 3 for the early error, and 1
and 3 for the late error. The one-round prefix kept its first
score of 1 and left the final score unavailable. The setup-only
prefix left both unavailable. The historical public archive
reproduced byte for byte. This replay covers deterministic public
Board evidence. Protected actor and observer custody are separate.

## Fresh joined CPU container identity

Two serial CPU fixture runs used the pinned night-loop patch source.
Both passed the same ten focused tests. Each retained the scheduled
container name, full create ID, and a single Docker inspection with
both name and ID. The verifier joins those records to the attachment
exit, exact removal, independent absence query, and UTC host window.
Both containers used the pinned image, one CPU, 1 GiB RAM, a read-only
root, disabled networking, and no GPU devices.

A copy with only the two inspection IDs exchanged was independently
rehashable and retained the original names and time windows. The
detached verifier refused it with exit 2. Reproduce the retained replay
from `runs/r1-joined-container-proof.Ytq6pf` with:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B verify.py capture index.json \
  --index-sha256 5350c445219d83174ab76ba65deab72fd753f41c2d0c8ad694a1b11c6cab7194
```

The replay report SHA-256 is
`fba1b3618fefcf462f8a7290957e55ca30e6b8674faeb7d462cdc39f9df7bfb4`.
These fixture captures establish the new identity join. The earlier
full-suite receipts retain their original captured fields. Candidate
nomination, quiet-host qualification, fresh per-module Opus review,
and the independent bench verdict remain open.

## Candidate nomination and remaining full runs

The Coordinator can nominate the patched candidate
`ee8237e5f288cb4f8d1a08453589d5e921cec2443f084d53b31519515a66689e`
after the protected N2 and independent verifier-mutant scope review.
Both archived candidates list 351 files. Their manifests differ only
in `src/murmuration/night.py` and `tests/test_night.py`.

| Evidence | Earlier candidate | Patched candidate |
| --- | --- | --- |
| Archived full runs with exit 0 | Three runs of 783 tests, one recorded skip per run | One run of 785 tests, one recorded skip |
| Fresh focused identity checks | Unavailable | Two runs of ten tests |
| Formal quiet-host qualification | Pending | Pending |
| Independent bench acceptance | Pending | Pending |

The full-suite gate requires three qualifying runs against one nominated
candidate. If the Coordinator and independent reviewer qualify the patched
candidate's retained full run, two full runs remain. Otherwise, three
qualifying runs remain. If the nominated source changes, bind all counted
runs to the resulting candidate. The fresh focused runs establish identity
for their own scope. The protected N2 carrier evidence, independent
verifier-mutant review, and fresh per-module and final verdicts remain
required.

From the repository root, verify the exact archived receipts and replay
the candidate comparison.

```bash
sha256sum -c runs/r1-nomination-ready.w0D3vn/evidence.sha256
python3 -B runs/r1-nomination-ready.w0D3vn/replay.py | cmp - runs/r1-nomination-ready.w0D3vn/report.json
```

## Public sibling-review parity on the patched candidate

A second reviewer executed the same archived Python and Lean predicates
over 360 normalized public four-worker states. The state grid varies
claim ownership, reviewer identity, task and worker matching, timing,
and a second review. The predicates and independent per-state
expectations agreed on all 360 states, with 63 allowed and 297 rejected.
The replay rechecks all 351 archived files and their modes.

```bash
bash runs/r1-public-sibling-grid.mgt1Uk/verify.sh
```

The ordered verdict digest is
`3e328675e2eeeaf04e224c41de50a804ec22c4f0a61a80239831a11fdc13e8ac`.
This result supports the public predicate review for candidate nomination.
Protected N2 still needs its independently sealed rule and carrier
evidence. The nomination, quiet-host qualification, and full-bench
verdict remain pending.
