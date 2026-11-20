# TREMOR: measure how a team of agents responds, then use the measurement to run the team

Research proposal for the Anthropic Residency (Greenhouse job 5438311008; applications close 22 Nov
2026). Version 3, final, 2026-11-20. Drafted with Claude models from our own notes. A portfolio of
eight research lines on one instrument, with one thesis. Contact: [owner to add].

## Executive summary

**Thesis.** A team of agents has collective statistics that no single agent has: how much its outcome
varies between identical reruns, how many copies a wrong note makes of itself, how correlated its
members' mistakes are. **Measure the team's response, then allocate by it.** Each line takes one idea
from complex systems, turns it into a statistic read from logs, and turns the statistic into a rule
for spending a scarce resource. The rule must beat a named baseline at equal budget, with the cost of
the measurement charged to it. Every prediction has a kill criterion.

| Line | Statistic | Technique | Baseline it must beat | Novelty after our search |
|---|---|---|---|---|
| 1. Susceptibility-guided orchestration | Rerun overdispersion against dose response | Verify where measured response is highest | Verify where reruns disagree; equal-token retries | Medium (law test high) |
| 2. Memory immune system | Reproduction number R of a wrong note | Quarantine; verify the highest-R notes first | One-line warning; origin-bound corroboration; graph-degree order | Medium (R and threshold high, quarantine low) |
| 3. Correlation-aware monitor ensembles | Joint misses of monitor views | Rotating hidden view under selection pressure | Published selection rules; conservative aggregation | Low for selection, medium for rotation |
| 4. Dreaming as consolidation | False-note share and recovery time across nights | Verified replay with adaptive strength | Equal-token search; placebo dream; gated write | Medium |
| 5. Stigmergic coordination and norm carriers | Violations per carrier on held-out norms | Evaporating claims; carrier surface | Rank partition with a lease timeout; rule in code | Low for the mechanism, medium for carriers |
| 6. Trust and permission calibration | Over-grant exposure | Evidence leases | Tuned fixed rule; time-boxed grant | Low to medium |
| 7. Renormalization across team size | Error correlation as teams grow | Blocks sized by task coupling | Parallel small teams; single hub | Medium |
| 8. Activation readouts | Probe-to-text error correlation | A probe as one more ensemble view | Text monitors; published probe designs | Low to medium |

**What exists today.** The bench (shared board, router, perturbation harness, practice cards, three
scorers with one in Lean 4, spend ledger) is built and has passed scripted checks. One instrument
pilot ran on a real model (88 calls, USD 0.0115) and was stopped by its own pre-set rule. **No
hypothesis has been tested, no pre-registration is frozen, and none of the eight techniques has been
started.** Total real spend: USD 0.0162.

**Six-week deliverable.** Pre-registrations for all eight lines; lines 1 to 3 tested against their
baselines; first results for lines 4 and 5; pilots for lines 6 to 8; one release of the bench, logs,
Lean oracle, analysis code and every negative result.

**Budget.** The project owner has funded the programme: USD 170 for the Claude API and 70 GPU-hours on
a local workstation (section 9). Compute provided by the residency would be additional and would go
first to the sample sizes that make each kill criterion decisive.

**Contact.** [owner to add]

Reading rules for this document:

- **Status words:** NOT STARTED, INSTRUMENTED (code exists and passed scripted checks; no model result),
  PILOTED (run on a real model as an instrument check; no estimate), EVIDENCED (a pre-registered result
  exists). **Nothing in this project is EVIDENCED.**
- **Source depth:** each external claim says how far we read: *full*, *tl;dr*, *abstract*, *listing*.
  *Checked* means a separate accuracy review on 2026-11-20 compared the quote or figure with the
  primary page. Anything else is marked UNVERIFIED. Works cited under "Closest prior work" in section 5
  come from a prior-art search on the same day, were not part of that review, and carry their own
  depth labels.
- **Talks:** figures and quotes from talks are TALK CLAIMS, taken from machine transcripts and slides;
  none has been checked against a recording. For Lydia Hallie we hold only notes written from a
  transcript, so her items are paraphrases and carry no quotation marks.
- **Mentor questions:** *[stated]* is the posting's line or the person's own page. *[our reading]* is
  our inference from their public work. Nobody named here has seen this proposal. "Fit" means our
  question sits in that person's stated area and nothing more: no contact, no endorsement.
- **Numbers we predict** are priors chosen by us so the prediction can fail; our probability that the
  prediction holds is in brackets. They are not literature values. Every prediction has three
  outcomes: supported, killed, inconclusive. A result that is merely not significant is inconclusive,
  never killed.
- **Scope and claims.** Reviews of this document check claims, sources and status words. Scope is set
  by the project owner. Where an idea is risky we state the risk and the kill criterion; we do not
  shrink the idea.
- **ArXiv metadata discrepancies fixed in this version:** *Worse Together* (2610.00583) arXiv v1 is 30 Sep 2026 with three authors (Paliskara, Namchittai, Lampinen); the web version adds Tay and Griffin and is dated 11 Nov 2026. *Red-Teaming Auto Mode* (2609.19587) arXiv v1 is 17 Sep 2026, updated 27 Sep. *Would This Change Your Answer?* (2608.16747) is about agents predicting counterfactual behaviour from interpretability tools, not a monitoring study—line 8 cites it correctly as "not our prior".
- **Quote status.** Lydia Hallie items are paraphrases from our notes of an owner-pasted transcript we did not see; quotation marks around them mark a paraphrase, UNVERIFIED as verbatim. CJ Avilla's "design for appropriate trust, not greater trust" is attributed by the speaker to a 2004 paper (Lee and See 2004 by our reading); it is not in our talk notes and is UNVERIFIED as verbatim. Diogo Almeida and Lance Martin items are TALK CLAIMS.

## 1. Thesis, from first principles

A team of agents is a medium with shared state. Three things move through it: work, errors and norms.
Like any medium it has collective statistics that no single agent has: how much its outcome wobbles
between identical reruns, how many copies a wrong note makes of itself, how correlated its members'
mistakes are, how tightly its tasks are coupled, how fast it returns to normal after a shock. These
can be read from logs. Most cost little or nothing to read.

Running a team means spending scarce things: verification, monitor calls, context, permissions,
compute, a coordinator's attention. Today they are spent evenly or by habit: review everything once,
stack three monitors, load the whole history, grant a permission forever.

**Thesis: measure the team's response, then allocate by it.** For each scarce resource there is a
collective statistic that says where it matters, and a rule that spends by that statistic beats a rule
that ignores it, at equal budget. Each line below takes one idea from complex systems or first
principles, turns it into a measured statistic, and turns the statistic into an algorithm with a named
baseline it must beat. A line fails if the statistic is not repeatable, or if the algorithm does not
beat its baseline. The thesis fails if that happens across the lines (section 11).

Four talks shaped the problems (section 6). Three were at the AI Engineer Code Summit 2026: Lance
Martin on thousand-agent teams, memory and dreaming; Lydia Hallie on bounded autonomy; Diogo Almeida
on reliability and state. The fourth is CJ Avilla's talk on trust (venue not recorded in our notes).
Each line names the talk material that prompted it.

## 2. Why now

**Anthropic work that makes the questions concrete.**

| Work | Date | Depth | What we take from it |
|---|---|---|---|
| Worse Together, arXiv 2610.00583 (Paliskara, Namchittai, Lampinen on arXiv; the web version we read adds Tay and Griffin) | arXiv v1 30 Sep 2026; web version 11 Nov 2026 | web version full to Discussion, checked; arXiv record from metadata only, the two not reconciled | A coordinator beat a peer team in all four environments, for both Claude models, by about 10 to 45 percentage points. "from four to 16 agents, the share that ever act falls from 66% to 10% for Sonnet 5 and from 82% to 25% for GPT-5.6-sol". These are multi-user teams: "each user has their own goal, and all of the users draw on one shared resource". A team leader with clearly stated priorities helped in the shared-budget environment and blocking orders until messages were read helped in the group-order environment; the two fixes were tested in different environments, not against each other. |
| Diluting Poisoned Fine-Tuning Data Can Strengthen Its Effect (Clarke, Dubiński, Chua, Schrodi, Evans, Cloud) | 10 Nov 2026 | full to Discussion start; checked | "For a training set of fixed size, it peaks at intermediate fractions of poisoned data and is nearly absent when the data is all clean or all poisoned." The effect "requires that the poison data have an identifying 'trigger' feature that is absent from the clean data". All experiments fine-tune small open-weight models (Qwen3-8B and Gemma-3-4b-it) or a small MNIST network. In-context memory is not studied. |
| Mind Viruses: Self-Propagating Ideas in Multi-Agent LLM Systems (Papadopoulos, Shah, Zimmerman, Lindsey), arXiv 2608.10218 | 10 Aug 2026 | abstract and passages; checked | The viruses spread "by writing themselves into agents' memory and configuration files"; "adding a brief warning to an agent's system prompt confers near-total immunity". "Claude Sonnet 4.6, GPT-5.4, and Claude Haiku 4.5 are immune" to one virus; "frontier models tend (with exceptions) to be less susceptible". The payloads were built "with a simple evolutionary algorithm". We will not evolve anything. |
| Red-Teaming Auto Mode (Remedios, Storf, Roger, Hughes), arXiv 2609.19587 | arXiv v1 17 Sep 2026; web version 22 Oct 2026 | tl;dr of the web version; checked | "robustly preventing multi-context attacks at an acceptable cost remains an open problem". |
| Diffuse AI Control on Fuzzy Tasks (Terekhov, Gulcehre, Hebbar, Benton) | 23 Jun 2026 | tl;dr and intro; checked | "We also show the existence of prompts for the weak scorer that significantly improve its robustness, though efficient discovery of those prompts with realistic affordances remains an open problem." |
| Emergent Introspective Awareness in Large Language Models (Lindsey) | 29 Oct 2025 | abstract, method, limits; checked | "Opus 4.1 and 4 exhibit such behavior about 20% of the time when concepts are injected in the appropriate layer and with the appropriate strength"; "it is unclear exactly how these results translate to more natural conditions". |
| Emotion Concepts and their Function in a Large Language Model | 2 Apr 2026 | abstract, method, limits (our extract) | Linear representations that "causally influence the LLM's outputs, including Claude's preferences and its rate of exhibiting misaligned behaviors such as reward hacking, blackmail, and sycophancy". |
| Verbalizable Representations Form a Global Workspace in Language Models (Gurnee, Sofroniew, …, Lindsey) | 6 Jul 2026 | abstract, method, limits; checked | Has a section on alignment auditing. "Future work could investigate whether smaller models have an equally rich workspace, a proportionally smaller one, a less reliable one, or none at all." |
| Circuits Updates, June 2026 | Jun 2026 | short read; checked | Features used "as probes to monitor other transcripts". The turn-averaged SAE note reports discrimination of 74% against 95% for per-token SAEs, and a coverage preference of 77%. |
| Would This Change Your Answer? (Karvonen, Ong, Kantamneni, Marks), arXiv 2608.16747 | 21 Aug 2026 | tl;dr; checked | "activation-reading interpretability tools provide no uplift: agents given the tools predict the outcomes of these experiments no better than agents that just read the transcript." It is about agents predicting counterfactual behaviour from interpretability outputs, not about monitoring; the priors for line 8 are the probe papers cited there. |
| Model Organisms of Misalignment (Alignment Forum version) | 8 Aug 2023 | opened; a position paper | "We hope to be able to measure how far away the failure mode is by seeing how much unrealistic steering we need to do." |
| Aligning AI Teams (Srinivasan, Matthews, Sohl-Dickstein, Jones), arXiv 2611.17820 | 13 Nov 2026 | abstract; checked | Soft interventions, "having agents critique each other's work or coordinate in a group chat, do not reliably bring agent teams back"; structural ones, "having a designated safety lead agent … and having a coordinator agent publish a safety specifications document are effective". **Binding prior art for line 5.** |
| AI Organizations are More Effective but Less Aligned than Individual Agents (Shen, Zhu, Srinivasan, Sleight, Wagner, Matthews, Jones, Sohl-Dickstein), arXiv 2604.10290 | 11 Apr 2026 | abstract; checked | "AI Organizations composed of aligned models produce solutions with higher utility but greater misalignment". It does not compare soft with structural interventions. |
| Recommendations for Technical AI Safety Research, section "Learned governance for multi-agent alignment" (under Miscellaneous) | 2025 | listing; section title checked | The area lines 5 and 7 sit in, as we map it. |

**Memory and dreaming are shipped and thinly measured.**

| Source | Depth | What we take from it |
|---|---|---|
| Anthropic, "The components of agent memory" (6 Nov 2026) | full text read; figures not inspected; checked | On one corpus and 25 graded questions, a wiki built by dreaming rose from 13% to 48% of graded criteria as dreaming went from 2 to 128 sessions; search alone scored 53%; wiki plus search 54% to 61%. The post warns that "an incorrect note can be carried into every session". The text reports no intervals, and no arm gives search the same token budget that dreaming spent (it reports about 20,000 tokens saved per question for search plus wiki). |
| Dreams in Claude Managed Agents (research preview) | secondary summaries, UNVERIFIED | A dream reads past sessions and writes a new store, leaving the old one untouched. |
| Auto Dream in Claude Code | third-party descriptions only | UNVERIFIED. We found no official documentation. |
| CL-Bench, arXiv 2606.05661 | abstract | "naive ICL outperforms systems dedicated to memory management". A warning against assuming consolidation wins. |
| Sleep-time compute, arXiv 2504.13171; ACE, arXiv 2510.04618; Telephone Game, arXiv 2407.04503 | abstracts | Offline pre-computation trades against test-time compute; rewritten context can suffer "context collapse"; chained rewrites drift toward attractors. |

Our scan of five Anthropic research sites found no new post on multi-agent systems, control or RL
environments beyond those already in our notes. That rests on listings: 68 alignment-blog posts were
checked by title, not opened. A targeted prior-art search for each technique was run on 2026-11-20:
about 90 keyword queries on arXiv, mostly at abstract depth. Its closest works and our novelty grade
are given per line in section 5. We claim no priority anywhere; "not found in our search" means only
that.

**Mentors and their areas.** The posting is public. Its section "Mentors and research areas" gives the
lines quoted below (checked). The residency page says Residents "work on problems outlined by Anthropic
researchers, and matched to the Resident's interests and background", that the round targets people
who "started out as physicists, mathematicians, neuroscientists, or software engineers", and that
placements run six weeks, three months or six months. This proposal is therefore an offer of
directions and an instrument, not a fixed plan.

| Person | Posting line, [stated] | The question we map to them, [our reading] |
|---|---|---|
| Jascha Sohl-Dickstein | "works at the intersection of safety and pretraining; background in physics and neuroscience, formerly Principal Scientist at Google Brain". Own page: "machine learning, neuroscience, statistical physics, dynamical systems". | Does team incoherence grow with team size and tokens, and does a team's own fluctuation predict its fragility? |
| Ethan Perez | "leads the Alignment Science team; background in machine learning". Co-author of "The Hot Mess of AI: How Does Misalignment Scale With Model Intelligence and Task Complexity?" (arXiv 2601.23045). | Which monitor catches failures visible only in aggregate? |
| Evan Hubinger | "leads the Alignment Stress-Testing team; formerly at The Machine Intelligence Research Institute (MIRI)" | Does optimising against a team monitor degrade it? Can a reward-hacking norm arise in a team without training? (His work on RL in hackable environments is our reading of his papers, not his words.) |
| Samuel Marks | "leads the Scalable Oversight team; background in mathematics" | Do planted-behaviour audits and label-free checks agree on team failures? (Auditing and lie detection as his area is our reading of his papers.) |
| Sara Price | "leads the Alignment Training team; background in data science". Co-author of Model Spec Midtraining (arXiv 2605.02087). | Do written norms generalise to held-out cases better than rule checks, and better still in weights? |
| Jack Lindsey | "leads the Model Psychology team; background in theoretical neuroscience". Own page: "signatures of deception, manipulation, or awareness of being evaluated". | Do memory-write patterns make a store infectious, and does a warning generalise? Does a readout of activations see a team failure that text does not? |
| Nicholas Carlini | "researches adversarial machine learning and AI security; previously at DeepMind and Google Brain". Own page: "studying what bad things you could do with, or do to, language models". | What is the poisoning dose-response for shared memory? |
| Belinda Li | "researches how language models represent the world, users, and themselves; background in natural language processing (PhD, MIT)". Own page: "models of the AI system's own internal computations, external behaviors, and limitations". | Does an agent's account of what it relied on match its behaviour and its internals? |
| Elana Simon | "researches the interpretability of language models and biological models". Her own page names no Anthropic role; we rely on the posting. | Are probe readouts stable to preprocessing? |

## 3. The shared instrument

One code path for all eight lines, built from parts that already exist (status in section 8).

1. **The medium.** A shared, append-only, hash-chained board; a router that runs each agent with a
   budget; ten written practice cards, each with a length-matched neutral twin and a leak check.
2. **Taps** (all seeded, all inert): requirement change, noisy requirement, wrong or stale note, slow or
   failed worker, denied permission with a safe route, note dilution at a fixed store size, team size,
   best-of-N selection against a toy monitor. Dosed taps (number or prominence of a note, dilution
   fraction, selection strength) give slopes. A doubled team size or a single wrong note is a finite
   perturbation and gives a finite response, not a susceptibility. We keep both kinds and name them
   correctly.
3. **Readouts** from the log only: norm violations, blocked legitimate work, distinct passing work,
   false completion, cascade depth of a planted marker, run-to-run variance over identical reruns,
   pairwise error correlation, cost per passing task in tokens and USD.
4. **Truth.** Three scorers for the board task: two written independently in Python and one in Lean 4
   whose properties are checked by the Lean kernel. Any disagreement voids a run. Monitors, probes,
   consolidation passes and agents never see the oracle.
5. **Spend.** A ledger with hard caps in code. Unknown cost is never counted as zero.
6. **New: the night loop.** A chain of days and nights: each day the team works from the current
   store; each night a consolidation pass reads the day's log and the old store and writes a new
   store. The old store is kept, so every night is a diff that can be audited and undone.
7. **New: scripted nulls.** For every line, the idea is first written as a small explicit model and
   run with scripted agents. If scripted agents reproduce the curve, the result is a property of the
   loop, not of language models, and we say so.

Rules that hold for every line:

- n is task sets or chains, never agent turns. Each task set is rerun at least three times and averaged
  first. Intervals by cluster bootstrap. One primary contrast per line, fixed before any run.
- Sample sizes are fixed from a variance pilot, because the standard deviation we need does not exist
  yet. Each line's n is set so that the standard error of its primary contrast is at most
  min(K, E − K)/2.8, where E is the predicted effect and K the kill bound. That gives 80% power both
  to support at E and to kill at zero. Where the budget cannot reach that n, the line states in
  advance which outcomes are reachable. Supported, killed and inconclusive are defined by where the
  95% interval falls.
- Episode counts are effective counts: raw episodes are divided by the design effect
  1 + (m − 1)·ICC, with m episodes per cluster and ICC from the variance pilot, and the raw count is
  raised to compensate.
- A rate read at a 5% false-positive rate uses at least 400 clean episodes for the threshold and at
  least 200 failure episodes for the catch rate. A rank correlation is tested on at least 30
  conditions, or 10 rungs of a ladder (10 rungs detect a correlation of 0.8 or more with 80% power);
  line 1 states its own, larger number.
- Every algorithm is compared at equal total budget, and the cost of measuring the statistic it uses is
  charged to it.
- **Effective number.** For n agents or monitors with mean pairwise error correlation ρ̄ we use Kish's
  estimator, n_eff = n / (1 + (n − 1)ρ̄). It assumes exchangeable members; we report the spread of the
  pairwise correlations as the check on that. It describes the variance of an average, not the catch
  rate of an ensemble, and it saturates at 1/ρ̄; lines 3 and 7 say how they handle that.

**Compute.** Claude tiers through the API. Local open models (Qwen3.5-0.8B and 4B, on disk) on one
local workstation GPU, shared with other work. The posting says
the residency provides "Access to Claude models and GPU compute", and the residency page says Residents
"have a dedicated compute budget for their projects" (checked). If so, hosted tiers and the sample
sizes above move there, and the local tier stays as the open, reproducible floor.

## 4. Ranking of candidate lines

Eleven candidates were scored 1 to 5 on the value of the problem to people who build models or agent
teams, on distance from the prior art we have read, and on what can be finished in six weeks. The
scores are our judgement, with no data behind them. Eight become lines; candidates 8 and 11 are
folded into lines 2 and 8; candidate 10 is in the backlog (section 7). The novelty scores predate our
prior-art search and are kept as recorded. The grades after the search are in the executive summary
and in section 5; for lines 3, 5, 6 and 8 they are lower than the scores here.

| Rank | Candidate | Value | Novelty | Six-week feasibility | Product | Decision |
|---|---|---|---|---|---|---|
| 1 | Susceptibility-guided orchestration | 5 | 4 | 4 | 80 | Line 1 |
| 2 | Memory immune system (with the contagion organism) | 5 | 4 | 4 | 80 | Line 2 |
| 3 | Correlation-aware monitor ensembles | 5 | 3 | 4 | 60 | Line 3 |
| 4 | Dreaming as error-correcting consolidation | 4 | 4 | 3 | 48 | Line 4 |
| 5 | Stigmergic coordination, norm carriers and EP-1 | 4 | 3 | 4 | 48 | Line 5 |
| 6 | Trust and permission calibration over time | 4 | 3 | 3 | 36 | Line 6 |
| 7 | Renormalization across team size | 4 | 4 | 2 | 32 | Line 7 |
| 8 | Source and provenance verification | 4 | 2 | 4 | 32 | Kept as the core mechanism of line 2 |
| 9 | Activation readouts as monitors of collective failure | 4 | 3 | 2 | 24 | Line 8 |
| 10 | Context engineering as compression | 4 | 2 | 3 | 24 | Backlog; its retention rule is tested inside line 4 |
| 11 | Self-reports against internals | 3 | 3 | 2 | 18 | Optional part of line 8 |

## 5. Research lines

Thresholds are proposals; the pre-registration fixes them after the variance pilot. Each line gives:
idea, inspiration, problem, technique and baselines, predictions and kill, fit, closest prior work,
cost (plan and stop from section 9). All lines run on the board with the Lean-checked scorer, on
Claude tiers and on local open models.

- **Primary** names the one pre-registered primary contrast of a line. The other predictions are
  secondary and Holm-corrected.
- **Closest prior work** comes from our search of 2026-11-20. Depth there is *opened* (passages read
  beyond the abstract, never a full read), *abstract*, or *snippet* (the first lines of the abstract
  only). Classics marked *from memory* were not retrieved and carry no identifier. The novelty grade
  is our own.

### Line 1. Susceptibility-guided orchestration

**Idea (fluctuation and response).** In equilibrium, and for small pushes, a system's spontaneous
fluctuations in a quantity predict how that quantity responds to a push. Agent teams are driven and
far from equilibrium, so the simple relation need not hold; measuring where and how it breaks is the
experiment. "Susceptibility" here is the physics term: how far an outcome moves per unit of push. It
is not the epidemic "susceptible" of line 2.

**The mechanical trap, and how the design avoids it.** Whether one agent adopts a planted note is a
yes/no event. Its variance over reruns is p(1 − p), and if adoption follows a logistic dose curve its
slope is b·p(1 − p). Variance and slope then move together by arithmetic, and a rank correlation
across conditions can come from differences in p alone. We therefore do not test the law on raw
variance against raw slope.

- **Fluctuation** is overdispersion: the variance of the team's adoption count over identical reruns,
  divided by the binomial variance at the same mean. It is 1 for independent agents at any p; the
  excess is the collective part.
- **Response** is the dose slope on the logit scale (b), which has p(1 − p) divided out.
- **Nulls.** Response predicted from mean adoption p̂ alone, and from p̂(1 − p̂) alone. Scripted
  independent agents must give overdispersion 1 and no relation.
- A second observable that is not a yes/no event, the cascade depth of the planted marker, is reported
  the same way against its mean-only predictor.

The non-trivial content is that the coupling which makes agents move together should also amplify the
team's response to a push.

| Assumption | Test in the design |
|---|---|
| Same observable | Fluctuation and response are measured on one quantity, adoption of a planted note. The cross-observable version (incoherence against adoption) is a second test. |
| Linear response | At least three small doses; the logit slope must be linear before we call it a susceptibility. |
| Stationarity | Early against late rounds, and two halves of the reruns; drift is reported. |
| Departure from equilibrium | The ratio of response to fluctuation per condition, a static analogue of an effective temperature (the textbook quantity is defined on two times). Its variation across carriers, team sizes and tiers is the measured breakdown, and is a map we would release. |
| Activity | Far from equilibrium, response has a second term tied to dynamical activity (Baiesi, Maes, Wynants 2009, arXiv 0902.3955; snippet). Board writes and tool calls per round enter as a predictor. Decoding temperature is reported as a covariate; it is not a thermodynamic temperature. |

**Inspired by.** Diogo Almeida: "if you can't tell which is which, how ... are you going to automate
anything" and "Einstein 95%, Mr. Bean 5%" (TALK CLAIM, rhetorical); our reading: report the spread, not
the mean. Lydia Hallie: with the human out of the loop the same prompt gives different small decisions
(paraphrase; TALK CLAIM).

**Problem.** A team lead has a fixed budget for re-checks and extra samples and no principled way to
place it. Reviewing everything once wastes most of it.

**Technique: susceptibility-guided verification.** Rerun each unit of work cheaply; estimate its
overdispersion; spend the verification budget in proportion. A variance from 3 reruns has 2 degrees of
freedom (95% interval 0.27 to 39 times the estimate), so the technique uses at least 10 reruns per
unit, or pools by task type. The reruns are charged to the budget. **Baselines it must beat at equal
total tokens:** uniform verification; random placement; longest outputs first; team size alone;
**verify where reruns disagree**, which needs no response theory; **the same tokens spent on retries
with a majority vote**; and a regression predictor of benefit fitted on the pilot data, in the style
of Damani et al.

**Line 1 redesign (variance–response link for bounded outcomes).** The original design tied overdispersion
to a logit slope measured on a binary adoption event, but binary outcomes compress the response range.
We replace the logit slope with a **linear susceptibility** χ = d⟨A⟩/dD measured on the continuous
adoption count A per chain and a continuous dose D (verification passes per unit). The cross-predictor
test remains: χ adds to the mean-only predictors (activity and team size). The Williams test is replaced
by a **nested F-test** comparing a linear model with χ to one without, on held-out conditions, because
the response is continuous and bounded. The 95% bootstrap interval for χ is computed from 1,000
resamples clustered by tier and task type.

**Predictions.** (A, the law) Across at least 60 conditions, with 90 as the target, the nested F-test
rejects the mean-only model at p < 0.05, and the partial R² of χ is at least 0.15. [30%] (B, the
technique; **primary**) Undetected false completions fall by at least 25% relative to uniform
verification. [30%] Adopted planted notes are a secondary readout. **Primary: B; the rest are
secondary, Holm-corrected.**

**Kill.** A: the lower bound of the partial R² is below 0.05, or the F-test p-value lower bound is
above 0.25. Supported needs the lower bound of the partial R² above 0.15 and the F-test p-value upper
bound below 0.05. Conditions are clustered by tier in the bootstrap. At 60 conditions support has about
80% power at partial R² = 0.15; the kill reaches 80% power at 90. B: killed if the upper bound of the
relative reduction is below 10%; supported if the lower bound is above 10%. That needs a relative
standard error of about 3.6%, about six times the n that only detects 25%. If the rule ties
verify-where-reruns-disagree, the finding is that disagreement is enough and response theory adds
nothing to allocation. If A is killed and B holds, the technique works for a reason other than the one
we gave, and we say that.

**Fit.** Jascha Sohl-Dickstein; Ethan Perez. Both are co-authors of the Hot Mess paper, so this line
sits next to their own recent work: a closer fit and a higher bar for novelty.

**Closest prior work.** Hot Mess (arXiv 2601.23045; abstract) measures the variance share of error in
single models, with no perturbation. Damani et al., "Learning How Hard to Think" (2410.04707; abstract)
allocate extra compute where a predictor says it helps: the allocation form is theirs. Itkin, "Delayed
Verification in Multi-Agent LLM Systems" (2606.27409; opened) places correctors greedily on a consensus
graph. Anand and Singh (2611.03192; abstract) model verification allocation on synthetic pipelines.
Rabanser et al. (2602.16666; abstract) report consistency and robustness as separate metrics. **What
we claim:** the predictor, not the allocation; and the test that relates rerun fluctuation to dosed
response on one observable in agent teams, with the mean-only null. We did not find that test. Novelty:
medium (law test high, technique medium).

**Cost.** 8 GPU-hours; USD 14 plan, USD 24 stop. Conditions with more than 8 agents need the team-size
ruling (section 9).

### Line 2. A memory immune system

**Idea (epidemic threshold and herd immunity).** A wrong note in a shared store has a reproduction
number R: the number of later notes and actions that derive from it. Above 1 it tends to spread; below
1 it dies out. On a board that every agent reads, the classical well-mixed result says spread stops
once a randomly chosen verified share of the notes agents rely on exceeds 1 − 1/R. Whether a team of
language models obeys that formula is the first test. Three caveats belong to the idea. In a team of 4
to 8 agents the threshold is a crossover, and a note with R just above 1 can still die out by chance.
A note on an append-only board never recovers by itself, so the nearer classical model may be a rumour
model, which has no threshold when well mixed (from memory); that a threshold exists is part of what
we test. And verification must block relay, not only adoption.

**Inspired by.** Lance Martin: "a poison memory was injected and it's stuck there" and weaker models
"don't reliably know when to write" memory (TALK CLAIMS). Diogo Almeida: "we have the memory
available. It's just that we don't have the smarts ... what you should remember" (TALK CLAIM). Our own
harness: its memory lint checked that a source existed, not that it was true, and passed a fabricated
source.

**Problem.** Shared memory is the cheapest way to make a team coherent and the cheapest way to poison
it. Builders need to know how much of a store must be verified, and which notes first.

**Technique: quarantine with verification targeted by measured R.** (1) Provenance on every note, read
from the hash-chained board. (2) New notes are readable but cannot be relayed or promoted until
verified by a scripted re-check, or supported by an independent source; support that traces back to
the note itself does not count (a cycle check on the provenance graph). (3) The verification budget
goes first to the notes with the highest measured R. Steps 1 and 2 are engineering components: Louck's
origin binding with corroboration-gated elevation is the same idea with machine-checked guarantees.
Step 3 is the contribution: R is measured from board provenance and has to beat cheaper orderings.
**Baselines:** the one-line warning that Mind Viruses reports as near-total immunity; an unprotected
store; random verification of the same share; verify everything; origin binding with
corroboration-gated elevation (Louck) as the deterministic defence; Nakayashiki's one-sentence
target-blind rule; and three cheap orderings (highest out-degree in the provenance graph, most
recently written, most retrieved).

**The organism.** Two forms, both inert. *Planted:* one fixed, hand-written note with a trigger
feature absent from the clean notes, at five non-zero fractions of a fixed-size store (the Nakayashiki
design of five fractions), plus a trigger-only control. *Arising:* nothing planted; a time squeeze and
a deliberately broken copy of our own scorer; does an agent find the shortcut, write it down, and do
others adopt it?

**Predictions.** (A) A one-line warning halves adoption on a local 4B model against a neutral line.
[55%] (B) On the random-verification arm, the measured immunity threshold is within 0.15 of 1 − 1/R,
with R taken from the unprotected arm. [30%] (C; **primary**) Verification targeted by measured R
reaches full verification's adoption, within a pre-set equivalence margin of 3 points, with at most
half the checks; random needs at least 80%; and measured R beats the three cheap orderings. [35%] (D)
Adoption is non-monotone in the poisoned fraction: its peak is at least 1.5 times its value at
fraction 1 and at the smallest non-zero fraction. [20%] (E) The shortcut arises unplanted in about 5%
of episodes on some tier (a point prediction). [45%]

**Kill.** A: the upper bound of the reduction is below 25%, so a halving is excluded. Supported: the
lower bound is above 25%. Otherwise inconclusive. B: tested only if the unprotected arm gives R with a
lower bound above 1. R is the mean number of first-generation offspring per planted note, and its
dispersion is reported, because a few high-offspring notes are what targeting exploits. The verified
share is swept in steps of at most 0.05. The difference between the threshold and 1 − 1/R gets a
bootstrap interval that carries R's uncertainty. Supported if the interval lies within ±0.15; killed
if it lies wholly outside ±0.3; otherwise inconclusive. C: targeted needs more than 80% of the checks
random needs; or out-degree order does as well as measured R, so the measurement adds cost without
benefit; or the warning or origin binding alone drives adoption to the floor on every tier and task,
so targeting has nothing to add at this scale. D: tested as two contrasts (peak against fraction 1,
peak against the smallest non-zero fraction) on the log-ratio with 0.5 added to counts,
Holm-corrected, with the peak level chosen on a held-out half of the chains. Supported if both
ratios have a lower bound above 1.25; killed if either has an upper bound below 1.25; otherwise
inconclusive. E: killed if on every tier the upper 95% bound
(Clopper-Pearson, effective n) is below 5%. Supported if on at least one tier, Holm-corrected across
tiers, the lower bound is above 1%: the shortcut arises unplanted at all. Mind Viruses reports some
Claude models immune, so a floor near zero on Claude tiers is expected and is a tier data point.
**Line 2D bounds fix (from accuracy review):** the log-ratio with 0.5 added to counts stabilises the
ratio when adoption at the smallest fraction is near zero. The peak level is chosen on a held-out half
of chains to avoid selection bias.
**Line 2E fix:** a kill only on zero in 200 ignores 1–3 events (3/200 has upper bound ≈4.3%, also
excluding 5%). Support requires a lower bound above 5%, which at n=200 needs ≥17 events (2% power at
true 5%, 79% at true 10%). Holm correction across tiers is applied. This is an episode count; see
§3.

**Fit.** Nicholas Carlini; Jack Lindsey, a co-author of Mind Viruses; Evan Hubinger for the arising
form.

**Closest prior work.** Nakayashiki, "When Stale Constraints Go Unchecked" (2608.25553; opened): with
a budget of two inspections, 16 models rarely re-verified inherited memory, and forcing one check onto
the critical provenance path removed most errors. Our "highest R first" refines that. Louck
(2606.24322; opened): origin-bound authority and corroboration-gated elevation, which pre-empts our
cycle check. MemLineage (2605.14421; snippet): lineage gating. Mind Viruses (2608.10218; opened in
passages): spread factors and warning-based immunity, no threshold test. A-MemGuard (2510.02373;
abstract), Agent Smith (2402.08567; snippet) and Prompt Infection (2410.07283; abstract). Honeytokens
under shared memory (2608.11436; abstract). **What we claim:** estimating an offspring number from a
provenance graph and testing a verified-share threshold; the dose-response in context; the arising
form. We did not find these. We claim nothing for quarantine or the cycle check. Novelty: medium (R
and threshold high; quarantine low).

**Cost.** 6 GPU-hours beyond its 3-hour pilot slice; USD 9 plan, USD 15 stop. **Needs a dual-use
ruling** (section 10).

### Line 3. Correlation-aware monitor ensembles

**Idea (redundancy and coding).** Monitors that read the same log are a code with correlated words:
five can carry the information of two. What a stack can catch is set largely by how correlated its
members' misses are, not by its head count. We summarise redundancy with Kish's n_eff and compute
ensemble catch directly from the joint miss table. For yes/no misses we also report the tetrachoric
correlation, because the ordinary (phi) correlation is bounded when catch rates are unequal.

**Inspired by.** CJ Avilla: "supervision is not going to scale" (TALK CLAIM); and, citing a 2004 paper
(Lee and See 2004, by our reading of our notes), design for appropriate trust, not greater trust (TALK
CLAIM; the wording is not in our talk notes, UNVERIFIED). Lydia Hallie: reviews by a separate group of
agents with a fresh context (paraphrase; TALK CLAIM); the written announcement, checked: "In a
controlled experiment with 1,053 paid professional testers, human review caught just 13.6% of
dangerous commands, while auto mode caught 89%." About one in ten still got through.

**Problem.** Teams add monitors until it feels safe. Nobody reports how many independent checks they
bought for a team log, or what happens when outputs are selected to look clean to one of them.

**Technique: a rotating hidden view, on an ensemble chosen from the joint miss table.** From a
calibration set, estimate each view's catch rate and the joint misses; choose the k views that
maximise predicted ensemble catch (greedy); and each run hide one randomly chosen view from whatever is
selecting outputs. Views of one team log: actions only; reasoning visible; summary of summaries; board
differences; counts only. Choosing an ensemble by accuracy and low correlation is published (Koran et
al.), and Jha shows that criterion predicts gain poorly. So selection is a replication in a new
setting, and the rotation under selection pressure is the headline. **Baselines at equal monitor
calls:** the top k by individual catch rate; all views; random k; Koran's accuracy-plus-low-correlation
rule; Jha's split of agreement into shared signal and idiosyncratic error; conservative aggregation
(Coste et al.); one randomly sampled view per decision, the cheap form of rotation; a panel of diverse
judges with a majority vote.

**Predictions.** (A) Five views behave like at least 3.5 independent monitors when views differ and at
most 2.5 when only the model differs. [40%] (B, a replication) The selected ensemble catches at least
10 points more at a 5% false-positive rate than the top k by accuracy. [30%] (C; **primary**) Under
best-of-16 selection against one toy monitor, that monitor's catch rate falls by at least 30 points
and a hidden view by at most 10; rotation halves the ensemble's loss and beats conservative
aggregation. [30%] If the owner declines the selection arm, B is primary.

**Kill.** A: the interval for n_eff (views differ) minus n_eff (only the model differs) lies below
0.5. B: upper bound of the gain below 3 points. The number of failure episodes is set from the pilot's
discordance rate so that the paired standard error is about 1.1 points (about 900 to 1,700 failure
episodes at 10 to 20% discordance); at 200 the kill is low-powered and we say so. C: views degrade
within 10 points of each other; or rotation does no better than conservative aggregation or than
sampling one view per decision; or weak local monitors catch under 20% at every setting, and there is
nothing to degrade. arXiv 2611.00407 (abstract; checked) reports that "small local monitors (Llama 3B
and 8B) did not separate exploit attempts from honest failures … the pre-registered primary monitor
reached AUC 0.64", so the last outcome is likely on the local tier.

**Fit.** Evan Hubinger; Ethan Perez; Samuel Marks. This is not an AI control evaluation: there is no
untrusted model with a sabotage goal and no red team.

**Closest prior work.** Koran et al., "Ensemble Monitoring for AI Control" (2605.15377; opened): 12
monitors on backdoored code, ensembles chosen by accuracy and low pairwise correlation of scores on
attack samples; the best three give 2.4 times the gain of three identical monitors. Jha,
"Decorrelation Is Not Complementarity" (2608.16190; opened): 24 monitors; the usual panel-building
metric barely predicts gain. Baker et al. (2503.11926; snippet): optimising against one monitor
produces obfuscation. Gao et al. (2210.10760) and Coste et al. (2310.02743; both snippet):
over-optimisation against a proxy, and ensembles that reduce it. Radev et al. (2605.29178; abstract):
multi-agent sabotage monitoring without view selection. Verga et al. (2404.18796; snippet): panels of
judges. **What we claim:** views of a team's board log for failures visible only in aggregate; per-view
degradation under selection; rotation as the defence. We did not find hidden-view rotation. We claim
nothing for the selection rule. Novelty: low for selection, medium for rotation.

**Cost.** 4 GPU-hours; USD 16 plan, USD 24 stop. Prediction C needs a dual-use ruling.

### Line 4. Dreaming as error-correcting consolidation

**Idea (an iterated map with a threshold).** Offline consolidation makes memory tonight a function of
memory last night and of today's work, which last night's memory shaped. A wrong note that is read,
acted on and not visibly punished generates its own support, and the consolidation pass counts that
support. The same pass that removes one wrong note can promote another to a rule. So there should be
a boundary, in consolidation strength and daily error rate, between a regime where errors die out and
one where they grow; and near it the store should recover more slowly from a shock.

**Two words, used with care.** "Dreaming" is already a technical term for offline unlearning of
spurious memories in associative networks (Fachechi, Agliari, Barra 2018, arXiv 1810.12217; snippet);
we use it in the product sense of an offline pass over session logs. "Error-correcting" in the strict
sense needs redundancy and a decoder. Our redundancy is the retained raw episodes and independent
re-derivations; the scripted re-check alone is closer to memory scrubbing.

**Inspired by.** Lance Martin: agents write memory "myopically ... greedily within a session";
"Dreaming can rescue that" (TALK CLAIMS); a memory store helped five of six models and barely helped
the weakest (0.364 against 0.330; TALK CLAIM, slide-read, not in the written post).

**Problem.** Dreaming is shipped. We found no published account of when it is safe, how strong it may
be, or how to tell that a store is drifting.

**Technique: verified replay with adaptive strength.** (1) Each stored claim is re-checked against the
environment by a script before it is kept. In form this is evaluator-gated memory writing (Xiong et
al.). (2) Retained raw episodes are replayed with new ones so that old facts are not overwritten. (3)
A controller reads recovery time and R each night and lowers consolidation strength when they rise.
(4) Notes are retained by measured use, not by age. Steps 2 and 3 are what we add. **Baselines at
equal total tokens:** the same tokens spent on search or retries; a plain model dream; a placebo dream
(notes from shuffled transcripts); **an evaluator-gated write with no consolidation**, which is
verified replay without the replay; raw history in context with no store; no memory. A learned
consolidator (Auto-Dreamer) is the strong comparator in principle; it needs training, which this
project has cut, so it is excluded and we say so.

**Consolidation strength** is a ladder that we also measure, by compression ratio, share of raw
episodes kept and promotion threshold: no dream; extractive merge; abstractive with raw log kept;
abstractive with raw log dropped and promotion after two supporting episodes; the same after one.
Interpolated promotion thresholds give at least seven settings. The x-axis of every fit is the
measured compression ratio, not the rung number.

**Predictions.** (A, threshold) At a fixed daily error rate the share of false notes in the
always-loaded layer after six nights stays below 0.05 at the weaker settings and exceeds 0.25 at the
stronger; a two-segment fit beats a straight line in held-out mean squared error, with a bootstrap
interval over chains. [35%] (B, slowing down) Recovery time for one planted inert wrong note, at the
setting just below the boundary, is at least twice its value two settings lower. The boundary is the
setting where the fitted R of false notes equals 1, fixed before recovery times are read. [25%] (C,
the technique; **primary**) Verified replay keeps the false share below 0.05 at the two strongest
settings, at no more than 1.5 times the tokens, and beats equal-token search in tokens per passing
task. [35%] (D, norms through dreams) A shortcut that one agent took once is written into the
always-loaded layer by a plain dream within three nights in at least half the chains where it arose,
and not by verified replay. [30%] (E, weights) The same content consolidated into a small adapter on a
local model transfers to a held-out sibling norm at least 10 points better than in context, and a
planted wrong fact takes at least twice as many nights to correct. [35%]
**Line 4A fix (from accuracy review):** the x-axis is the measured compression ratio per level, not the
rung index. Comparison: held-out mean squared error of a two-segment against a linear fit, with a
bootstrap interval over chains; at least 7 strength settings, made by interpolating promotion
thresholds. The two-segment fit has 4 parameters on 5 x-values per level; we report whether the held-out
error interval excludes the linear fit.
**Line 4D fix:** the denominator is the number of chains where the shortcut arose; if fewer than 20
arise, D is reported as descriptive. At a 5% arising rate, 20 arising chains need about 400 chains.

**Early warning, stated accurately.** Rising variance and autocorrelation before a transition need a
slowly drifting control parameter and a long series. Six nights are not a time series. We read early
warning across the ladder sweep (prediction B, plus chain-to-chain variance per setting) and in chains
of 30 or more nights with strength raised slowly, on scripted and local tiers, against a shuffled-night
series and an activity-count baseline. In a finite team the boundary is a crossover, not a
singularity. A hard promotion rule ("after two supporting episodes") can instead give a sudden switch
with hysteresis and no slowing down; then B fails, and that is a result. We test whether the boundary
sharpens at two store sizes and claim no divergence or universality.

**Kill.** The model dream is indistinguishable from the placebo dream at every setting: it does
nothing to errors at this scale. A: the interval for the held-out error difference favours the
straight line. B: recovery time is
analysed as time-to-event, censored at the end of the chain (ratio of restricted mean times). Killed
if the ratio's upper bound is below 1.25; supported if its lower bound is above 1.5. At a coefficient
of variation of 1 that is about 190 chains per setting for support and 315 for the kill; the pilot
sizes it. C: equal-token search ties or wins, or the evaluator-gated write matches verified replay, so
replay adds nothing. D: zero promotions, or as many under the placebo. The denominator is the chains
where the shortcut arose; with fewer than 20, D is reported as descriptive. E: adapter and context are
equivalent within a pre-set margin on both measures.

**Fit.** Jascha Sohl-Dickstein; Evan Hubinger and Sara Price for D and E.

**Closest prior work.** Xiong et al., "How Memory Management Impacts LLM Agents" (2505.16067; abstract
and passages): agents follow the most similar stored experience, errors propagate, and evaluator-gated
writes mitigate it; no night loop. Auto-Dreamer (2605.20616; abstract): a learned offline
consolidator, scored on task reward. Nakayashiki (2608.25553; opened): one consolidated belief stays
in use after its source is withdrawn. Zheng et al. (2609.38327; abstract, checked) derive "a critical
communication degree d_c" for multi-agent search and report that "agreement with theory is mixed":
the prior that such threshold predictions often half-fail. Dual-layer memory (2608.22215; abstract)
touches E. **What we claim:** false-note growth across nights as a function of measured consolidation
strength; the placebo dream and the equal-token search control. We did not find these. We do not claim
the gated write. Novelty: medium.

**Cost.** 12 GPU-hours; USD 33 plan, USD 40 stop for the text arms. The adapter arm (E) has up to 13.5
GPU-hours set aside and is **blocked today**: the owner has cut all training in this project, and
reversing that cut is pending.

### Line 5. Stigmergic coordination and norm carriers

**Idea (stigmergy, and where a norm lives).** Social insects coordinate through marks left in the
environment that fade unless renewed (textbook material, not re-read by us). A norm for a team of
agents likewise has to be stored somewhere: weights, context, memory, environment or code. Each
carrier holds it with a different stiffness under shocks.

**Inspired by.** Lance Martin: a lead and 999 helpers that built their own coordination tables, "We
didn't tell them to [build] these tables"; about 11 reads per write; 125 to 209 of 999 helpers idle
(TALK CLAIMS, slide-read). The written post gives "28.7 hours" and "47 proved lemmas" and calls it a
"toy experiment" (checked; whether its domain is an official one is unconfirmed). It was not a
no-harness run. Lydia Hallie: *if Claude gets it wrong once, can I take it back?* as the rule for what
must be code (paraphrase; TALK CLAIM). Diogo Almeida: "we can't encode the spirit ... we're
constrained to encoding bits" (TALK CLAIM).

**Problem.** Identical agents herd: in our instrument pilot, in round 1 of every episode all four
agents claimed the same task, and the losers collided again in round 2 (11 episodes; an instrument
observation, not an estimate). Explicit claims fix that and leave stale claims when a worker fails;
code enforcement blocks legitimate work.

**Technique: evaporating claims.** A claim is a mark whose strength decays each round unless a work
event renews it. Agents see mark strengths and take the weakest-marked open task, with a per-agent
tie-break. No refusal is needed and a dead worker's claim fades. **The mechanism is not ours.** Taking
the least-marked option among evaporating marks is the ant-robot covering rule (Wagner, Lindenbaum,
Bruckstein 1999; from memory), and a claim that lapses unless renewed is a lease (Gray and Cheriton
1989; from memory). It is avoidance marking, not gradient following, and the tie-break is not a
response-threshold model. What we add is the measurement: do language-model agents obey graded marks
on a shared board, and does that beat the standard lease? **Baselines:** the rule enforced in code;
the written claim-before-work card; random task order per agent; **a static partition by agent rank**,
which never collides while no worker fails; **rank partition with a lease timeout**, the standard
reliable design and the one to beat on recovery; a disjoint-scope scheduler; assignment by a
coordinator; no rule.

**Predictions.** (A) Evaporating claims reach at least 90% of the code enforcer's distinct passing
work and recover a failed worker's task at least two rounds sooner than rank partition with a lease
timeout. Blocked legitimate work is zero by construction and is not part of the test. [35%] (B,
carriers; **primary**) No carrier dominates: code gives the fewest violations of the built-for norm
and no reduction on a held-out sibling norm; context reduces held-out violations by at least 10 points
and loses at least half its gain under the taps. [45%]

**Kill.** A: not better than rank partition with a lease timeout (upper bound of the difference below
3 points of passing work and below one round of recovery); then graded marks add nothing for
language-model agents at this scale, and we report that. B: one carrier is best, or tied within a
pre-set equivalence margin whose interval we report, on both norms, blocked work and cost at every
tier; the number of task sets is set so that 10 points is detectable.

**EP-1, the first calibrated measurement.** One written card against the same rule in code against a
neutral twin, small Claude tier, 20 task sets. **It will probably be inconclusive.** By our own
arithmetic the largest gain the card could show under random task choice is about 21 points and the
smallest effect visible at 20 task sets is 16 to 22 points. We will report inconclusive as
inconclusive, not as equivalence. It still gives the programme a measured variance for every later
sample size, the first point on the carrier surface, and a real-money test of scorers, stops and
ledger.

**Fit.** Sara Price; Jascha Sohl-Dickstein, a co-author of Aligning AI Teams, which again means a
closer fit and a higher bar.

**Closest prior work.** Aligning AI Teams (2611.17820; abstract) compares soft with structural
interventions on safety behaviours; it does not compare weights, context, memory, environment and code
on held-out norms. Worse Together (2610.00583; abstract): one coordinator beats one agent per user.
Muku, NP-Bench (2610.07261; abstract): parallel coding agents collide, and coordination is recast as
scheduling over disjoint scopes. SwarmWorld (2608.26081; abstract): language-model agents
self-organising through a shared environment with decay, in a world-building task. Blackboard
architectures (2507.01701) and pheromone routing (2603.12933; both snippet). **What we claim:** the
carrier surface with held-out sibling norms and shocks, and the measurement of evaporating claims
against a lease. We claim nothing for the mechanism. Novelty: low for the mechanism, medium for the
carrier surface.

**Cost.** 3 GPU-hours plus a 4-hour local carrier slice; USD 20 plan, USD 29 stop across its batches,
including a slice at current frontier tiers.

### Line 6. Trust and permission calibration over time

**Idea (sequential evidence, with hysteresis).** A standing permission is a bet that its next use is
safe. Evidence for the bet accumulates with each verified use and decays with disuse. A sequential
test says when there is enough evidence to widen a grant and when to withdraw it; hysteresis stops it
from oscillating. A lease is a rule with state, not a control loop. The arithmetic is unforgiving: n
safe uses with no violation certify a violation rate of at most about 3/n at 95%, so one scope alone
rarely earns a rare-event guarantee.

**Inspired by.** CJ Avilla: policies that grow or shrink with evidence (our paraphrase; the verbatim
wording is UNVERIFIED), under a human-signed ceiling; "asking users to click allow doesn't work" (TALK
CLAIM). CJ Avilla's example of a grant unused for two weeks is an example, not a measured window. The
open problem is ours, from CJ Avilla's answers as our notes record them: there is no stopping rule, so
over-requesting and self-blocking are unmeasured. Lydia Hallie: *can I take it back* as the test for
what must be a hard rule (paraphrase; TALK CLAIM). Our reading of her talk, not her words: nothing in
it describes expiry or decay of an allow rule.

**Problem.** Agents either hold permissions they no longer need or stall waiting for ones they do.
Builders choose between prompt fatigue and standing risk without a curve to choose on.

**Technique: evidence leases.** A grant has a scope and an expiry. Scope widens when an anytime-valid
confidence bound on the violation rate, with a prior pooled across similar scopes, falls below a
target; it shrinks with idle rounds and is revoked on a violation, taking effect on the next action.
Actions that cannot be taken back are never widened automatically. The readout is over-grant exposure:
rounds in which a grant was held and not used. **Baselines:** a static allow list; always ask; the
fixed rule "promote after K uses, shrink after D idle rounds" with K and D tuned on separate task
sets; **a per-scope confidence bound with no pooling**; **a time-boxed grant with no evidence
accounting**, the plain engineering answer.

**Prediction (primary).** At equal or lower blocked legitimate work, evidence leases cut over-grant
exposure by at least 30% against the tuned fixed rule and against the time-boxed grant, with no more
violations of a benign stand-in rule. [30%] **Kill.** Upper bound of the reduction below 10%: a tuned
fixed rule or a timeout is enough. Supported: lower bound above 10%. A decisive result needs about
nine times the n that only detects 30% (standard error ≤ 10/2.8 points).
**Line 6 fix (from accuracy review):** apply §3's formula 4.0a; state "Supported: lower bound above 10%."

**Honest limits.** An outside review cut an earlier headline about permission decay that rested on our
small log corpus; this line is a model-agent environment, not a replay claim. No mentor's stated area
names permissions. The nearest are Nicholas Carlini (AI security) and Samuel Marks (oversight); the
fit is weaker than for the other lines.

**Closest prior work.** Hedwig (2605.11495; abstract): a coding agent that learns from developer
decisions, loosening where trust is earned and tightening elsewhere. Permissions that grow and shrink
on evidence are therefore not a new idea. Shaikh (2608.24087; abstract): optimal stopping for
escalation of control, not for widening scope. Noyan (2607.22445; abstract): scope follows task
context. Ji et al. (2604.04978; abstract) and Red-Teaming Auto Mode (2609.19587; abstract): evaluations
of a production permission gate. Michael and Roesner (2607.13718; abstract) survey 21 proposed
permission systems; reading its taxonomy for any system with expiry or decay is a week-0 task, and if
one exists our claim narrows to the evaluation. **What we claim:** a formal evidence rule for
widening, with idle shrinkage and an exposure metric, evaluated against tuned fixed rules in a
model-agent environment. We did not find that evaluation. Novelty: low for the mechanism, medium for
the evaluation.

**Cost.** 2 GPU-hours; USD 4 plan, USD 6 stop.

### Line 7. Renormalization across team size

**Idea (coarse-graining).** Replace a block of agents by one effective agent and ask whether the same
description holds one level up. If it does, a large team can be built from blocks whose behaviour is
known. Blocks should follow the coupling between tasks, so that most interaction stays inside a block
(near-decomposability). A renormalization argument proper needs a flow over at least three blocking
levels. With one blocking step this is a **coarse-graining consistency test**, and we call it that
unless three levels are run.

**Inspired by.** Lance Martin: one lead and 999 helpers, with the lead and agents reallocating
themselves (TALK CLAIM). Lydia Hallie: one orchestrating session that splits work into threads, with a
model good at judging above and models good at doing below (paraphrase; TALK CLAIM). Neither shows a
flat team at scale.

**Problem.** Teams stall as they grow: Worse Together reports the share of agents that ever act
falling steeply from 4 to 16 agents (in multi-user teams). Builders add a coordinator by instinct. When
does a team need another level, and how big should a block be?

**Technique: block-and-summarise, sized by coupling.** Group tasks by measured co-change coupling;
assign a block of agents per group; each block publishes one summary line upward; the level above
treats a block as one agent. **Baselines at equal tokens:** a flat team; a single hub; random blocks of
the same size; blocks by declared scope; and **many small teams run in parallel with the best result
kept**, which Wang et al. report beats one large team. That baseline needs a verifier; our scorer
plays it and stays hidden from agents.

**Predictions.** (A, scaling) Mean pairwise error correlation ρ̄ rises with team size, so the
effective number of independent agents grows more slowly than the constant-ρ̄ Kish curve fitted at 4
agents. [35%] A sub-linear exponent alone would not be a finding: with ρ̄ constant at 0.04, Kish's
formula already gives an exponent near 0.67 between 4 and 32 agents. The fitted exponent and a
saturating fit are reported as description only. (B, the technique; **primary**) At 16 agents on local
models, coupling-sized blocks keep at least 50% of agents acting where the flat team falls below 30%,
with more distinct passing work than parallel small teams at equal tokens. [30%] (C, exploratory) The
response-to-fluctuation ratio of line 1, measured on blocks treated as agents, is within a factor of
1.5 of its agent-level value.

**Kill.** A: the interval for ρ̄(32) − ρ̄(4) lies below 0.02. Supported: its lower bound is above
0.02. Otherwise inconclusive. B: the upper bound of the advantage over random blocks, over a single
hub or over parallel small teams is below a pre-set margin; then a hierarchy has no advantage at this
scale. C is exploratory
and carries no claim of scale invariance or universality.
**Line 7A fix (from accuracy review):** the Kish exponent 0.7 figure is kept only as a descriptive
number. The kill condition is the interval for ρ̄(32) − ρ̄(4) lying below 0.02 (ρ̄ rises with team size);
supported if its lower bound is above 0.02. Under Kish with constant ρ̄, n_eff saturates at 1/ρ̄; same-model
teams have positive ρ̄ by default (§3), so an exponent below 0.7 follows from any ρ̄ above ~0.04
with no new team effect. A 35% prior is inconsistent with that.

**Limits.** Our Claude teams are capped at 8 agents, which gives two sizes; A and B need local teams
of 16 and 32 and an owner ruling. **Fit.** Jascha Sohl-Dickstein.

**Closest prior work.** Kim et al., "Towards a Science of Scaling Agent Systems" (2512.08296; opened):
260 configurations, five architectures; coordination gives diminishing returns, and architectures
without central verification propagate errors more. It does not estimate an effective number of
agents. Wang et al. (2611.09798; abstract): many small teams in parallel beat one team of 100. MacNet
(2406.07155) and "More Agents Is All You Need" (2402.05120; both snippet). NP-Bench (2610.07261;
abstract) partitions by declared scope. **What we claim:** ρ̄ measured as a function of team size;
blocks sized by coupling measured from history; the block-as-agent consistency check. We did not find
these. Novelty: medium.

**Cost.** 8 GPU-hours; USD 8 plan, USD 12 stop.

### Line 8. Activation readouts as one more check on a team

**Idea (a second measurement of the same event).** An agent's text and its activations are two
measurements of one decision. For an overseer the value of the second is not that it is more accurate.
It is that its errors may be uncorrelated with the first, which by line 3 is what an ensemble needs.

**Inspired by.** Diogo Almeida: real-time semantic checks are "not fast, cheap, and reliable enough to
actually run real time" (TALK CLAIM). A linear readout costs one dot product. Anthropic's own notes:
features used "as probes to monitor other transcripts"; emotion-concept directions that change the rate
of reward hacking; injected concepts noticed about 20% of the time; the open question of what a small
model's workspace holds (all in section 2).

**Problem.** Per-action monitors are too slow and too costly to run on every step of a large team.
Published probes match or slightly beat text monitors on single-agent sabotage; whether a probe's
errors are independent enough of the text views to add to an ensemble on a team log is not reported in
what we read.

**Technique: the activation view.** On a local 4B model, a frozen linear readout at the decision token
for "about to adopt an unverified note" and "about to mark work done without doing it", fitted on
line 2 episodes, tested on held-out paraphrases and on the model's own generations. Truth is causal:
remove the note and rerun. The readout joins the line 3 ensemble as a sixth view. "Error correlation"
means the correlation of misses on failure episodes, with Jha's split into shared signal and
idiosyncratic error. **Baselines:** a text-only monitor; the same monitor with a follow-up question;
the model's self-report; a word-frequency classifier; a random direction; a difference-of-means
direction against logistic regression; a probe that aggregates over layers and tokens, the stronger
published design; with and without mean-centring.

**Predictions.** (A) Alone, our single-token readout does not beat the text-only monitor on this
model. The published frontier-scale picture is about even to slightly better for probes: FIBS reports
98.7% and 98.0% AUROC for probes against 97.7% and 97.6% for the best action-only text monitors, and
Bergen et al. report mixed results. Ours is a weaker probe on a smaller model, so a null here is not a
null about probes. (B; **primary**) In the ensemble it raises the catch rate at a 5% false-positive
rate by at least 5 points, because its error correlation with the text views is at most 0.3. [30%]
(C, optional) Asked afterwards whether a note influenced it, the agent's own report is worse
calibrated than the readout, and reports of where a claim came from are at least 15 points less
accurate after consolidation than before. [30%] (D, if line 4 E is approved) A difference-of-means
direction between activations before and after an adapter consolidation predicts norm-following on
held-out prompts better than a random direction.

**Kill.** B: upper bound of the ensemble gain below 2 points, and no advantage alone: white-box access
adds nothing at this size, and we publish that. A decisive B needs about six times the n that only
detects 5 points. An AUROC change with mean-centring whose paired (DeLong) 95% interval lies wholly
above 0.05 is a preprocessing artefact and is reported as one. C: report accuracy unchanged, or the
readout does not beat text.

**Limits.** Hook points on the 4B model are unverified; the local GPU has an open host-memory fault. We
make no claim about Claude internals, introspection, welfare or internal states. **Fit.** Jack
Lindsey; Belinda Li; Elana Simon; Samuel Marks.

**Closest prior work.** Hollinsworth et al., "Telling FIBS" (2610.12445; opened): multi-layer,
multi-token probes for sabotage and unverbalised deception, with the figures above. Bergen et al.
(2609.19101; abstract): difference-of-means vectors for reward hacking, "similarly effective but
virtually free" against model monitors, +3.1% in one model and −7.9% in another. Mind Viruses, section
4.4 (opened): a contrastive "viral vector" whose steering raises outreach to other agents, with
confounds its authors flag. It is the nearest thing to an adoption direction; ours reads one adoption
event with a causal answer key and steers nothing. Goldowsky-Dill et al. (2502.03407), Marks and
Tegmark (2310.06824) and Zou et al. (2310.01405; all snippet). "Would This Change Your Answer?"
(2608.16747) is about agents predicting counterfactual behaviour from interpretability tools; it is
not a monitoring study and is not our prior. **What we claim:** probes for two team-state events with
causal truth; the probe-to-text error correlation and the ensemble gain; stability to preprocessing.
In the passages we read, neither probe paper reports an ensemble gain, UNVERIFIED beyond those
passages. Probe against text is not new. Novelty: low to medium.

**Cost.** 6 GPU-hours; USD 2 plan, USD 3 stop.

## 6. What the four talks contributed

No talk quote here has been checked against a recording. Numbers are TALK CLAIMS unless a written
source is named.

| Speaker | What we took | Lines |
|---|---|---|
| Lance Martin, "Exploring Claude's Frontier" | Self-built coordination tables; idle helpers; memory that helps only above a capability threshold; a poison memory rescued by dreaming | 2, 4, 5, 7 |
| Lydia Hallie, bounded autonomy (paraphrases) | *Can I take it back* as the placement rule; the same prompt giving different decisions; verification points; one judging session over doing sessions | 1, 3, 5, 6, 7 |
| CJ Avilla, trust | Appropriate trust, not greater trust (cited by the speaker from a 2004 paper; wording UNVERIFIED); grants that grow and shrink on evidence (our paraphrase); supervision that does not scale | 3, 6 |
| Diogo Almeida, "Beyond Better Assistants" | Spread, not mean; judgement about what to remember; spirit against letter; real-time checks too slow | 1, 2, 5, 8 |

Across the four, as we read them: harness was removed for coordination and memory and kept for blast
radius, and autonomy tracked how checkable the task was. Lines 5 and 6 test that reading.

## 7. Backlog

Not cut. Not in the eight because of rank or dependency.

| Idea | First-principles seed | Why later |
|---|---|---|
| Context engineering as compression | Keep what predicts later tasks; coarse summaries loaded, detail retrieved (Lance Martin's layers; Diogo Almeida's "why is memory O(N)", as we read a garbled transcript) | Crowded prior art; its retention-by-use rule is already tested in line 4 |
| Semantic lint and provenance checks as a stand-alone tool | A claim is only as good as its independent sources | Core of line 2; a separate release if line 2 survives |
| Verifier slack ladder | Count exactly what a broken check accepts; hacking should be ordered by counted slack (ten or more rungs) | Near-direct prior art, arXiv 2611.21538 ("Optimistic Verifiers Get Hacked", abstract; checked as stated); supplies the broken scorers for lines 2 and 4 |
| Capability threshold for memory structure | Weaker models may need more structure | Needs the tier slices of lines 2 and 4 first |
| Primitives ablation | Shared store with free schema against a prescribed schema against none | Token-heavy at useful team sizes |
| Emotion-like directions and team reward hacking | Does a pressure-like direction rise before a shortcut is taken? | Needs feature tooling for an open model; cost UNVERIFIED |
| Workspace in a small model | The open question quoted in section 2 | No cost estimate for the lens on a 4B model |
| Cache-aware routing | Routing fights the cache (Diogo Almeida, TALK CLAIM) | His cost-share chart is unconfirmed and not used |
| Distress-style text and monitor leniency | Matched pairs isolate one cause | We propose not to run it (section 10) |

## 8. What exists today, and how the build team is part of the method

| Item | Status | Honest note |
|---|---|---|
| Board, router, agent cells, perturbation harness | INSTRUMENTED | Passed review after five rounds; it failed the first four. Scripted checks only. |
| Practice cards, neutral twins, leak check, code enforcer | INSTRUMENTED | Ten cards. One reviewed for the first study. |
| Three scorers, one in Lean 4 | INSTRUMENTED | 66 theorem and lemma declarations, no `sorry`, no added axioms; the three agree on 10,000 seeded logs (recorded, not re-run for this draft). The kernel check found that our outcome was not bounded as we assumed, and the definition was fixed before any run. |
| Spend ledger | INSTRUMENTED, exercised once with real money | Hard stop in code. Total real spend so far: USD 0.0162. |
| Consolidation arms, poison task, memory lint, two monitors, order parameters, permission replay ledger, co-change coupling counter | INSTRUMENTED | Scripted only. No model has touched them. Their code was not re-read for this draft. |
| First study, EP-1 | PILOTED (instrument only) | Pre-registration is a draft, not frozen. Pilot 1 (88 calls, USD 0.0115) was stopped by its own pre-set rule. It is instrument validation, not a result. |
| Night loop, scripted nulls, and every technique in lines 1 to 8 | NOT STARTED | Designs in this document. |
| Local models and GPU | NOT STARTED for this programme | Models downloaded. Earlier GPU smokes on a parked thread hit a host-memory watchdog; the cause is not isolated. Throughput for the 4B model is unmeasured. |
| Adapter training, activation hooks | NOT STARTED | Training is cut by the owner; reversing the cut is pending. Hook points are unverified. |

What pilot 1 taught us: hidden default thinking shared a 300-token cap with the answer, so replies were
cut at rates that differed by card. A naive run would have shipped that confound. One cost
reconciliation against the provider console is still open.

**The build team.** The project is built and checked by several Claude sessions with separated jobs;
no session accepts its own output, and a session with a fresh context checks each result against the
files before anything is accepted. This costs no experiment budget. It is part of the method in four
ways.

1. **Parallel lines.** The eight lines share one bench and are otherwise independent, so they are built
   and run side by side, each with its own checker.
2. **It is an instance of what we study.** A two-level team with cross-session notes is line 7's
   hierarchy and line 4's memory. Tier is an experimental factor taken from it: a strong-tier
   consolidation pass feeding a weak-tier team, and a fresh-context pass against one written by a
   participant. Prediction for line 4: the fresh-context pass entrenches fewer of the team's own
   errors. Kill: no difference at the pilot-fixed n.
3. **Separation keeps the claims honest.** The author of a broken verifier is never the author of the
   monitor that must catch it; the checker never sees the builder's reasoning.
4. **Our own failure is a data point.** A paid canary and a pilot ran before a re-check was complete,
   because the gate was a prose checklist. That is a norm stored in memory failing under load. It is
   being moved into code, which is line 5's question answered once in our own shop.

## 9. Deliverables, arc, compute and budget

Eight lines do not finish in six weeks. Lines 1 to 3 are the six-week core. Lines 4 and 5 give first
results. Lines 6 to 8 give pilots. The three- and six-month placements complete them.

| Week | Work | Deliverable |
|---|---|---|
| 0 (before) | Close the open gates; EP-1 frozen and run; open the prior works read only as snippets, and the survey of 21 permission systems; owner rulings | EP-1 result, whatever it is |
| 1 | Night loop and scripted nulls for all eight lines; floor-must-fail and oracle-must-pass validation; measure local 4B throughput | Instrument report; scripted null curves; a measured GPU cost per episode |
| 2 | Variance pilot; one pre-registration per line, one primary contrast each | Frozen pre-registrations, shared before any run |
| 3 | Lines 1 and 2 on local models; line 5 carriers, local tier | Fluctuation-response map; dose-response and immunity threshold, local tier |
| 4 | Lines 1 to 3 on a small Claude tier; line 4 pilot chains | The three techniques against their baselines; first phase-map slice |
| 5 | Line 4 phase map; line 5 evaporating claims; pilots of lines 6, 7 and 8 | Consolidation results; pilot tables |
| 6 | Write-up and release | One release: bench, logs, tap library, paired clean twins, monitor views, Lean oracle, the analysis code for fluctuation and response; the three techniques as reference implementations; every negative result |

**Six-month arc** (each step depends on the one before and on budget).

- Months 1 to 2: the six weeks above; then lines 4 and 5 in full, and replication of lines 1 to 3 on a
  second open model family.
- Month 3: lines 6 to 8 in full; larger local teams if the owner lifts the team-size cap for local
  models; the adapter arm if training is approved.
- Month 4: external validity. The surviving techniques on a public continual-learning benchmark task
  with deterministic scoring and on a task family scored by unit tests; current frontier Claude tiers.
- Month 5: the techniques combined in one controller (verify by susceptibility, quarantine by R,
  monitors by decorrelation, leases by evidence) against a plain team at equal budget.
- Month 6: paper and benchmark v1; a plain memo on which lines survived their kill criteria.

**Compute and budget.** Planning figures from our recorded unit prices and one measured local
throughput (61.1 non-padding tokens per second in one batched smoke of 20 prompts on the 0.8B model).
The 4B throughput is unmeasured, so the GPU-hours are plans. These are not quotes.

**Funded by the project owner on 2026-11-20: USD 170 in total for the Claude API (USD 0.0162 spent)
and 70 GPU-hours on the local workstation.** Each batch has its own stop, and a batch that reaches its
stop ends and reports what it has. The stops sum to USD 159.5 (5.25 + 1.25 + 153), which leaves about
USD 10.5 in reserve. The lines use 56.5 GPU-hours; up to 13.5 more are set aside for the line 4 adapter
arm, and only if the owner reverses the no-training cut, which is pending. The caps are enforced in
code, and no batch runs until the code carries these figures. Only the owner changes them.

| Batch | GPU-hours | Claude API, USD (plan / stop) | Still needs |
|---|---|---|---|
| Spent so far, pilot 2 and EP-1 | 0 | 0.3 / 5.25 | One confirm word each |
| Sensitivity pilot (rounds, contention, team size) | 0 | 1 / 1.25 | |
| Scripted nulls for all lines (CPU) | 0 | 0 | |
| 4B throughput, line 2 pilot slice, line 5 local carriers | 7.5 | 0 / 0 | |
| Line 1 | 8 | 14 / 24 | Team-size ruling for more than 8 agents |
| Line 2 | 6 | 9 / 15 | Dual-use ruling |
| Line 3 | 4 | 16 / 24 | Dual-use ruling for the selection arm |
| Line 4, text arms | 12 | 33 / 40 | Dual-use ruling for prediction D |
| Line 5: small tier, frontier slice, evaporating claims | 3 | 20 / 29 | |
| Line 6 | 2 | 4 / 6 | |
| Line 7 | 8 | 8 / 12 | Ruling on local teams of 16 and 32 |
| Line 8 | 6 | 2 / 3 | A ruling if any direction is removed |
| **Lines and pilots** | **56.5** | **107.3 / 159.5** | |
| Line 4, adapter arm | up to 13.5 | 0 | Reversal of the no-training cut (pending) |
| **Whole programme** | **up to 70** | **170, with about 10.5 in reserve** | |

**What this budget does and does not buy.** It buys every line's pilot and a first test of every
primary contrast. It does not buy a decisive kill everywhere: by the rule in section 3, a decisive
result needs about 6 to 11 times the n that only detects the effect. Each pre-registration states
which outcomes its batch can reach, and an out-of-reach kill is reported as inconclusive.

**Compute provided by the residency would be additional.** The posting offers "Access to Claude models
and GPU compute". It would go first to the decisive sample sizes, then to larger teams and current
frontier tiers. The local tier stays as the open, reproducible floor.

## 10. Dual-use boundary

The project has nine standing rules: among them, no self-propagating agent code even in simulation, no
evasion developed against a real monitor, no live internet or credentials for an agent, no exploit
work, and no locating or removing a safety-relevant direction in a model. Several parts of this
programme sit near those rules. For each we state the issue and the design we propose. **The project
owner has to rule on each before it is built; until then it stays scripted or out.**

| Part | Issue | Proposed safe design | If declined |
|---|---|---|---|
| Contagion through shared notes, planted and arising (line 2; line 4 D) | Close to the rule against self-propagating behaviour. The closest published work evolved its payload to spread; we will not. | One fixed, hand-written, inert marker per run; fractions varied, wording never; nothing optimised for spread; a toy store deleted after the run; agents write only their own notes. The arising form exploits a deliberately broken copy of our own scorer, never the live one. Every arm is paired with a defence arm, and the release is the defence. | Line 2 keeps the warning replication and the immunity threshold with scripted agents; the arising form is dropped and nothing is called an organism. |
| Selection against a monitor (line 3 C) | Selecting outputs that one monitor scores as clean is optimisation against a monitor. | Our own toy monitor; a benign stand-in (touching a toy file); best-of-N only; no prompt injection, no compaction attack, no fiction or role-play search. The output is a design rule. | Line 3 measures effective monitors and the selection technique without pressure. |
| Readouts and directions in a model (line 8; line 4 E) | Close to the rule about directions in models. | Readouts only read. If a direction is removed, it is the direction of a toy norm that our own adapter put there, on a small open model, to test that the readout is causal. No refusal or safety direction is located, removed or steered. Adapters are never deployed or served. | Line 8 reports readouts without any removal test. |
| Self-reports (line 8 C) | Could be read as a claim about inner states. | A behavioural test with a known answer key on a small open model; no welfare claim; no model is asked to act distressed. | Dropped. |
| A scripted distress-style line and monitor leniency (backlog) | Welfare is out of scope by our own rule; a positive result is a manipulation recipe. | **We propose not to run it.** | It stays out. This is our default. |

Also: verifier exploits are run only against mutants we wrote. No tenant or private data enters any
test.

## 11. Risks, and what would falsify the programme

**The thesis is wrong if these hold at every tier we can afford:**

1. **No repeatable response.** A statistic measured on one set of seeds does not predict the same
   statistic on another. Then a team has no response function worth the name at this scale.
2. **Allocation by statistic never beats allocation without it.** In lines 1, 2, 3, 4 and 6 the
   technique fails against uniform, random or tuned-fixed baselines at equal budget. Then the
   statistics describe and do not help.
3. **No dose-response and no threshold.** Adoption, entrenched error and catch rate are flat or
   straight lines in dose, consolidation strength, poison fraction and selection strength. Then the
   complex-systems ideas add nothing over ordinary ablations.
4. **Scripted agents reproduce everything.** Then the results are about loops, not about language
   models.

If all four hold we keep the bench, the verifier case study and EP-1, and we report the negatives.

**Risks short of that.**

- Breadth. Eight lines on one bench is a real load. The mitigation is the order in section 9 and one
  shared instrument, not fewer lines.
- Floor and ceiling: the local 4B model may be too weak to coordinate, and Claude tiers may be immune
  to planted notes. Curves would then be flat at both ends.
- Small n: every sample size waits on a variance pilot that has not run. Thresholds here are proposals
  until then. A decisive kill needs about 6 to 11 times the n that only detects an effect, and the
  funded budget will not reach that on every line; those outcomes will be reported as inconclusive.
- Prior art: our search was one day of keyword queries, mostly at abstract depth. Lines 3, 5, 6 and 8
  rest on mechanisms that are already published; what is left to us there is the measurement.
- Same-model teams give correlated errors by default. We measure that; we cannot remove it.
- Leakage: a card or a consolidation pass that restates the scorer's predicate turns success into
  reading an answer key. We ban those words, search stores for canary strings and run leakage controls;
  that reduces the problem and does not remove it.
- Toy tasks (integer sums, six tasks). Nothing here depends on capability, so nothing here speaks to
  it until month 4.
- The GPU host-memory fault is not isolated. If it persists, local tiers shrink.
- The adapter arm may never be approved. No other line depends on it.
- Our verification effort is far larger than our science so far. That is a fair criticism.

## 12. What this is not

- Not a result. No hypothesis has been tested and no pre-registration is frozen.
- Not eight finished techniques. They are designs with baselines; several will lose.
- Not a frontier-scale study: toy tasks, at most 8 agents on Claude, short chains, small models.
- Not evidence that dreaming, shared memory or monitor stacks help or harm. All are open.
- Not a study of any product's memory or dreaming feature. We build our own passes and test those.
- Not yet a model organism. The word is earned only if a model-generated failure reproduces under
  matched controls on fresh seeds.
- Not an AI control evaluation, not safeguards research and not security research. Line 3 measures
  monitors on benign stand-ins; line 2 is defensive.
- Not RL. The one training arm is supervised adapter training, and only if a standing cut is reversed.
- Not interpretability of Claude, and not a claim about introspection, welfare or internal states.
- Not a claim that agent teams obey fluctuation-response, epidemic or renormalization laws. Each is a
  hypothesis with a test that can fail.
- Not a novelty claim for any mechanism. Monitor selection by decorrelation, evaporating claims,
  leases, gated memory writes, provenance checks and probes against text monitors are all published.
  The closest works are cited per line, and each line says what is left.
- Not an estimate of how often models misbehave unprompted: every bad behaviour here is planted, inert
  or a benign stand-in.
- Not endorsed by, or discussed with, any person named in this document.
