# TREMOR work plan

The public version of the plan. Every item says where it stands today, using four status words:
**NOT STARTED**, **INSTRUMENTED** (code exists and passed scripted checks), **PILOTED** (run on a real
model as an instrument check, no estimate) and **EVIDENCED** (a pre-registered result exists).
**Nothing in this project is EVIDENCED yet.**

## Where we are (2026-11-20)

| Item | Status |
|---|---|
| Shared task board, router, practice cards, planted-note and perturbation tools | INSTRUMENTED |
| Three independent scorers, one proved in Lean 4 (0 disagreements on 10,000 seeded logs) | INSTRUMENTED |
| Spend ledger with hard caps in code | INSTRUMENTED, checked by independent reviews |
| First calibrated measurement: an instruction card against the same rule enforced in code | Pre-registration drafted, **not frozen** |
| Instrument pilots on a small Claude model | Two run; both stopped on rules written in advance; fixes in progress |
| Research lines 1 to 8 | NOT STARTED |

What the two pilots taught us, so far only about the instrument:

1. The model's hidden reasoning used up the reply budget. Fix: reasoning turned off for these runs.
2. With reasoning off, the model writes its reasoning as prose before a correct JSON answer. Fix: the
   parser accepts the final JSON array of a reply and treats anything after it as malformed, the same
   way in every condition.

## Rules that hold for every step

- **Pre-register, then run.** Each line's statistic, baseline, sample size, kill criterion and
  dual-use boundary are written down and frozen before its first real run.
- **Three outcomes.** Every prediction ends as supported, killed or inconclusive. A result that is only
  not significant is inconclusive, never killed.
- **Every number comes from a frozen, verified run.** Numbers in plans are labelled as priors.
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
- [ ] Parser fix verified by an independent reviewer
- [ ] Third pilot, both task orders, to choose the task order for the first measurement
- [ ] Freeze the first measurement's pre-registration, run it, publish the result whatever it is

### Phase 1. Extend the bench (week 1, no model cost)

- [ ] Overnight consolidation loop: daily notes replayed into long-term memory, with provenance
- [ ] Per-line readouts: rerun variance, dose response, reproduction number of a wrong note, joint
      monitor misses, recovery time
- [ ] Scripted controls for every line: each must fail with no signal present and pass with an ideal
      agent
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
- [ ] Lines 6 to 8: pilots of evidence leases, team-size scaling and activation readouts

### Phase 5. Release (week 6)

- [ ] One open release: bench, logs, Lean-checked scorer, analysis code, reference implementations of
      the surviving techniques, every negative result

### Months 2 to 6

- [ ] Replication on a second open model family
- [ ] External benchmarks with deterministic scoring
- [ ] The surviving techniques combined in one controller, tested against a plain team at equal budget
- [ ] Paper and benchmark v1

## What would falsify the programme

1. A statistic measured on one set of seeds does not predict itself on another.
2. Allocating by the statistic never beats allocating without it, at equal budget.
3. No dose response and no thresholds anywhere.
4. Scripted agents reproduce every effect, so the effects are about loops, not language models.

If all four hold, we publish the negatives and keep the bench for others.
