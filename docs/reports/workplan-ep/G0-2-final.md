# G0-2 final acceptance: spend guard before the first paid call

Date: 2026-11-19. Reviewer: Opus 5.5 (independent, own probes). Follows `spend-reverification.md` (NOT ACCEPTED on R1,
test gaps R2) and `spend-canary-plan.md`.

Method: all probes ran on a scratch copy of the repo against the loopback fake server (`tests/fakeclaude.py`) with a
fake key. No real provider call, no key, no `.env*` read. `train/`, `runs/`, `data/` and the GPU were not touched
(`runs/spend` does not exist yet in the live repo). A socket guard aborted any non-loopback connect in every probe.

Verified bytes (unchanged in the live tree at the end of the review):

| File | sha256 |
|---|---|
| `src/murmuration/spend.py` | `fd217ff8caf501ae764b77cde129c3b8131bb37241020aa92ae7e9b22978591d` |
| `src/murmuration/backend_claude.py` | `224a2c5fc07a4a79708d387523f57893b45910c26b8eec031eee7856ec2cf244` |
| `src/murmuration/runner.py` | `8071b9b526b2048b2028a7d6153da4f31636211ee24ab6bee28370d621e9f867` |
| `docs/reports/price-sheet.json` | `ab01704b1d00f2fc418c9b1d0d0fda0b716e6e5d617111e8aa304d5cdfe99581` |
| `tests/fakeclaude.py` | `bd27dfb5fa7ad155cc709ee78bae6811abfd805bf8d4cee5a674b800b9411582` |
| `tests/test_spend.py` | `7fef7c040f4da335d2a63c7252171e6aac623a7827f25ece5d30a67dcfa63706` |
| `tests/test_backend_claude.py` | `7b9eb5c88deab73ac30af44fcb5719bef2408f3beb76b26961f15a38a07869fc` |

## Verdict: ACCEPTED-WITH-NOTES

R1 is closed and R2 is closed. No probe got past USD 10 through code. What remains are operator actions the code
cannot see (N2, N3), one low-risk usage-shape gap (N1), and a red test file from another lane (N4), which must be fixed
before step 0 of the checklist.

## 1. R1: attempts to exceed the USD 10 cap

The real-host check (`_check_pilot_ledger`) accepts a ledger only directly in `PILOT_LEDGER_DIR` (= `<repo>/runs/spend`,
from the realpath of the package), with a lower-case `.jsonl` name, not a dotfile, not a symlink. In that directory
`Ledger._files` counts EVERY file, whatever its name, and stops on any symlink, subdirectory or non-ledger content.

| Probe | Result |
|---|---|
| For each of 18 path forms: first fill the pinned dir to the cap, then drain a real-host client on that path (Opus, USD 0.82 per reserve) | max total **9.84**. No form adds spend |
| Refused: other dir, subdir, sibling `runs/spendsib`, `.json`, `.log`, `.JSONL`, `K.jsonl`, `.l.jsonl`, no extension, symlinked dir alias, path through a symlinked `runs`, symlinked ledger file | `ValueError` at construction |
| Accepted: absolute, relative `runs/spend/b.jsonl`, `runs/spend/../spend/c.jsonl`, `runs/x/../spend/d.jsonl`, `//q.jsonl` | all normalise to the pinned dir; the five together: **9.84** |
| `n.jsonl/.` | accepted at construction (the check uses `abspath`), but the first write fails with `FileNotFoundError` (fail closed) |
| Relative ledger path, then `chdir` after construction | **the reserve is written to `<newcwd>/runs/spend/r.jsonl`, outside the pinned dir** (N6). No `src/` code calls `chdir`, so this needs the caller to change cwd |
| Reserve line inside `notes.TXT` in the pinned dir (9.5) | counted: next reserve refused |
| Non-JSON file / subdirectory in the pinned dir | every reserve refused (fail closed) |
| Hard link of a pre-filled outside ledger (9.0) into the pinned dir | counted; used as the ledger itself it is still capped |
| Ledger pre-created with 9.9 before the client starts | counted (0 more) |
| Mode bits: ledger 000, dir 500, lock 000 | `PermissionError` before any request (fail closed) |
| Ledger truncated to a torn line mid-run | `SpendError` corrupt line: stop |
| Pinned dir renamed and replaced by a symlink after the client was built | a new real-host client is refused |
| 5 storms x 12 processes, `Barrier` start, full `ClaudeClient.call` path through the pinned dir; the fake bills every request at its full worst case | 7 requests per storm; true cost **9.0785** = ledger 9.0785; no key slice on disk |
| SIGKILL during a stalled request (between reserve and charge) | the worst case (USD 1.2809) stays counted in the dir |
| Usage NaN, Infinity, -1, 1e400, 10**30, bool, string from the fake | `Overspent`; ledger stays finite; the next reserve in the dir is refused |
| Price sheet with NaN, Infinity, 1e400 | refused |
| Sheet age 3 days / 4 days / future-dated | accepted / refused / refused. The current sheet expires 2026-11-22 |

R2 (mutants M16 and M17 from round 2) is now covered: `test_d5_redirect_not_followed` covers 301, 302, 303, 307
and 308 with a second server, and `test_r2_proxy_env_never_receives_the_key` builds the opener after setting the
proxy variables.

## 2. Mutation testing (10 safety lines, one at a time, `test_spend` + `test_backend_claude` + `test_runner`)

All 10 were killed:

1. The pinned dir counts only `*.jsonl`.
2. The real host skips the pin check.
3. Upper-case or non-`.jsonl` names are allowed.
4. The `HARD_CAP_USD` check is removed.
5. The post-call overspend check is removed.
6. Stale reservations are not counted.
7. Symlink entries are allowed in the pinned dir.
8. A symlinked ledger file is allowed.
9. `_NoRedirect` is removed.
10. The empty `ProxyHandler` is removed.

## 3. Environment, network, flakiness

- `src/` reads no `os.environ`, `getenv`, `dotenv`, `.env` or `ANTHROPIC_*` (grep). `seal.py` inspects only variable
  names passed to it, and `monitor.py` only has a regex that matches `.env`.
- Tests never contact the real host. The tests that name `api.anthropic.com` only construct the client and call
  `ledger.reserve`. One full suite run under a `sitecustomize` socket and DNS guard logged zero non-loopback attempts.
  The guard covered the parent process only; subprocess tests override `PYTHONPATH`.
- The full suite ran 15 times on the first snapshot: every run was `Ran 263 tests`, with the same 4 failures each
  time, all in `tests/test_egress.py`, a file another lane is still writing. The spend-scope modules gave
  `Ran 55 tests ... OK`. No flake.
- A rerun on a fresh copy of the live tests (with the spend hashes unchanged) gave `Ran 287 tests`, and
  `test_egress` now passes. **One failure remains:** `test_hold.HoldTest.test_relay_plant_trips_lint_for_every_seed`
  (N4).

## 4. What the real run does differently from the tests

| Aspect | Tests | Real run |
|---|---|---|
| Host | `http://127.0.0.1:<port>` with `allow_host` | `https://api.anthropic.com:443`. TLS uses urllib's default verified context, which no test exercises. A TLS failure is an `OSError`, so the call is `void_unknown`, the worst case is kept, and one retry is reserved separately |
| Ledger dir | temp dirs; `PILOT_LEDGER_DIR` mocked | `<repo>/runs/spend` (created 0700 on first use) |
| Key | fake string | owner's key, passed as an argument |
| Usage block | fake shapes | real `usage` may add `service_tier`, `server_tool_use` and `inference_geo`. These are dropped and never billed |

Untested paths that could make the ledger undercount (a real overshoot is possible only where the ledger undercounts):

- **N1 (Low):** a `cache_creation` breakdown that does not sum to `cache_creation_input_tokens`. For example,
  `{5m: 0}` with a total of 100000 was charged USD 0.00024 against a true cost of at least USD 0.50, and no
  `Overspent` was raised. The real API returns both breakdown fields summing to the total, and the harness never
  sends `cache_control`. Fix later: bill `max(total, 5m + 1h)`, with the difference at the 1h rate.
- Price multipliers that are absent from `usage`: data-residency or `inference_geo` (1.1x, possibly a workspace
  default), priority tier, web search or other server tools. The harness sends no tools and no geo. Only the Console
  comparison in the canary catches these.
- Thinking tokens are billed inside `output_tokens` and bounded by `max_tokens`, so they are covered.
- Bytes are at least tokens for the input bound (`ub = len(body)`). A violation is caught after the fact as
  `Overspent`, so the overshoot is at most that one call's excess.

## 5. Notes (not blocking the canary)

- **N2:** the pinned dir is per checkout. The scratch copy accepted `api.anthropic.com` with its own `runs/spend`.
  Paid calls must run only from `/home/adelmar/SeaBridgeAI/murmuration`. The Console limit is the machine-wide
  backstop.
- **N3:** deleting, truncating to 0 or moving the pinned dir resets the record. One probe showed an exposure of
  USD 11.88. Standing rule: never touch `runs/spend`.
- **N4:** other lanes' test files are still changing on disk. The suite is red only outside the spend scope (now
  `test_hold`). The full suite must be green before step 0. If any fix touches a spend file, re-hash it and
  re-verify.
- **N6 (Low):** `Ledger.path` is kept as it was passed, while `Ledger.dir` is absolute. With a relative ledger path, a
  later `chdir` sends this ledger's own writes outside the pinned dir. Rule: always pass an absolute ledger path.
  Later fix: `self.path = os.path.abspath(path)`.
- **N5 (Info):** a refused subdirectory ledger still runs `makedirs`, which leaves a subdirectory in the pinned dir.
  That subdirectory then blocks every reserve: it fails closed, but it is a denial of service.

## 6. Pre-paid-call checklist (the parent runs these in order and stops at the first failure)

0. Check that the full suite is green, with N4 fixed. Check the hashes above (or have any changed spend file
   re-verified). `runs/spend` must not exist or must hold only canary/EP ledgers.
1. **Price sheet:** if `fetched` is more than 3 days old (the current sheet expires 2026-11-22), refetch
   https://platform.claude.com/docs/en/about-claude/pricing, re-verify every row and bump `fetched`. The loader refuses
   an older sheet.
2. **Dry run:** run `fakeclaude.dry_run(...)` with a temp-dir ledger. Expect one `reserve` and then one `charge` per
   call, the record `usd` equal to the ledger total, and the fake to see only `dry-run-no-key`.
3. **Console:** the owner sets a workspace spend limit of USD 10 or less. Record the value and his words.
4. **1-call canaries (Sonnet, then Haiku 5.5, both required):**
   - Use an absolute path `/home/adelmar/SeaBridgeAI/murmuration/runs/spend/canary-<model>.jsonl`, `ceiling=0.05`,
     `max_calls=1` and `max_tokens=16`. The key comes from the owner's shell as an argument.
   - **Size the prompt so that a 10x price error is visible in the Console.** A one-line prompt costs about
     USD 0.0002, which rounds the same at either price.
     - Sonnet: pad to a request body of about 11,000 bytes. `ub` must be <= 12,000, which gives a worst case of about
       USD 0.048. Expected cost is about USD 0.005; at 10x it would be about USD 0.05.
     - Haiku 5.5: pad to a body of about 90,000 bytes. `ub` must stay below the 100,000 long-context threshold, which
       gives a worst case of about USD 0.018. At USD 0.10 per million input the cost is about USD 0.002; at the
       Haiku-4.5-like USD 1.00 it would be about USD 0.02.
   - Assert:
     - the returned model is the requested one;
     - the usage ints are present;
     - `cache_creation_input_tokens == 0`, and its breakdown sums to the total (N1);
     - no `overspent` or `unbilled_unknown` line;
     - no key slice in the ledger or stdout.

     A 429 or 5xx is a stop: report it, do not rerun.
5. **Console check, for each canary:**
   - Console input and output token counts equal the ledger `usage`. Tokens are exact.
   - The Console cost equals the ledger `charge` to display precision. For Haiku, this confirms the USD 0.10 input
     price.
   - First check whether the Console shows each request or only daily totals per model, and its lag. If it shows
     totals only, the canary must be the only traffic in that workspace during the window.
   - On any mismatch, stop and never raise a limit.
6. **EP-1 in one process:**
   - Use the pinned dir with an **absolute** ledger path (N6), `ceiling` <= 9.00, an explicit `max_calls`, no
     parallel processes and never `--out-dir` there.
   - Every `charge` must have `cache_creation_input_tokens == 0`; otherwise stop (N1).
   - Check the directory total after each batch.
   - Stop at the first void, `unbilled_unknown`, `overspent`, Console mismatch or sheet expiry, and refetch the sheet
     if it is older than 3 days before any later batch.
