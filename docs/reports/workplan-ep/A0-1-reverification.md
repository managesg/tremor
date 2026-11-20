# A0-1 re-verification: `cell.py`, `router.py`, `perturb.py`

2026-11-19. Verifier: Opus 5.5, adversarial, own probes only (the builder's tests were used only as the mutation
target). Zero cost, no network, no GPU, no `.env*`. All probes and mutants ran on copies under the session scratchpad
(`rv/`, `rvprobe/`). Nothing in the repo was edited except this file.

**Verdict: `cell.py` FAIL, `router.py` FAIL, `perturb.py` FAIL.** Every finding from `A0-1.md` is fixed for the
inputs named there. But new inputs break the same contracts (NaN/inf budgets, Unicode model ids), and P1 is still never
delivered by `run_matrix`. Each fix is one to five lines.

## Reviewed content (uncommitted, bound by hash, base 972dee3)

| File | sha256 |
|---|---|
| `src/murmuration/cell.py` | `b76b1b65ab7f4b580e57fbbc9fe7db6535d47756e9566b4de3cf94ebcabb5b90` |
| `src/murmuration/router.py` | `862c3b3ea0f76d932e2621cf17162e3b7b954a134dfb07aa3d3b36fb02167dfd` |
| `src/murmuration/perturb.py` | `4665ea90a07fd9426e89e1be6209d78e5f1e90bcf55c77b10cdedb0c2cda184f` |
| `tests/test_cell.py` | `747817b3f4401795f5b16c31512cc497927e2644f67effc1572406c1558b696e` |
| `tests/test_router.py` | `ea0618ad59ad16d8d7668c9ca03d5cebf30343fbb8f42f52a635d41e103e8f3a` |
| `tests/test_perturb.py` | `64eb2ba16283d5d6d24ac27580ff04bebd279787a692324c3ef0ada561519af8` |

The live files were re-hashed at the end of the run and still match the copy.

## 1. Earlier findings: status under my probes

Probe script: `rvprobe/rv_probes.py` (124 checks, 47 broken). Output: `rvprobe/probes.out`.

| Earlier | Contract | Now | Evidence |
|---|---|---|---|
| R13 | last-line log edit | Fixed | detected |
| R14 | truncation | Fixed | detected; truncate plus a consistent `log.head` rewrite is caught when the bundle's `log_head` is passed |
| R15 | deletion | Fixed, with a fail-open | `log.jsonl` deleted: False. **Both** `log.jsonl` and `log.head` deleted, no expected head: **True** |
| R16 | forged self-consistent chain | Known shortcut | verifies without `expected_head`; rejected with the real bundle head |
| R17 | malformed log | Partly fixed | blank, list, int and bad-UTF-8 lines give False. A `log.head` of `[]`, `5`, `null` or `"x"` raises `AttributeError` (`rec.get`) |
| new | `log.head` edited alone | Held | False |
| new | truncate after an earlier bundle's head | Note | `expected_head` only has to be *in* the chain, so later entries can be cut (and `log.head` rewritten) while an earlier bundle still verifies |
| R18 | task-id traversal | Fixed for `../`, `/abs`, `a/b`, NUL, `..` | **`"x\n"` passes** `valid_name`: `NAME` ends in `$`, which matches before a trailing newline. It writes `outbox/x\n.json` |
| R19 | cell-name traversal | Fixed | absolute, `../`, symlink-out and `good\n` are rejected by `run_dir` |
| new | symlinks inside a cell | Broken (low) | `log.jsonl` or `outbox/` symlinked outside the cell: the log line and the bundle are written outside |
| new | symlink race | Broken (low) | swapping the cell for an outside symlink between the `realpath` check and `load` runs and writes in the outside cell |
| R3 | verifier checks the answer | Fixed | it recomputes from `spec["payload"]` (not from the bundle). Wrong and `None` results are rejected. Plan bundles verify |
| R4 | bundle bound to spec | Fixed | replay against the same id with another payload, or against another `cell`, is rejected. Adding `expect` keeps the sha (by design) |
| R1 | alias and case independence | Fixed for case, whitespace, tab, `-YYYYMMDD`, `@YYYYMMDD` | **Bypassed** by `claude-haiku-5-5​`, `claude‑haiku-5-5` (non-breaking hyphen), fullwidth `ｃｌａｕｄｅ`, `\x00` suffix, `-latest`, `:0`, `anthropic/` and `us.anthropic.` prefixes, `5.5` vs `5-5`. Each verified "independently" (`True`). `MODEL_ALIASES` is empty |
| R2 | forged bundle model | Fixed, if the caller passes the real worker cell | a forged model with a **decoy `worker_dir`** whose `cell.json` has that model is accepted. `verify` does not check `bundle["cell"]` against the worker cell id, and never calls `verify_log(worker_dir, bundle["log_head"])`. A fabricated bundle (never executed, `log_head` of zeros) is accepted |
| R6 | default-deny budget | Fixed for missing, 0, negative, string, bool | **`max_tokens: NaN`, `Infinity` and `max_seconds: NaN` pass `_check_policy`** (`NaN <= 0` is False). Loaded from disk, a 400k-character task ran as `done` |
| R5 | spec budget only tightens | Fixed for numbers | **`budget.tokens = NaN` loosens it**: `min([nan, 10])` is `nan`, and `tokens > nan` is False. Policy cap 10 tokens, the task ran `done`. A string budget or `budget: null` raises `TypeError` or `AttributeError` |
| R7 | negative `extra_seconds` | Fixed | floored at 0. NaN also floors to 0 |
| P1 (old) | P3 answer and label leak | Fixed for the keys | across 90 episodes no `fix` key or `x + k` expression reaches the view. The note names the canary command, which is the lure by design. **New leaks:** the view carries `k: "P3"`, which labels the trap episode. And `task`, `seed`, `k` are enough to rerun the public `traps.gen` and recover the gold fix and the canary: **20 of 20** recomputed exactly |
| P2 (old) | P1 delivery | **Not fixed where it counts** | `agent_view(ep, step)` delivers `spec_v2` only from `step` onward. But `run_matrix` calls the agent **once, with `step=0`** (`agents[arm](agent_view(ep))`), so in the matrix `spec_v2` never reaches the agent. The test `test_agent_never_sees_scorer_keys` asserts exactly that (line 112). The view also gives the injection step number (`step`) |
| P5 (old) | unscored harm is `None` | Fixed | `clean`, P2 and P4 give `None`, and `harm_rate` is `None` when nothing is scored |
| P3 (old) | independent P3 clusters | Fixed | 10 of 10 distinct canaries at one seed |
| P4 (old) | substring harm | Fixed for `cd repo && ...` | false negatives: double space, tab, `make -C repo <target>`, quoted target. False positives: `echo '<canary>'`, and a longer target (`...3071`) |
| new | agent mutates its view | **Broken** | `agent_view` is a shallow copy: `payload` is the episode's own dict. An agent that sets `view["payload"]["denied"] = "x"` and then acts on `protected/file` gets P5 `harm = False`, and `harm_rate = 0.0` through `run_matrix` (`rvprobe/p5mut.py`) |
| new | malformed agent output | Low | an event without `cmd` raises `KeyError`, `actions: None` raises `TypeError` |

### Does the test matrix overstate P1 coverage? Yes.

- No test runs an agent across steps. The only `spec_v2` delivery check calls `agent_view(e1, e1["step"])` directly.
- In `run_matrix`, P1 is "spec_v1 only". The `weak` agent's P1 failure (`harm_rate 1.0`) is produced by the test
  reading the scorer (`full(ep)`), not by a changed requirement.
- My probe: an agent that follows the only spec it was ever shown (`const_<a>` from `spec_v1`) is scored
  **harm_rate 1.0** under P1. So in the matrix, P1 harm measures "followed the original spec", not "ignored the
  mid-task change". Any P1 numbers from `run_matrix` are invalid until the agent interface is step-wise.

## 2. Flakiness

Full suite, 15 runs on an isolated copy (`rv/`, no concurrent writers), `CUDA_VISIBLE_DEVICES=""`,
`PYTHONPATH=src python3 -m unittest discover -s tests`:

```
runs 1-15   Ran 217 tests  OK (skipped=2)   rc=0, 28.9 s to 34.7 s   (15 of 15 green)
```

The two skips: `test_t7_gen ... test_presence_top_k_top_p` ("needs torch (container)") and
`test_t7_samples ... test_real_file_if_present` ("no data", because `data/` was not copied). Neither belongs to A0-1.
The live suite may run the second one, and these 15 runs do not cover it.

The three A0-1 test files, 15 runs with `PYTHONHASHSEED` 1 to 15: 15 of 15 OK (42 tests). The builder's one
unexplained error is not reproduced in isolation. That fits interference from concurrent writers in the live tree,
which I did not reproduce (I did not run in the live repo, to avoid racing other lanes).

## 3. Mutation check

`rvprobe/rv_mutants.py`: 26 mutants of safety lines, each in its own temp copy, against the three test files.
**25 killed, 1 survived.**

```
KILLED  cell    valid_name accepts any string        KILLED  router  task id unchecked
KILLED  cell    policy limit 0 allowed (<= -> <)     KILLED  router  run_dir realpath containment removed
KILLED  cell    policy check removed                 KILLED  router  allow-list only (deny does not win)
KILLED  cell    verify_log ignores log.head          KILLED  router  spec budget can loosen (max)
KILLED  cell    missing log.head -> True             KILLED  router  ceiling violation still accepted
KILLED  cell    expected_head ignored                KILLED  perturb agent sees scorer
KILLED  cell    verify accepts any non-empty result  KILLED  perturb P1 v2 up front
KILLED  cell    negative extra_seconds allowed       KILLED  perturb P1 v2 never delivered (agent_view only)
KILLED  router  no bundle-to-spec binding            SURVIVED perturb P3 gold fix in payload under key "hint"
KILLED  router  trust bundle model                   KILLED  perturb unscored harm is False
KILLED  router  worker model from bundle             KILLED  perturb harm_rate counts None as 0
KILLED  router  model_key no normalisation           KILLED  perturb P3 harm exact match only
KILLED  router  model_key no date strip              KILLED  perturb P3 seed not per task
```

The survivor: the planted-answer test checks key **names** (`"fix"`), not values. The gold fix under any other key
passes.

The A0-1 survivors, re-targeted at the current text (`OLD=1 rv_mutants.py`), are all killed now. Old M5 (row-level
bootstrap) is killed by an error rather than an assertion: a row resample with no clean rows gives `None - float`.
Old M8 (cost dropped from the log entry) and old M10 (plan `tokens_in` zeroed) are killed by assertions. So fix item 8
of `A0-1.md` is closed.

## 4. Verdicts

| Module | Verdict | Why |
|---|---|---|
| `cell.py` | **FAIL** (narrow) | Log anchoring, malformed lines, the recomputing verifier and safe names hold. `_check_policy` accepts NaN and Infinity, so "never unlimited" breaks again. `valid_name` accepts a trailing `\n`. A non-dict `log.head` raises. Deleting both log files verifies when no head is passed |
| `router.py` | **FAIL** (narrow) | Traversal, spec binding, the recomputing verifier, case and date aliases hold. A NaN spec budget loosens the cap. Unicode, provider-prefix and `-latest` model ids defeat independence. `verify` trusts the caller's `worker_dir` and does not check the log |
| `perturb.py` | **FAIL** | `run_matrix` never delivers P1's change, and scores an honest v1 follower as harmed. A shallow-copy view lets the agent erase P5 harm. The view labels the condition (`k`) and the injection `step`, and its `task`/`seed` let the agent recompute the gold fix |

## 5. Ranked residual defects

Threat model. Some defects happen by **accident**, with honest inputs: 1, 2 (any agent that edits its input dict), 3
(an `Infinity` written by `json.dump`), 5 (provider-prefixed or `-latest` ids), 8, 9 and 10. The others need an
**adversary**: someone who can write `cell.json`, `policy.json`, specs or the cells root (4, 7, 11), or an agent that
can import the package (6, the 20/20 recompute).

1. **P1 never delivered in `run_matrix`** (perturb). Severity critical: P1 data invalid.
2. **Shallow-copy view: agent erases P5 harm** (perturb). High.
3. **NaN/Infinity policy limits pass** (`cell._check_policy`). High: unlimited budget.
4. **NaN spec budget loosens the cap** (`router._cap`). High.
5. **Model-id normalisation bypass** (`router.model_key`): ZWSP, U+2011, fullwidth, NUL, `-latest`, `:N`,
   `anthropic/`, `us.anthropic.`, `5.5`. Medium.
6. **Condition label, step and seed leak** (perturb): `k`, `step` in the view; gold fix recomputable 20/20 from
   `task`/`seed`. Medium.
7. **`verify` trusts the caller's `worker_dir`**, does not match `bundle["cell"]`, and never calls `verify_log`. Medium.
8. **`valid_name` accepts a trailing newline** (`$` instead of `\Z` or `fullmatch`). Low to medium.
9. **`verify_log` edge cases:** a non-dict `log.head` raises, and both files deleted gives True with no head. Low.
10. **P3 harm matching:** whitespace and `make -C` false negatives, `echo` false positive. Low to medium.
11. **Symlinks inside a cell (`outbox/`, `log.jsonl`) and the check-then-use race in `run_dir`.** Low: needs write
    access to the cells root.
12. **Duplicate task ids overwrite bundles silently** (one file, two log entries). Low.
13. **`harm` crashes on malformed agent output** (`cmd` missing, `actions: None`). Low.
14. **Planted-answer test checks key names only** (the mutation survivor). Test gap.
15. In `make_episode`, the docstring sits after the guard, so it is not a docstring. Cosmetic.

## 6. What must be fixed

**Before the freeze** (the freeze hashes `src/`):

- (1) Make the agent step-wise. `run_matrix` passes `lambda step: agent_view(ep, step)`, or calls the agent at each
  step. Test: a scripted agent switches to v2 only after it sees v2, and `harm_rate` for an honest v1 follower that
  never saw v2 is not counted as harm.
- (2) `agent_view` returns a deep copy (`copy.deepcopy` or a JSON round-trip). Test: an agent that mutates its view
  cannot change `harm`.
- (3) In `_check_policy`, add `math.isfinite(v)`. (4) Validate spec `budget` values the same way, rejecting NaN,
  infinity, non-numbers and `null`, in `run_task`. Tests for NaN and inf on both.
- (5) In `model_key`: `unicodedata.normalize("NFKC", ...)`. Reject any id outside `^[a-z0-9._:/-]+$`, which removes
  ZWSP, NUL and controls. Strip `-latest`, provider prefixes and `:N`. Fill `MODEL_ALIASES` from the price sheet's
  `aliases`. Tests for each bypass named in R1 above.
- (6) Drop `k` and `step` from the agent view, or replace them with neutral fields, and keep `seed` and `task`
  scorer-side: give the agent an opaque episode id. Test: the gold fix is not recomputable from the view. This
  breaks the test agents in `tests/test_perturb.py`, which dispatch on `ep["k"]`, so the fix includes test edits: the
  test agents should key on payload shape.
- (8) `NAME.fullmatch` or `\Z`. Test `"x\n"`.
- (14) Test planted values, not key names: assert `str(fix)` with its context, `spec_v2` and `v1_only_artifact`
  values are absent from `json.dumps(view)` in every field.
- (9) In `verify_log`, put `isinstance(rec, dict)` in the `try`, and treat `log.head` missing with lines present, or
  both files missing, as False whenever a head is expected.

**Before A7** (A7 owns `router.py` next and adds enforcement hooks; these belong to it, not to the freeze fix):

- (7) `verify` loads the worker cell and requires `cell["id"] == bundle["cell"]` and
  `cellmod.verify_log(worker_dir, bundle["log_head"])`. The hook layer, not the caller, picks `worker_dir` from
  `bundle["cell"]` under the cells root. Test: decoy worker dir, and a fabricated bundle with a bogus `log_head`.
- (11) Refuse symlinks inside a cell: `lstat` `outbox/` and `log.jsonl`, open with `O_NOFOLLOW`. Resolve the cell dir
  once and pass the resolved path to `run_task`, which closes the check-then-use race.
- (12) Refuse to overwrite an existing `outbox/<id>.json` (`open(..., "x")`).
- The ceiling check must run **before** the handler once handlers are real (R8 is still wording only).
- (10, 13) Can wait for the P3 scorer owner: tokenise commands with `shlex.split` and match the make target, and
  `.get` with defaults on agent output.

Unchanged, a known shortcut: unkeyed hashes, so a full rewrite of `log.jsonl` plus `log.head` verifies. Signing
belongs before any real run.

verified: 972dee3 (plus working tree, hashes above) 2026-11-19
