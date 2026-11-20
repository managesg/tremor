# TREMOR work plan

This is the public, clean work plan. Internal gates, spend codes, hashes and machine names are in the
private repository.

---

## Gate sequence

The project moves through explicit gates. Nothing proceeds until its gate is signed.

| Gate | What must be true | Who checks |
|---|---|---|
| G0 | Instrument: board, router, scorers, ledger all pass scripted tests | Independent verifier |
| G1 | First calibrated measurement pre-registered and frozen | Independent verifier |
| G2 | First measurement run to completion; result published | Independent verifier |
| L1 | Sensitivity pilot: local 4B model speed, memory capacity, probe signal | Internal |
| L2 | Lines 1 to 3 pre-registrations frozen | Independent verifier |
| L3 | Lines 1 to 3 results against their baselines | Independent verifier |
| L4 | Dreaming phase map; evaporating claims pilot | Independent verifier |
| L5 | Lines 6 to 8 pilots | Independent verifier |
| L6 | Full write-up; open release of bench, logs, techniques, negatives | Owner |

---

## Week-by-week

### Week 0 (now)
- **Close the instrument gates.** The first calibration (an instruction card against the same rule
  enforced in code) is pre-registered and frozen. It runs as soon as G1 signs.
- **Public repo** set up with this work plan and the proposal summary.

### Week 1
- **Overnight consolidation loop added** to the task board: agents replay their shared memory and
  write a consolidated version. Scripted controls prove it must fail when nothing is there and pass
  with an ideal agent.
- **Instrument report** published: every verification that passed, every mutant killed, every
  stopping rule and the exact spend ledger.

### Week 2
- **Variance pilot** on the local 4B model: rerun variance and speed. This tells us how many
  episodes we can afford and what n is needed to make each kill criterion decisive.
- **One pre-registration per line** is written, frozen and published *before any run*. The
  pre-registrations state the statistic, the baseline, the sample size, the kill criterion and the
  dual-use ruling.

### Weeks 3 to 4
- **Lines 1 to 3 run** on the local 4B model and on a small hosted model.
- Each run uses its pre-registered sample size and stops itself on its written rules.
- Results published with full logs; negatives included.

### Week 5
- **Dreaming phase map (line 4):** consolidation strength is ramped from placebo to strong; the
  false-note share and recovery time are measured. The early-warning statistic (critical slowing
  down) is checked.
- **Evaporating claims pilot (line 5):** norms enforced in code versus in memory versus in
  environment versus evaporating claims.
- **Pilots for lines 6 to 8:** trust leases, team-size blocks, activation readouts. Each produces
  a table of what worked and what didn't.

### Week 6
- **Open release:** the bench (board, router, scorers, ledger), all logs, the Lean-checked scorer,
  the analysis code, reference implementations of the surviving techniques, and every negative
  result. A single markdown document links all of it.

---

## Months 2 to 6

- **Replication on a second open model family** (different architecture, same tasks).
- **External benchmarks** (existing agent benchmarks) run with the surviving techniques.
- **One combined controller** that allocates verification, monitors, memory, trust and team
  structure from a single shared measurement loop.
- **Paper and benchmark v1** submitted.

---

## Gates and rules

- **Every number comes from a frozen, verified run.** No number in any document is a prediction
  unless it is explicitly labelled "prior" with the author's probability.
- **Nothing is called EVIDENCED until its pre-registration and result exist.** The status words
  are: NOT STARTED, INSTRUMENTED, PILOTED, EVIDENCED.
- **Reviews check claims, sources and status words.** Scope is set by the owner. Reviews do not
  shrink ideas or budget; they state risks, missing assumptions and how to make each line testable.
- **Dual-use boundary:** poisoning and contagion experiments use benign stand-ins. Selecting
  monitors against an optimizer is a controlled experiment. No training of private capabilities.
- **Hard spend limits are in code.** The ledger stops the run before any ceiling is passed. The
  owner authorises the total budget; no per-batch ask.
- **Compute provided by the residency** goes first to the sample sizes that make each kill
  criterion decisive.
- **Local team sizes:** the current instrument runs teams of four agents. Lines 6 and 7 plan to
  test sizes 8, 16 and 32, which need the owner's re-approval when reached.

---

## What has been spent

| Item | GPU-hours | API, USD |
|---|---|---|
| Two instrument pilots (small hosted model) | 0 | 0.023 |
| **Total so far** | **0** | **0.023** |

All ledger files are open source in the private repo and are published in the week 6 release.

---

## What this is not

- Not a claim that any technique works. They are hypotheses with kill criteria.
- Not evidence about frontier systems. The first tasks are deliberately simple integer tasks.
- Not offensive work. Contagion and poisoning use benign stand-ins.
- Not a finished product. The week 6 release is the first complete, testable version.

---

## Contact

[owner to add]