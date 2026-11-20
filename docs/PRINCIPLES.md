# Principles: simple, first-principles, cost-aware

Complex-systems theory supplies **what to measure**. These rules decide **what we are allowed to
build**. Where they conflict with another file, these win. Sources for each rule are filled in from
`research/06-first-principles-and-efficiency.md`; until a rule has a verified source it is a design
commitment, not a cited fact.

## Evidence status of this file (see `SCIENCE.md` 7.2a)
Verified from abstracts only: scaling laws, test-time-compute efficiency, energy per prompt, and the
token-usage-explains-variance result (Anthropic, vendor data). NOT verified, cited from memory:
Fermi, MDL, Gall, Unix, Hickey, Chesterton, Amdahl, Little, roofline, Zilberstein, Musk's exact
wording. Energy on this box = sampled GPU power x time only. The 72% cache-saving figure is
talk-only and is not used in any cost model here.

## The five-step filter (applied to every requirement, module and experiment, in this order)
1. **Question the requirement.** Name the person who needs it and the decision it changes. No owner
   or no decision = cut. (Every requirement is partly wrong; ours too.)
2. **Delete.** Try removing it first. If nothing breaks, it stays deleted. If we end up restoring
   less than ~10% of what we cut, we are not cutting enough. Counter-rule (Chesterton): before
   deleting a guard, find out what it guards against.
3. **Simplify.** Only after deleting. The smallest design that can still fail the hypothesis.
4. **Accelerate.** Shorten the loop (CPU-only, seconds-long replays) before adding hardware.
5. **Automate.** Only what is already simple, stable and run more than twice.
(Provenance: the "algorithm" as Musk describes it in interviews; exact quotes to be confirmed in
research file 06. We use it as a working discipline, not as authority.)

## Physics-style rules
- **Every quantity has units.** tokens, joules, USD, seconds, prompts, idle-rule-days. No unit, no
  metric. Dimensionless ratios are reported with both numerator and denominator.
- **Budgets are conserved.** Any comparison holds one budget fixed (tokens, or joules, or USD) and
  varies one thing. A strategy that wins by spending more is not a win.
- **Fermi first.** Before any run, write the order-of-magnitude estimate of cost and expected
  effect. If the estimate says the effect cannot be seen at the planned n, do not run it.
- **Measure the bottleneck, not the guess.** Decode on a unified-memory machine is expected to be
  memory-bandwidth-bound; we measure tokens/s and watts before sizing anything (roofline thinking).
- **No new term without a null.** Each concept enters with a baseline that ignores it. If the
  baseline ties, the concept is dropped (Occam / description length).

## Simplicity rules
- Stdlib first. A dependency must replace more code than it adds, and must be pinned.
- One file per idea until it hurts. No framework, no plugin system, no config language.
- A mechanism earns its keep with a measured gain at matched cost, or it is removed.
- Prefer a deterministic check to a model judge; prefer a lookup to a model call; prefer a small
  model to a large one; prefer no model to either, when the answer is computable.
- Complexity budget: the repo stays small enough to read in one sitting. Growth needs a paragraph
  saying what it replaces.

**Hub-and-cells rules** (`ARCHITECTURE.md`). A cell is a directory of plain files the owner can
read and edit; the contract is four JSON files; cells talk only to the hub. No bus, daemon,
framework or cell-to-cell channel is added until a measured failure of the plain version names
it. A cell gets a model only where the model beats the no-model stub on held-out tasks, and a
task class leaves the hub only after a tier has cleared that class's floor. The hub adds a
model verifier only where no deterministic check exists. What this replaced: the T6
demonstrator, E3.2, and (deferred) Claude batch C3.

## Sustainability and compute rules ("when to run")
Every experiment reports, next to its quality metric, the same four costs:

| Metric | Unit | How measured |
|---|---|---|
| tokens per passing task | tokens / pass | API usage fields; local token counts |
| energy per passing task | J / pass (Wh) | GPU+system power sampled during the run (NVML / nvidia-smi); say what is NOT covered (CPU, DRAM, cooling) |
| money per passing task | USD / pass | price sheet read at run time, recorded in the manifest |
| idle-compute fraction | dimensionless | GPU-seconds with no work / reserved GPU-seconds |

**The run gate (value of computation).** Run an experiment, a dream pass, a fan-out, or a retry
only if `P(change in decision) x value of that decision > cost` in the same units. Concretely:
1. Estimate cost with a Fermi pass and from the smoke run.
2. Start with the cheapest instrument (replay, tabular model, CPU) and stop there if the answer is
   already clear.
3. Use an anytime design: every run can stop early with a valid partial result and a recorded
   reason, so a hopeless run does not burn its full budget.
4. Cache everything keyed by (code hash, config hash, seed). Never recompute a finished cell.
5. Batch GPU work so the device is not idle; run it when the machine is otherwise unused; kill it
   at a free-memory floor.
6. A result that cannot change what we do next is not run.

**Where the same logic lands in the product ideas** (hypotheses, not claims):
- Fan-out is a *cost* decision: gate it on predicted decomposability, at matched tokens (H2).
- A dream pass is a *compute* decision: it must beat the same tokens spent on retries (H3).
- Permission decay is a *risk-per-prompt* decision: exposure bought per prompt spent (H1).
- Local small model vs Claude is a *routing* decision: use the cheapest model whose held-out
  quality clears a floor; escalate only on failure (cascade) (H6).
- A weight edit or adapter is a *cost* decision too: it must beat a decoding setting under the
  same token cap (H7).

## Scope guard: what this project is NOT (owner, 2026-11-19)
We are not building a frontier-lab model, not pretraining, not racing a frontier model on general
capability, and not training a local model to imitate one. The local model is an instrument that makes
many seeds cheap and tests whether an idea survives without frontier capability; the hub stays a
frontier model we do not build. A track that needs a bigger local model to make its point is cut.
Every track must test one of three idea families, each with a matched-cost baseline:
1. **Memory:** provenance-linted and supersedable shared memory, dreaming against equal-token
   controls, structure imposed versus free-form by model strength (H3, H4, H8, E8.x).
2. **Green efficiency:** tokens, joules and USD per passing task, idle-compute fraction, the
   value-of-computation run gate, cheapest-model-that-clears-the-floor cascades (H6, E8.1, T7 cost).
3. **Adaptive policies and rules:** grow-on-need / decay-on-idle permissions under a human-signed
   ceiling, adaptive fan-out gates, rules learned from observed use and tested on held-out sessions
   (H1, H2).
Weight edits (T7) stay only as a cheap pre-test of whether a frontier model can adjust a small cell
better than a decoding fix; if it cannot, it is deleted.

## What these rules deliberately forbid
- A simulator whose constants we invent, and any result that only restates its assumptions.
- A metric with no unit, or a comparison with unequal budgets.
- A model judging its own output as the only evidence.
- Adding a track because it is interesting rather than because a decision depends on it.
- Reporting quality without cost, or cost without quality.

## Honest limits
Elon-Musk-style and physics-style heuristics are working disciplines, not proofs; they can delete
something that mattered. The guard is the baseline test: every deletion and every addition is
checked against a measured, matched-cost comparison, and Chesterton's question is asked first.
Energy figures cover only what we can measure on the box and are never extrapolated to a data
centre or to Claude's serving side.
