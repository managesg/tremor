# Integrating two adversarial reviews (GPT and Cursor/Grok)

2026-11-20. Opus 5.5 (orchestrate and verify role). Docs only: no code, run, commit, API call or
GPU; `.env*` not read; no test was run. Subjects: `gpt-adversarial-review.md` (an unidentified
OpenAI model) and `cursor-adversarial-review.md` (Cursor Agent, self-identified Grok 4.7, not shown
the GPT review). Both answered from a brief; their literature judgments are **unverified**.
Cross-checked against the code at 36bab4b plus the working tree, `prereg/EP1.md` and
`ep1-design-notes.md` (both read only), `workplan-ep/G1.md`, `G1b.md`, `G0-2R.md`, `T7-smoke.md`,
`ep-approvals.md` and Fable's `adversarial-review-2.md` ("Fable"; it predates the alignment docs,
so it is silent on most rows). `gpt-integration.md` now points here.

Verdicts: **A** accept, **P** partly, **R** reject. "Agree" = both reviews say it; "harsher" = the
Cursor review goes further than GPT.

**Against Fable's review 2.** Both new reviews agree with it on: cutting T7 stage 2 and arm 0 (and
now the thread), cutting E9-1 and E9-2, parking H1, the warning that a likely-inconclusive result
is treated like a kill, and the document debt. They disagree with it on one point: Fable ranked the
perturbation matrix on a local model and a Claude tier 7th and made it its research question; GPT
would cut broad perturbation sweeps and Cursor would allow nothing beyond EP-1 until it reports.
Owner rules; our view is to park the model matrix behind EP-1.

## 1. Overall, HDI, budget

| # | Point | GPT | Cursor | Verdict | Reason | Applied in |
|---|---|---|---|---|---|---|
| 1 | Strongest delivered claim is instrument behaviour; no model evidence | yes | yes | A | G1 and G1b say "instrument validation only". Fable 0.1 said the same | status words, all docs |
| 2 | Every ADDRESSED is overclaimed | yes | yes, and most PARTLY | A | No row has a real-model result | AI doc 1 to 3 |
| 3 | Router can make compliance tautological; violation drop is a manipulation check | yes | implied | A | Under `code` a duplicate claim cannot execute | EP 2.2 |
| 4 | EP-1 resolves only large effects | yes | yes ("16-20 points") | A | MDE recomputed: 16 to 23 points by correlation | WORKPLAN-ALIGN 6a; EP 6 |
| 5 | Prior team studies make broad novelty untenable; concession first | yes | yes, "first sentence" | A | AI doc 9 already narrowed it | PROPOSAL-SHARE 1 |
| 6 | HDI polarity: 0 = play matches code, 1 = recovers none | yes | n/a | A | AI doc 1 said the reverse; EP 2.2 was right | AI doc 1; EP 2.2; SCIENCE 4 |
| 7 | Three raw contrasts with task-block uncertainty first | yes | "report the both-arm, not only HDI" | A (contrasts); R (both arm) | `both` was dropped by the owner (addendum); not estimable at this n | EP 2.2 |
| 8 | Ratio unstable near zero or negative denominator; keep out-of-range values | yes | "undefined or explosive when code does not beat neutral" | A | `stats.hdi` keeps out-of-range values but returns a number when the denominator interval is wholly below 0 | EP 2.2; implementer |
| 9 | No HDI unless code beats neutral by a stated margin | implied | yes | A | Proposed margin: interval above 0 and at least 10 points | EP 2.2; SCIENCE 4; WORKPLAN-ALIGN 6a |
| 10 | Rename HDI or report recovered fraction | yes | n/a | P | Keep the name (in code and prereg); report `1 - HDI` | EP 2.2 |
| 11 | Equal budget per dimension; realised costs | yes | "match tokens in a fixed slot; match retries and denials" | A | EP-1 matches calls and per-call caps, not bytes or opportunities | EP 3; AI doc 4, 9 |
| 12 | Three-arm batch gives standalone effects only | yes | n/a | A | EP-1 is 3 x 20 | EP 2.2, 6 |

## 2. Areas and directions

| Row | GPT | Cursor | Verdict, new label (was) | Reason |
|---|---|---|---|---|
| Scalable oversight | PARTLY overclaimed | ordinary grading | A, OUT OF SCOPE (PARTLY) | Cursor harsher and right: checkable tasks are grading |
| AI control | ADDRESSED overclaimed | NOT STARTED, worst label | A, NOT STARTED (ADDRESSED) | No untrusted model, sabotage goal, protocol or red team |
| "Reasoning monitor never vetoes the action monitor is untested and hides a confessing saboteur" | n/a | yes | **R** | `monitor.combined` lets the reasoning monitor add a deny, never lift one; `test_combined_second_never_vetoes_first` asserts both (read, not re-run). A confession is denied only if the reasoning judge flags it. The brief was ambiguous |
| Model organisms | fixture | stop using the word | A, OUT OF SCOPE (PARTLY) | Agree |
| Internals | overclaimed | publish negative or beat bag-of-words | A, PARTLY, NOT STARTED; proposed cut (PARTLY) | Agree |
| Safeguards | PARTLY true | process integrity, OUT OF SCOPE; ledger unfinished | P, OUT OF SCOPE (PARTLY) | Accept relabel. Reject "unfinished canary decision": closed by the owner addendum (Haiku only, padded). Concurrency and overspend probes ran in G0-2R |
| Welfare | OUT | OUT | A, unchanged | |
| Security | PARTLY as defensive testing | OUT OF SCOPE, keep tests as QA | A, OUT OF SCOPE (PARTLY) | Cursor harsher; a test count has no coverage denominator |
| ML systems, RL | systems yes, RL no | out; drop joules, keep USD per pass | P, OUT OF SCOPE (PARTLY) | Joules leave every headline, stay a raw local field. Reject "no idle baseline": T7-smoke recorded one (it is contaminated by a shared engine, which it says) |
| 3.1, 3.8, 3.11, 3.14, 3.16 | true | true | A, unchanged | |
| 3.2 | reasonable; counterbalance | drop or 20 seeds locally | P, PARTLY, instrumented, scripted only | Keep: built and gated, costs nothing until EP-1 reports. Counterbalancing to the Fable list |
| 3.3 | defer | drop | A, OUT OF SCOPE (PARTLY thin) | Agree |
| 3.4 | cross framing with authority | least overclaimed; three token-matched cards | A, PARTLY, confounded | The three-card fix applies before any L run (EP-1b), not EP-1 |
| 3.5 | defer | rename "monitor string-invariance", cut | A, OUT OF SCOPE; check renamed | Agree |
| 3.6 | mechanically true | overclaimed until a rate | P, PARTLY, instrumented, mechanics only | `tpr_at_fpr` exists; label-independence rule added |
| 3.7 | exposure label | beat TF-IDF on paraphrases or drop | A, PARTLY, NOT STARTED; proposed cut | Agree |
| 3.9 | true as instrumentation | **the one underclaim**: freeze the "accept if present" failures as canaries, write a case study | A, PARTLY, instrumented; best lead | Three instances: any non-empty answer (A0-1 report), unknown task ids (G1b-2 report), fabricated source passing the lint (documented in AI doc 3.9; no gate report) |
| 3.10 | defer | relabel | A, OUT OF SCOPE (PARTLY) | Agree |
| 3.12 | overclaimed | rename false-completion; define a valid claim | A, renamed false-completion rate, PARTLY, instrumented | Valid claim = done release backed by an earlier passing work event (`orders.false_done_rate`) |
| 3.13 | overclaimed | NOT STARTED | A, NOT STARTED (ADDRESSED) | Cursor harsher and right: stand-ins test our own placeholders |
| 3.15 | not adaptive | call them tripwires | A, OUT OF SCOPE; "tripwires" | Agree |
| 3.17 | overclaimed | right question, unanswered | A, INSTRUMENTED (ADDRESSED) | Rung 0 accepted (G1); loop fix not re-gated; prereg not frozen |
| Stop publishing the coverage table; keep a private gap list | n/a | yes | A | AI doc 2 and 3 marked private; PROPOSAL-SHARE 3 table replaced by a paragraph |

Rejected inside these rows: every **new** study either review proposes for a row (calibration and
abstention, persona framing cross, adaptive defence, recursive checker, NLA artifact, fine-tuning
triage, a fine-tuned organism). Reason: "no new hypothesis or planning before one pre-registration
is frozen and run" (PROPOSAL 9, EP 9). Recorded as entry criteria.

## 3. Published lines

| Point | GPT | Cursor | Verdict | Note |
|---|---|---|---|---|
| Cite the primary source; never import reported rates as effect sizes | yes | yes ("do not set our rate beside 84% or 30-40%"; "do not re-estimate about 32 examples") | A | AI doc 5; PROPOSAL-SHARE 8 |
| Per-line "cannot establish" limits | yes | yes, mostly "cannot" | A, phrased as limits of **our** tests | Column in AI doc 5. PROPOSAL-SHARE discusses talks, so the rule is applied to the figures it quotes |
| Mind-viruses warning: the one line we can credibly replicate, locally, no API | test separately | yes, before inventing practices | P | Best next replication, but needs G3 and the leak isolated; after EP-1 |
| Team papers are binding prior art | inspect methods | binding | A | AI doc 3.17, 9 |
| Smart-contract: contribute nothing, even method | method only | nothing | P | We keep only held-out splits already built; no new borrowing |
| Specific new studies per line | some | some | R for now | Same "no new planning" rule |

## 4. Self-deception audit (WORKPLAN-ALIGN 6a)

| # | Item | GPT | Cursor | Verdict | State today |
|---|---|---|---|---|---|
| 1 | Scripted runs as model evidence; machine-checked refusal in analysis | yes | yes, machine check | A | Rule exists; machine check not built |
| 2 | Byte parity hides unequal treatment: placebo, counterbalanced templates, token-matched slot | yes | yes | A | Neutral card only; bytes only |
| 3 | Small n: MDE with actual randomisation and correlation; inconclusive is not null | yes | yes | A | Recomputed: 16 to 23 points |
| 4 | Same-family correlated errors: identical-wrong agreement, task-level n, pairwise correlation | yes | yes; add a dissenter | A; dissenter P (after EP-1) | rho read-off only |
| 5 | Leakage: blinded checks, held-out templates, sealed scorer, second scorer, unwinnable canary | yes | yes, harsher | A | Seal built; one scorer; held-out operand range, not template |
| 6 | Ban scorer predicate words from the playbook card, static check, other checker | n/a | yes, "the one built-in cheat" | A | Not built |
| 7 | "States the check" and keyword-stuffed cards as leakage controls | n/a | yes (in EP-1) | A, in the **pilot**, not EP-1 | Not built |
| 8 | Log truncation; match retries and denials | n/a | yes | A | Not logged |
| 9 | Model-free canary suite | n/a | yes | A | Scattered tests only |
| 10 | Human baseline, about ten manual tasks | n/a | yes | A | Not done; owner time, zero spend |
| 11 | Post-gate fix updates the prereg before spend; diff ships with the result | n/a | yes | A | Not written |
| 12 | Independently-verified claims sit beside the rejections and the unrun pilot | n/a | yes | A | PROPOSAL 9; PROPOSAL-SHARE 6 |

## 5. Next steps and cuts

| Item | Source | Verdict |
|---|---|---|
| Instrument pilot before frozen EP-1 | GPT 1 | A: WORKPLAN-ALIGN wave B0; 5 arms (EP-1's 3 plus two leakage cards) x 2 train sets, 80 calls, USD 0.75 proposed, own batch and approval |
| Re-gate then EP-1 directly | Cursor 1 | P: same content; we keep the pilot between |
| Frozen EP-1; extend one dimension conditional | GPT 2, 3 | A |
| Wrong-note and re-verify real-model run | GPT 4 | P: candidate beside EP-1b; owner picks after EP-1 |
| Local no-API memory-warning replication | Cursor 2 | P: after G3 and the leak |
| Error correlation; dissenter | Cursor 3 | P: read-off now; dissenter later |
| Model-free canary suite | Cursor 4 | A: now, zero cost |
| P4 with P5 on an inert workflow | GPT 5 | A, reordered: scripted, zero cost, now |
| Close canary decision; trip the hard stop | Cursor 5 | P: decision closed; a deliberate trip goes in the canary suite |
| Cut weight-edit thread, activation demo, persona vectors | both | A: proposed cut (owner rules) |
| Cut recursion, CoT branding | both | A: done |
| Cut welfare | both | A: already out |
| Cut broad perturbation sweeps | GPT | **Disagreement** with Fable review 2 (rank 7, section 9) and PROPOSAL 2: owner rules; our view, park the model matrix behind EP-1 |
| Park permissions-decay headline; 30 sessions is a recruitment target | both | A |
| Cut joules from headlines | Cursor | A |
| No second practice, paid tier or family before EP-1 reports | Cursor | A: already the rule |

Smoke numbers 0/20, 8/20, 1/20: now described everywhere as configuration results under an
8,192-token cap with most generations cut and different decoding per arm, not an edit effect
(AI doc 7, PROPOSAL 5 and 9, PROPOSAL-SHARE 6, WORKPLAN-ALIGN 1, SCIENCE 4). Two docs said "zero
accuracy results" (stale, not inflated).

## 6. Threat boundaries (ARCHITECTURE 9a)

Eleven rows, each with what the code holds (files, tests) and what it does not. Finding while
checking: **no lease object exists in `src/`** (grep finds only "release"). "Router leases" (AI
doc 1) and "Lease check BUILT" (EP 5, PROPOSAL-SHARE 3) were overclaims; corrected to router-checked
policy (allow, deny, caps) and board claims with a TTL. Cursor's "router is not containment" is
right: today the boundary is "cells have no tools", not the router.

## 7. For Fable / EP-1 pre-registration (I did not edit these files)

1. `prereg/EP1.md` line 173 lists `Y_both - Y_play`; EP-1 has no `both` arm. Remove or mark "not
   estimable".
2. Report the three raw contrasts with intervals before HDI; recovered fraction `1 - HDI`; HDI only
   when `Y_code - Y_none` beats a stated margin (interval above 0 and at least 10 points,
   proposed), including the wholly-below-0 case as "not interpretable".
3. Recompute the MDE for 3 x 20 under a stated within-set correlation (my range: about 16 to 23
   points at per-arm sd 0.25); say which rho "about 16 points" assumes.
4. Equal-budget table: calls and per-call caps matched; tokens per card slot, wall time, retries,
   denials and admitted actions realised per arm; prompt truncation logged.
5. Report censored task sets, refusal-stopped agents and blocked legitimate work per arm.
6. Card A: static check that it carries no scorer predicate words, run by someone other than its
   author; freeze cards before any score; token-matched slot (measured in the pilot).
7. Card wording: counterbalance two wordings (and two neutral texts) across sets, or state the
   single-template limit.
8. Held-out seeds of one `alloc` template are not held-out templates; say so.
9. Read-offs: pairwise error correlation, agreement on identical wrong outcomes, task-level n.
10. Freeze order (`ep1-design-notes.md` 3): loop re-gate, canary, instrument pilot (with the two
    leakage cards), any pilot-driven fix with its re-gate, a prereg update and diff, then the freeze.
11. A post-gate fix updates the prereg before spend; the diff ships with the result.
12. Human baseline (about ten manual tasks) before the freeze, or state its absence as a limit.
13. A second scorer implementation whose disagreement voids a run, or state its absence.
14. "Inconclusive is neither equivalence nor null": check the reading table.
14a. The harm kill criterion ("an action outside the lease", prereg near line 270) has no
     computable definition: no lease object exists in code. Define it operationally (for example
     an executed action outside the parsed action set, or a `violation_executed` under `code`) or
     drop it.
15. `docs/LEAN-AUTORESEARCH-PROPOSAL.md` (Cursor section 7): Python mirror cut as a scorer (no
    pinned toolchain means INVALID, not pass); Lean canaries that must score zero (`sorry`,
    `admit`, extra axioms, weakened statement, a lemma assuming the goal, unsealed import, any edit
    to the theorem); QGrid task family deferred (freeze a tiny export, never live-link); quantum
    stage out of every scored loop, the paper and the abstract; auto-research on cards deferred,
    likely dropped (a Goodhart engine; held-out sets only from another generator, scored once).
    My verdict: accept all five; they match our "no new planning before EP-1" rule.

## 8. For the implementer (code; not done)

1. `stats.hdi`: margin rule; "not interpretable" when the `Y_code - Y_none` interval is wholly
   below 0; count near-zero denominators, not only exact zeros.
2. `spend.BATCH_SPECS`: a sibling `pilot` batch (80 calls, USD 0.75) under the USD 9 code stop,
   outside `ep1` (G0-2R: `ep1` is token-bound at about 491 reserves).
3. Model-free canary suite in one test file: empty success, unknown task id, unmapped HTTP, truncated
   action, wrong returned model id, overspend trip, any-non-empty acceptance, fabricated source.
4. Static card check against the scorer's vocabulary; prompt-truncation logging; analysis refusal
   of scripted run ids on model figures.
5. A second, independently written scorer for `alloc`.
5a. Two pilot-only card files: "states the check" and a keyword-stuffed no-norm card, each matched
    to card A in bytes and tokens, and both run through the static vocabulary check.
6. External anchor for log heads (`cell.py` `log.head` and the board log share the writer's
   filesystem; `board.py` line 59 says so).
7. `backend_claude._record`: log the provider's response id and any request-id header.

## 9. Next action that needs no approval

Write the 3.9 case study ("accept if present" failures) from A0-1, G1b-2 and the lint gap, once
the canary suite (8.3) freezes them as tests that must score zero.

verified: 36bab4b (plus working tree) 2026-11-20
