# Pilot 4 and EP-1 readiness, 2026-11-27 (offline, no key, no network, no paid call)

Checked 2026-11-27T13:23Z to 13:29Z on this host (`/home/adelmar/SeaBridgeAI/murmuration`, HEAD `4c9049b`; `src/` and `prereg/` have no uncommitted change).
Paid spend for Pilot 4 and EP-1: USD 0.00; recorded total of earlier batches (canary and pilots) USD 0.0413027 (`PYTHONPATH=src python3 -m lab.tremor_spend_total runs/spend` prints `total_usd=0.0413027 cap_total=10.0`; no Pilot 4 or EP-1 call has been made). Owner authorisation to PREPARE both runs inside the shared USD 10 is the task statement; it is not a run confirm.
Command order and outputs: `EP1_RUN_PACKET.md`. Pilot 4 detail: `PILOT4_RUN_PACKET.md`.

## 1. Verdict

**READY-EXCEPT:** the key (named key holder), Alejandro's run "confirm" for Pilot 4, check 7 (Console reader and the 30-episode reviewer), the EP-1 freeze (preregistration
author), Alejandro's second "confirm" for EP-1, and a decision on the sheet window for EP-1. Everything a script can verify offline is green. Pilot 4 can start the moment the key and
the confirm exist. EP-1 cannot, by design, and may not fit the price-sheet window.

## 2. Preconditions

| # | Precondition | Status | Evidence |
|---|---|---|---|
| 1 | Key `TREMOR_EP1_KEY` (or legacy `MURMURATION_EP1_KEY`) in the run shell | BLOCKED: key holder (named person) | both unset in this session (checked, values never read); `ep1.py:771-776` |
| 2 | Alejandro's run confirm for Pilot 4 (`--i-have-owner-confirm`) | BLOCKED: Alejandro | CLI without the flag: `{"error": "refused: a paid run needs the explicit --i-have-owner-confirm flag"}` exit 2 (run offline) |
| 3 | `pilot4` exists in code with the owner caps | READY | `spend.py:69` (USD 0.25, 260 calls, 598,000 tokens, `requires_settled` canary); `ep1.py:54-65,781`; `__main__.py:105` |
| 4 | Price sheet loads and passes the pre-reservation check for Pilot 4 | READY | `Ledger.check_sheet()` on a temp copy of `runs/spend`: `pilot4 new sheet OK` (13:2xZ). Default sheet refused: `price sheet fetched 2026-11-20 is 7 days old (limit 3)` (so `--price-sheet` is mandatory) |
| 5 | Sheet digest and window | READY | `lab.pilot4_price_window` at 2026-11-27T13:23:38Z to 2026-11-28T23:59:59Z: `price_sheet_valid_for_window`, `valid_through_utc_date` 2026-11-29, `authorizes_execution` false; `sha256sum` of `runs/d8-price-refetch.20261126T0050Z/price-sheet.json` and `price-sheet-20261126.json` both `2edb8b5c...a0f2` |
| 6 | Sheet age at run time (limit `MAX_AGE_DAYS = 3`, `spend.py:46`) | READY for 2026-11-27 and 2026-11-28; REFUSED from 2026-11-30 00:00Z | `expires_on()` prints 2026-11-29. If a run would start on 2026-11-30 or later, or EP-1 would cross it, the sheet is too old: owner or PC refetches (network, named yes), same rates required, re-run the window check (`EP1_RUN_PACKET.md` section 1) |
| 7 | Clean slate for `pilot4` | READY | `runs/spend` holds only `canary pilot pilot2 pilot3 .jsonl`; no `runs/spend/pilot4.jsonl`, `runs/ep1-live/pilot4`, `runs/ep1-live/pilot4-stdout.txt`; `pgrep -af "tremor ep1"` empty; `runs/spend/*.jsonl` checksums identical before and after all checks |
| 8 | Canary settled `complete` (gate for `pilot4`) | READY | `totals()["stops"]` includes `('canary', 'complete')`; `spend.py:69` `settled_reasons ("complete",)` |
| 9 | D8-b wording `array_only`, D8-c scope, D8-d order, D8-e no second canary, recorded by the line author | READY (as recorded) | `DECISION_LOG.md:265-273`; `PILOT4_AUTHOR_RECORD.md`. The review-only manifest still prints `author_review_status: pending`, `selected_candidate: null`, `status: awaiting_review`, `execution_authorized_by_manifest: false` (`python3 -m lab.pilot4_preflight_manifest`, run today); it is pinned to Pilot 3 evidence and sets nothing. A signed non-author sign-off of the wording is UNVERIFIED |
| 10 | Independent spend and driver review of the sheet and flag code | READY (per log) | `DECISION_LOG.md` 2026-11-26 entries: Opus ACCEPT after fixes; commit `33343d2` is in `git log`; not re-reviewed today |
| 11 | Offline unit tests (about 8 minutes, no key) | see section 3 | `tests.test_spend tests.test_backend_claude tests.test_ep1 lab.tests.test_pilot4_preflight_manifest lab.tests.test_pilot4_price_window lab.tests.test_pilot4_rehearsal` |
| 12 | Pilot 4 loopback rehearsal | READY | `lab.tests.test_pilot4_rehearsal`: `Ran 3 tests in 10.268s OK` (dummy key, fake server, temp ledger; real `runs/spend` unchanged). Real HTTPS path and real model replies NOT rehearsed: UNVERIFIED |
| 13 | Check 1 to 5 tool (`lab.pilot_clearance`) | READY | Pilot 4 path today: exit 2 `Pilot 4 evidence unavailable or inconsistent: [Errno 2] No such file or directory: 'runs/ep1-live/pilot4/schedule.json'` (correct: no records). On Pilot 3 records it prints `failed`; criteria `1 pass, 2 fail, 3 pass, 4 pass, 5 pass, 6 unavailable, 7 unavailable`; order `shared`, "the only usable order" |
| 14 | Check 6 scripted bracket (floor/oracle) | READY | `ep1._bracket(...)`: `{"floor_Y": [0.25, 0.25, 0.25], "floor_fails": true, "oracle_Y": [1.0, 1.0, 1.0], "oracle_passes": true}` run today. The clearance script itself keeps `6_scripted_bracket: "unavailable"` (no machine-linked receipt) |
| 15 | Check 7: Console usage and USD for the batch against the ledger | BLOCKED: a human with Anthropic Console access (not named in the repo) | clearance prints `7_console_and_manual_review: "unavailable"` (`lab/pilot_clearance.py:189`) |
| 16 | Check 7: hand-read of all 30 episodes | BLOCKED: a reviewer (not named in the repo) | `PILOT4_RUN_PACKET.md` section 5; Pilot 3's reading record is absent (`unavailable_evidence.manual_episode_review`) |
| 17 | EP-1 sheet path (old ledger pin) | READY | `ep1 new sheet, no predecessor`: refused `price sheet changed mid-batch 'ep1' [no predecessor price sheet given]`; `ep1 new sheet + predecessor docs/reports/price-sheet.json`: passes `check_sheet`. `docs/reports/price-sheet.json` hashes to `16b204c2...`, the digest `canary.jsonl` pins for `ep1` |
| 18 | EP-1 freeze (`Status: FROZEN`, `code_tree_hash`) | BLOCKED: the preregistration author | `prereg/EP1.md:11` `Status: DRAFT`, `:18` `code_tree_hash:` blank; `ep1._check_freeze()` today: `refused: EP-1 code_tree_hash is missing, blank or invalid; freeze it first` |
| 19 | Pilot 4 clears checks 1 to 7 (including a usable order; Pilot 3 stays `shared` unless the author rules) | BLOCKED: Pilot 4 has not run | `PILOT4_RUN_PACKET.md` section 5 |
| 20 | B4 full-schedule and stop evidence, dry run of the 60-episode schedule | UNVERIFIED | not run here (the full `ep1 dry-run` exceeded its time box on 2026-11-26 per `PILOT4_RUN_PACKET.md` section 5) |
| 21 | Alejandro's second "confirm" before EP-1 | BLOCKED: Alejandro | `prereg/EP1.md` section 13, "The confirm step, twice" (before the canary and before EP-1; recorded in `docs/reports/ep-approvals.md`) |
| 22 | EP-1 caps and the shared USD 10 | READY | `spend.py:59` (5.0, 500, 1,250,000, canary inside); `HARD_CAP_USD = 10.0` at `spend.py:48`; recorded spend 0.0413027 |
| 23 | Host capacity | READY | `df -h .` 1.8T free; one writer; no other `ep1` process |

## 3. Unit-test result

Run 2026-11-27 (about 4.5 minutes, no key, no network): `Ran 258 tests in 272.213s`, `OK`, exit 0 (the command of `PILOT4_RUN_PACKET.md` section 1 item 6). `runs/spend/*.jsonl` checksums were identical after it.

## 4. Earliest possible time to run

- **Pilot 4:** now (2026-11-27T13:29Z), the moment the key holder puts the key in the shell and Alejandro confirms. Nothing else offline blocks it. It must start and finish inside
  2026-11-28T23:59:59Z (the agreed window; the sheet itself loads through 2026-11-29). Pilot 3's files span about four minutes on 2026-11-20 (`schedule.json` 14:40:09 to `final.json` 14:43:51
  -0500); Pilot 4 has the same size (240 planned calls), but its duration is UNVERIFIED.
- **EP-1:** no earlier than the completion of: Pilot 4 settled; checks 1 to 6 run; check 7 read by a human; the author's order record and freeze; B4 evidence; Alejandro's second confirm. No time can
  be computed for those people steps. EP-1 has 480 planned calls (about twice Pilot 4), duration UNVERIFIED. If EP-1 cannot start and end by 2026-11-28T23:59:59Z, ask the owner to extend the window
  (the sheet still loads until 2026-11-29), and if it would pass 2026-11-30T00:00Z the sheet must be refetched first.

## 5. Risks

1. **Criterion 2 may repeat.** Pilot 3's largest reply was 263 output tokens against the 150 limit (13 of 144 core calls over 150; `lab.pilot_clearance` on Pilot 3, `2_no_truncation` fail). The `array_only` wording is not shown to
   shorten replies (the replays hold archived replies fixed). Temperature is 1.0, so a new batch can differ. The cost of finding out is at most USD 0.25. A failed check leaves EP-1 blocked and cannot be re-run.
2. **One shot.** A stopped Pilot 4 (HTTP 400 on the first call is the pricing test, a third 401, a model mismatch, a malformed-reply rate, a scorer or Lean stop, a cap) cannot reopen; a new one needs a new owner ask. Earlier batches `pilot` and `pilot2`
   ended `stopped:void_model` (ledger stops), so the returned-model rule has fired before; `pilot3` completed. The sheet's `aliases` is empty, so only the exact id `claude-haiku-5-5` is accepted.
3. **Wrong flag or sheet.** Forgetting `--price-sheet` for Pilot 4, or `--predecessor-price-sheet` for EP-1, now exits 2 and writes nothing (commit `33343d2`; observed in the offline checks above), so it is recoverable; before that commit it burned the batch.
4. **EP-1 does not fit the window** (section 4 and row 6). A refetch is a network step and needs a named yes; the new sheet must have identical rates.
5. **`canary.jsonl` is appended** by the EP-1 continuity line (`spend.py:444-447`). Its checksum will change; that is expected, not tampering.
6. **Key handling.** A wrong key makes every call a 401 transport abort and the third stops the batch for good: use the `BAD KEY` guard and type the key once. Never put it in the repo, chat, STATUS or a log.
7. **Console reconciliation is a human step** and a mismatch stops the program. Unknown-cost calls count at their worst case in the total.
8. **EP-1 freeze is open work for the author;** the `code_tree_hash` covers `src`, `practices`, `tests` and Lean sources, so any later edit to those paths invalidates it (`ep1._check_freeze`). Do not edit them between the freeze and the run.
9. **Not verified here:** the real HTTPS path to `api.anthropic.com`, real model replies, that `claude-haiku-5-5` is served today (no network was used), the Console figures, the B4 evidence, any signed non-author wording review.
