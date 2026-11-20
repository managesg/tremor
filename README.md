<p align="center"><img src="assets/tremor-hero.svg" alt="TREMOR: measure how a team of agents responds, then use the measurement to run the team" width="100%"></p>

# TREMOR

**Measure how a team of agents responds, then use the measurement to run the team.**

TREMOR is a research proposal about teams of AI agents that work together through shared state: a task
board, shared notes, shared memory. It treats the team as a physical medium and asks first-principles
questions about it. How much does its outcome wobble between identical reruns? How far does a wrong note
copy itself? How correlated are the members' mistakes? How fast does the team recover from a shock?

Those collective properties can be read from logs, often for free. The proposal turns each one into an
**algorithm that decides where scarce resources go**: verification, monitor calls, memory, permissions
and team structure. Each algorithm must beat a named baseline at equal budget.

> Status: research proposal and working instrument. **No result in this repository is a finding yet.**
> Every prediction below can fail, and failures will be published.

## The problem

Agent teams are being deployed faster than we understand them. Today their scarce resources are spent
evenly or by habit:

- every piece of work is reviewed once, whatever its risk;
- three monitors are stacked, with no count of how many independent checks they really give;
- shared memory is consolidated ("dreamed") overnight, with no rule for when that corrects errors and
  when it amplifies them;
- permissions are granted once and kept forever;
- teams grow, and coordination quietly collapses.

Each of these is a safety question as much as a performance question. A team that spends oversight
blindly misses the failures that matter. A shared memory can spread one bad note to every agent.

## The thesis

A team of agents is a medium with shared state. Three things move through it: **work, errors and
norms**. Like any medium, it has collective statistics that no single agent has. For each scarce
resource there is a statistic that says where the resource matters, and a rule that spends by that
statistic beats a rule that ignores it.

## Eight research lines

| # | Line | Idea from complex systems or first principles | What it delivers |
|---|---|---|---|
| 1 | Susceptibility-guided verification | Fluctuation and response: natural variation predicts the response to a push | Re-check the work whose reruns vary most; tests whether a fluctuation-response law holds for agent teams |
| 2 | A memory immune system | Epidemic thresholds and herd immunity | Provenance on every note, quarantine of suspect notes, and the share of verified notes that stops a wrong note spreading |
| 3 | Decorrelated monitor ensembles | Redundancy and coding: correlated checks count as fewer checks | Choose monitors so that their failures do not overlap; measure the effective number of independent monitors |
| 4 | Dreaming that corrects | An iterated map with a threshold; critical slowing down | Verified replay with adaptive strength, and an early warning before consolidation flips from correcting errors to amplifying them |
| 5 | Stigmergy and norm carriers | Social insects coordinate through marks that evaporate | Evaporating task claims that stop herding; a map of where a team rule works best: in context, memory, environment or code |
| 6 | Evidence-based trust | Feedback control and sequential testing | Permissions as leases that widen or expire on evidence, not on time alone |
| 7 | Renormalizing team size | Coarse-graining: replace a block of agents by one effective agent | Team structure sized by measured task coupling; how the effective number of agents scales with team size |
| 8 | Activation readouts | Two measurements of the same event | A frozen readout from an open model's activations as one more, decorrelated check on a team |

Each line states a falsifiable prediction, a control, a kill criterion that can fire at the planned
sample size, and the closest prior work it must go beyond.

## The shared instrument

All eight lines run on one bench, so their results can be compared and combined:

- **A shared task board** with claims, work and releases, run by teams of four agents and up.
- **Deterministic scoring from logs.** Three independently written scorers must agree on every
  episode. One of them is written in Lean 4, and its soundness properties are checked by the Lean
  kernel (66 theorems, standard axioms only). Any disagreement voids the run.
- **Seeded shocks and planted notes**, so that responses and contagion can be measured, with clean
  twins as controls.
- **Hard spend limits in code**, with a ledger checked before and after every call.
- **Two kinds of models:** hosted Claude models at small and frontier tiers, and open-weight models run
  locally on a single workstation GPU for the activation and memory experiments.

## What exists today

| Part | Status |
|---|---|
| Task board, router, practice cards, perturbation and planted-note tools | Built and checked on scripted agents |
| Three agreeing scorers, one checked by the Lean kernel | Built; 0 disagreements on 10,000 seeded logs |
| Spend ledger with hard caps | Built; checked by independent reviews and by tests that break it on purpose |
| First calibrated measurement (instruction card versus enforcement in code) | Pre-registered; instrument pilots on a small Claude model have run |
| Research lines 1 to 8 | Designed; not started |

Two instrument pilots on a small Claude model already did their job. Each stopped on a rule we had
written in advance, and each exposed a design gap that is now being fixed. These pilots check the
instrument; they are not results.

## How the work is done

The project is itself run by a team of AI models with separate roles: planning and pre-registration,
orchestration and verification, implementation, and retrieval. Every change to the code is checked by a
fresh reviewer that did not write it. Every claim about outside work is checked against its source.
Reviews police claims and evidence, never the scope of the questions.

## Six-week deliverable

One open release:

- the bench, logs and analysis code;
- the Lean-checked scorer;
- the techniques from lines 1 to 3 as reference implementations, each tested against its baseline;
- first results for lines 4 and 5, and pilots for lines 6 to 8;
- every negative result.

Over six months: replication on a second open model family, external benchmarks, and the surviving
techniques combined into one controller tested against a plain team at equal budget.

## What this is not

- Not a claim that any of these techniques works. They are hypotheses with kill criteria.
- Not evidence about frontier systems in general. Results hold for the models and tasks tested.
- Not offensive security work. Contagion and poisoning experiments use benign stand-ins, and their
  dual-use boundary is written down before any run.

## Inspiration

The problems were shaped by four talks at the AI Engineer Code Summit 2026 on thousand-agent teams,
memory and dreaming, bounded autonomy, trust, and reliability, and by Anthropic's published research
directions on oversight, model organisms, interpretability and agent safety.

## Contact

[owner to add]
