# M4 freeze record drafts: R2-L2-C, R2-L3-C, R2-L4-C (TREMOR lane)

**DRAFT. Nothing is frozen. Nothing is admitted. No run, spend or GPU use follows from this file.**
Signatures, numbers, sealed inputs and approvals stay with the line authors, the custodian, the
independent reviewer and the owner. This file fills only values that already exist in a tracked
file or that a command prints. Every other cell is `OPEN`, with its holder. Nothing is invented.

Written 2026-11-26 at HEAD `49907a630eecdb1232b35bab9048a74ffb92c4ec` (tree
`d260d4481f57d8b58115db3df3364413b8ce9a03`). `prereg/` was clean at that reading. A freeze must
recompute every command value at the pinned commit; the values here are readings, not pins.

## Sources

- Field names: `lab/tremor_admission_gate.py:38-45` (`_FREEZE_KEYS`, `_PRESENCE_ONLY`). The gate
  refuses an empty presence-only field (`:230-232`), an empty custodian (`:264-265`) and an
  admission number above the freeze number (`:282-284`). It computes each input `sha256` from the
  file bytes (`_input_sha`), so those exist only after the custodian seals a file.
- Skeleton: `lab/tremor_freeze_skeleton.py` (batch, protocol path and sha256, commit, tree, then
  `missing()`, 14 entries per protocol before any custodian entries).
- Open items per field: `docs/reports/tremor/FREEZE_FIELD_REGISTER.md` (the L2-C, L3-C
  and L4-C sections, by their own headings), and each protocol's section 14 (OPEN table),
  section 15 (freeze record contents) and its Decisions sections (L2-C: 2026-11-24 and 2026-11-25,
  no D numbers; L3-C: D1-D4; L4-C: D1-D9, table at `prereg/R2-L4-C-protocol.md:410-420`).
- Legend: AR = `docs/reports/tremor/ADMISSION_RECORD_20261125.md`; ADM = `docs/reports/tremor/OWNER_DECISION_protected_admissions_M3R3_M4_M9.md`.
- Owner scope: AR:3,26-30.

## Holder vocabulary (no protocol names a person; these are the roles the repo gives)

line author; custodian (evaluator custodian, independent of the author); independent reviewer;
owner (spend); owner (commit or lock); pilot (the variance pilot, approved but not released:
AR:11, ADM:136).

## Cap that governs every hosted figure

The owner's words are "Paid calls for up to $10 for Tremor", USD 10 total across M2, M7 and D8
(AR:3). The record says each M4 line's later run stays "within the
remaining shared USD 10" and that the draft USD 15 stop "never applies above the owner cap"
(`:28-30`). The protocol hosted figures (L2-C 9 and 15, L3-C 16 and 24, L4-C 33 and 40) are draft
figures that exceed that cap, so they are not copied below. Only the owner reconciles them.

## Commands that fill the existing values

```
cd /home/adelmar/SeaBridgeAI/murmuration
sha256sum prereg/R2-L2-C-protocol.md prereg/R2-L3-C-protocol.md prereg/R2-L4-C-protocol.md
git rev-parse HEAD            # candidate commit reading only; the freeze pins an owner-approved commit
git rev-parse HEAD^{tree}     # tree at that commit
git log -1 --format=%H -- lab/l3c_harness.py lab/l4c_harness.py lab/l2c_detached_scoring.py
git show 1dabf53:docs/PROPOSAL-RESIDENCY-V3.md | sha256sum    # L4-C item 2a
git merge-base --is-ancestor c0daf55 HEAD && echo ok          # floor check (gate FLOOR_COMMIT)
```

Readings from those commands on 2026-11-26 (all exit 0; `c0daf55` and `4d264a5` are ancestors of HEAD):

| Reading | Value |
|---|---|
| `sha256 prereg/R2-L2-C-protocol.md` | `c25c46aeb8c3fc2ba8db773c8d244ce25fb6ea936905a72af32cabc041d41ed8` |
| `sha256 prereg/R2-L3-C-protocol.md` | `fdd664546c5feed2c0c525a2f87a4db85ccc8f3a56182947b06409c5807cebd3` |
| `sha256 prereg/R2-L4-C-protocol.md` | `7ff397fb0f51b2a609253d4a4b88f36896b59eb0a781d25a50e009a09e9fa7a5` |
| HEAD (candidate reading) | `49907a630eecdb1232b35bab9048a74ffb92c4ec` |
| tree at HEAD | `d260d4481f57d8b58115db3df3364413b8ce9a03` |
| last commit of `lab/l3c_harness.py` | `0390247270ef8ef690d0834b42b55e7189841185` |
| last commit of `lab/l4c_harness.py` | `9c8a2c917d6bb60958e5858f991b0a5dd4501d7c` |
| last commit of `lab/l2c_detached_scoring.py` | `c0daf557c8ab8d74c3956bd06a63128758dc2628` |
| sha256 of `git show 1dabf53:docs/PROPOSAL-RESIDENCY-V3.md` | `e1ffac0a9fe7836c5317aeeb1380abd5ffebbbdae4057321569ddb4d7fd14c04` |

The protocol sha256 values change if the protocol is edited before the freeze (the line authors
still owe edits for the OPEN items), so they must be re-read at the frozen commit. The candidate
commit needs the owner's approval before it is pinned (L2-O14, L3-O14, L4-O17).

---

## 1. R2-L2-C (`prereg/R2-L2-C-protocol.md`; section 14 `:290`, section 15 `:314-337`)

Batch id: OPEN (owner and line author name it; `[A-Za-z0-9][A-Za-z0-9_.-]{0,79}` per the gate).
Admitted scope: freeze only; a later run is at most 6 GPU-h, hosted within the remaining shared
USD 10 (AR:28).

| Field | Value | Holder | Source |
|---|---|---|---|
| `batch` | OPEN | owner, line author | gate `_BATCH` pattern |
| `protocol_path` | `prereg/R2-L2-C-protocol.md` | none needed | file path |
| `protocol_sha256` | reading above; re-read at the frozen commit | line author | `:318` (item 1) |
| `commit` | OPEN: a commit at or after `c0daf55`, never `f62cfe1`; owner approves | owner (commit), integration owner | `:319-320`, L2-O14 `:307` |
| `tree` | `git rev-parse <commit>^{tree}` at that commit; reading at HEAD above | line author | `:319-322` |
| `config_hash` | OPEN: method is `src/murmuration/manifest.py:51`; the config is not fixed (L2-O5, O9, O10, O17 to O19) | line author | `:322`, L2-O14 |
| `reserved_gpu_hours` | OPEN: at or under the ceiling 6 (`:280`) | owner (spend), line author picks | section 13 `:280` |
| `hosted_usd_plan` | OPEN: draft 9 (`:282`) exceeds the owner's shared 10 once other lines count; no hosted tier exists | owner (spend) | L2-O13 `:306`, AR:28 |
| `hosted_usd_stop` | OPEN: draft 15 (`:281`) exceeds the owner's 10 | owner (spend) | `:281`, AR:28 |
| `protected_inputs` | 9 inputs, each `{path, sha256, custodian}`, all OPEN: planted note, clean twin, trigger-only source, reference manifest, evaluator inventory, detached label tape, chain ID splits, seed map, ranking pins. No sealed bytes exist | line author writes the note, twin, trigger source, five fractions and store size; custodian seals and holds chain IDs and seed map | `:323-325`, L2-O5, L2-O7 |
| `model_snapshot` | Local tier only: Qwen3.5-4B revision `851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a` (M3 pin, ADM:47). Hosted tier and snapshot: OPEN | owner (tiers, spend); line author | `:326`, `:366`, L2-O13 |
| `task_family_revision` | OPEN | line author; custodian confirms | `:326`, L2-O13 |
| `scorer_ids` | OPEN: three scorers, any disagreement voids a run (`:113`); scorer agreement receipt required (`:251`), none recorded | custodian | `:113`, `:251` |
| `contrasts` | Structure exists (section 2 `:28-52`: primary conjunction, clauses decided under L2-O2). Bounds for C2, C3, K1 to K3, share s and the K3 floor are OPEN | line author proposes; owner approves | L2-O19 `:312` |
| `stopping_rules` | Statistical: fixed n, one analysis, no interim look (L2-O11, `:357`). Economic: 6 GPU-h or hosted stop (subject to the cap above). Cap on missing runs per arm and rerun count per chain: OPEN | line author; owner for caps | L2-O11, O17 `:310`, O18 |
| `expected_and_max_resources` | Maximum: `:280-282`. Expected (n, E, K, SD, ICC, reachable outcomes at the cap): OPEN, needs the unreleased pilot | owner releases pilot; line author computes; reviewer checks | L2-O10 `:303`, ADM:136 |
| `approval_review_evidence` | Owner words exist verbatim: AR:3, delegation quoted at `prereg/R2-L2-C-protocol.md:362` (L2-O3 text). Independent review: OPEN (first review REJECTED; a new one is needed) | independent reviewer; owner for words | `:330-331`, L2-O16 `:309` |
| `d1_basis` | Quote exactly `docs/reports/ep-approvals.md:166` (D1) and its ratification `prereg/R2-L2-L3-L4-scope.md:31`. Not yet copied here | line author copies, repo files only | `:332` (item 7) |
| `inherited_pins` | Candidate values: Qwen revision above and manifest sha256 `9b70e85c464f8dddbe1c6094832f51043a85fa7dcdf281e0cb81aa0d2d4d6ea6` (ADM:47). The M3 R3-L2 admission they come from does not exist (AR:9); custodian re-pins | custodian; owner for the M3 admission | `:333-334` (item 8) |

Harness reading: the L2-C modules are `lab/l2c_*.py` (11 files); the register names
`lab/l2c_detached_scoring.py:86-113` for custody; that range is scoring code, not custody, so the cite is carried from the register and not verified here. No native launch entry point exists (L2-O15).

---

## 2. R2-L3-C (`prereg/R2-L3-C-protocol.md`; section 14 `:304`, section 15 `:327-354`, section 16 `:356`)

Batch id: OPEN. Admitted scope: freeze only; a later run is at most 4 GPU-h, hosted within the
remaining shared USD 10 (AR:29).

| Field | Value | Holder | Source |
|---|---|---|---|
| `batch` | OPEN | owner, line author | gate `_BATCH` |
| `protocol_path` | `prereg/R2-L3-C-protocol.md` | none needed | file path |
| `protocol_sha256` | reading above; re-read at the frozen commit | line author | `:331` (item 1) |
| `commit` | OPEN: at or after `c0daf55`, never `f62cfe1`, with the harness at `4d264a5` or later (both are ancestors of HEAD); owner approves | owner (commit), integration owner | `:332-333`, L3-O14 `:321` |
| `tree` | `git rev-parse <commit>^{tree}` at that commit; reading at HEAD above; names the final candidate if L3-O8 or L3-O14 moves it | line author | `:332-335` |
| `config_hash` | OPEN: method `src/murmuration/manifest.py:51`; config unfixed (L3-O5, O9, O10, O17) | line author | `:335`, L3-O8 `:315` |
| `reserved_gpu_hours` | OPEN: at or under the ceiling 4 (`:295`) | owner (spend), line author picks | section 13 `:295` |
| `hosted_usd_plan` | OPEN: draft 16 (`:297`) exceeds the owner's shared 10 | owner (spend) | L3-O13 `:320`, AR:29 |
| `hosted_usd_stop` | OPEN: draft 24 (`:296`) exceeds the owner's 10 | owner (spend) | `:296`, AR:29 |
| `protected_inputs` | 8 groups, each `{path, sha256, custodian}`, all OPEN: view definitions, toy monitor and stand-in, calibration failure set, clean threshold set, clean and failure assessment sets, joint miss table pins, split IDs, seed map. No sealed pools exist | line author (k, view definitions, call budget, pool generation, sizes, stand-in); custodian seals and holds splits and seeds, including `hidden_view` seeds | `:336-338`, L3-O5, O6, O7 |
| `model_snapshot` | OPEN: the protocol states no pin | owner (tiers, spend); line author | `:340`, L3-O13 |
| `task_family_revision` | OPEN | line author; custodian confirms | `:340`, L3-O13 |
| `scorer_ids` | OPEN: three scorers, any disagreement voids a run (`:105`); agreement receipt (`:265`) none | custodian | `:105`, `:265` |
| `contrasts` | Structure exists (section 2; D1 clauses; D3 arm list; L3-O3 designated view = first selected view in ascending lexicographic order). Operating point (L3-O9) and the conservative-arm choice (L3-O18) are OPEN | line author; owner for the section 16 lock | L3-O9 `:316`, L3-O18 `:325` |
| `stopping_rules` | Statistical: fixed n, one analysis, no interim look (D2, `:394`). Near-zero-loss rule: report not testable, outcome inconclusive (`:397`). n, bootstrap B and the cap on the excluded share are OPEN | line author; reviewer checks | L3-O10, O11, O17 `:324` |
| `expected_and_max_resources` | Maximum: `:295-297`. Expected (K, n, ICC, discordance, reachable outcomes): OPEN, needs the unreleased pilot | owner releases pilot; line author computes; reviewer checks | L3-O10 `:317`, ADM:136 |
| `approval_review_evidence` | Owner words as for L2-C. Independent review of the protocol: OPEN. Harness at `1dabf53`: no ACCEPT verdict recorded (`:401`). Owner approval of the commit: not on record (`:399`) | independent reviewer; owner | `:344-345`, L3-O16 `:323` |
| `d1_basis` | Quote exactly `docs/reports/ep-approvals.md:166`, `prereg/R2-L2-L3-L4-scope.md:31` and the D1 scope statement at `prereg/R2-L3-C-protocol.md:77`. Not yet copied here | line author copies | `:346` (item 8) |
| `inherited_pins` | OPEN: section 15 has no matching item (the register flags "section not found"); the gate still requires a non-empty value, so the line author states what the batch inherits, or records a reason | line author decides; custodian | register L3-C section |

Extra section 15 items outside the gate keys, all OPEN:

| Item | Value | Holder | Source |
|---|---|---|---|
| 4 and 10, primary lock | owner lock line with message id and UTC time; custodian attestation that pools were sealed and unread at that time | owner; custodian | `:339`, `:349-350`, L3-O1 `:308`, section 16 |
| 9, null-ratio and bootstrap | `null_loss_ratio` with fitted (p, c) and pool draws, bootstrap code and seed derivation, harness commit `4d264a5` or later (reading: `lab/l3c_harness.py` last changed at `0390247270ef8ef690d0834b42b55e7189841185`) | line author | `:347-348`, L3-O17 |
| 11, conservative arm | OPEN: define it distinct from the fixed arm, or drop it from the conjunction, with the reason | line author | `:351`, L3-O18 |

---

## 3. R2-L4-C (`prereg/R2-L4-C-protocol.md`; section 14 `:303`, section 15 `:327-357`, section 16 `:359`)

Batch id: OPEN. Admitted scope: freeze only; a later run is at most 12 GPU-h plus the adapter,
hosted within the remaining shared USD 10 (AR:30). Decisions D1 to D9
(`:410-420`) are method rules only; D8 states the shared token cap and `store_size` are fixed on
calibration chains before any run and are OPEN numbers.

| Field | Value | Holder | Source |
|---|---|---|---|
| `batch` | OPEN | owner, line author | gate `_BATCH` |
| `protocol_path` | `prereg/R2-L4-C-protocol.md` | none needed | file path |
| `protocol_sha256` | reading above; re-read at the frozen commit | line author | `:331` (item 1) |
| `commit` | OPEN: at or after `c0daf55`, never `1dabf53`; owner approves | owner (commit), integration owner | `:332-335`, L4-O17 `:323` |
| `tree` | `git rev-parse <commit>^{tree}` at that commit; reading at HEAD above. The `1dabf53` tree `3a9a1dc57b138aab80ab46c0e878fe06a1984387` is history only (`:333-334`) | line author | `:332-335` |
| item 2a, proposal commit | commit `1dabf53`; sha256 of `git show 1dabf53:docs/PROPOSAL-RESIDENCY-V3.md` = `e1ffac0a9fe7836c5317aeeb1380abd5ffebbbdae4057321569ddb4d7fd14c04` (reading above; recompute at the freeze) | line author | `:336-337` |
| item 2b, steering inputs | OPEN: code hash of `readings`, `check`, `render`, `tokenizer`, `check_tokens`, `reading_tokens` and their measured charges | line author; reviewer | `:338-340`, L4-O2 |
| `config_hash` | OPEN: method `src/murmuration/manifest.py:51`; harness `lab/l4c_harness.py` last changed at `9c8a2c917d6bb60958e5858f991b0a5dd4501d7c`; config unfixed (L4-O2, O5, O6, O8, O13, O14); native launcher not built | line author; owner approves commit | `:335`, L4-O9 `:315`, L4-O17 |
| `reserved_gpu_hours` | OPEN: at or under the ceiling 12 (`:292`); the split among C, B and A work is not set | owner (spend) | L4-O14 `:320` |
| `hosted_usd_plan` | OPEN: draft 33 (`:294`) exceeds the owner's shared 10 | owner (spend) | L4-O14, AR:30 |
| `hosted_usd_stop` | OPEN: draft 40 (`:293`) exceeds the owner's 10 | owner (spend) | `:293`, AR:30 |
| `protected_inputs` | 8 groups, each `{path, sha256, custodian}`, all OPEN: day and night trace chains, old and new stores with source IDs, measured compression ratios per setting, ladder calibration, close-night truth labels, paired cost records, split IDs, seed map. No sealed files; no value for daily error rate, nights per chain, store size, shared cap or note inventory | line author (L4-O5, O6); custodian holds calibration chains, splits, seeds (L4-O7) | `:341-343` |
| `model_snapshot` | OPEN: no pin; the snapshot serving the token meter is OPEN (L4-O2) | owner (tiers, spend); line author | `:346`, L4-O16 `:322` |
| `task_family_revision` | OPEN | line author; custodian confirms | `:346`, L4-O16 |
| `scorer_ids` | OPEN: three scorers, any disagreement voids a run (`:135`); agreement receipt (`:252`) none | custodian | `:135`, `:252` |
| `contrasts` | Structure exists (six conjuncts at two settings, D2; prediction A not a conjunct, D3; reference arm for C2, D1). Open: numeric "ties" and "matches", C3 minimum advantage, tie rule, compression index unit (tokens or bytes), fitting loss and `tol` | line author proposes; owner approves; section 16 lock | L4-O5, O8 `:314`, O13 `:319` |
| `stopping_rules` | Statistical: fixed n, no interim look (D4, `:415`). Truncated-batch rule exists (`:449`). Economic: ceilings `:292-294` subject to the cap above. n per conjunct is OPEN | line author | L4-O10, O11 |
| `expected_and_max_resources` | Maximum: `:292-294`. Expected (n, variance, ICC, reachable outcomes): OPEN, needs the unreleased pilot; owner splits the ceiling | owner releases pilot and splits; line author computes; reviewer checks | L4-O10 `:316`, L4-O14 |
| `approval_review_evidence` | Owner words as for L2-C. Independent protocol review: OPEN (L4-O19). Harness ACCEPT is cited from the line author's report with no matching `DECISION_LOG.md` record (`:315`, `:453`), so it is not evidence yet | independent reviewer; owner | `:350-351`, L4-O9, O19 `:325` |
| `d1_basis` | Quote exactly `docs/reports/ep-approvals.md:166`, and the scope record that excludes L4-D, `prereg/R2-L2-L3-L4-scope.md:26` (item 8) with `:31`; the D1 flag paragraph is at `prereg/R2-L4-C-protocol.md:422`. Not yet copied here | line author copies; owner for the L4-D scope record | `:352` (item 8) |
| `inherited_pins` | OPEN: section 15 has no matching item (item 9 is L4-E only); line author states what is inherited, or records a reason | line author decides; custodian | register L4-C section |

Extra section 15 items outside the gate keys, all OPEN:

| Item | Value | Holder | Source |
|---|---|---|---|
| 4, two-setting lock | owner lock line with message id and UTC time, plus the bound token reference (D1) | owner | `:344-345`, L4-O18 `:324`, section 16 |
| 9, L4-E record | separate record: settled receipt and before and after checkpoint digests; outside this freeze | trainer, line author | `:353-354` |

---

## Open across all three

1. The owner reconciles the hosted figures with the shared USD 10 (one decision for L2-C, L3-C, L4-C, M2, M7, D8).
2. The owner approves a candidate commit at or after `c0daf55` and releases the variance pilot.
3. The line authors supply every number in the OPEN rows; the custodian seals the inputs and names three scorers per line.
4. An independent reviewer reviews each protocol (L2-O16, L3-O16, L4-O19).
5. The gate keys `inherited_pins` (L3-C, L4-C) and `d1_basis` have no clean protocol item; the line authors decide how each is filled.
