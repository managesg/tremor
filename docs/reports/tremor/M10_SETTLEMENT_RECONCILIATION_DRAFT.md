# M10 settlement reconciliation — DRAFT for reviewer use

> DRAFT only. This draft claims no settlement is done. The lane reviews, edits and commits any adopted text.
> Scope: TREMOR GPU-hour and USD items recorded to date, the T7 hold, and the two M10 owner inputs (Console totals, timer).
> Method: every figure below is copied from a cited file:line; where a value is missing the row says OPEN with its holder.
> Status key: RECORDED = present in a ledger, receipt or recorded disposition; ESTIMATE = derived from recorded tokens and a price sheet, not a billed figure; OPEN = needed value not recorded or not yet binding.

## 1. GPU-hour and USD items recorded for TREMOR so far

Scope note: rows 1-29 are the R2/T7 settlement and USD items. The three GPU-hour approvals of `DECISION_LOG.md:303` are rows 30-32; they are approvals, not charges.

| # | Item | Figure | Source (file:line) | Status |
|---|------|--------|--------------------|--------|
| 1 | R2 native GPU reserved (M1 Spark calibration admission) | 0.100000 GPU-h reserved | `docs/reports/workplan-ep/Portfolio-evidence-and-resource-reconciliation-20261121.md:257` | RECORDED |
| 2 | R2 charged — M1 settlement | 0.023123 GPU-h; reconciles to 83.24227687099483 s | `Portfolio-evidence-and-resource-reconciliation-20261121.md:257`; `docs/reports/workplan-ep/R3-resource-accounting-audit.md:9`; `docs/reports/tremor/OWNER_DECISION_M10_release_and_T7.md:22` | RECORDED |
| 3 | R2 released | 0.076877 GPU-h; "No outstanding hold on this admission" | `Portfolio-evidence-and-resource-reconciliation-20261121.md:257`; `R3-resource-accounting-audit.md:9` | RECORDED |
| 4 | T7 retained generation time (floor on measured activity, not billed occupancy) | 2.405372 GPU-h = 8,535.6347455 s (three completed arms) + 123.7038407 s (two probes) | `Portfolio-evidence-and-resource-reconciliation-20261121.md:258`; `OWNER_DECISION_M10_release_and_T7.md:23,28` | RECORDED |
| 5 | T7 wall subtotal (three containers, includes startup, overlaps row 4, excludes probes) | 8,655 s wall | `Portfolio-evidence-and-resource-reconciliation-20261121.md:258`; `OWNER_DECISION_M10_release_and_T7.md:23` | RECORDED |
| 6 | T7 provisional hold (planning number; derivation not stated in the files, not re-derived here) | 4.0 GPU-h retained | `Portfolio-evidence-and-resource-reconciliation-20261121.md:258`; `OWNER_DECISION_M10_release_and_T7.md:24,28`; `docs/reports/workplan-ep/Execution-plan-20261123.md:43-44,1542,1585` | RECORDED as a hold; underlying occupancy OPEN (see §2) |
| 7 | Program planning balance after settled R2 charge and T7 hold | 65.976877 GPU-h; R2/R3 share 7.476877 GPU-h; L1–L8 nominal ceilings total 49 GPU-h | `Portfolio-evidence-and-resource-reconciliation-20261121.md:259`; `R3-resource-accounting-audit.md:9`; `OWNER_DECISION_M10_release_and_T7.md:25` | RECORDED |
| 8 | Residual shared capacity | Plan assigns the remaining 9.5 GPU-h to additional work; `Execution-plan-20261123.md:487-489` projects 9.4 GPU-h shared among the adapter, Grover transfer, replication and controller if the 0.1 GPU-h SmolLM3 reserve is placed | `Portfolio-evidence-and-resource-reconciliation-20261121.md:259`; `Execution-plan-20261123.md:487-489` | RECORDED as a planning figure; current availability OPEN (resource owner, `Portfolio-evidence-and-resource-reconciliation-20261121.md:259`) |
| 9 | Proposed SmolLM3 reserve (not yet a binding reservation) | 0.1 GPU-h; would leave 9.4 GPU-h in that row and 65.876877 GPU-h program total | `Portfolio-evidence-and-resource-reconciliation-20261121.md:259`; `Execution-plan-20261123.md:487-489`; `OWNER_DECISION_M10_release_and_T7.md:26` | OPEN — needs a binding reservation by the resource owner (`Portfolio-evidence-and-resource-reconciliation-20261121.md:259`) |
| 10 | Hosted API ledger total (four pinned local ledgers, 417 uniquely paired reservations and charges) | USD 0.0413027 (stored sum 0.041302700000000000620) | `Portfolio-evidence-and-resource-reconciliation-20261121.md:260`; `OWNER_DECISION_M10_release_and_T7.md:33` | RECORDED (local ledger; not yet reconciled to the Console, see §3) |
| 11 | Hosted API by batch — canary | USD 0.0046625; 46,605 in / 4 out tokens | `OWNER_DECISION_M10_release_and_T7.md:34` | RECORDED |
| 12 | Hosted API by batch — pilot | USD 0.0114893; 41,088 in / 14,761 out tokens | `OWNER_DECISION_M10_release_and_T7.md:34` | RECORDED |
| 13 | Hosted API by batch — pilot2 | USD 0.0069008; 41,238 in / 5,554 out tokens | `OWNER_DECISION_M10_release_and_T7.md:34` | RECORDED |
| 14 | Hosted API by batch — pilot3 | USD 0.0182501; 112,706 in / 13,959 out tokens | `OWNER_DECISION_M10_release_and_T7.md:34` | RECORDED |
| 15 | WSP-R1 tokens (input to the estimate; model reported as "Opus", cache tier not recorded) | 8 calls; 62 in, 39,791 out, 983,957 cache-create, 1,841,140 cache-read tokens | `docs/reports/tremor/WSP_R1_COST_ESTIMATE.md:5` | RECORDED (tokens); model and tier OPEN (`WSP_R1_COST_ESTIMATE.md:5,17,21`) |
| 16 | WSP-R1 cost if claude-opus-5-5 | USD 6.08 (5-min cache writes) to USD 9.04 (1-h cache writes) | `WSP_R1_COST_ESTIMATE.md:11,15,17` | ESTIMATE — not a billed figure (`WSP_R1_COST_ESTIMATE.md:1,17`) |
| 17 | WSP-R1 cost if claude-sonnet-5-5 (reference only) | USD 3.04 to USD 4.52 | `WSP_R1_COST_ESTIMATE.md:12,15` | ESTIMATE |
| 18 | WSP-R1 cost if claude-fable-5-2 (reference only) | USD 11.80 to USD 17.70 | `WSP_R1_COST_ESTIMATE.md:13,15` | ESTIMATE |
| 19 | WSP-R1 billed figure | OPEN — "The billed figure stays with the billing ledger (Console)" | `WSP_R1_COST_ESTIMATE.md:17,21` | OPEN — holder: billing ledger / Console reader (see §3) |
| 20 | Price sheet used for rows 16–18 (USD per million tokens; fetched 2026-11-26; identical rates to the 2026-11-20 sheet) | e.g. claude-opus-5-5: input 4, output 20, cache-read 0.2, cache-write 5m 5, 1h 8 | `docs/reports/tremor/WSP_R1_COST_ESTIMATE.md:7`; `docs/reports/tremor/price-sheet-20261126.json:2,5,30-36` (sha256 `2edb8b5c…` at `WSP_R1_COST_ESTIMATE.md:7`) | RECORDED |
| 21 | Owner paid-call approval envelope for TREMOR (M2, M7, D8 refetch) | USD 10 total | `WSP_R1_COST_ESTIMATE.md:19`; `docs/reports/tremor/DECISION_LOG.md:265` ("paid-call budget USD 10 total approved by the owner via PC, running total 0.00") | RECORDED |
| 22 | Pilot 4 cap (one batch; no Pilot 4 call has run) | USD 0.25; 260 calls; 598,000 tokens | `DECISION_LOG.md:201,265`; `WSP_R1_COST_ESTIMATE.md:19`; caps in code at `src/murmuration/spend.py:69` (via `DECISION_LOG.md:285`) | RECORDED as a cap; spend RECORDED as 0 calls (`DECISION_LOG.md:273,303`) |
| 23 | EP-1 cap (canary counted inside) | USD 5.00; 500 calls; 1,250,000 tokens | `WSP_R1_COST_ESTIMATE.md:19`; `DECISION_LOG.md:201`; `src/murmuration/spend.py:57,59` (comment "the canary counts INSIDE ep1") | RECORDED as a cap; spend OPEN |
| 24 | Pilot 4 + EP-1 combined ceilings | USD 5.25, inside the USD 10 envelope (row 21) | `WSP_R1_COST_ESTIMATE.md:19`; `DECISION_LOG.md:265` | RECORDED |
| 25 | Hard cap in code (no argument can raise it) | HARD_CAP_USD = 10.0 | `src/murmuration/spend.py:48` (cited at `DECISION_LOG.md:285` context) | RECORDED |
| 26 | Paid total to date for TREMOR | USD 0.00; "no paid call has run". This 0.00 is the running total against the USD 10 envelope only; it is not yet reconciled with the USD 0.0413027 in the local ledgers (rows 10-14), which sit outside that count or predate it (not stated in the files) | `DECISION_LOG.md:265,273,283,303`; `docs/reports/tremor/MILESTONE_GAP_MATRIX_20261126.md:13` | RECORDED as a running total; reconciliation with rows 10-14 OPEN (holder: PC / Alejandro) |
| 27 | How the paid total is computed (read-only tool) | total = every charge line + `worst_usd` of every reserved call with no charge; counts only the given directory | `lab/tremor_spend_total.py:1-3,27,60-61` | RECORDED (method) |
| 28 | Provider Console total and current budget availability | `provider_console_total_usd: null`; `current_available_budget_usd: null` — both unknown today | `OWNER_DECISION_M10_release_and_T7.md:35`; `Portfolio-evidence-and-resource-reconciliation-20261121.md:260` | OPEN — holder: PC / Alejandro (see §3) |
| 29 | M10 local release adoption (context: not a settlement) | 14-patch, 50-file tree is the local release of record; inventory sha256 `36ee25cd…5074a`; nothing copied, committed, pushed or published by adoption | `docs/reports/tremor/M10_LOCAL_RELEASE_ADOPTION_20261123.md:7,24-29` ("Nothing was copied, committed into the release tree, pushed or published", line 24); `OWNER_DECISION_M10_release_and_T7.md:61` | RECORDED as a disposition; G8/publication OPEN (`M10_LOCAL_RELEASE_ADOPTION_20261123.md:26`) |
| 30 | R5 B0 cost and floor/ceiling probe approval (figure to be re-measured on Inkling, not carried from Qwen) | about 0.277 GPU-h on the local model; reservation decided YES by the line author; does not start a run | `DECISION_LOG.md:303` | RECORDED as an approval; no charge recorded; admission and window OPEN (other people's actions, `DECISION_LOG.md:303`) |
| 31 | R5 B1 variance pilot approval | about 2.592 GPU-h; YES, conditional on B0 showing neither floor nor ceiling at n=8 | `DECISION_LOG.md:303` | RECORDED as a conditional approval; no charge recorded |
| 32 | R6 P0 probe of the resident Inkling slot approval | no figure recorded | `DECISION_LOG.md:303` | RECORDED as YES in principle; figure OPEN |

Reviewer notes on Table 1:

- Rows 2–3 are the only settled GPU charge in the table; row 6 is a hold, not a charge, and rows 4–5 do not convert into billed occupancy (`OWNER_DECISION_M10_release_and_T7.md:28`).
- Rows 16–18 are one estimate under three model assumptions, not three costs; the lane must not add them together (`WSP_R1_COST_ESTIMATE.md:15,17`).
- WSP-R1 ran on 2026-11-24, before the USD 10 approval and on a separate model ledger, so it is not counted against row 21 unless the owner decides otherwise (`WSP_R1_COST_ESTIMATE.md:19`).
- If the owner decides WSP-R1 does count against the USD 10, headroom is USD 10 minus the billed figure (row 19), and Pilot 4 plus EP-1 would not both fit at the upper estimate — a decision for the owner, not the lane (`WSP_R1_COST_ESTIMATE.md:19`).
- D6 defers the canary-versus-Console reconciliation until publication, and Pilot 4 criterion 7 is its own separate Console check (`OWNER_DECISION_M10_release_and_T7.md:15,40`).

## 2. The T7 provisional 4.0 GPU-hour hold and what would release it

Current state (all RECORDED):

- The hold is 4.0 GPU-hours, retained because "Exact GPU attachment, full attempted occupancy and cleanup remain unavailable" (`OWNER_DECISION_M10_release_and_T7.md:24`; `Portfolio-evidence-and-resource-reconciliation-20261121.md:258`).
- The files do not state how 4.0 was derived, so it is not re-derived here (`OWNER_DECISION_M10_release_and_T7.md:28`).
- The planning balance in row 7 already includes this hold (`Portfolio-evidence-and-resource-reconciliation-20261121.md:259`; `R3-resource-accounting-audit.md:9`).
- The execution plan keeps the same position: "Historical billable occupancy remains unavailable and the existing 4.0 GPU-hour hold remains in the planning balance" (`Execution-plan-20261123.md:1541-1542`).

Why the retained T7 numbers do not release the hold:

- The journal replay found 11 named T7 endpoint joins and 28 Docker task-deletion records whose runtime IDs cannot be linked to the T7 names, plus three unassigned NVIDIA memory warnings (`OWNER_DECISION_M10_release_and_T7.md:30`; `Execution-plan-20261123.md:1580-1585`).
- The monitor replay saw 126 arm-name sightings that do not bind container instances (`OWNER_DECISION_M10_release_and_T7.md:30`; `Execution-plan-20261123.md:1537-1542`).
- The dated readback reaches the same conclusion: the records "supply no identity join between the named attempts and the deletion records" (`Execution-plan-20261123.md:1580-1585`).

Evidence that would release or resize the hold:

- A record that joins each of the three named T7 container instances to its Docker runtime ID, its GPU attachment interval and its terminal cleanup (`OWNER_DECISION_M10_release_and_T7.md:30`).
- Absent such a join, the only alternatives are to keep the hold (the default) or for the resource owner to record a named, reasoned release or a different figure; no agent may invent that figure (`OWNER_DECISION_M10_release_and_T7.md:30,49`).
- Holders for the disposition: the resource owner and the claims reviewer (`OWNER_DECISION_M10_release_and_T7.md:9,15`; `Execution-plan-20261123.md:43-44`).

Reviewer action: keep the 4.0 hold until one of the two bullets above is satisfied; do not release it on the current evidence (`OWNER_DECISION_M10_release_and_T7.md:9,49`).

## 3. Owner inputs still needed: Console totals and the timer executor

### 3a. Console totals needed — holder: PC (Alejandro reads and pastes)

The provider is the Anthropic Console, and the repo does not name the exact Console page labels, so the reader states the page name and the "data as of" time (`OWNER_DECISION_M10_release_and_T7.md:32`).

The reader pastes, in chat (`OWNER_DECISION_M10_release_and_T7.md:15,32-36`):

1. Total USD cost, all dates, for the workspace or key used by the Murmuration spend ledgers; the local comparison value is USD 0.0413027 (row 10) (`OWNER_DECISION_M10_release_and_T7.md:33`).
2. If the page allows a date filter, USD cost and input/output tokens per batch, to compare with rows 11–14 (canary, pilot, pilot2, pilot3); batch dates come from the ledger timestamps in `runs/spend/*.jsonl` (`OWNER_DECISION_M10_release_and_T7.md:34`).
3. Current available budget or credit balance, and the workspace spend limit (the approvals call for a limit of USD 10 or less); both are unknown today (row 28) (`OWNER_DECISION_M10_release_and_T7.md:35`).

Handling rules:

- Console data lags (it did not show a canary 21 minutes old), so the reader notes the read time (`OWNER_DECISION_M10_release_and_T7.md:36`).
- Unknown stays unknown: if a number cannot be read, the reader pastes "not available", not an estimate (`OWNER_DECISION_M10_release_and_T7.md:36`).
- Before the paste, the lane runs `bash runs/portfolio-api-nested.x81FKM/verify.sh` and `sha256sum -c runs/portfolio-reconciliation.BNttQL/evidence.sha256`; after recording, it reruns both and confirms the stored report is unchanged (`OWNER_DECISION_M10_release_and_T7.md:39-41`).
- This step is accounting records only: no spend, run, reservation or ledger edit, and it does not authorize Pilot 4, EP-1 or any paid call (`OWNER_DECISION_M10_release_and_T7.md:43`).

### 3b. Timer executor — holder: PC (Alejandro, user-manager owner)

Timer in scope: the one-shot `tremor-public-update-20261122.timer` (Decision 3) (`OWNER_DECISION_M10_release_and_T7.md:11,84-113`).

Recorded state (November 23, read-only):

- `is-enabled` returns `enabled`; ActiveState `inactive`, Result `success`; no NEXT and no LAST in `list-timers --all` (`OWNER_DECISION_M10_release_and_T7.md:86`).
- `OnCalendar=2026-11-22 11:00:00 America/New_York` with `Persistent=true`; `Linger=yes`; the service ends in a `git push` to the public remote, guarded only by a staged-repo HEAD check that a restage would remove (`OWNER_DECISION_M10_release_and_T7.md:86-88`).
- The M10 adoption record confirms the split: "timer disposition stays with its named executor" and the timer stays open with that owner (`M10_LOCAL_RELEASE_ADOPTION_20261123.md:3,29`).

Recommended executor action (not `mask`):

- Run `systemctl --user disable tremor-public-update-20261122.timer`, then confirm `is-enabled` returns `disabled` and no next trigger remains; the full before/hold/after command block is recorded in the packet (`OWNER_DECISION_M10_release_and_T7.md:92-104`).
- Do not use `mask`: it fails against a real unit file, and forcing it would replace the unit text with a link to `/dev/null` (`OWNER_DECISION_M10_release_and_T7.md:105`).
- Undo is `systemctl --user enable …`, but re-enabling with `Persistent=true` and a past `OnCalendar` can fire an immediate catch-up run, so it must not happen before a separate publication approval (`OWNER_DECISION_M10_release_and_T7.md:107`).

## 4. Closing checklist: lane work vs. named-person work

### Lane work (no gate; local edits, reads and tests only)

- [ ] Re-run the two pre/post Console checks and confirm byte-identical output once the Console numbers are pasted (`OWNER_DECISION_M10_release_and_T7.md:39-41`).
- [ ] Record the pasted Console totals with the read time and compare them to rows 10–14; leave any unread number as "not available" (`OWNER_DECISION_M10_release_and_T7.md:36,40`).
- [ ] Keep the 4.0 GPU-hour hold in the planning balance until §2 is satisfied; record any reviewer disposition as a new dated note without editing the original ledgers (`OWNER_DECISION_M10_release_and_T7.md:45,49`).
- [ ] Recompute the paid total with `lab/tremor_spend_total.py` over `runs/spend` before any future paid batch, adding any other spend by hand (`lab/tremor_spend_total.py:1-3,60-61`).
- [ ] Keep WSP-R1 as an ESTIMATE (rows 16–18) and the billed figure as OPEN (row 19) in all lane documents (`WSP_R1_COST_ESTIMATE.md:17,21`).

### Stays with a named person (lane does not do these)

- [ ] **Alejandro / PC — Console reading:** read the Anthropic Console page and paste the three totals in §3a (`OWNER_DECISION_M10_release_and_T7.md:9,15,32`).
- [ ] **Resource owner and claims reviewer — T7 disposition:** keep, release or resize the 4.0 hold only on the §2 join or a named, reasoned figure (`OWNER_DECISION_M10_release_and_T7.md:9,15,30`).
- [ ] **Alejandro / PC — timer executor:** run `systemctl --user disable` on `tremor-public-update-20261122.timer` (not `mask`) and confirm the after-state (`OWNER_DECISION_M10_release_and_T7.md:11,90-104`; `M10_LOCAL_RELEASE_ADOPTION_20261123.md:3,29`).
- [ ] **Release owner and Alejandro — adoption follow-ons:** G8 sharing and any publication need a separate, later yes; applying the 14 patches into the staged repo is also a separate ask (`OWNER_DECISION_M10_release_and_T7.md:53,61`; `M10_LOCAL_RELEASE_ADOPTION_20261123.md:26-27`).
- [ ] **Owner — WSP-R1 accounting decision:** decide whether WSP-R1 counts against the USD 10 envelope (row 21) once the billed figure (row 19) is known (`WSP_R1_COST_ESTIMATE.md:19`).
- [ ] **Key holder — Pilot 4 / EP-1 execution:** Pilot 4 and EP-1 still need `MURMURATION_EP1_KEY` and their own approvals; nothing in this reconciliation authorizes a paid call (`DECISION_LOG.md:273,285`; `OWNER_DECISION_M10_release_and_T7.md:43`).

## What this draft did not check

- The Console itself, the T7 container-to-GPU join, and GitHub rendering were not checked here (`OWNER_DECISION_M10_release_and_T7.md:115-116`).
- The recorded WSP-R1 token file, the model and cache tier actually used, and whether subscription use is billed at all were not checked (`WSP_R1_COST_ESTIMATE.md:21`).
- Whether `systemctl --user disable` behaves exactly as expected on this host was not run (`OWNER_DECISION_M10_release_and_T7.md:116`).
