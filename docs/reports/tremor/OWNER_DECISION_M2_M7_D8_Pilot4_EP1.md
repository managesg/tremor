# Owner decision packet: M2 (Pilot 4, then EP-1) and M7 (Grover) under D8

Prepared 2026-11-23 UTC on `seabridge-spark`, repository `/home/adelmar/SeaBridgeAI/murmuration`, branch `master`, HEAD `4442b97` at preparation; the repo HEAD is now `8de57ef`, and `git diff --name-only 4442b97 HEAD` lists only `docs/reports/workplan-ep/R1-row157-contention-pin.md` and `lab/r1_*` files (plus their tests), none of which is a cited source. Read-only preparation: no pilot was run, no network, no paid or live call, no git write. Every figure below is copied from a repo file (cited as path:line). Where an input does not exist it is listed as a precondition, not invented.

## 0. Recommendation (read this first)

**Approve with changes.** Approve the ceilings in section 3 as a conditional authorization that takes effect only when every precondition in section 2 is recorded. Do not approve a launch today, and do not approve M7 execution at all: M7 has no spend figure, no frozen protocol and no custodian in the repo.

Two main reasons:

1. **The instrument cannot launch, and its main known defect is unaddressed.** `pilot4` does not exist in `spend.py` or the driver (section 4). Neither draft wording is selected. Pilot 3 failed criterion 2 (largest reply 263 output tokens against a 150 ceiling), and the offline replays use archived replies, so they give no evidence that either wording shortens replies (`runs/m2-enabled-response-custody.cHx1kP/OWNER.md:5-7`). Spending USD 0.25 on an unchanged-risk instrument would likely repeat the failure.
2. **The money is already bounded by repo figures, so a conditional yes is safe.** Pilot 4 is capped at USD 0.25 / 260 calls / 598,000 tokens, EP-1 at USD 5.00 / 500 calls / 1,250,000 tokens, and the combined 5.25 plus prior spend sits far under the USD 10 code cap. The one time-critical item is the price sheet, which the loader refuses from 2026-11-24 (section 3.3).

## 1. What D8 needs decided (exact list)

The repo never defines D8 in `docs/reports/ep-approvals.md` (D1-D6 only, lines 163-171). The handoffs use "D8 hold" to mean the owner hold on Pilot 4 and EP-1 (`docs/reports/HANDOFF_TREMOR_SPARK_CHAT_MOVE_20261122.md:16,50`; `docs/reports/workplan-ep/Execution-plan-20261123.md:42`). Alejandro should confirm that reading. Under it, the decisions are:

| # | Decision | Owner | Source |
|---|---|---|---|
| D8-a | **Named release** of the D8 hold for one Pilot 4 batch, in a window when paid execution is permitted. Addendum 10 authorizes "one Pilot 4 after the gates pass" but the overnight directive excludes paid calls. | Alejandro | `ep-approvals.md:174-186`; `Pilot4-pricing-verification-gates.md:3` |
| D8-b | **Wording**: choose `packet` or `array_only` (or a third), as the identical second-round instruction in all arms. Both are unselected. | Preregistration author | `lab/pilot3_prompt_replay.py:16-19`; manifest `selected_candidate: null` (`lab/pilot4_preflight_manifest.py:146`) |
| D8-c | **Scoring**: whether the 150-token maximum applies to all five conditions or the three core conditions; the completed-call denominators for reply format and arithmetic (gates 3 and 4) versus shape/identity/spend checks over all attempts. | Preregistration author | `P3-clearance-criterion-2.md:91-96`; `Pilot4-pricing-verification-gates.md:28` |
| D8-d | **Order**: whether the new order result may supersede Pilot 3's `shared` selection (EP1.md:279), and what happens if the §13.16b rule gives a different order or none. Pilot 3 stays immutable. | Preregistration author | `Pilot4-pricing-verification-gates.md:28`; `P3-clearance-criterion-2.md:60` |
| D8-e | **Pricing coverage**: ruling on whether a second canary is needed, because `spend.py` and `backend_claude.py` changed after the one-call canary (EP1.md:1100-1102 says that is "an owner decision, not a re-run"). Plus an independent reviewer verifying the resulting coverage on the current code. | Alejandro + independent spend reviewer | `Pilot4-pricing-verification-gates.md:22,29` |
| D8-f | **Driver clearance**: independent re-gate of the implemented Pilot 4 batch (byte neutrality, schedule replay, distinct ledger/output, parser/scorer, reservation bounds, stop paths). | Implementer + independent driver reviewer | `P3-clearance-criterion-2.md:98-103`; `Pilot4-pricing-verification-gates.md:30` |
| D8-g | **Spend ceiling** and the allocation it comes from (section 3). | Alejandro | section 3 |

## 2. Preconditions (missing inputs; none are invented here)

- P1. D8-b, D8-c, D8-d recorded by the preregistration author. No such record exists; `author_review_status` is `pending`.
- P2. D8-e ruling on a second canary. If one is required, the owner must also set its cap; the code allows one call, USD 0.05, 90,300 tokens inside `ep1` (`spend.py:67`), and the existing canary already settled `complete`, so a second one needs a reviewed code path, not just a command.
- P3. The `pilot4` implementation (section 4) written, committed locally and independently re-gated (D8-f).
- P4. A price sheet that is valid for the whole window. The pinned sheet (sha256 `16b204c23aa5ce3b169e44a3b2608ee39e3aa8da14b6b1838d8cb15a3356984f`, fetched 2026-11-20) is refused from 2026-11-24 (`spend.py:45,187-188`). A refetch is a network step and is not covered by this packet; a new sheet also cannot replace the digest already pinned to the `ep1` parent ledger without a continuity review (`Pilot4-pricing-verification-gates.md:16`). Check with `lab/pilot4_price_window.py` (it takes the independently retained digest, start and end instants).
- **P4 lapse status (checked 2026-11-23 21:56 UTC):**
  - **Rule:** `PriceSheet` refuses a sheet whose UTC fetch date is more than `MAX_AGE_DAYS = 3` days old (`src/murmuration/spend.py:45,186-188`; `expires_on()` = fetched + 3 days, `:191-192`). The pinned sheet was fetched 2026-11-20, so it is valid through 2026-11-23 and refused from 2026-11-24 00:00 UTC, about two hours after this check. For any window not finished tonight, treat it as **lapsed**.
  - **No change in this packet:** no pricing file, timer or cap was changed by this update.
  - **What a fresh price window needs, in order:**
    1. A named yes to refetch the price sheet. This is a network step.
    2. The new sheet's sha256 and its source recorded.
    3. A continuity review, because the `ep1` parent ledger already pins the old digest (`docs/reports/workplan-ep/Pilot4-pricing-verification-gates.md:16`). A new sheet cannot silently replace it.
    4. Exact start and end instants for the window, checked with `lab/pilot4_price_window.py` against the new digest. The window must end no more than 3 days after the new fetch date.
    5. A re-run of the D8-e pricing-coverage ruling against the new sheet.
