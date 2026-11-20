# Spend verification: Claude API pilot (independent adversarial review)

Date: 2026-11-19. Subject: uncommitted work on top of 972dee3 in `src/murmuration/spend.py`, `backend_claude.py`,
`runner.py` (claude path), their tests, `tests/fakeclaude.py`, `docs/reports/price-sheet.json` and `price-sheet-notes.md`.
Method: code reading plus probes run on a scratchpad copy against the loopback fake server only. No real provider
call was made, and no key was read or used.
Owner rule: hard ceiling USD 10. Code default stop: USD 9.00. Unknown cost is not zero.

## Verdict: NOT ACCEPTED (for paid calls)

The single-process happy path is sound. If one process uses one ledger, the prices are right and billed input
tokens are no more than request bytes, total spend stays at or below the ceiling. Several fail-open paths are
reachable without a hostile server, though, and each one must be fixed before the first paid call (D1 to D5).

## Ranked defects

| # | Severity | Defect | Evidence (probe on copy) | Fix before paid call |
|---|---|---|---|---|
| D1 | Critical | The ceiling applies per ledger file. Each new `spend_ledger` path starts at USD 0, and runner callers choose the path freely (the tests use `l.jsonl`, then `l2.jsonl`). | 3 ledgers reserved USD 24.00 in total, each under its own 9.00. | Pin one canonical pilot ledger path (a constant, or refuse any other path) so every run shares one total. |
| D2 | Critical | No cross-process lock (a documented `shortcut:`). `totals()` and the append are not atomic, and the project rules encourage parallel workers. | Lockstep start (Barrier): 3 processes x USD 5 reserved USD 15 against a 9.00 ceiling. With 2 processes and no forced delay, 96/100 trials both passed. | `fcntl.flock(LOCK_EX)` around read-totals-check-append in `reserve` (and in `charge`). |
| D3 | Critical | NaN fails open. Python `json.loads` accepts `NaN` and `Infinity`, and `x > nan` is False. A NaN in the price sheet or in a response `usage` value disables the ceiling. A NaN charge is written to the ledger as `NaN`, so the ledger stays poisoned. | NaN price: 5 reserves of 1M/1M tokens passed a 0.0001 ceiling. NaN usage: 20/20 USD 12 reserves then passed a 0.05 ceiling. | Load the sheet and responses with `parse_constant` that raises. Require every price to be a finite number >= 0 and every token count to be an int >= 0. Write the check as `if not (spent + worst <= ceiling)`, and refuse when `spent` is not finite. |
| D4 | Critical | Caller arguments are not bounded. `ceiling` accepts 1000 or NaN (there is no hard cap at 10). `max_tokens` and `input_tokens_ub` accept negative values, which reserve a negative worst case and free budget. | `ceiling=1000` accepted. `ceiling=NaN` passed a USD 12 reserve. `max_tokens=-1e6` reserved worst = -10.00. | `HARD_CAP = 10.0`, and refuse unless `0 < ceiling <= 9.0`. Require positive ints for `max_tokens` and `ub`. |
| D5 | High | `base_url` accepts any https host (`https://evil.example`, `https://api.anthropic.com.evil.example`, `https://api.anthropic.com@evil.example`) and loopback http, with no explicit flag. That sends the key elsewhere and makes D6 to D8 reachable. | All 5 URLs accepted. | Allowlist `api.anthropic.com` only, with `allow_test_base_url=True` required for loopback. |
| D6 | High | `charge` never re-checks the ceiling. If actual cost exceeds the reserved worst case (the byte bound fails, or the server over-reports), spend passes the ceiling silently. Negative usage lowers spend. | A tiny reserve followed by a 5M-token usage report left spent = 10.00 with no error. A -10M input charge left spent = -20.00. | In `charge`, clamp each count to >= 0. If `usd > reserved worst`, write the charge, then raise and halt the run. |
| D7 | Medium | A returned model other than the one requested is priced at the requested model's price. A pricier returned model is undercounted (the episode is voided, but the money is spent). | Opus returned for a Sonnet request was charged 0.0120 against a true 0.0240. | Charge at max(price(requested), price(returned)), or keep the worst case when the returned model is not in the sheet. |
| D8 | Low | Key scrubbing covers only error text, and only the full key. A server echoing the key in `model`, `stop_reason` or `usage` writes it to the ledger and the record unscrubbed. Response `text` enters the in-memory record. A partial key prefix is not scrubbed (code inspection; the probe for this checked only the full key and proves nothing). Only reachable from a non-Anthropic host, which D5 closes. | Ledger leak confirmed for echoes in `model`, `stop_reason` and `usage`. Error 401/500, connection refused, timeout and bad JSON were clean. | Apply `_scrub` to everything persisted, or rely on D5. |
| D9 | Low | The run record's `usd` sums only successful calls. On a retry, the first attempt's worst case stays in the ledger but not in the record. | Ledger 0.000688 against record 0.000120. | Report ledger spend per episode, or label the field `usd_billed_known`. |
| D10 | Low | The price sheet's `unit` and `opened` fields are not checked. A sheet with `opened:false` and a per-thousand unit loads. | Loaded. | Refuse unless `opened is True` and the unit is `USD per million tokens`. |
| D11 | Info | `http.client.BadStatusLine` (an `HTTPException`, not an `OSError`) escapes the retry loop. This fails closed: the reserve stays at worst case and there is no retry. The CLI `run --backend claude --allow-backend` cannot reach the claude path (no ledger, sheet or key arguments) and fails closed. Its message "CLI: --allow-backend" is misleading. | Probe confirms the reserve is kept. | None required. |

## (1) Overshoot analysis

- Honest single process with one ledger and a correct sheet: total <= ceiling (9.00). At runner defaults the request
  body is at most 596 bytes, which gives a per-call worst case of USD 0.0054 (Sonnet), 0.0108 (Opus) or 0.0215 (Fable).
  An episode is 40 calls. With every call also retried, it reserves at most USD 0.43, 0.86 or 1.72.
- N processes on one ledger: overshoot <= (N-1) x the largest per-call worst case. That is cents at defaults, but
  unbounded if a caller raises `max_tokens` (for example, Opus at 128k output is USD 2.56 per call).
- Unbounded cases: D1 (k ledgers give k x 9), D3 (NaN), D4 (ceiling or negative argument), D6 (actual above worst
  case, or negative usage).
- Handled correctly:
  - A crash between reserve and charge counts at worst case.
  - A failed or timed-out call keeps its worst case (both attempts are reserved).
  - The 1h cache-write rate is used for the worst case and when no breakdown is given.
  - Thinking tokens fall within `max_tokens`, and no `thinking` parameter is sent.
  - Streaming is not used.
  - The Haiku tier threshold counts input, cache read and cache write tokens, which matches the page.
  - Non-ASCII text is escaped by `ensure_ascii`, which keeps the byte bound conservative.
- Residual assumption: billed input tokens <= request bytes. This holds for the text-only messages the runner
  builds. It does not hold for image or document blocks, especially URL sources. `call()` should refuse any
  non-text content block.

## (2) Price sheet

I opened https://platform.claude.com/docs/en/about-claude/pricing on 2026-11-19 (HTTP 200). Every number in the
sheet matches the "Model pricing" table:

- Fable 5.2: 8 / 40 / 10 / 16 / 0.20
- Opus 5.5: 4 / 20 / 5 / 8 / 0.20
- Sonnet 5.5: 2 / 10 / 2.50 / 4 / 0.10
- Haiku 5.5, prompts up to 100,000 tokens: 0.10 / 0.50 / 0.125 / 0.20 / 0.01
- Haiku 5.5, prompts over 100,000 tokens: 0.50 / 2.50 / 0.625 / 1 / 0.05

The page states that the prompt-length tier is Haiku-only ("Claude 4.6 and later ... except Claude Haiku 5.5 ...
standard pricing"), and that prompt length counts cache reads and writes.

- **Haiku oddity:** the page prints USD 0.10 input for Haiku 5.5, 10x below Haiku 4.5 (USD 1 on the same page). The
  sheet transcribes the page correctly, but the price is suspicious. Do not run Haiku until a 1-call canary's Console
  cost matches the ledger.
- **Units:** USD per MTok, divided by 1e6 in the code. Correct.
- **Nulls:** refused for the tier in use. Correct.
- **Staleness:** limited to 3 days, so refetch by 2026-11-22.
- **Data residency:** the page lists a 1.1x data-residency multiplier. The harness sends no residency parameter.
  Keep it that way.

## (3) Returned-model check

- Exact match, or a listed alias, is required. `aliases` is empty, so if the API returns a dated ID, every episode
  is voided after it has been paid for.
- A missing `model` field becomes `unbilled_unknown` at worst case, with no retry. Correct.
- A proxy redirect (3xx) is refused, with 1 request and no follow.
- A downgrade or other model voids the episode, but see D7 for the pricing.
- `ANTHROPIC_BASE_URL` and the `*_PROXY` variables are ignored (`ProxyHandler({})`, plus a test).

## (4) Key safety

The planted-key probe was clean for:

- an error body echoing the key (401, 500);
- connection refused;
- timeout;
- invalid JSON;
- an exception's `str`, `repr`, `__cause__` and `__context__`.

It leaked through the success-path echoes listed in D8. Verbose suite output contains neither fake-key literal.
The base-URL host restriction is missing (D5).

## (5) Idempotent retry

- A retry reserves `id#r1`, so both attempts count.
- Reusing a call ID is refused, so a replayed run cannot double-charge.
- A duplicate charge for the same ID overwrites rather than adds.

There is no double-count and no undercount in the ledger (the record undercounts, see D9).

## (6) Runner claude path

- `allow_backend`, `spend_ledger` and `price_sheet` are each required. Each is tested, and each fails before any
  client is built.
- The tests reach only `fakeclaude` on 127.0.0.1. The only uses of the default host are in `ClaudeClient`
  constructor validation, which makes no call.
- A suite run under a loopback-only socket guard (`sitecustomize`) passed. The sandbox refused my command to
  confirm the guard loaded, so treat this as supporting evidence. The static check is the primary evidence.
- Recommendation: make the default base URL unreachable from tests (D5's flag does that).

## (7) Flakiness

Full suite 10 times (`PYTHONPATH=src python3 -m unittest discover -s tests`): 10/10 `Ran 131 tests ... OK
(skipped=1)`, 17.2 to 18.9 s each. The skip is torch-only.

## (8) Checks the parent must run before the first paid call

1. Fix D1 to D6, and add a regression test for each: per-path ledger, a two-process flock race, NaN in the sheet and
   in usage, the ceiling cap and negative arguments, the host allowlist, and charge above worst case.
2. Have the owner set a Console workspace spend limit of USD 10 or less. This is the platform backstop; the ledger is
   only an estimate.
3. Refetch the price sheet (it must be under 3 days old) and bump `fetched`.
4. Dry run: the full pilot command against `fakeclaude` with the pinned ledger path. Check the ledger lines (reserve
   then charge for each call), the per-episode worst-case total, and that the record's `usd` matches the ledger.
5. Canary: 1 call to Sonnet with `max_tokens` = 16, a sub-ceiling of USD 0.05 on a fresh canary ledger, and
   `max_calls=1`. Assert:
   - returned model == requested model (with `aliases` empty);
   - the `usage` fields are present and finite;
   - ledger USD equals the Console cost for that request;
   - the ledger and stdout contain no key.
6. No Haiku until a Haiku canary's Console cost matches the ledger (because of the 0.10 price).
7. Batches: one process at a time on the pinned ledger, a `max_calls` per batch, and the cumulative ledger total
   checked against 9.00 after each batch. Stop at the first void, `unbilled_unknown` or Console mismatch.
