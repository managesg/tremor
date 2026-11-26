# R6 freeze packet: fill-in-the-blanks for the line author and the custodian

Read-only. No value is filled and none is invented. This is not a freeze record, an admission, an approval or a run authority. No network, model, GPU or key was used. Schema: `lab/tremor_admission_gate.py:38-48` (`_FREEZE_KEYS`, `_PRESENCE_ONLY`, `_ADMISSION_KEYS`). Protocol: `prereg/R6-protocol-draft.md` (cited as "draft:N"). DL = `docs/reports/tremor/DECISION_LOG.md`. PL = `prereg/R6-pvsnp-research-line-plan.md`.

## 1. Skeleton run

**skeleton run on 2026-11-26T14:43:13Z at HEAD 2ef7a32155a2350b452464dd4a1839507d5a5386; computed fields only.**

How: a Python script ran `python3 -m lab.tremor_freeze_skeleton prereg/R6-protocol-draft.md --batch <id> --out <tmp>/<id>.json` for `r6-b0` and `r6-p0`, with `tempfile.mkdtemp` outside the repo and `shutil.rmtree` in a `finally` (checked gone). No `--input`. Exit code 0 both times. Nothing was written into the repo except this file.

The two outputs differ only in `batch`. Output for `r6-b0` (for `r6-p0` replace `"batch"`):

```json
{
  "approval_review_evidence": "",
  "batch": "r6-b0",
  "commit": "2ef7a32155a2350b452464dd4a1839507d5a5386",
  "config_hash": "",
  "contrasts": "",
  "d1_basis": "",
  "expected_and_max_resources": "",
  "hosted_usd_plan": null,
  "hosted_usd_stop": null,
  "inherited_pins": "",
  "model_snapshot": "",
  "protected_inputs": [],
  "protocol_path": "prereg/R6-protocol-draft.md",
  "protocol_sha256": "2fb14fefce193483c59c580bc7630a321c2a3762705e22ea5a32d47c5eb31a62",
  "reserved_gpu_hours": null,
  "scorer_ids": "",
  "stopping_rules": "",
  "task_family_revision": "",
  "tree": "b804061c031180f12b4a640218efb3143dffe171"
}
```

`missing()` output (identical for `r6-p0` and `r6-b0`; 14 entries):

```
MISSING reserved_gpu_hours (section 11)
MISSING hosted_usd_plan (section 11; effective hosted cap is the caller's cap (the owner's shared USD 10), never the protocol's own stop)
MISSING hosted_usd_stop (section 11; effective hosted cap is the caller's cap (the owner's shared USD 10), never the protocol's own stop)
MISSING protected_inputs (section 14 item 3)
MISSING approval_review_evidence (section 14 item 6)
MISSING config_hash (section 14 item 2)
MISSING contrasts (section 14 item 4)
MISSING d1_basis (section 14 item 7)
MISSING expected_and_max_resources (section 14 item 4)
MISSING inherited_pins (section 14 item 8)
MISSING model_snapshot (section 14 item 4)
MISSING scorer_ids (section 14 item 4)
MISSING stopping_rules (section 14 item 4)
MISSING task_family_revision (section 14 item 4)
```

Count: 19 freeze keys = **5 computed** (`batch`, `protocol_path`, `protocol_sha256`, `commit`, `tree`) + **14 missing**. The 14 are 3 numbers, `protected_inputs`, and 10 presence-only fields. Once `protected_inputs` lists N entries, `missing()` adds one `protected_inputs[i].custodian` entry each (gate `:216-217`); `sha256` per input is computed by the gate from the file bytes (`:157-166`).

**These computed values are throwaway.** They pin the *draft* path. The real freeze runs on `prereg/R6-protocol.md` after R6-O1 (draft:187), so `protocol_path`, `protocol_sha256`, `commit` and `tree` all change. Re-run the skeleton at the final commit, after every code piece the freeze pins is committed (draft:240).

## 2. Rows: every empty field

Holders: **line author**, **custodian** (not yet named, R6-O2), **owner** (Alejandro), **PC placement** (PC coordinator places GPU-hours and wall caps, draft:196-197). Source "exists" means a value or method is in the repo; "produce" means a person or a measurement must create it.

| Field | Protocol item | Named holder | Source in repo, or must be produced | What exactly unblocks it |
|---|---|---|---|---|
| `reserved_gpu_hours` | section 11 (draft:146-148); R6-O10 | PC placement | P0: bound exists, min(15 min, 12 x 300 s) = 0.25, "placement OPEN" (draft:146; `lab/r6_inkling_client.py:24` `max_wall_s` 900). B0', B1': **produce**, 28 x T and 280 x T, T unmeasured until P0 (draft:111-112, 147-148) | PC coordinator states the placed number (and whether the resident service draws on the residual 9.4 GPU-h, draft:152). Line author enters it. It must be at or above the admission's number and the `--gpu-cap` (gate `:234-238`) |
| `hosted_usd_plan` | section 11 (draft:144); section 14 item 5 (draft:217) | line author | **Exists**: USD 0 at draft:144, 217 and PL:302. The gate accepts 0 (`:113`, `>= 0`) | Line author types 0. Every gate call uses `--hosted-cap 0`. The owner's shared USD 10 (`docs/reports/tremor/ADMISSION_RECORD_20261125.md:3`) does not apply to R6 |
| `hosted_usd_stop` | section 11 (draft:145); item 5 | line author | **Exists**: USD 0 (draft:145, 217; PL:302) | Line author types 0 |
| `protected_inputs` (N entries, each path, sha256, custodian) | section 14 item 3; R6-O2, R6-O3, R6-O4 | custodian seals; owner names the custodian; line author names the pilot family | **Produce.** No sealed file path for any R6 input is named in the draft or in DL (searched `briefing_keywords`: only code, tests and the draft mention it). The list of inputs is in section 3 below. Custodian: not named anywhere (draft:188) | (a) Owner names the custodian, not the author, not a runner (R6-O2). (b) Line author names the pilot family (R6-O4). (c) Custodian draws the pilot pool (disjoint from the main pool) and seals every item under the repo with no symlinks (gate `:157-166`), then gives path, sha256 and their own name per item. N is fixed by how many files the custodian seals; the gate needs one custodian per file |
| `config_hash` | section 14 item 2 | line author | Method exists: `src/murmuration/manifest.py:51` (`config_hash`, sha256 of sorted JSON). The config is **produced**: arms, sizes, caps, CL stops, output cap, rubric weights (draft:214). Parts exist: CL stops at `lab/r6_inkling_client.py:24`; P0 inputs 200/1,000/2,000 tokens, caps 64/300, 12 calls (draft:131); rubric weights = PL E defaults (D18, draft:179) | Line author writes one config per batch and hashes it with `config_hash`. For `r6-p0` it is fixed by draft section 10. For `r6-b0` it waits on the PC placement (R6-O10, O11), the dial (R6-O17) and the output cap and timeout (R6-O22, from P0) |
| `model_snapshot` | section 14 item 4; R6-O9; D12 | line author, on the Spark | **Partly exists.** DL:311 (2026-11-26T14:04Z): pid 435838, start time Mon Nov 23 01:54:13 2026, `llama-server` exe sha256, GGUF path, inode 18783528, size 22,867,451,616 bytes, locally computed GGUF sha256. Arguments, alias, runtime build `runtime-b12588`, endpoint `100.91.57.48:8011`: PL:241. mmproj and runtime-tarball hashes: the `SHA256SUMS` in `/home/adelmar/.cache/huggingface/seabridge-inkling-2-mini/` lists both (outside the repo). **Gaps:** DL:311 has no mmproj hash or inode, and no runtime-build hash of the running binary beyond the exe sha256 | Line author re-reads pid, start time, exe hash and GGUF inode read-only right before the freeze (draft:126, 130) and copies DL:311 only if they match, adds the mmproj hash and inode, and writes the note "local identity, not upstream verified" (draft:216). No request to the service |
| `task_family_revision` | section 14 item 4; R6-O5 | line author | M1 table commit `9a015ea` exists (draft:216). Generator and checker commits for F1 to F6 do **not** all exist: draft:52-57 lists F1, F3, F4, F6, and the F2 submitted-circuit evaluator as not built. `lab/r6_stage_a.py` has `gen_circuit_tasks:223`, `gen_lemma_tasks:260`, `gen_audit_tasks:718`, `oracle_f2:164`, `oracle_f3:174`, `oracle_f5:192`, `oracle_f6:741`, but DL:307 calls these scripted-agent consumer-side proof and defers F1 and F4 | **Produce.** Line author builds F1 (needed even for P0, draft:127), F4 and the missing checkers; an independent Opus reviewer kills every targeted mutant (R6-O5, DL:275). Then line author lists the commit shas |
| `scorer_ids` | section 14 item 4 | line author | **Exists in part** (draft:220): SC `fa03232` and `28610e1` (`lab/r6_scorecard.py` `validate:203`, `gates:246`, `score:312`), PR `caf0643` and `5108519` (`lab/r6_predicates.py` `parse:281`, `check_lemma:309`); all seven pins resolve as commits at HEAD. The F1 to F6 checker names: **produce**, same dependency as `task_family_revision` | Line author copies the SC and PR commits and function names now; adds checker names when R6-O5 closes |
| `contrasts` | section 14 item 4 | line author | **Exists**: draft:15-31 (H2 primary, Holm family {H1, H3, H5, RT} size 4, DA descriptive, G1 to G6 report only), summary at draft:216 | Line author copies the text. The deviations D8 and D9 still need DL entries (R6-O20, draft:203) |
| `stopping_rules` | section 14 item 4 | line author | **Exists**: draft section 8 (:97-103), P0 stops draft:134 (12 calls, 15 min, 2 errors in total, skip spike, 300 s per call), line stop 2026-12-10T04:50Z (draft:102). The wall and GPU caps inside them are OPEN (R6-O10, O11) | Line author copies; the caps come from PC placement |
| `expected_and_max_resources` | section 14 item 4 | line author | P0: **computable** from draft:131, 134, 146 (12 calls, 15 min, 0.25 GPU-h bound). B0', B1': **produce**, 28 x T and 280 x T need T from P0 (draft:111-112) | For `r6-p0`: line author writes the P0 bound. For `r6-b0`: P0 runs first, T is recorded (PL:316), then PC places the hours |
| `approval_review_evidence` | section 14 item 6 | line author collects; independent Opus reviewer; owner | Owner words **exist**: DL:303 (exact quote; it says each batch still needs its freeze, `admit`, PC placement, notice and quiet window). Reviews that exist in DL: SC, PR, T, M1 (`9a015ea`), Stage A (DL:305-307), CL (`9486e3c`, Opus security ACCEPT), Holm (`8e828f1`). **Produce:** the independent review of this protocol including D8 to D18 (R6-O20); reviews of the F1 to F6 checkers; the custodian's attestation that main-run inputs were sealed and unread before P0 (R6-O3); for `r6-p0` only, the notice message ids (before and after), the owner's agreed quiet window and the named service owner | Independent reviewer reviews the protocol; custodian writes the attestation; owner and PC coordinator agree the window; line author quotes each item exactly |
| `d1_basis` | section 14 item 7; R6-O19 | line author quotes; owner confirms | AP-D1 **exists**: `docs/reports/ep-approvals.md:166` (contagion or monitor-selection allowed as defensive; the R2 scope ratification is at `prereg/R2-L2-L3-L4-scope.md:31`). The H5 confirmation is **produced** by the owner (draft:202) | Owner confirms in writing that AP-D1 covers H5; line author quotes both |
| `inherited_pins` | section 14 item 8 | line author | **Exists** (draft:220): H `d0c67d7`, T `9a015ea`, SC `fa03232` and `28610e1`, PR `caf0643` and `5108519`, floor `c0daf55`. All seven resolve as commits (`git cat-file -t`) | Line author copies the seven shas |

## 3. Protected inputs the custodian must seal (R6-O3, R6-O4, draft:189-190)

For each: path in the repo, sha256 (computed from the file), custodian name. None has a path yet. Grouping into files is the custodian's choice, so N is not fixed here.

- Main-run task sets; seeds and the seed map.
- F5 false rate; F6 faithful rate; F6 defect spans; H5 spot-check eighth.
- H3 confidence wording; the neutral card; the RT role text and the control role text.
- `briefing_keywords` and `overclaim_patterns` (the scorecard also reads them: `lab/r6_scorecard.py`).
- Pilot pool and pilot task (R6-O4): family named by the line author; drawn by the custodian from a pool disjoint from the main pool; sealed **before P0** (D2, draft:163).

Both `r6-p0` and `r6-b0` list every item (draft:215). The main-run inputs are sealed before P0 (D2).

## 4. Commands, in order

Order from draft section 10 (:121-127) and PL:290-298: freeze record, admission record, PC notice, quiet window, P0. Placeholders only for what a person holds.

**Step 1. Freeze record, per batch (line author, then custodian).** After R6-O1 (rename and commit `prereg/R6-protocol.md`), every code piece committed, and the custodian's seals in place:

```
python3 -m lab.tremor_freeze_skeleton prereg/R6-protocol.md --batch r6-p0 --out <freeze-r6-p0.json> --input <sealed-path-1> --input <sealed-path-2> ...
python3 -m lab.tremor_freeze_skeleton prereg/R6-protocol.md --batch r6-b0 --out <freeze-r6-b0.json> --input <sealed-path-1> ...
```

The skeleton refuses to overwrite `--out`. It prints `MISSING ...` lines until the author and custodian have filled every field, as in section 2. `missing()` does not run the gate's other checks (tree match, protected-input hashes); Step 3 `check` does.

**Step 2. Admission record, per batch (owner).** Exact keys (gate `:46-48`): `batch` (must equal the freeze's), `one_use` true, `used` false, `valid_from_utc`, `valid_until_utc` (UTC, window is `[from, until)`), `reserved_gpu_hours`, `hosted_usd_plan` (0), `hosted_usd_stop` (0), `owner_words` (exact string the owner gave), `freeze_record_sha256` (sha256 of the finished freeze file). Admission numbers may not exceed the freeze's (gate `:234-236`).

**Step 3. Check, then admit, per batch.** `check` is a dry run; `admit` runs `check`, then claims the batch once and sets `used` true.

```
python3 -m lab.tremor_admission_gate check <freeze-r6-p0.json> <admission-r6-p0.json> --now <UTC time> --hosted-cap 0 --gpu-cap <PC-placed GPU-hours> --max-window-hours <h> --owner-words "<exact owner string>" --repo-root .
python3 -m lab.tremor_admission_gate admit <freeze-r6-p0.json> <admission-r6-p0.json> --now <UTC time> --hosted-cap 0 --gpu-cap <PC-placed GPU-hours> --max-window-hours <h> --owner-words "<exact owner string>" --repo-root .

python3 -m lab.tremor_admission_gate check <freeze-r6-b0.json> <admission-r6-b0.json> --now <UTC time> --hosted-cap 0 --gpu-cap <PC-placed GPU-hours> --max-window-hours <h> --owner-words "<exact owner string>" --repo-root .
python3 -m lab.tremor_admission_gate admit <freeze-r6-b0.json> <admission-r6-b0.json> --now <UTC time> --hosted-cap 0 --gpu-cap <PC-placed GPU-hours> --max-window-hours <h> --owner-words "<exact owner string>" --repo-root .
```

Each prints `OK` or `REFUSED: <reason>` (exit 2). `r6-b0` is not admitted until P0 has run and T is measured (PL:316-317); do not run its `admit` earlier.

**Step 4. PC notice.** Before and after the window, written, to the PC coordinator (OmniRoute fallback hop), the Spark service owner (to be named, R6-O11), and every known direct user of `:8011` (draft:123). The message ids go into `approval_review_evidence` of `r6-p0`.

**Step 5. Quiet window.** The owner agrees it with the PC coordinator; it takes the Spark hop out of OmniRoute routing (draft:124). The service owner is named in the PC placement (draft:125).

**Step 6. P0.** Only after Steps 1 to 5: read-only identity re-check (stop on any mismatch), then at most 12 strictly serial calls under the stops at draft:134, through the stub-tested client `lab/r6_inkling_client.py`. No request reaches the service before `admit` succeeds (PL:298).

## 5. Things the line author should check before using this

- **Order risk.** `admit` is one-use per batch id: a claim file in the git common dir (gate `:252-267`) keeps `r6-p0` spent even if the window slips, and the admission window `[from, until)` must already cover the quiet window. The draft puts `admit` first (draft:122) and the window third (:124). Run `check` freely; run `admit` only when notice and window are agreed, or accept that a new batch id is needed if they slip. This is a question for the R6-O20 reviewer; this packet does not change the protocol.
- **Stale statements in the draft.** The draft (written at `9a015ea`) says `lab/r6_holm.py` and the client are not built. They exist now: `lab/r6_holm.py` (`8e828f1`) and `lab/r6_inkling_client.py` (`9486e3c`), whose error stop already counts total errors (`:24`, `:186`, `:214`; the draft says CL encodes consecutive errors). The identity read of R6-O9 is recorded at DL:311. The `lab/r5_gpu_readiness.py` extension to hash a GGUF (draft:194) is not there: it has `other_gpu_processes_allowed` (`:84`) but no GGUF hash. The draft's own status of each item needs refreshing at R6-O1.
- **`_nonempty` treats 0 as empty** (gate `:133`) for presence-only fields; hosted and GPU numbers are checked by `_num` (`>= 0`), so 0 is valid there.
