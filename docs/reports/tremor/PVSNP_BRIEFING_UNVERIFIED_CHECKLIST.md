# P vs NP briefing: unverified-claims checklist (R6)

Written offline 2026-11-26. No network, model, GPU or key. This file asserts nothing about whether any claim is true or false; the author cannot verify any of them without network access.

Sources: the owner's briefing (`docs/reports/tremor/PVSNP_BRIEFING_OWNER_TEXT.md` (the owner text, copied verbatim from the session scratchpad on 2026-11-26), dated "Late 2026", header says its 2025-2026 claims are not independently verified). `PL` = `prereg/R6-pvsnp-research-line-plan.md`. `PR` = `prereg/R6-protocol-draft.md`.

Status values: **FB** = "from briefing, unverified" (every 2025-2026 claim). **CL** = "classical, citation to be verified".

**Standing rule for every row:** no proof step, lemma, score or gate in R6 rests on this claim (PL:12, PL:58, PL:337, PR:228). If the claim is retracted or false, nothing in R6 changes.

| # | Claim as stated | Source in briefing | Used where in R6 | Status | How it WOULD be verified (source type only) |
|---|---|---|---|---|---|
| 1 | P vs NP is still listed as an open Millennium Prize Problem by the Clay Mathematics Institute | Opening paragraph | not used | FB (current status, late 2026) | The Clay Mathematics Institute's own problem page and rules, read at a stated date |
| 2 | Ryan Williams's 2025 square-root-scale space simulation for time-bounded Turing machines | Opening paragraph; prompt Part A.2 ("sqrt(t)-space simulation") | PL:52 (tagged `[briefing, unverified]`) | FB | The author's own paper or preprint, plus the proceedings entry of a refereed venue |
| 3 | October 2026 Lean-checked claims from OpenAI and Anthropic disproving ETH | Opening paragraph; "Why the 2026 AI-math wave matters" | PL:53 (the labs are not named there) | FB | Each lab's own release or preprint; the linked Lean repository; independent expert commentary |
| 4 | Those claims use 2^{n/sqrt(log n)}-time 3-SAT counting (#3-SAT) algorithms | Opening paragraph | PL:53 | FB | The preprints' theorem statements, read against the standard definitions of #3-SAT and ETH |
| 5 | Both October 2026 ETH preprints passed the Lean checker | "Formalization Semantic Gap" | PL:53 ("Lean-checked"); PL:133 reports Lean checking as NOT DONE here | FB | Rebuilding the cited Lean projects with a pinned toolchain; an axiom listing of the main theorem; a human audit of the definitions |
| 6 | The ETH claims are under human review by Impagliazzo, Paturi and Williams | Opening paragraph | not used | FB | Public statements by those three, or a journal or venue record |
| 7 | A crossover of 2^{420} to 2^{8000} clause thresholds in the October 2026 preprints | "Asymptotic vs. Practical Implications" | PL:129 (illustration for scenario row 2) | FB | The preprints' stated constants, read directly |
| 8 | William Hoza's November 2026 report that NL = UL | Opening paragraph; prompt Part A.2 ("NL vs. UL") | PL:55 | FB | The author's preprint or an ECCC/arXiv record; expert commentary |
| 9 | Late-November 2026 unreviewed claims on algebraic VP != VNP | Opening paragraph | PL:56 | FB | The claimants' preprints and any review record; a statement of what is claimed and by whom |
| 10 | Cook-Mertz tree evaluation (listed with the space-time trade-offs; no year given) | Prompt Part A.2 | PL:52 (tagged `[briefing, unverified]`) | FB (the briefing places it in the 2025-2026 frontier but gives no date) | The authors' paper and its proceedings entry |
| 11 | Relativization barrier: Baker, Gill, Solovay (1975) | Barrier table; prompt section 2 | PL:44 (tagged `[classical]`) | CL | The original paper (SIAM J. Comput.) and a standard textbook treatment |
| 12 | Natural Proofs barrier: Razborov, Rudich (1997) | Barrier table | PL:45 | CL | The original paper (JCSS) and a standard textbook treatment |
| 13 | Algebrization barrier: Aaronson, Wigderson (2008) | Barrier table | PL:46 | CL | The original paper (STOC 2008 / TOCT) |
| 14 | "Three proven mathematical barriers" rule out almost all naive proof strategies | Barrier paragraph | PL:40-46 (table); PL:62 (gate G1) | CL (the count and the "almost all" wording are the briefing's) | A survey of barriers in complexity theory |
| 15 | Williams's paradigm: faster SAT algorithms imply circuit lower bounds (NEXP not in ACC^0); no year in the briefing | "Algorithms-to-Lower-Bounds"; prompt Part A.2 | PL:54, PL:67, PL:68 (PL tags the 2011 result `[classical]`; the year is the plan's, not the briefing's) | CL | Williams's journal paper; follow-up surveys |
| 16 | "Compression-plus-diagonalization" ETH claims | "Algorithms-to-Lower-Bounds" | PL:54 | FB | The October 2026 preprints (rows 3-4) |
| 17 | A Lean kernel checks only that the formal theorem follows from its axioms; the formal definitions may not match the intended problem ("garbage code") | "Formalization Semantic Gap" | PL:140 (Definition Audit step); PR:29 | CL (a general statement about proof assistants) | The Lean 4 documentation and the Mathlib guidance on axioms |
| 18 | Worst-case hardness does not give average-case hardness (one-way functions) | "Asymptotic vs. Practical Implications" | PL:123-124 (PL cites Impagliazzo 1995, `[classical]`) | CL | Impagliazzo's survey "A personal view of average-case complexity" |
| 19 | Cook-Levin / Karp definitions of NP-completeness | Prompt Part A.1 | PL:30 | CL | Original papers and standard textbooks |
| 20 | Fagin's theorem (NP = SO-exists); Immerman-Vardi (P = FO(LFP) on ordered structures) | Prompt lens 6 | PL:101 | CL | Original papers; a finite model theory text |
| 21 | Valiant's VP vs VNP; determinant vs permanent | Prompt lens 2 | PL:73 | CL | Valiant 1979; algebraic complexity texts |
| 22 | Meta-complexity: MCSP, K^t, equivalence of average-case hardness with one-way functions | Prompt lens 3 | PL:80-81 | CL (the year of the equivalence result is not in the briefing) | The cited papers (PL names Kabanets-Cai 2000 and Liu-Pass) |
| 23 | ETH and SETH as the fine-grained frontier | Prompt lens 5 | PL:94 | CL | Impagliazzo-Paturi papers |
| 24 | IP = PSPACE as the origin of arithmetization techniques | Barrier table | not used | CL | The original papers |
| 25 | Proof complexity (Resolution, Frege, Extended Frege) and the NP vs coNP pathway | Prompt lens 4 | PL:88 | CL | Texts on propositional proof complexity |

No other dated claim is in the briefing.

## Check: does any R6 document rely on an unverified claim for a proof step?

Method: grep of PL and PR for each claim above, then a read of each hit. Result: no hit makes a proof step, lemma, score, gate or run decision depend on a row marked FB. PL:12, PL:58, PL:337 and PR:228 state the rule.

Places that come close, for a reviewer to look at:

- **PL:53** says "If true they refute ETH and leave P vs NP open". It is conditional and sits in a "From the briefing" column, but it is an interpretation of a briefing claim. Keep it conditional.
- **PL:52** adds "Separates time from space, not P from NP" next to rows 2 and 10. That is the plan's gloss, not the briefing's.
- **PL:54** quotes "Compression plus diagonalization" next to a classical row. The two are in separate columns, but the quote could be read as an established method.
- **PL:68 and PL:110** (and the lens choice at PL:108) rely on "reported to evade" for Williams's route, tagged `[ctv]`, not `[briefing]`. This is a reputation, not a briefing claim, and PL:68 already requires each candidate to write its own algebrization argument. It is the nearest place to a proof step resting on an unchecked citation.
- **PL:129** uses the 2^{420} to 2^{8000} figures only as an illustration of scenario row 2. Remove if the figures are retracted.
- **PL:133** reports "Lean-checked" as NOT DONE here. Row 5's "Lean-checked" label is never counted as evidence.
- **PL:178 (G2)** fails any output that uses a sealed briefing keyword without `from_briefing_unverified`. This is the mechanical guard; its keyword list is sealed in R6-O3 (PR:190), so this file cannot confirm which of the rows above it covers.
- **PR:229** uses "briefing claim, unverified" for the coordinator's brief about Stage A, not the owner's P vs NP briefing. Different source; do not confuse.

Not checked: the actual sealed `briefing_keywords` list (not in the files read); any R6 file other than PL and PR; whether `lab/` code has hard-coded any of these claims.
