# Lance Martin, "Exploring Claude's Frontier" (AI Engineer Code Summit 2026)

Source status: owner-supplied machine transcript (YouTube y9JtCCZP2MQ, 03:48:31-04:06:48, recognition
errors remain) and owner-supplied slide screenshots. Not independently verified against the blog posts
or the recording. Figures below are read off slides by the assistant: they are TALK CLAIMS, owner-validated
as Anthropic material, not peer-reviewed. Slide numbers may contain OCR/reading error; re-check against the
recording before any public quote.

## Story 1: a 1,000-agent team formalizes Fermat's Last Theorem in Lean (Fable 5.2 launch blog)
Setup (slide "harness"):
- 1 lead + 999 helpers. Each agent: its own lightweight VM sandbox, no API keys/credentials, no network
  access, no direct path to other sandboxes. Agent loop (harness code) runs inside the sandbox with
  NO tool access to that code; tools = shell, file editor; unprivileged user account; files = repo, Lean,
  math library.
- "The only link out" is a gateway (a pipe, not a network) outside the sandboxes: model requests (calls
  the Claude API, classifies tool calls, records the response, returns it only if checks pass) and Git/SQL
  requests (forwarded to Git and Postgres; agent identity set at the gateway; every push and query logged).
- Team infrastructure: Git repo (Lean files, plans; own-branch pushes only; merge job for main) and
  Postgres (instructions, tasks, notes; shared unprivileged role; time and size limits).
- Monitoring: (2) real-time blocking classifier on each tool call, fail-closed; (3) offline monitoring of
  run records kept outside sandboxes; run owners told of serious findings. Talk: offline review of all
  agents' runs every 10 minutes.
- Prompt: one lead, 999 helpers, awareness of Git, the database and the problem statement. No domain
  harness (earlier September work used a dozen agents, a domain harness "ProofToMe" and researcher support).
  No human steering of the solution. Ran about 30 hours.
- CORRECTION (2026-11-19, from research/10 and research/14, which opened the written posts): this was
  NOT a no-harness result. "No domain harness" means only that the ProofToMe platform was absent. The
  agents were given lead and helper roles in the prompt, the 60 target statements, a one-sentence route
  sketch, definitions and 47 already-proved lemmas; Lean checked every proof (a machine verifier); and the
  sandbox, gateway, classifier, monitors and merge job above stayed in place. The post calls the run a
  "toy experiment" and gives 28.7 hours; one run, not reproduced. Read "little coordination scaffolding",
  never "no harness".
Self-organization (the agents, not the prompt, created these tables about five minutes in):
- Announce (lead's orders to everyone), Assign (who works on what), Notes (open board), Subtasks (shared
  to-do list, owned by first helper to grab it), Landed (log of finished work and whether it passed checks).
  Write/read pattern per slide: Announce, Assign = lead writes, helpers read; Notes = everyone both;
  Subtasks = anyone adds, first helper claims; Landed = helpers write, lead reads.
- Hour 0.3: 56 writes, 3,561 reads. Hour 5.3: 12,929 writes, 147,425 reads (read:write about 11.4).
  Hour 5.3 per table (lead/helpers): Notes writes 7/9,495, reads 64/77,790; Subtasks writes 0/2,967, reads
  3/23,470; Announce writes 18/1, reads 5/23,782; Assign writes 22/0, reads 40/16,196; Landed writes 0/386,
  reads 25/4,720; other tables (look-up, claim limit from lead; three helper check logs on main) writes 2/31.
- Progress of the 60 statements: hour 0.2 -> 0 proved (999 helpers "not running"); hour 1.2 -> 13 proved
  (563 at a statement, 309 working, 125 idle); hour 1.9 -> 18; hour 4.8 -> 34 (333 at a statement, 108 at a
  line of work/shared tools, 326 working, 209 idle, 2 not running). The lead grouped statements by how it
  staffed them ("landed first", "judged doable", "set aside, staffed by hour 1.2", "set aside, taken up from
  hour 1.5", "modularity lifting", "Langlands-Tunnell", "last links").
- Hour 22.6: 1,079 of 2,418 written tasks shown for one hard subtree (Langlands-Tunnell), 946 marked done.
  Agents built their own task trees/abstractions for hard parts.
- Lead's note: "Total freeze of origin/main, effective now ... Magnificent work, all 999 of you."
- Claim: a formalization expected to take years completed autonomously with Git + a database only.
  (Talk claim; see the CORRECTION above: roles, 47 proved lemmas and the Lean verifier were also given.)

## Story 2: memory and "dreaming" (Anthropic engineering blog)
- Framing: life understood backward, lived forward (Kierkegaard). Agents write memory myopically/greedily
  inside a session; memory must be globally coherent and non-redundant. Human analogy: hippocampus replay
  to neocortex during sleep. Decomposition: daily memory vs long-term knowledge.
- Architecture slide: Transcripts (searchable event log) -> Memory notes (salient observations written by
  Claude) -> Memory representations (computed from transcripts and notes, e.g. wikis) -> Injected context
  (memory loaded into every session). "Dreaming" is the offline process across these layers.
- CL-Bench (open-source continual-learning benchmark per the talk): 40 questions about a database, fresh
  session each, a memory directory with no memory prompting. Task score with memory store vs stateless:
  Opus 5.5 0.838 vs 0.655; Sonnet 5.5 0.833 vs 0.644; Opus 5 0.828 vs 0.564; Opus 4.7 0.700 vs 0.383;
  Sonnet 5 0.610 vs 0.306; Sonnet 4.6 0.364 vs 0.330. Reading: the memory benefit grows sharply with model
  capability (+0.03 for Sonnet 4.6, +0.18 for Opus 5.5). Talk: weaker models do not reliably know when to
  write or read memory.
- Pokemon memory directories (area proportional to characters of memory, same scale): Claude Sonnet 3.7
  413 files, 977,930 characters at step 9,989 (many directories named "consolidated", "master", "core",
  an alarm-named "emergency"); Claude Fable 5 10 files, 43,406 characters. Talk: stronger models have better
  salience instincts; Fable 5 got much further.
- Wrong-memory trap: an incorrectly written landmark location trapped the agent in a loop (falls through a
  trap door back to the prior level). Raw memory regressed (fell off the ledge, backtracked to Pewter);
  memory + dreaming found the exit ladder and reached Cerulean at action 1935 in the first plotted run window
  shown; no-memory stayed flat. Talk: "a poison memory was injected and it's stuck there. Dreaming can rescue
  that."
- Representations (Stainless corpus, anonymized, 25 questions answerable only from the corpus; wikis built
  by Opus 5): search tool without wiki 53%; wiki alone 13% after 2 dreaming sessions rising to 48% after
  128; wiki + search 54% after 2 sessions rising to 61% after 128. Axis is log scale. The slide labels it
  2M to 128M with the note "budget of 1M tokens per session, not measured spend"; Anthropic's written post
  puts sessions (2 to 128) on the x-axis (research/14, research/17). CORRECTION (2026-11-19): the axis is
  sessions at a nominal budget. Tokens actually spent are not reported. Example wiki after 2 sessions: 103 pages, 766 links; after 128 sessions: 222 pages,
  12,893 links. Dreaming also fills placeholder pages and builds an index.

## What this implies for murmuration (assistant's reading, interpretation, to be tested)
1. Stigmergy at scale: the tables are a shared environment, not messages. Read:write about 11:1 and 80%+ of
   traffic on Notes/Subtasks (about 71% by my sum of the hour-5.3 table): cheap reads dominate. Matches the cost slide below (cache reads dominate cost).
2. Idle compute is visible and measurable: 125-209 of 999 helpers idle at hours 1.2-4.8 (about 13-21%).
   This is the idle-compute-fraction metric in PRINCIPLES.md measured in the wild.
3. Near-decomposability (Simon) and Ostrom-style rules appear in the design: statements grouped by staffing,
   own-branch pushes only, merge job for main, time/size limits, fail-closed monitoring.
4. Dreaming has a dose curve: wiki alone gains 35 points for 64x the dreaming sessions (2 -> 128, each
   with a nominal 1M-token budget, not measured spend); wiki+search gains 7 points. Value-of-computation
   question: what was actually spent, what is the marginal gain per token spent, and does equal-token
   extra search/retry give the same? (H3 control.)
5. CORRECTION (Fable review): the memory gain is NOT a smooth capability gradient. From the slide numbers the
   gain is +0.03 (Sonnet 4.6), +0.19 (Sonnet 5.5), +0.26 (Opus 5), +0.32 (Opus 4.7), +0.30 (Sonnet 5), +0.18
   (Opus 5.5): near zero only for the weakest model, largest for mid models, smaller at the top because
   stateless scores are already high. Read it as a threshold. The CL-Bench paper abstract also says naive
   in-context learning beats dedicated memory systems (see research/10). A small local cell model may need
   MORE structure (schema,
   lint, caps) than Lance recommends for frontier models. New hypothesis H8 candidate: required memory
   structure is inversely related to model strength; test with the same CL-Bench-style task on a small
   local model vs Claude.
6. Sources to open before public claims: the Fable 5.2 launch blog, the Anthropic memory/dreaming
   engineering post, the CL-Bench repo/licence, the harness diagram source link on the slides.

## Diogo Almeida slides seen (talk "Agents beyond the KV cache", TypeSafe AI)
- Bullets: much of the "tyranny of agent design" comes from the KV cache; why is memory O(N) instead of
  log(N); why is state not shared between agents; why can't non-naive routing/subagents work.
- Cost slide citing a Sep 09 2026 post "(KV) Cache Rules Everything Around Me": what devs think agents cost
  (output about 75%, input 18.8%, cache write 4.7%, cache read 1.5%) vs what agents actually cost (cache
  read about 67%, output 18%, input 12%, cache write 3%; assumes 100% cache hit rate; cache write = the
  extra 25% write premium). Slide read by the assistant; verify against the post.
- Second slide: "Principal-agent solutions + spirit over letter" (agency problem: moral hazard, adverse
  selection) — relevant to permissions and delegation. Full talk transcript: see research/10.
