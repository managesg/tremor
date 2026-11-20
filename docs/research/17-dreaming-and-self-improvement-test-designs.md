# 17. Testing "dreaming" and self-improvement cheaply and rigorously

Scope: one GPU, a 4B-9B open-weight model, limited API credits. Date of research: 2026-11-19.
Note: `docs/research/03` does not exist in this checkout (only `01-...` is present), so the Anthropic numbers below were re-read from the primary post, not from research/03.

## Source ledger (OPENED = I read the text this session)

| Source | OPENED | How |
|---|---|---|
| Anthropic, "The components of agent memory" (anthropic.com/engineering/components-of-agent-memory) | yes | python urllib via ctx_execute; excerpted by keyword, not read end to end |
| dev.to summary of that post (gabrielanhaia) | yes (keyword excerpt) | same |
| fourweekmba, other secondary write-ups | no (search snippets only; fourweekmba page returned ~29 chars) | |
| Sleep-time compute, arXiv 2504.13171 | abstract only | arXiv API |
| ACE 2510.04618, DGM 2505.22954, AlphaEvolve 2506.13131, Generative Agents 2304.03442, Reflexion 2303.11366, Voyager 2305.16291, A-Mem 2502.12110, Mem0 2504.19413, STaR 2203.14465, Dreamer 1912.01603, SkillWeaver 2504.07079 | abstract only | arXiv API |
| CL-Bench paper 2606.05661 and repo README | abstract + README | arXiv API, raw.githubusercontent |
| LongMemEval 2410.10813, LoCoMo 2402.17753, tau-bench 2406.12045, SWE-bench 2310.06770 | abstract only | arXiv API |
| Licences (LongMemEval, tau-bench, SWE-bench, sleep-time repo, CL-Bench) | yes | GitHub API licence field |
| Zep, Complementary Learning Systems (McClelland et al.), experience replay (Lin / DQN), AlphaEvolve numbers, DGM numbers, Mem0 numbers | no | cited from background knowledge only; no numbers used |

WebFetch was blocked by a context-mode hook in this session; all page reads went through `ctx_execute` python urllib. WebSearch worked.

## 1. What "dreaming" means across the literature

Common core: spend compute while no user task is pending, over stored experience, to produce an artifact (notes, wiki, skills, code, weights) that makes later tasks cheaper or better.

- **Anthropic Dreams (Managed Agents, research preview).** Per the post and search summaries: an offline pass reads 1-100 past sessions plus the current memory, writes a new separate store, never mutates the old one. Strongest evidence (OPENED): on a ~350,000-file, ~420M-token Stainless corpus with 25 graded questions, wiki-only rose from 13% to 48% of graded criteria as dreaming went from 2 to 128 sessions; wiki+search rose 54% to 61% versus 53% for search alone; ~20,000 tokens saved per question; multi-document items 87% (wiki) vs 73% (search). Best wiki-only score (48%) stayed below the search baseline (53%). Weakest points: n=25 questions, one corpus, no intervals reported in what I read, the x-axis is "sessions" in the post but "2M to 128M dreaming tokens" in the brief given to me (flagged below), no equal-compute retrieval arm described, graded by a model (judge not checked). The post itself warns that "an incorrect note can be carried into every session" and reports a wiki-derived brief that covered 41 of 57 facts (72%) until the wiki was improved (then 100%): consolidation can lose facts.
- **Sleep-time compute (Letta/Berkeley, 2504.13171).** Abstract only: pre-computing over context cuts test-time compute by ~5x at equal accuracy on Stateful GSM-Symbolic and Stateful AIME; scaling sleep-time compute adds up to +13% and +18% accuracy. Control: it is explicitly a test-time-compute trade curve, i.e. the closest thing to a compute-matched design. Weak point: the "stateful" tasks are modified math problems where the context is known and queries are predictable; the paper itself motivates multi-query amortisation. Generalisation to open agent work is unverified.
- **Dreamer / world-model imagination (RL).** Learn a model, train a policy on imagined rollouts. Gain claimed in data-efficiency, computation time and final performance (abstract). Relevance here is analogical: LLM "dreaming" has no learned dynamics model, so it is closer to replay/summarisation.
- **Experience replay and Complementary Learning Systems.** Not opened. Conceptual basis: fast episodic store plus slow consolidation. Useful as a design hint (interleave old and new, avoid overwriting) but offers no benchmark numbers for LLM agents.
- **Generative Agents reflection (2304.03442), Reflexion (2303.11366).** Reflection turns raw episodes into higher-level text. Reflexion reflects after failure using feedback signals and stores text for the next trial. Both are online or per-episode, not offline batch.
- **Voyager (2305.16291), SkillWeaver (2504.07079).** Executable skill libraries validated by environment feedback. Strong feature: skills are verified by running, which is the "scripted re-verify" idea in code form.
- **A-Mem, Mem0, Zep.** Memory organisation and retrieval systems. Mem0 is evaluated on LoCoMo against RAG variants and full-context (abstract). Organisation, not dreaming per se.
- **ACE (2510.04618).** Context as an evolving playbook with generate/reflect/curate and incremental delta updates to avoid "brevity bias" and "context collapse". Directly relevant failure modes for any dream pass that rewrites memory. Numbers not read.
- **Darwin Godel Machine, AlphaEvolve.** Self-modification or evolutionary code search validated by benchmarks or evaluators. Strong where a deterministic evaluator exists; they self-improve against a fixed scorer, so they are a template for "scripted evaluator in the loop", not for prose memory.
- **STaR (2203.14465), self-play curricula.** Weight-updating self-training on filtered rationales. Needs fine-tuning compute; on one GPU feasible only at small scale, and out of scope for a memory-only test.

## 2. Compute-matched controls: used or missing

- Sleep-time compute: present (accuracy vs test-time tokens, plotted as a frontier).
- Anthropic dreaming: partial. Search-alone is a baseline, but from what I read there is no "same offline tokens spent on retries, longer search, or more retrieval" arm, and the dreaming budget is on the x-axis rather than charged against the answer-time saving (the ~20,000 tokens/question saved is not netted against dream cost in what I read).
- Reflexion, Generative Agents, Voyager, A-Mem, ACE, DGM: baselines are mostly no-memory or prior-method, not equal-total-token. Treat as missing unless a full read shows otherwise (unverified).
- CL-Bench: compares stateless vs memory systems and defines a gain metric to isolate learning from prior capability (abstract). Token matching not confirmed.
- Missing everywhere I could check: (a) random/placebo dream (same tokens, shuffled or irrelevant notes), (b) scripted non-LLM consolidation, (c) horizon-amortised cost.

## 3. Benchmarks usable offline with deterministic scoring

| Benchmark | Licence (OPENED) | Deterministic score | Cost/limits |
|---|---|---|---|
| CL-Bench (pgasawa/continual-learning-bench) | Apache-2.0 (GitHub API) | Task scripts with reward metric per episode, six domains incl. database querying and software engineering (abstract) | Python 3.13+, uv, Docker; sequential episodes; cost depends on model. Closest fit to "does experience help". |
| LongMemEval | MIT (repo) | 500 questions; official scoring uses an LLM judge (my background knowledge, unverified here), exact-match subsets possible | Long histories are token heavy for a 4-9B model |
| LoCoMo | repo licence field NOASSERTION; check the licence file before reuse | QA with F1; summarisation uses model metrics | Known label noise reported by others (unverified) |
| tau-bench | MIT | Compares final DB state to goal state; pass^k for reliability | Needs a user simulator LLM (cost, variance) |
| SWE-bench (and variants) | MIT | Unit tests | Docker heavy; small models score low, floor effects |
| trapbench (ours, `src/murmuration/trapbench/`) | ours | Planted wrong memory with known truth; exact | Not re-read this session; see `prereg/H8.md` |
| SQL-sequence tasks (ours, `sqlseq.py` generator) | ours | Result-set equality on generated SQLite | Cheapest; ideal for 4-9B |

Recommendation: our two own generators first (exact scoring, no judge, leakage controllable), CL-Bench database task second for external validity.

## 4. Designs for the key questions

Common arms for every experiment (same task stream, same seeds, same model):
A no memory. B raw-log memory with retrieval. C equal-token retrieval/retries (give the dream's token budget to extra search, longer context or best-of-k). D placebo dream (same tokens, notes from shuffled/other-task transcripts). E scripted re-verify pass (no LLM, replays stored claims against the environment/oracle and deletes failures). F model dream. G model dream followed by scripted verify.

1. **Dreaming vs equal-token alternatives.** Claim holds only if F > C at equal total tokens (online + offline) and F > D. Report both "offline tokens excluded" and "offline tokens amortised over H future tasks" (section 6).
2. **Poisoned memory correction.** Plant k wrong facts (trapbench). Metrics: poison-hit rate (answers using planted wrong value), correction half-life (number of tasks until the wrong note is no longer used, 50% survival), false-correction rate (true notes deleted). Compare A..G. Include a "confident poison" condition (poison phrased like a verified fact), since models defer to written notes.
3. **Small vs strong model.** Run the same pipeline with 4-9B local as dreamer and as solver, and with an API model as dreamer feeding a local solver (cheap distillation of memory). Cross design 2x2: dreamer {local, API} x solver {local, API}; the interesting cell is API-dreamer/local-solver.
4. **Scripted re-verify vs model dream.** E vs F on tasks where claims are mechanically checkable (SQL results, file existence, test pass). Prediction to falsify: E matches F on correction and sprawl for verifiable facts, F wins only on abstraction.
5. **Collaboration and lock-in.** Two or more agents share one store. Metrics: cross-agent transfer gain (agent B improves from A's notes), contamination (A's error propagating to B, count of tasks affected), lock-in (after the world changes, steps to unlearn a stale shared note; compare shared vs private memory). Plant a changed fact mid-stream.
6. **Sprawl, salience, half-life.** Sprawl: files, total characters, characters per correct-answer-supporting fact, growth per dream cycle. Salience: fraction of stored notes ever retrieved or cited in a successful task (dead-weight fraction); injected-token overhead per task. Half-life: as above. Anthropic's own warning that injected memory costs tokens makes tokens-per-task a first-class metric.

## 5. Statistics at small n

- Paired design: same tasks under every arm; analyse per-task differences. Use k>=3 repeats per task and average first (task is the cluster), because repeats of one task are not independent.
- Cluster (task-level) bootstrap, >=10,000 resamples, 95% CI on the mean paired difference; report effect with CI, not just p.
- Binary outcomes: McNemar/exact sign test on discordant pairs only. Arithmetic: with 8 discordant pairs all in one direction, two-sided exact p = 0.0078; 7 of 7 gives 0.0156; 8 of 9 gives 0.039. So at n=40 tasks, a 20% discordance rate means essentially every discordant pair must favour the dream.
- Minimum detectable effect (80% power, alpha 0.05, two-sided, normal approximation): MDE ~ 2.8 * sd_d / sqrt(n), where sd_d is the SD of per-task paired differences. n=10 gives 0.89 sd_d; n=20 gives 0.63 sd_d; n=40 gives 0.44 sd_d. Estimate sd_d from a 10-task pilot with arm A vs B; do not guess.
- Sequential stopping: pre-register looks (for example at n=10, 20, 40), use an alpha-spending rule (Pocock-style constant boundary, roughly alpha 0.0158 per look for 3 looks, from standard tables, unverified here) or a futility rule (stop if CI upper bound < pre-registered smallest effect of interest). Never peek without a spending rule.
- Multiple comparisons: pre-register one primary contrast (F vs C); treat the rest as exploratory with Holm correction.
- Prefer many cheap tasks from generators (hundreds of SQL sequences) over 25 hand-built ones; the generator raises n at near-zero cost, which is the cheapest lever on power.

## 6. Pitfalls

- **Answer leakage via consolidation.** A dream that sees transcripts containing gold answers or oracle feedback writes them into memory; later "success" is lookup. Controls: dream only over train-split episodes, evaluate on held-out tasks with different instances; canary strings in gold answers and grep memory for them; the scripted verifier must not expose test labels to the dreamer.
- **Evaluation contamination.** Public benchmarks (SWE-bench, LoCoMo, LongMemEval) may be in the 4-9B model's pretraining; a no-memory arm A score above chance on "unseen" items is the check. Generated tasks avoid this.
- **Judge dependence.** Anthropic's graded-criteria scores, LongMemEval and LoCoMo summaries use model judges. Prefer exact/executable scoring; if a judge is unavoidable, use a different model family than the dreamer, fix the rubric, and report judge agreement on a human-labelled subset.
- **Cost accounting.** Total cost = online tokens + offline dream tokens / H, where H is the number of future tasks the memory serves. Report break-even H. A dream that wins only if H is huge is not a win for a small store. Also count verifier calls and GPU seconds (local tokens are not free; log wall-clock and tokens/s).
- **Consolidation loss and collapse.** The post's 72% (41 of 57 facts) result and ACE's "context collapse" are the failure modes: measure fact retention before and after each dream with a fixed fact checklist.
- **Compounding error.** A wrong note persists in every session (Anthropic's own caution). Measure it (poison tests) instead of assuming it is rare.
- **Seed/ordering effects.** Task order matters in continual-learning designs; randomise order across repeats and report order as a blocking factor.

## 7. Minimal dreaming test ladder (ordered by cost)

1. **Scripted re-verify vs no memory, SQL-sequence tasks (cheapest).**
   - Hypothesis: a non-LLM replay-and-check pass over stored claims reduces repeated-error rate versus raw log memory.
   - Control: arm B (raw log) and arm D (placebo).
   - Metric: error rate per task (fraction wrong); poison-hit rate; tokens per task.
   - Kill: paired difference CI includes 0 and the upper bound is below the pre-registered smallest effect of interest at n=40 tasks x 3 repeats.
   - Needs: local GPU only (4-9B). No API.
2. **Poison correction with half-life, trapbench.**
   - Hypothesis: a dream/verify pass corrects planted wrong notes faster than leaving memory untouched.
   - Control: A, B, E.
   - Metric: correction half-life (tasks until poison-hit rate halves), false-correction rate (percent of true notes removed).
   - Kill: poison-hit rate not lower than arm B, or false-correction rate above a pre-set tolerance (set before running).
   - Needs: GPU; no API.
3. **Model dream vs equal-token retrieval and placebo (the core question).**
   - Hypothesis: F beats C at equal total tokens (online + offline).
   - Control: C (extra retrieval/retries with the same token budget), D (placebo dream).
   - Metric: task accuracy (percent) and tokens per correct answer; report with and without amortising dream cost over H.
   - Kill: F not better than C by the MDE, or better than D by less than noise, after the sequential looks at n=10/20/40.
   - Needs: GPU; no API unless using an API dreamer.
4. **Dreamer/solver size crossing (small vs strong).**
   - Hypothesis: an API dreamer feeding a local solver beats local-only dream (memory as cheap distillation).
   - Control: 2x2 {local, API} dreamer x solver, plus A.
   - Metric: accuracy (percent) and API dollars per 100 tasks.
   - Kill: API-dreamer gain over local-dreamer below the MDE, or dollar cost per point of accuracy above running C with the same budget.
   - Needs: GPU plus a small API budget (a few hundred dream sessions on generated tasks; size it from a 10-task pilot cost, not guessed).
5. **Shared-memory collaboration and lock-in, then CL-Bench database task for external validity.**
   - Hypothesis: shared dreamed memory improves agent B via agent A's notes, but slows unlearning after a mid-stream world change relative to private memory.
   - Control: private memory per agent; shared raw log.
   - Metric: transfer gain (percentage points), contamination count (tasks affected by another agent's wrong note), steps-to-unlearn a stale note, memory sprawl (files, characters) and dead-weight fraction.
   - Kill: no transfer gain over private memory, or contamination exceeds the transfer gain.
   - Needs: GPU; CL-Bench needs Docker, Python 3.13 and uv; optional API for a strong-model reference arm.

Rule across the ladder: do not advance a rung until the previous one has a pre-registered primary contrast and a measured sd_d; stop the ladder if rung 3 fails, since rungs 4-5 assume dreaming adds value over equal-token retrieval.

## 8. Unverified items

- Whether the Anthropic x-axis is "2 to 128 sessions" (post excerpt) or "2M to 128M dreaming tokens" (brief); both are in circulation. The post excerpt I read says sessions; the token version appears in a search-summary only.
- That the Anthropic study had no equal-compute retrieval arm and no confidence intervals: inferred from keyword excerpts, not a full read.
- Judge model and rubric in the Anthropic and LongMemEval/LoCoMo scoring.
- Sleep-time compute details (control design, models, task generator) beyond the abstract.
- All ACE, DGM, AlphaEvolve, Mem0, A-Mem, Voyager, Reflexion numbers (none used); Zep, CLS and replay claims are background knowledge.
- CL-Bench per-task costs, token matching, and exact metric definition; LoCoMo licence text (GitHub reports NOASSERTION); LongMemEval judge usage.
- Pocock alpha-per-look value and the exact-binomial values are standard arithmetic/tables, not checked against a source; the binomial figures were hand-computed (2 x (1/2)^8, 2 x (1/2)^7, 2 x 10/512).
- Trapbench/H8 specifics: only the file path and one line of H8.md were seen.
