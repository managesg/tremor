# Owner approvals for the emergence program (recorded by the parent, verbatim)

These are the project owner's own words from the live session, quoted exactly (including typos).
Recorded 2026-11-19. Any paid step must cite this file.

1. "Yes please go ahead with your recommendation and I give you a 10 dollar celeing for testing with
   API and also keep using the GPU. You have the Claude API key on my .env to use. I like the latest
   approch. Have fable develop it and Opus + Sonnet orchestrate and implement it"
2. "there is a key please check again or use other model key you can find for now also use the
   typescript key for jev. Go on with the plan please"
3. Earlier, on the next-steps list: "go on with all your recommendations" and
   "Go ahead with all your recommendations" (the list included local commits in this repo with no push).

## What the parent did with them
- The Anthropic key was found in `manageesg-backend/.env.live` (a live-environment file). Only that one
  variable was read, in-process, never printed; validated with the free model-list call. No other key
  was read or used. No TypeSafe/JEV key exists in the env files; none was used.
- Overall API ceiling: USD 10 (owner). Code hard stop: USD 9.00 absolute; EP-1 sub-cap USD 5 and 500
  calls; canary sub-cap USD 0.05 inside EP-1.

## Still required before the FIRST paid call
- [ ] Owner acknowledgement (one line) that a direct API key has no provider-enforced spend cap, so the
      ceiling is enforced only by our own ledger (policy: Safety rule 8, soft-budget acknowledgement).
- [ ] Opus acceptance of the fixed spend code (spend-verification D1-D9 re-verified).
- [ ] Rung 0 passed; EP-1 pre-registration frozen (commit first, then prereg-check).
- [ ] Haiku 5.5 price confirmed by the canary (Console cost equals the ledger).
- [ ] Price sheet fetched within 3 days (current sheet expires 2026-11-22).

## Addendum 2026-11-20: owner approval of the six EP-1 recommendations
Owner's words, verbatim: "Go ahead with all your recommendations I approve them. Should we use the
Quantum Simulator and Lean from out Qgrid project to test the findings too? Implement it altogether
with auto research"
The recommendations approved by that sentence (as listed in the parent's report, ep1-design-notes
section 2): (1) acknowledgement text: a direct API key has no provider-enforced spend cap and the
USD 10 ceiling rests only on our own ledger (code stop USD 9 per ledger file, USD 10 hard cap across
the pinned directory), EP-1 and the canary approval restated; (2) 3 arms x 20 task sets (480 calls);
(3) smallest effect of interest about 20 points, "inconclusive" is a legitimate result and doubling n
is a new ask; (4) canary: Haiku only, padded (the 90,000-byte option, worst case about USD 0.018), a
named canary-only exception to the 2,000-token per-call cap; (5) the key is read in-process by the
parent at launch, never printed or given to a builder; a Console workspace spend limit of USD 10 or
less is STRONGLY RECOMMENDED and must be set by the owner (not done by the parent: owner action
pending); (6) the freeze commit may include verified but uncommitted files, `train/` excluded from the
hash, local only, no push.
Parent's note: the owner approved the acknowledgement text by approving the recommendation. The parent
will ask for a one-word "confirm" with the exact numbers immediately before the first paid call
(the canary), so the soft-budget acknowledgement is stated in the owner's own live words at the moment
of spend.
Still open: the Console spend limit (owner action); the Qgrid question (project not found locally).

## Addendum 2026-11-20 (2): pilot, local model, work plan
Owner's words, verbatim: "Yes you got my approval"
In reply to the parent's three asks in the immediately preceding report: (1) the instrument pilot,
150 calls, USD 0.50 sub-cap taken from the USD 2 unallocated reserve, hand-checked traces, excluded from
confirmatory estimates; (2) downloading Qwen/Qwen3.5-4B (Apache-2.0, about 8 GB, ID and licence to be
re-verified on Hugging Face before download) into data/hf/ for the no-API memory-warning replication;
(3) the work plan in docs/WORKPLAN-CURRENT.md.
Not covered by this approval (owner action or a later live confirm): the Console workspace spend limit;
the one-word "confirm" immediately before the canary; the human baseline (about ten manual tasks).

## Addendum 2026-11-20 (3): QGrid tools, not the QGrid project
Owner's words, verbatim: "So I didn't asked to use the Qgird project but from it use the quantum simulator
and lean tools for our current research work please" and "Update work plan and goal".
Parent's reading (recorded so it can be corrected): use QGrid's TOOLS, not its domain: (1) the Lean 4
toolchain pinned by QGrid (leanprover/lean4:v4.35.0, core only, no Mathlib) and its pattern (a decision
procedure compiled from Lean definitions with kernel-checked soundness theorems and an axiom audit);
(2) its quantum simulators: PsiQDK 2.5.0 (Apache-2.0, PyPI) and QGrid's own numpy statevector simulator.
Approved installs, CONTAINED in the repo (no global tool, no elan, no PATH change): the official
lean-4.35.0-linux_aarch64 release archive (about 595 MB) extracted under data/tools/lean (gitignored);
psiqdk==2.5.0 in a repo-local virtual environment under data/venv-q (gitignored). Rollback: delete those
two folders. QGrid source is internal (no licence file): code is read, never copied into this repo
verbatim beyond short API facts; nothing is republished.

## Addendum (4), 2026-11-20

Owner, verbatim, two messages:
1. "Yes agree with your recommendation including the spend limit"
2. "Confirm"

Context: both replied to the orchestrator's list after G0-2R3. The list asked the owner to:
- set the Anthropic Console spend limit to USD 10 or less;
- send the one-word "confirm" for the canary;
- decide on the human baseline.

Recorded reading:
- The owner agrees to the recommendations, including the Console limit of USD 10 or less, which only the owner can set in the Console.
- "Confirm" is the canary confirm. It covers exactly one `ep1 canary` run: one Haiku call, USD 0.05 sub-cap, worst case USD 0.018.
- The canary runs only after the price sheet is refetched and the fake dry run is green. If either fails, the confirm is not used.
- The pilot and EP-1 each need their own confirm, after the Console check of the canary.
- Human baseline: not addressed. It stays open, or its absence is stated as a limit.

## Addendum (5), 2026-11-20 (about 14:42 UTC)

Owner, verbatim: "Yes then that is the key you should be using its just its have not update the usage yet ... CONFIRM PILOT also check the Spark"

Background:
- The orchestrator confirmed, without printing it, that the key's start and end match the owner's `sk-ant-api03-2ww...EQAA`.
- The Console, "data as of 13:43 UTC", did not yet show the 13:22 UTC canary.

Recorded reading:
- The owner accepts that the canary was billed to this key and that the Console is lagging.
- The Console comparison (46,605 in, 4 out, Haiku 5.5, Nov 20) is deferred, not waived. It must still match before EP-1.
- "CONFIRM PILOT" covers exactly one `ep1 pilot` batch: USD 0.50, 150 calls, 345,000 tokens, finishing by 2026-11-23 on the unchanged price sheet.
- EP-1 needs its own confirm after the pilot traces are hand-checked.
