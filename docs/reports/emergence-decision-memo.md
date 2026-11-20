# Decision memo: re-centring on practice versus enforcement

2026-11-19. Author: Fable 5.2 (planner). For the owner. Full text: `docs/EMERGENCE-PROGRAM.md`.
Nothing was run, installed, committed or sent. No GPU was used.

## What changed from PROPOSAL.md, and why

| PROPOSAL.md | Now proposed | Why |
|---|---|---|
| Headline: handoff record against raw-log search | Headline: for seven named practices, does a short playbook match the same rule enforced in code, by model tier | Your goal names practices, emergence and less harness. The handoff test answers none of them. No paper we opened compares instruction with enforcement head to head (note 16; abstract-level search, not proof of novelty) |
| Dreaming arms, shared board, lock-in, capability threshold: cut | Reinstated as proposals, each with a kill rule | They are the goal. Each now has a scripted or equal-token control first |
| Handoff store | One practice (memory hygiene at a boundary); no separate store | Simpler |
| First spend: USD 40 Claude batch, 8 GPU-hours | First spend: USD 5, 500 calls, no GPU | Smaller, and not blocked by the memory leak |
| Kept unchanged | S0 to S5, cross-model protocol, confidentiality section, leases, deterministic scoring, matched budgets | First principles hold |

## Decisions needed (yes or no)

| # | Decision | My recommendation |
|---|---|---|
| 1 | Make practice versus enforcement the one headline question, superseding PROPOSAL.md sections 2, 4 and 5? | **Yes** |
| 2 | Reinstate the shared board harness (`board.py`) and the playbook-only arm, scripted first, zero cost? | **Yes** |
| 3 | Reinstate dreaming as the seven-arm, five-rung ladder, starting with scripted re-verify, stopping if rung 3 fails? | **Yes** |
| 4 | Approve batch EP-1: Haiku 5.5, direct key, USD 5, 500 calls, at most 1.15M tokens? | **Yes**, after rung 0 passes and the pre-registration is frozen |
| 5 | Allow local commits in `murmuration` (no push) so a pre-registration can be frozen? | **Yes**; it blocks every freeze |
| 6 | Keep every local-GPU item parked until the memory leak (S0) is isolated? | **Yes** |
| 7 | Allow later distillation of successful trajectories into a local adapter? | **No for now**; revisit only if a card survives on two tiers |
| 8 | Keep dream dose, T7 stage 2 and LoRA, E9-1, E9-2, personas, debate and criticality cut? | **Yes** |

## Ceiling proposed for the first API pilot (EP-1)

**USD 5 and 500 calls**, one named batch. The USD figure is the policy default, unchanged. Only
the call count differs from the default of 9: a team episode is 8 calls (4 agents, 2 rounds), so 9
calls cannot hold one episode per arm. Sizing: 15 task sets x 4 arms x 8 calls = 480, plus 20
spare. Caps: 2,000 input and 300 output tokens per call. Estimated cost at the full cap: USD 3.50
at Sonnet 5.5 prices, used as an assumed upper bound because the Haiku price row could not be
read. The runner stops at USD 5 or 500 calls, whichever comes first. A second tier is a separate
batch and a separate approval. It detects only large effects (about 20 points).

## What I edited

`docs/research/11-lance-martin-code-summit-2026.md`
1. Story 1 setup: CORRECTION added. Not a no-harness result: roles, 60 statements, route sketch,
   definitions, 47 proved lemmas, Lean verifier, safety harness kept; "toy experiment"; one run.
2. Story 1 last bullet: pointer to that correction.
3. Story 2 wiki bullet: "2M to 128M dreaming tokens" became 2 to 128 sessions, a nominal budget,
   "not measured spend".
4. Implication 4: "64x tokens" became 64x the dreaming sessions.

`docs/PROPOSAL-SHARE.md`
5. Section 2.1, "What we took": the run is not read as no-harness; inputs listed.
6. Figure table, row 1: 47 lemmas added. 7. Wiki row: sessions wording and status.
8. Gap 3: "64 times the tokens" became 64 times the dreaming sessions.
9. "Our question" and 10. the section 7 ask to Lance: now ask for the measured spend.
11. Section 3 table: "128M-token curve" became "128-session curve".
12. Section 8 sources row: the memory post was later read in full (note 14).

`docs/PROPOSAL.md`: **no edit.** It contains neither wording.

## What I could not verify

- The brief's "graph of theorem statements and task-lock files" for the 1,000-agent run. Notes 10
  and 14 support roles, 60 statements, a route sketch, definitions, 47 lemmas and Lean. In note 14
  the statement graph belongs to the earlier 11-day run (Prove2Me) and lock files to the C-compiler
  project. I did not write those two items into any file.
- The same stale "64 times the tokens" wording remains in `SCIENCE.md` 1.5 (row 5, note 5),
  `PLAN.md` E8.4 and `adversarial-review-2.md` claim 6. I was not allowed to edit them.
- Haiku 5.5 pricing; every vendor figure (single runs); most papers (abstracts only); slide
  numbers (screenshot-read). The session-axis reading rests on notes 14 and 17.
- No code or test was run. `cell.py`, `router.py` and `perturb.py` are still unverified. During
  this pass `runner.py` and `tests/test_runner.py` changed in the working tree; not by me.
- PROPOSAL.md proposed "no new hypothesis until one pre-registration is frozen and run". This
  program replaces the headline; it still adds about 4,100 words of planning.

verified: 972dee3 (plus working tree) 2026-11-19
