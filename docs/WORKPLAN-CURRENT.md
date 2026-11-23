# Sortie (repo `murmuration`): current work plan and checklist

Updated 2026-11-20 by the orchestrator (Opus 5.5). This file is the live checklist. Detail lives in
`prereg/EP1.md`, `docs/reports/ep1-design-notes.md`, `docs/WORKPLAN-ALIGN.md`,
`docs/reports/review-integration.md` and `docs/ARCHITECTURE.md` (threat model, section 9a).
Roles: Fable 5.2 plans and pre-registers; Opus 5.5 orchestrates and verifies (a different Opus than
the implementer, fresh context); Sonnet 5.5 builds; Haiku fetches; outside reviewers (GPT via Codex,
Cursor/Grok) attack. Status words: NOT STARTED / INSTRUMENTED / PILOTED / EVIDENCED / OUT OF SCOPE.

For the next Codex session, start with the [Claude handoff](reports/HANDOFF-claude-opus-20261120.md)
and its [verification and corrections](../coordinator-outbox/tremor-execution-20261120.md#handoff-verification).

## State as of 2026-11-20 18:10 UTC (reconciled against evidence files; history kept)
Rows: 65 done [x], 27 open [ ], 3 in progress [~] (total 95). Rows marked done because an addendum or
later row replaced them say SUPERSEDED or CLOSED in the row. Two items (Lean static-scan clause, `ui/` content)
were checked for existence only. No number in this file was changed.

MVP-critical path:
| Row | State |
|---|---|
| Parser gate (change 19 fix) | ACCEPTED WITH NOTES. See [P3 gate](reports/workplan-ep/P3-gate.md). |
| Pilot 3 build + gate | DONE. The independent gate allowed Pilot 3 to run. |
| Pilot 3 run | DONE. The order rule selected `shared`. Clearance criterion 2 failed. |
| EP-1 freeze | BLOCKED on preregistration author review of criterion 2. See the [trace packet](reports/workplan-ep/P3-clearance-criterion-2.md). |
| EP-1 run | OPEN (spend cap code still USD 10 hard cap; EP-1 itself is inside USD 5.25 stop) |
| EP-1 analysis + claims check | OPEN |
| Public repo README + video | Explainer linked from the public README at `ba08c0a`. Pilot 3 documentation updates are local. |

## Goal
Produce **one pre-registered number that is allowed to be null**: for one coordination practice
(claim-before-work, card A), does giving it to a small Claude tier as a short instruction card recover
the outcome of enforcing the same rule in code, at a matched budget, scored deterministically from logs?
Report the three raw contrasts with intervals first; the ratio (HDI) only if enforcement clearly helps.
Everything else (memory, dreaming, Lean, auto-research, local models) is sequenced after this number.

**The number must be trustworthy, so the instrument is verified three ways:** two independently written
Python scorers plus a third scorer whose soundness is checked by the Lean 4 kernel (pattern and toolchain
taken from the owner's QGrid project). Any disagreement voids a run. Task generators are tested against a
second, independent generator (exact quantum statevector tasks, from QGrid's simulators) before any
cross-domain claim.

What this is not: a frontier model; evidence about oversight, control, alignment or governance in general;
a novelty claim (two 2026 papers already compare soft and structural practices in model teams); a quantum
advantage claim; a use of QGrid's grid-site domain (only its Lean and simulator tools are used).

## Budget and approvals (owner)
- API: owner ceiling USD 10 (hard cap in code across the pinned ledger directory); USD 9 per ledger file.
  Allocation: EP-1 USD 5 (expected about USD 0.3), canary USD 0.05 inside EP-1, auto-research `ar1`
  USD 3 (cannot open until EP-1 settles), instrument pilot USD 0.50 / 150 calls from the USD 2 reserve
  (approved 2026-11-20; opens only after the canary completes). USD 1.50 stays unallocated.
- GPU: 12 GPU-hour cap for T7, about 3.8 used; T7 parked. The local 4B model is for the post-EP-1
  memory-warning replication.
- Approved: EP-1 design (3 arms x 20 task sets), 20-point smallest effect, Haiku-only padded canary
  (90,000 bytes), local commits only (no push), freeze scope with `train/` excluded, the instrument
  pilot, the Qwen3.5-4B download (done), QGrid's Lean toolchain and simulator tools (repo-local installs).
- Owner actions pending: Console spend limit (USD 10 or less); a one-word "confirm" immediately before
  the canary; human baseline (about ten manual tasks).
- Tools: Lean 4.35.0 at `data/tools/lean` (repo-local); PsiQDK not usable here (proprietary native
  simulator, no aarch64 build); QGrid's numpy simulator and our `lab/quantum/gatesim.py` instead.

## Checklist

### Phase 0. Foundations (done)
- [x] Repo, three local commits (last 36bab4b), research notes 01-22, verification reports.
- [x] Scripted instruments: board, orders, practice cards, adopters, team loop, rung-0 driver, perturbation
      matrix, poison/consolidate, monitors, evaluator seal, enforcement predicates, router wiring.
- [x] Router/cell/perturb accepted with notes after five Opus rounds (A0-1R5).
- [x] Rung 0 GREEN over 1,080 scripted episodes; G1 ACCEPT-WITH-NOTES; D1-D4 fixed.
- [x] Spend ledger: hard cap, per-file cap, batch sub-caps, token meter, canary exception, overspent and
      unbatched-ledger rules (G0-2R ACCEPTED-WITH-NOTES).
- [x] Two independent adversarial reviews (GPT, Cursor) integrated; statuses relabelled; coverage table
      removed from the shareable draft; prior art first; threat model added.
- [x] T7 weight-edit smoke run and parked (configuration results only: 0/20, 8/20, 1/20 under an 8k cap).

### Phase 1. Make the instrument honest (mostly done, zero cost; open boxes are tracked in Phase 2)
- [x] Model-loop fixes from G1b (ordered round actions, task-id allowlist, HTTP mapping, void rules,
      seeded claim order, reachable refusal stops, gold-leak scan): Opus implementer running. evidence: docs/reports/workplan-ep/G1b-R2.md (R-1..R-6 closed; implemented and re-gated).
- [x] EP-1 token cap 1,250,000 and `ar1` batch in `spend.py` (landed; awaiting re-verification).
- [x] `pilot` batch spec (sibling of `ep1`, USD 0.50 / 150 calls) once the pilot is approved. evidence: src/murmuration/spend.py (`pilot` batch) and runs/spend/pilot.jsonl (pilot 1 ran under it).
- [x] Model-free canary suite (`tests/test_canaries.py`): 'accept if present' failures must score zero. evidence: tests/test_canaries.py; prereg/EP1.md (canary suite row); suite counts in docs/reports/workplan-ep/G1b-R2.md.
- [x] HDI margin rule + `analysis.py` (refuses scripted/FAKE records on model figures; n as task sets). evidence: src/murmuration/analysis.py (`summarise`, margin rule); docs/reports/workplan-ep/G1b-R2.md row R-6 (11 vs 12 sets).
- [x] Independent second scorer `alloc2.py` + differential test against `alloc.py`. evidence: src/murmuration/trapbench/alloc2.py; docs/reports/scorer-differential.md.
- [x] Static card check `cardcheck.py` + two pilot-only leakage cards (states-the-check, keyword-stuffed). evidence: src/murmuration/cardcheck.py, tests/test_cardcheck.py; docs/reports/card-A-review.md (addendum: cardcheck OK).
- [x] Auto-research scaffold under `lab/` (unrun; outside the freeze hash). evidence: lab/autoresearch/loop.py, lab/tests/test_loop.py (scaffold only; unrun, as scoped).
- [~] Prompt and response telemetry records request bytes, rejects oversize input locally, and logs a
      validated optional provider response ID. Provider-side input truncation is explicitly unknown.
      Offline verification: 94 adapter/team tests and five independent loopback metadata cases passed.
- [~] External log-head anchor: cell and board receipt comparison verified offline (lab/log_head_receipt.py; two regression tests and independent fixture replay). Actual independent receipt custody remains open.
- [x] Card A review (`docs/reports/card-A-review.md`, independent Opus model reviewer; the owner may
      override): APPROVE with the stated paraphrase limit; card v1 kept (sha256 9875048b...). Decision
      (orchestrator): v1 stays; its two lines beyond the code arm ("one at a time", release etiquette)
      cannot move Y but can move the false-done and release-refusal read-offs: pre-register this as a
      limit (pass to Fable with the next prereg edit). Optional 166-byte v2 (exact V1 match) available.
- [x] EP-1 batch driver `ep1.py` + CLI (dry-run, canary, pilot, run, analyse; paid commands refuse
      without an owner-confirm flag; key only from the CLI process environment); 28 tests, 21/21 mutants.

### Phase 1b. Formal and independent verification with QGrid's tools (approved 2026-11-20, zero API cost)
- [x] Install Lean 4.35.0 (official aarch64 archive, core only, no Mathlib) under `data/tools/lean`:
      sha256 c8f0f8a3...b028 matches the release digest; 3.1 GB extracted; `lean --version` OK. Smoke test:
      QGrid's Lean library built (13 jobs) in a scratch copy; its 11 theorems use only propext, Quot.sound,
      Classical.choice (no sorryAx).
- [x] `formal/alloc_score` built: 52 kernel-checked theorems, axioms propext / Quot.sound /
      Classical.choice only. FINDING: `distinct_passing <= slots` and `Y in [0,1]` are false for arbitrary
      logs (counterexample); they need at most one accepted work per agent; after the G1b fix Y can reach
      1.5. Primary-outcome definition goes back to Fable before the freeze. Differential (5,000 logs, all
      explained): vs alloc2 2,283 (alloc2 counts refused and unknown-task releases in false_done: wrong by
      our no-op rule); vs alloc 1,081 (alloc accepts 30.0 for 30: rule set to integers only).
- [x] Align all three scorers to the decided outcome definition and the two settled rules; differential 0. evidence: docs/reports/scorer-differential.md (one definition; 10,000 logs, 0 disagreements per pair, see the Phase 2 row).
- [x] Original spec for the Lean scorer: the EP-1 allocation scorer written as Lean definitions, compiled to an
      executable that reads a board log (JSON) and prints the scores; kernel-checked theorems at least:
      unknown-task events change no score; Y in [0, 1]; distinct_passing <= slots; clobber rule (last
      writer per name survives); score is deterministic and extensional; check_iff for every predicate.
      Axiom audit: `#print axioms` must show only the standard axioms (no sorryAx); a static scan refuses
      `sorry`, `admit`, new `axiom`, `native_decide`, `unsafe`, `implemented_by`, extra imports. evidence: formal/alloc_score/ (AllocScore, Axioms.lean), tests/test_formal_alloc.py, docs/reports/scorer-differential.md. The static-scan clause was not re-verified when reconciling.
- [x] Third-scorer gate: Python `alloc`, independent `alloc2` and Lean `AllocScore` agree on 5,000 seeded
      logs; disagreement in a real run voids it. Lean missing or unpinned = INVALID, never pass. evidence: docs/reports/scorer-differential.md (alloc, alloc2, Lean agree on 10,000 seeded logs; the Phase 2 row).
- [x] Optional Lean proof of abstract HDI decision logic and exact reservation arithmetic. Evidence: lab/ep1_gate_arithmetic.lean; six theorems kernel-checked and independently reviewed. Runtime and floating-point parity remain separate checks.
- [x] PsiQDK checked and NOT installed: its native simulator `workbench-sim-native` 0.3.0 is proprietary
      and has no aarch64 wheel (the other PsiQDK packages are Apache-2.0 pure Python but cannot simulate
      without it). QGrid itself falls back to its numpy statevector simulator.
- [x] Differential test: QGrid's numpy statevector simulator (imported read-only, not copied) vs our own
      independent stdlib gate-level simulator (`lab/quantum/gatesim.py`): 0 disagreements over 65
      instances / 329 statevectors (n 1 to 10, edge cases, k to optimal+2), amplitudes incl. global
      phase, probabilities within 1e-12, optimal iterations exact; run in the `murmuration-t7:1`
      container (host has no numpy; host test skips with that reason). Report: `lab/quantum/`.
- [x] Local model: Qwen3.5-4B downloaded to `data/hf/` at revision 851bf6e8...cd0a, LFS sha256 verified.
- [ ] `trapbench/qstate` (after EP-1, before any cross-domain claim): an independent task generator with
      exact checks (choose Grover iterations or a marked set to reach a target probability; statevector
      verdict), used only as a held-out family from a different generator. No advantage claims. STILL OPEN (after EP-1, by design).

### Phase 2. Gates (zero cost)
- [x] G0-2R2: ACCEPTED-WITH-NOTES (worst sequence USD 8.47; egress test 10/10; 15/16 mutants). Open note: a
      stopped batch could count as settled (canary stopped, then ep1 settled by hand, then ar1 opens).
- [x] G0-2R3 (fresh Opus): ACCEPTED-WITH-NOTES; 695 OK, 16/16 mutants killed. N10 (fake `--base-url` canary
      could settle in the real ledger) fixed: `--base-url` now needs `--ledger-dir`, test added. N2 blocks only ar1;
      N5, N6 are operator checklist items for the canary day.
- [x] Final fix round (Opus implementer): settle refuses after any stop in the subtree; `invalid_log` stop
      reason; all-stopped batch stop removed (ruling 1); canary plan uses the `ep1 canary` CLI path and the
      price-sheet rule. Then a fresh Opus narrow re-gate of spend and driver.
- [x] Prereg amended for rulings 1-3 (Fable; pre-freeze rows 8-12).
- [x] Ruling 3 in `analysis.py`: label uses the cluster-bootstrap upper bound alone; the kill read-off keeps
      both intervals (`hi_below_soi_both`); test fails on the old rule (mutant checked). Prereg rows 12 and the
      section 11 table still say "code not yet matching": flip with the next Fable pass.
- [x] Card A review addendum: card bytes unchanged, cardcheck OK against scorer 07ae29d8; verdict unchanged.
- [x] G1b re-gate: fresh Opus on the fixed model loop with the real client against the fake server. evidence: docs/reports/workplan-ep/G1b-R2.md (ACCEPTED-WITH-NOTES).
- [x] Full suite green on a quiet machine, 3 of 3 runs (OK, 1 torch-only skip) plus the lab suite (2026-11-20).
- [x] Three scorers agree on 10,000 seeded logs (0 disagreements each pair, incl. `valid`); strict input
      rule (episode action log only); Lean `no_action_not_valid` proved.
- [x] Local commit after both gates accept: b4a820e (owner, 2026-11-20; 89 files; no key, no runs/ or data/).
- [ ] B4: whole EP-1 schedule against the fake server at worst-case usage, every stop fires, table stamped FAKE.
      Verified on Spark: 60 EP-1 episodes, FAKE-stamped report, floor 0.25 and oracle 1.0 in all arms.
      Eight full-schedule fault probes stopped as expected: HTTP 400, transport aborts, first-block malformation,
      model mismatch, excessive reported usage, and lowered call, token and synthetic USD caps.
      The full-plan loopback probes now reproduce the aggregate and per-arm malformed thresholds
      and three scorer stops. A separate full-reservation probe reproduced the retry and no-room boundaries.
      Outstanding: the author-specified decoy-output guard and a frozen-SHA matrix rerun.
      Loopback outputs and scripts: `/tmp/murmuration-b4.cUIEWE`. See the [B4 evidence matrix](reports/workplan-ep/B4-offline-evidence.md) for the remaining boundaries and frozen-SHA rerun.

### Phase 3. First money (owner "confirm" required at each step)
- [x] Price sheet refetched 2026-11-20: every row re-verified against the pricing page, unchanged; only
      `fetched` moved (sha256 16b204c2...984f). The canary, pilot and EP-1 must all finish by 2026-11-23 UTC.
- [x] Fake dry run GREEN 2026-11-20 (canary, pilot and EP-1 complete on the fake server).
- [~] Canary RUN 2026-11-20 under the owner's "Confirm": ok, complete, returned model claude-haiku-5-5,
      46,605 input + 4 output tokens, ledger USD 0.0046625 (worst case 0.01815); no key fragment in outputs.
      OPEN: the owner compares the Console cost for that one request with USD 0.0046625. First look
      (Console "data as of 13:43 UTC", org SeaBridge.AI, all models, last 7 days): no Nov 20 usage shown, only
      Sonnet 5.5 on Nov 14-15. Not yet a match. Canary ledger written 13:22:32 UTC. Pilot blocked until resolved. Run part DONE (evidence: runs/spend/canary.jsonl, runs/ep1-live/canary). Console comparison STILL OPEN, but timing changed: required before publishing results, not before EP-1 (D6, docs/reports/ep-approvals.md addendum 9). The 'pilot blocked' clause is SUPERSEDED: pilots 1 and 2 ran.
- [x] Pilot 1 RAN 2026-11-20 under owner "CONFIRM PILOT": STOPPED `void_model` / `malformed_states_check` after
      11 episodes, 88 calls, USD 0.0115 (directory total USD 0.0162 of 10). The pre-registered stop worked.
- [x] Pilot 1 diagnosis (`docs/reports/pilot-1-diagnosis.md`, fresh Opus):
      (1) TRUNCATION: hidden default thinking on Haiku 5.5 shares the 300-token cap (all 88 replies hash-match
      the ledger; nothing stripped); token use varies by card, so turns could be lost unevenly across arms.
      Prereg error: it assumed "no thinking parameter" meant no thinking (EP1.md:308).
      (2) `board_error:ValueError` = designed refusal of a claim loser's release (board.py:138); Y and the
      log unchanged; only refusal labels differ by arm.
      (3) HERDING: all agents claim task 0 in round 1, so Y is only 0.5 or 0.75: low sensitivity.
- [x] Fable decided (prereg pre-freeze changes 13-17): thinking explicitly OFF (docs: Haiku 5.5 "Thinking off
      at high effort or below"), max_tokens stays 300, no cap moves; fallback on a 400 is max_tokens 1,000 (owner
      ask). Herding: task order seeded per agent, no arm in the seed (AWAITS OWNER CONFIRM). Refusal labels: note
      only. Pilot 2: `pilot2` USD 0.25 / 260 calls / 598,000 tokens, 240 scheduled; unallocated falls to USD 1.25
      (AWAITS OWNER CONFIRM; since given, see the 'You got my approval' row and docs/reports/ep-approvals.md addendum 6). Ruling 3 notes flipped. Opus implementer running; then fresh Opus re-gate.
- [x] (superseded) Fable decides the fix: thinking explicitly off (verify the API parameter for Haiku 5.5 against the
      docs first) or `max_tokens` about 1,000 (token caps to about 1.5M); and whether herding needs a design
      change (it is the phenomenon card A targets, so maybe not). Prereg diff recorded; fresh Opus re-gate. SUPERSEDED by the row 'Fable decided (prereg pre-freeze changes 13-17)'; evidence: prereg/EP1.md changes 13-17.
- [x] PROCESS SLIP (found by H3, 2026-11-20): the canary and pilot 1 ran while the G1b re-gate of the fixed
      model loop was still open (G1b-R said REJECT; defects 1-6 were fixed but the fresh re-gate never ran;
      G0-2R3 covered spend and driver only). Spend was USD 0.016 and both runs are instrument validation only.
      Rule from now on: the G1b re-gate (fresh Opus, real client vs fake server, including the pilot-1 fixes)
      must ACCEPT before pilot 2. CLOSED; evidence: docs/reports/workplan-ep/G1b-R2.md (fresh re-gate ACCEPTED-WITH-NOTES; defects R-1..R-6 closed before pilot 2 ran).
- [x] Pilot-1 fix round implemented (Opus): thinking disabled on every request (fake server 400s without it;
      a thinking block voids and stops), max_tokens 300; per-agent order behind an option, default OFF (prompts
      byte-identical to HEAD); `pilot2` USD 0.25 / 260 / 598,000, `p2` id prefix; all caps total USD 8.75; 724 tests
      OK; fake dry run GREEN; real ledger unchanged. Note: Sonnet/Opus 5.5 reject `disabled` (EP-1 is Haiku only).
- [x] Combined gate G1b-R2 (fresh Opus): ACCEPTED-WITH-NOTES. G1b-R defects R-1..R-6 closed (process slip
      closed); 724 tests (22 skipped); dry run GREEN; 20/20 mutants killed; real ledger unchanged. Pilot 2 blocked
      by: (1) task-order decision (prereg 16b says pilot 2 tests changes 13 and 14, code runs shared order with no
      switch); (2) owner ask + confirm USD 0.25; (3) spend re-check of changed spend.py/backend_claude.py (G0-2R4
      running). Note: Sonnet/Opus 5.5 reject `thinking: disabled`; only the opt-in W1-10 runner uses Sonnet, so
      future ar1/W1-10 runs need a per-model thinking setting.
- [x] G0-2R4 (fresh Opus, spend.py + backend_claude.py): ACCEPTED-WITH-NOTES; pilot 2 may run on spend grounds;
      cap counts the USD 0.0162 already spent; 15/15 mutants; real ledger unchanged; pilot2 worst full use USD 0.091.
      Its one fix applied by the orchestrator: `block_types` scrubbed before truncation; test added, fails on the
      old line (mutant checked). backend_claude.py sha256 now 8e122edb... (one-line change after the gate).
- [x] Owner approval 2026-11-20 "You got my approval": pilot 2 with both task orders, USD 0.25 (addendum 6).
- [x] Prereg change 18 (Fable): order decision rule for EP-1 (Y_none 0.30-0.80, >=2 duplicates under none,
      Y_code != Y_none in one set; tie -> shared); thresholds unsimulated.
- [x] Order factor in pilot2 (Opus implementer): 6 task sets, 3 shared / 3 per_agent, seeded without arm;
      `task_order` field; per_agent ids `ep1p2pa...`; 729 tests OK; dry run GREEN (15 episodes per order); ledger unchanged.
- [x] P2-order-gate (fresh Opus): ACCEPTED-WITH-NOTES; 730 tests; 13/14 mutants; gap: `analyse` lacks the
      per-order decision table (Y per set/cond, duplicates, rule pass/fail, picked order).
- [x] Pilot 2 RAN 2026-11-20 16:32 UTC: STOPPED `void_model` / `malformed_states_check` after 11 episodes, 88 calls,
      USD 0.0069 (directory total USD 0.0231). API accepted thinking disabled. Cause: with thinking off the model
      writes visible prose before a correct JSON array; parser requires JSON only (not_json: states_check 10,
      play 6, keyword_stuffed 3, none 2, code 1; 1 oversize). Exploratory: per_agent order showed 0 duplicates
      (n=1 per cell). No key fragment in outputs.
- [x] Fable decided parse fix (change 19): accept last JSON array in reply; prose before ignored/logged; no
      prefill, no token increase; thresholds unchanged; implementer + fresh gate + pilot 3 (addendum 7).
- [x] Public repo PUBLIC at https://github.com/managesg/tremor with README, WORKPLAN, PROPOSAL, hero v2,
      video storyboard (commits d7eb8bd, 5f9d641, ee8d517 ready; push from Spark).
- [x] Parser fix (prereg change 19) implemented by the orchestrator: strict parse first (bare object still
      accepted), fallback to the LAST top-level JSON array with only whitespace after it; text after the array stays
      `extra_text` (change 19's rule; its test-3 example contradicted the rule). `two_arrays` case now accepted by
      design. 63 model-loop tests OK; 2 mutants caught. Shortcut: `extra_text_bytes` not logged yet.
- [x] Pilot 3 batch and decision table gated and run. The batch completed 30 episodes,
      240 calls, zero voids. The local analyser selected `shared` under section 13.16b.
      Evidence: docs/reports/workplan-ep/P3-gate.md, runs/ep1-live/pilot3, prereg/EP1.md section 18.
- [ ] Resolve Pilot 3 clearance criterion 2 with the preregistration author before freeze.
      The maximum was 263 output tokens against a ceiling of 150, with zero truncated replies.
- [x] Owner addendum 8 2026-11-20 "Yes go ahead with your recommendations please": dual-use rulings granted
      (lines 2, 3, 4); team-size ruling granted (>8, 16/32); training re-approved (line 4 adapter); line 8
      kept; Console limit to USD 170; push commits from Spark; proceed pilot 3 and EP-1 under new budget.
- [x] Pilot 2: new `pilot2` batch from the unallocated USD 1.50 (about USD 0.02 expected), owner confirm. DONE as `pilot2` USD 0.25 / 260 calls (see the 'Pilot-1 fix round' and 'Pilot 2 RAN' rows); evidence: runs/spend/pilot2.jsonl, runs/ep1-live/pilot2/final.json.
- [ ] Console check of the canary (46,605 in / 4 out, Haiku 5.5, Nov 20): deferred by the owner (Console
      lag), required before EP-1. STILL OPEN; timing SUPERSEDED: required before publishing results, not before EP-1 (D6, docs/reports/ep-approvals.md addendum 9).
- [x] Human baseline (about ten manual tasks) or its absence stated as a limit. SUPERSEDED by D5 (docs/reports/ep-approvals.md addendum 9): no human baseline; its absence must be stated as a limit in the write-up.
- [ ] Price sheet: the current window ends 2026-11-23. Refetch and restart the three-day window if EP-1
      runs after that date. Pilots 2 and 3 have run. EP-1 awaits clearance criterion 2 review.
      Evidence: docs/reports/price-sheet.json.

### Phase 4. EP-1 (the number)
- [ ] Freeze: commit, write `code_tree_hash`, `prereg-check` passes, second commit. STILL OPEN (prereg/EP1.md: `code_tree_hash:` blank, status DRAFT).
- [ ] Run EP-1 in one process: 3 arms x 20 task sets x 8 calls; stops at USD 5 / 500 calls / 1.25M tokens. STILL OPEN (no EP-1 episode run).
- [ ] Analysis with both scorers agreeing; raw contrasts with intervals; HDI only under the margin rule;
      inconclusive reported as inconclusive. STILL OPEN.
- [ ] Opus claims check; write-up drafted by Sonnet from frozen results only. STILL OPEN.

### Phase 5. After EP-1 (each needs its own approval)
- [ ] No-API replication of the one-line memory warning on planted notes (local 4B model; download gate).
- [ ] Cross-agent error correlation and three-copies-plus-dissenter on those traces.
- [x] 3.9 case study: the 'accept if present' failure family as a write-up. Evidence: docs/reports/workplan-ep/R3-scorer-evidence-case-study.md.
- [ ] Extend exactly one dimension depending on EP-1 (more blocks, or a second model family).
- [ ] Deferred: auto-research over cards (`ar1`, held-out family from `trapbench/qstate`), dreaming ladder.
      Not used: QGrid's grid-site domain and its Python mirror. Cut: quantum search as a proposer or any
      quantum claim, weight-edit thread, joules headlines, permissions-decay headline, persona vectors,
      recursion and CoT branding. STILL OPEN (after EP-1, by design).

### Phase 5b. Research fit: Anthropic Residency posting (job 5438311008, read 2026-11-20)
Honest fit, three levels. DIRECT = the frozen EP-1 or a planned Phase 5 item measures it. REACHABLE = a
named, costed item below would let us measure a slice of it. NOT = no credible path; said plainly.
Mentor names are from the posting; "fit" means our question sits in that team's stated area, nothing more.

| Area (posting) | Fit | What we can honestly contribute | Closest mentors |
|---|---|---|---|
| Scalable oversight | REACHABLE (slice) | 3.9 "oversight with systematic errors": the 'accept if present' family found in our own harness, frozen as canaries that must score 0; a write-up | Samuel Marks, Ethan Perez |
| Adversarial robustness and AI control | REACHABLE (defensive slice) | Planted-note memory poisoning and the one-line warning, replicated on the local 4B model (no API) | Nicholas Carlini, Evan Hubinger |
| Model organisms | NOT (as organisms) | Our leakage cards (`states_check`, `keyword_stuffed`) test whether an instruction that names the grader changes behaviour: a specification-gaming probe, not a trained organism | Evan Hubinger |
| Model internals and interpretability | REACHABLE (small) | Read-only probe on the local 4B model for planted-note adoption, must beat a TF-IDF baseline | Jack Lindsey, Belinda Li |
| Safeguards research | REACHABLE (evaluation integrity) | Kernel-checked scoring: three independent scorers, one proved in Lean, any disagreement voids; a method for trustworthy evaluation logs | Ethan Perez |
| AI welfare | NOT | No instrument measures a welfare-relevant state | none |
| Frontier red-teaming (cyber, robotics, crypto) | NOT | Offensive work excluded by rule | none |
| ML systems and RL | REACHABLE (environment only) | A multi-agent environment with a verifiable, kernel-checked reward and spend-capped episodes: RL-environment-shaped; we do not train | Sara Price (training data/environments), Jascha Sohl-Dickstein (no direct fit) |
| Multi-agent governance (rec. direction 3.17) | DIRECT | EP-1: does an instruction card recover the effect of enforcing the same rule in code, at matched budget | Ethan Perez |
| Honesty / false completion (3.12) | DIRECT (secondary read-off) | False-completion rate from logs, exploratory | Samuel Marks |

Items added to reach the REACHABLE rows (each needs its own approval and gate; zero or near-zero cost):
- [x] R1 3.9 case study and canaries verified offline. Evidence: docs/reports/workplan-ep/R3-scorer-evidence-case-study.md and the lane handoff.
- [x] R2 Exploratory spec-gaming read-off from Pilot 3. Evidence: docs/reports/workplan-ep/R2-pilot3-leakage.md.
- [ ] R3 Memory-poisoning replication on the local Qwen3.5-4B (GPU, about 1-2 GPU-h; Phase 5 item).
- [ ] R4 Read-only activation probe on the same model vs TF-IDF (GPU; after R3).
- [x] R5 Verifiable environment note and offline checks. Evidence: docs/reports/workplan-ep/R5-verifiable-environment.md (23 tests passed; independent scope review).
- [x] R6 Alignment evidence update for sections 2–3, with independent review. Evidence: docs/ALIGNMENT-INTEGRATION.md.
- [x] Research console UI (artifact, SeaBridge + QGrid design): status, spend, pilot evidence, fit map. evidence: ui/sortie-console.html (file exists; content not re-verified).

### Phase 7. Ambition review for the Residency (owner request 2026-11-20: "push the frontier")
Pipeline set by the owner: Haiku retrieves, Sonnet researches and evaluates, Fable writes the proposal.
EP-1 continues in parallel as the first, small, honest result; it is not replaced.
- [x] Stage 1 Haiku (3 parallel): H1 Anthropic sites delta (52 new transformer-circuits items), H2 mentor
      pages delta, H3 talks + repo assets (`docs/research/residency/`).
- [x] Stage 2 Sonnet: S1 seven directions + TREMOR programme (D2, D4, D7 need dual-use rulings); S2
      evaluation (EP-1 likely inconclusive at n=20; card cannot act in round 1; herding is the effect card A
      acts on; Safeguards/ML-RL fit overstated; ten changes about USD 40 + 30 GPU-h, above current ceilings).
- [x] Stage 3 Fable v2: TREMOR (norm carriers; USD ~53 / 33 GPU-h whole programme).
- [x] OWNER DIRECTION 2026-11-20: "Team rule should be one component but testing concepts like dreaming
      complex systems inspired should be key someone in the review is killing the ambition". Rule: reviews
      police CLAIMS (accuracy, sources, status words), never SCOPE. Opus review narrowed to accuracy only.
      Fable v3 (`docs/PROPOSAL-RESIDENCY-V3.md`): dreaming as the centrepiece, TREMOR as the instrument,
      team rules one line; lines: dream improves vs amplifies (phase transition, early warning), emergent
      misalignment via consolidation, auditing the dream, poisoning dose-response, dreaming into weights on
      the Spark + probes, norm carriers/EP-1, optional introspection. Then merge accuracy fixes, publish page. evidence: docs/PROPOSAL-RESIDENCY-V3.md (v3 final), docs/reports/proposal-v3-accuracy.md and proposal-v3-final-check.md (accuracy fixes). SUPERSEDED in scope by OWNER DIRECTION (2) below. Publishing the page stays open (D0).
- [x] OWNER DIRECTION (2) 2026-11-20: "dreaming shouldnt be the olny concept to test but also alot more from first
      principes and complex systems (testing what lance, lynda, cj, and diogo have inspired) to do deep reserach but
      solve actual problems. Creating new algorithms and techniques to advance models". v3 becomes a PORTFOLIO:
      6-8 ranked lines, each = first-principles/complex-systems idea + speaker inspiration + real problem + NEW
      algorithm with a baseline to beat + falsifiable prediction + kill criterion that can fire. Candidates:
      susceptibility-guided orchestration; memory immune system; correlation-aware monitor ensembles; dreaming as
      error-correcting consolidation; stigmergic coordination (+ TREMOR/EP-1); renormalization across team size;
      context compression (Lance); provenance verification (Diogo); trust calibration (CJ); features as monitors. evidence: docs/PROPOSAL-RESIDENCY-V3.md (portfolio of lines), docs/WORKPLAN-RESIDENCY-V3.md (lines L1-L8).
- [x] Herding change put behind an option, default OFF (current behaviour), until the owner and Fable decide.
- [x] Opus adversarial review of the proposal (claims vs evidence); then a shareable page (owner shares, G8). review part DONE; evidence: docs/reports/proposal-residency-review.md, docs/reports/proposal-v3-accuracy.md, docs/reports/proposal-v3-final-check.md. The shareable page and owner sharing stay open under D0 (Phase 8) and G8 (Phase 6).

### Phase 8. TREMOR programme under the owner budget (USD 170 API, 70 GPU-h; addendum 7, 2026-11-20)
Plan: `docs/PROPOSAL-RESIDENCY-V3.md`, `docs/WORKPLAN-RESIDENCY-V3.md`. Residency applications close 2026-11-22.
Batch stops (sum USD 159.5, reserve about USD 10.5; GPU 56.5 h + up to 13.5 h for the adapter arm):

| Batch | GPU-h | USD plan / stop |
|---|---|---|
| Spent + pilot 2 + EP-1 | 0 | 0.3 / 5.25 |
| Sensitivity pilot | 0 | 1 / 1.25 |
| 4B throughput, L2 slice, L5 local carriers | 7.5 | 0 / 0 |
| L1 susceptibility-guided orchestration | 8 | 14 / 24 |
| L2 memory immune system | 6 | 9 / 15 |
| L3 correlation-aware monitors | 4 | 16 / 24 |
| L4 dreaming, text arms | 12 | 33 / 40 |
| L5 small tier / frontier slice / evaporating claims | 3 | 20 / 29 |
| L6 trust calibration | 2 | 4 / 6 |
| L7 renormalization | 8 | 8 / 12 |
| L8 activation readouts | 6 | 2 / 3 |
| L4 adapter arm (local design approved under D3, execution gate pending) | up to 13.5 | 0 |

- [ ] D0 (by 2026-11-22): final shareable proposal: merge v3 accuracy fixes + prior-art; publish page; owner shares. STILL OPEN (partial: docs/PROPOSAL-SHARE.md, proposal-v3-final-check.md READY-WITH-EDITS).
- [ ] Spend code: hard cap USD 170, per-batch stops above, per-file rule redesigned; fresh spend gate. Owner raises
      the Console limit to USD 170 or less. STILL OPEN (checked: src/murmuration/spend.py still has HARD_CAP_USD = 10.0; D4, docs/reports/ep-approvals.md addendum 9, allows the change only through a gated code change).
- [~] R0 Pilot 3 completed 30 episodes and 240 calls, selected `shared`, and failed clearance criterion 2.
      EP-1 awaits author review and prospective clearance. Then R1 bench extensions (CPU), R2 throughput,
      sensitivity pilot and one preregistration per line, R3/R4 in L1–L8 order, and R5 write-up.
      The L4 adapter checkpoints must be ready before L8 prediction D. Other L8 work follows its own
      dependencies. See [the portfolio work plan](WORKPLAN-RESIDENCY-V3.md#phase-r4-line-runs-under-the-owner-budget-stops-from-docsworkplan-currentmd-phase-8).
- [x] Owner rulings still open: training cut (adapter arm); contagion, selection, direction-removal dual-use;
      local team sizes 16/32; sharing (G8). SUPERSEDED by docs/reports/ep-approvals.md addendum 9 (D1 dual-use, D2 team sizes 16/32, D3 training cut reversed for the adapter arm). Sharing (G8) stays owner-only (Phase 6).

### Phase 6. Sharing (gate G8, owner only)
- [ ] Rename to Sortie (no job running; before any freeze hash that matters). STILL OPEN (checked: repo and package still named murmuration).
- [x] Public explainer and README embed verified on Tremor `origin/main` at `ba08c0a` (2026-11-20). Further publication follows G8.
- [ ] Shareable proposal checked against recordings and primary sources; nothing sent without the owner. STILL OPEN (owner only).
