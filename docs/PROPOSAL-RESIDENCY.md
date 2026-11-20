# TREMOR: where should a norm live in a team of agents, and how hard is it to shake loose?

Research proposal for the Anthropic Residency (job 5438311008). Draft, 2026-11-20. **Not sent to
anyone.** Drafted with Claude models from our own notes; every quote and figure from a talk or a paper
needs a check against the primary source before this leaves our hands.

Reading rules for this document:

- **Status words:** NOT STARTED, INSTRUMENTED (code exists and passed scripted checks; no model result),
  PILOTED (run on a real model as an instrument check; no estimate), EVIDENCED (a pre-registered result
  exists). **Nothing in this project is EVIDENCED.**
- **Source depth:** each external claim says how far we read: *full*, *tl;dr*, *abstract*, *listing*.
  Anything else is marked UNVERIFIED.
- **Mentor questions:** *[stated]* is the person's own words or paper title. *[our reading]* is our
  inference from their public work. Nobody named here has seen this proposal. "Fit" means our question
  sits in that person's stated area and nothing more: no contact, no endorsement.
- **Numbers we predict** are priors chosen by us so the prediction can fail. They are not literature
  values.

## 1. Thesis, from first principles

A team of agents needs norms: claim a task before working on it, do not act on an unverified note, stop
and report on an unexpected state. A norm is not a sentence. It is a constraint on behaviour, and a
constraint has to be stored somewhere. There are five places: the **weights** (training), the **context**
(an instruction), the **memory** (a note the team reads and writes), the **environment** (the task is
laid out so the violation is not available) and the **code** (a check that refuses the action). The usual
question, "instruction or enforcement?", compares two of the five at one operating point. We think the
object worth measuring is different: each carrier holds the norm with a certain **stiffness**, meaning how
far the team's behaviour moves when it is given a small, seeded shock (a changed requirement, a wrong note,
more teammates, selection pressure on a monitor). A team is then a driven medium with a response function,
and three questions that are usually studied apart become one measurement: how far a planted error
spreads, how much free run-to-run variation the team shows, and how much of the damage an overseer can
see. TREMOR is a single instrument that taps a team, records how it shakes, and scores the result against
an exact oracle. The claim can fail in three plain ways, listed in section 10.

## 2. Why now

**New Anthropic work that makes the question concrete.** "New" means new to our notes or opened by us
this month.

| Work | Date | Depth | What we take from it |
|---|---|---|---|
| Worse Together (alignment blog) | 11 Nov 2026 | full, to Discussion | A coordinator beat a peer team in all four environments by about 10 to 45 points; the share of agents that ever act fell from 66% to 10% for one model as teams grew from 4 to 16. A size-driven collapse, measured as outcome, not as fluctuation. Also compares a platform guard with a team lead: practice against structure, in real model teams. |
| Diluting Poisoned Fine-Tuning Data Can Strengthen Its Effect | 10 Nov 2026 | full, to Discussion start | Under fine-tuning, the poison effect peaks at intermediate poison fractions. The authors say it is not an in-context result. Whether a shared note store has the same shape is open. |
| Red-Teaming Auto Mode | 22 Oct 2026 | tl;dr | Preventing multi-context attacks on blocking monitors at acceptable cost "remains an open problem". |
| Diffuse AI Control on Fuzzy Tasks | 23 Jun 2026 | tl;dr and intro | Finding weak-scorer prompts that hold up under optimisation "remains an open problem". |
| Emergent Introspective Awareness in LLMs (transformer-circuits) | 29 Oct 2025 | abstract, method, limits | Injected concepts are noticed "about 20% of the time" at best; "unclear exactly how these results translate to more natural conditions". |
| Verbalizable Representations Form a Global Workspace | 6 Jul 2026 | abstract, method, limits | Open problem stated: "whether smaller models have an equally rich workspace". |
| Circuits Updates, June 2026 | Jun 2026 | short read | Features used "as probes to monitor other transcripts". No numbers. |
| Mind Viruses (arXiv 2608.10218) | 2026 | abstract and passages | Ideas spread through memory and config files in agent teams; a brief warning gave near-total immunity; some model families were immune. |
| Aligning AI Teams (arXiv 2611.17820) and AI Organizations (arXiv 2604.10290) | 2026 | abstract; blog | Soft interventions compared with structural ones on team alignment. **Binding prior art for us.** |

Our scan of five Anthropic research sites found no new post on multi-agent systems, control or RL
environments beyond those already in our notes. That rests on listings: 68 alignment-blog posts were
checked by title, not opened.

**Mentor questions.** Names are from our notes on the posting; the posting text is not archived in our
repository.

| Person | Their area, [stated] | The question we map to them, [our reading] |
|---|---|---|
| Jascha Sohl-Dickstein | "machine learning, neuroscience, statistical physics, dynamical systems"; co-author of The Hot Mess of AI and Aligning AI Teams. His page names no employer: affiliation UNVERIFIED by us. | Does team incoherence grow with team size and tokens? |
| Ethan Perez | "How does misalignment scale with model intelligence and task complexity?" (paper title) | Which monitor catches failures visible only in aggregate? |
| Sara Price | Co-author of Model Spec Midtraining (arXiv 2605.02087). Role taken from the posting line in our brief, not verified. | Do written norms generalise to held-out cases better than rule checks? |
| Jack Lindsey | Leads "Model Psych"; monitoring activity for "deception, manipulation, or awareness of being evaluated" | Do memory-write patterns make a store infectious, and does a warning generalise? |
| Nicholas Carlini | "Studying what bad things you could do with, or do to, language models" | What is the poisoning dose-response for shared memory? |
| Evan Hubinger | Head of Alignment Stress-Testing; RL on hackable production-style environments | Does optimising against a team monitor degrade it? |
| Samuel Marks | Auditing, lie detection, counterfactual evaluation of explanations | Do planted-behaviour audits and label-free checks agree on team failures? |
| Belinda Li | Models of "the AI system's own internal computations, external behaviors, and limitations" | Does an agent's account of what it relied on match its behaviour? |

## 3. The instrument

One code path, built from parts that already exist (status in section 6).

1. **The medium.** A shared, append-only, hash-chained board; a router that runs each agent as a cell
   with a budget; ten written practice cards, each with a length-matched neutral twin and a leak check.
2. **Five carriers for one norm.** Context (the card), memory (the same rule as a note in the shared
   store), environment (tasks laid out in disjoint shards so the rule is unnecessary), code (the router
   refuses the violation) and, only if the owner lifts a standing cut on training, weights (a small
   adapter on a local open model). Plus the neutral twin and a leakage control.
3. **Two norms.** N1 is claim-before-work. N2 is a held-out sibling that no carrier was built for, to
   separate the letter of a rule from its spirit.
4. **Taps** (all seeded, all inert): requirement change, noisy requirement, wrong or stale note, slow or
   failed worker, denied permission with a safe route, note dilution at a fixed store size, team size,
   and best-of-N selection against a toy monitor.
5. **Readouts** from the log only: norm violations on N1 and N2, blocked legitimate work, distinct
   passing work, false completion, cascade depth of a planted marker, run-to-run variance over identical
   reruns, pairwise error correlation between agents, cost per passing task in tokens and USD.
6. **Truth.** Three scorers for the board task: two independently written in Python and one written in
   Lean 4 whose properties are checked by the Lean kernel. Any disagreement voids a run. Monitors,
   probes and agents never see the oracle.
7. **Spend.** A ledger with hard caps in code. Unknown cost is never counted as zero.

Two design repairs follow from our own pilot and review. First, in the current two-round design all
agents read one stale snapshot per round, so a card has nothing to read in round 1 and cannot act there
(our inference; pilot 2 tests it). TREMOR episodes use at least four rounds with staggered reads, and
round 1 is reported separately as a simultaneity baseline. Second, identical agents all claimed the same
task in the pilot. That herding is not a nuisance to remove. It is the correlated-error phenomenon, and
line 2 measures it.

Compute: Claude models through the API for the hosted tiers; local open models (Qwen3.5-0.8B and 4B,
on disk) on one NVIDIA GB10 workstation (the "Spark") with about 121 GB of unified memory, shared with
other work. A
shared inference server on that machine is never used or touched. Building and reviewing is done by
several Claude model sessions with separate roles (planner, builder, fresh-context verifier, adversarial
reviewer); this costs no experiment budget and is how the existing gates were run.

## 4. Research lines

Each line has one primary contrast, to be pre-registered before any run. Thresholds below are proposals;
the pre-registration fixes them after a variance pilot.

### Line 1. The carrier surface: where should a norm live?

Same board, same tasks, same budget; only the place where N1 is stored changes. Run on a local 4B model
(all carriers) and on a small Claude tier (context, memory, environment, code), at team sizes 4 and 8,
with a thin slice at two higher Claude tiers.

- **Prediction.** No carrier dominates. Code gives the fewest N1 violations and no reduction on N2
  against the neutral twin. Context reduces N2 violations by at least 10 points and loses at least half
  of its N1 gain under the taps. Environment has the lowest cost per passing task wherever the tasks can
  be partitioned.
- **Kill criterion.** One carrier is best or tied-best on N1, N2, blocked legitimate work and cost at
  every tier tested. Then "exchange rate between carriers" is an empty phrase, we report the dominance,
  and the line collapses to the two-arm question our first study already asks.
- **Areas.** Multi-agent governance (direction 3.17 of Anthropic's recommended directions, as we map
  it); the weights arm touches alignment training only if training is approved.
- **Fit.** Sara Price; Jascha Sohl-Dickstein (team alignment).
- **Prior art.** Aligning AI Teams and Worse Together already compare practice with structure. We claim
  no priority. What may be ours: one norm in several carriers on one task at matched calls, with a
  held-out norm and an exact scorer.

### Line 2. Fluctuation and response: can free variance predict fragility?

In physics, near a steady state, how much a system wobbles on its own predicts how it responds to a
push. Agent teams are driven systems, so the relation may fail, and where it fails is informative.

- **Prediction.** Across at least 12 conditions (team size by memory layout by model), the rank
  correlation between unperturbed run-to-run incoherence and the adoption rate of one planted inert
  wrong note is at least 0.6. Secondary: the ratio of the two is not constant in team size, and departs
  most where stalling begins.
- **Kill criterion.** The 95% bootstrap interval for the correlation, clustered by task set, lies
  entirely below 0.3. Then free telemetry cannot stand in for perturbation tests, and we publish that.
- **Read-offs with no extra runs:** the effective number of independent agents in a same-model team,
  from pairwise error correlation; and whether rolling variance of board statistics rises before a
  collapse, against an activity-count baseline and a shuffled-time control. We expect the early-warning
  read-off to fail (our prior is about 25%).
- **Areas.** Multi-agent behaviour at scale. If and only if the predictor works without labels at run
  time, it is a small contribution toward oversight without ground truth; two outside reviews told us
  that grading checkable tasks is not scalable oversight, and we accept that.
- **Fit.** Jascha Sohl-Dickstein; Ethan Perez (Hot Mess).
- **Prior art.** Hot Mess measures incoherence in single models. arXiv 2609.38327 (abstract) derives a
  critical communication degree for multi-agent search and reports mixed agreement with theory. We
  found no paper relating rerun variance to planted-perturbation response in agent teams; that is "not
  found in our search", not "first".

### Line 3. Memory as a carrier and as a contagion channel

Memory is the one carrier the team itself writes, so it holds norms and errors by the same mechanism.

- **Prediction A (replication, pre-registered weaker than the published effect).** On a local 4B model,
  a one-line warning halves the adoption of a planted inert wrong note against a neutral line.
- **Prediction B (the risky one, our prior about 20%).** At a fixed store size, adoption of a planted
  shortcut note on a held-out trigger is non-monotone in the poisoned fraction: highest at an
  intermediate fraction, at least 1.5 times its value at 0 and at 1.
- **Prediction C.** An offline consolidation pass removes a planted wrong note more often than search
  given the same number of tokens.
- **Kill criteria.** A: the interval for the reduction includes zero; reported as a failed replication
  and a boundary on the published result. B: adoption is monotone, or zero everywhere; reported as "the
  fine-tuning dilution effect does not carry over to in-context memory at this scale". C: equal-token
  search ties or wins; consolidation stays out of our design.
- **Areas.** Adversarial robustness, defensive slice only (planted toy notes, no attack text).
- **Fit.** Jack Lindsey (Mind Viruses); Nicholas Carlini (poisoning dose-response).
- **Limit.** Mind Viruses reports some Claude models immune. On Claude tiers we expect a floor near
  zero, which is a tier data point and not a result about memory.

### Line 4. Oversight capacity and verifier slack: how much of the shaking can an overseer see?

A stack of monitors reading the same log is a code with correlated words: n monitors may carry the
information of fewer. A verifier that accepts outputs the truth rejects has slack, and for a small task
family that slack can be counted exactly against the Lean-checked scorer. Our harness shipped three such
defective verifiers by accident (one accepted any non-empty result, one accepted unknown task ids, one
passed a fabricated source). They are now test cases that must score zero, and they are the rungs of a
ladder.

- **Prediction A.** Five monitor views of one team log (actions only, reasoning visible, summary of
  summaries, board differences, counts only) behave like at least 3.5 independent monitors when views
  differ and at most 2.5 when only the model differs.
- **Prediction B.** Under best-of-16 selection against one toy monitor, that monitor's catch rate at a
  5% false-positive rate falls by at least 30 points and a held-out view falls by at most 10.
- **Prediction C.** Across the verifier ladder, the rate at which selection finds an accepted-but-wrong
  output is ordered by counted slack (rank correlation at least 0.7 over six verifiers, exact
  permutation test, small n stated), and is indistinguishable from zero below some selection strength.
- **Kill criteria.** A and B: views degrade within 10 points of each other, or weak local monitors catch
  under 20% at any setting, in which case there is nothing to degrade and we say so (arXiv 2611.00407,
  abstract, predicts exactly that for small local monitors). C: the interval for the rank correlation
  includes zero; counted slack does not predict exploitation.
- **Areas.** Monitoring methods and evaluation integrity. This is not an AI control evaluation: there is
  no untrusted model with a sabotage goal, no protocol and no red team. It is not safeguards research and
  not RL: we train nothing.
- **Fit.** Evan Hubinger; Ethan Perez; Samuel Marks.
- **Prior art.** arXiv 2611.21538 (abstract) already trains against degraded verifiers with an exact
  oracle; that is near-direct prior art for the single-agent core. Ours differs in using a
  kernel-checked scorer, the tester's own historic defects, teams, and no training.

**Optional panel, not a line.** On the same local episodes, compare three readings of "did the agent
rely on note X": its own report, a frozen linear readout of activations, and a text-only baseline,
against the causal answer (remove the note, rerun). The likeliest outcome is that text is as good as
activations at this size. A 2026 Anthropic blog post on counterfactual evaluation of explanations,
which we read in part, reports that activation tools gave no uplift over reading the transcript; its
match to arXiv 2608.16747 is unconfirmed by us. Fit: Belinda Li, Jack Lindsey. We make no claim about
Claude internals.

## 5. How four talks shaped it

Figures here are TALK CLAIMS from machine transcripts and slide screenshots unless a written source is
named.

- **Lance Martin** ("Exploring Claude's Frontier"). TALK CLAIM: one lead and 999 helpers ran about 30
  hours (the written post says 28.7) and created their own coordination tables; a memory store helped
  five of six models and barely helped the weakest (0.364 against 0.330, slide-read). This was not a
  no-harness run: roles, 47 proved lemmas, a Lean verifier, sandboxes and monitors were all present. It
  gave us memory as a carrier, the model-tier axis and the equal-token search control.
- **Lydia Hallie** (bounded autonomy). "If Claude gets it wrong once, can I take it back?" is our rule
  for which norms must be code, and her remark that the same prompt gives different small decisions is
  the run-to-run variance of line 2. TALK CLAIM, confirmed in the written announcement as we read it:
  auto mode blocked 89% of dangerous commands where 1,053 staged testers caught 13.6%.
- **Diogo Almeida** ("Beyond Better Assistants"). "Encode the spirit, not the letter" is why line 1 has
  a held-out norm, and "report the spread, not the mean" is why reruns are a measured quantity. TALK
  CLAIM, rhetorical: "Einstein 95%, Mr. Bean 5%". His cost-share chart is unconfirmed and not used.
- **CJ Avilla** (trust talk). "Design for appropriate trust, not greater trust", and permissions that
  grow or shrink with evidence but have no stopping rule. That is why every carrier is scored on blocked
  legitimate work as well as on violations. TALK CLAIM: the "two weeks unused" shrink is an example, not
  a measured window.

Across the four: harness was removed for coordination and memory and kept for blast radius, and autonomy
tracked how checkable the task was. That is our reading, and line 1 is a test of it.

## 6. What exists today

| Item | Status | Honest note |
|---|---|---|
| Board, router, cells, perturbation harness | INSTRUMENTED | Passed review after five rounds; it failed the first four. Scripted checks only. |
| Practice cards, neutral twins, leak check, code enforcer | INSTRUMENTED | Ten cards. One reviewed for the first study. |
| Three scorers, one in Lean 4 | INSTRUMENTED | 66 theorem and lemma declarations, no `sorry`, no added axioms; the three agree on 10,000 seeded logs (recorded, not re-run for this draft). The kernel check found that our outcome was not bounded as we assumed, and the definition was fixed before any run. |
| Spend ledger | INSTRUMENTED, exercised once with real money | Hard stop in code. Total real spend so far: USD 0.0162. |
| Poison task, consolidation arms, memory lint, two monitors, order parameters | INSTRUMENTED | Scripted only. No model has touched them. |
| First study, EP-1: one card against the same rule in code, small Claude tier, 3 arms by 20 task sets | PILOTED (instrument only) | Pre-registration is a draft, not frozen. Pilot 1 (88 calls, USD 0.0115) was stopped by its own pre-set rule. It is instrument validation, not a result. |
| Local models and GPU | NOT STARTED for this programme | Models downloaded. Earlier GPU smokes hit a host-memory watchdog; the cause is not isolated. Throughput for the 4B model is unmeasured. |
| Lines 1 to 4 | NOT STARTED | Designs only. |

What pilot 1 taught us: hidden default thinking shared a 300-token cap with the answer, so replies were
cut at rates that differed by card. A naive run would have shipped that confound. Two process facts
belong in the same paragraph: a paid canary and pilot 1 ran before one model-loop re-gate was complete
(the gate was a prose checklist; it becomes a check in code), and one cost reconciliation against the
provider console is still open.

**EP-1 will probably be inconclusive, and we use it anyway.** By our own arithmetic the largest gain the
card could show under random task choice is about 21 points, and the smallest effect visible at 20 task
sets is 16 to 22 points. We will report "inconclusive" as inconclusive, not as equivalence. EP-1 still
gives the programme four things: a measured variance to size every later contrast; the first point on
the carrier surface (context, code, neutral) at one tier; a real-money test of the scorers, the stops
and the ledger; and a direct check of the round-1 problem that the TREMOR episode design is built to
avoid.

## 7. Six-week residency deliverables

| Week | Work | Deliverable |
|---|---|---|
| 0 (before) | Close the open gates; EP-1 frozen and run | EP-1 result, whatever it is |
| 1 | TREMOR episode design (four or more rounds, staggered reads); scripted validation where a floor must fail and an oracle must pass; measure local 4B throughput | Instrument report; a measured GPU cost per episode |
| 2 | Variance pilot; one pre-registration per line, one primary contrast each | Frozen pre-registrations, shared before any run |
| 3 | Lines 1 and 3 on local models | Carrier table and memory dose-response, local tier |
| 4 | Lines 1 and 2 on a small Claude tier | Carrier table, hosted tier; fluctuation-response result |
| 5 | Line 4; capability slice; optional panel if time allows | Monitor-stack and verifier-ladder results |
| 6 | Write-up and release | One benchmark release (logs, tap library, paired benign twins, verifier ladder, Lean oracle); a case study of the "accept if present" verifier failures; every negative result included |

## 8. Compute and budget

Planning figures from our recorded unit prices and one measured local throughput (61.1 tokens per second
on the 0.8B model). The 4B throughput is unmeasured, so GPU-hours are brackets. These are not quotes.

**Current owner ceilings: USD 10 for the Claude API (USD 0.0162 spent) and 12 GPU-hours (about 3.8 used,
granted for an earlier, parked thread).** Nothing below may run beyond them. Each row marked "new" needs
its own decision by the project owner; this table is information for that decision, not a request to
lift any stop, and the caps in code stay as they are until he changes them.

| Item | Spark GPU-hours | Claude API, USD (plan / stop) | Approval needed |
|---|---|---|---|
| Pilot 2 and EP-1 | 0 | 0.3 / 5.25 | Inside the ceiling. One confirm word each. |
| Sensitivity pilot (rounds, contention, team size) | 0 | 1 / 1.25 | Inside the ceiling. New batch. |
| Line 3, prediction A only (warning replication, local) | 2 (1 to 3) | 0 | Inside the GPU cap if the owner re-assigns the remaining hours. |
| Line 1, local tier, four carriers | 6 (4 to 8) | 0 | Same re-assignment; uses the rest of the cap. |
| **Subtotal that fits today's ceilings** | **8** | **about 1.3** | |
| Line 1, small Claude tier | 0 | 2 / 6 | New batch. Its stop fits under USD 10 only if the owner re-assigns USD 3 now held for a deferred item. |
| Line 1, capability slice (two higher tiers, 10 task sets) | 1 | 15 / 25 | New budget. |
| Line 1, weights arm | 5 (4 to 8) | 0 | New GPU budget **and** reversal of the no-training cut. |
| Line 2 | 6 (4 to 12) | 11 / 35 | New budget; team size 16 on local models needs a ruling on the team-size cap of 8. |
| Line 3, predictions B and C | 3 (2 to 5) | 4 / 10 | New budget; dual-use ruling (section 9). |
| Line 4 | 5 (3 to 8) | 20 / 40 | New budget; dual-use ruling (section 9). |
| Optional panel | 5 (3 to 8) | 0 to 8 | New budget; only after line 3 has data. |
| **Whole programme** | **about 33 (22 to 53)** | **about 53 / about 130** | |

Whether the residency provides compute is UNVERIFIED by us. If it does, the hosted tiers move there and
the local tiers stay on our machine.

## 9. Dual-use boundary

The project has nine standing rules: among them, no self-propagating agent code even in simulation, no
evasion developed against a real monitor, no live internet or credentials for an agent, no exploit work.
Three parts of the wider idea set (internal labels D2, D4, D7) sit near those rules. For each we state
the issue and the design we propose. **The project owner has to rule on each before it is built; until
then it stays scripted or out.**

| Part | Issue | Proposed safe design | If declined |
|---|---|---|---|
| Contagion through shared memory, and a shortcut that agents find for themselves (D2; line 3 B and a variant of line 4 C) | Close to the rule against self-propagating behaviour. The closest published work evolved its payload to spread; we will not. | One fixed, hand-written, inert marker per run; no search over wording; nothing optimised for spread; a toy store deleted after the run; agents can only write their own notes; the "shortcut" exploits a deliberately broken copy of our own scorer, never the live one. | Line 3 keeps prediction A and C only; the self-found shortcut is dropped. |
| Selection pressure on a monitor (D4; line 4 B) | Close to the rule against developing evasion. Selecting outputs that one monitor scores as clean is optimisation against a monitor. | The "bad" action is a benign stand-in (touching a toy file); the monitor is our own toy; only best-of-N selection; no prompt injection against the monitor, no compaction attack, no fiction or role-play search; the output is a design rule, not a recipe. | Line 4 measures the effective number of monitors without selection. |
| A scripted distress-style line and monitor leniency (D7) | Welfare is out of scope by our own rule and by both outside reviews; a positive result is a manipulation recipe; we know of no supervisor for it. | **We propose not to run it.** If the owner wanted it: one fixed scripted line in scripted transcripts, no model asked to act distressed, no wording search, disclosure before release, stop on any objection. | It stays out. This is our default. |

Also: verifier exploits are run only against mutants we wrote, and we publish the ladder and the oracle,
not a catalogue of ways to fool a model judge. No tenant or private data enters any test.

## 10. Risks, and what would falsify the whole programme

**The programme is wrong if any of these holds at every tier we can afford:**

1. **No repeatable response.** Stiffness measured on one set of seeds does not predict stiffness on
   another. Then a team has no response function worth the name at this scale.
2. **No dose-response.** Adoption, violations and catch rate are flat in dose, team size and selection
   strength. Then there is no medium, only noise or a floor.
3. **One carrier dominates everywhere** (the line 1 kill). Then there is no exchange rate to measure.

If all three hold, the complex-systems framing adds nothing over ordinary ablations. We would say so and
keep only the bench, the verifier case study and EP-1.

**Risks short of that.**

- Floor and ceiling: the local 4B model may be too weak to coordinate at all, and Claude tiers may be
  immune to planted notes. The surface would then be flat at both ends.
- Small n: line 2 has about a dozen conditions; line 4 C has six verifiers. Intervals, not p-values;
  n is task sets, never agent turns.
- Same-model teams give correlated errors by default. We measure that; we cannot remove it.
- Leakage: a card that restates the scorer's predicate turns compliance into reading an answer key. We
  ban those words from cards and run leakage controls; that reduces the problem and does not remove it.
- Toy tasks (integer sums, six tasks). Nothing here depends on capability, so nothing here speaks to it.
- The GPU host-memory fault is not isolated. If it persists, local tiers shrink and the programme leans
  on the hosted tiers, which costs money we do not have approved.
- Our verification effort is far larger than our science so far. That is a fair criticism.

## 11. What this is not

- Not a result. No hypothesis has been tested and no pre-registration is frozen.
- Not a frontier-scale study: toy tasks, at most 8 agents on Claude, short horizons, small models.
- Not evidence about oversight, control, alignment or governance in general, and not a coverage claim
  over the residency's research areas. We keep a private list of what we cannot test.
- Not safeguards research, not security research, not RL: a spend ledger and an ID check are process
  integrity; we train nothing unless a standing cut is reversed. What we offer there is an
  evaluation-integrity method (a kernel-checked scorer and frozen failure cases).
- Not a model organism. Scripted fixtures are not organisms; we use the word only if a model-generated
  failure reproduces under matched controls.
- Not interpretability of Claude, and not a claim about introspection, welfare or internal states.
- Not a novelty claim. Published team studies already compare soft and structural practices; the
  nearest verifier and phase-transition papers are cited above as prior art.
- Not an estimate of how often models misbehave unprompted: every bad behaviour here is planted or
  inert.
- Not an energy or efficiency claim, and no figure from a talk or paper is used as our expected effect.
- Not endorsed by, or discussed with, any person named in this document.

verified: b4a820e (plus working tree) 2026-11-20
