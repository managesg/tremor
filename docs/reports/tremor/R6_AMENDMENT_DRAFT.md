# R6 amendment draft: VP != VNP sources (T1, T2, T3), exact sentences

Draft for the TREMOR lane. Nothing is applied; no file other than this one was touched. Offline. Keys: PD = `prereg/R6-protocol-draft.md` (HEAD `1a669c7`), PL = `prereg/R6-pvsnp-research-line-plan.md`, IP = `docs/reports/tremor/VPVNP_TREMOR_INTEGRATION_PLAN.md`, RV = `docs/reports/tremor/VPVNP_CLAIM_REVIEW_20261126.md`, SA = `lab/r6_stage_a.py`, SS = `lab/tremor_sealed_inputs.py`. This draft does not say the paper's proof is correct or incorrect.

## 0. OPEN numbering gap

The last real item in PD is R6-O24 (PD:208; the table runs R6-O1 to R6-O24, with O13 to O16 closed at PD:200). No R6-O25 to R6-O29 exists in PD. All five exist only in IP:44-48.

| ID | In PD | In IP | Subject in IP |
|---|---|---|---|
| R6-O25 | no | IP:44 | T1 source (Statement.lean plus two transcriptions) |
| R6-O26 | no | IP:45 | build and review t1, t2, t3 and the G1 fixture |
| R6-O27 | no | IP:46 | seal T1 pairs, t2/t3 seeds and false rate, pool shares |
| R6-O28 | no | IP:47 | contamination |
| R6-O29 | no | IP:48 | G1 scope for arithmetic-circuit routes |

Note: the request calls O26 "T3 lemmas" and O29 "G1 fixture". IP:45 makes O26 the build of t1, t2, t3 and the fixture, and IP:48 makes O29 the G1 scope question (fixture is its regression point, IP:72). This draft follows IP. O27 (sealing) is needed for amendment 3.

## 1. New OPEN items

**Location:** PD section 13 table, after the row ending "...frozen before the main run" (R6-O24, PD:208), before the heading `## 14. What the freeze record must contain` (PD:210).

**New rows (exact):**

| ID | Decision still needed, and the method to set it | Holder | Person |
|---|---|---|---|
| R6-O25 | T1 source. The formal side comes only from `Statement.lean` at commit `11b6c7e3c927df2658f513b6b68ea7f8929c62c5`, retrieved under a gated request, sha256 recorded and equal to `f090345dafa13c7629ff0c0737bb1c2fe5d60e8b2d08372281cbb2e65b506ffd` for the copy in `docs/reports/tremor/vpvnp_source/`. The prose side comes from two independent transcriptions of the PDF (path and full sha256 recorded first; prefix `882f5eef`) that agree character for character. Until both exist `t1` has no data and is excluded from every pool. Number of pairs: OPEN (R6-O3) | owner (clone approval); line author | **yes** |
| R6-O26 | Build and review `t1`, `t2`, `t3` and the G1 fixture under the R6-O5 rules: an independent second implementation for `t2`, every targeted mutant killed, independent Opus review | line author; reviewer | no |
| R6-O27 | Seal under R6-O3: the T1 pair file (faithful rate, defect spans), the `t2` and `t3` seeds and false rate, and each sub-generator's share of the F5 and F6 pools. Values: OPEN. Pilot draws stay disjoint from main draws (`tremor_sealed_inputs.no_overlap`) | custodian (R6-O2) | **yes** |
| R6-O28 | Contamination: no prompt, system card or tool context shows an agent the paper, the repository or `Statement.lean`. DA reports `t1` as a separate descriptive stratum labelled "public source, exposure unknown" | line author | no |
| R6-O29 | G1 scope for arithmetic-circuit routes: whether "not_applicable with a reason" covers relativization and algebrization (PL:75 calls them Boolean-oracle notions). Until decided G1 stays as coded and the fixture expects `fail` | protocol owner; independent reviewer | no |

**Reason:** IP:44-48; R6-O3 and R6-O5 at PD:190, PD:192.

## 2. Families table and task sources

**Location:** PD section 5, directly after the F6 table row `| F6 informal/formal pair, faithful pairs at a sealed rate | ... | **not built** |` and before the paragraph beginning `**M1 ground truth.**` (PD:48-62).

**Exact text (new paragraph):**
> "F5 also draws from the sub-generators `t2` (`lab/r6_t2_identity.py`: formal identity versus 0/1 agreement) and `t3` (`lab/r6_t3_lemmas.py`: finite lemmas suggested by the VP != VNP paper). F6 also draws from `t1` (`lab/r6_t1_audit_pairs.py`). Every label comes from our exhaustive checker or from a planted edit, never from the paper. No family is added: `FAMILIES` in `lab/r6_scorecard.py:24` and the pooled H2 stratum (D9, PD:171) are unchanged, and per-sub-generator results are descriptive."

**Reason:** IP:35; family tuple at `lab/r6_scorecard.py:24`; D9 at PD:171.

**Also, Predicates paragraph.** Location: PD section 5, paragraph `**Predicates.**` ending "That registry is empty at `5108519`." Append:
> "A generator module may pass a per-task registry to `PR.parse` (the `registry` argument). Each registered function counts one step, so it lies outside the step limit. Each such function is therefore reviewed independently, every targeted mutant killed, and named in `scorer_ids`. It takes int arguments, returns an int below 2^64 and closes over precomputed per-task data. Functions that evaluate a given arithmetic circuit or compute `rank_f2` are not circuit-size functions; R6-O23 is unchanged. The PR pin (`5108519`) is unchanged."

**Reason:** IP:38; the paragraph states the registry is empty (PD:61); R6-O23 at PD:207.

## 3. Sealed-input effect (held-out pairs)

**Location:** PD section 14 item 3, `**Protected inputs** (`protected_inputs`), each with path, sha256 and custodian: every item of R6-O3 and R6-O4. Paths must be under the repo and contain no symlinks (G:153-165).` Append:
> "For `t1`, the protected input is the pair file (labels and spans). Its faithful text is public, so the seal hides only which pairs are defective and where. The `t1` working copies of `Statement.lean` and of the two transcriptions stay outside the sealed roots, and the pair file is sealed with `tremor_sealed_inputs.seal` under the custodian of R6-O2. Pilot and main `t1`, `t2`, `t3` draws are checked disjoint with `tremor_sealed_inputs.no_overlap` (path and sha256 overlap raise `SealError`, SS:260-268)."

**Reason:** IP:54, IP:46; `no_overlap` compares manifests, not disks (SS:262, module LIMITS).

## 4. Freeze-record effect

**Location A:** PD section 14 item 4 (`**Model snapshot** (`model_snapshot`): ... Also `task_...`). Append:
> "`task_family_revision` also names the `t1`, `t2` and `t3` generator commits and the `Statement.lean` sha256; `scorer_ids` names the `t2` oracle functions (A and B), `rank_f2` and every per-task registry function."

**Location B:** PD section 14, after the line `A freeze authorises no run; no request reaches the service before that batch's `admit` succeeds (PL:298).` Add:
> "Holm stays {H1, H3, H5, RT}, size 4 (D8, PD:170; also PD:23). Inherited pins are unchanged. A sub-generator that joins a pool after a freeze voids that freeze: a new protocol sha256 and a new record are needed."

**Reason:** IP:51, IP:62; D8 at PD:170.

## 5. The paper's lemmas are never relied on as true

**Location:** PD section 2, end of the paragraph `R6 measures how well agents and teams do checkable work...` after "...small n says nothing asymptotic." (PD:13). Insert:
> "No step relies on a lemma, bound or proof of the VP != VNP paper being true. Every T2 and T3 label comes only from our own exhaustive checker, and a T2 label counts only when workers A and B agree. The paper supplies candidate statements, not truth values. No T1 'faithful' label comes from text we cannot trust (our extracted text is damaged, RV:126)."

**Reason:** IP:7, IP:20, IP:24; RV:126 (extracted text damaged).

## 6. Status wording PS

**Location:** `prereg/R6-protocol-draft.md` section 15 (`## What is unverified`, PD:226), after the bullet `**Briefing claims** (PL:12): no step depends on any 2025 to 2026 item.` Add the bullet:
> "- **VP != VNP paper:** status PS = primary source retrieved, proof not verified by us. The document was read (RV); its proof, its formalization and its citations were not checked. `Statement.lean` is copied unmodified and not elaborated here (no Mathlib on this host, IP:99). No `kernel_checked: true` or `proved_in_artifact` is recorded for it."

**Location (companion, outside PD):** `docs/reports/tremor/PVSNP_BRIEFING_UNVERIFIED_CHECKLIST.md` legend (CK:7) and row 9 (CK:21), wording as RV:109-112. PL:56 gets RV:112's wording.

**Reason:** RV:109-112; IP:105; PROVENANCE.md says "the proof is not verified by us".

## 7. No P vs NP or Boolean claim

**Location:** PD section 2, same paragraph, after the new sentence of amendment 5. Add:
> "Nothing in R6 supports any claim about P vs NP or about any Boolean circuit bound. The paper's bound is for arithmetic circuits; no milestone M1 to M10, R6 milestone or lens changes status (IP:7, IP:11, IP:113). Results measure agents, never the theorem."

**Reason:** IP:7, IP:11, IP:113 (the paper's own caveats only).


## 8. Contamination

**Location:** PD section 16 (`## Risks`, PD:235), after the `**Memorization:** sealed random seeds are the control.` bullet. Add:
> "- **Contamination (R6-O28):** the paper and `Statement.lean` are public (RV: public since 2026-11-23 per the owner; the paper gives no date). No prompt, system card or tool context shows an agent either. `t1` may still measure recall, so DA reports it as a separate descriptive stratum labelled 'public source, exposure unknown'."

**Reason:** IP:47, IP:106; RV T1 'uninformative if'.

## 9. Licence notice (Apache-2.0)

**Location:** PD section 5, after the amendment-2 paragraph, or PD section 15. Text:
> "`docs/reports/tremor/vpvnp_source/Statement.lean` (sha256 `f090345dafa13c7629ff0c0737bb1c2fe5d60e8b2d08372281cbb2e65b506ffd`, 4,837 bytes) is copied unmodified from `github.com/anthropics/formal-math`, commit `11b6c7e3c927df2658f513b6b68ea7f8929c62c5`, path `vp-vnp/Statement.lean`, under Apache-2.0 (SPDX line in the file, `Statement.lean:3-4`). The licence text is kept beside it as `LICENSE` (sha256 `c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4`). Any derived pair file keeps this notice and states its changes."

**Reason:** `docs/reports/tremor/vpvnp_source/PROVENANCE.md:3-8`. A defective variant is a modified file; PROVENANCE.md:12 requires a 'modified' notice under Apache-2.0 section 4(b) when distributed outside the repo.

## 10. T1 span convention and informal side

**Location:** PD section 5, the F6 table row (`planted label; exact span match` is the ground-truth cell; F6 row PD:57, Predicates paragraph PD:61). Append to the section 5 paragraph of amendment 2:
> "T1 spans are code-point offsets `[start, end)` into the exact UTF-8 formal text, with no normalization (the text contains ℝ, ℕ and ∑). The span is recorded as in `SA.gen_audit_tasks` (SA:718-739; the span is `[a, a+len(new)]`, SA:737; whether a minimal-diff span is preferred is OPEN, holders line author and reviewer). Until R6-O25 lands, the informal side of a T1 pair is the Lean docstrings of `Statement.lean`, not the paper's prose."

**Reason:** IP:20; the existing generator records `[a, a+len(new)]` at SA:737-738 and `oracle_f6` matches the span exactly (SA:741-751). OPEN, holder line author with the reviewer: a deletion-only defect has an empty minimal-diff span, while `n_spans` assumes `start < end` (SA:703). Whether such defects are excluded or given a rule is not decided here. Also OPEN: whether the docstring side is accepted as faithful prose. The docstring text has not been compared with the paper in this draft.

## 11. P0 and B0 consequences

**Location:** PD section 9 table notes, after `B0′ and B1′ size H2 only; ... (R6-O4, R6-O17).` (PD:115). Add:
> "P0 is unaffected: its prompts are synthetic F1 only (PD:132). B0′ and B1′ draw their one task set from one family the line author names (R6-O4). If that family is F5 or F6, `t1`, `t2` and `t3` enter that pool only after the pilot generators are built and reviewed (R6-O26) and sealed (R6-O27); a sub-generator added to an already frozen pool voids the freeze (amendment 4). Pilot and main pools stay disjoint (D2, PD:164)."

**Reason:** PD:115, PD:132, PD:164; IP:62. No call count, size or GPU-hour changes: those stay R6-O10 and R6-O12.

## 12. PL amendments

**PL Part II section 1** (`## 1. Task suite R6-TS`, PL:188), after the family table. Add:
> "Sub-generators `t1` (F6), `t2` and `t3` (F5) draw candidate statements from the VP != VNP paper (RV). Truth comes only from our exhaustive checker or from a planted edit; no result about them is evidence about that paper."

**PL section D** (`## D. Executable research loop`, PL:131), after the executable-predicate rule. Add:
> "Generator modules may supply reviewed, bounded, pure functions through the per-task `registry` argument of `PR.parse`. This is the only exception to 'not available in the first implementation', and it never runs agent-supplied code."

**Reason:** IP:57, IP:60.

## 13. Checked and not checked

Checked: `PR.parse` takes a `registry` argument (`lab/r6_predicates.py:11,165`). No new family, and no change to Holm, the H2 primary, DA or SC (IP:11, IP:30); the G1 fixture is a test file, its scope question is R6-O29. Not checked: line numbers of RV (being revised, IP:5); what `SS.seal` accepts for a pair file. Nothing was run.
