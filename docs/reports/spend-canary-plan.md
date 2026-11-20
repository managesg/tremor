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
- Price sheet staleness: 3 days. The sheet fetched 2026-11-19 expires 2026-11-22 (`PriceSheet.expires_on()`).
  Refetch and bump `fetched` before then; an older sheet is refused.

## Step 0: dry run (no key, no network)

`tests/fakeclaude.dry_run(task, arm, seed, ledger, price_sheet)` runs the full claude path against the loopback fake
server. In `dry_run` mode the runner refuses a non-loopback `base_url` and replaces any supplied key with a dummy.
Check the ledger: one `reserve` then one `charge` per call, run `usd` equals the directory total.

## Step 1: Console limit

Owner sets a Console workspace spend limit of USD 10 or less. The ledger is an estimate; the Console is the backstop.

## Step 2: Sonnet canary

- One call, model `claude-sonnet-5-5`, `max_tokens=16`, a one-line prompt.
- Fresh canary ledger in the pilot ledger directory, `ceiling=0.05`, `max_calls=1`.
- Assert: returned model equals the requested one; usage fields present and finite; no `overspent` marker; no key in
  the ledger or stdout.
- Compare: the Console cost for that request must equal the ledger `charge` USD (to display precision). A mismatch stops
  everything, and nobody raises any limit.

Skeleton for the owner's shell (the key comes from the owner's environment, never from a file in the repo):

```python
led = spend.Ledger(f"{PILOT_DIR}/canary.jsonl", spend.PriceSheet.load(SHEET), ceiling=0.05, max_calls=1)
cl = backend_claude.ClaudeClient(api_key, led)
rec = cl.call(backend_claude.Episode("canary", 200, 30), "canary:0", "claude-sonnet-5-5",
              [{"role": "user", "content": "Reply with OK."}], 16)
```

## Step 3: Haiku canary (only after step 2 passes)

The sheet lists Haiku 5.5 input at USD 0.10 per million tokens, 10x below Haiku 4.5. Repeat step 2 with
`claude-haiku-5-5` and the same 0.05 sub-ceiling. Console cost must equal the ledger. No Haiku batch before this.

## Step 4: batches

One process at a time, a `max_calls` per batch, directory total checked against 9.00 after each batch. Stop at the first
void, `unbilled_unknown`, `overspent` marker or Console mismatch.
