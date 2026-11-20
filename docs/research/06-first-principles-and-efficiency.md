# 06 First principles, physics-style reasoning, and token/energy/cost efficiency

Date: 2026-11-19. Purpose: keep a coding-agent research project simple and cost-aware.

Evidence convention. Every source says OPENED-IN-FULL yes/no. In this session no source was read end to end. "Abstract page" means I fetched the arXiv abstract page only. "Search snippet" means I only saw a search-result summary and never opened the page. Anything marked UNVERIFIED is from memory or a secondary summary. Status is established, interpretation, or speculative. Numbers appear only where a source I saw states them.

Reliability scale: high = peer-reviewed or primary vendor measurement; medium = preprint, blog, or secondary summary; low = unvetted.

---

## A) First principles and simplicity

### A1. Musk's "algorithm" (five steps)
- Source: Everyday Astronaut, "Starbase Tour with Elon Musk" (Tim Dodd, July 2021, about 13:30 per secondary sources). Isaacson, *Elon Musk* (2023). Seen only via search snippets from startuparchive.org, blakesnotes.io and others. Direct fetch of startuparchive failed (EPROTO). OPENED-IN-FULL: no. Video not watched, book not read.
- Reliability: medium (secondary quoting of a primary). Status: interpretation (a management heuristic, not a measured result).
- Steps as summarised by the results I saw, NOT verbatim quotes: (1) question every requirement and attach a person's name to it; (2) delete any part or process you can; (3) simplify and optimize, only after deleting; (4) accelerate cycle time; (5) automate, last. The only verbatim quote I saw is from a startuparchive headline: "First, make your requirements less dumb. Your requirements are definitely dumb… It's particularly dangerous if a smart person gave you the requirements because you might not question them enough." The "add back at least 10%" test is attributed by the same summaries and is UNVERIFIED as exact wording. Exact five-step wording must be checked against the video or book before quoting.
- Application: before adding an agent role, tool, or memory layer, name its owner and the requirement it serves. Delete first, then automate.
- Where it fails: "delete until you add back 10%" is a heuristic with no evidence of calibration. Deleting safety checks or tests is a hazard (see A9).
- Experiment: take the current harness (tools, prompts, roles). Ablate one component at a time on a fixed task set (n tasks, k seeds). Record pass rate and tokens per passing task. Keep a component only if removing it costs more than the noise band.

### A2. Feynman / Fermi estimation
- Source: no primary opened. Search not run. OPENED-IN-FULL: no. UNVERIFIED citations (Fermi problems are standard; I cite no URL).
- Reliability: high as a method, but not checked here. Status: established (as a technique).
- Concept: reduce a quantity to a product of factors whose units you can bound, and get the order of magnitude before measuring.
- Application: estimate tokens per task as (turns) x (context tokens per turn) x (fraction not cached) before building. Compare to the later measurement.
- Where it fails: errors multiply when factors are correlated; gives no tail estimate.
- Experiment: write the estimate for 5 tasks first, then measure. Report the ratio measured/estimated per task. A log-ratio spread above about one order of magnitude means the model of the system is wrong.

### A3. Occam, MDL, Kolmogorov
- Source: not opened; no search run. OPENED-IN-FULL: no. UNVERIFIED (Rissanen MDL, Solomonoff/Kolmogorov are standard references I did not fetch).
- Reliability: high in theory. Status: established as a model-selection principle; Kolmogorov complexity is uncomputable (from memory).
- Concept: prefer the hypothesis that minimises description length of model plus data given the model.
- Application: prefer the harness variant whose extra complexity buys a measurable gain. Count lines/config knobs as description length.
- Where it fails: encoding choice is arbitrary; MDL does not weigh the cost of error.
- Experiment: for each harness variant record (tokens per passing task) and (lines of harness code + config keys). Plot the Pareto front; reject variants dominated on both.

### A4. Gall's law
- Source: not opened. OPENED-IN-FULL: no. UNVERIFIED wording ("a complex system that works is invariably found to have evolved from a simple system that worked", from memory).
- Reliability: low (aphorism). Status: interpretation.
- Application: start with one agent, one loop, and add parts only when a measured failure demands it.
- Where it fails: no evidence that it holds in general; some systems need co-designed parts.
- Experiment: keep a changelog where every added component links to the failing task that motivated it. Count components with no such link.

### A5. Unix philosophy and "worse is better"
- Source: not opened. OPENED-IN-FULL: no. UNVERIFIED (McIlroy; Gabriel's "Worse is Better", from memory).
- Reliability: medium. Status: interpretation.
- Concept: small tools that do one thing and compose; simplicity of implementation can beat completeness of interface.
- Application: tools as small, text-in/text-out commands the agent composes, with a stable contract.
- Where it fails: composition costs tokens when every pipe stage needs an LLM turn.
- Experiment: compare one composite tool versus three small tools on the same tasks; measure tool-call count and tokens per passing task.

### A6. Hickey, "Simple Made Easy"
- Source: not opened. OPENED-IN-FULL: no. UNVERIFIED (talk, 2011, from memory).
- Reliability: medium. Status: interpretation.
- Concept: "simple" means few intertwined concerns (objective); "easy" means near at hand (subjective).
- Application: judge a design by how many concerns are braided together, not by how fast it was to write.
- Where it fails: "complecting" has no agreed metric.
- Experiment: count cross-module dependencies (import edges) per feature; track over time.

### A7. Brooks, "No Silver Bullet"
- Source: search result listing only: UNC TR86-020 (https://www.cs.unc.edu/techreports/86-020.pdf) and IEEE Computer 20(4), 1987. OPENED-IN-FULL: no (snippet summary).
- Reliability: high (primary exists, I did not read it). Status: established as argument, interpretation as prediction.
- Concept (from the summary): essential complexity (conceptual structure) versus accidental complexity (representation, tooling). Unless accidental work exceeds 9/10 of effort, removing it cannot give an order-of-magnitude gain.
- Application: an agent harness mostly attacks accidental work; do not expect it to remove the essential difficulty of specifying the right change.
- Where it fails: LLMs may change what counts as accidental.
- Experiment: label time-to-pass components (reading, specifying, editing, testing). Report what share the agent actually cut.

### A8. Chesterton's fence
- Source: not opened. OPENED-IN-FULL: no. UNVERIFIED (Chesterton, *The Thing*, 1929, from memory).
- Reliability: medium. Status: interpretation.
- Application: counter to A1. Before deleting a check, test, or guard, find why it exists (git blame, linked issue).
- Where it fails: unlimited archaeology costs more than a revertible deletion.
- Experiment: delete only behind a flag or in a branch with a revert; if the removal is reverted within N days, record the cost. Estimate the delete/revert ratio.

---

## B) Physics-style principles

### B1. Budgets and dimensional analysis
- Source: none opened. OPENED-IN-FULL: no. Status: established (as discipline).
- Rule: every metric carries units (tokens, J, USD, s). Conserve budgets: total tokens = sum over turns of (input uncached + cached read + output); never add unlike units.
- Where it fails: a unit check cannot tell you the quantity is meaningful.
- Experiment: a unit-lint on the metrics code; fail CI if a field lacks a unit suffix.

### B2. Scaling laws (Kaplan 2020; Hoffmann 2022)
- Source: https://arxiv.org/abs/2001.08361 and https://arxiv.org/abs/2203.15556. OPENED-IN-FULL: no (abstract pages only).
- Reliability: high (peer-reviewed lineage), but my reading is abstract-level. Status: established for pretraining loss; interpretation when transferred to agents.
- Concept: Kaplan abstract says loss scales as a power law with model size, data size, and compute over more than seven orders of magnitude. Chinchilla abstract says model size and tokens should be scaled together; a 70B model with 4x more data than Gopher (280B) outperformed it at the same compute, and also cheaper to fine-tune and run.
- Application: inference cost is set by the deployed model; a smaller, better-trained model lowers per-token cost. For agent loops, expect diminishing returns, not unlimited gains.
- Where it fails: pretraining laws do not predict agent task pass rates.
- Experiment: fit pass rate versus log(tokens) on your task set for 3 model sizes; check whether the curve saturates.

### B3. Landauer's principle
- Source: search snippet (Wikipedia and others, URL https://en.wikipedia.org/wiki/Landauer's_principle). OPENED-IN-FULL: no.
- Reliability: high for the physics. Status: established.
- Concept: erasing one bit dissipates at least k_B T ln 2, about 2.9e-21 J at 300 K (search result figure).
- Why it is not binding: Google reports a median text prompt at 0.24 Wh (B/D below, 864 J). That is vastly above any plausible bit-erasure count times 2.9e-21 J; I did not compute a specific ratio and will not invent one. The same result states practical transistors dissipate thousands of times more than the limit per operation (that "thousands" figure is the snippet's claim, not mine). Data movement and idle power dominate.
- Experiment: none needed; use it only to justify ignoring thermodynamic floors and optimizing data movement and utilization.

### B4. Amdahl / Gustafson
- Source: not opened. OPENED-IN-FULL: no. UNVERIFIED (standard, from memory).
- Status: established. Amdahl: speedup bounded by the serial fraction. Gustafson: scale the problem with the machine.
- Application: parallel sub-agents help only if the serial parts (planning, merge, test run) are small. Anthropic itself notes most coding tasks have fewer parallelizable parts than research (see C6).
- Where it fails: ignores coordination cost that grows with workers.
- Experiment: measure wall time versus worker count 1, 2, 4 on the same tasks; fit the serial fraction.

### B5. Little's law and queueing, idle cost
- Source: not opened. OPENED-IN-FULL: no. UNVERIFIED (L = lambda W, from memory).
- Status: established (for stable systems in steady state).
- Application: in-flight requests = arrival rate x latency. A GPU that sits idle still draws power (Google's accounting counts idle machines, see D1). Utilization near 1 raises queueing delay.
- Where it fails: bursty arrivals and unstable queues.
- Experiment: log queue length, arrival rate, latency, and GPU power at idle versus load; report idle-compute fraction (defined below).

### B6. Roofline and memory-bound decode (GB10/Spark class)
- Source: spec search result only: gpuwerk.com summary lists 128 GB unified memory and 273 GB/s bandwidth for DGX Spark (low-quality aggregator, UNVERIFIED). Roofline model (Williams, Waterman, Patterson 2009) not opened; UNVERIFIED.
- Status: roofline established; the numbers for Spark are UNVERIFIED.
- Concept: decode is memory-bandwidth bound: tokens/s upper bound is about bandwidth / bytes read per token (roughly the active weights). Units: (GB/s) / (GB/token) = tokens/s.
- Application: on a Spark-class box, a quantized smaller model decodes faster per joule; batching raises arithmetic intensity.
- Where it fails: speculative decoding, batching, and KV-cache reads shift the bound; I did not verify measured figures.
- Experiment: measure tokens/s for 2 quantizations of one model at batch 1; compare to bandwidth / model-bytes. Record the gap.

---

## C) Efficiency and when to compute

### C1. Value of computation (Russell and Wefald, 1991)
- Source: citation only via search (Artificial Intelligence 49(1-3):361-395, doi 10.1016/0004-3702(91)90015-C); secondary summaries seen. OPENED-IN-FULL: no.
- Reliability: high (primary exists). Status: established as theory.
- Concept: treat a computation as an action. Do it only if expected improvement in decision quality exceeds its cost; stop when no computation has positive value. A myopic approximation was used for search control.
- Application: the "value-of-computation gate": run another sample, tool call, or verifier pass only if expected gain x value of success > cost.
- Where it fails: expected gain is hard to estimate; wrong priors cause stopping too early or late.
- Experiment: log per-step marginal pass-rate gain versus marginal cost on a task set; check if a simple gate beats a fixed budget.

### C2. Anytime algorithms (Zilberstein)
- Source: not opened. OPENED-IN-FULL: no. UNVERIFIED.
- Status: established concept; application interpretation.
- Application: the agent can be stopped at any time and return its best patch so far; quality should be a non-decreasing function of time.
- Experiment: plot best-so-far patch test-pass versus cumulative tokens across tasks; check monotonicity.

### C3. Compute-optimal test-time scaling (Snell et al. 2024)
- Source: https://arxiv.org/abs/2408.03314. OPENED-IN-FULL: no (abstract page).
- Reliability: medium-high (preprint). Status: established on the tested benchmarks, interpretation for coding agents.
- Concept: abstract says the effectiveness of test-time methods varies with prompt difficulty; allocating compute adaptively per prompt improved efficiency by more than 4x versus best-of-N, and in a FLOPs-matched evaluation a smaller model could beat a 14x larger one on problems where it had non-trivial success.
- Where it fails: needs a difficulty estimate; tested on math, not repository-scale edits.
- Experiment: bucket tasks by a cheap difficulty proxy; compare fixed N versus adaptive N at equal total tokens.

### C4. FrugalGPT and cascades
- Source: https://arxiv.org/abs/2305.05176. OPENED-IN-FULL: no (abstract page; the page text I saw is truncated before the numeric cost claim, so I do not repeat any percentage).
- Reliability: medium (preprint). Status: established for the tested query sets.
- Concept: abstract says API prices differ by up to two orders of magnitude and proposes prompt adaptation, LLM approximation, and LLM cascade, with FrugalGPT as a learned cascade.
- Application: try a cheap model first, escalate on a failed check (tests). Matches the project's tier-escalation rule.
- Where it fails: a bad scorer makes the cascade pay for both models; coding checks (tests) are cheap but not complete.
- Experiment: tier A then tier B on a fixed task set; report USD per passing task versus always-tier-B.

### C5. Speculative decoding, prompt caching, early stopping, adaptive effort
- Source: none opened. OPENED-IN-FULL: no. UNVERIFIED (Leviathan et al. 2023 and vendor caching docs from memory).
- Status: speculative decoding established (output distribution preserved, from memory); cache pricing is vendor-specific.
- Application: cache the stable prefix (system prompt, tool schemas) and keep it byte-stable; set reasoning effort by task difficulty; stop self-consistency sampling when answers agree.
- Where it fails: caches expire; changing the prefix invalidates it; early stop can lock in a wrong consensus.
- Experiment: report cached-read tokens / total input tokens per run; vary prefix stability and compare USD.

### C6. Anthropic multi-agent research system
- Source: https://www.anthropic.com/research/multi-agent-research-system (indexed; I read the matching passages, not the whole post). OPENED-IN-FULL: no.
- Reliability: medium-high (vendor engineering post, self-reported). Status: established for their own system; interpretation elsewhere.
- Quotes seen: "agents typically use about 4x more tokens than chat interactions, and multi-agent systems use about 15x more tokens than chats." Token usage alone "explains 80% of the variance" in BrowseComp performance, with tool calls and model choice as the other factors. Upgrading to Claude Sonnet 4 "is a larger performance gain than doubling the token budget on Claude Sonnet 3.7." They add that most coding tasks have fewer truly parallelizable tasks than research.
- Where it fails: one vendor, one benchmark, self-measured; correlation, not a causal law.
- Experiment: replicate the token-versus-pass-rate regression on your own tasks; check whether model choice dominates tokens.

### C7. Agent cost studies (SWE-bench)
- Source: none opened. A search snippet surfaced a multi-agent-debate evaluation saying MAD often fails to beat simple single-agent baselines such as CoT and Self-Consistency at higher inference cost (arXiv listing seen in search index; title and URL not captured). I also saw arXiv 2610.10263 on sub-agent concurrency in long-horizon coding (title only). OPENED-IN-FULL: no. UNVERIFIED for any numbers.
- Status: interpretation.
- Application: demand a single-agent baseline at equal tokens before accepting any multi-agent claim.
- Experiment: always report single-agent-at-equal-budget alongside the multi-agent arm.

### C8. Sleep-time compute
- Source: https://arxiv.org/abs/2504.13171. OPENED-IN-FULL: no (abstract page).
- Reliability: medium (preprint). Status: established on modified reasoning tasks only.
- Concept: precompute useful quantities about a context before queries arrive; abstract reports about 5x less test-time compute for equal accuracy on Stateful GSM-Symbolic and Stateful AIME.
- Application: precompute repo summaries and test maps during idle time (turns idle compute into value).
- Where it fails: wasted if queries are unpredictable; only tested on synthetic stateful tasks.
- Experiment: with and without a precomputed repo index; compare tokens per passing task including the precompute cost.

---

## D) Sustainability

### D1. Google, per-prompt disclosure (Aug 2025)
- Source: https://cloud.google.com/blog/products/infrastructure/measuring-the-environmental-impact-of-ai-inference (seen in search results; my fetch of a different Google URL returned no readable text) and arXiv 2508.15734. OPENED-IN-FULL: no.
- Reliability: medium-high (vendor primary, self-reported, not independently audited). Status: established for their serving stack; not portable.
- Seen via search summaries: median Gemini Apps text prompt 0.24 Wh, 0.03 gCO2e, 0.26 mL water. A secondary summary breaks 0.24 Wh into active accelerators 0.14, CPU+DRAM 0.06, idle machines 0.02, data-centre overhead 0.02 Wh (UNVERIFIED breakdown). A narrower accelerator-only method gives 0.10 Wh. A critic notes a median is not an average and location-based carbon would be higher.
- Experiment: report both accelerator-only and wall-power joules for the same run to expose boundary effects.

### D2. Epoch AI
- Source: https://epoch.ai/gradient-updates/how-much-energy-does-chatgpt-use (search summary only). OPENED-IN-FULL: no.
- Reliability: medium. Status: interpretation (a bottom-up estimate).
- Seen: about 0.3 Wh per typical GPT-4o query (Feb 2025), computed from about 1 s of H100 at 1500 W and 70% utilization = 1050 W-s; long inputs raise it (about 2.5 Wh at 10k tokens, almost 40 Wh at 100k per the summary); reasoning models may use substantially more.
- Where it fails: assumptions about hardware and throughput; agents send long contexts, so the long-input numbers matter most here.
- Experiment: measure J per request versus input length on local hardware; compare slope to this estimate.

### D3. Luccioni et al., "Power Hungry Processing"
- Source: https://arxiv.org/abs/2311.16863. OPENED-IN-FULL: no (abstract page).
- Reliability: medium-high. Status: established for the models tested.
- Concept: abstract proposes a systematic comparison of the energy and carbon cost of 1,000 inferences across task-specific and general-purpose models. I did not see the numeric findings; none are claimed here.
- Application: task-specific small models (linters, parsers) may beat an LLM turn for narrow subtasks.
- Experiment: replace one LLM subtask with a deterministic tool; compare J per task.

### D4. Strubell 2019, Patterson et al., Schwartz "Green AI"
- Source: Green AI abstract page https://arxiv.org/abs/1907.10597. OPENED-IN-FULL: no (abstract page). Strubell and Patterson not opened; UNVERIFIED.
- Reliability: medium. Status: interpretation (position paper).
- Concept: Green AI abstract proposes making efficiency an evaluation criterion alongside accuracy and reporting the financial cost ("price tag") of developing, training, and running models; it cites a 300,000x rise in compute from 2012 to 2018.
- Application: report cost next to accuracy in every result table.
- Where it fails: efficiency metrics are hard to compare across hardware.
- Experiment: every run emits a record {pass, tokens, joules, USD}.

### D5. Local energy measurement and GB10
- Sources: Zeus docs https://ml.energy/zeus/measure/ and blog https://ml.energy/blog/energy/measurement/measuring-gpu-energy-best-practices/ (search summaries only). NVIDIA forum thread https://forums.developer.nvidia.com/t/nvidia-smi-shows-nvidia-gb10-not-supported/350322 and NVIDIA support answer (snippets only). CodeCarbon not searched; UNVERIFIED. OPENED-IN-FULL: no for all.
- Reliability: medium. Status: established for NVML on discrete GPUs; GB10 specifics are forum-level evidence.
- Seen: Zeus wraps NVML `nvmlDeviceGetTotalEnergyConsumption` (Volta and newer), reporting joules and time in begin/end windows. On GB10, one forum report shows `nvidia-smi` returned `power.draw` (10.37 W at idle) while memory fields are N/A and power limit is N/A, by design for unified memory. One report gives 179.6 W at the outlet during a long prefill (single unit, secondary source). NVML counter availability on GB10 is UNVERIFIED; I did not confirm that the total-energy counter works there.
- Where it fails: GPU-only power omits CPU, DRAM, and PSU losses; use a wall meter to bound it.
- Experiment: measure idle W, load W by nvidia-smi sampling at 1 Hz, and wall power; integrate to J; report the ratio of GPU-reported to wall energy.
- Carbon: multiply kWh by the grid's gCO2e/kWh (location-specific, time-varying; no figure asserted here).

---

## 1. Eight design rules

1. State a requirement and an owner before adding any component; delete before automating. Source: A1 (summary, unverified wording). Check: every harness component links to a task ID; ablation table exists.
2. Add complexity only against a measured failure. Source: A4 Gall (aphorism) and A3 MDL. Check: changelog entry cites the failing task; unlinked components counted.
3. Every metric has units and a unit suffix. Source: B1. Check: unit-lint in CI.
4. Spend another computation only if expected gain x value exceeds cost. Source: C1 (Russell and Wefald), C3 Snell. Check: logged per-step marginal gain versus cost; gate beats fixed budget at equal tokens.
5. Try the cheap tier first and escalate on a failed test. Source: C4 FrugalGPT abstract. Check: USD per passing task versus always-large.
6. Any multi-agent or extra-sampling arm must be compared to a single-agent arm at equal tokens. Source: C6 (4x/15x statements), C7 (unverified). Check: result tables list both arms.
7. Stable, cacheable prompt prefix; precompute during idle time only if the precompute cost is counted. Source: C5, C8. Check: cached-read share; tokens per passing task including precompute.
8. Every result reports tokens, joules, and USD per passing task, with the measurement boundary stated. Source: D1 (boundary matters), D4 Green AI. Check: run record schema validated; accelerator-only and wall joules both present.

## 2. Metric definitions

- Tokens per passing task (tokens/task) = (sum of input uncached + cached-read + output tokens over all calls, listed separately) / (number of tasks passing the fixed oracle). Failed tasks' tokens stay in the numerator.
- Joules per passing task (J/task) = integral of measured power over the run window (W x s) / passing tasks. Always label the boundary: GPU-only (NVML), host, or wall.
- USD per passing task (USD/task) = (API bill or amortized hardware + electricity) / passing tasks. Say which; unknown cost is not zero.
- Idle-compute fraction (dimensionless) = (GPU-seconds with utilization below a stated threshold) / (total GPU-seconds in the window). State the threshold and sampling rate.
- Value-of-computation gate: run step only if p_gain x V_success > C_step, where p_gain is the estimated increase in success probability (dimensionless), V_success is the value of a pass (USD), and C_step is the step cost (USD). Calibrate p_gain from logged history; refuse the gate until at least a stated number of logged steps exist.
- Report pass rate with a confidence interval next to all three per-pass metrics.

## 3. Prior-art and honesty warnings

- Several principles (Gall, Unix, worse-is-better, Chesterton) are heuristics with no controlled evidence; treat them as prompts to measure, not as laws.
- Vendor numbers (Google, Anthropic) are self-reported and not independently audited; do not compare them to a different boundary.
- Scaling-law results concern pretraining loss; their transfer to agent pass rates is unproven.
- Token usage correlating with pass rate (Anthropic, one benchmark) is not proof that spending more tokens causes success.
- Multi-agent gains are often not shown at equal compute; one summary I saw says debate methods often fail to beat self-consistency (source not fully captured).
- The "Musk algorithm" wording below the one headline quote is secondary; do not quote it as verbatim until checked.
- Energy figures for local boxes are measurement-boundary dependent; GB10 NVML behavior is only forum-level evidence.

## 4. What I could not verify

- Exact five-step wording from the Everyday Astronaut video and Isaacson's book.
- Any primary text for Feynman/Fermi, MDL, Gall, Unix, worse-is-better, Hickey, Chesterton, Amdahl, Gustafson, Little, roofline, Zilberstein, speculative decoding, Strubell, Patterson, CodeCarbon.
- Full text of every paper listed; I read abstract pages and search snippets only, so no per-benchmark numbers beyond the abstract statements quoted.
- FrugalGPT's numeric cost-reduction claim (the fetched abstract text was truncated before it).
- Luccioni's numeric results and Google's full methodology (only secondary summaries of the breakdown).
- DGX Spark bandwidth and power under load (aggregator and forum only), and whether NVML total-energy counters work on GB10.
- Any SWE-bench cost-per-task figures; no study was opened.
- Carbon intensity of any grid; none retrieved.
