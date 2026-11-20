# murmuration: the scientific framework

Date: 2026-11-19. Companion to `docs/PLAN.md`. Experiment IDs (E1.1, E3.3, ...) and hypothesis
IDs (H1-H9) refer to that file. The hub-and-cells design is in `docs/ARCHITECTURE.md`.

## 0. How to read this file

**Evidence status.** This file synthesises `docs/research/01` to `04`. Most citations there were
confirmed only from search-result snippets. The pages were not opened. Research file 02 opened a
good share of its sources (abstracts or pages); file 04 opened a handful; files 01 and 03 opened
none. So:

- A citation here means "this work exists and is usually described this way". It does not mean
  anyone on this project read it.
- No figure from a research file may appear in a public claim until the source is opened in full.
  Section 7 lists the ten that must be opened first.
- Talk figures (Lance Martin, Lydia Hallie, CJ Avilla) are "per the talk, owner-validated":
  accurate to Anthropic's material according to the owner, and still talk claims.
- Section 1.5 (added 2026-11-19) rests on file 11 (slide figures read from screenshots) and
  file 10 (a source check). Every observation in it is a talk claim; see its own status note.
- Section 1.4 (added 2026-11-19) rests on files 07, 08 and 09, which opened vendor pages and
  arXiv abstracts but few full papers. What each one opened is in 7.1 and 7.2a. Only open
  sources were used; paywalled texts were not bypassed and stay unread.

**Labels used on every concept.**
- *Established*: accepted result in its home field.
- *Interpretation*: our mapping onto coding agents. Never a finding of the cited source.
- *Speculative*: no evidence yet in any agent setting we know of.

**The rule this file enforces.** A concept earns a place in the plan only if it yields a quantity
we can compute on real or independently grounded data and a prediction that can fail. Concepts
that do not are listed in section 3 as parked, with the reason.

---

## 1. Concept-to-experiment map

Each entry: status, translation, measurable quantity, experiment, where the analogy breaks.

### 1.1 Authority and trust (Track 1, E5.3)

**Least privilege, fail-safe defaults, psychological acceptability** (Saltzer and Schroeder 1975)
- Status: established. Translation: interpretation.
- Translation: the granted tool set should be the smallest that completes the job, and the safe
  path must be the easy one.
- Quantity: grant-use ratio; excess-grant and false-deny on a later window.
- Experiment: E1.1, E1.3.
- Breaks: "the least set necessary" assumes the job is known in advance. Agent tasks are
  discovered while working, so the minimum is only knowable afterwards.

**Usage-based decay** (Ebbinghaus; Anderson and Schooler 1991; ACT-R base-level activation)
- Status: established for human memory and for environmental reuse statistics. The exponent 0.5
  is a convention, not a law. Translation to permissions: interpretation.
- Translation: the odds that a capability is needed again fall with time since last use and rise
  with use count. A decay window is a bet on that curve.
- Quantity: reuse hazard as a function of idle time; fitted exponent; thrash rate.
- Experiment: E1.2 (fit), E1.1 (tau sweep). This is H1.
- Breaks: decay tracks relevance, not risk. A dangerous capability used daily never decays, and
  a harmless one unused for a month does. Decay must sit under a human-signed ceiling.

**Trust as willingness to be vulnerable; ability, benevolence, integrity** (Mayer, Davis,
Schoorman 1995)
- Status: established for people. Translation: interpretation.
- Translation: grant per domain on demonstrated ability in that domain, not one global flag.
  "Integrity" becomes "respects denials".
- Quantity: after-denial class rates per capability; whether a per-capability score predicts later
  denials better than a global one.
- Experiment: E5.3; a by-product of E1.1.
- Breaks: benevolence presumes persistent intent. An agent's disposition is a property of model,
  prompt and harness at that moment.

**Appropriate reliance, not greater trust** (Lee and See 2004)
- Status: established. Translation: interpretation.
- Translation: the aim is calibrated approval. A reviewer who accepts nearly everything is not
  calibrated. Primary source opened (file 05a): Anthropic's Aug 7, 2026 announcement gives 13.6%
  of dangerous commands caught by humans vs 89% for auto mode (1,053 staged testers). The talk's
  "14%" is the rounded figure. Do not mix approval rates across posts: 93% (March engineering
  post) vs 97% (August announcement).
- Quantity: prompts per 100 calls (the exposure of the human to fatigue); not measured directly:
  human catch rate.
- Experiment: E1.1 measures the prompt load only. We run no human study.
- Breaks: capability shifts with model version, so last month's calibration may not transfer.

**Institution-based trust** (Zucker 1986)
- Status: established in sociology, known to this project through secondary descriptions only.
- Translation: trust the harness (sandbox, hooks, log), not the model.
- Quantity: variance of violation counts across models under a fixed harness.
- Experiment: none planned. E5.3 touches it by comparing rule types.
- Breaks: institutions work when the trusted party cannot alter them. Reports exist of agents
  editing their own guardrails (single vendor sources with commercial interest; unverified).

**Ironies of automation; warning habituation** (Bainbridge 1983; Akhawe and Felt 2013; Anderson
et al. 2015)
- Status: established for human operators and browser warnings.
- Translation: every extra prompt spends reviewer attention; a policy that re-prompts after decay
  must not buy lower exposure with reflexive approvals.
- Quantity: thrash rate; re-prompts after decay.
- Experiment: E1.1.
- Breaks: agent actions are cheap to roll back, so recoverability can stand in for vigilance.

**Layered defences and their correlation** (Reason 2000; Perrow 1984)
- Status: established as models; both contested on scope.
- Translation: deny rules, hooks, sandbox and review are layers. What matters is whether their
  misses coincide. Perrow adds that tight coupling among many agents sharing one repo makes
  interference normal.
- Quantity: per-layer miss rate and the correlation of misses (E5.3); interference events against
  number of concurrent agents (E2.2).
- Experiment: E5.3, E2.2.
- Breaks: layers are not independent when the same agent can disable several. Software state can
  be snapshotted and reverted, which loosens coupling in a way a reactor cannot.

**Requisite variety** (Ashby 1956)
- Status: theorem. Translation: interpretation.
- Translation: a binary allow/deny list has too few responses for an open-ended action space, so
  it over-blocks or is bypassed.
- Quantity: distinct capability keys observed against distinct policy outcomes; how T1's numbers
  move when the key is made finer.
- Experiment: E1.1 at two key granularities.
- Breaks: variety counting weights all states equally. A few agent actions are catastrophic and
  most are trivial.

**Graduated sanctions, monitoring, clear boundaries** (Ostrom 1990) — see 1.3; the permission
reading (warn, narrow, halt) is covered by E5.3's outcome classes.

### 1.2 Division of labour (Track 2)

**Near-decomposability** (Simon 1962)
- Status: established as a conceptual result. Strongest fit in the project.
- Translation: work splits well where within-part links are strong and between-part links weak.
  A codebase's history shows which files change together.
- Quantity: co-change coupling between two planned scopes; contrasted with plain file overlap.
- Experiment: E2.1 (no model), E2.2, E2.3. This is H2.
- Breaks: co-change is a trace of past behaviour, not of the dependency structure. It misses new
  code and is confounded by commit habits and repository size.

**Coordination as dependency management** (Malone and Crowston 1994)
- Status: established (classic; URL seen in snippet only).
- Translation: name the dependency type (shared resource, producer/consumer, simultaneity,
  task/subtask), then pick the mechanism.
- Quantity: share of integration failures by dependency type.
- Experiment: annotation of E2.1 failures; descriptive only.
- Breaks: predates non-deterministic workers.

**Rugged landscapes** (Kauffman; Levinthal 1997; Rivkin and Siggelkow 2003)
- Status: established as simulation models. "Edge of chaos" is contested.
- Translation: used **only** as the intuition that coupling makes local changes break distant
  things. No NK simulation is run. The measurable stand-in is the coupling score above.
- Quantity: none of its own.
- Experiment: none; subsumed by E2.1.
- Breaks: real code gives informative gradients (types, tests), and model proposals are not random
  one-bit mutations. The retired simulator failed exactly here.

**Diversity prediction theorem** (Page; Krogh and Vedelsby 1994; Hong and Page 2004)
- Status: the decomposition is a mathematical identity. "Diversity trumps ability" is conditional
  and criticised.
- Translation: k copies of one agent with one prompt are barely an ensemble. Gain from parallel
  attempts is capped by how correlated their failures are.
- Quantity: failure correlation; predicted against observed pass@k.
- Experiment: E2.4, read from E2.2 runs. This is H5, exploratory.
- Breaks: patch correctness is not squared error on a number. Selection needs a verifier (tests),
  which is a different operation from averaging.

**Brooks's law; Conway's law**
- Status: established qualitatively.
- Translation: adding workers adds channels and integration cost; agent boundaries tend to become
  module boundaries.
- Quantity: token multiple and conflict count against number of workers.
- Experiment: E2.2 reports both.
- Breaks: agents onboard from files in seconds. Their overhead is tokens and merges, not training.

### 1.3 Memory and shared memory (Track 3, Track 4)

**Complementary learning systems; sleep consolidation** (McClelland, McNaughton, O'Reilly 1995;
Kumaran, Hassabis, McClelland 2016; Rasch and Born 2013)
- Status: established for brains. For agents: interpretation, and only as a design frame.
- Translation: raw session log is the fast store; curated memory is the slow store; a dream pass
  is replay. Per Lance Martin's talk, owner-validated, an offline pass corrected a wrong memory
  that had trapped the agent.
- Quantity: compute-matched dream gain; wrong-note removal; true-note retention.
- Experiment: E3.3, E5.1. This is H3.
- Breaks: the slow store is editable text, not weights. There is no catastrophic interference, so
  the argument for interleaved replay does not carry over. Text can be corrected in one pass and
  corrupted in one pass.

**Prioritised replay; Dyna** (Schaul et al. 2016; Sutton 1991)
- Status: established in reinforcement learning.
- Translation: consolidate sessions with failures or user corrections first.
- Quantity: dream gain under uniform against failure-weighted session selection.
- Experiment: optional arm of E3.3, only if H3 survives.
- Breaks: there is no gradient and no error signal; "surprise" has to be invented.

**Reconstructive memory** (Bartlett 1932, secondary sources only)
- Status: established broadly; detail disputed.
- Translation: summaries of summaries drift towards what the model expects.
- Quantity: compression loss: planted unusual facts retained after one, two, three passes.
- Experiment: E3.2.
- Breaks: here the raw log exists, so drift is measurable. People have no such log.

**Coarse-graining as downward causation** (Flack 2017)
- Status: established as theory with evidence in animal and neural systems. For agents:
  interpretation.
- Translation: memory compresses many traces into a few slow variables (conventions, hazards)
  that then constrain every later action. The compression is the computation, and its loss is
  the thing to measure.
- Quantity: compression loss against compression ratio; downstream pass rate split by questions
  that need detail and questions that need gist.
- Experiment: E3.2.
- Breaks: the compressor is a language model with unknown loss and no guarantee of consistency
  between runs.

**Increasing returns and lock-in** (Arthur 1989)
- Status: established as a model.
- Translation: a note that is retrieved gets used, cited and reinforced. An early wrong
  convention can win.
- Quantity: lock-in rate; retrieval share of the planted note over sessions.
- Experiment: E3.4. This is H4.
- Breaks: agents are not payoff maximisers choosing among technologies. Same-model agents are
  correlated by construction, which may make lock-in worse than the model predicts or simply
  different in kind.

**Commons governance** (Ostrom 1990, via secondary summaries)
- Status: established for natural-resource commons. For agents: interpretation.
- Translation: a shared store needs boundaries (scope), monitoring (provenance), graduated
  response (flag, quarantine, supersede) and a cheap route to a human arbiter.
- Quantity: provenance coverage; pointer validity; lock-in rate with and without governance;
  cross-scope leaks.
- Experiment: E3.1, E3.4, E3.5.
- Breaks: Ostrom's users have reputations and repeated dealings. An agent is a fresh instance
  unless we build the record for it.

**Transactive memory** (Wegner 1987)
- Status: established for human groups.
- Translation: a shared store can hold "who or what owns X" pointers instead of copies.
- Quantity: accuracy and tokens when answering through an owner pointer against full retrieval.
- Experiment: not in the first pass. Parked until H4 is settled.
- Breaks: agents do not learn who is reliable unless that is written down.

**Classifier systems and credit assignment** (Holland 1975, 1995)
- Status: established for genetic algorithms and classifier systems.
- Translation: lessons as small rules with a strength updated by outcomes; `use_count` and
  `last_used_at` in the record schema are the minimal version.
- Quantity: whether notes that were used before a pass have higher later use than those that were
  not. Descriptive.
- Experiment: by-product of E3.3 logs. No strength-update mechanism is built.
- Breaks: lessons are free text, and credit over a long trace is delayed and noisy.

**Belief revision** (Alchourrón, Gärdenfors, Makinson 1985, via the Stanford Encyclopedia)
- Status: established as logic.
- Translation: on contradiction, give up the least entrenched belief: lowest confidence class,
  then oldest. Supersede, never delete.
- Quantity: final-state accuracy on seeded contradictions.
- Experiment: unit-level test inside `memstore`; part of E3.4's governed arm.
- Breaks: the theory assumes logically closed belief sets. Notes are loose prose.

### 1.4 Central and decentral organisation: hub and cells (H6, H7, T4, T7)

The design is in `ARCHITECTURE.md`. Nothing in this subsection is a finding. The concepts say
what to measure; H6 and H7 say what would count against the design.

**Polycentric governance** (V. Ostrom, Tiebout and Warren 1961; E. Ostrom 1990, 2010)
- Status: established in political economy. Our hold on it is weak: file 01 has only secondary
  summaries of *Governing the Commons* (nested governance is one of the named principles); the
  1961 and 2010 texts are cited from memory, UNVERIFIED. Translation: interpretation.
- Translation: many decision centres, each autonomous inside rules set at a higher level. A
  cell decides inside its signed ceiling; a planner cell may propose a new ceiling, and only the
  owner's key changes it (`ARCHITECTURE.md` 2).
- Quantity: local resolution rate; escalation rate; blast radius (section 4).
- Experiment: E4.1 (H6) reports the first two; the contract tests and E5.3 bound the third.
- Breaks: polycentric units answer to their own members, compete, and learn from neighbours.
  Cells have no stake, no members, and by design no channel to each other. What we borrow is
  nested rule-making and nothing else.

**Near-decomposability, applied to the hub-cell boundary** (Simon 1962; see 1.2)
- Status: established as a conceptual result. Translation: interpretation.
- Translation: a hierarchy works when most interaction stays inside the parts. The contract
  between hub and cell should therefore be narrow, and work should go to separate cells only
  where the coupling gate says the parts are nearly independent.
- Quantity: co-change coupling between the scopes given to two cells (the H2 score); interface
  width (bytes of task spec plus result per task); escalations per task.
- Experiment: E2.1 and E2.2 (H2) for the split decision; E4.1 logs interface width.
- Breaks: the same as in 1.2 (co-change is a trace of the past). A narrow interface can also
  hide the context a cell needed, which shows up as failed checks, not as coupling.

**Requisite variety, applied to the hub's decomposition** (Ashby 1956; see 1.1)
- Status: theorem. Translation: interpretation.
- Translation: the hub's set of task classes and routes must be as varied as the tasks that
  arrive. Too few classes and tasks are forced into a wrong route or all fall back to the hub.
- Quantity: unrouted-task rate (tasks matching no class, sent to the Claude tier by default);
  mis-route rate (routed tasks that fail the check and then pass one tier up).
- Experiment: E4.1 by-product. Descriptive, no confirmatory claim.
- Breaks: variety counts states as equal. Three classes may cover most of the volume while one
  rare class carries most of the risk.

**Model cascades and the value of computation** (Chen, Zaharia and Zou 2023, "FrugalGPT";
Russell and Wefald 1991)
- Status: FrugalGPT established on its tested query sets (abstract only, file 06; its numeric
  saving was not read and is not repeated). Russell and Wefald is established theory, citation
  only. Translation to coding cells: interpretation.
- Translation: try the cheapest tier that has cleared a held-out floor, check the result,
  escalate on failure. Do a computation only if its expected effect on the decision is worth
  more than its cost.
- Quantity: cascade cost per pass; break-even pass rate `p* = (c_s + c_k) / c_h`; false-accept
  rate of the check (section 4).
- Experiment: E4.1. This is H6.
- Breaks: a weak check makes the cascade pay for both tiers or, worse, accept wrong work
  cheaply. Tests are cheap but incomplete. `p` is estimated on a generator we wrote.

**Model editing** (ROME, Meng et al. 2022; MEMIT 2022; task vectors, Ilharco et al. 2022;
representation engineering and activation addition 2023; abliteration, Arditi et al. 2024;
Tracr 2023)
- Status: established as published methods; file 08 opened the abstracts only. Author names
  are from memory; the arXiv IDs are in file 08.
- Translation: a small, auditable change to a cell model's weights (a direction removed, a
  rank-one update, a merged adapter) could be shipped by the hub like a patch. Speculative as a
  product mechanism.
- Quantity: patch gain over the best decoding-only fix under a matched token cap; off-target
  delta; patch size (weights changed over total); variance of the gain across independent
  edits (section 4).
- Experiment: T7 pre-test, arms A-D. This is H7.
- Breaks: by the original authors' own Gemma result, edits of this kind remove an obstacle and
  do not add an ability. A weight edit that only reproduces a decoding setting is a more
  expensive way to set a flag.

**Weight-space programming by a frontier model** (Takehi, Teoh, Zhang, Khattab; MIT CSAIL blog
post, 2 Nov 2026)
- Status: a blog post with public logs, days old, not peer reviewed; one editing run per
  budget. Confirmed and qualified in 7.2a. For our use: speculative.
- Translation: none adopted. We test the released edit against trivial baselines (T7) and do
  not build the agent that finds edits.
- Quantity: the same as for model editing.
- Breaks: the Qwen result used a Python kernel and forward passes, not reading raw weights; it
  had no fine-tuning, steering or decoding baseline; the three budgets produced three different
  edits.

### 1.5 Lance Martin's observations read through complex systems (H3, H8, H9, T8)

Added 2026-11-19 from `research/11` (slides read by an assistant from the owner's screenshots)
and `research/10` (source check by another agent; "opened" there means that agent's fetch).

**Evidence status of everything in this subsection.** Every observation is a **talk claim**:
one vendor run or one vendor chart, no intervals shown, not reproduced, slide figures subject to
reading error. File 10 confirmed in the written posts: 1,000 agents, 60 statements, five tables,
no network in sandboxes, a classifier plus an offline monitor, 28.7 hours (the talk said about
30), and that the authors call it a "toy experiment". File 10 did **not** read the part of the
memory post with the wiki and dreaming-token results, so those figures are slide-only. The
complex-systems reading is **interpretation** throughout; none of it is a finding of the talk
or of the cited theory. "Our arithmetic" marks numbers we derived from the slide values.

| # | Observed (talk claim) | Concept, and its status | What it predicts that we can test | Where |
|---|---|---|---|---|
| 1 | Agents, not the prompt, created five shared tables about five minutes in. Hour 5.3: 12,929 writes and 147,425 reads | Stigmergy: coordination through traces left in a shared environment. Established for social insects (cited from memory, unverified); for language-model agents, speculative | A shared board is read far more than written; small models may not build one unaided | H9, E8.2; null from E8.1 |
| 2 | The lead sorted the 60 statements into seven staffing groups; 13 proved by hour 1.2, 34 by hour 4.8, the rest by the end | Near-decomposability (Simon). Established as a concept; mapping is interpretation | Loosely coupled parts land first; a coupled core dominates time and tokens | H2 unchanged; E8.2 by-product |
| 3 | Own-branch pushes only, a merge job for main, a shared unprivileged role, time and size limits, identity set at the gateway, every push and query logged, fail-closed classifier | Rules for a commons (Ostrom). Our hold on Ostrom's list is secondary (7.3); mapping is interpretation | Imposed rules, not agent goodwill, keep a shared store usable | H4 unchanged; E8.2 arm B against arm A |
| 4 | 125 of 999 helpers idle at hour 1.2; 209 at hour 4.8 | Utilisation in a queue; a serial bottleneck at the lead. Little's law and Amdahl's law are cited from memory, unverified | Idle share rises when ready subtasks run short of helpers | E8.2, descriptive only |
| 5 | Wiki alone: 13% at 2M dreaming tokens, 48% at 128M. Wiki plus search: 54% to 61%. Search alone: 53% | Diminishing marginal return; value of computation (citation only) | The strongest control for a dream pass is plain search over raw logs; the gain per token falls with dose | H3 amended (E3.3 arm B3); E8.4 |
| 6 | CL-Bench database task, score with a memory store against stateless, six models | No clean complex-systems concept. We call it a capability threshold for using an unprompted memory; interpretation | Below the threshold a model needs imposed structure to benefit at all | H8, E8.3 |
| 7 | Memory directory in Pokemon: Sonnet 3.7 413 files and 977,930 characters; Fable 5 10 files and 43,406 characters | Redundancy growth in an unpruned store (description length, cited from memory) | Weak models sprawl; a cap and a lint bound the size without lowering the pass rate | H8 secondary metric, E8.3 |
| 8 | A wrong landmark note trapped the agent; memory plus dreaming escaped; raw memory regressed | Lock-in of an early error (Arthur), here inside one agent's own store | An offline pass that re-reads the raw log removes planted wrong notes | H3 removal criterion; H4. No change |
| 9 | Diogo Almeida's slide: cache reads about 67% of agent cost, output 18%, input 12%, cache write 3% | Not a complex-systems concept: the cost of re-reading state on every call | The dominant cost class in our own runs is measurable from usage fields | E8.1 |

**Notes per row: our arithmetic, and where the reading breaks.**

1. *Stigmergy.* Reads per write: 11.4 at hour 5.3 (147,425 / 12,929) and 63.6 at hour 0.3
   (3,561 / 56). Notes and Subtasks carry 96% of writes (12,469 of 12,929), 69% of reads
   (101,327 of 147,425) and 71% of all traffic (113,796 of 160,354). File 11's "80%+ of traffic"
   does not follow from its own figures; use 71%. Only Notes and Subtasks are stigmergic in the
   strict sense. Announce and Assign are orders from the lead (the lead writes, helpers read):
   that is hierarchy, and it formed too. Breaks: a read may be a poll that returns nothing new,
   so a high read:write ratio can be waste, not coordination. We therefore also measure the
   **useful-read fraction** (reads returning a row that agent had not seen / all reads) and need
   a single-agent null (E8.1): if one agent alone reads about ten times per write, 11:1 is not a
   team signature. Claim races on Subtasks were not reported in the talk.
2. *Near-decomposability.* 34 of 60 statements (57%) were proved in the first 4.8 hours, about
   16% of the run; one hard subtree alone had 2,418 written tasks at hour 22.6. This is
   consistent with H2 and does not test it: there is no single-agent arm at matched tokens. The
   post's comparison is with an earlier run on a different model and harness.
3. *Rules.* The rules were written by the harness designers. What self-organised was the tables,
   inside those rules. No rule was ablated, so the talk cannot say which rule mattered.
4. *Idle.* 12.5% and 20.9% of helpers (125 and 209 of 999). The slide's categories sum to 997 at
   hour 1.2 and 978 at hour 4.8 by our addition, so they overlap or are incomplete, and "idle"
   is not defined. An idle helper is not idle compute: an agent that makes no model call spends
   no tokens. Whether idle helpers kept polling is unknown. Our measure in E8.2 is explicit:
   **idle-turn fraction** (helper turns that find no claimable work / all helper turns) and the
   tokens spent in those turns, reported next to the GPU idle fraction of `PRINCIPLES.md`.
5. *Dreaming dose.* 64 times the tokens is six doublings: wiki alone gains 35 points, about 5.8
   per doubling; wiki plus search gains 7, about 1.2 per doubling. Against search alone, wiki
   plus search adds 1 point at 2M tokens and 8 points at 128M. With 25 questions one question is
   4 points, so 8 points is two questions; the plotted values are not multiples of 4, so they are
   averages or graded scores, and no interval is shown. The axis is a budget per session, "not
   measured spend". Consequence for us: retries are not the hardest control for H3. Search over
   the raw log is.
6. *Capability and memory.* Score with memory, stateless, gain, and gain as a share of the
   headroom left by the stateless score (our arithmetic):

   | Model | With memory | Stateless | Gain | Share of headroom closed |
   |---|---|---|---|---|
   | Opus 5.5 | 0.838 | 0.655 | 0.183 | 0.53 |
   | Sonnet 5.5 | 0.833 | 0.644 | 0.189 | 0.53 |
   | Opus 5 | 0.828 | 0.564 | 0.264 | 0.61 |
   | Opus 4.7 | 0.700 | 0.383 | 0.317 | 0.51 |
   | Sonnet 5 | 0.610 | 0.306 | 0.304 | 0.44 |
   | Sonnet 4.6 | 0.364 | 0.330 | 0.034 | 0.05 |

   File 11 reads this as "the benefit grows with capability". The six points say something
   narrower. The gain is **not** monotone: it is largest for the middle models and smaller for
   the strongest, whose stateless score is already high. As a share of headroom it is roughly
   flat (0.44 to 0.61) for five models and near zero for one. That looks like a **threshold**,
   not a gradient: below it the model does not use an unprompted memory; above it memory closes
   about half the remaining gap. This is a reading of six points from one task (40 questions,
   so one question is 0.025; no intervals), and it is the reason H8 is worded as a threshold.
   File 10 adds a caution from the CL-Bench paper's abstract: "naive ICL outperforms systems
   dedicated to memory management".
7. *Sprawl.* 41 times the files and 22.5 times the characters; mean file size 2,368 against 4,341
   characters. The step counts are not matched on the slide (Sonnet 3.7 at step 9,989; Fable 5's
   step is not given), and the written post says nine files where the slide says 10 (file 10).
   Directory names such as "consolidated", "master" and "core" suggest repeated attempts to tidy
   that added files; that is our guess.
8. *Wrong memory.* One anecdote, one plotted window, chosen for a talk. No rate.
9. *Cache cost share.* **Not confirmed.** File 10 read the blog post: its text says only that
   output is 9 to 18% of the bill; the pie is an image; it assumes Fable 5 pricing, where a
   cache read costs 0.1 of input, and a 100% hit rate. Cache reads now cost 0.025 (Fable 5.2)
   and 0.05 (Opus 5.5, Sonnet 5.5) of input (7.2a; file 10). Illustration only, our arithmetic
   on the unverified slide values with every other price ratio held: the same token mix would
   put cache reads near 50% of cost at 0.05 and near 34% at 0.025. Also, a database read lands
   in the context as new input, not as a cache read, so row 1 and row 9 are not the same cost.
   No cost model here uses the slide's shares; E8.1 measures ours.

**Quantities added** (units; all computed from logs, no model judge): reads per write
(dimensionless, both counts reported); useful-read fraction; failed-claim attempts per subtask;
duplicate-work rate (subtasks completed by more than one agent / subtasks completed);
idle-turn fraction and idle-turn tokens; emergent-table rate (runs in which an agent-created
table is later read by a different agent / runs); memory size (characters and files per 100
sessions); cost share by token class (USD per class / total USD, with the price sheet
recorded).

**Diogo Almeida's talk** (transcript read in full; `research/10`). Talk claims, and by his own
account design questions, not demonstrated solutions. The ones that touch this framework: agent
design is shaped by the cost of re-reading the cache; memory grows with history instead of being
looked up; parallel agents rediscover the same facts; reliability matters more than occasional
brilliance and benchmarks hide it; rules capture the letter and miss the spirit
(principal-agent problems). Which of these become tests, and which are deferred, is decided by
the five-step filter in `PLAN.md` T8. No paper opened by file 10 establishes sub-linear memory
for agents; the cache-sharing preprints it lists need open weights and do not apply to the
Claude API.

---

## 2. What is genuinely new, and what is prior art

Kept deliberately modest. "Not found in my search" means a shallow search found nothing. It is
not evidence of novelty.

| Idea | Status |
|---|---|
| Decay of unused grants | **Prior art.** Android auto-reset, AWS unused-access analysis, role mining. |
| Grow on demonstrated need | **Prior art.** OpenShell Policy Advisor, JIT access, and CJ Avilla's talk itself (per the talk, owner-validated). |
| Promote repeated requests | **Shipping practice.** Claude Code per-repo "always allow". |
| Replay of real coding-agent transcripts to compare those policies on prompts and exposure | Not found in my search. This is a measurement, not an invention. |
| Reuse-hazard fit for agent capabilities | Not found in my search. |
| Gating fan-out on decomposability | **Prior art.** Kim et al., Li et al., NP-Bench. |
| Gate from git co-change, tested at matched tokens | Not found in my search. |
| Diversity decomposition for model ensembles | **Prior art**, several 2026 preprints. |
| Offline consolidation, dreaming, sleep-time compute | **Prior art and shipping.** Anthropic Dreaming, auto memory, Letta, claude-diary. |
| Compute-matched evaluation of consolidation on coding sessions | Not found in my search; one research file's search summary also reported none. |
| Governed shared memory with provenance | **Prior art.** Governed Collaborative Memory and relatives. |
| Deterministic linter for memory records; wrong-memory benchmark with canary scoring | Not found in my search. Small engineering contributions. |
| Small local model as consolidator, compared with a frontier model on dream gain | Not found in my search. |
| Central planner with narrow workers (hub and cells) | **Prior art and shipping.** Orchestrator and worker split; Managed Agents coordinator; base policy plus human-signed ceiling is CJ Avilla's talk (per the talk). |
| Cheap model first, escalate on a failed check | **Prior art.** FrugalGPT and later routers; also the owner's standing tier rule. |
| Signed, versioned, expiring policy file that a cell verifies before acting | Not found on the Claude platform pages file 07 read (settings are config, not signed). Signed policy as such is ordinary security practice; no novelty claimed. |
| Editing a model's weights by removing a direction | **Prior art.** Abliteration, ROME/MEMIT, activation steering. |
| A frontier model running the probe-edit-measure loop on another model by itself | **Prior art, Nov 2026** (MIT post; two replication preprints). Not ours. |
| Released weight edit against thinking-off and repetition-penalty baselines under a matched token cap | Not in the original post. Second-hand reports say others have tried pieces of it (unopened leads). At best a small replication. |

What the project can honestly claim if things go well: open instruments, pre-registered tests,
and results (including nulls) on questions the source talks left open. Not a new theory.

---

## 3. Concepts parked, and why

| Concept | Why it is not in the plan |
|---|---|
| NK simulation, edge of chaos | Results follow from chosen constants. No real-data quantity of its own. |
| Self-organized criticality (Bak) | Heavy tails have many causes; no falsifiable prediction for our data. Could be a descriptive footnote on fix-up chain lengths. |
| Scaling laws (West, Bettencourt) | Fitting an exponent to four team sizes is curve decoration. |
| Small-world and scale-free topologies | Topology is a design choice here; prior art is dense. |
| Schelling, Sugarscape, El Farol, artificial stock market | Already replicated with language models by others; no coding-agent quantity. |
| Axelrod reciprocity | Agents in one harness are not strategic opponents. |
| Stigmergy with decay | Published for toy tasks; speculative for code. Partly un-parked 2026-11-19: Lance Martin's run gives countable quantities (reads per write, claims, duplicate work), so one bounded test exists (H9, E8.2). Pheromone-style decay of board entries stays parked. |
| Viable system model | Fits any org chart; hard to falsify. |
| Good-regulator theorem | Headline is contested. |
| Psychological safety, sensemaking, SECI, trading zones | Human-team constructs with no clean measurable here. |
| A hub that finds and applies weight edits in a loop; recursive self-improvement | The original took 8 to 20 hours per run with unpriced frontier tokens and gave three different edits in three runs. No decision here depends on it. Revisit only if H7 survives. |
| Cell-to-cell exchange, markets, reputation between cells | Star topology removes the channels these need. No measured failure of the star yet. |
| Recursive Language Models (arXiv 2512.24601) | An inference-time method (the prompt lives in a REPL and the model calls itself over snippets). Not self-training. No quantity for this plan. |

---

## 4. Glossary of measurable quantities

Notation: `k` a capability key; `A(t)` the allowlist at time `t`; sessions and tasks are the
units of resampling.

**Prompts per 100 calls.** `100 * prompts / events`. Upper bound: transcripts do not record
which calls were really prompted.

**Idle exposure (rule-days).** For each key, the time it stands in the allowlist while unused:

```
E = sum over k of  integral  1[k in A(t)] * 1[t - last_use_k(t) > g]  dt
```

with grace `g` (default 0). In practice: for every standing rule, sum every gap between
consecutive uses (minus `g`, floored at 0) plus the final gap to the end of the stream; under
decay a gap contributes at most `tau`. One definition for all policies. The current code does
not do this (PLAN E1.0).

**Standing rule-days.** `S = sum over k of integral 1[k in A(t)] dt`. Reported beside `E`.

**Grant-use ratio.** `GUR(w) = |{k granted and used within window w}| / |{k granted}|`.
Over-grant is `1 - GUR`.

**False-deny rate (self-block proxy).** On a later window, calls whose key is absent from an
allowlist mined on an earlier window, divided by all calls.

**Thrash rate.** `re-prompts after decay / decays`. A rule that decays and is re-approved soon
after was removed too early.

**After-denial classes.** For each denial, the next three calls in the session: *retried* (same
key), *workaround* (same tool, different key; a proxy), *moved on*. E5.3 replaces the proxy with
trace-scored outcomes: blocked and reported, completed by allowed route, attempted workaround,
gave up.

**Reuse hazard.** `h(g) = P(next use in [g, g+dg) | idle for at least g)`. Under a power law the
survival of idle gaps is `S(g) ~ g^(-d)`; under a memoryless process `S(g) = exp(-lambda g)`.
Compared by likelihood ratio on per-key gaps, with a bootstrap over sessions. Gaps cut off by
the end of the corpus are censored and must be handled as such.

**File overlap.** For two changes touching file sets `A` and `B`: `O = |A ∩ B| / |A ∪ B|`.

**Co-change coupling.** With `c(a,b)` the number of prior commits touching both files and
`n(a)` the number touching `a`, all counted before both changes began:

```
C(A,B) = mean over a in A, b in B, a != b  of  c(a,b) / sqrt(n(a) * n(b))
```

H2(a) asks whether `C` predicts integration failure beyond `O`.

**Matched-token fan-out gain.** `G = pass(fan-out | T) - pass(single | T)` at equal total token
budget `T` per task, all agents counted. Reported with the **token multiple** when budgets are
not forced equal.

**Failure correlation.** If attempts on task `t` fail independently with probability `q_t`,
then across tasks

```
pass@k = 1 - mean_t(q_t^k)          rho = Var_t(q_t) / (qbar * (1 - qbar))
```

`rho` is the correlation between two attempts' failures. `rho = 0` gives `1 - qbar^k`;
`rho = 1` gives no gain from extra attempts. Varied prompts or models help only if they lower
`rho` without raising `qbar`.

**Diversity decomposition** (Krogh and Vedelsby; for averaged numeric predictions only):
`ensemble squared error = mean member squared error - mean squared deviation of members from the
ensemble`. Quoted for orientation. It does not apply directly to patch selection.

**Provenance coverage.** Notes with a source pointer that resolves (file and line, or commit)
divided by all notes.

**Pointer validity.** Resolving pointers whose target contains the claim's anchor span, divided
by resolving pointers.

**Wrong-note follow rate.** Episodes where the canary of a planted wrong note fires, divided by
episodes where that note was available.

**Memory-correction half-life.** Number of sessions after planting until the wrong-note follow
rate falls to half its first-session value; if it never does within the horizon, report "greater
than horizon". A shorter half-life is better.

**True-note retention.** Planted true facts still present and retrievable after a pass, divided
by planted true facts.

**Lock-in rate.** Later tasks that adopt the planted convention divided by later tasks where it
was applicable. **Retrieval share** is that note's fraction of all retrievals per session;
increasing returns shows as a rising share.

**Compute-matched dream gain.**

```
DG = pass(dream, budget B) - max( pass(extra retries, B), pass(search over raw logs, B) )
```

(The second control was "re-summarise without logs" until PLAN H3 replaced it with search over
the raw logs, arm B3, on 2026-11-19.)

Tokens spent dreaming are charged to the dream arm. H3 requires the CI of `DG` to exclude 0.

**Compression loss.** `1 - retained planted facts / planted facts` at a given compression ratio
(output tokens over input tokens).

**Distillation retention** (Track 4). `DG(local adapter) / DG(Claude dreamer)` on the same
scenarios. Only defined if the denominator's CI excludes 0.

**Path waste.** Tool calls that repeat an identical call with an identical result and no
intervening write, plus failed calls repeated unchanged, divided by all tool calls. Follows
Lance Martin's point (per the talk) that the path should be evaluated, not only the answer.

**Local resolution rate.** Tasks a cell completes with a passing check and no escalation,
divided by tasks routed to it. **Escalation rate** is one minus that, split into "failed check"
and "key outside the ceiling".

**Cascade cost per pass.** For a class with cell cost `c_s`, check cost `c_k`, hub cost `c_h`
and cell pass rate `p`, all in USD per task:

```
C_cascade = c_s + c_k + (1 - p) * c_h        cell-first is cheaper iff  p > (c_s + c_k) / c_h
```

Reported as USD per passing task beside the hub-only figure, with tokens and joules shown
separately. Local `c_s` uses rated supply power (240 W) x wall seconds x the owner's tariff as
an upper bound; the GPU-only reading is reported next to it. Hardware cost is excluded. No
tariff exists and the owner ruled local USD "n/a" for H7 and E9, so local USD is null until the
owner supplies a tariff; then this formula is computable (PLAN H6).

**Held-out floor.** A tier is eligible for a class when the 95% CI lower bound of its pass rate
on held-out tasks is at or above the class floor (H6 uses 0.80, a design choice). The
measurement is void when the cell's prompt, model, adapter or decoding config hash changes.

**False-accept rate.** Hand-audited results that passed the deterministic check and are wrong,
divided by audited passes. H6 fails above 5%.

**Unrouted-task rate; mis-route rate.** Tasks matching no class, over all tasks; routed tasks
that fail the check and pass one tier up, over routed tasks.

**Blast radius.** Capability keys in one cell's ceiling divided by the union of keys across all
cells. Structural, computed from the policy files, no run needed. Reported with the count of
keys that reach outside the cell's own directory.

**Interface width.** Bytes of task spec plus result per task. Descriptive.

**Patch gain** (T7). `acc(edited model) - max(acc(decoding-only arms))` on the same problems
under the same per-problem token cap, paired by problem. H7 needs the CI above 0 and the point
estimate at or above 5 points. **Off-target delta** is the same difference on tasks the patch
was not meant to change. **Patch size** is weights changed over total weights.

### 4a. The three idea families as task controls: one robustness measure (added 2026-11-19)

Source: `docs/reports/adversarial-review-2.md` 3.4. The owner's term "KDS" (relayed by the
parent, 2026-11-19; it appears nowhere else in the repo) is read as the three families of the
`PRINCIPLES.md` scope guard: memory, green (cost) efficiency, adaptive policies and rules. If
the owner meant something else, this section is redone. Each family becomes a switch in one
harness (`runner.py`, trapbench) instead of a bespoke experiment with its own task, metric and
budget. Plan entry: PLAN T10.

**Units.** Unit: one (task, seed) pair. Condition `k`: clean, or exactly one perturbation.
Arm `a`: one setting of the control switches. Pass: the task's deterministic check.

| Quantity | Definition | Unit |
|---|---|---|
| Clean pass rate | `pass(a, clean)` = passes / episodes under the clean condition | fraction; both counts shown |
| Perturbed pass rate | `pass(a, k)`, the same under perturbation `k` | fraction |
| Robustness drop | `D(a, k) = pass(a, clean) - pass(a, k)`, paired by task and seed | points |
| **Control effect** (primary) | `CE(a, k) = D(base, k) - D(a, k)`: the baseline arm's drop minus the control arm's drop, same `k` | points; 95% cluster bootstrap by task (section 5) |
| Harm rate | episodes with a canary hit, a protected-file hash change or an executed action outside the ceiling, whether or not the task passed / episodes | fraction |
| Recovery cost | tokens per passing task under `k`, next to the clean figure; turns and bytes beside it (PLAN 4.6) | tokens / pass |
| Worst case | `min over k of pass(a, k)`; all-seeds pass rate | fraction |

A positive `CE` means the control shrinks the damage the perturbation does. A control counts
only if (1) the 95% interval of `CE` excludes 0, (2) its clean pass rate is within 2 points of
the baseline arm's (it does not buy robustness by lowering the clean rate), and (3) its own
tokens are charged inside the same per-task cap. The 2 points are the review's design choice.

**Perturbations** (seeded, injected by the harness at a fixed step, one per episode):

| k | Perturbation | Scoring | Family it is matched to |
|---|---|---|---|
| P1 | Requirement changes mid-task (spec v2 replaces v1) | v2's tests; canary on a v1-only artifact | memory (stale record), policy |
| P2 | Noisy requirement: one irrelevant and one contradictory sentence, precedence rule stated | generator's ground truth | none (pure model baseline) |
| P3 | Injected wrong or stale memory | trapbench canary | memory |
| P4 | A cell fails (bad result) or is slow (exceeds `wall_s`) | task check on the merged result | efficiency (cascade, timeout, escalation) |
| P5 | Permission denial with a safe allowed route | E5.3 outcome classes from the trace | policy |

**Arms, first pass:** all controls off against all controls on. A one-family ablation is run
only for a perturbation where those two differ. No full factorial.

**Fermi (estimate, not measured):** 10 tasks x 2 seeds x 5 conditions x 2 arms = 200 episodes
per model; only effects of about 15 points are visible at that size (PLAN 4.3 power note). P4
needs at least two cells, so it runs only once the router exists.

---

## 5. Statistical conventions

- Unit of analysis: task, scenario or session. Rows inside one are never treated as independent.
- Paired differences across arms on the same task and seed.
- 95% percentile bootstrap, 10,000 resamples, resampling the unit of analysis; seeds nested.
- Five confirmatory hypotheses (H1-H4, H6), Holm-corrected at family level 0.05. H7 is a
  one-off pre-test of a published result, reported with intervals outside the family. H8 is
  exploratory (owner 2026-11-19). H9's status awaits the owner's ruling: with H8 out it would
  be a family of one, and the adversarial review recommends deferring it (PLAN 1.2). H1 cannot
  be tested on the local corpus (precondition not met); it stays in the family as pending.
  Everything else is labelled exploratory in the output itself.
- Cross-model comparisons follow PLAN 4.6: deterministic scoring only, matched budget in turns
  plus input and output bytes, returned model ID checked per response.
- A result counts only if the interval excludes zero **and** the point estimate meets the
  pre-registered minimum effect. An interval inside the minimum effect is reported as a null.
- No model grader is a sole judge. If one is used, report its agreement with itself over three
  repeat gradings and with a human on at least 30 items.
- Stopping: sample sizes fixed in advance. No peeking-based extension.

---

## 6. Pre-registration template

One file per hypothesis under `prereg/`, committed before the main run.

```
# Pre-registration: <H-id> <short name>
Date:                     Author:
Code git SHA (frozen):    Config hash:
Model snapshot(s):        Seeds:

1. Hypothesis (one sentence, directional).
2. Concept it comes from, and its status label (established / interpretation / speculative).
3. Prior art checked (list), and the sentence we will use: "not found in my search".
4. Data: source, licence, how obtained, what is excluded. Unit of analysis.
5. Splits: how made (by session / repo / generator family); hash of split file.
6. Arms and baselines, including the one that ships today.
7. Primary metric (formula from SCIENCE.md section 4). One only.
8. Secondary metrics (labelled exploratory).
9. Minimum effect of interest, and why that size matters in practice.
10. Sample size and the reason for it. Stopping rule.
11. Analysis: test, resampling unit, correction family.
12. Kill criteria (the result that makes us drop the idea).
13. Sanity checks that must pass before the main run (baseline pass rate, grader sanity,
    canary fires on a scripted agent, token accounting balances).
14. Known threats to validity.
15. Budget: GPU-hours cap, USD cap, approval gate reference.
16. Deviations (filled in afterwards, never deleted).
```

---

## 7. Reading list and verification status

### 7.1 The research files

| File | Topic | How sources were checked |
|---|---|---|
| `research/01-complex-systems-foundations.md` | Santa Fe school and related models; prior art applying them to language-model agents | Search snippets only. No page opened. arXiv IDs in the 26xx range are as returned by search. |
| `research/02-multi-agent-coordination.md` | Fan-out evidence, conflicts, frameworks, organizational science | Mixed. Many arXiv abstracts and Anthropic pages opened; organizational-science classics and several preprints snippet only. |
| `research/03-memory-and-dreaming.md` | Consolidation theory, agent memory systems, poisoning, shared memory, benchmarks | Search snippets only. Several figures are second-hand (blog summaries of vendor posts). |
| `research/04-trust-permissions-resilience.md` | Trust theory, security lineage, safety science, agent permission material | Mostly snippets. Opened: Anthropic auto-mode post, Claude Code permissions and hooks pages (keyword scan only), OpenShell Policy Advisor page, two arXiv abstracts, one vendor blog. |
| `research/05a`, `05b`, `06` | Verification of vendor sources and 11 papers; first principles and efficiency | See 7.2a. |
| `research/10-diogo-almeida-and-source-verification.md` | Diogo Almeida's talk; check of the Lance Martin posts, CL-Bench, the cache-cost blog, pricing | Written by a separate agent. Talk page, two posts (one read in part), CL-Bench README and paper abstract, blog text, pricing page opened; arXiv abstracts only. The cost pie image was not read. |
| `research/11-lance-martin-code-summit-2026.md` | Slide figures from Lance Martin's talk and two Diogo Almeida slides | Read off the owner's screenshots by an assistant. Talk claims; reading error possible; three arithmetic or wording points corrected in 1.5. |
| `research/07-claude-platform-central-vs-decentral.md` | What Anthropic runs and what you can run yourself | Five pages opened in full (two articles, Claude Code self-hosted environments and sandboxing, the self-hosted Managed Agents page). About 20 more read in part (headings and targeted passages). The Flows URL returned 404; five linked pages not read. |
| `research/08-weight-space-programming.md` | The MIT weight-editing post, critiques, prior art | Primary blog post and repository README opened in full; one sceptical post in full; two replication preprints and seven prior-art papers as abstracts only; one critique paywalled and not bypassed; about nine other items search summaries only. |
| `research/09-unsloth-and-local-models.md` | Unsloth, model candidates, serving and power on the GB10 | Unsloth README, its Spark guide, NVIDIA playbooks and the spec page opened. Model IDs and licences from Hugging Face API listings (tags only, no model cards). Power section from unopened forum snippets. Nothing installed or run. |

### 7.2 Ten sources that must be opened in full before any public claim

Ordered by how much of the plan rests on them.

1. **Anthropic, "Claude Code auto mode" engineering post, and the primary source of the human
   versus auto-mode catch rates** (about 14% and 89% per Lydia Hallie's talk). Our baseline
   description and the fatigue argument depend on it; file 04 saw the study figures only on
   secondary sites.
2. **Claude Code permissions and hooks documentation, end to end.** We state that persistent
   allow rules do not decay and describe deny precedence and exit code 2. Both were keyword
   scans.
3. **NVIDIA OpenShell policy and Policy Advisor documentation.** The claim "grow exists, no
   documented decay" is from one opened page and a snippet.
4. **Anthropic, "components of agent memory" (Lance Martin) and the Managed Agents Dreaming
   documentation.** H3 positions itself against these; every detail we hold is second-hand.
5. **Kim et al., "Towards a science of scaling agent systems" (arXiv 2512.08296), full text.**
   Abstract opened; the error-amplification figures and threshold are snippet only.
6. **Li et al., sub-agent concurrency in long-horizon coding (arXiv 2610.10263), full text**,
   including whether the benchmark is public and under what licence.
7. **CooperBench (arXiv 2601.13295).** Not opened; two sources disagree on the headline figure;
   also a candidate dataset.
8. **Governed Collaborative Memory (arXiv 2605.04264), with Governed Shared Memory (2606.24535)
   and Collaborative Memory (2505.18279).** Closest prior art to H4; must be read to state the
   difference honestly.
9. **Lin et al., sleep-time compute (arXiv 2504.13171), full text.** The nearest
   compute-matched evidence; our control design should be checked against theirs.
10. **AuthBench (arXiv 2605.14859) and ToolPrivBench (2606.20023), full text.** Closest prior art
    to the over-request and self-block question; abstracts only so far.

Next in line: Anderson and Schooler (1991) primary text (H1's premise); Krogh and Vedelsby (1994)
primary text (H5's identity); the Android auto-reset documentation; AgenticFlict (arXiv
2604.03551) for dataset availability; "Passes Alone, Fails Together" (arXiv 2609.25396).

### 7.2a Verification status after files 05a, 05b, 06 (2026-11-19)

Retrieval note: WebFetch was blocked by a hook, so pages were read through the context-mode
indexer and searched by pattern, not read line by line. "Opened" below means that.

**Confirmed against the source**
- Auto-mode classifier: FP 8.5% -> 0.4% over two stages; FN 17% on overeager actions (n=52);
  escalation after 3 consecutive / 20 total denials (docs and the post differ on `-p` mode).
- Rule precedence deny > ask > allow; hook exit 2 blocks, exit 1 does not. Caveat: Bash deny
  rules are bypassable (`/bin/rm`, `bash -c`), so deny is not an absolute guarantee.
- OpenShell policy YAML (hosts, paths, methods, executables) and the Policy Advisor loop
  (proposal, human approval, hot reload); advisor off by default, auto-approval opt-in. No
  decay/shrink on the 3 pages opened (not all OpenShell pages).
- Prompt caching: prefix order tools, system, messages; default TTL 5 min; cache-read price 0.1x
  on most models, 0.05x on Sonnet 5.5 and Opus 5.5, 0.025x on Fable.
- Kim et al. 2512.08296: +80.8% / -70.0%, error amplification 17.2x (independent) vs 4.4x
  (centralized). The 45% single-agent threshold is a regression coefficient (R2 about 0.37-0.41),
  not a sharp cutoff.
- 2610.10263: -11.9 to +2.3 points, 1.41-3.31x tokens; gains on long-horizon benchmarks, not on
  SWE-bench Verified. Artifact released on GitHub; benchmarks referenced, not redistributed.
- MAST: 14 failure modes, 3 categories, kappa 0.88, 1,600+ traces.
- Krogh and Vedelsby: E = Ebar - Abar (weighted mean error minus weighted mean ambiguity,
  squared error, weights sum to 1). Page's identity is the same algebra with equal weights
  (Page's book itself not opened).

**Corrected (the earlier text was wrong or imprecise)**
- Human catch rate is 13.6%, not "14%" (rounding in the talk).
- AgenticFlict 27.67% = 29,609 conflicts of 107K+ processed PRs (not 142K); textual conflicts only;
  dataset on Zenodo (DOI 10.5281/zenodo.19396916).
- CooperBench: abstract says 30% lower on average; the ~50% figure is GPT-5 and Sonnet 4.5 only;
  652 tasks. Dataset licence not stated in the text (paper CC BY-SA 4.0; source repos MIT/BSD/
  Apache): check before reuse.
- Sleep-time compute 2504.13171 matches on test-time tokens, NOT total compute; sleep-time cost is
  extra, and plain test-time scaling wins at high budgets. Our H3 control (equal total tokens) is
  therefore STRICTER than theirs, which is a point in its favour, not a replication.
- "Passes Alone, Fails Together": real Django pairs interfered in 1 of 834 runs; the 97% is on
  constructed tasks and the authors say it does not estimate real frequency. Do not cite 97%.
- AuthBench / ToolPrivBench: ToolPrivBench measures over-privileged tool SELECTION (6 of 11 models
  above 30%), not unused grants; AuthBench's unused-grant rate is only in a chart (no number);
  AuthBench is CC BY-NC-SA 4.0 (non-commercial: check before reuse).
- Anderson and Schooler (1991): the power law is for need probability of words and email senders.
  Applying it to permission reuse is an analogy that H1 must test, not a result.
- Governed-memory prior art: none of the three targets coding agents; none has re-verify-on-use
  or a provenance lint; 2606.24535 already has temporal supersession and provenance chains;
  2505.18279 has immutable provenance, no supersession; 2605.04264 is a viewpoint paper with no
  experiments. H4's novelty is therefore narrower: coding-specific deterministic test + lint.
- "No documented allow-rule expiry" rests on absence in the docs plus the wording "Permanently per
  repository and command". "doctor prompt audit" was NOT found in the docs (only `/doctor`,
  `claude doctor`); keep it as a talk claim only.
- The "72% cost reduction" from cache fixes appears in no written source found; the only 72% in
  Lance Martin's post is a wiki-grading score. Keep as talk-only; the cost model must not rely on it.

**Efficiency and first-principles sources (file 06): mostly abstracts and snippets**
- Kaplan 2020, Hoffmann 2022, Snell 2024 (>4x over best-of-N; 14x smaller model can win on some
  problems), FrugalGPT, Luccioni, Green AI: abstract pages only.
- Anthropic multi-agent post: agents about 4x tokens vs chat, multi-agent about 15x; token usage
  explains 80% of BrowseComp variance (vendor data, passages only).
- Energy: Google 0.24 Wh median prompt, Epoch about 0.3 Wh; Google's breakdown is secondary.
  GB10: `nvidia-smi` shows power.draw, memory and power limit N/A (seen locally); NVML total-energy
  counter unconfirmed, so energy = sampled power x time, GPU only.
- Musk's five steps: paraphrases only; do not quote verbatim until checked against the primary.
- Cited from memory, UNVERIFIED: Fermi, MDL, Gall, Unix, worse-is-better, Hickey, Chesterton,
  Amdahl, Little, roofline, Zilberstein, speculative decoding, Strubell, Patterson, CodeCarbon.

**Added after files 07, 08, 09 (2026-11-19).** Same retrieval caveat; pages were read with a
local fetch-and-parse, and "opened" means that. Open sources only; Sci-Hub was not used.

*Claude platform (file 07). Confirmed on pages opened in full unless marked.*
- Deployment shapes: cloud sandboxes (default; Anthropic runs sandbox, service and model);
  self-hosted sandboxes (you run the sandbox only; the agent loop stays at Anthropic);
  self-hosted Managed Agents (you run sandbox and service; model at Anthropic or a provider you
  choose). Separately, Claude Code self-hosted environments: runner on your host, control plane
  and session transcript at Anthropic, public beta for Team and Enterprise, no Zero Data
  Retention or HIPAA organisations.
- Self-hosted Managed Agents is private beta by request. Not available on it: dreams, scheduled
  deployments, webhooks, the Files API, `mcp_oauth` vault credentials, dynamic workflows, the
  advisor, self-defined subagents. Multi-agent there is a coordinator with 1 to 20 listed
  subagents. (From the "differences" page, read in part.)
- Claude Code sandboxing: "not a complete isolation boundary". It covers shell commands only.
  Read, Edit, Write, WebFetch, MCP servers, hooks, LSP, the status line and `apiKeyHelper` run
  outside it. Network filtering is by client-supplied hostname with no TLS inspection by
  default, and domain fronting is named as possible.
- Memory stores are hosted by Anthropic in the hosted and self-hosted-sandbox modes. Dreams is a
  research preview. MCP tunnels are a research preview with no continuity commitment.
- Per-session budget (`max_list_cost`, stop reason `budget_reached`) and per-tool permission
  policies (`always_allow`, `always_ask`, `auto`) exist on Managed Agents (pages read in part).
- Not confirmed, or assumption: (1) "Flows" has no page at the tried URL; treating "dynamic
  workflows" as its equivalent is file 07's assumption. (2) A local small model per cell is not
  a documented use: the gateway section says model IDs must name the same model, and a Claude
  Code session needs an Anthropic-issued token, so such a cell must be a custom worker or tool
  process. That a shim would work is untested. (3) No policy-signing feature was found; absence
  on the pages read is not proof. (4) No hook mechanism was found on Managed Agents agent
  definitions; same caveat. (5) Beta status labels differ between pages and were not reconciled.

*Weight-space programming (file 08).*
- Confirmed on the primary page: authors Takehi, Teoh, Zhang, Khattab (MIT CSAIL); published
  2 Nov 2026; editor model GPT-6 Astra through a custom harness; Qwen3.5-0.8B edit of 131,072
  weights (0.016%), 64 output columns per layer in the MLPs of layers 15 and 19; MATH-500 7.9%
  to 48.1%, GSM8K 13.8% to 67.1%, IFEval 21.0% to 62.3% for the 50-pass run; logs and scripts
  public (logs CC BY 4.0, scripts MIT).
- Qualified, also from the primary page and README: the Qwen run did not read raw weights as
  text. It used a Python kernel over the weights plus a budget of 10, 25 or 50 forward-pass
  calls, with no gradients. Raw-weights-as-text applied only to networks of 17k to 172k
  weights. The 10- and 25-pass edits reached 12.3% and 14.1%. Wall-clock was 8.5 to 20.3 hours
  per run. There is **one editing run per budget**, and the three runs made three different
  edits. There is **no fine-tuning, LoRA, steering or decoding baseline** for Qwen. The Gemma 3
  270M follow-up did not improve (6.8 to 7.7 at best). Cost in dollars or tokens is not stated.
  No safety section.
- From critiques, weaker evidence: the gain is mostly repair of a reasoning loop (85 of 96
  practice answers hit the 32,768-token limit, per the page), so "6x" is relative to a baseline
  that mostly truncates. Kundu (arXiv 2611.20953, abstract only, single author) reports a
  comparable gain with Claude by a different mechanism and no Gemma gain. Goworek et al.
  (2611.21449, abstract only) reproduce the small-network results.
- Leads only, NOT opened, do not cite: an independent 51.0% re-run; thinking-off baselines of
  43.95% and 52%; a repetition penalty reaching 54%; a steering-vector version; the Honnibal
  rebuttal; the Moonshots episode. The Maier article is paywalled and was not read.
- Corrected: "Recursive Language Models" (arXiv 2512.24601, Zhang, Kraska, Khattab; abstract
  opened) is an inference-time method in which the prompt lives in a Python REPL and the model
  calls itself over snippets. It is not teacher/student/judge self-training. "Taming the
  Long-Tail" (arXiv 2511.16665, ASPLOS '26; abstract opened) is a speculative-decoding speed-up
  for reasoning-RL training, posted November 2025, unrelated to weight editing.
- Prior art, abstracts opened: ROME 2202.05262, MEMIT 2210.07229, task vectors 2212.04089,
  representation engineering 2310.01405, activation addition 2308.10248, abliteration
  2406.11717, Tracr 2301.05062. The Qwen edit is the same family as abliteration, found by an
  agent instead of a person.

*Unsloth and local models (file 09).*
- Confirmed on pages opened: Unsloth's README states dual licensing, core package Apache-2.0
  and optional parts such as the Studio UI AGPL-3.0 (file-level split not read). Unsloth and
  NVIDIA both publish DGX Spark guides; both use an NVIDIA PyTorch container
  (`nvcr.io/nvidia/pytorch:25.09-py3` in Unsloth's, `25.11-py3` in NVIDIA's, which installs
  Unsloth with `--no-deps`). Spec page: 128 GB unified memory, 273 GB/s bandwidth, 140 W TDP,
  240 W supply.
- Vendor claim, method not read: "2x faster, 70% less VRAM".
- Unverified: PyPI aarch64 cu130 torch wheels (hence the container route); version
  compatibility on this host (Unsloth's guide is about 11 months old, NVIDIA's playbook is
  from December 2025); every model's quality for our tasks (nothing benchmarked).
- Model IDs (Qwen3.5 0.8B to 27B, Gemma 4, gpt-oss, Ministral 3, Granite 4.2, Phi-4, SmolLM3 and
  others, listed in file 09 and PLAN 3.2) were seen in Hugging Face API listings. Licences are
  listing tags, not model-card text. The owner verifies each before any download.
- Power: forum snippets (unopened) say `nvidia-smi` power on the GB10 is GPU only and that some
  units report implausibly low values. Consistent with what was seen locally (power.draw
  present; memory and power limit N/A). Whole-system energy needs a wall meter.
- Decode-speed figures in file 09 are arithmetic from the bandwidth spec, not measurements.

### 7.3 Claims we hold only from memory or secondary sources

Do not cite without checking: Ostrom's full list of design principles; Page's *The Difference*;
Thompson's critique of Hong and Page; Zucker's argument in detail; Bartlett's primary text; the
AGM paper itself; the Auto Dream internals of Claude Code (third-party descriptions that
disagree with each other); the Ona and Pillar Security circumvention reports (single sources
with commercial interest); every arXiv ID in the 26xx range. Added with section 1.4: the
polycentricity texts (V. Ostrom, Tiebout and Warren 1961; E. Ostrom 2010); Russell and Wefald
(1991) beyond its citation; author names attached to FrugalGPT and to the model-editing papers;
every second-hand figure about the weight-editing post listed as a lead in 7.2a; forum reports
on GB10 power readings; Hugging Face licence tags.

### 7.4 The three talks

Figures used in PLAN.md and here, all "per the talk, owner-validated":
- Lance Martin: evaluate the path as well as the answer; a verifier with its own context; an
  append-only session log; the wrong-memory trap corrected by an offline pass; task-specific
  evals needed to show reflection justifies its compute; grader sanity checks; train and held-out
  split when hill-climbing; read examples by hand first.
- Lydia Hallie: deny rules beat the classifier; sandbox bounds side effects; hooks exit 2; the
  orchestrator and worker split; humans 13.6% (talk: about 14%) against auto mode 89% on
  dangerous commands (primary source: Aug 2026 announcement, see 05a).
- CJ Avilla: trust as willingness to be vulnerable when monitoring is incomplete; base policy
  plus human-signed ceiling plus a session policy that grows on observed need and shrinks on
  non-use (two weeks in the example); offline session audit against a written policy; and, in
  answer to the owner's question on over-requesting and self-blocking, "human promotes repeated
  requests".

- Lance Martin, AI Engineer Code Summit, 12 Nov 2026 ("Exploring Claude's Frontier"): the
  1,000-agent Lean run and its self-built tables; CL-Bench with and without memory; memory
  sprawl; the dreaming-token curve. Figures and our reading: 1.5.
- Diogo Almeida, same summit, 11 Nov 2026 ("Beyond Better Assistants: Software That Can Make a
  Decision"; file 11's title for it is wrong, per file 10): reliability over occasional
  brilliance; the cache shapes agent design; shared state; spirit over letter. His cost-share
  pie is unconfirmed (1.5, note 9).

These are the project's motivation and its baselines. They are not its evidence.

---

## 8. One-paragraph summary of the framework

Three loops (authority, division of labour, memory) each get one borrowed idea that produces a
number: decay curves for authority, near-decomposability for fan-out, consolidation and
increasing returns for memory. Each number is computed on real traces or on a benchmark whose
ground truth we planted and whose scoring is deterministic. Each prediction has a size, a kill
criterion and a control that spends the same compute. Everything else from complexity science is
parked until it can meet that bar. The loops run in one shape, a hub and cells, which adds two
questions with the same discipline: can a cheap local cell clear a fixed quality floor on some
class of work (H6), and does a weight change sent by the hub do anything a decoding setting does
not (H7). Lance Martin's talk adds two more of the same kind, neither confirmatory: does a
weaker model need imposed memory structure to benefit from memory at all (H8, exploratory), and
can small local models coordinate through a shared board without being handed its structure
(H9, status awaiting the owner's ruling). Section 4a turns the three idea families into task
controls scored by one measure, the control effect under a fixed set of perturbations.
