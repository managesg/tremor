# 01 - Complex-systems foundations and their application to LLM coding agents

Date: 2026-11-19. Method: generic public web searches only. Verification legend used below:
- **Y-search** = the URL and its bibliographic metadata appeared in a search result this session; the page itself was NOT opened (WebFetch was blocked by a hook, so no page was read in full).
- **UNVERIFIED (from memory)** = no URL seen; do not cite without checking.
Status legend: established (accepted result in its field), interpretation (my mapping onto agents), speculative (no evidence yet).
Caveat on all "Coding-agent analogy" lines: they are interpretation, not findings of the cited source.

---

## Part A. Concept cards

### A1. Holland - complex adaptive systems, building blocks, classifier systems
**Source:** J. H. Holland, *Hidden Order: How Adaptation Builds Complexity* (1995); *Adaptation in Natural and Artificial Systems* (1975; MIT Press ed.). URLs: https://blas.com/hidden-order/ (reader summary), https://direct.mit.edu/books/monograph/2574/Adaptation-in-Natural-and-Artificial-SystemsAn ; classifier-system history: https://cacm.acm.org/research/adaptive-computation/ (Forrest & Mitchell 2016). Verified: Y-search.
**Reliability:** books; CACM retrospective is peer-reviewed magazine.
**Status:** established (GA/classifier systems); the CAS "seven basics" framing is established as theory, not empirically tested on LLMs.
**Plain-language concept:** Adaptive systems reuse small recombinable building blocks; rules compete and are credited by a "bucket brigade"; general default rules get refined by exceptions.
**Coding-agent analogy:** Shared memory as a rule/skill population: small tagged lessons (building blocks), each with a strength updated by whether using it preceded a passing build; defaults (general rules) overridden by specific exceptions.
**Where the analogy fails:** LLM "rules" are free text, not fixed-length condition-action strings; credit assignment over long agent traces is noisy and delayed.
**Concrete experiment:** On a fixed 50-task repo benchmark, store lessons with a strength score updated +/- by task pass/fail; compare retrieval-by-strength vs unweighted retrieval. Metric: pass@1, same seeds/temperature 0.

### A2. W. Brian Arthur - increasing returns, path dependence, El Farol
**Source:** Arthur (1989) "Competing Technologies, Increasing Returns, and Lock-In by Historical Events," Economic Journal 99(394):116-131, https://doi.org/10.2307/2234208 (also https://academic.oup.com/ej/article-abstract/99/394/116/5188212). Arthur (1994) "Inductive Reasoning and Bounded Rationality," AER Papers & Proceedings 84:406-411 (listed on https://sites.santafe.edu/~wbarthur/publications.htm). Verified: Y-search.
**Reliability:** peer-reviewed.
**Status:** established (lock-in model; El Farol); mapping interpretation.
**Plain-language concept:** When adoption makes an option better, early random events can lock in one option, not necessarily the best. In El Farol, agents using similar predictors defeat their own predictions.
**Coding-agent analogy:** Agents copy the first plausible pattern found in shared memory; memory entries that get retrieved get reinforced, so early (possibly wrong) conventions lock in. Also: N agents all running the same model and prompt make identical "predictions" and crowd the same files/tasks.
**Where the analogy fails:** Agents are not payoff-maximizers with private predictors; same-model agents are correlated by construction, which is worse than El Farol's heterogeneity.
**Concrete experiment:** Seed memory with one wrong-but-plausible convention vs none; run 20 tasks; measure lock-in rate (fraction of later tasks adopting it) with and without a retrieval-diversity cap (max share per entry).

### A3. Kauffman - NK landscapes, edge of chaos, adjacent possible
**Source:** S. Kauffman, *The Origins of Order* (OUP 1993), https://www.researchgate.net/publication/37811275_The_Origins_of_Order_Self-Organization_and_Selection_in_Evolution ; adjacent possible: https://www.edge.org/3rd_culture/kauffman03/kauffman_index.html ; NK model: Kauffman & Weinberger 1989, J. Theor. Biol. 141:211-245 (seen only in a reference list inside https://arxiv.org/pdf/nlin/0204062). Verified: Y-search (book/essay); NK paper citation partial.
**Reliability:** book; essay; peer-reviewed.
**Status:** NK model established as a model; "edge of chaos" contested (critique seen: https://arxiv.org/pdf/1712.09609); adjacent possible = interpretation/metaphor.
**Plain-language concept:** Fitness depends on K interacting components; higher K gives more local peaks, harder hill-climbing. Adjacent possible = options one step from the current state.
**Coding-agent analogy:** Code changes with high coupling (K) form a rugged landscape: local edits break distant tests, greedy agents stall at local optima. Task difficulty ~ coupling of touched modules.
**Where the analogy fails:** Real codebases have structure (types, tests) that gives informative gradients; LLM proposals are not random single-bit mutations.
**Concrete experiment:** Simulate NK (N=20, K in {0,2,5,10}) with greedy vs population-of-restarts searchers to calibrate; then regress real agent success on a measured coupling proxy (co-change count of touched files from git history). Cheap, deterministic given seeds.

### A4. Axelrod - cooperation tournaments, dissemination of culture
**Source:** Axelrod (1997) "The dissemination of culture," J. Conflict Resolution 41(2):203-226, https://web.mit.edu/curhan/www/docs/Articles/15341_Readings/Culture_and_Identity/Axelrod-1997.pdf . IPD tournament library: Axelrod-Python, https://arxiv.org/pdf/1604.00896 . Original 1984 *Evolution of Cooperation* book: UNVERIFIED (from memory; no URL seen). Verified: Y-search for the two cited.
**Reliability:** peer-reviewed; preprint.
**Status:** established (models); mapping interpretation.
**Plain-language concept:** Nice, provocable, forgiving reciprocity wins repeated games; similarity-driven imitation yields local convergence with global polarization.
**Coding-agent analogy:** Agents that share a repo repeatedly "play": reciprocal rules (do not overwrite a peer's claimed file; yield if the peer yielded last time). Culture model: conventions (style, naming) converge within clusters of agents that talk, but separate clusters diverge.
**Where the analogy fails:** Agents are cooperative by design; conflict is accidental (races), not strategic. Culture "traits" are not independent discrete features.
**Concrete experiment:** Simulated file-claim game with scripted agents: tit-for-tat claim yielding vs always-grab vs always-yield; metric = merge conflicts and total completed tasks over 1000 rounds.

### A5. Schelling segregation
**Source:** T. Schelling (1971) "Dynamic models of segregation," J. Math. Sociology 1(2):143-186, https://www.tandfonline.com/doi/abs/10.1080/0022250X.1971.9989794 ; PDF https://www.suz.uzh.ch/dam/jcr:00000000-68cb-72db-ffff-ffffff8071db/04.02_schelling_71.pdf . Verified: Y-search.
**Reliability:** peer-reviewed.
**Status:** established.
**Plain-language concept:** Mild individual preferences produce strong macro-level sorting (tipping); no simple map from micro-incentive to macro outcome.
**Coding-agent analogy:** Mild per-agent preferences (prefer working near code I already know/cached) cause agents to specialize into territories, which could be good (locality) or bad (orphaned areas, bus-factor).
**Where the analogy fails:** Agents have no residential cost of moving; specialization is a routing policy we control.
**Concrete experiment:** Router with a "familiarity bonus" b in {0,0.1,0.3,0.5}; measure Gini of per-module agent assignment and task latency on a replayed task stream.

### A6. Epstein & Axtell - Sugarscape
**Source:** *Growing Artificial Societies: Social Science from the Bottom Up* (Brookings/MIT Press 1996), https://direct.mit.edu/books/book/2503/Growing-Artificial-SocietiesSocial-Science-from . Verified: Y-search.
**Reliability:** book.
**Status:** established (method); mapping interpretation.
**Plain-language concept:** Simple local rules on a resource landscape generate trade, wealth inequality, migration: "grow it to explain it."
**Coding-agent analogy:** Treat token/time budget as "sugar": agents with budgets, metabolism (cost per step), and a task landscape; observe inequality of budget use and starvation of hard tasks.
**Where the analogy fails:** Budgets are allocated by humans/orchestrator, not foraged.
**Concrete experiment:** Replay a task-cost distribution through a scripted-agent simulator with first-come vs budget-weighted dispatch; metric = fraction of heavy tasks finished, budget Gini.

### A7. SFI artificial stock market
**Source:** Arthur, Holland, LeBaron, Palmer, Tayler (1997) "Asset Pricing Under Endogenous Expectations in an Artificial Stock Market," https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2252 (SFI WP 96-12-093: https://ideas.repec.org/p/wop/safiwp/96-12-093.html). Verified: Y-search.
**Reliability:** working paper / book chapter / journal (Economic Notes 26).
**Status:** established as a model result; mapping interpretation.
**Plain-language concept:** Agents continually adapt predictors to a market their own predictions create; slow exploration gives equilibrium, fast exploration gives complex, bubble-like dynamics.
**Coding-agent analogy:** Agents that continually rewrite shared heuristics/memory in response to outcomes that depend on other agents' heuristics: memory-update rate is the exploration-rate knob; too fast yields churn.
**Where the analogy fails:** Prices are a single scalar feedback; repo feedback is multi-dimensional and sparse.
**Concrete experiment:** Sweep memory-write rate (max N lessons per task) and measure repeat-error rate and memory churn (fraction of entries rewritten) across a task stream.

### A8. Bak - self-organized criticality
**Source:** Bak, Tang, Wiesenfeld (1987) PRL 59:381, https://dx.doi.org/10.1103/physrevlett.59.381 . Verified: Y-search. A pedagogical review reportedly questions the 1/f claim (https://arxiv.org/pdf/physics/0204033).
**Reliability:** peer-reviewed.
**Status:** established (sandpile); applicability to software/agents = speculative.
**Plain-language concept:** Driven threshold systems self-tune to a critical state with power-law avalanches.
**Coding-agent analogy:** Failure/rework cascades in a multi-agent repo (one bad edit triggers a chain of fixups) may be heavy-tailed; dependency graph = sandpile.
**Where the analogy fails:** No evidence agent systems are "self-tuned" to criticality; heavy tails could be just preferential attachment or task heterogeneity.
**Concrete experiment:** From existing run logs, compute distribution of "fix-up chain length" per root edit; fit power-law vs lognormal; report which wins (likelihood ratio). Zero new compute.

### A9. Watts-Strogatz small world; Barabasi-Albert scale-free
**Source:** Watts & Strogatz (1998) Nature 393:440-442 (seen via https://www.semanticscholar.org/paper/Collective-dynamics-of-%E2%80%98small-world%E2%80%99-networks-Watts-Strogatz/d61031326150ba23f90e6587c13d99188209250e and https://www.nature.com/articles/s42254-023-00628-6); Barabasi & Albert (1999) Science 286:509-512, https://www.science.org/doi/10.1126/science.286.5439.509 . Verified: Y-search.
**Reliability:** peer-reviewed.
**Status:** established; mapping interpretation.
**Plain-language concept:** A few long-range shortcuts give short paths with high clustering; growth with preferential attachment gives hubs.
**Coding-agent analogy:** Agent communication topology (who may message/read whom). Dense clusters per module plus a few cross-module shortcuts; orchestrator = hub (a single point of failure and bottleneck).
**Where the analogy fails:** Topology is a design choice and LLM context cost per edge is token-priced; hubs are by-design, not emergent.
**Concrete experiment:** Same task set with 4 topologies (star, ring, small-world rewire p=0.1, full mesh) at fixed N; metric = pass rate and total tokens. Prior LLM-debate results exist (see Part B).

### A10. Simon - near-decomposability
**Source:** H. Simon (1962) "The Architecture of Complexity," Proc. Am. Philos. Soc. 106(6):467-482, https://sites.cc.gatech.edu/classes/AY2013/cs7601_spring/papers/Simon-Complexity.pdf (also https://www.sfipress.org/21-simon-1962). Verified: Y-search.
**Reliability:** peer-reviewed/classic.
**Status:** established (conceptual); strong fit.
**Plain-language concept:** Complex systems that evolve are hierarchical and nearly decomposable: strong within-module links, weak between-module links; stable subassemblies evolve faster.
**Coding-agent analogy:** Assign agents to modules with narrow interfaces; communicate through contracts, not through shared scratch state. Memory should be scoped per module with a thin global layer.
**Where the analogy fails:** Real code coupling often violates the module map; LLM agents can read everything, so "decomposition" must be enforced, not assumed.
**Concrete experiment:** Measure cross-module edge ratio of agent-touched files vs module boundaries from git history; correlate with merge conflicts/rework per task. Then restrict agents to a module scope and compare.

### A11. Ostrom - polycentric governance, commons design principles
**Source:** E. Ostrom, *Governing the Commons* (CUP 1990); principles summarized at https://wiki.p2pfoundation.net/Governing_the_Commons (secondary) and https://sesmad.dartmouth.edu/theories/54 (secondary; notes a 2010 meta-analysis extension). Full list of 8: UNVERIFIED (from memory) beyond the ones named: clear boundaries, monitoring, graduated sanctions, conflict-resolution mechanisms, user-modifiable rules. Verified: Y-search (secondary only).
**Reliability:** book (primary not opened); secondary web.
**Status:** established in field studies; applying to agents = interpretation.
**Plain-language concept:** Durable commons have defined boundaries, rules matched to local conditions, monitoring, graduated sanctions, cheap conflict resolution, nested governance.
**Coding-agent analogy:** The shared memory/repo is a commons: write boundaries (who may write which scope), provenance/monitoring, graduated response to bad writes (flag, quarantine, revert), cheap arbitration route to a human.
**Where the analogy fails:** Agents do not have self-interest or reputations across sessions unless we build them.
**Concrete experiment:** Inject 5 bad memory entries into a 100-entry store; compare no governance vs provenance+quarantine-on-failure; metric = number of later tasks poisoned.

### A12. Levinthal (1997); Rivkin & Siggelkow (2003) - NK organizational models
**Source:** Levinthal (1997) "Adaptation on Rugged Landscapes," Management Science 43(7):934-950, https://pubsonline.informs.org/doi/10.1287/mnsc.43.7.934 ; Rivkin & Siggelkow (2003) "Balancing Search and Stability," Mgmt Sci 49(3):290-311, https://pubsonline.informs.org/doi/10.1287/mnsc.49.3.290.12740 . Verified: Y-search.
**Reliability:** peer-reviewed.
**Status:** established (as simulation models); mapping interpretation.
**Plain-language concept:** Initial organizational form has lasting effect on rugged landscapes; broad search elements raise the value of stabilizing elements (e.g., hierarchy).
**Coding-agent analogy:** Orchestrator = stabilizing hierarchy; explorers = search breadth. Broader parallel exploration needs a stronger integrator/verifier; tightly coupled tasks need one decision-maker.
**Where the analogy fails:** Models assume decision elements, not open-ended generation.
**Concrete experiment:** In a simulated NK org (N=12) vary number of parallel searchers vs central integrator acceptance threshold; use the result to set explorer count per coupling level.

### A13. Page - diversity prediction theorem; Hong-Page
**Source:** Hong & Page (2004) PNAS 101(46):16385-16389, https://www.pnas.org/content/101/46/16385 . Diversity prediction theorem (Page, *The Difference* 2007): UNVERIFIED (from memory; no primary URL seen); the error-decomposition (collective error = average error - diversity) is cited via Krogh & Vedelsby 1994 in https://arxiv.org/pdf/2609.14570 . Verified: Y-search for Hong-Page.
**Reliability:** peer-reviewed; theorem is a mathematical identity.
**Status:** theorem established; the Hong-Page "diversity trumps ability" result is conditional and has been criticized (critique by Thompson 2014: UNVERIFIED from memory).
**Plain-language concept:** Collective squared error = mean individual error minus prediction diversity. Diversity helps only when members are individually competent.
**Coding-agent analogy:** Parallel same-model agents have near-zero diversity, so ensembles give little. Diversity must come from differing prompts, tools, context slices, models.
**Where the analogy fails:** Code correctness is not squared-error on a number; "voting" on patches needs a verifier.
**Concrete experiment:** For 30 tasks, run k=5 attempts under (a) same prompt, (b) varied prompt, (c) varied model; measure pass@k and pairwise failure correlation. Report oracle-selected and test-selected pass rates.

### A14. Krakauer / Flack - collective computation and coarse-graining
**Source:** J. Flack (2017) "Coarse-graining as a downward causation mechanism," Phil. Trans. R. Soc. A, https://extendedevolutionarysynthesis.com/wp-content/uploads/2017/02/Flack_2017SFI_PhilTrans.pdf ; SFI C4 group https://c4.santafe.edu/c4pubs/ . Verified: Y-search.
**Reliability:** peer-reviewed.
**Status:** established as theory/empirical in animal/neural systems; mapping interpretation.
**Plain-language concept:** Micro-level variation is compressed into slower macro variables that feed back to constrain the micro level.
**Coding-agent analogy:** Shared memory as coarse-graining: compress traces into a few macro variables (module health, convention, known-hazard) that constrain agents' next actions. The compression itself is the "computation."
**Where the analogy fails:** The compression is done by an LLM summarizer with unknown loss; no measure of what was discarded.
**Concrete experiment:** Compress 100 session logs into memory at 3 compression ratios; test downstream task accuracy on questions requiring detail vs gist; plot accuracy vs ratio.

### A15. West - scaling laws
**Source:** West, Brown, Enquist (1997) Science 276:122-126, https://www.science.org/doi/10.1126/science.276.5309.122 ; Bettencourt et al. (2007) PNAS 104:7301-7306, https://www.pnas.org/doi/10.1073/pnas.0610172104 . Metabolic-scaling model is contested (Apol et al. 2008, https://besjournals.onlinelibrary.wiley.com/doi/full/10.1111/j.1365-2435.2008.01458.x). Verified: Y-search.
**Reliability:** peer-reviewed.
**Status:** established for cities empirically; biological derivation contested; agent analogy speculative.
**Plain-language concept:** Output and cost scale as power laws in size; superlinear for innovation (beta ~1.2), sublinear for infrastructure (~0.8).
**Coding-agent analogy:** Does throughput scale sub- or superlinearly in number of agents? Coordination overhead suggests sublinear; shared-memory reuse may give superlinear gains in mature stores.
**Where the analogy fails:** No network-geometry derivation applies to LLM agents; fit is empirical only.
**Concrete experiment:** Run N in {1,2,4,8} agents on same task batch; fit throughput ~ N^beta and token cost ~ N^gamma; report beta, gamma with CIs.

### A16. Ashby - requisite variety
**Source:** Ashby, *An Introduction to Cybernetics* (1956), http://panarchy.org/ashby/variety.1956.html . Verified: Y-search.
**Reliability:** book; the law is a theorem.
**Status:** established (theorem); applying to agents = interpretation.
**Plain-language concept:** A regulator can only counter as much disturbance variety as it has response variety.
**Coding-agent analogy:** A single agent with one toolset/prompt cannot cover a task space of many failure types; verifier/review variety must match defect variety (types of bugs).
**Where the analogy fails:** "Variety" is not directly countable for LLM behaviors; more variety inside the regulator can also add noise.
**Concrete experiment:** Catalog defect classes in past failures (e.g., 10); measure which classes are caught by each reviewer/check; compute coverage; add a check only if it covers a currently-missed class.

### A17. Mitchell - Complexity: A Guided Tour; SFI Complexity Explorer
**Source:** M. Mitchell, *Complexity: A Guided Tour* (OUP 2009), https://books.google.com/books/about/Complexity.html?id=j-PQCwAAQBAJ ; Complexity Explorer https://www.complexityexplorer.org/courses/165-introduction-to-complexity . Verified: Y-search.
**Reliability:** book; educational platform.
**Status:** established (survey).
**Plain-language concept:** Survey of dynamics, chaos, information, evolution, networks, agent-based modeling.
**Coding-agent analogy:** Onboarding/reference only; supplies shared vocabulary.
**Where the analogy fails:** Not a source of agent-specific claims.
**Concrete experiment:** None (reading list).

### A18. ABM tooling and protocols - Mesa, NetLogo, ODD, Concordia, Melting Pot
**Source:** Mesa 3: https://www.theoj.org/joss-papers/joss.07668/10.21105.joss.07668.pdf ; NetLogo: Wilensky (1999), https://ccl.northwestern.edu/2013/netlogo-agent2004c.pdf ; ODD: Grimm et al. (2020) JASSS 23(2):7, http://jasss.soc.surrey.ac.uk/23/2/7.html ; Concordia: https://arxiv.org/abs/2312.03664 and v2.0 tech report arXiv:2507.08892 (ID from search summary only) and https://github.com/google-deepmind/concordia ; Melting Pot: https://arxiv.org/abs/2107.06857 , 2.0 https://arxiv.org/abs/2211.13746 . Verified: Y-search.
**Reliability:** peer-reviewed (Mesa/ODD/Melting Pot ICML), preprint, software repo.
**Status:** established tooling.
**Plain-language concept:** ODD gives a standard 7-element description of a simulation; Mesa/NetLogo run agent models; Concordia uses an LLM "game master" to adjudicate grounded actions; Melting Pot tests generalization to novel partners via background populations.
**Coding-agent analogy:** ODD as the spec template for any orchestration experiment (reproducibility); Mesa to simulate scripted agents cheaply before spending tokens; Melting Pot idea: evaluate an orchestrator against unseen "partner" agents/models.
**Where the analogy fails:** Concordia/Melting Pot target social simulation/RL, not code tasks.
**Concrete experiment:** Write each experiment in this document as an ODD sheet and a Mesa model with scripted agents; require a seed-pinned result before any LLM run.

---

## Part B. Prior art applying these ideas to LLM multi-agent systems (2023-2026)
All entries Y-search only (not opened) unless stated. arXiv IDs of form 26xx are as returned by search; treat dates as unverified.
- El Farol with LLM agents: Takata, Masumori, Ikegami, arXiv 2509.04537 https://arxiv.org/abs/2509.04537 ; arXiv 2602.23093 https://arxiv.org/pdf/2602.23093 ; arXiv 2608.05479 https://arxiv.org/pdf/2608.05479 .
- Sugarscape-style LLM: Masumori & Ikegami, arXiv 2508.12920 https://arxiv.org/abs/2508.12920 .
- Schelling + LLM (one LLM agent in Mesa): arXiv 2607.17948 https://arxiv.org/html/2607.17948v1 .
- Axelrod IPD tournaments with LLMs: arXiv 2509.04847 https://arxiv.org/abs/2509.04847 ; arXiv 2507.02618 https://arxiv.org/pdf/2507.02618 ; arXiv 2501.16173 https://arxiv.org/html/2501.16173v1 . Axelrod culture model with LLM agents: arXiv 2604.01520 https://arxiv.org/pdf/2604.01520 .
- LLM stock-market agents: StockAgent https://arxiv.org/abs/2407.18957 ; arXiv 2510.12189 https://arxiv.org/html/2510.12189v1 .
- Network topology: AgentsNet https://arxiv.org/pdf/2507.08616 ; small-world debate https://arxiv.org/abs/2512.18094 ; NetworkGames https://arxiv.org/html/2511.21783 ; topology diffusion https://arxiv.org/html/2510.07799v2 .
- Diversity decomposition: arXiv 2607.01661, 2607.17384, 2609.14570, 2603.20324, 2610.18786 (URLs as returned, e.g. https://arxiv.org/pdf/2609.14570).
- Stigmergy / shared environment for LLM agents: pressure fields + temporal decay arXiv 2601.08129 https://arxiv.org/pdf/2601.08129 ; emergent collective memory arXiv 2512.10166 https://arxiv.org/pdf/2512.10166 ; CodeCRDT (multi-agent code generation, CRDTs, stigmergy-adjacent) arXiv 2510.18893 https://arxiv.org/pdf/2510.18893 .
- Ostrom for LLM agents and memory governance: GovSim-style commons https://arxiv.org/pdf/2510.14401 ; power asymmetry https://arxiv.org/pdf/2605.29062 ; research swarms cheating/whistleblowing https://arxiv.org/pdf/2609.04170 ; **Governed Collaborative Memory** (private/shared boundaries, provenance, graduated ratification, human arbiter) https://arxiv.org/pdf/2605.04264 ; commons-governed AI taxonomy https://arxiv.org/html/2606.15466v1 ; vector subscriptions https://arxiv.org/pdf/2603.20833 .
- SOC / criticality: arXiv 2609.17419 https://arxiv.org/abs/2609.17419 (single long-horizon agents); herding/runaway cascades arXiv 2610.30769 https://arxiv.org/html/2610.30769v1 ; error cascades arXiv 2603.04474 https://arxiv.org/pdf/2603.04474 .
- Requisite variety / cybernetics for agents: arXiv 2605.10754 https://arxiv.org/pdf/2605.10754 .
- NK-style LLM search landscapes: LLM-assisted algorithm search landscape (empirical, not NK) arXiv 2504.19636 https://arxiv.org/html/2504.19636v2 .
- CAS framing of LLM-MAS: arXiv 2506.01839 https://arxiv.org/pdf/2506.01839 ; arXiv 2505.21298 https://arxiv.org/pdf/2505.21298 ; swarm intelligence arXiv 2503.03800 https://arxiv.org/html/2503.03800v1 .
- Coding multi-agent organization: survey arXiv 2404.04834 https://arxiv.org/pdf/2404.04834 ; design patterns arXiv 2511.08475 https://arxiv.org/html/2511.08475v2 ; SEMAP arXiv 2510.12120 https://arxiv.org/pdf/2510.12120 ; "When more is less" arXiv 2609.19759 https://arxiv.org/pdf/2609.19759 .
- SFI current work: AI Foundations to Frontiers project https://www.santafe.edu/research/projects/artificial-intelligence-foundations-frontiers ; 2025 working group on collective learning https://www.santafe.edu/events/augmenting-intelligence-through-collective-learning1 ; AI and multi-scale human intelligence workshop https://www.santafe.edu/info/ai-and-multi-scale-human-intelligence/abstract ; metacognition in human-AI teams https://www.santafe.edu/events/metacognitive-intelligence-in-human-ai-teams-2026 ; workshop report https://arxiv.org/pdf/2112.06864 .

---

## Part C. Deliverables

### (1) Ranked top-8 ideas most likely to improve coding-agent orchestration/collaboration/memory
1. **Page diversity decomposition (A13):** measure inter-agent failure correlation; spend parallel budget on diverse (prompt/context/model) attempts, not clones. Cheapest, most directly measurable.
2. **Simon near-decomposability (A10):** module-scoped agents and memory with thin global layer; measure cross-module coupling vs rework.
3. **Ostrom governance of shared memory (A11):** boundaries, provenance, graduated quarantine, human arbiter. Closest published design (2605.04264) already validates the direction.
4. **Arthur lock-in (A2):** cap retrieval share per memory entry; test for early-convention lock-in. Simple instrumentation.
5. **Ashby requisite variety (A16):** map defect classes to checks; add checks only for uncovered classes.
6. **Flack coarse-graining (A14):** treat memory compression as a measured, lossy macro-variable layer; test accuracy vs compression ratio.
7. **Levinthal / Rivkin-Siggelkow + NK (A3, A12):** set explorer count and integrator strictness from measured coupling.
8. **Stigmergy with decay (Part B, Holland A1 credit):** strength-weighted, decaying shared traces instead of an append-only store.
(Lower: SOC, West scaling, Sugarscape budgets: diagnostic lenses on logs, not first-line changes.)

### (2) Prior-art warnings for "novel" claims
- "Stigmergy / pheromone-decay shared state for LLM agents": prior art (2601.08129, 2512.10166, 2510.18893).
- "Governed / Ostrom-inspired shared memory for LLM agents": prior art (2605.04264, 2510.14401, 2609.04170, 2606.15466).
- "Diversity prediction theorem / diversity beats ability for LLM ensembles": prior art (2607.01661, 2607.17384, 2609.14570, 2603.20324).
- "Small-world / scale-free topologies for multi-agent LLMs": prior art (2512.18094, 2507.08616, 2511.21783).
- "LLMs in El Farol, Sugarscape, Axelrod IPD, artificial stock market": all done (Part B). Schelling with a full LLM population: not found, but a Mesa+LLM Schelling paper exists (2607.17948), so say "not found" not "first".
- "Requisite variety for agents": at least one 2026 paper (2605.10754).
- "SOC in LLM agents": at least one (2609.17419).
- "NK landscapes for LLM coding agents": I found none; LLM algorithm-search landscape paper exists (2504.19636). Claim only "not found in my search", not "novel".
- Genuinely less covered (per my search only): applying these specifically to coding-agent orchestration with git-derived coupling measures; Simon near-decomposability as agent/memory scope design; credit-assigned (classifier-system style) lesson strengths from build outcomes. Absence of search hits is not proof of novelty.

### (3) What I could not verify
- No page was opened in full; WebFetch was blocked by a hook. All "Y-search" entries rest on search-result titles/snippets. Claims about paper contents (e.g., "claims O(1) coordination overhead", critical density 0.230) come from search summaries.
- Primary text of Ostrom's eight design principles; Page's *The Difference*; Axelrod's 1984 book; Holland's *Induction*/classifier paper; Ashby primary text beyond the panarchy.org copy (not read); Kauffman-Weinberger 1989 (reference-list mention only); Langton/Packard edge-of-chaos papers; Thompson's critique of Hong-Page.
- Concordia v2.0 report ID 2507.08892 and arXiv IDs in the 26xx range are as returned by search; dates, versions, peer-review status not checked.
- Whether SFI has published agent-specific results beyond the event/project pages listed (those pages were seen only as search results). CoevolveSim and "Agentic AI and the next intelligence explosion" were named in a search summary without a URL I saw: UNVERIFIED.
- NetLogo's current version; Complexity Explorer course list beyond Introduction to Complexity.
- No experiment in this document has been run.
