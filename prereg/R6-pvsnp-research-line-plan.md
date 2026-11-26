# R6 plan: P vs NP research line, and how we score agents on it

**PLAN, revision 2 (after Opus REJECT of revision 1). Not frozen; no run, spend or admission authority.** Written at HEAD `9a74aef` by the planner (Fable 5.2). No network, model call or GPU process was used.

**What this line is.** (I) A research proposal and evaluation framework for P vs NP, following the owner's master prompt (MP): Parts A to D, rubric, JSON scorecard. (II) The connection to the R5 agent-performance line: a task suite with mechanical ground truth on which single agents and teams are scored.

**What it is not.** It claims no proof of P = NP or P ≠ NP and gives no probability of resolving the question. The deliverable is falsifiable intermediate milestones and a measurement of how well agents do this work.

**Claim status tags.**
- **[classical]**: a result the planner is certain of.
- **[ctv]**: citation to be verified.
- **[briefing, unverified]**: from the owner's briefing (2025 to 2026 items); not verifiable here. **No step depends on one.**
- **[recalled, unverified]**: a number the planner recalls, used only as a cross-check.
- **[ours]**: computed by our own reviewed exact solver.

Keys: R5 `prereg/R5-agent-performance-line-plan.md`; EP `prereg/EP1.md`; DL `docs/reports/tremor/DECISION_LOG.md`; RD `docs/reports/tremor/R5_GPU_READINESS_20261126.md`.

---

# Part I. Research proposal and evaluation framework

## A. Problem formulation and frontier

### A1. Definitions

Model: deterministic multitape Turing machine. Parameter: $N$ = bit-length of the input. For SAT, $n$ = variables, $m$ = clauses, $N=\Theta(m\log n)$ for $k$-CNF.

- $\mathsf{P}=\bigcup_k\mathsf{DTIME}(N^k)$.
- $L\in\mathsf{NP}$ iff there are a polynomial $p$ and a polynomial-time verifier $V$ with $x\in L\iff\exists w,\ |w|\le p(|x|),\ V(x,w)=1$.
- $L$ is NP-complete iff $L\in\mathsf{NP}$ and every NP language reduces to it by a polynomial-time many-one reduction. SAT is NP-complete (Cook 1971, Levin 1973) **[classical]**; so are Karp's 21 problems (Karp 1972) **[classical]**.

### A2. What a proof must show

| Goal | Sufficient | Notes |
|---|---|---|
| $\mathsf{P}=\mathsf{NP}$ | A polynomial-time algorithm for one NP-complete language with proofs of correctness and of the bound; or a non-constructive existence proof | The exponent may be astronomically large (Part C) |
| $\mathsf{P}\ne\mathsf{NP}$ | For one $L\in\mathsf{NP}$: every deterministic TM deciding $L$ exceeds $N^k$ steps for every $k$ on infinitely many lengths | About **all** algorithms, worst case |
| Stronger, also sufficient | $\mathsf{NP}\not\subseteq\mathsf{P/poly}$, or $\mathsf{NP}\ne\mathsf{coNP}$ | Neither is necessary |

### A3. Barriers

| Barrier | Source | Rules out |
|---|---|---|
| Relativization | Baker, Gill, Solovay 1975 **[classical]** | Arguments that hold relative to every oracle. Oracles exist with $\mathsf{P}^A=\mathsf{NP}^A$ and $\mathsf{P}^B\ne\mathsf{NP}^B$, so proofs of **either** outcome are constrained |
| Natural proofs | Razborov, Rudich 1997 **[classical]** | Circuit lower bounds from a constructive, large property useful against a class containing pseudorandom functions (conditional on their existence) |
| Algebrization | Aaronson, Wigderson 2008 **[classical]** | Arguments that survive low-degree extensions of the oracle |

### A4. How adjacent results constrain the search

| Area | Certain or to verify | From the briefing |
|---|---|---|
| Time vs space | $\mathsf{DTIME}(t)\subseteq\mathsf{SPACE}(t/\log t)$ (Hopcroft, Paul, Valiant 1977) **[classical]** | Cook-Mertz tree evaluation; Williams's 2025 $\sqrt t$-scale space simulation **[briefing, unverified]**. Separates time from space, not P from NP |
| ETH frontier | ETH, SETH (Impagliazzo, Paturi 2001; with Zane, sparsification) **[ctv]** | October 2026 Lean-checked $2^{n/\sqrt{\log n}}$ 3-SAT counting claims **[briefing, unverified]**. If true they refute ETH and leave P vs NP open |
| Algorithms to lower bounds | $\mathsf{NEXP}\not\subseteq\mathsf{ACC}^0$ from a faster ACC-SAT algorithm (Williams 2011) **[classical]** | "Compression plus diagonalization" **[briefing, unverified]** |
| Space-bounded | $\mathsf{NL/poly}=\mathsf{UL/poly}$ (Reinhardt, Allender) **[ctv]** | Hoza, NL = UL, November 2026 **[briefing, unverified]** |
| Algebraic | VP, VNP, permanent complete (Valiant 1979) **[classical]** | Late-November 2026 VP ≠ VNP claims **[briefing, unverified]** |

If any briefing item is retracted, nothing here changes.

## B. Six lenses

Audit letters: R = relativization, N = natural proofs, A = algebrization. **Rule (gate G1): a lower-bound route passes only if each of R, N, A is "evades" with a written mechanism, or "not applicable" with a written reason. "Open", "unknown" or a recalled reputation fails.**

### B1. Circuit complexity and algorithms-to-lower-bounds

- **Translation.** $\mathsf{P}\subseteq\mathsf{P/poly}$, so a superpolynomial circuit lower bound for an NP language gives $\mathsf{P}\ne\mathsf{NP}$. Model: non-uniform circuits, fan-in 2; parameter: input bits.
- **Strongest known.** Parity not in $\mathsf{AC}^0$ (Håstad 1986 and predecessors) **[classical]**; $\mathsf{AC}^0[p]$ (Razborov 1987, Smolensky 1987) **[classical]**; monotone clique (Razborov 1985) **[classical]**; $\mathsf{NEXP}\not\subseteq\mathsf{ACC}^0$ (Williams 2011) **[classical]**. For unrestricted circuits, only linear bounds near $3n$ **[ctv]**.
- **Audit.** Restrictions and polynomial approximation: N = hits → DEAD beyond where they already work. Williams's route: R = evades (non-relativizing ingredients); N = evades (diagonalization, no large constructive property); A = reported to evade **[ctv]**. The **[ctv]** is a reputation, so **any new candidate on this route must write its own algebrization argument to pass G1**.
- **Sub-problem.** For a restricted class, exact evaluation counts of a candidate #SAT algorithm against $2^n$ at $n\le 20$. Small $n$ refutes only a claim with explicit constants and a threshold $n_0\le 20$; it can neither refute nor support a purely asymptotic one.

### B2. Algebraic complexity and GCT

- **Translation.** VP vs VNP (Valiant 1979) **[classical]**: is the determinantal complexity of $\mathrm{perm}_n$ polynomial. Model: arithmetic circuits over a named field; parameter: matrix dimension. An algebraic analogue; VP ≠ VNP does not imply $\mathsf{P}\ne\mathsf{NP}$.
- **Strongest known.** $\mathrm{dc}(\mathrm{perm}_n)\ge n^2/2$ (Mignon, Ressayre) **[ctv]**; occurrence obstructions cannot give superpolynomial bounds (Bürgisser, Ikenmeyer, Panova) **[ctv]**.
- **Audit.** R and A are defined for Boolean oracle classes; N has an algebraic analogue **[ctv]**. Not auditable like for like → not selected.
- **Sub-problem.** Exact dimensions of partial-derivative spans of $\det_n$ and $\mathrm{perm}_n$, $n\le 4$.

### B3. Meta-complexity

- **Translation.** MCSP: given a truth table of length $2^n$ and $s$, is there a circuit of size at most $s$ (Kabanets, Cai 2000) **[classical]**. In NP; NP-completeness open. A natural property is in effect an average-case MCSP algorithm, so this lens studies the natural-proofs barrier itself.
- **Strongest known.** MCSP in P implies no one-way functions (Kabanets, Cai 2000) **[classical]**. One-way functions exist iff time-bounded Kolmogorov complexity is mildly hard on average (Liu, Pass 2020) **[ctv]**. Non-black-box worst-to-average reductions (Hirahara 2018) **[ctv]**.
- **Audit.** For reductions, equivalences and finite measurements G1 is "not applicable: no lower bound is claimed". **For any lower-bound route inside this lens the planner cannot write an algebrization argument (status open), so such a route FAILS G1 and is not pursued here.**
- **Sub-problem.** The natural-property meter (M2).

### B4. Proof complexity

- **Translation.** $\mathsf{NP}=\mathsf{coNP}$ iff some propositional proof system has polynomial-size proofs of all tautologies (Cook, Reckhow 1979) **[classical]**.
- **Strongest known.** Exponential resolution bounds for pigeonhole (Haken 1985) **[classical]**; width-size relation (Ben-Sasson, Wigderson) **[ctv]**. Nothing superpolynomial for Frege.
- **Audit.** A bound for one weak system separates nothing; a bound for every system must pass all three and no known technique does. DEAD as a route; kept as a task source.
- **Sub-problem.** Exact minimum resolution width for pigeonhole with at most 4 holes and small Tseitin formulas.

### B5. Fine-grained complexity and upper bounds

- **Translation.** ETH: 3-SAT has no $2^{o(n)}$-time algorithm. SETH: for every $\varepsilon>0$ there is a $k$ such that $k$-SAT has no $2^{(1-\varepsilon)n}$-time algorithm (Impagliazzo, Paturi 2001) **[ctv]**. Both are stronger than $\mathsf{P}\ne\mathsf{NP}$.
- **Strongest known.** Sparsification **[ctv]**; best 3-SAT algorithms near $1.31^n$ **[ctv]**.
- **Audit.** A claimed polynomial algorithm must itself be non-relativizing (BGS). Lower-bound use goes through B1.
- **Sub-problem.** Exact model and search-node counts, 3-CNF, $n\le 20$.

### B6. Descriptive complexity

- **Translation.** $\mathsf{NP}=\exists\mathsf{SO}$ (Fagin 1974) **[classical]**; $\mathsf{P}=\mathsf{FO(LFP)}$ on ordered structures (Immerman 1986, Vardi 1982) **[classical]**.
- **Strongest known.** Fixed-point logic with counting does not capture P (Cai, Fürer, Immerman 1992) **[ctv]**.
- **Audit.** R = open; no known evading technique → fails G1, not selected.
- **Sub-problem.** An Ehrenfeucht-Fraïssé game solver on structures of at most 8 elements.

### B7. The two lenses chosen

**Lens 1 (circuits, algorithms-to-lower-bounds) as the only lower-bound route, and Lens 3 (meta-complexity) as an instrument, not a lower-bound route.**

1. Lens 1 holds the only known proof pattern reported past all three barriers; each new candidate must still pass G1 on its own written arguments.
2. Lens 3 makes the natural-proofs check measurable. Its work here is reductions, tables and the meter, where G1 is not applicable. Its lower-bound routes fail G1 (B3) and are excluded.
3. Both use one object: a truth table with its exact minimum size.
4. Every finite claim in both is checkable exhaustively in minutes.

Lens 4 supplies tasks to Part II.

## C. Implications matrix

Two separations run through every row: **asymptotic vs practical**, **worst-case vs average-case**.

| Scenario | Cryptography | Formal verification, automated mathematics | Optimization and AI | Physics of computation |
|---|---|---|---|---|
| 1a. $\mathsf{P}\ne\mathsf{NP}$, worst case only | No guarantee: one-way functions need average-case hardness (Impagliazzo's worlds, 1995 **[classical]**) | Proof search hard in the worst case; practice unchanged | Heuristics remain the practice | No new statement |
| 1b. $\mathsf{P}\ne\mathsf{NP}$ and one-way functions exist | Symmetric cryptography has a foundation; RSA and ECC keep their own assumptions | As 1a | As 1a | As 1a |
| 2. $\mathsf{P}=\mathsf{NP}$, non-constructive or exponent like $10^6$ | Asymptotically no one-way functions; nothing breaks at real key sizes | No usable prover | No usable solver | None |
| 3. $\mathsf{P}=\mathsf{NP}$, constructive, low degree | Public-key and most symmetric schemes break; information-theoretic ones remain | Short proofs findable in time polynomial in their length | Exact optimization becomes feasible | None; Landauer's bound concerns erasure |
| 4. Independent of ZFC or PA | No practical change | Still true or false in the standard model; our tools cannot settle it | No change | None |

The briefing's $2^{420}$ to $2^{8000}$ clause thresholds **[briefing, unverified]** illustrate row 2.

## D. Executable research loop

Tooling checked read-only on this host: `lean`, `lake`, `cadical`, `kissat`, `minisat` are not on PATH; `pysat` is not importable. Installing any is a Safety rule 2 gate. **Ground truth is standard-library Python**, and "Lean-checked" is reported NOT DONE until an install is approved.

| Phase | Work | Output | Falsifier |
|---|---|---|---|
| 1. Literature and barrier map | A claims register with status tag, model, parameter per entry. Built offline from memory, so non-classical entries stay **[ctv]**; a citation fetch is a separate gated network step | `claims_register.json` | A "classical" entry a reviewer cannot confirm |
| 2. Small-scale experiments | M1 tables, M3 counts, M2 meter | hash-pinned tables | Two independent implementations disagree |
| 3. Conjecture and refutation | Lemmas submitted as executable predicates (below); a Red Team agent tries to refute each | lemma ledger | A surviving lemma later refuted by exhaustive check |
| 4. Formal verification | Lean-style statements with a Definition Audit; kernel check once Lean is approved | statement pack | A second auditor shows an audited statement is vacuous |

**Executable-predicate rule (Phase 3 and family F5).** A lemma is mechanical only if it arrives as a predicate in one fixed language: a Python function over a declared finite domain (all truth tables on $n\le 4$ inputs, or all CNFs of a declared shape), restricted to a whitelisted syntax (integer and bit operations, comparisons, bounded `range` loops, calls into our checker library: NOT available in the first implementation (`lab/r6_predicates.py` offers `popcount`, `bit`, `abs`, `min`, `max` and aggregates plus an empty registry for named pure functions; circuit-size lemmas wait until the M1 tables are accepted and registered, per the Opus review of 2026-11-26), run under a step limit. **Out of scope:** statements over unbounded $n$, asymptotic statements, anything needing a judge. Those are recorded as `conjecture` and produce no pass row.

**Trust boundary.** Running agent-submitted Python is a trust boundary. The whitelist parser and the step limit are one module, `lab/r6_predicates.py`, owned by worker W4 (step R2), with an escape test: predicates that try imports, attribute access, file or network use, or unbounded loops must be rejected before execution. No predicate runs outside it.

**Milestones.**

- **M1. Exact size tables [ours].** Cost models, fixed here:
  - *Formula size* = number of leaves (variable occurrences). De Morgan basis: AND, OR with negations free at any point, no constants. Binary basis: all 16 two-input operations, same leaf count.
  - *Circuit size* = number of two-input gates over all 16 operations; inputs free, negation free (absorbed), unbounded fan-out, no constants.
  - Scope: formula size for all $2^{16}$ functions on 4 inputs; circuit size for all functions on 3 inputs and on 4 inputs as far as the bounded search completes, the rest reported as lower bounds.
  - Cross-checks **[recalled, unverified]**: classes under input negation, input permutation and output negation number 4, 14, 222 for $n=2,3,4$; minimum De Morgan formula size of 4-input parity is 16 (Khrapchenko); the largest 4-input circuit size is 7 (Knuth). A mismatch opens an investigation of both the solver and the recollection; neither wins by default.
- **M2. Natural-property meter.** "Constructive" and "large" are asymptotic and vacuous at $n\le 4$, so the meter uses finite stand-ins, each fixed in the protocol before use: cost = operations counted by an instrumented run of the property's predicate, compared with $(2^n)^k$ for a fixed $k$; large = density at least $2^{-cn}$ for a fixed $c$; useful = no function of circuit size at most a fixed $s$ has the property. The planner names no value for $k$, $c$, $s$. Output is a screen, not a proof of naturalness.
- **M3. Savings measurements.** Exact evaluation counts against $2^n$, $n\le 20$, for one restricted class. A claim is recorded **refuted** only if it states explicit constants and a threshold $n_0\le 20$ and the count violates it; any other claim is recorded **not testable at small n**.
- **M4. Statement pack.** Audited formal statements of P, NP and the finite lemmas.
- **M5 (stretch).** One exact value that an authorized literature check shows is new.

## E. Rubric

Scores 0 to 5. **The weights are the planner's choice, not derived; the owner may replace them; frozen in the protocol before any scoring.**

| # | Criterion | Weight | 0 | 3 | 5 |
|---|---|---|---|---|---|
| 1 | Barrier compliance | 0.25 | no audit | all three addressed, one mechanism thin | a named mechanism for each |
| 2 | Formal precision | 0.20 | model or parameter missing | one quantifier ambiguous | model, parameter, quantifiers explicit |
| 3 | Falsifiability | 0.25 | no finite test | test over minutes or $n>20$ | core lemma tested at $n\le 20$ in minutes |
| 4 | Verifiability | 0.15 | prose only | checked by our oracle | Lean-checked and audit passed |
| 5 | Incremental value | 0.15 | none | internal tool | standalone result |

$\text{total}=100\cdot\sum_i w_is_i/5$.

**Hard gates. Any failure sets `disqualified: true` and the rubric total to 0.** G1, G2, G4, G5, G6 are decided mechanically from scorecard fields; **G3 is partly judgment** (a pattern match plus a reviewer flag).

| Gate | Fails when |
|---|---|
| G1 barrier | `claim_type` is `lower_bound` and any of the three entries is not `evades` with a non-empty argument, or `not_applicable` with a non-empty reason. For `upper_bound`: the relativization entry fails the same test. Other claim types: `na` |
| G2 unverified as fact | a claim has no status; a `checked_by_oracle` claim fails on re-run; a sealed keyword for a briefing item appears without `from_briefing_unverified` |
| G3 overclaim | a sealed pattern for "proof of P vs NP" or a resolution probability matches, or the reviewer flags it |
| G4 model and parameter | either field is empty or outside the vocabulary |
| G5 separation | either `separations` field is empty. It checks only that text is present, not its quality. `claim_type` `finite_lemma`: `na` |
| G6 definition audit | `claim_type` is `formal_statement` and not (`definition_audit.done` and `definition_audit.faithful`) |

---

# Part II. Connection to the agent-performance system

## 1. Task suite R6-TS

A pass is decided by a program, never by a judge model.

| Family | Task | Agent output | Checker and ground truth |
|---|---|---|---|
| F1 SAT, #SAT | 3-CNF, $n\le 20$ | witness, or model count | satisfying set as a $2^n$-bit integer, popcount |
| F2 circuit size | truth table, $n\le 4$ | a circuit, claimed size, optionally "minimum" | evaluate on all inputs; M1 table |
| F3 MCSP-type | (truth table, $s$) | yes with a circuit, or no | M1 table |
| F4 proof complexity | small unsatisfiable CNF | a resolution refutation | step checker; exact minimum width |
| F5 lemmas | an executable predicate (section D rule), planted true or false at a sealed rate | true, or false with a counterexample | exhaustive run of the predicate |
| F6 definition audit | informal statement paired with a formal one | faithful, or the defect and its location | planted label. **Faithful pairs are included as true negatives at a sealed rate**; each defect (quantifier swap, $n$ vs $N$, vacuous hypothesis, uniform vs non-uniform, degenerate edge case) sits at a **fixed recorded span**, and location is scored by exact span match |

Difficulty is a dial ($n$, size bound, clause ratio), set from the pilot to stay off floor and ceiling.

**New code.** `lab/r6_pvsnp_tasks.py` (generators, solvers, checkers), `lab/r6_m1_enum.py` (independent M1), `lab/r6_scorecard.py`, `lab/r6_predicates.py` (whitelist parser, step limit). Standard library only; no default for any open parameter.

## 2. R5 hypotheses instantiated here

**Precondition.** `lab/r5_perf_harness.py` and its tests are **untracked** at `9a74aef` and under repair after a rejected review (the mathematics stood; missing: the `run_episode` loop and the H5 gap; the H2 overdispersion check measured task spread; per the independent Opus review of 2026-11-26, record to be added to DECISION_LOG). **Stage A (R3) does not start until the harness is committed and its review has closed. That commit, `d0c67d7`, is recorded in DL and as an inherited pin in the R6 protocol.** R6 uses the harness exactly as pinned.

| Hypothesis | On R6-TS | Harness call (names as of today; confirmed at the pin) |
|---|---|---|
| **H2 (primary)** | Fit $(q,c)$ at team sizes 2 and 4, forecast the pass-count distribution at 8, per family. Row `{"n","task","rerun","agent","pass"}`; **pass is the F1 to F6 oracle's verdict only** | `episode_counts`, `fit_common_cause`, `h2_primary` |
| H3 (secondary) | Stated confidence against oracle pass rate, team of 4 against solo, with a no-confidence arm | `h3_primary`, `behaviour_check`, `brier` |
| H5 (secondary) | Best of $N$ chosen by imperfect views, never the oracle: syntax validator, spot check on a sealed eighth of assignments, a second agent's flag | `select_clean`, `h5_primary` |
| RT (secondary, new) | section 3 | pair permutation |
| H1 | not instantiated; stays with R5 | |

Holm family size 3 (H3, H5, RT). E, K, n from the pilot by R5's rule. Claims are about agents on these tasks, never about P vs NP. R6-TS data enter R5's own analysis only if the R5 author registers that before any run.

## 3. Red Team arm (scored)

- **Setup.** F5 lemmas. A proposer labels each true or false. A second agent then responds: in the treatment arm with a Red Team role ("refute this"), in the control arm with an ordinary solver role, same calls and tokens.
- **One override rule for both arms.** The proposer's label stands unless the second agent supplies a counterexample that the checker verifies. The arms differ by role, not by decision rule.
- **Endpoint RT.** Share of false lemmas still accepted, treatment minus control, paired by lemma. Null: arm labels permuted within lemma. Supported: 95% interval below 0. Killed: interval above 0.
- **Also reported.** Verified-refutation recall on false lemmas; rate of unverified counterexamples on true ones (each is a G2 failure, reported separately).
- **Uninformative.** The proposer already rejects nearly every false lemma, or too few false lemmas for the pilot's SE rule.

## 4. Definition Audit arm (scored)

On F6: precision and recall for "defective", with the true-negative rate on faithful pairs, and exact-span location accuracy. Rates with intervals; no hypothesis test. Auditor and statement author are different agents. Gate G6 reads its result.

## 5. Hard gates in scoring

`lab/r6_scorecard.py` computes G1 to G6 as defined in Part I E.

**Gate failures never change `pass`.** The pass in every F1 to F6 row stays oracle-only, so H2, H3, H5 and RT measure task performance alone. Gate failures are reported **separately**: a rate per gate, per arm and per team size, on the research-type answers that carry a scorecard. The rubric total (not the pass) is zeroed by a gate failure.

## 6. Local model: Inkling on the Spark, in place of Qwen

**Rule.** Reuse the resident service; never restart, copy or reconfigure it (AGENTS.md workspace rules).

**Live values (read-only `ps`, this session).** pid 435838, up 2 days 21 hours: `runtime-b12588/llama-server`, model `Inkling-2-Mini-UD-Q8_K_XL.gguf`, `--mmproj mmproj-F16.gguf`, alias `Inkling-2-Mini`, TCP `100.91.57.48:8011`, `--ctx-size 131072 --parallel 1`. **The note `coordinator-outbox/inkling-spark-residency-update-20261121.md` (UD-Q4_K_M, 8,192 context, Unix socket) is stale** and is not used.

**Model identity.** `SHA256SUMS` in the model directory lists the Q4_K_M GGUF, the mmproj and the runtime tarball; **it has no Q8_K_XL entry**. The freeze record's `model_snapshot` therefore holds a **locally computed sha256 of the Q8_K_XL file as its identity**, plus the mmproj hash, runtime build and the arguments above. This identifies the bytes we ran; it is **not** verification against upstream. Fetching an upstream hash is a separate gated network step.

**Unmeasured for our workload: seconds per call, generation tokens per second, queue wait, seed behaviour. Every GPU-hour figure is "to be set from the measured probe".**

### 6.1 What changes in R5's B0 and B1 when Qwen becomes Inkling

| R5 item (Qwen) | With Inkling |
|---|---|
| 33.08 s per call from 300 tokens at 9.07 tokens/s | **Void**; Qwen measurements. Replaced by the probe's upper bound |
| 71.094 s model load | Dropped; nothing is loaded |
| B0 = 0.277, B1 = 2.592 GPU-hours | **Void.** B0′ = 28 calls × $T$; B1′ = 280 calls × $T$; $T$ = measured worst wall time per call including queue wait |
| Weights with manifest and revision | Local sha256 identity (above) |
| Readiness check fails on other GPU processes (RD) | The resident server is the model: `lab/r5_gpu_readiness.py` is called with other processes allowed and extended to hash a GGUF |
| Launch gate `MemAvailable` ≥ 70 GiB (DL:15) | Nothing is launched; keep the 10 GiB host stop before each batch |
| R3-L2 native launcher | Not needed; a thin standard-library HTTP client to this one address supplies rows. It needs its own review |
| Model to itself | **One slot, and it is a last-resort OmniRoute fallback hop for other lanes** (section 6.2) |
| 4B model | Stronger model: ceiling risk; the dial is set from the pilot |
| 300-token output cap (EP:985) | Whether output tokens go to reasoning first is unknown; P0 measures, then the cap is set |
| Residual 9.4 GPU-hours | Whether requests to a resident service draw on it is the resource owner's call; until then our wall time counts |

### 6.2 Probe P0

**Why P0 is not harmless.** Reported by the coordinator from the server log, not measured by this line: the single slot currently holds another lane's cached prompt of about 33.7k tokens, so **any P0 call evicts it** and that lane pays the re-evaluation (roughly two minutes at the logged 275 to 283 prompt tokens/s); other traffic has sent prompts above 100k tokens; and a check-then-send idle test races with other clients, so it protects nothing.

**Preconditions, all required.**
1. Freeze record and `admit` for batch `r6-p0`.
2. Written notice to the PC coordinator, who runs the fallback hop, before and after.
3. A quiet window agreed with the PC coordinator in which no fallback traffic is routed to this hop.
4. The service owner named in the placement.

**Steps.**
1. Read-only: record the server's reported model, context and slot count; compute the Q8_K_XL sha256. Endpoint names are confirmed against the resident build here.
2. Twelve generation calls, strictly one in flight: input about 200, 1,000, 2,000 tokens (2,000 matches `spend.py`'s per-call input figure) × output cap 64 and 300 × 2 same-seed repeats. Synthetic F1 prompts only.
3. Per call: client wall time; server prompt and generation token counts and times; queue wait = wall minus server times; finish reason; reasoning-token share; whether repeats match.

**Stops, whichever first.** 12 calls; 15 minutes wall; 2 errors; **any skip spike: two calls that find the slot busy or wait over 60 s**, which means other traffic has arrived and the window is not quiet. No retry loop. The 60 s and the 300 s per-call timeout are the planner's choices.

**P0 sets** $T$, the slowest generation rate, the output cap and whether reruns can be seeded. **It gives no pass rate, variance or ICC.**

### 6.3 Stages after P0

- **B0′ (floor and ceiling):** one task set × 1 rerun at sizes 2, 4, 8: 28 calls × $T$.
- **B1′ (variance pilot):** one task set × 10 reruns: 280 calls × $T$. No ICC (one task set).
- Each has its own notice, quiet window, freeze and admission. H3, H5 and RT arms are sized from B1′ and requested separately; a request that does not fit leaves that hypothesis inconclusive.
- Pilot task sets and seeds never enter the main run, whose sets, seeds, planted labels and keyword lists are sealed before P0.

### 6.4 Admission path (as R5)

```
python3 -m lab.tremor_freeze_skeleton prereg/R6-protocol.md --batch <id> --out <freeze> --input <path>...
# author and custodian fill every empty field; the owner's admission record is written
python3 -m lab.tremor_admission_gate check <freeze> <admission> --now <utc> --hosted-cap 0 --gpu-cap <placed> --max-window-hours <h> --owner-words "<exact>"
python3 -m lab.tremor_admission_gate admit <freeze> <admission> --now <utc> --hosted-cap 0 --gpu-cap <placed> --max-window-hours <h> --owner-words "<exact>"
```

No request reaches the service before `admit` succeeds.

### 6.5 Hosted calls

**None proposed.** The owner's USD 10 cap is shared and is a code constant (`spend.py:48`, `HARD_CAP_USD`). R6 assumes no share; every gate call uses `--hosted-cap 0`.

## 7. Orchestration (the coordinator's ordered plan)

**Roles.** Fable planned. Opus coordinates and has every step checked by an independent Opus reviewer. Sonnet implements and consults an Opus advisor on hard decisions; the advisor for an item is never its reviewer.

| Step | Work | Acceptance |
|---|---|---|
| R0 | Revision 2 of this plan, fresh Opus review | ACCEPT recorded in DL |
| R1 | Pin the R5 harness commit | `d0c67d7` committed, review closed, recorded in DL |
| R2 | Four Sonnet workers in parallel, separate files. **W1** `lab/r6_pvsnp_tasks.py`, M1 by dynamic programming. **W2** `lab/r6_m1_enum.py`, an **independent** M1 by exhaustive enumeration, written without sight of W1. **W3** `lab/r6_scorecard.py`. **W4** `lab/r6_predicates.py`, the whitelist parser and step limit, with the escape test. Then an Opus reviewer: mutants, W1 against W2 on every entry, both against the recalled values (4, 14, 222; 16; 7) | Every targeted mutant killed; the escape test passes; W1 and W2 agree. **A mismatch between W1 and W2, or with a recalled value, opens an investigation and is not a failed acceptance; it goes to the Opus advisor, never to a vote.** R2 is accepted once the investigation closes with a recorded cause |
| R3 | Stage A offline through the pinned R5 harness: scripted agents with planted $q$, $c$, confidence bias, false-lemma rate, defect rate | Each planted value recovered; each null matches its closed form; a planted gate failure appears in the gate report and leaves `pass` unchanged |
| R4 | Opus drafts `prereg/R6-protocol.md`; Sonnet writes the HTTP client against a **stub only** | No OPEN method item; no real request sent |
| R5 | The owner names a custodian (not author, not runner), who seals task sets, seeds, planted labels, keyword lists | Path, sha256, custodian recorded |
| R6 | P0, only after `admit` and notice, in a quiet window, under the stop rules | Trace reviewed; $T$ recorded |
| R7 | B0′, then B1′, each with its own admission | Ledger settled; fixed n, no interim look (DL:238) |

**Stop the whole line** on contact with a hard rule or Safety gate, or on expiry.

**Test commands.**

```
PYTHONPATH=src:. python3 -m unittest lab.tests.test_r5_perf_harness lab.tests.test_tremor_admission_gate lab.tests.test_tremor_freeze_skeleton lab.tests.test_r5_gpu_readiness
PYTHONPATH=src:. python3 -m unittest lab.tests.test_r6_pvsnp_tasks lab.tests.test_r6_m1_enum lab.tests.test_r6_scorecard lab.tests.test_r6_predicates   # new, R2
PYTHONPATH=src:. python3 -m unittest lab.tests.test_r6_inkling_client                                                  # new, R4, stub only
PYTHONPATH=src python3 -m unittest tests.test_nulls tests.test_spend tests.test_readouts tests.test_stats
```

**Expiry and fallback.** R0 to R4 need nothing external beyond the R1 pin. The Inkling stage expires 14 days after R0 acceptance (the planner's choice, mirroring R5; the owner may replace it). On expiry the line reports "INSTRUMENTED, not piloted", makes no agent-performance claim and releases any reservation; M1 to M4 are still delivered offline. Lean falls back to "statement plus Definition Audit, kernel check NOT DONE".

## 8. Risks and what is unproven

- **Nothing is evidenced.** No solver, table, probe or run exists.
- **The milestones may yield nothing new**; their value is as ground truth and as a screen.
- **Small $n$ says nothing asymptotic.** Every report repeats this.
- **Citations.** Every **[ctv]** and **[recalled, unverified]** entry may be wrong; none carries a step.
- **Harness.** R3 is blocked on a commit that does not exist yet.
- **Shared slot.** A quiet window may not be obtainable; then the Inkling stage does not run.
- **Identity.** A local hash cannot detect a file that was wrong at download.
- **Determinism.** If seeds are not honoured, reruns are still independent draws, though not reproducible singly.
- **Memorization.** Famous small instances may be recalled; random sealed-seed instances are the control, and results are reported by family.
- **Gate keyword lists** catch wording, not meaning.
- **Unverified:** the gate on a real R6 record; the readiness extension; the resident build's endpoint names.

---

# JSON Evaluation Scorecard template

One object per candidate. `lab/r6_scorecard.py` validates it, recomputes `weighted_total` and the gates, and sets `disqualified`.

```json
{
  "schema_version": "r6-scorecard-2",
  "line": "R6",
  "candidate_id": "",
  "iteration": 0,
  "commit": "",
  "agent": {"role": "proposer|red_team|control_solver|definition_auditor|solver", "model": "", "team_size": 1, "arm": ""},
  "lens": "circuit|algebraic|meta_complexity|proof_complexity|fine_grained|descriptive",
  "claim_type": "lower_bound|upper_bound|reduction|finite_lemma|formal_statement",
  "model_of_computation": "multitape_tm|ram|uniform_circuit|nonuniform_circuit|arithmetic_circuit|proof_system",
  "input_parameter": "bit_length_N|variables_n|clauses_m|truth_table_2^n|matrix_dim_n",
  "statement": "",
  "predicate": {"path": "", "sha256": "", "domain": "", "step_limit": 0},
  "small_n_claim": {"explicit_constants": false, "threshold_n0": null, "result": "refuted|not_refuted|not_testable_at_small_n|na"},
  "claims": [
    {"id": "", "text": "", "status": "checked_by_oracle|proved_in_artifact|cited_classical|citation_to_be_verified|recalled_unverified|from_briefing_unverified|conjecture", "evidence": ""}
  ],
  "barrier_audit": {
    "relativization": {"status": "evades|hits|not_applicable|open", "argument": ""},
    "natural_proofs": {"status": "evades|hits|not_applicable|open", "argument": "", "meter": {"k": null, "c": null, "s": null, "cost_ops": null, "density": null, "useful": null}},
    "algebrization": {"status": "evades|hits|not_applicable|open", "argument": ""}
  },
  "hard_gates": {
    "G1_barrier": "pass|fail|na",
    "G2_unverified_as_fact": "pass|fail",
    "G3_overclaim": "pass|fail",
    "G4_model_parameter": "pass|fail",
    "G5_separation": "pass|fail|na",
    "G6_definition_audit": "pass|fail|na"
  },
  "criteria": {
    "barrier_compliance": {"score": 0, "weight": 0.25, "evidence": ""},
    "formal_precision": {"score": 0, "weight": 0.20, "evidence": ""},
    "falsifiability": {"score": 0, "weight": 0.25, "evidence": ""},
    "verifiability": {"score": 0, "weight": 0.15, "evidence": ""},
    "incremental_value": {"score": 0, "weight": 0.15, "evidence": ""}
  },
  "weighted_total": 0.0,
  "disqualified": false,
  "disqualification_reasons": [],
  "oracle_checks": {"claims_checkable": 0, "claims_checked": 0, "claims_passed": 0, "max_n": 0, "wall_seconds": 0.0, "checker": ""},
  "red_team": {"attempted": false, "verdict": "refuted|not_refuted|na", "counterexample": "", "counterexample_verified": null, "label_overridden": false},
  "definition_audit": {"done": false, "auditor": "", "reference_statement": "", "faithful": null, "defect_spans": []},
  "lean": {"kernel_checked": false, "toolchain": "", "axioms": [], "sorry_count": null},
  "separations": {"asymptotic_vs_practical": "", "worst_vs_average_case": ""},
  "performance_row": {"task": "", "family": "F1|F2|F3|F4|F5|F6", "n": 0, "rerun": 0, "agent": 0, "pass": 0, "conf": null},
  "resources": {"calls": 0, "input_tokens": 0, "output_tokens": 0, "wall_seconds": 0.0, "hosted_usd": 0.0},
  "verdict": "advance|revise|prune",
  "reviewer": {"id": "", "independent": true, "notes": "", "overclaim_flag": "true|false"},
  "evidence_paths": []
}
```

Parsing rules: each `a|b|c` value lists the allowed values and is replaced by exactly one. Any `fail` in `hard_gates` forces `disqualified: true`, `weighted_total: 0.0` and a verdict other than `advance`. **`performance_row.pass` is set by the family oracle alone and is never altered by a gate.**
