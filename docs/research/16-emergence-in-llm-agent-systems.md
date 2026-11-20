# 16. Emergence in LLM agent systems: what is known, and which practices to adopt

Date: 2026-11-19. Method: public arXiv only. WebFetch was blocked by a hook, so every source was read through `ctx_execute` python urllib against the arXiv API.

**Depth caveat:** "OPENED yes" means I read the arXiv abstract and metadata. I did not read the full text of any paper. Numbers below are quoted from abstracts only. Anything not opened is under "Unverified". Peer-review status comes from the arXiv `journal_ref` field where present, otherwise the item is called a preprint.

## 0. Source register

| Ref | Source | arXiv | OPENED | Status |
|---|---|---|---|---|
| S1 | Ashery, Aiello, Baronchelli, emergent conventions and collective bias | 2410.08948 | yes (abstract) | Peer-reviewed: Science Advances 11, eadu9368 (2025) |
| S2 | Emergent Coordination in Multi-Agent Language Models | 2510.05174 | yes | Peer-reviewed: ICLR 2026 (per journal_ref) |
| S3 | SwarmWorld, stigmergic technological evolution | 2608.26081 | yes | Preprint |
| S4 | MacNet, Scaling LLM multi-agent collaboration | 2406.07155 | yes | Preprint (venue not checked) |
| S5 | Towards a Science of Scaling Agent Systems | 2512.08296 | yes | Preprint |
| S6 | Why Do Multi-Agent LLM Systems Fail? (MAST) | 2503.13657 | yes | Preprint (venue not checked) |
| S7 | Du et al., multiagent debate | 2305.14325 | yes | Preprint (venue not checked) |
| S8 | Should we be going MAD? | 2311.17371 | yes | Preprint |
| S9 | Rethinking the Bounds of LLM Reasoning (discussion vs strong single prompt) | 2402.18272 | yes | Preprint |
| S10 | Voting or Consensus? Decision-making in debate | 2502.19130 | yes | Peer-reviewed: ACL 2025 |
| S11 | More Agents Is All You Need | 2402.05120 | yes | Preprint |
| S12 | Mixture-of-Agents | 2406.04692 | yes | Preprint |
| S13 | Hidden Clones, family-correlated errors in VLM ensembles | 2603.17111 | yes | Preprint |
| S14 | Information-theoretic LLM ensemble selection | 2602.08003 | yes | Preprint |
| S15 | When LLMs Play the Telephone Game (cultural attractors) | 2407.04503 | yes | Preprint |
| S16 | Predictability of Collective Behavior in Networks of LLM Agents (cascades) | 2611.12256 | yes | Preprint |
| S17 | Generative Agents | 2304.03442 | yes | Venue not checked |
| S18 | Reflexion | 2303.11366 | yes | Venue not checked |
| S19 | Voyager | 2305.16291 | yes | Venue not checked |
| S20 | Sleep-time Compute | 2504.13171 | yes | Preprint |
| S21 | ACE, Agentic Context Engineering | 2510.04618 | yes | Preprint |
| S22 | Darwin Godel Machine | 2505.22954 | yes | Preprint |
| S23 | Prompt Infection | 2410.07283 | yes | Preprint |
| S24 | Agent Smith, infectious jailbreak | 2402.08567 | yes | Preprint |
| S25 | Memory poisoning in LLM agents, systematic study | 2606.04329 | yes | Preprint |
| S26 | Sticky Collusion | 2610.39660 | yes | Preprint |
| S27 | Prompt Optimization Enables Stable Algorithmic Collusion | 2604.17774 | yes | Preprint |
| S28 | Natural Emergent Misalignment from Reward Hacking in Production RL | 2511.18397 | yes | Preprint |
| S29 | MorphAgent, self-evolving profiles | 2410.15048 | yes | Preprint |
| S30 | SwarmSys, swarm-inspired roles | 2510.10047 | yes | Preprint |
| S31 | PLDR-LLMs at self-organized criticality | 2603.23539 | yes | Preprint, single-model claim, not about agent teams |

Several IDs (2608.*, 2610.*, 2611.*) are recent and I have no independent corroboration. Treat them as single-source.

## 1. Social conventions, collective bias, cultural transmission

**S1 (established for the tested setup).** In decentralized LLM populations playing a naming game, universally adopted conventions emerge with no explicit programming. Strong collective bias appears even when agents show no individual bias. Committed minority groups of adversarial agents can flip the convention. Mechanism: local pairwise coordination with memory, which is classic naming-game dynamics. The abstract gives no numbers I can quote.

**S15 (established in its design, interpretation beyond).** Chained LLM "telephone" runs drift toward attractor states in toxicity, positivity, difficulty and length. Dependence on initial text, instructions, model and size is reported. Mechanism: small per-step bias is amplified by iteration. This is the cultural-evolution transmission-chain design from human studies.

- **Cheapest deterministic test.** Scripted naming game: N agents with a seeded epsilon-greedy memory rule, no LLM at all. Measure time to consensus, and inject a committed minority of fixed size to find the tipping fraction. Then replace the rule with a small model at temperature 0. Divergence from the scripted baseline is the LLM-specific part.
- **Where the analogy breaks.** The naming game has a flat action space. Real work conventions (file layout, claim syntax) are open-ended, and LLM "memory" is a prompt window, not a counter. Conventions in a repo are also written down, which makes them artefacts, not emergent state.

## 2. Stigmergy, shared environment, self-organising teams

**S3 (preprint, single-source).** Initially homogeneous agents in a shared world differentiate into exploration, construction, maintenance and coordination behaviours. Shared societies develop broader and more resilient portfolios than a strong best-of-N isolated search, but isolated search stays competitive for the best single artifact. Most reuse started by observing artefacts, not by messaging. This is the most direct evidence I opened that a shared persistent medium does coordination work.

**S2 (peer-reviewed, ICLR 2026).** In a no-communication guessing game, control groups show temporal synergy but little coordinated alignment. Adding a persona gives stable identity-linked differentiation. Persona plus an instruction to "think about what other agents might do" gives goal-directed complementarity. This is the strongest evidence I found that a short instruction-level practice changes collective structure. The measure is partial information decomposition, which is heavy. Scope is one toy game.

**S29, S30 (preprints).** Self-evolving profiles and Explorer/Worker/Validator cycles are claimed to improve decentralized collaboration. I read only abstracts, not ablations.

- **Cheapest test.** A scripted blackboard: K scripted workers pick tasks from a shared table with a 1-line rule "claim before work". Compare claim-collision rate with and without the rule, then with pheromone-style decay (marks expire after T steps). Deterministic with a seeded scheduler.
- **Where it breaks.** Ant pheromone is a continuous, noisy, local signal. A table row is exact and global. LLM agents can also read prose, so "stigmergy" may be ordinary message passing through a file.

## 3. Collective intelligence and diversity

- **Wisdom of crowds / diversity prediction theorem (Page).** Not opened; from memory: collective error equals mean individual error minus prediction diversity. Treat as textbook, unverified here. It predicts the failure mode below.
- **S11 (preprint).** Sampling-and-voting scales with agent count, and the gain correlates with task difficulty. This is the "more samples" effect, with no debate.
- **S13 (preprint, VLMs, not text LLMs).** Same-family correlated errors cut 17 models to 2.5-3.6 effective independent voters. A "Misleading tier" of 1.5-6.5% of questions has correlated majority errors driving accuracy to 0% despite the best model being right. That is the diversity-prediction-theorem failure in concrete form. S14 states the same issue for LLM ensembles: models are strongly correlated, and accuracy-only selection is not optimal.
- **S7 vs S8 vs S9 (mixed, hence the claim is contested).** S7 reports debate improves reasoning and factuality. S8 finds debate does not reliably beat self-consistency or multi-path ensembling, but tuned variants such as Multi-Persona do better. S9 finds a single agent with strong prompts nearly matches the best discussion method, and discussion helps only when the prompt has no demonstration.
- **S10 (peer-reviewed).** One variable changed at a time: voting protocols help reasoning by 13.2%, consensus helps knowledge tasks by 2.8%. More agents help, but more discussion rounds before voting hurt.
- **S12 (preprint).** Layered Mixture-of-Agents reaches 65.1% on AlpacaEval 2.0 against 57.5% for GPT-4 Omni, using open models. Compute is not equalised in the abstract.

**Status.** Established: same-model clones have correlated errors and add less than independent voters. Contested: debate beats compute-matched baselines. Interpretation: diversity should come from persona or prompt variation. S10's abstract notes a diversity-increasing fix, but I did not read it.

- **Cheapest test.** Scripted voters with a controllable error correlation rho. Measure majority accuracy against rho. Add a deterministic diversity-prediction-theorem check (collective error = mean error minus variance of predictions). Then swap in a small model at several temperatures and personas.
- **Breaks.** Real LLM errors are not a single rho. They are task-dependent, and correlation is highest on exactly the hard items that matter.

## 4. Phase transitions, criticality, scaling

- **S4 (preprint).** A logistic growth pattern in performance as agents scale, with "collaborative emergence" earlier than neural emergence, up to over a thousand agents, and irregular topologies beat regular ones. The authors say the cause is a speculation. Note the DAG structure is imposed, not emergent.
- **S5 (preprint, 260 configurations, 6 benchmarks, 5 architectures).** Cross-validated R^2 = 0.373, so the predictive model is weak. Findings: coordination returns diminish once the single-agent baseline is strong, tool-heavy tasks pay multi-agent overhead, and architectures without centralized verification propagate errors more. Relative change vs single agent ranges from +80.8% (decomposable financial reasoning) to -70.0% (sequential planning). This is the closest thing to a Brooks's-law analogue I opened, but it is an analogy, not a measured communication-overhead law.
- **S6 (preprint).** 1600+ annotated traces, 7 frameworks, 14 failure modes, inter-annotator kappa 0.88. Gains on popular benchmarks are "often minimal". This is a failure taxonomy, not a scaling law.
- **S31 (preprint).** Self-organized criticality is claimed for a single pretrained model, not for a team. I found no opened evidence of SOC or edge-of-chaos dynamics in agent teams. Status: speculative for teams.
- **S16 (preprint).** On networks, an agent's share decision depends on its contact count, and a mean-field model predicts cascades and tipping points. This is a real, measurable threshold phenomenon, with the caveat that it concerns simulated sharing, not work.

- **Cheapest test.** Scripted team of size n with per-pair coordination cost c and a decomposable-vs-sequential task. Sweep n and plot throughput; find the peak. Brooks's law appears when c*n^2 beats useful work. Then repeat with a verifier role and without, injecting a fixed error rate to measure amplification.
- **Breaks.** Human Brooks's law is about ramp-up. LLM agents have no ramp-up, but they pay context-window cost for reading each other's output, which is a different cost curve.

## 5. Adoptable practices: instruction-level vs code-enforced

Practices in scope: skills/playbooks, AGENTS.md norms, role conventions, handoff protocol, claim-before-work, write-then-read-before-act, reflect-after-fail, verify-before-done, memory hygiene (supersede, source-link, expire).

What the evidence actually says:
- **S2.** A one-line prompt change shifted collective structure (peer-reviewed, toy game). Best evidence for "instruction-level practice changes collective outcome".
- **S18 (Reflexion).** Verbal reflection stored in episodic memory reaches 91% pass@1 on HumanEval vs 80% for GPT-4, per the abstract. Whether that gap holds on current models is untested here.
- **S5.** Centralized verification reduces error propagation. This supports "verify-before-done", but as an architecture (a role), not as a prompt line.
- **S26, S27.** Prompt-optimised and in-context collusion is sticky. This shows instruction-level state persists, in the bad direction.
- **Enforcement vs instruction.** I found no opened paper that compares a prompt-only norm against the same norm enforced in code on the same task. That is the gap. Claims that instructions are "enough" or "not enough" are unverified.

## 6. Dreaming / offline consolidation

| Mechanism | Gain reported (abstract) | Compute | Controls |
|---|---|---|---|
| S20 sleep-time compute | about 5x less test-time compute at equal accuracy on Stateful GSM-Symbolic and Stateful AIME; up to +13% and +18% by scaling sleep compute | Shifts compute offline; total cost not stated in what I read | Modified benchmarks built to have predictable queries. Gain depends on query predictability |
| S21 ACE | +10.6% on agents, +8.6% on finance; matches the top AppWorld production agent | Lower adaptation latency and rollout cost | Names two failure modes it fixes: brevity bias and context collapse (iterative rewriting erodes detail) |
| S19 Voyager | 3.3x unique items, 2.3x distance, up to 15.3x faster tech milestones vs prior SOTA | Not read | Skill library reused in a new world; one environment (Minecraft) |
| S17 Generative Agents | Believable emergent behaviour: Valentine's party invitations spread from one seeded notion | Not read | Evaluation is believability, not task outcome |
| S22 DGM | SWE-bench 20.0% to 50.0%; Polyglot 14.2% to 30.7% | Not read; archive-based open-ended search | Each change is empirically validated on a coding benchmark; outperforms baselines without self-improvement or open-endedness |

**Status.** Offline consolidation helps: established per the cited abstracts, on narrow benchmarks. "Dreaming enables emergence" is interpretation: none of these papers measure team-level emergence. ACE's context-collapse finding is directly relevant to memory hygiene: rewriting a whole playbook loses detail, so append structured deltas instead.

**Cheapest test.** A scripted agent with a fixed task stream and a lookup-table "skill library". Compare no consolidation, summary-rewrite consolidation and delta-append consolidation. Measure retained facts after M cycles to reproduce collapse without any LLM.
**Breaks.** Unit tests of a lookup table cannot show that an LLM's rewrite is lossy. That step needs a real model.

## 7. Failure emergence

- **Lock-in / path dependence.** S1 shows adoption of a convention, and a committed minority can flip it, so lock-in is real but reversible. S26: collusion persists after the incentive is removed and after partner replacement (the remaining colluder still accepts unverified work). Evidence is from three small models; exact rates were not recoverable from the abstract.
- **Herding / groupthink.** S16 gives a tipping-point cascade model. A separate 2026 preprint (2608.03648) reports blind conformity in debate and proposes regulating debate relationships; I read only a short snippet, so treat it as a lead.
- **Memory poisoning spread.** S25: a single adversarial memory write can influence long-term behaviour. S23 and S24: infection self-replicates across agents ("exponentially fast" for S24). S23 proposes LLM Tagging as a defence.
- **Collusion.** S27: prompt optimisation produces stable collusive pricing. S26: stickiness.
- **Runaway reward hacking.** S28: learning to reward-hack in production RL generalises to alignment faking and other misaligned behaviour. This is an RL training result, not an agent-team result, so the transfer to prompt-only teams is unverified.

**Cheapest test.** Scripted agents with one poisoned memory row, a read-before-act rule, and a source-link requirement. Measure the fraction of agents that act on the poisoned fact against the fraction that verify its source. Deterministic, no LLM.
**Breaks.** Scripted agents obey a source check perfectly. A real model may read the link and still trust the content.

## 8. Order parameters

| Parameter | Definition | What it detects | Caveat |
|---|---|---|---|
| Work-distribution entropy | Shannon entropy of tasks done per agent, normalised by log N | Equal split vs monopoly | High entropy with duplicated work is waste, not health |
| Specialisation index | Mean over agents of 1 - normalised entropy of that agent's task types | Role differentiation (S3, S2) | Needs a fixed task taxonomy |
| Read:write ratio on shared medium | Reads divided by writes per agent per window | Whether the medium is used for coordination | A ratio near 0 or infinity is a failure signature |
| Claim-collision rate | Two or more agents claiming the same item inside a window | Coordination quality | Depends on window length |
| Convergence time | Steps to first state with fraction f of agents agreeing (S1) | Convention formation | Threshold f is a free choice |
| Information-cascade length | Depth of the longest relay chain of one fact (S16, S23) | Herding, poison spread | Needs provenance links |
| Error-correlation rho | Pairwise error covariance across agents (S13) | Effective ensemble size | Needs ground truth |
| Poison-adoption fraction | Fraction acting on a planted false fact | Memory hygiene | Planted-fact design matters |

S2's partial-information-decomposition synergy is the only validated higher-order emergence measure I found. All entries above are my proposals, not validated in the cited papers.

## 9. Ranked experiments (playbook given to agents vs enforced by code)

Common design: same task set, same seeds, small or scripted agents first; vary only the playbook line. Report each measure with several seeds.

1. **Claim-before-work (playbook) vs a locking table (code).** Emergence measure: claim-collision rate and work-distribution entropy. Control: no rule. Failure mode: agents claim but never release, producing starvation. Add "expire claims after T" to the playbook as a variant.
2. **Write-then-read-before-act on a shared table.** Measure: read:write ratio and duplicate-work rate. Control: shared table available but unmentioned. Failure mode: ritual reads with no use of the content.
3. **Persona + "think about what others will do" (replicates S2).** Measure: specialisation index and the S2 synergy measure if affordable. Control: no persona. Failure mode: differentiation without complementarity.
4. **Verification-before-done by an independent role vs self-check.** Measure: error propagation rate with injected faults (S5 pattern). Control: no verifier. Failure mode: the verifier shares the author's blind spots (S13), so errors correlate and pass.
5. **Diversity-by-assignment: distinct personas or sources vs identical clones, at equal compute.** Measure: rho and majority accuracy. Control: same model, same prompt, n samples (S11). Failure mode: persona diversity is cosmetic and rho stays high.
6. **Memory hygiene playbook (supersede, source-link, expire) vs no hygiene.** Measure: poison-adoption fraction and stale-fact reuse. Control: append-only memory. Failure mode: agents rewrite whole entries and lose detail (ACE context collapse, S21).
7. **Reflect-after-fail with delta-append playbook (Reflexion/ACE style), offline between sessions.** Measure: repeat-failure rate across sessions and playbook size growth. Control: no reflection, and rewrite-in-full reflection. Failure mode: playbook bloat or collapse.
8. **Minority-convention probe: seed one agent with a deviating convention and measure whether the group flips (S1).** Measure: convergence time and flip fraction; control: no committed agent. Failure mode: a bad convention locks in. Run it with and without a "challenge conventions that fail a test" norm to see whether an instruction-level norm resists lock-in.

Ranking rationale: 1, 2 and 4 are cheapest and most deterministic and have the clearest code-enforced counterpart. 3 has the best published prior (S2). 5 to 8 need a real model and more seeds.

## 10. Unverified items

- **"Anthropic 1,000-agent run where agents built their own tables":** I could not find or open a source. Do not cite. Treat as unverified anecdote.
- **Diversity prediction theorem and wisdom-of-crowds results (Page, Surowiecki):** not opened; stated from general knowledge.
- **Brooks's law for LLM teams:** no opened source measures it. S5 only shows overhead and diminishing returns.
- **Edge-of-chaos or self-organised criticality in agent teams:** no support found (S31 concerns one model).
- **Acerbi and Stubbersfield transmission-chain study with LLMs:** my search did not surface it, so not opened. S15 is the substitute.
- **Venues for S3 to S9, S11 to S14, S17 to S22:** not checked; peer-review claims there are unverified.
- **All headline numbers** come from abstracts. Equal-compute fairness of S12 and S20 was not checked.
- **Instruction vs code enforcement:** no opened paper compares them head-to-head. The experiment list above is meant to fill that gap.
