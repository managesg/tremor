# VP != VNP paper: integration plan for TREMOR (R5/R6)

Written 2026-11-26 by the TREMOR coordinator (Opus 5.5) on seabridge-spark, HEAD `d0101c9`. Offline: no network, model call, GPU process or key. One new file; nothing else edited, run, registered or committed.

Keys: RV = `docs/reports/tremor/VPVNP_CLAIM_REVIEW_20261126.md` at `d0101c9` (being revised; line numbers may shift). PL = `prereg/R6-pvsnp-research-line-plan.md`. PD = `prereg/R6-protocol-draft.md`. PR, SA, SC = `lab/r6_predicates.py`, `lab/r6_stage_a.py`, `lab/r6_scorecard.py`. `L<n>` = paper text line as cited in RV.

Standing rules (Opus review of RV): faithful T1 pairs cannot come from our damaged extracted text; the paper's lemmas are never relied on as true; no milestone changes status, because the bound does not apply to Boolean circuits.

## 1. How it integrates

The paper adds three things to R6. First, a new source of mechanically checkable tasks: its elementary finite steps (T3) and its formal-identity versus 0/1-agreement distinction (T2, L551-L554) become F5 lemmas, and its short statement file becomes F6 audit pairs (T1), a target for the Definition Audit arm on a step that only AI readers have done (L3799). Second, a fixed reference point for gate G1 on an algebraic route: filled from the paper's own words, its scorecard fails G1 as coded, because relativization and algebrization are "not analysed" (L157-L158; `SC:252-257`); we keep that as a regression fixture and a scope question, not a relaxation. Third, a worked example of the formal-statement semantic gap, and of the layout for the R6 plan's M4 statement pack: a short statement file that depends only on the library, kept apart from proofs (RV section 4). It changes no TREMOR milestone (M1-M10), R6 milestone or lens; it makes no Boolean or P vs NP claim; and no step uses the paper's lemmas or bound as true. Every T2 and T3 label comes from our own exhaustive checker, and no T1 "faithful" label comes from text we cannot trust. Holm, the H2 primary and DA stay as they are. Results measure agents, never the theorem.

## 2. Task map

| | T1 Definition-Audit pairs | T2 formal identity vs 0/1 agreement | T3 finite lemmas, exhaustive |
|---|---|---|---|
| R6 family | F6 | F5 (sub-generator `t2`) | F5 (sub-generator `t3`) |
| New files | `lab/r6_t1_audit_pairs.py`; `lab/tests/test_r6_t1_audit_pairs.py`; later the data file `data/r6/t1/pairs.json` (sealed, see section 3) | `lab/r6_t2_identity.py` (worker A), `lab/r6_t2_identity_b.py` (worker B, independent); `lab/tests/test_r6_t2_identity.py` | `lab/r6_t3_lemmas.py`; `lab/tests/test_r6_t3_lemmas.py` |
| Agent output | faithful, or defective plus span | per lemma: true, or false with a counterexample (a 0/1 point, or a monomial) | true, or false with a counterexample |
| Oracle | planted label and exact span, reusing `SA.oracle_f6`. Spans are code-point offsets `[start, end)` on the exact UTF-8 text, with no normalization (the text contains ℝ, ℕ and ∑). Each defect is a single edit, checked as in `SA.gen_audit_tasks` | Two F5 predicates per instance over `{PERM_m, HC_m}`, `m <= 4`, over `F_2` or `F_3`: (i) agreement on all `2^(m^2)` 0/1 points; (ii) equal coefficient at every exponent vector up to the degree bound, so the domain is the monomials. Expansions are precomputed per task and reached through a per-task registry closed over the circuit (int in, int out, under 2^64). Labels count only when A and B agree | `PR.check_lemma` over a declared domain. (a) and (b) need only `popcount`, `bit`, `sum` and `range`, with the subset as a bitmask, `k <= 14`. (c) and (d) take `Mat_mu(F_2)`, `mu <= 3`, as 9-bit ints through a registered `rank_f2`; (d) runs over pairs `x = a-b`, `y = b-c` (512² points, not 512³ triples), integer-only: `r1 <= r2+r3` or `(r1-r2-r3)² <= 4 r2 r3` |
| Cost | Authoring and sealing pairs (RV estimates about 16; the count is set at R6-O3); no compute | Seconds of CPU per instance | Minutes of CPU, plus a review of `rank_f2` |
| Arms and hypotheses | DA; H2 (pooled stratum F6) | RT; H2 (pooled stratum F5) | RT; H2 (pooled stratum F5) |
| Uninformative if | unclean source; auditor saw the file; a defect fails to elaborate (syntax alone finds it); ceiling | agents run code (ceiling); proposer rejects nearly every false lemma (D16 d) | the same RT condition; these are the paper's easiest steps |
| WAITING on | **the repository's `Statement.lean` at `11b6c7e`** for the formal side, **and** a clean prose side. The prose must be transcribed twice independently from the PDF and compared. Without both, no pair data exist | nothing | nothing (labels are ours; the paper only suggests statements) |
| Buildable now | The module: load the text, apply a defect spec, check uniqueness, record the span, seal the hook. Tested on a toy fixture **of our own**, not the paper's text | All of it | All of it; (a) and (b) first |

Notes:
- **H3 and H5** run on one `h35_family` (`SA:886-943`). A T-task enters H3 or H5 only if its family is chosen as `h35_family`; nothing here proposes that.
- **T1 defects:** the eight single edits of RV:126. RV:138's exploratory Euclidean question stays out of the scored pool (no oracle in our predicate language).
- **G1 fixture** (`lab/tests/test_r6_scorecard_g1_algebraic.py`, SC untouched): `lens: algebraic`, `claim_type: lower_bound`, relativization and algebrization `open` (L157-L158), `kernel_checked: false` (RV:121); asserts `G1_barrier == "fail"`.

## 3. Amendments (exact sentences; none applied by this file)

**PD section 5, after the F6 row's table** (task sources):
> "F5 also draws from the sub-generators `t2` (`lab/r6_t2_identity.py`, formal identity versus 0/1 agreement) and `t3` (`lab/r6_t3_lemmas.py`, finite lemmas suggested by the VP != VNP paper); F6 also draws from `t1` (`lab/r6_t1_audit_pairs.py`). Every label comes from our exhaustive checker or from a planted edit, never from the paper. No F7 is added: the scorecard's `FAMILIES` and the pooled H2 stratum (D9) stay unchanged, and per-sub-generator results are descriptive."

**PD section 5, "Predicates" paragraph, append:**
> "A generator module may pass a per-task registry to `PR.parse` (the `registry` argument). Each registered function counts one step, so it lies outside the step limit. Each such function is therefore reviewed independently, with every targeted mutant killed, and named in `scorer_ids`. It takes int arguments, returns an int below 2^64, and closes over precomputed per-task data. Functions that evaluate a given arithmetic circuit or compute `rank_f2` are not circuit-size functions; R6-O23 is unchanged. The PR pin (`5108519`) is unchanged."

**PD section 13, new rows:**

| ID | Decision still needed, and the method | Holder | Person |
|---|---|---|---|
| R6-O25 | T1 source: the formal side only from `Statement.lean` at `11b6c7e3c927df2658f513b6b68ea7f8929c62c5`, retrieved under a gated request, with sha256 recorded; the prose side from two independent transcriptions of the PDF (path and full sha256, prefix `882f5eef`, recorded first; the PDF is not in this repo) that agree character for character. Working copies stay outside the sealed root. Until both exist, `t1` has no data and is excluded from every pool | owner (clone approval); line author | **yes** |
| R6-O26 | Build and review `t1`, `t2`, `t3` and the G1 fixture under R6-O5 rules: an independent second implementation for `t2`, mutants killed, independent Opus review | line author; reviewer | no |
| R6-O27 | Seal, under R6-O3: the T1 pair file, faithful rate and defect spans; the `t2` and `t3` seeds and false rate; the share of each sub-generator in the F5 and F6 pools. Pilot draws stay disjoint from main draws (`tremor_sealed_inputs.no_overlap`) | custodian | **yes** |
| R6-O28 | Contamination: no prompt, system card or tool context shows the paper or `Statement.lean`. DA reports `t1` as a separate descriptive stratum labelled "public source, exposure unknown" | line author | no |
| R6-O29 | G1 scope for arithmetic-circuit routes: does "not_applicable with a reason" cover relativization and algebrization, which PL:75 calls Boolean-oracle notions? Until decided, G1 stays as coded and the fixture expects `fail` | protocol owner; independent reviewer | no |

**PD section 14, item 4, append:**
> "`task_family_revision` also names the `t1`, `t2` and `t3` generator commits and the `Statement.lean` sha256; `scorer_ids` names the `t2` oracle functions (A and B), `rank_f2`, and every per-task registry function."

**PD section 14, item 3, append:**
> "For `t1`, the protected input is the pair file (labels and spans). Its faithful text is public, so the seal hides only which pairs are defective and where."

**PL Part II section 1, after the table:**
> "Sub-generators `t1` (F6) and `t2` and `t3` (F5) draw candidate statements from the VP != VNP paper (RV `d0101c9`). Truth comes only from our exhaustive checker or from a planted edit; no result about them is evidence about that paper."

**PL section D, after the executable-predicate rule:**
> "Generator modules may supply reviewed, bounded, pure functions through the per-task `registry` argument of `PR.parse`; this is the only exception to 'not available in the first implementation', and it never runs agent-supplied code."

**Freeze-record effect.** Holm stays {H1, H3, H5, RT}, size 4; inherited pins are unchanged; sub-generators joining a pool after a freeze void it (new protocol sha256 and record).

## 4. Work queue (SUBTASK lines)

**Convention.** The lane may add **one** SUBTASK line, and only when no open line remains. Lines 56 and 57 of `docs/reports/TREMOR_GOAL_AND_PLAN_20261123.md` are still open. Paste these one at a time, each after the previous one is ticked. The order puts what is buildable offline now first.

1. `- [ ] SUBTASK <date>: build lab/r6_t3_lemmas.py part 1, T3(a)(b) as F5 sub-generator t3: predicates with popcount/bit/sum/range only, declared bitmask domain k<=14, planted false variants (changed constant), labels from PR.check_lemma only; tests lab/tests/test_r6_t3_lemmas.py; mutants: flipped comparison, off-by-one k, label taken from template; Opus review. Reason: R6-O26, offline, no registry, no gate. Est. 2 h.`
2. `- [ ] SUBTASK <date>: T3(c)(d) in lab/r6_t3_lemmas.py: rank_f2 for mu<=3 as a per-task registry entry, checked against a brute-force span count; transversal predicate; triangle predicate over pairs (x+y), integer-only; false variants drop "transversal" or change a constant; tests and mutants (rank off by one, wrong field), Opus review. Reason: R6-O26; registry rule in section 3. Est. 3 h.`
3. `- [ ] SUBTASK <date>: build lab/r6_t2_identity.py (worker A, sparse expansion) and lab/r6_t2_identity_b.py (worker B, separate representation, not shown A): circuits in list form for PERM_m/HC_m m<=4 over F_2/F_3, planted "identity", "0/1 only" (adds sum (x_i^2-x_i) h_i), "neither"; two F5 predicates per instance; A=B on every generated instance; tests lab/tests/test_r6_t2_identity.py; mutants: char ignored, x^2 reduced to x, cycle filter dropped in HC; Opus review. Reason: R6-O26. Est. 4 h.`
4. `- [ ] SUBTASK <date>: build lab/r6_t1_audit_pairs.py on a toy fixture of our own (not the paper): load UTF-8 text, apply defect spec, single-edit check, code-point span, oracle via SA.oracle_f6; tests lab/tests/test_r6_t1_audit_pairs.py; mutants: byte offsets instead of code points, NFC normalization, second occurrence accepted; Opus review. Reason: R6-O26; data waits on R6-O25. Est. 2 h.`
5. `- [ ] SUBTASK <date>: add lab/tests/test_r6_scorecard_g1_algebraic.py (G1 fixture, section 2); SC untouched; mutant: G1 passing on "open"; Opus review. Reason: R6-O29 regression point. Est. 30 min.`
6. `- [ ] SUBTASK <date>: draft the section 3 amendments into prereg/R6-protocol-draft.md and the R6 plan; tests/mutants: none (docs only); independent Opus review (R6-O20 scope extended). Reason: protocol must name the sources before any freeze. Est. 1 h.`

**After the gates only:** T1 data, then custodian sealing (R6-O25, R6-O27).

**Dependencies.** Lines 1-5 are independent; 6 follows 1-5 so it cites commits; T1 data follow R6-O25; sealing follows R6-O2.

**Acceptance (each line).** Lab suite green with the count in STATUS; listed mutants killed; T2 A=B on every instance; Opus ACCEPT; only the line's own paths touched.

**Stop conditions.** T2 A/B disagreement after one fix attempt; a registry function needing unbounded work (redesign as a precomputed table); any need for network, project Lean, Mathlib or a model call (file the request below); two failed reviews on one line (escalate in STATUS); expiry 2026-12-10T04:50Z (PD:102).

## 5. Gated requests (prepared, not done)

**G-a. Retrieve the repository (network; new clone).**
Approver: the owner (AGENTS.md: new clones need the owner; network on the Spark). Target: under the git-ignored `data/` (`.gitignore:7`), untrusted, read-only after checkout.

```
D=/home/adelmar/SeaBridgeAI/murmuration/data/external/formal-math-11b6c7e
mkdir -p "$D" && cd "$D" && git init -q
GIT_TERMINAL_PROMPT=0 GIT_LFS_SKIP_SMUDGE=1 git -c credential.helper= -c core.hooksPath=/dev/null \
  -c protocol.file.allow=never fetch --depth 1 --no-recurse-submodules \
  https://github.com/anthropics/formal-math 11b6c7e3c927df2658f513b6b68ea7f8929c62c5
git -c core.hooksPath=/dev/null checkout -q --detach FETCH_HEAD && chmod -R a-w "$D"
```

**Checks.** Expected tree and file hashes cannot be known in advance and are not invented. Check: `git rev-parse HEAD` equals the full SHA; record `HEAD^{tree}`, the file list and sizes, and the sha256 of `Statement.lean`; its `import` lines are Mathlib only (L587-L589); its definitions match RV's printed L590-L687; a second fetch on the PC gives the same tree id and sha256. **Never** run `lake`, `lean` or any script inside the clone, or init submodules.

**G-b. Mathlib, or Lean on the project (install gate, Safety rule 2).** The local `data/tools/lean/lean-4.35.0-linux_aarch64/bin` (`lean`, `lake`, `leanchecker`, `lean4lean`, `nanoda_bin`) can elaborate core-only files such as our toy fixtures. It cannot elaborate `Statement.lean` (no Mathlib on this host), and it is not the paper's pin (Lean 4.33.1, Mathlib `0df444a360e...`), so it cannot give the stated rebuild. **Request:** the owner approves fetching that toolchain and Mathlib commit into `data/tools/`, with a disk and CPU budget. Only then: check that each T1 defective variant still elaborates (otherwise the defect is detectable by syntax alone) and list our own axioms. None of this is a semantic check.

**G-c. The OpenAI paper and the independent audit (network).** For each, the owner names the exact document (RV:114: the only OpenAI item cited is [OAI26], on border determinantal complexity) and approves a read-only fetch; we record its sha256. Until then neither is evidence.

## 6. Risks

- **Semantic-gap trap.** A kernel check shows the formal statement follows from the axioms, not that it means VP != VNP. Keep `kernel_checked` and the definition audit separate; G6 reads only DA; never record the paper's report as our `kernel_checked: true` or `proved_in_artifact`.
- **Contamination.** Public paper and file: `t1` may measure recall (R6-O28).
- **Overclaiming.** Results are about agents (G3; PD section 2).
- **Label error, ceiling, registry bypass.** A wrong "faithful" label voids T1; T2 is trivial with code execution; a registered function is guarded only by review.

## 7. Owner summary

1. The paper gives R6 new checkable test material: F5 lemmas (T2, T3) and F6 audit pairs (T1). It also gives a G1 reference case. No new family is needed.
2. Nothing changes status: no milestone, no Boolean or P vs NP claim, and no reliance on the paper's lemmas being true.
3. T3, T2, the T1 module and the G1 fixture are buildable offline now (six queued SUBTASK lines, about 12 hours of worker time).
4. T1 data wait on the repository's `Statement.lean` plus two clean transcriptions of the prose.
5. Your decisions: approve the read-only clone of `11b6c7e` (section 5); optionally the Lean 4.33.1 + Mathlib install; name the OpenAI paper and the audit you meant.
6. The main risks: a Lean check is not a meaning check; agents may already know the paper; results are about agents only.
