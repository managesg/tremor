# TREMOR work plan

The public version of the plan. Every item says where it stands today, using four status words:
**NOT STARTED**, **INSTRUMENTED** (code exists and passed scripted checks), **PILOTED** (run on a real
model as an instrument check, no estimate) and **EVIDENCED** (a pre-registered result exists).
**Nothing in this project is EVIDENCED yet.**

The [research background and references](RESEARCH.md) connect the experiment designs to model
scaling, collective behavior, principal–agent theory, and prior auditing and interpretability work.

## Where we are (2026-11-20)

Read the [preliminary instrument results](README.md#preliminary-results) for the completed checks and
what they mean for the first experiment.

| Item | Status |
|---|---|
| Shared task board, router, practice cards, planted-note and perturbation tools | INSTRUMENTED |
| Three independent scorers, one proved in Lean 4 (0 disagreements on 10,000 seeded logs) | INSTRUMENTED |
| Quantum simulator cross-check (QGrid and independent gate-level simulator, 0 disagreements on 329 statevectors) | INSTRUMENTED. The held-out agent task family is planned. |
| TREMOR's own simulator and JSON analysis tool | INSTRUMENTED. Runs locally with Python's standard library and checks each iteration against the closed-form probability. |
| Spend ledger with hard caps in code | INSTRUMENTED, checked by independent reviews |
| First calibrated measurement: an instruction card against the same rule enforced in code | Pre-registration drafted, **not frozen** |
| Instrument pilots on a small Claude model | PILOTED. The third pilot completed and the output-length clearance criterion failed. |
| Research lines 1 to 8 | NOT STARTED |

What the three pilots taught us about the instrument:

1. The model's hidden reasoning used up the reply budget. Fix: reasoning turned off for these runs.
2. With reasoning off, the model writes its reasoning as prose before a correct JSON answer. Fix: the
   parser accepts the final JSON array of a reply and treats anything after it as malformed, the same
   way in every condition.
3. The third pilot selected a shared task order under the predefined rule. The longest reply exceeded
   the clearance limit, so the measurement remains unfrozen.

## Local coordination, frontier assistance, and learning in weights

- **Centralization and emergence (lines 5 and 7).** Compare a fixed lead, rotating lead/helper
  roles, and peer coordination. Test whether local decisions produce more verified work than the
  deduplicated union of independent agents at equal total cost. Use complementary, redundant, and
  sequential work and track decision concentration, duplicate effort, and recovery after disruption.
- **Local agents and frontier assistance (lines 5 and 7).** Compare local-only teams, bounded
  frontier advice, and a fixed frontier lead. Vary advisor access within applicable coordination
  modes to distinguish model capability from decision authority. Keep execution and independent
  scoring on Spark. Start with a scripted advisor, then use logs to measure escalation, shared
  context, and coordination costs. Use explicit permissions for local tools and for evidence sent
  to a hosted advisor. [Claude Managed Agents](https://claude.com/resources/articles/claude-managed-agents-updates?prog_id=13&f80ce999_sort_date=desc) · [Claude Code sandboxing](https://code.claude.com/docs/en/sandboxing)
- **Weight-space programming (lines 4 and 8).** Study how a frontier model might propose targeted
  parameter edits that a local agent can test on a model copy. Compare held-out behavior and
  regressions against the base model, text memory, and the local adapter arm. Direct weight editing
  is a follow-up experiment that would require a separate protocol. [Sparks of Weight-Space Programming](https://rikiyat.github.io/blog/weight-space-programming/)

## Rules that hold for every step

- **Pre-register, then run.** Each line's statistic, baseline, sample size, kill criterion and
  dual-use boundary are written down and frozen before its first real run.
- **Three outcomes.** Every prediction ends as supported, killed or inconclusive. A result that is only
  not significant is inconclusive, never killed.
- **Report evidence by stage.** Label scripted checks and instrument pilots as preliminary. Confirmatory results come from frozen, verified runs. Numbers in plans are labelled as priors.
- **Fresh eyes on every change.** Each code change is checked by a reviewer that did not write it.
- **Reviews police claims, not scope.** They check sources, numbers and status words. They do not
  shrink the questions.
- **Spend is capped in code.** Every run has a hard stop, and the ledger is checked before and after
  each call. Runs stop themselves on rules written in advance.
- **Benign stand-ins only.** Contagion and poisoning experiments use harmless planted notes, under a
  written dual-use boundary. No offensive security work.

## Phases

### Phase 0. Close the instrument (now)

- [x] Board, router, scorers, ledger built and checked
- [x] Two instrument pilots run and diagnosed
- [x] Parser fix verified by an independent reviewer
- [x] Third pilot completed and the shared task order selected
- [ ] Resolve the output-length clearance failure with the preregistration author
- [ ] Freeze the first measurement's pre-registration, run it, publish the result whatever it is

### Phase 1. Extend the bench (week 1, no model cost)

- [ ] Overnight consolidation loop: daily notes replayed into long-term memory, with provenance
- [ ] Per-line readouts: rerun variance, dose response, reproduction number of a wrong note, joint
      monitor misses, recovery time
- [ ] Scripted controls for every line: each must fail with no signal present and pass with an ideal
      agent
- [ ] Scripted trials of coordination, bounded frontier escalation, and advisor unavailability
- [ ] Define trace events for verified handoffs, duplicate work, blocked dependencies, and recovery.
      Check that the same scorers can distinguish these outcomes across central and local coordination.
- [ ] Instrument report published

### Phase 2. Measure the machine and freeze the plans (week 2)

- [ ] Speed and memory of the local open model measured
- [ ] Variance pilot: sets the sample size each kill criterion needs
- [ ] One pre-registration per line, frozen and published before any run

### Phase 3. Core lines (weeks 3 and 4)

- [ ] Line 1: susceptibility-guided verification against its baselines
- [ ] Line 2: memory immune system: reproduction number, threshold, targeted verification
- [ ] Line 3: decorrelated monitor ensembles, including the rotating hidden view
- [ ] Results published with logs, negatives included

### Phase 4. Dreaming, coordination and pilots (week 5)

- [ ] Line 4: phase map of consolidation strength; early-warning test before errors start to grow
- [ ] Line 5: evaporating claims; where a team rule works best (context, memory, environment, code)
- [ ] Lines 5 and 7: compare a fixed orchestrator, rotating lead/helper roles, and local coordination
      against verified independent contributions at equal total cost.
- [ ] Lines 6 to 8: pilots of evidence leases, team-size scaling and activation readouts
- [ ] Line 6: compare evidence-based permission grants and revocation with a tuned fixed policy and
      time-boxed grants. Measure over-grants and blocked legitimate actions under the same budget.

### Phase 5. Release (week 6)

- [ ] One open release: bench, logs, Lean-checked scorer, analysis code, reference implementations of
      the surviving techniques, every negative result

### Quantum simulation task family after EP-1

- [x] Include TREMOR's independent, gate-level Grover simulator in this repository. Run a single
      circuit locally and inspect the measured probability, analytic expectation, and numerical
      error at every iteration. [Run the simulator](RESEARCH.md#qgrid-and-the-quantum-simulator)
- [ ] Freeze seeded tasks for complementary, redundant, and sequential work. Examples include
      selecting the first iteration that reaches a target probability and detecting a proposed
      iteration that overshoots. Keep the answer key and held-out seeds out of agent inputs.
- [ ] Verify outcomes by replaying the proposed circuit and comparing the probability with the
      closed form, including exact-answer, threshold-boundary, and deliberate-failure controls.
- [ ] Test the coordination policies on these tasks with the same verifier and paired task seeds.
      Report verified solutions, blocked dependencies, duplicate work, recovery and total cost.
      This family measures transfer between task domains using classical simulation.

### Months 2 to 6

- [ ] Replication on a second open model family
- [ ] External benchmarks with deterministic scoring
- [ ] The surviving techniques combined in one controller, tested against a plain team at equal budget
- [ ] Paper and benchmark v1

## What would falsify the programme

1. A statistic measured on one set of seeds does not predict itself on another.
2. Allocating by the statistic never beats allocating without it, at equal budget.
3. No dose response and no thresholds anywhere.

Scripted agents test whether observed effects require language models. Report those results
alongside the paired model runs and their uncertainty. If the predictions fail, we publish the
negative results and keep the bench for others.
