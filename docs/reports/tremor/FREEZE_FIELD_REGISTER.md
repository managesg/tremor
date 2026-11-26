# Freeze field register: L2-C, L3-C, L4-C, M7

Read-only register of what still blocks each freeze record. No value is filled and no number is
set here. Regenerated 2026-11-26 at HEAD `19ce7b9274ad3c31ffec8fa002ab0e335b81ea76`, after the coordinator fixed `missing()`. Nothing here is an admission, an
approval or a run authority.

## How this was produced

`lab/tremor_freeze_skeleton.py` (fixed version, which reads each protocol's own headings) was re-run per
protocol (batch ids `L2C-reg`, `L3C-reg`, `L4C-reg`, `M7-reg`, no `--input`; skeletons written to a
temp directory that the script removed with `shutil.rmtree`, checked gone; nothing was written into the
repo). `missing()` again returned 14 entries for each of the four protocols. The schema is
`lab/tremor_admission_gate.py:38-45` (`_FREEZE_KEYS`, `_PRESENCE_ONLY`); the gate refuses an empty
presence-only field at `:182-184`, an empty protected-input custodian at `:216-217`, and an admission
number above the freeze number at `:234-236`.

The 14 entries per protocol: 3 numbers (`reserved_gpu_hours`, `hosted_usd_plan`, `hosted_usd_stop`),
`protected_inputs`, and 10 presence-only fields (`approval_review_evidence`, `config_hash`,
`contrasts`, `d1_basis`, `expected_and_max_resources`, `inherited_pins`, `model_snapshot`,
`scorer_ids`, `stopping_rules`, `task_family_revision`). Once `protected_inputs` lists N entries,
`missing()` adds one `protected_inputs[i].custodian` entry per input (N is named in each table below).
`sha256` per input is computed by the gate from the file bytes (`_input_sha`), so it exists only
after the custodian seals a file.

Section references below are the fixed skeleton's output, "section 15 item N" meaning the numbered item
in that protocol's "What the freeze record must contain". Four field and protocol pairs print
"section not found", and the tables mark them as such:

| Gate field | Protocols with "section not found" |
|---|---|
| `inherited_pins` | L3-C, L4-C, M7 (only L2-C has it, section 15 item 8) |
| `d1_basis` | M7 (L2-C finds item 7; L3-C and L4-C find item 8) |

So two gate fields, `inherited_pins` and `d1_basis`, have no matching protocol item for some protocols,
yet the gate requires both non-empty for every batch. In M7, `task_family_revision` is mapped by the
skeleton to section 13 item 4, but that item's text does not name a task-family revision (it lists model
snapshot, scorer IDs, contrasts, stopping rules and resources); treat that mapping as nominal.

**Effective hosted cap.** The gate checks admission hosted numbers against the caller's `hosted_cap`
(`lab/tremor_admission_gate.py:239-241`), which is the owner's shared USD 10, not the protocol's own
stop. The owner's words are "Paid calls for up to $10 for Tremor", USD 10 total across M2, M7 and D8
(`docs/reports/tremor/ADMISSION_RECORD_20261125.md:3`), and the record states each line's later run is
"within the remaining shared USD 10" (`:28-30`). The protocol hosted figures (USD 9/15, 16/24, 33/40)
are drafts that cannot exceed that cap at admission, so they cannot be copied without an owner
reconciliation.

Holder vocabulary: **line author**, **custodian** (evaluator custodian, independent of the author),
**independent reviewer**, **owner (spend)**, **owner (commit or lock)**, **pilot** (the approved
variance pilot, not released: `docs/reports/tremor/OWNER_DECISION_protected_admissions_M3R3_M4_M9.md:136`
and `docs/reports/tremor/ADMISSION_RECORD_20261125.md:11`), **trainer** (only L4-E adapter, outside this
register). No protocol names a person; roles are what the repo gives. "Named" below means the
protocol row names the role.

---

## L2-C (`prereg/R2-L2-C-protocol.md`; freeze record section 15, OPEN table section 14)

14 empty fields; 9 protected inputs named at `:323` (planted note, clean twin, trigger-only source,
reference manifest, evaluator inventory, detached label tape, chain ID splits, seed map, ranking
pins), so 9 custodian entries once listed.

| Field | Section / OPEN id | Named holder | In repo? | Unblocks |
|---|---|---|---|---|
| `reserved_gpu_hours` | 13 (`:280`); 15 | Owner (spend) | Ceiling 6 exists: `prereg/R2-L2-C-protocol.md:280`, `docs/reports/workplan-ep/R2-R4-protocol-readiness.md:19`. The reserved value is the author's and owner's choice at or under it | Line author picks the value; owner confirms (P:942 per `:285`: only the owner changes a cap) |
| `hosted_usd_plan` | 13 (`:282`); L2-O13 (`:306`) | Owner (spend) | Draft 9 at `:282`, but a hosted tier and snapshot do not exist (L2-O13, `:366`) and the shared owner cap is USD 10 (`ADMISSION_RECORD_20261125.md:3,28`) | Owner decides whether any hosted tier runs, then the plan figure |
| `hosted_usd_stop` | 13 (`:281`); L2-O13 | Owner (spend) | Draft 15 at `:281` exceeds the owner's USD 10 (`ADMISSION_RECORD_20261125.md:28`) | Owner reconciliation of 15 against 10 shared with M2, M7, D8 |
| `protected_inputs` (9 custodians, 9 sha256) | 15 item 3 (`:323`); L2-O5 (`:298`), L2-O7 (`:300`) | Line author writes the planted note, clean twin, trigger-only source and the five fraction values and store size; custodian seals; custodian holds chain IDs and seed map | No sealed bytes. Closest repo sources: `docs/reports/workplan-ep/L2-reference-custody.md`, `lab/l2c_detached_scoring.py:86-113`. No sha256 exists | Author finishes L2-O5; custodian seals files and fixes L2-O7; the gate then computes sha256 |
| `config_hash` | 15 item 2 (`:319`); L2-O14 (`:307`) | Line author, after owner approves the commit | Method exists: `src/murmuration/manifest.py:51` (`config_hash`). The config itself is not fixed: depends on L2-O5, L2-O9, L2-O10, L2-O17 to L2-O19 and on the pinned commit | Candidate commit at or after `c0daf55` approved by the owner; all config numbers fixed |
| `model_snapshot` | 15 item 4 (`:326`); L2-O13 (`:306`, `:366`) | Owner (tiers and spend); line author | Local tier only: Qwen3.5-4B revision `851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a` at `docs/reports/tremor/OWNER_DECISION_protected_admissions_M3R3_M4_M9.md:47`, cited in `prereg/R2-L2-C-protocol.md:366`. Hosted tier and snapshot: none | Owner names any hosted tier and snapshot, or the freeze registers local only |
| `task_family_revision` | 15 item 4; L2-O13 (`:306`) | Line author | None in repo (`:366` lists it as missing) | Line author defines and pins the task family; custodian confirms |
| `scorer_ids` | 15 item 4; L2-O5 | Custodian (evaluator independent of the author) | None as IDs. "Three scorers; any disagreement voids a run" (`prereg/R2-L2-C-protocol.md:113`); a scorer agreement receipt is required (`:251`), none recorded. `lab/l2c_detached_scoring.py` exists | Custodian names scorers and issues the agreement receipt |
| `contrasts` | 15 item 4; sections 2, 7; L2-O19 (`:312`) | Line author | Structure exists: primary conjunction (section 2, `:28-52`; L2-O2, L2-O3 closed). Numeric bounds for C2, C3, K1 to K3 and the share s do not (L2-O19) | Line author proposes bounds, owner approves at freeze |
| `stopping_rules` | 15 item 4; L2-O11 (`:357`), L2-O17 (`:310`) | Line author; owner for caps | Statistical half exists: fixed n, one analysis, no interim look (`:357`). Economic stop 6 GPU-hours or USD 15 (`:357`, subject to the USD 10 note). Cap on missing runs per arm: no value (L2-O17) | Line author sets L2-O17; owner reconciles hosted stop |
| `expected_and_max_resources` | 15 item 4; L2-O10 (`:303`) | Pilot (owner releases), line author computes, reviewer checks | Maximum: ceilings at `:280-282`. Expected: none; "Memory and runtime per line: no figure in the repo" (`:287`, citing ADM:107) | Owner releases the variance pilot; line author computes n, E, K, SD, ICC |
| `approval_review_evidence` | 15 item 6 (`:330`); L2-O16 (`:309`) | Independent reviewer; owner for words | Owner words exist verbatim: `ADMISSION_RECORD_20261125.md:3`; the 2026-11-26 delegation is quoted at `prereg/R2-L2-C-protocol.md:87`. Independent review: none; the first review REJECTED the draft and a new one is "still needed" (`:309`). Owner approval of the commit is "not recorded" (`:307`) | Independent reviewer accepts the final protocol; owner approves the commit |
| `d1_basis` | 15 item 7 (`:332`) | Line author quotes; owner ratified | Exists: `docs/reports/ep-approvals.md:166` (D1) and ratification at `prereg/R2-L2-L3-L4-scope.md:31` | Line author copies both exactly (repo files only) |
| `inherited_pins` | 15 item 8 (`:333`); L2-O13 | Custodian (re-pin for this batch); owner for the M3 admission | Values exist: Qwen revision above and manifest sha256 `9b70e85c464f8dddbe1c6094832f51043a85fa7dcdf281e0cb81aa0d2d4d6ea6` at `OWNER_DECISION_protected_admissions_M3R3_M4_M9.md:47`. The M3 R3-L2 admission they come from does not exist (`ADMISSION_RECORD_20261125.md:9`: no) | Custodian re-pins for this batch; M3 R3-L2 admission or an explicit statement of what is inherited |

---

## L3-C (`prereg/R2-L3-C-protocol.md`; freeze record section 15, OPEN table section 14)

14 empty fields; 8 protected inputs named at `:336-338` (view definitions, toy monitor and stand-in,
calibration failure set, clean threshold set, clean and failure assessment sets, joint miss table pins,
split IDs, seed map), so 8 custodian entries if the assessment sets count as one. The skeleton does
not cover section 15 items 4, 9, 10 and 11 (primary lock, null-ratio procedure, owner lock line and
custodian attestation, conservative-arm choice); they are separate blockers of the same freeze.

| Field | Section / OPEN id | Named holder | In repo? | Unblocks |
|---|---|---|---|---|
| `reserved_gpu_hours` | 13 (`:295`) | Owner (spend) | Ceiling 4: `prereg/R2-L3-C-protocol.md:295`, `R2-R4-protocol-readiness.md:20` | Line author picks value at or under 4; owner confirms |
| `hosted_usd_plan` | 13 (`:297`); L3-O13 (`:320`) | Owner (spend) | Draft 16 at `:297` exceeds the owner's shared USD 10 (`ADMISSION_RECORD_20261125.md:29`) | Owner reconciliation against USD 10 shared with M2, M7, D8 |
| `hosted_usd_stop` | 13 (`:296`); L3-O13 | Owner (spend) | Draft 24 at `:296`, same conflict | Same |
| `protected_inputs` (8 custodians, sha256) | 15 item 3 (`:336`); L3-O5 (`:312`), L3-O6 (`:313`), L3-O7 (`:314`) | Line author (k, view definitions, call budget, pool generation and sizes, stand-in); custodian seals and holds splits and seeds | No numbers: "k and the call budget; no number in the repo" (`:401`). No sealed pools | Author fixes L3-O5, L3-O6; custodian seals pools and fixes L3-O7 |
| `config_hash` | 15 item 2 (`:332`); L3-O8 (`:315`), L3-O14 (`:321`) | Line author; owner approves commit | Method `src/murmuration/manifest.py:51`; harness at `4d264a5` or later (`:333`). Config not fixed (L3-O5, L3-O9, L3-O10, L3-O17) | Owner approves commit at or after `c0daf55`; config numbers fixed |
| `model_snapshot` | 15 item 5 (`:340`); L3-O13 (`:320`) | Owner (tiers and spend); line author | None. L3-C protocol states no pin (the Qwen pin in `OWNER_DECISION_protected_admissions_M3R3_M4_M9.md:47` is M3 R3-L2's, not named here) | Owner names tiers and snapshots |
| `task_family_revision` | 15 item 5; L3-O13 | Line author | None | Line author defines and pins; custodian confirms |
| `scorer_ids` | 15 item 5; section 5 truth rule (`:105`); sanity check 4 (`:265`) | Custodian | "Three scorers; any disagreement voids a run (P:165-166)" (`:105`). Scorer IDs and the agreement receipt (`:265`): none | Custodian names three scorers and issues the receipt |
| `contrasts` | 15 item 5; sections 2, 9; L3-O1 (`:308`), L3-O17 (`:324`), L3-O18 (`:325`) | Line author; owner for the primary lock | Structure exists (section 2; L3-O2, L3-O3, L3-O4, L3-O12 closed). Primary lock (section 16): owner statement not on record (`:401`). Conservative arm vacuous until L3-O18 is settled | Owner issues the lock line with message id and UTC time; author settles L3-O18 |
| `stopping_rules` | 15 item 5; L3-O11 (`:318`, D2 `:394`), L3-O10 (`:317`) | Line author | Statistical: fixed n, one analysis, no interim look (`:318`, `:394`). Economic: ceilings at `:295-297` subject to the USD 10 note. Near-zero-loss rule (`:397`): no number needed. n and the cap on the excluded share: no value (L3-O10, L3-O17) | Pilot for n; author sets bootstrap B and exclusion cap |
| `expected_and_max_resources` | 15 item 5; L3-O10 (`:317`) | Pilot (owner releases), line author, reviewer | Maximum from `:295-297`. Expected: none (`:301`) | Owner releases pilot; author computes K, n, ICC, discordance |
| `approval_review_evidence` | 15 item 7 (`:344`); L3-O16 (`:323`), L3-O8 (`:315`) | Independent reviewer; owner for words | Owner words as for L2-C. Independent review: none. Harness built at `1dabf53` but "no ACCEPT verdict on it is recorded" (`:401`). Owner approval of the commit not on record (`:399`) | Independent reviewer; owner approves commit |
| `d1_basis` | 15 item 8 (`:346`) | Line author quotes | `docs/reports/ep-approvals.md:166`; `prereg/R2-L2-L3-L4-scope.md:31`; the D1 scope statement at `prereg/R2-L3-C-protocol.md:77` | Line author copies exactly (repo files only) |
| `inherited_pins` | section not found | Line author decides; custodian | No inherited item in section 15 (items 9 to 11 are different content). No L3 pin exists | Line author states what the batch inherits, or the gate field gets a recorded "none" with a reason, which is a person's call |

---

## L4-C (`prereg/R2-L4-C-protocol.md`; freeze record section 15, OPEN table section 14)

14 empty fields; 8 protected inputs named at `:341-343` (day and night trace chains, old and new
stores with source IDs, measured compression ratios per setting, ladder calibration, close-night truth
labels, paired cost records, split IDs, seed map), so 8 custodian entries. Extra blockers outside the
skeleton: item 2a (proposal commit `1dabf53` and the sha256 of `git show 1dabf53:docs/PROPOSAL-RESIDENCY-V3.md`),
item 2b (code hash of six steering functions and their measured charges), item 4 (two-setting lock),
item 9 (L4-E only, separate record).

| Field | Section / OPEN id | Named holder | In repo? | Unblocks |
|---|---|---|---|---|
| `reserved_gpu_hours` | 13 (`:292`); L4-O14 (`:320`) | Owner (spend) | Ceiling 12: `prereg/R2-L4-C-protocol.md:292`, `R2-R4-protocol-readiness.md:21`. Split among C, B, A work: none (L4-O14) | Owner splits the 12 GPU-hours |
| `hosted_usd_plan` | 13 (`:294`); L4-O14 | Owner (spend) | Draft 33 at `:294` exceeds the owner's shared USD 10 (`ADMISSION_RECORD_20261125.md:30`) | Owner reconciliation and split |
| `hosted_usd_stop` | 13 (`:293`); L4-O14 | Owner (spend) | Draft 40 at `:293`, same conflict | Same |
| `protected_inputs` (8 custodians, sha256) | 15 item 3 (`:341`); L4-O6 (`:312`), L4-O7 (`:313`), L4-O5 (`:311`) | Line author (daily error rate, nights, store size, note inventory, compression index and calibration); custodian holds calibration chains, splits, seeds | No value: "no value in P or the repo; P:531 gives six nights for A only" (`:434`). No sealed files | Author fixes L4-O5 and L4-O6; custodian seals and fixes L4-O7 |
| `config_hash` | 15 item 2 (`:332`); L4-O9 (`:315`), L4-O17 (`:323`) | Line author; owner approves commit | Method `src/murmuration/manifest.py:51`. Harness `lab/l4c_harness.py` is tracked and built (`d11b32c`). Config unfixed (L4-O2, O5, O6, O8, O13, O14) | Owner approves commit at or after `c0daf55`; native launcher built (L4-O17) |
| `model_snapshot` | 15 item 5 (`:346`); L4-O16 (`:322`), L4-O2 (`:429`) | Owner (tiers and spend); line author | None; `:429` lists the snapshot serving the token meter as OPEN | Owner names tiers and snapshots |
| `task_family_revision` | 15 item 5; L4-O16 | Line author | None | Line author defines and pins; custodian confirms |
| `scorer_ids` | 15 item 5; truth rule (`:135`); sanity check (`:252`) | Custodian | "Three scorers; any disagreement voids a run" (`:135`). IDs and agreement receipt: none | Custodian names scorers and issues the receipt |
| `contrasts` | 15 item 5; section 2; L4-O8 (`:314`), L4-O5 (`:311`), L4-O13 (`:319`) | Line author proposes; owner approves at freeze | Structure exists (six conjuncts; L4-O1, O3, O4, O12, O15, O18 closed or half closed). Open: numeric meaning of "ties" and "matches", C3 minimum advantage, tie rule, fitting loss and `tol` (`:428-431`) | Line author proposes; owner approves; section 16 lock line |
| `stopping_rules` | 15 item 5; L4-O11 (D4 `:415`, `:198`) | Line author | Statistical: fixed n, no interim look (`:198`, `:415`). Economic: ceilings `:292-294` subject to the USD 10 note; truncated-batch rule exists (`:449`). n: OPEN (L4-O10) | Pilot for n |
| `expected_and_max_resources` | 15 item 5; L4-O10 (`:316`), L4-O14 | Pilot (owner releases), line author, reviewer; owner for the split | Maximum from `:292-294`. Expected: none (`:299`) | Owner releases pilot; author computes; owner splits |
| `approval_review_evidence` | 15 item 7 (`:350`); L4-O19 (`:325`), L4-O9 (`:315`) | Independent reviewer; owner for words | Owner words as for L2-C. Independent review of the protocol: none. For the harness: ACCEPT "cited from the line author's report, and no matching record was found in `DECISION_LOG.md`" (`:315`, `:453`) | Reviewer record added to `docs/reports/tremor/DECISION_LOG.md`; independent protocol review |
| `d1_basis` | 15 item 8 (`:352`); L4-O1 flag (`:422`) | Line author quotes; owner for the L4-D scope record | `docs/reports/ep-approvals.md:166`; `prereg/R2-L2-L3-L4-scope.md:26` (excludes L4-D, cited at `:352`) and `:31`. The D1 flag paragraph after the D table is at `:422` | Line author copies exactly (repo files only) |
| `inherited_pins` | section not found (item 9 is L4-E only) | Line author decides; custodian | None | Line author states what is inherited or records a reason |

---

## M7 (`prereg/M7-grover-protocol-draft.md`; freeze record section 13, OPEN table section 12 and 12a)

14 empty fields; 5 protected inputs named at `:299-300` (manifest envelope, private blocks, split
audit, opening location, custody receipt), so 5 custodian entries. M7 has no section 13 resource
table, and no M7 line appears in `R2-R4-protocol-readiness.md`. Section 13 item 7 (EP-1 clearance
record, G-O12) is outside the skeleton.

| Field | Section / OPEN id | Named holder | In repo? | Unblocks |
|---|---|---|---|---|
| `reserved_gpu_hours` | 11 (`:223-225`); G-O11 (`:245`, `:285`) | Resource reviewer; owner | No M7 figure. The only number is a 9.4 GPU-hour share pooled with the adapter, replication and controller (EPL:489; OD:106, cited `:223-224`) | Resource reviewer measures; owner admits a share |
| `hosted_usd_plan` | 11 (`:216-218`); G-O10 (`:244`, `:284`) | Grover author proposes; spend reviewer; owner approves | None: "No Claude API figure or live allocation exists for Grover" (`:216-217`). Shared cap USD 10 (`:207`); EP-1 share unreconciled (`:212-215`) | Named allocation and cost estimate; spend reviewer check |
| `hosted_usd_stop` | 11; G-O10 | Same | None | Same, plus per-call, token and call-count caps and the mapping of 32 abstract units to calls |
| `protected_inputs` (5 custodians, sha256) | 13 item 3 (`:299`); G-O1 (`:235`, `:281`), G-O7 (`:241`), G-O8 (`:242`), G-O9 (`:243`) | Protocol author proposes; custodian holds files and issues the receipt; owner appoints the custodian | None sealed. GCC and GTD are untracked (`:18-19`). "No such record in the repo" (`:235`) | Owner appoints custodian and scorer; custodian seals and issues receipt |
| `config_hash` | 13 item 2 (`:298`); G-O16 (`:250`, `:289`) | Integration owner; owner approves commit | Method `src/murmuration/manifest.py:51`. "code tree hash and config hash not recorded" (`:250`); GTD, GCC, SE and the `runs/` items are untracked | Owner approves a commit that tracks them |
| `model_snapshot` | 13 item 4 (`:301`); G-O6 (`:240`, `:274`) | Owner (model and spend); protocol author | Decided text: `claude-haiku-5-5`, direct key, no alias, temperature 1.0 sent, thinking disabled (`:274`); source `prereg/EP1.md:20`, `:358-360`, `:387-394`. Conditional: "If EP-1's frozen values differ, M7 follows them" and EP-1 is not frozen (G-O12) | EP-1 freeze; owner confirms |
| `task_family_revision` | 13 item 4 by the skeleton, but that item's text does not name it; nearest source is G-O1 generator revision (`:281`) | Protocol author; custodian | None: "Split-rule revision and digest, generator revision, configuration digest" are missing (`:281`) | Author fixes the mapping of this gate field to G-O1; custodian records the revision |
| `scorer_ids` | 13 item 4; G-O7 (`:241`, `:283`) | Owner appoints; custodian | None: "no source names who appoints" (`:241`) | Owner appoints an independent scorer; ID recorded |
| `contrasts` | 13 item 4; G-O2 (`:236`, 12a `:265-269`) | Protocol author and independent reviewer | Structure exists: single primary conjunction of three regime tests, secondaries listed (`:265`). Numeric residual open: meaningful gain, kill bound, predicted effect (`:271`) | Approved M7 variance pilot plus the author's E and K |
| `stopping_rules` | 13 item 4; G-O5 (`:273`), G-O10 | Protocol author; owner approves | Statistical: fixed n, no interim look, one analysis (`:273`). Economic stop: OPEN (G-O10). Block count: OPEN (G-O3, `:282`) | Same as `hosted_usd_*`; pilot for n |
| `expected_and_max_resources` | 13 item 4; G-O3, G-O10, G-O11 | Resource and spend reviewers; owner | None for either | Same as the three number fields |
| `approval_review_evidence` | 13 item 6 (`:305`); G-O18 (`:252`, `:291`) | Independent reviewer; owner | Owner words: "Paid calls for up to $10 for Tremor" (`ADMISSION_RECORD_20261125.md:3`, not a one-use admission, `:229`); the 2026-11-26 delegation is quoted at `:256-257`. Independent review: none | Independent reviewer accepts protocol including 12a |
| `d1_basis` | section not found | Line author and owner decide | M7 does not cite D1 anywhere (grep of `prereg/M7-grover-protocol-draft.md` for "D1", "benign" and "defensive" finds no scope statement); D1 is at `docs/reports/ep-approvals.md:166` | Line author and owner decide whether D1 applies or what basis the gate field carries |
| `inherited_pins` | section not found (13 item 7 is the EP-1 clearance record) | Line author; EP-1 author | No pins to inherit; the EP-1 clearance record does not exist (G-O12, `:246`, `:286`) | EP-1 completion and Pilot 4 clearance |

---

## What the line author can fill today (repo files only)

Each item is a transcription or a computation from tracked files. None sets a new number. Items marked
(check) need the author to confirm the value is a ceiling and not a reservation.

1. `protocol_sha256`, `commit`, `tree`, `protocol_path`, `batch`: already written by the skeleton at HEAD
   `1838abe`. The commit to pin is the owner's decision (L2-O14, L3-O14, L4-O17, G-O16), so the skeleton's
   HEAD commit is a placeholder, not a pin.
2. `d1_basis` for L2-C, L3-C, L4-C: quote `docs/reports/ep-approvals.md:163-166` and
   `prereg/R2-L2-L3-L4-scope.md:31` exactly. L4-C also quotes the scope record that excludes L4-D.
3. `contrasts` (structure only) and the statistical half of `stopping_rules` (fixed n, one analysis, no
   interim look) for all four: transcribe from the protocol sections cited above. The numeric bounds and
   n stay OPEN; the gate checks only that the field is non-empty, so the text must say which bounds are
   still open rather than imply they are fixed.
4. `reserved_gpu_hours` ceilings (check): L2-C 6, L3-C 4, L4-C 12, from section 13 and RR:19-21. M7: none.
5. The maximum half of `expected_and_max_resources` (ceilings at the same lines). The expected half cannot be filled.
6. `model_snapshot` for the local tier of L2-C (Qwen3.5-4B revision `851bf6e8...` at
   `OWNER_DECISION_protected_admissions_M3R3_M4_M9.md:47`) and, conditionally, M7 (`claude-haiku-5-5`, `:274`).
7. `inherited_pins` for L2-C: the Qwen revision and manifest sha256 `9b70e85c...` at
   `OWNER_DECISION_protected_admissions_M3R3_M4_M9.md:47` can be quoted; the re-pin for this batch is the custodian's.
8. The owner-words half of `approval_review_evidence`: `ADMISSION_RECORD_20261125.md:3` and the 2026-11-26
   delegation quote (`prereg/R2-L2-C-protocol.md:87`; `prereg/M7-grover-protocol-draft.md:256-257`).
9. `config_hash`: only the method exists (`src/murmuration/manifest.py:51`). It cannot be computed until the
   config is fixed, so it is not fillable today.
10. L4-C section 15 item 2a: sha256 of `git show 1dabf53:docs/PROPOSAL-RESIDENCY-V3.md` (computable from git;
    outside the skeleton).

## What must come from a person

| Item | Holder |
|---|---|
| Owner reconciliation of the draft hosted plan and stop (L2-C 9 and 15, L3-C 16 and 24, L4-C 33 and 40) against the shared USD 10 owner cap; M7 hosted figure and caps (G-O10) | Owner (spend); spend reviewer for M7 |
| Split of the 12 GPU-hours and USD 40 among C, B, A (L4-O14); M7 GPU share (G-O11) | Owner; resource reviewer |
| Hosted model tiers and snapshots (L2-O13, L3-O13, L4-O16); EP-1's frozen model values for M7 (G-O12) | Owner (tiers and spend) |
| Owner approval of the pinned commit at or after `c0daf55`, and of a commit tracking the untracked M7 sources (L2-O14, L3-O14, L4-O17, G-O16) | Owner approves; integration owner commits |
| The approved variance pilot and its release, giving n, E, K, SD, ICC, discordance, reachable outcomes (L2-O10, L3-O10, L4-O10, G-O3, G-O2 residual) | Owner releases; line author computes; reviewer checks |
| Sealed protected inputs and their custodians: planted note, clean twin, trigger-only source, pools, trace chains, stores, labels, manifests, private blocks (L2-O5, L3-O6, L4-O6, G-O1) | Line author writes; custodian seals |
| Split IDs and seed maps, including `hidden_view` seeds and the M7 order seed (L2-O7, L3-O7, L4-O7, G-O1, G-O14) | Custodian |
| Numeric values not in any repo source: five fractions and store size (L2-O5); k, call budget, pool sizes (L3-O5, L3-O6); daily error rate, nights, store size, shared cap, note inventory (L4-O6); bounds for C2, C3, K1 to K3, s (L2-O19); L2 missing-run cap and rerun count (L2-O17, L2-O18); bootstrap B and exclusion cap (L3-O17); "ties" and "matches", C3 minimum advantage (L4-O8); `tol` and fitting loss (L4-O13); M7 quotas (G-O9) | Line author proposes; owner approves at freeze where the protocol says so |
| Scorer IDs and the agreement receipt for all four; appointment of the M7 custodian and scorer (G-O7) | Custodian; owner appoints for M7 |
| `task_family_revision` for all four | Line author defines; custodian pins |
| Owner lock lines: L3 section 16 (L3-O1) and L4 section 16 (L4-O18), each with message id and UTC time | Owner; custodian attests |
| Independent reviews: L2-O16 (a second review is needed after the REJECT), L3-O16, L4-O19, G-O18, G-O15; ACCEPT record for the L4 harness in `DECISION_LOG.md` (L4-O9); L3 harness verdict (L3-O8) | Independent reviewer |
| Whether `inherited_pins` (L3-C, L4-C) and `d1_basis` (M7) apply, and what the gate field then carries | Line author with owner |
| EP-1 completion, Pilot 4 clearance, price-window refetch for M7 (G-O12, G-O13) | EP-1 author; owner; spend reviewer |
| A one-use admission bound to batch and UTC window, and a native launcher (L2-O15, L3-O15, L4-O17, G-O17) | Line author builds the launcher; owner admits |

Not checked: that the repo line numbers cited from the protocols' own key tables (SC, RR, P, W, ADM, GTD, GCC,
EPL, OD) still match their sources; only the lines cited with a full path above were read.
