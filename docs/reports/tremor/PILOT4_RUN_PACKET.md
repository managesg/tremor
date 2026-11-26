# Pilot 4 run packet (copy-paste; no decisions left)

Prepared 2026-11-26 UTC, offline. Nothing here was run with a real key. One Pilot 4 batch only: 30 episodes, 240 planned calls,
Haiku 5.5 (`claude-haiku-5-5`), temperature 1.0, thinking disabled, no prefill, round-2 wording `array_only` (D8-b).
Run everything from the repo root `/home/adelmar/SeaBridgeAI/murmuration`.

## 1. Preconditions (all must hold; any miss: do not start)

1. **Key.** `MURMURATION_EP1_KEY` is set in this one shell session only, typed at a silent prompt (never inline before the command, so it
   never reaches shell history or `ps`; never in a file or argument; never echoed). Each HTTP 401 from a wrong key is a transport abort and
   the third stops the batch for good, so the guard below rejects an obviously wrong key before launch:
   ```
   read -rs MURMURATION_EP1_KEY; export MURMURATION_EP1_KEY; case "$MURMURATION_EP1_KEY" in sk-ant-?*) ;; *) echo BAD KEY; false;; esac
   ```
   (`BAD KEY` and a non-zero status: stop, `unset MURMURATION_EP1_KEY`, start over.) After the run, and also after any refusal:
   `unset MURMURATION_EP1_KEY`. The driver reads it in `ep1.cli` only.
2. **Spend limits.** Owner USD 10 total cap (shared; `HARD_CAP_USD`, `spend.py:46`). The driver and `lab/tremor_spend_total.py` count only the ledgers in `runs/spend`; any other spend on this key or account must be added by hand before launch. Pilot 4 cap USD 0.25, 260 calls, 598,000
   tokens, one batch (`spend.py:69`). Prior recorded spend USD 0.0413027, so after a full batch the total stays near USD 0.19 at
   worst-case reservation (260 x 0.00055 = 0.143).
3. **Price sheet.** `runs/d8-price-refetch.20261126T0050Z/price-sheet.json`, sha256
   `2edb8b5ca979694eefe720d0fb3f0bf2a33cda73966b5c26f856392342a7a0f2`, fetched 2026-11-26, valid through 2026-11-29. It must be
   passed with `--price-sheet`: the driver's default sheet (`docs/reports/price-sheet.json`, fetched 2026-11-20) is refused as
   6 days old (checked 2026-11-26: `PriceSheetRefused ... 6 days old (limit 3)`), so without the flag the command refuses. The flag is
   labelled "test hook" in `--help`; here it is the supported route because Pilot 4 opens on its own ledger lineage with the new
   sheet (`DECISION_LOG.md`, "D8 price sheet refetched"). `--predecessor-price-sheet` is NOT used: it exists for `ep1 run` only
   (the `ep1` batch pins the old sheet). Rehearsal below confirms `pilot4` opens on the copied real canary ledger with the new sheet.
4. **Window check, immediately before launch**, with the checked window and today's real instants (start = now, end = the end of
   the planned run, not later than 2026-11-28T23:59:59Z):
   ```
   PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m lab.pilot4_price_window \
     runs/d8-price-refetch.20261126T0050Z/price-sheet.json \
     --price-sheet-sha256 2edb8b5ca979694eefe720d0fb3f0bf2a33cda73966b5c26f856392342a7a0f2 \
     --starts-at "$(date -u +%FT%TZ)" --ends-at "<run end, UTC, e.g. 2026-11-26T23:59:59Z>"
   ```
   Must print `"status": "price_sheet_valid_for_window"`. The previously checked window is 2026-11-26T01:00:00Z to
   2026-11-28T23:59:59Z. The agreed window ends 2026-11-28T23:59:59Z. The sheet's age is checked only when the driver loads it at start (`spend.py` `_check_age`, `PriceSheet.load`), and the sheet is accepted through 2026-11-29 (`valid_through_utc_date`); a later start is refused. Finish inside the agreed window anyway.
5. **Clean slate.** None of these may exist: `runs/spend/pilot4.jsonl`, `runs/ep1-live/pilot4`. `runs/spend/canary.jsonl` must end with
   `batch_stop` reason `complete` (it does; Pilot 4 requires the settled canary).
   `ls runs/spend/pilot4.jsonl runs/ep1-live/pilot4` must report "No such file" twice.
6. **Offline tests green** (about 8 minutes, no key, no network):
   ```
   PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -W ignore -m unittest tests.test_spend tests.test_backend_claude tests.test_ep1 \
     lab.tests.test_pilot4_preflight_manifest lab.tests.test_pilot4_price_window lab.tests.test_pilot4_rehearsal
   ```
7. **Owner release.** Alejandro's named release for paid execution (the overnight hold is lifted for this batch) is recorded in
   `DECISION_LOG.md`. The `--i-have-owner-confirm` flag below is his confirm; do not add it on anyone else's behalf.
8. **Lean scorer available.** The real (unstubbed) `ep1._bracket` call in section 5 ran on this host on 2026-11-26; an `INVALID` Lean
   probe would stop the batch before the first call at no cost, but run the check 6 command first as a free smoke test.
9. **Host.** One writer, no other `ep1` process running (`pgrep -af "murmuration ep1"` shows nothing). Network is the only paid
   route used: HTTPS to `api.anthropic.com` from the client; nothing else.

## 2. The command (paid; run once)

```
set -o pipefail
PYTHONPATH=src python3 -m murmuration ep1 pilot4 \
  --out-dir runs/ep1-live/pilot4 --schedule-seed 0 --i-have-owner-confirm \
  --price-sheet runs/d8-price-refetch.20261126T0050Z/price-sheet.json 2>&1 \
  | tee runs/ep1-live/pilot4-stdout.txt
echo "exit=$?"; unset MURMURATION_EP1_KEY
```
(The key is already exported from item 1 of section 1; nothing key-bearing is on this command line. `pipefail` makes the exit code the
driver's, not `tee`'s. `runs/ep1-live/pilot4-stdout.txt` must not exist before launch.)

Derived from Pilot 3's shape (`ep1 pilot3 --out-dir runs/ep1-live/pilot3 --schedule-seed 0 --i-have-owner-confirm`) plus the
`--price-sheet` flag. Do not pass `--base-url`, `--ledger-dir` (loopback test hooks; each refuses without the other), `--review` (the
default `docs/reports/card-A-review.md` is used) or `--predecessor-price-sheet`. Ledger lands in `runs/spend/pilot4.jsonl`; output in
`runs/ep1-live/pilot4` (`schedule.json`, `episodes.jsonl`, `events.jsonl`, `final.json`, `pilot_trace.txt`). Expected schedule digest
`ba4f68ad0128073f8d338c16afd5adbdbbb68b06bfa249afe08e2bfc56cc5365` (30 episode ids prefix `p4`, 240 call ids). The command prints one
JSON object (`final`) when it ends; exit 0 means the driver ended normally (`reason` may still be `stopped:<why>` or `inconclusive`: read it).

**Exit 2 is not a stop (added after the 2026-11-26 review, commit of the pre-reservation sheet check).** Exit 2 with `price sheet refused:` on stderr and `{"error": ...}` on stdout means a sheet or flag problem was caught BEFORE any reservation: nothing was written to `runs/spend` and the batch is still openable. Fix the flag or the sheet path, move `runs/ep1-live/pilot4-stdout.txt` aside (it must not exist at launch), and run once more. An exit 0 with `stopped:*`, or any HTTP 400, is final.

## 3. Stop rules (the driver enforces them; the operator never overrides)

- **HTTP 400 on the first call (or any call): the batch stops at once, is never re-run.** This is the request-shape failure; record it,
  do not retry, do not start a second Pilot 4 (a new attempt needs a new owner ask).
- **Any over-cap:** batch USD 0.25, 260 calls, 598,000 tokens, per-call 2,000 input / 300 output tokens, the USD 10 total. A cap
  hit settles `stopped:cap`; usage above the per-call cap voids.
- Also stops: third transport abort, returned-model mismatch, any cache-creation token, scorer disagreement, `invalid_log`, Lean
  `INVALID`, malformed replies above 10 in the first 40-call block / 10% overall / 15% in one condition, overspent ledger, unexplained
  unbilled unknown (`ep1.py:8-24`).
- A stopped or settled batch refuses to run again. Operator rules on top: do not re-run the command, do not delete or edit
  `runs/spend/pilot4.jsonl` or `runs/ep1-live/pilot4`, do not run it a second time to "see". Press Ctrl-C only if the running total
  visibly exceeds USD 0.25 (it cannot by design); the ledger holds worst-case reservations for any in-flight call.

## 4. Log after the run (read-only; paste the output into STATUS)

Per-call cost, running Pilot 4 total and the shared total over ALL ledgers in `runs/spend` (read-only; owner rule: unknown cost counts at its
upper estimate, so the total is every charge line plus the reservation worst case of every reserved call with no charge, i.e. failed or
`unbilled_unknown` calls; a charge with null usage is read as no usage and its charged worst case is kept):
```
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m lab.tremor_spend_total runs/spend --batch pilot4
```
It prints one line per Pilot 4 call (id, input tokens, output tokens, stop reason, USD, running USD, `charged` / `charged(no usage: worst case)` /
`UNCHARGED(worst case)`), then `total_usd=... cap_total=10.0 batch_usd=... cap_batch=0.25`, and exits 1 with `OVER CAP: STOP` if either cap is
exceeded. Run it again before any further paid action. Tested in `lab/tests/test_tremor_spend_total.py`. Also record: the `final.json` `reason` and `detail`, the ledger path `runs/spend/pilot4.jsonl` (480-ish lines for a complete batch: 1 open,
a reserve and a charge per call, 1 stop), `sha256sum runs/ep1-live/pilot4/{schedule.json,episodes.jsonl,final.json} runs/spend/pilot4.jsonl`,
and the per-call usage lines above (they are the input for check 7's usage comparison). The `usd` and `id` fields come from the
ledger's `charge` lines; response ids (`msg_...`) are in the episode records' turns.

## 5. Checks 1 to 6 (offline, no key)

Checks 1 to 5 in one command; read `criteria`, `readouts` and `order_rule`:
```
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m lab.pilot_clearance runs/ep1-live/pilot4 runs/spend/pilot4.jsonl --batch pilot4
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m murmuration ep1 analyse runs/ep1-live/pilot4
```
It refuses (exit 2, "evidence unavailable or inconsistent") unless the batch is `complete`, all 30 episodes and 240 calls are present, the
schedule is non-dry, and the ledger reconciles to the records. A refusal means the batch is not clearable: go to section 8.

| # | Check | Where to read it | Pass rule |
|---|---|---|---|
| 1 | Request shape | `criteria."1_request_shape"`; `readouts.all_conditions.http_400_in_trace`, `non_text_replies` | both 0 |
| 2 | Output length | `criteria."2_no_truncation"`; `readouts.core.max_output_tokens`, `over_150`, `stop_max_tokens` | `stop_max_tokens` 0 over the batch; core (144 calls) max output <= 150 |
| 3 | Reply format | `criteria."3_reply_format"`; `readouts.core.malformed`, `per_condition.<none,play,code>.malformed` | core malformed <= 7 of 144; each core condition <= 4 of 48 |
| 4 | Arithmetic | `criteria."4_arithmetic"`; `readouts.core.wrong_admitted_work` | <= 3 of up to 72 admitted |
| 5 | Usable order | `criteria."5_usable_order"`; `order_rule.orders.{shared,per_agent}` (`mean_Y_none` in [0.30, 0.80], `duplicates.none` >= 2, `duplicates.code` 0, a set with different `Y_code`/`Y_none`), `order_rule.picked` | `picked` non-null and `code` duplicates 0; Pilot 4 never replaces Pilot 3's `shared` selection (D8-d); a different or no order goes back to the author |

Scope note (D8-c, ruled; do not reopen): `pilot_clearance` check 2 is zero `max_tokens` stops over the whole batch and a maximum of 150 output
tokens over the three core conditions (144 calls), per `prereg/EP1.md` 13.16b and D8-c. The whole-batch `over_150`, the per-condition maxima and
every overage are printed as well; report them. Pilot 3 failed this check at 263 vs 150 (13 of 144 core calls over 150).

**Check 6, scripted bracket** (no key, loopback fake server, about 4 seconds):
```
B=$(mktemp -d) && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -W ignore -c "
from murmuration import ep1; import json, sys
print(json.dumps(ep1._bracket(sys.argv[1], 0, ep1.REVIEW_FILE, None), sort_keys=True))" "$B"

```
Pass: `"floor_fails": true` and `"oracle_passes": true` with `floor_Y` `[0.25, 0.25, 0.25]` and `oracle_Y` `[1.0, 1.0, 1.0]` (floor exactly 0.25,
oracle exactly 1.0 in each of the three arms). The same bracket runs inside `python3 -m murmuration ep1 dry-run --out-dir <dir>`
(`bracket` key, verdict GREEN), but that full dry run was not completed here (the 60-episode `ep1` stage exceeded the time box), so the direct
call is the supported shortcut. See section 9 for the open point on `lab.ep1_bracket_receipt`.

**Check 7, reconciliation and review: PENDING, needs a human.** Not passed by any script, and the clearance script prints
`"7_console_and_manual_review": "unavailable"`. A human must (a) read the Anthropic Console usage and cost for this batch and compare
it with the ledger totals from section 4 (calls, input and output tokens, USD); (b) the recorded D8 substitution is already agreed (ledger
charges vs each response's `usage` and `msg_` ids, plus an independent hand-read of all 30 episodes' prompts, replies and logs against the
scores), but check 7 stays PENDING until a human has read the Console. Do not mark it passed on the substitution alone.

## 6. STATUS template (one line, append to the lane STATUS)

```
PILOT4 <UTC time> reason=<complete|inconclusive|stopped:why> episodes=<n>/30 calls=<n>/260 pilot4_usd=<x> total_usd=<x>/10.0 ledger=runs/spend/pilot4.jsonl out=runs/ep1-live/pilot4 sha(final.json)=<64hex> c1=<pass|fail> c2=<pass|fail max_out=n core_over150=n> c3=<..> c4=<..> c5=<..picked=..> c6=<pass|fail> c7=PENDING(Console read: human) sheet=2edb8b5c next=<EP-1 stays blocked | author freeze review>
```

## 7. Order of operation (checklist)

1. Section 1 items 1 to 9. 2. Section 2 command, once. 3. Section 4 log, paste into STATUS. 4. Section 5 checks 1 to 6, paste
`criteria` and the order result. 5. Hand check 7 to the Console reader. 6. Re-run the section 1 item 6 tests to confirm nothing changed.
7. STATUS line. A pass on 1 to 6 does not clear EP-1: check 7 and the author's freeze are still required.

## 8. If it fails

- **Refusal before any call** (missing flag/key, expired or wrong-digest sheet, existing `pilot4` ledger, canary not settled): nothing was
  spent. Fix the named cause only (never raise a cap, never edit a ledger or the sheet) and re-check section 1. If the sheet window
  lapsed, a new refetch needs a fresh owner yes and a new continuity review.
- **Batch stopped** (`reason` `stopped:*`, any HTTP 400, cap, model mismatch, malformed or scorer stop): the batch is not settled as
  complete and cannot be retried. Record `final.json`, the ledger path and totals (section 4), write STATUS, stop. EP-1 freeze stays
  blocked, Pilot 3's `shared` selection stays, nothing else changes. A new Pilot 4 needs a new owner ask.
- **`complete` but a check fails** (for example check 2 repeats Pilot 3's overage): do not re-run; report the numbers and both scopes;
  EP-1 freeze stays blocked.
- **Crash or kill mid-run:** do not restart blindly. Ids are idempotent and a crashed attempt is logged as interrupted; resuming is
  the driver's job but needs the owner's say, so report first.
- Never delete runs, ledgers or outputs (Safety rule 1). Money spent is not returned.

## 9. Open points (read before launch)

- `lab/ep1_bracket_receipt.py` audits historical pinned fake receipts and requires a `complete` terminal record; a fresh one-set bracket ends
  `inconclusive` and is refused ("bracket must have a complete, zero-void fake terminal record"). So check 6 has no machine-linked receipt for
  Pilot 4 (its output field `pilot4_clearance` is `None`); the direct `_bracket` result above is the evidence, and `_bracket` is a private
  function.
- `pilot_clearance` check 2 now follows D8-c (core 150-token maximum, whole-batch zero `max_tokens`); the Pilot 3 verdict is unchanged (core max 263, 13 of 144 over).
- The first paid call is the pricing test (D8-e: no second canary). An HTTP 400 there stops the batch.

## 10. Throwaway-live rehearsal on a loopback fake server, not evidence for any check

What ran: `lab/tests/test_pilot4_rehearsal.py` (dummy key `sk-ant-DUMMY-loopback-rehearsal-0000`, fake server from `tests/fakeclaude.py`
on 127.0.0.1, ledger dir and outputs in a Python `tempfile` directory removed by the script, `spend.PILOT_LEDGER_DIR` patched, Lean
scorer stubbed as `tests/test_ep1.py` does, new price sheet `2edb8b5c...`). Same argv as section 2 plus the two loopback hooks
`--base-url`, `--ledger-dir` (and `--review` to a throwaway review file). Real `runs/spend` was verified unchanged (directory
listing hash identical before and after). Run it: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests python3 -W ignore -m lab.tests.test_pilot4_rehearsal [real]`
(`real` copies the real `runs/spend/*.jsonl` read-only into the throwaway directory so only `pilot4` runs, on the real canary lineage).
Its unittest form passes (3 tests).

Output of `ep1 canary` then `ep1 pilot4` (trimmed; fake server returns worst-case usage 90,000 / 1,364 input and 300 output tokens, so
its dollar figures are meaningless):
```
## ep1 canary rc=0   (reason complete, ledger_usd 0.00915, stamp "FAKE: loopback fake server; not evidence about any model")
## ep1 pilot4 rc=0
 "episodes": 30, "kind": "pilot4", "reason": "complete", "aborts": 0, "detail": null,
 "ledger": {"batch": "pilot4", "calls": 240, "caps": {"calls": 260, "parent": null, "requires_settled": "canary",
   "settled_reasons": ["complete"], "tokens": 598000, "usd": 0.25},
   "price_sheet_sha256": "2edb8b5ca979694eefe720d0fb3f0bf2a33cda73966b5c26f856392342a7a0f2",
   "remaining": {"calls": 20, "tokens": 179290, "usd": 0.179329}, "stop_reason": "complete", "tokens": 418710,
   "tokens_by_class": {"cache_creation": 0, "cache_read": 0, "input": 346710, "output": 72000, "unmetered_worst": 0},
   "usd": 0.070671},
 "stamp": "FAKE: loopback fake server; not evidence about any model",
 "voids": {"code": 0, "keyword_stuffed": 0, "none": 0, "play": 0, "states_check": 0}
requests_seen 241          (1 canary + 240 pilot4)
ledger lines 482           (first batch_open, last batch_stop complete)
```
`real` mode (real canary and older ledgers copied, only pilot4 run, new sheet): `ep1 pilot4 rc=0`, `requests_seen 240`, 482 ledger lines,
same final summary. So `pilot4` opens on the real canary lineage with the refetched sheet.

Section 4 command on the throwaway ledger directory (`real` mode: real ledgers copied, `pilot4.jsonl` skipped in the copy; first 3 and last 3 call lines):
```
pilot4.jsonl usd=0.0706710
   ep1p4kw-play-t0-s0:r0:a0 1364 300 end_turn 0.0002864 0.0002864 charged
   ep1p4kw-play-t0-s0:r0:a1 1364 300 end_turn 0.0002864 0.0005728 charged
   ep1p4kw-play-t0-s0:r0:a2 1364 300 end_turn 0.0002864 0.0008592 charged
...
   ep1p4pa-code-t5-s5:r1:a1 1522 300 end_turn 0.0003022 0.0700620 charged
   ep1p4pa-code-t5-s5:r1:a2 1545 300 end_turn 0.0003045 0.0703665 charged
   ep1p4pa-code-t5-s5:r1:a3 1545 300 end_turn 0.0003045 0.0706710 charged
total_usd=0.1119737 cap_total=10.0 batch=pilot4 batch_usd=0.0706710 cap_batch=0.25 (this directory only; add any other spend by hand)
```
(The 0.0413027 prior spend equals the real recorded `runs/spend` total; `python3 -m lab.tremor_spend_total runs/spend` on the real directory prints
`total_usd=0.0413027`. Its test covers a null-usage charge, an uncharged reservation and an `unbilled_unknown` reservation, and equals
`spend.Ledger._sum`; a mutated copy that drops uncharged reservations fails it.)

`pilot_clearance runs... --batch pilot4` on the loopback output, as run:
```
Pilot 4 evidence unavailable or inconsistent: saved schedule differs from the Pilot 4 design      (exit 2)
```
It refuses because the loopback schedule says `"dry_run": true` and the script requires `false`; this is the intended guard, so a fake run can
never produce a clearance. To show the output shape only, the same throwaway output with `schedule.json` `dry_run` flipped to `false` in
the temporary copy (not a valid run; the fake server's constant 300-token answers fail checks 2 and 5):
```
"batch": "pilot4", "clearance": "failed",
"criteria": {"1_request_shape": "pass", "2_no_truncation": "fail", "3_reply_format": "pass", "4_arithmetic": "pass",
             "5_usable_order": "fail", "6_scripted_bracket": "unavailable", "7_console_and_manual_review": "unavailable"},
"local_ledger": {"calls": 240, "charges": 240, "reservations": 240, "tokens": 418710, "transport_aborts": 0,
                 "usd": "0.0706710", "voided_episodes": 0},
"order_rule": {"label": "design decision, not a confirmatory result", "picked": null,
               "why": "no usable order: criterion 5 fails, EP-1 not cleared",
               "orders": {"shared": {"sets": [0, 3, 4], "mean_Y_none": 0.25, "duplicates": {"code": 0, "none": 9}, "usable": false},
                          "per_agent": {"sets": [1, 2, 5], "mean_Y_none": 0.25, "duplicates": {"code": 0, "none": 9}, "usable": false}}},
"readouts": {"all_conditions": {"calls": 240, "episodes": 30, "http_400_in_trace": 0, "non_text_replies": 0, "malformed": 0,
             "stop_max_tokens": 0, "over_150": 240, "max_output_tokens": 300, "admitted_work": 102, "wrong_admitted_work": 0}, "...": "..."}
```
Check 6 on the loopback fake (`ep1._bracket`, 3.4 s): `{"expected": {"floor": 0.25, "oracle": 1.0}, "floor_Y": [0.25, 0.25, 0.25],
"floor_fails": true, "oracle_Y": [1.0, 1.0, 1.0], "oracle_passes": true}`.

Not rehearsed: the real HTTPS client path to `api.anthropic.com` (the client refuses any other non-loopback host), real model replies, and real
Lean scoring (stubbed, as in the repo's own tests). Everything else in the command path ran.
