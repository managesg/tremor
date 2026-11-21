# Grover coordination replay

The CPU development replay runs the three Grover regimes through the existing coordinator.
It crosses four policies with own or shared evidence, fixes worker traversal order in all arms,
and charges the same per-event prices and 32-unit ceiling. A rotating lead still pays for its
handoffs. The proposer receives the local question and payloads of exactly the required earlier
receipts. The private verifier separately checks stage answers and source-shard content. The
coordinator checks the receipt event IDs, visibility, and round order before scoring. A verified
no-hit predecessor is a present receipt and can release its registered fallback.

## Observed development cases

All four policies had the same distinct verified stage count at a given access setting. The
independent-plus-own union is the emergence baseline. The independent-plus-shared arm controls
for evidence access when comparing assignment policies. Shard work, verification, and other
operations are charged and retained in the trace. Only verified Grover stages count as utility.

| Public development case | Own stage count across policies | Shared stage count across policies | Realized cost across the eight cells |
| --- | ---: | ---: | ---: |
| Complementary, seed 0 | 0 | 1 | 17–25 |
| Complementary, seed 9 | 0 | 1 | 17–25 |
| Redundant, seed 0 | 2 | 2 | 16–24 |
| Sequential, seed 0 | 1 | 3 | 18–27 |

The two complementary cases include a verified no-hit and a verified hit. Shared evidence
allows stages with cross-worker requirements in both that regime and the sequential case.
At this budget, changing assignment policy within either access setting gave no additional
verified stages on these inputs. The results concern scripted fixtures. The post-EP-1 model
transfer still needs its protected seeds, approved allocation, and frozen science protocol.
The fixed and rotating leads used the same deterministic planner and made identical assignments.
Rotation therefore added two handoff units per cell and supplies no comparison of lead-specific
decision quality. An independent reconstruction checked all 665 trace events, 77 verified work
items, and the per-state amplitude recurrence used to validate stage answers. A sweep of 992
lower-budget cells verified the spending ceiling, charged work and verification, and final merge.

## Reproduce

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m lab.quantum.topology_transfer
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:lab:tests python3 -m unittest -v \
    lab.tests.test_topology_transfer lab.tests.test_topology lab.tests.test_advisor_controls
```

The 32-cell JSON replay reproduced SHA-256
`6ce893d3c05d06df563dde15086bc3764e1e1b0efdcceebb650b303210115bdc`. Both historical arithmetic
topology traces reproduced byte for byte. [Coordinator](../../../lab/topology.py) · [Adapter](../../../lab/quantum/topology_transfer.py) · [Tests](../../../lab/tests/test_topology_transfer.py)

The separate [serialized trace auditor](../../../lab/quantum/topology_audit.py) checks exact
stage answers, receipt visibility and chronology, known actor labels, event costs, directed
handoffs and the derived distinct stage union. It accepts a source digest from an independent
record. The synthetic actor labels carry no identity authentication. The audited full envelope
and budgets 1–31 together cover 1,024 cells. The verified summary SHA-256 is
`55c770e621a3402a4c5c715a0d1dc24205af59abbbcbbda4bf9bae62cf3da285`.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m lab.quantum.topology_audit \
  /path/to/grover-topology-scripted-trace.json \
  --expected-sha256 6ce893d3c05d06df563dde15086bc3764e1e1b0efdcceebb650b303210115bdc
```

## Planner input and serialized assignment verification

The scripted coordinator now computes readiness before calling the
planner. The planner receives ordered task IDs and immutable per-worker
sets of ready task IDs. The coordinator retains the worker observations
and full receipt payloads. A spy test confirms that the planner receives
no shard contents, answer payloads, or worker views under either access
condition.

The serialized auditor reconstructs expected assignments independently
from public task order, eligible workers, and earlier visible receipt
IDs. It rejects extra planner fields, unknown workers in assignments,
and assignments with missing prerequisites even when the supplied
digest matches the modified trace.

The pinned local source closure is
`runs/grover-planner-projection.XwHcCX/source`, manifest SHA-256
`22e3ed56113cfc8c430055560a8d71bb4a50fcc8d1d3fffaafff358ac5b49295`.
Twenty-six isolated tests passed. Across caps 1 through 32, the auditor
replayed 1,024 public arms and 1,038 planner events. Sweep receipt
`ab5dd8a1f6b371ca1994b3f3411bb0b1e44d883bdd34ca74a918aa8ddf2f59d1`.
The default arithmetic, crossed arithmetic, Grover trace and Grover audit
all matched their archived bytes.

The evidence covers public scripted tasks and in-process information
flow. Protected transfer still requires the frozen protocol, independent
custody, EP-1 dependency and exact native admission.

## Mixed roles and complete dispatch

A stage whose solvers hold only partial marks needs separate
publishing and solving roles. The prior projection discarded the
publisher role for a worker who could also solve. It also omitted
shard dependencies when each solver held some local marks, even
when neither held the full set.

The projection now separates local mark publishing from solving
and gives the solve task only the source IDs and threshold inputs.
The solver uses the verified shards from its allowed access view.
A stage whose eligible solvers already hold complete redundant
sets keeps direct questions. In two public mixed-role controls,
all eight shared cells found the exact hit at iteration 1 with
probability 1. The eight own-access cells left the join unverified.

The verifier checks independently computed rational answers,
receipts and accounting. It also checks the complete scheduled
dispatch for public fixture cases. Mutations omitted the verified
no-hit confirmation and the later fallback solve, either by
closing early or by keeping all nine reads and dropping the work.
Both are now rejected. The closed event schema also refuses extra
worker input fields.

The integrated suite passed 44 tests, the cap sweep verified
1,024 cells, and the original 32-cell trace and audit matched
byte for byte. Reproduction artifacts are in
`runs/grover-projection-current.OhP1lP`. Its separate QGrid run
used a network-disabled, read-only CPU container and found zero
disagreements across 329 statevectors from 65 cases. These are
public instrument results. Protected fixtures and a host-observed
delivery and scoring record require independent custody and admission.

## Synthetic custody opening

Run `bash runs/grover-custody-current.JX6TFI/rehearse.sh` from
the checkout. The script uses invented inventory, opening and
receipt material. It reproduced the aggregate report byte for byte
and refused a crossed planner field with CLI exit 2.

The commitment binds canonical bytes under a Grover-specific domain
and a 32-byte opening. The verifier checks the caller's independent
receipt digest, protocol and split digests, and custodian ID. It
rebuilds worker projections and verifier-side task eligibility.
Static eligibility records which worker may perform each task.
Runtime readiness still depends on observed receipt release.

The rehearsal checks exact rational branches and rejects relabeled
duplicate blocks using ordered prerequisites, source incidence,
solver slots, thresholds and probability traces. Equal traces can
remain distinct when their source or dependency structure differs.
The synthetic inventory has one block with eight planned arms and
one stage each in the hit, no-hit and equality branches. The report
contains aggregate counts and the commitment. The independently
appointed custodian, protected split rules and authenticated
pre-execution receipt are still required for protected assessment.

## Observed release rehearsal

Run `bash runs/grover-release-current.AYSM67/rehearse.sh` from the
repository root. The verifier takes the audited public trace and
two separate pins for the scheduled scope and the observer tape. It
checks qualified receipt identity, result type, next-round
availability, allowed visibility, and the exact receipts used by
each work attempt.

The no-hit control used the fallback once. The hit control used
two exact predecessor probabilities and zero fallbacks. The
own-access control verified only the first stage and issued no
no-hit receipt. At cap 21, the no-hit control issued the receipt
and stopped before the final work slot. The prefix's actual
fallback count is zero and its complete-schedule count is
unavailable. A late release failed the CLI with exit 2.

One independent check counted 40 distinct verified stages and
77 verified work receipts across the public archive. The full
readback joined the same 32 arms to distinct synthetic observer
scopes and retained 288 reads and four fallback uses. The synthetic
tapes exercise the evidence contract. Actual actor deliveries and
observer identity still need a protected independent capture.

## Cap label verification

The cap sweep now requires each trace arm's integer budget to equal
the cap requested by the sweep. The regression supplies the genuine
cap-32 trace to the cap-26 request. The earlier verifier accepted
that trace as cap 26. The fixed verifier refuses it.

The genuine 1,024-cell sweep reproduces the archived report byte for
byte. Cap 27 remains the first cap with the exact full-cap stage unions
in this public fixture. It is measured in abstract scripted cost units.
All 27 focused quantum tests passed. Red and green logs and the
reproduced report are in `runs/grover-cap-label.ntHuTI`.

An independent integer gate calculation checked 645 normalized trace
points up to 10 qubits and the full 128-iteration bound. The scorer
matched all 11 rational threshold decisions. In three fixtures,
thresholds (2^{-120}) above and below the exact maximum had the same
float representation, while the exact decisions distinguished hit from
no-hit. The maximum floating gate deviation was (4.44 \times 10^{-13}).
The verifying command and receipt are under
`runs/grover-exact-boundary.s0ClQc`. These are public mathematical
fixtures for the transfer scorer.
