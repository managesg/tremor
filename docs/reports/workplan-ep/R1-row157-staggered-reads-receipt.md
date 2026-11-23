# R1 row 157: staggered-reads receipt and claims-only reconciliation (candidate 83e4870)

**Requested by:** the Assistant's independent source check (`msg_5ee3ebc91bb9`) before any row-157 closure request.
**Source:** a run of `lab.r1_episode_v4.run(<dir>, case="early_error")` on a clean `git archive 83e4870`, seed 17. Output hashes: `reads.json` sha256 `fd10570775876ba206b260ac610638d3c80d2bdf85222547880034dc3b1b3e0c`, `board.jsonl` sha256 `527c6727edc523278c41e74a277a8c195350727213ce0c24615ecb8db3ce081c`.

## Receipt: a later reader sees an earlier agent's committed action

Board events, from `board.jsonl` (seq, type, agent, round, data, hash prefix):

| seq | type | agent | round | data | hash |
|---|---|---|---|---|---|
| 1 | claim | a0 | 0 | item t17t0 | `fa3e0aba` |
| 2 | end_round | | 0 | t17t0 to a0 | `6a6e4345` |
| 3 | claim | a1 | 1 | item t17t1 | `4c3d7fdf` |
| 4 | claim | a2 | 1 | item t17t4 | `ab6968ff` |
| 5 | claim | a3 | 1 | item t17t4 | `40dbb499` |
| 6 | end_round | | 1 | t17t1 to a1; t17t4 collision, winner a2 | `cb2afc93` |

Round-2 reads, from `reads.json`:

- **a0, scheduled lag 1:** `seen_round` 1, `seen_commit_hash` `cb2afc931fa27f29723d07049b89177c443d96dbdb58eec9bd16f03c361e96c1`, which is seq 6. Its claims are `{t17t0: a0, t17t1: a1, t17t4: a2}`. a0's view therefore contains a1's committed claim (seq 3) and a2's committed winning claim on the contested t17t4 (seq 4, resolved at seq 6). Both are actions other agents committed in an earlier round.
- **a1, scheduled lag 2:** `seen_round` 0, `seen_commit_hash` `6a6e43456f24c916e4b490e734ee5aa67b3e7e19076fb00454ff6f03c73a90b6`, which is seq 2. Its claims are `{t17t0: a0}`. Neither round-1 action is visible to it.

So in the same round, two agents hold different committed board states. The one with the shorter lag sees earlier agents' committed actions that the one with the longer lag does not. Each read's commit hash is the hash of the `end_round` event at round − lag.

## Reconciliation with definition item 1 and the e11df9d verdict

- **Definition item 1** defines a board read as a read of the shared work board, meaning what has been committed so far: claims, posts and work results. It excludes reading a fixed marker or any value that never changes during the episode.
- **This fixture's board** commits only init, claim and end_round events. No posts or work results are board events here (work runs through the router and is scored outside the board). A v4 read therefore returns the board's full committed state, and that state is claims only, so `items` is empty. The claims-only content is everything the board holds, not a subset chosen for the read.
- **The exclusion is met.** The state read changes across rounds and differs between agents in the same round, as the receipt shows. The e11df9d verdict found that v3 had "one named reader of a setup marker per round", a fixed value. v4 removes that marker read and replaces it with these changing board states.
- **Open question for the reviewer.** If item 1's mention of work results is read as requiring them inside the read, this fixture cannot meet it until work results become board events. That would be a design change outside this candidate, and the reviewer decides.

## Schedule claim and behavioural claim, kept apart

- **Schedule (established):** the lags are pinned (`R1-row157-staggered-reads-pin.md`, commit `83e4870`, reads pin `8a11207d…`), and each realized view matches its scheduled lag. All 16 reads were checked by the independent v4 review; this receipt shows one in full.
- **Behaviour (not established):** in this scripted fixture, every action follows the fixed plan, and no agent's action depends on its view. This receipt makes no claim that staggered views change what agents do. That needs non-scripted agents.
