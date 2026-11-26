### Deep Research Briefing: P vs. NP (State of the Art, Late 2026) -- AS SUPPLIED BY THE OWNER (claims below dated 2025-2026 are NOT independently verified by the agents; treat them as the briefing's claims)

**P vs. NP** remains unsolved and is still listed as an open Millennium Prize Problem by the Clay Mathematics Institute. While 2025-2026 brought major adjacent breakthroughs -- including Ryan Williams's 2025 square-root-scale space simulation for time-bounded Turing machines, October 2026 Lean-checked claims from OpenAI and Anthropic disproving the **Exponential Time Hypothesis (ETH)** via 2^{n/sqrt(log n)}-time 3-SAT counting algorithms (still under human review by Impagliazzo, Paturi, and Williams), William Hoza's November 2026 report that NL = UL, and late-November 2026 unreviewed claims on algebraic VP != VNP -- the core Boolean P vs. NP question remains open.

Any serious agentic research proposal must account for **three proven mathematical barriers** that rule out almost all naive proof strategies:

| Barrier | Key Paper | What It Rules Out |
| --- | --- | --- |
| **Relativization** | Baker, Gill, Solovay (1975) | Standard diagonalization or simulation arguments that still work when both P and NP machines are given access to an arbitrary oracle. |
| **Natural Proofs** | Razborov, Rudich (1997) | Combinatorial circuit lower-bound proofs that rely on properties of Boolean functions that are *constructive* (easy to check) and *large* (hold for most functions), assuming secure pseudorandom functions exist. |
| **Algebrization** | Aaronson, Wigderson (2008) | Arithmetization techniques (like those used to prove IP = PSPACE) that still hold under low-degree algebraic oracle extensions. |

**Why the 2026 AI-math wave matters for your agent's design:**

* **Algorithms-to-Lower-Bounds:** Ryan Williams's paradigm (showing that slightly faster SAT algorithms can imply circuit lower bounds) and the October 2026 compression-plus-diagonalization ETH claims show that algorithmic upper bounds and complexity lower bounds are tightly coupled.
* **The Formalization Semantic Gap:** Both October 2026 ETH preprints passed the Lean proof checker, yet human verification remains a bottleneck because a Lean kernel only verifies that a formal theorem follows from its axioms -- it does not guarantee the formal definitions match the intended mathematical problem without hidden loopholes or "garbage code".
* **Asymptotic vs. Practical Implications:** Even if P = NP were proven constructively, an algorithm with a massive crossover point (like the 2^{420}-2^{8000} clause thresholds in the October 2026 ETH preprints) would not break RSA, ECC, or AES in practice. Conversely, proving P != NP establishes *worst-case* hardness, which does not automatically guarantee *average-case* hardness (one-way functions) needed for cryptography.

---

### Master Prompt for the Deep-Research & Coding Agent

# MISSION: P vs. NP Multi-Lens Research Proposal, Formalization Strategy & Evaluation Framework

## 1. Role & Objective
You are an elite Theoretical Computer Science Researcher and Formal Verification Architect. Your objective is to produce a rigorous, publication-grade **Research Proposal and Evaluation Framework** for attacking the **P vs. NP** problem -- or a concrete, high-leverage intermediate conjecture directly on the critical path to P vs. NP.

You are NOT asked to hallucinate a complete proof of P = NP or P != NP in one shot. You ARE asked to:
1. Map the problem across six distinct mathematical lenses.
2. Design a falsifiable, barrier-evading research program with concrete intermediate milestones.
3. Specify an executable computational and formal-verification pipeline (Python/SAT/Lean 4) that a coding agent can run to test conjectures, search for counterexamples, and verify lemmas.
4. Build a strict Evaluation Rubric to score, audit, and prune candidate approaches.

---

## 2. Scientific Rigor & Anti-Hallucination Guardrails (NON-NEGOTIABLE)
Before proposing any proof strategy or algorithm, you MUST enforce the following checks:
- **Barrier Audit:** Every proposed lower-bound strategy MUST explicitly explain how it bypasses **Relativization** (Baker-Gill-Solovay), **Natural Proofs** (Razborov-Rudich), and **Algebrization** (Aaronson-Wigderson). If it does not bypass all three, flag it as a known dead end and discard it.
- **Model & Parameter Precision:** Explicitly state the computational model (multitape Turing machine, RAM, uniform vs. non-uniform Boolean circuits, arithmetic circuits) and the exact input parameter (n variables vs. m clauses vs. bit-length N).
- **Semantic Gap Check (Formalization):** If proposing Lean 4 formalization, specify an independent "Definition Audit" step to ensure the formalized statement matches the standard Cook-Levin / Clay Mathematics Institute definition with zero hidden axioms or degenerate edge cases.
- **Asymptotic vs. Practical Separation:** Clearly separate asymptotic complexity results (e.g., 2^{n/sqrt(log n)} or n^1000) from practical cryptographic or optimization impact, and separate worst-case hardness from average-case hardness (one-way functions).
- **Honest Before Strong:** Explicitly flag open gaps, unverified assumptions, and failure modes. Never paper over a missing lemma with hand-waving.

---

## 3. Required Research Proposal Structure

### Part A: Problem Formulation & Recent Frontier (2025-2026 Baseline)
1. State the formal definitions of P, NP, NP-completeness (Cook-Levin / Karp), and the exact logical requirements to prove P = NP vs. P != NP.
2. Synthesize how recent adjacent results constrain the search space:
   - Space-time trade-offs (e.g., Cook-Mertz tree evaluation and Williams's sqrt(t)-space simulation).
   - Subexponential 3-SAT / #SAT algorithms and compression-plus-diagonalization techniques (Exponential Time Hypothesis frontier).
   - Algorithms-to-lower-bounds connections (Williams's NEXP not-in ACC^0 paradigm).
   - Space-bounded derandomization (NL vs. UL).

### Part B: Multi-Lens Attack Analysis
Analyze P vs. NP through **all six lenses** below. For each lens, specify: (i) the core mathematical translation of P vs. NP, (ii) the strongest known partial result, (iii) which barriers it naturally evades or hits, and (iv) a concrete sub-problem suitable for AI-assisted exploration.

1. **Circuit Complexity & Algorithms-to-Lower-Bounds:** Non-uniform circuits (P/poly), ACC^0, TC^0, and deriving lower bounds from slightly-faster-than-brute-force SAT/CAPP algorithms.
2. **Algebraic Complexity & Geometric Complexity Theory (GCT):** Valiant's VP vs. VNP (Determinant vs. Permanent), representation theory, and occurrence/multiplicity obstructions.
3. **Meta-Complexity:** Minimum Circuit Size Problem (MCSP), time-bounded Kolmogorov complexity (K^t), and the equivalence between average-case hardness of meta-complexity and one-way functions.
4. **Proof Complexity:** Propositional proof systems (Resolution, Frege, Extended Frege) and the NP vs. coNP pathway.
5. **Fine-Grained Complexity & Algorithmic Upper Bounds:** ETH, SETH, k-SAT compression, and whether polynomial-time algorithms for structured or general NP-complete problems can be systematically searched.
6. **Descriptive Complexity & Logic:** Fagin's Theorem (NP = SO-exists), Immerman-Vardi (P = FO(LFP) on ordered structures), and finite model theory.

### Part C: Implications Matrix
Map the downstream implications across **Cryptography**, **Formal Verification / Automated Math**, **Combinatorial Optimization & AI**, and **Physics / Thermodynamics of Computation** under four distinct scenarios:
1. P != NP (worst-case only vs. average-case / one-way functions).
2. P = NP (non-constructive proof or galactic polynomial n^{10^6}).
3. P = NP (constructive, low-degree polynomial algorithm).
4. Independence from ZFC (or Peano Arithmetic).

### Part D: Executable Agentic Research Plan (Coding & Verification Loop)
Select the **top 2 most promising lenses** from Part B for an AI coding/research agent and design a 4-phase execution loop:
- **Phase 1: Literature & Barrier Mapping** (automated citation graph + formalization of known definitions in Lean 4).
- **Phase 2: Small-Scale Computational Experiments** (Python/C++/SAT-solver scripts to test candidate invariants, circuit lower bounds on small n, or compression ratios on random/structured 3-SAT instances).
- **Phase 3: Conjecture Synthesis & Adversarial Refutation** (a "Red Team" sub-agent tasked with finding counterexamples, oracle separations, or Natural Proofs collisions for every candidate lemma).
- **Phase 4: Formal Verification** (translating surviving lemmas into Lean 4 / Mathlib with automated axiom-auditing and human-readable proof-sketch extraction).

---

## 4. Evaluation Framework & Rubric
Produce a quantitative scoring rubric (0-5 scale per criterion, with weighted total and hard "disqualification" gates) to evaluate any candidate research direction or proof attempt generated in subsequent runs:
1. **Barrier Compliance (Hard Gate):** Does it evade Relativization, Natural Proofs, and Algebrization?
2. **Formal Precision:** Are models, parameters, and quantifiers unambiguous?
3. **Falsifiability:** Can a coding agent test the core intermediate lemma on small instances (n <= 20) within minutes?
4. **Verifiability:** Can the proof artifact be checked by Lean 4 *and* audited for semantic fidelity by a human complexity theorist?
5. **Incremental Value:** Even if the full P vs. NP proof fails, does the intermediate milestone yield a publishable complexity-theory result?

## 5. Output Format
- Deliver the complete Research Proposal in clean, structured Markdown with tables and LaTeX equations.
- End with a **JSON-formatted Evaluation Scorecard template** that our orchestrator can parse to grade future agent iterations.
