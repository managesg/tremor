# Lydia Hallie (Claude Code team), AI Engineer Code Summit 2026: bounded autonomy talk

Source status: owner-pasted machine transcript (video recorded at home after a technical failure; two
different YouTube IDs were pasted, the correct one is unresolved) and a pasted summary. Figures were
validated by the owner as matching Anthropic's material; they remain TALK CLAIMS. Primary-source checks
done in research/05a. Not re-verified against the recording.

## Claims (talk), in her order
- Models (Opus 5.5, Fable 5.2) are good at long-running tasks, understanding code, and (Fable) verifying
  own output. As models improve, the way we work changes: earlier in the year sessions used Opus 4.5,
  stopped sooner, needed steering and CLAUDE.md pleading ("IMPORTANT!"), and had no auto mode (manual
  approval or `--dangerously-skip-permissions`).
- Now (at Anthropic): dozens of sessions at once, running for hours, verifying their own results, sessions
  orchestrating sessions; developers have become managers of sessions. Blog figure: about 2,500 changes a
  day in May to more than 30,000 a day in September.
- Everywhere the human steps out of the loop, something else must take over: the model, the harness or the
  environment.
- Defaults: Opus 5.5 plus auto mode (default permission mode since August).
- CLAUDE.md: with today's models, keep only what Claude cannot see from the code (e.g. a legacy service not
  referenced in code). Emphatic rules can make the model go off track, give more tool calls and worse
  results. "doctor prompt audit" command checks CLAUDE.md and skills for what the new model no longer
  needs (talk claim; research/05a did not find this command in the docs: only /doctor and claude doctor).
- Auto mode: a separate classifier on nearly everything except reading/editing project files; allows known
  safe commands, blocks unsure ones; trusts the current folder and repo by default; configurable in plain
  English in settings (trusted repos, buckets, domains, always-allow, never-do).
- Study (Aug): only about 14% of people caught a clearly dangerous command; auto mode blocked 89%; about
  one in ten still went through (primary: 13.6% vs 89%, 1,053 staged testers, research/05a).
- Guarantees only come from the harness: deny rules are checked before the auto-mode classifier; a call
  matching a deny rule never reaches the classifier. Rule of thumb for what must be a rule: "if Claude gets
  it wrong once, can I take it back?" (wrong code: revertable; deleting uncommitted changes or reading a key
  into the transcript: make it a rule). Example: never read .env.
- Permissions decide whether a tool call runs, not what it can reach once running: `npm test` runs
  dependency code that could read .env or SSH keys and send them out. Fix: limit the environment: a
  sandbox (files readable, folders writable, hosts reachable, enforced by the OS including child
  processes; add a rule for SSH keys; still reads most of the machine by default). The sandbox covers only
  shell commands; Claude's own files, MCP servers and hooks run outside it.
- Cloud sessions: own machine, fresh repo copy, runs with the laptop closed; no .env or SSH keys or GitHub
  token unless provided; API keys as "network secrets" that the session uses without sending them to the
  model; network limited to package registries and GitHub by default; still: a commit pushed or a message
  sent through a connector leaves the machine; run auto mode and deny rules there too.
- Verification: with the human out of the loop the same prompt can yield different small decisions (moving
  auth to a new API: leave the old one in, only new logins, or log everyone out). Set up verification points
  (pass/fail: tests, build, screenshot). Prompting is not a guarantee; use hooks: lint on every edit, tests
  for what changed at task completion, full suite at session end. A failing script must exit with code 2
  (exit 1 marks the task completed anyway) to send Claude back to fix.
- CI is the common check for all sessions; autofix lets Claude react to failing checks; "merge when ready"
  depending on risk. At Anthropic every PR is reviewed by Claude first (fresh context, a separate group of
  agents double-checking each bug), human review by risk: docs/copy none, ordinary one reviewer, risky two.
- Direction: one orchestrator session (Claude Code projects, beta) splits work into threads (new sessions),
  tracks and verifies them; orchestrator uses a model good at deciding and judging (Fable), threads use a
  model good at doing (Opus 5.5); set separately; context management handled automatically.
- Advice: give one thing bigger than usual, make sure CI catches what you care about, configure environment
  (network, secrets, setup scripts), start in the cloud and see where you are still in the loop.

## Lydia's public bio (speaker page, owner-pasted; unverified): created JavaScript Visualized and JavaScript
Questions, co-created Patterns.dev with Addy Osmani, built a framework on Vercel's Build Output API, led
developer experience at Bun, joined the Claude Code team after Anthropic acquired Bun (Dec 2025).

## Open issues we flag, politely
1. Deny rules are not an absolute guarantee: research/05a found Bash deny rules bypassable (`/bin/rm`,
   `bash -c`); the guarantee holds through the documented decision order only.
2. The classifier's false-negative rate on overeager actions was 17% (n=52) in the March post; the human
   baseline was staged testers, not real reviewers.
3. "doctor prompt audit" not found in docs (talk claim only); the sandbox excludes hooks, MCP and file
   tools.
4. Both permission rules and CLAUDE.md lines are static: nothing in the talk describes expiry or decay of
   an allow rule (docs: "Permanently per repository and command"); our H1 asks whether decay helps, and our
   permissions corpus is too small to say.
5. Verification points are the right control, but "the same prompt gives different small decisions" is
   exactly the perturbation matrix we propose to measure (P1-P5).
