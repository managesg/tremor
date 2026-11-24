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
  - **Status now:** lapsed. Since 2026-11-24 00:00 UTC the pinned sheet is refused, so M2 and M7 need steps 1 to 5 above before any window.
- P5. A named allocation for the USD 0.25. The proposal table lists only "Pilot 2 and EP-1" at 0.3 / 5.25 (`docs/PROPOSAL-RESIDENCY-V3.md:944`); Pilot 4 is called "a separately assigned allocation" (`P3-clearance-criterion-2.md:67`). The USD 170 total has about 10.5 reserve (`PROPOSAL-RESIDENCY-V3.md:958`), enough, but the line must be named.
- P6. A human who can read the Anthropic Console for the Pilot 4 reconciliation (check 7), and a reviewer for the 30-episode manual read.
- P7. Only for M7: everything in section 7.

## 3. Spend ceiling recommended (all figures from the repo)

### 3.1 Pilot 4
**USD 0.25, 260 calls, 598,000 tokens, one batch.** Source: the request Alejandro answered (`ep-approvals.md:176-178`), the same caps as `pilot2` and `pilot3` (`src/murmuration/spend.py:63,65`). Design calls: 30 episodes x 8 = 240; 20 spare attempts for retries and re-runs (`Pilot4-pricing-verification-gates.md:13`). Full reservation: 260 x USD 0.00055 = USD 0.143 (`:12-13`). Per-call caps: 2,000 input and 300 output tokens (`spend.py:50`).

### 3.2 EP-1 (after all seven Pilot 4 checks and the author's freeze)
**USD 5.00, 500 calls, 1,250,000 tokens**, canary counted inside (`spend.py:57`; `prereg/EP1.md:638-643`). 60 episodes = 3 arms x 20 sets x 8 calls = 480 calls, 19 usable spares for infrastructure re-runs (EP1.md:192-206). The cap is never raised after the freeze (EP1.md:642-643).

### 3.3 Totals
- Prior recorded spend: USD 0.0413027 (canary 0.0046625, pilot 0.0114893, pilot2 0.0069008, pilot3 0.0182501; from `runs/spend/*.jsonl` charge lines, total matches `Pilot4-pricing-verification-gates.md:14`).
- Pilot 4 plus EP-1 ceilings: 0.25 + 5.00 = **USD 5.25** (Pilot 4 is outside the 5.25 row (that row is Pilot 2 and EP-1, and Pilot 2 already used its 0.25); its allocation must be named (P5)). With prior spend: 5.2913027, under `HARD_CAP_USD = 10.0` (`spend.py:46`) and the funded USD 170 (`PROPOSAL-RESIDENCY-V3.md:37,936-937`).
- No cap change is needed or requested. Do not use the "USD 150" or "USD 170 code cap" route (D4, `ep-approvals.md:169`) for this.

## 4. Pilot 4 command: none exists

Searched `src/`, `lab/`, `tests/`: `pilot4` appears only in review tools (`lab/pilot4_preflight_manifest.py`, `lab/pilot4_price_window.py`, `lab/ep1_bracket_receipt.py:83`). `BATCH_SPECS` has no entry (`spend.py:55-67`) and the CLI offers only `canary, pilot, pilot2, pilot3, run` (`src/murmuration/__main__.py:105`; kind map `src/murmuration/ep1.py:773`). The gates doc says the same (`Pilot4-pricing-verification-gates.md:30`; `P3-clearance-criterion-2.md:64`).

**The command shape that Pilot 3 used (for reference, do not run):**

```
MURMURATION_EP1_KEY=<in the environment only, never in a file or argument> \
PYTHONPATH=src python3 -m murmuration ep1 pilot3 \
  --out-dir runs/ep1-live/pilot3 --schedule-seed 0 --i-have-owner-confirm
```
Argv: `ep1 pilot3 --out-dir <dir> --schedule-seed 0 --i-have-owner-confirm`; refuses without the flag or `MURMURATION_EP1_KEY` (`ep1.py:753-771`). Ledger lands in `runs/spend/pilot3.jsonl`.

**Smallest missing piece for Pilot 4** (about six touch points, mirroring Pilot 3; implementer plus independent review, local commit only):
1. `spend.py` `BATCH_SPECS["pilot4"] = {"usd": 0.25, "calls": 260, "tokens": 598_000, "parent": None, "requires_settled": CANARY, "settled_reasons": ("complete",)}` (copy of line 65).
2. `ep1.py`: add `pilot4` to `KINDS` (:52), `PILOTS` (:53), `DEFAULT_SETS` = 6 (:57), `SPLIT` = train (:58), a new `ID_PREFIX` such as `p4` (:59), the kind map (:773); handle the mixed order schedule (shared on sets 0, 3, 4; per-agent on 1, 2, 5) instead of the Pilot 3 `ORDER_KINDS` path (:63).
3. The selected second-round instruction, applied only to round-2 requests, identical across arms (D8-b).
4. `__main__.py:105`: add `"pilot4"` to the subcommand names.
5. Output `runs/ep1-live/pilot4`, ledger `runs/spend/pilot4.jsonl`, 30 episode IDs, 240 call IDs, schedule digest `ba4f68ad0128073f8d338c16afd5adbdbbb68b06bfa249afe08e2bfc56cc5365` (`Pilot4-pricing-verification-gates.md:40`).
6. Tests for byte neutrality, schedule replay and the stop paths. Because this edits `spend.py` and `ep1.py`, it again touches the canary-coverage question (D8-e); decide that first.

Offline review manifest (safe to rerun): `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m lab.pilot4_preflight_manifest`. Retained report `runs/l1-baselines-pilot4-preflight.qvMLCj/pilot4.json`, sha256 `45b55302c2275a6f8e9948d1db5f2da29b8629197cc64c1849dd77f4a1efd609`; status `awaiting_review`, `execution_authorized_by_manifest: false`.

## 5. The seven Pilot 4 checks and how each is verified

Source: `P3-clearance-criterion-2.md:62-83` (EP-1 §13.16b). Evaluated on Pilot 4 evidence only, never pooled with Pilot 3, no threshold changes. Core conditions are read together across both orders (18 episodes, 144 planned calls).

| # | Check | Pass rule | Verification |
|---|---|---|---|
| 1 | Request shape | Zero HTTP 400; text-only response blocks | Ledger and episode records; HTTP 400 is also a code stop (EP1.md:11-12 area, `ep1.py:10`) |
| 2 | Output length | Zero `max_tokens` stop reasons; max output 150 tokens for the clearance read-off; record full-batch and per-condition maxima and every overage | Per-turn usage and stop reasons. Scope (5 vs 3 conditions) is D8-c. **Known failure at Pilot 3: 263 vs 150.** |
| 3 | Reply format | At most 7 malformed of 144 core replies; at most 4 of 48 in any core condition | Episode records; denominator fixed by D8-c |
| 4 | Arithmetic | At most 3 wrong among admitted work events (up to 72) | Score checks over the same records |
| 5 | Usable order | Existing §13.16b rule unmodified: `Y_none` mean in [0.30, 0.80] within an order; `none` has at least two executed duplicate work events and `code` zero; at least one set with different `Y_code` and `Y_none`; print the prescribed selection and the `shared` tie rule | `lab.pilot_clearance` run on the new output (Pilot 3 usage: `Pilot3-seven-criterion-replay.md:37`) |
| 6 | Scripted bracket | Floor exactly 0.25 and oracle exactly 1.0 in each arm | `lab/ep1_bracket_receipt.py`; EP1.md:761-763 |
| 7 | Reconciliation and review | Pilot 4 ledger agrees with the Anthropic Console for this batch; recorded manual reading of every episode's prompts, replies and log against the scores | Manual: P6. Console receipt, dated pricing and driver integration still owed (`m2-enabled-response-custody.cHx1kP/OWNER.md:22-24`). All 30 manual reviews are currently unavailable. |

A failed or missing check leaves the EP-1 freeze blocked (`P3-clearance-criterion-2.md:109-111`).

## 6. Then EP-1: the 60-episode step

Only after: all seven checks pass; author records the order result and approved digests; `prereg/EP1.md` carries `Status: FROZEN` and a valid `code_tree_hash` (currently `Status: DRAFT`, `code_tree_hash:` blank, EP1.md:11,18; checked in code by `_check_freeze`, `ep1.py:113-135`); B4 full-schedule and stop evidence done; Alejandro's own "confirm" (EP1.md:1104 onward). Then: `ep1 run` -> 3 arms x 20 held-out sets = 60 episodes, 480 calls, stop at USD 5, 500 calls, 1,250,000 tokens or any §12 stop (EP1.md:638-639). It needs its own admission; Pilot 4's authorization does not cover it ("EP-1 confirmatory run ... outside this approval", `Pilot4-pricing-verification-gates.md:3`). The `ar1` batch (USD 3.00) is not part of this packet.

## 7. M7 (Grover transfer): what a yes can and cannot cover

M7 depends on EP-1 (`Grover-transfer-protocol-draft.md:49`; `TREMOR_GOAL_AND_PLAN_20261123.md:41-42`). No Claude API figure or live allocation exists for Grover: "no live transfer allocation is established" (`Grover-transfer-protocol-draft.md:49`). Its only recorded resource figure is a share of 9.4 GPU-hours pooled with the adapter, replication and controller (`Execution-plan-20261123.md:489`), inside the funded 70 GPU-hours (`PROPOSAL-RESIDENCY-V3.md:937`). I therefore recommend: **no M7 approval beyond acknowledging the dependency.** Preconditions (all missing): EP-1 complete; frozen protocol with split, generator, contrasts, primary estimand, stopped-pair policy, defensible sample size; appointed independent custodian and scorer with an authenticated commitment issued before execution; reviewed offline validation of the custody manifest; measured resource admission placed inside the 70 GPU-hour program (`Grover-holdout-custody-checklist.md:25-29`; `Coordinator-blockers-20261122.md:35`). Public-only evidence (statistical envelope, scripted topology) is verified but does not establish inferential sample size or protected custody (`runs/grover-statistical-envelope.6Cln7i/OWNER.md`).

## 8. Scope

In: one Pilot 4 batch (Haiku 5.5, exact id `claude-haiku-5-5`, temperature 1.0, thinking disabled, no prefill), 30 episodes, 5 conditions x train sets 0-5; then, if cleared, one EP-1 run. Out: any cap change, a second Pilot 4, more than one canary without ruling, held-out sets in Pilot 4, the `ar1` batch, price-sheet refetch, any other provider, M7 execution, publication and D6 Console reconciliation (belongs to publication, `ep-approvals.md:171`), pushes.

## 9. Stop conditions enforced in code

- **Hard cap**: no argument can raise USD 10 (`spend.py:11,46`); reserve refuses when the worst case would cross the ceiling, the hard cap, `max_calls` or any batch cap (`spend.py:431-456,500-508`).
- **Per-batch caps**, never from arguments (`spend.py:55-67`; checked on every `Ledger()`).
- **Per-call caps**: 2,000 input, 300 output tokens (`spend.py:50,490-491`).
- **Batch stop** on any cache-creation token, a bad model, transport/other stop reasons from the closed set `cap, transport, http400, void_model, invalid_log, scorer_disagreement, refusal_loop, owner, crash` (`spend.py:23-27,53-54`); a stopped batch refuses all later reserves and cannot settle (`spend.py:520-527`).
- **Pilot gate**: opens only after the canary settled `complete` (`spend.py:61-65`).
- **Driver stops**: HTTP 400 at once, never re-run; third transport abort; malformed replies above 1/4 of the first block, 10% overall or 15% in one condition; void on returned-model mismatch or usage above per-call cap; scorer disagreement; invalid log; Lean `INVALID`; overspent ledger; unexplained unbilled unknown; any cap before an episode could start (`ep1.py:8-24`). Pilot 3 numeric forms carried forward: more than 10 malformed in the first 40 calls, more than 24 overall, more than 7 in a condition (`P3-clearance-criterion-2.md:68`).
- **Paid-run refusal** without `--i-have-owner-confirm` and `MURMURATION_EP1_KEY`; EP-1 additionally refuses unless frozen (`ep1.py:753-771`).
- **Offline retry boundary** already exercised: at 260 attempts the 261st is refused with `MaxCallsExceeded`, zero transport, batch ends `stopped:cap`, and that episode is excluded from the comparison (`runs/pilot4-full-retry.ZwWZHE/OWNER_PACKET.md:10`). Unknown-attempt reservations are held at worst case, up to USD 0.0088822 (`:12`).

## 10. Rollback

- **Money cannot be returned.** Anything spent on Anthropic is gone, whatever the result. The most that can be lost on this yes: USD 0.25 for Pilot 4, and, if later released, USD 5.00 for EP-1 (reservation arithmetic says the real spend is far lower, 0.143 and about 0.27, but those are bounds, not promises).
- **Data rollback**: leave the run folders unused. Do not delete them (Safety Rule 1). Pilot 4 lives in its own `runs/ep1-live/pilot4`, `runs/spend/pilot4.jsonl` and `p4` IDs, so Pilot 3 and earlier ledgers remain immutable. A stopped batch is not settled and is not retried; a new attempt needs a new owner ask.
- **Code rollback**: the `pilot4` change is a local commit; revert with an approved `git revert` of that own SHA. No pushes are involved.
- A failed or void Pilot 4 leaves the EP-1 freeze blocked and keeps `shared` from Pilot 3; nothing else changes.

## 11. Tests

**Before** (offline, run today on HEAD `4442b97`, no key): `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -W ignore -m unittest tests.test_spend tests.test_backend_claude tests.test_ep1 lab.tests.test_pilot4_preflight_manifest lab.tests.test_pilot4_price_window` -> **Ran 215 tests, OK** (about 8 minutes). Add before launch: the new `pilot4` tests (item 6 of section 4); the offline retry replay `bash runs/pilot4-full-retry.ZwWZHE/verify.sh "$PWD/fresh-output" > fresh-report.json` then `cmp report.json fresh-report.json` (retained report sha256 `f474c08ee86973182440f16c3cf8ccdc8bdb2447c2d0608e0f65669641963896`); `bash runs/m2-enabled-response-custody.cHx1kP/verify.sh`; `python3 -m lab.pilot4_price_window` with the pinned digest and the exact window; EP-1 `dry-run` on the fake server (`python3 -m murmuration ep1 dry-run --out-dir <dir>`) returning GREEN.

**After**: `python3 -m lab.pilot_clearance runs/ep1-live/pilot4 runs/spend/pilot4.jsonl` (checks 1-6), `python3 -m murmuration ep1 analyse runs/ep1-live/pilot4`, a ledger-versus-Console comparison and the 30-episode manual read (check 7), then rerun the 215-test command to confirm nothing changed.

## 12. Risks

1. **Criterion 2 repeat.** Pilot 3 maximum 263 vs 150 ceiling, all 240 calls ended `end_turn` (`P3-clearance-criterion-2.md:3`). The `max_tokens` cap is 300 so a reply can exceed 150 without hitting the cap. Temperature 1.0 means a new batch can differ even with identical prompts (`P3-clearance-criterion-2.md:58-59`). Chance of a second failure is real and unquantified; the cost of finding out is up to USD 0.25.
2. **Wording is unvalidated.** Replays use archived fixtures, so neither draft is shown to change replies.
3. **Price sheet expires after 2026-11-23** (valid today, refused 2026-11-24); a refetch is a separate network step and cannot swap the digest pinned to the `ep1` parent without review.
4. **Canary coverage lapsed** on changed `spend.py` and `backend_claude.py`; and Pilot 4 itself must edit `spend.py` and `ep1.py` again.
5. **Console reconciliation and manual read are human-only** and not yet scheduled; check 7 cannot pass without them. Unknown-attempt usage cannot be billed exactly from the ledger.
6. **Ambiguity in D8.** The repo does not define it; confirm scope.
7. **Overnight hold.** Paid execution was excluded for the overnight window; a named release is needed.
8. **M7 and EP-1 cascade**: a Pilot 4 failure blocks EP-1, and so M7. No part of M7 can be rescued by spending more.

## 13. Suggested wording for Alejandro's yes

"Approve one Pilot 4 batch at USD 0.25 / 260 calls / 598,000 tokens, and, if all seven checks pass and the author freezes EP-1, one EP-1 run at USD 5.00 / 500 calls / 1,250,000 tokens. Takes effect only when the preregistration author has recorded wording, scoring and order decisions, the spend and driver reviewers have cleared the exact code and pricing coverage on a price sheet valid for the window, and I have named the release window. EP-1 still requires my two confirms per prereg/EP1.md:1104. No cap change. M7 not approved."
