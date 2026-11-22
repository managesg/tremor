# Scripted coordination with matched worker traversal

The original authority-by-access instrument let the rotating lead change
worker traversal as well as assignment authority. At a 19-unit cap,
rotating traversal let the complementary fixture verify `join`, `left`
and `right`. With fixed traversal the same rotating-lead policy and
shared access verified `left` and `right`. The sequential fixture at 16
units likewise went from `middle` and `root` to `root`.

The [matched-traversal runner](../../../lab/topology_matched_traversal.py)
crosses four assignment policies with two evidence access modes. Each
block uses the same planned worker order in all arms and all rounds.
The public fixtures cover all six orders at 16, 19 and 32 synthetic
units, for 54 blocks and 432 arms. The rotating lead still changes each
round. The verifier checked the executed traversal prefixes and confirmed
240 actual budget stops.

| Cap per arm | Arms | Same utility as self-assignment at the same access | One fewer verified task |
| --- | ---: | ---: | ---: |
| 16 | 144 | 115 | 29 |
| 19 | 144 | 124 | 20 |
| 32 | 144 | 144 | 0 |

These counts compare implemented policies at equal ceilings. Planning,
claims and handoffs consume budget. In 72 of 108 fixture, budget, order
and access groups, at least two policies read different realized
sequences. The control therefore matches planned traversal while
preserving the policy-specific work and its cost. The counts come from
deterministic public fixtures and provide no held-out model estimate.

A separate audit replayed the historical fixed-share independent control.
The per-fixture verified unions were `left/right`, `backup/common/separate`
and `root`. The audit rejects an altered root answer even with a
matching new file digest. It independently verifies integrity and replay
against the same public scripted scorer. A native run still needs a
protected independent assessment and resource receipts.

## Reproduce

The pinned source closure is
`runs/topology-matched-traversal.cFjf5f/source`, manifest SHA-256
`9993c62a0ae310bbf0b8cbdb7339cf24e643f77c035752291bce5944ddcaaaf4`.
Run the following from that directory.

```bash
sha256sum -c source.sha256
python3 -B -m unittest -q lab.tests.test_topology_matched_traversal lab.tests.test_topology
python3 -B -m lab.topology_matched_traversal
```

Nine tests passed in the isolated closure. Its replay matched the archived
report SHA-256
`6527fd83df48389fb1a15398955fc910b0985898a9035e22e955905145a1cf12`.
The original crossed trace replay remained byte-identical at
`efc70772f5813e30379a640b8b99612023e99a5e7296e7b4436e8710ba8f4699`.
The fixed-share audit and its six focused tests ran on the worktree.
The audit receipt is in `runs/topology-independent-audit.uM8V7P/audit.json`,
SHA-256 `2906c1ad437927dae16fbbe9ea79ab46929294e229667b3773834eb6bb4913c5`.

## Read opportunities and the separate-worker baseline

Across the 432 public arms, own access yielded 1,611 read opportunities
and zero foreign receipt exposures. Shared access yielded 1,567 read
opportunities, with 1,280 foreign receipt exposures and 207 foreign
receipts used as work inputs. These are occurrences across all reads,
including repeated exposure to a receipt. The script resolves each
pointer to a previously accepted submission. A fresh report digest
did not make a foreign receipt in an own-access trace valid.

Among 648 comparisons between policies at the same access setting,
350 reached different read slots and 62 saw different receipts at a
slot both reached. Equal planned traversal and equal caps estimate
the total policy effect, including which exchanges the policy can
afford. A direct authority contrast needs a separately frozen common
delivery schedule. The public traces count requests and receipts.
Actual delivered context and token use require host observation.

The archived self-assignment arm uses a pooled budget. The separate
control assigns each worker its own cap and reviews its sealed output
before merging. The per-block comparison reserves three units for
reviews and one for merging. The remaining shares are 4/4/4, 5/5/5
and 10/9/9 at caps 16, 19 and 32. The first worker in the balanced
traversal receives the extra unit at cap 32. Testing all recipients
and orders at that cap produced the same union and cost per fixture.

The separate control's union differed from pooled own-access
self-assignment in 12 redundant-fixture blocks at caps 16 and 19.
There, the pooled arm verified `backup`, `common` and `separate`.
The separate union contained `common` and `separate`. All 432 arms
were re-reviewed using the same detached public answer inventory.
Against the separate union, 209 scored higher and 223 tied.

Run `bash runs/topology-block-union.w3ilis/verify.sh` from the repo
root to reproduce both historical archives and the blockwise check.
Eleven tests passed. The block report SHA-256 is
`def1536c1759d4403946c974b9be96385481739312d1fcebc139891b86a2f511`.
The independent exposure recount and refusal evidence are in
`runs/topology-exposure-current.GctymJ`. Protected acceptance
still needs the frozen comparison, actual host delivery records,
independent scoring custody and realized resource accounting.

## Combining evidence from different workers

A replay of the 432 public arms followed accepted work back to the
prerequisite receipts delivered to each worker. It joined both baselines
by fixture, resource ceiling and planned traversal. In 121 arms, an
accepted task used another worker's evidence and the arm verified more
tasks than both pooled own-access work and the fixed-share union. Of
these arms, 56 had a task that directly used evidence from at least two
other workers. Another 30 reached two other workers through a chain of
prior work without such a direct combination.

Another 88 arms beat only the fixed-share union and used no foreign
evidence. For example, at 16 units the shared-access pooled condition
completed `join` by giving worker `c` accepted `left` and `right` receipts
from workers `a` and `b`. Neither baseline completed `join` in that block.
Track these evidence paths alongside the two baseline differences in the
held-out comparison. The public replay describes engineered dependencies
and supplies no causal or held-out model estimate.
[Reproduction and scope](../../../runs/m6-complementary-lineage.odFNO3/OWNER.md)

## Realized cost and the two baselines

A separate audit recomputed event costs and rejoined both baselines within
each of the 54 fixture, planned traversal and ceiling blocks. It compared
verified task sets as well as counts.

| Observation | Scripted arms | Blocks represented |
| --- | ---: | ---: |
| More verified tasks than both baselines | 121 | 36 |
| More tasks at no higher realized cost than either baseline | 41 | 26 |
| More tasks at exactly the realized cost of both baselines | 25 | 12 |
| Strict improvement against both on cost and verified task-set inclusion | 47 | 26 |

All 41 gains without a higher cost preserved both baseline task sets. The
six additional improvements verified the same tasks as both baselines
and spent 15 units versus 16. These were the shared peer arms for the
six traversals of the complementary fixture at the 16-unit ceiling.
The redundant fixture had no count gain against both baselines.

The equal-ceiling design is primary. The equal-realized-cost slice is
descriptive because realized spending depends on the policy. These
operation units do not measure model tokens or native cost. Review the
[proof and reproduction packet](../../../runs/m6-realized-cost-frontier.3kIqzZ/OWNER.md).

## Fixed-share arithmetic evidence

The independent fixed-share comparator now requires exact integers in
the full scoring reference and in worker observations. A Boolean
`True` and the float `1.0` previously counted as the integer answer
`1`. The regression distinguishes those inputs from the valid integer
mismatch `0`. Forty focused tests pass and the archived fixed-share
report reproduces byte for byte.
[Evidence packet](../../../runs/m6-fixed-share-arithmetic.j3FJO8/OWNER.md)
