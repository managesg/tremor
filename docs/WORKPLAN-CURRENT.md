# Sortie (repo `murmuration`): current work plan and checklist

Updated 2026-11-20 by the orchestrator (Opus 5.5). This file is the live checklist. Detail lives in
`prereg/EP1.md`, `docs/reports/ep1-design-notes.md`, `docs/WORKPLAN-ALIGN.md`,
`docs/reports/review-integration.md` and `docs/ARCHITECTURE.md` (threat model, section 9a).
Roles: Fable 5.2 plans and pre-registers; Opus 5.5 orchestrates and verifies (a different Opus than
the implementer, fresh context); Sonnet 5.5 builds; Haiku fetches; outside reviewers (GPT via Codex,
Cursor/Grok) attack. Status words: NOT STARTED / INSTRUMENTED / PILOTED / EVIDENCED / OUT OF SCOPE.

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
- [~] Model-loop fixes from G1b (ordered round actions, task-id allowlist, HTTP mapping, void rules,
      seeded claim order, reachable refusal stops, gold-leak scan): Opus implementer running.
- [x] EP-1 token cap 1,250,000 and `ar1` batch in `spend.py` (landed; awaiting re-verification).
- [ ] `pilot` batch spec (sibling of `ep1`, USD 0.50 / 150 calls) once the pilot is approved.
- [~] Model-free canary suite (`tests/test_canaries.py`): 'accept if present' failures must score zero.
- [~] HDI margin rule + `analysis.py` (refuses scripted/FAKE records on model figures; n as task sets).
- [~] Independent second scorer `alloc2.py` + differential test against `alloc.py`.
- [~] Static card check `cardcheck.py` + two pilot-only leakage cards (states-the-check, keyword-stuffed).
- [~] Auto-research scaffold under `lab/` (unrun; outside the freeze hash).
- [ ] Prompt-truncation logging and provider response-id logging (`backend_claude._record`).
- [ ] External anchor for log heads (cell log and board log).
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
- [ ] Align all three scorers to the decided outcome definition and the two settled rules; differential 0.
- [ ] Original spec for the Lean scorer: the EP-1 allocation scorer written as Lean definitions, compiled to an
      executable that reads a board log (JSON) and prints the scores; kernel-checked theorems at least:
      unknown-task events change no score; Y in [0, 1]; distinct_passing <= slots; clobber rule (last
      writer per name survives); score is deterministic and extensional; check_iff for every predicate.
      Axiom audit: `#print axioms` must show only the standard axioms (no sorryAx); a static scan refuses
      `sorry`, `admit`, new `axiom`, `native_decide`, `unsafe`, `implemented_by`, extra imports.
- [ ] Third-scorer gate: Python `alloc`, independent `alloc2` and Lean `AllocScore` agree on 5,000 seeded
      logs; disagreement in a real run voids it. Lean missing or unpinned = INVALID, never pass.
- [ ] (optional, same pattern) Lean proof of the HDI margin decision table and of the ledger cap arithmetic.
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
      verdict), used only as a held-out family from a different generator. No advantage claims.

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
- [ ] G1b re-gate: fresh Opus on the fixed model loop with the real client against the fake server.
- [x] Full suite green on a quiet machine, 3 of 3 runs (OK, 1 torch-only skip) plus the lab suite (2026-11-20).
- [x] Three scorers agree on 10,000 seeded logs (0 disagreements each pair, incl. `valid`); strict input
      rule (episode action log only); Lean `no_action_not_valid` proved.
- [ ] Local commit after both gates accept.
- [ ] B4: whole EP-1 schedule against the fake server at worst-case usage, every stop fires, table stamped FAKE.

### Phase 3. First money (owner "confirm" required at each step)
- [x] Price sheet refetched 2026-11-20: every row re-verified against the pricing page, unchanged; only
      `fetched` moved (sha256 16b204c2...984f). The canary, pilot and EP-1 must all finish by 2026-11-23 UTC.
- [x] Fake dry run GREEN 2026-11-20 (canary, pilot and EP-1 complete on the fake server).
- [~] Canary RUN 2026-11-20 under the owner's "Confirm": ok, complete, returned model claude-haiku-5-5,
      46,605 input + 4 output tokens, ledger USD 0.0046625 (worst case 0.01815); no key fragment in outputs.
      OPEN: the owner compares the Console cost for that one request with USD 0.0046625. First look
      (Console "data as of 13:43 UTC", org SeaBridge.AI, all models, last 7 days): no Nov 20 usage shown, only
      Sonnet 5.5 on Nov 14-15. Not yet a match. Canary ledger written 13:22:32 UTC. Pilot blocked until resolved.
- [ ] Local commit: `git add`/`git commit` were denied by the session permissions on 2026-11-20; everything
      through the canary is uncommitted. Needs the owner to allow it, or to commit by hand.
- [x] Pilot RAN 2026-11-20 under owner "CONFIRM PILOT": STOPPED `void_model` / `malformed_states_check` after
      11 episodes, 88 calls, USD 0.0115 (directory total USD 0.0162 of 10). Pre-registered stop worked as designed.
      Findings: (1) 5/88 replies hit max_tokens 300 (4 in the states_check leakage arm) although the JSON is short;
      (2) `board_error:ValueError` in a none-arm and a code-arm episode. Opus diagnosis running
      (`docs/reports/pilot-1-diagnosis.md`). The pilot batch is stopped and cannot reopen; a re-pilot needs a new
      batch spec and owner approval. EP-1 is not blocked by the pilot stop (sibling batch), but must not run
      until the fixes are re-gated.
- [ ] (was) Pilot STARTED 2026-11-20 ~14:43 UTC (pid 161791, out
      `runs/ep1-live/pilot`). Console check of the canary deferred by the owner (Console lag), required before EP-1.
- [ ] Instrument pilot (if approved): about 150 calls, hand-checked traces, two leakage cards; excluded
      from confirmatory estimates; any pilot-driven fix is re-gated and the prereg diff recorded.
- [ ] Human baseline (about ten manual tasks) or its absence stated as a limit.

### Phase 4. EP-1 (the number)
- [ ] Freeze: commit, write `code_tree_hash`, `prereg-check` passes, second commit.
- [ ] Run EP-1 in one process: 3 arms x 20 task sets x 8 calls; stops at USD 5 / 500 calls / 1.25M tokens.
- [ ] Analysis with both scorers agreeing; raw contrasts with intervals; HDI only under the margin rule;
      inconclusive reported as inconclusive.
- [ ] Opus claims check; write-up drafted by Sonnet from frozen results only.

### Phase 5. After EP-1 (each needs its own approval)
- [ ] No-API replication of the one-line memory warning on planted notes (local 4B model; download gate).
- [ ] Cross-agent error correlation and three-copies-plus-dissenter on those traces.
- [ ] 3.9 case study: the 'accept if present' failure family as a write-up.
- [ ] Extend exactly one dimension depending on EP-1 (more blocks, or a second model family).
- [ ] Deferred: auto-research over cards (`ar1`, held-out family from `trapbench/qstate`), dreaming ladder.
      Not used: QGrid's grid-site domain and its Python mirror. Cut: quantum search as a proposer or any
      quantum claim, weight-edit thread, joules headlines, permissions-decay headline, persona vectors,
      recursion and CoT branding.

### Phase 6. Sharing (gate G8, owner only)
- [ ] Rename to Sortie (no job running; before any freeze hash that matters).
- [ ] Shareable proposal checked against recordings and primary sources; nothing sent without the owner.
