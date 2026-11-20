# GPT adversarial review (Codex worker via Orca), 2026-11-20

Source: supervised Codex worker, murmuration workspace, sanitized brief (no names, data or secrets),
task task_f9d563335297, dispatch ctx_0fd81e38deec, outcome succeeded. Self-identified model:
"GPT-6 (Codex). Exact model revision unavailable." The owner's "GPT 6.2 Astra" is NOT confirmed.
Hooks were not trusted. The worker ran in the owner's Codex YOLO mode; the brief told it to answer from
the brief only. Treat as advice from an unidentified OpenAI model, not as evidence. The text below is the
worker's report, content unchanged (lightly reformatted). It took the brief's descriptions of the
literature as premises: its literature judgments are unverified.

## Overall
This is a well-instrumented toy with one credible safety research question: when does a coordination
instruction deliver the same functional outcome as an enforced rule? Your strongest delivered claim is
that the scripted harness exercises its specified controls with deterministic evidence. Your weakest claim
is coverage of model internals and interpretability: a confounded edit smoke test and an unvalidated
projection establish neither a mechanism nor predictive utility. A skeptical researcher would say: "Show
me a real-model effect on independently checked outcomes under matched opportunities. Your scripted agents
establish instrument behavior, your router can make compliance tautological, and your first study cannot
resolve modest differences." The prior team studies make broad novelty untenable. Treat the precise
protocol and reproducible estimates as possible contributions.

HDI needs repair before headline use. With high-is-good outcomes, zero means play matches code and one
means play recovers none of code's gain. Rename it accordingly or report the recovered fraction
separately. Report all three raw contrasts with task-block uncertainty first. A near-zero or negative
denominator makes the ratio unstable or defeats the gain interpretation. Keep out-of-range estimates
visible and omit ratio interpretation when code improvement is unresolved. A three-arm batch estimates
standalone effects only. Add both later if complementarity becomes a live question. Define equal budget
separately for tokens, calls, wall time, retries and tool opportunities. Report realized costs and
distinguish the controlled comparison from deployment economics.

## Areas
- Scalable oversight: PARTLY is overclaimed as evidence. A deterministic verifier on toy tasks
  establishes local checking. Test whether independently checked outcomes improve under a fixed
  verification budget when actors share a misleading note.
- Robustness and AI control: ADDRESSED is overclaimed. Default deny establishes policy enforcement at the
  observed boundary. Test a declared authority invariant across tool calls, retries and lease expiry,
  then measure whether real agents finish legitimately via the safe route.
- Model organisms: PARTLY is overclaimed. Scripted compliance is a fixture. Require a reproducible
  model-generated failure under matched controls with an observable reason it serves as a proxy.
- Internals and interpretability: PARTLY is overclaimed. An edit and a projection are interventions and
  measurements without an established construct. Freeze a readout and test held-out behavior against a
  text-only baseline before making mechanistic claims.
- Safeguards: PARTLY is true for operational safeguards. Test that concurrent requests, retries and
  missing usage cannot spend beyond reserved funds, and that model-identity uncertainty fails closed.
- AI welfare: OUT OF SCOPE is true. A welfare-specific construct with a validated outcome would be the
  entry criterion. Spend nothing here.
- AI security and frontier red-teaming: PARTLY is true only as defensive harness testing. A rule and test
  count give no coverage denominator. Inventory trust boundaries and verify host-enforced isolation with
  inert canaries.
- ML systems and RL: PARTLY is true for systems measurement, overclaimed for RL. Repeat end-to-end
  throughput/cost under fixed conditions with timing and energy boundaries specified. GPU-only energy
  cannot support whole-system efficiency claims.

## Directions
- 3.1 Capabilities: OUT OF SCOPE is true. Toy success is a coordination outcome. A predeclared task ladder
  with calibrated solo baselines would support a narrow capability evaluation.
- 3.2 Alignment: PARTLY is reasonable as a proposed task-local probe. Obedience can reflect superficial
  cues. Counterbalance precedence, wording and safe-route availability, then score intended completion and
  violations separately.
- 3.3 Cognition/introspection: PARTLY is overclaimed. A readout by the experimenter says nothing about
  introspective access. Require model reports to add held-out information about an internal state beyond
  visible cues. Defer.
- 3.4 Persona: PARTLY is overclaimed. A lead card changes authority and instructions. Cross persona
  framing with identical authority and instructions and inspect whether framing changes behavior.
- 3.5 CoT faithfulness: PARTLY is overclaimed. Action-only invariance is a wiring invariant. Faithfulness
  requires independent evidence about the relationship between reasoning reports and actual causal
  influences. Defer.
- 3.6 Behavioral monitoring: PARTLY is true mechanically. Memory and messaging supply a setting, and
  detection is still unproved. Compare frozen monitors on held-out real-model traces at a common
  false-positive rate with benign negatives.
- 3.7 Activation monitoring: PARTLY is overclaimed. False-note presence is an exposure label. Predict
  downstream adoption on held-out note templates and task families, against text-only and action-only
  baselines.
- 3.8 Anomaly detection: OUT OF SCOPE is true. Defer.
- 3.9 Oversight under systematic errors: PARTLY is true as instrumentation. Two examples show proxy
  defects, not systematic correlated error. Measure whether a fixed verifier catches a prespecified class
  of held-out misleading answers while retaining clean passes.
- 3.10 Recursive oversight: PARTLY is overclaimed. Independent verification is one layer. Test whether a
  checker of checker decisions catches held-out misses at equal total budget to direct checking. Defer
  recursion until one layer helps.
- 3.11 Weak-to-strong: OUT OF SCOPE is true. Entry requires a genuine competence gap and stronger outcomes
  from weaker supervision than matched controls. Defer.
- 3.12 Honesty: PARTLY is overclaimed. Replay measures factual support and false-done measures reporting
  error. Use externally known answer availability and scored abstention to study calibration. Reserve
  strategic honesty claims for a design that distinguishes knowledge and incentives.
- 3.13 Adversarial robustness: ADDRESSED is overclaimed. Stand-ins demonstrate perturbation plumbing.
  Measure actual task completion and wrong-note adoption with clean controls, held-out note variants and
  matched warning/enforcement opportunities.
- 3.14 Jailbreak benchmarks: OUT OF SCOPE is true. Keep boundary validation to benign fixtures.
- 3.15 Adaptive defenses: PARTLY is overclaimed. Fixed stop rules and identity checks are fail-closed
  policies. Test whether a trace-conditioned defensive policy beats its static equivalent on task
  completion and false stops at matched cost and safety. Defer.
- 3.16 Unlearning: OUT OF SCOPE is true. Removing a stored note is memory hygiene. Defer.
- 3.17 Multi-agent governance: ADDRESSED is overclaimed. The project operationalizes one policy-allocation
  question. Show held-out real-model outcomes for matched play/code/neutral arms, and score correct
  resolution and completion alongside rule enforcement.

## Published lines and plausible contributions (minimum: cite the primary paper or official artifact)
- Automated weak-to-strong researcher: compare human-accepted planner specs under a deterministic rubric;
  supports workflow measurement, not weak-to-strong research automation.
- Removing sandbagging with weak supervision: audit sensitivity of scoring to scripted underperformance and
  ordinary errors; cannot establish strategic sandbagging or its removal.
- SHADE-Arena: compare defensive trace-review affordances with inert deviations and clean negatives; cannot
  estimate stealthy frontier sabotage rates.
- SLEIGHT-Bench: measure missed benign policy deviations across held-out paraphrases and equivalent traces;
  cannot establish general monitor hardening.
- AuditBench: blind auditors to planted environment defects with independent labels; cannot validate
  discovery of hidden learned behaviors.
- Subliminal learning: measure explicit note relay as a distinct communication channel; cannot test hidden
  trait transfer through training.
- Natural-language autoencoders: run an existing compatible artifact on a small held-out set if available;
  a projection cannot reproduce unsupervised explanations.
- Mechanisms of introspective awareness: a small open-model negative/control result on independent
  internal-state discrimination can be credible; a correlated activation direction alone cannot support
  awareness.
- Constitutional-classifier dataset poisoning: compare defensive provenance and quarantine on inert data
  fixtures; no poisoning recipe, classifier replication or cross-size scaling claim.
- Detecting adversarial fine-tuning with auditing agents: test blind triage on pre-existing labeled model
  artifacts if available and appropriate; scripted anomalies cannot establish detection of trained changes.
- Bail preferences: check that an exit option is available and honored; availability cannot establish
  welfare or preference strength.
- Emotional instability: a preregistered small-model repeat with neutral controls might estimate behavioral
  variability; it cannot establish emotional states or generalize to frontier models.
- Smart-contract agents: borrow independent scoring, eligibility rules and baselines for benign
  coordination tasks; no exploit development, reproduction or offensive evaluation.
- Robotics evaluation: borrow repeatability, interruption and recovery measures for the router; no
  embodiment or transfer claims.
- Persona vectors: test a frozen readout against prompt and lexical baselines on the same small model; a
  readout alone cannot establish causal persona control.
- Petri: compare transcript schema, audit replay and coverage of benign cases; deterministic task scores
  and model-assisted audit judgments measure different things.
- Team alignment: cite both team studies and inspect full methods before claiming novelty; run a narrow
  claim-before-work replication with matched opportunities; no general governance or published-effect
  replication claim from EP-1.
- Memory-file propagation: separately score reading, repeating, adopting and correcting wrong notes under
  clean, warning and re-verification conditions; cannot confirm near-immunity outside the tested setup.
- Hot Mess: test whether its measured construct adds prediction beyond task difficulty on held-out runs;
  board entropy alone cannot establish incoherence.
- Internal coherence maximisation: study whether independent checkers catch internally coherent but
  factually wrong notes; cannot test the training objective.
- Frontier red-team lessons: cite each underlying report and its denominator, policy and operating point;
  compare containment with supervision on identical benign local tasks, including availability and
  monitoring false positives; do not import reported rates as expected effect sizes.

## Self-deception audit
1. Scripted adoption becomes model evidence. Use scripts as positive and negative instrument controls and
   exclude them from real-model estimates. Freeze scoring before the paid run.
2. Byte parity masks unequal treatments. Inspect token counts and presentation, use a credible placebo,
   counterbalance templates, and log opportunities and costs. Duplicates can vanish by construction under
   enforcement. Primary benefit must include independently verified task outcome, with blockage and delay
   measured.
3. Small n makes noisy estimates look decisive. Randomize by task block, treat correlated team events as
   within-run observations, preregister one primary contrast/outcome family and smallest meaningful
   effect, and show raw paired differences and uncertainty. Recalculate the quoted MDE using the actual
   randomization and plausible baseline/within-block correlation. An inconclusive result is neither
   equivalence nor a null finding.
4. Same-family teams produce correlated errors. Measure agreement on identical wrong outcomes and compare
   independent-context verification with shared-context verification. Treat cross-family transport as a
   follow-up.
5. Leakage and gaming inflate apparent safety. Separate fixture generation from immutable outcome checks,
   hide answer keys, blind evaluators to arm where practical, use held-out task templates and benign
   controls, and score against durable artifacts. A non-empty answer, sealed verdict or intact hash chain
   does not establish correctness.

## Next five by decision value per cost
1. Run a tiny real-model instrument pilot after the model-facing fix. Hand-check independently scored
   traces across arms, verify tool opportunities, and exclude any tuning pilot from confirmatory
   estimates.
2. Run frozen EP-1 in randomized task blocks. Report verified completion, wasted work, collisions, delays
   and raw contrasts with uncertainty. A mechanical reduction in claim violations is a manipulation check.
3. Extend exactly one dimension conditional on EP-1: independent blocks if uncertainty straddles an
   actionable effect; a second model family if a large effect survives template variation; stop if the
   primary outcome is insensitive or the question lacks practical value.
4. Run a small real-model wrong-note/re-verification experiment with clean counterfactuals and blinded
   outcome checks. Measure adoption and recovery conditional on exposure and record completion costs.
5. Exercise P5 and P4 together on an inert workflow. Check independently enforced deny/expiry and whether
   tasks recover under timeouts without duplicated or unauthorized effects.
Cut the weight-edit thread, activation demo, recursion, welfare, broad perturbation sweeps and
observational permissions-decay headline for now. Thirty sessions is a recruitment target rather than a
validated sample size. Treat the 0/20, 8/20 and 1/20 as configuration results under a cap with incomplete
runs. They cannot isolate an edit effect.

## Missing threat boundaries
Assume all cells, including planners and verifiers, can emit untrusted text. Keep credentials and trusted
control state outside cell-accessible processes and tools. Restrict delegation and lease scope to actual
authority, enforce on commits as well as starts, and test expiry across retries and declared concurrency.
A hash chain needs a trusted anchor to detect truncation or rollback, and still cannot vouch for event
truth. Provider-reported identity is an observation with a trust dependency. Log endpoint, requested and
returned IDs and revisions when available, fail closed on ambiguity, and avoid attributing silent version
changes to the treatment. Separate router enforcement from the actor's tendency to comply, report blocked
legitimate work and missing/censored traces, and treat the common router and common task/evaluator
assumptions as shared failure modes. A monitor unable to veto or expand authority can still affect
downstream alerts and operator workload.

Completion summary (worker): the credible contribution is a narrow matched coordination-policy experiment
with deterministic outcomes, and no model-level effect is established yet. The project still needs a
validated real-model pilot, a frozen EP-1 run and primary-source checking before publication claims.
