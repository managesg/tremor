# Owner-run packet: Pilot 4, the seven checks, then EP-1 (copy-paste, in this order)

Prepared 2026-11-27 UTC, offline, TREMOR lane. Nothing here was run with a key. No network, no provider call, no paid call; paid spend for Pilot 4 and EP-1 is
USD 0.00; the recorded total of earlier batches (canary and pilots) is USD 0.0413027. This packet authorises nothing: every paid command needs Alejandro's `--i-have-owner-confirm` and a key that a named person
puts in the run shell. Paid ceilings (owner, inside the shared USD 10): Pilot 4 USD 0.25 / 260 calls / 598,000 tokens (`spend.py:69`);
EP-1 USD 5.00 / 500 calls / 1,250,000 tokens (`spend.py:59`). `HARD_CAP_USD` is 10.0 (`spend.py:48`), counted over every file in `runs/spend`.
Run from the repo root `/home/adelmar/SeaBridgeAI/murmuration`, in `bash`. The Pilot 4 details (stop rules, checks, STATUS line,
failure handling) stay in `PILOT4_RUN_PACKET.md`; this file is the order and the EP-1 half. State of every precondition today:
`PILOT4_EP1_READINESS_20261127.md`.

## 0. Who does what (only a person can do these)

| Step | Person | Why only a person |
|---|---|---|
| Put the key in the run shell | key holder (named person) or the owner | the key is never in a file, argument, chat or this repo |
| Say "confirm" before Pilot 4, and again before EP-1 | Alejandro | paid calls; Pilot 4 has its own owner ask (`ep-approvals.md`, addendum 10); `prereg/EP1.md` section 13 "the confirm step, twice" means before the canary and before EP-1, recorded in `ep-approvals.md` |
| Read the Anthropic Console for the Pilot 4 batch (check 7) | a human with Console access | the clearance script prints `7_console_and_manual_review: "unavailable"` on purpose |
| Hand-read all 30 Pilot 4 episodes against the scores (check 7) | a reviewer | `PILOT4_RUN_PACKET.md` section 5 |
| Freeze EP-1 (`Status: FROZEN`, `code_tree_hash`) and record the order result | the preregistration author | `ep1.py:115-140` refuses otherwise; `prereg/EP1.md:11,18` are `DRAFT` and blank today |
| Refetch the price sheet if it would be too old | the owner or PC (a network step) | see section 1 |
| Run the commands below | the owner or the key holder | the lane may not run them |

## 1. Time and price sheet (read first)

- Sheet in use: `runs/d8-price-refetch.20261126T0050Z/price-sheet.json` (copy `docs/reports/tremor/price-sheet-20261126.json`), sha256
  `2edb8b5ca979694eefe720d0fb3f0bf2a33cda73966b5c26f856392342a7a0f2`, fetched 2026-11-26.
- Rule: a sheet is refused when `today - fetched` is more than `MAX_AGE_DAYS = 3` days (`spend.py:46,166-169`). Fetched 2026-11-26, so
  it loads through 2026-11-29 (`expires_on()` prints 2026-11-29) and is refused from 2026-11-30 00:00 UTC. The age is read when the driver
  loads the sheet in `check_sheet` (`spend.py:516`) and once inside the first EP-1 reservation (the continuity step, `spend.py:504`). `reserve()` does not re-check it on every call, so a run already
  under way when 2026-11-30 00:00 UTC passes does not stop for age; still finish inside the agreed window.
- The agreed window ends 2026-11-28T23:59:59Z. Pilot 4 and EP-1 must both finish inside it unless the owner extends it. If EP-1 cannot start
  early enough, the sheet must be refetched (owner or PC, network, a named yes). A refetched sheet must have the same rates as `2edb8b5c...`
  (the code accepts a digest move only when every key except `fetched` is equal, `spend.py:491-511`) and the window must be re-checked with
  `lab.pilot4_price_window`. Do not edit a sheet by hand; do not change `MAX_AGE_DAYS`.
- Check at run time, immediately before each paid command (prints `"status": "price_sheet_valid_for_window"` and exit 0; on failure see the module):
  ```
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m lab.pilot4_price_window \
    runs/d8-price-refetch.20261126T0050Z/price-sheet.json \
    --price-sheet-sha256 2edb8b5ca979694eefe720d0fb3f0bf2a33cda73966b5c26f856392342a7a0f2 \
    --starts-at "$(date -u +%FT%TZ)" --ends-at 2026-11-28T23:59:59Z
  ```
  Run offline on 2026-11-27T13:23:38Z it printed `price_sheet_valid_for_window`, `valid_through_utc_date` 2026-11-29, `authorizes_execution` false.

## 2. The key (key holder, same shell as every paid command)

```
read -rs TREMOR_EP1_KEY; export TREMOR_EP1_KEY; case "$TREMOR_EP1_KEY" in sk-ant-?*) ;; *) echo BAD KEY; false;; esac
unset MURMURATION_EP1_KEY      # the legacy name is also read; if both are set and differ the run refuses (ep1.py:771-774)
```
Placeholder only: type the key at the silent prompt; never write it after the variable name, in a script or in this file. `BAD KEY` and a
non-zero status: `unset TREMOR_EP1_KEY` and start again. Each HTTP 401 is a transport abort and the third stops the batch for good.
After every paid command, and after any refusal: `unset TREMOR_EP1_KEY`. The driver reads the key only in `ep1.cli` (`ep1.py:771-776`).
Keep the shell open between Pilot 4 and EP-1 only if the key holder accepts that; otherwise re-run this block.

## 3. Order of operation

### Step A: offline preflight (no key; any miss, do not start)

1. `ls runs/spend` shows exactly `canary.jsonl pilot.jsonl pilot2.jsonl pilot3.jsonl` (any other regular file makes every batch refuse as ledger-corrupt).
2. `ls runs/spend/pilot4.jsonl runs/ep1-live/pilot4 runs/ep1-live/pilot4-stdout.txt` reports "No such file" three times.
3. `pgrep -af "tremor ep1"` prints nothing (one writer).
4. Tests, about 8 minutes, no key: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -W ignore -m unittest tests.test_spend tests.test_backend_claude tests.test_ep1 lab.tests.test_pilot4_preflight_manifest lab.tests.test_pilot4_price_window lab.tests.test_pilot4_rehearsal` (must end `OK`).
5. Section 1 window check prints `price_sheet_valid_for_window`.
6. Alejandro's "confirm" for Pilot 4, recorded verbatim in `docs/reports/ep-approvals.md` and in the lane STATUS.

### Step B: Pilot 4 (paid, once; the key block of section 2 first)

```
set -o pipefail
PYTHONPATH=src python3 -m tremor ep1 pilot4 \
  --out-dir runs/ep1-live/pilot4 --schedule-seed 0 --i-have-owner-confirm \
  --price-sheet runs/d8-price-refetch.20261126T0050Z/price-sheet.json 2>&1 \
  | tee runs/ep1-live/pilot4-stdout.txt
echo "exit=$?"; unset TREMOR_EP1_KEY
```
No `--predecessor-price-sheet` (pilot4 opens on its own lineage), no `--base-url`, no `--ledger-dir`, no `--review`.

| Outcome | What it prints | What it means |
|---|---|---|
| Success | one JSON object, `"kind": "pilot4"`, `"episodes": 30`, `"reason"`, `"ledger"` with `calls`, `usd`, `tokens`; exit 0 | the driver ended normally. Read `reason`: `complete`, `inconclusive` or `stopped:<why>` (a `stopped:*` is final) |
| Missing owner flag | `{"error": "refused: a paid run needs the explicit --i-have-owner-confirm flag"}`, exit 2 | observed offline 2026-11-27 (command run without the flag); nothing written |
| Missing key | `{"error": "refused: set TREMOR_EP1_KEY in the environment (legacy name MURMURATION_EP1_KEY also accepted; ...)"}`, exit 2 | from `ep1.py:776`; UNVERIFIED (running it needs the flag, which this lane never passes) |
| Sheet or flag problem before any reservation | stderr `price sheet refused: ...`; stdout `{"error": "refused: PriceSheetRefused: ..."}`; exit 2 | nothing written to `runs/spend`; the batch is still openable. Fix the flag or path, move `pilot4-stdout.txt` aside, run once more |
| Any other refusal after a reservation, HTTP 400, cap, model mismatch, malformed, scorer or Lean stop | JSON with `stopped:*`, or an error line | the batch is stopped, cannot reopen, cannot be re-run (`ep1.py:28`, `spend.py:596-603`) |

Offline check today of the same sheet logic (copy of `runs/spend`, nothing written; see the readiness file): `pilot4` on the new sheet passes;
`pilot4` on the default sheet is refused "fetched 2026-11-20 is 7 days old (limit 3)".

### Step C: read the result (no key, read-only)

```
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m lab.tremor_spend_total runs/spend --batch pilot4
sha256sum runs/ep1-live/pilot4/{schedule.json,episodes.jsonl,final.json} runs/spend/pilot4.jsonl
```
`tremor_spend_total` prints one line per Pilot 4 call, then `total_usd=... cap_total=10.0 batch_usd=... cap_batch=0.25`, and exits 1 with
`OVER CAP: STOP` if either is exceeded. Unknown cost counts at its worst case (a reservation with no charge). A complete batch ledger has
about 482 lines (1 open, 240 reserves, 240 charges, 1 stop; rehearsal figure). Expected prospective schedule digest (from the manifest, not a file hash):
`ba4f68ad0128073f8d338c16afd5adbdbbb68b06bfa249afe08e2bfc56cc5365` (30 episodes, 240 call ids, prefix `p4`).

### Step D: checks 1 to 6 (no key) and check 7 (human)

```
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m lab.pilot_clearance runs/ep1-live/pilot4 runs/spend/pilot4.jsonl --batch pilot4
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m tremor ep1 analyse runs/ep1-live/pilot4
B=$(mktemp -d) && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -W ignore -c "
from tremor import ep1; import json, sys
print(json.dumps(ep1._bracket(sys.argv[1], 0, ep1.REVIEW_FILE, None), sort_keys=True))" "$B"
```
- `pilot_clearance` prints JSON with `batch`, `clearance`, `criteria`, `criterion_scope`, `local_ledger`, `order_rule`, `readouts`, `source_sha256`,
  `unavailable_evidence`. Checks 1 to 5 are `pass` or `fail` in `criteria`; `clearance` is `failed` unless all are met. Today, with no Pilot 4
  records, it exits 2 and prints `Pilot 4 evidence unavailable or inconsistent: [Errno 2] No such file or directory: 'runs/ep1-live/pilot4/schedule.json'`
  (observed offline); it also refuses (exit 2) on a dry-run schedule, a partial batch or a ledger that does not reconcile.
- Its `6_scripted_bracket` is always `unavailable` (no machine-linked receipt, `PILOT4_RUN_PACKET.md` section 9). Check 6 is the third command: pass is
  `"floor_fails": true`, `"oracle_passes": true`, `floor_Y` `[0.25, 0.25, 0.25]`, `oracle_Y` `[1.0, 1.0, 1.0]`. Observed offline 2026-11-27: exactly that.
- Check 7 stays `unavailable` in the script. A human reads the Anthropic Console usage and USD for this batch and compares it with the
  `tremor_spend_total` lines (calls, input tokens, output tokens, USD), and a reviewer hand-reads all 30 episodes (prompts, replies, logs) against the
  scores. Do not mark check 7 passed on the script, or on the substitution alone.
- Pass rules and the order rule are in `PILOT4_RUN_PACKET.md` section 5. A `stopped:*` batch, a failed check or a missing check 7 leaves EP-1 blocked.

### Step E: author freeze (preregistration author; no spend)

Only after Step D passes checks 1 to 7 and the author records the order result (Pilot 4 never replaces Pilot 3's `shared` selection, D8-d): the author
sets `prereg/EP1.md` to `Status: FROZEN`, fills `code_tree_hash:` (64 lowercase hex over `src`, `practices`, `tests` and the Lean sources/manifests, `ep1.py:131-139`),
and records the approved digests. Check, no key: `PYTHONPATH=src python3 -m tremor prereg-check prereg/EP1.md --tree src practices tests ...` (the exact `--tree` list is the author's; `_check_freeze` is the
authority). Then the B4 full-schedule and stop evidence, and Alejandro's second "confirm" (`prereg/EP1.md` section 13). Until then `ep1 run` refuses:
observed offline: `PreflightError refused: EP-1 code_tree_hash is missing, blank or invalid; freeze it first`.

### Step F: EP-1 (paid, once; only after A to E; key block of section 2 again)

Repeat the section 1 window check. Clean slate (read-only; each must report "No such file"):
```
ls runs/spend/ep1.jsonl runs/ep1-live/ep1 runs/ep1-live/ep1-stdout.txt
```
Then:
```
set -o pipefail
PYTHONPATH=src python3 -m tremor ep1 run \
  --out-dir runs/ep1-live/ep1 --schedule-seed 0 --i-have-owner-confirm \
  --price-sheet runs/d8-price-refetch.20261126T0050Z/price-sheet.json \
  --predecessor-price-sheet docs/reports/price-sheet.json 2>&1 \
  | tee runs/ep1-live/ep1-stdout.txt
echo "exit=$?"; unset TREMOR_EP1_KEY
```
`--predecessor-price-sheet` is required for `run`: the `ep1` batch was opened by the canary on the OLD sheet (`runs/spend/canary.jsonl` pins
`16b204c2...`, which `docs/reports/price-sheet.json` hashes to; checked), and without the flag the run is refused "price sheet changed mid-batch 'ep1'
[no predecessor price sheet given]". The code accepts the move only because the two sheets differ only in `fetched`. Run the flag in this exact form.
Expected effects: the driver writes one `sheet_continuity` line into `runs/spend/canary.jsonl` (the file that holds `ep1`'s `batch_open`,
`spend.py:444-447`), so `canary.jsonl` changes by one appended line; EP-1's own ledger is `runs/spend/ep1.jsonl`; outputs in `runs/ep1-live/ep1`
(`schedule.json`, `episodes.jsonl`, `events.jsonl`, `final.json`). Design: 3 arms x 20 held-out sets = 60 episodes = 480 calls; cap 500 calls (19 spare after the canary),
USD 5.00, 1,250,000 tokens with the canary counted inside (canary used: 1 call, 46,609 tokens, USD 0.0046625). Output on success, refusals and stops is the
same shape as Step B (one JSON object, exit 0, read `reason`; exit 2 for a pre-reservation refusal that writes nothing). Frozen refusal text: see Step E.
Rehearsal of this exact CLI path with `--predecessor-price-sheet` exists only as tests (`lab.tests.test_ep1_continuity_cli`, per `DECISION_LOG.md`); a paid-path
run end to end is UNVERIFIED. `ep1 analyse runs/ep1-live/ep1` reads it afterwards. The cap is never raised after the freeze (`prereg/EP1.md:642-643`).

## 4. Where the money and the record live

| Item | Location |
|---|---|
| Ledgers (append-only JSONL, one line per reserve and per charge) | `runs/spend/{canary,pilot,pilot2,pilot3}.jsonl` today; `pilot4.jsonl` after Step B; `ep1.jsonl` after Step F |
| Lock file | `runs/spend/.spend.lock` (not a ledger) |
| Output folders | `runs/ep1-live/pilot4`, `runs/ep1-live/ep1`; stdout copies `runs/ep1-live/pilot4-stdout.txt`, `runs/ep1-live/ep1-stdout.txt` |
| Shared total | `PYTHONPATH=src python3 -m lab.tremor_spend_total runs/spend` (offline today: `total_usd=0.0413027 cap_total=10.0`) |
| Caps in code (never from an argument) | `spend.py:48` (10.0), `:52` (per-call 2,000 in / 300 out), `:57-72` (batches) |

How to read a settlement: `final.json` `reason` (`complete`, `inconclusive`, `stopped:<why>`), `detail`, and the `ledger` block (`calls`, `usd`, `tokens`,
`remaining`, `stop_reason`). The ledger's last line is the `batch_stop` line; its `reason` is the settlement. Only `complete` or `inconclusive` settle a batch; any
`stopped:*` blocks it and its children (`spend.py:585-603`). Reconcile: ledger USD against the Console for the same call count and tokens; a mismatch stops the
program (`prereg/EP1.md` section 13, canary paragraph).

## 5. How to stop, and rollback

- The driver stops itself on every rule in `PILOT4_RUN_PACKET.md` section 3 and `ep1.py:8-24`; the operator never overrides. To stop by hand press Ctrl-C only if the
  running total visibly exceeds the batch cap (it cannot by design). A kill writes no `batch_stop`; the in-flight call stays reserved at its worst case, a crashed
  attempt is logged `interrupted` in `events.jsonl`, and the batch is neither settled nor stopped. Do not restart blindly: report first; resuming needs the owner's say.
  A CLI for an owner stop does not exist in the code read here (`STOP_WHY` has `owner`, `spend.py:55`, reachable only through the API); UNVERIFIED beyond that.
- **A stopped batch cannot reopen.** `_check_open` refuses a batch with any recorded stop (`ep1.py:201-205`); every later reserve in its lineage is refused. A new Pilot 4 or
  a second EP-1 needs a new owner ask and new code review; no flag, edit or retry reopens it.
- **Money cannot be returned.** Bounds, not promises: Pilot 4 at most USD 0.25 (worst-case reservation 260 x 0.00055 = USD 0.143); EP-1 at most USD 5.00.
- **Data rollback:** none. Never delete or edit `runs/spend/*`, `runs/ep1-live/*` (Safety rule 1). A failed or `stopped` Pilot 4 leaves the EP-1 freeze blocked and
  `shared` from Pilot 3 in force. Code rollback is an approved `git revert` of the lane's own commit; no push is involved.
- After any refusal or stop: `unset TREMOR_EP1_KEY`, record `final.json`, the ledger path and the section 4 totals in STATUS, stop.
