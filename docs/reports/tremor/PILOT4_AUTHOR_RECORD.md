# Pilot 4 author record (D8-b, D8-c, D8-d and the seven criteria)

Status: a transcription of rulings already logged in `docs/reports/tremor/DECISION_LOG.md`
("2026-11-25: Pilot 4 D8 rulings", commit a1ed80d, line author under OD4) against the sources
below. It sets nothing, authorizes no spend, and changes no pinned file. No network, model, GPU
or key was used to write it. Running paid-call total recorded in the log: USD 0.00.

Sources read: `DECISION_LOG.md:265-273`; `lab/pilot3_prompt_replay.py`; `src/murmuration/team_claude.py`;
`prereg/EP1.md`; `docs/reports/workplan-ep/P3-clearance-criterion-2.md`;
`docs/reports/workplan-ep/Pilot4-pricing-verification-gates.md`; `lab/pilot_clearance.py`;
`lab/pilot4_preflight_manifest.py` and `lab/tests/test_pilot4_preflight_manifest.py`;
`docs/reports/tremor/PILOT4_RUN_PACKET.md` (secondary, for command lines).

## 1. Wording (D8-b): `array_only`

Exact text (one line, no trailing newline, 103 UTF-8 bytes), the identical second-round instruction in
every arm and order, replacing only turn.md's last line `Reply with one JSON array.`:

```
Return exactly one JSON action array, starting with [ and ending with ]. Do not include any other text.
```

SHA-256, recomputed here:
`bdfc985f869eb32894e5fa166aa58e2991d59469bfd7845ab71d4446fe0643c9`

Command (run from the repo root, `PYTHONPATH=src:.`):

```
python3 -c 'import hashlib,sys; w="Return exactly one JSON action array, starting with [ and ending with ]. Do not include any other text."; print(hashlib.sha256(w.encode()).hexdigest(), len(w.encode()))'
```

Cross-checks, all run in this session:
- `lab/pilot3_prompt_replay.py:18` `CANDIDATES["array_only"]` equals the text above (string equality True).
- `src/murmuration/team_claude.py:50` `PILOT4_ROUND2_WORDING` equals the text above (True), and
  `:51` `PILOT4_ROUND2_WORDING_SHA256 = hashlib.sha256(PILOT4_ROUND2_WORDING.encode()).hexdigest()` prints the same digest.
  It is applied only when `batch == "pilot4"` and round index 1 (`:255-258`).
- Convention for the recorded value: each pilot4 episode record carries
  `"round2_wording_sha256": PILOT4_ROUND2_WORDING_SHA256` (`team_claude.py:526`), the sha256 of the UTF-8 bytes
  of the wording with no newline. The manifest uses the same method for `wording_sha256`
  (`lab/pilot4_preflight_manifest.py:144`). No pilot4 episode record exists (no run), so the recorded
  value could be checked only against the convention, not against a real record.
- Why chosen (log, `P3-clearance-criterion-2.md:7`): every Pilot 3 overage had text before the final array;
  the largest archived request with this wording is 1,586 bytes against the 2,000-byte cap.
  The log's own limit: the offline replays hold archived replies fixed, so neither wording is shown to shorten replies.
  `array_only` is the reviewer's alternative in `P3-clearance-criterion-2.md`; the other candidate, `packet`, is not chosen.

## 2. Scoring scope (D8-c; no new ruling, `EP1.md` already fixes it)

The log says: "`EP1.md:997-1007` and `:1297` already fix it".
- Core, 144 calls (the three EP-1 conditions `none`, `play`, `code`: 18 episodes): the 150-token maximum
  (`EP1.md:1003-1004`, "the largest `output_tokens` is at most 150"), reply format (`:1005-1006`) and arithmetic (`:1007`).
  `EP1.md:997-998`: "All seven, read on the three EP-1 conditions (`none`, `play`, `code`: 18 episodes, 144 calls) unless stated."
  `EP1.md:1297` shows the same scope in the Pilot 3 result: "Across the 144 calls in the three EP-1 arms, 13 exceeded 150".
- Whole batch: zero `max_tokens` stops (`EP1.md:1003`, "0 replies with `stop_reason` `max_tokens` in the batch").
- All attempts: shape, identity and spend (D8-c in the log; `Pilot4-pricing-verification-gates.md` review item 1 asks for
  "which shape and spend checks use all attempts"). `EP1.md:1001` reads criterion 1 over "the batch".
- `EP1.md:999-1000`: criteria 1 to 4, 6 and 7 are read on the whole batch, both orders together, with thresholds unchanged;
  each is also printed per order as a description.
- Implemented in `lab/pilot_clearance.py:183` (zero whole-batch `stop_max_tokens` and core `over_150 == 0`) and
  `:201` (criterion_scope text citing D8-c). The whole-batch over-150 count and per-condition maxima are printed too.

## 3. Order rule (D8-d)

"Apply the rule unchanged; Pilot 4 never replaces Pilot 3's `shared` selection (`EP1.md:279`); a different or
absent order result goes back to the author and the EP-1 freeze stays blocked." (log, D8-d)
- `EP1.md:279-280`: "Task list order: `shared`, selected by the section 13.16b rule using Pilot 3 (section 18, pre-freeze change 20)."
- Rule text: `EP1.md:1018-1043` (usable = (a) room, mean `Y_none` 0.30 to 0.80; (b) at least 2 executed duplicates under `none`;
  (c) `Y_code` differs from `Y_none` in at least one set). Exactly one usable: it; both: `shared`; neither: criterion 5 fails and
  EP-1 is not cleared (`:1039-1044`).
- Pilot 3 stays immutable (`Pilot4-pricing-verification-gates.md`, review item 1; `P3-clearance-criterion-2.md`, "Keep Pilot 3 immutable").
- Implemented in `ep1.order_gate` (`src/murmuration/ep1.py` `:579-608`); `pilot_clearance` check 5 passes only when
  `picked` is non-null and `code` duplicates are 0 (`lab/pilot_clearance.py:187`).
- **Stated deviation (author ruling, OD4):** the zero-`code`-duplicates requirement is stricter than `EP1.md:1026-1027` ("Under `code` the count is 0 by construction; a non-zero count is the stop of section 12, not an input here"). It is kept because it can only turn a pass into a fail (the cautious side). Same note in `PILOT4_RUN_PACKET.md:118`.
- If Pilot 4's result differs from `shared` or is absent: the table goes back to the author, nothing is picked by hand
  (`EP1.md:1015-1017`: "no order is picked by hand and no threshold is moved"), and the freeze stays blocked.

## 4. The seven criteria

Text is quoted from `prereg/EP1.md:1001-1012`. `EP1.md` contains no Pilot 4 text; these criteria sit in its Pilot 2
specification, and `P3-clearance-criterion-2.md` applies them to the follow-up batch as "EP-1 section 13.16b".
Commands 1 to 5 are one invocation (there is no per-check `check N` subcommand; the CLI is
`pilot_clearance.py [-h] [--batch {pilot3,pilot4}] directory ledger`), run only after a pilot4 run exists:

```
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m lab.pilot_clearance runs/ep1-live/pilot4 runs/spend/pilot4.jsonl --batch pilot4
```

Read each result in the printed `criteria` object, keys as below. Exit 2 means the evidence is missing or inconsistent.

| # | Quote (`EP1.md` line) | Scope | Check |
|---|---|---|---|
| 1 | `:1001` "Request shape: 0 HTTP 400 in the batch; every response holds only `text` blocks (the block types are recorded per call)." | whole batch, all attempts | `criteria."1_request_shape"` (`pilot_clearance.py:182`: `http_400_in_trace` and `non_text_replies` both 0) |
| 2 | `:1003-1004` "No truncation: 0 replies with `stop_reason` `max_tokens` in the batch, and the largest `output_tokens` is at most 150, half the cap." | zero `max_tokens`: whole batch; 150 maximum: core 144 calls | `criteria."2_no_truncation"` (`:183`) |
| 3 | `:1005-1006` "Reply format: at most 7 malformed of 144 (under 5%) and at most 4 of 48 in any one arm." | core 144 and 48 per core arm | `criteria."3_reply_format"` (`:184-185`) |
| 4 | `:1007` "Arithmetic: at most 3 wrong answers among the admitted work events (at most 72)." | core 72 admitted | `criteria."4_arithmetic"` (`:186`) |
| 5 | `:1008-1009` "At least one order is **usable** under the order rule below. (Before change 18 this was one room-to-move screen on 6 `none` episodes; it is now read per order, on 3.)" | per order, 3 task sets each | `criteria."5_usable_order"` (`:187`) plus `order_rule`. **Stated deviation (author ruling, OD4):** the tool and `PILOT4_RUN_PACKET.md:118` also require zero `code` duplicates; `EP1.md:1026-1027` treats a non-zero `code` count as "the stop of section 12, not an input here", not part of criterion 5. The stricter rule is kept: it can only turn a pass into a fail. |
| 6 | `:1010` "The scripted floor scores exactly 0.25 and the oracle exactly 1.0 in each arm." | each arm, loopback fake server, no key | NOT in `pilot_clearance` (prints `"unavailable"`, `:188`). `lab/ep1_bracket_receipt.py` cannot serve as the check 6 tool for a fresh Pilot 4 bracket: it needs a `complete` terminal record and a fresh bracket ends `inconclusive` (`PILOT4_RUN_PACKET.md:170-172`). `PILOT4_RUN_PACKET.md` gives the direct call `ep1._bracket(<dir>, 0, ep1.REVIEW_FILE, None)`; `lab/ep1_bracket_receipt.py` audits pinned receipts (needs `--floor-sha256` and `--oracle-sha256`). Not run here. |
| 7 | `:1011-1012` "The ledger equals the Console for the batch, and every episode's prompts, replies and log are hand-read against the scores, with the reading recorded." | whole batch | PENDING, no command. Human reads the Console and reads the episodes by hand. `pilot_clearance` prints `"unavailable"` (`:189`). |

Check 7 substitution under OD4 (log, "Check 7 substitution (P6)"): the ledger's charges are compared with each response's `usage` and
`msg_` ids, and an independent agent hand-reads the 30 episodes' prompts, replies and logs against the scores. This is recorded as an
EP-1 section 19 deviation (`EP1.md:1302`, "filled in afterwards, never deleted"; the section is empty today and no entry is written by this
record). Check 7 stays PENDING, not passed, until a named human has read the Console and recorded the reading. The packet agrees:
"Do not mark it passed on the substitution alone." No human reviewer is named in any source read; none is invented here.
A pass on 1 to 6 does not clear EP-1: check 7 and the author's freeze are still required (`PILOT4_RUN_PACKET.md`).

Failure rule (`EP1.md:1013-1017`): "If a criterion fails, EP-1 is not cleared and nothing is tuned on the result here."

## 5. Manifest fields a later REVIEWED change would set

Current values in `lab/pilot4_preflight_manifest.py:145-147`: `"status": "awaiting_review"`,
`"author_review_status": "pending"`, `"selected_candidate": None`, `"execution_authorized_by_manifest": False`.
Also `reservation.pricing_review_status: "pending"` (`:118`).

A reviewed change would set:
- `selected_candidate` = `"array_only"` (one of the two keys of `CANDIDATES`, `lab/pilot3_prompt_replay.py:16-19`).
- `author_review_status` = a value for "reviewed". No source defines it; the only value in code is `"pending"`. The value is for
  the reviewing author to name; it is not invented here.

Effect on the pins (read from the manifest and its tests; no change made):
- The fields are literals in `build_manifest`; nothing computes them from other pins, and no code outside the test reads them.
  The digests `SCHEDULE_SHA256`, `PRICE_SHEET_SHA256`, `CANDIDATE_REQUEST_SHA256`, the Pilot 3 archive digests and
  `prospective_schedule_sha256` (over `schedule` only, `:150`) are unaffected.
- `lab/tests/test_pilot4_preflight_manifest.py:21-22` asserts `status == "awaiting_review"` and `selected_candidate is None`
  (`:23` asserts `execution_authorized_by_manifest is False`, `:31` `pricing_review_status == "pending"`). Changing `selected_candidate` alone breaks only test line `:22`; changing `status` would break `:21`. No test checks `author_review_status`, so any value would pass the tests as they stand. Update the tests in the same reviewed commit.
- `array_only`'s request digest `8d8c681b424b5772f9c6513ad368e58e36c0a2441bfd766f1b7a9e96fe0eb192` stays pinned; both candidates are still replayed.
- `execution_authorized_by_manifest` must stay False: the manifest authorizes no execution, and the pricing review, renewed coverage and
  independent re-gate remain separate gates.
- Drift to note: the runner already hard-wires `array_only` for batch `pilot4` (`team_claude.py:255-258`), while the manifest still says unselected.
  The manifest change records the author's decision; it does not change the runner.

## 6. Unverified

- No pilot4 run exists: criteria 1 to 6 have no Pilot 4 result; no pilot4 episode record shows `round2_wording_sha256`.
- Neither wording is shown to shorten live replies (offline replays hold replies fixed; temperature 1.0 differs per batch).
- Criterion 6 and check 7 are not checked by `pilot_clearance`; the bracket call was not run here.
- The `author_review_status` "reviewed" value, and any named human Console reader, are in no source.
- `EP1.md` has no heading numbered 13.16b and no Pilot 4 text; the criteria are quoted from the Pilot 2 block (`:997-1012`).
- `pilot_clearance` check 5's zero-`code`-duplicates requirement is a stated deviation (section 3); `ep1.order_gate` was read only by its comments.
- Check 1's "all attempts" is counted in the tool over episode turns (`pilot_clearance.py:143-144`), where retried attempts appear; aborted attempts that leave no turn are not counted by that line.
- The replay equivalence of `packet`/`array_only` request bytes was taken from the manifest's pinned digests, not re-run here.
- Open EP-1 items outside this record: price-sheet continuity for EP-1, M7 spend protocol, `MURMURATION_EP1_KEY` (per the log).
