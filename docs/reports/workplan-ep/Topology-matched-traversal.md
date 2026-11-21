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
