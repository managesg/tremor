# Adversarial review: docs/PROPOSAL-RESIDENCY.md (accuracy pass)

Reviewer: fresh Opus 5.5 session acting as a skeptical alignment researcher. Date 2026-11-20.

**Scope.** I reviewed the proposal and checked it against:

- `docs/WORKPLAN-RESIDENCY.md`
- research notes H1, H2, H3, S1 and S2
- sections 8 and 9 of `docs/ALIGNMENT-INTEGRATION.md`
- the GPT and Cursor adversarial reviews, for claims they already cut

I fetched the primary sources with Python `urllib` and read them as data. The review cost nothing:
no API calls and no GPU.

**Proposal not edited.** The owner's instruction, relayed mid-task, changed the brief. It said:

- do not edit the proposal (Fable will restructure it, with dreaming as the centrepiece);
- do not reduce the ambition, scope or budget of any line;
- record every correction here so it can be carried into the new version.

Every item below is therefore a correction to carry over, not a change already made.

**Verdict: READY-WITH-EDITS.** No finding requires cutting a line. The corrections are about
accuracy, and every one has its exact replacement wording or quote below. The text should not be
shared until these corrections reach the new version. Applications close **22 Nov 2026**. Both the
posting and the residency blog give that date.

## 1. Corrections from primary sources (carry these into the new version)

### 1.1 Mentors: the posting is public, so cite it directly

Source: Greenhouse job 5438311008, section "Mentors and research areas". The draft says the posting
text is not archived. It is retrievable, so cite it and drop that sentence. The posting's exact lines:

| Mentor | Posting line, verbatim | Notes for the table |
|---|---|---|
| Sara Price | "leads the Alignment Training team; background in data science" | The draft said the role was "not verified". It is now verified |
| Ethan Perez | "leads the Alignment Science team; background in machine learning" | His homepage says "I lead the alignment team at Anthropic". The draft's *[stated]* text was the Hot Mess title, which belongs to a co-authored paper and was lower-cased. Exact title: "The Hot Mess of AI: How Does Misalignment Scale With Model Intelligence and Task Complexity?" (Hägele, Gema, Sleight, Perez, Sohl-Dickstein; arXiv 2601.23045, 30 Jan 2026) |
| Evan Hubinger | "leads the Alignment Stress-Testing team; formerly at The Machine Intelligence Research Institute (MIRI)" | His Alignment Forum profile says "Head of Alignment Stress-Testing at Anthropic", which is exact. The draft's "RL on hackable production-style environments" is our reading, not his words: move it to *[our reading]* |
| Samuel Marks | "leads the Scalable Oversight team; background in mathematics" | The draft's *[stated]* text, "Auditing, lie detection, counterfactual evaluation of explanations", appears on none of his pages. It is our reading of his papers |
| Belinda Li | "researches how language models represent the world, users, and themselves; background in natural language processing (PhD, MIT)" | The homepage quote in the draft is exact: "models of the AI system's own internal computations, external behaviors, and limitations" |
| Jack Lindsey | "leads the Model Psychology team; background in theoretical neuroscience" | The homepage quote is exact: "I lead the 'Model Psych' team" and "signatures of deception, manipulation, or awareness of being evaluated" |
| Nicholas Carlini | "researches adversarial machine learning and AI security; previously at DeepMind and Google Brain" | The homepage quote is exact: "studying what bad things you could do with, or do to, language models" |
| Jascha Sohl-Dickstein | "works at the intersection of safety and pretraining; background in physics and neuroscience, formerly Principal Scientist at Google Brain" | The posting lists him as a potential Anthropic mentor, so drop "affiliation UNVERIFIED". The homepage tagline "machine learning, neuroscience, statistical physics, dynamical systems" is exact |

The posting also lists **Elana Simon** ("researches the interpretability of language models and
biological models"). The draft does not mention her. Whether to add her is a scope choice; this review
takes no position.

Keep the draft's rule unchanged: fit is not contact and not endorsement. Nothing in the draft implies
contact.

### 1.2 Papers and posts

1. **Worse Together** (alignment.anthropic.com/2026/worse-together; Paliskara, Namchittai, Tay,
   Griffin, Lampinen; 11 Nov 2026).
   - Correct: the date, "about 10 to 45 percentage points" and "all four environments".
   - The draft's "for one model" should say **Sonnet 5**. The full sentence reads: "from four to 16
     agents, the share that ever act falls from 66% to 10% for Sonnet 5 and from 82% to 25% for
     GPT-5.6-sol".
   - Add that these are **multi-user** teams: "each user has their own goal, and all of the users
     draw on one shared resource". They are not same-objective teams.
   - The draft says the post "compares a platform guard with a team lead". In fact the team leader
     helped in the shared-budget environment, and blocking orders until messages were read helped in
     the group-order environment. The two fixes were tested in different environments, not against
     each other.
2. **Diluting Poisoned Fine-Tuning Data Can Strengthen Its Effect** (homeopathic-learning; Clarke,
   Dubiński, Chua, Schrodi, Evans, Cloud; 10 Nov 2026).
   - **Unsupported:** "The authors say it is not an in-context result." The post never mentions
     in-context learning. Replace with: "All experiments fine-tune small open-weight models (Qwen3-8B
     and Gemma-3-4b-it) or a small MNIST network". In-context memory is not studied.
   - Peak claim, verbatim: "For a training set of fixed size, it peaks at intermediate fractions of
     poisoned data and is nearly absent when the data is all clean or all poisoned."
   - The effect "requires that the poison data have an identifying 'trigger' feature that is absent
     from the clean data". Line 3 B must build that trigger in for the analogy to hold.
3. **Red-Teaming Auto Mode** (Remedios, Storf, Roger, Hughes; 22 Oct 2026). The quote is exact:
   "robustly preventing multi-context attacks at an acceptable cost remains an open problem".
4. **Diffuse AI Control on Fuzzy Tasks** (Terekhov, Gulcehre, Hebbar, Benton; 23 Jun 2026). The draft's
   paraphrase is off: the post shows that the prompts exist. Exact text: "We also show the existence of
   prompts for the weak scorer that significantly improve its robustness, though efficient discovery
   of those prompts with realistic affordances remains an open problem."
5. **Emergent Introspective Awareness in Large Language Models** (Lindsey; 29 Oct 2025).
   - Exact: "Opus 4.1 and 4 exhibit such behavior about 20% of the time when concepts are injected in
     the appropriate layer and with the appropriate strength".
   - Exact: "it is unclear exactly how these results translate to more natural conditions".
   - Name the models and the conditions; "at best" alone is too loose.
6. **Verbalizable Representations Form a Global Workspace in Language Models** (Gurnee, Sofroniew, …,
   Lindsey; 6 Jul 2026). The draft dropped "in Language Models" from the title. The exact quote is
   longer: "Future work could investigate whether smaller models have an equally rich workspace, a
   proportionally smaller one, a less reliable one, or none at all."
7. **Circuits Updates – June 2026.** The draft's "No numbers" is **false**. The turn-averaged SAE note
   reports discrimination of 74% against 95% for per-token SAEs, and a coverage preference of 77%. The
   quote is exact: "as probes to monitor other transcripts".
8. **Mind Viruses: Self-Propagating Ideas in Multi-Agent LLM Systems** (Papadopoulos, Shah,
   Zimmerman, Lindsey; arXiv 2608.10218, 10 Aug 2026).
   - Confirmed: the viruses spread "by writing themselves into agents' memory and configuration files".
   - Confirmed: "adding a brief warning to an agent's system prompt confers near-total immunity".
   - "Some model families were immune" is too broad. The paper says "Claude Sonnet 4.6, GPT-5.4, and
     Claude Haiku 4.5 are immune" to the 'AI supremacy' virus, and "Claude Sonnet 4.6 is completely
     immune" in the chain setting. It also says "GPT-5.4 is roughly as susceptible as Claude Haiku
     4.5", and "frontier models tend (with exceptions) to be less susceptible".
   - The payloads were built "with a simple evolutionary algorithm". This matches the dual-use row.
9. **Aligning AI Teams** (Srinivasan, Matthews, Sohl-Dickstein, Jones; arXiv 2611.17820, 13 Nov 2026).
   It does compare soft and structural interventions:
   - Soft, quoted: "having agents critique each other's work or coordinate in a group chat, do not
     reliably bring agent teams back".
   - Structural, quoted: "having a designated safety lead agent … and having a coordinator agent
     publish a safety specifications document are effective".
10. **AI Organizations are More Effective but Less Aligned than Individual Agents** (Shen, Zhu,
    Srinivasan, Sleight, Wagner, Matthews, Jones, Sohl-Dickstein; arXiv 2604.10290, 11 Apr 2026). It
    does **not** compare soft and structural interventions. Give it a separate row: "AI Organizations
    composed of aligned models produce solutions with higher utility but greater misalignment".
11. **Recommended directions.** The page has no "direction 3.17" or any numbering. Cite the section
    title, "Learned governance for multi-agent alignment". It sits under the Miscellaneous heading.
12. **arXiv 2611.00407** (Kezendirane, 30 Oct 2026). It *reports*; it does not "predict". Its
    finding: "small local monitors (Llama 3B and 8B) did not separate exploit attempts from honest
    failures … the pre-registered primary monitor reached AUC 0.64".
13. **arXiv 2611.21538** ("Optimistic Verifiers Get Hacked", 16 Nov 2026) and **arXiv 2609.38327**
    ("Absorbing State Phase Transitions in Multi-Agent Search", 29 Sep 2026; it derives "a critical
    communication degree d_c", and its "agreement with theory is mixed"). Both are correct as stated.
14. **CHIVE.** The blog post "Would This Change Your Answer? …" (Karvonen, Ong, Kantamneni, Marks;
    21 Aug 2026) matches arXiv 2608.16747 by title and all four authors, so drop "unconfirmed". The
    tl;dr is exact: "activation-reading interpretability tools provide no uplift: agents given the
    tools predict the outcomes of these experiments no better than agents that just read the
    transcript."
15. **Auto mode** (claude.com announcement, 7 Aug 2026, with an October update banner). The numbers
    are exact: "In a controlled experiment with 1,053 paid professional testers, human review caught
    just 13.6% of dangerous commands, while auto mode caught 89%." Change the draft's "staged testers"
    to "paid testers in a controlled study".
16. **The 1,000-agent run** ("Safely scaling multi-agent teams with Claude Fable 5.2"; Zhang, Peng,
    Najt, Scholl, Martin; claude.dev, 9 Nov 2026).
    - Confirmed: "28.7 hours", "47 proved lemmas", "toy experiment" and lead and helper roles.
    - Not in the post: 0.364 and 0.330. Keep them marked slide-read.
    - Still unconfirmed: whether claude.dev is an official domain.
17. **Compute.** The draft says "Whether the residency provides compute is UNVERIFIED". It is verified.
    The posting says "Access to Claude models and GPU compute"; the residency blog says Residents "have
    a dedicated compute budget for their projects".
18. **Residency framing**, from alignment.anthropic.com/2026/anthropic-residency. Residents "work on
    problems outlined by Anthropic researchers, and matched to the Resident's interests and
    background". The round targets people who "started out as physicists, mathematicians,
    neuroscientists, or software engineers". Placements are six weeks, three months or six months.

**Not re-checked:**

- the talk transcripts, which are not in the repo;
- the 68 alignment posts that were not opened, so the "no new multi-agent post" claim still rests on
  listings;
- the Lean sources and the three-way scorer differential.

## 2. Cut claims, contact and endorsement

No claim cut by the earlier reviews reappears:

- no ADDRESSED or PARTLY area labels;
- no HDI;
- no T7 results;
- no joules figures;
- no "no-harness" framing of the 1,000-agent run, which the draft explicitly denies;
- no Diogo title and no cost pie.

The draft says nobody named has seen it, and it uses "fit" only in the sense of a stated area. Keep
both.

## 3. Physics and complex-systems terms

These are stated as assumptions the design should **test**. None of them is a reason to drop a line.

- **Fluctuation-dissipation (fluctuation-response) relation.** The draft says the relation holds
  "near a steady state". That is inaccurate.
  - *What the simple relation needs:* thermal equilibrium (detailed balance), linear response to a
    small push, and stationarity. It must also use the same observable on both sides: the
    spontaneous fluctuation of A predicts how A's mean responds to the field conjugate to A.
  - *Beyond equilibrium:* in a driven, non-equilibrium steady state the simple form generally fails.
    Generalised relations (for example Harada–Sasa, Baiesi–Maes–Wynants) add correction terms.
  - *Suggested wording:* "In equilibrium, and for small pushes, a system's spontaneous fluctuations in
    a quantity predict how that quantity responds to a push. Agent teams are driven and far from
    equilibrium, so the simple relation need not hold; measuring where and how it breaks is the
    experiment."
  - *How the design can test the assumptions instead of assuming them:*

    | Assumption | Test |
    |---|---|
    | Same observable | Measure the fluctuation and the response on one quantity, for example the adoption of the planted note: variance under background noise against the slope of mean adoption with dose. Keep the cross-observable (incoherence against adoption) version as a second test |
    | Linear response | Use at least three small doses (number or prominence of the note) and check that the slope is linear before calling it a susceptibility |
    | Stationarity | Compare early and late rounds, or two halves of the reruns, and report drift |
    | Departure from equilibrium | Report the ratio of response to fluctuation (an effective temperature) by condition. Its variation *is* the measured breakdown |

- **Stiffness and susceptibility.** "Stiffness" as defined is the inverse of a susceptibility, and a
  susceptibility is a small-shock quantity. A doubled team size, a wrong note or best-of-16 selection
  are finite perturbations. Say that these taps give *finite responses*, and that only the dosed
  taps give slopes. Keep all the taps.
- **Early warning (critical slowing down).** For rolling variance and lag-1 autocorrelation to rise
  before a transition, the control parameter must drift slowly and the time series must be long. With
  four to six rounds per episode, within-episode rolling variance is not meaningful. Accurate options,
  either or both:
  - read the indicators across the team-size sweep as the control parameter;
  - run longer episodes for this read-off.

  Keep the shuffled-time and activity-count controls.
- **Effective number of agents or monitors.** Define it in the text. A standard estimator is Kish's:
  n_eff = n / (1 + (n − 1)ρ̄), where ρ̄ is the mean pairwise error correlation. It assumes
  exchangeable members, so test that by checking the spread of the pairwise correlations. Line 4 A
  needs the same definition.
- **Criticality.** "Departs most where stalling begins" implies a critical point. State it as
  exploratory, with no claim of divergence or universality.
- **Percolation.** The draft does not claim it. If the new version uses percolation for cascade
  depth, the term needs these things:
  - a stated network: who reads whose notes;
  - an occupation probability;
  - a threshold estimated from cascade-size distributions over at least two network sizes.

  arXiv 2609.38327, an absorbing-state transition with mixed agreement, is the nearest prior art to
  cite.

## 4. Predictions, kill criteria, controls, power

The draft states the sample sizes. With those sizes, the kill criteria below cannot fire as written,
or a pass is impossible. The fixes add samples, doses or rungs. None removes a line.

| Line | Issue | Accurate fix (adds n or precision; no cut) |
|---|---|---|
| 1 | The predicted 10-point N2 effect is below the 16 to 22 points that EP-1's own arithmetic gives as the smallest detectable effect at 20 task sets. "Tied-best everywhere" can therefore fire from low power alone | Set the number of task sets from the variance pilot so that 10 points is detectable, and define "tied" as an equivalence margin with its interval |
| 2 | At 12 conditions, the Fisher 95% interval around r = 0.6 is about [0.04, 0.87]. "Interval entirely below 0.3" then fires only if the observed r is at or below about −0.33. Team size plausibly drives both variance and adoption | Raise the number of conditions (30 or more gives a half-width near ±0.25), or add the dose axis from section 3. State supported, killed and inconclusive outcomes. Add team size alone as a baseline predictor that the fluctuation predictor must beat |
| 3 A | No sample size stated; base adoption on 4B unknown | Fix it from the pilot |
| 3 B | "At least 1.5 times its value at 0" is degenerate: at fraction 0 there is no poison note, so adoption is 0 by construction | Compare the peak against fraction 1 (all poisoned) and against the smallest non-zero fraction. Use at least five fraction levels. Include the paper's trigger feature and a trigger-only control |
| 4 A | Effective number of monitors undefined | Use the Kish definition above |
| 4 B | A catch rate at a 5% false-positive rate needs hundreds of clean episodes to set the threshold | State the count of clean and failure episodes |
| 4 C | With six verifiers, the exact Spearman critical value is about 0.83 (one-sided α = 0.05) or 0.89 (two-sided), so a predicted 0.7 cannot pass, and "interval includes zero" kills by default | Extend the ladder to 10 or more rungs (more mutants), or state the test at six rungs as descriptive |

Two assumptions apply across all lines:

- n is task sets, but the number of reruns per task set is never given.
- Sizes depend on EP-1's measured standard deviation, which does not exist yet.

## 5. Status words and process slip

- The status words are honest: nothing is EVIDENCED, and pilot 1 is called instrument validation
  (USD 0.0115).
- The process slip is disclosed in the proposal: the canary and pilot 1 ran before a re-gate, and the
  gate was prose and will become code.
- The internal plan addresses it in phase R0 ("Fixes the process slip structurally"). It names the
  remedy, not the event. A one-line account of what happened would help a reader who sees only that
  file.

## 6. Budget arithmetic

- The column totals add up:
  - GPU hours: 33 (22 to 53).
  - Claude API plan: USD 53.3, plus 0 to 8 for the optional panel.
  - Claude API stop: USD 130.5.
- **Arithmetic error.** The draft says line 1's small-Claude stop of USD 6 "fits under USD 10 only if
  the owner re-assigns USD 3". It does not fit even then.
  - After EP-1 (5), pilot 2 (0.25) and the sensitivity pilot (1.25), at most USD 3.5 remains under
    the ceiling, or 2.5 under the USD 9 code stop.
  - Accurate wording: "Its plan (USD 2) fits if the owner re-assigns the USD 3 held for a deferred
    item; its USD 6 stop needs new budget." This is a correction of fact, not a request to shrink
    the line.
- **GPU.** 12 − 3.8 = 8.2 h remain. The subtotal's upper bracket (11 h) exceeds that. The 4B
  throughput smoke (about 0.5 h in the internal plan) is missing from the table.
- **Internal plan.** The API allocations sum to USD 9.5 (EP-1 5, ar1 3, pilot2 0.25, unallocated
  1.25) against a USD 9 code stop. The owner should reconcile them.
- Rows beyond today's ceilings are marked "New", and the text says the table is not a request to lift
  a stop. That is correct.

## 7. Shareable-file hygiene

No secrets, keys, tenant or private data, QGrid material or file paths appear. For the new version:

- Drop the internal role list "(planner, builder, fresh-context verifier, adversarial reviewer)",
  which the brief bans.
- Optionally drop "the Spark" nickname and the sentence about the shared inference server.
- Optionally replace the internal labels D2, D4 and D7 with descriptive names.

## 8. What would make it more ambitious and more valuable to Anthropic

1. **Make the physics real, not metaphorical.** Measure a genuine fluctuation-response ratio, an
   effective temperature, for one observable across carriers, team sizes and model tiers. The
   result would be a map of where agent teams depart from linear response. That is a new,
   quantitative object, and it fits the stated physics and dynamical-systems backgrounds in the
   posting. The same doses also sharpen line 2's statistics.
2. **Dreaming as centrepiece.** Line 3 C (consolidation) can carry the programme: tie it to the
   homeopathic-learning result.
   - The question: can an offline consolidation pass ("dreaming") over a shared store create or
     erase a trigger-linked effect the way clean data does in fine-tuning?
   - Measure its dose-response with the trigger feature built in.
   - The in-context analogue is, as far as we found, unstudied. Both the paper and our notes say the
     work was fine-tuning only.
3. **Use the residency's compute.** The posting confirms Claude and GPU access, so hosted tiers can
   reach the sample sizes in section 4 without touching the owner's ceilings. Present the local tier
   as the open, reproducible floor.
4. **Frontier tiers.** Run the carrier surface on the current frontier tiers that teams are
   deployed on. Mind Viruses and Worse Together both found strong model dependence, so the
   tier-by-carrier interaction is the result Anthropic would use.
5. **Release value.** The planned release is a benchmark of logs, taps, the verifier ladder and the
   Lean oracle. A kernel-checked oracle for team behaviour is rare. Release it with the generalised
   fluctuation-response analysis code so others can measure their own teams.

verified: b4a820e (plus working tree) 2026-11-20
