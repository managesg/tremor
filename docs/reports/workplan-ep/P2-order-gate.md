# P2-order-gate: verification of the pilot 2 task-order factor

Verifier: Opus 5.5, fresh context, read-only on the repo (this file is the only write). Date 2026-11-20.
Scope: the pilot 2 task-order factor in `src/murmuration/ep1.py` and `tests/test_ep1.py`. The subject is the
delta against the pre-change working tree that G0-2R4 tested (copy at `ep1.py` 412475a1, byte-equal to G0-2R4's
hashes). Spec: `prereg/EP1.md` change 18 and section 13 item 16b; `docs/reports/ep-approvals.md` addendum 6.
There was no key, no `.env*` read, no network and no GPU. Experiments ran in a scratch copy with `train/` and the
Lean toolchain: `/tmp/claude-1000/-home-adelmar-SeaBridgeAI-manageesg-backend/6d6e3057-52a5-4529-b1fd-fc0a5bee49e3/scratchpad/p2gate`.

> **Instrument validation only.** Every number here comes from the loopback fake server or scripted responders.
> None of it is evidence about any model.

## Hashes

| File | sha256 (prefix) |
|---|---|
| `src/murmuration/ep1.py` | `4f52e6b01ff42e05` |
| `tests/test_ep1.py` | `29b6ad39e656f6c4` |
| `src/murmuration/team_claude.py` | `1bb4ed66bc71cad3` (unchanged since G1b-R2) |
| `src/murmuration/backend_claude.py` | `8e122edbee17edca` (G0-2R4's file plus the one `s(...)` scrub line on `block_types`) |
| `src/murmuration/spend.py` | `c7ec57de50d026b5` (unchanged since G0-2R4) |

**Real ledger.** I hashed all 10 files in `runs/spend` and `runs/ep1-live` (including `canary.jsonl` 45aaffae and
`pilot.jsonl` 38bd2f02) at the start and again at the end. All 10 were byte-identical. At the end, the repo's
`ep1.py` and `test_ep1.py` were byte-equal to the copies I tested.

## Verdict: ACCEPTED-WITH-NOTES. Pilot 2 may run now

All three run conditions in addendum 6 hold:
- G0-2R4 accepted.
- This order switch is implemented and verified.
- The 16b text is in the prereg.

Two things still apply:
- The run must finish by 2026-11-23 on the unchanged price sheet.
- It needs the owner's confirm flag at launch.

The report gap N1 must be closed before the order is picked. It does not have to be closed before the run, because
every input the rule needs is in `episodes.jsonl`.

## Claims checked

| Claim | Evidence | Holds |
|---|---|---|
| 6 sets split 3/3 by a seed with no arm in it | The seed is `random.Random(f"ep1:task_order:{schedule_seed}")`, over a balanced list `(TASK_ORDERS*n)[:n]`. Seeds 0 to 5 give 3/3 every time, and the assignment varies across seeds. Patching the condition list leaves the assignment unchanged (test, plus mutants M1 and M12 killed). Seed 0 gives shared on sets {0,3,4} and per_agent on {1,2,5}. | Yes |
| Every arm and both pilot cards in a set use the set's order | A full 6-set fake `pilot2` run against a copy of the real ledger finished `complete`: 30 episodes, 240 calls. Each order has 15 episodes, 3 per condition. No record's `task_order` differs from its set's plan. M5, M6 and M8 (leakage card forced to shared) were killed. | Yes |
| `task_order` is recorded | Every record has `task_order`. `pilot_trace.txt` prints `task_order=` on all 30 episodes. | Yes |
| Ids are unique, including against pilot 1 in the same ledger directory | Probed with the copied `runs/spend` (that copy's pinned directory). All 30 ids are unique. Collisions with pilot 1's 11 episode ids: 0. Ids have the form `ep1p2[pa]{sc,kw}[r1]-...`. The prefix test uses `eid + ":"`. | Yes |
| Caps unchanged | `pilot2` is 260 calls, USD 0.25 and 598,000 tokens. The schedule is 6 × 5 × 8 = 240 calls. The top-level caps sum to ep1 5 + pilot 0.5 + pilot2 0.25 + ar1 3 = USD 8.75, which is at most USD 10. The canary is inside ep1, and the 0.0162 already spent sits inside its batches. `spend.py` is unchanged since G0-2R4. | Yes |
| EP-1 and canary bodies unchanged by this change | Fake server, `n_sets=2`, seed 0. EP-1 has 48 bodies. Pre-change tree: sha 8a8e4766…, canary 3fc5eb8a…. The current tree is identical, and so is the test's `EP1_BODIES_SHA`. | Yes |
| EP-1 bodies against `b4a820e` | Removing `"thinking": {"type": "disabled"}` from each current EP-1 body leaves all 48 equal to HEAD's (HEAD sha bfa19f48…). The canary also differs from HEAD by 34 fewer filler bytes, which keeps it at exactly 90,000 bytes with the new field. That difference comes from the gated change 13, not from this change. | Yes |
| Tests | Targeted `test_ep1`: 60 tests OK. Full `unittest discover`: 730 tests, OK, 2 skipped. A first full run had 1 teardown error, caused by my own probe writing `pilot2.jsonl` into the copy's ledger at the same moment. The rerun with nothing else running was clean. | Yes |
| Fake dry run | `python3 -m murmuration ep1 dry-run` gave `GREEN`. The floor was [0.25]×3 and the oracle [1.0]×3. Canary `complete`; pilot `complete` with 15 episodes; pilot2 `complete` with 30; ep1 `inconclusive` with 60. | Yes |
| Mutants | 13 of 14 killed: M1 to M13 cover the seed, the shuffle, balance, ep1 leakage, the driver block order, the caps pass-through, the id tag, the leakage card, the report filter, the trace, `schedule_seed`, per-arm order and tag order. **M14 survived**: deleting `pilot2_report` from `dry_run_all` is not tested. | Mostly |

## Change-18 rule: computable from the data, not printed by `analyse`

The inputs are all in `episodes.jsonl`:
- `task_order`;
- `set` (or `taskset_id`);
- `cond`;
- `Y`;
- `scores.duplicates`, the executed duplicate work: work events minus distinct tasks, from the trapbench alloc scorer;
- `ended` and `void`, which filter to `analysis.SCORED_ENDS` and non-void attempts.

`p2gate/rule.py` computes (a), (b) and (c) and the tie rule from these fields alone, and it ran on the fake output.

`analyse` prints only the mean `Y` per order and condition. **Exact gap against 16b's "the pilot 2 report prints, per
order":**
- `Y` per task set and condition;
- executed duplicates under `none` and under `code`;
- (a), (b) and (c) as pass or fail;
- which orders are usable and the resulting EP-1 order;
- criteria 1 to 4, 6 and 7 per order "as a description".

## Notes

- **N1 (close before the order decision).** Add the gap above to `analyse` for `pilot2`, or commit a rule script
  before the run. The numbers in the rule are already fixed, so adding this after the run tunes nothing. Doing it
  before the run is cleaner.
- **N2.** 16b says executed duplicates are counted "as `analysis` counts it". `analysis.py` does not count them; the
  count is `scores.duplicates`. Fix the wording or the code.
- **N3.** The rule is undefined when an order ends with fewer than 3 valid `none` episodes, for example after a void
  and a failed `r1`. The prereg should say whether that order is unusable.
- **N4.** Mutant M14 survived: `pilot2_report` in `dry_run_all` has no test. This is cosmetic.
- **N5.** With per_agent sets, the oracle and floor responders sort the task ids. The code comment says this is
  correct only below 10 tasks per set, and alloc sets have 6.
