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
