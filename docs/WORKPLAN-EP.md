# Emergence program: work plan

2026-11-19, Opus 5.5. Plan only; nothing run. `EMERGENCE-PROGRAM.md` ("EP") governs the science;
this file governs order, roles and stops.

**Corrections to EP:** the opened price sheet has a Haiku 5.5 row (USD 0.10 / 0.50 per million
input / output), so EP-1's full cap costs about USD 0.18, not 3.50; `spend.MAX_AGE_DAYS = 3`
refuses that sheet after 2026-11-22; `runner._claude` defaults to `claude-sonnet-5-5`; the 1-call
canary replaces EP's 9-call smoke.

## 1. Approval scope

These approvals were relayed. Repo policy: only Alejandro approves. Every paid row is triggered
only by **his verbatim words in `docs/reports/ep-approvals.md`** plus the Rule 8 soft-budget
acknowledgement (a direct key has no provider-enforced cap).

| Item | Status | Stop and ask when |
|---|---|---|
| Wave A build, rung 0 (stdlib, CPU) | Approved | install; file outside the row; network |
| Local commits in `murmuration` | Approved, no push | remote, push, PR, branch |
| Price sheet re-fetch (public page) | Approved, zero cost | login or API call needed |
| Canary: 1 call, USD 0.05 sub-cap, counted inside EP-1 | Approved within EP-1 | the verbatim record is missing; rung 0 has not passed; the pre-registration is not frozen |
| EP-1: Haiku 5.5, direct key, USD 5, 500 calls, at most 1.15M tokens | Approved after rung 0 passes and the freeze | any cap would be crossed; any void condition (section 7); a second process |
| Program API ceiling | Owner USD 10; code stops at USD 9 absolute | never raised; any spend stop means stop and report |
| Doubling n after an "inconclusive" result | **Needs ask** | always |
| EP-2 (Sonnet tier), any API dream rung, any second batch | **Needs ask** | always |
| Local-GPU rungs, T7, any model download | **Blocked**: parked until the host-memory leak is isolated | n/a |
| Cut items (section 9), distillation, `.env*`, push, deletion | **Blocked** | n/a |

## 2. Task DAG

Every task: builder Sonnet 5.5 high; verifier Opus 5.5, fresh context, `interrogate` brief
(section 4); stdlib, no network, no GPU; only the listed files. Acceptance:
`PYTHONPATH=src python3 -m unittest discover -s tests -p '<test file>' -v` passes and the full
`discover` stays green. Size S ≤ 150 lines, about 0.2M build tokens; M about 0.4M (Fermi).

**Frozen until a verdict (no builder touches them):**

| Files | Waiting on |
|---|---|
| `cell.py`, `router.py`, `perturb.py` | A0-1 |
| `spend.py`, `backend_claude.py` | the Opus verification running now |
| `runner.py`, `tests/test_runner.py` | another agent's uncommitted edits |
| `train/` | the T7 builder, still running |

### Wave A0: orchestrator, zero cost

| ID | Goal | Output | Acceptance |
|---|---|---|---|
| A0-1 | EP E0: adversarial verification of `cell.py`, `router.py`, `perturb.py` | `docs/reports/workplan-ep/A0-1.md` | tests rerun, output quoted; accept or return |
| A0-2 | Verdict on `spend.py`, `backend_claude.py` | same folder | B1 waits on "accept" |
| A0-3 | Baseline `discover` count; **analytic rung-0 expectations** per practice and q | `docs/reports/workplan-ep/rung0-expected.md` | exists before A9 starts |

A0-3 must be honest: at q = 0, `Y_play = Y_none`, so HDI = 1 by algebra (validates arithmetic
only); at q = 1 for practice A, adopters on one stale snapshot can still collide, so HDI near 0 is
not guaranteed; A0-3 derives the expected collision rate.

### Wave A: scripted instruments, zero cost (A1–A5, A8 parallel; then A6, A7; A9 last)

| ID | Goal | Files | Interface | Tests must cover (adversarial ones marked †) | Size, after |
|---|---|---|---|---|---|
| A1 | Practice cards and loader | `practices/{A..G}.md`, `src/murmuration/practice.py`, `tests/test_practice.py` | `load(id)` returns `{id, version, text, enforcer, measures, sha256}`; `neutral(card)`; `attach(prompt, card)` returns `(prompt, sha)`; `leak_check(card, texts)` | each card at most 600 B and all seven under 5,000 B; the neutral card has the same byte length † and contains no practice keyword (claim, owner, verify, …) †; a one-byte edit changes the sha; a missing field raises; `leak_check` catches a task answer planted in a card † | S, — |
| A2 | Shared board | `src/murmuration/board.py`, `tests/test_board.py` | `Board(log_path, seed)`; `snapshot()`, `read`, `post`, `claim`, `release`, `end_round()`. The JSONL log is the source of truth; state is an in-memory replay | two agents both claim from the same snapshot, and a collision is logged †; writes made within a round are invisible until `end_round` †; claims are resolved in seeded order (deterministic); `replay(log) == state`; claim expiry; an edited earlier log line is detected (hash chain) † | M, — |
| A3 | EP-1 allocation micro-task | `src/murmuration/trapbench/alloc.py`, `tests/test_alloc.py` | `gen(seed)` returns 6 tasks with checks plus a naming rule; `score(log, taskset)` returns `{distinct_passing, slots, duplicates, name_collisions}` | byte-identical per seed; train and held-out disjoint; scoring reads only the log (hand-written log) †; floor (all pick task 0) fails, oracle scores 4 of 4; a rejected slot scores 0, so enforcement is not free † | S, — |
| A4 | Order parameters | `src/murmuration/orders.py`, `tests/test_orders.py` | `compute(log, f=0.75)` returns the eight EP quantities with units: entropy, read:write, claim-collision rate, convergence time, specialisation, cascade length, fact retention, sprawl | known answer per quantity from a hand-written log †; undefined is `None`, not 0 or inf †; log only, never agent objects † | M, — |
| A5 | HDI and EG | `src/murmuration/stats.py` (additions only), `tests/test_stats.py` | `hdi(rows, cluster, n, seed)` returns `{point, lo, hi, denom_ci, undefined, degenerate_resamples}`; `emergence_gain(team, nominal)`; `nominal_group(rows)`, which pools and de-duplicates | a denominator CI containing 0 returns `undefined` with a reason, never a number †; known-answer synthetic data; HDI below 0 and above 1 allowed; resampling is by cluster (a permutation within a cluster leaves the result unchanged) †; seeded determinism; the old 6 tests pass | S, — |
| A6 | Scripted adopters and team loop | `src/murmuration/adopters.py`, `src/murmuration/team.py`, `tests/test_team.py` | `ScriptedAdopter(q, seed)`; `run_episode(taskset, arm, practice, n_agents=4, rounds=2, backend, seed, budget)` returns a record that carries `instrument_validation: true` | neutral card ignored by construction; q = 0 equals `none` †; budget charges card bytes, reads, rejected actions †; board reachable only through the router (direct access raises) †; label on every record | M, A1 A2 A3 A7 |
| A7 | Enforcement hooks | `src/murmuration/enforce.py`, `router.py` (sole owner), `tests/test_enforce.py`, `tests/test_router.py` | `PREDICATES[A..G]`; `router.act(action, board, enforced)` returns `(status, reason)` under default deny | per practice, violation refused and compliant action admitted; enforcement off: violation executes and is logged †; a refusal costs the turn; same-model verification raises the existing `IndependenceError`; 7 router tests pass | M, A0-1 A2 |
| A8 | Dream control and poison tasks | `src/murmuration/consolidate.py`, `src/murmuration/trapbench/poison.py`, `tests/test_consolidate.py` | arms A–E: none; raw log (retrieval over the cap); equal-token retrieval; placebo (shuffled other-task transcripts); scripted re-verify (replay claims, withdraw failures by appended supersede). `poison.gen(seed)`: true notes, wrong note, "confident poison" | E withdraws both poisons, keeps every true note †; supersede append-only †; C and D byte-matched to the dream budget †; no gold canary in memory †; dream bytes charged in the cap | M, — |
| A9 | Rung 0 driver and instrument checks | `src/murmuration/rung0.py`, `tests/test_rung0.py` | `run(practices, qs=(0, .5, 1), sets=15, seed)` returns a table compared against `rung0-expected.md` | floor fails, oracle passes; no duplicate executes under `code`; **mutations turn it red** †: no claim lock, no stale snapshot, scoring from agent state, a wrong expectation; rewrite vs delta-append moves fact retention as expected | M, all of A |

### Wave B: EP-1

| ID | Goal | Owner, files | Acceptance and must-cover |
|---|---|---|---|
| B0 | Re-fetch the price sheet within 3 days of the canary | Orchestrator; `docs/reports/price-sheet.json` | sha and date recorded; Haiku row not null |
| B1 | One program ledger with batch sub-caps (S) | Sonnet; `spend.py`, `tests/test_spend.py`; after A0-2 | One global ledger at USD 9.00; batches `ep1-canary` (0.05, 1 call) and `ep1` (5, 500 calls, 1.15M tokens, includes the canary); token meter = recorded usage + in-flight upper bound. Tests: † ceiling above 9.00 raises; † batches share the 9.00; uncharged reserve counts at worst case; meter stops the run |
| B2 | EP-1 Claude team adapter and launcher (M) | Sonnet; `src/murmuration/team_claude.py`, `__main__.py` (`ep1` subcommand), `tests/test_team_claude.py`; after B1 | `ClaudeClient` unchanged; prompt = system + card or neutral + snapshot; malformed reply = logged no-op, lost slot; model required, no default (†); `usage` input over 2,000 voids the episode; key from `MURMURATION_EP1_KEY`, read only in `__main__`. `fakeclaude` tests: † a dated alias passes only if in the sheet's `aliases`, else void; missing `usage` stops the batch; † `ANTHROPIC_BASE_URL`/`HTTPS_PROXY` at launch do not change the destination; † a canary key never appears in `runs/`, ledger or exceptions; call 501 refused; a high-usage responder hits the USD cap. Single process (no ledger lock) |
| B3 | Pre-registration `prereg/EP1.md` | Fable drafts; Opus checks every number against EP 2.2, 6 and this file | It must settle the section 5 decisions. `code_tree_hash:` is left blank |
| B4 | After B1–B3: whole EP-1 schedule against the **fake** server, worst-case usage | Orchestrator | every stop fires; projected USD; analysis table stamped `FAKE`; `docs/reports/workplan-ep/B4.md` |
| B5 | Freeze | Orchestrator | section 5 order; `check_prereg` passes |
| B6 | Canary | **Parent**; key in the environment only | 1 call; model ID accepted; usage present; one ledger line; no key text anywhere. Any failure stops the program |
| B7 | EP-1 | **Parent**, single process | completes or stops at the first cap; partial JSONL valid |

### Wave C: analysis and claims

| ID | Goal | Owner | Acceptance |
|---|---|---|---|
| C1 | Frozen analysis on frozen results | Orchestrator | `check_prereg` passes; table in `docs/reports/EP1-results.md` |
| C2 | Report draft from frozen results only | Sonnet | every number cites a results file and line |
| C3 | Claims check | Opus | each number recomputed or removed; kill-table reading quoted |

### Wave D: parked

Dream ladder rungs 1–5 with a model, local-model tiers (EP rung 2) and EP-2 wait for the leak fix
and an owner ruling. Nothing is sized here.

## 3. Roles and escalation

| Role | Model | Does | Never |
|---|---|---|---|
| Consultant | Fable 5.2 | B3; design contradictions; failed kills; tasks after two failures | builds, runs |
| Orchestrator, verifier | Opus 5.5 | A0, B0, B4, B5, C1, C3; dispatch; reviews; local commits | builds unless escalated |
| Builder | Sonnet 5.5 high | one task row | commit, push, install, other files, paid calls |
| Bulk | Haiku 5.5 | chores no script can do; EP-1's cells under test | judging |
| Parent | — | launches B6, B7 | — |

**Fable consult triggers:** EP 3 says "one practice at a time" but EP-1 combines cards A and C;
the `none` arm keeps the board, so EP-1 has no nominal group and EG needs an added arm; a rung-0
expectation contradicts EP; a kill criterion fires; two failed acceptances. Answers go to
`docs/reports/decisions.md`; one that changes a gate goes to the owner.

## 4. Per-task verification protocol

1. **Deterministic first:** the orchestrator reruns the acceptance command and quotes its output
   in the same turn.
2. **Mutation check:** the verifier breaks each † invariant once; the suite must go red, else the
   task returns.
3. **Adversarial review:** an Opus subagent gets the diff, task row and `interrogate` brief, never
   the builder's summary. Targets: hidden network or writes, `None` recorded as 0, metrics read
   from agent state, key leaks, files outside the row, prompt-length confounds. A second
   independent reviewer applies mattpocock `code-review` (Standards, Spec).
4. `git diff --stat` touches only the listed files.
5. **Evidence:** `docs/reports/workplan-ep/<ID>.md`: command, output, verdict, build tokens, open
   findings.
6. One return with findings; a second failure goes to Fable (design) or Opus (build).

## 5. Pre-registration discipline

**Decided before the freeze, in `prereg/EP1.md`:** primary Y (distinct passing tasks per 4
slots, both counts); the A/C split (Fable); arms and neutral card; n = 15 task sets, seeds,
held-out sets; smallest effect of interest (20 points); kill and void table; model ID and aliases;
price sheet sha; analysis entry point; the bootstrap choice (`paired_bootstrap` warns below about
20 clusters: accept with a caveat, or build a bias-corrected interval first).

**Freeze order:**

1. Rung 0 report accepted.
2. `code_tree_hash` covers `src/`, `practices/`, `tests/` only (not `train/`, which T7 may write;
   not the prereg, which holds the hash). `git status --short --ignored` on those paths shows
   nothing but `__pycache__` (`tree_hash` skips that, but hashes any ignored `.jsonl`).
3. Local commit, never `--no-verify`.
4. Hash into `code_tree_hash`; the prereg's own sha256 and the config hash go only in
   `docs/reports/prereg-freezes.md`; second local commit.
5. `stats.check_prereg` passes.

Any later code change means a new freeze and a new run. Canary data never enters the analysis.

## 6. Cost and energy per wave

| Wave | Tokens | USD | Energy |
|---|---|---|---|
| A0–A | about 3.5M build and verify (Fermi) | subscription: unknown, not zero | CPU, not measured |
| B0–B5 | about 1M build; fake server | 0 | CPU, not measured |
| B6 canary | ≤ 2,300 | estimate 0.0004; cap 0.05 | provider-side unknown |
| B7 EP-1 | ≤ 1.15M | estimate 0.18 = 500 × (2,000 × 0.10 + 300 × 0.50) / 1M; cap 5 | provider-side unknown |
| C | about 0.5M build | 0 | CPU |
| D | parked | — | ≤ 0.86 MJ per GPU-hour, own approval |

Actual USD = usage × sheet, from the ledger; unknown cost is never 0.

## 7. Risk register and stop conditions

| Risk | Stop or guard |
|---|---|
| Spend | Stops: global USD 9; EP-1 USD 5, 500 calls, 1.15M tokens; canary USD 0.05. Reserve before every call; missing usage stops the batch. Any stop: halt, report, never raise a cap |
| Key safety | `MURMURATION_EP1_KEY` only, at launch; never a file, printed or in errors; proxy and base-URL variables ignored; redirects refused; agents never read `.env*` or run `env`; canary-key grep over `runs/` in B4 and B6 |
| Wrong model | Returned ID not in the sheet's aliases voids the episode; never the local proxy |
| Instrument void | Floor passes, oracle fails, a duplicate executes under `code`, model mismatch, a rung-0 mutation stays green, hash mismatch: fix, no claim, re-freeze |
| Leakage | `leak_check` on every card; canaries in gold answers; held-out sets |
| Collusion and lock-in artefacts | Enforcement zeroes collisions by construction, so arms are compared on Y and cost, never on the enforced quantity; a stale snapshot per round is not concurrency; equal-length neutral card; one model family: report rho, claim nothing about diversity |
| Scripted as evidence | Rung-0 records carry `instrument_validation: true`; C3 strikes any rung-0 number shown as model behaviour |
| Concurrency, shared host | One process per ledger; disjoint builder files; no GPU, ports, OmniRoute or `spark-vllm` |

## 8. First 8 tasks to dispatch now

1. A0-1 (Opus): verify `cell.py`, `router.py`, `perturb.py`.
2. A0-3 (Opus): baseline count and `rung0-expected.md`.
3. to 8. A1, A2, A3, A4, A5, A8 to Sonnet builders in parallel (disjoint files).

The Fable consult (A/C split, nominal arm) goes out in parallel.

## 9. Cut by the five-step filter

- SQLite in `board.py`: JSONL plus replay suffices; add only if replay is slow.
- The 9-call smoke: replaced by the canary.
- `runner.py` as EP-1 host (frozen, SQL-specific).
- EG in EP-1 (needs a nominal arm outside 480 calls); rung 0 only unless Fable adds it.
- Error correlation rho: a read-off, not a test.
- Owner cuts unchanged (dream dose, T7 stage 2, LoRA, E9-1/2, personas, debate, criticality,
  distillation).
- Predicates B, D–G serve rung 0 only; paid tests needs-ask.

## Owner questions

1. **Key delivery:** how does the key reach the launch environment unseen by any agent? Proposal:
   you run `read -s MURMURATION_EP1_KEY && export MURMURATION_EP1_KEY` in a terminal with no agent
   or SDK process (a project-only name, so no other tool bills it), then launch
   `python -m murmuration ep1 …` in that terminal (the parent drives it via Orca; a fresh agent
   Bash shell would not inherit the variable).
2. **Verbatim approval:** restate the EP-1 and canary approval and acknowledge the direct key has
   no provider-enforced cap, for `docs/reports/ep-approvals.md`.
3. **Freeze commit:** may it include other agents' uncommitted files (`cell.py`, `router.py`,
   `perturb.py`, `spend.py`, `backend_claude.py`, `runner.py` edits) once verified, and exclude
   `train/` from the hash?
4. **Smallest effect:** 20 points acceptable at n = 15?
5. **Board:** JSONL-only instead of SQLite?

verified: 972dee3 (plus working tree) 2026-11-19
