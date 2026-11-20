# Spend re-verification: Claude API pilot (independent adversarial review, round 2)

Date: 2026-11-19. Subject: the uncommitted work on top of 972dee3 in `src/murmuration/spend.py`, `backend_claude.py`,
`runner.py` (claude path) and `docs/reports/price-sheet.json`.

Method: I wrote my own probes. I ran them on a scratchpad copy against loopback fake servers only, with a fake key.
No real provider call was made, no key was read, and no `.env*` file was opened. `train/`, `runs/`, `data/` and the
GPU were not touched; the `train/*.py` files were only copied so the tests could import them.

The probe scripts are `probes.py`, `probes2.py`, `mutate.py` and `m16probe.py` in the session scratchpad. Their
results are quoted below. `probes2.py` was later overwritten on disk by another process, but its results were
captured before that.

Verified bytes (sha256 of the working-tree files I tested):

| File | sha256 |
|---|---|
| `src/murmuration/spend.py` | `7abf34abd1717e5547953b3bfd29a7a654ef969ada452b1a8da4ec72cb75c517` |
| `src/murmuration/backend_claude.py` | `77ac7a9071c73bae14af577cb3bd228144705fb74ed37087791bf67de0a93bd2` |
| `src/murmuration/runner.py` | `8071b9b526b2048b2028a7d6153da4f31636211ee24ab6bee28370d621e9f867` |
| `docs/reports/price-sheet.json` | `ab01704b1d00f2fc418c9b1d0d0fda0b716e6e5d617111e8aa304d5cdfe99581` |
| `tests/fakeclaude.py` | `bd27dfb5fa7ad155cc709ee78bae6811abfd805bf8d4cee5a674b800b9411582` |

## Verdict: NOT ACCEPTED, with one small blocking fix (R1)

D1 to D9 are fixed as originally scoped (table below). One residual is still money-critical: the USD 10 owner cap
covers only one directory and only files named `*.jsonl`. Pass a different ledger directory, or a ledger name that
does not end in `.jsonl`, and `HARD_CAP_USD = 10` is sidestepped. A probe reserved **USD 27.06 in one directory**
using the names `a.json`, `b.log`, `c.JSONL` and `d.jsonl`.

Fix R1 first (a few lines plus 2 tests). After that the code is ACCEPTED-WITH-NOTES for the canary and EP-1, under
the checklist in section 6.

## 1. D1 to D9: re-proved with my own probes

| # | Status | Evidence (my probe) |
|---|---|---|
| D1 per-file ceiling | FIXED within one dir; **bypass remains** (R1) | 12 processes on 4 files in one dir (opus reserve USD 0.82 each, ceiling 9 each): dir total 9.84. Ten storms of 8 processes on 8 files, each with ceiling 10: max dir total 9.84. Three dirs: total 29.52. A subdirectory (`dir/sub/x.jsonl`) is a separate dir: total 19.68. Non-`.jsonl` names in the same dir: 27.06. |
| D2 cross-process race | FIXED (per dir) | The storms above all used a `Barrier` lockstep start. No storm overshot. A symlinked alias of the same dir shares the lock (total <= 10). With the lock held elsewhere, `reserve` fails closed (`SpendError`). |
| D3 NaN | FIXED | The sheet refuses `NaN`, `Infinity`, `-Infinity`, `1e400` (parsed as inf), `-1`, `"2"` and `true`. Usage values NaN, inf, negative, float, bool, str, missing input, non-dict, negative `cache_creation` and 1e30 each give `Overspent`, a finite spend >= the reserve, and every later reserve in the dir blocked. A NaN usage sent by the fake server gives `Overspent`, with a finite ledger. |
| D4 unbounded args | FIXED | `ceiling` NaN, inf, -1, 0, 10.0001, 1e9, "5", True and None are refused, and 10.0 is accepted. `max_calls` 0, -1, True, 1.5 and "3" are refused. `ub` and `max_tokens` that are negative, 0, float, bool, NaN, or `max_tokens` > 64000 are refused. `ub = 10**400` fails closed (`OverflowError`, no line written). `ub = 1e12` is refused by the ceiling. |
| D5 host | FIXED | 21 bad URLs are refused (evil host, suffix host, `@` userinfo both ways, http, ports 8443/80, path, query, fragment, trailing dot, ftp, `\@`, loopback without `allow_host`, `[::1]`, bad port, scheme-less). `allow_host` is refused for 10.0.0.1, 0.0.0.0, `::ffff:7f00:1`, 127.0.0.2 and evil hosts. Redirects 301, 302, 307 and 308: 1 request, the second server is never hit. A URL with control characters is accepted at construction, but `http.client` refuses it before connecting: 0 server hits, the reserve is kept (fail closed, Info). |
| D6 post-call overspend | FIXED | A fake response reporting 5M input tokens: the true cost (USD 10.0001) is recorded, `Overspent` is raised, and the dir is blocked. Sonnet requested, Fable returned: actual > reserve, so `Overspent` is raised and the Fable price is recorded. |
| D7 model mismatch | FIXED | Sonnet requested, Opus returned: charged at the Opus price. Haiku returned: charged at the Sonnet price (the dearer one). An unknown model is charged at the reserved worst case. A non-string `model` is voided and charged at the worst case. Every case voids the episode. |
| D8 key echo | FIXED for full key, first 10 and last 10 characters | A key echoed in `model`, `stop_reason`, `text`, `usage`, extra fields, and 401, 429 and 500 bodies: no full key, prefix or suffix appears in the ledger, record or error. **Residual (Info):** a middle slice (`key[10:30]`) is not scrubbed. Only a non-Anthropic (loopback test) host can echo it. |
| D9 record usd | FIXED for the normal and retry paths | After a 500 and then a retry: 2 reserves, and the record `usd` equals the ledger. Dry run of 40 calls: the record and the ledger both show USD 0.015100. **Residual (Low):** on `http.client.BadStatusLine` the ledger keeps USD 0.000968, but `ep.usd` = 0 (no `void_unknown`, no `unbilled_usd`). The ledger fails closed; the record undercounts. |

**Stale reservations.** A child process SIGKILLed after `reserve` leaves its worst case counted in the global total
(USD 0.82). Its id cannot be reused. A stale reservation stays counted forever, which fails closed.

### What the cap actually covers

- **Covered:** every `*.jsonl` file (case-sensitive) directly inside `dirname(abspath(path))`, for every process
  and process tree that uses that same directory.
- **Not covered:**
  - a different directory, including a subdirectory;
  - a ledger name that does not end in lower-case `.jsonl`;
  - renaming, moving or deleting the ledger files;
  - patching `spend.HARD_CAP_USD` at runtime.
- **So:** it is **not** per machine. **Yes, HARD_CAP_USD = 10 can be sidestepped by passing a different ledger
  directory** (or a non-`.jsonl` name). The Console workspace limit is the only true backstop.

## 2. Flakiness

I ran the full suite 20 times (`PYTHONPATH=src python3 -m unittest discover -s tests`, on the scratch copy with
`train/*.py` and `practices/` copied). All 20 runs gave `Ran 186 tests ... OK (skipped=2)`, in 26.8 to 29.1 s. No
flake.

## 3. Price sheet

I re-opened https://platform.claude.com/docs/en/about-claude/pricing on 2026-11-19. Every sheet number still
matches the Model pricing table:

- Fable 5.2: 8 / 40 / 10 / 16 / 0.20
- Opus 5.5: 4 / 20 / 5 / 8 / 0.20
- Sonnet 5.5: 2 / 10 / 2.50 / 4 / 0.10
- Haiku 5.5: 0.10 / 0.50 / 0.125 / 0.20 / 0.01 for prompts up to 100k tokens, and 0.50 / 2.50 / 0.625 / 1 / 0.05
  above that

**The Haiku 5.5 oddity is unchanged.** Input is USD 0.10, while the same page lists Haiku 4.5 at USD 1. So the
oddity is in the source, not in the transcription. No Haiku run until a Haiku canary's Console cost equals the
ledger.

**Expiry.** `expires_on()` = 2026-11-22. The sheet is accepted on 11-22 and refused on 11-23. A future-dated sheet
is refused.

**The `inference_geo` parameter** carries a 1.1x price multiplier. The harness never sends it (the payload keys are
only model, max_tokens, temperature, messages and system), so keep it that way.

**D10 is still open (Low).** A sheet with `opened:false` and a per-thousand `unit` still loads.

## 4. Runner claude path and environment

- The runner refuses before writing any ledger line in each of these cases:
  - no `allow_backend`;
  - no `spend_ledger`;
  - no `price_sheet`;
  - no `api_key` (`ValueError`);
  - `ceiling=50`;
  - `dry_run` with api.anthropic.com.
- Dry run sends only `x-api-key: dry-run-no-key`, and the key is absent from the ledger and the record.
- The CLI `run ... --backend claude --allow-backend` fails closed. The message "(CLI: --allow-backend)" is misleading
  (Info, D11).
- No code in `src/` reads `os.environ`, `getenv`, `dotenv`, `.env` or `ANTHROPIC_*` (checked with grep).
  - In the tests, `test_ledger.py` and `test_cli.py` copy `os.environ` only to set `PYTHONPATH` for a subprocess.
  - `test_backend_claude.py` sets `ANTHROPIC_BASE_URL` and the proxy variables to prove they are ignored.
  - `ProxyHandler({})` ignores the proxy variables, but see M17.

## 5. Mutation testing

24 mutants were run against `test_spend`, `test_backend_claude` and `test_runner` on a temp copy. **20 were killed.
4 survived:**

- M3: the ceiling compare rewritten in the NaN-unsafe form. Equivalent now: NaN cannot reach `spent` or `worst`.
- M13: `parse_constant` removed from the sheet load. Equivalent: `_num` still refuses non-finite values.
- **M16: `_NoRedirect` removed. A real test gap.** The test covers only 307, which urllib never follows for POST.
  For 301, 302 and 303, urllib (`urllib/request.py` lines 660 to 679) re-issues a GET to the `Location` host and
  copies every header except content-*, so `x-api-key` would go to that host.
- **M17: `ProxyHandler({})` removed. A real test gap.** The test sets the proxy variables after `_OPENER` was built
  at import. A probe with the opener built after `HTTP_PROXY` was set sent the key to the proxy (1 hit).

The killed mutants include:

- removing the global cap, the per-file ceiling, flock, the post-call overspend check, the overspent marker, dearer
  pricing, the ceiling bound or the price check;
- allowing negative usage;
- not counting the other ledgers or the stale reserves;
- allowing a non-loopback `allow_host` or any host;
- disabling the full or partial scrub;
- leaving the retry unreserved;
- allowing non-text blocks;
- turning off the runner gate or the dry-run key swap;
- making a lock timeout fail open.

## Ranked residual defects

| # | Severity | Defect | Fix |
|---|---|---|---|
| R1 | **Critical (blocks paid calls)** | The cap is sidestepped by another directory, a subdirectory, or a name that is not `.jsonl` (USD 27.06 in one dir, 29.52 over 3 dirs). | Add a constant `PILOT_LEDGER_DIR`: one fixed absolute directory under the repo (for example `<repo>/ledgers/pilot`, git-ignored). Put the check in `ClaudeClient.__init__` on the `api.anthropic.com` branch only. Do not put it in `Ledger.__init__`: the tests use temp dirs, and any escape hatch there reopens the bypass. The check requires `realpath(ledger.dir) == realpath(PILOT_LEDGER_DIR)` and `basename(ledger.path)` ending in lower-case `.jsonl`. Loopback and dry-run runs stay free; the paid path is closed. Add 2 tests: a temp-dir ledger with the real host is refused, and `x.json` in the pinned dir is refused. Optionally also take an owner-level `flock` on a fixed file. |
| R2 | Medium | Test gaps M16 and M17: removing the no-redirect handler or the empty `ProxyHandler` would leak the key, and no test fails. | Add a 302 test that asserts the second server sees zero requests of any method (add `do_GET` to the fake). Add a test that rebuilds the opener with `HTTP_PROXY` set, or asserts `ProxyHandler` has empty `proxies` on `_OPENER.handlers`. |
| R3 | Low | Ledger API misuse: a second `charge` for the same id replaces the first (0.38 to 0.00). `charge(..., usd=0)` and `void_unknown(..., kind="charge", usd=0)` overwrite fixed fields through `**record` (0.82 to 0.00). `ClaudeClient` never does either. | Refuse an already-charged id. Put `**record` first in the dict literal, or reject the reserved keys. |
| R4 | Low | `ep.usd` is 0 when `BadStatusLine` or `IncompleteRead` escapes. The ledger is correct. | Catch `http.client.HTTPException` together with `OSError`. |
| R5 | Low | `usage` of `10**400` raises `OverflowError` in `charge`. No charge or overspent marker is written; the worst-case reserve still counts. | Catch `OverflowError` alongside `SpendError` in `charge`. |
| R6 | Low | `system` is not checked for non-text blocks, which breaks the bytes >= tokens bound. The runner only passes a string, and D6 catches any overrun after the fact. | Apply the same text-only check to `system`. |
| R7 | Low | D10: `opened` and `unit` are not checked. | Refuse unless `opened is True` and `unit == "USD per million tokens"`. |
| R8 | Info | The middle slice of the key is not scrubbed. A control-character URL passes construction but never connects. D11 message wording. | Optional. |

## 6. Final pre-paid-call checklist (the parent follows this in order)

0. Fix R1 and add its 2 tests. R2 is strongly recommended. Rerun the full suite: it must be green.
   - Re-hash the files in the table above.
   - Have anything that changed outside the R1/R2 diff re-verified before the canary.
1. **Price sheet:** check that it is under 3 days old (expires 2026-11-22). Otherwise refetch, re-verify every row and
   bump `fetched`.
2. **Dry run (no key, no network):**
   - Run `fakeclaude.dry_run(...)` with its ledger in a temp dir (R1 allows that on loopback).
   - Check: one `reserve` then one `charge` per call; the record `usd` equals the ledger; the fake saw only
     `dry-run-no-key`.
   - **Standing rules:**
     - Never rename, move or delete anything in the pinned dir.
     - `--out-dir` must never be the pinned dir: a run-record `.jsonl` there stops every call.
3. **Console:** the owner sets a workspace spend limit of USD 10 or less. Record the value and his words.
4. **Sonnet canary, 1 call:**
   - Fresh `canary.jsonl` in the pinned dir: `ceiling=0.05`, `max_calls=1`, `max_tokens=16`, a one-line prompt.
   - The key comes from the owner's shell and is passed explicitly, never from a file.
   - Assert: the returned model equals `claude-sonnet-5-5`; the usage ints are present; no `overspent` or
     `unbilled_unknown` line; no key slice in the ledger or stdout.
   - A 429 or 5xx ends in `MaxCallsExceeded` on the retry (`max_calls=1`). That is a stop: report it, do not re-run.
5. **Console cost check:** the Console cost for that request equals the ledger `charge` (to display precision). On a
   mismatch, stop and report. Never raise any limit.
6. **Haiku:** only if Haiku is needed, repeat steps 4 and 5 with `claude-haiku-5-5` (the 0.10 oddity).
7. **EP-1 as a single process:**
   - Pinned dir, `ceiling` <= 9.00, an explicit `max_calls`, never running in parallel.
   - Check the directory total after each batch.
   - Stop at the first void, `unbilled_unknown`, `overspent`, Console mismatch or sheet expiry.
