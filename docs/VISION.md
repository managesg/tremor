# murmuration: what we are trying to build

Date: 2026-11-19. Status: **vision and design. Built so far: one permission-replay ledger with
nine unit tests. Nothing else below is built or run.** `PRINCIPLES.md` wins any conflict.
Details: `ARCHITECTURE.md` (design), `PLAN.md` (hypotheses, tests, gates), `SCIENCE.md`
(concepts, evidence status). Labels used here: *established* (accepted in its home field),
*talk claim* (said or shown in a conference talk, owner-validated, not checked by us),
*interpretation* (our mapping), *speculative* (no evidence yet).

## The thesis in one paragraph

A strong central model is good at planning, checking and judging. Small local models are cheap,
private and always on, and are only good at narrow jobs. We want one system that uses both: a
**hub** that plans and verifies, and many small **cells** that do narrow work under permissions
the owner signs, with their own memory, on the owner's own machine where possible. Every part is
a plain file the owner can read, edit and take away. Every design choice is a hypothesis with a
number attached: how many tokens, joules and dollars one passing task costs. If a part does not
earn its cost against a simpler baseline, it is deleted. We build the measuring instruments first and the
system second.

## The picture

```
            OWNER  holds the signing key; can read and edit every file
              |    signs permission ceilings; edits memory, prompts, routes, adapters
              v
   +--------------------------------------------+
   | HUB  strong model (Claude)                 |
   | plans - splits work - routes - verifies    |
   | keeps the shared memory it has linted      |
   +------+-----------------+-------------+-----+
          | signed policy   |             |      ^
          | + task          |             |      | result + evidence + cost,
          v                 v             v      | memory digest (never raw logs)
      [ cell ]          [ cell ]      [ cell ]---+
      plain code        local model   Claude worker
      (no model)        (+ adapter)
      each cell: own folder, own log, own memory, narrow permissions

   Central    = the routing table sends every job to the Claude tier.
   Decentral  = the routing table sends a job class to a local cell
                once that cell has cleared a quality floor on held-out tasks.
```

## The parts, and what each one rests on

**Permissions that grow and decay.** A cell starts with a small base. Inside a ceiling signed by
the owner, a permission is granted when first needed and dropped after it sits unused. Anything
outside the ceiling is escalated to the owner. Source: CJ Avilla's talk (base policy, human-signed
ceiling, grow on need, shrink after about two weeks unused) — *talk claim*. Ours is only the
measurement: does decay cut standing exposure without adding many prompts (H1)? Not yet measured.

**Bounded autonomy.** Hard limits beat judgement: deny rules, a sandbox that bounds side effects,
hooks that block, and an orchestrator separate from workers (Lydia Hallie's talk — *talk claim*;
the caveats we verified are in `SCIENCE.md` 7.2a: the Claude Code sandbox covers shell commands
only, and Bash deny rules can be bypassed).

**Orchestration.** Lance Martin showed one lead and 999 helpers proving 60 Lean statements in
about 30 hours with only a Git repository and a database, behind a gateway that set identity and
logged everything; the agents built their own task tables (*talk claim*; the write-up calls it a
toy experiment and it is unreproduced). We take a question from it, not a recipe: does that
self-organisation need a frontier model, or can small local cells do it if handed the table
structure (H9)? And when is splitting work worth its tokens (H2)?

**Memory and dreaming.** Agents write notes greedily during a session; an offline pass
("dreaming") rewrites them into coherent long-term memory (Lance Martin — *talk claim*). His
slides also show the limits: a wrong note can trap an agent, weak models sprawl (hundreds of
files) and may not use memory at all, and extra dreaming tokens buy less and less. Our stance:
every note carries a source pointer; a dream pass must beat the same tokens spent on retries or
plain search (H3); shared memory needs governance or early errors lock in (H4); weaker models
probably need more imposed structure (H8). All untested by us.

**Local models.** Small open-weight models (Qwen, Gemma and others) run on the owner's GPU box;
Unsloth is the planned tool for training small adapters. A local model gets a job class only when
it beats a no-model stub and clears a fixed floor on held-out tasks (H6). No model has been
downloaded or benchmarked.

**Weight surgery.** An MIT post (2 Nov 2026) reports a frontier model editing 0.016% of a small
model's weights and raising its maths score sixfold. *Verified and qualified*: one run per
budget, no fine-tuning or decoding baseline, and the gain is mostly repair of a repetition loop
(`SCIENCE.md` 7.2a). We test that one edit once against simple decoding settings (H7) and expect
it to lose. A hub that edits cell weights in a loop is *speculative* and not built.

**Ownership, control, edit.** The owner's principle: I can open, understand, change and remove
every part. So: a cell is a folder of plain files; policy takes effect only with the owner's
signature and no model can hold the key; memory is corrected by appending, never by silent
deletion; base weights are never modified, edited models are hashed copies; rollback is one line.

## Complex-systems ideas: used only where they give a number

| Idea (home field) | What we measure | Status of the mapping |
|---|---|---|
| Near-decomposability (Simon) | coupling between parts of a task, before fan-out | interpretation; H2 |
| Stigmergy: coordination through a shared environment | read:write ratio, claim races, duplicate work on a shared board | interpretation; H9 |
| Commons governance (Ostrom) | error lock-in in shared memory with and without rules | interpretation; H4 |
| Usage-based decay (memory research) | chance a permission is reused after idle time | analogy; H1 |
| Consolidation during sleep (neuroscience) | dream gain at equal tokens | design frame only; H3 |
| Queueing and utilisation | idle fraction of agents and of the GPU | interpretation; descriptive |
| Model cascades, value of computation | cost per passing task, cheapest tier clearing a floor | interpretation; H6 |

The rest of complexity science (criticality, scaling laws, edge of chaos) stays parked until it
yields a prediction that can fail.

## First principles and sustainability

The five-step filter, in order, applied to every requirement, module and experiment: **question
the requirement, delete, simplify, accelerate, automate.** Every result reports quality next to
four costs: **tokens per passing task, joules per passing task, USD per passing task, and idle
fraction.** The **run gate**: run an experiment, a dream pass, a fan-out or a retry only if the
chance it changes a decision, times the value of that decision, exceeds its cost. Comparisons
hold the budget fixed. No simulator with invented constants. Missing cost is recorded as unknown,
never as zero.

## Connecting a very strong model to everyone's local agents

The question: if the hub model becomes far stronger than any person's local model, how do
ordinary people's local agents benefit without handing over control? Four mechanisms, with what
we can honestly say about each:

1. **Distil verified skills into local weights.** Work the hub did that passed a deterministic
   check becomes training data for a small adapter that a local cell runs. *Speculative.* The
   only evidence we cite says weight edits removed an obstacle and did not add an ability.
2. **Share memory digests, not logs.** Lessons travel as short records with a source pointer,
   linted before acceptance. *Design; untested.*
3. **Each person signs their own policy.** The hub may propose; only the person's key grants.
   *Design; the signature check is ordinary practice and is testable now.*
4. **Route by cost.** Most work runs locally; only what the local cell fails is escalated.
   *Hypothesis H6.*

The real risks: **concentration** (everyone leaning on one hub means correlated errors, one
point of failure and pricing power); **memory poisoning across users** (one bad digest spreads;
a lint checks provenance, not truth); **privacy leakage** (digests and adapters can carry
private detail; we can test retrieval leaks, not what an adapter memorised); **policy drift**
(ceilings creep, and one hub suggesting policies to everyone makes them all alike).

What we can test now: one owner, one box, a few cells — signatures, lint, leak sentinels, the
cost cascade. What we cannot test: many users, real adversaries, real incentives, or anything
about "superintelligence". We have no such system, and nothing here shows that its abilities
would transfer into small local models. That part is a direction, not a result (`ARCHITECTURE.md` 12).

## What this is not

Not a framework, a simulator, a new theory, or a claim that agents "self-organise". If it goes
well: open instruments, tests written before the data, and honest results, including the ones
that kill our own ideas.

Model roles are in `PLAN.md` 4.2, with one open question for the owner.
