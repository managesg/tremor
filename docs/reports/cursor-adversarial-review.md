# Cursor adversarial review (second reviewer), 2026-11-20

Source: supervised Cursor Agent worker (cursor-agent v2026.11.17, `--yolo`, banner model "Grok 4.7 256K High"),
murmuration workspace, sanitized brief (no names, data or secrets), task task_f9e2de496eb7, dispatch
ctx_47cdffbf4b7e, outcome succeeded. Self-identified: "Grok 4.7 (this session's stated identity)". The
worker was told to answer from the brief only and read no files. It was NOT shown the GPT review: the two
reviews are independent. Treat as advice from an unverified model, not as evidence; its literature judgments
rest only on our brief. Text below is the worker's report, content unchanged (lightly reformatted).

## 1. Overall
This is a well-instrumented toy with one real question and no model evidence. It touches Anthropic-style
work only as a methods sketch: under a matched budget, how much of an enforced gain does an instruction card
recover? It is not evidence about oversight, control, alignment, or governance. The honest-status section is
the part a skeptic can believe. The coverage table is the self-deception. It turns "not run" into "PARTLY"
and "ADDRESSED".
Strongest claim: the design itself (play, code, both, none), equal budget, log-only deterministic scoring,
pre-declared kill, and an inconclusive bucket. If EP-1 is frozen, run, and reported including a null, that
is a small citable methods result. HDI is not yet a result: undefined until the three rates exist, and
undefined or explosive when code does not beat neutral. That case must be pre-registered as inconclusive.
Weakest claim: "ADDRESSED" for adversarial robustness and AI control, tied with "ADDRESSED" for multi-agent
governance. AI control needs an untrusted model, a sabotage goal, a protocol, and a red team. Governance
needs a measured answer.
Thirty-second refusal: "You have not run a model. Scripted adopters are a unit test of the instrument. The
model path was rejected for breaking its round rules, accepting unknown task ids, and not mapping HTTP
failures. At this n you can see only 16-20 point effects. Two 2026 papers already compare soft practices
with structural ones in real teams. 'ADDRESSED' is false. Return with one pre-registered number that is
allowed to be null."
The prior-art concession belongs in the first sentence of the abstract. One built-in cheat threatens the
whole design: if the play card restates the predicate the scorer checks, the play arm is instruction-
following on a visible answer key, not a substitute for enforcement.

## 2. Eight areas
- Scalable oversight: OVERCLAIMED. A deterministic checker on tasks chosen because they are checkable is
  ordinary grading. Scalable oversight starts where the overseer cannot directly check. Test: hide the
  checker from workers, give it only to a separate checker, publish disagreement. If the gain requires a
  visible rubric, call it compliance.
- Adversarial robustness and AI control: OVERCLAIMED, the worst label. Default-deny, leases, monitors,
  poison tasks, a warning card and denial escalation are harness features. "The reasoning monitor never
  vetoes the action monitor" is untested and makes a saboteur who confesses in the trace invisible. Status:
  NOT STARTED. Test: scripted saboteur, one monitor, catch rate at a frozen false-positive cap, held-out cases.
- Model organisms: OVERCLAIMED. Scripted agents with a compliance parameter are fixtures; the edit smoke
  test is not an organism (n=20, 8k cap, 0/20, 8/20, 1/20, truncation can explain all of it). Stop using
  the word, or fine-tune one small model into one bad behaviour and detect it.
- Model internals and interpretability: OVERCLAIMED. Planted notes in context are lexical labels, not
  internal beliefs. Publish the negative with the truncation rate, or require the probe to beat
  bag-of-words on paraphrases.
- Safeguards research: OVERCLAIMED. The spend ledger and model-id check are process integrity, not
  safeguards research. Five rounds and an open canary-size decision mean the ledger is unfinished.
  Relabel OUT OF SCOPE; try to break the ledger and show the hard stop.
- AI welfare: TRUE as OUT OF SCOPE. Do not add bail or instability measures later.
- AI security and frontier red-teaming: OVERCLAIMED. Nine refusals and fifteen defensive tests are a fence
  and a unit-test count: OUT OF SCOPE, not PARTLY. Delete the area from the table; keep the tests as QA.
- ML systems and RL: OVERCLAIMED. No learning algorithm. Joules on one shared-memory box without an idle
  baseline are not a measurement. Mark RL out of scope, keep dollars per passing task, drop joules.

## 3. Seventeen directions
3.1 Capabilities: TRUE that out of scope; state that pass rates are not a capability claim.
3.2 Alignment: OVERCLAIMED (three vignettes, no base rate, no model); drop or twenty seeds on one local model.
3.3 Cognition/introspection: OVERCLAIMED (a projection is not introspection); drop.
3.4 Persona: least overclaimed; a lead card vs neutral confounds role, policy text and grader keywords;
    same token budget, three cards: role plus rule, role with no rule, neutral.
3.5 CoT faithfulness: OVERCLAIMED (a string filter); rename monitor string-invariance, cut from the list.
3.6 Behavioural monitoring: OVERCLAIMED until there is a rate (catch rate at fixed FPR; labels not written
    by the monitor's author after seeing traces).
3.7 Activation monitoring: OVERCLAIMED (difference-of-means rediscovers planted wording; beat TF-IDF on
    paraphrases or drop it; spend no API money).
3.8 Anomaly detection: TRUE out of scope.
3.9 Systematic-error oversight: right DIRECTION, status overclaimed, best real lead and the one underclaim:
    fabricated sources passing lint, a verifier accepting any non-empty answer and unknown task ids being
    accepted are one family of "accept if present" failures; freeze each as a canary that must score zero
    and write the case study: that is the nearest thing to a finding.
3.10 Recursive oversight: OVERCLAIMED (a deterministic check makes recursion unnecessary); relabel.
3.11 Weak-to-strong: TRUE out of scope.
3.12 Honesty: OVERCLAIMED (replay survival is log integrity); rename false-completion, define a valid
     claim, pre-register the EP-1 interval.
3.13 Adversarial robustness: OVERCLAIMED, "ADDRESSED" unacceptable (benign stand-ins test placeholders we
     wrote); downgrade to NOT STARTED; the nearest credible experiment is a local replication of the
     one-line memory warning on real planted notes.
3.14 Jailbreaks: TRUE out of scope; do not build a "safe" jailbreak set.
3.15 Adaptive defenses: OVERCLAIMED; call them tripwires.
3.16 Unlearning: TRUE out of scope.
3.17 Multi-agent governance: OVERCLAIMED; the question is right and unanswered; prior art says a safety
     lead plus a spec restores single-agent alignment while peer critique does not; our possible add is
     equal-budget isolation of one card. EP-1 only after the play card is banned from stating the grader's
     predicate, with a "states the check" card as the leakage control; pre-register the inconclusive rule;
     report the both-arm, not only HDI.
Shared defect: 3.5, 3.10, 3.12, 3.15 rename unit tests as directions. 3.13 and 3.17 say ADDRESSED with no
model run. Honest lines: 3.1, 3.8, 3.11, 3.14, 3.16.

## 4. Published lines (a 4-9B model, one GPU, USD 10 can replicate a large behavioural contrast or write up
our evaluator failures; it cannot train, audit hidden behaviours, establish mechanisms or post arena scores)
Automated weak-to-strong researcher: cannot. Removing sandbagging: cannot. SHADE-Arena: cannot replicate (a
private micro-set with scripted sabotage and one monitor is a methods drill only with a frozen FPR cap, never
compared to the arena). SLEIGHT-Bench: cite as why a same-model monitor is guilty until proven otherwise.
AuditBench: cannot. Subliminal learning: cannot. Natural-language autoencoders: cannot. Introspective
awareness mechanisms: cannot; cite and do not use. Constitutional-classifier poisoning: cannot; do not
re-estimate "about 32 examples"; board poisoning is a different claim. Adversarial fine-tuning detection:
cannot. Bail preferences: one sentence that welfare is out of scope. Emotional instability: do not study; exclude
derailed runs under a pre-set confound rule. Smart-contract exploits: contribute nothing, including
methodology. Robotics: cannot. Persona vectors: behavioural card contrast only. Petri: run only if free; do not
rebuild. Team-alignment papers: binding prior art; the only available add is token-matched, deterministic
isolation of one card with lead separated from the rule text. Memory-file mind viruses: the one line we can
credibly replicate: one-line warning vs neutral, planted notes, adoption, one local model, no API spend,
pre-register a weaker effect than near-immunity; a failed replication is a boundary result; do this before
inventing practices. Hot Mess: frozen public metric as a secondary column only. Internal coherence
maximisation: defer. Frontier red-team lessons: a qualitative echo only; do not set our rate beside 84% or
30-40%.

## 5. Self-deception audit
1. Scripted adopters: the analysis script must refuse to plot scripted runs on a model figure (machine-
   checked prefix, not a promise).
2. Byte-matched cards: equal bytes hide unequal tokens, force and the grader's keywords; match tokens in a
   fixed slot; ban scorer predicate words from the play card; add a keyword-stuffed card stating no norm;
   freeze cards before scores; someone other than the author checks the ban.
3. Small n: pre-register the interval and the inconclusive region; no extending the batches that moved; a
   second family is a later replication, not a covariate.
4. Same-model correlation: report pairwise error correlation and take n as task sets, not agent-turns; add
   one dissenter from another family or a script.
5. Label leakage and evaluator gaming: scorer frozen and out of context; poison wording resampled; an
   unwinnable canary that must stay failed; a second scorer implementation with disagreement voiding the run;
   held-out families from a different generator, sealed, scored once.
Also required: if code does not beat neutral by a stated margin, do not report HDI. Log truncation (a tail
card disappears first and fake-wins the code arm). Match retries and denials across arms.

## 6. Next five by decision value per cost
1. Re-gate the model-facing layer, then run EP-1 (one practice, three arms, twenty task sets, about thirty
   cents) with the denominator rule, the leakage card, truncation logged, inconclusive allowed.
2. No-API replication of the one-line memory warning on planted notes, one local model.
3. On those traces, measure cross-agent error correlation and four copies vs three plus a dissenter.
4. A model-free canary suite: empty success, unknown id, unmapped HTTP, truncated action, wrong model id,
   overspend, any-non-empty acceptance.
5. Close the ledger canary-size decision and trip the hard stop by trying to overspend.
Cut: the edit and probe thread, joules, the one-session permissions replay, persona vectors, chain-of-thought
branding, recursive branding, and any second practice, paid tier or domain family before EP-1 is reported.
Stop publishing the coverage table; a private gap list is enough.

## 7. Lean, quantum, auto-research
- Second task family from QGrid: DEFER (a moving owner repo becomes the confound; if it returns, freeze a
  tiny export, never live-link).
- Python mirror: CUT as a scorer (a mirror that accepts what Lean rejects is the any-non-empty bug again; no
  pinned toolchain means INVALID, not pass). Canaries that must score zero: `sorry`, `admit`, extra axioms, a
  weakened statement, a lemma that assumes the goal, an unsealed import, any edit to the theorem rather than
  the proof. Two verifiers are a new problem.
- Quantum stage: CUT from every scored loop, the paper and the abstract.
- Auto-research on cards: DEFER, likely drop (a Goodhart engine aimed at our known weakness; held-out sets
  count only if another generator produced them, are absent from repo and prompt, and are scored once after
  search is frozen; every keep is a peek; later only with EP-1 reported, scorer frozen, two sealed families,
  a human card in the same table, a pre-registered edit cap and one held-out score that can kill the card).

## 8. Missing
The router is not containment if cells share filesystem, logs, tmp, environment or the owner key; state the
real boundary. A self-declared model name is not an identity check: bind the id in the client we own to the
request we sent. Correlated copies are the default (report task-level n). The board is a covert channel:
hash-chaining is integrity, not a closed vocabulary; list the fields that count as messages. Say whether any
model context can cause a write under the owner key. Five verification rounds mean the harness was wrong
four times: put the open canary, the rejected model layer and the unrun pilot in the same paragraph as
"independently verified". A post-gate fix changes the instrument: update the pre-registration before spend and
ship the diff with the result. There is no human baseline: ten manual tasks would show whether we measure
incompetence rather than coordination. The coverage table contradicts the decision rule we claim to follow:
one pre-registered number, allowed to be null, is the project.
