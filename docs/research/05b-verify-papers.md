# 05b Paper verification (checked 2026-11-19)

Method: every arXiv ID below resolved (including all 26xx IDs). Abstract pages were opened, and the full text was retrieved as arXiv HTML (PDF text for 2605.04264 and Krogh and Vedelsby). Full text was searched by targeted pattern, not read line by line, so "OPENED-IN-FULL" means "full text retrieved and searched", not "every page read". No figures were filled from memory. Where a number appears only in a chart, it is marked NOT IN TEXT.

Peer-review rule: "preprint" means the arXiv page shows no venue. Only venues stated on the page are listed.

## 1. Kim et al., Towards a Science of Scaling Agent Systems
- arXiv 2512.08296 (abs + html v3). Authors: Yubin Kim, Ken Gu, ... Xin Liu (Google Research / MIT et al.). v1 2025-12-09, v3 2026-04-08. Full text retrieved: yes.
- Status: preprint (no venue on page). Code: https://github.com/ybkim95/agent-scaling (framework, configs, prompts, analysis, sanitized traces). Licence for code not stated in text.
- Abstract: 260 configurations, six benchmarks, five architectures, three LLM families. Cross-validated R^2 = 0.373 (0.413 with ACI).
- +80.8% / -70.0% CONFIRMED: "ranges from +80.8% on decomposable financial reasoning to -70.0% on sequential planning". (Finance-Agent and PlanCraft; relative to the single-agent baseline.)
- Threshold CONFIRMED, with a number the plan may lack: "tasks where single-agent performance already exceeds 45% accuracy experience negative returns" (beta = -0.236, p = 0.004). It is a regression coefficient from observational configs, not a controlled threshold.
- Error amplification CONFIRMED: "Independent systems amplify trace-level errors 17.2x"; centralized 4.4x. Body text also gives decentralized 7.8x and hybrid 5.1x, single agent 1.0.
- 87% = best architecture predicted for held-out configurations. This is relative selection only; the paper says it is "more stable than absolute cross-domain performance prediction".

## 2. When Sub-Agents Work in Parallel (dynamic concurrency, long-horizon coding)
- arXiv 2610.10263 (abs + html v1). Authors: Han Li, HanHaoNing Li, Ziqian Jiang, Yiling Lou. v1 2026-10-07. Full text retrieved: yes.
- Status: preprint. Artifact: https://github.com/schwerli/Concurrency-Failures-Trajectory-Artifact (2,124-cell manifest, evaluator summaries, annotations, scripts). Licence not stated. Benchmark data "referenced rather than redistributed where licenses require it".
- Design: Codex, Claude Code, Kimi Code, concurrency on vs off; 354 tasks, 2,124 executions, 11.2B tokens, USD 20,780 at API rates. Benchmarks: RepoZero, ProgramBench, NL2Repo (226 repo-generation tasks), LoopsBench (28 evolution tasks), plus 100 SWE-bench Verified tasks.
- -11.9..+2.3 CONFIRMED: "resolution effects range from an 11.9 percentage point decrease to a 2.3 point increase". Token use "1.41 to 3.31 times" CONFIRMED.
- Caveat: gains appear on long-horizon sets (esp. LoopsBench) and none on SWE-bench Verified. The range is quoted as an example ("e.g.") across agents/benchmarks, so it is not one pooled effect.
- Taxonomy: four categories, 13 subcategories, 28 patterns.

## 3. CooperBench
- arXiv 2601.13295 (abs + html v2). Authors: Arpandeep Khatua, Hao Zhu, ... Diyi Yang (Stanford, SAP Labs). v1 2026-01-19, v2 2026-01-26. Full text retrieved: yes.
- Status: preprint (no venue on page). Site: https://cooperbench.com. A resolver model is on Hugging Face (CodeConflict/Qwen2.5-Coder-0.5B-Merge-Resolver).
- Headline (abstract): "agents achieve on average 30% lower success rates when working together compared to performing both tasks individually". Intro adds GPT-5 and Claude Sonnet 4.5 agents reach only 25% in cooperation, "around 50% lower" than Solo. The two figures differ (30% average vs about 50% for the two named models); do not conflate.
- Size: abstract says "over 600" tasks; body says 652 task pairs, 199 features, 52 task sets, 12 repos, 4 languages.
- Dataset licence: NOT STATED in the retrieved text. The source repos carry MIT, MIT-CMU, BSD-3, Apache-2.0 (appendix table). The paper itself is CC BY-SA 4.0. Treat dataset licence as unverified.

## 4. Memory papers vs "provenance lint + supersede-not-delete + re-verify-on-use for coding-agent shared memory"
- 2605.04264 Governed Collaborative Memory as Artificial Selection (Cuadros, Maiga, Meskhidze, Curtis-Trudel). v1 2026-05-05, CC BY 4.0. Full text via PDF: yes. A Viewpoint paper (position), no benchmark. Argues memory governance is a selection regime (persist / private / rejected / abstained / superseded). Layered architecture: agent-local, shared institutional, archive, project-continuity memory, with provenance and version lineage. Evidence is "documented traces from one running ... ecosystem", which "do not establish causal superiority". Not coding-specific (0 hits for code/software). 0 hits for lint, re-verify, staleness.
- 2606.24535 Governed Shared Memory for Multi-Agent LLM Systems (Margalit et al., Caura.ai). v1 2026-06-23, CC BY 4.0. Full text: yes. Preprint. Names four failure modes (unauthorized leakage, stale propagation, contradiction persistence, provenance collapse). Primitives: scoped retrieval, temporal supersession, provenance tracking, policy-governed propagation. Implemented in MemClaw, evaluated with ArgusFleet. Closest prior art: it does supersession (`supersedes_id` edge or older row flipped to non-active) and provenance chains (`derived_from`; 100% of depth-four chains reconstructed). It has no re-verify-on-use or provenance lint. Its own negative result: a near-duplicate gate can reject a contradictory write before the async contradiction detector sees it. Code availability not found. Not coding-specific.
- 2505.18279 Collaborative Memory (Rezazadeh et al.). v1 2025-05-23. Full text: yes. Preprint. Private and shared memory tiers, bipartite access-control graph, "immutable provenance attributes" on each fragment, read/write policies. 0 hits for supersede, stale, re-verify, delete. Focus is permissions, not staleness.
- Net: provenance and supersession both have prior art in 2606.24535, and provenance-for-permission has prior art in 2505.18279. Supersede-not-delete is not unique. No retrieved paper does a provenance lint or re-verification of a memory against the code on use, and none targets coding agents. That absence is "not found in these three", not "novel in the literature".

## 5. Lin et al., Sleep-time Compute
- arXiv 2504.13171 (abs + html v1). Authors: Kevin Lin, Charlie Snell, Yu Wang, Charles Packer, Sarah Wooders, Ion Stoica, Joseph E. Gonzalez. 2025-04-17. CC BY 4.0. Full text retrieved: yes. Preprint on page. Code and data: https://github.com/letta-ai/sleep-time-compute (licence not stated in text).
- Design: sleep-time S(c) -> c' pre-processes context before the query; test-time uses a smaller budget b << B. It is NOT total-compute-matched. Comparison is at equal TEST-TIME token budget (and against pass@k at the same test-time budget); sleep-time tokens are an additional cost. Total-cost accounting appears only in the multi-query amortization experiment.
- Numbers (abstract): about 5x less test-time compute for equal accuracy (Stateful GSM-Symbolic and Stateful AIME); up to +13% / +18% accuracy by scaling sleep-time compute; 2.5x lower average cost per query with Multi-Query GSM-Symbolic.
- Caveats stated: "at the test-time compute budgets [high], the test-time compute only baseline slightly outperforms sleep-time compute". Gain correlates with query predictability. SWE-Features case study: up to roughly 1.5x fewer test-time tokens at low budget; at high budget test-time-only is better. It scores predicted file sets (F1), not tests.

## 6. AuthBench and ToolPrivBench
- 2605.14859 Do Coding Agents Understand Least-Privilege Authorization? (Evolvent AI Research Team). v1 2026-05-14, v2 2026-05-15; paper licence CC BY-NC-SA 4.0 (non-commercial: flag). Code: github.com/evolvent-ai/Authbench. Preprint. Full text: yes. AuthBench = 120 terminal tasks. Finding: "frontier models often omit permissions required by the execution chain while also granting unused or sensitive accesses"; "even successful runs leave many granted permissions unused". The numeric unused-grant rate is NOT IN TEXT (chart only, Fig. 4c). Other stated number: Sufficiency-Tightness Decomposition improves sensitive-task success by up to 15.8%. More reasoning does not fix it.
- 2606.20023 When Lower Privileges Suffice (ToolPrivBench; Yang et al.). v1 2026-06-18, v2 2026-07-07. Code and data: https://github.com/AISafetyHub/agent-tool-selection-bias/ (licence not stated). Preprint. Full text: yes. Eleven models, eight domains, five risk types. Metric OPUR (over-privileged tool use rate): "Six of the eleven models exceed 30% OPUR", Qwen3-8B 64.9%, LLaMA-3.1-8B 55.9%; Claude 4.6 Sonnet, GPT-5.2, GLM-5 "below 10%". Escalation after transient failures is "amplified"; the numeric effect was not extracted. Simulation only (no live tools). Note: this measures tool selection, not unused grants.

## 7. AgenticFlict
- arXiv 2604.03551 (abs + html v2). Authors: Daniel Ogenrwot, John Businge. Accepted at AIware 2026 (stated on page) = peer-reviewed. Full text: yes. Dataset on Zenodo, DOI 10.5281/zenodo.19396916; paper page marks "cc-license: by" (arXiv paper licence CC BY 4.0; the dataset licence itself was not independently opened). Stores hashes plus short previews (default 5 lines), not full conflict blocks, for licensing reasons.
- 27.67% CONFIRMED: 29,609 conflicting of 107K+ successfully simulated (from 142K+ Agentic PRs, 59K+ repos); 336,380 conflict regions. The 27.67% denominator is the 107K+ processed, not 142K. Textual conflicts only, agent PRs against their target branch (not agent-vs-agent).

## 8. Passes Alone, Fails Together
- arXiv 2609.25396 (html v1). Authors: Haocheng Xia, Eugene Wu, Yongjoo Park. 2026-09-21, CC BY 4.0. Six-page workshop paper accepted at EXPRESS 2026 (workshop). Code: https://github.com/illinoisdata/STALE-bench (the benchmark is called "stale"). Full text: yes.
- Numbers: 834 runs on 417 mined Django PR pairs showed one interference after grading correction; on 36 constructed tasks over 12 Django helpers, interference in 97% of runs; a message describing the completed concurrent change recovered 82%. Authors state the constructed rates "do not estimate how often these problems occur in practice". This tempers the CooperBench and AgenticFlict framing.

## 9. Anderson and Schooler 1991
- Psychological Science 2(6): 396-408, "Reflections of the environment in memory". Primary PDF opened (Northwestern-hosted copy; OCR-noisy); journal DOI 10.1111/j.1467-9280.1991.tb00174.x. Peer-reviewed. Full text retrieved: yes (searched).
- Abstract (quote): "the probability that a memory will be needed also shows reliable relationships to frequency, recency, and pattern of prior exposures". Sources: New York Times headlines, parental speech, email.
- Power-law claim: the paper states environment and memory both display "retention and practice functions that are at least approximately power laws", with retention fitted as P = A*T^-b (Ebbinghaus fit exponent .126). Caveat for the plan: this is need probability of words/senders over days, not reuse of code-memory items. Applying it to memory reuse is an analogy.

## 10. Krogh and Vedelsby 1994
- "Neural Network Ensembles, Cross Validation, and Active Learning", NIPS 7 (1994), pp. 231-238. Primary PDF opened (papers.nips.cc). Peer-reviewed.
- Identity (their eqs 2-10), regression with squared error and weights w_a >= 0 summing to 1: ensemble output V(x) = sum_a w_a V_a(x); ambiguity a(x) = sum_a w_a (V_a(x) - V(x))^2; per-input e(x) = eps_bar(x) - a(x), where eps_bar = sum_a w_a (f(x) - V_a(x))^2 and e = (f(x) - V(x))^2. Averaged over input distribution: E = E_bar - A_bar (ensemble generalization error = weighted mean member error minus weighted mean ambiguity). The sum-to-one constraint is "crucial". The paper's later "bias-variance" framing uses the same identity.

## 11. Page diversity prediction theorem
- Not a primary paper: the statement comes from Page's 2007 book *The Difference*, via the Mauboussin white paper (Legg Mason, PDF opened) and search-result summaries. Book NOT OPENED.
- Statement: collective error = average individual error - prediction diversity, with collective error (mean - truth)^2, average error mean of (xi - truth)^2, diversity mean of (xi - mean)^2. It is the same algebra as Krogh-Vedelsby with equal weights. It is an identity, so it implies only collective error <= average individual error. It does not show that adding diversity lowers error at fixed accuracy (critics on arXiv 2307.04709 and 2008.01485 were seen only as search snippets, NOT OPENED).

## 12. Cemri et al., MAST
- Why Do Multi-Agent LLM Systems Fail? arXiv 2503.13657 (html v3, 2025-10-26). Authors: Mert Cemri, Melissa Z. Pan, ... Ion Stoica (UC Berkeley). Paper licence CC BY-NC-ND 4.0. Full text: yes. Venue not stated on page (treat as preprint). Code: github.com/multi-agent-systems-failure-taxonomy/MAST; data: huggingface.co/datasets/mcemri/MAST-Data (licences not stated).
- Facts: MAST-Data 1600+ annotated traces, 7 MAS frameworks; taxonomy built from 150 traces, kappa = 0.88; 14 modes in 3 categories: system design issues (FM-1.x), inter-agent misalignment (FM-2.x), task verification (FM-3.x). Example frequencies: step repetition 15.7%, reasoning-action mismatch 13.2%, incorrect verification 9.1%, no/incomplete verification 8.2%.

## Corrections the plan needs
1. Do not call 2606.24535 or 2505.18279 coding-agent memory papers. Supersession and provenance have prior art (2606.24535 for supersession and derivation chains; 2505.18279 for immutable provenance). Re-verify-on-use and provenance lint were not found in any of the three, and 2605.04264 is a position paper with no experiments. Phrase the claim as "not found in these three".
2. CooperBench headline: abstract says 30% average lower; the roughly 50% figure (25% cooperation) is for GPT-5 and Sonnet 4.5 only. Task count is 652, not "over 600". Dataset licence is not stated; the paper is CC BY-SA, source repos MIT/BSD/Apache.
3. Sleep-time compute is not compute-matched on total cost; it matches test-time tokens only, with sleep-time cost extra. The 5x is test-time tokens; the 2.5x per-query saving needs many queries per context; at high test-time budgets plain test-time scaling wins.
4. AgenticFlict 27.67% denominator is 107K+ processed PRs (not 142K+) and covers textual conflicts versus target branch, not agent-vs-agent semantic conflicts.
5. Passes Alone: real mined Django pairs showed essentially no interference (1 of 834 runs); the 97% is for constructed tasks and the authors disclaim it as a frequency estimate. Use it as mechanism evidence only.
6. Kim et al.: the saturation point is about 45% single-agent accuracy from a regression with R^2 around 0.37-0.41, not a sharp threshold. Quote the error-amplification values as 17.2x independent, 4.4x centralized.
7. 2610.10263: the -11.9..+2.3 range is quoted as an example across agents/benchmarks; gains concentrate on long-horizon sets and are absent on SWE-bench Verified.
8. AuthBench: unused-grant rate is shown only in a chart (NOT IN TEXT); do not cite a number. Paper licence is CC BY-NC-SA 4.0. ToolPrivBench measures over-privileged tool selection (OPUR), not unused grants.
9. Anderson and Schooler power law is need probability for words and email senders by recency/frequency; applying it to memory reuse is an extrapolation. Page's theorem is an identity (same as Krogh-Vedelsby with equal weights), not evidence that diversity helps at fixed accuracy.
10. Only AgenticFlict (AIware 2026), Passes Alone (EXPRESS 2026 workshop), Krogh and Vedelsby (NIPS 1994) and Anderson and Schooler (Psychological Science 1991) show confirmed peer review; the rest are arXiv preprints as far as the pages show.
