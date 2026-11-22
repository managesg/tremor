# Scorer differential: alloc, alloc2 and the Lean scorer (EP-1 primary outcome, option C)

Date 2026-11-20. Tree: HEAD 36bab4b plus uncommitted work (nothing committed). Instrument validation
only: no model, no provider call, no GPU. File digests (sha256, first 16 hex) at the time of the run:
`alloc.py` 91b4d8938dfdb6fb, `alloc2.py` 03ce98dbd093dcfd, `formal_alloc.py` 6c256eeb0eca7366,
`Basic.lean` 1cc108ab2e9d44eb, `Json.lean` f6d0ba894b748596, `Theorems.lean` 65bec48f0275aeb1.

## The one definition all three scorers now implement

From `prereg/EP1.md` section 7 and 7a, option C, and its two settled rules:

- `Y = distinct_passing / slots` when `valid`, else `Y` is null. Lean keeps `Y_num`/`Y_den` as
  diagnostics and reports `valid`; `formal_alloc.score` returns them raw, and the test helper
  `lean_as_alloc` maps them to a null `Y` when `valid` is false. An invalid log is void.
  It is never capped or partly scored. The other fields are still computed for diagnostics.
- `extra_work_events`: accepted (not rejected) work events on a task in the set beyond the first by
  the same agent.
- `valid`: every event well formed, `extra_work_events == 0`, and at most `slots` accepted
  known-task work events (prereg section 7 states this count condition explicitly).
- False-done counts only executed (not `rejected`) done releases on tasks in the set (rule 1).
- Answers pass only as JSON integers: `30.0`, `"30"`, `true`, `30.5` are not `30` (rule 2).
- Unknown-task events remain logged no-ops.

**Well-formedness is my choice** (the prereg does not define it; the brief asked for it). An event
is malformed when it is not an object, `action` is present and not a string, `agent`, `task` or
`name` is present and neither a string nor null, or `rejected` is present and neither a bool nor
null. A malformed event counts in no field and makes the log invalid. The rule covers only fields
all three scorers read. Lean no longer rejects the whole input for a malformed event. It still
returns REJECTED for a malformed task set, a log that is not an array, or input that is not JSON. A
non-string `type`, `item` or `data.item` is not malformed; it reads as no kind or no task (a no-op).

A missing or null `agent` is one agent key in all three scorers (uniform, so no disagreement).

## Generator

`tests/test_formal_alloc.py`, `rand_case`, seed `"formal_alloc:differential:v2"`, N = 10,000.
Each log has 1 to 6 tasks, `n_agents` 1 to 4 and 0 to 12 events. Agents are drawn from
`a0`..`a3` or null. Half of the logs give each agent at most one work event. The event mix:

| Share | Event |
|---|---|
| 50% | `action: work`. The answer is drawn from: expected (3 of 11), 0, null, float, string, `true`, `false`, expected + 0.5, list. The name is drawn from `n0`, `n1`, `""`, null, the rule name, or missing. In 5% of these the task is deleted |
| 4% | `type: work` (open category, see Residual) |
| 6% | `action: claim` |
| 15% | `action: release`, `done` true with probability 0.7 |
| 15% | board `type: release`; `data.item` is the task or the integer 5, and `done` is true, false or 1 |
| 5% | `type` 5, `"post"` or `"release"` with a top-level `item` (task or 5) |
| 5% | malformed event (11 shapes) |

`rejected` is `true` 15% of the time, `false` 15%, null 5% and absent otherwise. Task ids include
two unknown ids (`zz`, `t9`).

Logs containing each category (one log can contain several):

| Category | Logs |
|---|---|
| refused release | 2,370 |
| unknown-task event | 7,490 |
| non-integer answer on accepted work | 6,565 |
| an agent with 2+ accepted known-task work events | 1,028 |
| malformed event | 2,477 |
| `type: work` event | 2,173 |
| valid (Lean) | 6,299 |

## Numbers

| Comparison | Before this alignment | After |
|---|---|---|
| alloc vs alloc2 (`test_alloc2` 2,000 logs) | 341, then 0 after the unknown-task fix (reported by the building session) | 0 (the test now asserts 0) |
| Lean vs alloc2 (old 5,000-log mix) | 2,283 (1,973 refused/unknown-task release, 144 `type: work`, 166 both), rerun at the start of this session | n/a (mix replaced) |
| Lean vs alloc (old 5,000-log mix) | 1,081 (float answer equal to the integer), rerun at the start of this session | n/a (mix replaced) |
| Lean vs alloc (new 10,000) | n/a | **0** |
| Lean vs alloc2 (new 10,000) | n/a | 617, all `type: work`; **0** of any other kind |
| alloc vs alloc2 (new 10,000) | n/a | 617; **0** once `type: work` events are removed |

Every shared field is compared: `distinct_passing`, `surviving_passing`, `slots`, `duplicates`,
`name_collisions`, `Y`, `extra_work_events` and `valid` in all three; `unknown_task_events` for
alloc and Lean; `done_releases` and `false_done` for alloc2 and Lean. Every disagreement, `valid`
included, disappears once the `type: work` events are removed from the log.

Not a live difference: Lean's `intOf?` reads the JSON number `3e2` as the integer 300, while Python
reads it as a float. Through `formal_alloc`, `json.dumps` writes floats below 1e16 with a decimal
point (not an integer in Lean), and larger values cannot equal an expected answer.

## Downstream: void not yet wired (outside my files)

`team.py` `_score` computes the episode outcome as `s[k] / s["slots"]`, not `s["Y"]`, and neither
`team_claude.py` nor `ep1.py` reads `valid`. So an invalid log would still produce a numeric
episode `Y`, and `analysis.py` drops only a null `Y`. Required of the owners of those files: void the
episode when `valid` is false, whatever the number. The EP-1 loop is argued not to produce an
invalid log (prereg section 7), so this guards a harness fault.

Concurrency: during this run another session added `"extra_work_events"` and `"valid"` to
`cardcheck.py` (`BANNED`), which `test_cardcheck.test_vocabulary_drift` needs. My baseline run of the
suite overlapped my first `alloc.py` edit; its differential numbers match the pre-change scorers.

## Residual: one open spec question (not resolved here)

`alloc2` reads a work event written as a board `type` when there is no `action`. `alloc.py` and
Lean do not. The prereg (section 7, "work events written with `type` instead of `action` ... open")
leaves this open, so I did not choose. The minimal log, with task set
`{"n_agents": 4, "tasks": [{"id": "t0", "expect": 30}]}`:

```json
[{"type": "work", "agent": "a0", "task": "t0", "answer": 30}]
```

alloc gives `distinct_passing` 0 and `Y` 0.0. Lean gives 0 and 0.0. alloc2 gives 1 and 0.25.

The episode log writes work only as `action` (`team.py` line 148). So the EP-1 loop cannot produce
this case. The differential tests tolerate this one named category and print its count. They
fail on any other disagreement. The owner should decide whether a `type: work` event counts.
After that decision, the generator share can stay and the tolerance can be removed.

## Lean

- `lake build`: clean in a fresh copy (no warnings, no errors). 64 theorems (52 kept, 12 added),
  each with a `#print axioms` line. `lake env lean Axioms.lean` reports only `propext`,
  `Quot.sound` and `Classical.choice`. The static scan is clean.
- Added: `validWith_iff`/`score_valid_iff` (`valid` decides `Valid`: no malformed event, the
  agents of accepted known-task work pairwise different, at most `slots` of them),
  `extraWork_eq_zero_iff`, `wellFormed_iff`, `distinct_le_slots_of_valid`, `Y_in_unit_of_valid`,
  `valid_bounds` (on a valid log: `surviving <= distinct <= slots`, `0 < Y_den`, `Y_num <= Y_den`),
  `distinct_gt_slots_log_not_valid`, `two_work_one_agent_not_valid`, `malformed_not_valid`, and
  two list lemmas.
- Changed: `score_insert_unknown` now needs `e.malformed = false`, because a malformed event voids
  the log. `score_swap` covers the two new fields.
- `formal_alloc` returns INVALID for a build failure (tested with a temp copy that has a syntax
  error and a clean static scan), for a wrong `lean-toolchain` file and for a wrong `lean --version`.

## Regression check on old behaviour

I copied the pre-change `src/`, `formal/` (sources) and the toolchain link into a scratch tree and
ran the new `test_alloc`, `test_alloc2` and `test_formal_alloc` there: 16 failures and 11 errors.
They cover the alloc float answer, the alloc2 refused and unknown-task release, the invalid-log
cases in all three scorers, the Lean malformed event, the build failure and the toolchain file.
`alloc2` was already integer-only and Lean already excluded refused and unknown-task releases, so
those tests pass on the old code as expected.

## Ruling: scorer input is the episode action log only (alloc2 change, 2026-11-20)

Orchestrator ruling (owner-delegated): every event is a dict keyed by `action` in
{claim, work, release, pass}. An event without a string `action` (a `type`-keyed event, a board
release, any other shape) is malformed and voids the log. `alloc2.py` now implements this: no
`type` fallback, no board-shape release reading, release read from top-level `task`/`done` only.
Regression tests added (`type: work` smallest case and board release give `valid` false).

After-numbers (same generator and seed, N = 10,000, repo-local Lean): Lean vs alloc 0 disagreements;
alloc vs alloc2 3,903 (Y, valid); Lean vs alloc2 4,599 (Y 3,903, valid 3,903, done_releases 1,494,
false_done 1,477). **Target not met.** The ruling's premise does not hold for the reference scorers:
`alloc.well_formed` and Lean accept an event with no `action` key (a logged no-op, log stays valid),
and Lean reads a `type: "release"` board line as a release. Smallest residual:
`[{"type":"release","agent":null,"data":{"item":"t9","done":true},"rejected":false}]` gives
alloc/Lean `valid` true, `Y` 0.0 and alloc2 `valid` false, `Y` null. Zero disagreement needs one
of: alloc and Lean also reject action-less events (frozen here), or alloc2 treats them as no-ops
(and keeps Lean's board `type: release` reading for done/false-done).

## Ruling applied to alloc and Lean (2026-11-20, second pass)

The strict rule now holds in all three scorers. Scorer input is the episode action log only. An event
without a string `action` is malformed and makes the log invalid (`valid` false, `Y` null, episode void).
This covers an event with no `action`, a `type`-keyed event and a board release
(`{"type":"release","data":{...}}`). Every other field and rule is unchanged: option C, integers only,
unknown-task no-ops, and false-done counted on executed releases of tasks in the set.

- `alloc.well_formed` requires `isinstance(e.get("action"), str)`, the same as `alloc2._malformed`.
- In the Lean parser (`Json.lean`), an `action` that is missing or not a string throws, so the event
  reads as malformed. The `type` fallback is gone. A release now reads `task` and `done` at the top
  level only: the `item`, `data.item` and `data.done` board readings are removed (unused `strOrNone`
  deleted). This matches the frozen `alloc2` reading of releases.
  It is not a new choice, and the tests `test_release_reads_top_level_task_and_done_only` cover the
  three shapes against alloc2.
- Lean definitions (`Basic.lean`): `wellFormedEvent e := !e.malformed && e.kind.isSome`, with the Prop
  twin `WellFormedEvent` and `wellFormedEvent_iff`. `wellFormed`/`Valid` quantify over it. So the
  rule is in the definitions, not only the parser.
- Proofs re-checked under the new definitions. `validWith_iff`/`score_valid_iff` show that `valid`
  decides `Valid`. `distinct_le_slots_of_valid`, `surviving_le_distinct`, `Y_in_unit_of_valid` and
  `valid_bounds` are unchanged in statement. `score_insert_unknown` now takes
  `wellFormedEvent e = true`, and `malformed_not_valid` was adapted. Added
  `no_action_not_valid`: an event with no kind makes the log not valid.
- `lake build` (repo-local Lean 4.35.0) is clean. 66 `#print axioms` lines. The audit reports
  only `propext`, `Quot.sound` and `Classical.choice`. The static scan is clean.
- Tests: the `R()` helper in `test_formal_alloc` defaults to an action-keyed release. The former
  "odd, but readable: no-ops" events are now asserted malformed. The `strip_type_work` tolerance is
  removed, and all three differential pairs assert 0 on the full logs. In `test_alloc`, the new
  test `test_event_without_action_is_malformed` covers no-action, `type: work` and board-release events.

Numbers. The generator and seed are unchanged (`formal_alloc:differential:v2`, N = 10,000), and the
counts are raw, with no category stripped:

| Pair | Before | After |
|---|---|---|
| Lean vs alloc | 0 | **0** |
| alloc vs alloc2 | 3,903 (Y, valid) | **0** |
| Lean vs alloc2 | 4,599 (Y 3,903, valid 3,903, done_releases 1,494, false_done 1,477) | **0** |
| logs valid (Lean) | 6,299 | 2,396 |

The valid share falls because about 24% of generated events are now malformed (board release,
`type` events), and the mix is kept as is.

The minimal log from the residual above, with task set `{"n_agents": 4, "tasks": [{"id": "t0", "expect": 30}]}`:

```json
[{"type":"release","agent":null,"data":{"item":"t9","done":true},"rejected":false}]
```

All three scorers now give `valid` false (before: alloc true, Lean true, alloc2 false). The earlier
`type: work` residual is resolved by the same ruling: it is malformed in all three. No residual spec
ambiguity remains in this mix.

Regression check: the new `test_alloc` and `test_formal_alloc` were run on a scratch copy of the
pre-change `src/`, `tests/` and Lean sources, with the repo-local toolchain linked and 0 skips. The
result was 1 failure in `test_alloc` and 13 failures in `test_formal_alloc` (no-action and board
events, the release shapes, the minimal log, and both alloc2 differential pairs).

Full suite (`python3 -B -I -W ignore -m unittest discover -s tests`): 669 tests OK, 1 skipped (a
`test_t7_gen` test that needs torch). The rung-0 and team tests pass with no change to an expected
value. Concurrency: another session was editing `team.py`, `team_claude.py`, `ep1.py` and `spend.py`
during this run. The suite result is for the tree as it was at run time.
Digests (sha256, first 16 hex): `alloc.py` 07ae29d898ee57ef, `alloc2.py` c78207f7dab9d66d,
`formal_alloc.py` 6c256eeb0eca7366 (unchanged), `Basic.lean` 6362b8d173e4a455, `Json.lean`
2fb07ff937460ab5, `Theorems.lean` a91b4aac74c9b06e.

## November 22 release-candidate recheck

A fresh isolated Lean build from the archived 351-file R1 source ran
the retained four differential tests with the same 10,000 seeded
logs. All three scorer pairs had zero disagreements, and the scoring
bridge checked the returned score count and schema. The set contained
2,396 valid logs. This verifies the scripted scorer-agreement claim in
the staged public release.

The exact staged public `quantum/gatesim.py` also completed the
independent QGrid differential. The comparison used the release's
public iteration-estimate function and checked 329 statevectors over
65 cases. It found zero differences at the registered tolerances,
including global phase, and both simulators matched the closed-form
probability in all 329 states. The first check used system Python,
which lacked NumPy. The successful run used the existing local Python
3.12 environment with NumPy 2.5.5.

```bash
bash runs/release-three-scorers.hDZq9x/verify.sh
```

The staged release remained clean at
`a99cddd1301905566e09a25b10aa583af9867ad3`. These checks cover
the scripted public instruments. Held-out model effects and
scientific acceptance remain open.
