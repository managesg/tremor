# Review of the claim "VP != VNP over every field" against the TREMOR R5/R6 lines

Written 2026-11-26 by the research reviewer (Fable 5.2) on seabridge-spark. No network, model call, GPU or key. One new file; nothing else edited; nothing committed.

**Input.** Extracted text of `vp-vnp/paper.pdf` (author line "Claude, Anthropic"; PDF sha256 prefix `882f5eef`; commit `11b6c7e3c927df2658f513b6b68ea7f8929c62c5` of `github.com/anthropics/formal-math`), 4,031 lines, read as data. `L<n>` is a line of that text.

**Read in full:** L1-L1010 (Sections 1-3, references, appendix introduction), Appendix D, K.4-K.5, L, M, N, Q. Appendices A-C, E-J, O, P: headings only. **Not seen:** the Lean repository, any OpenAI paper, the Toledo audit, the video. "Toledo" and "73,000 lines" do not occur in the paper text (grep: 0 hits); they come from the owner's message.

**Standing limit.** This review does not say the proof is correct and does not say it is incorrect. Reading cannot certify about 50 pages of appendix, and the paper says four of its printed proofs are not complete on paper (L959-L965).

PL = `prereg/R6-pvsnp-research-line-plan.md`. CK = `docs/reports/tremor/PVSNP_BRIEFING_UNVERIFIED_CHECKLIST.md`.

---

## 1. State of evidence

### 1.1 What the document claims

| Item | Claim | Where |
|---|---|---|
| Theorem 1.1 (`thm_allfields`, = M.3) | An absolute `c > 0`; for each `p` (zero or prime) an `m0`; over every field of characteristic `p`, for `m >= m0`, every circuit for `HC_m`, and for `PERM_m` if `p != 2`, has more than `m^{c (log m)^{1/3}}` gates. `log = log2` | L65-L70, L3531-L3535 |
| Corollary 1.2 (= M.4) | Over every field VP is a proper subset of VNP | L74, L3546 |
| Theorem 1.4 (= N.5) | The same bound for approximating (border) circuits; VNP not contained in the closure of VP | L88-L89, L3667 |
| Model | Circuit = finite list of polynomials, each a variable, a constant, or sum/product of two earlier entries; size = list length | L162-L169 |
| Classes | VP: variables, degree and size polynomially bounded. VNP: sum over bit vectors of a VP family | L170-L176 |
| Per-case bounds | Flat: `2^{(log m)^{4/3}/1600}`. Contracting: `2^{c (log m)^2 / log log m}` | L2134-L2137, L3402-L3405 |
| Strength, in the paper's words | "Our lower bound is quasipolynomial, whereas the best upper bounds are exponential"; "there is still plenty of room to tighten the bounds" | L54-L55 |

**Architecture as the paper describes it** (Figure 1, L227-L265; Table 1, L983-L1000): a common part (tensors, spectral points, "prices", an inequality for two crossing wires, nonpositive curvature), then a dichotomy (Theorem 2.2/D.2: "at least one of the two hypotheses ... holds", L289-L290), then one lower-bound argument per case. The permanent enters "once in each case" by substitution (L320-L323); the circuit is inspected at two other steps (L326-L337).

**What it says it does not prove.**
- P vs NP: "it does not settle that conjecture ... our superpolynomial bound does not apply to Boolean circuits" (L13-L15); "no implication in the other direction is known" (L35-L36).
- Which case holds: "We do not know which of the two hypotheses holds, even over R, nor do we show that the two are mutually exclusive" (L291-L292).
- `m0` is "not effective" (L3456); the exponent 1/3 is not claimed optimal (L70).
- Relativization and algebrization: "We have not analysed" (L157-L158). Derandomization: "not worked out" (L159-L160).
- Remark N.6 (determinantal complexity) is "not formalized in Lean" (L134, L3675).
- Human review: "No human mathematician has checked the proofs" (L578-L579); "Whether the statements say what is meant was judged only by AI readers" (L3799).
- Completeness on paper: for I.1, H.2(d,e), J.3, N.4, "the contracting case, and with it every main result, rests on Lean at these points" (L961-L965).

### 1.2 Internal-consistency checks done (reading and arithmetic only)

| # | Check | Result |
|---|---|---|
| 1 | `m^{c(log m)^{1/3}}` vs `2^{Omega((log m)^{4/3})}` (L9, L53, L3422) | The same quantity, since `m = 2^{log m}` and `log = log2` (L70). Superpolynomial: `c (log m)^{1/3}` exceeds any fixed `C` (L3439) |
| 2 | Contracting bound dominates the flat one (L3436) | `(log m)^2/log log m >= (log m)^{4/3}` for large `m`. Consistent |
| 3 | Flat parameters (L445-L447, L477-L480, L2134-L2139) | `k = r^2`, `l = 100r`: `log m ~ 100 r^3`, `log L >= l k^{3/2}/16 = 6.25 r^4`. With `200 r^3 <= log m` that is about `(log m)^{4/3}/187`; the printed `1/1600` is weaker, so not contradicted |
| 4 | Balanced sets (L397, L443, L453) | `|S|(k-|S|) >= 2k^2/9` and "a vector of length at least `k^{3/2}/9`": both hold in our exhaustive standard-library check for `k = 3..14` (an inline Python 3 script run once this session in a sandboxed subprocess, not saved in the repo: for each `k` and each `S` with `k/3 <= |S| <= 2k/3` from `itertools.combinations`, it tests `9|S|(k-|S|) >= 2k^2` and, with `w = 2v` built by adding 1 at coordinate `a` for each pair `a < b` with `a` in `S` and subtracting 1 for each with `b` in `S`, `81|w|^2 >= 4k^3` in exact integers). Two elementary steps, nothing more |
| 5 | Quadrilateral bound (L280-L286, L1717-L1730) | Subadditivity of `D^2` gives `D(mu) <= sqrt(mu) D(1)`; Step 2's chain forces equality. Consistent given Lemma C.4(b), not read |
| 6 | Quantifiers, prose vs printed Lean (L65-L69, L630-L632) | `exists c > 0, forall p, exists m0, forall F [Field F] [CharP F p], forall m >= m0, forall s`. Matches: `c` absolute, `m0` depends on `p` only |
| 7 | `Beyond` (L625) | Exponent typed `(1/3 : R)`, so not natural-number division. Strict inequality matches "more than" |
| 8 | `Computes` (L607-L611) | "At most `s` gates", inputs strictly earlier, formal equality in `MvPolynomial`. Matches L162-L169 |
| 9 | `perm`, `hc` (L614-L621) | `perm` uses `X (sigma i, i)`, the prose `x_{i,sigma(i)}` (L44): equal after `sigma -> sigma^{-1}`. Not checked: that `IsCycleOn Set.univ` means "one cycle through all points" for every `m` |
| 10 | `VP`, `VNP`, `Separation` (L663-L682) | VP bounds variables, total degree and size; VNP sums a VP family over bit vectors; strict subset for every field. Matches L170-L176 |
| 11 | Characteristic | `PERM` for `p != 2` only (L70-L72; entries `+-1/2`, L567-L570); `HC` for all fields ("needs no division", L572). Consistent across Sections 1, 2.5, M |
| 12 | Use of VNP-completeness | The separation needs only membership: `PERM` by Ryser's formula (L3445-L3453), `HC` at L3547. The reductions to `PERM`/`HC` are proved in the paper (Prop. E.1, M.2; L3490-L3517). Valiant's completeness theorem is cited for framing (L49-L51), not as a step |
| 13 | Extraction damage | Overlines are lost: "VNP not in VP" at L76, L89 means the closure. L475-L479 have displaced radicals |
| 14 | Discrepancy | [Guo26] is described as a bound "of order `m^2 log m`" (L139); its title reads "`n^2 log log n`" (L792). Check against the source |

### 1.3 Citations we cannot verify here (all "citation to be verified")

- Complexity background: [Bür00b] (L34, L188; conditional on a Riemann hypothesis); [Ber84] (L94); [Str73, BS83] as best prior general bound (L100); [Hya79, VSBR83] (L399); [JS82, MP08] (L336); [Rys63, Gly10] (L3445); [Val79, Mal03, FPV13] (L3526, L3547).
- Mathematics used: [Str87, Str88, WZ26] (L210); [BT72, BH99, Stu03] (Appendix O says it proves the facts used; not read); [Eis95, Thm 4.19] (L540, L3365); the Nullstellensatz (L3485).
- Barriers and GCT as characterized (L124-L158): [EGOW18, GMOW19], [FSV18, GKSS17], [RR97], [CKRST20, KRST22], [BGS75, AW09], [MS01, MS08], [IP17, BIP19], [MR04, CCL10, Yab15, LMR13].
- Every 2026 item (L104-L141): [OAI26], [She26], [She26b], [Guo26], [KV26], [Raz26], [Cur26].
- Tooling (L584-L586, L3790-L3798): Lean 4.33.1, Mathlib commit `0df444a360e...`, no `sorry` outside `Challenge.lean`, axioms `propext`, `Classical.choice`, `Quot.sound`, Comparator and `nanoda` rechecks. These are the paper's statements about a repository we have not seen.

---

## 2. The technique, as the paper describes it

**Spectral points and the geometry.** A spectral point is "a function phi from the V-tensors to [0, infinity)" that is normalized, multiplicative and subadditive under restriction (L210-L214). On a wire (a `q x q` identity between two parties) its value is `q^{d_phi(u,v)}` for "a pseudometric d_phi on V with values in [0, 1]" (L217-L218). "Ranks become distances" (L387): a tensor of rank `r` across a partition is a restriction of wires to two hubs joined by a wire of dimension `r`, which gives inequality (2.3), "where the rank enters only through the last term" (L395). A circuit with `L` gates splits a block-multilinear polynomial into at most `2^k` pieces, "each of rank at most L across a split" (L364-L365). A price is "a pointwise limit of functions c d_phi" (L273). "Prices have nonpositive curvature" (L282), by "the inequality of Bruhat and Tits" (L417), and "every price is induced by a map into" a CAT(0) space (L419-L421). The spectral points "are not explicit at all, since they are only known to exist by Zorn's lemma" (L151-L152).

**The split.** Both are "hypotheses on the field k" (L200).
- *Flat:* "All finite subsets of all Euclidean spaces, with their metrics, are prices" (L1700).
- *Contracting:* some `mu >= 2`, `1 <= s`, `s^2 < mu` with `D(mu) <= s D(1)` for all prices on `Mat_mu(F_2)` (L1701-L1702): "every price ... falls short of a Euclidean rectangle by a fixed factor" (L285-L286).
- *Dichotomy:* if contracting fails, "a compactness argument gives prices ... with equality in the quadrilateral inequality, and the flat rectangle property of CAT(0) spaces ... puts a solid cube" into a price (L422-L427).

**Flat case** (L435-L480): the polynomial `f_{k,l}` of "a network of wires on the complete graph" (L296); ends and hubs placed in `R^k`; "(2.4) gives the bound directly" (L371-L372).

**Contracting case** (L482-L544): "the argument is indirect". Contraction yields "a Poincaré inequality" on unitriangular groups over `F_2` (L487-L492); "a form of Strassen's duality" gives "rerouting laws" (L492-L496); every network is "a sum of values of tree networks" (L497); "computations can be cut" (L499); a small permanent circuit would give an "accelerator" (L524-L526); a program applied to itself "has a value V with V = 1 + V, which is impossible in a nonzero ring" (L544). The paper calls it "an indirect diagonalization" (L3397).

**Barriers, from the paper's own statements only.**
- *Rank methods:* "In the flat case we use, instead of ranks, functionals in a variant of Strassen's asymptotic spectrum" (L147-L149). No proof of evasion is claimed.
- *Algebraically natural proofs:* they "may be unable to prove superpolynomial lower bounds for general circuits, and there is evidence in both directions" (L153-L156); "In the contracting case no property of polynomials other than low degree is used, and the argument ends in a diagonalization" (L156-L157). No claim of evasion; on the flat case **silent** beyond the Zorn remark.
- *Relativization and algebrization:* explicitly **not analysed** (L157-L158).
- *Razborov-Rudich natural proofs proper:* cited only as the origin of the analogue (L154); otherwise **silent**.

**Boolean setting.** A Boolean circuit for `HC_m` "may compute any polynomial g = HC_m + sum (x_i^2 - x_i) h_i, and our theorem says nothing about such g" (L551-L554). "The proof breaks at the two steps that look inside the circuit" (L555). "Nor can a large Boolean circuit take the place of the program that the contracting case refutes" (L562-L563). For the determinant the proof "fails at one point only: the reduction of clause sums to the permanent" (L548).

---

## 3. Relation to our work

### 3.1 R6 research line

| Our item | Effect |
|---|---|
| **Lens 2, algebraic and GCT (PL:71-76)** | A primary source for the lens we did **not** select. The choice (PL:108) stands: PL:75 excluded Lens 2 because R and A "are defined for Boolean oracle classes", and the paper's "not analysed" (L157) leaves that reason in place. The paper says it "does not follow" GCT (L129) |
| **PL:73 wording** | PL:73 equates VP vs VNP with "is the determinantal complexity of perm_n polynomial". That is a neighbouring statement, not the same one. The reason is classical and does not rest on the paper: the determinant has polynomial-size circuits ([Ber84], **[ctv]**), so polynomial determinantal complexity would put the permanent in VP, and the converse direction is not given. (The paper's own Remark N.6 draws a consequence of this kind but is the one statement it says is not formalized in Lean, so we do not lean on it.) Suggested fix for the plan owner: "do `perm_n`/`HC_n` have polynomial-size arithmetic circuits; superpolynomial determinantal complexity follows from VP != VNP and is not the same statement". A Definition Audit finding on our own plan |
| **PL:74 [ctv] items** | The paper cites the same results as [MR04], [IP17, BIP19] (L128-L136). A second citing document is not verification; they stay [ctv] |
| **PL:76 sub-problem** | Unchanged. The paper says it does not use ranks of partial derivatives (L116-L117, L147-L149) |
| **Lens 1 (PL:64-69)** | No change. No Boolean circuit bound (L13-L15) |
| **Gate G1 (PL:62, PL:177)** | A scorecard for this paper with `claim_type: lower_bound` would **fail G1 as coded**: relativization and algebrization would be `open` (`lab/r6_scorecard.py:252-257`). That is a fact about our gate, written for Boolean routes, not about the paper. Open question for the protocol owner; no change proposed here |
| **G2** | The sealed `briefing_keywords` list is not visible to us (CK:53). Until the custodian changes it, a scorecard claim that mentions this result keeps status `from_briefing_unverified`. Do not add a schema status for it |
| **M1-M5** | **No milestone changes status.** M1 is Boolean, `n <= 4`, with a different cost model (inputs free, 16 operations; PL:150) from the paper's (leaves counted, `+` and `x` only; L168) |

**Checklist rows (CK).** Only one row changes status.

- **Legend (CK:7):** add "**PS** = primary source retrieved, proof not verified by us (the document was read; its proof, its formalization and its citations were not checked)".
- **Row 9** (CK:21): from `FB` to the new value `PS`. Proposed wording:
  > 9 | "VP != VNP over every field" (Claude, Anthropic; released 2026-11-23 per the owner; PDF sha256 prefix 882f5eef; formal-math commit 11b6c7e). Claims a `2^{Omega((log m)^{4/3})}` arithmetic-circuit lower bound for `HC_m` (every field) and `PERM_m` (characteristic not 2); in its own words the bound "is quasipolynomial, whereas the best upper bounds are exponential". Says it does not settle P vs NP, does not apply to Boolean circuits, and has not been checked by a human mathematician. | Paper text retrieved; Lean repository not seen | PL:56 | PS | A rebuild at the stated pins; our own axiom listing; a human audit of `Statement.lean`; expert review
- **PL:56** proposed wording: "'VP != VNP over every field' (Anthropic; released 2026-11-23 per the owner, the paper gives no date) **[primary source retrieved, proof not verified by us]**; algebraic only, by its own statement".
- **Unchanged:** row 21 (Valiant, CL); row 17 (Lean semantic gap, CL; the paper is a first-hand example, L3799-L3800); rows 11-13 (barriers, CL; the paper's keys agree with ours, which is not verification); row 2 (Williams 2025, FB; the paper's bibliography lists [Wil25] at L939, a lead only); rows 3-7 (ETH; the paper does not mention ETH, grep 0 hits).
- The briefing says "claims" (plural). We retrieved one paper. The only OpenAI item it cites is a manuscript on border determinantal complexity [OAI26] (L137-L138, L865), which by this paper's description is not a VP != VNP claim. Whether that is "the OpenAI paper" of the owner's message is unknown.

### 3.2 Agent-performance line (R5; R6 Part II)

- **R5 hypotheses H1, H2, H3, H5:** no change. The paper reports nothing about teams, forecasts or confidence; on how it was made it says only "discovered by an internal research Claude model" (L16).
- **F6 Definition Audit arm (PL:199, PL:227-229):** the paper names the step this arm measures and says only AI readers did it (L3799). Its statement file (L590-L687) is real, short and self-contained: material for audit pairs (T1).
- **Red Team arm (PL:219-225):** the paper's elementary finite steps can be planted as true or false F5 lemmas (T3). The override rule is unchanged.
- **`lab/r6_scorecard.py`:** the vocabulary already has `algebraic`, `arithmetic_circuit`, `matrix_dim_n` and a `lean` block. Filled by us for this paper: `kernel_checked: false`, `sorry_count: null`, `axioms: []` (the paper's list is its report, not our observation); never `proved_in_artifact`.

### 3.3 Proposed new test tasks (none is run or registered by this file)

**T1. Definition Audit pairs from the statement file (F6). Status: WAITING on a clean source.**
- *Task:* the paper's prose (L65-L69, L162-L176) paired with a Lean-style definition. Faithful pairs must come from the repository's `Statement.lean` once it has been retrieved, or from two independent transcriptions of the PDF that are compared and agree. They cannot be cut from our extracted text: it is damaged (sum and product signs displaced at L614, L620, L672-L679; `N` and `R` standing in for the natural-number and real-number symbols), so a "faithful" fragment taken from it would itself be defective. Defective pairs carry one planted defect at a fixed span: `(1/3 : R)` made natural-number `1/3` (the bound collapses to `m^c`); `i < k` made `i <= k` in `Computes` (a gate may cite itself); the degree bound dropped from `VP`; `exists c, forall p` swapped; `IsCycleOn Set.univ` made `IsCycle`; `CharP F p` dropped; strict subset made subset; formal equality made agreement on 0/1 inputs.
- *Oracle:* planted label and exact span match, as F6 specifies.
- *Cost:* authoring and sealing about 16 pairs; no compute.
- *Uninformative if:* the faithful pairs were not taken from a clean source as above (then the labels are wrong and the task is void); the auditor has seen the file (public since 2026-11-23 per the owner; the paper gives no date); auditors hit ceiling; defects are found by syntax alone. **Limit:** "faithful" means "matches the paper's prose", not "matches the literature", which we have not verified.

**T2. Formal identity versus Boolean agreement (new arithmetic family, F2 style).**
- *Task:* given an arithmetic circuit in the paper's list form over `F_2` or `F_3` and a target (`PERM_m` or `HC_m`, `m <= 4`), answer: computes the target as a formal polynomial; agrees only on 0/1 inputs; neither. Planted instances add `sum (x_i^2 - x_i) h_i`, the paper's own construction (L554).
- *Oracle:* exact expansion to a monomial dictionary, plus evaluation on all `2^{m^2}` 0/1 inputs (at most 65,536). Standard library.
- *Cost:* one small module and an independent second implementation; seconds per instance.
- *Uninformative if:* agents may run code (a ceiling task); no errors appear without tools. It tests care with one distinction. Exact *minimum* size is not in the oracle: `m = 2` is trivial and `m = 3` is not known to be within exhaustive search.

**T3. Finite lemmas from the paper's elementary steps (F5 and the Red Team arm).**
- *Task:* predicates planted true or false: (a) every balanced `S` has `9|S|(k-|S|) >= 2k^2`, `k <= 14`; (b) the end-position vector has `81|2v|^2 >= 4k^3` (both true in our check); (c) on `Mat_mu(F_2)`, `mu <= 3`, transversal pairs have `rk(W + W') = rk W + rk W'` (L1671); (d) `sqrt(rk(a - a'))` satisfies the triangle inequality there. False variants change a constant or drop "transversal". Exploratory, with no label until two implementations agree: is `sqrt(rk)` on `Mat_3(F_2)` Euclidean (the paper says not, L1787-L1789).
- *Oracle:* exhaustive run under the step limit. Every true or false label comes only from our own exhaustive checker, never from the paper's say-so; the paper supplies the candidate statements, not their truth values.
- *Cost:* a registered `rank_f2` function and its review; minutes of CPU.
- *Uninformative if:* the proposer already rejects nearly every false variant (PL:225). **Limit:** these are the paper's easiest steps. The steps that carry the theorem (spectral points from Zorn's lemma, the duality, the cutting theorem, the diagonal) have no finite instance.

---

## 4. Formal proof structure

**What a Lean check gives, in this paper's layout.** `Statement.lean` "imports Mathlib and nothing else" (L587-L589); `Solution.lean` proves terms of exactly those types (L3785-L3788). If a rebuild succeeds and the axiom listing is as reported, what remains for humans is whether about 90 printed lines (L598-L687) say what "VP != VNP" means. The intermediate notions (spectral point, price, accelerator) need **no** audit for that. This is the structure to copy for our M4 statement pack: a short statement file that depends on the library only, kept apart from proofs.

**The semantic gap, item by item (what a Definition Audit must cover).**

| Item | Question for the auditor | In the printed file |
|---|---|---|
| Arithmetic circuit | Gates (no division), fan-out, free constants, formal polynomial vs function | L607-L611: `+`, `x`, any constant, reuse, formal equality |
| Size | What is counted; "exactly" vs "at most" | list length, leaves counted, "at most `s`" |
| VP | Is the degree bound present | yes, L664 |
| VNP | Is the summed family in VP; is the witness length bounded | yes; through the variable count, L676-L679 |
| Field, characteristic | `Field` vs `CommSemiring`; `CharP F p` | definitions over `CommSemiring`, theorems over `Field`, L631 |
| "Every field" | Universe of `F` | `Type u`; Q.3: `Solution` holds in every universe (L3814-L3819) |
| Constants | Order of `exists c`, `forall p`, `exists m0`; real exponent | L631, L625 |
| The polynomials | Index convention; `IsCycleOn Set.univ`; `m = 0, 1` | L614-L621; small `m` not checked by us |
| Border class | Laurent series vs rational functions | L640-L642; closure equivalence cited, "we do not use" (L3565) |
| Outside the file | Remark N.6; VNP-completeness | not formalized; not needed for `Separation` |

**"Hidden axioms" checks, and what they do not cover.** The mechanical ones: axiom listing of the final theorems; no `sorry`, `native_decide` or added `axiom` on the path; a clean rebuild at pinned toolchain and library commits; a recheck by an independent kernel. The paper reports all of these (L3790-L3798); we have observed none. `Classical.choice` is on its list and Zorn's lemma is used (L1018, L1142), so the result is non-constructive by the paper's own account. None of these checks covers the table above. That is the Definition Audit arm's job, and gate G6 should read only that.

**What we have locally (read-only check this session).**
- `data/tools/lean/lean-4.35.0-linux_aarch64/` with `PROVENANCE.json` (tag v4.35.0, sha256 `c8f0f8a3...`). `bin/lean --version` reports 4.35.0, aarch64. `bin/` also holds `lake`, `leanchecker`, `lean4lean`, `nanoda_bin`, `cadical`. None is on PATH: PL:133 is literally true but understates what exists.
- `formal/alloc_score/` is a Lake project pinned to `leanprover/lean4:v4.35.0`.
- Two other toolchain folders exist outside the repo: `/home/adelmar/aws-pilot-full-20261122/.elan` and `/home/ubuntu/aws-pilot-full-20261122/.elan`. Each holds one toolchain, `leanprover--lean4---v4.35.0`, and no Mathlib (directory listing only). No `~/.elan`.
- **No Mathlib** directory on this host (search from `/`, depth 7). **Lean 4.33.1 is not here either**: every toolchain found is 4.35.0.
- The paper needs Lean 4.33.1 and Mathlib at `0df444a360e...` (L3778-L3779). **Kernel check: NOT DONE, and not doable offline.** Lean was run only with `--version`.

---

## 5. Gaps and open questions

Needing a primary source we do not have:
1. The Lean repository at commit `11b6c7e`: file list, size, pins, the axiom script's output, whether `Statement.lean` there equals L590-L687.
2. A rebuild at the stated pins by someone other than the authors. The owner names an independent verification by Carlos Toledo; we have not seen it and the paper does not mention it.
3. The OpenAI paper the owner names, and which result it is.
4. Human review status. The paper says none at release.

Needing a human expert:
5. Does `Statement.lean` match the standard VP and VNP (section 4 table), especially `hc` and the border class.
6. Theorem D.2 and Appendix A (spectral points via Zorn, the duality): parts the paper calls complete on paper (L959-L960), the natural first target for a reader.
7. The four statements that rest on Lean alone (L961-L965): does the Lean form of "program", "accelerator" and "plain instance" mean what the prose means. This gap is *inside* the proof; it does not affect the final theorem if items 1, 2 and 5 hold.
8. The relation to relativization, algebrization and algebraic natural proofs, which the paper leaves open.
9. The [Guo26] discrepancy (1.2 row 14).

**Owner-facing summary (five lines).**
1. The paper claims a superpolynomial lower bound for arithmetic circuits computing the Hamiltonian cycle polynomial (every field) and the permanent (characteristic other than 2), hence VP != VNP over every field. In its words the bound "is quasipolynomial, whereas the best upper bounds are exponential". Its abstract says this does not settle P vs NP and does not apply to Boolean circuits.
2. We read the text only. Its statements, quantifiers, constants and printed Lean definitions are internally consistent as far as we checked; we cannot say whether the proof holds, and the paper says no human has checked it.
3. The method is a two-case split (flat or contracting) on the geometry of "spectral points"; the paper does not know which case holds and has not analysed relativization or algebrization.
4. Nothing in R6 or R5 changes status. Checklist row 9 moves from "from briefing, unverified" to "primary source retrieved, proof not verified by us"; one sentence of our plan (PL:73) should be corrected.
5. It is usable now as test material (three mechanical tasks). A real check needs the Lean repository, Lean 4.33.1 and Mathlib (neither is on this host; we have Lean 4.35.0 only) and a human audit of about 90 lines.

---

## 6. What we recommend we do NOT do

1. **Do not claim anything about P vs NP from it.** The paper denies the implication (L13-L15, L35-L37); gate G3 exists for this.
2. **Do not mark any R6 milestone or lens as advanced**, and do not select Lens 2 because of it.
3. **Never rely on the paper's lemmas, proof or bound as true** in any experiment, score, predicate registry or gate. T3 uses the paper only as a source of candidate statements; T3's labels come only from our own exhaustive checker. CK:9 holds: if the claim is retracted, nothing in R6 changes.
4. **Do not treat a Lean check as a semantic check**, ours or theirs. Keep "kernel-checked" and "definition audit" as two fields.
5. **Do not record `kernel_checked: true`, an axiom list or `proved_in_artifact`** on the paper's own report.
6. **Do not run Lean on the project, clone it or install Mathlib** without the owner's approval (Safety rule 2).
7. **Do not treat the cited audit, the OpenAI paper or the video as evidence** until retrieved, and do not attribute to the paper what only the owner's message says (the line count, the auditor).
8. **Do not relax G1** because an algebraic result now exists; decide the gate's scope on its merits.
9. **Do not use T1-T3 results as evidence about the theorem.** They measure agents.

Not checked: Appendices A-C, E-J, O, P beyond headings; the sealed keyword lists; `IsCycleOn Set.univ` in Mathlib; any citation.

## Addendum 2026-11-26: what could and could not be checked offline

Checked (regex over the extracted text, an internal-consistency check only, not a verification of any source): all 76 distinct citation keys used in the text before the bibliography appear in the bibliography (127 entries); 51 bibliography entries are not matched by the regex in the text (formatting may hide some). The bibliography has 8 entries dated 2026 that we cannot verify: `Cur26`, `Guo26`, `KV26`, `OAI26`, `Raz26`, `She26`, `She26b`, `WZ26`. The text cites `[Str88, WZ26]` for the variant of Strassen's asymptotic spectrum from which the paper's "spectral points" come, so a central tool of the argument rests on a 2026 work we have not seen. Not checked, and not checkable from here: the Lean repository (needs the owner's yes/no for a read-only shallow clone), the OpenAI manuscript (the paper's reference `OAI26` describes it as a manuscript on the border determinantal complexity of the permanent with a cubic lower bound, which differs from the owner's description of an OpenAI paper "VP and VNP are different"; no URL was given), the independent audit (no URL), every citation's content, and the proof. Only the paper's own caveats are safe to quote.
