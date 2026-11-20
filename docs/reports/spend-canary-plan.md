# Spend canary plan (before any paid batch)

Status: plan only. Nothing here was run with a key. The owner supplies the key and the Console access; builders and
verifiers never read or hold one. Follows `spend-verification.md` section (8).

## Guards now in the code (D1 to D9)

- `spend.HARD_CAP_USD = 10.0` is a constant. All `*.jsonl` ledgers in ONE directory count toward it, so a new ledger
  path in that directory never resets the total. `ceiling` is per ledger file, must be in (0, 10.0], default 9.00.
  Keep every pilot and canary ledger in one directory (the cap is per directory, not per machine).
- `reserve` and `charge` run under `flock` on `<dir>/.spend.lock`; a lock timeout fails closed.
- NaN, inf, negative, non-integer or missing usage and prices raise `SpendError`; a corrupt ledger line stops the run.
- After each call, actual cost above the reserved worst case, or an invalid usage block, writes the cost and an
  `overspent` marker; every later `reserve` in the directory then raises `Overspent`.
- Only `https://api.anthropic.com` is accepted by default. A key is never sent anywhere else except an explicit
  loopback `allow_host` (tests). Redirects are not followed.
- A returned model that differs from the requested one is priced at the dearer of the two (worst case if unknown).
- The key and its 10-character ends are scrubbed from everything persisted or returned.
- The run record's `usd` is the ledger spend for the episode, retried attempts included.
- Price sheet staleness: 3 days (`PriceSheet.expires_on()`); an older sheet is refused. The canary's first reserve pins
  the sheet sha256 for both `canary` and `ep1`, so a changed sheet is refused mid-batch. See the price-sheet rule below.
- A batch is settled only when no stop is recorded anywhere in its subtree or the batch it depends on: a stopped
  canary refuses the pilot and any settle of `ep1`, so `ar1` never opens after a stop.

## Step 0: dry run (no key, no network)

`tests/fakeclaude.dry_run(task, arm, seed, ledger, price_sheet)` runs the full claude path against the loopback fake
server. In `dry_run` mode the runner refuses a non-loopback `base_url` and replaces any supplied key with a dummy.
Check the ledger: one `reserve` then one `charge` per call, run `usd` equals the directory total.

## Step 1: Console limit

Owner sets a Console workspace spend limit of USD 10 or less. The ledger is an estimate; the Console is the backstop.

## Price-sheet rule (G0-2R2 section 4; binding for canary, pilot and EP-1)

- Refetch `docs/reports/price-sheet.json` on canary day. Re-verify every row against the source URL, set `fetched` to
  that UTC date and record the new sha256.
- Leave the sheet byte-unchanged until EP-1 settles. The canary, the pilot, the pilot hand-check, EP-1 and every resume
  must all finish by `fetched` + 3 days (UTC) on that unchanged sheet. Otherwise EP-1 is stranded: a refetch is refused
  mid-batch and the old sheet is too old.
- Never pass `--price-sheet` (nor `--ledger-dir` or `--base-url`) on a paid command; they are test hooks.
- One process at a time, ever: no second driver on the same ledger or output directory (a second one strands the batch).

## Step 2: canary through the CLI (Haiku, one padded call)

The only canary path is `ep1 canary`: one `claude-haiku-5-5` call with a 90,000-byte padded request, `max_tokens` 300,
batch `canary` (cap USD 0.05, 1 call, 90,300 tokens) in the pinned ledger directory `runs/spend`. The key is read from
`MURMURATION_EP1_KEY` in the owner's environment only, never from a file or an argument.

```sh
MURMURATION_EP1_KEY=... PYTHONPATH=src python3 -m murmuration ep1 canary --out-dir <out>/canary --i-have-owner-confirm
```

- Pass: `<out>/canary/canary.json` has `ok: true` and `reason: complete`; the batch settled `complete`.
- Any other reason (`stopped:<why>`) leaves the canary stopped: the pilot and EP-1 stay refused, EP-1 can never settle
  and ar1 never opens. Do not settle anything by hand.
- Compare: the Console cost and tokens for that one request must equal `ledger_usd` and `usage` in `canary.json` (to
  display precision). A mismatch stops everything, and nobody raises any limit.

## Step 3: pilot, then EP-1 (only after step 2 passes)

```sh
MURMURATION_EP1_KEY=... PYTHONPATH=src python3 -m murmuration ep1 pilot --out-dir <out>/pilot --i-have-owner-confirm
MURMURATION_EP1_KEY=... PYTHONPATH=src python3 -m murmuration ep1 run --out-dir <out>/ep1 --i-have-owner-confirm
```

Hand-check `<out>/pilot/pilot_trace.txt` before `run`. Each batch writes `final.json`; stop at the first
`stopped:<why>`, void, `unbilled_unknown`, `overspent` marker or Console mismatch. All of it within the sheet's 3 days.
