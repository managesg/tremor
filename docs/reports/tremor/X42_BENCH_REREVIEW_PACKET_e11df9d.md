# X42 Gate R1 bench re-review packet: e11df9d (supersedes d918428)

**Candidate:** commit `e11df9d5cdc73108ed045a5e61689d81411ad35c`, tree `1256d32715ede9f2882fa1530adceee5f374b550`, on the TREMOR research repo `/home/adelmar/SeaBridgeAI/murmuration`. Review this exact tree, through `git archive e11df9d`.

**Supersedes:** the `d918428` nomination (`msg_3f78bc730381`). `d918428` lacks row 157's episode v3, so row 157 would fail there. Every per-row instruction in `X42_BENCH_REREVIEW_PACKET_d918428.md` (sha256 `ff523102…`) still applies, with this exact candidate substituted, except row 157, which is restated below. That file stays the reference for rows 155, 158, 159, 162, 165, 167 and 169.

## What changed since d918428

An independent diff review returned ACCEPT. `git diff d918428 e11df9d` adds the following and touches no existing code, test or archive-derived file:

- **New code:** `lab/r1_contention_schedule.py`, `lab/r1_episode_v3.py`, `lab/r1_contention_readouts.py`, plus their tests.
- **New docs:**
  - the row-157 addendum (`5cabfe7`) and pin (`1d333f7`);
  - the owner-decision packets;
  - the lane handoff.
- **Modified:** the plan.

## Row 157 (episode design: four or more rounds, staggered reads, contention above 1, round 1 scored apart)

- **Definition:** `docs/reports/workplan-ep/R1-row157-contention-definition.md` (sha256 `b9db8f83…`, `8a16e88`) and addendum `R1-row157-contention-addendum.md` (sha256 `f6ae2b43…`, `5cabfe7`). The Assistant accepted both at source scope.
- **Pinned before the reveal:** `docs/reports/workplan-ep/R1-row157-contention-pin.md`, committed in `1d333f7` at 2026-11-23 08:02:58 -0500.
  - Generator `lab/r1_episode_v3.py`, sha256 `edfe7750…d236`; rule `fixed-roster-staggered-release-v3`; seed 17; R = 4.
  - Scheduled κ = 4/3, 4/3, 4/3, 2.
  - Pin `6fa1d9e56fad0a74829e6f9de4a9f70b73118165c696e044923b0efffd69f588`. The diff review recomputed it from a clean `git archive e11df9d` and it matches.
  - For comparison, v2 gives κ = 2/3, 4/5, 1 and 4/3.
- **Realized readouts** (a separate readout, never used for eligibility): `lab/r1_contention_readouts.py`. Default v3 run, per round: ρ = 2, 4, 4, undefined; c = 3/2, 1, 1, undefined.
- **Staggered reads:** one named reader per round, as in v2. The frozen definition leaves a fuller definition open, so the reviewer judges whether this is enough.
- **Reviews:** v3 review ACCEPT, with its findings fixed in `ea24c1f`. The readouts were rejected once and then fixed in `8de57ef`, with tests that fail on the rejected version.

## Test evidence for this exact commit

The suites ran in the pinned offline image `murmuration-t7:1` (`sha256:c74c8710…befb7`) with `--network=none`, `--read-only` and `--rm`. The Lean toolchain, `runs/ep1-live/pilot3` and `runs/spend/pilot3.jsonl` were mounted read-only (`runs/container-suite-e11df9d.hZjTis`, EVIDENCE.sha256 `f9dab853…`).

| Suite | Tests | Result | Exit | Skipped |
|---|---|---|---|---|
| Package | 869 | OK | 0 | 1 (a test that needs torch to be absent) |
| Lab | 860 | OK | 0 | 2 (qgrid data not in the archive; local Qwen checkpoints unavailable) |

## Unchanged

- **N2:** sealed. The commitment `6def4efcb166fc1c8da3f0974e8257c4bbe560c2449f85da86dbc808335119aa` is held by the Assistant as custodian.
- **Reviewer:** works read-only and has no N2 access.
- **Output:** a per-row ACCEPT, REJECT or INCOMPLETE bound to `e11df9d`.
- **Quiet-machine runs:** the "three green runs on a quiet machine" stay a separate gate (`OWNER_DECISION_X42_quiet_host_window.md`).
