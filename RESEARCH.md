# Research background and scientific references

TREMOR asks when a statistic measured from an agent team can improve the allocation of verification,
monitoring, memory, permissions, or compute. The [workplan](WORKPLAN.md) describes the planned
experiments. The [preliminary results](README.md#preliminary-results) describe completed instrument checks.

## Scaling models and agent systems

Kaplan et al. measured empirical relationships between language-model loss, parameter count,
training data, and compute. Hoffmann et al. tested how a fixed training budget should be divided
between model size and training tokens. These studies use model training as the unit of analysis.
TREMOR holds the model fixed within a comparison and changes how a team uses its inference and
tool budget. [Kaplan et al., *Scaling Laws for Neural Language Models* (2020)](https://arxiv.org/abs/2001.08361) ·
[Hoffmann et al., *Training Compute-Optimal Large Language Models* (2022)](https://arxiv.org/abs/2203.15556)

Kim et al. found that the effect of multi-agent coordination differed by task and architecture in
their evaluation. Cemri et al. used multi-agent traces to identify recurring failures in task
specification, coordination, and verification. TREMOR builds on these observations by testing
whether a statistic measured on one set of runs predicts the response to an intervention on held-out
runs, and whether allocating resources by that statistic improves verified output at equal cost.
[Kim et al., *Towards a Science of Scaling Agent Systems*](https://arxiv.org/abs/2512.08296) ·
[Cemri et al., *Why Do Multi-Agent LLM Systems Fail?* (2025)](https://arxiv.org/abs/2503.13657)

## Collective behavior and emergence

Couzin et al. modeled how a small informed minority can guide collective movement through local
interactions. Woolley et al. studied a group-level performance factor in human teams across tasks.
These studies motivate measuring both local actions and collective outcomes in AI teams. TREMOR
tests four arrangements: independent contributors, a fixed lead with helpers, rotating lead/helper
roles, and peers coordinating through shared state. The main emergence comparison is against the
verified, deduplicated output of independent contributors at the same total cost, with a fixed
aggregation and verification policy. Use tasks with
complementary, redundant, and sequential work to distinguish integration from parallel throughput.
Record positive gains and losses from interaction, including blocked dependencies, duplicated work,
correlated errors, and recovery after a delayed handoff. [Couzin et al., *Effective Leadership and Decision-Making in Animal Groups on the Move* (2005)](https://doi.org/10.1038/nature03236) ·
[Woolley et al., *Evidence for a Collective Intelligence Factor in the Performance of Human Groups* (2010)](https://pubmed.ncbi.nlm.nih.gov/20929725/)

Ostrom's work on polycentric governance suggests a further distinction between where decisions
are made and which rules apply to everyone. TREMOR can vary assignment authority while holding
the board's rules, scoring, and information access fixed. A separate comparison can vary what
each worker sees while holding authority fixed. This helps diagnose whether an observed change
comes from the decision structure or from access to evidence. [Ostrom, *Beyond Markets and States* (2010)](https://www.aeaweb.org/articles?id=10.1257/aer.100.3.641)

## Delegation, oversight, and trust

Jensen and Meckling describe costs that arise when a principal delegates decisions and cannot
perfectly observe the agent's actions. In TREMOR, the principal sets the goal and policy, workers
observe local state and propose or perform actions, and a separate verifier checks evidence. An
orchestrator is itself a delegate when it assigns work. This lens gives us measurable risks:
verifying too little, checking everything at prohibitive cost, or rewarding a proxy that diverges
from verified work. [Jensen and Meckling, *Theory of the Firm* (1976)](https://doi.org/10.1016/0304-405X(76)90026-X)

Lee and See frame trust as appropriate reliance given the task and evidence. Greenblatt et al.
evaluate oversight protocols under a limited auditing budget. TREMOR's trust ladder applies these
ideas to scoped permissions: propose, verify, grant a bounded lease, then recheck, revoke or escalate.
Line 6 compares evidence leases with a tuned fixed rule and a time-boxed grant. Measure over-grants
and blocked legitimate actions together. Charge the time and compute required to collect evidence
and escalate. [Lee and See, *Trust in Automation* (2004)](https://doi.org/10.1518/hfes.46.1.50_30392) ·
[Greenblatt et al., *AI Control* (2024)](https://proceedings.mlr.press/v235/greenblatt24a.html)

## Residency research comparators

The Residency announcement cites these as examples from the Anthropic Fellows Program.
[Anthropic Residency announcement](https://alignment.anthropic.com/2026/anthropic-residency/)

| Work | What it establishes and what TREMOR takes from it |
|---|---|
| [Fronsdal et al., *Petri* (2025)](https://www.anthropic.com/research/petri-open-source-auditing) | Petri pairs an open auditing tool for multi-turn behavior with pilot evaluations and a case study with ablations. TREMOR targets verifiable team outcomes. Its release should let readers reproduce the benchmark, inspect a failing trace, and see how the outcome changes when a coordination rule is removed. |
| [Chen et al., *Persona Vectors* (2025)](https://www.anthropic.com/research/persona-vectors) · [Paper](https://arxiv.org/abs/2507.21509) | The paper extracts activation directions associated with traits and tests monitoring and intervention. It motivates L8's controlled test of whether an activation readout adds information beyond text monitors on held-out local runs. |
| [Cloud et al., *Subliminal Learning* (2025)](https://arxiv.org/abs/2507.14805) | The study finds behavioral transfer through training data in the tested shared-base distillation setups even when overt examples of the trait are filtered. It motivates checking what gets carried across a learning boundary. TREMOR tests runtime propagation through shared notes and verified memory replay under separate protocols. |

The release target is a versioned benchmark with scripted positive and negative controls, a frozen
protocol and scoring rule, deterministic replay from shareable traces, paired episode comparisons
at matched budgets, and a held-out replication on a second model family. Independent scorers
should agree on the same logged evidence. We will report uncertainty, failure cases, and null and
inconclusive outcomes with the tasks, models, and conditions each claim covers.

## QGrid and the quantum simulator

TREMOR includes its own [Python gate-level simulator](quantum/gatesim.py), based on the classical
statevector verification approach we used in QGrid. We cross-checked it against QGrid's NumPy
simulator and the closed-form probability for Grover search. The internal differential rerun
compared 329 statevectors from 65 cases over one to
ten qubits, with zero disagreements. The amplitude tolerance was 1e-9 and the probability tolerance
was 1e-12. QGrid's simulator is used read-only as an internal reference. [Grover, *A Fast Quantum Mechanical Algorithm for Database Search* (1996)](https://arxiv.org/abs/quant-ph/9605043)

From the repository root, run a circuit and verify the simulator:

```bash
python3 -m quantum --qubits 3 --marked 5 --iterations 2
python3 -m unittest discover -s tests -v
```

The simulator writes JSON showing the marked-state probability, the analytic expectation, their
absolute difference, and state normalization error for each iteration. The circuit, reference
calculation, and standalone tests use only Python's standard library.

After EP-1, use these checks to build an independently scored held-out task family. For example,
agents can choose an iteration count and justify a predicted success probability, then an exact
reference checks the result. This tests whether the coordination findings travel beyond the
arithmetic task family. The release design pairs the independently implemented simulator with
public circuit definitions and closed-form checks. The completed evidence is simulator agreement
on idealized circuits.
