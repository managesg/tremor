# TREMOR work plan for the Residency (internal)

Written 2026-11-20 by Fable 5.2 (plan). Internal: not shareable. Companion to
`docs/PROPOSAL-RESIDENCY.md`. Live EP-1 checklist stays in `docs/WORKPLAN-CURRENT.md`; this file starts
where that one ends and does not replace it. Nothing here is approved, built or run.

Roles (owner 2026-11-17): Fable 5.2 plans and pre-registers; Opus 5.5 orchestrates and verifies with a
fresh context; Sonnet 5.5 builds; Haiku fetches; outside reviewers attack. One integration writer;
no subagent pushes; no push at all until the owner declares the whole plan complete.

Status words: NOT STARTED / INSTRUMENTED / PILOTED / EVIDENCED. Nothing is EVIDENCED.

## Synthesis decision (S1 + S2)

One programme, one instrument. S2's question ("where should a norm live: weights, context, memory,
environment, code") is the **axis**. S1's response-function idea (TREMOR) is the **measurement**: each
carrier's stiffness under seeded taps. Mapping:

| Line | From | Kept | Dropped or parked |
|---|---|---|---|
| L1 carrier surface | S2 section 5, S2 items 1, 3, 4 | carriers C/M/E/K, held-out norm N2, tier slice, team size 4 and 8 | W arm unless the training cut is reversed |
| L2 fluctuation-response | S1 D1, D6; S2 items 6, 11 | rho prediction, effective independent agents, early warning as a read-off | D6 as its own line |
| L3 memory | S1 D2a; S2 item 5 | warning replication, dilution curve, dream vs equal-token search | Mind Viruses evolution loop (never) |
| L4 oversight and verifier slack | S1 D4, D5; S2 item 2 | n_eff, selection sweep, verifier ladder, "accept if present" case study | gradient tier (GRPO); LLM-judge hack catalogue |
| Optional panel | S1 D3; S2 item 9 | probe vs text vs self-report against removal truth | Jacobian-lens work |
| Out | S1 D7; S2 items 7, 10 | nothing | D7 (welfare, default excluded); 1,000-agent-style substrate run; lease environment |

S2 errors fixed in the proposal: Safeguards and ML/RL are OUT OF SCOPE as area claims (only
"evaluation-integrity method" is offered), which also settles the WP:197/WP:200 against AI:60/AI:63
conflict in favour of OUT OF SCOPE; the card cannot act in round 1 (TREMOR episodes use four or more
rounds and staggered reads); EP-1 is stated as probably inconclusive at n=20.

## Hard rules for every phase

- Never touch `spark-vllm`, ports 8010/8080, OmniRoute or any other process. Local models run in our own
  container from `data/hf/` only.
- Owner ceilings today: API USD 10 (code stop USD 9 per ledger file; USD 0.0162 spent; EP-1 5, `ar1` 3,
  `pilot2` 0.25, unallocated 1.25). GPU 12 h, about 3.8 used, granted for T7 (parked). No agent raises,
  re-scopes or works around either. A new budget exists only when the owner states it; we record his
  words verbatim in `docs/reports/ep-approvals.md`.
- Every paid or GPU batch: its own pre-registration, its own batch in `spend.py`, its own owner confirm.
- No training (LoRA, RL, distillation) unless the owner reverses the cut in AI section 8.
- Claude team size stays at 8 or below. Local 16 needs a ruling.
- Claims cut by the outside reviews are never re-introduced (list: S2 section 4).
- Each line: one primary contrast; scripted floor must fail and oracle must pass or the batch is void;
  n is task sets.

## Phase R0. Finish what is open (feeds everything; inside current ceilings)

- [ ] Gate as code: `ep1.py` paid commands refuse unless a G1b-R ACCEPT file with a matching code-tree
      hash exists (CPU only). Fixes the process slip structurally.
- [ ] G1b re-gate ACCEPT (fresh Opus, real client against the fake server, pilot-1 fixes included).
- [ ] Console reconciliation of the canary (USD 0.0046625). Owner action. Unknown cost is not zero.
- [ ] Owner decision: herding option (default OFF today). Recommendation for EP-1: leave OFF, because
      herding is the phenomenon L2 measures; record the decision in the prereg.
- [ ] Pilot 2 (`pilot2`, USD 0.25 cap, about USD 0.02 expected). **Owner confirm.**
- [ ] Third-scorer gate box closed (the 10,000-log agreement is recorded; the gate line is still open).
- [ ] EP-1 freeze and run (USD 5 cap, about USD 0.3 expected). **Owner confirm.**

**Gate R0:** EP-1 reported from frozen results, inconclusive allowed. If EP-1 is never frozen, TREMOR
runs scripted and local tiers only.

What pilot 2 and EP-1 hand to TREMOR:

| From | Number or fact | Used for |
|---|---|---|
| Pilot 2 | round-1 violation and collision rates by arm | confirms or refutes "the card cannot act in round 1"; sets rounds and read staggering in R1 |
| Pilot 2 | malformed and truncation rate with thinking off | void rules for every later batch |
| Pilot 2 | leakage-card read-off (exploratory) | whether cards need a stricter word ban before L1 |
| EP-1 | sd of the paired difference per task set | sample size for L1 to L4; no guessed sd |
| EP-1 | Y for context, code, neutral at one tier | first point on the L1 surface |
| EP-1 | pairwise error correlation between agents | first effective-N estimate for L2 |
| EP-1 | realised USD per call | replaces the planning anchors in the budget table |

## Phase R1. Build the TREMOR bench (CPU only, USD 0)

- [ ] Read the bodies of `board`, `orders`, `perturb`, `poison`, `monitor`, `consolidate`, `enforce`
      before extending them (S1 read docstrings only).
- [ ] Episode design v2: four or more rounds, staggered reads, contention above 1, round 1 scored apart.
- [ ] Carriers: memory arm (rule as a board note), environment arm (sharded task generator). Norm N2
      task and its scorer, with a Lean statement for its predicate.
- [ ] Taps: dilution fraction at fixed store size; team size; best-of-N selector (built only after the
      D4 ruling).
- [ ] Readouts in one thin module (`susceptibility.py`): variance over reruns, adoption, cascade depth,
      pairwise error correlation, n_eff.
- [ ] Verifier ladder: exact scorer, `alloc`, `alloc2`, three mutants of the historic defects. Mutant
      author is not the monitor author.
- [ ] Rung-0 validation, scripted: hand-derived expected values, recomputed by enumeration.
- [ ] Fresh-context Opus verification; then adversarial verifier briefed with `interrogate`.

**Gate R1:** verifier ACCEPT on the bench; full suite green three times on a quiet machine.

## Phase R2. Measure the machine and freeze the plans

- [ ] Isolate or bound the host-memory leak; watchdog floor stays at 10 GiB. If not bounded: local tiers
      capped at short jobs and stated as a limit.
- [ ] 4B throughput smoke (under 0.5 GPU-h) in our container. **Owner approval: re-assign T7's remaining
      GPU hours to TREMOR.** Replaces every GPU bracket with a measured figure.
- [ ] Sensitivity pilot on the small Claude tier (about USD 1, from unallocated). **Owner confirm.**
- [ ] One pre-registration per line (Fable), thresholds fixed from the measured sd; Holm for secondaries.
- [ ] Owner rulings, one line each, recorded verbatim: D2 (inert marker and self-found shortcut), D4
      (selection on a toy monitor), D7 (default: excluded), training cut, local team size 16.

**Gate R2:** pre-registrations frozen with tree hash; every ruling recorded. A missing ruling blocks only
its dependent arm.

## Phase R3. Runs inside today's ceilings (about 8 GPU-h, about USD 1.3)

- [ ] L3-A warning replication on local 4B (about 2 GPU-h). This is WP item R3.
- [ ] L1 local tier, carriers C/M/E/K, norms N1 and N2, team sizes 4 and 8 (about 6 GPU-h).
- [ ] Case study of the "accept if present" family with frozen canaries (CPU). This is WP item R1.

**Gate R3:** Opus claims check per result. Stop rule: if the local 4B model fails the scripted-oracle
comparison on plain coordination (floor), stop local L1 and report the floor.

## Phase R4. Runs that need a new owner budget (each its own decision)

| # | Batch | GPU-h | USD plan / stop | Extra ruling |
|---|---|---|---|---|
| R4-1 | L1 small Claude tier | 0 | 2 / 6 | re-assign `ar1`'s USD 3 or new budget |
| R4-2 | L2 local and Claude | 6 (4 to 12) | 11 / 35 | team size 16 (local) |
| R4-3 | L3-B dilution, L3-C dream vs search | 3 (2 to 5) | 4 / 10 | D2 |
| R4-4 | L4 n_eff, selection, ladder | 5 (3 to 8) | 20 / 40 | D4 |
| R4-5 | L1 capability slice | 1 | 15 / 25 | none |
| R4-6 | L1 weights arm | 5 (4 to 8) | 0 | training cut reversed |
| R4-7 | Optional panel | 5 (3 to 8) | 0 to 8 | after L3 data |

- [ ] Order if the owner funds only part: R4-1, R4-3, R4-2, R4-4, R4-5. Cut first: R4-7, R4-6.
- [ ] Two-failure pivot: a line whose pilot shows a floor or ceiling twice is closed with that result.

## Phase R5. Write-up and sharing

- [ ] Results drafted by Sonnet from frozen outputs only; Opus claims check; negatives included.
- [ ] Opus adversarial review of `docs/PROPOSAL-RESIDENCY.md` (claims against evidence) before sharing.
- [ ] Quotes checked against recordings and primary pages; UNVERIFIED items resolved or kept marked.
- [ ] Gate G8: the owner alone shares. No push before the whole-plan rule is met.

## Owner approvals, in one list

1. Confirm pilot 2. 2. Confirm EP-1. 3. Herding option. 4. Canary console reconciliation.
5. Re-assign the remaining T7 GPU hours to TREMOR. 6. Sensitivity pilot batch. 7. Rulings D2, D4, D7.
8. Training cut (keep or reverse). 9. Local team size 16. 10. Any budget beyond USD 10 / 12 GPU-h, per
batch in R4. 11. Sharing the proposal (G8).

## Not checked

Module bodies (docstrings only, via S1 and H3); the Lean sources and the differential were not re-run;
the residency posting text is not in the repo; whether the residency provides compute; 4B throughput and
hook points; every cost is a projection from recorded unit prices.

verified: b4a820e (plus working tree) 2026-11-20
