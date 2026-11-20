# D3 decision: the refusal stop is per agent

2026-11-20. Owner-delegated design decision, answering G1 D3. Code: `enforce.Refusals`, `enforce.Enforcer`, `team._Episode`.

## Rule

- **3 consecutive refusals by the same agent** stop that agent's contribution to the episode. Its later turns are
  skipped, and a later action from it is answered `agent_stopped` (not counted as a new refusal).
- **The episode ends only if** every agent is stopped, **or** the team total reaches **20** refusals.
- **A counter is reset only by that agent's own admitted action** (a `read` is an admitted action). Reads and
  admitted actions of other agents never reset or advance another agent's counter.
- Applies to every arm, but only the enforced arms (`code`, `both`) can refuse, so only they can stop anyone.

## Reason

G1 D3: the old counter was one team-wide run, reset by any admitted read. Four agents herding on task 0 in
round 1 (a1, a2, a3 each refused once) stopped the code-arm episode at `Y = 0`. Reading first gave `Y = 0.25`.
Herding is the expected model behaviour, and the pre-registration forbids behavioural re-runs, so a team-wide
stop would bias `Y_code` downward in one arm only. A per-agent run measures an agent's own persistence in
breaking a rule, which is what the defensive stop was for.

## Effect on rung-0 expectations

None. Scripted agents in the A code arm read first, are refused at most once in a row, and never reach 3. The
enumerated `Y_code` for A stays `85469/86400`, the rung-0 table stays GREEN, and every episode ends `complete`.
Tests: `test_enforce.PerAgentStop`, `test_team.RefusalStopTests` (the herding scenario: `ended = complete`,
`Y = 0.25`, nobody stopped), and the enumeration in `test_team`.

## Limits

- `Refusals(agents=None)` counts the agents *seen so far*, so a lone early actor who is stopped ends the episode.
  `Enforcer(practices, agents=[...])` fixes this, but `router.seal` does not pass it yet. It needs one call-site
  change in `router.py` (`seal(..., agents=None)` forwarded to `Enforcer`), and the model loop (G1b) must pass the
  agent list.
- `router.act` records a board error with `enf.refusals.record(True)` and no agent. That refusal counts toward the
  team total and the anonymous agent only; passing `action.get("agent")` there would attribute it.
- The harness's own identity-spoof refusals use a separate `Refusals` in `team._Episode`: same per-agent rule, but a
  separate team total.
