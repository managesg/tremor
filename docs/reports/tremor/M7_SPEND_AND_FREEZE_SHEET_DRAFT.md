# M7 (Grover) spend figure and frozen-protocol sheet: DRAFT for the M7 author to sign

Status: DRAFT, 2026-11-26, written by the TREMOR lane from tracked files only. Nothing here is frozen,
admitted, approved or a run authority. No price, count or threshold is invented: where a source gives
none the cell says OPEN. Citations are `file:line` as read at HEAD `56c9189b` (working tree).

Keys: PROT = `prereg/M7-grover-protocol-draft.md`; GTS = `docs/reports/workplan-ep/Grover-topology-scripted.md`;
FFR = `docs/reports/tremor/FREEZE_FIELD_REGISTER.md`; OD = `docs/reports/tremor/OWNER_DECISION_M2_M7_D8_Pilot4_EP1.md`;
SPEND = `src/murmuration/spend.py`; WSP = `docs/reports/tremor/WSP_R1_COST_ESTIMATE.md`;
SHEET = `docs/reports/tremor/price-sheet-20261126.json`; GATE = `lab/tremor_admission_gate.py`.

## 1. Cost basis lines that exist in the sources

M7 has no spend figure, no sub-cap and no batch spec. `grep -i "m7\|grover" src/murmuration/spend.py`
returns nothing; `BATCH_SPECS` (SPEND:57-71) holds only `ep1`, `pilot`, `pilot2`, `pilot3`, `pilot4`,
`ar1` and `canary`.

| Cost kind | What the sources say for M7 | file:line |
|---|---|---|
| Hosted USD (provider calls, tokens) | OPEN (G-O10). "No Claude API figure or live allocation exists for Grover." Holder: Grover author proposes, spend reviewer checks, owner approves | PROT:216-218, PROT:244; OD:106 |
| Provider calls (count) | OPEN. Per-call, token and call-count caps are G-O10 | PROT:244, PROT:284 |
| Tokens (per call) | OPEN for M7. The only per-call caps in code are the repo-wide 2,000 input and 300 output (not an M7 allocation) | SPEND:52 (`PER_CALL_INPUT_TOKENS, PER_CALL_OUTPUT_TOKENS`); OD:116 (its own `spend.py` line numbers are stale) |
| Model whose rates would apply | Decided text (proposal for the freeze, not a freeze): `claude-haiku-5-5`, direct key, temperature 1.0 sent, thinking disabled, 3 workers; "If EP-1's frozen values differ, M7 follows them" | PROT:274 |
| Hosted cost per call, if that model is used | Rates exist on the sheet (USD per million tokens, haiku-5-5: input 0.1, output 0.5, cache_read 0.01, cache_write_5m 0.125, cache_write_1h 0.2). No M7 call or token count exists, so no M7 cost can be computed | SHEET:7-14 |
| GPU-hours | OPEN (G-O11). Only recorded figure is a share of 9.4 GPU-hours pooled with the adapter, replication and controller, inside the funded 70 GPU-hours. The M7 share is not stated | PROT:223-225, PROT:245; OD:106 |
| CPU time | The offline scripted replay (no model call, no network, no spend) is CPU only. No CPU-time figure is recorded in the sources | PROT:172-175, PROT:196; GTS:3 |
| Scripted cost unit | 32 abstract cost units, not dollars or tokens. Mapping to model calls and tokens is OPEN (G-O10) | PROT:96-98; GTS:4-5, GTS:177-179 |
| Economic stop | OPEN (G-O10). "No M7 figure exists" | PROT:153 |
| Shared hosted cap | USD 10 total across M2, M7 and D8; running total USD 0.00 recorded in the admission record, no call made. It counts Tremor calls only, not the whole pinned directory | PROT:207-211; FFR:39-45 |
| Code hard cap | `HARD_CAP_USD = 10.0` across every ledger in the pinned directory; no argument raises it. Not an M7 allocation | SPEND:48; PROT:154-155 |
| EP-1 share vs M7 | PROT records that the EP-1 allocation text and the shared-cap text do not reconcile, so no M7 sub-cap is taken from either | PROT:212-215 |
| Cap is soft | A direct API key has no provider-enforced cap; a Console workspace limit of USD 10 or less is recommended and is an owner action | PROT:226-227 |
| Price sheet | The sheet pinned earlier lapsed 2026-11-24. The 2026-11-26 sheet (sha256 `2edb8b5c...`) was fetched; the ruling recorded for it covers Pilot 4 only. M7 still needs its own window instants and pricing-coverage re-ruling | PROT:219-222, PROT:287 |

Kinds M7 uses per the protocol: the model run (post-EP-1 transfer) would use hosted provider calls and
tokens (PROT:274 names a hosted model) and GPU-hours (PROT:223-225); the offline replay uses CPU only.
How much of each is OPEN. No figure above is a plan, a reservation or a recommendation.

### Spend figure to be signed (all cells blank until the M7 author fills them)

| Line | Value | Source or holder |
|---|---|---|
| `hosted_usd_plan` | OPEN | Grover author proposes; spend reviewer checks (PROT:244) |
| `hosted_usd_stop` | OPEN | same |
| Calls cap | OPEN | same |
| Tokens cap (input+output) | OPEN | same |
| `reserved_gpu_hours` | OPEN | Resource reviewer measures; owner admits (PROT:245) |
| Expected resources | OPEN | same |
| Window (UTC) | OPEN | Owner names; PROT:287 |

## 2. Freeze fields (gate schema `GATE:38-45`; register FFR:136-160)

Gate refusals: empty presence-only field `GATE:231-232`, empty protected-input custodian `GATE:264-265`,
admission number above the freeze number `GATE:284` (FFR:13-15 cites older line numbers). The 14 empty fields for
M7 are the 3 numbers, `protected_inputs` and the 10 presence-only fields (FFR:138-141).

| Field | Value or command | Holder if OPEN |
|---|---|---|
| `batch` | Skeleton argument, needs a bare batch id (`lab/tremor_freeze_skeleton.py:138`). FFR used `M7-reg`. The real batch id: OPEN | M7 author |
| `protocol_path` | `prereg/M7-grover-protocol-draft.md` (written by the skeleton) | none |
| `protocol_sha256` | From the command `git show <commit>:prereg/M7-grover-protocol-draft.md \| sha256sum` at the frozen commit (the skeleton hashes the blob at HEAD, `lab/tremor_freeze_skeleton.py:47-51`). Working-tree file today hashes `2afad384f75a45dd32fd13932f57450e797d3d1111f602ffc17f20cfafa293da` (`sha256sum`, 2026-11-26); the file is still being edited (12a added), so this is not the freeze value | value comes from the command at the pinned commit |
| `commit` | `git rev-parse --verify HEAD^{commit}` (skeleton `:41-44`). Which commit to pin is the owner's decision (G-O16); HEAD today `56c9189b3a3d46ce036923c6173824c8db7e6a50` is a placeholder, and the gate floor is `c0daf55` (`GATE:36`) | owner (commit or lock) |
| `tree` | `git rev-parse <commit>^{tree}` (skeleton `:44`) | from command |
| (non-field row, not a gate key or FFR field) harness commit | The code tree hash and config hash at the candidate are not recorded (PROT:250, PROT:298). Command for the commit once pinned: `git rev-parse <commit>`. Which harness commit M7 runs is OPEN | PC (command); integration owner and owner approve |
| `protected_inputs` (5: manifest envelope, private blocks, split audit, opening location, custody receipt) | Paths and custodian OPEN. `sha256` is computed by the gate from file bytes once sealed (FFR:22-23) | custodian seals; owner appoints (G-O1, G-O7, G-O8, G-O9) |
| `config_hash` | Method exists `src/murmuration/manifest.py:51`; not computable until config is fixed; GTD, GCC, SE and the `runs/` items are untracked | integration owner; owner approves commit (G-O16) |
| `model_snapshot` | Decided text at PROT:274 (`claude-haiku-5-5`, direct key, temp 1.0, thinking disabled), conditional on EP-1's frozen values (EP-1 not frozen, G-O12). Snapshot id pin: OPEN | owner (model, spend); M7 author |
| `task_family_revision` | OPEN. Nominal mapping only; nearest source is the G-O1 generator revision (FFR:151) | M7 author; custodian |
| `scorer_ids` | OPEN (G-O7). No appointment exists | owner appoints; custodian |
| `contrasts` | Structure exists (single primary, conjunction of three regime tests, PROT:265); numeric gain, kill bound and predicted effect OPEN (PROT:271) | M7 author and independent reviewer |
| `stopping_rules` | Statistical half decided: fixed n, no interim look, one analysis (G-O5, PROT:273). Aborted-block and stopped-pair policy decided (G-O4, PROT:272). Order policy decided (G-O14, PROT:275). Economic stop OPEN (G-O10); block counts OPEN (G-O3); order seed value OPEN (G-O1) | M7 author; owner approves |
| `expected_and_max_resources` | OPEN (G-O3, G-O10, G-O11) | resource and spend reviewers; owner |
| `approval_review_evidence` | Owner words "Paid calls for up to $10 for Tremor" (not a one-use admission, PROT:228-229). Independent review: none (G-O18) | independent reviewer; owner |
| `d1_basis` | No protocol section found (FFR:157). D1 is at `docs/reports/ep-approvals.md:166` | M7 author and owner decide |
| `inherited_pins` | No section found; EP-1 clearance record does not exist (G-O12) | M7 author; EP-1 author |

The skeleton command (read only, writes to `--out`; run by PC or the author, not part of this sheet):
`python3 lab/tremor_freeze_skeleton.py prereg/M7-grover-protocol-draft.md --batch <id> --out <path>`
(arguments `lab/tremor_freeze_skeleton.py:136-141`).

## 3. Who can do what

Lane work (repo files only, already done or doable by the line author):
- Transcribe decided text into the freeze record: G-O2 structure, G-O4, G-O5, G-O6, G-O14 (PROT:254-275).
- Copy the owner words and the 2026-11-26 delegation quote (PROT:256-257).
- Run the offline scripted replay and focused tests listed at PROT:177-189 (no spend, no network). Digests
  there were not recomputed for this draft (PROT:196-198).
- Maintain this sheet and the register. None of this sets a number.

Only the M7 author can give: the hosted USD plan and stop, calls cap, tokens cap, the mapping of the 32 abstract
units to calls (G-O10); the block count after a variance pilot (G-O3); the meaningful gain, kill bound and predicted
effect (G-O2 residual); the order seed (G-O1); `task_family_revision`; `d1_basis`.

Only the custodian can give: sealed protected inputs and their sha256, the authenticated pre-execution custody
receipt, quotas from the private inventory (G-O1, G-O8, G-O9); scorer IDs once appointed.

Only the owner can give: appointment of the custodian and scorer (G-O7); the model tier and spend decision (G-O6,
G-O10); the GPU-hours share (G-O11); the commit or lock (G-O16); a one-use admission bound to batch and UTC window
(PROT:228-229); the Console workspace limit (PROT:226-227).

Only the PC (integration owner host) can give: the pinned commit, tree and `protocol_sha256` from `git`/`sha256sum`
at that commit; a tracked archive of the untracked GTD, GCC, SE and `runs/` items (G-O16, after owner approval);
the native M7 runner build (G-O17); the price-sheet refetch and re-ruling, a network step (G-O13).

Others: independent reviewer (G-O15, G-O18); EP-1 author and owner (G-O12, EP-1 completion and Pilot 4 clearance,
the stated prerequisite, PROT:40, OD:104-106).

## 4. TREMOR USD 10 envelope: recorded facts only

| Item | Figure | file:line |
|---|---|---|
| Owner words, shared cap for M2, M7 and D8 | "Paid calls for up to $10 for Tremor"; USD 10 total | PROT:207, PROT:228; FFR:39-43 |
| Recorded Tremor running total at admission | USD 0.00, no call made (as stated in the admission record) | PROT:207-208 |
| Prior recorded ledger spend (canary, pilot, pilot2, pilot3) | USD 0.0413027 | OD:56-57 section 3.3 |
| Pilot 4 cap | USD 0.25, 260 calls, 598,000 tokens | SPEND:69; OD:50-51 |
| EP-1 cap | USD 5.00, 500 calls, 1,250,000 tokens (canary inside) | SPEND:59; OD:53-54 |
| Pilot 4 plus EP-1 caps | USD 5.25 | OD:57-58; WSP:19 |
| Arithmetic on those facts: USD 10 minus USD 5.25 | USD 4.75 (caps only; excludes the prior ledger spend and any M2, D8, `ar1` or M7 line) | arithmetic from the two rows above |
| `ar1` batch cap, present in code | USD 3.00, 400 calls; refuses to open until `ep1` settles | SPEND:70 |
| WSP-R1 estimate (Opus 5.5 assumed, recorded tokens, not billed) | USD 6.08 (5-minute cache write) to USD 9.04 (1-hour cache write) | WSP:9-13 |
| WSP-R1 ledger status | Ran 2026-11-24, before the USD 10 approval and on a separate model ledger, so the estimate says it is not counted against it; the owner decides, and at the upper estimate Pilot 4 plus EP-1 would not both fit if it were counted | WSP:19 |
| M7 line inside the envelope | none; no M7 sub-cap is taken from EP-1 or the shared cap | PROT:212-215 |

Nothing in this table is an approval. The USD 4.75 line is subtraction of two recorded caps and is not a
reservation for M7, nor evidence that M7 fits; the M7 figure is OPEN (G-O10).

## 5. Signature block (for the M7 author; blank)

- [ ] Section 1 spend figure cells filled, each with a source or "OPEN".
- [ ] Section 2 OPEN fields assigned to a named holder.
- [ ] Author: ______________________  Date (UTC): ______________________

Signing this sheet does not freeze the protocol, admit a batch or approve spend (PROT:308).
