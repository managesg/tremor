# Document reconciliation after adversarial review 2 (2026-11-19)

Author: Opus 5.5 (orchestrator/verifier). Source: `docs/reports/adversarial-review-2.md`
(read in full), review actions 5-8 and its section 5 contradiction table, plus the owner
decisions relayed by the parent on 2026-11-19. Scope: `docs/*.md` (not `docs/research/`) and
`prereg/*.md`. No code, no runs, no commits. No `code_tree_hash` line was touched
(`git diff -U0 -- prereg docs | grep -c code_tree_hash` printed 0). Every recommended cut is
**marked, not applied**.

Status lines cite `972dee3` (git log) and the "89 tests" figure from
`docs/reports/E1-E8.1-local-results.md`; the suite was not re-run. Uncommitted `cell.py`,
`router.py` and `perturb.py` appeared in the working tree during this pass; they are mentioned
as "not verified" and were not read.

## 1. Requirements from the parent's brief

| Req | What | File and section changed |
|---|---|---|
| (a) | Self-hosted environments and MCP tunnels do not hide session content from the provider; overclaims rewritten | ARCHITECTURE new 6a (table of shapes, what stays local, what reaches the provider), 2, 4 file 4, 6 "Not used" para, 9 row 1, 12 two rows; VISION thesis, picture, "Ownership"; PLAN T1 Data, 4.4, 4.5 (MCP tunnel row + paragraph), 7.3; prereg/H1 4; prereg/E8.1 4 |
| (b) | Hub split into owner key, router code, models; every model is a cell; Claude orchestrating local models is a planner cell whose output is task specs, the router launches workers | ARCHITECTURE 1, 2 (three-part table, same-model-ID verification rule, costs of the split), 3 lead-in, 8 (tiers, planner/verifier cost logged), 10 steps 3-4 (two hub-as-cell contract tests); VISION thesis and picture; PLAN 1.1 "Organisation" |
| (c) | Three families as task controls, one robustness measure, P1-P5, control-effect metric defined | SCIENCE new 4a (definitions incl. `CE`, perturbation table, arms, Fermi); PLAN new T10; PRINCIPLES scope guard (KDS reading + pointer); SCIENCE 8 |
| (d) | Cross-model protocol: own loop, bytes and turns as matched budget, returned-model-ID check, sentinel set, drift | PLAN new 4.6; 4.2 amendment; 4.4 (direct key, returned model ID); 4.3 C6 row; E8.3 arms; H8 header; prereg/H8 6, 13; SCIENCE 5 |
| (e) | Owner decisions recorded; review cuts marked RECOMMENDED CUT, not applied | PLAN new 6.4 (decisions table + cut table with status and reason + other open recommendations); markers at T2 cut list (T4), T7, E8.4, T8 priority table, T9, 3.2 menu, 6.1 P5/P7, 6.2 G5/G6/G9/new G11; WORKPLAN 1 table (G9 row, new G11 row); prereg/H7 status + 12; prereg/E9 status + gate line; ARCHITECTURE 12 (T4) |
| (f) | Contradictions fixed | see section 3 |
| (g) | Naming note; nothing renamed | VISION new "Naming" section |

## 2. Review actions 5-8

| Action | Resolution |
|---|---|
| 5. Amend PLAN 4.2 and section 3 for model-agnostic testing | PLAN 4.2 amendment (any model in any role; one snapshot per model per experiment; Fable not an execution tier); PLAN 4.6 protocol |
| 6. Confidentiality wording | Requirement (a) above; section 4 below lists each overclaim row |
| 7. Reconcile H8/H9, T7 vs prereg/H7, H1 threshold and counts, USD 185, status lines | Rows 1, 2, 3, 6, 7, 9, 15 below |
| 8. Cuts | Marked RECOMMENDED CUT in PLAN 6.4 and at each item; E9-0 marked keep. Not applied |

## 3. Section 5 contradiction table, row by row

| # | Topic | Resolution | Files and sections |
|---|---|---|---|
| 1 | H8 status | H8 exploratory (owner) everywhere | PLAN 1.2 lead and H8 header; SCIENCE 5, 8; prereg/H8 11 ("every Holm family") |
| 2 | H9 status | Marked "awaiting owner ruling; review recommends defer"; family-of-one stated; E8.4 "outside both families" -> "outside every Holm family" | PLAN 1.2 lead and H9 header, E8.4; SCIENCE 5, 8; PLAN 6.3 #13; prereg/E8.1 11 |
| 3 | T7 design | PLAN T7 rewritten as a staged summary that defers to prereg/H7 6, 7, 10, 12 (no caps re-typed except the gate); H7 hypothesis points to prereg; P3, G9, gate notes, WORKPLAN steps 8-9 staged | PLAN 1.2 H7, T7, 6.1 P3, 6.2 G9 + notes; WORKPLAN 1 table, wave 2 steps 8-9 |
| 4 | 12-point gate vs 5-point margin | Owner decision recorded; the power limit stated as a limit in PLAN T7; action 9 (drop or labelled smoke) recorded as open alternative, not applied | PLAN T7, 6.4; prereg/H7 status, 12 |
| 5 | Arm C selection on MATH-500 smoke items | WORKPLAN step 8 now uses `smoke_ids` for timing only and chooses r on `math_train.jsonl` practice problems | WORKPLAN wave 2 step 8 |
| 6 | H1 "Kill" vs precondition | "Precondition (not a kill)"; "untestable on that corpus, not refuted" | PLAN 1.2 H1; WORKPLAN wave 2 step 1.2; prereg/H1 pre-freeze note, 10 |
| 7 | H1 corpus size (155 vs 1,079) | 1,079 events, 1 session, 11 denials; the session count fails | PLAN 1.2 H1, T1, 8.2; WORKPLAN 7 |
| 8 | Session counting (1 vs 5 main) | Recorded as unexplained; must be resolved before any H1 or E8.1 claim. No cause offered | PLAN T1; WORKPLAN 7 |
| 9 | USD 185 | Verbatim quote left intact; reading note added: only C0 (USD 5, 9 requests) is approved; 185 is a proposal total incl. conditional C6 | WORKPLAN 1 note; PLAN 4.3, 6.2 G7 |
| 10 | Local USD | H6 cost criterion marked not computable until the owner supplies a tariff or rules local USD stays "n/a" (then rewritten) | PLAN 1.2 H6; SCIENCE 4 cascade cost; prereg/H8 15 |
| 11 | Next GPU item | Made conditional on the owner's cut ruling; no GPU item before the watchdog kills are explained | PLAN T9, 6.1 P5 |
| 12 | Small-model subject (0.8B in E9) | Given as part of the E9-1/E9-2 cut reason; not otherwise changed | PLAN T9, 6.4 |
| 13 | Model roles | 4.2 amended (any tier in either role); role-table row "Hub ... split, route, verify, judge" relabelled as planner and verifier cells (Opus 5.5 by default; routing is router code); tier order ends at Opus then the owner, Fable plans only; E5.6 hub -> planner cell. "+5 from 5" still open | PLAN 4.1 E5.6, 4.2 |
| 14 | `cell.py` / board: start-now vs cut | Both positions stated; open for the owner | PLAN 6.1 P1b, 6.3 #9, #13; WORKPLAN 9; ARCHITECTURE 10 step 3 |
| 15 | Stale status lines | Rewritten with `972dee3`, the reported 89 tests, E1/E8.1 and smoke-kill state | VISION header; PLAN header; ARCHITECTURE header (uncommitted files noted) |
| 16 | Memory floors 10 vs 20 GiB | Not unified: 10 GiB abort (T7, G5) and 20 GiB start floors where a source sets one (G2a preflight, E9 design item 8) stated as compatible; caveat on tens-of-GiB swings and wall-clock noise | PLAN 3.8, 6.2 G5 |

Also fixed while there (same topics, not in the table):
- SCIENCE 4 `DG` formula still named the retired "re-summarise without logs" control; it now
  uses search over raw logs (PLAN H3, arm B3).
- "Hub" used as a model, after the split: PRINCIPLES scope guard keeps the owner's sentence
  ("the hub stays a frontier model we do not build") with a terminology note that "hub" there
  means the strongest model cell; PRINCIPLES hub-and-cells rules ("leaves the Claude tier";
  "router adds a model verifier cell"); ARCHITECTURE 2 terminology note for older "hub model"
  uses (sections 6, 11, 12, VISION, PLAN H7/T7), 6 table row, 8 "unreachable", 9 "wrong or
  down"; PLAN 7.1 shared-family line, H8 kill 1; prereg/H8 kill 1; SCIENCE 1.4 ceiling line;
  VISION picture ("only the owner's key signs").
- 20 GB E9 download cap attributed to the parent, as briefed.

## 4. Section 2 overclaim rows

| Review row | Resolution |
|---|---|
| ARCHITECTURE 2, 4: hub never reads raw logs; raw logs never leave the cell | ARCHITECTURE 2 closing para, 4 file 4: true only for local cells and only via router code; false for Claude cells |
| ARCHITECTURE 2.1: no model process can read the key | ARCHITECTURE 2 item 1; VISION "Ownership": an intention unless the key is off the box, on a token or passphrase-protected; signature proves approval, not enforcement |
| ARCHITECTURE 9 row 1: cannot sign or reach another cell | Qualified per worker kind |
| VISION thesis: local cells are "private" | Narrowed to raw logs and inputs passed by path and hash that no Claude cell reads |
| PLAN T1, 7.3: transcripts never leave the box | "Our analysis exports nothing" (also prereg/H1, prereg/E8.1) |
| ARCHITECTURE 6, PLAN 4.5: self-hosted envs and MCP tunnels "Not used" | Kept as "not used"; added that using them is an owner decision and their limits become constraints |
| Proxy fallback chain (outside file 07) | ARCHITECTURE 6a closing para; PLAN 4.4 (direct key, returned model ID, build sessions) |

## 5. Needs an owner ruling (nothing decided here)

1. Every RECOMMENDED CUT in PLAN 6.4: E9-1, E9-2, E8.4, T7 stage 2, arm 0, arm D, the LoRA
   step, T4 (E9-0 is marked keep).
2. T7 stage 1 as a test with the 12-point gate (owner decision) versus the review's labelled
   smoke (action 9).
3. H9: confirmatory family of one, exploratory, or deferred.
4. Reinstating P1b (scripted router, stub cells, hub-as-cell tests) against WORKPLAN 9's cut.
5. The T10 merges (E3.3, E3.4, E5.3, E8.2 hub-assign arm, E9 authority, H8).
6. Next GPU item (T9 / P5), after the watchdog cause is found.
7. A local tariff, or a ruling that local USD stays "n/a" (H6 cost criterion).
8. Whether self-hosted environments or MCP tunnels are wanted at all.
9. Where the signing key lives (off the box, hardware token, or passphrase).
10. "+5 from 5" (PLAN 4.2); "KDS" read as the three families (confirm).
11. The name (VISION "Naming"); nothing checked for availability.

## 6. Unresolved without new data

- Row 8: E1 counts 1 session, E8.1 counts 5 main sessions in the same corpus. Unexplained.
- The two T7 smoke watchdog kills: cause unknown (review action 1).

## 7. Out of scope, still stale (not editable in this pass)

- `README.md`: "155 events / 1 session" and "far below the 200-event threshold" (row 7; the
  session count is what fails).
- `docs/reports/E1-E8.1-local-results.md`: "a kill of H1's precondition" (row 6 wording).
- `docs/reports/prereg-audit.md`: lists PLAN/SCIENCE lines now fixed; not updated.
- Other reports (E9 design, staged T7 decision) were grepped for "next GPU"; no hit, so no
  stale row-11 wording was found there. They were not re-read in full.
- Review recommendations outside actions 5-8 are listed in PLAN 6.4 and not applied.
- `docs/PROPOSAL.md` and `docs/reports/rename-plan.md` appeared from another session during
  this pass. They were not read or reconciled; PROPOSAL.md mentions cutting "T7 as a hypothesis
  test, E9-1 and E9-2", which may conflict with the owner decisions recorded in PLAN 6.4.

verified: 972dee3 (plus working tree) 2026-11-19
