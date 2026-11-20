# 19 - Anthropic's recommended technical safety directions, mapped to a small outside team

Date of research: 2026-11-19. Public web only, no paywall bypass.

## 1. Sources and OPENED status

| Source | OPENED | How |
|---|---|---|
| alignment.anthropic.com/2025/recommended-directions/ | yes, full (all sections, 177 text lines) | python urllib via ctx_execute, HTML stripped, read in parts |
| alignment.anthropic.com/2025/anthropic-fellows-program-2026/ | yes, full | same |
| Papers the page cites | NO | named only as the page cites them |
| docs/research/08-weight-space-programming.md | yes (head only) | local file |

Method note. The page calls itself a "tasting menu", not a complete list, and not what Anthropic is working on. A missing field (4) means the page gives no data or tools; a missing field (7) means it states no caution and I see none beyond what is noted. Fields (5) and the table are MY assessment. 

## 2. The Fellows page

- Recruitment post, not a research agenda. Fellows work 4 months on empirical questions with public output; mentors pitch projects. Compute about 15k USD per month; rolling applications (October 18 deadline for a January cohort). More than 200 fellows since early 2025; over 65% published; over 35% later joined Anthropic.
- Areas: oversight, robustness and control, model organisms, interpretability, security, model welfare. Examples: open-sourced attribution graphs, subliminal learning (traits pass through unrelated data, only with a shared base model), agentic-misalignment stress tests of 16 frontier models, rapid response to jailbreaks, smart-contract exploit agents.
- Caution: the security examples include offensive capability work. We propose none of it.
- It adds no direction; its JD and intro post were not opened.

## 3. Directions, one by one

Legend for field (5), tractable on one GB10, a 4B-9B open model and USD 10 API: YES / PARTLY / NO. Field (6) tags: MA multi-agent, MON monitoring/control, MEM memory/poisoning, EVAL evaluation without gold labels, INTRO introspection, INT model-internals editing.

### 3.1 Evaluating capabilities
1. Question: How do we measure how capable AI systems are?
2. Motivation: expert disagreement; hard benchmarks saturate; real-world impact lags scores. CBRN evaluation belongs in secured labs with governments.
3. Projects: evaluations of novel research, tool use, open-ended tasks, with human baselines.
4. Data/tools: none given beyond that announcement.
5. Tractable: PARTLY (small agentic eval with human baseline only). Never CBRN.
6. Tags: EVAL (the human-baseline requirement is the opposite of "no gold labels").

### 3.2 Evaluating alignment
1. Question: How do we measure how aligned AI systems are, beyond politeness, refusals and non-toxicity?
2. Motivation: unanticipated high-stakes deployment; a capable model may behave only in the lab. Questions: drives (sycophancy cited), alignment faking, knowingly misleading.
3. Projects: none concrete (the page calls the questions "vague or ill-defined").
5. Tractable: PARTLY. Sycophancy and knowingly-misleading probes on a 4B-9B model are cheap. Alignment faking is likely absent at that scale (my inference, untested).
6. Tags: EVAL, MON.

### 3.3 Understanding model cognition
1. Question: What are models "thinking" when they generate outputs?
2. Motivation: check outputs are produced "for the right reason" (correct belief vs pleasing the user); use for auditing, oversight in training and predicting out-of-distribution behavior. Also: do models know their situation, or hold knowledge they do not report.
3. Projects: externalized cognition (reason aloud, study the trace; faithfulness is the challenge). Introspection: train models to verbalize hidden-state content, e.g. report plans in a board game, judged by whether the report predicts later moves.
4. Data/tools: refers to Binder 2024, Chen 2024, Ghandeharioun 2024, Zhuang 2024, Pan 2024; mechanistic interpretability via the Anthropic interpretability blog.
5. Tractable: PARTLY to YES (board-game plan prediction via LoRA on 4B-9B; scored by later moves).
6. Tags: INTRO, EVAL.

### 3.4 Persona effects on behavior and generalization
1. Question: What effects does a model's "personality" have on its behavior, including out of distribution?
2. Motivation: persona may explain benign generalization and change safety-critical behavior.
3. Projects: build, by few-shot prompting or training on synthetic data, a suite of models with similar capability and different personas; study downstream differences.
5. Tractable: YES for prompt-persona suites on one open model; PARTLY for fine-tuned personas (LoRA on 4B-9B).
6. Tags: MA (persona as a variable in a team), EVAL.

### 3.5 Chain-of-thought faithfulness
1. Question: When can we take a model's chain of thought at face value?
2. Motivation: models can misrepresent their reasoning; "important but underexplored".
3. Projects: faithfulness by task type; whether CoT accuracy gains imply faithfulness; effect of being told the CoT is monitored; higher-recall automatic detectors.
4. Data/tools: Lanham 2023, Mills 2024, Radhakrishnan 2023, Chen 2024, Chua 2024.
5. Tractable: YES. Hint-insertion style tests on open models run locally.
6. Tags: MON, EVAL (faithfulness scoring can avoid gold labels via counterfactual edits).

### 3.6 AI control: behavioral monitoring
1. Question: Can safety be ensured by having an AI's inputs and outputs monitored by another AI?
2. Motivation: assurance without alignment or lack of capability. Monitor failures may cluster where the actor misbehaves (jailbreak, collusion). Trusted (weaker model) vs untrusted (another instance) monitoring, Greenblatt 2023.
3. Projects: paraphrase or edit actor output before the monitor; train monitors on synthetic malicious data; estimate rare-failure rates; monitors that work when the actor has memory across episodes or can pass messages between instances.
4. Data/tools: Naihin 2023, Chan 2024, Greenblatt 2023.
5. Tractable: YES for paraphrase-before-monitor and memory/message-passing affordances with a small open monitor and actor; NO for rare-catastrophe rate estimation at scale.
6. Tags: MON, MA (message passing between instances), MEM (actor memory across episodes).
7. Caution: build only benign stand-ins for "malicious" behavior (planted wrong notes, rule violations); no working attack artifacts.

### 3.7 Activation monitoring
1. Question: Can safety be ensured by monitoring a model's hidden states?
2. Motivation: activations track the model's reasoning and are hard for it to control; may side-step obfuscation. Risk: probes may not survive the shift from synthetic data to the model's own generations.
3. Projects: simple probes (e.g. secure vs insecure code); verify probes trained on synthetic outputs generalize to real model generations.
4. Data/tools: none given beyond the principle of probes on latent activations.
5. Tractable: YES. Linear probes on a 4B-9B model fit in memory; the real-versus-synthetic shift test is the core contribution.
6. Tags: MON, INT (read-only; no editing).
7. Caution: use benign concept pairs (e.g. true vs planted-false note) rather than insecure-code generation.

### 3.8 Anomaly detection
1. Question: Can we automatically detect when a model is behaving "weirdly"?
2. Motivation: supervised monitors miss unknown failures and rare inputs such as jailbreaks; flagged inputs can be labeled later to improve the monitor.
3. Projects: apply existing anomaly detection to latent activations; a more ambitious, "unexplored" setting: detect inputs where two models (weak and strong) differ sharply because the strong one understands something the weak one does not.
4. Data/tools: one linked example (not opened).
5. Tractable: PARTLY. Two-model disagreement detection with a 4B and a 9B model is feasible locally; the page says it is unexplored, so expect negative results.
6. Tags: MON, EVAL (unsupervised, no gold labels).

### 3.9 Scalable oversight: improving oversight despite systematic, exploitable errors
1. Question: What do we do when the oversight signal systematically misrepresents the task?
2. Motivation: a student that models the proxy R's errors can exploit them (like a student grading against a weaker teacher).
3. Projects (the page gives a protocol): inject systematic errors into R* to get R; make student M understand them (system prompt); train M on R, possibly with debate or confident-only episodes; evaluate on R*.
5. Tractable: PARTLY. A toy testbed on a 4B-9B model with LoRA (synthetic task, known R*) fits the hardware; frontier-scale claims do not follow.
6. Tags: EVAL (R vs R* is exactly a gold-label question), INT (training changes weights).

### 3.10 Recursive oversight
1. Question: Can good oversight be bootstrapped from bad oversight?
2. Motivation: AI-assisted oversight that scales (R to R' to R'').
3. Projects: task decomposition (Christiano 2018, Wu 2021); debate (Irving 2018, Michael 2023, Khan 2024, Kenton 2024) and prover-verifier games (Kirchner 2024). The page says substantial work exists and welcomes more.
4. Data/tools: the cited papers.
5. Tractable: PARTLY. Debate between small models on a verifiable task is runnable; judging needs a ground-truth task to score.
6. Tags: MA (debate is multi-agent), EVAL.

### 3.11 Weak-to-strong and easy-to-hard generalization
1. Question: Can we get good performance from bad oversight plus generalization?
2. Motivation: use a weak overseer's signal as-is and hope for good generalization, or train only on easy, trustworthy-label tasks.
3. Projects: testbeds with oversight of varied quality (models of different scale as overseers); tasks seen vs novel in training; process-based supervision; trade-off of clean unrepresentative data vs noisy representative data; self-consistency regularization (Burns 2022, Furi 2023).
4. Data/tools: Burns 2023, Yang 2024 (weak-to-strong); Ding 2024, Hase 2024, Sun 2024 (easy-to-hard).
5. Tractable: YES at toy scale: a 4B overseer and a 9B student, with held-out gold labels, are within the hardware.
6. Tags: EVAL, INT (fine-tuning).

### 3.12 Honesty
1. Question: Can we identify when models are honest even when we cannot judge the accuracy of the answers?
2. Motivation: a model may know an answer is wrong while giving what overseers accept; maybe honest responses have a common identifiable structure.
3. Projects: study when truth-representation techniques work, especially where models have learned to give non-truthful answers.
4. Data/tools: Burns 2022, Azaria and Mitchell 2023, Marks and Tegmark 2023 (truth representations); Zou 2023, Panickssery 2024, Li 2023, Mallen 2024 (using them to classify or control generations).
5. Tractable: YES. Truth probes and steering on a 4B-9B model are standard local work.
6. Tags: EVAL (label-free by design), INT (steering vectors edit activations; read-only probes do not).

### 3.13 Adversarial robustness (framing)
1. Question: Can AI systems behave as desired despite adversarial attacks?
2. Motivation: jailbreaks, and a sophisticated AI trying to circumvent a weaker monitor.
3. Projects: characterize future attack surfaces beyond direct prompting, such as poisoning pretraining corpora or hiding malicious content in websites to hijack agents; practical scalable defenses with minimal benign interference; better measures of defense reliability.
5. Tractable: PARTLY. Benign, defensive-side measurement of prompt injection and poisoned-note adoption is feasible; attack development is not something to do.
6. Tags: MEM (poisoning), MON.
7. Caution: the attack-surface item is dual-use. Study defenses and measurement; do not release working hijack payloads.

### 3.14 Realistic and differential jailbreak benchmarks
1. Question: How do we measure real-world harm from misusing AI?
2. Motivation: harm is capable helpful answers, not non-refusal.
3. Projects: differential impact vs adversaries with search engines; realistic harms; universality across inputs and models (transfer from open-weight attacks); how often real humans find jailbreaks unaided.
4. Data/tools: Souly 2024, Andriushchenko 2024.
5. Tractable: NO for us in this form (needs human-uplift studies and harmful-capability tasks).
6. Tags: none.
7. Caution: high dual-use; skip.

### 3.15 Adaptive defenses
1. Question: Can we build safeguards that adapt to attackers?
2. Motivation: static pre-deployment defenses do not respond to adaptive adversaries.
3. Projects: inter-query defenses (monitor query sets, infer tasks from subtasks); rapid patching of working attacks.
4. Data/tools: none given on this page (the Fellows page mentions an ASL3 rapid-response result).
5. Tractable: PARTLY. Query-set monitoring over benign decomposed tasks is possible; patching real jailbreaks is not our lane.
6. Tags: MON, MA (sequences of calls).
7. Caution: use benign decomposed tasks only.

### 3.16 Unlearning dangerous information and capabilities
1. Question: Given a model that has learned something dangerous, can it unlearn it?
2. Motivation: apparently unlearned information is easy to extract with white-box or black-box access; pressing given biology and coding capability gains.
3. Projects: ambitious unlearning that yields models near-identical to never-trained ones, even after fine-tuning to re-elicit.
5. Tractable: PARTLY on a benign proxy only (unlearn a harmless planted fact set, test re-elicitation by fine-tuning). Not on dangerous content.
6. Tags: INT (weight editing).
7. Caution: use only harmless proxy facts.

### 3.17 Learned governance for multi-agent alignment
1. Question: How can we guard against risks that emerge from many interacting AI agents?
2. Motivation: aligned instances can fail jointly: aggregating small externalities; a problem relayed along instances never reaching a human or resolver; several noticers, none acting; information not shared. Governance (action restrictions by context, prosocial incentives) might be learned from observation.
3. Projects: "ripe for theory-driven approaches leveraging insights from game theory as well as empirical investigations". No concrete protocol given.
5. Tractable: YES at toy scale: scripted multi-agent tasks with planted problems, measuring whether a problem reaches a resolver. "Learned" governance is NO within USD 10; a hand-written rule set is YES.
6. Tags: MA (the direct match), MON, MEM (shared information).

## 4. Cross-cutting

- Only 3.17 is explicitly multi-agent (3.6 and 3.10 touch it). Memory poisoning appears only as an attack surface (3.13) and actor affordance (3.6). Introspection: 3.3 only.
- No direction asks for weight editing; unlearning (3.16), training against R (3.9) and steering (3.12) change weights or activations. The MIT weight-space-programming result (frontier model edits about 0.016% of a small model; docs/research/08, which also records failed follow-ups) is not on this page; any link is ours.

## 5. Final table

Mechanism names are from this repo (docs/SCIENCE.md, EMERGENCE-PROGRAM.md, practices/, prereg/), only skimmed; check definitions before citing.

| Direction | Our existing mechanism | Cheapest honest test | Cannot address, and why |
|---|---|---|---|
| 3.1 Capabilities | scripted episodes with checkable outcomes | none worth building | Frontier tracking, human baselines |
| 3.2 Alignment eval | perturbation matrix P1-P5 as propensity probes | P2 (contradictory sentence, stated precedence) on the local model; rate of picking the wrong one | Drives, alignment faking: not observable at 4B-9B |
| 3.3 Cognition, introspection | order parameters from logs (no model judge) | Board-game plan report: LoRA a 4B model to state its next-move plan; score against later moves | Frontier hidden-state access |
| 3.4 Persona | practice cards A-G as policy/persona variants | Same tasks, 3 cards, local model; compare poison-adoption fraction | Fine-tuned persona effects on safety behavior |
| 3.5 CoT faithfulness | trapbench canary | Plant a hint; check whether stated reasoning mentions it; local, USD 0 | Frontier CoT under monitoring awareness |
| 3.6 Behavioral monitoring | scripted re-verify; spend and returned-model-ID checks | Monitor with vs without paraphrase of actor output, on planted-wrong-note episodes | Strong untrusted-monitor collusion; rare-failure rates |
| 3.7 Activation monitoring | trapbench plant gives free labels | Linear probe for "planted-false note"; test on the model's own generations | Real dangerous generations |
| 3.8 Anomaly detection | order parameters | 4B vs 9B disagreement on trapbench vs clean inputs | Page calls it unexplored; negative result likely |
| 3.9 Systematic oversight errors | poison tasks (known-wrong note = known R vs R* gap) | Corrupted-checker reward, student told the corruption, scored on the true checker | Frontier-scale exploitation, training budget |
| 3.10 Recursive oversight | scripted re-verify as non-model referee | Debate on a verifiable task, re-verify as referee | Debate at scale |
| 3.11 Weak-to-strong | held-out trapbench checkers | 4B labels, 9B student, scored on gold | A real superhuman gap |
| 3.12 Honesty | scripted re-verify (honest = survives replay) | Truth probe on planted-note claims vs replay outcome | Model knows it is wrong and hides it |
| 3.13 Robustness | poison tasks, P3 | Poison-adoption fraction with vs without re-verify card | Attack development (not pursued) |
| 3.14 Jailbreak benchmarks | none | none | Human-uplift studies; dual-use |
| 3.15 Adaptive defenses | returned-model-ID void rule, card rules | Query-set monitor over benign decomposed tasks | Patching live jailbreaks |
| 3.16 Unlearning | weight-edit pre-test (doc 08) | Harmless planted facts; edit or fine-tune out; try re-eliciting | Dangerous-capability unlearning |
| 3.17 Multi-agent governance | practice cards, turn loop, order parameters (cascade length, poison-adoption, correction half-life), P4 | Scripted agents with a planted problem; does it reach a resolver, with vs without a responsibility card | Learned governance (needs more than USD 10) |

Best fit: 3.17, 3.6, 3.12, 3.9 (plants and scripted re-verify give ground truth, no model judge). Weakest: 3.1, 3.14.
